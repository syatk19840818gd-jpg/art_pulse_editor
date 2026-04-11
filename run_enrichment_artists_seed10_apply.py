#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import unicodedata
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

from dotenv import load_dotenv
from openai import OpenAI

from gallery_skip_registry import (
    SKIPPED_GALLERIES_REGISTRY_PATH,
    build_skip_lookup,
    find_skip_entry,
    load_skip_registry_entries,
)
from enrichment_batch_common import (
    BULK_LIFECYCLE_MODES,
    FAILED_BATCH_STATUSES,
    TERMINAL_BATCH_STATUSES,
    acquire_process_lock,
    build_materialized_current_runtime_rows,
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
    is_optional_output_enabled,
    load_enrichment_history_apply_rows,
    load_guard_state,
    normalize_bulk_lifecycle_mode,
    normalize_requested_enrichment_fields,
    read_jsonl,
    release_process_lock,
    resolve_batch_request_model,
    resolve_optional_io_root,
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
    ARTISTS_ENRICHMENT_BATCH_FIELDS,
    ARTISTS_ENRICHMENT_FIELD_MODELS,
    ENRICH_USE_OPENAI_BATCH_DEFAULT,
    get_enrichment_model_fingerprint,
)
from run_enrichment_artists_preview import (
    ARTIST_NAME_KANA_MAX_CHARS,
    ENRICH_BATCH_COMPLETION_WINDOW,
    ENRICH_PROMPT_VERSION,
    HEADLINE_MAX_CHARS,
    RAG_CATEGORY,
    SUMMARY_MAX_CHARS,
    build_openai_request_body,
    build_warnings,
    ensure_requests_output_path,
    infer_artist_name_en,
    parse_openai_response_body,
    resolve_artists_enrichment_io_paths,
)

