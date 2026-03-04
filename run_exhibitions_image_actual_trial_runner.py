#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

EXIT_SUCCESS = 0
EXIT_FAIL_MISSING_REQUIRED = 10
EXIT_FAIL_SCHEMA = 11
EXIT_FAIL_CONSISTENCY = 12
EXIT_FAIL_IMPOSSIBLE_SET = 13
EXIT_HOLD = 20
EXIT_PARTIAL_SUCCESS = 21
EXIT_INTERNAL = 30

STATUS_SUCCESS = "SUCCESS"
STATUS_PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
STATUS_HOLD = "HOLD"
STATUS_FAIL_FAST = "FAIL_FAST"
STATUS_INTERNAL_FAILURE = "INTERNAL_FAILURE"

LANE_KEEP = "Keep-Current"
LANE_SAFE = "Safe-But-Provenance-Gated"
LANE_GUARD = "Guard-First-Then-Upgrade"


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


def compact_token(value: str, fallback: str = "x", max_len: int = 40) -> str:
    text = norm_text(value)
    if not text:
        return fallback
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in text)
    safe = "-".join(part for part in safe.split("-") if part)
    if not safe:
        safe = fallback
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]
    if len(safe) > max_len:
        safe = safe[:max_len]
    return f"{safe}-{digest}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Execute actual trial per planned_unit_id from READY runtime bundle "
            "(no post-trial QA/adoption/rollback execution)."
        )
    )
    parser.add_argument("--trial-runtime-input-manifest", default="")
    parser.add_argument("--trial-runtime-unit-summary", default="")
    parser.add_argument("--trial-runtime-target-rows-csv", default="")
    parser.add_argument("--trial-runtime-target-units-csv", default="")
    parser.add_argument("--trial-runtime-scope-json", default="")
    parser.add_argument("--trial-runtime-report-md", default="")
    parser.add_argument("--trial-runtime-errors-csv", default="")
    parser.add_argument("--trial-runtime-warnings-csv", default="")
    parser.add_argument("--resolved-input-manifest-json", default="")
    parser.add_argument("--classification-bundle-manifest", default="")
    parser.add_argument("--handoff-validation-manifest", default="")
    parser.add_argument("--classification-integration-summary-json", default="")
    parser.add_argument("--handoff-validation-summary-json", default="")

    parser.add_argument("--output-dir", default="data/phase1_seed10/logs")
    parser.add_argument("--planned-unit-id", action="append", default=[])
    parser.add_argument("--fair-slug", action="append", default=[])
    parser.add_argument("--lane", action="append", default=[])
    parser.add_argument("--gallery-name", action="append", default=[])
    parser.add_argument("--trial-runner-bundle-id", default="")

    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--strict-trace", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--continue-on-unit-failure", action="store_true")
    parser.add_argument("--fail-on-output-collision", action="store_true")
    parser.add_argument("--fail-on-policy-violation", action="store_true")

    parser.add_argument(
        "--unit-executor",
        choices=["noop", "collector-subprocess"],
        default="noop",
        help="Execution backend. Keep noop for fixture/smoke safety.",
    )
    parser.add_argument(
        "--collector-script",
        default="run_phase1_seed10_exhibition_image_collect.py",
        help="Used only when --unit-executor collector-subprocess and not dry-run.",
    )
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


class RunnerError(Exception):
    def __init__(self, exit_code: int, reason_code: str, message: str) -> None:
        super().__init__(message)
        self.exit_code = int(exit_code)
        self.reason_code = reason_code
        self.message = message


