#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from r2_auto_sync import auto_sync_after_job, format_auto_sync_brief

TARGET_YEAR = 2025
RAG_CATEGORY = "exhibitions_text"

RAW_INPUT_PATHS = {
    "frieze_london": Path("data/phase1_seed10/raw/exhibitions_frieze_london_2025.jsonl"),
    "liste": Path("data/phase1_seed10/raw/exhibitions_liste_2025.jsonl"),
}

ENRICHMENT_OUTPUT_DIR = Path("data/phase1_seed10/enrichment")
ENRICHMENT_REQUESTS_PATH = ENRICHMENT_OUTPUT_DIR / "enrichment_requests_seed10_2025.jsonl"
ENRICHMENT_SUMMARY_PATH = ENRICHMENT_OUTPUT_DIR / "enrichment_summary_seed10_2025.json"


@dataclass
class CandidateRecord:
    text_hash: str
    fair_slug: str
    gallery_name_en: str
    gallery_name_kana: str
    target_year: int
    rag_category: str
    source_urls: list[str]
    needs_fields: list[str]
    text: str
    text_length: int


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
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
                records.append(row)
    return records


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")


def append_unique(items: list[str], item: str) -> None:
    if item and item not in items:
        items.append(item)


def main() -> int:
    started_at = utc_now_iso()
    print(f"[START] Post-fetch enrichment seed10 at {started_at}")
    ENRICHMENT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for fair_slug, raw_path in RAW_INPUT_PATHS.items():
        if not raw_path.exists():
            raise FileNotFoundError(f"Missing raw input for {fair_slug}: {raw_path}")

    raw_counts_by_fair: dict[str, int] = {}
    counters = defaultdict(int)
    candidates_by_hash: dict[str, CandidateRecord] = {}

    for fair_slug, raw_path in RAW_INPUT_PATHS.items():
        rows = read_jsonl(raw_path)
        raw_counts_by_fair[fair_slug] = len(rows)

        for row in rows:
            text_hash = str(row.get("text_hash", "")).strip()
            text = str(row.get("text", "")).strip()
            source_url = str(row.get("source_url", "")).strip()
            headline_ja = str(row.get("headline_ja", "")).strip()
            summary_ja = str(row.get("summary_ja", "")).strip()

            if not text_hash:
                counters["skipped_missing_text_hash"] += 1
                continue
            if not text:
                counters["skipped_empty_text"] += 1
                continue

            needs_fields: list[str] = []
            if not headline_ja:
                needs_fields.append("headline_ja")
            if not summary_ja:
                needs_fields.append("summary_ja")

            if not needs_fields:
                counters["skipped_already_enriched"] += 1
                continue

            existing = candidates_by_hash.get(text_hash)
            if existing is None:
                candidates_by_hash[text_hash] = CandidateRecord(
                    text_hash=text_hash,
                    fair_slug=fair_slug,
                    gallery_name_en=str(row.get("gallery_name_en", "")),
                    gallery_name_kana=str(row.get("gallery_name_kana", "")),
                    target_year=int(row.get("target_year") or TARGET_YEAR),
                    rag_category=str(row.get("rag_category") or RAG_CATEGORY),
                    source_urls=[source_url] if source_url else [],
                    needs_fields=needs_fields,
                    text=text,
                    text_length=len(text),
                )
                counters["candidates_new"] += 1
            else:
                counters["candidates_merged_by_text_hash"] += 1
                append_unique(existing.source_urls, source_url)
                for field_name in needs_fields:
                    append_unique(existing.needs_fields, field_name)

    candidate_rows = [
        {
            "request_id": f"seed10_enrich_{record.text_hash}",
            "text_hash": record.text_hash,
            "fair_slug": record.fair_slug,
            "gallery_name_en": record.gallery_name_en,
            "gallery_name_kana": record.gallery_name_kana,
            "source_urls": record.source_urls,
            "target_year": record.target_year,
            "rag_category": record.rag_category,
            "needs_fields": record.needs_fields,
            "text_length": record.text_length,
            "text": record.text,
        }
        for record in sorted(
            candidates_by_hash.values(),
            key=lambda x: (x.fair_slug, x.text_hash),
        )
    ]

    write_jsonl(ENRICHMENT_REQUESTS_PATH, candidate_rows)

    completed_at = utc_now_iso()
    summary = {
        "started_at": started_at,
        "completed_at": completed_at,
        "target_year": TARGET_YEAR,
        "raw_input_paths": {k: str(v) for k, v in RAW_INPUT_PATHS.items()},
        "raw_records_by_fair": raw_counts_by_fair,
        "raw_records_total": sum(raw_counts_by_fair.values()),
        "enrichment_candidates_total": len(candidate_rows),
        "counters": dict(counters),
        "output_requests_path": str(ENRICHMENT_REQUESTS_PATH),
    }
    write_json(ENRICHMENT_SUMMARY_PATH, summary)

    print(
        f"[DONE] Enrichment entry complete. raw_total={summary['raw_records_total']} "
        f"candidates={summary['enrichment_candidates_total']}"
    )
    print(f"[DONE] requests={ENRICHMENT_REQUESTS_PATH}")
    print(f"[DONE] summary={ENRICHMENT_SUMMARY_PATH}")
    auto_sync_result = auto_sync_after_job(
        target="phase1_derived",
        trigger="run_enrichment_seed10.py",
    )
    print(format_auto_sync_brief(auto_sync_result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
