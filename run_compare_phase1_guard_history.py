#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from phase1_guard_common import (
    DEFAULT_GUARD_CATEGORY,
    EXIT_CODE_MEANING,
    GUARD_CATEGORY_COMPATIBILITY_POLICY,
    GUARD_SCHEMA_VERSION_POLICY,
    INCOMPATIBLE_EXIT_CODE,
    REGRESSION_EXIT_CODE,
    paths_equal,
    resolve_logs_dir,
    utc_now_iso,
    utc_timestamp_compact,
    write_summary_json,
)

OUTPUT_TEMPLATE = "phase1_guard_history_compare_{timestamp}.json"
EXPECTED_GENERATOR = "run_compare_phase1_guard.py"
EXPECTED_SIGNATURE_KEYS = {"guard_passed", "mismatch_fields", "check_results", "input_paths", "target_year"}
SUMMARY_FILENAME_PATTERN = re.compile(r"^phase1_guard_summary_(\d{4})_(\d{8}T\d{6}Z)\.json$")
DEFAULT_SUMMARY_GLOB = "phase1_guard_summary_*.json"


@dataclass
class BaselineCandidate:
    path: Path
    load_error: str | None
    generated_ok: bool
    generated_reason: str
    target_year: int | None
    target_year_matches: bool
    schema_version: str | None
    schema_matches_current: bool | None
    guard_passed: bool | None
    sort_time: datetime | None
    is_past_current: bool
    mandatory_compatible: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare two Phase1 guard summaries and detect regressions."
    )
    parser.add_argument("--current-summary", required=True, help="current phase1 guard summary json path")
    parser.add_argument("--baseline-summary", default="", help="baseline phase1 guard summary json path")
    parser.add_argument(
        "--baseline-search-dir",
        default="",
        help="directory for auto baseline search when --baseline-summary is omitted (default: current summary parent)",
    )
    parser.add_argument(
        "--summary-glob",
        default=DEFAULT_SUMMARY_GLOB,
        help="glob pattern for auto baseline candidates (default: phase1_guard_summary_*.json)",
    )
    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="return non-zero when regression or incompatible comparison is detected",
    )
    parser.add_argument(
        "--strict-compatibility",
        action="store_true",
        help="return non-zero when compatibility checks fail (exit 3)",
    )
    parser.add_argument(
        "--output-path",
        default="",
        help="optional output summary path (default: <current-summary-parent>/phase1_guard_history_compare_<timestamp>.json)",
    )
    return parser.parse_args()


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


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        return normalized in {"1", "true", "yes", "on"}
    return False


def parse_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    values: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        if item not in values:
            values.append(item)
    return values


