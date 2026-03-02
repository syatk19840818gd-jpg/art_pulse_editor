#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from phase1_exhibitions_text_utils import (
    canonicalize_exhibition_url,
    extract_exhibition_dates,
    extract_participating_artists_line,
    has_explicit_non_target_year,
    merge_sources,
    normalize_sources,
)


RAW_PATHS = {
    "frieze_london": Path("data/phase1_seed10/raw/exhibitions_frieze_london_2025.jsonl"),
    "liste": Path("data/phase1_seed10/raw/exhibitions_liste_2025.jsonl"),
}
LOG_DIR = Path("data/phase1_seed10/logs")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def utc_timestamp_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def choose_representative(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {}
    best = max(rows, key=lambda row: len(str(row.get("text") or "")))
    merged = dict(best)
    merged["source_url"] = canonicalize_exhibition_url(str(best.get("source_url") or ""))
    merged["target_year"] = int(merged.get("target_year") or 2025)
    merged["sources"] = normalize_sources(best.get("sources"), fallback_source_url=merged["source_url"])
    for row in rows:
        row_source = canonicalize_exhibition_url(str(row.get("source_url") or ""))
        merged["sources"] = merge_sources(merged.get("sources"), row_source)
        for field_name in (
            "headline_ja",
            "summary_ja",
            "exhibition_start_date",
            "exhibition_end_date",
            "date_source",
            "date_confidence",
            "participating_artists",
        ):
            current = str(merged.get(field_name) or "").strip()
            incoming = str(row.get(field_name) or "").strip()
            if not current and incoming:
                merged[field_name] = incoming
    merged_text = str(merged.get("text") or "")
    if not str(merged.get("participating_artists") or "").strip():
        merged["participating_artists"] = extract_participating_artists_line(merged_text)
    if not str(merged.get("exhibition_start_date") or "").strip() and not str(merged.get("exhibition_end_date") or "").strip():
        date_info = extract_exhibition_dates(
            page_url=str(merged.get("source_url") or ""),
            html="",
            extracted_text=merged_text,
            target_year=int(merged.get("target_year") or 2025),
        )
        merged["exhibition_start_date"] = date_info["exhibition_start_date"]
        merged["exhibition_end_date"] = date_info["exhibition_end_date"]
        merged["date_source"] = date_info["date_source"]
        merged["date_confidence"] = date_info["date_confidence"]
    return merged


def cleanup_file(path: Path, target_year: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = read_jsonl(path)
    grouped: dict[str, list[dict[str, Any]]] = {}
    dropped_rows: list[dict[str, Any]] = []
    for row in rows:
        source_url_raw = str(row.get("source_url") or "").strip()
        if not source_url_raw:
            dropped_rows.append({"reason": "missing_source_url", "row": row})
            continue
        source_url = canonicalize_exhibition_url(source_url_raw)
        if has_explicit_non_target_year(source_url, target_year):
            dropped_rows.append({"reason": "non_target_year_source_url", "row": row})
            continue
        grouped.setdefault(source_url, []).append(row)

    merged_rows: list[dict[str, Any]] = []
    duplicate_groups = 0
    for source_url in sorted(grouped):
        same_source_rows = grouped[source_url]
        if len(same_source_rows) >= 2:
            duplicate_groups += 1
        merged_rows.append(choose_representative(same_source_rows))

    stats = {
        "path": path.as_posix(),
        "rows_before": len(rows),
        "rows_after": len(merged_rows),
        "removed_rows": len(rows) - len(merged_rows),
        "duplicate_groups_merged": duplicate_groups,
        "dropped_non_target_year_rows": sum(1 for x in dropped_rows if x["reason"] == "non_target_year_source_url"),
        "dropped_missing_source_url_rows": sum(1 for x in dropped_rows if x["reason"] == "missing_source_url"),
        "dropped_rows": dropped_rows,
    }
    return merged_rows, stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cleanup exhibitions text raw rows by target year and source_url")
    parser.add_argument("--target-year", type=int, default=2025)
    parser.add_argument(
        "--log-path",
        default="",
        help="Optional output path for cleanup log JSON",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    file_stats: list[dict[str, Any]] = []
    for path in RAW_PATHS.values():
        merged_rows, stats = cleanup_file(path, args.target_year)
        write_jsonl(path, merged_rows)
        file_stats.append(stats)

    total_before = sum(int(x["rows_before"]) for x in file_stats)
    total_after = sum(int(x["rows_after"]) for x in file_stats)
    payload = {
        "artifact": "exhibitions_text_raw_cleanup",
        "generated_at": utc_now_iso(),
        "target_year": int(args.target_year),
        "files": file_stats,
        "totals": {
            "rows_before": total_before,
            "rows_after": total_after,
            "rows_removed": total_before - total_after,
        },
    }
    if args.log_path:
        log_path = Path(args.log_path)
    else:
        log_path = LOG_DIR / f"exhibitions_text_raw_cleanup_{utc_timestamp_compact()}.json"
    write_json(log_path, payload)
    print(f"[cleanup] rows_before={total_before} rows_after={total_after} removed={total_before - total_after}")
    print(f"[cleanup] log={log_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
