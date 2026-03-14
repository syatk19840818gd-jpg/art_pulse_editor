from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import OpenAI

from phase2_art_pulse_config import (
    get_enrichment_current_output_path,
    get_enrichment_current_summary_path,
    get_enrichment_history_dir,
    get_enrichment_history_output_path,
    get_enrichment_history_summary_path,
    get_enrichment_runtime_requests_completed_dir,
    get_enrichment_runtime_requests_path,
    get_enrichment_runtime_requests_reports_dir,
    get_enrichment_seed10_legacy_requests_path,
)

TRUTHY_VALUES = {"1", "true", "yes", "on"}
TERMINAL_BATCH_STATUSES = {"completed", "failed", "expired", "cancelled"}
ALLOWED_PROMOTE_RERUN_GUARD_VERDICTS = {"new_run", "resume_existing_batch"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def utc_now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def is_truthy_flag(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in TRUTHY_VALUES


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def to_plain_dict(obj: Any) -> dict[str, Any]:
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        dumped = obj.model_dump(mode="json")
        if isinstance(dumped, dict):
            return dumped
    if hasattr(obj, "model_dump_json"):
        dumped_json = obj.model_dump_json()
        if dumped_json:
            loaded = json.loads(dumped_json)
            if isinstance(loaded, dict):
                return loaded
    raise TypeError(f"Unsupported object for to_plain_dict: {type(obj)!r}")


def build_input_bundle_hash(requests_path: Path) -> str:
    return sha256_file(requests_path.resolve())


def build_bulk_guard_key(
    *,
    requests_path: Path,
    input_bundle_hash: str,
    prompt_version: str,
    model: str,
    target_year: int,
) -> str:
    payload = {
        "requests_path": str(requests_path.resolve()),
        "input_bundle_hash": input_bundle_hash,
        "prompt_version": str(prompt_version or ""),
        "model": str(model or ""),
        "target_year": int(target_year),
    }
    return sha256_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def build_bulk_artifact_paths(category: str, *, stamp: str, target_year: int, guard_key: str) -> dict[str, Path]:
    history_dir = get_enrichment_history_dir(category)
    runtime_dir = history_dir / "_runtime_guards"
    return {
        "history_output_path": get_enrichment_history_output_path(category, stamp, target_year),
        "history_summary_path": get_enrichment_history_summary_path(category, stamp, target_year),
        "history_manifest_path": history_dir / f"{category}_enrichment_apply_manifest_{target_year}_{stamp}.json",
        "batch_input_path": history_dir / f"{category}_enrichment_batch_input_{target_year}_{stamp}.jsonl",
        "current_output_path": get_enrichment_current_output_path(category, target_year),
        "current_summary_path": get_enrichment_current_summary_path(category, target_year),
        "guard_state_path": runtime_dir / f"{category}_enrichment_guard_{target_year}_{guard_key}.json",
        "lock_path": runtime_dir / f"{category}_enrichment_guard_{target_year}_{guard_key}.lock",
    }


def build_requests_runtime_report_path(category: str, *, action: str, target_year: int, stamp: str | None = None) -> Path:
    safe_action = str(action or "report").strip().replace(" ", "_")
    report_stamp = str(stamp or utc_now_compact())
    return (
        get_enrichment_runtime_requests_reports_dir()
        / f"{category}_enrichment_requests_{safe_action}_{target_year}_{report_stamp}.json"
    )


def resolve_runtime_requests_path(category: str, *, target_year: int, migrate_legacy: bool = True) -> Path:
    runtime_path = get_enrichment_runtime_requests_path(category, target_year)
    if runtime_path.exists():
        return runtime_path

    legacy_path = get_enrichment_seed10_legacy_requests_path(category, target_year)
    if not migrate_legacy or not legacy_path.exists():
        return runtime_path

    runtime_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_hash = sha256_file(legacy_path)
    legacy_size = int(legacy_path.stat().st_size)
    os.replace(str(legacy_path), str(runtime_path))
    write_json(
        build_requests_runtime_report_path(category, action="legacy_migration", target_year=target_year),
        {
            "category": category,
            "target_year": int(target_year),
            "action": "legacy_migration_to_runtime_active",
            "migrated_at": utc_now_iso(),
            "legacy_requests_path": str(legacy_path),
            "runtime_requests_path": str(runtime_path),
            "legacy_sha256": legacy_hash,
            "legacy_size_bytes": legacy_size,
        },
    )
    return runtime_path


def load_guard_state(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = read_json(path)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def write_guard_state(path: Path, payload: dict[str, Any]) -> None:
    write_json(path, payload)


def acquire_process_lock(lock_path: Path, *, category: str, guard_key: str) -> str:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    process_lock_id = f"{category}:{os.getpid()}:{utc_now_compact()}:{guard_key[:12]}"
    payload = {
        "category": category,
        "guard_key": guard_key,
        "process_lock_id": process_lock_id,
        "pid": os.getpid(),
        "created_at": utc_now_iso(),
    }
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    try:
        fd = os.open(str(lock_path), flags)
    except FileExistsError as exc:
        raise RuntimeError(f"process_lock_exists:{lock_path}") from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    except Exception:
        try:
            lock_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise
    return process_lock_id


def release_process_lock(lock_path: Path) -> None:
    lock_path.unlink(missing_ok=True)


def load_process_lock_payload(lock_path: Path) -> dict[str, Any]:
    if not lock_path.exists():
        raise RuntimeError(f"rerun_guard_lock_file_missing:{lock_path}")
    try:
        payload = read_json(lock_path)
    except Exception as exc:
        raise RuntimeError(f"rerun_guard_lock_payload_invalid:{lock_path}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"rerun_guard_lock_payload_invalid:{lock_path}")
    process_lock_id = str(payload.get("process_lock_id") or "").strip()
    if not process_lock_id:
        raise RuntimeError(f"rerun_guard_lock_process_lock_id_missing:{lock_path}")
    return payload


def validate_resume_guard_state(
    *,
    existing_state: dict[str, Any] | None,
    lock_path: Path,
    expected_target_request_ids: list[str],
    category: str,
    guard_key: str,
) -> dict[str, Any]:
    if not isinstance(existing_state, dict):
        raise RuntimeError("rerun_guard_state_missing")

    state_process_lock_id = str(existing_state.get("process_lock_id") or "").strip()
    if not state_process_lock_id:
        raise RuntimeError("rerun_guard_missing_process_lock_id")

    existing_target_ids = [str(x) for x in list(existing_state.get("target_request_ids") or [])]
    expected_target_ids = [str(x) for x in expected_target_request_ids]
    if existing_target_ids != expected_target_ids:
        raise RuntimeError("rerun_guard_target_ids_changed")

    state_category = str(existing_state.get("category") or "").strip()
    if state_category and state_category != str(category or ""):
        raise RuntimeError("rerun_guard_state_category_mismatch")

    state_guard_key = str(existing_state.get("guard_key") or "").strip()
    if state_guard_key and state_guard_key != str(guard_key or ""):
        raise RuntimeError("rerun_guard_state_guard_key_mismatch")

    lock_payload = load_process_lock_payload(lock_path)
    lock_process_lock_id = str(lock_payload.get("process_lock_id") or "").strip()
    if lock_process_lock_id != state_process_lock_id:
        raise RuntimeError("rerun_guard_lock_process_lock_id_mismatch")

    lock_category = str(lock_payload.get("category") or "").strip()
    if lock_category and lock_category != str(category or ""):
        raise RuntimeError("rerun_guard_lock_category_mismatch")

    lock_guard_key = str(lock_payload.get("guard_key") or "").strip()
    if lock_guard_key and lock_guard_key != str(guard_key or ""):
        raise RuntimeError("rerun_guard_lock_guard_key_mismatch")

    return {
        "process_lock_id": state_process_lock_id,
        "target_request_ids": existing_target_ids,
        "lock_payload": lock_payload,
    }


def _optional_summary_path(summary: dict[str, Any], key: str) -> Path | None:
    value = str(summary.get(key) or "").strip()
    return Path(value) if value else None


def evaluate_runtime_requests_retention(
    *,
    category: str,
    target_year: int,
    requests_path: Path,
    summary: dict[str, Any],
    guard_state_path: Path,
    lock_path: Path,
) -> tuple[bool, str]:
    if not requests_path.exists():
        return False, "requests_cleanup_skipped_missing_active_runtime_requests"
    if lock_path.exists():
        return False, "requests_cleanup_retained_lock_active"
    if not guard_state_path.exists():
        return False, "requests_cleanup_retained_guard_state_missing"

    guard_state = load_guard_state(guard_state_path)
    if not isinstance(guard_state, dict):
        return False, "requests_cleanup_retained_guard_state_invalid"

    guard_status = str(guard_state.get("guard_status") or "").strip()
    if guard_status == "in_progress":
        return False, "requests_cleanup_retained_guard_in_progress"

    batch_status = str(summary.get("batch_status") or guard_state.get("batch_status") or "").strip()
    if batch_status not in TERMINAL_BATCH_STATUSES:
        return False, "requests_cleanup_retained_batch_non_terminal"

    required_fields = {
        "execution_mode": ("bulk_apply", "requests_cleanup_retained_execution_mode"),
        "api_mode": ("openai_batch_apply", "requests_cleanup_retained_api_mode"),
    }
    for field_name, (expected_value, failure_code) in required_fields.items():
        if str(summary.get(field_name) or "").strip() != expected_value:
            return False, failure_code

    truthy_fields = {
        "batch_required": "requests_cleanup_retained_batch_not_required",
        "batch_used": "requests_cleanup_retained_batch_unused",
    }
    for field_name, failure_code in truthy_fields.items():
        if not bool(summary.get(field_name)):
            return False, failure_code

    nonempty_fields = {
        "batch_job_id": "requests_cleanup_retained_missing_batch_job_id",
        "input_bundle_hash": "requests_cleanup_retained_missing_input_bundle_hash",
        "process_lock_id": "requests_cleanup_retained_missing_process_lock_id",
        "rerun_guard_verdict": "requests_cleanup_retained_missing_rerun_guard_verdict",
        "promote_verdict": "requests_cleanup_retained_missing_promote_verdict",
    }
    for field_name, failure_code in nonempty_fields.items():
        if not str(summary.get(field_name) or "").strip():
            return False, failure_code

    if str(summary.get("guard_state_path") or "").strip() != str(guard_state_path):
        return False, "requests_cleanup_retained_guard_state_path_mismatch"

    required_artifact_paths = {
        "apply_output_path": "requests_cleanup_retained_missing_history_output",
        "apply_summary_path": "requests_cleanup_retained_missing_history_summary",
        "apply_manifest_path": "requests_cleanup_retained_missing_history_manifest",
    }
    for field_name, failure_code in required_artifact_paths.items():
        artifact_path = _optional_summary_path(summary, field_name)
        if artifact_path is None or not artifact_path.exists():
            return False, failure_code

    if requests_path != get_enrichment_runtime_requests_path(category, target_year):
        return False, "requests_cleanup_retained_non_runtime_active_path"

    return True, "requests_cleanup_allowed"


def finalize_runtime_requests_retention(
    *,
    category: str,
    target_year: int,
    requests_path: Path,
    summary: dict[str, Any],
    guard_state_path: Path,
    lock_path: Path,
) -> dict[str, Any]:
    cleanup_allowed, retention_verdict = evaluate_runtime_requests_retention(
        category=category,
        target_year=target_year,
        requests_path=requests_path,
        summary=summary,
        guard_state_path=guard_state_path,
        lock_path=lock_path,
    )
    stamp = utc_now_compact()
    report_path = build_requests_runtime_report_path(
        category,
        action="retention",
        target_year=target_year,
        stamp=stamp,
    )
    report: dict[str, Any] = {
        "category": category,
        "target_year": int(target_year),
        "evaluated_at": utc_now_iso(),
        "active_requests_path": str(requests_path),
        "guard_state_path": str(guard_state_path),
        "lock_path": str(lock_path),
        "retention_verdict": retention_verdict,
        "cleanup_allowed": cleanup_allowed,
        "batch_status": str(summary.get("batch_status") or ""),
        "promote_verdict": str(summary.get("promote_verdict") or ""),
        "batch_job_id": str(summary.get("batch_job_id") or ""),
    }
    if cleanup_allowed:
        archived_path = (
            get_enrichment_runtime_requests_completed_dir(category)
            / f"{requests_path.stem}_{stamp}{requests_path.suffix}"
        )
        archived_path.parent.mkdir(parents=True, exist_ok=True)
        report["active_requests_sha256"] = sha256_file(requests_path)
        report["active_requests_size_bytes"] = int(requests_path.stat().st_size)
        os.replace(str(requests_path), str(archived_path))
        report["retention_action"] = "moved_to_completed_runtime_archive"
        report["archived_requests_path"] = str(archived_path)
    else:
        report["retention_action"] = "kept_runtime_active"
        report["archived_requests_path"] = ""

    write_json(report_path, report)
    return {
        "requests_retention_action": str(report.get("retention_action") or ""),
        "requests_retention_verdict": retention_verdict,
        "requests_cleanup_report_path": str(report_path),
        "archived_requests_path": str(report.get("archived_requests_path") or ""),
    }


def validate_bulk_batch_prerequisites(*, api_key: str, use_batch: str | bool, target_rows: int) -> dict[str, Any]:
    client = OpenAI(api_key=api_key or "test")
    batch_flag_enabled = is_truthy_flag(use_batch)
    details = {
        "batch_required": True,
        "execution_mode": "bulk_apply",
        "api_mode": "openai_batch_apply",
        "direct_openai_allowed": False,
        "openai_api_key_present": bool(str(api_key or "").strip()),
        "batch_flag_enabled": batch_flag_enabled,
        "client_files_create_available": hasattr(client.files, "create"),
        "client_files_content_available": hasattr(client.files, "content"),
        "client_batches_create_available": hasattr(client.batches, "create"),
        "client_batches_retrieve_available": hasattr(client.batches, "retrieve"),
        "target_rows": int(target_rows),
    }
    reasons: list[str] = []
    if not batch_flag_enabled:
        reasons.append("batch_flag_disabled")
    if not details["openai_api_key_present"]:
        reasons.append("openai_api_key_missing")
    if not details["client_files_create_available"]:
        reasons.append("sdk_missing_files_create")
    if not details["client_files_content_available"]:
        reasons.append("sdk_missing_files_content")
    if not details["client_batches_create_available"]:
        reasons.append("sdk_missing_batches_create")
    if not details["client_batches_retrieve_available"]:
        reasons.append("sdk_missing_batches_retrieve")
    details["ok"] = not reasons
    details["reasons"] = reasons
    return details


def build_batch_request_line(*, custom_id: str, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "custom_id": custom_id,
        "method": "POST",
        "url": "/v1/responses",
        "body": body,
    }


def upload_batch_input_file(client: OpenAI, batch_input_path: Path) -> dict[str, Any]:
    with batch_input_path.open("rb") as handle:
        file_obj = client.files.create(file=handle, purpose="batch")
    return to_plain_dict(file_obj)


def create_responses_batch(
    client: OpenAI,
    *,
    input_file_id: str,
    completion_window: str,
    metadata: dict[str, str] | None = None,
) -> dict[str, Any]:
    batch_obj = client.batches.create(
        completion_window=str(completion_window or "24h"),
        endpoint="/v1/responses",
        input_file_id=input_file_id,
        metadata=metadata or None,
    )
    return to_plain_dict(batch_obj)


def retrieve_batch(client: OpenAI, batch_job_id: str) -> dict[str, Any]:
    return to_plain_dict(client.batches.retrieve(batch_job_id))


def download_batch_file_rows(client: OpenAI, file_id: str) -> list[dict[str, Any]]:
    if not file_id:
        return []
    text = client.files.retrieve_content(file_id)
    rows: list[dict[str, Any]] = []
    for line in str(text or "").splitlines():
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


def extract_response_text_from_body(body: dict[str, Any]) -> str:
    output_text = str(body.get("output_text") or "").strip()
    if output_text:
        return output_text

    texts: list[str] = []
    output_items = body.get("output")
    if isinstance(output_items, list):
        for item in output_items:
            if not isinstance(item, dict):
                continue
            if str(item.get("type") or "") in {"output_text", "text"}:
                text = str(item.get("text") or "").strip()
                if text:
                    texts.append(text)
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for chunk in content:
                if not isinstance(chunk, dict):
                    continue
                chunk_type = str(chunk.get("type") or "")
                text = str(chunk.get("text") or "").strip()
                if chunk_type in {"output_text", "text"} and text:
                    texts.append(text)
    return "\n".join(texts).strip()


def build_bulk_contract_fields(
    *,
    api_mode: str,
    batch_used: bool,
    batch_job_id: str,
    input_bundle_hash: str,
    target_rows: int,
    updated_rows: int,
    rerun_guard_verdict: str,
    process_lock_id: str,
    execution_mode: str = "bulk_apply",
    batch_required: bool = True,
) -> dict[str, Any]:
    return {
        "api_mode": api_mode,
        "batch_used": bool(batch_used),
        "batch_job_id": str(batch_job_id or ""),
        "input_bundle_hash": str(input_bundle_hash or ""),
        "target_rows": int(target_rows),
        "updated_rows": int(updated_rows),
        "rerun_guard_verdict": str(rerun_guard_verdict or ""),
        "process_lock_id": str(process_lock_id or ""),
        "execution_mode": str(execution_mode or "bulk_apply"),
        "batch_required": bool(batch_required),
    }


def validate_bulk_promote_summary(summary: dict[str, Any]) -> tuple[bool, str]:
    execution_mode = str(summary.get("execution_mode") or "")
    api_mode = str(summary.get("api_mode") or "")
    batch_job_id = str(summary.get("batch_job_id") or "")
    input_bundle_hash = str(summary.get("input_bundle_hash") or "")
    process_lock_id = str(summary.get("process_lock_id") or "")
    rerun_guard_verdict = str(summary.get("rerun_guard_verdict") or "")
    batch_status = str(summary.get("batch_status") or "")
    guard_state_path = str(summary.get("guard_state_path") or "")

    try:
        target_rows = int(summary.get("target_rows"))
        updated_rows = int(summary.get("updated_rows"))
        error_count = int(summary.get("error_count", 0))
    except Exception:
        return False, "promote_summary_numeric_fields_invalid"

    if execution_mode != "bulk_apply":
        return False, "promote_blocked_execution_mode"
    if not bool(summary.get("batch_required")):
        return False, "promote_blocked_batch_not_required"
    if api_mode != "openai_batch_apply":
        return False, "promote_blocked_api_mode"
    if not bool(summary.get("batch_used")):
        return False, "promote_blocked_batch_unused"
    if not batch_job_id:
        return False, "promote_blocked_missing_batch_job_id"
    if not input_bundle_hash:
        return False, "promote_blocked_missing_input_bundle_hash"
    if not process_lock_id:
        return False, "promote_blocked_missing_process_lock_id"
    if not rerun_guard_verdict:
        return False, "promote_blocked_missing_rerun_guard_verdict"
    if rerun_guard_verdict not in ALLOWED_PROMOTE_RERUN_GUARD_VERDICTS:
        return False, "promote_blocked_invalid_rerun_guard_verdict"
    if not guard_state_path:
        return False, "promote_blocked_missing_guard_state_path"
    if batch_status != "completed":
        return False, "promote_blocked_batch_not_completed"
    if target_rows < 0 or updated_rows < 0:
        return False, "promote_blocked_negative_row_counts"
    if updated_rows != target_rows:
        return False, "promote_blocked_updated_rows_mismatch"
    if error_count != 0:
        return False, "promote_blocked_error_count"
    return True, "promote_allowed"
