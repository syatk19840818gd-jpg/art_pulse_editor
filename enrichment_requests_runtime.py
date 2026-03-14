from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


def read_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
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


def write_jsonl_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")


def append_unique(items: list[str], value: str) -> None:
    if value and value not in items:
        items.append(value)


def build_artists_enrichment_requests(
    *,
    raw_input_paths: dict[str, Path],
    output_path: Path,
    target_year: int,
    rag_category: str,
) -> dict[str, Any]:
    counters: Counter[str] = Counter()
    warnings: list[str] = []
    raw_records_by_fair: dict[str, int] = {}
    candidates_by_hash: dict[str, dict[str, Any]] = {}

    for fair_slug, raw_path in raw_input_paths.items():
        if not raw_path.exists():
            warnings.append(f"missing_raw_input:{fair_slug}:{raw_path}")
            raw_records_by_fair[fair_slug] = 0
            continue

        rows = read_jsonl_rows(raw_path)
        raw_records_by_fair[fair_slug] = len(rows)
        for row in rows:
            text_hash = str(row.get("text_hash") or "").strip()
            if not text_hash:
                counters["skipped_missing_text_hash"] += 1
                continue

            text = str(row.get("text") or "").strip()
            if not text:
                counters["skipped_empty_text"] += 1
                continue

            headline_ja = str(row.get("headline_ja") or "").strip()
            summary_ja = str(row.get("summary_ja") or "").strip()

            needs_fields: list[str] = []
            if not headline_ja:
                needs_fields.append("headline_ja")
            if not summary_ja:
                needs_fields.append("summary_ja")
            if not needs_fields:
                counters["skipped_already_enriched"] += 1
                continue

            source_url = str(row.get("source_url") or "").strip()
            existing = candidates_by_hash.get(text_hash)
            if existing is None:
                candidates_by_hash[text_hash] = {
                    "text_hash": text_hash,
                    "fair_slug": fair_slug,
                    "gallery_name_en": str(row.get("gallery_name_en") or ""),
                    "gallery_name_kana": str(row.get("gallery_name_kana") or ""),
                    "target_year": int(row.get("target_year") or target_year),
                    "rag_category": str(row.get("rag_category") or rag_category),
                    "source_urls": [source_url] if source_url else [],
                    "needs_fields": list(needs_fields),
                    "text_length": len(text),
                    "text": text,
                }
                counters["candidates_new"] += 1
                continue

            counters["candidates_merged_by_text_hash"] += 1
            append_unique(existing["source_urls"], source_url)
            for field_name in needs_fields:
                append_unique(existing["needs_fields"], field_name)

    request_rows: list[dict[str, Any]] = []
    for text_hash in sorted(candidates_by_hash):
        candidate = candidates_by_hash[text_hash]
        request_rows.append(
            {
                "request_id": f"seed10_artists_enrich_{text_hash}",
                "text_hash": candidate["text_hash"],
                "fair_slug": candidate["fair_slug"],
                "gallery_name_en": candidate["gallery_name_en"],
                "gallery_name_kana": candidate["gallery_name_kana"],
                "source_urls": candidate["source_urls"],
                "target_year": candidate["target_year"],
                "rag_category": candidate["rag_category"],
                "needs_fields": candidate["needs_fields"],
                "text_length": candidate["text_length"],
                "text": candidate["text"],
            }
        )

    write_jsonl_rows(output_path, request_rows)

    return {
        "artists_enrichment_mode": "post_fetch_requests_only",
        "artists_enrichment_candidates_total": len(request_rows),
        "artists_enrichment_requests_created": len(request_rows),
        "artists_enrichment_requests_output_path": str(output_path),
        "artists_enrichment_raw_records_total": sum(raw_records_by_fair.values()),
        "artists_enrichment_raw_records_by_fair": raw_records_by_fair,
        "artists_enrichment_counters": dict(counters),
        "artists_enrichment_warnings": warnings,
    }
