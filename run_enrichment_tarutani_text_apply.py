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

REQUESTS_PATH = Path("data/Tarutani_data/enrichment/enrichment_requests_tarutani_text.jsonl")
TARGET_JSONL_PATH = Path("data/Tarutani_data/tarutani_text.jsonl")
OUTPUT_DIR = Path("data/Tarutani_data/enrichment")

HEADLINE_MAX_CHARS = 50
MAX_TEXT_CHARS_FOR_PROMPT = 6000


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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def sanitize_short_headline(text: str) -> str:
    text = normalize_whitespace(text)
    text = text.strip("[]")
    # series prefix like "1_Grains / ..." should be removed from generated short text.
    text = re.sub(r"^[^/]{1,40}/\s*", "", text)
    if len(text) > HEADLINE_MAX_CHARS:
        text = text[:HEADLINE_MAX_CHARS].rstrip()
    return text


def generate_short_headline(client: OpenAI, model: str, series_name: str, text: str) -> str:
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
                            "あなたは日本語の短い見出し作成アシスタントです。"
                            "本文の要約置換はせず、検索しやすい短い見出しのみ返してください。"
                            f"文字数は {HEADLINE_MAX_CHARS} 字以内。"
                            "出力は見出し本文のみ（括弧・シリーズ名・説明文は不要）。"
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
                            "次の本文から、短い日本語見出しを1つ作成してください。\n"
                            f"シリーズ名: {series_name}\n"
                            f"本文:\n{prompt_text}"
                        ),
                    }
                ],
            },
        ],
    )

    output_text = normalize_whitespace(getattr(response, "output_text", "") or "")
    if not output_text:
        raise RuntimeError("empty_output_text")

    short = sanitize_short_headline(output_text)
    if not short:
        raise RuntimeError("empty_short_headline_after_sanitize")

    return short


def main() -> int:
    started_at = utc_now_iso()
    print(f"[START] Tarutani_Text enrichment apply at {started_at}")

    if not REQUESTS_PATH.exists():
        raise FileNotFoundError(f"Missing requests jsonl: {REQUESTS_PATH}")
    if not TARGET_JSONL_PATH.exists():
        raise FileNotFoundError(f"Missing target jsonl: {TARGET_JSONL_PATH}")

    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing")
    model = os.getenv("ENRICH_TEXT_MODEL", "gpt-5-mini")
    client = OpenAI(api_key=api_key)

    request_rows = read_jsonl(REQUESTS_PATH)
    target_rows = read_jsonl(TARGET_JSONL_PATH)
    source_index = {
        str(row.get("source_path", "")).strip(): idx
        for idx, row in enumerate(target_rows)
        if str(row.get("source_path", "")).strip()
    }

    counters: defaultdict[str, int] = defaultdict(int)
    output_rows: list[dict[str, Any]] = []

    for request in request_rows:
        request_id = str(request.get("request_id", "")).strip()
        source_path = str(request.get("source_path", "")).strip()
        series_name = str(request.get("series_name", "")).strip() or "UNKNOWN_SERIES"
        text = str(request.get("text", "")).strip()
        text_hash = str(request.get("text_hash", "")).strip()

        if not source_path:
            counters["skipped_missing_source_path"] += 1
            output_rows.append(
                {
                    "request_id": request_id,
                    "source_path": source_path,
                    "status": "SKIPPED_MISSING_SOURCE_PATH",
                }
            )
            continue

        target_idx = source_index.get(source_path)
        if target_idx is None:
            counters["skipped_missing_target_row"] += 1
            output_rows.append(
                {
                    "request_id": request_id,
                    "source_path": source_path,
                    "status": "SKIPPED_MISSING_TARGET_ROW",
                }
            )
            continue

        target_row = target_rows[target_idx]
        target_text = str(target_row.get("text", "")).strip()
        existing_headline = str(target_row.get("headline_ja", "")).strip()

        if existing_headline:
            counters["skipped_already_has_headline_ja"] += 1
            output_rows.append(
                {
                    "request_id": request_id,
                    "source_path": source_path,
                    "status": "SKIPPED_ALREADY_HAS_HEADLINE",
                    "headline_ja": existing_headline,
                }
            )
            continue

        if not text or not target_text:
            counters["skipped_empty_text"] += 1
            output_rows.append(
                {
                    "request_id": request_id,
                    "source_path": source_path,
                    "status": "SKIPPED_EMPTY_TEXT",
                }
            )
            continue

        if not text_hash:
            counters["skipped_missing_text_hash"] += 1
            output_rows.append(
                {
                    "request_id": request_id,
                    "source_path": source_path,
                    "status": "SKIPPED_MISSING_TEXT_HASH",
                }
            )
            continue

        try:
            short_headline = generate_short_headline(
                client=client,
                model=model,
                series_name=series_name,
                text=target_text,
            )
            final_headline = f"[{series_name} / {short_headline}]"

            target_row["headline_ja"] = final_headline
            counters["updated_records"] += 1
            output_rows.append(
                {
                    "request_id": request_id,
                    "source_path": source_path,
                    "text_hash": text_hash,
                    "series_name": series_name,
                    "model": model,
                    "status": "UPDATED",
                    "headline_ja": final_headline,
                }
            )
            print(f"[UPDATED] {source_path} -> {final_headline}")
        except Exception as exc:  # noqa: BLE001
            counters["failed_generation"] += 1
            output_rows.append(
                {
                    "request_id": request_id,
                    "source_path": source_path,
                    "text_hash": text_hash,
                    "series_name": series_name,
                    "model": model,
                    "status": "FAILED_GENERATION",
                    "error": str(exc),
                }
            )
            print(f"[FAILED] {source_path} error={exc}")

    write_jsonl(TARGET_JSONL_PATH, target_rows)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = OUTPUT_DIR / f"enrichment_output_tarutani_text_{timestamp}.jsonl"
    summary_path = OUTPUT_DIR / f"enrichment_apply_summary_tarutani_text_{timestamp}.json"
    write_jsonl(output_path, output_rows)

    completed_at = utc_now_iso()
    summary = {
        "started_at": started_at,
        "completed_at": completed_at,
        "requests_path": str(REQUESTS_PATH),
        "target_jsonl_path": str(TARGET_JSONL_PATH),
        "model": model,
        "request_rows_total": len(request_rows),
        "target_rows_total": len(target_rows),
        "updated_records": int(counters.get("updated_records", 0)),
        "failed_generation": int(counters.get("failed_generation", 0)),
        "skipped_records_total": sum(v for k, v in counters.items() if k.startswith("skipped_")),
        "counters": dict(counters),
        "output_jsonl_path": str(output_path),
    }
    write_json(summary_path, summary)

    print(
        f"[DONE] Tarutani_Text enrichment apply complete. "
        f"updated={summary['updated_records']} "
        f"failed={summary['failed_generation']}"
    )
    print(f"[DONE] output={output_path}")
    print(f"[DONE] summary={summary_path}")
    auto_sync_result = auto_sync_after_job(
        target="tarutani_all",
        trigger="run_enrichment_tarutani_text_apply.py",
    )
    print(format_auto_sync_brief(auto_sync_result))

    return 0 if summary["failed_generation"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
