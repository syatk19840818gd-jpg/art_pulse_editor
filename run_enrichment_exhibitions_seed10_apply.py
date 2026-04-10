#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import os
import re
import unicodedata
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from enrichment_batch_common import (
    BULK_LIFECYCLE_MODES,
    FAILED_BATCH_STATUSES,
    TERMINAL_BATCH_STATUSES,
    acquire_process_lock,
    build_enrichment_request_custom_id,
    build_batch_request_line,
    build_bulk_artifact_paths,
    build_bulk_contract_fields,
    build_bulk_guard_key,
    build_bulk_lifecycle_fields,
    build_input_bundle_hash,
    create_responses_batch,
    download_batch_file_rows,
    finalize_runtime_requests_retention,
    load_guard_state,
    normalize_bulk_lifecycle_mode,
    normalize_requested_enrichment_fields,
    read_jsonl,
    release_process_lock,
    resolve_batch_request_model,
    resolve_optional_io_root,
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
)
from phase2_art_pulse_config import get_current_raw_paths, promote_history_file_to_current
from run_enrichment_exhibitions_preview import (
    ENRICH_BATCH_COMPLETION_WINDOW,
    ENRICH_PROMPT_VERSION,
    HEADLINE_MAX_CHARS,
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
    parser.add_argument(
        "--allowlist-csv",
        default="",
        help="optional allowlist CSV with fair_slug and gallery_name_en columns; out-of-scope requests are skipped",
    )
    parser.add_argument(
        "--approval-token",
        default="",
        help="required for live OpenAI Batch execution; preflight-only remains available without approval",
    )
    parser.add_argument(
        "--io-root",
        default="",
        help="optional trial I/O root; when set, requests/artifacts/raw writeback resolve under this root",
    )
    parser.add_argument(
        "--lifecycle-mode",
        choices=BULK_LIFECYCLE_MODES,
        default="auto",
        help="batch lifecycle mode: auto|submit_only|resume_or_check (default: auto)",
    )
    return parser.parse_args()


def require_live_batch_approval(args: argparse.Namespace) -> None:
    if args.preflight_only:
        return
    if str(args.approval_token or "").strip():
        return
    raise RuntimeError(
        "approval_required_for_openai_batch_apply:"
        "pass --approval-token <user-approved-note>; use --preflight-only for offline-only diagnosis"
    )


def normalize_gallery_scope_name(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value or "").strip())
    text = re.sub(r"\s+", " ", text)
    return text.casefold()


def load_gallery_allowlist(path_text: str) -> set[tuple[str, str]]:
    path = Path(path_text)
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Missing allowlist CSV: {path}")
    out: set[tuple[str, str]] = set()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            fair_slug = str(row.get("fair_slug") or row.get("fair") or "").strip().lower().replace("-", "_")
            gallery_name = str(row.get("gallery_name_en") or row.get("gallery_name") or "").strip()
            if not fair_slug or not gallery_name:
                continue
            out.add((fair_slug, normalize_gallery_scope_name(gallery_name)))
    if not out:
        raise RuntimeError(f"No valid allowlist rows found: {path}")
    return out


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


def load_requests(*, requests_path: Path, io_root: Path | None) -> list[dict[str, Any]]:
    if requests_path.exists():
        return read_jsonl(requests_path)
    if io_root is not None:
        raise FileNotFoundError(f"Missing trial exhibitions requests path: {requests_path}")
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