def parse_iso_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def parse_summary_time_from_filename(path: Path) -> datetime | None:
    match = SUMMARY_FILENAME_PATTERN.match(path.name)
    if not match:
        return None
    timestamp_raw = match.group(2)
    try:
        return datetime.strptime(timestamp_raw, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def resolve_summary_sort_time(path: Path, summary_obj: dict[str, Any] | None) -> datetime | None:
    by_name = parse_summary_time_from_filename(path)
    if by_name is not None:
        return by_name
    if isinstance(summary_obj, dict):
        for key in ("completed_at", "started_at"):
            parsed = parse_iso_utc(summary_obj.get(key))
            if parsed is not None:
                return parsed
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    except OSError:
        return None


def detect_generated_by(summary_obj: dict[str, Any]) -> tuple[bool, str]:
    generated_by = summary_obj.get("generated_by")
    if isinstance(generated_by, str) and generated_by:
        if generated_by == EXPECTED_GENERATOR:
            return True, "explicit_generated_by"
        return False, f"generated_by_unexpected:{generated_by}"

    # Backward-compatible fallback for older TASK18 outputs.
    if EXPECTED_SIGNATURE_KEYS.issubset(set(summary_obj.keys())):
        return True, "inferred_by_signature"
    return False, "missing_generated_by_and_signature_mismatch"


def extract_metrics(summary_obj: dict[str, Any]) -> dict[str, int | None]:
    check_results = summary_obj.get("check_results")
    if not isinstance(check_results, dict):
        return {
            "records_saved_total": None,
            "skipped_total": None,
            "failed_fetches_total_ledger": None,
            "visited_pages_total_ledger": None,
            "mismatches": safe_int(summary_obj.get("mismatches")),
        }

    internal_values = (
        check_results.get("internal_consistency", {}).get("values", {})
        if isinstance(check_results.get("internal_consistency"), dict)
        else {}
    )
    ledger_values = (
        check_results.get("summary_vs_ledger_counts", {}).get("values", {})
        if isinstance(check_results.get("summary_vs_ledger_counts"), dict)
        else {}
    )

    if not isinstance(internal_values, dict):
        internal_values = {}
    if not isinstance(ledger_values, dict):
        ledger_values = {}

    mismatches = safe_int(summary_obj.get("mismatches"))
    if mismatches is None:
        mismatches = len(parse_string_list(summary_obj.get("mismatch_fields")))

    return {
        "records_saved_total": safe_int(internal_values.get("records_saved_total")),
        "skipped_total": safe_int(internal_values.get("skipped_total")),
        "failed_fetches_total_ledger": safe_int(ledger_values.get("summary_failed_fetches_total_ledger")),
        "visited_pages_total_ledger": safe_int(ledger_values.get("summary_visited_pages_total_ledger")),
        "mismatches": mismatches,
    }


def diff_metric(name: str, current: dict[str, int | None], baseline: dict[str, int | None]) -> dict[str, int | None]:
    current_value = current.get(name)
    baseline_value = baseline.get(name)
    delta: int | None = None
    if current_value is not None and baseline_value is not None:
        delta = current_value - baseline_value
    return {
        "baseline": baseline_value,
        "current": current_value,
        "delta": delta,
    }


def normalize_schema_version(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized if normalized else None


def evaluate_guard_schema_version_compatibility(
    current_version: str | None,
    baseline_version: str | None,
) -> dict[str, Any]:
    if current_version is not None and baseline_version is not None:
        mode = "both_present"
        compatible = current_version == baseline_version
        warnings: list[str] = []
        errors: list[str] = []
        if not compatible:
            errors.append(f"guard_schema_version_mismatch:{baseline_version}!={current_version}")
    elif current_version is not None:
        mode = "current_only"
        compatible = True
        warnings = ["baseline_guard_schema_version_missing"]
        errors = []
    elif baseline_version is not None:
        mode = "baseline_only"
        compatible = True
        warnings = ["current_guard_schema_version_missing"]
        errors = []
    else:
        mode = "both_missing"
        compatible = True
        warnings = ["current_guard_schema_version_missing", "baseline_guard_schema_version_missing"]
        errors = []

    return {
        "current_guard_schema_version": current_version,
        "baseline_guard_schema_version": baseline_version,
        "guard_schema_version_comparison_mode": mode,
        "guard_schema_version_compatible": compatible,
        "guard_schema_version_policy": GUARD_SCHEMA_VERSION_POLICY,
        "compatibility_warnings": warnings,
        "compatibility_errors": errors,
    }


def normalize_category(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized if normalized else None


def evaluate_category_compatibility(
    current_category: str | None,
    baseline_category: str | None,
) -> dict[str, Any]:
    if current_category is not None and baseline_category is not None:
        comparison_mode = "both_present"
        category_compatible = current_category == baseline_category
        if category_compatible:
            effective = current_category
            warnings: list[str] = []
            errors: list[str] = []
        else:
            effective = "unresolved_mismatch"
            warnings = [f"category_mismatch:{baseline_category}!={current_category}"]
            errors = [f"category_mismatch:{baseline_category}!={current_category}"]
    elif current_category is not None:
        comparison_mode = "current_only"
        category_compatible = True
        effective = current_category
        warnings = ["baseline_category_missing"]
        errors = []
    elif baseline_category is not None:
        comparison_mode = "baseline_only"
        category_compatible = True
        effective = baseline_category
        warnings = ["current_category_missing"]
        errors = []
    else:
        comparison_mode = "both_missing"
        category_compatible = True
        effective = DEFAULT_GUARD_CATEGORY
        warnings = [
            "current_category_missing",
            "baseline_category_missing",
            f"default_category_assumed:{DEFAULT_GUARD_CATEGORY}",
        ]
        errors = []

    return {
        "current_category": current_category,
        "baseline_category": baseline_category,
        "category_comparison_mode": comparison_mode,
        "category_effective_for_comparison": effective,
        "category_compatible": category_compatible,
        "category_compatibility_policy": GUARD_CATEGORY_COMPATIBILITY_POLICY,
        "category_warnings": warnings,
        "category_compatibility_errors": errors,
    }


def normalize_additional_check_state(entry: Any) -> str:
    if not isinstance(entry, dict):
        return "skipped"

    passed = entry.get("passed")
    if isinstance(passed, bool):
        return "pass" if passed else "fail"

    status = entry.get("status")
    if isinstance(status, str) and "skip" in status.lower():
        return "skipped"

    return "skipped"


def extract_additional_check_state_map(summary_obj: dict[str, Any]) -> tuple[dict[str, str], bool]:
    raw = summary_obj.get("additional_guard_check_results")
    if not isinstance(raw, dict):
        return {}, False

    state_map: dict[str, str] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not key:
            continue
        state_map[key] = normalize_additional_check_state(value)
    return state_map, True


def build_additional_guard_checks_diff(current_obj: dict[str, Any], baseline_obj: dict[str, Any]) -> dict[str, Any]:
    current_state_map, current_present = extract_additional_check_state_map(current_obj)
    baseline_state_map, baseline_present = extract_additional_check_state_map(baseline_obj)

    if current_present and baseline_present:
        comparison_mode = "both_present"
        missing_in: list[str] = []
    elif current_present:
        comparison_mode = "current_only"
        missing_in = ["baseline"]
    elif baseline_present:
        comparison_mode = "baseline_only"
        missing_in = ["current"]
    else:
        comparison_mode = "both_missing"
        missing_in = ["baseline", "current"]

    current_keys = set(current_state_map.keys())
    baseline_keys = set(baseline_state_map.keys())
    common_keys = sorted(current_keys & baseline_keys)
    added_checks = sorted(current_keys - baseline_keys)
    removed_checks = sorted(baseline_keys - current_keys)

    changed_to_fail: list[str] = []
    changed_to_pass: list[str] = []
    changed_to_skipped: list[str] = []
    changed_from_skipped: list[str] = []
    unchanged_pass: list[str] = []
    unchanged_fail: list[str] = []
    unchanged_skipped: list[str] = []
    transitions: dict[str, dict[str, str]] = {}

    for check_id in common_keys:
        baseline_state = baseline_state_map[check_id]
        current_state = current_state_map[check_id]
        if baseline_state == current_state:
            if current_state == "pass":
                unchanged_pass.append(check_id)
            elif current_state == "fail":
                unchanged_fail.append(check_id)
            else:
                unchanged_skipped.append(check_id)
            continue

        transitions[check_id] = {"baseline": baseline_state, "current": current_state}
        if current_state == "fail":
            changed_to_fail.append(check_id)
        if current_state == "pass":
            changed_to_pass.append(check_id)
        if current_state == "skipped":
            changed_to_skipped.append(check_id)
        if baseline_state == "skipped" and current_state in {"pass", "fail"}:
            changed_from_skipped.append(check_id)

    for check_id in added_checks:
        transitions[check_id] = {"baseline": "missing", "current": current_state_map[check_id]}
    for check_id in removed_checks:
        transitions[check_id] = {"baseline": baseline_state_map[check_id], "current": "missing"}

    changed_fields = sorted(
        set(changed_to_fail)
        | set(changed_to_pass)
        | set(changed_to_skipped)
        | set(changed_from_skipped)
        | set(added_checks)
        | set(removed_checks)
    )

    return {
        "comparison_mode": comparison_mode,
        "missing_in": missing_in,
        "diff": {
            "changed_to_fail": changed_to_fail,
            "changed_to_pass": changed_to_pass,
            "changed_to_skipped": changed_to_skipped,
            "changed_from_skipped": changed_from_skipped,
            "unchanged_pass": unchanged_pass,
            "unchanged_fail": unchanged_fail,
            "unchanged_skipped": unchanged_skipped,
            "added_checks": added_checks,
            "removed_checks": removed_checks,
        },
        "changed_fields": changed_fields,
        "transitions": transitions,
    }


def build_candidate(
    *,
    path: Path,
    current_path: Path,
    current_target_year: int | None,
    current_schema_version: str | None,
    current_time: datetime | None,
) -> BaselineCandidate:
    obj, load_error = load_json_object(path)
    if obj is None:
        obj = {}

    generated_ok, generated_reason = detect_generated_by(obj)
    target_year = safe_int(obj.get("target_year"))
    target_year_matches = current_target_year is not None and target_year == current_target_year

    schema_version = normalize_schema_version(obj.get("guard_schema_version"))
    if current_schema_version is None or schema_version is None:
        schema_matches_current: bool | None = None
    else:
        schema_matches_current = schema_version == current_schema_version

    guard_passed: bool | None
    if "guard_passed" in obj:
        guard_passed = parse_bool(obj.get("guard_passed"))
    else:
        guard_passed = None

    sort_time = resolve_summary_sort_time(path, obj)
    is_past_current = bool(sort_time is not None and current_time is not None and sort_time < current_time)

    mandatory_compatible = load_error is None and generated_ok and target_year_matches and not paths_equal(path, current_path)

    return BaselineCandidate(
        path=path,
        load_error=load_error,
        generated_ok=generated_ok,
        generated_reason=generated_reason,
        target_year=target_year,
        target_year_matches=target_year_matches,
        schema_version=schema_version,
        schema_matches_current=schema_matches_current,
        guard_passed=guard_passed,
        sort_time=sort_time,
        is_past_current=is_past_current,
        mandatory_compatible=mandatory_compatible,
    )


def candidate_to_dict(candidate: BaselineCandidate) -> dict[str, Any]:
    return {
        "path": str(candidate.path),
        "load_error": candidate.load_error,
        "generated_ok": candidate.generated_ok,
        "generated_reason": candidate.generated_reason,
        "target_year": candidate.target_year,
        "target_year_matches": candidate.target_year_matches,
        "schema_version": candidate.schema_version,
        "schema_matches_current": candidate.schema_matches_current,
        "guard_passed": candidate.guard_passed,
        "sort_time": candidate.sort_time.isoformat().replace("+00:00", "Z") if candidate.sort_time else None,
        "is_past_current": candidate.is_past_current,
        "mandatory_compatible": candidate.mandatory_compatible,
    }


def select_auto_baseline(
    *,
    current_path: Path,
    current_obj: dict[str, Any],
    search_dir: Path,
    summary_glob: str,
) -> tuple[Path | None, str, str, int, list[str], list[dict[str, Any]]]:
    current_target_year = safe_int(current_obj.get("target_year"))
    current_schema_version = normalize_schema_version(current_obj.get("guard_schema_version"))
    current_time = resolve_summary_sort_time(current_path, current_obj)

    candidates: list[BaselineCandidate] = []
    try:
        raw_paths = sorted(search_dir.glob(summary_glob))
    except OSError:
        raw_paths = []

    for path in raw_paths:
        if paths_equal(path, current_path):
            continue
        candidates.append(
            build_candidate(
                path=path,
                current_path=current_path,
                current_target_year=current_target_year,
                current_schema_version=current_schema_version,
                current_time=current_time,
            )
        )

    candidate_dicts = [candidate_to_dict(x) for x in candidates]
    candidate_paths = [str(x.path) for x in candidates]

    mandatory_candidates = [x for x in candidates if x.mandatory_compatible]
    if not mandatory_candidates:
        return (
            None,
            "auto_not_found",
            "no_baseline_found: no mandatory-compatible candidate",
            len(candidates),
            candidate_paths,
            candidate_dicts,
        )

    # Prefer summaries older than current.
    older_candidates = [x for x in mandatory_candidates if x.is_past_current]
    pool = older_candidates if older_candidates else mandatory_candidates
    older_priority_applied = len(older_candidates) > 0

    # Prefer schema version match when current has schema_version and matching candidates exist.
    schema_priority_applied = False
    if current_schema_version is not None:
        schema_matched = [x for x in pool if x.schema_matches_current is True]
        if schema_matched:
            pool = schema_matched
            schema_priority_applied = True

    # Prefer guard_passed=True baseline.
    passed_pool = [x for x in pool if x.guard_passed is True]
    if passed_pool:
        pool = passed_pool
        resolution_mode = "auto_latest_passed"
    else:
        resolution_mode = "auto_latest_compatible"

    def sort_key(candidate: BaselineCandidate) -> tuple[int, datetime]:
        ts = candidate.sort_time if candidate.sort_time is not None else datetime.min.replace(tzinfo=timezone.utc)
        return (0 if candidate.sort_time is None else 1, ts)

    selected = max(pool, key=sort_key)
    reason_parts = ["auto-selected compatible candidate"]
    if older_priority_applied:
        reason_parts.append("preferred_past_summary")
    else:
        reason_parts.append("past_summary_not_found_fallback")
    if schema_priority_applied:
        reason_parts.append("preferred_schema_match")
    else:
        reason_parts.append("schema_match_not_applied")
    if resolution_mode == "auto_latest_passed":
        reason_parts.append("preferred_guard_passed_true")
    else:
        reason_parts.append("guard_passed_true_not_found")

    return (
        selected.path,
        resolution_mode,
        "; ".join(reason_parts),
        len(candidates),
        candidate_paths,
        candidate_dicts,
    )


def main() -> int:
    args = parse_args()
    started_at = utc_now_iso()
    print(f"[START] Phase1 guard history compare at {started_at}")

    current_path = resolve_logs_dir(args.current_summary)

    compatibility_errors: list[str] = []
    compatibility_warnings: list[str] = []

    current_obj, current_err = load_json_object(current_path)
    if current_err:
        compatibility_errors.append(f"current_summary_load_error:{current_err}")
    if current_obj is None:
        current_obj = {}

    baseline_auto_search_dir = resolve_logs_dir(args.baseline_search_dir) if args.baseline_search_dir else current_path.parent
    baseline_resolution_mode = "manual" if args.baseline_summary else "auto"
    baseline_selected_reason = "manual_baseline_argument:auto_search_skipped" if args.baseline_summary else ""
    baseline_candidates_checked = 0
    baseline_candidate_paths: list[str] = []
    baseline_candidate_details: list[dict[str, Any]] = []

    if args.baseline_summary:
        baseline_path: Path | None = Path(args.baseline_summary)
    else:
        if current_err:
            baseline_path = None
            baseline_resolution_mode = "auto_not_found"
            baseline_selected_reason = "no_baseline_found: current summary load failed"
            compatibility_errors.append("no_baseline_found")
        else:
            (
                baseline_path,
                baseline_resolution_mode,
                baseline_selected_reason,
                baseline_candidates_checked,
                baseline_candidate_paths,
                baseline_candidate_details,
            ) = select_auto_baseline(
                current_path=current_path,
                current_obj=current_obj,
                search_dir=baseline_auto_search_dir,
                summary_glob=args.summary_glob,
            )
            if baseline_path is None:
                compatibility_errors.append("no_baseline_found")

    baseline_obj: dict[str, Any]
    if baseline_path is None:
        baseline_obj = {}
        baseline_err = "MISSING_BASELINE"
    else:
        baseline_obj_or_none, baseline_err = load_json_object(baseline_path)
        baseline_obj = baseline_obj_or_none if baseline_obj_or_none is not None else {}

    if baseline_err:
        compatibility_errors.append(f"baseline_summary_load_error:{baseline_err}")

    current_generator_ok, current_generator_reason = detect_generated_by(current_obj)
    baseline_generator_ok, baseline_generator_reason = detect_generated_by(baseline_obj)
    if not current_generator_ok:
        compatibility_errors.append(f"current_summary_generator_invalid:{current_generator_reason}")
    elif current_generator_reason == "inferred_by_signature":
        compatibility_warnings.append("current_summary_generator_inferred_by_signature")

    if not baseline_generator_ok:
        compatibility_errors.append(f"baseline_summary_generator_invalid:{baseline_generator_reason}")
    elif baseline_generator_reason == "inferred_by_signature":
        compatibility_warnings.append("baseline_summary_generator_inferred_by_signature")

    current_target_year = safe_int(current_obj.get("target_year"))
    baseline_target_year = safe_int(baseline_obj.get("target_year"))
    if current_target_year is None:
        compatibility_errors.append("current_target_year_missing_or_invalid")
    if baseline_target_year is None:
        compatibility_errors.append("baseline_target_year_missing_or_invalid")
    if current_target_year is not None and baseline_target_year is not None and current_target_year != baseline_target_year:
        compatibility_errors.append(
            f"target_year_mismatch:{baseline_target_year}!={current_target_year}"
        )

    current_schema_version = normalize_schema_version(current_obj.get("guard_schema_version"))
    baseline_schema_version = normalize_schema_version(baseline_obj.get("guard_schema_version"))
    schema_version_eval = evaluate_guard_schema_version_compatibility(
        current_version=current_schema_version,
        baseline_version=baseline_schema_version,
    )
    compatibility_errors.extend(schema_version_eval["compatibility_errors"])
    compatibility_warnings.extend(schema_version_eval["compatibility_warnings"])

    current_category = normalize_category(current_obj.get("category"))
    baseline_category = normalize_category(baseline_obj.get("category"))
    category_eval = evaluate_category_compatibility(
        current_category=current_category,
        baseline_category=baseline_category,
    )
    compatibility_warnings.extend(category_eval["category_warnings"])
    if args.strict_compatibility and not category_eval["category_compatible"]:
        compatibility_errors.extend(category_eval["category_compatibility_errors"])

    comparison_compatible = len(compatibility_errors) == 0

    current_mismatch_fields = parse_string_list(current_obj.get("mismatch_fields"))
    baseline_mismatch_fields = parse_string_list(baseline_obj.get("mismatch_fields"))

    current_set = set(current_mismatch_fields)
    baseline_set = set(baseline_mismatch_fields)
    added_fields = sorted(current_set - baseline_set)
    removed_fields = sorted(baseline_set - current_set)
    common_fields = sorted(current_set & baseline_set)

    current_metrics = extract_metrics(current_obj)
    baseline_metrics = extract_metrics(baseline_obj)

    diffs = {
        "records_saved_total": diff_metric("records_saved_total", current_metrics, baseline_metrics),
        "skipped_total": diff_metric("skipped_total", current_metrics, baseline_metrics),
        "failed_fetches_total_ledger": diff_metric("failed_fetches_total_ledger", current_metrics, baseline_metrics),
        "visited_pages_total_ledger": diff_metric("visited_pages_total_ledger", current_metrics, baseline_metrics),
        "mismatches": diff_metric("mismatches", current_metrics, baseline_metrics),
        "mismatch_fields": {
            "added": added_fields,
            "removed": removed_fields,
            "common": common_fields,
            "baseline_count": len(baseline_mismatch_fields),
            "current_count": len(current_mismatch_fields),
        },
    }
    additional_checks_diff = build_additional_guard_checks_diff(current_obj, baseline_obj)

    regression_reasons: list[str] = []
    if comparison_compatible:
        baseline_guard_passed = parse_bool(baseline_obj.get("guard_passed"))
        current_guard_passed = parse_bool(current_obj.get("guard_passed"))
        if baseline_guard_passed and not current_guard_passed:
            regression_reasons.append("guard_passed_regressed:true->false")

        baseline_mismatches = baseline_metrics.get("mismatches")
        current_mismatches = current_metrics.get("mismatches")
        if baseline_mismatches is not None and current_mismatches is not None and current_mismatches > baseline_mismatches:
            regression_reasons.append(
                f"mismatches_increased:{baseline_mismatches}->{current_mismatches}"
            )

        if added_fields:
            regression_reasons.append(f"new_mismatch_fields:{','.join(added_fields)}")
    else:
        regression_reasons.append("comparison_incompatible")

    regression_passed = comparison_compatible and len(regression_reasons) == 0

    if comparison_compatible:
        if args.fail_on_regression and not regression_passed:
            exit_code = REGRESSION_EXIT_CODE
        else:
            exit_code = 0
    else:
        if args.strict_compatibility or args.fail_on_regression:
            exit_code = INCOMPATIBLE_EXIT_CODE
        else:
            exit_code = 0

    timestamp = utc_timestamp_compact()
    output_path = (
        resolve_logs_dir(args.output_path)
        if args.output_path
        else current_path.parent / OUTPUT_TEMPLATE.format(timestamp=timestamp)
    )

    payload = {
        "started_at": started_at,
        "completed_at": utc_now_iso(),
        "generated_by": "run_compare_phase1_guard_history.py",
        "current_summary_path": str(current_path),
        "baseline_summary_path": str(baseline_path) if baseline_path else None,
        "comparison_compatible": comparison_compatible,
        "compatibility_errors": compatibility_errors,
        "compatibility_warnings": compatibility_warnings,
        "baseline_resolution_mode": baseline_resolution_mode,
        "baseline_candidates_checked": baseline_candidates_checked,
        "baseline_selected_reason": baseline_selected_reason,
        "baseline_auto_search_dir": str(baseline_auto_search_dir) if not args.baseline_summary else None,
        "summary_glob_effective": args.summary_glob,
        "current_guard_schema_version": schema_version_eval["current_guard_schema_version"],
        "baseline_guard_schema_version": schema_version_eval["baseline_guard_schema_version"],
        "guard_schema_version_comparison_mode": schema_version_eval["guard_schema_version_comparison_mode"],
        "guard_schema_version_compatible": schema_version_eval["guard_schema_version_compatible"],
        "guard_schema_version_policy": schema_version_eval["guard_schema_version_policy"],
        "current_category": category_eval["current_category"],
        "baseline_category": category_eval["baseline_category"],
        "category_comparison_mode": category_eval["category_comparison_mode"],
        "category_effective_for_comparison": category_eval["category_effective_for_comparison"],
        "category_compatible": category_eval["category_compatible"],
        "category_compatibility_policy": category_eval["category_compatibility_policy"],
        "category_warnings": category_eval["category_warnings"],
        "baseline_candidate_paths": baseline_candidate_paths,
        "baseline_candidate_details": baseline_candidate_details,
        "diffs": diffs,
        "additional_guard_checks_diff": additional_checks_diff["diff"],
        "additional_guard_checks_changed_fields": additional_checks_diff["changed_fields"],
        "additional_guard_check_transitions": additional_checks_diff["transitions"],
        "additional_guard_checks_comparison_mode": additional_checks_diff["comparison_mode"],
        "additional_guard_checks_missing_in": additional_checks_diff["missing_in"],
        "regression_passed": regression_passed,
        "regression_reasons": regression_reasons,
        "fail_on_regression": bool(args.fail_on_regression),
        "strict_compatibility": bool(args.strict_compatibility),
        "exit_code": exit_code,
        "exit_code_meaning": EXIT_CODE_MEANING,
    }
    write_summary_json(output_path, payload)

    print(
        "[DONE] Phase1 guard history compare complete. "
        f"compatible={comparison_compatible} regression_passed={regression_passed}"
    )
    if baseline_path is not None:
        print(f"[DONE] baseline={baseline_path} mode={baseline_resolution_mode}")
    else:
        print(f"[DONE] baseline=NONE mode={baseline_resolution_mode}")
    if compatibility_errors:
        print(f"[DONE] compatibility_errors={compatibility_errors}")
    if regression_reasons:
        print(f"[DONE] regression_reasons={regression_reasons}")
    print(f"[DONE] summary={output_path}")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