TARGET_YEAR = 2025
# Request-id specific carry-forward is intentionally disabled in the baseline.
# Localized repair must go through explicit offline diagnosis plus approved promote flow.
LOCALIZED_REPAIR_TARGET_REQUEST_IDS: set[str] = set()
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
    parser.add_argument(
        "--approval-token",
        default="",
        help="required for live OpenAI Batch execution; preflight-only remains available without approval",
    )
    parser.add_argument(
        "--allowlist-csv",
        default="",
        help="optional allowlist CSV with fair_slug and gallery_name_en columns; out-of-scope requests are skipped",
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


def load_skip_lookup() -> dict[str, dict[Any, Any]]:
    return build_skip_lookup(load_skip_registry_entries(SKIPPED_GALLERIES_REGISTRY_PATH))


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


def load_requests(*, io_root: Path | None = None) -> list[dict[str, Any]]:
    requests_path = ensure_requests_output_path(io_root=io_root)
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


def artist_runtime_key_from_raw(row: dict[str, Any]) -> tuple[str, str, str] | None:
    fair_slug = str(row.get("fair_slug") or "").strip()
    text_hash = str(row.get("text_hash") or "").strip()
    source_url_norm = normalize_source_url_for_match(str(row.get("source_url") or ""))
    if not fair_slug or not text_hash or not source_url_norm:
        return None
    return fair_slug, text_hash, source_url_norm


def artist_runtime_key_from_enrichment(row: dict[str, Any]) -> tuple[str, str, str] | None:
    fair_slug = str(row.get("fair_slug") or "").strip()
    text_hash = str(row.get("text_hash") or "").strip()
    source_url_norm = normalize_source_url_for_match(str(row.get("source_url") or ""))
    if not fair_slug or not text_hash or not source_url_norm:
        return None
    return fair_slug, text_hash, source_url_norm


def raw_artist_has_enrichment_values(row: dict[str, Any]) -> bool:
    return any(str(row.get(key) or "").strip() for key in ("headline_ja", "summary_ja", "artist_name_kana"))


def build_artist_runtime_row_from_raw(
    raw_row: dict[str, Any],
    *,
    base_row: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base = dict(base_row or {})
    headline_ja = str(raw_row.get("headline_ja") or "").strip()
    summary_ja = str(raw_row.get("summary_ja") or "").strip()
    artist_name_kana = str(raw_row.get("artist_name_kana") or "").strip()
    enrich_models_by_field = raw_row.get("enrich_models_by_field")
    if not isinstance(enrich_models_by_field, dict):
        enrich_models_by_field = base.get("enrich_models_by_field")
    if not isinstance(enrich_models_by_field, dict):
        enrich_models_by_field = {}
    warnings = base.get("warnings")
    if not isinstance(warnings, list):
        warnings = []
    out = dict(base)
    out.update(
        {
            "request_id": str(base.get("request_id") or ""),
            "fair_slug": str(raw_row.get("fair_slug") or base.get("fair_slug") or "").strip(),
            "text_hash": str(raw_row.get("text_hash") or base.get("text_hash") or "").strip(),
            "source_url": str(raw_row.get("source_url") or base.get("source_url") or "").strip(),
            "status": "APPLIED",
            "headline_ja": headline_ja,
            "summary_ja": summary_ja,
            "artist_name_kana": artist_name_kana,
            "headline_ja_chars": len(headline_ja),
            "summary_ja_chars": len(summary_ja),
            "artist_name_kana_chars": len(artist_name_kana),
            "warnings": warnings,
            "enrich_model": str(raw_row.get("enrich_model") or base.get("enrich_model") or "").strip(),
            "enrich_models_by_field": enrich_models_by_field,
            "enrich_mode": str(raw_row.get("enrich_mode") or base.get("enrich_mode") or "current_raw_carry_forward").strip(),
            "enrich_use_openai_batch": str(
                raw_row.get("enrich_use_openai_batch") or base.get("enrich_use_openai_batch") or ""
            ).strip(),
            "enrich_completion_window": str(
                raw_row.get("enrich_completion_window") or base.get("enrich_completion_window") or ""
            ).strip(),
            "enrich_prompt_version": str(
                raw_row.get("enrich_prompt_version") or base.get("enrich_prompt_version") or ""
            ).strip(),
            "enrich_input_text_hash": str(
                raw_row.get("enrich_input_text_hash") or raw_row.get("text_hash") or base.get("enrich_input_text_hash") or ""
            ).strip(),
            "enrich_batch_job_id": str(
                raw_row.get("enrich_batch_job_id") or base.get("enrich_batch_job_id") or ""
            ).strip(),
            "enrich_notes": str(raw_row.get("enrich_notes") or base.get("enrich_notes") or "").strip(),
        }
    )
    return out


def materialize_artist_current_runtime_row(
    raw_row: dict[str, Any],
    current_row: dict[str, Any] | None,
    history_row: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, str]:
    if raw_artist_has_enrichment_values(raw_row):
        return build_artist_runtime_row_from_raw(raw_row, base_row=current_row or history_row), "raw"
    if current_row is not None:
        return dict(current_row), "current"
    if history_row is not None:
        return dict(history_row), "history"
    return None, ""


def build_artist_current_runtime_rows(
    *,
    raw_rows_by_fair: dict[str, list[dict[str, Any]]],
    current_output_path: Path,
    current_rows_override: list[dict[str, Any]] | None = None,
    io_root: Path | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raw_rows_in_order: list[dict[str, Any]] = []
    for fair_slug in sorted(raw_rows_by_fair):
        raw_rows_in_order.extend(raw_rows_by_fair[fair_slug])
    current_rows = current_rows_override if current_rows_override is not None else (
        read_jsonl(current_output_path) if current_output_path.exists() else []
    )
    history_rows = load_enrichment_history_apply_rows("artists", target_year=TARGET_YEAR, root=io_root)
    return build_materialized_current_runtime_rows(
        raw_rows_in_order=raw_rows_in_order,
        current_rows=current_rows,
        history_rows=history_rows,
        raw_key_builder=artist_runtime_key_from_raw,
        enrichment_key_builder=artist_runtime_key_from_enrichment,
        materialize_row=materialize_artist_current_runtime_row,
    )


def diagnostic_path_for_apply(paths: dict[str, Path]) -> Path:
    summary_path = paths["history_summary_path"]
    replaced = summary_path.name.replace("_apply_summary_", "_apply_diagnostics_")
    if replaced == summary_path.name:
        replaced = f"{summary_path.stem}_diagnostics{summary_path.suffix}"
    return summary_path.with_name(replaced)


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


def commit_successful_artist_enrichment_updates(
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
        row["artist_name_kana"] = update["artist_name_kana"]
        row["enrich_status"] = "applied"
        row["enrich_model"] = enrich_model_fingerprint
        row["enrich_models_by_field"] = dict(ARTISTS_ENRICHMENT_FIELD_MODELS)
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
        dirty_fairs.add(fair_slug)
        if len(update["headline_ja"]) > HEADLINE_MAX_CHARS:
            counters["headline_over_limit"] += 1
        if len(update["summary_ja"]) > SUMMARY_MAX_CHARS:
            counters["summary_over_limit"] += 1
        if len(update["artist_name_kana"]) > ARTIST_NAME_KANA_MAX_CHARS:
            counters["artist_name_kana_over_limit"] += 1
        if update["warnings"]:
            counters["warnings_rows"] += 1
        batch_result_rows.append(
            {
                "request_id": update["request_id"],
                "fair_slug": fair_slug,
                "text_hash": update["text_hash"],
                "source_url": update["source_url"],
                "status": "APPLIED",
                "headline_ja": update["headline_ja"],
                "summary_ja": update["summary_ja"],
                "artist_name_kana": update["artist_name_kana"],
                "headline_ja_chars": len(update["headline_ja"]),
                "summary_ja_chars": len(update["summary_ja"]),
                "artist_name_kana_chars": len(update["artist_name_kana"]),
                "warnings": update["warnings"],
                "enrich_model": enrich_model_fingerprint,
                "enrich_models_by_field": dict(ARTISTS_ENRICHMENT_FIELD_MODELS),
                "enrich_mode": "openai_batch_apply",
                "enrich_use_openai_batch": use_batch,
                "enrich_completion_window": completion_window,
                "enrich_prompt_version": ENRICH_PROMPT_VERSION,
                "enrich_input_text_hash": update["text_hash"],
                "enrich_batch_job_id": batch_job_id,
                "enrich_notes": str(update.get("repair_mode") or ""),
            }
        )

    for fair_slug in sorted(dirty_fairs):
        write_jsonl(raw_input_paths[fair_slug], raw_rows_by_fair[fair_slug])
    return committed_rows


def main() -> int:
    args = parse_args()
    started_at = utc_now_iso()
    safe_print(f"[START] artists enrichment apply: {started_at}")
    require_live_batch_approval(args)
    lifecycle_mode = normalize_bulk_lifecycle_mode(args.lifecycle_mode)
    io_root = resolve_optional_io_root(args.io_root)
    io_paths = resolve_artists_enrichment_io_paths(io_root=io_root)
    raw_input_paths = io_paths["raw_input_paths"]
    requests_path = io_paths["requests_output_path"]
    allow_current_promote = io_root is None

    for fair_slug, raw_path in raw_input_paths.items():
        if not raw_path.exists():
            raise FileNotFoundError(f"Missing artists raw input for {fair_slug}: {raw_path}")

    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    enrich_model_fingerprint = get_enrichment_model_fingerprint("artists")
    use_batch = (
        os.getenv("ENRICH_USE_OPENAI_BATCH", ENRICH_USE_OPENAI_BATCH_DEFAULT).strip()
        or ENRICH_USE_OPENAI_BATCH_DEFAULT
    )
    completion_window = (
        os.getenv("ENRICH_BATCH_COMPLETION_WINDOW", ENRICH_BATCH_COMPLETION_WINDOW).strip()
        or ENRICH_BATCH_COMPLETION_WINDOW
    )

    request_rows = load_requests(io_root=io_root)
    allowlist = load_gallery_allowlist(args.allowlist_csv) if str(args.allowlist_csv or "").strip() else set()
    allowlist_enabled = bool(allowlist)
    skip_lookup = load_skip_lookup()
    skip_registry_gallery_count = len(skip_lookup.get("by_scope", {})) + len(skip_lookup.get("by_gallery", {}))
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
        gallery_name = str(row.get("gallery_name_en") or req.get("gallery_name_en") or "").strip()
        if find_skip_entry(skip_lookup, fair_slug=fair_slug, gallery_name_en=gallery_name) is not None:
            counters["skipped_by_skip_registry"] += 1
            apply_rows.append(
                {
                    "request_id": request_id,
                    "fair_slug": fair_slug,
                    "text_hash": text_hash,
                    "source_url": source_url,
                    "gallery_name_en": gallery_name,
                    "status": "SKIPPED_BY_SKIP_REGISTRY",
                }
            )
            continue
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
                        "gallery_name_en": gallery_name,
                        "status": "SKIPPED_OUT_OF_SCOPE_ALLOWLIST",
                    }
                )
                continue
        scoped_request_rows += 1
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
        requested_fields = normalize_requested_enrichment_fields(
            req.get("needs_fields"),
            ARTISTS_ENRICHMENT_BATCH_FIELDS,
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
                    field_models=ARTISTS_ENRICHMENT_FIELD_MODELS,
                ),
                "input_chars": len(text),
            }
        )

    target_rows = len(pending_tasks)
    input_bundle_hash = build_input_bundle_hash(requests_path)
    guard_key = build_bulk_guard_key(
        requests_path=requests_path,
        input_bundle_hash=input_bundle_hash,
        prompt_version=ENRICH_PROMPT_VERSION,
        model=enrich_model_fingerprint,
        target_year=TARGET_YEAR,
    )
    probe_paths = build_bulk_artifact_paths(
        "artists",
        stamp=utc_now_compact(),
        target_year=TARGET_YEAR,
        guard_key=guard_key,
        root=io_root,
    )
    prereq = validate_bulk_batch_prerequisites(api_key=api_key, use_batch=use_batch, target_rows=target_rows)
    target_request_ids = [build_enrichment_request_custom_id(str(task["custom_id"])) for task in pending_tasks]

    if args.preflight_only:
        payload = {
            "status": "ok" if prereq["ok"] else "blocked",
            "category": "artists",
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
            "skip_registry_path": str(SKIPPED_GALLERIES_REGISTRY_PATH),
            "skip_registry_gallery_count": skip_registry_gallery_count,
            "scoped_request_rows": scoped_request_rows,
            "out_of_scope_skipped": counters["skipped_out_of_scope_allowlist"],
            "skip_registry_skipped": counters["skipped_by_skip_registry"],
            "target_request_ids_count": len(target_request_ids),
            "enrich_model": enrich_model_fingerprint,
            "enrich_models_by_field": dict(ARTISTS_ENRICHMENT_FIELD_MODELS),
            "prereq": prereq,
        }
        safe_print(payload)
        return 0 if prereq["ok"] else 1

    if not prereq["ok"]:
        raise RuntimeError(f"batch_required_preflight_failed:{','.join(prereq['reasons'])}")

    if target_rows == 0:
        stamp = utc_now_compact()
        paths = build_bulk_artifact_paths(
            "artists",
            stamp=stamp,
            target_year=TARGET_YEAR,
            guard_key=guard_key,
            root=io_root,
        )
        raw_state = summarize_raw_state(raw_rows_by_fair, raw_text_before)
        summary = {
            "started_at": started_at,
            "completed_at": utc_now_iso(),
            "target_year": TARGET_YEAR,
            "rag_category": RAG_CATEGORY,
            "requests_path": str(requests_path),
            "raw_input_paths": {k: str(v) for k, v in raw_input_paths.items()},
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
            "enrich_models_by_field": dict(ARTISTS_ENRICHMENT_FIELD_MODELS),
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
            **build_bulk_lifecycle_fields(
                lifecycle_mode=lifecycle_mode,
                batch_status="not_submitted",
                batch_job_id="",
                materialized=False,
            ),
            "requests_path": str(requests_path),
            "target_request_ids": [],
            "enrich_model": enrich_model_fingerprint,
            "enrich_models_by_field": dict(ARTISTS_ENRICHMENT_FIELD_MODELS),
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
            paths = build_bulk_artifact_paths(
                "artists",
                stamp=stamp,
                target_year=TARGET_YEAR,
                guard_key=guard_key,
                root=io_root,
            )
            batch_job_id = str(existing_state.get("batch_job_id") or "").strip()
            batch_input_file_id = str(existing_state.get("batch_input_file_id") or "").strip()
            if not batch_job_id:
                raise RuntimeError("rerun_guard_missing_batch_job_id")
        else:
            if lifecycle_mode == "resume_or_check":
                raise RuntimeError("resume_or_check_requires_existing_in_progress_batch")
            process_lock_id = acquire_process_lock(probe_paths["lock_path"], category="artists", guard_key=guard_key)
            release_lock_at_exit = True
            stamp = utc_now_compact()
            paths = build_bulk_artifact_paths(
                "artists",
                stamp=stamp,
                target_year=TARGET_YEAR,
                guard_key=guard_key,
                root=io_root,
            )
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
                "requests_path": str(requests_path),
                "input_bundle_hash": input_bundle_hash,
                "enrich_model": enrich_model_fingerprint,
                "enrich_models_by_field": dict(ARTISTS_ENRICHMENT_FIELD_MODELS),
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
                "rag_category": RAG_CATEGORY,
                "requests_path": str(requests_path),
                "raw_input_paths": {k: str(v) for k, v in raw_input_paths.items()},
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
                "enrich_models_by_field": dict(ARTISTS_ENRICHMENT_FIELD_MODELS),
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
                "guard_status": "terminal_failed",
                "batch_status": batch_status,
                **lifecycle_fields,
                "requests_path": str(requests_path),
                "target_request_ids": target_request_ids,
                "request_counts": batch_state.get("request_counts") or {},
                "batch_input_file_id": batch_input_file_id,
                "batch_input_path": str(paths["batch_input_path"]),
                "enrich_model": enrich_model_fingerprint,
                "enrich_models_by_field": dict(ARTISTS_ENRICHMENT_FIELD_MODELS),
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
            guard_state["guard_status"] = "terminal_failed"
            guard_state["completed_at"] = summary["completed_at"]
            guard_state["updated_at"] = summary["completed_at"]
            persist_artifacts(
                history_output_path=paths["history_output_path"],
                history_summary_path=paths["history_summary_path"],
                history_manifest_path=paths["history_manifest_path"],
                apply_rows=failed_rows,
                summary=summary,
                manifest=manifest,
                guard_state_path=paths["guard_state_path"],
                guard_state=guard_state,
            )
            release_process_lock(paths["lock_path"])
            release_lock_at_exit = False
            retention_info = finalize_runtime_requests_retention(
                category="artists",
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
            safe_print(f"[FAILED] batch_job_id={batch_job_id} status={batch_status}")
            safe_print(f"[FAILED] history_summary={paths['history_summary_path']}")
            return 1

        if lifecycle_mode == "submit_only" or batch_status not in TERMINAL_BATCH_STATUSES:
            waiting_status = batch_status or ("submitted_or_validating" if lifecycle_mode == "submit_only" else "in_progress")
            waiting_row_status = "BATCH_SUBMITTED" if lifecycle_mode == "submit_only" else "BATCH_WAITING"
            promote_verdict = (
                "promote_pending_materialization_resume_required"
                if lifecycle_fields["materialization_ready"]
                else "promote_pending_batch_resume_required"
            )
            waiting_rows = apply_rows + [
                {
                    "request_id": str(task["request_id"]),
                    "fair_slug": str(task["fair_slug"]),
                    "text_hash": str(task["text_hash"]),
                    "source_url": str(task["source_url"]),
                    "status": waiting_row_status,
                    "batch_job_id": batch_job_id,
                    "batch_status": waiting_status,
                }
                for task in pending_tasks
            ]
            raw_state = summarize_raw_state(raw_rows_by_fair, raw_text_before)
            summary = {
                "started_at": str(guard_state.get("started_at") or started_at),
                "completed_at": "",
                "target_year": TARGET_YEAR,
                "rag_category": RAG_CATEGORY,
                "requests_path": str(requests_path),
                "raw_input_paths": {k: str(v) for k, v in raw_input_paths.items()},
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
                "enrich_models_by_field": dict(ARTISTS_ENRICHMENT_FIELD_MODELS),
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
                "enrich_models_by_field": dict(ARTISTS_ENRICHMENT_FIELD_MODELS),
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
            safe_print(f"[HOLD] batch_job_id={batch_job_id} status={waiting_status}")
            safe_print(f"[HOLD] summary={paths['history_summary_path']}")
            return 0

        output_rows = download_batch_file_rows(client, str(batch_state.get("output_file_id") or ""))
        error_rows = download_batch_file_rows(client, str(batch_state.get("error_file_id") or ""))
        output_map = build_batch_row_map(output_rows)
        error_map = build_batch_row_map(error_rows)
        current_applied_index = build_current_applied_row_index(paths["current_output_path"])
        diagnostics_path = diagnostic_path_for_apply(paths)
        emit_diagnostics = is_optional_output_enabled("diagnostics")

        staged_updates: list[dict[str, Any]] = []
        warning_count = 0
        batch_result_rows: list[dict[str, Any]] = []
        diagnostic_rows: list[dict[str, Any]] = []
        parsed_success_rows = 0
        batch_error_count = 0

        for task in pending_tasks:
            request_id = str(task["custom_id"])
            artist_name_en = infer_artist_name_en(dict(task["working"]))
            requested_fields = normalize_requested_enrichment_fields(
                task.get("requested_fields"),
                ARTISTS_ENRICHMENT_BATCH_FIELDS,
            )
            parsed_fields: dict[str, str] = {}
            failure_status = ""
            failure_field = ""
            failure_error: Any = ""
            failure_status_code = 0
            parser_response_info: dict[str, Any] | None = None
            parser_response_body: dict[str, Any] | None = None
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
                        failure_status_code = status_code
                        failure_error = result_row.get("error")
                    else:
                        try:
                            headline_ja, summary_ja, artist_name_kana = parse_openai_response_body(response_body)
                        except Exception as exc:
                            failure_status = "BATCH_PARSE_FAILED"
                            failure_field = ",".join(requested_fields)
                            failure_error = str(exc)
                            parser_response_info = response_info
                            parser_response_body = response_body
                        else:
                            parsed_fields = {
                                "headline_ja": str(headline_ja or "").strip(),
                                "summary_ja": str(summary_ja or "").strip(),
                                "artist_name_kana": str(artist_name_kana or "").strip(),
                            }
                            missing_fields = [
                                field_name
                                for field_name in requested_fields
                                if not str(parsed_fields.get(field_name) or "").strip()
                            ]
                            if missing_fields:
                                failure_status = "BATCH_FIELD_EMPTY"
                                failure_field = ",".join(missing_fields)
                                failure_error = "parsed_field_empty"

            if failure_status:
                if failure_status == "BATCH_PARSE_FAILED":
                    response_request_id = ""
                    response_status_code = 0
                    if isinstance(parser_response_info, dict):
                        response_request_id = str(parser_response_info.get("request_id") or "").strip()
                        response_status_code = int(parser_response_info.get("status_code") or 0)
                    response_text = ""
                    if isinstance(parser_response_body, dict):
                        response_text = extract_response_text_for_diagnostic(parser_response_body)
                    repaired_update, diagnostic = maybe_build_localized_repair_update(
                        task=task,
                        current_applied_index=current_applied_index,
                        batch_job_id=batch_job_id,
                        parser_error=str(failure_error),
                    )
                    diagnostic.update(
                        {
                            "batch_status": batch_status,
                            "response_request_id": response_request_id,
                            "response_status_code": response_status_code,
                            "response_text": response_text,
                            "failed_field": failure_field,
                        }
                    )
                    diagnostic_rows.append(diagnostic)
                    if repaired_update is not None:
                        counters["batch_parse_failed_localized_repair_applied"] += 1
                        parsed_success_rows += 1
                        staged_updates.append(repaired_update)
                        continue
                    counters["batch_parse_failed"] += 1
                elif failure_status == "BATCH_RESULT_FAILED":
                    counters["batch_error_file_rows"] += 1
                elif failure_status == "BATCH_RESULT_MISSING":
                    counters["batch_result_missing"] += 1
                elif failure_status == "BATCH_RESPONSE_MISSING":
                    counters["batch_response_missing"] += 1
                elif failure_status == "BATCH_REQUEST_FAILED":
                    counters["batch_request_failed"] += 1
                elif failure_status == "BATCH_FIELD_EMPTY":
                    counters["batch_field_empty"] += 1

                batch_error_count += 1
                batch_result_row = {
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
                    batch_result_row["status_code"] = failure_status_code
                batch_result_rows.append(batch_result_row)
                continue

            headline_ja = parsed_fields["headline_ja"]
            summary_ja = parsed_fields["summary_ja"]
            artist_name_kana = parsed_fields["artist_name_kana"]
            warnings = build_warnings(summary_ja=summary_ja, artist_name_en=artist_name_en, artist_name_kana=artist_name_kana)
            warning_count += len(warnings)
            parsed_success_rows += 1
            staged_updates.append({"fair_slug": str(task["fair_slug"]), "row_index": int(task["row_index"]), "text_hash": str(task["text_hash"]), "source_url": str(task["source_url"]), "request_id": request_id, "headline_ja": headline_ja, "summary_ja": summary_ja, "artist_name_kana": artist_name_kana, "warnings": warnings, "input_chars": int(task["input_chars"]), "repair_mode": "", "repair_source_request_id": "", "repair_source_summary_chars": 0})

        committed_rows = 0
        if staged_updates:
            committed_rows = commit_successful_artist_enrichment_updates(
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

        status_counts = Counter(str(row.get("status") or "").strip() for row in batch_result_rows)
        parse_failed_rows = int(status_counts.get("BATCH_PARSE_FAILED", 0))
        ready_uncommitted_rows = int(status_counts.get("BATCH_RESULT_READY_UNCOMMITTED", 0)) + int(
            status_counts.get("LOCALIZED_REPAIR_READY_UNCOMMITTED", 0)
        )
        failed_rows = batch_error_count

        apply_rows.extend(batch_result_rows)
        raw_state = summarize_raw_state(raw_rows_by_fair, raw_text_before)
        error_count = counters["skipped_non_artists_category"] + counters["skipped_invalid_fair_slug"] + counters["skipped_missing_text_hash"] + counters["skipped_target_guard_non_artist_utility_url"] + counters["skipped_target_guard_missing_target"] + counters["skipped_target_row_not_found"] + counters["skipped_empty_text"] + batch_error_count
        full_success = committed_rows == target_rows and error_count == 0
        partial_success = committed_rows > 0 and error_count > 0
        apply_completed_ok = batch_status == "completed" and committed_rows > 0 and ready_uncommitted_rows == 0

        diagnostics_payload = {
            "category": "artists",
            "target_year": TARGET_YEAR,
            "batch_job_id": batch_job_id,
            "batch_status": batch_status,
            "localized_repair_applied": int(counters.get("batch_parse_failed_localized_repair_applied", 0)),
            "diagnostic_rows": diagnostic_rows,
        }
        if diagnostic_rows and emit_diagnostics:
            write_json(diagnostics_path, diagnostics_payload)

        summary = {
            "started_at": str(guard_state.get("started_at") or started_at),
            "completed_at": utc_now_iso(),
            "target_year": TARGET_YEAR,
            "rag_category": RAG_CATEGORY,
            "requests_path": str(requests_path),
            "raw_input_paths": {k: str(v) for k, v in raw_input_paths.items()},
            "apply_output_path": str(paths["history_output_path"]),
            "apply_summary_path": str(paths["history_summary_path"]),
            "apply_manifest_path": str(paths["history_manifest_path"]),
            "current_output_path": str(paths["current_output_path"]),
            "current_summary_path": str(paths["current_summary_path"]),
            "total_targeted": len(request_rows),
            "applied_rows": committed_rows,
            "total_applied": committed_rows,
            "total_not_updated": len(request_rows) - committed_rows,
            "warning_count": warning_count,
            "warning_rows": counters["warnings_rows"],
            "generated_openai": committed_rows,
            "generated_fallback": 0,
            "error_count": error_count,
            "failed_rows": failed_rows,
            "parse_failed_rows": parse_failed_rows,
            "ready_uncommitted_rows": ready_uncommitted_rows,
            "partial_success": partial_success,
            "batch_status": batch_status,
            "request_counts": batch_state.get("request_counts") or {},
            "parsed_success_rows": parsed_success_rows,
            "batch_error_rows": batch_error_count,
            "diagnostics_path": str(diagnostics_path) if diagnostic_rows and emit_diagnostics else "",
            "diagnostic_rows": len(diagnostic_rows),
            "localized_repair_applied": int(counters.get("batch_parse_failed_localized_repair_applied", 0)),
            **build_bulk_lifecycle_fields(
                lifecycle_mode=lifecycle_mode,
                batch_status=batch_status,
                batch_job_id=batch_job_id,
                materialized=True,
            ),
            "promoted_to_current": False,
            "promote_verdict": "",
            "guard_state_path": str(paths["guard_state_path"]),
            "guard_key": guard_key,
            "target_request_ids_count": len(target_request_ids),
            "target_request_ids": target_request_ids,
            "counters": dict(counters),
            "enrich_model": enrich_model_fingerprint,
            "enrich_models_by_field": dict(ARTISTS_ENRICHMENT_FIELD_MODELS),
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
            "diagnostics_path": str(diagnostics_path) if diagnostic_rows and emit_diagnostics else "",
            "diagnostic_rows": len(diagnostic_rows),
            "localized_repair_applied": int(counters.get("batch_parse_failed_localized_repair_applied", 0)),
            "enrich_model": enrich_model_fingerprint,
            "enrich_models_by_field": dict(ARTISTS_ENRICHMENT_FIELD_MODELS),
            "enrich_prompt_version": ENRICH_PROMPT_VERSION,
            "enrich_completion_window": completion_window,
            "openai_client_available": bool(api_key),
            "parsed_success_rows": parsed_success_rows,
            "batch_error_rows": batch_error_count,
            "applied_rows": committed_rows,
            "failed_rows": failed_rows,
            "parse_failed_rows": parse_failed_rows,
            "ready_uncommitted_rows": ready_uncommitted_rows,
            "partial_success": partial_success,
            **build_bulk_contract_fields(api_mode="openai_batch_apply", batch_used=True, batch_job_id=batch_job_id, input_bundle_hash=input_bundle_hash, target_rows=target_rows, updated_rows=committed_rows, rerun_guard_verdict=rerun_guard_verdict, process_lock_id=process_lock_id),
        }

        promote_ready = False
        if allow_current_promote:
            if full_success:
                promote_ready, promote_verdict = validate_bulk_promote_summary(summary)
            elif apply_completed_ok:
                promote_ready, promote_verdict = True, "promote_allowed_partial_success"
            else:
                promote_verdict = "promote_blocked_no_committed_rows"
        else:
            promote_verdict = "promote_skipped_non_current_root"
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

        current_runtime_rows, current_runtime_materialization = build_artist_current_runtime_rows(
            raw_rows_by_fair=raw_rows_by_fair,
            current_output_path=paths["current_output_path"],
            io_root=io_root,
        )
        summary["current_runtime_rows_total"] = len(current_runtime_rows)
        summary["current_runtime_status_counts"] = {"APPLIED": len(current_runtime_rows)} if current_runtime_rows else {}
        summary["current_runtime_rows_dropped_from_current"] = max(
            0,
            current_runtime_materialization["raw_key_total"] - len(current_runtime_rows),
        )
        summary["current_runtime_rows_dropped_reason"] = "rows_without_current_raw_or_available_applied_or_raw_enrichment_values"
        summary["current_runtime_source_of_truth"] = "current_raw_then_current_applied_then_history_applied"
        summary["current_runtime_materialization"] = dict(current_runtime_materialization)
        manifest["current_runtime_rows_total"] = len(current_runtime_rows)
        manifest["current_runtime_status_counts"] = summary["current_runtime_status_counts"]
        manifest["current_runtime_source_of_truth"] = summary["current_runtime_source_of_truth"]
        manifest["current_runtime_materialization"] = dict(current_runtime_materialization)

        if allow_current_promote and promote_ready:
            write_jsonl(paths["current_output_path"], current_runtime_rows)
            summary["promoted_to_current"] = True
        release_process_lock(paths["lock_path"])
        release_lock_at_exit = False

        retention_info = finalize_runtime_requests_retention(
            category="artists",
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

        if allow_current_promote and promote_ready:
            write_json(paths["current_summary_path"], summary)
            safe_print(f"[DONE] total_targeted={summary['total_targeted']} total_applied={summary['total_applied']}")
            safe_print(f"[DONE] history_summary={paths['history_summary_path']}")
            safe_print(f"[DONE] current_summary={paths['current_summary_path']}")
            return 0

        if apply_completed_ok:
            safe_print(f"[DONE] total_targeted={summary['total_targeted']} total_applied={summary['total_applied']}")
            safe_print(f"[DONE] history_summary={paths['history_summary_path']}")
            if not allow_current_promote:
                safe_print("[DONE] current_promotion=skipped_non_current_root")
            return 0

        safe_print(f"[BLOCKED] promote_verdict={summary['promote_verdict']}")
        safe_print(f"[BLOCKED] history_summary={paths['history_summary_path']}")
        return 1
    finally:
        if release_lock_at_exit:
            release_process_lock(probe_paths["lock_path"])


if __name__ == "__main__":
    raise SystemExit(main())
