#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

EXIT_READY = 0
EXIT_REJECT_MISSING_REQUIRED = 10
EXIT_REJECT_SCHEMA = 11
EXIT_REJECT_CONSISTENCY = 12
EXIT_HOLD = 20
EXIT_SKIP = 21
EXIT_INTERNAL = 30

LANE_KEEP = "Keep-Current"
LANE_SAFE = "Safe-But-Provenance-Gated"
LANE_GUARD = "Guard-First-Then-Upgrade"

STATUS_READY = "READY"
STATUS_HOLD = "HOLD"
STATUS_REJECT = "REJECT"
STATUS_SKIP = "SKIP"


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build trial runtime input bundle from PASS handoff bundle "
            "(no actual trial/QA/adoption execution)."
        )
    )
    parser.add_argument("--handoff-summary-json", default="")
    parser.add_argument("--handoff-manifest-json", default="")
    parser.add_argument("--lane-ready-inventory-csv", default="")
    parser.add_argument("--unit-plan-csv", default="")
    parser.add_argument("--classification-bundle-manifest", default="")
    parser.add_argument("--classification-integration-summary-json", default="")
    parser.add_argument("--handoff-paths-json", default="")
    parser.add_argument("--resolved-input-manifest-json", default="")
    parser.add_argument("--classification-decision-csv", default="")

    parser.add_argument("--target-year", type=int, default=0)
    parser.add_argument("--fair-slug", action="append", default=[])
    parser.add_argument("--lane", choices=["keep", "safe", "guard", "all"], default="all")
    parser.add_argument("--gallery-name", action="append", default=[])
    parser.add_argument("--planned-unit-id", action="append", default=[])

    parser.add_argument("--output-dir", default="data/phase1_seed10/logs")
    parser.add_argument("--trial-runtime-bundle-id", default="")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--fail-on-output-collision", action="store_true")
    parser.add_argument("--fail-on-policy-violation", action="store_true")
    parser.add_argument("--write-errors-csv", action="store_true")
    parser.add_argument("--write-warnings-csv", action="store_true")
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


def lane_filter_to_class(lane_filter: str) -> str | None:
    mapping = {"keep": LANE_KEEP, "safe": LANE_SAFE, "guard": LANE_GUARD}
    return mapping.get(norm_text(lane_filter))


class AdapterError(Exception):
    def __init__(self, exit_code: int, reason_code: str, message: str) -> None:
        super().__init__(message)
        self.exit_code = int(exit_code)
        self.reason_code = reason_code
        self.message = message


class AdapterState:
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


def require_file(path_text: str, *, label: str, state: AdapterState) -> Path | None:
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
    fields: list[str],
    required: list[str],
    *,
    artifact: str,
    state: AdapterState,
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


def choose_reject_exit(errors: list[dict[str, Any]]) -> int:
    categories = {norm_text(err.get("category")) for err in errors}
    if "missing_artifact" in categories:
        return EXIT_REJECT_MISSING_REQUIRED
    if "schema" in categories:
        return EXIT_REJECT_SCHEMA
    return EXIT_REJECT_CONSISTENCY


