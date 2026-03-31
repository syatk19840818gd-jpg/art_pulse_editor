#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from enrichment_batch_common import extract_response_text_from_body, is_truthy_flag
from model_routing import (
    ENRICH_BATCH_COMPLETION_WINDOW_DEFAULT,
    ENRICH_USE_OPENAI_BATCH_DEFAULT,
    EXHIBITIONS_ENRICHMENT_BATCH_FIELDS,
    EXHIBITIONS_ENRICHMENT_FIELD_MODELS,
    GENERATION_MODEL,
    get_enrichment_model_fingerprint,
)
from phase2_art_pulse_config import (
    get_current_raw_paths,
    get_enrichment_preview_dir,
    get_enrichment_runtime_requests_path,
)

TARGET_YEAR = 2025
RAG_CATEGORY = "exhibitions_text"

RAW_INPUT_PATHS = get_current_raw_paths("exhibitions", TARGET_YEAR)
REQUESTS_OUTPUT_PATH = get_enrichment_runtime_requests_path("exhibitions", TARGET_YEAR)
PREVIEW_OUTPUT_DIR = get_enrichment_preview_dir("exhibitions")

# Kept for compatibility with imports from apply scripts.
ENRICH_TEXT_MODEL = GENERATION_MODEL
ENRICH_USE_OPENAI_BATCH = ENRICH_USE_OPENAI_BATCH_DEFAULT
ENRICH_BATCH_COMPLETION_WINDOW = ENRICH_BATCH_COMPLETION_WINDOW_DEFAULT
ENRICH_PROMPT_VERSION = "exh_preview_v1"

HEADLINE_MAX_CHARS = 50
SUMMARY_MAX_CHARS = 500
MAX_TEXT_CHARS_FOR_PROMPT = 7000
SAMPLE_PREVIEW_MAX = 3


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def utc_now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
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


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def append_unique(items: list[str], item: str) -> None:
    if item and item not in items:
        items.append(item)


def strip_cookie_noise(text: str) -> str:
    if not text:
        return ""
    patterns = [
        r"Manage cookies.*$",
        r"Cookie preferences.*$",
        r"Join our mailing list.*$",
        r"COPYRIGHT.*$",
    ]
    output = text
    for pat in patterns:
        output = re.sub(pat, "", output, flags=re.IGNORECASE | re.DOTALL)
    return normalize_whitespace(output)


def derive_exhibition_title(row: dict[str, Any], text: str) -> str:
    title = str(row.get("exhibition_title") or "").strip()
    if title:
        return title
    first_line = ""
    for line in text.splitlines():
        line = line.strip()
        if line:
            first_line = line
            break
    if first_line:
        first_line = re.sub(r"\s*\|\s*\d{1,2}\s+.*$", "", first_line)
        return first_line.strip()
    source_url = str(row.get("source_url") or "").strip()
    return source_url.rsplit("/", 1)[-1] if source_url else "Untitled Exhibition"


