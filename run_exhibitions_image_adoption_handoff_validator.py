#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

EXIT_PASS = 0
EXIT_REQUIRED_MISSING = 10
EXIT_SCHEMA_FAILURE = 11
EXIT_CONSISTENCY_FAILURE = 12
EXIT_EMPTY_HANDOFF_SET = 13
EXIT_HOLD = 20
EXIT_INTERNAL_FAILURE = 30

VERDICT_PASS = "PASS"
VERDICT_HOLD = "HOLD"
VERDICT_FAIL = "FAIL"

RUNNER_STATUS_SUCCESS = "SUCCESS"
RUNNER_STATUS_PARTIAL = "PARTIAL_SUCCESS"


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def utc_compact() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def norm_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def parse_bool(value: Any) -> bool | None:
    text = norm_text(value).lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return None


def parse_int(value: Any) -> int | None:
    text = norm_text(value)
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def as_text_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [norm_text(v) for v in value if norm_text(v)]
    text = norm_text(value)
    return [text] if text else []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate QA result bundle for adoption handoff readiness "
            "(no adoption/rollback execution)."
        )
    )
    parser.add_argument("--qa-execution-manifest", default="")
    parser.add_argument("--qa-execution-summary", default="")
    parser.add_argument("--qa-execution-report", default="")
    parser.add_argument("--qa-bundle-result-csv", default="")
    parser.add_argument("--qa-adoption-handoff-manifest", default="")

    parser.add_argument("--qa-unit-result-root", default="")
    parser.add_argument("--qa-failure-queue-csv", default="")
    parser.add_argument("--qa-defer-queue-csv", default="")

    parser.add_argument("--qa-runtime-input-manifest-json", default="")
    parser.add_argument("--trial-execution-manifest-json", default="")
    parser.add_argument("--qa-handoff-validation-manifest-json", default="")
    parser.add_argument("--classification-bundle-manifest-json", default="")

    parser.add_argument("--planned-unit-id", action="append", default=[])
    parser.add_argument("--fair-slug", action="append", default=[])
    parser.add_argument("--lane", action="append", default=[])

    parser.add_argument("--output-dir", default="data/phase1_seed10/logs")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--strict-trace", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fp:
        reader = csv.DictReader(fp)
        if reader.fieldnames is None:
            raise ValueError(f"csv_has_no_header:{path}")
        fields = [norm_text(v) for v in reader.fieldnames]
        rows: list[dict[str, str]] = []
        for row in reader:
            rows.append({norm_text(k): norm_text(v) for k, v in (row or {}).items()})
    return fields, rows


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_md(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], default_fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = default_fields if not rows else list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


class ValidationState:
    def __init__(self) -> None:
        self.errors: list[dict[str, Any]] = []
        self.warnings: list[dict[str, Any]] = []

    def add_error(
        self,
        *,
        code: str,
        check_id: str,
        message: str,
        category: str = "consistency",
        file: str = "",
        row_key: str = "",
    ) -> None:
        self.errors.append(
            {
                "severity": "error",
                "category": category,
                "code": code,
                "check_id": check_id,
                "message": message,
                "file": file,
                "row_key": row_key,
            }
        )

    def add_warning(
        self,
        *,
        code: str,
        check_id: str,
        message: str,
        category: str = "consistency",
        file: str = "",
        row_key: str = "",
    ) -> None:
        self.warnings.append(
            {
                "severity": "warning",
                "category": category,
                "code": code,
                "check_id": check_id,
                "message": message,
                "file": file,
                "row_key": row_key,
            }
        )


def require_file(path_text: str, *, label: str, state: ValidationState) -> Path | None:
    path_str = norm_text(path_text)
    if not path_str:
        state.add_error(
            code="required_path_missing",
            check_id="required_file_presence",
            message=f"required path missing: {label}",
            category="missing_artifact",
            file=label,
        )
        return None
    path = Path(path_str)
    if not path.exists():
        state.add_error(
            code="required_file_not_found",
            check_id="required_file_presence",
            message=f"required file not found: {label} -> {path}",
            category="missing_artifact",
            file=str(path),
        )
        return None
    return path


def ensure_required_columns(
    fields: list[str], required: list[str], *, artifact: str, state: ValidationState
) -> None:
    missing = [col for col in required if col not in fields]
    if missing:
        state.add_error(
            code="missing_required_columns",
            check_id="required_columns",
            message=f"{artifact} missing columns: {','.join(missing)}",
            category="schema",
            file=artifact,
        )


def choose_fail_exit(errors: list[dict[str, Any]]) -> int:
    categories = {norm_text(err.get("category")) for err in errors}
    if "missing_artifact" in categories:
        return EXIT_REQUIRED_MISSING
    if "schema" in categories:
        return EXIT_SCHEMA_FAILURE
    if "impossible_set" in categories:
        return EXIT_EMPTY_HANDOFF_SET
    return EXIT_CONSISTENCY_FAILURE


def build_output_paths(output_dir: Path, run_id: str) -> dict[str, Path]:
    return {
        "summary_json": output_dir
        / f"exhibitions_image_task_t209_adoption_handoff_validation_summary_{run_id}.json",
        "report_md": output_dir
        / f"exhibitions_image_task_t209_adoption_handoff_validation_report_{run_id}.md",
        "manifest_json": output_dir
        / f"exhibitions_image_task_t209_adoption_handoff_validation_manifest_{run_id}.json",
        "errors_csv": output_dir
        / f"exhibitions_image_task_t209_adoption_handoff_validation_errors_{run_id}.csv",
        "warnings_csv": output_dir
        / f"exhibitions_image_task_t209_adoption_handoff_validation_warnings_{run_id}.csv",
    }


def resolve_input_paths(args: argparse.Namespace) -> dict[str, str]:
    resolved = {
        "qa_execution_manifest_json": norm_text(args.qa_execution_manifest),
        "qa_execution_summary_json": norm_text(args.qa_execution_summary),
        "qa_execution_report_md": norm_text(args.qa_execution_report),
        "qa_bundle_result_csv": norm_text(args.qa_bundle_result_csv),
        "qa_adoption_handoff_manifest_json": norm_text(args.qa_adoption_handoff_manifest),
        "qa_unit_result_root": norm_text(args.qa_unit_result_root),
        "qa_failure_queue_csv": norm_text(args.qa_failure_queue_csv),
        "qa_defer_queue_csv": norm_text(args.qa_defer_queue_csv),
        "qa_runtime_input_manifest_json": norm_text(args.qa_runtime_input_manifest_json),
        "trial_execution_manifest_json": norm_text(args.trial_execution_manifest_json),
        "qa_handoff_validation_manifest_json": norm_text(args.qa_handoff_validation_manifest_json),
        "classification_bundle_manifest_json": norm_text(args.classification_bundle_manifest_json),
    }
    manifest_path = resolved["qa_execution_manifest_json"]
    if manifest_path and Path(manifest_path).exists():
        payload = read_json(Path(manifest_path))
        outputs = payload.get("outputs") or {}
        if not resolved["qa_execution_summary_json"]:
            resolved["qa_execution_summary_json"] = norm_text(outputs.get("summary_json"))
        if not resolved["qa_execution_report_md"]:
            resolved["qa_execution_report_md"] = norm_text(outputs.get("report_md"))
        if not resolved["qa_bundle_result_csv"]:
            resolved["qa_bundle_result_csv"] = norm_text(outputs.get("bundle_result_csv"))
        if not resolved["qa_adoption_handoff_manifest_json"]:
            resolved["qa_adoption_handoff_manifest_json"] = norm_text(
                outputs.get("adoption_handoff_manifest_json")
            )
        if not resolved["qa_failure_queue_csv"]:
            resolved["qa_failure_queue_csv"] = norm_text(outputs.get("failure_queue_csv"))
        if not resolved["qa_defer_queue_csv"]:
            resolved["qa_defer_queue_csv"] = norm_text(outputs.get("defer_queue_csv"))
        inputs = payload.get("inputs") or {}
        if not resolved["qa_runtime_input_manifest_json"]:
            resolved["qa_runtime_input_manifest_json"] = norm_text(
                inputs.get("qa_runtime_input_manifest_json")
            )
    return resolved


