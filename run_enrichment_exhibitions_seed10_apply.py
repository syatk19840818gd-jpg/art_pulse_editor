#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from run_enrichment_exhibitions_preview import (
    ENRICH_BATCH_COMPLETION_WINDOW,
    ENRICH_PROMPT_VERSION,
    ENRICH_TEXT_MODEL,
    ENRICH_USE_OPENAI_BATCH,
    HEADLINE_MAX_CHARS,
    RAW_INPUT_PATHS,
    REQUESTS_OUTPUT_PATH,
    SUMMARY_MAX_CHARS,
    build_requests,
    build_warnings,
    generate_fallback_preview,
    generate_preview_with_openai,
    read_jsonl,
    utc_now_compact,
    utc_now_iso,
    write_jsonl,
)

APPLY_OUTPUT_DIR = Path("data/phase1_seed10/derived")
APPLY_SUMMARY_DIR = Path("data/phase1_seed10/logs")


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_row_index(rows: list[dict[str, Any]]) -> dict[tuple[str, str], int]:
    index: dict[tuple[str, str], int] = {}
    for i, row in enumerate(rows):
        text_hash = str(row.get("text_hash") or "").strip()
        source_url = str(row.get("source_url") or "").strip()
        if text_hash:
            index[(text_hash, source_url)] = i
            if (text_hash, "") not in index:
                index[(text_hash, "")] = i
    return index


def load_requests() -> list[dict[str, Any]]:
    if REQUESTS_OUTPUT_PATH.exists():
        return read_jsonl(REQUESTS_OUTPUT_PATH)

    request_rows, _ = build_requests()
    write_jsonl(REQUESTS_OUTPUT_PATH, request_rows)
    return request_rows