def build_requests() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    counters: dict[str, int] = defaultdict(int)
    raw_records_by_fair: dict[str, int] = {}
    candidates_by_hash: dict[str, dict[str, Any]] = {}

    for fair_slug, raw_path in RAW_INPUT_PATHS.items():
        if not raw_path.exists():
            raise FileNotFoundError(f"Missing raw input for {fair_slug}: {raw_path}")

        rows = read_jsonl(raw_path)
        raw_records_by_fair[fair_slug] = len(rows)

        for row in rows:
            text_hash = str(row.get("text_hash") or "").strip()
            text = str(row.get("text") or "").strip()
            source_url = str(row.get("source_url") or "").strip()
            headline_ja = str(row.get("headline_ja") or "").strip()
            summary_ja = str(row.get("summary_ja") or "").strip()

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
                exhibition_title = derive_exhibition_title(row, text)
                candidates_by_hash[text_hash] = {
                    "request_id": f"seed10_exhibitions_enrich_{text_hash}",
                    "record_id": str(row.get("record_id") or text_hash),
                    "text_hash": text_hash,
                    "fair_slug": fair_slug,
                    "gallery_name": str(row.get("gallery_name_en") or "").strip(),
                    "exhibition_title": exhibition_title,
                    "source_url": source_url,
                    "source_urls": [source_url] if source_url else [],
                    "participating_artists": str(row.get("participating_artists") or "").strip(),
                    "target_year": int(row.get("target_year") or TARGET_YEAR),
                    "rag_category": str(row.get("rag_category") or RAG_CATEGORY),
                    "needs_fields": list(needs_fields),
                    "text": text,
                    "text_length": len(text),
                }
                counters["candidates_new"] += 1
            else:
                counters["candidates_merged_by_text_hash"] += 1
                append_unique(existing["source_urls"], source_url)
                for field_name in needs_fields:
                    append_unique(existing["needs_fields"], field_name)

    request_rows = [
        candidates_by_hash[key]
        for key in sorted(candidates_by_hash.keys(), key=lambda k: (candidates_by_hash[k]["fair_slug"], k))
    ]

    summary = {
        "generated_at": utc_now_iso(),
        "target_year": TARGET_YEAR,
        "raw_records_by_fair": raw_records_by_fair,
        "raw_records_total": sum(raw_records_by_fair.values()),
        "requests_total": len(request_rows),
        "counters": dict(counters),
        "requests_output_path": str(REQUESTS_OUTPUT_PATH),
    }
    return request_rows, summary


def select_preview_samples(request_rows: list[dict[str, Any]], max_samples: int = SAMPLE_PREVIEW_MAX) -> list[dict[str, Any]]:
    if not request_rows:
        return []

    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()

    def pick_one(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not rows:
            return None
        rows_sorted = sorted(rows, key=lambda x: int(x.get("text_length") or 0), reverse=True)
        return rows_sorted[0]

    for fair_slug in ("frieze_london", "liste"):
        fair_rows = [r for r in request_rows if str(r.get("fair_slug")) == fair_slug]
        chosen = pick_one(fair_rows)
        if chosen and chosen["request_id"] not in selected_ids:
            selected.append(chosen)
            selected_ids.add(chosen["request_id"])
            if len(selected) >= max_samples:
                return selected

    remaining = [r for r in request_rows if r["request_id"] not in selected_ids]
    if remaining and len(selected) < max_samples:
        remaining_sorted = sorted(remaining, key=lambda x: int(x.get("text_length") or 0))
        mid = len(remaining_sorted) // 2
        selected.append(remaining_sorted[mid])

    return selected[:max_samples]


def sanitize_headline(headline: str) -> str:
    text = normalize_whitespace(headline)
    text = re.sub(r"^[\s\"'「『]+", "", text)
    text = re.sub(r"[\s\"'」』]+$", "", text)
    if len(text) > HEADLINE_MAX_CHARS:
        text = text[:HEADLINE_MAX_CHARS].rstrip()
    return text


def sanitize_summary(summary: str) -> str:
    text = strip_cookie_noise(summary)
    text = re.sub(r"\.{3,}", "。", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > SUMMARY_MAX_CHARS:
        text = text[:SUMMARY_MAX_CHARS].rstrip(" 、,.;") + "。"
    return text


def extract_json_object(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    text = text.strip()
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None
    try:
        obj = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def build_openai_request_body(model: str, row: dict[str, Any]) -> dict[str, Any]:
    prompt_text = str(row.get("text") or "")[:MAX_TEXT_CHARS_FOR_PROMPT]
    return {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "You are generating enrichment JSON for exhibitions."
                            "Return JSON only."
                            "headline_ja must be concise Japanese under 50 chars."
                            "summary_ja must be Japanese under 500 chars."
                        ),
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            f"fair_slug: {row.get('fair_slug','')}\n"
                            f"gallery_name: {row.get('gallery_name','')}\n"
                            f"exhibition_title: {row.get('exhibition_title','')}\n"
                            f"source_url: {row.get('source_url','')}\n"
                            f"participating_artists: {row.get('participating_artists','')}\n"
                            f"text:\n{prompt_text}\n\n"
                            "Return JSON: {\"headline_ja\":\"...\",\"summary_ja\":\"...\"}"
                        ),
                    }
                ],
            },
        ],
    }