def validate_summary_fields(
    summary: dict[str, Any], state: ValidationState, summary_path: Path
) -> dict[str, Any]:
    qa_runner_status = norm_text(summary.get("qa_runner_status"))
    adoption_handoff_allowed = parse_bool(summary.get("adoption_handoff_allowed"))
    executed_unit_count = parse_int(summary.get("executed_unit_count"))
    succeeded_unit_count = parse_int(summary.get("succeeded_unit_count"))
    failed_unit_count = parse_int(summary.get("failed_unit_count"))
    deferred_unit_count = parse_int(summary.get("deferred_unit_count"))

    ids = summary.get("ids") or {}
    classification_run_id = norm_text(ids.get("classification_run_id"))
    bundle_id = norm_text(ids.get("bundle_id"))
    trial_runtime_bundle_id = norm_text(ids.get("trial_runtime_bundle_id"))
    trial_runner_bundle_id = norm_text(ids.get("trial_runner_bundle_id"))
    qa_runtime_bundle_id = norm_text(ids.get("qa_runtime_bundle_id"))
    qa_runner_bundle_id = norm_text(ids.get("qa_runner_bundle_id"))
    scope_hash = norm_text(summary.get("scope_hash"))

    if qa_runner_status not in {RUNNER_STATUS_SUCCESS, RUNNER_STATUS_PARTIAL}:
        state.add_error(
            code="qa_runner_status_not_adoption_eligible",
            check_id="summary_gate",
            message=f"qa_runner_status must be SUCCESS|PARTIAL_SUCCESS, got={qa_runner_status}",
            category="consistency",
            file=str(summary_path),
        )
    if adoption_handoff_allowed is not True:
        state.add_error(
            code="adoption_handoff_not_allowed",
            check_id="summary_gate",
            message="adoption_handoff_allowed must be true",
            category="consistency",
            file=str(summary_path),
        )
    if executed_unit_count is None or executed_unit_count <= 0:
        state.add_error(
            code="executed_unit_count_non_positive",
            check_id="summary_gate",
            message=f"executed_unit_count must be >0, got={executed_unit_count}",
            category="impossible_set",
            file=str(summary_path),
        )
    if None in {
        executed_unit_count,
        succeeded_unit_count,
        failed_unit_count,
        deferred_unit_count,
    }:
        state.add_error(
            code="summary_count_parse_failure",
            check_id="summary_count_consistency",
            message="summary count fields must be numeric",
            category="schema",
            file=str(summary_path),
        )
    elif executed_unit_count != (
        succeeded_unit_count + failed_unit_count + deferred_unit_count
    ):
        state.add_error(
            code="summary_count_mismatch",
            check_id="summary_count_consistency",
            message=(
                "executed_unit_count != succeeded+failed+deferred "
                f"({executed_unit_count} vs {succeeded_unit_count}+{failed_unit_count}+{deferred_unit_count})"
            ),
            category="consistency",
            file=str(summary_path),
        )

    for key, value in {
        "classification_run_id": classification_run_id,
        "bundle_id": bundle_id,
        "trial_runtime_bundle_id": trial_runtime_bundle_id,
        "trial_runner_bundle_id": trial_runner_bundle_id,
        "qa_runner_bundle_id": qa_runner_bundle_id,
        "qa_runtime_bundle_id": qa_runtime_bundle_id,
        "scope_hash": scope_hash,
    }.items():
        if not value:
            state.add_error(
                code="summary_required_id_missing",
                check_id="summary_required_ids",
                message=f"summary missing required id: {key}",
                category="schema",
                file=str(summary_path),
            )

    return {
        "qa_runner_status": qa_runner_status,
        "adoption_handoff_allowed": adoption_handoff_allowed,
        "executed_unit_count": executed_unit_count or 0,
        "succeeded_unit_count": succeeded_unit_count or 0,
        "failed_unit_count": failed_unit_count or 0,
        "deferred_unit_count": deferred_unit_count or 0,
        "classification_run_id": classification_run_id,
        "bundle_id": bundle_id,
        "trial_runtime_bundle_id": trial_runtime_bundle_id,
        "trial_runner_bundle_id": trial_runner_bundle_id,
        "qa_runner_bundle_id": qa_runner_bundle_id,
        "qa_runtime_bundle_id": qa_runtime_bundle_id,
        "scope_hash": scope_hash,
        "manual_review_required": parse_bool(summary.get("manual_review_required")) is True,
        "retry_recommended": parse_bool(summary.get("retry_recommended")) is True,
        "warning_count": parse_int(summary.get("warning_count")) or 0,
    }


