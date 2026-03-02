#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI
from r2_auto_sync import auto_sync_after_job, format_auto_sync_brief

TARGET_YEAR = 2025
RAG_CATEGORY = "exhibitions_text"

REQUESTS_PATH = Path("data/phase1_seed10/enrichment/enrichment_requests_seed10_2025.jsonl")
RAW_INPUT_PATHS = {
    "frieze_london": Path("data/phase1_seed10/raw/exhibitions_frieze_london_2025.jsonl"),
    "liste": Path("data/phase1_seed10/raw/exhibitions_liste_2025.jsonl"),
}
OUTPUT_DIR = Path("data/phase1_seed10/enrichment")
MAX_TEXT_CHARS_FOR_PROMPT = 7000
HEADLINE_MAX_CHARS = 56
SUMMARY_MAX_CHARS = 220
DEFAULT_ALLOW_HEURISTIC_FALLBACK = True


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def utc_timestamp_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


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


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sanitize_headline(text: str) -> str:
    cleaned = normalize_whitespace(text).strip("[]")
    cleaned = re.sub(r"^[\"'「『]+", "", cleaned)
    cleaned = re.sub(r"[\"'」』]+$", "", cleaned)
    if len(cleaned) > HEADLINE_MAX_CHARS:
        cleaned = cleaned[:HEADLINE_MAX_CHARS].rstrip()
    return cleaned


def sanitize_summary(text: str) -> str:
    cleaned = normalize_whitespace(text).strip("[]")
    cleaned = re.sub(r"^[\"'「『]+", "", cleaned)
    cleaned = re.sub(r"[\"'」』]+$", "", cleaned)
    if len(cleaned) > SUMMARY_MAX_CHARS:
        cleaned = cleaned[:SUMMARY_MAX_CHARS].rstrip()
    return cleaned


def generate_heuristic_headline(*, gallery_name_en: str, source_url: str, text: str) -> str:
    lines = [normalize_whitespace(line) for line in str(text or "").splitlines()]
    lines = [line for line in lines if line]
    for line in lines[:30]:
        lowered = line.lower()
        if len(line) < 6:
            continue
        if any(token in lowered for token in ("cookie", "privacy", "newsletter", "copyright")):
            continue
        return sanitize_headline(line) or sanitize_headline(gallery_name_en) or "展示情報"
    return sanitize_headline(gallery_name_en or source_url or "展示情報")


def generate_heuristic_summary(*, text: str) -> str:
    lines = [normalize_whitespace(line) for line in str(text or "").splitlines()]
    lines = [line for line in lines if line]
    if not lines:
        return "展示情報の要約を生成できませんでした。"
    summary = " ".join(lines[:5])
    return sanitize_summary(summary) or "展示情報の要約を生成できませんでした。"


def parse_fields_from_model_output(output_text: str) -> tuple[str, str]:
    text = normalize_whitespace(output_text)
    if not text:
        raise RuntimeError("empty_model_output")
    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            headline = sanitize_headline(str(payload.get("headline_ja") or ""))
            summary = sanitize_summary(str(payload.get("summary_ja") or ""))
            if headline and summary:
                return headline, summary
    except json.JSONDecodeError:
        pass
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) >= 2:
        headline = sanitize_headline(lines[0])
        summary = sanitize_summary(" ".join(lines[1:]))
        if headline and summary:
            return headline, summary
    raise RuntimeError("invalid_model_output")


def generate_exhibition_fields(
    client: OpenAI,
    model: str,
    *,
    gallery_name_en: str,
    fair_slug: str,
    source_url: str,
    text: str,
) -> tuple[str, str]:
    prompt_text = text[:MAX_TEXT_CHARS_FOR_PROMPT]
    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "あなたは展示情報RAGの整形担当です。"
                            "必ずJSONのみを返し、キーは headline_ja と summary_ja。"
                            f"headline_jaは{HEADLINE_MAX_CHARS}文字以内、summary_jaは{SUMMARY_MAX_CHARS}文字以内。"
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
                            "次の情報から、展示向けの日本語見出しと要約を作成してください。\n"
                            f"gallery_name_en: {gallery_name_en}\n"
                            f"fair_slug: {fair_slug}\n"
                            f"source_url: {source_url}\n"
                            f"text:\n{prompt_text}"
                        ),
                    }
                ],
            },
        ],
    )
    return parse_fields_from_model_output(getattr(response, "output_text", "") or "")