def resolve_paths(args: argparse.Namespace) -> dict[str, str]:
    resolved = {
        "handoff_summary_json": norm_text(args.handoff_summary_json),
        "handoff_manifest_json": norm_text(args.handoff_manifest_json),
        "lane_ready_inventory_csv": norm_text(args.lane_ready_inventory_csv),
        "unit_plan_csv": norm_text(args.unit_plan_csv),
        "classification_bundle_manifest_json": norm_text(args.classification_bundle_manifest),
        "classification_integration_summary_json": norm_text(
            args.classification_integration_summary_json
        ),
        "handoff_paths_json": norm_text(args.handoff_paths_json),
        "resolved_input_manifest_json": norm_text(args.resolved_input_manifest_json),
        "classification_decision_csv": norm_text(args.classification_decision_csv),
    }
    if resolved["handoff_manifest_json"] and Path(resolved["handoff_manifest_json"]).exists():
        handoff_manifest = read_json(Path(resolved["handoff_manifest_json"]))
        inputs = handoff_manifest.get("inputs") or {}
        if not resolved["classification_bundle_manifest_json"]:
            resolved["classification_bundle_manifest_json"] = norm_text(
                inputs.get("bundle_manifest_json")
            )
        if not resolved["classification_integration_summary_json"]:
            resolved["classification_integration_summary_json"] = norm_text(
                inputs.get("integration_summary_json")
            )
        if not resolved["handoff_paths_json"]:
            resolved["handoff_paths_json"] = norm_text(inputs.get("handoff_paths_json"))
        if not resolved["lane_ready_inventory_csv"]:
            resolved["lane_ready_inventory_csv"] = norm_text(
                inputs.get("lane_ready_inventory_csv")
            )
        if not resolved["unit_plan_csv"]:
            resolved["unit_plan_csv"] = norm_text(inputs.get("unit_plan_csv"))
        if not resolved["resolved_input_manifest_json"]:
            resolved["resolved_input_manifest_json"] = norm_text(
                inputs.get("resolved_input_manifest_json")
            )
    if (
        resolved["classification_bundle_manifest_json"]
        and Path(resolved["classification_bundle_manifest_json"]).exists()
    ):
        bundle_manifest = read_json(Path(resolved["classification_bundle_manifest_json"]))
        outputs = bundle_manifest.get("classification_outputs") or {}
        if not resolved["lane_ready_inventory_csv"]:
            resolved["lane_ready_inventory_csv"] = norm_text(outputs.get("lane_ready_inventory_csv"))
        if not resolved["unit_plan_csv"]:
            resolved["unit_plan_csv"] = norm_text(outputs.get("unit_plan_csv"))
        if not resolved["classification_decision_csv"]:
            resolved["classification_decision_csv"] = norm_text(outputs.get("classification_decision_csv"))
        if not resolved["resolved_input_manifest_json"]:
            resolved["resolved_input_manifest_json"] = norm_text(
                bundle_manifest.get("resolved_input_manifest_json")
            )
        if not resolved["classification_integration_summary_json"]:
            resolved["classification_integration_summary_json"] = norm_text(
                bundle_manifest.get("classification_integration_summary_json")
            )
        if not resolved["handoff_paths_json"]:
            resolved["handoff_paths_json"] = norm_text(bundle_manifest.get("handoff_paths_json"))
    if resolved["handoff_paths_json"] and Path(resolved["handoff_paths_json"]).exists():
        handoff_paths = read_json(Path(resolved["handoff_paths_json"]))
        required_paths = handoff_paths.get("required_paths") or {}
        optional_paths = handoff_paths.get("optional_paths") or {}
        if not resolved["lane_ready_inventory_csv"]:
            resolved["lane_ready_inventory_csv"] = norm_text(required_paths.get("lane_ready_inventory_csv"))
        if not resolved["unit_plan_csv"]:
            resolved["unit_plan_csv"] = norm_text(required_paths.get("unit_plan_csv"))
        if not resolved["classification_decision_csv"]:
            resolved["classification_decision_csv"] = norm_text(required_paths.get("classification_decision_csv"))
        if not resolved["classification_decision_csv"]:
            resolved["classification_decision_csv"] = norm_text(optional_paths.get("classification_decision_csv"))
    return resolved


def build_output_paths(output_dir: Path, run_id: str) -> dict[str, Path]:
    return {
        "manifest_json": output_dir / f"exhibitions_image_task_t199_trial_runtime_input_manifest_{run_id}.json",
        "unit_summary_json": output_dir / f"exhibitions_image_task_t199_trial_runtime_unit_summary_{run_id}.json",
        "target_rows_csv": output_dir / f"exhibitions_image_task_t199_trial_runtime_target_rows_{run_id}.csv",
        "target_units_csv": output_dir / f"exhibitions_image_task_t199_trial_runtime_target_units_{run_id}.csv",
        "scope_json": output_dir / f"exhibitions_image_task_t199_trial_runtime_scope_{run_id}.json",
        "report_md": output_dir / f"exhibitions_image_task_t199_trial_runtime_report_{run_id}.md",
        "errors_csv": output_dir / f"exhibitions_image_task_t199_trial_runtime_errors_{run_id}.csv",
        "warnings_csv": output_dir / f"exhibitions_image_task_t199_trial_runtime_warnings_{run_id}.csv",
    }


def validate_output_collision(output_paths: dict[str, Path], state: AdapterState) -> None:
    for key, path in output_paths.items():
        if path.exists():
            state.add_error(
                code="output_collision",
                check_id="output_collision",
                message=f"output path already exists: {key} -> {path}",
                category="consistency",
                file=str(path),
            )