class RunnerState:
    def __init__(self) -> None:
        self.errors: list[dict[str, Any]] = []
        self.warnings: list[dict[str, Any]] = []

    def add_error(
        self,
        *,
        code: str,
        check_id: str,
        message: str,
        category: str = "validation",
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
        category: str = "validation",
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


def choose_fail_exit(errors: list[dict[str, Any]]) -> int:
    categories = {norm_text(err.get("category")) for err in errors}
    if "missing_artifact" in categories:
        return EXIT_FAIL_MISSING_REQUIRED
    if "schema" in categories:
        return EXIT_FAIL_SCHEMA
    if "impossible_set" in categories:
        return EXIT_FAIL_IMPOSSIBLE_SET
    return EXIT_FAIL_CONSISTENCY


def require_file(path_text: str, *, label: str, state: RunnerState) -> Path | None:
    text = norm_text(path_text)
    if not text:
        state.add_error(
            code="required_path_missing",
            check_id="required_file_presence",
            message=f"required path missing: {label}",
            category="missing_artifact",
            file=label,
        )
        return None
    path = Path(text)
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
    fields: list[str], required: list[str], *, artifact: str, state: RunnerState
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


def build_output_paths(output_dir: Path, run_id: str) -> dict[str, Path]:
    return {
        "manifest_json": output_dir / f"exhibitions_image_task_t201_trial_execution_manifest_{run_id}.json",
        "summary_json": output_dir / f"exhibitions_image_task_t201_trial_execution_summary_{run_id}.json",
        "report_md": output_dir / f"exhibitions_image_task_t201_trial_execution_report_{run_id}.md",
        "bundle_result_csv": output_dir / f"exhibitions_image_task_t201_trial_bundle_result_{run_id}.csv",
        "qa_handoff_manifest_json": output_dir
        / f"exhibitions_image_task_t201_trial_qa_handoff_manifest_{run_id}.json",
        "defer_queue_csv": output_dir / f"exhibitions_image_task_t201_trial_defer_queue_{run_id}.csv",
        "failure_queue_csv": output_dir / f"exhibitions_image_task_t201_trial_failure_queue_{run_id}.csv",
        "errors_csv": output_dir / f"exhibitions_image_task_t201_trial_execution_errors_{run_id}.csv",
        "warnings_csv": output_dir / f"exhibitions_image_task_t201_trial_execution_warnings_{run_id}.csv",
    }


def validate_output_collision(paths: dict[str, Path], state: RunnerState) -> None:
    for key, path in paths.items():
        if path.exists():
            state.add_error(
                code="output_collision",
                check_id="output_collision",
                message=f"output path exists: {key} -> {path}",
                category="consistency",
                file=str(path),
            )


def parse_force_unit_status_map() -> dict[str, str]:
    text = norm_text(os.environ.get("TASK201_FORCE_UNIT_STATUS_JSON"))
    if not text:
        return {}
    payload = json.loads(text)
    if not isinstance(payload, dict):
        return {}
    out: dict[str, str] = {}
    for k, v in payload.items():
        key = norm_text(k)
        value = norm_text(v).lower()
        if key and value in {"success", "failed", "deferred"}:
            out[key] = value
    return out


def unit_policy_check(unit: dict[str, Any], state: RunnerState, fail_on_policy: bool) -> None:
    lane = norm_text(unit.get("lane"))
    galleries = parse_int(unit.get("gallery_count")) or 0
    seeds = parse_int(unit.get("trial_ready_seed_count")) or 0
    violation = False
    if lane == LANE_SAFE:
        if galleries > 10 or seeds > 150:
            violation = True
    elif lane == LANE_GUARD:
        if galleries > 4 or seeds > 60:
            violation = True
    if violation:
        fn = state.add_error if fail_on_policy else state.add_warning
        fn(
            code="unit_policy_violation",
            check_id="unit_policy",
            message=(
                f"unit policy exceeded for {norm_text(unit.get('planned_unit_id'))}: "
                f"lane={lane}, galleries={galleries}, seeds={seeds}"
            ),
            category="consistency",
            row_key=norm_text(unit.get("planned_unit_id")),
        )


def simulate_unit_result(
    unit: dict[str, Any], unit_rows: list[dict[str, Any]], actual_trial_run_id: str
) -> dict[str, Any]:
    status_map = parse_force_unit_status_map()
    forced = status_map.get(norm_text(unit.get("planned_unit_id")), "success")
    failed_count = len(unit_rows) if forced == "failed" else 0
    deferred_count = len(unit_rows) if forced == "deferred" else 0
    succeeded_count = len(unit_rows) if forced == "success" else 0
    return {
        "unit_status": "SUCCESS" if forced == "success" else ("FAILED" if forced == "failed" else "DEFERRED"),
        "actual_trial_run_id": actual_trial_run_id,
        "executed_row_count": len(unit_rows),
        "succeeded_row_count": succeeded_count,
        "failed_row_count": failed_count,
        "deferred_row_count": deferred_count,
        "execution_backend": "noop",
        "exit_code": 0 if forced == "success" else 12,
        "error_message": "" if forced == "success" else f"simulated_{forced}",
    }

def run_collector_for_unit(
    *,
    args: argparse.Namespace,
    unit: dict[str, Any],
    unit_rows: list[dict[str, Any]],
    output_dir: Path,
    actual_trial_run_id: str,
) -> dict[str, Any]:
    unit_id = norm_text(unit.get("planned_unit_id"))
    unit_token = compact_token(unit_id, fallback="unit", max_len=8)
    run_token = compact_token(actual_trial_run_id, fallback="run", max_len=8)
    targets_csv_path = output_dir / f"t201_utarget_{unit_token}_{run_token}.csv"
    summary_json_path = output_dir / f"t201_ucsum_{unit_token}_{run_token}.json"
    target_fields = ["fair_slug", "gallery_name_en", "source_url", "target_year"]
    write_csv(targets_csv_path, unit_rows, target_fields)
    cmd = [
        sys.executable,
        str(args.collector_script),
        "--targets-csv",
        str(targets_csv_path),
        "--target-year",
        str(parse_int(unit.get("target_year")) or 2025),
        "--output-json",
        str(summary_json_path),
    ]
    completed = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if completed.returncode != 0:
        return {
            "unit_status": "FAILED",
            "actual_trial_run_id": actual_trial_run_id,
            "executed_row_count": len(unit_rows),
            "succeeded_row_count": 0,
            "failed_row_count": len(unit_rows),
            "deferred_row_count": 0,
            "execution_backend": "collector-subprocess",
            "exit_code": int(completed.returncode),
            "error_message": (completed.stderr or completed.stdout or "").strip()[:4000],
            "collector_summary_path": str(summary_json_path),
            "collector_targets_csv_path": str(targets_csv_path),
        }
    summary_payload: dict[str, Any] = {}
    if summary_json_path.exists():
        summary_payload = read_json(summary_json_path)
    failed_case_count = parse_int(summary_payload.get("failed_case_count")) or 0
    success = failed_case_count == 0
    return {
        "unit_status": "SUCCESS" if success else "FAILED",
        "actual_trial_run_id": actual_trial_run_id,
        "executed_row_count": parse_int(summary_payload.get("seed_exhibition_count")) or len(unit_rows),
        "succeeded_row_count": (parse_int(summary_payload.get("seed_exhibition_count")) or len(unit_rows))
        - failed_case_count,
        "failed_row_count": failed_case_count,
        "deferred_row_count": 0,
        "execution_backend": "collector-subprocess",
        "exit_code": int(completed.returncode),
        "error_message": "",
        "collector_summary_path": str(summary_json_path),
        "collector_targets_csv_path": str(targets_csv_path),
    }


def choose_actual_trial_run_id(run_id: str, unit: dict[str, Any]) -> str:
    planned = norm_text(unit.get("planned_trial_run_id"))
    if planned:
        return planned
    unit_token = norm_text(unit.get("planned_unit_id")) or "unit"
    return f"{run_id}-{unit_token}"


def main() -> int:
    args = parse_args()
    run_id = norm_text(args.trial_runner_bundle_id) or f"{utc_compact()}-trial-runner"
    output_dir = Path(args.output_dir)
    output_paths = build_output_paths(output_dir, run_id)
    state = RunnerState()
    started_at = utc_now_iso()

    try:
        if norm_text(os.environ.get("TASK201_FORCE_INTERNAL_FAILURE")) == "1":
            raise RuntimeError("forced_internal_failure_for_test")

        required_paths = {
            "trial_runtime_input_manifest_json": require_file(
                args.trial_runtime_input_manifest, label="trial_runtime_input_manifest_json", state=state
            ),
            "trial_runtime_unit_summary_json": require_file(
                args.trial_runtime_unit_summary, label="trial_runtime_unit_summary_json", state=state
            ),
            "trial_runtime_target_rows_csv": require_file(
                args.trial_runtime_target_rows_csv, label="trial_runtime_target_rows_csv", state=state
            ),
            "trial_runtime_target_units_csv": require_file(
                args.trial_runtime_target_units_csv, label="trial_runtime_target_units_csv", state=state
            ),
            "trial_runtime_scope_json": require_file(
                args.trial_runtime_scope_json, label="trial_runtime_scope_json", state=state
            ),
            "trial_runtime_report_md": require_file(
                args.trial_runtime_report_md, label="trial_runtime_report_md", state=state
            ),
        }

        if norm_text(args.trial_runtime_errors_csv):
            require_file(args.trial_runtime_errors_csv, label="trial_runtime_errors_csv", state=state)
        if norm_text(args.trial_runtime_warnings_csv):
            require_file(args.trial_runtime_warnings_csv, label="trial_runtime_warnings_csv", state=state)
        if args.strict and norm_text(args.resolved_input_manifest_json):
            require_file(
                args.resolved_input_manifest_json,
                label="resolved_input_manifest_json",
                state=state,
            )
        elif args.strict:
            state.add_error(
                code="strict_required_missing",
                check_id="strict_required",
                message="resolved_input_manifest_json is required in strict mode",
                category="missing_artifact",
            )
        if args.strict_trace:
            require_file(
                args.classification_bundle_manifest,
                label="classification_bundle_manifest_json",
                state=state,
            )
            require_file(
                args.handoff_validation_manifest,
                label="handoff_validation_manifest_json",
                state=state,
            )

        if args.fail_on_output_collision:
            validate_output_collision(output_paths, state)

        if state.errors:
            raise RunnerError(choose_fail_exit(state.errors), "preflight_required_missing", "required preflight failed")

        manifest_path = required_paths["trial_runtime_input_manifest_json"]
        unit_summary_path = required_paths["trial_runtime_unit_summary_json"]
        rows_csv_path = required_paths["trial_runtime_target_rows_csv"]
        units_csv_path = required_paths["trial_runtime_target_units_csv"]
        scope_json_path = required_paths["trial_runtime_scope_json"]

        assert manifest_path and unit_summary_path and rows_csv_path and units_csv_path and scope_json_path
        runtime_manifest = read_json(manifest_path)
        runtime_unit_summary = read_json(unit_summary_path)
        runtime_scope = read_json(scope_json_path)
        row_fields, row_rows = read_csv(rows_csv_path)
        unit_fields, unit_rows_raw = read_csv(units_csv_path)

        ensure_required_columns(
            row_fields,
            [
                "classification_run_id",
                "bundle_id",
                "trial_runtime_bundle_id",
                "planned_unit_id",
                "planned_trial_run_id",
                "scope_hash",
                "target_year",
                "fair_slug",
                "lane",
                "gallery_name_en",
                "adoption_allowed",
                "trial_ready",
            ],
            artifact=str(rows_csv_path),
            state=state,
        )
        ensure_required_columns(
            unit_fields,
            [
                "classification_run_id",
                "bundle_id",
                "trial_runtime_bundle_id",
                "planned_unit_id",
                "planned_trial_run_id",
                "scope_hash",
                "target_year",
                "fair_slug",
                "lane",
            ],
            artifact=str(units_csv_path),
            state=state,
        )
        if state.errors:
            raise RunnerError(choose_fail_exit(state.errors), "schema_validation_failed", "schema validation failed")

        adapter_status = norm_text(runtime_manifest.get("adapter_status") or runtime_unit_summary.get("adapter_status"))
        trial_runtime_ready = parse_bool(runtime_unit_summary.get("trial_runtime_ready"))
        if adapter_status != "READY" or trial_runtime_ready is not True:
            raise RunnerError(EXIT_FAIL_CONSISTENCY, "runtime_bundle_not_ready", "runtime bundle is not READY")

        manifest_ids = runtime_manifest.get("ids") or {}
        manifest_scope = runtime_manifest.get("scope") or {}
        classification_run_id_values = {
            norm_text(manifest_ids.get("classification_run_id")),
            norm_text(runtime_unit_summary.get("ids", {}).get("classification_run_id")),
        }
        bundle_id_values = {
            norm_text(manifest_ids.get("bundle_id")),
            norm_text(runtime_unit_summary.get("ids", {}).get("bundle_id")),
        }
        runtime_bundle_values = {
            norm_text(manifest_ids.get("trial_runtime_bundle_id")),
            norm_text(runtime_unit_summary.get("ids", {}).get("trial_runtime_bundle_id")),
        }
        scope_hash_values = {
            norm_text(manifest_scope.get("scope_hash")),
            norm_text(runtime_scope.get("scope_hash")),
        }

        filtered_unit_rows: list[dict[str, Any]] = []
        for unit in unit_rows_raw:
            unit = {k: norm_text(v) for k, v in unit.items()}
            classification_run_id_values.add(norm_text(unit.get("classification_run_id")))
            bundle_id_values.add(norm_text(unit.get("bundle_id")))
            runtime_bundle_values.add(norm_text(unit.get("trial_runtime_bundle_id")))
            scope_hash_values.add(norm_text(unit.get("scope_hash")))
            filtered_unit_rows.append(unit)

        for row in row_rows:
            classification_run_id_values.add(norm_text(row.get("classification_run_id")))
            bundle_id_values.add(norm_text(row.get("bundle_id")))
            runtime_bundle_values.add(norm_text(row.get("trial_runtime_bundle_id")))
            scope_hash_values.add(norm_text(row.get("scope_hash")))

        classification_run_id_values = {v for v in classification_run_id_values if v}
        bundle_id_values = {v for v in bundle_id_values if v}
        runtime_bundle_values = {v for v in runtime_bundle_values if v}
        scope_hash_values = {v for v in scope_hash_values if v}
        if len(classification_run_id_values) > 1:
            state.add_error(
                code="classification_run_id_mismatch",
                check_id="id_consistency",
                message=f"classification_run_id mismatch: {sorted(classification_run_id_values)}",
                category="consistency",
            )
        if len(bundle_id_values) > 1:
            state.add_error(
                code="bundle_id_mismatch",
                check_id="id_consistency",
                message=f"bundle_id mismatch: {sorted(bundle_id_values)}",
                category="consistency",
            )
        if len(runtime_bundle_values) > 1:
            state.add_error(
                code="trial_runtime_bundle_id_mismatch",
                check_id="id_consistency",
                message=f"trial_runtime_bundle_id mismatch: {sorted(runtime_bundle_values)}",
                category="consistency",
            )
        if len(scope_hash_values) > 1:
            state.add_error(
                code="scope_hash_mismatch",
                check_id="scope_consistency",
                message=f"scope_hash mismatch: {sorted(scope_hash_values)}",
                category="consistency",
            )

        fair_filter = {norm_text(v) for v in args.fair_slug if norm_text(v)}
        lane_filter = {norm_text(v) for v in args.lane if norm_text(v)}
        gallery_filter = {norm_text(v) for v in args.gallery_name if norm_text(v)}
        unit_filter = {norm_text(v) for v in args.planned_unit_id if norm_text(v)}

        rows_by_unit: dict[str, list[dict[str, Any]]] = {}
        for row in row_rows:
            unit_id = norm_text(row.get("planned_unit_id"))
            if not unit_id:
                state.add_error(
                    code="planned_unit_id_empty",
                    check_id="row_unit_join",
                    message="row has empty planned_unit_id",
                    category="schema",
                )
                continue

            if parse_bool(row.get("trial_ready")) is not True:
                continue
            if parse_bool(row.get("adoption_allowed")) is not False:
                state.add_error(
                    code="adoption_allowed_not_false",
                    check_id="trial_row_gate",
                    message=f"row adoption_allowed must be false for unit={unit_id}",
                    category="consistency",
                    row_key=unit_id,
                )
                continue

            lane = norm_text(row.get("lane"))
            if lane == LANE_KEEP:
                continue

            fair_slug = norm_text(row.get("fair_slug"))
            gallery_name = norm_text(row.get("gallery_name_en"))
            if fair_filter and fair_slug not in fair_filter:
                continue
            if lane_filter and lane not in lane_filter:
                continue
            if gallery_filter and gallery_name not in gallery_filter:
                continue
            if unit_filter and unit_id not in unit_filter:
                continue

            rows_by_unit.setdefault(unit_id, []).append({k: norm_text(v) for k, v in row.items()})

        selected_units: list[dict[str, Any]] = []
        unit_seen: set[str] = set()
        for unit in filtered_unit_rows:
            unit_id = norm_text(unit.get("planned_unit_id"))
            if not unit_id:
                state.add_error(
                    code="planned_unit_id_empty",
                    check_id="unit_primary_key",
                    message="unit row has empty planned_unit_id",
                    category="schema",
                )
                continue
            if unit_id in unit_seen:
                state.add_error(
                    code="duplicate_unit_id",
                    check_id="unit_primary_key",
                    message=f"duplicate unit id: {unit_id}",
                    category="consistency",
                    row_key=unit_id,
                )
                continue
            unit_seen.add(unit_id)
            unit_rows = rows_by_unit.get(unit_id, [])
            if not unit_rows:
                continue

            unit_scope_hash = norm_text(unit.get("scope_hash"))
            unit_year = norm_text(unit.get("target_year"))
            unit_fair = norm_text(unit.get("fair_slug"))
            unit_lane = norm_text(unit.get("lane"))
            for r in unit_rows:
                if (
                    norm_text(r.get("scope_hash")) != unit_scope_hash
                    or norm_text(r.get("target_year")) != unit_year
                    or norm_text(r.get("fair_slug")) != unit_fair
                    or norm_text(r.get("lane")) != unit_lane
                ):
                    state.add_error(
                        code="unit_row_scope_mismatch",
                        check_id="unit_scope_consistency",
                        message=f"unit/row scope mismatch in unit={unit_id}",
                        category="consistency",
                        row_key=unit_id,
                    )
                    break

            unit_policy_check(unit, state, args.fail_on_policy_violation)
            selected_units.append(unit)

        if state.errors:
            raise RunnerError(choose_fail_exit(state.errors), "preflight_consistency_failed", "consistency preflight failed")

        if not selected_units:
            summary_payload = {
                "task_id": "TASK201",
                "run_id": run_id,
                "started_at": started_at,
                "completed_at": utc_now_iso(),
                "trial_runner_status": STATUS_HOLD,
                "executed_unit_count": 0,
                "succeeded_unit_count": 0,
                "failed_unit_count": 0,
                "deferred_unit_count": 0,
                "qa_handoff_allowed": False,
                "manual_review_required": True,
                "retry_recommended": False,
                "error_count": 0,
                "warning_count": len(state.warnings),
                "ids": {
                    "classification_run_id": next(iter(classification_run_id_values), ""),
                    "bundle_id": next(iter(bundle_id_values), ""),
                    "trial_runtime_bundle_id": next(iter(runtime_bundle_values), ""),
                    "trial_runner_bundle_id": run_id,
                },
                "scope": runtime_scope,
                "selected_unit_ids": [],
            }
            manifest_payload = {
                "task_id": "TASK201",
                "run_id": run_id,
                "created_at": utc_now_iso(),
                "trial_runner_status": STATUS_HOLD,
                "inputs": {
                    "trial_runtime_input_manifest_json": str(manifest_path),
                    "trial_runtime_unit_summary_json": str(unit_summary_path),
                    "trial_runtime_target_rows_csv": str(rows_csv_path),
                    "trial_runtime_target_units_csv": str(units_csv_path),
                    "trial_runtime_scope_json": str(scope_json_path),
                },
                "outputs": {k: str(v) for k, v in output_paths.items()},
                "selected_unit_ids": [],
            }
            qa_handoff_payload = {
                "task_id": "TASK201",
                "run_id": run_id,
                "trial_runner_status": STATUS_HOLD,
                "qa_handoff_allowed": False,
                "reason": "no_executable_units",
            }
            report_lines = [
                "# TASK201 Trial Execution Report",
                "",
                f"- trial_runner_status: `{STATUS_HOLD}`",
                "- reason: `no_executable_units`",
            ]
            write_json(output_paths["summary_json"], summary_payload)
            write_json(output_paths["manifest_json"], manifest_payload)
            write_json(output_paths["qa_handoff_manifest_json"], qa_handoff_payload)
            write_md(output_paths["report_md"], report_lines)
            write_csv(
                output_paths["bundle_result_csv"],
                [],
                [
                    "planned_unit_id",
                    "actual_trial_run_id",
                    "unit_status",
                    "executed_row_count",
                    "succeeded_row_count",
                    "failed_row_count",
                    "deferred_row_count",
                    "exit_code",
                    "error_message",
                ],
            )
            if state.warnings:
                write_csv(output_paths["warnings_csv"], state.warnings, list(state.warnings[0].keys()))
            else:
                write_csv(
                    output_paths["warnings_csv"],
                    [],
                    ["severity", "category", "code", "check_id", "message", "file", "row_key"],
                )
            write_csv(
                output_paths["errors_csv"],
                [],
                ["severity", "category", "code", "check_id", "message", "file", "row_key"],
            )
            return EXIT_HOLD

        unit_results: list[dict[str, Any]] = []
        bundle_rows: list[dict[str, Any]] = []
        failed_queue: list[dict[str, Any]] = []
        defer_queue: list[dict[str, Any]] = []
        executed_unit_ids: list[str] = []

        for unit in selected_units:
            unit_id = norm_text(unit.get("planned_unit_id"))
            unit_rows = rows_by_unit.get(unit_id, [])
            actual_trial_run_id = choose_actual_trial_run_id(run_id, unit)
            executed_unit_ids.append(unit_id)

            if args.dry_run or args.unit_executor == "noop":
                exec_result = simulate_unit_result(unit, unit_rows, actual_trial_run_id)
            else:
                exec_result = run_collector_for_unit(
                    args=args,
                    unit=unit,
                    unit_rows=unit_rows,
                    output_dir=output_dir,
                    actual_trial_run_id=actual_trial_run_id,
                )

            unit_status = norm_text(exec_result.get("unit_status"))
            if unit_status == "FAILED":
                failed_queue.append(
                    {
                        "planned_unit_id": unit_id,
                        "actual_trial_run_id": actual_trial_run_id,
                        "lane": norm_text(unit.get("lane")),
                        "fair_slug": norm_text(unit.get("fair_slug")),
                        "target_year": norm_text(unit.get("target_year")),
                        "failed_row_count": exec_result.get("failed_row_count", ""),
                        "error_message": norm_text(exec_result.get("error_message")),
                    }
                )
            elif unit_status == "DEFERRED":
                defer_queue.append(
                    {
                        "planned_unit_id": unit_id,
                        "actual_trial_run_id": actual_trial_run_id,
                        "lane": norm_text(unit.get("lane")),
                        "fair_slug": norm_text(unit.get("fair_slug")),
                        "target_year": norm_text(unit.get("target_year")),
                        "deferred_row_count": exec_result.get("deferred_row_count", ""),
                        "reason": norm_text(exec_result.get("error_message")) or "deferred",
                    }
                )

            unit_result_payload = {
                "task_id": "TASK201",
                "run_id": run_id,
                "planned_unit_id": unit_id,
                "actual_trial_run_id": actual_trial_run_id,
                "trial_runner_bundle_id": run_id,
                "classification_run_id": next(iter(classification_run_id_values), ""),
                "bundle_id": next(iter(bundle_id_values), ""),
                "scope_hash": norm_text(unit.get("scope_hash")),
                "target_year": norm_text(unit.get("target_year")),
                "fair_slug": norm_text(unit.get("fair_slug")),
                "lane": norm_text(unit.get("lane")),
                "gallery_count": norm_text(unit.get("gallery_count")),
                "trial_ready_seed_count": norm_text(unit.get("trial_ready_seed_count")),
                "unit_status": unit_status,
                "execution_backend": norm_text(exec_result.get("execution_backend")),
                "executed_row_count": exec_result.get("executed_row_count", 0),
                "succeeded_row_count": exec_result.get("succeeded_row_count", 0),
                "failed_row_count": exec_result.get("failed_row_count", 0),
                "deferred_row_count": exec_result.get("deferred_row_count", 0),
                "exit_code": exec_result.get("exit_code", 0),
                "error_message": norm_text(exec_result.get("error_message")),
                "collector_summary_path": norm_text(exec_result.get("collector_summary_path")),
                "collector_targets_csv_path": norm_text(exec_result.get("collector_targets_csv_path")),
                "started_at": started_at,
                "completed_at": utc_now_iso(),
            }
            unit_results.append(unit_result_payload)

            unit_token = compact_token(unit_id, fallback="unit", max_len=8)
            run_token = compact_token(run_id, fallback="run", max_len=8)
            unit_rows_path = output_dir / f"t201_urows_{unit_token}_{run_token}.csv"
            unit_result_json_path = output_dir / f"t201_ures_{unit_token}_{run_token}.json"
            unit_result_md_path = output_dir / f"t201_ures_{unit_token}_{run_token}.md"
            write_csv(
                unit_rows_path,
                unit_rows,
                [
                    "classification_run_id",
                    "bundle_id",
                    "trial_runtime_bundle_id",
                    "planned_unit_id",
                    "planned_trial_run_id",
                    "scope_hash",
                    "target_year",
                    "fair_slug",
                    "lane",
                    "gallery_name_en",
                    "source_url",
                    "adoption_allowed",
                    "trial_ready",
                ],
            )
            write_json(unit_result_json_path, unit_result_payload)
            write_md(
                unit_result_md_path,
                [
                    "# TASK201 Trial Unit Result",
                    "",
                    f"- planned_unit_id: `{unit_id}`",
                    f"- actual_trial_run_id: `{actual_trial_run_id}`",
                    f"- unit_status: `{unit_status}`",
                    f"- executed_row_count: `{unit_result_payload['executed_row_count']}`",
                    f"- succeeded_row_count: `{unit_result_payload['succeeded_row_count']}`",
                    f"- failed_row_count: `{unit_result_payload['failed_row_count']}`",
                    f"- deferred_row_count: `{unit_result_payload['deferred_row_count']}`",
                ],
            )

            bundle_rows.append(
                {
                    "planned_unit_id": unit_id,
                    "actual_trial_run_id": actual_trial_run_id,
                    "unit_status": unit_status,
                    "executed_row_count": unit_result_payload["executed_row_count"],
                    "succeeded_row_count": unit_result_payload["succeeded_row_count"],
                    "failed_row_count": unit_result_payload["failed_row_count"],
                    "deferred_row_count": unit_result_payload["deferred_row_count"],
                    "exit_code": unit_result_payload["exit_code"],
                    "error_message": unit_result_payload["error_message"],
                    "trial_unit_result_json_path": str(unit_result_json_path),
                    "trial_unit_rows_csv_path": str(unit_rows_path),
                }
            )

            if unit_status == "FAILED" and not args.continue_on_unit_failure:
                break

        succeeded_count = len([r for r in unit_results if norm_text(r.get("unit_status")) == "SUCCESS"])
        failed_count = len([r for r in unit_results if norm_text(r.get("unit_status")) == "FAILED"])
        deferred_count = len([r for r in unit_results if norm_text(r.get("unit_status")) == "DEFERRED"])
        executed_count = len(unit_results)

        if executed_count == 0:
            runner_status = STATUS_HOLD
            exit_code = EXIT_HOLD
        elif failed_count == 0 and deferred_count == 0:
            runner_status = STATUS_SUCCESS
            exit_code = EXIT_SUCCESS
        elif succeeded_count > 0:
            runner_status = STATUS_PARTIAL_SUCCESS
            exit_code = EXIT_PARTIAL_SUCCESS
        else:
            runner_status = STATUS_FAIL_FAST
            exit_code = EXIT_FAIL_CONSISTENCY

        qa_handoff_allowed = runner_status in {STATUS_SUCCESS, STATUS_PARTIAL_SUCCESS} and executed_count > 0
        summary_payload = {
            "task_id": "TASK201",
            "run_id": run_id,
            "started_at": started_at,
            "completed_at": utc_now_iso(),
            "trial_runner_status": runner_status,
            "executed_unit_count": executed_count,
            "succeeded_unit_count": succeeded_count,
            "failed_unit_count": failed_count,
            "deferred_unit_count": deferred_count,
            "qa_handoff_allowed": qa_handoff_allowed,
            "manual_review_required": runner_status in {STATUS_HOLD, STATUS_INTERNAL_FAILURE, STATUS_PARTIAL_SUCCESS},
            "retry_recommended": runner_status in {STATUS_FAIL_FAST, STATUS_PARTIAL_SUCCESS},
            "error_count": len(state.errors),
            "warning_count": len(state.warnings),
            "ids": {
                "classification_run_id": next(iter(classification_run_id_values), ""),
                "bundle_id": next(iter(bundle_id_values), ""),
                "trial_runtime_bundle_id": next(iter(runtime_bundle_values), ""),
                "trial_runner_bundle_id": run_id,
            },
            "scope_hash": next(iter(scope_hash_values), ""),
            "selected_unit_ids": [norm_text(u.get("planned_unit_id")) for u in selected_units],
            "executed_unit_ids": executed_unit_ids,
            "output_paths": {k: str(v) for k, v in output_paths.items()},
        }
        manifest_payload = {
            "task_id": "TASK201",
            "run_id": run_id,
            "created_at": utc_now_iso(),
            "trial_runner_status": runner_status,
            "inputs": {
                "trial_runtime_input_manifest_json": str(manifest_path),
                "trial_runtime_unit_summary_json": str(unit_summary_path),
                "trial_runtime_target_rows_csv": str(rows_csv_path),
                "trial_runtime_target_units_csv": str(units_csv_path),
                "trial_runtime_scope_json": str(scope_json_path),
            },
            "outputs": {k: str(v) for k, v in output_paths.items()},
            "executed_unit_ids": executed_unit_ids,
        }
        qa_handoff_payload = {
            "task_id": "TASK201",
            "run_id": run_id,
            "trial_runner_status": runner_status,
            "qa_handoff_allowed": qa_handoff_allowed,
            "trial_runner_bundle_id": run_id,
            "classification_run_id": summary_payload["ids"]["classification_run_id"],
            "bundle_id": summary_payload["ids"]["bundle_id"],
            "scope_hash": summary_payload["scope_hash"],
            "target_year": sorted({norm_text(r.get("target_year")) for r in row_rows if norm_text(r.get("target_year"))}),
            "fair_slug_set": sorted({norm_text(r.get("fair_slug")) for r in row_rows if norm_text(r.get("fair_slug"))}),
            "lane_set": sorted({norm_text(r.get("lane")) for r in row_rows if norm_text(r.get("lane"))}),
            "executed_unit_ids": executed_unit_ids,
            "unit_result_paths": [r["trial_unit_result_json_path"] for r in bundle_rows if r.get("trial_unit_result_json_path")],
            "bundle_summary_path": str(output_paths["summary_json"]),
            "failure_queue_path": str(output_paths["failure_queue_csv"]) if failed_queue else "",
            "defer_queue_path": str(output_paths["defer_queue_csv"]) if defer_queue else "",
        }
        report_lines = [
            "# TASK201 Trial Execution Report",
            "",
            f"- trial_runner_status: `{runner_status}`",
            f"- executed_unit_count: `{executed_count}`",
            f"- succeeded_unit_count: `{succeeded_count}`",
            f"- failed_unit_count: `{failed_count}`",
            f"- deferred_unit_count: `{deferred_count}`",
            f"- qa_handoff_allowed: `{str(qa_handoff_allowed).lower()}`",
        ]
        write_json(output_paths["summary_json"], summary_payload)
        write_json(output_paths["manifest_json"], manifest_payload)
        write_json(output_paths["qa_handoff_manifest_json"], qa_handoff_payload)
        write_md(output_paths["report_md"], report_lines)
        write_csv(
            output_paths["bundle_result_csv"],
            bundle_rows,
            [
                "planned_unit_id",
                "actual_trial_run_id",
                "unit_status",
                "executed_row_count",
                "succeeded_row_count",
                "failed_row_count",
                "deferred_row_count",
                "exit_code",
                "error_message",
                "trial_unit_result_json_path",
                "trial_unit_rows_csv_path",
            ],
        )
        if defer_queue:
            write_csv(
                output_paths["defer_queue_csv"],
                defer_queue,
                [
                    "planned_unit_id",
                    "actual_trial_run_id",
                    "lane",
                    "fair_slug",
                    "target_year",
                    "deferred_row_count",
                    "reason",
                ],
            )
        if failed_queue:
            write_csv(
                output_paths["failure_queue_csv"],
                failed_queue,
                [
                    "planned_unit_id",
                    "actual_trial_run_id",
                    "lane",
                    "fair_slug",
                    "target_year",
                    "failed_row_count",
                    "error_message",
                ],
            )
        if state.errors:
            write_csv(output_paths["errors_csv"], state.errors, list(state.errors[0].keys()))
        else:
            write_csv(
                output_paths["errors_csv"],
                [],
                ["severity", "category", "code", "check_id", "message", "file", "row_key"],
            )
        if state.warnings:
            write_csv(output_paths["warnings_csv"], state.warnings, list(state.warnings[0].keys()))
        else:
            write_csv(
                output_paths["warnings_csv"],
                [],
                ["severity", "category", "code", "check_id", "message", "file", "row_key"],
            )
        return exit_code
    except RunnerError as exc:
        summary_payload = {
            "task_id": "TASK201",
            "run_id": run_id,
            "started_at": started_at,
            "completed_at": utc_now_iso(),
            "trial_runner_status": STATUS_FAIL_FAST,
            "executed_unit_count": 0,
            "succeeded_unit_count": 0,
            "failed_unit_count": 0,
            "deferred_unit_count": 0,
            "qa_handoff_allowed": False,
            "manual_review_required": True,
            "retry_recommended": True,
            "error_count": len(state.errors),
            "warning_count": len(state.warnings),
            "reason_code": exc.reason_code,
            "message": exc.message,
        }
        write_json(output_paths["summary_json"], summary_payload)
        write_json(
            output_paths["manifest_json"],
            {
                "task_id": "TASK201",
                "run_id": run_id,
                "created_at": utc_now_iso(),
                "trial_runner_status": STATUS_FAIL_FAST,
                "exit_code": exc.exit_code,
                "reason_code": exc.reason_code,
                "message": exc.message,
                "outputs": {k: str(v) for k, v in output_paths.items()},
            },
        )
        write_json(
            output_paths["qa_handoff_manifest_json"],
            {
                "task_id": "TASK201",
                "run_id": run_id,
                "trial_runner_status": STATUS_FAIL_FAST,
                "qa_handoff_allowed": False,
                "reason": exc.reason_code,
            },
        )
        write_md(
            output_paths["report_md"],
            [
                "# TASK201 Trial Execution Report",
                "",
                "- trial_runner_status: `FAIL_FAST`",
                f"- reason_code: `{exc.reason_code}`",
                f"- message: `{exc.message}`",
            ],
        )
        if state.errors:
            write_csv(output_paths["errors_csv"], state.errors, list(state.errors[0].keys()))
        else:
            write_csv(
                output_paths["errors_csv"],
                [{"severity": "error", "category": "runtime", "code": exc.reason_code, "check_id": "runner_error", "message": exc.message, "file": "", "row_key": ""}],
                ["severity", "category", "code", "check_id", "message", "file", "row_key"],
            )
        if state.warnings:
            write_csv(output_paths["warnings_csv"], state.warnings, list(state.warnings[0].keys()))
        else:
            write_csv(
                output_paths["warnings_csv"],
                [],
                ["severity", "category", "code", "check_id", "message", "file", "row_key"],
            )
        write_csv(
            output_paths["bundle_result_csv"],
            [],
            [
                "planned_unit_id",
                "actual_trial_run_id",
                "unit_status",
                "executed_row_count",
                "succeeded_row_count",
                "failed_row_count",
                "deferred_row_count",
                "exit_code",
                "error_message",
                "trial_unit_result_json_path",
                "trial_unit_rows_csv_path",
            ],
        )
        return exc.exit_code
    except Exception as exc:  # noqa: BLE001
        message = f"internal_failure:{exc}"
        write_json(
            output_paths["summary_json"],
            {
                "task_id": "TASK201",
                "run_id": run_id,
                "started_at": started_at,
                "completed_at": utc_now_iso(),
                "trial_runner_status": STATUS_INTERNAL_FAILURE,
                "qa_handoff_allowed": False,
                "manual_review_required": True,
                "retry_recommended": True,
                "message": message,
            },
        )
        write_json(
            output_paths["manifest_json"],
            {
                "task_id": "TASK201",
                "run_id": run_id,
                "created_at": utc_now_iso(),
                "trial_runner_status": STATUS_INTERNAL_FAILURE,
                "exit_code": EXIT_INTERNAL,
                "message": message,
                "outputs": {k: str(v) for k, v in output_paths.items()},
            },
        )
        write_json(
            output_paths["qa_handoff_manifest_json"],
            {
                "task_id": "TASK201",
                "run_id": run_id,
                "trial_runner_status": STATUS_INTERNAL_FAILURE,
                "qa_handoff_allowed": False,
                "reason": "internal_failure",
            },
        )
        write_md(
            output_paths["report_md"],
            [
                "# TASK201 Trial Execution Report",
                "",
                "- trial_runner_status: `INTERNAL_FAILURE`",
                f"- message: `{message}`",
            ],
        )
        write_csv(
            output_paths["errors_csv"],
            [{"severity": "error", "category": "runtime", "code": "internal_failure", "check_id": "exception", "message": message, "file": "", "row_key": ""}],
            ["severity", "category", "code", "check_id", "message", "file", "row_key"],
        )
        write_csv(
            output_paths["warnings_csv"],
            [],
            ["severity", "category", "code", "check_id", "message", "file", "row_key"],
        )
        write_csv(
            output_paths["bundle_result_csv"],
            [],
            [
                "planned_unit_id",
                "actual_trial_run_id",
                "unit_status",
                "executed_row_count",
                "succeeded_row_count",
                "failed_row_count",
                "deferred_row_count",
                "exit_code",
                "error_message",
                "trial_unit_result_json_path",
                "trial_unit_rows_csv_path",
            ],
        )
        return EXIT_INTERNAL


if __name__ == "__main__":
    raise SystemExit(main())