def build_target_index(raw_rows_by_fair: dict[str, list[dict[str, Any]]]) -> dict[tuple[str, str], list[int]]:
    index: dict[tuple[str, str], list[int]] = defaultdict(list)
    for fair_slug, rows in raw_rows_by_fair.items():
        for idx, row in enumerate(rows):
            text_hash = str(row.get("text_hash") or "").strip()
            if not text_hash:
                continue
            index[(fair_slug, text_hash)].append(idx)
    return index


def select_target_row_index(rows: list[dict[str, Any]], indexes: list[int], source_urls: list[str]) -> int | None:
    if not indexes:
        return None
    if not source_urls:
        return indexes[0]
    source_set = {str(x or "").strip() for x in source_urls if str(x or "").strip()}
    if not source_set:
        return indexes[0]
    for idx in indexes:
        row_source_url = str(rows[idx].get("source_url") or "").strip()
        if row_source_url in source_set:
            return idx
        row_sources = rows[idx].get("sources")
        if isinstance(row_sources, list) and any(str(x or "").strip() in source_set for x in row_sources):
            return idx
    return indexes[0]


def main() -> int:
    started_at = utc_now_iso()
    print(f"[START] exhibitions enrichment apply at {started_at}")

    if not REQUESTS_PATH.exists():
        raise FileNotFoundError(f"Missing requests jsonl: {REQUESTS_PATH}")
    for fair_slug, path in RAW_INPUT_PATHS.items():
        if not path.exists():
            raise FileNotFoundError(f"Missing exhibitions raw input for {fair_slug}: {path}")

    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("ENRICH_TEXT_MODEL", "gpt-5-mini")
    allow_fallback_raw = os.getenv("ENRICH_EXHIBITIONS_ALLOW_HEURISTIC_FALLBACK", "")
    if allow_fallback_raw.strip():
        allow_fallback = allow_fallback_raw.strip().lower() in {"1", "true", "yes", "on"}
    else:
        allow_fallback = DEFAULT_ALLOW_HEURISTIC_FALLBACK

    client: OpenAI | None = None
    if api_key:
        client = OpenAI(api_key=api_key)
    elif not allow_fallback:
        raise RuntimeError("OPENAI_API_KEY is missing")

    request_rows = read_jsonl(REQUESTS_PATH)
    raw_rows_by_fair = {fair_slug: read_jsonl(path) for fair_slug, path in RAW_INPUT_PATHS.items()}
    target_index = build_target_index(raw_rows_by_fair)

    counters: defaultdict[str, int] = defaultdict(int)
    output_rows: list[dict[str, Any]] = []

    for request in request_rows:
        request_id = str(request.get("request_id") or "").strip()
        fair_slug = str(request.get("fair_slug") or "").strip()
        text_hash = str(request.get("text_hash") or "").strip()
        rag_category = str(request.get("rag_category") or "").strip()
        source_urls_raw = request.get("source_urls")
        source_urls: list[str] = []
        if isinstance(source_urls_raw, list):
            source_urls = [str(x).strip() for x in source_urls_raw if str(x).strip()]
        gallery_name_en = str(request.get("gallery_name_en") or "").strip()

        if rag_category and rag_category != RAG_CATEGORY:
            counters["skipped_non_exhibitions_category"] += 1
            output_rows.append(
                {
                    "request_id": request_id,
                    "fair_slug": fair_slug,
                    "text_hash": text_hash,
                    "status": "SKIPPED_NON_EXHIBITIONS_CATEGORY",
                    "rag_category": rag_category,
                }
            )
            continue
        if not fair_slug or fair_slug not in raw_rows_by_fair:
            counters["skipped_invalid_fair_slug"] += 1
            output_rows.append(
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
            output_rows.append(
                {
                    "request_id": request_id,
                    "fair_slug": fair_slug,
                    "status": "SKIPPED_MISSING_TEXT_HASH",
                }
            )
            continue

        rows = raw_rows_by_fair[fair_slug]
        indexes = target_index.get((fair_slug, text_hash), [])
        target_idx = select_target_row_index(rows, indexes, source_urls)
        if target_idx is None:
            counters["skipped_missing_target_row"] += 1
            output_rows.append(
                {
                    "request_id": request_id,
                    "fair_slug": fair_slug,
                    "text_hash": text_hash,
                    "status": "SKIPPED_MISSING_TARGET_ROW",
                }
            )
            continue

        target_row = rows[target_idx]
        existing_headline = str(target_row.get("headline_ja") or "").strip()
        existing_summary = str(target_row.get("summary_ja") or "").strip()
        if existing_headline and existing_summary:
            counters["skipped_already_enriched"] += 1
            output_rows.append(
                {
                    "request_id": request_id,
                    "fair_slug": fair_slug,
                    "text_hash": text_hash,
                    "status": "SKIPPED_ALREADY_ENRICHED",
                    "headline_ja": existing_headline,
                }
            )
            continue

        source_url = str(target_row.get("source_url") or "").strip()
        target_text = str(target_row.get("text") or "").strip()
        if not target_text:
            counters["skipped_empty_text"] += 1
            output_rows.append(
                {
                    "request_id": request_id,
                    "fair_slug": fair_slug,
                    "text_hash": text_hash,
                    "status": "SKIPPED_EMPTY_TEXT",
                }
            )
            continue

        used_fallback = False
        fallback_reason = ""
        try:
            if client is None:
                if not allow_fallback:
                    raise RuntimeError("openai_client_unavailable")
                used_fallback = True
                fallback_reason = "openai_client_unavailable"
                headline = generate_heuristic_headline(
                    gallery_name_en=gallery_name_en,
                    source_url=source_url,
                    text=target_text,
                )
                summary = generate_heuristic_summary(text=target_text)
            else:
                try:
                    headline, summary = generate_exhibition_fields(
                        client=client,
                        model=model,
                        gallery_name_en=gallery_name_en,
                        fair_slug=fair_slug,
                        source_url=source_url,
                        text=target_text,
                    )
                except Exception as exc:
                    if not allow_fallback:
                        raise
                    used_fallback = True
                    fallback_reason = str(exc)
                    headline = generate_heuristic_headline(
                        gallery_name_en=gallery_name_en,
                        source_url=source_url,
                        text=target_text,
                    )
                    summary = generate_heuristic_summary(text=target_text)

            target_row["headline_ja"] = headline
            target_row["summary_ja"] = summary
            counters["updated_records"] += 1
            if used_fallback:
                counters["updated_with_fallback"] += 1
            output_rows.append(
                {
                    "request_id": request_id,
                    "fair_slug": fair_slug,
                    "text_hash": text_hash,
                    "source_url": source_url,
                    "model": model,
                    "status": "UPDATED_FALLBACK" if used_fallback else "UPDATED",
                    "headline_ja": headline,
                    "summary_ja": summary,
                    "fallback_reason": fallback_reason,
                }
            )
        except Exception as exc:  # noqa: BLE001
            counters["failed_generation"] += 1
            output_rows.append(
                {
                    "request_id": request_id,
                    "fair_slug": fair_slug,
                    "text_hash": text_hash,
                    "source_url": source_url,
                    "model": model,
                    "status": "FAILED_GENERATION",
                    "error": str(exc),
                }
            )

    for fair_slug, output_path in RAW_INPUT_PATHS.items():
        write_jsonl(output_path, raw_rows_by_fair[fair_slug])

    timestamp = utc_timestamp_compact()
    output_path = OUTPUT_DIR / f"enrichment_apply_output_seed10_{TARGET_YEAR}_{timestamp}.jsonl"
    summary_path = OUTPUT_DIR / f"enrichment_apply_summary_seed10_{TARGET_YEAR}_{timestamp}.json"
    write_jsonl(output_path, output_rows)

    completed_at = utc_now_iso()
    summary = {
        "started_at": started_at,
        "completed_at": completed_at,
        "target_year": TARGET_YEAR,
        "rag_category": RAG_CATEGORY,
        "requests_path": str(REQUESTS_PATH),
        "raw_input_paths": {k: str(v) for k, v in RAW_INPUT_PATHS.items()},
        "requests_total": len(request_rows),
        "updated_records": counters.get("updated_records", 0),
        "counters": dict(counters),
        "output_jsonl_path": str(output_path),
        "summary_path": str(summary_path),
        "model": model,
        "allow_heuristic_fallback": allow_fallback,
        "openai_client_available": client is not None,
    }
    write_json(summary_path, summary)

    print(
        "[DONE] exhibitions enrichment apply complete. "
        f"updated={summary['updated_records']} requests_total={summary['requests_total']}"
    )
    print(f"[DONE] output={output_path}")
    print(f"[DONE] summary={summary_path}")
    auto_sync_result = auto_sync_after_job(
        target="phase1_derived",
        trigger="run_enrichment_seed10_apply.py",
    )
    print(format_auto_sync_brief(auto_sync_result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
