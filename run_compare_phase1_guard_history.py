#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOG_DIR = Path("data/phase1_seed10/logs")
OUTPUT_TEMPLATE = "phase1_guard_history_compare_{timestamp}.json"
EXPECTED_GENERATOR = "run_compare_phase1_guard.py"
EXPECTED_SIGNATURE_KEYS = {"guard_passed", "mismatch_fields", "check_results", "input_paths", "target_year"}

REGRESSION_EXIT_CODE = 2
INCOMPATIBLE_EXIT_CODE = 3


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare two Phase1 guard summaries and detect regressions."
    )
    parser.add_argument("--current-summary", required=True, help="current phase1 guard summary json path")
    parser.add_argument("--baseline-summary", required=True, help="baseline phase1 guard summary json path")
    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="return non-zero only when regression (or incompatible comparison) is detected",
    )
    parser.add_argument(
        "--output-path",
        default="",
        help="optional output summary path (default: data/phase1_seed10/logs/phase1_guard_history_compare_<timestamp>.json)",
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


def main() -> int:
    args = parse_args()
    started_at = utc_now_iso()
    print(f"[START] Phase1 guard history compare at {started_at}")

    current_path = Path(args.current_summary)
    baseline_path = Path(args.baseline_summary)

    compatibility_errors: list[str] = []
    compatibility_warnings: list[str] = []

    current_obj, current_err = load_json_object(current_path)
    baseline_obj, baseline_err = load_json_object(baseline_path)

    if current_err:
        compatibility_errors.append(f"current_summary_load_error:{current_err}")
    if baseline_err:
        compatibility_errors.append(f"baseline_summary_load_error:{baseline_err}")

    if current_obj is None:
        current_obj = {}
    if baseline_obj is None:
        baseline_obj = {}

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

    current_schema_version = current_obj.get("guard_schema_version")
    baseline_schema_version = baseline_obj.get("guard_schema_version")
    if isinstance(current_schema_version, str) and isinstance(baseline_schema_version, str):
        if current_schema_version != baseline_schema_version:
            compatibility_errors.append(
                f"guard_schema_version_mismatch:{baseline_schema_version}!={current_schema_version}"
            )
    else:
        # Optional field; keep as warning only.
        if not isinstance(current_schema_version, str):
            compatibility_warnings.append("current_guard_schema_version_missing")
        if not isinstance(baseline_schema_version, str):
            compatibility_warnings.append("baseline_guard_schema_version_missing")

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

    if args.fail_on_regression:
        if not comparison_compatible:
            exit_code = INCOMPATIBLE_EXIT_CODE
        elif not regression_passed:
            exit_code = REGRESSION_EXIT_CODE
        else:
            exit_code = 0
    else:
        exit_code = 0

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = Path(args.output_path) if args.output_path else LOG_DIR / OUTPUT_TEMPLATE.format(timestamp=timestamp)

    payload = {
        "started_at": started_at,
        "completed_at": utc_now_iso(),
        "generated_by": "run_compare_phase1_guard_history.py",
        "current_summary_path": str(current_path),
        "baseline_summary_path": str(baseline_path),
        "comparison_compatible": comparison_compatible,
        "compatibility_errors": compatibility_errors,
        "compatibility_warnings": compatibility_warnings,
        "diffs": diffs,
        "regression_passed": regression_passed,
        "regression_reasons": regression_reasons,
        "fail_on_regression": bool(args.fail_on_regression),
        "exit_code": exit_code,
    }
    write_json(output_path, payload)

    print(
        "[DONE] Phase1 guard history compare complete. "
        f"compatible={comparison_compatible} regression_passed={regression_passed}"
    )
    if compatibility_errors:
        print(f"[DONE] compatibility_errors={compatibility_errors}")
    if regression_reasons:
        print(f"[DONE] regression_reasons={regression_reasons}")
    print(f"[DONE] summary={output_path}")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