def main() -> int:
    started_at = utc_now_iso()
    stamp = utc_now_compact()

    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("ENRICH_TEXT_MODEL", ENRICH_TEXT_MODEL).strip() or ENRICH_TEXT_MODEL
    use_batch = os.getenv("ENRICH_USE_OPENAI_BATCH", ENRICH_USE_OPENAI_BATCH).strip() or ENRICH_USE_OPENAI_BATCH
    completion_window = (
        os.getenv("ENRICH_BATCH_COMPLETION_WINDOW", ENRICH_BATCH_COMPLETION_WINDOW).strip()
        or ENRICH_BATCH_COMPLETION_WINDOW
    )

    client = OpenAI(api_key=api_key) if api_key else None
    request_rows = load_requests()

    raw_rows_by_fair: dict[str, list[dict[str, Any]]] = {}
    raw_text_before: dict[str, list[str]] = {}
    row_index_by_fair: dict[str, dict[tuple[str, str], int]] = {}
    for fair_slug, raw_path in RAW_INPUT_PATHS.items():
        rows = read_jsonl(raw_path)
        raw_rows_by_fair[fair_slug] = rows
        raw_text_before[fair_slug] = [str(r.get("text") or "") for r in rows]
        row_index_by_fair[fair_slug] = build_row_index(rows)

    counters: Counter[str] = Counter()
    apply_rows: list[dict[str, Any]] = []
    warning_count = 0

    for req in request_rows:
        request_id = str(req.get("request_id") or "").strip()
        fair_slug = str(req.get("fair_slug") or "").strip()
        text_hash = str(req.get("text_hash") or "").strip()
        source_url = str(req.get("source_url") or "").strip()

        if not fair_slug or fair_slug not in raw_rows_by_fair:
            counters["skipped_invalid_fair_slug"] += 1
            apply_rows.append(
                {
                    "request_id": request_id,
                    "fair_slug": fair_slug,
                    "text_hash": text_hash,
                    "status": "SKIPPED_INVALID_FAIR_SLUG",
                }
            )
            continue
        if not text_hash:
            counters["skipped_missing_text_hash"] += 1
            apply_rows.append(
                {
                    "request_id": request_id,
                    "fair_slug": fair_slug,
                    "status": "SKIPPED_MISSING_TEXT_HASH",
                }
            )
            continue

        rows = raw_rows_by_fair[fair_slug]
        idx = row_index_by_fair[fair_slug].get((text_hash, source_url))
        if idx is None:
            idx = row_index_by_fair[fair_slug].get((text_hash, ""))
        if idx is None:
            counters["skipped_target_row_not_found"] += 1
            apply_rows.append(
                {
                    "request_id": request_id,
                    "fair_slug": fair_slug,
                    "text_hash": text_hash,
                    "source_url": source_url,
                    "status": "SKIPPED_TARGET_ROW_NOT_FOUND",
                }
            )
            continue

        row = rows[idx]
        text = str(row.get("text") or "").strip()
        if not text:
            counters["skipped_empty_text"] += 1
            apply_rows.append(
                {
                    "request_id": request_id,
                    "fair_slug": fair_slug,
                    "text_hash": text_hash,
                    "source_url": source_url,
                    "status": "SKIPPED_EMPTY_TEXT",
                }
            )
            continue

        current_headline = str(row.get("headline_ja") or "").strip()
        current_summary = str(row.get("summary_ja") or "").strip()
        current_hash = str(row.get("enrich_input_text_hash") or "").strip()
        current_prompt = str(row.get("enrich_prompt_version") or "").strip()

        if current_headline and current_summary and current_hash == text_hash and current_prompt == ENRICH_PROMPT_VERSION:
            counters["skipped_hash_match"] += 1
            apply_rows.append(
                {
                    "request_id": request_id,
                    "fair_slug": fair_slug,
                    "text_hash": text_hash,
                    "source_url": source_url,
                    "status": "SKIPPED_HASH_MATCH",
                    "headline_ja": current_headline,
                    "summary_ja": current_summary,
                }
            )
            continue

        if current_headline and current_summary:
            counters["skipped_already_filled"] += 1
            apply_rows.append(
                {
                    "request_id": request_id,
                    "fair_slug": fair_slug,
                    "text_hash": text_hash,
                    "source_url": source_url,
                    "status": "SKIPPED_ALREADY_FILLED",
                    "headline_ja": current_headline,
                    "summary_ja": current_summary,
                }
            )
            continue

        working = deepcopy(req)
        working["text"] = text
        working["source_url"] = source_url or str(row.get("source_url") or "").strip()
        working["gallery_name"] = str(row.get("gallery_name_en") or req.get("gallery_name") or "").strip()

        method = "fallback"
        note = "openai_key_missing"
        try:
            if client is None:
                raise RuntimeError("openai_client_unavailable")
            headline_ja, summary_ja = generate_preview_with_openai(client, model, working)
            method = "openai_direct_apply"
            note = ""
            counters["generated_openai"] += 1
        except Exception as exc:
            headline_ja, summary_ja = generate_fallback_preview(working)
            note = str(exc)
            counters["generated_fallback"] += 1

        warnings = build_warnings(summary_ja=summary_ja, row=working)
        warning_count += len(warnings)

        row["headline_ja"] = headline_ja
        row["summary_ja"] = summary_ja
        row["enrich_status"] = "applied"
        row["enrich_model"] = model
        row["enrich_mode"] = method
        row["enrich_completion_window"] = completion_window
        row["enrich_prompt_version"] = ENRICH_PROMPT_VERSION
        row["enrich_input_text_hash"] = text_hash
        row["enrich_input_chars"] = len(text)
        row["enrich_summary_chars"] = len(summary_ja)
        row["enrich_headline_chars"] = len(headline_ja)
        row["enrich_generated_at"] = utc_now_iso()
        row["enrich_notes"] = note

        counters["applied"] += 1
        if len(headline_ja) > HEADLINE_MAX_CHARS:
            counters["headline_over_limit"] += 1
        if len(summary_ja) > SUMMARY_MAX_CHARS:
            counters["summary_over_limit"] += 1
        if not headline_ja:
            counters["headline_empty_after_apply"] += 1
        if not summary_ja:
            counters["summary_empty_after_apply"] += 1

        apply_rows.append(
            {
                "request_id": request_id,
                "record_id": str(row.get("record_id") or text_hash),
                "fair_slug": fair_slug,
                "text_hash": text_hash,
                "source_url": source_url,
                "status": "APPLIED",
                "headline_ja": headline_ja,
                "summary_ja": summary_ja,
                "headline_ja_chars": len(headline_ja),
                "summary_ja_chars": len(summary_ja),
                "warnings": warnings,
                "enrich_model": model,
                "enrich_mode": method,
                "enrich_completion_window": completion_window,
                "enrich_prompt_version": ENRICH_PROMPT_VERSION,
                "enrich_input_text_hash": text_hash,
                "enrich_notes": note,
            }
        )

    for fair_slug, raw_path in RAW_INPUT_PATHS.items():
        write_jsonl(raw_path, raw_rows_by_fair[fair_slug])

    raw_text_changed_count = 0
    headline_empty_total = 0
    summary_empty_total = 0
    for fair_slug, rows in raw_rows_by_fair.items():
        before = raw_text_before[fair_slug]
        after = [str(r.get("text") or "") for r in rows]
        raw_text_changed_count += sum(1 for b, a in zip(before, after) if b != a)
        headline_empty_total += sum(1 for r in rows if not str(r.get("headline_ja") or "").strip())
        summary_empty_total += sum(1 for r in rows if not str(r.get("summary_ja") or "").strip())

    apply_output_path = APPLY_OUTPUT_DIR / f"exhibitions_enrichment_apply_output_2025_{stamp}.jsonl"
    write_jsonl(apply_output_path, apply_rows)

    spot_checks: dict[str, Any] = {}
    for fair_slug in ("frieze_london", "liste"):
        hit = next((r for r in apply_rows if r.get("fair_slug") == fair_slug and r.get("status") == "APPLIED"), None)
        if hit:
            spot_checks[fair_slug] = {
                "record_id": hit.get("record_id"),
                "source_url": hit.get("source_url"),
                "headline_ja_chars": hit.get("headline_ja_chars"),
                "summary_ja_chars": hit.get("summary_ja_chars"),
            }

    summary = {
        "started_at": started_at,
        "completed_at": utc_now_iso(),
        "target_year": 2025,
        "requests_path": str(REQUESTS_OUTPUT_PATH),
        "apply_output_path": str(apply_output_path),
        "total_targeted": len(request_rows),
        "total_applied": counters["applied"],
        "skipped_already_filled": counters["skipped_already_filled"],
        "skipped_hash_match": counters["skipped_hash_match"],
        "error_count": counters["skipped_invalid_fair_slug"]
        + counters["skipped_missing_text_hash"]
        + counters["skipped_target_row_not_found"]
        + counters["skipped_empty_text"],
        "empty_after_apply_count": counters["headline_empty_after_apply"] + counters["summary_empty_after_apply"],
        "headline_empty_total": headline_empty_total,
        "summary_empty_total": summary_empty_total,
        "headline_over_50_count": counters["headline_over_limit"],
        "summary_over_500_count": counters["summary_over_limit"],
        "warning_count": warning_count,
        "raw_text_changed_count": raw_text_changed_count,
        "generated_openai": counters["generated_openai"],
        "generated_fallback": counters["generated_fallback"],
        "enrich_model": model,
        "enrich_use_openai_batch": use_batch,
        "enrich_completion_window": completion_window,
        "enrich_prompt_version": ENRICH_PROMPT_VERSION,
        "spot_checks": spot_checks,
    }
    summary_path = APPLY_SUMMARY_DIR / f"exhibitions_enrichment_apply_summary_2025_{stamp}.json"
    write_json(summary_path, summary)

    print(f"[START] exhibitions enrichment apply: {started_at}")
    print(f"[DONE] total_targeted={summary['total_targeted']} total_applied={summary['total_applied']}")
    print(
        "[DONE] "
        f"headline_empty_total={headline_empty_total} summary_empty_total={summary_empty_total} "
        f"headline_over_50={summary['headline_over_50_count']} summary_over_500={summary['summary_over_500_count']}"
    )
    print(f"[DONE] apply_output={apply_output_path}")
    print(f"[DONE] apply_summary={summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
