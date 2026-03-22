#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from phase1_ledger_contract import (
    FAILED_FETCH_REQUIRED_FIELDS,
    GUARD_BASE_REQUIRED_SUMMARY_KEYS,
    LedgerLoadResult,
    get_phase1_logs_dir,
    load_guard_ledger,
    resolve_guard_default_failed_fetches_path,
    resolve_guard_default_run_summary_path,
    resolve_guard_default_visited_pages_path,
    validate_failed_fetch_schema,
)
from phase1_guard_common import (
    DEFAULT_CATEGORY_PROFILE_CONFIG_PATH,
    DEFAULT_GUARD_CATEGORY,
    GUARD_CATEGORY_PROFILE_VERSION,
    GUARD_SCHEMA_VERSION,
    get_effective_category_profiles,
    resolve_logs_dir,
    utc_now_iso,
    utc_timestamp_compact,
    write_summary_json,
)

DEFAULT_LOGS_DIR = get_phase1_logs_dir()
OUTPUT_TEMPLATE = "phase1_guard_summary_{target_year}_{timestamp}.json"
GENERATED_BY = "run_compare_phase1_guard.py"

MANIFEST_MIN_KEYS = {"target_year", "generated_at", "files"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Phase1 guard checks for Exhibitions/Artists summaries and ledgers."
    )
    parser.add_argument("--target-year", type=int, required=True, help="target year (e.g. 2025)")
    parser.add_argument(
        "--logs-dir",
        default=str(DEFAULT_LOGS_DIR),
        help="base directory for guard input/output defaults",
    )
    parser.add_argument(
        "--run-summary-path",
        default="",
        help="input run_summary path. Default: <logs-dir>/run_summary_seed10_<target_year>.json",
    )
    parser.add_argument(
        "--summary-path",
        default="",
        help="output summary path. Default: <logs-dir>/phase1_guard_summary_<target_year>_<timestamp>.json",
    )
    parser.add_argument("--visited-path", default="", help="override visited_pages path")
    parser.add_argument("--failed-path", default="", help="override failed_fetches path")
    parser.add_argument("--manifest-path", default="", help="optional artifact_manifest path")
    parser.add_argument(
        "--category",
        default=DEFAULT_GUARD_CATEGORY,
        help=f"guard category metadata (default: {DEFAULT_GUARD_CATEGORY})",
    )
    parser.add_argument(
        "--category-profile-config",
        default=str(DEFAULT_CATEGORY_PROFILE_CONFIG_PATH),
        help=f"category profile config path (default: {DEFAULT_CATEGORY_PROFILE_CONFIG_PATH})",
    )
    parser.add_argument(
        "--fail-on-mismatch",
        action="store_true",
        help="return non-zero when mismatch_fields is non-empty",
    )
    return parser.parse_args()