def main() -> int:
    args = parse_args()
    run_id = norm_text(args.run_id) or f"{utc_compact()}-adoption-handoff-validate"
    output_dir = Path(args.output_dir)
    output_paths = build_output_paths(output_dir, run_id)
    started_at = utc_now_iso()
    state = ValidationState()

    try:
        if norm_text(os.environ.get("TASK209_FORCE_INTERNAL_FAILURE")) in {"1", "true", "yes"}:
            raise RuntimeError("forced_internal_failure_for_task209")

        resolved = resolve_input_paths(args)

        manifest_path = require_file(
            resolved["qa_execution_manifest_json"],
            label="qa_execution_manifest_json",
            state=state,
        )
        summary_path = require_file(
            resolved["qa_execution_summary_json"],
            label="qa_execution_summary_json",
            state=state,
        )
        report_path = require_file(
            resolved["qa_execution_report_md"],
            label="qa_execution_report_md",
            state=state,
        )
        bundle_result_path = require_file(
            resolved["qa_bundle_result_csv"],
            label="qa_bundle_result_csv",
            state=state,
        )
        qa_adoption_handoff_manifest_path = require_file(
            resolved["qa_adoption_handoff_manifest_json"],
            label="qa_adoption_handoff_manifest_json",
            state=state,
        )

        qa_runtime_input_manifest_path: Path | None = None
        qa_handoff_validation_manifest_path: Path | None = None
        classification_bundle_manifest_path: Path | None = None
        if args.strict_trace:
            qa_runtime_input_manifest_path = require_file(
                resolved["qa_runtime_input_manifest_json"],
                label="qa_runtime_input_manifest_json",
                state=state,
            )
            qa_handoff_validation_manifest_path = require_file(
                resolved["qa_handoff_validation_manifest_json"],
                label="qa_handoff_validation_manifest_json",
                state=state,
            )
            require_file(
                resolved["trial_execution_manifest_json"],
                label="trial_execution_manifest_json",
                state=state,
            )
            classification_bundle_manifest_path = require_file(
                resolved["classification_bundle_manifest_json"],
                label="classification_bundle_manifest_json",
                state=state,
            )
        else:
            if norm_text(resolved["qa_runtime_input_manifest_json"]):
                qa_runtime_input_manifest_path = require_file(
                    resolved["qa_runtime_input_manifest_json"],
                    label="qa_runtime_input_manifest_json",
                    state=state,
                )
            if norm_text(resolved["qa_handoff_validation_manifest_json"]):
                qa_handoff_validation_manifest_path = require_file(
                    resolved["qa_handoff_validation_manifest_json"],
                    label="qa_handoff_validation_manifest_json",
                    state=state,
                )
            if norm_text(resolved["classification_bundle_manifest_json"]):
                classification_bundle_manifest_path = require_file(
                    resolved["classification_bundle_manifest_json"],
                    label="classification_bundle_manifest_json",
                    state=state,
                )

        if state.errors:
            exit_code = choose_fail_exit(state.errors)
            summary_payload = {
                "task_id": "TASK209",
                "run_id": run_id,
                "started_at": started_at,
                "completed_at": utc_now_iso(),
                "adoption_handoff_verdict": VERDICT_FAIL,
                "adoption_handoff_allowed": False,
                "manual_review_required": True,
                "retry_recommended": True,
                "validated_unit_count": 0,
                "validated_row_count": 0,
                "error_count": len(state.errors),
                "warning_count": len(state.warnings),
                "resolved_inputs": resolved,
                "exit_code": exit_code,
                "output_paths": {k: str(v) for k, v in output_paths.items()},
            }
            write_json(output_paths["summary_json"], summary_payload)
            write_json(
                output_paths["manifest_json"],
                {
                    "task_id": "TASK209",
                    "run_id": run_id,
                    "created_at": utc_now_iso(),
                    "inputs": resolved,
                    "outputs": {k: str(v) for k, v in output_paths.items()},
                    "adoption_handoff_verdict": VERDICT_FAIL,
                    "exit_code": exit_code,
                },
            )
            write_md(
                output_paths["report_md"],
                [
                    "# TASK209 Adoption Handoff Validation Report",
                    "",
                    f"- adoption_handoff_verdict: `{VERDICT_FAIL}`",
                    f"- exit_code: `{exit_code}`",
                    f"- error_count: `{len(state.errors)}`",
                    "",
                    "## Failures",
                    *[
                        f"- [{err['category']}/{err['code']}] {err['message']}"
                        for err in state.errors
                    ],
                ],
            )
            write_csv(
                output_paths["errors_csv"],
                state.errors,
                ["severity", "category", "code", "check_id", "message", "file", "row_key"],
            )
            write_csv(
                output_paths["warnings_csv"],
                state.warnings,
                ["severity", "category", "code", "check_id", "message", "file", "row_key"],
            )
            return exit_code

        assert (
            manifest_path
            and summary_path
            and report_path
            and bundle_result_path
            and qa_adoption_handoff_manifest_path
        )
        qa_execution_manifest = read_json(manifest_path)
        qa_execution_summary = read_json(summary_path)
        qa_adoption_handoff_manifest = read_json(qa_adoption_handoff_manifest_path)
        bundle_fields, bundle_rows = read_csv(bundle_result_path)
        summary_info = validate_summary_fields(qa_execution_summary, state, summary_path)

        ensure_required_columns(
            bundle_fields,
            [
                "planned_unit_id",
                "actual_trial_run_id",
                "actual_qa_run_id",
                "unit_status",
                "executed_row_count",
                "succeeded_row_count",
                "failed_row_count",
                "deferred_row_count",
                "exit_code",
                "qa_unit_result_json_path",
                "qa_unit_rows_csv_path",
            ],
            artifact=str(bundle_result_path),
            state=state,
        )
        if not bundle_rows:
            state.add_error(
                code="bundle_result_empty",
                check_id="bundle_result_rows",
                message="qa_bundle_result.csv has no rows",
                category="impossible_set",
                file=str(bundle_result_path),
            )

        bundle_unit_ids: set[str] = set()
        seen_unit_ids: set[str] = set()
        seen_actual_qa_run_ids: set[str] = set()
        failed_units: set[str] = set()
        deferred_units: set[str] = set()
        unit_results: list[dict[str, Any]] = []
        per_unit_fairs: set[str] = set()
        per_unit_lanes: set[str] = set()
        per_unit_years: set[str] = set()
        selected_unit_filter = {norm_text(v) for v in args.planned_unit_id if norm_text(v)}
        selected_fair_filter = {norm_text(v) for v in args.fair_slug if norm_text(v)}
        selected_lane_filter = {norm_text(v) for v in args.lane if norm_text(v)}

        for row in bundle_rows:
            unit_id = norm_text(row.get("planned_unit_id"))
            row_key = unit_id or "<missing_unit_id>"
            if not unit_id:
                state.add_error(
                    code="bundle_row_missing_unit_id",
                    check_id="bundle_result_pk",
                    message="planned_unit_id is empty",
                    category="schema",
                    file=str(bundle_result_path),
                    row_key=row_key,
                )
                continue
            if unit_id in seen_unit_ids:
                state.add_error(
                    code="bundle_row_duplicate_unit_id",
                    check_id="bundle_result_pk",
                    message=f"duplicate planned_unit_id in qa_bundle_result: {unit_id}",
                    category="consistency",
                    file=str(bundle_result_path),
                    row_key=row_key,
                )
                continue
            seen_unit_ids.add(unit_id)
            bundle_unit_ids.add(unit_id)

            actual_trial_run_id = norm_text(row.get("actual_trial_run_id"))
            actual_qa_run_id = norm_text(row.get("actual_qa_run_id"))
            if not actual_trial_run_id:
                state.add_error(
                    code="bundle_row_missing_actual_trial_run_id",
                    check_id="bundle_result_required",
                    message=f"actual_trial_run_id is empty for unit={unit_id}",
                    category="schema",
                    file=str(bundle_result_path),
                    row_key=row_key,
                )
            if not actual_qa_run_id:
                state.add_error(
                    code="bundle_row_missing_actual_qa_run_id",
                    check_id="bundle_result_required",
                    message=f"actual_qa_run_id is empty for unit={unit_id}",
                    category="schema",
                    file=str(bundle_result_path),
                    row_key=row_key,
                )
            elif actual_qa_run_id in seen_actual_qa_run_ids:
                state.add_error(
                    code="bundle_row_duplicate_actual_qa_run_id",
                    check_id="bundle_result_pk",
                    message=f"duplicate actual_qa_run_id in qa_bundle_result: {actual_qa_run_id}",
                    category="consistency",
                    file=str(bundle_result_path),
                    row_key=row_key,
                )
            else:
                seen_actual_qa_run_ids.add(actual_qa_run_id)

            executed_row_count = parse_int(row.get("executed_row_count"))
            succeeded_row_count = parse_int(row.get("succeeded_row_count"))
            failed_row_count = parse_int(row.get("failed_row_count"))
            deferred_row_count = parse_int(row.get("deferred_row_count"))
            if None in {
                executed_row_count,
                succeeded_row_count,
                failed_row_count,
                deferred_row_count,
            }:
                state.add_error(
                    code="bundle_row_count_parse_failure",
                    check_id="bundle_result_counts",
                    message=f"count parse failed for unit={unit_id}",
                    category="schema",
                    file=str(bundle_result_path),
                    row_key=row_key,
                )
                continue
            if executed_row_count != (
                succeeded_row_count + failed_row_count + deferred_row_count
            ):
                state.add_error(
                    code="bundle_row_count_mismatch",
                    check_id="bundle_result_counts",
                    message=(
                        f"unit={unit_id} executed != succeeded+failed+deferred "
                        f"({executed_row_count} vs {succeeded_row_count}+{failed_row_count}+{deferred_row_count})"
                    ),
                    category="consistency",
                    file=str(bundle_result_path),
                    row_key=row_key,
                )

            unit_json_path = norm_text(row.get("qa_unit_result_json_path"))
            unit_rows_path = norm_text(row.get("qa_unit_rows_csv_path"))
            if not unit_json_path and norm_text(args.qa_unit_result_root):
                unit_json_path = str(
                    Path(args.qa_unit_result_root) / f"t207_ures_{unit_id}.json"
                )

            unit_json = require_file(
                unit_json_path,
                label=f"qa_unit_result_json:{unit_id}",
                state=state,
            )
            unit_rows_csv = require_file(
                unit_rows_path,
                label=f"qa_unit_rows_csv:{unit_id}",
                state=state,
            )
            if not unit_json or not unit_rows_csv:
                continue

            unit_payload = read_json(unit_json)
            unit_fields, unit_rows = read_csv(unit_rows_csv)
            ensure_required_columns(
                unit_fields,
                [
                    "planned_unit_id",
                    "classification_run_id",
                    "bundle_id",
                    "trial_runtime_bundle_id",
                    "trial_runner_bundle_id",
                    "qa_runtime_bundle_id",
                    "scope_hash",
                    "target_year",
                    "fair_slug",
                    "lane",
                    "gallery_name_en",
                    "source_url",
                    "selected_reason",
                    "local_path",
                ],
                artifact=str(unit_rows_csv),
                state=state,
            )

            for key in [
                "planned_unit_id",
                "actual_trial_run_id",
                "actual_qa_run_id",
                "unit_status",
                "executed_row_count",
                "succeeded_row_count",
                "failed_row_count",
                "deferred_row_count",
                "classification_run_id",
                "bundle_id",
                "trial_runtime_bundle_id",
                "trial_runner_bundle_id",
                "qa_runtime_bundle_id",
                "qa_runner_bundle_id",
                "scope_hash",
                "target_year",
                "fair_slug",
                "lane",
            ]:
                if not norm_text(unit_payload.get(key)):
                    state.add_error(
                        code="unit_result_missing_key",
                        check_id="unit_result_required_keys",
                        message=f"unit result missing key={key} for unit={unit_id}",
                        category="schema",
                        file=str(unit_json),
                        row_key=row_key,
                    )

            unit_exec = parse_int(unit_payload.get("executed_row_count"))
            unit_succ = parse_int(unit_payload.get("succeeded_row_count"))
            unit_fail = parse_int(unit_payload.get("failed_row_count"))
            unit_def = parse_int(unit_payload.get("deferred_row_count"))
            if None in {unit_exec, unit_succ, unit_fail, unit_def}:
                state.add_error(
                    code="unit_result_count_parse_failure",
                    check_id="unit_result_counts",
                    message=f"unit result count parse failed for unit={unit_id}",
                    category="schema",
                    file=str(unit_json),
                    row_key=row_key,
                )
            else:
                if unit_exec != len(unit_rows):
                    state.add_error(
                        code="unit_rows_count_mismatch",
                        check_id="unit_rows_vs_result",
                        message=(
                            f"unit={unit_id} result executed_row_count={unit_exec} "
                            f"but qa_unit_rows rows={len(unit_rows)}"
                        ),
                        category="consistency",
                        file=str(unit_rows_csv),
                        row_key=row_key,
                    )
                if unit_exec != executed_row_count:
                    state.add_error(
                        code="unit_bundle_count_mismatch",
                        check_id="unit_result_vs_bundle",
                        message=(
                            f"unit={unit_id} unit_result executed_row_count={unit_exec} "
                            f"!= bundle executed_row_count={executed_row_count}"
                        ),
                        category="consistency",
                        file=str(bundle_result_path),
                        row_key=row_key,
                    )
                if (
                    unit_succ != succeeded_row_count
                    or unit_fail != failed_row_count
                    or unit_def != deferred_row_count
                ):
                    state.add_error(
                        code="unit_bundle_subcount_mismatch",
                        check_id="unit_result_vs_bundle",
                        message=f"unit={unit_id} succeeded/failed/deferred mismatch between unit_result and bundle_result",
                        category="consistency",
                        file=str(bundle_result_path),
                        row_key=row_key,
                    )

            if norm_text(unit_payload.get("planned_unit_id")) != unit_id:
                state.add_error(
                    code="unit_result_unit_id_mismatch",
                    check_id="unit_result_vs_bundle",
                    message=f"unit_id mismatch bundle={unit_id} unit_result={norm_text(unit_payload.get('planned_unit_id'))}",
                    category="consistency",
                    file=str(unit_json),
                    row_key=row_key,
                )
            if norm_text(unit_payload.get("actual_trial_run_id")) != actual_trial_run_id:
                state.add_error(
                    code="unit_result_actual_trial_run_id_mismatch",
                    check_id="unit_result_vs_bundle",
                    message=f"actual_trial_run_id mismatch for unit={unit_id}",
                    category="consistency",
                    file=str(unit_json),
                    row_key=row_key,
                )
            if norm_text(unit_payload.get("actual_qa_run_id")) != actual_qa_run_id:
                state.add_error(
                    code="unit_result_actual_qa_run_id_mismatch",
                    check_id="unit_result_vs_bundle",
                    message=f"actual_qa_run_id mismatch for unit={unit_id}",
                    category="consistency",
                    file=str(unit_json),
                    row_key=row_key,
                )

            unit_status = norm_text(row.get("unit_status")).upper()
            if unit_status == "FAILED":
                failed_units.add(unit_id)
            if unit_status == "DEFERRED":
                deferred_units.add(unit_id)

            fair_slug = norm_text(unit_payload.get("fair_slug"))
            lane = norm_text(unit_payload.get("lane"))
            year = norm_text(unit_payload.get("target_year"))
            per_unit_fairs.add(fair_slug)
            per_unit_lanes.add(lane)
            per_unit_years.add(year)

            unit_results.append(
                {
                    "planned_unit_id": unit_id,
                    "actual_trial_run_id": actual_trial_run_id,
                    "unit_status": unit_status,
                    "executed_row_count": executed_row_count,
                    "fair_slug": fair_slug,
                    "lane": lane,
                    "target_year": year,
                    "classification_run_id": norm_text(unit_payload.get("classification_run_id")),
                    "bundle_id": norm_text(unit_payload.get("bundle_id")),
                    "trial_runtime_bundle_id": norm_text(unit_payload.get("trial_runtime_bundle_id")),
                    "trial_runner_bundle_id": norm_text(unit_payload.get("trial_runner_bundle_id")),
                    "qa_runtime_bundle_id": norm_text(unit_payload.get("qa_runtime_bundle_id")),
                    "scope_hash": norm_text(unit_payload.get("scope_hash")),
                    "qa_runner_bundle_id": norm_text(unit_payload.get("qa_runner_bundle_id")),
                    "qa_unit_result_json_path": str(unit_json),
                    "qa_unit_rows_csv_path": str(unit_rows_csv),
                }
            )

            if args.strict:
                unit_md = Path(unit_json).with_suffix(".md")
                if not unit_md.exists():
                    state.add_error(
                        code="strict_unit_md_missing",
                        check_id="strict_unit_md",
                        message=f"strict requires unit markdown result: {unit_md}",
                        category="missing_artifact",
                        file=str(unit_md),
                        row_key=row_key,
                    )

        if summary_info["executed_unit_count"] != len(bundle_rows):
            state.add_error(
                code="summary_bundle_unit_count_mismatch",
                check_id="summary_vs_bundle",
                message=(
                    f"summary.executed_unit_count={summary_info['executed_unit_count']} "
                    f"!= bundle rows={len(bundle_rows)}"
                ),
                category="consistency",
                file=str(bundle_result_path),
            )

        bundle_succeeded = sum(
            1 for row in bundle_rows if norm_text(row.get("unit_status")).upper() == "SUCCESS"
        )
        bundle_failed = sum(
            1 for row in bundle_rows if norm_text(row.get("unit_status")).upper() == "FAILED"
        )
        bundle_deferred = sum(
            1 for row in bundle_rows if norm_text(row.get("unit_status")).upper() == "DEFERRED"
        )
        if (
            bundle_succeeded != summary_info["succeeded_unit_count"]
            or bundle_failed != summary_info["failed_unit_count"]
            or bundle_deferred != summary_info["deferred_unit_count"]
        ):
            state.add_error(
                code="summary_bundle_status_count_mismatch",
                check_id="summary_vs_bundle",
                message=(
                    "bundle status counts mismatch summary: "
                    f"summary=({summary_info['succeeded_unit_count']},{summary_info['failed_unit_count']},{summary_info['deferred_unit_count']}) "
                    f"bundle=({bundle_succeeded},{bundle_failed},{bundle_deferred})"
                ),
                category="consistency",
                file=str(bundle_result_path),
            )

        if len(per_unit_fairs) > 1:
            state.add_error(
                code="bundle_scope_fair_mixed",
                check_id="bundle_scope_consistency",
                message=f"fair_slug is mixed in bundle: {sorted(per_unit_fairs)}",
                category="consistency",
                file=str(bundle_result_path),
            )
        if len(per_unit_lanes) > 1:
            state.add_error(
                code="bundle_scope_lane_mixed",
                check_id="bundle_scope_consistency",
                message=f"lane is mixed in bundle: {sorted(per_unit_lanes)}",
                category="consistency",
                file=str(bundle_result_path),
            )
        if len(per_unit_years) > 1:
            state.add_error(
                code="bundle_scope_year_mixed",
                check_id="bundle_scope_consistency",
                message=f"target_year is mixed in bundle: {sorted(per_unit_years)}",
                category="consistency",
                file=str(bundle_result_path),
            )

        handoff_status = norm_text(qa_adoption_handoff_manifest.get("qa_runner_status"))
        handoff_allowed = parse_bool(qa_adoption_handoff_manifest.get("adoption_handoff_allowed"))
        if handoff_status not in {RUNNER_STATUS_SUCCESS, RUNNER_STATUS_PARTIAL}:
            state.add_error(
                code="handoff_manifest_status_invalid",
                check_id="handoff_manifest_gate",
                message=f"qa_runner_status in qa_adoption_handoff_manifest must be SUCCESS|PARTIAL_SUCCESS, got={handoff_status}",
                category="consistency",
                file=str(qa_adoption_handoff_manifest_path),
            )
        if handoff_allowed is not True:
            state.add_error(
                code="handoff_manifest_not_allowed",
                check_id="handoff_manifest_gate",
                message="adoption_handoff_allowed in qa_adoption_handoff_manifest must be true",
                category="consistency",
                file=str(qa_adoption_handoff_manifest_path),
            )

        handoff_executed_units = set(as_text_list(qa_adoption_handoff_manifest.get("executed_unit_ids")))
        if not handoff_executed_units:
            state.add_error(
                code="handoff_manifest_empty_executed_units",
                check_id="handoff_manifest_unit_set",
                message="qa_adoption_handoff_manifest executed_unit_ids is empty",
                category="impossible_set",
                file=str(qa_adoption_handoff_manifest_path),
            )
        if handoff_executed_units and handoff_executed_units != bundle_unit_ids:
            state.add_error(
                code="handoff_manifest_unit_set_mismatch",
                check_id="handoff_manifest_unit_set",
                message=(
                    "qa_adoption_handoff_manifest executed_unit_ids mismatch bundle units: "
                    f"handoff={sorted(handoff_executed_units)} bundle={sorted(bundle_unit_ids)}"
                ),
                category="consistency",
                file=str(qa_adoption_handoff_manifest_path),
            )

        unit_result_paths = [Path(v) for v in as_text_list(qa_adoption_handoff_manifest.get("qa_unit_result_paths"))]
        if len(unit_result_paths) != len(bundle_unit_ids):
            state.add_error(
                code="handoff_manifest_unit_result_paths_count_mismatch",
                check_id="handoff_manifest_unit_paths",
                message=(
                    f"unit_result_paths count mismatch: {len(unit_result_paths)} vs unit_count={len(bundle_unit_ids)}"
                ),
                category="consistency",
                file=str(qa_adoption_handoff_manifest_path),
            )
        for path in unit_result_paths:
            if not path.exists():
                state.add_error(
                    code="handoff_manifest_output_path_missing",
                    check_id="handoff_manifest_output_paths",
                    message=f"qa_adoption_handoff_manifest references missing unit_result_path: {path}",
                    category="consistency",
                    file=str(path),
                )

        bundle_summary_path = Path(norm_text(qa_adoption_handoff_manifest.get("qa_bundle_summary_path")))
        if not bundle_summary_path.exists():
            state.add_error(
                code="handoff_manifest_bundle_summary_missing",
                check_id="handoff_manifest_output_paths",
                message=f"qa_adoption_handoff_manifest references missing bundle_summary_path: {bundle_summary_path}",
                category="consistency",
                file=str(bundle_summary_path),
            )

        failure_queue_path = norm_text(resolved.get("qa_failure_queue_csv")) or norm_text(
            qa_adoption_handoff_manifest.get("qa_failure_queue_path")
        )
        defer_queue_path = norm_text(resolved.get("qa_defer_queue_csv")) or norm_text(
            qa_adoption_handoff_manifest.get("qa_defer_queue_path")
        )
        failure_queue_rows: list[dict[str, str]] = []
        defer_queue_rows: list[dict[str, str]] = []

        if summary_info["failed_unit_count"] > 0:
            failure_path_obj = require_file(
                failure_queue_path,
                label="qa_failure_queue_csv(required because failed_unit_count>0)",
                state=state,
            )
            if failure_path_obj:
                failure_fields, failure_queue_rows = read_csv(failure_path_obj)
                ensure_required_columns(
                    failure_fields,
                    ["planned_unit_id", "actual_trial_run_id", "actual_qa_run_id", "failed_row_count"],
                    artifact=str(failure_path_obj),
                    state=state,
                )
        elif failure_queue_path:
            maybe_failure = Path(failure_queue_path)
            if maybe_failure.exists():
                state.add_warning(
                    code="failure_queue_present_with_zero_failed_units",
                    check_id="optional_queue_presence",
                    message="qa_failure_queue.csv exists though failed_unit_count=0",
                    file=str(maybe_failure),
                )

        if summary_info["deferred_unit_count"] > 0:
            defer_path_obj = require_file(
                defer_queue_path,
                label="qa_defer_queue_csv(required because deferred_unit_count>0)",
                state=state,
            )
            if defer_path_obj:
                defer_fields, defer_queue_rows = read_csv(defer_path_obj)
                ensure_required_columns(
                    defer_fields,
                    ["planned_unit_id", "actual_trial_run_id", "actual_qa_run_id", "deferred_row_count"],
                    artifact=str(defer_path_obj),
                    state=state,
                )
        elif defer_queue_path:
            maybe_defer = Path(defer_queue_path)
            if maybe_defer.exists():
                state.add_warning(
                    code="defer_queue_present_with_zero_deferred_units",
                    check_id="optional_queue_presence",
                    message="qa_defer_queue.csv exists though deferred_unit_count=0",
                    file=str(maybe_defer),
                )

        failure_units_in_queue = {
            norm_text(row.get("planned_unit_id"))
            for row in failure_queue_rows
            if norm_text(row.get("planned_unit_id"))
        }
        defer_units_in_queue = {
            norm_text(row.get("planned_unit_id"))
            for row in defer_queue_rows
            if norm_text(row.get("planned_unit_id"))
        }
        if failed_units and failure_units_in_queue != failed_units:
            state.add_error(
                code="failure_queue_unit_set_mismatch",
                check_id="queue_vs_bundle",
                message=f"failure queue units mismatch expected failed units: queue={sorted(failure_units_in_queue)} expected={sorted(failed_units)}",
                category="consistency",
                file=failure_queue_path,
            )
        if deferred_units and defer_units_in_queue != deferred_units:
            state.add_error(
                code="defer_queue_unit_set_mismatch",
                check_id="queue_vs_bundle",
                message=f"defer queue units mismatch expected deferred units: queue={sorted(defer_units_in_queue)} expected={sorted(deferred_units)}",
                category="consistency",
                file=defer_queue_path,
            )

        handoff_ids = {
            "classification_run_id": norm_text(qa_adoption_handoff_manifest.get("classification_run_id")),
            "bundle_id": norm_text(qa_adoption_handoff_manifest.get("bundle_id")),
            "trial_runtime_bundle_id": norm_text(qa_adoption_handoff_manifest.get("trial_runtime_bundle_id")),
            "trial_runner_bundle_id": norm_text(qa_adoption_handoff_manifest.get("trial_runner_bundle_id")),
            "qa_runtime_bundle_id": norm_text(qa_adoption_handoff_manifest.get("qa_runtime_bundle_id")),
            "qa_runner_bundle_id": norm_text(qa_adoption_handoff_manifest.get("qa_runner_bundle_id")),
            "scope_hash": norm_text(qa_adoption_handoff_manifest.get("scope_hash")),
        }
        for key in [
            "classification_run_id",
            "bundle_id",
            "trial_runtime_bundle_id",
            "trial_runner_bundle_id",
            "qa_runtime_bundle_id",
            "qa_runner_bundle_id",
            "scope_hash",
        ]:
            expected = summary_info[key]
            actual = handoff_ids[key]
            if expected != actual:
                state.add_error(
                    code="cross_file_id_mismatch",
                    check_id="cross_file_ids",
                    message=f"{key} mismatch summary={expected} handoff={actual}",
                    category="consistency",
                    file=str(qa_adoption_handoff_manifest_path),
                )

        unit_summary_scope_hashes = {
            norm_text(u.get("scope_hash")) for u in unit_results if norm_text(u.get("scope_hash"))
        }
        unit_summary_classification_ids = {
            norm_text(u.get("classification_run_id"))
            for u in unit_results
            if norm_text(u.get("classification_run_id"))
        }
        unit_summary_bundle_ids = {
            norm_text(u.get("bundle_id")) for u in unit_results if norm_text(u.get("bundle_id"))
        }
        unit_summary_trial_runtime_bundle_ids = {
            norm_text(u.get("trial_runtime_bundle_id"))
            for u in unit_results
            if norm_text(u.get("trial_runtime_bundle_id"))
        }
        unit_summary_trial_runner_bundle_ids = {
            norm_text(u.get("trial_runner_bundle_id"))
            for u in unit_results
            if norm_text(u.get("trial_runner_bundle_id"))
        }
        unit_summary_qa_runtime_bundle_ids = {
            norm_text(u.get("qa_runtime_bundle_id"))
            for u in unit_results
            if norm_text(u.get("qa_runtime_bundle_id"))
        }
        unit_summary_runner_bundle_ids = {
            norm_text(u.get("qa_runner_bundle_id"))
            for u in unit_results
            if norm_text(u.get("qa_runner_bundle_id"))
        }
        if unit_summary_scope_hashes and unit_summary_scope_hashes != {summary_info["scope_hash"]}:
            state.add_error(
                code="cross_file_scope_hash_mismatch",
                check_id="cross_file_ids",
                message=f"scope_hash mismatch in per-unit results: {sorted(unit_summary_scope_hashes)} vs summary={summary_info['scope_hash']}",
                category="consistency",
                file=str(bundle_result_path),
            )
        if (
            unit_summary_classification_ids
            and unit_summary_classification_ids != {summary_info["classification_run_id"]}
        ):
            state.add_error(
                code="cross_file_classification_run_id_mismatch",
                check_id="cross_file_ids",
                message=f"classification_run_id mismatch in per-unit results: {sorted(unit_summary_classification_ids)} vs summary={summary_info['classification_run_id']}",
                category="consistency",
                file=str(bundle_result_path),
            )
        if unit_summary_bundle_ids and unit_summary_bundle_ids != {summary_info["bundle_id"]}:
            state.add_error(
                code="cross_file_bundle_id_mismatch",
                check_id="cross_file_ids",
                message=f"bundle_id mismatch in per-unit results: {sorted(unit_summary_bundle_ids)} vs summary={summary_info['bundle_id']}",
                category="consistency",
                file=str(bundle_result_path),
            )
        if (
            unit_summary_trial_runtime_bundle_ids
            and unit_summary_trial_runtime_bundle_ids != {summary_info["trial_runtime_bundle_id"]}
        ):
            state.add_error(
                code="cross_file_trial_runtime_bundle_id_mismatch",
                check_id="cross_file_ids",
                message=f"trial_runtime_bundle_id mismatch in per-unit results: {sorted(unit_summary_trial_runtime_bundle_ids)} vs summary={summary_info['trial_runtime_bundle_id']}",
                category="consistency",
                file=str(bundle_result_path),
            )
        if (
            unit_summary_trial_runner_bundle_ids
            and unit_summary_trial_runner_bundle_ids != {summary_info["trial_runner_bundle_id"]}
        ):
            state.add_error(
                code="cross_file_trial_runner_bundle_id_mismatch",
                check_id="cross_file_ids",
                message=f"trial_runner_bundle_id mismatch in per-unit results: {sorted(unit_summary_trial_runner_bundle_ids)} vs summary={summary_info['trial_runner_bundle_id']}",
                category="consistency",
                file=str(bundle_result_path),
            )
        if (
            unit_summary_qa_runtime_bundle_ids
            and unit_summary_qa_runtime_bundle_ids != {summary_info["qa_runtime_bundle_id"]}
        ):
            state.add_error(
                code="cross_file_qa_runtime_bundle_id_mismatch",
                check_id="cross_file_ids",
                message=f"qa_runtime_bundle_id mismatch in per-unit results: {sorted(unit_summary_qa_runtime_bundle_ids)} vs summary={summary_info['qa_runtime_bundle_id']}",
                category="consistency",
                file=str(bundle_result_path),
            )
        if (
            unit_summary_runner_bundle_ids
            and unit_summary_runner_bundle_ids != {summary_info["qa_runner_bundle_id"]}
        ):
            state.add_error(
                code="cross_file_qa_runner_bundle_id_mismatch",
                check_id="cross_file_ids",
                message=f"qa_runner_bundle_id mismatch in per-unit results: {sorted(unit_summary_runner_bundle_ids)} vs summary={summary_info['qa_runner_bundle_id']}",
                category="consistency",
                file=str(bundle_result_path),
            )

        handoff_fairs = set(as_text_list(qa_adoption_handoff_manifest.get("fair_slug_set")))
        handoff_lanes = set(as_text_list(qa_adoption_handoff_manifest.get("lane_set")))
        handoff_years = set(as_text_list(qa_adoption_handoff_manifest.get("target_year")))
        if handoff_fairs and handoff_fairs != per_unit_fairs:
            state.add_error(
                code="cross_file_fair_set_mismatch",
                check_id="cross_file_scope",
                message=f"fair_slug_set mismatch handoff={sorted(handoff_fairs)} per_unit={sorted(per_unit_fairs)}",
                category="consistency",
                file=str(qa_adoption_handoff_manifest_path),
            )
        if handoff_lanes and handoff_lanes != per_unit_lanes:
            state.add_error(
                code="cross_file_lane_set_mismatch",
                check_id="cross_file_scope",
                message=f"lane_set mismatch handoff={sorted(handoff_lanes)} per_unit={sorted(per_unit_lanes)}",
                category="consistency",
                file=str(qa_adoption_handoff_manifest_path),
            )
        if handoff_years and handoff_years != per_unit_years:
            state.add_error(
                code="cross_file_year_set_mismatch",
                check_id="cross_file_scope",
                message=f"target_year mismatch handoff={sorted(handoff_years)} per_unit={sorted(per_unit_years)}",
                category="consistency",
                file=str(qa_adoption_handoff_manifest_path),
            )

        if qa_runtime_input_manifest_path:
            runtime_payload = read_json(qa_runtime_input_manifest_path)
            runtime_ids = runtime_payload.get("ids") or {}
            runtime_classification = norm_text(runtime_ids.get("classification_run_id"))
            runtime_bundle = norm_text(runtime_ids.get("bundle_id"))
            runtime_scope_hash = norm_text(runtime_payload.get("scope_hash"))
            runtime_bundle_id = norm_text(runtime_ids.get("trial_runtime_bundle_id"))
            if runtime_classification and runtime_classification != summary_info["classification_run_id"]:
                state.add_error(
                    code="strict_trace_classification_run_id_mismatch",
                    check_id="strict_trace_ids",
                    message=f"classification_run_id mismatch runtime_manifest={runtime_classification} summary={summary_info['classification_run_id']}",
                    category="consistency",
                    file=str(qa_runtime_input_manifest_path),
                )
            if runtime_bundle and runtime_bundle != summary_info["bundle_id"]:
                state.add_error(
                    code="strict_trace_bundle_id_mismatch",
                    check_id="strict_trace_ids",
                    message=f"bundle_id mismatch runtime_manifest={runtime_bundle} summary={summary_info['bundle_id']}",
                    category="consistency",
                    file=str(qa_runtime_input_manifest_path),
                )
            if runtime_scope_hash and runtime_scope_hash != summary_info["scope_hash"]:
                state.add_error(
                    code="strict_trace_scope_hash_mismatch",
                    check_id="strict_trace_ids",
                    message=f"scope_hash mismatch runtime_manifest={runtime_scope_hash} summary={summary_info['scope_hash']}",
                    category="consistency",
                    file=str(qa_runtime_input_manifest_path),
                )
            if runtime_bundle_id and runtime_bundle_id != summary_info["trial_runtime_bundle_id"]:
                state.add_error(
                    code="strict_trace_trial_runtime_bundle_id_mismatch",
                    check_id="strict_trace_ids",
                    message=f"trial_runtime_bundle_id mismatch runtime_manifest={runtime_bundle_id} summary={summary_info['trial_runtime_bundle_id']}",
                    category="consistency",
                    file=str(qa_runtime_input_manifest_path),
                )

        if qa_handoff_validation_manifest_path:
            handoff_validation_payload = read_json(qa_handoff_validation_manifest_path)
            handoff_verdict = norm_text(
                handoff_validation_payload.get("qa_handoff_verdict")
                or handoff_validation_payload.get("handoff_verdict")
            )
            if handoff_verdict and handoff_verdict != "PASS":
                state.add_error(
                    code="strict_trace_handoff_verdict_not_pass",
                    check_id="strict_trace_handoff",
                    message=f"handoff_validation_manifest verdict must be PASS, got={handoff_verdict}",
                    category="consistency",
                    file=str(qa_handoff_validation_manifest_path),
                )

        if classification_bundle_manifest_path:
            classification_bundle_payload = read_json(classification_bundle_manifest_path)
            classification_bundle_id = norm_text(classification_bundle_payload.get("bundle_id"))
            if classification_bundle_id and classification_bundle_id != summary_info["bundle_id"]:
                state.add_error(
                    code="strict_trace_classification_bundle_id_mismatch",
                    check_id="strict_trace_classification_bundle",
                    message=f"classification_bundle_manifest bundle_id mismatch: {classification_bundle_id} vs {summary_info['bundle_id']}",
                    category="consistency",
                    file=str(classification_bundle_manifest_path),
                )

        selected_units = unit_results
        if selected_unit_filter:
            selected_units = [
                u
                for u in selected_units
                if norm_text(u.get("planned_unit_id")) in selected_unit_filter
            ]
        if selected_fair_filter:
            selected_units = [
                u for u in selected_units if norm_text(u.get("fair_slug")) in selected_fair_filter
            ]
        if selected_lane_filter:
            selected_units = [
                u for u in selected_units if norm_text(u.get("lane")) in selected_lane_filter
            ]

        validated_unit_count = len(selected_units)
        validated_row_count = sum(parse_int(u.get("executed_row_count")) or 0 for u in selected_units)
        if validated_unit_count <= 0 or validated_row_count <= 0:
            state.add_error(
                code="empty_handoff_candidate_set",
                check_id="selected_handoff_candidate_set",
                message=(
                    "selected handoff candidate set is empty or zero rows: "
                    f"validated_unit_count={validated_unit_count}, validated_row_count={validated_row_count}"
                ),
                category="impossible_set",
                file=str(bundle_result_path),
            )

        if state.errors:
            verdict = VERDICT_FAIL
            exit_code = choose_fail_exit(state.errors)
            adoption_handoff_allowed_final = False
            manual_review_required = True
            retry_recommended = True
        else:
            hold_reasons: list[str] = []
            if summary_info["qa_runner_status"] == RUNNER_STATUS_PARTIAL:
                hold_reasons.append("qa_runner_status_partial_success")
            if summary_info["manual_review_required"]:
                hold_reasons.append("summary_manual_review_required_true")
            if summary_info["retry_recommended"]:
                hold_reasons.append("summary_retry_recommended_true")
            if summary_info["failed_unit_count"] > 0 or summary_info["deferred_unit_count"] > 0:
                hold_reasons.append("failed_or_deferred_units_present")
            if summary_info["warning_count"] > 0:
                hold_reasons.append("summary_warning_count_gt_zero")
            if state.warnings:
                hold_reasons.append("validator_warnings_present")

            if hold_reasons:
                verdict = VERDICT_HOLD
                exit_code = EXIT_HOLD
                adoption_handoff_allowed_final = False
                manual_review_required = True
                retry_recommended = False
                for reason in hold_reasons:
                    state.add_warning(
                        code="hold_reason",
                        check_id="verdict_policy_hold",
                        message=f"hold reason: {reason}",
                    )
            else:
                verdict = VERDICT_PASS
                exit_code = EXIT_PASS
                adoption_handoff_allowed_final = True
                manual_review_required = False
                retry_recommended = False

        summary_payload = {
            "task_id": "TASK209",
            "run_id": run_id,
            "started_at": started_at,
            "completed_at": utc_now_iso(),
            "adoption_handoff_verdict": verdict,
            "adoption_handoff_allowed": adoption_handoff_allowed_final,
            "manual_review_required": manual_review_required,
            "retry_recommended": retry_recommended,
            "validated_unit_count": validated_unit_count,
            "validated_row_count": validated_row_count,
            "error_count": len(state.errors),
            "warning_count": len(state.warnings),
            "ids": {
                "classification_run_id": summary_info["classification_run_id"],
                "bundle_id": summary_info["bundle_id"],
                "trial_runtime_bundle_id": summary_info["trial_runtime_bundle_id"],
                "trial_runner_bundle_id": summary_info["trial_runner_bundle_id"],
                "qa_runtime_bundle_id": summary_info["qa_runtime_bundle_id"],
                "qa_runner_bundle_id": summary_info["qa_runner_bundle_id"],
            },
            "scope_hash": summary_info["scope_hash"],
            "selected_unit_ids": [u["planned_unit_id"] for u in selected_units],
            "selected_fair_slug_set": sorted(
                {u["fair_slug"] for u in selected_units if norm_text(u["fair_slug"])}
            ),
            "selected_lane_set": sorted(
                {u["lane"] for u in selected_units if norm_text(u["lane"])}
            ),
            "resolved_inputs": resolved,
            "exit_code": exit_code,
            "output_paths": {k: str(v) for k, v in output_paths.items()},
            "adoption_minimum_set": {
                "qa_adoption_handoff_manifest_json": str(qa_adoption_handoff_manifest_path),
                "qa_execution_summary_json": str(summary_path),
                "qa_bundle_result_csv": str(bundle_result_path),
                "qa_unit_result_json_paths": [
                    u["qa_unit_result_json_path"] for u in selected_units
                ],
                "qa_unit_rows_csv_paths": [
                    u["qa_unit_rows_csv_path"] for u in selected_units
                ],
                "qa_failure_queue_csv": failure_queue_path,
                "qa_defer_queue_csv": defer_queue_path,
                "scope_hash": summary_info["scope_hash"],
                "target_year_set": sorted(
                    {u["target_year"] for u in selected_units if norm_text(u["target_year"])}
                ),
                "fair_slug_set": sorted(
                    {u["fair_slug"] for u in selected_units if norm_text(u["fair_slug"])}
                ),
                "lane_set": sorted(
                    {u["lane"] for u in selected_units if norm_text(u["lane"])}
                ),
            },
        }
        write_json(output_paths["summary_json"], summary_payload)
        write_json(
            output_paths["manifest_json"],
            {
                "task_id": "TASK209",
                "run_id": run_id,
                "created_at": utc_now_iso(),
                "adoption_handoff_verdict": verdict,
                "exit_code": exit_code,
                "inputs": resolved,
                "outputs": {k: str(v) for k, v in output_paths.items()},
                "adoption_minimum_set": summary_payload["adoption_minimum_set"],
            },
        )

        report_lines = [
            "# TASK209 Adoption Handoff Validation Report",
            "",
            f"- adoption_handoff_verdict: `{verdict}`",
            f"- exit_code: `{exit_code}`",
            f"- validated_unit_count: `{validated_unit_count}`",
            f"- validated_row_count: `{validated_row_count}`",
            f"- error_count: `{len(state.errors)}`",
            f"- warning_count: `{len(state.warnings)}`",
            "",
            "## Target Bundle",
            f"- qa_runner_bundle_id: `{summary_info['qa_runner_bundle_id']}`",
            f"- qa_runtime_bundle_id: `{summary_info['qa_runtime_bundle_id']}`",
            f"- trial_runner_bundle_id: `{summary_info['trial_runner_bundle_id']}`",
            f"- classification_run_id: `{summary_info['classification_run_id']}`",
            f"- bundle_id: `{summary_info['bundle_id']}`",
            f"- trial_runtime_bundle_id: `{summary_info['trial_runtime_bundle_id']}`",
            f"- scope_hash: `{summary_info['scope_hash']}`",
            "",
            "## Failures",
        ]
        if state.errors:
            report_lines.extend(
                [
                    f"- [{err['category']}/{err['code']}] {err['message']}"
                    for err in state.errors
                ]
            )
        else:
            report_lines.append("- (none)")
        report_lines.extend(["", "## Warnings"])
        if state.warnings:
            report_lines.extend(
                [
                    f"- [{warn['category']}/{warn['code']}] {warn['message']}"
                    for warn in state.warnings
                ]
            )
        else:
            report_lines.append("- (none)")
        report_lines.extend(
            [
                "",
                "## Next Action",
                "- PASS: proceed to adoption safe-replace planning/execution gate",
                "- HOLD: manual review then retry validator",
                "- FAIL: fix bundle integrity before retry",
            ]
        )
        write_md(output_paths["report_md"], report_lines)
        write_csv(
            output_paths["errors_csv"],
            state.errors,
            ["severity", "category", "code", "check_id", "message", "file", "row_key"],
        )
        write_csv(
            output_paths["warnings_csv"],
            state.warnings,
            ["severity", "category", "code", "check_id", "message", "file", "row_key"],
        )
        return exit_code
    except Exception as exc:
        summary_payload = {
            "task_id": "TASK209",
            "run_id": run_id,
            "started_at": started_at,
            "completed_at": utc_now_iso(),
            "adoption_handoff_verdict": VERDICT_FAIL,
            "adoption_handoff_allowed": False,
            "manual_review_required": True,
            "retry_recommended": False,
            "validated_unit_count": 0,
            "validated_row_count": 0,
            "error_count": 1,
            "warning_count": len(state.warnings),
            "exit_code": EXIT_INTERNAL_FAILURE,
            "internal_error": f"{type(exc).__name__}: {exc}",
            "output_paths": {k: str(v) for k, v in output_paths.items()},
        }
        write_json(output_paths["summary_json"], summary_payload)
        write_json(
            output_paths["manifest_json"],
            {
                "task_id": "TASK209",
                "run_id": run_id,
                "created_at": utc_now_iso(),
                "adoption_handoff_verdict": VERDICT_FAIL,
                "exit_code": EXIT_INTERNAL_FAILURE,
                "internal_error": f"{type(exc).__name__}: {exc}",
                "outputs": {k: str(v) for k, v in output_paths.items()},
            },
        )
        write_md(
            output_paths["report_md"],
            [
                "# TASK209 Adoption Handoff Validation Report",
                "",
                f"- adoption_handoff_verdict: `{VERDICT_FAIL}`",
                f"- exit_code: `{EXIT_INTERNAL_FAILURE}`",
                "",
                "## Internal Error",
                f"- `{type(exc).__name__}: {exc}`",
            ],
        )
        state.add_error(
            code="internal_exception",
            check_id="main_exception",
            message=f"{type(exc).__name__}: {exc}",
            category="internal",
        )
        write_csv(
            output_paths["errors_csv"],
            state.errors,
            ["severity", "category", "code", "check_id", "message", "file", "row_key"],
        )
        write_csv(
            output_paths["warnings_csv"],
            state.warnings,
            ["severity", "category", "code", "check_id", "message", "file", "row_key"],
        )
        return EXIT_INTERNAL_FAILURE


if __name__ == "__main__":
    raise SystemExit(main())

