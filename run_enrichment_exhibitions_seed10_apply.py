#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from enrichment_batch_common import (
    TERMINAL_BATCH_STATUSES,
    acquire_process_lock,
    build_enrichment_field_custom_id,
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
    resolve_runtime_requests_path,
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
from model_routing import (
    ENRICH_USE_OPENAI_BATCH_DEFAULT,
    EXHIBITIONS_ENRICHMENT_BATCH_FIELDS,
    EXHIBITIONS_ENRICHMENT_FIELD_MODELS,
    get_enrichment_model_fingerprint,
    get_exhibitions_enrichment_model,
)
from phase2_art_pulse_config import promote_history_file_to_current
from run_enrichment_exhibitions_preview import (
    ENRICH_BATCH_COMPLETION_WINDOW,
    ENRICH_PROMPT_VERSION,
    HEADLINE_MAX_CHARS,
    RAW_INPUT_PATHS,
    REQUESTS_OUTPUT_PATH,
    SUMMARY_MAX_CHARS,
    build_openai_request_body,
    build_requests,
    build_warnings,
    parse_openai_response_body,
)

TARGET_YEAR = 2025


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply exhibitions text enrichment through OpenAI Batch API only.")
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Validate bulk batch prerequisites and rerun-guard inputs without creating a batch job.",
    )
    return parser.parse_args()


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
    requests_path = resolve_runtime_requests_path("exhibitions", target_year=TARGET_YEAR)
    if requests_path.exists():
        return read_jsonl(requests_path)
    request_rows, _ = build_requests()
    write_jsonl(requests_path, request_rows)
    return request_rows