def commit_successful_exhibitions_enrichment_updates(
    *,
    staged_updates: list[dict[str, Any]],
    raw_rows_by_fair: dict[str, list[dict[str, Any]]],
    raw_input_paths: dict[str, Path],
    batch_result_rows: list[dict[str, Any]],
    counters: Counter[str],
    batch_job_id: str,
    enrich_model_fingerprint: str,
    completion_window: str,
    use_batch: str,
) -> int:
    committed_rows = 0
    dirty_fairs: set[str] = set()
    for update in staged_updates:
        fair_slug = str(update["fair_slug"])
        row = raw_rows_by_fair[fair_slug][int(update["row_index"])]
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
        dirty_fairs.add(fair_slug)
        if len(update["headline_ja"]) > HEADLINE_MAX_CHARS:
            counters["headline_over_limit"] += 1
        if len(update["summary_ja"]) > SUMMARY_MAX_CHARS:
            counters["summary_over_limit"] += 1
        batch_result_rows.append(
            {
                "request_id": update["request_id"],
                "record_id": str(row.get("record_id") or update["text_hash"]),
                "fair_slug": fair_slug,
                "text_hash": update["text_hash"],
                "source_url": update["source_url"],
                "status": "APPLIED",
                "headline_ja": update["headline_ja"],
                "summary_ja": update["summary_ja"],
                "headline_ja_chars": len(update["headline_ja"]),
                "summary_ja_chars": len(update["summary_ja"]),
                "warnings": update["warnings"],
                "enrich_model": enrich_model_fingerprint,
                "enrich_models_by_field": dict(EXHIBITIONS_ENRICHMENT_FIELD_MODELS),
                "enrich_mode": "openai_batch_apply",
                "enrich_completion_window": completion_window,
                "enrich_prompt_version": ENRICH_PROMPT_VERSION,
                "enrich_input_text_hash": update["text_hash"],
                "enrich_batch_job_id": batch_job_id,
                "enrich_notes": "",
            }
        )

    for fair_slug in sorted(dirty_fairs):
        write_jsonl(raw_input_paths[fair_slug], raw_rows_by_fair[fair_slug])
    return committed_rows