def safe_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def load_json_object(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, "MISSING_FILE"
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, f"JSON_DECODE_ERROR: {exc}"
    except OSError as exc:
        return None, f"OS_ERROR: {exc}"

    if not isinstance(obj, dict):
        return None, f"INVALID_ROOT_TYPE:{type(obj).__name__}"
    return obj, None


def count_jsonl_records(path: Path) -> tuple[int | None, str | None]:
    if not path.exists():
        return None, "MISSING_FILE"
    count = 0
    try:
        with path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line:
                    continue
                count += 1
    except OSError as exc:
        return None, f"OS_ERROR: {exc}"
    return count, None


def resolve_path(override: str, fallback: Any) -> Path | None:
    if override:
        return Path(override)
    if isinstance(fallback, str) and fallback:
        return Path(fallback)
    return None


def parse_counter_map(value: Any) -> tuple[dict[str, int] | None, list[str]]:
    if not isinstance(value, dict):
        return None, ["not_dict"]

    counts: dict[str, int] = {}
    errors: list[str] = []
    for key, raw in value.items():
        if not isinstance(key, str) or not key:
            errors.append("invalid_key")
            continue
        parsed = safe_int(raw)
        if parsed is None:
            errors.append(f"non_int_value:{key}")
            continue
        counts[key] = parsed

    return counts, errors


def dedupe_strings(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def resolve_category_profile(
    requested_category: str,
    category_profiles: dict[str, dict[str, Any]],
) -> tuple[str, dict[str, Any], list[str]]:
    category = requested_category.strip() if isinstance(requested_category, str) else ""
    if not category:
        category = DEFAULT_GUARD_CATEGORY

    profile = category_profiles.get(category)
    warnings: list[str] = []
    if profile is None:
        category = DEFAULT_GUARD_CATEGORY
        profile = category_profiles.get(category)
        if profile is None and category_profiles:
            category, profile = next(iter(category_profiles.items()))
            warnings.append(f"default_category_missing_fallback_to_first:{category}")
        elif profile is None:
            profile = {}
        warnings.append(f"unknown_category_fallback:{requested_category}->{category}")
    return category, dict(profile), warnings


def resolve_required_summary_keys(category_profile: dict[str, Any]) -> set[str]:
    explicit_required_raw = category_profile.get("required_summary_keys")
    if isinstance(explicit_required_raw, list):
        explicit_required: set[str] = set()
        for key in explicit_required_raw:
            if isinstance(key, str) and key:
                explicit_required.add(key)
        if explicit_required:
            return explicit_required

    required = set(GUARD_BASE_REQUIRED_SUMMARY_KEYS)
    drop_keys_raw = category_profile.get("required_summary_keys_drop")
    if isinstance(drop_keys_raw, list):
        for key in drop_keys_raw:
            if isinstance(key, str) and key:
                required.discard(key)
    add_keys_raw = category_profile.get("required_summary_keys_add")
    if isinstance(add_keys_raw, list):
        for key in add_keys_raw:
            if isinstance(key, str) and key:
                required.add(key)
    return required


def infer_output_files_from_raw(logs_dir: Path, target_year: int) -> tuple[dict[str, Path], str]:
    raw_dir = logs_dir.parent / "raw"
    paths = sorted(raw_dir.glob(f"exhibitions_*_{target_year}.jsonl"))
    output_file_paths: dict[str, Path] = {}
    for path in paths:
        match = re.match(rf"^exhibitions_(.+)_{target_year}\.jsonl$", path.name)
        if not match:
            continue
        fair_slug = match.group(1)
        output_file_paths[fair_slug] = path
    if output_file_paths:
        return output_file_paths, "from_logs_dir_raw_glob"
    return {}, "missing"


def detect_artists_data_presence(logs_dir: Path, target_year: int, summary_obj: dict[str, Any]) -> dict[str, Any]:
    raw_dir = logs_dir.parent / "raw"
    raw_candidates = sorted(raw_dir.glob(f"artists_*_{target_year}.jsonl"))
    raw_candidate_paths = [str(path) for path in raw_candidates]

    summary_output_keys: list[str] = []
    output_files = summary_obj.get("output_files")
    if isinstance(output_files, dict):
        for key in output_files.keys():
            if not isinstance(key, str):
                continue
            lowered = key.lower()
            if lowered.startswith("artists_") or lowered.startswith("artist_") or "artist" in lowered:
                summary_output_keys.append(key)

    has_artists_data = bool(raw_candidate_paths or summary_output_keys)
    return {
        "has_artists_data": has_artists_data,
        "raw_dir": str(raw_dir),
        "raw_candidate_count": len(raw_candidate_paths),
        "raw_candidate_paths": raw_candidate_paths,
        "summary_output_file_artist_keys": summary_output_keys,
    }


def load_manifest_check(path: Path | None, target_year: int) -> dict[str, Any]:
    if path is None:
        return {
            "status": "skipped_optional",
            "manifest_path": None,
            "exists": False,
            "passed": True,
            "errors": [],
        }

    result: dict[str, Any] = {
        "status": "checked",
        "manifest_path": str(path),
        "exists": path.exists(),
        "passed": True,
        "errors": [],
    }

    if not path.exists():
        result["passed"] = False
        result["errors"].append("manifest_path_missing")
        return result

    obj, err = load_json_object(path)
    if err:
        result["passed"] = False
        result["errors"].append(f"manifest_load_error:{err}")
        return result

    assert obj is not None
    missing = sorted(MANIFEST_MIN_KEYS - set(obj.keys()))
    if missing:
        result["passed"] = False
        result["errors"].append(f"manifest_missing_keys:{','.join(missing)}")

    files = obj.get("files")
    if not isinstance(files, list):
        result["passed"] = False
        result["errors"].append("manifest_files_not_list")

    manifest_year = safe_int(obj.get("target_year"))
    if manifest_year is not None and manifest_year != target_year:
        result["passed"] = False
        result["errors"].append(f"manifest_target_year_mismatch:{manifest_year}!={target_year}")

    return result


def main() -> int:
    args = parse_args()
    started_at = utc_now_iso()
    print(f"[START] Phase1 guard compare at {started_at}")

    category_profile_bundle = get_effective_category_profiles(args.category_profile_config)
    loaded_category_profiles_raw = category_profile_bundle.get("profiles")
    category_profiles = (
        loaded_category_profiles_raw
        if isinstance(loaded_category_profiles_raw, dict)
        else {}
    )
    effective_category, category_profile, category_warnings = resolve_category_profile(
        args.category, category_profiles
    )
    category_profile_source = str(category_profile_bundle.get("source") or "builtin_fallback")
    category_profile_config_path = str(category_profile_bundle.get("config_path") or "")
    category_profile_config_loaded = bool(category_profile_bundle.get("config_loaded"))
    category_profile_config_error_raw = category_profile_bundle.get("config_error")
    category_profile_config_error = (
        str(category_profile_config_error_raw)
        if isinstance(category_profile_config_error_raw, str) and category_profile_config_error_raw
        else None
    )
    category_profile_config_error_detail_raw = category_profile_bundle.get("config_error_detail")
    category_profile_config_error_detail = (
        str(category_profile_config_error_detail_raw)
        if isinstance(category_profile_config_error_detail_raw, str) and category_profile_config_error_detail_raw
        else None
    )
    category_profile_config_version_effective = str(
        category_profile_bundle.get("config_version_effective") or ""
    )
    category_required_inputs_raw = category_profile.get("required_input_files")
    category_required_inputs = (
        [x for x in category_required_inputs_raw if isinstance(x, str) and x]
        if isinstance(category_required_inputs_raw, list)
        else ["run_summary_path", "visited_pages_path", "failed_fetches_path", "output_files"]
    )
    category_support_mode_configured = str(category_profile.get("support_mode") or "active")
    category_support_mode_effective = category_support_mode_configured
    category_required_summary_keys = resolve_required_summary_keys(category_profile)
    category_activation_conditions_raw = category_profile.get("activation_conditions")
    category_activation_conditions = (
        [x for x in category_activation_conditions_raw if isinstance(x, str) and x]
        if isinstance(category_activation_conditions_raw, list)
        else []
    )
    category_reserved_reason = str(category_profile.get("reserved_reason") or "")
    category_profile_version = str(category_profile.get("profile_version") or GUARD_CATEGORY_PROFILE_VERSION)
    category_data_presence: dict[str, Any] | None = None
    if category_profile_config_error is not None:
        category_warnings.append(f"category_profile_config_fallback:{category_profile_config_error}")

    logs_dir = resolve_logs_dir(args.logs_dir)
    timestamp = utc_timestamp_compact()

    # Backward-compatible fallback:
    # If old usage passed --summary-path as input run_summary path, treat it as input when it
    # points to an existing run_summary_* file and --run-summary-path is omitted.
    run_summary_path_arg = args.run_summary_path
    output_summary_path_arg = args.summary_path
    if not run_summary_path_arg and output_summary_path_arg:
        summary_path_candidate = Path(output_summary_path_arg)
        if summary_path_candidate.exists() and summary_path_candidate.name.startswith("run_summary_"):
            run_summary_path_arg = output_summary_path_arg
            output_summary_path_arg = ""

    run_summary_path = (
        Path(run_summary_path_arg)
        if run_summary_path_arg
        else resolve_guard_default_run_summary_path(logs_dir, args.target_year)
    )
    output_path = (
        Path(output_summary_path_arg)
        if output_summary_path_arg
        else logs_dir / OUTPUT_TEMPLATE.format(target_year=args.target_year, timestamp=timestamp)
    )

    check_results: dict[str, Any] = {}
    mismatch_fields: list[str] = []

    summary_obj, summary_load_error = load_json_object(run_summary_path)
    if summary_load_error:
        mismatch_fields.append("run_summary_load_error")
        check_results["run_summary_load"] = {
            "passed": False,
            "path": str(run_summary_path),
            "error": summary_load_error,
        }
        summary_obj = {}
    else:
        check_results["run_summary_load"] = {
            "passed": True,
            "path": str(run_summary_path),
            "error": None,
        }

    assert isinstance(summary_obj, dict)

    missing_summary_keys = sorted(category_required_summary_keys - set(summary_obj.keys()))
    required_keys_passed = len(missing_summary_keys) == 0
    check_results["required_summary_keys"] = {
        "passed": required_keys_passed,
        "missing_keys": missing_summary_keys,
        "required_keys": sorted(category_required_summary_keys),
    }
    if not required_keys_passed:
        mismatch_fields.append("required_summary_keys_missing")

    if effective_category == "artists_text":
        category_data_presence = detect_artists_data_presence(logs_dir, args.target_year, summary_obj)
        if (
            category_support_mode_configured == "reserved_minimal"
            and category_data_presence.get("has_artists_data") is True
        ):
            category_support_mode_effective = "provisional_minimal"
            category_warnings.append(
                "artists_data_detected:support_mode_promoted:reserved_minimal->provisional_minimal"
            )
        elif category_support_mode_configured == "reserved_minimal":
            category_warnings.append("artists_data_not_found:keep_support_mode_reserved_minimal")

    if category_support_mode_effective != "active":
        category_warnings.append(f"category_support_mode:{category_support_mode_effective}")
    if category_reserved_reason and category_support_mode_effective.startswith("reserved"):
        category_warnings.append(f"category_reserved_reason:{category_reserved_reason}")
    category_warnings = dedupe_strings(category_warnings)

    check_results["category_profile"] = {
        "passed": True,
        "requested_category": args.category,
        "effective_category": effective_category,
        "profile_version": category_profile_version,
        "config_source": category_profile_source,
        "config_path": category_profile_config_path,
        "config_loaded": category_profile_config_loaded,
        "config_error": category_profile_config_error,
        "config_error_detail": category_profile_config_error_detail,
        "config_version_effective": category_profile_config_version_effective,
        "support_mode_configured": category_support_mode_configured,
        "support_mode_effective": category_support_mode_effective,
        "required_input_files": category_required_inputs,
        "required_summary_keys": sorted(category_required_summary_keys),
        "required_summary_keys_effective": sorted(category_required_summary_keys),
        "activation_conditions": category_activation_conditions,
        "activation_ready": category_support_mode_effective in {"active", "provisional_minimal", "active_minimal"},
        "warnings": category_warnings,
        "data_presence": category_data_presence,
    }

    # Input paths (summary values can be overridden by CLI args).
    visited_path = resolve_path(args.visited_path, summary_obj.get("visited_pages_path"))
    if visited_path is None:
        visited_path = resolve_guard_default_visited_pages_path(logs_dir, args.target_year)
    failed_path = resolve_path(args.failed_path, summary_obj.get("failed_fetches_path"))
    if failed_path is None:
        failed_path = resolve_guard_default_failed_fetches_path(logs_dir, args.target_year)

    output_files = summary_obj.get("output_files")
    output_file_paths: dict[str, Path] = {}
    output_file_errors: list[str] = []
    output_files_resolution = "from_summary"
    output_files_required = "output_files" in category_required_inputs
    if isinstance(output_files, dict):
        for fair_slug, value in output_files.items():
            if not (isinstance(fair_slug, str) and isinstance(value, str) and value):
                output_file_errors.append(f"invalid_output_file_entry:{fair_slug}")
                continue
            output_file_paths[fair_slug] = Path(value)
    else:
        output_files_resolution = "from_logs_dir_raw_glob_pending"

    if not output_file_paths:
        inferred_output_files, inferred_mode = infer_output_files_from_raw(logs_dir, args.target_year)
        if inferred_output_files:
            output_file_paths = inferred_output_files
            output_files_resolution = inferred_mode
        else:
            if not isinstance(output_files, dict):
                output_file_errors.append("output_files_not_dict")
            output_files_resolution = "missing"

    if output_file_errors and output_files_required:
        mismatch_fields.append("output_files_invalid")

    output_file_checks: dict[str, Any] = {}
    output_file_paths_exist = True
    for fair_slug, path in sorted(output_file_paths.items()):
        record_count, record_error = count_jsonl_records(path)
        exists = path.exists()
        if not exists:
            output_file_paths_exist = False
            if output_files_required:
                mismatch_fields.append(f"output_file_missing:{fair_slug}")
        output_file_checks[fair_slug] = {
            "path": str(path),
            "exists": exists,
            "record_count": record_count,
            "record_count_error": record_error,
        }

    output_files_check_passed = output_file_paths_exist and not output_file_errors
    if not output_files_required:
        output_files_check_passed = True

    check_results["output_files"] = {
        "passed": output_files_check_passed,
        "required_by_category": output_files_required,
        "checked_as": "required" if output_files_required else "optional_reserved",
        "resolution_mode": output_files_resolution,
        "errors": output_file_errors,
        "items": output_file_checks,
    }

    if visited_path is None:
        mismatch_fields.append("visited_path_missing")
        visited_ledger = LedgerLoadResult(
            path=Path(""),
            exists=False,
            format="missing",
            entries={},
            load_error="MISSING_PATH_IN_SUMMARY",
            key_hash_mismatch_count=0,
            missing_hash_field_count=0,
        )
    else:
        visited_ledger = load_guard_ledger(visited_path, hash_field="page_url_hash")
        if visited_ledger.load_error:
            mismatch_fields.append("visited_ledger_load_error")

    if failed_path is None:
        mismatch_fields.append("failed_path_missing")
        failed_ledger = LedgerLoadResult(
            path=Path(""),
            exists=False,
            format="missing",
            entries={},
            load_error="MISSING_PATH_IN_SUMMARY",
            key_hash_mismatch_count=0,
            missing_hash_field_count=0,
        )
    else:
        failed_ledger = load_guard_ledger(failed_path, hash_field="fail_hash")
        if failed_ledger.load_error:
            mismatch_fields.append("failed_ledger_load_error")

    check_results["visited_ledger"] = {
        "passed": visited_ledger.load_error is None
        and visited_ledger.key_hash_mismatch_count == 0
        and visited_ledger.missing_hash_field_count == 0,
        "path": str(visited_ledger.path),
        "exists": visited_ledger.exists,
        "format": visited_ledger.format,
        "entry_count": len(visited_ledger.entries),
        "load_error": visited_ledger.load_error,
        "key_hash_mismatch_count": visited_ledger.key_hash_mismatch_count,
        "missing_hash_field_count": visited_ledger.missing_hash_field_count,
    }
    if visited_ledger.key_hash_mismatch_count > 0:
        mismatch_fields.append("visited_key_hash_mismatch")
    if visited_ledger.missing_hash_field_count > 0:
        mismatch_fields.append("visited_missing_hash_field")

    check_results["failed_ledger"] = {
        "passed": failed_ledger.load_error is None
        and failed_ledger.key_hash_mismatch_count == 0
        and failed_ledger.missing_hash_field_count == 0,
        "path": str(failed_ledger.path),
        "exists": failed_ledger.exists,
        "format": failed_ledger.format,
        "entry_count": len(failed_ledger.entries),
        "load_error": failed_ledger.load_error,
        "key_hash_mismatch_count": failed_ledger.key_hash_mismatch_count,
        "missing_hash_field_count": failed_ledger.missing_hash_field_count,
    }
    if failed_ledger.key_hash_mismatch_count > 0:
        mismatch_fields.append("failed_key_hash_mismatch")
    if failed_ledger.missing_hash_field_count > 0:
        mismatch_fields.append("failed_missing_hash_field")

    # Internal consistency checks
    existing_records_total = safe_int(summary_obj.get("existing_records_total"))
    new_records_saved_total = safe_int(summary_obj.get("new_records_saved_total"))
    records_saved_total = safe_int(summary_obj.get("records_saved_total"))
    records_total_after_run = safe_int(summary_obj.get("records_total_after_run"))

    skipped_total = safe_int(summary_obj.get("skipped_total"))
    skipped_by_reason = summary_obj.get("skipped_by_reason")
    skipped_sum = None
    if isinstance(skipped_by_reason, dict):
        skipped_values = [safe_int(value) for value in skipped_by_reason.values()]
        if all(value is not None for value in skipped_values):
            skipped_sum = sum(value for value in skipped_values if value is not None)

    records_saved_by_fair = summary_obj.get("records_saved_by_fair")
    records_saved_by_fair_sum = None
    if isinstance(records_saved_by_fair, dict):
        fair_values = [safe_int(value) for value in records_saved_by_fair.values()]
        if all(value is not None for value in fair_values):
            records_saved_by_fair_sum = sum(value for value in fair_values if value is not None)

    internal_errors: list[str] = []
    if None in {existing_records_total, new_records_saved_total, records_total_after_run}:
        internal_errors.append("records_total_fields_not_int")
    else:
        expected_total = existing_records_total + new_records_saved_total
        if records_total_after_run != expected_total:
            internal_errors.append(
                f"records_total_after_run_mismatch:{records_total_after_run}!={expected_total}"
            )

    if records_saved_total is None or new_records_saved_total is None:
        internal_errors.append("records_saved_fields_not_int")
    elif records_saved_total != new_records_saved_total:
        internal_errors.append(
            f"records_saved_total_mismatch:{records_saved_total}!={new_records_saved_total}"
        )

    if records_saved_by_fair_sum is None or new_records_saved_total is None:
        internal_errors.append("records_saved_by_fair_not_int")
    elif records_saved_by_fair_sum != new_records_saved_total:
        internal_errors.append(
            f"records_saved_by_fair_sum_mismatch:{records_saved_by_fair_sum}!={new_records_saved_total}"
        )

    if skipped_sum is None or skipped_total is None:
        internal_errors.append("skipped_fields_not_int")
    elif skipped_total != skipped_sum:
        internal_errors.append(f"skipped_total_mismatch:{skipped_total}!={skipped_sum}")

    summary_target_year = safe_int(summary_obj.get("target_year"))
    if summary_target_year is None:
        internal_errors.append("summary_target_year_not_int")
    elif summary_target_year != args.target_year:
        internal_errors.append(f"target_year_mismatch:{summary_target_year}!={args.target_year}")

    check_results["internal_consistency"] = {
        "passed": len(internal_errors) == 0,
        "errors": internal_errors,
        "values": {
            "existing_records_total": existing_records_total,
            "new_records_saved_total": new_records_saved_total,
            "records_saved_total": records_saved_total,
            "records_total_after_run": records_total_after_run,
            "records_saved_by_fair_sum": records_saved_by_fair_sum,
            "skipped_total": skipped_total,
            "skipped_by_reason_sum": skipped_sum,
            "summary_target_year": summary_target_year,
            "cli_target_year": args.target_year,
        },
    }
    if internal_errors:
        mismatch_fields.append("internal_consistency_mismatch")

    # Summary vs ledger count consistency
    visited_total_ledger = safe_int(summary_obj.get("visited_pages_total_ledger"))
    failed_total_ledger = safe_int(summary_obj.get("failed_fetches_total_ledger"))

    summary_ledger_errors: list[str] = []
    if visited_total_ledger is None:
        summary_ledger_errors.append("visited_pages_total_ledger_not_int")
    elif visited_total_ledger != len(visited_ledger.entries):
        summary_ledger_errors.append(
            f"visited_count_mismatch:{visited_total_ledger}!={len(visited_ledger.entries)}"
        )

    if failed_total_ledger is None:
        summary_ledger_errors.append("failed_fetches_total_ledger_not_int")
    elif failed_total_ledger != len(failed_ledger.entries):
        summary_ledger_errors.append(
            f"failed_count_mismatch:{failed_total_ledger}!={len(failed_ledger.entries)}"
        )

    check_results["summary_vs_ledger_counts"] = {
        "passed": len(summary_ledger_errors) == 0,
        "errors": summary_ledger_errors,
        "values": {
            "summary_visited_pages_total_ledger": visited_total_ledger,
            "actual_visited_entries": len(visited_ledger.entries),
            "summary_failed_fetches_total_ledger": failed_total_ledger,
            "actual_failed_entries": len(failed_ledger.entries),
        },
    }
    if summary_ledger_errors:
        mismatch_fields.append("summary_ledger_count_mismatch")

    # Additional guard checks (backward-compatible: missing keys are skipped, not mismatched)
    additional_guard_checks = [
        "GX_SKIP_BREAKDOWN_SUM_MATCH",
        "GX_FAILED_REASON_COUNTS_SUM_MATCH",
        "GX_RECORDS_RELATIONS_MATCH",
    ]
    additional_guard_check_results: dict[str, Any] = {}
    missing_keys: list[str] = []
    skipped_checks: list[str] = []

    skip_counts_key: str | None = None
    if "skip_breakdown" in summary_obj:
        skip_counts_key = "skip_breakdown"
    elif "skipped_by_reason" in summary_obj:
        skip_counts_key = "skipped_by_reason"

    if skip_counts_key is None:
        skipped_checks.append("GX_SKIP_BREAKDOWN_SUM_MATCH")
        missing_keys.extend(["skip_breakdown", "skipped_by_reason"])
        additional_guard_check_results["GX_SKIP_BREAKDOWN_SUM_MATCH"] = {
            "status": "skipped_backward_compatible",
            "passed": None,
            "missing_keys": ["skip_breakdown", "skipped_by_reason"],
            "reason": "skip counter map key missing",
        }
    elif skipped_total is None:
        skipped_checks.append("GX_SKIP_BREAKDOWN_SUM_MATCH")
        missing_keys.append("skipped_total")
        additional_guard_check_results["GX_SKIP_BREAKDOWN_SUM_MATCH"] = {
            "status": "skipped_backward_compatible",
            "passed": None,
            "used_key": skip_counts_key,
            "missing_keys": ["skipped_total"],
            "reason": "skipped_total missing or non-int",
        }
    else:
        parsed_map, parse_errors = parse_counter_map(summary_obj.get(skip_counts_key))
        if parsed_map is None or parse_errors:
            mismatch_fields.append("GX_SKIP_BREAKDOWN_SUM_MISMATCH")
            additional_guard_check_results["GX_SKIP_BREAKDOWN_SUM_MATCH"] = {
                "status": "failed",
                "passed": False,
                "used_key": skip_counts_key,
                "errors": parse_errors or ["invalid_counter_map"],
            }
        else:
            breakdown_sum = sum(parsed_map.values())
            passed = breakdown_sum == skipped_total
            if not passed:
                mismatch_fields.append("GX_SKIP_BREAKDOWN_SUM_MISMATCH")
            additional_guard_check_results["GX_SKIP_BREAKDOWN_SUM_MATCH"] = {
                "status": "checked",
                "passed": passed,
                "used_key": skip_counts_key,
                "breakdown_sum": breakdown_sum,
                "skipped_total": skipped_total,
            }

    failed_reasons_key = "failed_fetches_reason_counts"
    if failed_reasons_key not in summary_obj:
        skipped_checks.append("GX_FAILED_REASON_COUNTS_SUM_MATCH")
        missing_keys.append(failed_reasons_key)
        additional_guard_check_results["GX_FAILED_REASON_COUNTS_SUM_MATCH"] = {
            "status": "skipped_backward_compatible",
            "passed": None,
            "missing_keys": [failed_reasons_key],
            "reason": "failed reason counter map key missing",
        }
    elif failed_total_ledger is None:
        skipped_checks.append("GX_FAILED_REASON_COUNTS_SUM_MATCH")
        missing_keys.append("failed_fetches_total_ledger")
        additional_guard_check_results["GX_FAILED_REASON_COUNTS_SUM_MATCH"] = {
            "status": "skipped_backward_compatible",
            "passed": None,
            "used_key": failed_reasons_key,
            "missing_keys": ["failed_fetches_total_ledger"],
            "reason": "failed_fetches_total_ledger missing or non-int",
        }
    else:
        parsed_map, parse_errors = parse_counter_map(summary_obj.get(failed_reasons_key))
        if parsed_map is None or parse_errors:
            mismatch_fields.append("GX_FAILED_REASON_COUNTS_SUM_MISMATCH")
            additional_guard_check_results["GX_FAILED_REASON_COUNTS_SUM_MATCH"] = {
                "status": "failed",
                "passed": False,
                "used_key": failed_reasons_key,
                "errors": parse_errors or ["invalid_counter_map"],
            }
        else:
            reason_sum = sum(parsed_map.values())
            passed = reason_sum == failed_total_ledger
            if not passed:
                mismatch_fields.append("GX_FAILED_REASON_COUNTS_SUM_MISMATCH")
            additional_guard_check_results["GX_FAILED_REASON_COUNTS_SUM_MATCH"] = {
                "status": "checked",
                "passed": passed,
                "used_key": failed_reasons_key,
                "reason_sum": reason_sum,
                "failed_fetches_total_ledger": failed_total_ledger,
            }

    required_record_keys = ["existing_records_total", "new_records_saved_total", "records_total_after_run"]
    missing_record_keys = [key for key in required_record_keys if key not in summary_obj]
    if missing_record_keys:
        skipped_checks.append("GX_RECORDS_RELATIONS_MATCH")
        missing_keys.extend(missing_record_keys)
        additional_guard_check_results["GX_RECORDS_RELATIONS_MATCH"] = {
            "status": "skipped_backward_compatible",
            "passed": None,
            "missing_keys": missing_record_keys,
            "reason": "required records keys missing",
        }
    elif None in {existing_records_total, new_records_saved_total, records_total_after_run}:
        skipped_checks.append("GX_RECORDS_RELATIONS_MATCH")
        for key, value in (
            ("existing_records_total", existing_records_total),
            ("new_records_saved_total", new_records_saved_total),
            ("records_total_after_run", records_total_after_run),
        ):
            if value is None:
                missing_keys.append(key)
        additional_guard_check_results["GX_RECORDS_RELATIONS_MATCH"] = {
            "status": "skipped_backward_compatible",
            "passed": None,
            "missing_keys": [k for k in ("existing_records_total", "new_records_saved_total", "records_total_after_run") if k in missing_keys],
            "reason": "required records values are non-int",
        }
    else:
        expected_after = existing_records_total + new_records_saved_total
        base_passed = records_total_after_run == expected_after

        records_saved_semantics = "missing"
        records_saved_relation_passed = True
        if "records_saved_total" in summary_obj:
            if records_saved_total is None:
                records_saved_semantics = "invalid_non_int"
                records_saved_relation_passed = False
            elif records_saved_total == new_records_saved_total:
                records_saved_semantics = "new_saved_semantics"
            elif records_saved_total == records_total_after_run:
                records_saved_semantics = "after_run_semantics"
            else:
                records_saved_semantics = "inconsistent"
                records_saved_relation_passed = False

        passed = base_passed and records_saved_relation_passed
        if not passed:
            mismatch_fields.append("GX_RECORDS_RELATIONS_MISMATCH")
        additional_guard_check_results["GX_RECORDS_RELATIONS_MATCH"] = {
            "status": "checked",
            "passed": passed,
            "records_total_after_run": records_total_after_run,
            "expected_after_run": expected_after,
            "records_saved_total": records_saved_total,
            "records_saved_semantics": records_saved_semantics,
            "records_saved_relation_passed": records_saved_relation_passed,
        }

    missing_keys = dedupe_strings(missing_keys)
    skipped_checks = dedupe_strings(skipped_checks)
    check_results["additional_guard_checks"] = {
        "checks": additional_guard_checks,
        "results": additional_guard_check_results,
        "missing_keys": missing_keys,
        "skipped_checks": skipped_checks,
    }

    failed_schema_check = validate_failed_fetch_schema(failed_ledger.entries)
    check_results["failed_fetches_schema"] = failed_schema_check
    if not failed_schema_check["passed"]:
        mismatch_fields.append("failed_fetches_schema_invalid")

    manifest_path = Path(args.manifest_path) if args.manifest_path else None
    manifest_check = load_manifest_check(manifest_path, args.target_year)
    check_results["manifest"] = manifest_check
    if not manifest_check.get("passed", False):
        mismatch_fields.append("manifest_invalid")

    # Deduplicate mismatch fields, preserve first-seen order.
    deduped_mismatches: list[str] = []
    seen: set[str] = set()
    for item in mismatch_fields:
        if item in seen:
            continue
        seen.add(item)
        deduped_mismatches.append(item)

    guard_passed = len(deduped_mismatches) == 0

    required_input_files_effective: list[dict[str, Any]] = []
    for required_name in category_required_inputs:
        if required_name == "run_summary_path":
            required_input_files_effective.append(
                {
                    "name": required_name,
                    "path": str(run_summary_path),
                    "exists": run_summary_path.exists(),
                }
            )
        elif required_name == "visited_pages_path":
            required_input_files_effective.append(
                {
                    "name": required_name,
                    "path": str(visited_path) if visited_path else None,
                    "exists": bool(visited_path and visited_path.exists()),
                }
            )
        elif required_name == "failed_fetches_path":
            required_input_files_effective.append(
                {
                    "name": required_name,
                    "path": str(failed_path) if failed_path else None,
                    "exists": bool(failed_path and failed_path.exists()),
                }
            )
        elif required_name == "output_files":
            required_input_files_effective.append(
                {
                    "name": required_name,
                    "count": len(output_file_paths),
                    "all_exist": output_file_paths_exist,
                    "items": {fair_slug: str(path) for fair_slug, path in sorted(output_file_paths.items())},
                }
            )
        else:
            required_input_files_effective.append(
                {
                    "name": required_name,
                    "status": "unknown_required_input_key",
                }
            )

    summary_payload = {
        "started_at": started_at,
        "completed_at": utc_now_iso(),
        "generated_by": GENERATED_BY,
        "guard_schema_version": GUARD_SCHEMA_VERSION,
        "category": args.category,
        "category_profile_version": category_profile_version,
        "category_profile_source": category_profile_source,
        "category_profile_config_path": category_profile_config_path,
        "category_profile_config_loaded": category_profile_config_loaded,
        "category_profile_config_error": category_profile_config_error,
        "category_profile_config_error_detail": category_profile_config_error_detail,
        "category_profile_config_version_effective": category_profile_config_version_effective,
        "category_required_files_profile": effective_category,
        "required_input_files_effective": required_input_files_effective,
        "required_summary_keys_effective": sorted(category_required_summary_keys),
        "category_support_mode": category_support_mode_effective,
        "category_support_mode_configured": category_support_mode_configured,
        "category_warnings": category_warnings,
        "category_activation_conditions": category_activation_conditions,
        "category_data_presence": category_data_presence,
        "logs_dir": str(logs_dir),
        "target_year": args.target_year,
        "fail_on_mismatch": bool(args.fail_on_mismatch),
        "guard_passed": guard_passed,
        "mismatches": len(deduped_mismatches),
        "mismatch_fields": deduped_mismatches,
        "additional_guard_checks": additional_guard_checks,
        "additional_guard_check_results": additional_guard_check_results,
        "missing_keys": missing_keys,
        "skipped_checks": skipped_checks,
        "input_paths": {
            "run_summary_path": str(run_summary_path),
            "visited_pages_path": str(visited_path) if visited_path else None,
            "failed_fetches_path": str(failed_path) if failed_path else None,
            "manifest_path": str(manifest_path) if manifest_path else None,
            "output_files": {fair_slug: str(path) for fair_slug, path in sorted(output_file_paths.items())},
        },
        "check_results": check_results,
    }
    write_summary_json(output_path, summary_payload)

    print(
        "[DONE] Phase1 guard compare complete. "
        f"guard_passed={guard_passed} mismatches={len(deduped_mismatches)}"
    )
    if deduped_mismatches:
        print(f"[DONE] mismatch_fields={deduped_mismatches}")
    print(f"[DONE] summary={output_path}")

    if args.fail_on_mismatch and not guard_passed:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
