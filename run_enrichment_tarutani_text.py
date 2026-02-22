#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INPUT_JSONL_PATH = Path("data/Tarutani_data/tarutani_text.jsonl")
OUTPUT_DIR = Path("data/Tarutani_data/enrichment")
REQUESTS_PATH = OUTPUT_DIR / "enrichment_requests_tarutani_text.jsonl"
SUMMARY_PATH = OUTPUT_DIR / "enrichment_summary_tarutani_text.json"


@dataclass
class EnrichmentCandidate:
    request_id: str
    source_path: str
    series_name: str
    text_hash: str
    text: str
    text_length: int
    source_ext: str
    extract_status: str


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")


def build_request_id(source_path: str) -> str:
    digest = hashlib.sha256(source_path.encode("utf-8")).hexdigest()
    return f"tarutani_headline_{digest}"


def main() -> int:
    started_at = utc_now_iso()
    print(f"[START] Tarutani_Text enrichment entry at {started_at}")

    if not INPUT_JSONL_PATH.exists():
        raise FileNotFoundError(f"Missing input jsonl: {INPUT_JSONL_PATH}")

    rows = read_jsonl(INPUT_JSONL_PATH)
    counters: defaultdict[str, int] = defaultdict(int)
    series_total_counts: Counter[str] = Counter()
    series_candidate_counts: Counter[str] = Counter()
    seen_source_paths: set[str] = set()
    candidates: list[EnrichmentCandidate] = []

    for row in rows:
        source_path = str(row.get("source_path", "")).strip()
        series_name = str(row.get("series_name", "")).strip() or "UNKNOWN_SERIES"
        text_hash = str(row.get("text_hash", "")).strip()
        text = str(row.get("text", "")).strip()
        headline_ja = str(row.get("headline_ja", "")).strip()
        source_ext = str(row.get("source_ext", "")).strip()
        extract_status = str(row.get("extract_status", "")).strip()

        series_total_counts[series_name] += 1

        if not source_path:
            counters["skipped_missing_source_path"] += 1
            continue
        if source_path in seen_source_paths:
            counters["skipped_duplicate_source_path"] += 1
            continue
        seen_source_paths.add(source_path)

        if headline_ja:
            counters["skipped_already_has_headline_ja"] += 1
            continue
        if not text:
            counters["skipped_empty_text"] += 1
            continue
        if not text_hash:
            counters["skipped_missing_text_hash"] += 1
            continue

        candidate = EnrichmentCandidate(
            request_id=build_request_id(source_path),
            source_path=source_path,
            series_name=series_name,
            text_hash=text_hash,
            text=text,
            text_length=len(text),
            source_ext=source_ext,
            extract_status=extract_status,
        )
        candidates.append(candidate)
        series_candidate_counts[series_name] += 1
        counters["candidates_total"] += 1

    candidate_rows = [
        {
            "request_id": c.request_id,
            "source_path": c.source_path,
            "series_name": c.series_name,
            "text_hash": c.text_hash,
            "needs_fields": ["headline_ja"],
            # SSOT 5-5: headline_ja should include series name + short Japanese headline.
            "headline_format_hint": f"[{c.series_name} / <short_japanese_headline>]",
            "source_ext": c.source_ext,
            "extract_status": c.extract_status,
            "text_length": c.text_length,
            "text": c.text,
        }
        for c in sorted(candidates, key=lambda x: (x.series_name, x.source_path))
    ]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_jsonl(REQUESTS_PATH, candidate_rows)

    completed_at = utc_now_iso()
    summary = {
        "started_at": started_at,
        "completed_at": completed_at,
        "input_jsonl_path": str(INPUT_JSONL_PATH),
        "records_total": len(rows),
        "enrichment_candidates_total": len(candidate_rows),
        "series_counts_total": dict(series_total_counts),
        "series_counts_candidates": dict(series_candidate_counts),
        "counters": dict(counters),
        "output_requests_path": str(REQUESTS_PATH),
    }
    write_json(SUMMARY_PATH, summary)

    print(
        "[DONE] Tarutani_Text enrichment entry complete. "
        f"records_total={summary['records_total']} "
        f"candidates={summary['enrichment_candidates_total']}"
    )
    print(f"[DONE] requests={REQUESTS_PATH}")
    print(f"[DONE] summary={SUMMARY_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
