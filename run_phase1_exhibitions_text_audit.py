#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from phase1_exhibitions_text_utils import has_explicit_non_target_year


RAW_PATHS = [
    Path("data/phase1_seed10/raw/exhibitions_frieze_london_2025.jsonl"),
    Path("data/phase1_seed10/raw/exhibitions_liste_2025.jsonl"),
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit exhibitions_text raw rows against SSOT recovery checkpoints")
    parser.add_argument("--target-year", type=int, default=2025)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--artifact-name", default="exhibitions_text_ssot_recovery_audit")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    files: list[dict[str, Any]] = []
    totals = {
        "rows": 0,
        "source_url_duplicate_rows": 0,
        "non2025_source_url_rows": 0,
        "date_filled_rows": 0,
        "headline_filled_rows": 0,
        "summary_filled_rows": 0,
        "participating_artists_marker_rows": 0,
        "pdf_text_merged_rows": 0,
        "sources_field_present_rows": 0,
    }

    for path in RAW_PATHS:
        rows = read_jsonl(path)
        source_urls = [str(row.get("source_url") or "").strip() for row in rows if str(row.get("source_url") or "").strip()]
        source_unique = len(set(source_urls))
        source_dupe_rows = max(0, len(source_urls) - source_unique)
        non_target_rows = sum(1 for row in rows if has_explicit_non_target_year(str(row.get("source_url") or ""), args.target_year))
        date_filled_rows = sum(
            1
            for row in rows
            if str(row.get("exhibition_start_date") or "").strip() or str(row.get("exhibition_end_date") or "").strip()
        )
        headline_rows = sum(1 for row in rows if str(row.get("headline_ja") or "").strip())
        summary_rows = sum(1 for row in rows if str(row.get("summary_ja") or "").strip())
        participating_rows = sum(1 for row in rows if str(row.get("participating_artists") or "").strip())
        pdf_merged_rows = sum(1 for row in rows if bool(row.get("pdf_text_merged")))
        sources_rows = sum(
            1
            for row in rows
            if isinstance(row.get("sources"), list) and len([x for x in row.get("sources", []) if str(x).strip()]) >= 1
        )

        files.append(
            {
                "path": path.as_posix(),
                "rows": len(rows),
                "source_url_unique": source_unique,
                "source_url_duplicate_rows": source_dupe_rows,
                "non2025_source_url_rows": non_target_rows,
                "date_filled_rows": date_filled_rows,
                "headline_filled_rows": headline_rows,
                "summary_filled_rows": summary_rows,
                "participating_artists_marker_rows": participating_rows,
                "pdf_text_merged_rows": pdf_merged_rows,
                "sources_field_present_rows": sources_rows,
            }
        )
        totals["rows"] += len(rows)
        totals["source_url_duplicate_rows"] += source_dupe_rows
        totals["non2025_source_url_rows"] += non_target_rows
        totals["date_filled_rows"] += date_filled_rows
        totals["headline_filled_rows"] += headline_rows
        totals["summary_filled_rows"] += summary_rows
        totals["participating_artists_marker_rows"] += participating_rows
        totals["pdf_text_merged_rows"] += pdf_merged_rows
        totals["sources_field_present_rows"] += sources_rows

    payload = {
        "artifact": str(args.artifact_name),
        "target_year": int(args.target_year),
        "generated_at": utc_now_iso(),
        "files": files,
        "totals": totals,
    }
    output_path = Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[audit] output={output_path.as_posix()}")
    print(
        "[audit] "
        f"rows={totals['rows']} non2025={totals['non2025_source_url_rows']} "
        f"dupe_rows={totals['source_url_duplicate_rows']} "
        f"date_filled={totals['date_filled_rows']} "
        f"headline={totals['headline_filled_rows']} summary={totals['summary_filled_rows']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
