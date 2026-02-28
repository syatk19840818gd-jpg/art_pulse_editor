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
RAG_CATEGORY = "artists_text"

REQUESTS_PATH = Path("data/phase1_seed10/derived/artists_enrichment_requests_2025.jsonl")
RAW_INPUT_PATHS = {
    "frieze_london": Path("data/phase1_seed10/raw/artists_frieze_london_2025.jsonl"),
    "liste": Path("data/phase1_seed10/raw/artists_liste_2025.jsonl"),
}
OUTPUT_DIR = Path("data/phase1_seed10/derived")

HEADLINE_MAX_CHARS = 56
MAX_TEXT_CHARS_FOR_PROMPT = 7000
DEFAULT_ALLOW_HEURISTIC_FALLBACK = True


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def utc_timestamp_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


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


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")


def sanitize_headline(text: str) -> str:
    cleaned = normalize_whitespace(text).strip("[]")
    cleaned = re.sub(r"^[\"'「『]+", "", cleaned)
    cleaned = re.sub(r"[\"'」』]+$", "", cleaned)
    if len(cleaned) > HEADLINE_MAX_CHARS:
        cleaned = cleaned[:HEADLINE_MAX_CHARS].rstrip()
    return cleaned


def generate_headline_fallback(*, gallery_name_en: str, source_url: str, text: str) -> str:
    lines = [normalize_whitespace(line) for line in text.splitlines()]
    lines = [line for line in lines if line]
    best = ""
    for line in lines[:25]:
        lowered = line.lower()
        if len(line) < 6:
            continue
        if any(token in lowered for token in ("cookie", "privacy", "manage cookies", "newsletter", "copyright")):
            continue
        best = line
        break
    if not best:
        best = gallery_name_en or source_url or "artists profile"
    best = re.sub(r"\s*\|\s*.*$", "", best).strip()
    best = re.sub(r"\s*[-:]\s*.*$", "", best).strip()
    return sanitize_headline(best) or sanitize_headline(gallery_name_en) or "artists profile"


def generate_artist_headline(
    client: OpenAI,
    model: str,
    *,
    gallery_name_en: str,
    fair_slug: str,
    source_url: str,
    text: str,
) -> str:
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
                            "あなたはアーティスト紹介文の見出し作成アシスタントです。"
                            "検索しやすい日本語の短い見出しだけを返してください。"
                            f"{HEADLINE_MAX_CHARS}文字以内、1行、括弧や説明文は不要です。"
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
                            "次の情報をもとに、artists_text の headline_ja を1つ作成してください。\n"
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
    output_text = normalize_whitespace(getattr(response, "output_text", "") or "")
    if not output_text:
        raise RuntimeError("empty_output_text")
    headline = sanitize_headline(output_text)
    if not headline:
        raise RuntimeError("empty_headline_after_sanitize")
    return headline


def build_target_index(raw_rows_by_fair: dict[str, list[dict[str, Any]]]) -> dict[tuple[str, str], list[int]]:
    index: dict[tuple[str, str], list[int]] = defaultdict(list)
    for fair_slug, rows in raw_rows_by_fair.items():
        for idx, row in enumerate(rows):
            text_hash = str(row.get("text_hash") or "").strip()
            if not text_hash:
                continue
            index[(fair_slug, text_hash)].append(idx)
    return index


def select_target_row_index(
    rows: list[dict[str, Any]],
    candidate_indexes: list[int],
    source_urls: list[str],
) -> int | None:
    if not candidate_indexes:
        return None
    if not source_urls:
        return candidate_indexes[0]
    source_url_set = {url for url in source_urls if url}
    if not source_url_set:
        return candidate_indexes[0]
    for idx in candidate_indexes:
        row_source_url = str(rows[idx].get("source_url") or "").strip()
        if row_source_url in source_url_set:
            return idx
    return candidate_indexes[0]