def parse_openai_response_body(body: dict[str, Any]) -> tuple[str, str]:
    obj = extract_json_object(extract_response_text_from_body(body))
    if obj is None:
        raise RuntimeError("openai_output_not_json")

    headline = sanitize_headline(str(obj.get("headline_ja") or ""))
    summary = sanitize_summary(str(obj.get("summary_ja") or ""))
    if not headline:
        raise RuntimeError("empty_headline")
    if not summary:
        raise RuntimeError("empty_summary")
    return headline, summary


def parse_artist_tokens(participating_artists: str) -> list[str]:
    text = participating_artists.strip()
    if not text:
        return []
    text = re.sub(r"^Participating Artists:\s*", "", text, flags=re.IGNORECASE)
    raw = [normalize_whitespace(x) for x in text.split(",")]
    return [x for x in raw if x]


def build_warnings(*, summary_ja: str, row: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    summary = summary_ja or ""

    exhibition_title = str(row.get("exhibition_title") or "").strip()
    gallery_name = str(row.get("gallery_name") or "").strip()
    participating_artists = str(row.get("participating_artists") or "").strip()

    if exhibition_title and exhibition_title in summary:
        warnings.append("title_repeat")
    if gallery_name and gallery_name in summary:
        warnings.append("gallery_repeat")

    for artist in parse_artist_tokens(participating_artists)[:4]:
        if artist and artist in summary:
            warnings.append(f"artist_repeat:{artist}")
            break

    if re.search(r"\b(19|20)\d{2}\b", summary):
        warnings.append("date_repeat_possible")
    if re.search(r"https?://", summary):
        warnings.append("url_repeat")

    return warnings


def _build_raw_row_index() -> dict[tuple[str, str, str], dict[str, Any]]:
    index: dict[tuple[str, str, str], dict[str, Any]] = {}
    for fair_slug, raw_path in RAW_INPUT_PATHS.items():
        for row in read_jsonl(raw_path):
            text_hash = str(row.get("text_hash") or "").strip()
            source_url = str(row.get("source_url") or "").strip()
            if not text_hash:
                continue
            index[(fair_slug, text_hash, source_url)] = row
            if (fair_slug, text_hash, "") not in index:
                index[(fair_slug, text_hash, "")] = row
    return index


def _resolve_batch_preview_values(
    *,
    request_row: dict[str, Any],
    raw_row_index: dict[tuple[str, str, str], dict[str, Any]],
) -> tuple[str, str, dict[str, Any]]:
    fair_slug = str(request_row.get("fair_slug") or "").strip()
    text_hash = str(request_row.get("text_hash") or "").strip()
    source_url = str(request_row.get("source_url") or "").strip()
    raw_row = raw_row_index.get((fair_slug, text_hash, source_url)) or raw_row_index.get((fair_slug, text_hash, ""))
    if raw_row is None:
        raise RuntimeError(f"preview_source_row_not_found:{fair_slug}:{text_hash}")

    enrich_mode = str(raw_row.get("enrich_mode") or "").strip()
    if enrich_mode != "openai_batch_apply":
        raise RuntimeError(f"preview_batch_enforcement_violation:enrich_mode={enrich_mode or 'missing'}")

    headline = sanitize_headline(str(raw_row.get("headline_ja") or ""))
    summary = sanitize_summary(str(raw_row.get("summary_ja") or ""))
    if not headline or not summary:
        raise RuntimeError("preview_batch_enforcement_violation:missing_batch_outputs")
    return headline, summary, raw_row


def make_preview_rows(sample_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    use_batch = os.getenv("ENRICH_USE_OPENAI_BATCH", ENRICH_USE_OPENAI_BATCH).strip() or ENRICH_USE_OPENAI_BATCH
    if not is_truthy_flag(use_batch):
        raise RuntimeError("preview_batch_enforcement_violation:batch_flag_disabled")

    raw_row_index = _build_raw_row_index()
    model_fingerprint = get_enrichment_model_fingerprint("exhibitions")
    stats = {"batch_snapshot_ok": 0, "warnings": 0}
    preview_rows: list[dict[str, Any]] = []

    for row in sample_rows:
        headline_ja, summary_ja, raw_row = _resolve_batch_preview_values(
            request_row=row,
            raw_row_index=raw_row_index,
        )
        warnings = build_warnings(summary_ja=summary_ja, row=row)
        stats["warnings"] += len(warnings)
        stats["batch_snapshot_ok"] += 1

        preview_rows.append(
            {
                "request_id": row.get("request_id"),
                "record_id": row.get("record_id") or row.get("text_hash"),
                "fair_slug": row.get("fair_slug"),
                "exhibition_title": row.get("exhibition_title"),
                "gallery_name": row.get("gallery_name"),
                "source_url": row.get("source_url"),
                "text_excerpt": normalize_whitespace(str(row.get("text") or ""))[:320],
                "headline_ja": headline_ja,
                "summary_ja": summary_ja,
                "headline_ja_chars": len(headline_ja),
                "summary_ja_chars": len(summary_ja),
                "warnings": warnings,
                "enrich_status": "preview_generated_from_batch_output",
                "enrich_model": model_fingerprint,
                "enrich_models_by_field": dict(EXHIBITIONS_ENRICHMENT_FIELD_MODELS),
                "enrich_mode": "openai_batch_apply",
                "api_mode": "openai_batch_apply_snapshot",
                "execution_mode": "sample_preview_batch_snapshot",
                "batch_required": True,
                "batch_used": True,
                "enrich_use_openai_batch": use_batch,
                "enrich_completion_window": str(raw_row.get("enrich_completion_window") or ENRICH_BATCH_COMPLETION_WINDOW),
                "enrich_prompt_version": str(raw_row.get("enrich_prompt_version") or ENRICH_PROMPT_VERSION),
                "enrich_input_text_hash": row.get("text_hash"),
                "enrich_input_chars": int(row.get("text_length") or 0),
                "enrich_summary_chars": len(summary_ja),
                "enrich_headline_chars": len(headline_ja),
                "enrich_generated_at": utc_now_iso(),
                "enrich_notes": "",
                "enrich_generation_method": "batch_snapshot",
            }
        )

    return preview_rows, stats


def main() -> int:
    started_at = utc_now_iso()

    request_rows, request_summary = build_requests()
    write_jsonl(REQUESTS_OUTPUT_PATH, request_rows)

    sample_rows = select_preview_samples(request_rows, max_samples=SAMPLE_PREVIEW_MAX)
    preview_rows, preview_stats = make_preview_rows(sample_rows)

    stamp = utc_now_compact()
    preview_path = PREVIEW_OUTPUT_DIR / f"exhibitions_enrichment_preview_2025_{stamp}.jsonl"
    write_jsonl(preview_path, preview_rows)

    print(f"[START] exhibitions enrichment preview: {started_at}")
    print(f"[DONE] requests={REQUESTS_OUTPUT_PATH} total={len(request_rows)}")
    print(f"[DONE] preview={preview_path} samples={len(preview_rows)}")
    print(
        "[DONE] preview_stats="
        f"batch_snapshot_ok={preview_stats['batch_snapshot_ok']} warnings={preview_stats['warnings']}"
    )
    print(
        "[DONE] request_counters="
        f"raw_total={request_summary['raw_records_total']} candidates={request_summary['requests_total']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