def build_batch_row_map(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        custom_id = str(row.get("custom_id") or "").strip()
        if custom_id:
            out[custom_id] = row
    return out


def summarize_raw_state(
    raw_rows_by_fair: dict[str, list[dict[str, Any]]],
    raw_text_before: dict[str, list[str]],
) -> dict[str, int]:
    raw_text_changed_count = 0
    headline_empty_total = 0
    summary_empty_total = 0
    for fair_slug, rows in raw_rows_by_fair.items():
        before = raw_text_before[fair_slug]
        after = [str(r.get("text") or "") for r in rows]
        raw_text_changed_count += sum(1 for b, a in zip(before, after) if b != a)
        headline_empty_total += sum(1 for r in rows if not str(r.get("headline_ja") or "").strip())
        summary_empty_total += sum(1 for r in rows if not str(r.get("summary_ja") or "").strip())
    return {
        "raw_text_changed_count": raw_text_changed_count,
        "headline_empty_total": headline_empty_total,
        "summary_empty_total": summary_empty_total,
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

    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    enrich_model_fingerprint = get_enrichment_model_fingerprint("exhibitions")
    use_batch = (
        os.getenv("ENRICH_USE_OPENAI_BATCH", ENRICH_USE_OPENAI_BATCH_DEFAULT).strip()
        or ENRICH_USE_OPENAI_BATCH_DEFAULT
    )
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
        source_url = str(req.get("source_url") or "").strip()

        if not fair_slug or fair_slug not in raw_rows_by_fair:
            counters["skipped_invalid_fair_slug"] += 1
            apply_rows.append({"request_id": request_id, "fair_slug": fair_slug, "text_hash": text_hash, "status": "SKIPPED_INVALID_FAIR_SLUG"})
            continue
        if not text_hash:
            counters["skipped_missing_text_hash"] += 1
            apply_rows.append({"request_id": request_id, "fair_slug": fair_slug, "status": "SKIPPED_MISSING_TEXT_HASH"})
            continue

        rows = raw_rows_by_fair[fair_slug]
        idx = row_index_by_fair[fair_slug].get((text_hash, source_url))
        if idx is None:
            idx = row_index_by_fair[fair_slug].get((text_hash, ""))
        if idx is None:
            counters["skipped_target_row_not_found"] += 1
            apply_rows.append({"request_id": request_id, "fair_slug": fair_slug, "text_hash": text_hash, "source_url": source_url, "status": "SKIPPED_TARGET_ROW_NOT_FOUND"})
            continue

        row = rows[idx]
        text = str(row.get("text") or "").strip()
        if not text:
            counters["skipped_empty_text"] += 1
            apply_rows.append({"request_id": request_id, "fair_slug": fair_slug, "text_hash": text_hash, "source_url": source_url, "status": "SKIPPED_EMPTY_TEXT"})
            continue

        current_headline = str(row.get("headline_ja") or "").strip()
        current_summary = str(row.get("summary_ja") or "").strip()
        current_hash = str(row.get("enrich_input_text_hash") or "").strip()
        current_prompt = str(row.get("enrich_prompt_version") or "").strip()

        if current_headline and current_summary and current_hash == text_hash and current_prompt == ENRICH_PROMPT_VERSION:
            counters["skipped_hash_match"] += 1
            apply_rows.append({"request_id": request_id, "fair_slug": fair_slug, "text_hash": text_hash, "source_url": source_url, "status": "SKIPPED_HASH_MATCH", "headline_ja": current_headline, "summary_ja": current_summary})
            continue
        if current_headline and current_summary:
            counters["skipped_already_filled"] += 1
            apply_rows.append({"request_id": request_id, "fair_slug": fair_slug, "text_hash": text_hash, "source_url": source_url, "status": "SKIPPED_ALREADY_FILLED", "headline_ja": current_headline, "summary_ja": current_summary})
            continue

        working = deepcopy(req)
        working["text"] = text
        working["source_url"] = source_url or str(row.get("source_url") or "").strip()
        working["gallery_name"] = str(row.get("gallery_name_en") or req.get("gallery_name") or "").strip()
        pending_tasks.append({"custom_id": request_id, "request_id": request_id, "fair_slug": fair_slug, "text_hash": text_hash, "source_url": source_url, "row_index": idx, "working": working, "input_chars": len(text)})

    target_rows = len(pending_tasks)
    input_bundle_hash = build_input_bundle_hash(REQUESTS_OUTPUT_PATH)
    guard_key = build_bulk_guard_key(requests_path=REQUESTS_OUTPUT_PATH, input_bundle_hash=input_bundle_hash, prompt_version=ENRICH_PROMPT_VERSION, model=enrich_model_fingerprint, target_year=TARGET_YEAR)
    probe_paths = build_bulk_artifact_paths("exhibitions", stamp=utc_now_compact(), target_year=TARGET_YEAR, guard_key=guard_key)
    prereq = validate_bulk_batch_prerequisites(api_key=api_key, use_batch=use_batch, target_rows=target_rows)
    target_request_ids = [
        build_enrichment_field_custom_id(str(task["custom_id"]), field_name)
        for task in pending_tasks
        for field_name in EXHIBITIONS_ENRICHMENT_BATCH_FIELDS
    ]

    if args.preflight_only:
        print(
            {
                "status": "ok" if prereq["ok"] else "blocked",
                "category": "exhibitions",
                "execution_mode": "bulk_apply",
                "batch_required": True,
                "direct_openai_allowed": False,
                "requests_path": str(REQUESTS_OUTPUT_PATH),
                "input_bundle_hash": input_bundle_hash,
                "guard_key": guard_key,
                "guard_state_path": str(probe_paths["guard_state_path"]),
                "target_rows": target_rows,
                "total_requests": len(request_rows),
                "target_request_ids_count": len(target_request_ids),
                "enrich_model": enrich_model_fingerprint,
                "enrich_models_by_field": dict(EXHIBITIONS_ENRICHMENT_FIELD_MODELS),
                "prereq": prereq,
            }
        )
        return 0 if prereq["ok"] else 1

    if not prereq["ok"]:
        raise RuntimeError(f"batch_required_preflight_failed:{','.join(prereq['reasons'])}")

    if target_rows == 0:
        stamp = utc_now_compact()
        paths = build_bulk_artifact_paths("exhibitions", stamp=stamp, target_year=TARGET_YEAR, guard_key=guard_key)
        raw_state = summarize_raw_state(raw_rows_by_fair, raw_text_before)
        summary = {
            "started_at": started_at,
            "completed_at": utc_now_iso(),
            "target_year": TARGET_YEAR,
            "requests_path": str(REQUESTS_OUTPUT_PATH),
            "apply_output_path": str(paths["history_output_path"]),
            "apply_summary_path": str(paths["history_summary_path"]),
            "apply_manifest_path": str(paths["history_manifest_path"]),
            "current_output_path": str(paths["current_output_path"]),
            "current_summary_path": str(paths["current_summary_path"]),
            "total_targeted": len(request_rows),
            "total_applied": 0,
            "warning_count": 0,
            "error_count": 0,
            "batch_status": "not_submitted",
            "promoted_to_current": False,
            "promote_verdict": "promote_blocked_no_target_rows",
            "guard_state_path": str(paths["guard_state_path"]),
            "guard_key": guard_key,
            "target_request_ids_count": 0,
            "target_request_ids": [],
            "counters": dict(counters),
            "enrich_model": enrich_model_fingerprint,
            "enrich_models_by_field": dict(EXHIBITIONS_ENRICHMENT_FIELD_MODELS),
            "enrich_use_openai_batch": use_batch,
            "enrich_completion_window": completion_window,
            "enrich_prompt_version": ENRICH_PROMPT_VERSION,
            "openai_client_available": bool(api_key),
            **raw_state,
            **build_bulk_contract_fields(api_mode="bulk_noop", batch_used=False, batch_job_id="", input_bundle_hash=input_bundle_hash, target_rows=0, updated_rows=0, rerun_guard_verdict="no_target_rows", process_lock_id=""),
        }
        manifest = {
            "schema_name": "enrichment_bulk_apply_manifest",
            "category": "exhibitions",
            "guard_status": "completed_no_target_rows",
            "batch_status": "not_submitted",
            "requests_path": str(REQUESTS_OUTPUT_PATH),
            "target_request_ids": [],
            "enrich_model": enrich_model_fingerprint,
            "enrich_models_by_field": dict(EXHIBITIONS_ENRICHMENT_FIELD_MODELS),
            "enrich_prompt_version": ENRICH_PROMPT_VERSION,
            "enrich_completion_window": completion_window,
            "openai_client_available": bool(api_key),
            **build_bulk_contract_fields(api_mode="bulk_noop", batch_used=False, batch_job_id="", input_bundle_hash=input_bundle_hash, target_rows=0, updated_rows=0, rerun_guard_verdict="no_target_rows", process_lock_id=""),
        }
        write_jsonl(paths["history_output_path"], apply_rows)
        write_json(paths["history_summary_path"], summary)
        write_json(paths["history_manifest_path"], manifest)
        print(f"[DONE] history_summary={paths['history_summary_path']}")
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
                category="exhibitions",
                guard_key=guard_key,
            )
            rerun_guard_verdict = "resume_existing_batch"
            process_lock_id = str(resume_guard["process_lock_id"])
            stamp = str(existing_state.get("stamp") or "").strip()
            if not stamp:
                raise RuntimeError("rerun_guard_missing_stamp")
            paths = build_bulk_artifact_paths("exhibitions", stamp=stamp, target_year=TARGET_YEAR, guard_key=guard_key)
            batch_job_id = str(existing_state.get("batch_job_id") or "").strip()
            batch_input_file_id = str(existing_state.get("batch_input_file_id") or "").strip()
            if not batch_job_id:
                raise RuntimeError("rerun_guard_missing_batch_job_id")
        else:
            process_lock_id = acquire_process_lock(probe_paths["lock_path"], category="exhibitions", guard_key=guard_key)
            release_lock_at_exit = True
            stamp = utc_now_compact()
            paths = build_bulk_artifact_paths("exhibitions", stamp=stamp, target_year=TARGET_YEAR, guard_key=guard_key)
            batch_job_id = ""
            batch_input_file_id = ""

        client = OpenAI(api_key=api_key)

        if rerun_guard_verdict == "new_run":
            batch_input_rows: list[dict[str, Any]] = []
            for task in pending_tasks:
                for field_name in EXHIBITIONS_ENRICHMENT_BATCH_FIELDS:
                    batch_input_rows.append(
                        build_batch_request_line(
                            custom_id=build_enrichment_field_custom_id(str(task["custom_id"]), field_name),
                            body=build_openai_request_body(
                                get_exhibitions_enrichment_model(field_name),
                                dict(task["working"]),
                            ),
                        )
                    )
            write_jsonl(paths["batch_input_path"], batch_input_rows)
            upload_file = upload_batch_input_file(client, paths["batch_input_path"])
            batch_input_file_id = str(upload_file.get("id") or "").strip()
            if not batch_input_file_id:
                raise RuntimeError("batch_input_file_id_missing")
            batch_state = create_responses_batch(client, input_file_id=batch_input_file_id, completion_window=completion_window, metadata={"category": "exhibitions", "target_year": str(TARGET_YEAR), "guard_key": guard_key[:32], "input_bundle_hash": input_bundle_hash[:32]})
            batch_job_id = str(batch_state.get("id") or "").strip()
            if not batch_job_id:
                raise RuntimeError("batch_job_id_missing")
            guard_state = {
                "category": "exhibitions",
                "target_year": TARGET_YEAR,
                "stamp": stamp,
                "guard_status": "in_progress",
                "guard_key": guard_key,
                "guard_state_path": str(paths["guard_state_path"]),
                "requests_path": str(REQUESTS_OUTPUT_PATH),
                "input_bundle_hash": input_bundle_hash,
                "enrich_model": enrich_model_fingerprint,
                "enrich_models_by_field": dict(EXHIBITIONS_ENRICHMENT_FIELD_MODELS),
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
            waiting_rows = apply_rows + [{"request_id": str(task["request_id"]), "fair_slug": str(task["fair_slug"]), "text_hash": str(task["text_hash"]), "source_url": str(task["source_url"]), "status": "BATCH_WAITING", "batch_job_id": batch_job_id, "batch_status": batch_status or "in_progress"} for task in pending_tasks]
            raw_state = summarize_raw_state(raw_rows_by_fair, raw_text_before)
            summary = {
                "started_at": str(guard_state.get("started_at") or started_at),
                "completed_at": "",
                "target_year": TARGET_YEAR,
                "requests_path": str(REQUESTS_OUTPUT_PATH),
                "apply_output_path": str(paths["history_output_path"]),
                "apply_summary_path": str(paths["history_summary_path"]),
                "apply_manifest_path": str(paths["history_manifest_path"]),
                "current_output_path": str(paths["current_output_path"]),
                "current_summary_path": str(paths["current_summary_path"]),
                "total_targeted": len(request_rows),
                "total_applied": 0,
                "warning_count": 0,
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
                "enrich_model": enrich_model_fingerprint,
                "enrich_models_by_field": dict(EXHIBITIONS_ENRICHMENT_FIELD_MODELS),
                "enrich_use_openai_batch": use_batch,
                "enrich_completion_window": completion_window,
                "enrich_prompt_version": ENRICH_PROMPT_VERSION,
                "openai_client_available": bool(api_key),
                **raw_state,
                **build_bulk_contract_fields(api_mode="openai_batch_apply", batch_used=True, batch_job_id=batch_job_id, input_bundle_hash=input_bundle_hash, target_rows=target_rows, updated_rows=0, rerun_guard_verdict=rerun_guard_verdict, process_lock_id=process_lock_id),
            }
            manifest = {
                "schema_name": "enrichment_bulk_apply_manifest",
                "category": "exhibitions",
                "guard_status": "in_progress",
                "batch_status": batch_status or "in_progress",
                "requests_path": str(REQUESTS_OUTPUT_PATH),
                "target_request_ids": target_request_ids,
                "request_counts": batch_state.get("request_counts") or {},
                "batch_input_file_id": batch_input_file_id,
                "batch_input_path": str(paths["batch_input_path"]),
                "enrich_model": enrich_model_fingerprint,
                "enrich_models_by_field": dict(EXHIBITIONS_ENRICHMENT_FIELD_MODELS),
                "enrich_prompt_version": ENRICH_PROMPT_VERSION,
                "enrich_completion_window": completion_window,
                "openai_client_available": bool(api_key),
                **build_bulk_contract_fields(api_mode="openai_batch_apply", batch_used=True, batch_job_id=batch_job_id, input_bundle_hash=input_bundle_hash, target_rows=target_rows, updated_rows=0, rerun_guard_verdict=rerun_guard_verdict, process_lock_id=process_lock_id),
            }
            persist_artifacts(history_output_path=paths["history_output_path"], history_summary_path=paths["history_summary_path"], history_manifest_path=paths["history_manifest_path"], apply_rows=waiting_rows, summary=summary, manifest=manifest, guard_state_path=paths["guard_state_path"], guard_state=guard_state)
            print(f"[HOLD] batch_job_id={batch_job_id} status={batch_status or 'in_progress'}")
            print(f"[HOLD] summary={paths['history_summary_path']}")
            return 0

        output_rows = download_batch_file_rows(client, str(batch_state.get("output_file_id") or ""))
        error_rows = download_batch_file_rows(client, str(batch_state.get("error_file_id") or ""))
        output_map = build_batch_row_map(output_rows)
        error_map = build_batch_row_map(error_rows)

        staged_updates: list[dict[str, Any]] = []
        warning_count = 0
        batch_result_rows: list[dict[str, Any]] = []
        parsed_success_rows = 0
        batch_error_count = 0

        for task in pending_tasks:
            request_id = str(task["custom_id"])
            parsed_fields: dict[str, str] = {}
            failure_status = ""
            failure_field = ""
            failure_error: Any = ""
            failure_status_code = 0

            for field_name in EXHIBITIONS_ENRICHMENT_BATCH_FIELDS:
                field_custom_id = build_enrichment_field_custom_id(request_id, field_name)
                result_row = output_map.get(field_custom_id)
                error_row = error_map.get(field_custom_id)
                if error_row:
                    failure_status = "BATCH_RESULT_FAILED"
                    failure_field = field_name
                    failure_error = error_row.get("error")
                    break
                if not result_row:
                    failure_status = "BATCH_RESULT_MISSING"
                    failure_field = field_name
                    break
                response_info = result_row.get("response")
                if not isinstance(response_info, dict):
                    failure_status = "BATCH_RESPONSE_MISSING"
                    failure_field = field_name
                    break
                status_code = int(response_info.get("status_code") or 0)
                response_body = response_info.get("body")
                if status_code != 200 or not isinstance(response_body, dict):
                    failure_status = "BATCH_REQUEST_FAILED"
                    failure_field = field_name
                    failure_status_code = status_code
                    failure_error = result_row.get("error")
                    break
                try:
                    headline_ja, summary_ja = parse_openai_response_body(response_body)
                except Exception as exc:
                    failure_status = "BATCH_PARSE_FAILED"
                    failure_field = field_name
                    failure_error = str(exc)
                    break

                parsed_value = {"headline_ja": headline_ja, "summary_ja": summary_ja}.get(field_name, "")
                parsed_value = str(parsed_value or "").strip()
                if not parsed_value:
                    failure_status = "BATCH_FIELD_EMPTY"
                    failure_field = field_name
                    failure_error = "parsed_field_empty"
                    break
                parsed_fields[field_name] = parsed_value

            if failure_status:
                if failure_status == "BATCH_RESULT_FAILED":
                    counters["batch_error_file_rows"] += 1
                elif failure_status == "BATCH_RESULT_MISSING":
                    counters["batch_result_missing"] += 1
                elif failure_status == "BATCH_RESPONSE_MISSING":
                    counters["batch_response_missing"] += 1
                elif failure_status == "BATCH_REQUEST_FAILED":
                    counters["batch_request_failed"] += 1
                elif failure_status == "BATCH_PARSE_FAILED":
                    counters["batch_parse_failed"] += 1
                elif failure_status == "BATCH_FIELD_EMPTY":
                    counters["batch_field_empty"] += 1
                batch_error_count += 1
                row_payload = {
                    "request_id": request_id,
                    "fair_slug": str(task["fair_slug"]),
                    "text_hash": str(task["text_hash"]),
                    "source_url": str(task["source_url"]),
                    "status": failure_status,
                    "batch_job_id": batch_job_id,
                    "batch_status": batch_status,
                    "failed_field": failure_field,
                    "error": failure_error,
                }
                if failure_status_code:
                    row_payload["status_code"] = failure_status_code
                batch_result_rows.append(row_payload)
                continue

            headline_ja = parsed_fields["headline_ja"]
            summary_ja = parsed_fields["summary_ja"]
            warnings = build_warnings(summary_ja=summary_ja, row=dict(task["working"]))
            warning_count += len(warnings)
            parsed_success_rows += 1
            staged_updates.append({"fair_slug": str(task["fair_slug"]), "row_index": int(task["row_index"]), "text_hash": str(task["text_hash"]), "source_url": str(task["source_url"]), "request_id": request_id, "headline_ja": headline_ja, "summary_ja": summary_ja, "warnings": warnings, "input_chars": int(task["input_chars"])})

        committed_rows = 0
        if batch_error_count == 0 and parsed_success_rows == target_rows:
            for update in staged_updates:
                row = raw_rows_by_fair[update["fair_slug"]][update["row_index"]]
                row["headline_ja"] = update["headline_ja"]
                row["summary_ja"] = update["summary_ja"]
                row["enrich_status"] = "applied"
                row["enrich_model"] = enrich_model_fingerprint
                row["enrich_models_by_field"] = dict(EXHIBITIONS_ENRICHMENT_FIELD_MODELS)
                row["enrich_mode"] = "openai_batch_apply"
                row["enrich_use_openai_batch"] = use_batch
                row["enrich_completion_window"] = completion_window
                row["enrich_prompt_version"] = ENRICH_PROMPT_VERSION
                row["enrich_input_text_hash"] = update["text_hash"]
                row["enrich_input_chars"] = update["input_chars"]
                row["enrich_summary_chars"] = len(update["summary_ja"])
                row["enrich_headline_chars"] = len(update["headline_ja"])
                row["enrich_generated_at"] = utc_now_iso()
                row["enrich_notes"] = ""
                row["enrich_batch_job_id"] = batch_job_id
                committed_rows += 1
                if len(update["headline_ja"]) > HEADLINE_MAX_CHARS:
                    counters["headline_over_limit"] += 1
                if len(update["summary_ja"]) > SUMMARY_MAX_CHARS:
                    counters["summary_over_limit"] += 1
                batch_result_rows.append({"request_id": update["request_id"], "record_id": str(row.get("record_id") or update["text_hash"]), "fair_slug": update["fair_slug"], "text_hash": update["text_hash"], "source_url": update["source_url"], "status": "APPLIED", "headline_ja": update["headline_ja"], "summary_ja": update["summary_ja"], "headline_ja_chars": len(update["headline_ja"]), "summary_ja_chars": len(update["summary_ja"]), "warnings": update["warnings"], "enrich_model": enrich_model_fingerprint, "enrich_models_by_field": dict(EXHIBITIONS_ENRICHMENT_FIELD_MODELS), "enrich_mode": "openai_batch_apply", "enrich_completion_window": completion_window, "enrich_prompt_version": ENRICH_PROMPT_VERSION, "enrich_input_text_hash": update["text_hash"], "enrich_batch_job_id": batch_job_id, "enrich_notes": ""})
            for fair_slug, raw_path in RAW_INPUT_PATHS.items():
                write_jsonl(raw_path, raw_rows_by_fair[fair_slug])
        else:
            for update in staged_updates:
                batch_result_rows.append({"request_id": update["request_id"], "fair_slug": update["fair_slug"], "text_hash": update["text_hash"], "source_url": update["source_url"], "status": "BATCH_RESULT_READY_UNCOMMITTED", "headline_ja": update["headline_ja"], "summary_ja": update["summary_ja"], "warnings": update["warnings"], "batch_job_id": batch_job_id, "batch_status": batch_status})

        apply_rows.extend(batch_result_rows)
        raw_state = summarize_raw_state(raw_rows_by_fair, raw_text_before)
        error_count = counters["skipped_invalid_fair_slug"] + counters["skipped_missing_text_hash"] + counters["skipped_target_row_not_found"] + counters["skipped_empty_text"] + batch_error_count
        summary = {
            "started_at": str(guard_state.get("started_at") or started_at),
            "completed_at": utc_now_iso(),
            "target_year": TARGET_YEAR,
            "requests_path": str(REQUESTS_OUTPUT_PATH),
            "apply_output_path": str(paths["history_output_path"]),
            "apply_summary_path": str(paths["history_summary_path"]),
            "apply_manifest_path": str(paths["history_manifest_path"]),
            "current_output_path": str(paths["current_output_path"]),
            "current_summary_path": str(paths["current_summary_path"]),
            "total_targeted": len(request_rows),
            "total_applied": committed_rows,
            "skipped_already_filled": counters["skipped_already_filled"],
            "skipped_hash_match": counters["skipped_hash_match"],
            "error_count": error_count,
            "warning_count": warning_count,
            "parsed_success_rows": parsed_success_rows,
            "batch_error_rows": batch_error_count,
            "batch_status": batch_status,
            "request_counts": batch_state.get("request_counts") or {},
            "promoted_to_current": False,
            "promote_verdict": "",
            "guard_state_path": str(paths["guard_state_path"]),
            "guard_key": guard_key,
            "target_request_ids_count": len(target_request_ids),
            "target_request_ids": target_request_ids,
            "counters": dict(counters),
            "enrich_model": enrich_model_fingerprint,
            "enrich_models_by_field": dict(EXHIBITIONS_ENRICHMENT_FIELD_MODELS),
            "enrich_use_openai_batch": use_batch,
            "enrich_completion_window": completion_window,
            "enrich_prompt_version": ENRICH_PROMPT_VERSION,
            "openai_client_available": bool(api_key),
            **raw_state,
            **build_bulk_contract_fields(api_mode="openai_batch_apply", batch_used=True, batch_job_id=batch_job_id, input_bundle_hash=input_bundle_hash, target_rows=target_rows, updated_rows=committed_rows, rerun_guard_verdict=rerun_guard_verdict, process_lock_id=process_lock_id),
        }
        manifest = {
            "schema_name": "enrichment_bulk_apply_manifest",
            "category": "exhibitions",
            "guard_status": "completed" if committed_rows == target_rows and error_count == 0 else "terminal_failed",
            "batch_status": batch_status,
            "requests_path": str(REQUESTS_OUTPUT_PATH),
            "target_request_ids": target_request_ids,
            "request_counts": batch_state.get("request_counts") or {},
            "batch_input_file_id": batch_input_file_id,
            "batch_output_file_id": str(batch_state.get("output_file_id") or ""),
            "batch_error_file_id": str(batch_state.get("error_file_id") or ""),
            "batch_input_path": str(paths["batch_input_path"]),
            "enrich_model": enrich_model_fingerprint,
            "enrich_models_by_field": dict(EXHIBITIONS_ENRICHMENT_FIELD_MODELS),
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
            category="exhibitions",
            target_year=TARGET_YEAR,
            requests_path=REQUESTS_OUTPUT_PATH,
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
            print(f"[DONE] total_targeted={summary['total_targeted']} total_applied={summary['total_applied']}")
            print(f"[DONE] history_summary={paths['history_summary_path']}")
            print(f"[DONE] current_summary={paths['current_summary_path']}")
            return 0
        print(f"[BLOCKED] promote_verdict={promote_verdict}")
        print(f"[BLOCKED] history_summary={paths['history_summary_path']}")
        return 1
    finally:
        if release_lock_at_exit:
            release_process_lock(probe_paths["lock_path"])


if __name__ == "__main__":
    raise SystemExit(main())
