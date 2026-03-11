#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from dotenv import load_dotenv
from openai import OpenAI

from run_enrichment_artists_preview import (
    ARTIST_NAME_KANA_MAX_CHARS,
    ENRICH_BATCH_COMPLETION_WINDOW,
    ENRICH_PROMPT_VERSION,
    ENRICH_TEXT_MODEL,
    ENRICH_USE_OPENAI_BATCH,
    HEADLINE_MAX_CHARS,
    RAG_CATEGORY,
    SUMMARY_MAX_CHARS,
    build_warnings,
    generate_fallback_preview,
    generate_preview_with_openai,
    infer_artist_name_en,
    read_jsonl,
    utc_now_compact,
    utc_now_iso,
    write_jsonl,
)

TARGET_YEAR = 2025

REQUESTS_PATH = Path("data/phase1_seed10/derived/artists_enrichment_requests_2025.jsonl")
RAW_INPUT_PATHS = {
    "frieze_london": Path("data/phase1_seed10/raw/artists_frieze_london_2025.jsonl"),
    "liste": Path("data/phase1_seed10/raw/artists_liste_2025.jsonl"),
}
APPLY_OUTPUT_DIR = Path("data/phase1_seed10/derived")
APPLY_SUMMARY_DIR = Path("data/phase1_seed10/logs")
NON_ARTIST_UTILITY_TOKENS = {
    "privacy",
    "policy",
    "policies",
    "contact",
    "form",
    "terms",
    "condition",
    "conditions",
    "cookie",
    "cookies",
    "newsletter",
    "subscribe",
    "account",
    "login",
    "signin",
    "signup",
}


def safe_print(line: str) -> None:
    text = str(line)
    encoding = sys.stdout.encoding or "utf-8"
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode(encoding, errors="replace").decode(encoding, errors="replace"))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_row_index(rows: list[dict[str, Any]]) -> dict[tuple[str, str], int]:
    index: dict[tuple[str, str], int] = {}
    for i, row in enumerate(rows):
        text_hash = str(row.get("text_hash") or "").strip()
        source_url = str(row.get("source_url") or "").strip()
        if not text_hash:
            continue
        index[(text_hash, source_url)] = i
        if (text_hash, "") not in index:
            index[(text_hash, "")] = i
    return index


def is_non_artist_utility_url(url: str) -> bool:
    value = str(url or "").strip()
    if not value:
        return False
    try:
        parsed = urlparse(value)
    except Exception:
        return False
    path = str(parsed.path or "").strip().lower().strip("/")
    if not path:
        return False
    parts = [p for p in path.split("/") if p]
    if not parts:
        return False
    for part in parts:
        tokens = [t for t in part.replace(".", "-").replace("_", "-").split("-") if t]
        if any(token in NON_ARTIST_UTILITY_TOKENS for token in tokens):
            return True
    return False


def request_source_url(req: dict[str, Any], *, row_index: dict[tuple[str, str], int], text_hash: str) -> str:
    source_urls = req.get("source_urls")
    candidates: list[str] = []
    if isinstance(source_urls, list):
        for value in source_urls:
            url = str(value or "").strip()
            if url:
                candidates.append(url)
    fallback_url = str(req.get("source_url") or "").strip()
    if fallback_url:
        candidates.append(fallback_url)

    # Prefer URLs that exist in current raw and are not utility endpoints.
    for url in candidates:
        if is_non_artist_utility_url(url):
            continue
        if (text_hash, url) in row_index:
            return url
    for url in candidates:
        if (text_hash, url) in row_index:
            return url
    for url in candidates:
        if not is_non_artist_utility_url(url):
            return url
    return candidates[0] if candidates else ""


def load_requests() -> list[dict[str, Any]]:
    if not REQUESTS_PATH.exists():
        raise FileNotFoundError(f"Missing requests jsonl: {REQUESTS_PATH}")
    return read_jsonl(REQUESTS_PATH)