def select_rows_and_units(
    *,
    inventory_rows: list[dict[str, str]],
    unit_rows: list[dict[str, str]],
    args: argparse.Namespace,
    scope_hash: str,
    classification_run_id: str,
    bundle_id: str,
    state: AdapterState,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    fair_filter = {norm_text(v) for v in args.fair_slug if norm_text(v)}
    gallery_filter = {norm_text(v) for v in args.gallery_name if norm_text(v)}
    unit_filter = {norm_text(v) for v in args.planned_unit_id if norm_text(v)}
    lane_filter_class = lane_filter_to_class(args.lane)
    target_year = int(args.target_year) if int(args.target_year or 0) > 0 else None

    unit_index: dict[str, dict[str, str]] = {}
    for unit in unit_rows:
        unit_id = norm_text(unit.get("planned_unit_id")) or norm_text(unit.get("unit_id"))
        if not unit_id:
            state.add_error(
                code="unit_id_empty",
                check_id="unit_primary_key",
                message="unit_plan row has empty unit id",
                category="schema",
            )
            continue
        if unit_id in unit_index:
            state.add_error(
                code="duplicate_unit_id",
                check_id="unit_primary_key",
                message=f"duplicate unit id: {unit_id}",
                category="consistency",
                row_key=unit_id,
            )
            continue
        unit_index[unit_id] = unit

    selected_rows: list[dict[str, Any]] = []
    excluded_due_to_filter = 0
    for row in inventory_rows:
        trial_ready = parse_bool(row.get("trial_ready"))
        adoption_allowed = parse_bool(row.get("adoption_allowed"))
        if trial_ready is not True:
            continue
        if adoption_allowed is not False:
            state.add_error(
                code="adoption_allowed_not_false",
                check_id="trial_row_gate",
                message="trial-ready row has adoption_allowed!=false",
                category="consistency",
                row_key="|".join(
                    [
                        norm_text(row.get("fair_slug")),
                        norm_text(row.get("gallery_name_en")),
                        norm_text(row.get("target_year")),
                    ]
                ),
            )
            continue

        lane = norm_text(row.get("recommended_lane"))
        if lane == LANE_KEEP:
            continue
        if lane == LANE_SAFE and parse_bool(row.get("provenance_gate_required")) is not True:
            state.add_error(
                code="safe_lane_without_provenance_gate",
                check_id="lane_gate",
                message="safe lane row requires provenance_gate_required=true",
                category="consistency",
            )
            continue
        if lane == LANE_GUARD and norm_text(row.get("required_guard_steps")):
            state.add_error(
                code="guard_lane_guard_not_resolved",
                check_id="lane_gate",
                message="guard lane row still has required_guard_steps",
                category="consistency",
            )
            continue

        unit_id = norm_text(row.get("recommended_unit_id"))
        if not unit_id:
            state.add_error(
                code="trial_row_missing_unit",
                check_id="row_unit_join",
                message="trial-ready row missing recommended_unit_id",
                category="consistency",
            )
            continue
        unit = unit_index.get(unit_id)
        if unit is None:
            state.add_error(
                code="trial_row_unit_not_found",
                check_id="row_unit_join",
                message=f"recommended_unit_id not found in unit_plan: {unit_id}",
                category="consistency",
                row_key=unit_id,
            )
            continue

        row_year = parse_int(row.get("target_year"))
        unit_year = parse_int(unit.get("target_year"))
        if row_year is None or unit_year is None or row_year != unit_year:
            state.add_error(
                code="row_unit_year_mismatch",
                check_id="row_unit_consistency",
                message=f"row/unit target_year mismatch: {unit_id}",
                category="consistency",
                row_key=unit_id,
            )
            continue
        if norm_text(row.get("fair_slug")) != norm_text(unit.get("fair_slug")):
            state.add_error(
                code="row_unit_fair_mismatch",
                check_id="row_unit_consistency",
                message=f"row/unit fair mismatch: {unit_id}",
                category="consistency",
                row_key=unit_id,
            )
            continue
        if lane != norm_text(unit.get("lane")):
            state.add_error(
                code="row_unit_lane_mismatch",
                check_id="row_unit_consistency",
                message=f"row/unit lane mismatch: {unit_id}",
                category="consistency",
                row_key=unit_id,
            )
            continue

        matched = True
        if target_year is not None and row_year != target_year:
            matched = False
        if fair_filter and norm_text(row.get("fair_slug")) not in fair_filter:
            matched = False
        if lane_filter_class and lane != lane_filter_class:
            matched = False
        if gallery_filter and norm_text(row.get("gallery_name_en")) not in gallery_filter:
            matched = False
        if unit_filter and unit_id not in unit_filter:
            matched = False
        if not matched:
            excluded_due_to_filter += 1
            continue

        selected_rows.append(
            {
                "classification_run_id": classification_run_id,
                "bundle_id": bundle_id,
                "scope_hash": scope_hash,
                "planned_unit_id": unit_id,
                "planned_trial_run_id": "",
                "trial_runtime_bundle_id": "",
                "target_year": str(row_year),
                "fair_slug": norm_text(row.get("fair_slug")),
                "lane": lane,
                "gallery_name_en": norm_text(row.get("gallery_name_en")),
                "source_url": norm_text(row.get("source_url")),
                "recommended_next_action": norm_text(row.get("recommended_next_action")),
                "current_input_grain": norm_text(row.get("current_input_grain")),
                "trial_ready_seed_count": norm_text(row.get("trial_ready_seed_count")),
                "blocking_reasons": norm_text(row.get("blocking_reasons")),
                "required_guard_steps": norm_text(row.get("required_guard_steps")),
                "provenance_gate_required": norm_text(row.get("provenance_gate_required")),
                "recommended_unit_scope": norm_text(row.get("recommended_unit_scope")),
                "adoption_allowed": norm_text(row.get("adoption_allowed")),
                "trial_ready": norm_text(row.get("trial_ready")),
            }
        )

    selected_unit_ids = sorted(
        {norm_text(r.get("planned_unit_id")) for r in selected_rows if norm_text(r.get("planned_unit_id"))}
    )
    selected_units: list[dict[str, Any]] = []
    for unit_id in selected_unit_ids:
        unit = unit_index[unit_id]
        row_count = len([r for r in selected_rows if norm_text(r.get("planned_unit_id")) == unit_id])
        if row_count <= 0:
            state.add_error(
                code="empty_selected_unit",
                check_id="selected_unit_non_empty",
                message=f"selected unit has zero rows: {unit_id}",
                category="consistency",
                row_key=unit_id,
            )
            continue
        lane = norm_text(unit.get("lane"))
        g_count = parse_int(unit.get("gallery_count")) or 0
        s_count = parse_int(unit.get("trial_ready_seed_count")) or 0
        selected_units.append(
            {
                "classification_run_id": classification_run_id,
                "bundle_id": bundle_id,
                "scope_hash": scope_hash,
                "planned_unit_id": unit_id,
                "planned_trial_run_id": "",
                "trial_runtime_bundle_id": "",
                "target_year": norm_text(unit.get("target_year")),
                "fair_slug": norm_text(unit.get("fair_slug")),
                "lane": lane,
                "gallery_count": str(g_count),
                "trial_ready_seed_count": str(s_count),
                "gallery_names": norm_text(unit.get("gallery_names")),
                "queue_order": norm_text(unit.get("queue_order")),
                "unit_scope": norm_text(unit.get("unit_scope")),
                "recommended_next_action": norm_text(unit.get("recommended_next_action")),
                "selected_row_count": str(row_count),
            }
        )

    selection_mode = "normal"
    if not selected_rows and excluded_due_to_filter > 0:
        selection_mode = "filtered_to_zero"
    elif not selected_rows:
        selection_mode = "trial_ready_zero"
    return selected_rows, selected_units, selection_mode


def build_planned_trial_run_id(
    *,
    target_year: str,
    fair_slug: str,
    lane: str,
    planned_unit_id: str,
) -> str:
    lane_token = "all"
    if lane == LANE_SAFE:
        lane_token = "safe"
    elif lane == LANE_GUARD:
        lane_token = "guard"
    elif lane == LANE_KEEP:
        lane_token = "keep"
    suffix = norm_text(planned_unit_id).replace("U-", "").replace(":", "-")
    return f"trial-{target_year}-{fair_slug}-{lane_token}-{suffix}"


def main() -> int:
    args = parse_args()
    run_id = norm_text(args.trial_runtime_bundle_id) or f"{utc_compact()}-trial-runtime"
    output_dir = Path(args.output_dir)
    output_paths = build_output_paths(output_dir, run_id)
    started_at = utc_now_iso()
    state = AdapterState()

    try:
        if os.environ.get("TASK199_FORCE_INTERNAL_FAILURE") == "1":
            raise RuntimeError("forced_internal_failure_for_task199")
        resolved = resolve_paths(args)

        handoff_summary_path = require_file(
            resolved["handoff_summary_json"], label="handoff_summary_json", state=state
        )
        handoff_manifest_path = require_file(
            resolved["handoff_manifest_json"], label="handoff_manifest_json", state=state
        )
        inventory_path = require_file(
            resolved["lane_ready_inventory_csv"], label="lane_ready_inventory_csv", state=state
        )
        unit_plan_path = require_file(
            resolved["unit_plan_csv"], label="unit_plan_csv", state=state
        )
        bundle_manifest_path = require_file(
            resolved["classification_bundle_manifest_json"],
            label="classification_bundle_manifest_json",
            state=state,
        )
        integration_summary_path = require_file(
            resolved["classification_integration_summary_json"],
            label="classification_integration_summary_json",
            state=state,
        )
        handoff_paths_path = require_file(
            resolved["handoff_paths_json"], label="handoff_paths_json", state=state
        )

        resolved_input_path: Path | None = None
        if norm_text(resolved["resolved_input_manifest_json"]):
            resolved_input_path = require_file(
                resolved["resolved_input_manifest_json"],
                label="resolved_input_manifest_json",
                state=state,
            )
        elif args.strict:
            state.add_error(
                code="strict_requires_resolved_input_manifest",
                check_id="conditional_required",
                message="resolved_input_manifest_json is required in strict mode",
                category="missing_artifact",
            )
        else:
            state.add_warning(
                code="resolved_input_manifest_missing",
                check_id="optional_input",
                message="resolved_input_manifest_json not provided; strict cross-check skipped",
            )

        decision_path: Path | None = None
        if norm_text(resolved["classification_decision_csv"]):
            decision_path = require_file(
                resolved["classification_decision_csv"],
                label="classification_decision_csv",
                state=state,
            )
        elif args.strict or any(norm_text(v) for v in args.planned_unit_id):
            state.add_error(
                code="classification_decision_required",
                check_id="conditional_required",
                message="classification_decision_csv required in strict mode or when --planned-unit-id is used",
                category="missing_artifact",
            )
        else:
            state.add_warning(
                code="classification_decision_missing",
                check_id="optional_input",
                message="classification_decision_csv not provided; continuing with inventory/unit_plan only",
            )

        validate_output_collision(output_paths, state)
        if state.errors:
            raise AdapterError(
                choose_reject_exit(state.errors),
                "required_or_preflight_failure",
                "preflight required checks failed",
            )

        assert handoff_summary_path and handoff_manifest_path and inventory_path and unit_plan_path
        assert bundle_manifest_path and integration_summary_path and handoff_paths_path
        handoff_summary = read_json(handoff_summary_path)
        _handoff_manifest = read_json(handoff_manifest_path)
        bundle_manifest = read_json(bundle_manifest_path)
        integration_summary = read_json(integration_summary_path)
        handoff_paths = read_json(handoff_paths_path)
        resolved_input_manifest = read_json(resolved_input_path) if resolved_input_path else {}

        inventory_fields, inventory_rows = read_csv(inventory_path)
        unit_fields, unit_rows = read_csv(unit_plan_path)
        decision_fields: list[str] = []
        if decision_path:
            decision_fields, _decision_rows = read_csv(decision_path)

        ensure_required_columns(
            inventory_fields,
            [
                "run_id",
                "target_year",
                "fair_slug",
                "gallery_name_en",
                "recommended_lane",
                "trial_ready",
                "adoption_allowed",
                "recommended_unit_id",
                "provenance_gate_required",
                "required_guard_steps",
            ],
            artifact=str(inventory_path),
            state=state,
        )
        ensure_required_columns(
            unit_fields,
            [
                "run_id",
                "unit_id",
                "lane",
                "fair_slug",
                "target_year",
                "gallery_count",
                "trial_ready_seed_count",
            ],
            artifact=str(unit_plan_path),
            state=state,
        )
        if decision_path:
            ensure_required_columns(
                decision_fields,
                [
                    "run_id",
                    "target_year",
                    "fair_slug",
                    "gallery_name_en",
                    "recommended_unit_id",
                    "recommended_lane",
                ],
                artifact=str(decision_path),
                state=state,
            )

        handoff_verdict = norm_text(handoff_summary.get("handoff_verdict"))
        handoff_allowed = parse_bool(handoff_summary.get("handoff_allowed"))
        classification_exit_code = parse_int(handoff_summary.get("exit_code"))
        selected_rows: list[dict[str, Any]] = []
        selected_units: list[dict[str, Any]] = []
        selection_mode = "normal"

        if handoff_verdict != "PASS":
            adapter_status = STATUS_HOLD
            exit_code = EXIT_HOLD
            selection_mode = "handoff_not_pass"
        else:
            if handoff_allowed is not True or classification_exit_code != 0:
                state.add_error(
                    code="handoff_summary_gate_failed",
                    check_id="handoff_summary_gate",
                    message="handoff summary indicates non-ready bundle",
                    category="consistency",
                )

            bundle_id_values = {
                norm_text(handoff_summary.get("bundle_id")),
                norm_text(bundle_manifest.get("bundle_id")),
                norm_text(integration_summary.get("bundle_id")),
                norm_text(handoff_paths.get("bundle_id")),
            }
            bundle_id_values = {v for v in bundle_id_values if v}
            if len(bundle_id_values) > 1:
                state.add_error(
                    code="bundle_id_mismatch",
                    check_id="cross_file_id_consistency",
                    message=f"bundle_id mismatch: {sorted(bundle_id_values)}",
                    category="consistency",
                )

            classification_run_values = {
                norm_text(handoff_summary.get("classification_run_id")),
                norm_text(bundle_manifest.get("classification_run_id")),
                norm_text(integration_summary.get("classification_run_id")),
                norm_text(handoff_paths.get("classification_run_id")),
            }
            classification_run_values.update(
                {norm_text(row.get("run_id")) for row in inventory_rows if norm_text(row.get("run_id"))}
            )
            classification_run_values.update(
                {norm_text(row.get("run_id")) for row in unit_rows if norm_text(row.get("run_id"))}
            )
            classification_run_values = {v for v in classification_run_values if v}
            if len(classification_run_values) > 1:
                state.add_error(
                    code="classification_run_id_mismatch",
                    check_id="cross_file_id_consistency",
                    message=f"classification_run_id mismatch: {sorted(classification_run_values)}",
                    category="consistency",
                )

            scope_hash_values = {
                norm_text(handoff_summary.get("scope_hash")),
                norm_text(bundle_manifest.get("scope_hash")),
                norm_text(integration_summary.get("scope_hash")),
                norm_text(handoff_paths.get("scope_hash")),
            }
            if isinstance(resolved_input_manifest, dict):
                scope_from_resolved = norm_text(((resolved_input_manifest.get("scope") or {}).get("scope_hash")))
                if scope_from_resolved:
                    scope_hash_values.add(scope_from_resolved)
            scope_hash_values = {v for v in scope_hash_values if v}
            if len(scope_hash_values) > 1:
                state.add_error(
                    code="scope_hash_mismatch",
                    check_id="cross_file_scope_consistency",
                    message=f"scope_hash mismatch: {sorted(scope_hash_values)}",
                    category="consistency",
                )

            integration_status = norm_text(integration_summary.get("integration_status"))
            if integration_status != "success":
                state.add_error(
                    code="integration_status_not_success",
                    check_id="integration_summary_gate",
                    message=f"integration_status must be success, got={integration_status}",
                    category="consistency",
                )

            required_paths = handoff_paths.get("required_paths") or {}
            for key, path_text in required_paths.items():
                p = Path(norm_text(path_text))
                if not p.exists():
                    state.add_error(
                        code="handoff_required_path_missing",
                        check_id="handoff_paths_existence",
                        message=f"handoff required path missing: {key} -> {p}",
                        category="missing_artifact",
                        file=str(handoff_paths_path),
                    )

            if state.errors:
                raise AdapterError(
                    choose_reject_exit(state.errors),
                    "cross_file_or_schema_failure",
                    "cross-file/schema validation failed",
                )

            classification_run_id = next(iter(classification_run_values)) if classification_run_values else ""
            bundle_id = next(iter(bundle_id_values)) if bundle_id_values else norm_text(handoff_summary.get("bundle_id"))
            scope_hash = next(iter(scope_hash_values)) if scope_hash_values else ""
            selected_rows, selected_units, selection_mode = select_rows_and_units(
                inventory_rows=inventory_rows,
                unit_rows=unit_rows,
                args=args,
                scope_hash=scope_hash,
                classification_run_id=classification_run_id,
                bundle_id=bundle_id,
                state=state,
            )

            unit_ids = [norm_text(u.get("planned_unit_id")) for u in selected_units]
            if len(unit_ids) != len(set(unit_ids)):
                state.add_error(
                    code="duplicate_selected_unit",
                    check_id="selected_unit_uniqueness",
                    message="duplicate planned_unit_id in selected units",
                    category="consistency",
                )

            for unit in selected_units:
                lane = norm_text(unit.get("lane"))
                g_count = parse_int(unit.get("gallery_count")) or 0
                s_count = parse_int(unit.get("trial_ready_seed_count")) or 0
                unit_id = norm_text(unit.get("planned_unit_id"))
                if lane == LANE_SAFE and (g_count > 10 or s_count > 150):
                    state.add_error(
                        code="safe_unit_policy_violation",
                        check_id="unit_policy",
                        message=f"safe unit policy exceeded: {unit_id}",
                        category="consistency",
                        row_key=unit_id,
                    )
                if lane == LANE_GUARD and (g_count > 4 or s_count > 60):
                    state.add_error(
                        code="guard_unit_policy_violation",
                        check_id="unit_policy",
                        message=f"guard unit policy exceeded: {unit_id}",
                        category="consistency",
                        row_key=unit_id,
                    )

            if args.fail_on_policy_violation and any(
                e["code"] in {"safe_unit_policy_violation", "guard_unit_policy_violation"}
                for e in state.errors
            ):
                raise AdapterError(
                    EXIT_REJECT_CONSISTENCY,
                    "planned_unit_policy_violation",
                    "planned unit policy violation detected",
                )
            if state.errors:
                raise AdapterError(
                    choose_reject_exit(state.errors),
                    "selection_or_policy_failure",
                    "selection/policy validation failed",
                )

            if not selected_rows:
                if selection_mode == "filtered_to_zero":
                    adapter_status = STATUS_SKIP
                    exit_code = EXIT_SKIP
                else:
                    adapter_status = STATUS_HOLD
                    exit_code = EXIT_HOLD
            else:
                adapter_status = STATUS_READY
                exit_code = EXIT_READY

        if selected_rows and selected_units:
            unit_trial_ids: dict[str, str] = {}
            for unit in selected_units:
                unit_id = norm_text(unit.get("planned_unit_id"))
                unit_trial_ids[unit_id] = build_planned_trial_run_id(
                    target_year=norm_text(unit.get("target_year")),
                    fair_slug=norm_text(unit.get("fair_slug")),
                    lane=norm_text(unit.get("lane")),
                    planned_unit_id=unit_id,
                )
                unit["planned_trial_run_id"] = unit_trial_ids[unit_id]
                unit["trial_runtime_bundle_id"] = run_id
            for row in selected_rows:
                unit_id = norm_text(row.get("planned_unit_id"))
                row["planned_trial_run_id"] = unit_trial_ids.get(unit_id, "")
                row["trial_runtime_bundle_id"] = run_id

        ready_row_count = len(selected_rows)
        ready_unit_count = len(selected_units)
        trial_runtime_ready = adapter_status == STATUS_READY
        manual_review_required = adapter_status in {STATUS_HOLD, STATUS_REJECT}
        retry_recommended = adapter_status == STATUS_REJECT

        scope_payload = {
            "target_year": sorted({norm_text(r.get("target_year")) for r in selected_rows if norm_text(r.get("target_year"))}),
            "fair_slug": sorted({norm_text(r.get("fair_slug")) for r in selected_rows if norm_text(r.get("fair_slug"))}),
            "lane": sorted({norm_text(r.get("lane")) for r in selected_rows if norm_text(r.get("lane"))}),
            "gallery_name_en": sorted({norm_text(r.get("gallery_name_en")) for r in selected_rows if norm_text(r.get("gallery_name_en"))}),
            "scope_hash": norm_text(
                handoff_summary.get("scope_hash")
                or bundle_manifest.get("scope_hash")
                or integration_summary.get("scope_hash")
                or handoff_paths.get("scope_hash")
            ),
            "filter_applied": {
                "target_year": args.target_year if int(args.target_year or 0) > 0 else None,
                "fair_slug": [norm_text(v) for v in args.fair_slug if norm_text(v)],
                "lane": args.lane,
                "gallery_name": [norm_text(v) for v in args.gallery_name if norm_text(v)],
                "planned_unit_id": [norm_text(v) for v in args.planned_unit_id if norm_text(v)],
            },
        }

        summary_payload = {
            "task_id": "TASK199",
            "run_id": run_id,
            "started_at": started_at,
            "completed_at": utc_now_iso(),
            "adapter_status": adapter_status,
            "trial_runtime_ready": trial_runtime_ready,
            "manual_review_required": manual_review_required,
            "retry_recommended": retry_recommended,
            "ready_unit_count": ready_unit_count,
            "ready_row_count": ready_row_count,
            "error_count": len(state.errors),
            "warning_count": len(state.warnings),
            "selection_mode": selection_mode,
            "ids": {
                "classification_run_id": norm_text(handoff_summary.get("classification_run_id")),
                "bundle_id": norm_text(handoff_summary.get("bundle_id")),
                "trial_runtime_bundle_id": run_id,
            },
            "resolved_inputs": resolved,
            "output_paths": {k: str(v) for k, v in output_paths.items()},
        }

        manifest_payload = {
            "task_id": "TASK199",
            "run_id": run_id,
            "created_at": utc_now_iso(),
            "adapter_status": adapter_status,
            "inputs": resolved,
            "outputs": {k: str(v) for k, v in output_paths.items()},
            "ids": summary_payload["ids"],
            "scope": scope_payload,
        }

        report_lines = [
            "# TASK199 Trial Runtime Adapter Report",
            "",
            f"- adapter_status: `{adapter_status}`",
            f"- trial_runtime_ready: `{str(trial_runtime_ready).lower()}`",
            f"- manual_review_required: `{str(manual_review_required).lower()}`",
            f"- retry_recommended: `{str(retry_recommended).lower()}`",
            f"- ready_unit_count: `{ready_unit_count}`",
            f"- ready_row_count: `{ready_row_count}`",
            f"- error_count: `{len(state.errors)}`",
            f"- warning_count: `{len(state.warnings)}`",
            f"- selection_mode: `{selection_mode}`",
            "",
            "## IDs",
            f"- classification_run_id: `{summary_payload['ids']['classification_run_id']}`",
            f"- bundle_id: `{summary_payload['ids']['bundle_id']}`",
            f"- trial_runtime_bundle_id: `{summary_payload['ids']['trial_runtime_bundle_id']}`",
            "",
            "## Scope",
            f"- scope_hash: `{scope_payload['scope_hash']}`",
            f"- target_year: `{','.join(scope_payload['target_year']) if scope_payload['target_year'] else ''}`",
            f"- fair_slug: `{','.join(scope_payload['fair_slug']) if scope_payload['fair_slug'] else ''}`",
            f"- lane: `{','.join(scope_payload['lane']) if scope_payload['lane'] else ''}`",
            f"- gallery_name_en: `{','.join(scope_payload['gallery_name_en']) if scope_payload['gallery_name_en'] else ''}`",
            "",
            "## Next Action",
        ]
        if adapter_status == STATUS_READY:
            report_lines.append("- handoff runtime bundle to actual trial runner (not executed in TASK199)")
        elif adapter_status == STATUS_HOLD:
            report_lines.append("- manual review required before runtime handoff")
        elif adapter_status == STATUS_SKIP:
            report_lines.append("- scope filter produced 0 candidate rows; adjust filter if needed")
        else:
            report_lines.append("- fix input consistency/schema and rerun adapter")

        write_json(output_paths["manifest_json"], manifest_payload)
        write_json(output_paths["unit_summary_json"], summary_payload)
        write_json(output_paths["scope_json"], scope_payload)
        write_md(output_paths["report_md"], report_lines)
        write_csv(
            output_paths["target_rows_csv"],
            selected_rows,
            default_fields=[
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
                "recommended_next_action",
                "current_input_grain",
                "trial_ready_seed_count",
                "blocking_reasons",
                "required_guard_steps",
                "provenance_gate_required",
                "recommended_unit_scope",
                "trial_ready",
                "adoption_allowed",
            ],
        )
        write_csv(
            output_paths["target_units_csv"],
            selected_units,
            default_fields=[
                "classification_run_id",
                "bundle_id",
                "trial_runtime_bundle_id",
                "planned_unit_id",
                "planned_trial_run_id",
                "scope_hash",
                "target_year",
                "fair_slug",
                "lane",
                "gallery_count",
                "trial_ready_seed_count",
                "gallery_names",
                "queue_order",
                "unit_scope",
                "recommended_next_action",
                "selected_row_count",
            ],
        )
        if args.write_errors_csv or state.errors:
            write_csv(
                output_paths["errors_csv"],
                state.errors,
                default_fields=["severity", "category", "code", "check_id", "message", "file", "row_key"],
            )
        if args.write_warnings_csv or state.warnings:
            write_csv(
                output_paths["warnings_csv"],
                state.warnings,
                default_fields=["severity", "category", "code", "check_id", "message", "file", "row_key"],
            )
        return int(exit_code)
    except AdapterError as err:
        fallback_summary = {
            "task_id": "TASK199",
            "run_id": run_id,
            "started_at": started_at,
            "completed_at": utc_now_iso(),
            "adapter_status": STATUS_REJECT,
            "trial_runtime_ready": False,
            "manual_review_required": True,
            "retry_recommended": True,
            "ready_unit_count": 0,
            "ready_row_count": 0,
            "error_count": len(state.errors),
            "warning_count": len(state.warnings),
            "reason_code": err.reason_code,
            "reason_message": err.message,
            "output_paths": {k: str(v) for k, v in output_paths.items()},
        }
        write_json(output_paths["unit_summary_json"], fallback_summary)
        write_json(
            output_paths["manifest_json"],
            {
                "task_id": "TASK199",
                "run_id": run_id,
                "created_at": utc_now_iso(),
                "adapter_status": STATUS_REJECT,
                "outputs": {k: str(v) for k, v in output_paths.items()},
                "reason_code": err.reason_code,
            },
        )
        write_json(output_paths["scope_json"], {"scope_hash": "", "target_year": [], "fair_slug": [], "lane": [], "gallery_name_en": []})
        write_md(
            output_paths["report_md"],
            [
                "# TASK199 Trial Runtime Adapter Report",
                "",
                "- adapter_status: `REJECT`",
                f"- reason_code: `{err.reason_code}`",
                f"- reason_message: `{err.message}`",
                f"- error_count: `{len(state.errors)}`",
                f"- warning_count: `{len(state.warnings)}`",
            ],
        )
        write_csv(
            output_paths["target_rows_csv"],
            [],
            default_fields=[
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
            ],
        )
        write_csv(
            output_paths["target_units_csv"],
            [],
            default_fields=[
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
        )
        write_csv(
            output_paths["errors_csv"],
            state.errors
            + [
                {
                    "severity": "error",
                    "category": "adapter",
                    "code": err.reason_code,
                    "check_id": "adapter_error",
                    "message": err.message,
                    "file": "",
                    "row_key": "",
                }
            ],
            default_fields=["severity", "category", "code", "check_id", "message", "file", "row_key"],
        )
        if state.warnings or args.write_warnings_csv:
            write_csv(
                output_paths["warnings_csv"],
                state.warnings,
                default_fields=["severity", "category", "code", "check_id", "message", "file", "row_key"],
            )
        return int(err.exit_code)
    except Exception as err:  # pragma: no cover
        write_json(
            output_paths["unit_summary_json"],
            {
                "task_id": "TASK199",
                "run_id": run_id,
                "started_at": started_at,
                "completed_at": utc_now_iso(),
                "adapter_status": STATUS_REJECT,
                "trial_runtime_ready": False,
                "manual_review_required": True,
                "retry_recommended": True,
                "ready_unit_count": 0,
                "ready_row_count": 0,
                "reason_code": "adapter_internal_exception",
                "reason_message": str(err),
            },
        )
        write_json(
            output_paths["manifest_json"],
            {
                "task_id": "TASK199",
                "run_id": run_id,
                "created_at": utc_now_iso(),
                "adapter_status": STATUS_REJECT,
                "reason_code": "adapter_internal_exception",
                "outputs": {k: str(v) for k, v in output_paths.items()},
            },
        )
        write_json(output_paths["scope_json"], {"scope_hash": "", "target_year": [], "fair_slug": [], "lane": [], "gallery_name_en": []})
        write_md(
            output_paths["report_md"],
            [
                "# TASK199 Trial Runtime Adapter Report",
                "",
                "- adapter_status: `REJECT`",
                f"- reason_code: `adapter_internal_exception`",
                f"- reason_message: `{err}`",
            ],
        )
        write_csv(
            output_paths["errors_csv"],
            [
                {
                    "severity": "error",
                    "category": "internal",
                    "code": "adapter_internal_exception",
                    "check_id": "internal_exception",
                    "message": str(err),
                    "file": "",
                    "row_key": "",
                }
            ],
            default_fields=["severity", "category", "code", "check_id", "message", "file", "row_key"],
        )
        return EXIT_INTERNAL


if __name__ == "__main__":
    raise SystemExit(main())
