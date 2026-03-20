#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

from dotenv import load_dotenv
from openai import OpenAI

from enrichment_batch_common import (
    TERMINAL_BATCH_STATUSES,
    acquire_process_lock,
    build_batch_request_line,
    build_bulk_artifact_paths,
    build_bulk_contract_fields,
    build_bulk_guard_key,
    build_input_bundle_hash,
    create_responses_batch,
    download_batch_file_rows,
    finalize_runtime_requests_retention,
    load_guard_state,
    read_jsonl,
    release_process_lock,
    retrieve_batch,
    utc_now_compact,
    utc_now_iso,
    upload_batch_input_file,
    validate_bulk_batch_prerequisites,
    validate_bulk_promote_summary,
    validate_resume_guard_state,
    write_guard_state,
    write_json,
    write_jsonl,
)
from phase2_art_pulse_config import promote_history_file_to_current
from run_enrichment_artists_preview import (
    ARTIST_NAME_KANA_MAX_CHARS,
    ENRICH_BATCH_COMPLETION_WINDOW,
    ENRICH_PROMPT_VERSION,
    ENRICH_TEXT_MODEL,
    ENRICH_USE_OPENAI_BATCH,
    HEADLINE_MAX_CHARS,
    RAG_CATEGORY,
    RAW_INPUT_PATHS,
    REQUESTS_OUTPUT_PATH,
    SUMMARY_MAX_CHARS,
    build_openai_request_body,
    build_warnings,
    ensure_requests_output_path,
    infer_artist_name_en,
    parse_openai_response_body,
)

TARGET_YEAR = 2025

REQUESTS_PATH = REQUESTS_OUTPUT_PATH
LOCALIZED_REPAIR_TARGET_REQUEST_IDS = {
    "seed10_artists_enrich_336ffd39ede28d95d3a1983d90f7174bb1f0b740fd34b710a968f6fb4ba38f74",
}
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply artists text enrichment through OpenAI Batch API only.")
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Validate bulk batch prerequisites and rerun-guard inputs without creating a batch job.",
    )
    return parser.parse_args()


def safe_print(line: str) -> None:
    text = str(line)
    encoding = sys.stdout.encoding or "utf-8"
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode(encoding, errors="replace").decode(encoding, errors="replace"))


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


def normalize_source_url_for_match(url: str) -> str:
    value = str(url or "").strip()
    if not value:
        return ""
    try:
        parsed = urlparse(value)
    except Exception:
        return value.strip().rstrip("/").lower()
    scheme = str(parsed.scheme or "https").lower()
    netloc = str(parsed.netloc or "").lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = str(parsed.path or "").rstrip("/")
    path = path or "/"
    return urlunparse((scheme, netloc, path, "", "", ""))


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
    requests_path = ensure_requests_output_path()
    return read_jsonl(requests_path)