def main() -> int:
    args = parse_args()
    started_at = utc_now_iso()
    require_live_batch_approval(args)
    lifecycle_mode = normalize_bulk_lifecycle_mode(args.lifecycle_mode)
    io_root = resolve_optional_io_root(args.io_root)
    requests_path = resolve_runtime_requests_path("exhibitions", target_year=TARGET_YEAR, root=io_root)
    raw_input_paths = get_current_raw_paths("exhibitions", TARGET_YEAR, root=io_root)
    allow_current_promote = io_root is None

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

    request_rows = load_requests(requests_path=requests_path, io_root=io_root)
    allowlist = load_gallery_allowlist(args.allowlist_csv) if str(args.allowlist_csv or "").strip() else set()
    allowlist_enabled = bool(allowlist)
    raw_rows_by_fair: dict[str, list[dict[str, Any]]] = {}
    raw_text_before: dict[str, list[str]] = {}
    row_index_by_fair: dict[str, dict[tuple[str, str], int]] = {}
    for fair_slug, raw_path in raw_input_paths.items():
        rows = read_jsonl(raw_path)
        raw_rows_by_fair[fair_slug] = rows
        raw_text_before[fair_slug] = [str(r.get("text") or "") for r in rows]
        row_index_by_fair[fair_slug] = build_row_index(rows)

    counters: Counter[str] = Counter()
    apply_rows: list[dict[str, Any]] = []
    pending_tasks: list[dict[str, Any]] = []
    scoped_request_rows = 0

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
        gallery_name = str(
            row.get("gallery_name_en")
            or row.get("gallery_name")
            or req.get("gallery_name_en")
            or req.get("gallery_name")
            or ""
        ).strip()
        if allowlist_enabled:
            key = (fair_slug.lower().replace("-", "_"), normalize_gallery_scope_name(gallery_name))
            if key not in allowlist:
                counters["skipped_out_of_scope_allowlist"] += 1
                apply_rows.append(
                    {
                        "request_id": request_id,
                        "fair_slug": fair_slug,
                        "text_hash": text_hash,
                        "source_url": source_url,
                        "gallery_name": gallery_name,
                        "status": "SKIPPED_OUT_OF_SCOPE_ALLOWLIST",
                    }
                )
                continue
        scoped_request_rows += 1
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
        working["gallery_name"] = gallery_name
        requested_fields = normalize_requested_enrichment_fields(
            req.get("needs_fields"),
            EXHIBITIONS_ENRICHMENT_BATCH_FIELDS,
        )
        working["needs_fields"] = list(requested_fields)
        pending_tasks.append(
            {
                "custom_id": request_id,
                "request_id": request_id,
                "fair_slug": fair_slug,
                "text_hash": text_hash,
                "source_url": source_url,
                "row_index": idx,
                "working": working,
                "requested_fields": list(requested_fields),
                "model": resolve_batch_request_model(
                    request_id=request_id,
                    requested_fields=requested_fields,
                    field_models=EXHIBITIONS_ENRICHMENT_FIELD_MODELS,
                ),
                "input_chars": len(text),
            }
        )

    target_rows = len(pending_tasks)
    input_bundle_hash = build_input_bundle_hash(requests_path)
    guard_key = build_bulk_guard_key(requests_path=requests_path, input_bundle_hash=input_bundle_hash, prompt_version=ENRICH_PROMPT_VERSION, model=enrich_model_fingerprint, target_year=TARGET_YEAR)
    probe_paths = build_bulk_artifact_paths("exhibitions", stamp=utc_now_compact(), target_year=TARGET_YEAR, guard_key=guard_key, root=io_root)
    prereq = validate_bulk_batch_prerequisites(api_key=api_key, use_batch=use_batch, target_rows=target_rows)
    target_request_ids = [build_enrichment_request_custom_id(str(task["custom_id"])) for task in pending_tasks]

    if args.preflight_only:
        print(
            {
                "status": "ok" if prereq["ok"] else "blocked",
                "category": "exhibitions",
                "execution_mode": "bulk_apply",
                "lifecycle_mode": lifecycle_mode,
                "batch_required": True,
                "direct_openai_allowed": False,
                "requests_path": str(requests_path),
                "input_bundle_hash": input_bundle_hash,
                "guard_key": guard_key,
                "guard_state_path": str(probe_paths["guard_state_path"]),
                "target_rows": target_rows,
                "total_requests": len(request_rows),
                "allowlist_enabled": allowlist_enabled,
                "allowlist_path": str(args.allowlist_csv or ""),
                "allowlist_entry_count": len(allowlist),
                "scoped_request_rows": scoped_request_rows,
                "out_of_scope_skipped": counters["skipped_out_of_scope_allowlist"],
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
        paths = build_bulk_artifact_paths("exhibitions", stamp=stamp, target_year=TARGET_YEAR, guard_key=guard_key, root=io_root)
        raw_state = summarize_raw_state(raw_rows_by_fair, raw_text_before)
        summary = {
            "started_at": started_at,
            "completed_at": utc_now_iso(),
            "target_year": TARGET_YEAR,
            "requests_path": str(requests_path),
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
            **build_bulk_lifecycle_fields(
                lifecycle_mode=lifecycle_mode,
                batch_status="not_submitted",
                batch_job_id="",
                materialized=False,
            ),
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
            **build_bulk_lifecycle_fields(
                lifecycle_mode=lifecycle_mode,
                batch_status="not_submitted",
                batch_job_id="",
                materialized=False,
            ),
            "requests_path": str(requests_path),
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
            paths = build_bulk_artifact_paths("exhibitions", stamp=stamp, target_year=TARGET_YEAR, guard_key=guard_key, root=io_root)
            batch_job_id = str(existing_state.get("batch_job_id") or "").strip()
            batch_input_file_id = str(existing_state.get("batch_input_file_id") or "").strip()
            if not batch_job_id:
                raise RuntimeError("rerun_guard_missing_batch_job_id")
        else:
            if lifecycle_mode == "resume_or_check":
                raise RuntimeError("resume_or_check_requires_existing_in_progress_batch")
            process_lock_id = acquire_process_lock(probe_paths["lock_path"], category="exhibitions", guard_key=guard_key)
            release_lock_at_exit = True
            stamp = utc_now_compact()
            paths = build_bulk_artifact_paths("exhibitions", stamp=stamp, target_year=TARGET_YEAR, guard_key=guard_key, root=io_root)
            batch_job_id = ""
            batch_input_file_id = ""

        client = OpenAI(api_key=api_key)

        if rerun_guard_verdict == "new_run":
            batch_input_rows: list[dict[str, Any]] = []
            for task in pending_tasks:
                batch_input_rows.append(
                    build_batch_request_line(
                        custom_id=build_enrichment_request_custom_id(str(task["custom_id"])),
                        body=build_openai_request_body(
                            str(task["model"]),
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
                "requests_path": str(requests_path),
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
                "lifecycle_mode": lifecycle_mode,
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

        if rerun_guard_verdict == "new_run" and lifecycle_mode != "submit_only":
            batch_state = retrieve_batch(client, batch_job_id)

        batch_status = str(batch_state.get("status") or "").strip()
        lifecycle_fields = build_bulk_lifecycle_fields(
            lifecycle_mode=lifecycle_mode,
            batch_status=batch_status,
            batch_job_id=batch_job_id,
            materialized=False,
        )
        guard_state["batch_status"] = batch_status
        guard_state["batch_job_id"] = batch_job_id
        guard_state["batch_input_file_id"] = batch_input_file_id
        guard_state["request_counts"] = batch_state.get("request_counts") or {}
        guard_state["lifecycle_mode"] = lifecycle_mode
        guard_state["lifecycle_phase"] = lifecycle_fields["lifecycle_phase"]
        guard_state["needs_resume"] = lifecycle_fields["needs_resume"]
        guard_state["terminal_ready"] = lifecycle_fields["terminal_ready"]
        guard_state["materialization_ready"] = lifecycle_fields["materialization_ready"]
        guard_state["updated_at"] = utc_now_iso()

        if batch_status in FAILED_BATCH_STATUSES:
            failed_rows = apply_rows + [
                {
                    "request_id": str(task["request_id"]),
                    "fair_slug": str(task["fair_slug"]),
                    "text_hash": str(task["text_hash"]),
                    "source_url": str(task["source_url"]),
                    "status": "BATCH_TERMINAL_FAILED",
                    "batch_job_id": batch_job_id,
                    "batch_status": batch_status,
                }
                for task in pending_tasks
            ]
            raw_state = summarize_raw_state(raw_rows_by_fair, raw_text_before)
            summary = {
                "started_at": str(guard_state.get("started_at") or started_at),
                "completed_at": utc_now_iso(),
                "target_year": TARGET_YEAR,
                "requests_path": str(requests_path),
                "apply_output_path": str(paths["history_output_path"]),
                "apply_summary_path": str(paths["history_summary_path"]),
                "apply_manifest_path": str(paths["history_manifest_path"]),
                "current_output_path": str(paths["current_output_path"]),
                "current_summary_path": str(paths["current_summary_path"]),
                "total_targeted": len(request_rows),
                "total_applied": 0,
                "warning_count": 0,
                "error_count": 0,
                "batch_status": batch_status,
                **lifecycle_fields,
                "promoted_to_current": False,
                "promote_verdict": "promote_blocked_batch_terminal_failed",
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
                "guard_status": "terminal_failed",
                "batch_status": batch_status,
                **lifecycle_fields,
                "requests_path": str(requests_path),
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
            guard_state["guard_status"] = "terminal_failed"
            guard_state["completed_at"] = summary["completed_at"]
            guard_state["updated_at"] = summary["completed_at"]
            persist_artifacts(history_output_path=paths["history_output_path"], history_summary_path=paths["history_summary_path"], history_manifest_path=paths["history_manifest_path"], apply_rows=failed_rows, summary=summary, manifest=manifest, guard_state_path=paths["guard_state_path"], guard_state=guard_state)
            release_process_lock(paths["lock_path"])
            release_lock_at_exit = False
            retention_info = finalize_runtime_requests_retention(
                category="exhibitions",
                target_year=TARGET_YEAR,
                requests_path=requests_path,
                summary=summary,
                guard_state_path=paths["guard_state_path"],
                lock_path=paths["lock_path"],
                root=io_root,
            )
            summary.update(retention_info)
            manifest.update(retention_info)
            write_json(paths["history_summary_path"], summary)
            write_json(paths["history_manifest_path"], manifest)
            print(f"[FAILED] batch_job_id={batch_job_id} status={batch_status}")
            print(f"[FAILED] history_summary={paths['history_summary_path']}")
            return 1

        if lifecycle_mode == "submit_only" or batch_status not in TERMINAL_BATCH_STATUSES:
            waiting_status = batch_status or ("submitted_or_validating" if lifecycle_mode == "submit_only" else "in_progress")
            waiting_row_status = "BATCH_SUBMITTED" if lifecycle_mode == "submit_only" else "BATCH_WAITING"
            promote_verdict = (
                "promote_pending_materialization_resume_required"
                if lifecycle_fields["materialization_ready"]
                else "promote_pending_batch_resume_required"
            )
            waiting_rows = apply_rows + [{"request_id": str(task["request_id"]), "fair_slug": str(task["fair_slug"]), "text_hash": str(task["text_hash"]), "source_url": str(task["source_url"]), "status": waiting_row_status, "batch_job_id": batch_job_id, "batch_status": waiting_status} for task in pending_tasks]
            raw_state = summarize_raw_state(raw_rows_by_fair, raw_text_before)
            summary = {
                "started_at": str(guard_state.get("started_at") or started_at),
                "completed_at": "",
                "target_year": TARGET_YEAR,
                "requests_path": str(requests_path),
                "apply_output_path": str(paths["history_output_path"]),
                "apply_summary_path": str(paths["history_summary_path"]),
                "apply_manifest_path": str(paths["history_manifest_path"]),
                "current_output_path": str(paths["current_output_path"]),
                "current_summary_path": str(paths["current_summary_path"]),
                "total_targeted": len(request_rows),
                "total_applied": 0,
                "warning_count": 0,
                "error_count": 0,
                "batch_status": waiting_status,
                **build_bulk_lifecycle_fields(
                    lifecycle_mode=lifecycle_mode,
                    batch_status=waiting_status,
                    batch_job_id=batch_job_id,
                    materialized=False,
                ),
                "promoted_to_current": False,
                "promote_verdict": promote_verdict,
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
                "batch_status": waiting_status,
                **build_bulk_lifecycle_fields(
                    lifecycle_mode=lifecycle_mode,
                    batch_status=waiting_status,
                    batch_job_id=batch_job_id,
                    materialized=False,
                ),
                "requests_path": str(requests_path),
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
            print(f"[HOLD] batch_job_id={batch_job_id} status={waiting_status}")
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
            requested_fields = normalize_requested_enrichment_fields(
                task.get("requested_fields"),
                EXHIBITIONS_ENRICHMENT_BATCH_FIELDS,
            )
            parsed_fields: dict[str, str] = {}
            failure_status = ""
            failure_field = ""
            failure_error: Any = ""
            failure_status_code = 0
            result_row = output_map.get(request_id)
            error_row = error_map.get(request_id)
            if error_row:
                failure_status = "BATCH_RESULT_FAILED"
                failure_field = ",".join(requested_fields)
                failure_error = error_row.get("error")
            elif not result_row:
                failure_status = "BATCH_RESULT_MISSING"
                failure_field = ",".join(requested_fields)
            else:
                response_info = result_row.get("response")
                if not isinstance(response_info, dict):
                    failure_status = "BATCH_RESPONSE_MISSING"
                    failure_field = ",".join(requested_fields)
                else:
                    status_code = int(response_info.get("status_code") or 0)
                    response_body = response_info.get("body")
                    if status_code != 200 or not isinstance(response_body, dict):
                        failure_status = "BATCH_REQUEST_FAILED"
                        failure_field = ",".join(requested_fields)
                        failure_error = result_row.get("error")
                        failure_status_code = status_code
                    else:
                        try:
                            headline_ja, summary_ja = parse_openai_response_body(response_body)
                        except Exception as exc:
                            failure_status = "BATCH_PARSE_FAILED"
                            failure_field = ",".join(requested_fields)
                            failure_error = str(exc)
                        else:
                            parsed_fields = {
                                "headline_ja": str(headline_ja or "").strip(),
                                "summary_ja": str(summary_ja or "").strip(),
                            }
                            missing_fields = [
                                field_name
                                for field_name in requested_fields
                                if not str(parsed_fields.get(field_name) or "").strip()
                            ]
                            if missing_fields:
                                failure_status = "BATCH_FIELD_EMPTY"
                                failure_field = ",".join(missing_fields)
                                failure_error = f"missing_fields:{','.join(missing_fields)}"

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
        if staged_updates:
            committed_rows = commit_successful_exhibitions_enrichment_updates(
                staged_updates=staged_updates,
                raw_rows_by_fair=raw_rows_by_fair,
                raw_input_paths=raw_input_paths,
                batch_result_rows=batch_result_rows,
                counters=counters,
                batch_job_id=batch_job_id,
                enrich_model_fingerprint=enrich_model_fingerprint,
                completion_window=completion_window,
                use_batch=use_batch,
            )

        apply_rows.extend(batch_result_rows)
        raw_state = summarize_raw_state(raw_rows_by_fair, raw_text_before)
        status_counts = Counter(str(row.get("status") or "").strip() for row in batch_result_rows)
        parse_failed_rows = int(status_counts.get("BATCH_PARSE_FAILED", 0))
        ready_uncommitted_rows = int(status_counts.get("BATCH_RESULT_READY_UNCOMMITTED", 0))
        error_count = counters["skipped_invalid_fair_slug"] + counters["skipped_missing_text_hash"] + counters["skipped_target_row_not_found"] + counters["skipped_empty_text"] + batch_error_count
        partial_success = committed_rows > 0 and error_count > 0
        apply_completed_ok = batch_status == "completed" and committed_rows > 0 and ready_uncommitted_rows == 0
        summary = {
            "started_at": str(guard_state.get("started_at") or started_at),
            "completed_at": utc_now_iso(),
            "target_year": TARGET_YEAR,
            "requests_path": str(requests_path),
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
            "parse_failed_rows": parse_failed_rows,
            "ready_uncommitted_rows": ready_uncommitted_rows,
            "partial_success": partial_success,
            "batch_status": batch_status,
            **build_bulk_lifecycle_fields(
                lifecycle_mode=lifecycle_mode,
                batch_status=batch_status,
                batch_job_id=batch_job_id,
                materialized=True,
            ),
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
            "guard_status": "completed" if apply_completed_ok else "terminal_failed",
            "batch_status": batch_status,
            **build_bulk_lifecycle_fields(
                lifecycle_mode=lifecycle_mode,
                batch_status=batch_status,
                batch_job_id=batch_job_id,
                materialized=True,
            ),
            "requests_path": str(requests_path),
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
            "parse_failed_rows": parse_failed_rows,
            "ready_uncommitted_rows": ready_uncommitted_rows,
            "partial_success": partial_success,
            **build_bulk_contract_fields(api_mode="openai_batch_apply", batch_used=True, batch_job_id=batch_job_id, input_bundle_hash=input_bundle_hash, target_rows=target_rows, updated_rows=committed_rows, rerun_guard_verdict=rerun_guard_verdict, process_lock_id=process_lock_id),
        }
        if allow_current_promote:
            promote_ok, promote_verdict = validate_bulk_promote_summary(summary)
        else:
            promote_ok, promote_verdict = False, "promote_skipped_non_current_root"
        summary["promote_verdict"] = promote_verdict
        guard_state["guard_status"] = "completed" if apply_completed_ok else "terminal_failed"
        guard_state["updated_rows"] = committed_rows
        guard_state["batch_status"] = batch_status
        guard_state["completed_at"] = utc_now_iso()
        guard_state["updated_at"] = guard_state["completed_at"]
        guard_state.update(
            build_bulk_lifecycle_fields(
                lifecycle_mode=lifecycle_mode,
                batch_status=batch_status,
                batch_job_id=batch_job_id,
                materialized=True,
            )
        )
        persist_artifacts(history_output_path=paths["history_output_path"], history_summary_path=paths["history_summary_path"], history_manifest_path=paths["history_manifest_path"], apply_rows=apply_rows, summary=summary, manifest=manifest, guard_state_path=paths["guard_state_path"], guard_state=guard_state)
        release_lock_at_exit = True
        if allow_current_promote and promote_ok:
            promote_history_file_to_current(paths["history_output_path"], paths["current_output_path"])
            promote_history_file_to_current(paths["history_summary_path"], paths["current_summary_path"])
            summary["promoted_to_current"] = True
        release_process_lock(paths["lock_path"])
        release_lock_at_exit = False

        retention_info = finalize_runtime_requests_retention(
            category="exhibitions",
            target_year=TARGET_YEAR,
            requests_path=requests_path,
            summary=summary,
            guard_state_path=paths["guard_state_path"],
            lock_path=paths["lock_path"],
            root=io_root,
        )
        summary.update(retention_info)
        manifest.update(retention_info)
        write_json(paths["history_summary_path"], summary)
        write_json(paths["history_manifest_path"], manifest)

        if allow_current_promote and promote_ok:
            write_json(paths["current_summary_path"], summary)
            print(f"[DONE] total_targeted={summary['total_targeted']} total_applied={summary['total_applied']}")
            print(f"[DONE] history_summary={paths['history_summary_path']}")
            print(f"[DONE] current_summary={paths['current_summary_path']}")
            return 0
        if apply_completed_ok:
            print(f"[DONE] total_targeted={summary['total_targeted']} total_applied={summary['total_applied']}")
            print(f"[DONE] history_summary={paths['history_summary_path']}")
            if not allow_current_promote:
                print("[DONE] current_promotion=skipped_non_current_root")
            return 0
        print(f"[BLOCKED] promote_verdict={promote_verdict}")
        print(f"[BLOCKED] history_summary={paths['history_summary_path']}")
        return 1
    finally:
        if release_lock_at_exit:
            release_process_lock(probe_paths["lock_path"])


if __name__ == "__main__":
    raise SystemExit(main())