def main() -> int:
    started_at = utc_now_iso()
    stamp = utc_now_compact()
    safe_print(f"[START] artists enrichment apply: {started_at}")

    for fair_slug, raw_path in RAW_INPUT_PATHS.items():
        if not raw_path.exists():
            raise FileNotFoundError(f"Missing artists raw input for {fair_slug}: {raw_path}")

    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("ENRICH_TEXT_MODEL", ENRICH_TEXT_MODEL).strip() or ENRICH_TEXT_MODEL
    use_batch = os.getenv("ENRICH_USE_OPENAI_BATCH", ENRICH_USE_OPENAI_BATCH).strip() or ENRICH_USE_OPENAI_BATCH
    completion_window = (
        os.getenv("ENRICH_BATCH_COMPLETION_WINDOW", ENRICH_BATCH_COMPLETION_WINDOW).strip()
        or ENRICH_BATCH_COMPLETION_WINDOW
    )
    workers_raw = os.getenv("ENRICH_ARTISTS_APPLY_WORKERS", "8").strip() or "8"
    try:
        workers = max(1, min(16, int(workers_raw)))
    except ValueError:
        workers = 8

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
    pending_tasks: list[dict[str, Any]] = []

    for req in request_rows:
        request_id = str(req.get("request_id") or "").strip()
        fair_slug = str(req.get("fair_slug") or "").strip()
        text_hash = str(req.get("text_hash") or "").strip()
        rag_category = str(req.get("rag_category") or "").strip()

        if rag_category and rag_category != RAG_CATEGORY:
            counters["skipped_non_artists_category"] += 1
            apply_rows.append(
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

        row_index = row_index_by_fair[fair_slug]
        source_url = request_source_url(req, row_index=row_index, text_hash=text_hash)
        if source_url and is_non_artist_utility_url(source_url):
            counters["skipped_target_guard_non_artist_utility_url"] += 1
            apply_rows.append(
                {
                    "request_id": request_id,
                    "fair_slug": fair_slug,
                    "text_hash": text_hash,
                    "source_url": source_url,
                    "status": "SKIPPED_TARGET_GUARD_NON_ARTIST_UTILITY_URL",
                }
            )
            continue
        if (text_hash, source_url) not in row_index and (text_hash, "") not in row_index:
            counters["skipped_target_guard_missing_target"] += 1
            apply_rows.append(
                {
                    "request_id": request_id,
                    "fair_slug": fair_slug,
                    "text_hash": text_hash,
                    "source_url": source_url,
                    "status": "SKIPPED_TARGET_GUARD_MISSING_TARGET",
                }
            )
            continue

        rows = raw_rows_by_fair[fair_slug]
        idx = row_index.get((text_hash, source_url))
        if idx is None:
            idx = row_index.get((text_hash, ""))
        if idx is None:
            counters["skipped_target_guard_lookup_inconsistent"] += 1
            apply_rows.append(
                {
                    "request_id": request_id,
                    "fair_slug": fair_slug,
                    "text_hash": text_hash,
                    "source_url": source_url,
                    "status": "SKIPPED_TARGET_GUARD_LOOKUP_INCONSISTENT",
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
        current_kana = str(row.get("artist_name_kana") or "").strip()
        current_hash = str(row.get("enrich_input_text_hash") or "").strip()
        current_prompt = str(row.get("enrich_prompt_version") or "").strip()

        if (
            current_headline
            and current_summary
            and current_kana
            and current_hash == text_hash
            and current_prompt == ENRICH_PROMPT_VERSION
        ):
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
                    "artist_name_kana": current_kana,
                }
            )
            continue

        if current_headline and current_summary and current_kana:
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
                    "artist_name_kana": current_kana,
                }
            )
            continue

        pending_tasks.append(
            {
                "request": req,
                "request_id": request_id,
                "fair_slug": fair_slug,
                "text_hash": text_hash,
                "source_url": source_url,
                "row_index": idx,
                "text": text,
            }
        )

    def run_enrich_task(task: dict[str, Any]) -> dict[str, Any]:
        req = task["request"]
        working = deepcopy(req)
        working["text"] = task["text"]
        working["source_url"] = task["source_url"] or str(working.get("source_url") or "").strip()
        working["artist_name_kana"] = str(working.get("artist_name_kana") or "").strip()

        method = "fallback"
        note = "openai_key_missing"
        try:
            if not api_key:
                raise RuntimeError("openai_client_unavailable")
            client = OpenAI(api_key=api_key)
            headline_ja, summary_ja, artist_name_kana = generate_preview_with_openai(client, model, working)
            method = "openai_direct_apply"
            note = ""
        except Exception as exc:
            headline_ja, summary_ja, artist_name_kana = generate_fallback_preview(working)
            note = str(exc)

        artist_name_en = infer_artist_name_en(working)
        warnings = build_warnings(
            summary_ja=summary_ja,
            artist_name_en=artist_name_en,
            artist_name_kana=artist_name_kana,
        )
        return {
            "request_id": task["request_id"],
            "fair_slug": task["fair_slug"],
            "text_hash": task["text_hash"],
            "source_url": task["source_url"],
            "row_index": task["row_index"],
            "headline_ja": headline_ja,
            "summary_ja": summary_ja,
            "artist_name_kana": artist_name_kana,
            "warnings": warnings,
            "method": method,
            "note": note,
            "input_chars": len(task["text"]),
        }

    if pending_tasks:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(run_enrich_task, task) for task in pending_tasks]
            for future in as_completed(futures):
                result = future.result()
                fair_slug = str(result["fair_slug"])
                row_index = int(result["row_index"])
                row = raw_rows_by_fair[fair_slug][row_index]
                headline_ja = str(result["headline_ja"])
                summary_ja = str(result["summary_ja"])
                artist_name_kana = str(result["artist_name_kana"])
                warnings = list(result["warnings"])
                method = str(result["method"])
                note = str(result["note"])
                text_hash = str(result["text_hash"])
                source_url = str(result["source_url"])
                request_id = str(result["request_id"])

                if method == "openai_direct_apply":
                    counters["generated_openai"] += 1
                else:
                    counters["generated_fallback"] += 1

                warning_count += len(warnings)

                row["headline_ja"] = headline_ja
                row["summary_ja"] = summary_ja
                row["artist_name_kana"] = artist_name_kana
                row["enrich_status"] = "applied"
                row["enrich_model"] = model
                row["enrich_mode"] = method
                row["enrich_use_openai_batch"] = use_batch
                row["enrich_completion_window"] = completion_window
                row["enrich_prompt_version"] = ENRICH_PROMPT_VERSION
                row["enrich_input_text_hash"] = text_hash
                row["enrich_input_chars"] = int(result["input_chars"])
                row["enrich_headline_chars"] = len(headline_ja)
                row["enrich_summary_chars"] = len(summary_ja)
                row["enrich_artist_name_kana_chars"] = len(artist_name_kana)
                row["enrich_generated_at"] = utc_now_iso()
                row["enrich_notes"] = note

                counters["applied"] += 1
                if len(headline_ja) > HEADLINE_MAX_CHARS:
                    counters["headline_over_limit"] += 1
                if len(summary_ja) > SUMMARY_MAX_CHARS:
                    counters["summary_over_limit"] += 1
                if len(artist_name_kana) > ARTIST_NAME_KANA_MAX_CHARS:
                    counters["artist_name_kana_over_limit"] += 1
                if not headline_ja:
                    counters["headline_empty_after_apply"] += 1
                if not summary_ja:
                    counters["summary_empty_after_apply"] += 1
                if not artist_name_kana:
                    counters["artist_name_kana_empty_after_apply"] += 1
                if warnings:
                    counters["warnings_rows"] += 1

                apply_rows.append(
                    {
                        "request_id": request_id,
                        "fair_slug": fair_slug,
                        "text_hash": text_hash,
                        "source_url": source_url,
                        "status": "APPLIED",
                        "headline_ja": headline_ja,
                        "summary_ja": summary_ja,
                        "artist_name_kana": artist_name_kana,
                        "headline_ja_chars": len(headline_ja),
                        "summary_ja_chars": len(summary_ja),
                        "artist_name_kana_chars": len(artist_name_kana),
                        "warnings": warnings,
                        "enrich_model": model,
                        "enrich_mode": method,
                        "enrich_use_openai_batch": use_batch,
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
    artist_name_kana_empty_total = 0
    for fair_slug, rows in raw_rows_by_fair.items():
        before = raw_text_before[fair_slug]
        after = [str(r.get("text") or "") for r in rows]
        raw_text_changed_count += sum(1 for b, a in zip(before, after) if b != a)
        headline_empty_total += sum(1 for r in rows if not str(r.get("headline_ja") or "").strip())
        summary_empty_total += sum(1 for r in rows if not str(r.get("summary_ja") or "").strip())
        artist_name_kana_empty_total += sum(1 for r in rows if not str(r.get("artist_name_kana") or "").strip())

    apply_output_path = APPLY_OUTPUT_DIR / f"artists_enrichment_apply_output_{TARGET_YEAR}_{stamp}.jsonl"
    write_jsonl(apply_output_path, apply_rows)

    summary = {
        "started_at": started_at,
        "completed_at": utc_now_iso(),
        "target_year": TARGET_YEAR,
        "rag_category": RAG_CATEGORY,
        "requests_path": str(REQUESTS_PATH),
        "raw_input_paths": {k: str(v) for k, v in RAW_INPUT_PATHS.items()},
        "apply_output_path": str(apply_output_path),
        "apply_summary_path": str(APPLY_SUMMARY_DIR / f"artists_enrichment_apply_summary_{TARGET_YEAR}_{stamp}.json"),
        "total_targeted": len(request_rows),
        "total_applied": counters["applied"],
        "total_not_updated": len(request_rows) - counters["applied"],
        "warning_count": warning_count,
        "warning_rows": counters["warnings_rows"],
        "generated_openai": counters["generated_openai"],
        "generated_fallback": counters["generated_fallback"],
        "headline_empty_total": headline_empty_total,
        "summary_empty_total": summary_empty_total,
        "artist_name_kana_empty_total": artist_name_kana_empty_total,
        "headline_over_limit": counters["headline_over_limit"],
        "summary_over_limit": counters["summary_over_limit"],
        "artist_name_kana_over_limit": counters["artist_name_kana_over_limit"],
        "raw_text_changed_count": raw_text_changed_count,
        "counters": dict(counters),
        "enrich_model": model,
        "enrich_use_openai_batch": use_batch,
        "enrich_completion_window": completion_window,
        "enrich_prompt_version": ENRICH_PROMPT_VERSION,
        "openai_client_available": bool(api_key),
        "workers": workers,
    }

    summary_path = APPLY_SUMMARY_DIR / f"artists_enrichment_apply_summary_{TARGET_YEAR}_{stamp}.json"
    write_json(summary_path, summary)

    safe_print(f"[DONE] total_targeted={summary['total_targeted']} total_applied={summary['total_applied']}")
    safe_print(
        "[DONE] "
        f"not_updated={summary['total_not_updated']} warnings={summary['warning_count']} "
        f"fallback={summary['generated_fallback']}"
    )
    safe_print(f"[DONE] apply_output={apply_output_path}")
    safe_print(f"[DONE] apply_summary={summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