def main() -> int:
    started_at = utc_now_iso()
    print(f"[START] artists enrichment apply at {started_at}")

    if not REQUESTS_PATH.exists():
        raise FileNotFoundError(f"Missing requests jsonl: {REQUESTS_PATH}")
    for fair_slug, path in RAW_INPUT_PATHS.items():
        if not path.exists():
            raise FileNotFoundError(f"Missing artists raw input for {fair_slug}: {path}")

    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("ENRICH_TEXT_MODEL", "gpt-5-mini")
    allow_fallback_raw = os.getenv("ENRICH_ARTISTS_ALLOW_HEURISTIC_FALLBACK", "")
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
        text_hash = str(request.get("text_hash") or "").strip()
        fair_slug = str(request.get("fair_slug") or "").strip()
        rag_category = str(request.get("rag_category") or "").strip()
        text = str(request.get("text") or "").strip()
        source_urls_raw = request.get("source_urls")
        source_urls: list[str] = []
        if isinstance(source_urls_raw, list):
            source_urls = [str(x).strip() for x in source_urls_raw if str(x).strip()]
        gallery_name_en = str(request.get("gallery_name_en") or "").strip()

        if rag_category and rag_category != RAG_CATEGORY:
            counters["skipped_non_artists_category"] += 1
            output_rows.append(
                {
                    "request_id": request_id,
                    "fair_slug": fair_slug,
                    "text_hash": text_hash,
                    "status": "SKIPPED_NON_ARTISTS_CATEGORY",
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
        target_idx = select_target_row_index(rows=rows, candidate_indexes=indexes, source_urls=source_urls)
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
        if existing_headline:
            counters["skipped_already_has_headline_ja"] += 1
            output_rows.append(
                {
                    "request_id": request_id,
                    "fair_slug": fair_slug,
                    "text_hash": text_hash,
                    "status": "SKIPPED_ALREADY_HAS_HEADLINE",
                    "headline_ja": existing_headline,
                }
            )
            continue

        target_text = str(target_row.get("text") or "").strip()
        if not target_text or not text:
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

        source_url = str(target_row.get("source_url") or "").strip()
        used_fallback = False
        fallback_reason = ""
        try:
            if client is None:
                if not allow_fallback:
                    raise RuntimeError("OPENAI client unavailable and fallback disabled")
                used_fallback = True
                fallback_reason = "openai_client_unavailable"
                headline = generate_headline_fallback(
                    gallery_name_en=gallery_name_en,
                    source_url=source_url,
                    text=target_text,
                )
            else:
                try:
                    headline = generate_artist_headline(
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
                    headline = generate_headline_fallback(
                        gallery_name_en=gallery_name_en,
                        source_url=source_url,
                        text=target_text,
                    )
            target_row["headline_ja"] = headline
            counters["updated_records"] += 1
            status = "UPDATED_FALLBACK" if used_fallback else "UPDATED"
            if used_fallback:
                counters["updated_with_fallback"] += 1
            output_rows.append(
                {
                    "request_id": request_id,
                    "fair_slug": fair_slug,
                    "text_hash": text_hash,
                    "source_url": source_url,
                    "model": model,
                    "status": status,
                    "headline_ja": headline,
                    "fallback_reason": fallback_reason,
                }
            )
            if used_fallback:
                print(
                    f"[UPDATED][fallback] fair={fair_slug} text_hash={text_hash} "
                    f"headline={headline} reason={fallback_reason}"
                )
            else:
                print(f"[UPDATED] fair={fair_slug} text_hash={text_hash} headline={headline}")
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
            print(f"[FAILED] fair={fair_slug} text_hash={text_hash} error={exc}")

    for fair_slug, output_path in RAW_INPUT_PATHS.items():
        write_jsonl(output_path, raw_rows_by_fair[fair_slug])

    timestamp = utc_timestamp_compact()
    output_path = OUTPUT_DIR / f"artists_enrichment_apply_output_{TARGET_YEAR}_{timestamp}.jsonl"
    summary_path = OUTPUT_DIR / f"artists_enrichment_apply_summary_{TARGET_YEAR}_{timestamp}.json"
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
        "[DONE] artists enrichment apply complete. "
        f"updated={summary['updated_records']} "
        f"requests_total={summary['requests_total']}"
    )
    print(f"[DONE] output={output_path}")
    print(f"[DONE] summary={summary_path}")
    auto_sync_result = auto_sync_after_job(
        target="phase1_derived",
        trigger="run_enrichment_artists_seed10_apply.py",
    )
    print(format_auto_sync_brief(auto_sync_result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