def build_batch_row_map(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        custom_id = str(row.get("custom_id") or "").strip()
        if custom_id:
            out[custom_id] = row
    return out


def build_current_applied_row_index(current_output_path: Path) -> dict[tuple[str, str, str, str], dict[str, Any]]:
    if not current_output_path.exists():
        return {}
    out: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for row in read_jsonl(current_output_path):
        if str(row.get("status") or "").strip() != "APPLIED":
            continue
        request_id = str(row.get("request_id") or "").strip()
        fair_slug = str(row.get("fair_slug") or "").strip()
        text_hash = str(row.get("text_hash") or "").strip()
        source_url_norm = normalize_source_url_for_match(str(row.get("source_url") or ""))
        if not request_id or not text_hash or not source_url_norm:
            continue
        out[(request_id, fair_slug, text_hash, source_url_norm)] = row
    return out


def diagnostic_path_for_apply(paths: dict[str, Path]) -> Path:
    return paths["history_summary_path"].with_name(
        paths["history_summary_path"].name.replace("_apply_summary_", "_apply_diagnostics_")
    )


def extract_response_text_for_diagnostic(response_body: dict[str, Any]) -> str:
    output_items = response_body.get("output")
    if isinstance(output_items, list):
        for item in output_items:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for chunk in content:
                if not isinstance(chunk, dict):
                    continue
                if str(chunk.get("type") or "") in {"output_text", "text"}:
                    text = str(chunk.get("text") or "")
                    if text:
                        return text
    return str(response_body.get("output_text") or "")


def maybe_build_localized_repair_update(
    *,
    task: dict[str, Any],
    current_applied_index: dict[tuple[str, str, str, str], dict[str, Any]],
    batch_job_id: str,
    parser_error: str,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    request_id = str(task.get("request_id") or "").strip()
    fair_slug = str(task.get("fair_slug") or "").strip()
    text_hash = str(task.get("text_hash") or "").strip()
    source_url = str(task.get("source_url") or "").strip()
    source_url_norm = normalize_source_url_for_match(source_url)
    diagnostic = {
        "request_id": request_id,
        "fair_slug": fair_slug,
        "text_hash": text_hash,
        "source_url": source_url,
        "source_url_normalized": source_url_norm,
        "batch_job_id": batch_job_id,
        "parser_error": parser_error,
        "repair_target_request_id_match": request_id in LOCALIZED_REPAIR_TARGET_REQUEST_IDS,
        "repair_current_applied_match": False,
        "localized_repair_applied": False,
        "repair_disposition": "not_attempted",
    }
    if request_id not in LOCALIZED_REPAIR_TARGET_REQUEST_IDS:
        diagnostic["repair_disposition"] = "request_id_not_whitelisted"
        return None, diagnostic

    matched = current_applied_index.get((request_id, fair_slug, text_hash, source_url_norm))
    if not matched:
        diagnostic["repair_disposition"] = "current_applied_row_not_found"
        return None, diagnostic

    diagnostic["repair_current_applied_match"] = True
    headline_ja = str(matched.get("headline_ja") or "").strip()
    summary_ja = str(matched.get("summary_ja") or "").strip()
    artist_name_kana = str(matched.get("artist_name_kana") or "").strip()
    if not headline_ja or not summary_ja or not artist_name_kana:
        diagnostic["repair_disposition"] = "current_applied_row_missing_fields"
        return None, diagnostic

    diagnostic["localized_repair_applied"] = True
    diagnostic["repair_disposition"] = "carry_forward_current_applied_row"
    diagnostic["repair_source_status"] = str(matched.get("status") or "")
    diagnostic["repair_source_enrich_mode"] = str(matched.get("enrich_mode") or "")
    update = {
        "fair_slug": fair_slug,
        "row_index": int(task["row_index"]),
        "text_hash": text_hash,
        "source_url": source_url,
        "request_id": request_id,
        "headline_ja": headline_ja,
        "summary_ja": summary_ja,
        "artist_name_kana": artist_name_kana,
        "warnings": [],
        "input_chars": int(task["input_chars"]),
        "repair_mode": "localized_carry_forward_current_applied_row",
        "repair_source_request_id": request_id,
        "repair_source_summary_chars": len(summary_ja),
    }
    return update, diagnostic


def summarize_raw_state(
    raw_rows_by_fair: dict[str, list[dict[str, Any]]],
    raw_text_before: dict[str, list[str]],
) -> dict[str, int]:
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
    return {
        "raw_text_changed_count": raw_text_changed_count,
        "headline_empty_total": headline_empty_total,
        "summary_empty_total": summary_empty_total,
        "artist_name_kana_empty_total": artist_name_kana_empty_total,
    }


def persist_artifacts(
    *,
    history_output_path: Path,
    history_summary_path: Path,
    history_manifest_path: Path,
    apply_rows: list[dict[str, Any]],
    summary: dict[str, Any],
    manifest: dict[str, Any],
    guard_state_path: Path,
    guard_state: dict[str, Any],
) -> None:
    write_jsonl(history_output_path, apply_rows)
    write_json(history_summary_path, summary)
    write_json(history_manifest_path, manifest)
    write_guard_state(guard_state_path, guard_state)


def main() -> int:
    args = parse_args()
    started_at = utc_now_iso()
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
        current_kana = str(row.get("artist_name_kana") or "").strip()
        current_hash = str(row.get("enrich_input_text_hash") or "").strip()
        current_prompt = str(row.get("enrich_prompt_version") or "").strip()

        if current_headline and current_summary and current_kana and current_hash == text_hash and current_prompt == ENRICH_PROMPT_VERSION:
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

        working = deepcopy(req)
        working["text"] = text
        working["source_url"] = source_url or str(working.get("source_url") or "").strip()
        working["artist_name_kana"] = str(working.get("artist_name_kana") or "").strip()
        pending_tasks.append(
            {
                "custom_id": request_id,
                "request_id": request_id,
                "fair_slug": fair_slug,
                "text_hash": text_hash,
                "source_url": source_url,
                "row_index": idx,
                "working": working,
                "input_chars": len(text),
            }
        )

    target_rows = len(pending_tasks)
    input_bundle_hash = build_input_bundle_hash(REQUESTS_PATH)
    guard_key = build_bulk_guard_key(
        requests_path=REQUESTS_PATH,
        input_bundle_hash=input_bundle_hash,
        prompt_version=ENRICH_PROMPT_VERSION,
        model=model,
        target_year=TARGET_YEAR,
    )
    probe_paths = build_bulk_artifact_paths("artists", stamp=utc_now_compact(), target_year=TARGET_YEAR, guard_key=guard_key)
    prereq = validate_bulk_batch_prerequisites(api_key=api_key, use_batch=use_batch, target_rows=target_rows)
    target_request_ids = [str(task["custom_id"]) for task in pending_tasks]

    if args.preflight_only:
        payload = {
            "status": "ok" if prereq["ok"] else "blocked",
            "category": "artists",
            "execution_mode": "bulk_apply",
            "batch_required": True,
            "direct_openai_allowed": False,
            "requests_path": str(REQUESTS_PATH),
            "input_bundle_hash": input_bundle_hash,
            "guard_key": guard_key,
            "guard_state_path": str(probe_paths["guard_state_path"]),
            "target_rows": target_rows,
            "total_requests": len(request_rows),
            "target_request_ids_count": len(target_request_ids),
            "prereq": prereq,
        }
        safe_print(payload)
        return 0 if prereq["ok"] else 1

    if not prereq["ok"]:
        raise RuntimeError(f"batch_required_preflight_failed:{','.join(prereq['reasons'])}")

    if target_rows == 0:
        stamp = utc_now_compact()
        paths = build_bulk_artifact_paths("artists", stamp=stamp, target_year=TARGET_YEAR, guard_key=guard_key)
        raw_state = summarize_raw_state(raw_rows_by_fair, raw_text_before)
        summary = {
            "started_at": started_at,
            "completed_at": utc_now_iso(),
            "target_year": TARGET_YEAR,
            "rag_category": RAG_CATEGORY,
            "requests_path": str(REQUESTS_PATH),
            "raw_input_paths": {k: str(v) for k, v in RAW_INPUT_PATHS.items()},
            "apply_output_path": str(paths["history_output_path"]),
            "apply_summary_path": str(paths["history_summary_path"]),
            "apply_manifest_path": str(paths["history_manifest_path"]),
            "current_output_path": str(paths["current_output_path"]),
            "current_summary_path": str(paths["current_summary_path"]),
            "total_targeted": len(request_rows),
            "total_applied": 0,
            "total_not_updated": len(request_rows),
            "warning_count": 0,
            "warning_rows": 0,
            "generated_openai": 0,
            "generated_fallback": 0,
            "error_count": 0,
            "batch_status": "not_submitted",
            "promoted_to_current": False,
            "promote_verdict": "promote_blocked_no_target_rows",
            "guard_state_path": str(paths["guard_state_path"]),
            "guard_key": guard_key,
            "target_request_ids_count": 0,
            "target_request_ids": [],
            "counters": dict(counters),
            "enrich_model": model,
            "enrich_use_openai_batch": use_batch,
            "enrich_completion_window": completion_window,
            "enrich_prompt_version": ENRICH_PROMPT_VERSION,
            "openai_client_available": bool(api_key),
            **raw_state,
            **build_bulk_contract_fields(
                api_mode="bulk_noop",
                batch_used=False,
                batch_job_id="",
                input_bundle_hash=input_bundle_hash,
                target_rows=0,
                updated_rows=0,
                rerun_guard_verdict="no_target_rows",
                process_lock_id="",
            ),
        }
        manifest = {
            "schema_name": "enrichment_bulk_apply_manifest",
            "category": "artists",
            "guard_status": "completed_no_target_rows",
            "batch_status": "not_submitted",
            "requests_path": str(REQUESTS_PATH),
            "target_request_ids": [],
            "enrich_model": model,
            "enrich_prompt_version": ENRICH_PROMPT_VERSION,
            "enrich_completion_window": completion_window,
            "openai_client_available": bool(api_key),
            **build_bulk_contract_fields(
                api_mode="bulk_noop",
                batch_used=False,
                batch_job_id="",
                input_bundle_hash=input_bundle_hash,
                target_rows=0,
                updated_rows=0,
                rerun_guard_verdict="no_target_rows",
                process_lock_id="",
            ),
        }
        write_jsonl(paths["history_output_path"], apply_rows)
        write_json(paths["history_summary_path"], summary)
        write_json(paths["history_manifest_path"], manifest)
        safe_print("[DONE] target_rows=0 batch_not_submitted current_not_promoted")
        safe_print(f"[DONE] history_summary={paths['history_summary_path']}")
        return 0

    process_lock_id = ""
    release_lock_at_exit = False
    try:
        existing_state = load_guard_state(probe_paths["guard_state_path"])
        rerun_guard_verdict = "new_run"
        if existing_state:
            existing_status = str(existing_state.get("guard_status") or "")
            if existing_status == "completed":
                raise RuntimeError(f"rerun_guard_blocked_completed:{probe_paths['guard_state_path']}")
            if existing_status in {"terminal_failed", "failed", "cancelled", "expired"}:
                raise RuntimeError(f"rerun_guard_blocked_terminal:{probe_paths['guard_state_path']}")
            if existing_status != "in_progress":
                raise RuntimeError(f"rerun_guard_blocked_unknown_state:{existing_status}")
            resume_guard = validate_resume_guard_state(
                existing_state=existing_state,
                lock_path=probe_paths["lock_path"],
                expected_target_request_ids=target_request_ids,
                category="artists",
                guard_key=guard_key,
            )
            rerun_guard_verdict = "resume_existing_batch"
            process_lock_id = str(resume_guard["process_lock_id"])
            stamp = str(existing_state.get("stamp") or "").strip()
            if not stamp:
                raise RuntimeError("rerun_guard_missing_stamp")
            paths = build_bulk_artifact_paths("artists", stamp=stamp, target_year=TARGET_YEAR, guard_key=guard_key)
            batch_job_id = str(existing_state.get("batch_job_id") or "").strip()
            batch_input_file_id = str(existing_state.get("batch_input_file_id") or "").strip()
            if not batch_job_id:
                raise RuntimeError("rerun_guard_missing_batch_job_id")
        else:
            process_lock_id = acquire_process_lock(probe_paths["lock_path"], category="artists", guard_key=guard_key)
            release_lock_at_exit = True
            stamp = utc_now_compact()
            paths = build_bulk_artifact_paths("artists", stamp=stamp, target_year=TARGET_YEAR, guard_key=guard_key)
            batch_job_id = ""
            batch_input_file_id = ""

        client = OpenAI(api_key=api_key)

        if rerun_guard_verdict == "new_run":
            batch_input_rows: list[dict[str, Any]] = []
            for task in pending_tasks:
                batch_input_rows.append(
                    build_batch_request_line(
                        custom_id=str(task["custom_id"]),
                        body=build_openai_request_body(model, dict(task["working"])),
                    )
                )
            write_jsonl(paths["batch_input_path"], batch_input_rows)
            upload_file = upload_batch_input_file(client, paths["batch_input_path"])
            batch_input_file_id = str(upload_file.get("id") or "").strip()
            if not batch_input_file_id:
                raise RuntimeError("batch_input_file_id_missing")
            batch_state = create_responses_batch(
                client,
                input_file_id=batch_input_file_id,
                completion_window=completion_window,
                metadata={
                    "category": "artists",
                    "target_year": str(TARGET_YEAR),
                    "guard_key": guard_key[:32],
                    "input_bundle_hash": input_bundle_hash[:32],
                },
            )
            batch_job_id = str(batch_state.get("id") or "").strip()
            if not batch_job_id:
                raise RuntimeError("batch_job_id_missing")
            guard_state = {
                "category": "artists",
                "target_year": TARGET_YEAR,
                "stamp": stamp,
                "guard_status": "in_progress",
                "guard_key": guard_key,
                "guard_state_path": str(paths["guard_state_path"]),
                "requests_path": str(REQUESTS_PATH),
                "input_bundle_hash": input_bundle_hash,
                "enrich_model": model,
                "enrich_prompt_version": ENRICH_PROMPT_VERSION,
                "enrich_completion_window": completion_window,
                "target_rows": target_rows,
                "updated_rows": 0,
                "target_request_ids": target_request_ids,
                "process_lock_id": process_lock_id,
                "rerun_guard_verdict": rerun_guard_verdict,
                "execution_mode": "bulk_apply",
                "batch_required": True,
                "api_mode": "openai_batch_apply",
                "batch_used": True,
                "batch_job_id": batch_job_id,
                "batch_input_file_id": batch_input_file_id,
                "batch_input_path": str(paths["batch_input_path"]),
                "history_output_path": str(paths["history_output_path"]),
                "history_summary_path": str(paths["history_summary_path"]),
                "history_manifest_path": str(paths["history_manifest_path"]),
                "current_output_path": str(paths["current_output_path"]),
                "current_summary_path": str(paths["current_summary_path"]),
                "started_at": started_at,
                "updated_at": utc_now_iso(),
                "completed_at": "",
            }
            write_guard_state(paths["guard_state_path"], guard_state)
            release_lock_at_exit = False
        else:
            batch_state = retrieve_batch(client, batch_job_id)
            guard_state = dict(existing_state or {})
            guard_state["rerun_guard_verdict"] = rerun_guard_verdict
            guard_state["updated_at"] = utc_now_iso()

        if rerun_guard_verdict == "new_run":
            batch_state = retrieve_batch(client, batch_job_id)

        batch_status = str(batch_state.get("status") or "").strip()
        guard_state["batch_status"] = batch_status
        guard_state["batch_job_id"] = batch_job_id
        guard_state["batch_input_file_id"] = batch_input_file_id
        guard_state["request_counts"] = batch_state.get("request_counts") or {}
        guard_state["updated_at"] = utc_now_iso()

        if batch_status not in TERMINAL_BATCH_STATUSES:
            waiting_rows = apply_rows + [
                {
                    "request_id": str(task["request_id"]),
                    "fair_slug": str(task["fair_slug"]),
                    "text_hash": str(task["text_hash"]),
                    "source_url": str(task["source_url"]),
                    "status": "BATCH_WAITING",
                    "batch_job_id": batch_job_id,
                    "batch_status": batch_status or "in_progress",
                }
                for task in pending_tasks
            ]
            raw_state = summarize_raw_state(raw_rows_by_fair, raw_text_before)
            summary = {
                "started_at": str(guard_state.get("started_at") or started_at),
                "completed_at": "",
                "target_year": TARGET_YEAR,
                "rag_category": RAG_CATEGORY,
                "requests_path": str(REQUESTS_PATH),
                "raw_input_paths": {k: str(v) for k, v in RAW_INPUT_PATHS.items()},
                "apply_output_path": str(paths["history_output_path"]),
                "apply_summary_path": str(paths["history_summary_path"]),
                "apply_manifest_path": str(paths["history_manifest_path"]),
                "current_output_path": str(paths["current_output_path"]),
                "current_summary_path": str(paths["current_summary_path"]),
                "total_targeted": len(request_rows),
                "total_applied": 0,
                "total_not_updated": len(request_rows),
                "warning_count": 0,
                "warning_rows": 0,
                "generated_openai": 0,
                "generated_fallback": 0,
                "error_count": 0,
                "batch_status": batch_status or "in_progress",
                "promoted_to_current": False,
                "promote_verdict": "promote_blocked_batch_not_completed",
                "guard_state_path": str(paths["guard_state_path"]),
                "guard_key": guard_key,
                "target_request_ids_count": len(target_request_ids),
                "target_request_ids": target_request_ids,
                "counters": dict(counters),
                "request_counts": batch_state.get("request_counts") or {},
                "enrich_model": model,
                "enrich_use_openai_batch": use_batch,
                "enrich_completion_window": completion_window,
                "enrich_prompt_version": ENRICH_PROMPT_VERSION,
                "openai_client_available": bool(api_key),
                **raw_state,
                **build_bulk_contract_fields(
                    api_mode="openai_batch_apply",
                    batch_used=True,
                    batch_job_id=batch_job_id,
                    input_bundle_hash=input_bundle_hash,
                    target_rows=target_rows,
                    updated_rows=0,
                    rerun_guard_verdict=rerun_guard_verdict,
                    process_lock_id=process_lock_id,
                ),
            }
            manifest = {
                "schema_name": "enrichment_bulk_apply_manifest",
                "category": "artists",
                "guard_status": "in_progress",
                "batch_status": batch_status or "in_progress",
                "requests_path": str(REQUESTS_PATH),
                "target_request_ids": target_request_ids,
                "request_counts": batch_state.get("request_counts") or {},
                "batch_input_file_id": batch_input_file_id,
                "batch_input_path": str(paths["batch_input_path"]),
                "enrich_model": model,
                "enrich_prompt_version": ENRICH_PROMPT_VERSION,
                "enrich_completion_window": completion_window,
                "openai_client_available": bool(api_key),
                **build_bulk_contract_fields(
                    api_mode="openai_batch_apply",
                    batch_used=True,
                    batch_job_id=batch_job_id,
                    input_bundle_hash=input_bundle_hash,
                    target_rows=target_rows,
                    updated_rows=0,
                    rerun_guard_verdict=rerun_guard_verdict,
                    process_lock_id=process_lock_id,
                ),
            }
            persist_artifacts(
                history_output_path=paths["history_output_path"],
                history_summary_path=paths["history_summary_path"],
                history_manifest_path=paths["history_manifest_path"],
                apply_rows=waiting_rows,
                summary=summary,
                manifest=manifest,
                guard_state_path=paths["guard_state_path"],
                guard_state=guard_state,
            )
            safe_print(f"[HOLD] batch_job_id={batch_job_id} status={batch_status or 'in_progress'}")
            safe_print(f"[HOLD] summary={paths['history_summary_path']}")
            return 0

        output_rows = download_batch_file_rows(client, str(batch_state.get("output_file_id") or ""))
        error_rows = download_batch_file_rows(client, str(batch_state.get("error_file_id") or ""))
        output_map = build_batch_row_map(output_rows)
        error_map = build_batch_row_map(error_rows)
        current_applied_index = build_current_applied_row_index(paths["current_output_path"])
        diagnostics_path = diagnostic_path_for_apply(paths)

        staged_updates: list[dict[str, Any]] = []
        warning_count = 0
        batch_result_rows: list[dict[str, Any]] = []
        diagnostic_rows: list[dict[str, Any]] = []
        parsed_success_rows = 0
        batch_error_count = 0

        for task in pending_tasks:
            custom_id = str(task["custom_id"])
            result_row = output_map.get(custom_id)
            error_row = error_map.get(custom_id)
            artist_name_en = infer_artist_name_en(dict(task["working"]))

            if error_row:
                batch_error_count += 1
                counters["batch_error_file_rows"] += 1
                batch_result_rows.append({"request_id": custom_id, "fair_slug": str(task["fair_slug"]), "text_hash": str(task["text_hash"]), "source_url": str(task["source_url"]), "status": "BATCH_RESULT_FAILED", "batch_job_id": batch_job_id, "batch_status": batch_status, "error": error_row.get("error")})
                continue
            if not result_row:
                batch_error_count += 1
                counters["batch_result_missing"] += 1
                batch_result_rows.append({"request_id": custom_id, "fair_slug": str(task["fair_slug"]), "text_hash": str(task["text_hash"]), "source_url": str(task["source_url"]), "status": "BATCH_RESULT_MISSING", "batch_job_id": batch_job_id, "batch_status": batch_status})
                continue

            response_info = result_row.get("response")
            if not isinstance(response_info, dict):
                batch_error_count += 1
                counters["batch_response_missing"] += 1
                batch_result_rows.append({"request_id": custom_id, "fair_slug": str(task["fair_slug"]), "text_hash": str(task["text_hash"]), "source_url": str(task["source_url"]), "status": "BATCH_RESPONSE_MISSING", "batch_job_id": batch_job_id, "batch_status": batch_status})
                continue

            status_code = int(response_info.get("status_code") or 0)
            response_body = response_info.get("body")
            if status_code != 200 or not isinstance(response_body, dict):
                batch_error_count += 1
                counters["batch_request_failed"] += 1
                batch_result_rows.append({"request_id": custom_id, "fair_slug": str(task["fair_slug"]), "text_hash": str(task["text_hash"]), "source_url": str(task["source_url"]), "status": "BATCH_REQUEST_FAILED", "batch_job_id": batch_job_id, "batch_status": batch_status, "status_code": status_code, "error": result_row.get("error")})
                continue

            try:
                headline_ja, summary_ja, artist_name_kana = parse_openai_response_body(response_body)
            except Exception as exc:
                parser_error = str(exc)
                response_request_id = ""
                if isinstance(response_info, dict):
                    response_request_id = str(response_info.get("request_id") or "").strip()
                response_text = extract_response_text_for_diagnostic(response_body)
                repaired_update, diagnostic = maybe_build_localized_repair_update(
                    task=task,
                    current_applied_index=current_applied_index,
                    batch_job_id=batch_job_id,
                    parser_error=parser_error,
                )
                diagnostic.update(
                    {
                        "batch_status": batch_status,
                        "response_request_id": response_request_id,
                        "response_status_code": status_code,
                        "response_text": response_text,
                    }
                )
                diagnostic_rows.append(diagnostic)
                if repaired_update is None:
                    batch_error_count += 1
                    counters["batch_parse_failed"] += 1
                    batch_result_rows.append({"request_id": custom_id, "fair_slug": str(task["fair_slug"]), "text_hash": str(task["text_hash"]), "source_url": str(task["source_url"]), "status": "BATCH_PARSE_FAILED", "batch_job_id": batch_job_id, "batch_status": batch_status, "error": parser_error})
                    continue

                counters["batch_parse_failed_localized_repair_applied"] += 1
                parsed_success_rows += 1
                staged_updates.append(repaired_update)
                continue

            warnings = build_warnings(summary_ja=summary_ja, artist_name_en=artist_name_en, artist_name_kana=artist_name_kana)
            warning_count += len(warnings)
            parsed_success_rows += 1
            staged_updates.append({"fair_slug": str(task["fair_slug"]), "row_index": int(task["row_index"]), "text_hash": str(task["text_hash"]), "source_url": str(task["source_url"]), "request_id": custom_id, "headline_ja": headline_ja, "summary_ja": summary_ja, "artist_name_kana": artist_name_kana, "warnings": warnings, "input_chars": int(task["input_chars"]), "repair_mode": "", "repair_source_request_id": "", "repair_source_summary_chars": 0})

        committed_rows = 0
        if batch_error_count == 0 and parsed_success_rows == target_rows:
            for update in staged_updates:
                fair_slug = update["fair_slug"]
                row = raw_rows_by_fair[fair_slug][update["row_index"]]
                row["headline_ja"] = update["headline_ja"]
                row["summary_ja"] = update["summary_ja"]
                row["artist_name_kana"] = update["artist_name_kana"]
                row["enrich_status"] = "applied"
                row["enrich_model"] = model
                row["enrich_mode"] = "openai_batch_apply"
                row["enrich_use_openai_batch"] = use_batch
                row["enrich_completion_window"] = completion_window
                row["enrich_prompt_version"] = ENRICH_PROMPT_VERSION
                row["enrich_input_text_hash"] = update["text_hash"]
                row["enrich_input_chars"] = update["input_chars"]
                row["enrich_headline_chars"] = len(update["headline_ja"])
                row["enrich_summary_chars"] = len(update["summary_ja"])
                row["enrich_artist_name_kana_chars"] = len(update["artist_name_kana"])
                row["enrich_generated_at"] = utc_now_iso()
                row["enrich_notes"] = str(update.get("repair_mode") or "")
                row["enrich_batch_job_id"] = batch_job_id
                committed_rows += 1
                if len(update["headline_ja"]) > HEADLINE_MAX_CHARS:
                    counters["headline_over_limit"] += 1
                if len(update["summary_ja"]) > SUMMARY_MAX_CHARS:
                    counters["summary_over_limit"] += 1
                if len(update["artist_name_kana"]) > ARTIST_NAME_KANA_MAX_CHARS:
                    counters["artist_name_kana_over_limit"] += 1
                if update["warnings"]:
                    counters["warnings_rows"] += 1
                batch_result_rows.append({"request_id": update["request_id"], "fair_slug": fair_slug, "text_hash": update["text_hash"], "source_url": update["source_url"], "status": "APPLIED", "headline_ja": update["headline_ja"], "summary_ja": update["summary_ja"], "artist_name_kana": update["artist_name_kana"], "headline_ja_chars": len(update["headline_ja"]), "summary_ja_chars": len(update["summary_ja"]), "artist_name_kana_chars": len(update["artist_name_kana"]), "warnings": update["warnings"], "enrich_model": model, "enrich_mode": "openai_batch_apply", "enrich_use_openai_batch": use_batch, "enrich_completion_window": completion_window, "enrich_prompt_version": ENRICH_PROMPT_VERSION, "enrich_input_text_hash": update["text_hash"], "enrich_batch_job_id": batch_job_id, "enrich_notes": str(update.get("repair_mode") or "")})
            for fair_slug, raw_path in RAW_INPUT_PATHS.items():
                write_jsonl(raw_path, raw_rows_by_fair[fair_slug])
        else:
            for update in staged_updates:
                status = "LOCALIZED_REPAIR_READY_UNCOMMITTED" if str(update.get("repair_mode") or "") else "BATCH_RESULT_READY_UNCOMMITTED"
                batch_result_rows.append({"request_id": update["request_id"], "fair_slug": update["fair_slug"], "text_hash": update["text_hash"], "source_url": update["source_url"], "status": status, "headline_ja": update["headline_ja"], "summary_ja": update["summary_ja"], "artist_name_kana": update["artist_name_kana"], "warnings": update["warnings"], "batch_job_id": batch_job_id, "batch_status": batch_status, "repair_mode": str(update.get("repair_mode") or ""), "repair_source_request_id": str(update.get("repair_source_request_id") or "")})

        apply_rows.extend(batch_result_rows)
        raw_state = summarize_raw_state(raw_rows_by_fair, raw_text_before)
        error_count = counters["skipped_non_artists_category"] + counters["skipped_invalid_fair_slug"] + counters["skipped_missing_text_hash"] + counters["skipped_target_guard_non_artist_utility_url"] + counters["skipped_target_guard_missing_target"] + counters["skipped_target_row_not_found"] + counters["skipped_empty_text"] + batch_error_count

        diagnostics_payload = {
            "category": "artists",
            "target_year": TARGET_YEAR,
            "batch_job_id": batch_job_id,
            "batch_status": batch_status,
            "localized_repair_applied": int(counters.get("batch_parse_failed_localized_repair_applied", 0)),
            "diagnostic_rows": diagnostic_rows,
        }
        if diagnostic_rows:
            write_json(diagnostics_path, diagnostics_payload)

        summary = {
            "started_at": str(guard_state.get("started_at") or started_at),
            "completed_at": utc_now_iso(),
            "target_year": TARGET_YEAR,
            "rag_category": RAG_CATEGORY,
            "requests_path": str(REQUESTS_PATH),
            "raw_input_paths": {k: str(v) for k, v in RAW_INPUT_PATHS.items()},
            "apply_output_path": str(paths["history_output_path"]),
            "apply_summary_path": str(paths["history_summary_path"]),
            "apply_manifest_path": str(paths["history_manifest_path"]),
            "current_output_path": str(paths["current_output_path"]),
            "current_summary_path": str(paths["current_summary_path"]),
            "total_targeted": len(request_rows),
            "total_applied": committed_rows,
            "total_not_updated": len(request_rows) - committed_rows,
            "warning_count": warning_count,
            "warning_rows": counters["warnings_rows"],
            "generated_openai": committed_rows,
            "generated_fallback": 0,
            "error_count": error_count,
            "batch_status": batch_status,
            "request_counts": batch_state.get("request_counts") or {},
            "parsed_success_rows": parsed_success_rows,
            "batch_error_rows": batch_error_count,
            "diagnostics_path": str(diagnostics_path) if diagnostic_rows else "",
            "diagnostic_rows": len(diagnostic_rows),
            "localized_repair_applied": int(counters.get("batch_parse_failed_localized_repair_applied", 0)),
            "promoted_to_current": False,
            "promote_verdict": "",
            "guard_state_path": str(paths["guard_state_path"]),
            "guard_key": guard_key,
            "target_request_ids_count": len(target_request_ids),
            "target_request_ids": target_request_ids,
            "counters": dict(counters),
            "enrich_model": model,
            "enrich_use_openai_batch": use_batch,
            "enrich_completion_window": completion_window,
            "enrich_prompt_version": ENRICH_PROMPT_VERSION,
            "openai_client_available": bool(api_key),
            **raw_state,
            **build_bulk_contract_fields(api_mode="openai_batch_apply", batch_used=True, batch_job_id=batch_job_id, input_bundle_hash=input_bundle_hash, target_rows=target_rows, updated_rows=committed_rows, rerun_guard_verdict=rerun_guard_verdict, process_lock_id=process_lock_id),
        }
        manifest = {
            "schema_name": "enrichment_bulk_apply_manifest",
            "category": "artists",
            "guard_status": "completed" if committed_rows == target_rows and error_count == 0 else "terminal_failed",
            "batch_status": batch_status,
            "requests_path": str(REQUESTS_PATH),
            "target_request_ids": target_request_ids,
            "request_counts": batch_state.get("request_counts") or {},
            "batch_input_file_id": batch_input_file_id,
            "batch_output_file_id": str(batch_state.get("output_file_id") or ""),
            "batch_error_file_id": str(batch_state.get("error_file_id") or ""),
            "batch_input_path": str(paths["batch_input_path"]),
            "diagnostics_path": str(diagnostics_path) if diagnostic_rows else "",
            "diagnostic_rows": len(diagnostic_rows),
            "localized_repair_applied": int(counters.get("batch_parse_failed_localized_repair_applied", 0)),
            "enrich_model": model,
            "enrich_prompt_version": ENRICH_PROMPT_VERSION,
            "enrich_completion_window": completion_window,
            "openai_client_available": bool(api_key),
            "parsed_success_rows": parsed_success_rows,
            "batch_error_rows": batch_error_count,
            **build_bulk_contract_fields(api_mode="openai_batch_apply", batch_used=True, batch_job_id=batch_job_id, input_bundle_hash=input_bundle_hash, target_rows=target_rows, updated_rows=committed_rows, rerun_guard_verdict=rerun_guard_verdict, process_lock_id=process_lock_id),
        }

        promote_ok, promote_verdict = validate_bulk_promote_summary(summary)
        summary["promote_verdict"] = promote_verdict
        guard_state["guard_status"] = "completed" if promote_ok else "terminal_failed"
        guard_state["updated_rows"] = committed_rows
        guard_state["batch_status"] = batch_status
        guard_state["completed_at"] = utc_now_iso()
        guard_state["updated_at"] = guard_state["completed_at"]

        persist_artifacts(history_output_path=paths["history_output_path"], history_summary_path=paths["history_summary_path"], history_manifest_path=paths["history_manifest_path"], apply_rows=apply_rows, summary=summary, manifest=manifest, guard_state_path=paths["guard_state_path"], guard_state=guard_state)
        release_lock_at_exit = True

        if promote_ok:
            promote_history_file_to_current(paths["history_output_path"], paths["current_output_path"])
            promote_history_file_to_current(paths["history_summary_path"], paths["current_summary_path"])
            summary["promoted_to_current"] = True
        release_process_lock(paths["lock_path"])
        release_lock_at_exit = False

        retention_info = finalize_runtime_requests_retention(
            category="artists",
            target_year=TARGET_YEAR,
            requests_path=REQUESTS_PATH,
            summary=summary,
            guard_state_path=paths["guard_state_path"],
            lock_path=paths["lock_path"],
        )
        summary.update(retention_info)
        manifest.update(retention_info)
        write_json(paths["history_summary_path"], summary)
        write_json(paths["history_manifest_path"], manifest)

        if promote_ok:
            write_json(paths["current_summary_path"], summary)
            safe_print(f"[DONE] total_targeted={summary['total_targeted']} total_applied={summary['total_applied']}")
            safe_print(f"[DONE] history_summary={paths['history_summary_path']}")
            safe_print(f"[DONE] current_summary={paths['current_summary_path']}")
            return 0

        safe_print(f"[BLOCKED] promote_verdict={promote_verdict}")
        safe_print(f"[BLOCKED] history_summary={paths['history_summary_path']}")
        return 1
    finally:
        if release_lock_at_exit:
            release_process_lock(probe_paths["lock_path"])


if __name__ == "__main__":
    raise SystemExit(main())
