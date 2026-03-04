
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

EXIT_PASS = 0
EXIT_REQUIRED_MISSING = 10
EXIT_SCHEMA_FAILURE = 11
EXIT_CONSISTENCY_FAILURE = 12
EXIT_EMPTY_HANDOFF_CANDIDATE = 13
EXIT_HOLD = 20
EXIT_INTERNAL_FAILURE = 30

CLASS_KEEP = "Keep-Current"
CLASS_SAFE = "Safe-But-Provenance-Gated"
CLASS_GUARD = "Guard-First-Then-Upgrade"


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
        description="Validate lane-ready handoff bundle (no trial/QA/adoption execution)."
    )
    parser.add_argument("--bundle-manifest-json", default="")
    parser.add_argument("--integration-summary-json", default="")
    parser.add_argument("--handoff-paths-json", default="")
    parser.add_argument("--lane-ready-inventory-csv", default="")
    parser.add_argument("--unit-plan-csv", default="")
    parser.add_argument("--resolved-input-manifest-json", default="")
    parser.add_argument("--output-dir", default="data/phase1_seed10/logs")
    parser.add_argument("--run-id", default="")
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


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["severity", "category", "code", "check_id", "message", "file", "row_key"] if not rows else list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def lane_filter_to_class(lane_filter: str) -> str | None:
    return {"keep": CLASS_KEEP, "safe": CLASS_SAFE, "guard": CLASS_GUARD}.get(norm_text(lane_filter))


class ValidationState:
    def __init__(self) -> None:
        self.errors: list[dict[str, Any]] = []
        self.warnings: list[dict[str, Any]] = []

    def add_error(self, *, category: str, code: str, check_id: str, message: str, file: str = "", row_key: str = "") -> None:
        self.errors.append({
            "severity": "error", "category": category, "code": code,
            "check_id": check_id, "message": message, "file": file, "row_key": row_key,
        })

    def add_warning(self, *, category: str, code: str, check_id: str, message: str, file: str = "", row_key: str = "") -> None:
        self.warnings.append({
            "severity": "warning", "category": category, "code": code,
            "check_id": check_id, "message": message, "file": file, "row_key": row_key,
        })

def resolve_input_paths(args: argparse.Namespace) -> dict[str, str]:
    resolved = {
        "bundle_manifest_json": norm_text(args.bundle_manifest_json),
        "integration_summary_json": norm_text(args.integration_summary_json),
        "handoff_paths_json": norm_text(args.handoff_paths_json),
        "lane_ready_inventory_csv": norm_text(args.lane_ready_inventory_csv),
        "unit_plan_csv": norm_text(args.unit_plan_csv),
        "resolved_input_manifest_json": norm_text(args.resolved_input_manifest_json),
    }
    if resolved["bundle_manifest_json"]:
        bundle = read_json(Path(resolved["bundle_manifest_json"]))
        if not resolved["integration_summary_json"]:
            resolved["integration_summary_json"] = norm_text(bundle.get("classification_integration_summary_json"))
        if not resolved["handoff_paths_json"]:
            resolved["handoff_paths_json"] = norm_text(bundle.get("handoff_paths_json"))
        if not resolved["resolved_input_manifest_json"]:
            resolved["resolved_input_manifest_json"] = norm_text(bundle.get("resolved_input_manifest_json"))
        outputs = bundle.get("classification_outputs", {})
        if not resolved["lane_ready_inventory_csv"]:
            resolved["lane_ready_inventory_csv"] = norm_text(outputs.get("lane_ready_inventory_csv"))
        if not resolved["unit_plan_csv"]:
            resolved["unit_plan_csv"] = norm_text(outputs.get("unit_plan_csv"))
    return resolved


def require_file(path_text: str, state: ValidationState, key: str) -> Path | None:
    if not norm_text(path_text):
        state.add_error(category="missing_artifact", code="required_path_missing", check_id="required_file_presence", message=f"required path missing: {key}", file=key)
        return None
    path = Path(path_text)
    if not path.exists():
        state.add_error(category="missing_artifact", code="required_file_not_found", check_id="required_file_presence", message=f"required file not found: {key} -> {path}", file=str(path))
        return None
    return path


def ensure_required_columns(fields: list[str], required: list[str], *, state: ValidationState, artifact: str) -> None:
    missing = [col for col in required if col not in fields]
    if missing:
        state.add_error(category="schema", code="missing_required_columns", check_id="required_columns", message=f"{artifact} missing columns: {','.join(missing)}", file=artifact)


def choose_exit_from_errors(errors: list[dict[str, Any]]) -> int:
    cats = {norm_text(err.get("category")) for err in errors}
    if "missing_artifact" in cats:
        return EXIT_REQUIRED_MISSING
    if "schema" in cats:
        return EXIT_SCHEMA_FAILURE
    return EXIT_CONSISTENCY_FAILURE


def bool_token_set(text: str) -> set[str]:
    return {norm_text(v) for v in text.split("|") if norm_text(v)}

def main() -> int:
    args = parse_args()
    run_id = norm_text(args.run_id) or f"{utc_compact()}-handoff-validate"
    output_dir = Path(args.output_dir)
    output_paths = {
        "summary_json": output_dir / f"exhibitions_image_task_t197_handoff_validation_summary_{run_id}.json",
        "report_md": output_dir / f"exhibitions_image_task_t197_handoff_validation_report_{run_id}.md",
        "manifest_json": output_dir / f"exhibitions_image_task_t197_handoff_validation_manifest_{run_id}.json",
        "errors_csv": output_dir / f"exhibitions_image_task_t197_handoff_validation_errors_{run_id}.csv",
        "warnings_csv": output_dir / f"exhibitions_image_task_t197_handoff_validation_warnings_{run_id}.csv",
    }
    state = ValidationState()
    started_at = utc_now_iso()

    try:
        resolved_paths = resolve_input_paths(args)

        bundle_manifest_path = require_file(resolved_paths["bundle_manifest_json"], state, "bundle_manifest_json")
        summary_path = require_file(resolved_paths["integration_summary_json"], state, "integration_summary_json")
        handoff_path = require_file(resolved_paths["handoff_paths_json"], state, "handoff_paths_json")
        inventory_path = require_file(resolved_paths["lane_ready_inventory_csv"], state, "lane_ready_inventory_csv")
        unit_plan_path = require_file(resolved_paths["unit_plan_csv"], state, "unit_plan_csv")

        resolved_input_path: Path | None = None
        if norm_text(resolved_paths["resolved_input_manifest_json"]):
            resolved_input_path = require_file(resolved_paths["resolved_input_manifest_json"], state, "resolved_input_manifest_json")
        else:
            state.add_warning(category="consistency", code="resolved_input_manifest_missing", check_id="optional_resolved_input", message="resolved_input_manifest_json not provided; scope_hash cross-check will use available artifacts only")

        if state.errors:
            exit_code = choose_exit_from_errors(state.errors)
            summary = {
                "task_id": "TASK197", "run_id": run_id, "started_at": started_at, "completed_at": utc_now_iso(),
                "handoff_verdict": "FAIL", "handoff_allowed": False, "manual_review_required": True, "retry_recommended": True,
                "exit_code": exit_code, "error_count": len(state.errors), "warning_count": len(state.warnings),
                "resolved_inputs": resolved_paths, "output_paths": {k: str(v) for k, v in output_paths.items()},
            }
            write_json(output_paths["summary_json"], summary)
            write_json(output_paths["manifest_json"], {"task_id": "TASK197", "run_id": run_id, "created_at": utc_now_iso(), "inputs": resolved_paths, "outputs": {k: str(v) for k, v in output_paths.items()}, "handoff_verdict": "FAIL", "exit_code": exit_code})
            write_md(output_paths["report_md"], ["# TASK197 Handoff Validation Report", "", "- handoff_verdict: `FAIL`", f"- exit_code: `{exit_code}`", f"- error_count: `{len(state.errors)}`", "", "## Failures", *[f"- [{e['category']}/{e['code']}] {e['message']}" for e in state.errors]])
            write_csv(output_paths["errors_csv"], state.errors)
            write_csv(output_paths["warnings_csv"], state.warnings)
            return exit_code

        assert bundle_manifest_path and summary_path and handoff_path and inventory_path and unit_plan_path
        bundle_manifest = read_json(bundle_manifest_path)
        integration_summary = read_json(summary_path)
        handoff_paths = read_json(handoff_path)
        resolved_input_manifest = read_json(resolved_input_path) if resolved_input_path else {}
        inventory_fields, inventory_rows = read_csv(inventory_path)
        unit_fields, unit_rows = read_csv(unit_plan_path)

        integration_status = norm_text(integration_summary.get("integration_status"))
        classification_exit_code = parse_int(integration_summary.get("classification_exit_code"))
        next_handoff_allowed = parse_bool(integration_summary.get("next_handoff_allowed"))

        if integration_status == "hold":
            state.add_warning(category="consistency", code="integration_hold_status", check_id="integration_summary_gate", message="integration_status is hold; handoff remains on hold", file=str(summary_path))
        elif integration_status != "success":
            state.add_error(category="consistency", code="integration_not_success", check_id="integration_summary_gate", message=f"integration_status must be success for handoff, got={integration_status}", file=str(summary_path))
        if integration_status == "success" and classification_exit_code != 0:
            state.add_error(category="consistency", code="classification_exit_not_zero", check_id="integration_summary_gate", message=f"classification_exit_code must be 0 for success handoff, got={classification_exit_code}", file=str(summary_path))
        if integration_status == "success" and next_handoff_allowed is not True:
            state.add_error(category="consistency", code="next_handoff_not_allowed", check_id="integration_summary_gate", message="next_handoff_allowed must be true for success handoff", file=str(summary_path))

        ensure_required_columns(inventory_fields, ["run_id", "target_year", "fair_slug", "gallery_name_en", "recommended_lane", "trial_ready", "blocking_reasons", "provenance_gate_required", "recommended_unit_id", "adoption_allowed", "trial_ready_seed_count"], state=state, artifact=str(inventory_path))

        inventory_keys: set[tuple[str, str, str]] = set()
        trial_ready_rows: list[dict[str, str]] = []
        for row in inventory_rows:
            row_key_t = (norm_text(row.get("fair_slug")), norm_text(row.get("gallery_name_en")), norm_text(row.get("target_year")))
            row_key = "|".join(row_key_t)
            if row_key_t in inventory_keys:
                state.add_error(category="consistency", code="inventory_primary_key_duplicate", check_id="inventory_pk_unique", message=f"duplicate inventory key: {row_key_t}", file=str(inventory_path), row_key=row_key)
            inventory_keys.add(row_key_t)

            lane = norm_text(row.get("recommended_lane"))
            if not lane:
                state.add_error(category="schema", code="recommended_lane_empty", check_id="inventory_lane_non_empty", message=f"recommended_lane empty: {row_key}", file=str(inventory_path), row_key=row_key)
            adoption_allowed = parse_bool(row.get("adoption_allowed"))
            if adoption_allowed is not False:
                state.add_error(category="consistency", code="adoption_allowed_must_be_false", check_id="inventory_adoption_allowed", message=f"adoption_allowed must be false: {row_key}", file=str(inventory_path), row_key=row_key)

            trial_ready = parse_bool(row.get("trial_ready"))
            seed_count = parse_int(row.get("trial_ready_seed_count"))
            blocking = bool_token_set(norm_text(row.get("blocking_reasons")))
            if trial_ready is True:
                trial_ready_rows.append(row)
                if seed_count is None or seed_count < 1:
                    state.add_error(category="consistency", code="trial_ready_without_seed_count", check_id="inventory_trial_ready_seed_count", message=f"trial_ready=true but seed_count<1: {row_key}", file=str(inventory_path), row_key=row_key)
                if "trial_ready_seed_zero" in blocking:
                    state.add_error(category="consistency", code="blocking_reason_conflict_trial_ready", check_id="inventory_blocking_vs_trial_ready", message=f"trial_ready=true but blocking includes trial_ready_seed_zero: {row_key}", file=str(inventory_path), row_key=row_key)

            provenance_gate_required = parse_bool(row.get("provenance_gate_required"))
            if lane == CLASS_SAFE and provenance_gate_required is not True:
                state.add_error(category="consistency", code="safe_lane_requires_provenance_gate", check_id="inventory_provenance_gate", message=f"safe lane requires provenance_gate_required=true: {row_key}", file=str(inventory_path), row_key=row_key)
            if lane in {CLASS_KEEP, CLASS_GUARD} and provenance_gate_required is True:
                state.add_warning(category="consistency", code="non_safe_with_provenance_gate_true", check_id="inventory_provenance_gate", message=f"non-safe lane with provenance_gate_required=true: {row_key}", file=str(inventory_path), row_key=row_key)

        ensure_required_columns(unit_fields, ["run_id", "lane", "fair_slug", "target_year", "gallery_count", "trial_ready_seed_count", "unit_scope"], state=state, artifact=str(unit_plan_path))
        if "unit_id" not in unit_fields and "planned_unit_id" not in unit_fields:
            state.add_error(category="schema", code="unit_identifier_missing", check_id="unit_plan_required_columns", message="unit_plan must contain unit_id or planned_unit_id", file=str(unit_plan_path))

        unit_id_to_row: dict[str, dict[str, str]] = {}
        for row in unit_rows:
            unit_id = norm_text(row.get("planned_unit_id")) or norm_text(row.get("unit_id"))
            if not unit_id:
                state.add_error(category="schema", code="unit_id_empty", check_id="unit_plan_id_not_empty", message="unit_id is empty", file=str(unit_plan_path))
                continue
            if unit_id in unit_id_to_row:
                state.add_error(category="consistency", code="unit_id_duplicate", check_id="unit_plan_unit_id_unique", message=f"duplicate unit_id: {unit_id}", file=str(unit_plan_path), row_key=unit_id)
            unit_id_to_row[unit_id] = row

            g_count = parse_int(row.get("gallery_count"))
            s_count = parse_int(row.get("trial_ready_seed_count"))
            lane = norm_text(row.get("lane"))
            fair_slug = norm_text(row.get("fair_slug"))
            t_year = parse_int(row.get("target_year"))
            if g_count is None or g_count <= 0:
                state.add_error(category="consistency", code="unit_gallery_count_invalid", check_id="unit_plan_non_empty_unit", message=f"gallery_count must be >0: {unit_id}", file=str(unit_plan_path), row_key=unit_id)
            if s_count is None or s_count < 0:
                state.add_error(category="schema", code="unit_seed_count_invalid", check_id="unit_plan_seed_count", message=f"trial_ready_seed_count invalid: {unit_id}", file=str(unit_plan_path), row_key=unit_id)
            if not lane or not fair_slug or t_year is None:
                state.add_error(category="schema", code="unit_scope_columns_invalid", check_id="unit_plan_scope_columns", message=f"lane/fair/target_year invalid: {unit_id}", file=str(unit_plan_path), row_key=unit_id)
            if lane == CLASS_SAFE:
                if g_count is not None and g_count > 10:
                    state.add_error(category="consistency", code="safe_unit_gallery_limit_exceeded", check_id="unit_policy_safe_gallery_limit", message=f"safe unit gallery_count exceeds 10: {unit_id}", file=str(unit_plan_path), row_key=unit_id)
                if s_count is not None and s_count > 150:
                    state.add_error(category="consistency", code="safe_unit_seed_limit_exceeded", check_id="unit_policy_safe_seed_limit", message=f"safe unit seed_count exceeds 150: {unit_id}", file=str(unit_plan_path), row_key=unit_id)
            if lane == CLASS_GUARD:
                if g_count is not None and g_count > 4:
                    state.add_error(category="consistency", code="guard_unit_gallery_limit_exceeded", check_id="unit_policy_guard_gallery_limit", message=f"guard unit gallery_count exceeds 4: {unit_id}", file=str(unit_plan_path), row_key=unit_id)
                if s_count is not None and s_count > 60:
                    state.add_error(category="consistency", code="guard_unit_seed_limit_exceeded", check_id="unit_policy_guard_seed_limit", message=f"guard unit seed_count exceeds 60: {unit_id}", file=str(unit_plan_path), row_key=unit_id)

        handoff_unit_ids: set[str] = set()
        for row in trial_ready_rows:
            row_key = "|".join([norm_text(row.get("fair_slug")), norm_text(row.get("gallery_name_en")), norm_text(row.get("target_year"))])
            unit_id = norm_text(row.get("recommended_unit_id"))
            if not unit_id:
                state.add_error(category="consistency", code="trial_ready_row_without_unit_id", check_id="inventory_unit_mapping", message=f"trial-ready row missing unit id: {row_key}", file=str(inventory_path), row_key=row_key)
                continue
            if unit_id not in unit_id_to_row:
                state.add_error(category="consistency", code="trial_ready_row_unit_id_not_found", check_id="inventory_unit_mapping", message=f"recommended_unit_id not found in unit plan: {unit_id}", file=str(unit_plan_path), row_key=row_key)
                continue
            handoff_unit_ids.add(unit_id)
            unit_row = unit_id_to_row[unit_id]
            if norm_text(unit_row.get("lane")) != norm_text(row.get("recommended_lane")):
                state.add_error(category="consistency", code="unit_lane_mismatch", check_id="inventory_unit_lane_consistency", message=f"lane mismatch for {row_key}", file=str(unit_plan_path), row_key=row_key)
            if norm_text(unit_row.get("fair_slug")) != norm_text(row.get("fair_slug")):
                state.add_error(category="consistency", code="unit_fair_mismatch", check_id="inventory_unit_fair_consistency", message=f"fair mismatch for {row_key}", file=str(unit_plan_path), row_key=row_key)
            if parse_int(unit_row.get("target_year")) != parse_int(row.get("target_year")):
                state.add_error(category="consistency", code="unit_target_year_mismatch", check_id="inventory_unit_year_consistency", message=f"target_year mismatch for {row_key}", file=str(unit_plan_path), row_key=row_key)

        bundle_id_bundle = norm_text(bundle_manifest.get("bundle_id"))
        bundle_id_summary = norm_text(integration_summary.get("bundle_id"))
        bundle_id_handoff = norm_text(handoff_paths.get("bundle_id"))
        if len({bundle_id_bundle, bundle_id_summary, bundle_id_handoff}) > 1:
            state.add_error(category="consistency", code="bundle_id_mismatch", check_id="cross_file_bundle_id", message=f"bundle_id mismatch: {bundle_id_bundle}/{bundle_id_summary}/{bundle_id_handoff}")

        run_id_bundle = norm_text(bundle_manifest.get("classification_run_id"))
        run_id_summary = norm_text(integration_summary.get("classification_run_id"))
        run_id_handoff = norm_text(handoff_paths.get("classification_run_id"))
        inv_run_ids = sorted({norm_text(r.get("run_id")) for r in inventory_rows if norm_text(r.get("run_id"))})
        unit_run_ids = sorted({norm_text(r.get("run_id")) for r in unit_rows if norm_text(r.get("run_id"))})
        run_values = [run_id_bundle, run_id_summary, run_id_handoff] + inv_run_ids + unit_run_ids
        if len({v for v in run_values if v}) > 1:
            state.add_error(category="consistency", code="classification_run_id_mismatch", check_id="cross_file_run_id", message=f"classification_run_id mismatch: {sorted(set(run_values))}")

        scope_hash_bundle = norm_text(bundle_manifest.get("scope_hash"))
        scope_hash_summary = norm_text(integration_summary.get("scope_hash"))
        scope_hash_handoff = norm_text(handoff_paths.get("scope_hash"))
        scope_hash_resolved = norm_text(((resolved_input_manifest.get("scope") or {}).get("scope_hash")) if isinstance(resolved_input_manifest, dict) else "")
        scope_values = [scope_hash_bundle, scope_hash_summary, scope_hash_handoff] + ([scope_hash_resolved] if scope_hash_resolved else [])
        if len({v for v in scope_values if v}) > 1:
            state.add_error(category="consistency", code="scope_hash_mismatch", check_id="cross_file_scope_hash", message=f"scope_hash mismatch: {sorted(set(scope_values))}")

        summary_year = parse_int(integration_summary.get("target_year"))
        if summary_year is not None:
            for row in inventory_rows:
                row_year = parse_int(row.get("target_year"))
                if row_year is not None and row_year != summary_year:
                    state.add_error(category="consistency", code="target_year_scope_conflict", check_id="cross_file_target_year_scope", message=f"inventory target_year mismatch: {row_year}!={summary_year}", file=str(inventory_path))
            for row in unit_rows:
                row_year = parse_int(row.get("target_year"))
                if row_year is not None and row_year != summary_year:
                    state.add_error(category="consistency", code="unit_target_year_scope_conflict", check_id="cross_file_target_year_scope", message=f"unit target_year mismatch: {row_year}!={summary_year}", file=str(unit_plan_path), row_key=norm_text(row.get("unit_id")))

        summary_fairs = {norm_text(v) for v in (integration_summary.get("fair_slug") or []) if norm_text(v)}
        if summary_fairs:
            for row in inventory_rows:
                if norm_text(row.get("fair_slug")) not in summary_fairs:
                    state.add_error(category="consistency", code="fair_scope_conflict", check_id="cross_file_fair_scope", message=f"fair outside summary scope: {norm_text(row.get('fair_slug'))}", file=str(inventory_path))

        summary_galleries = {norm_text(v) for v in (integration_summary.get("gallery_name") or []) if norm_text(v)}
        if summary_galleries:
            for row in inventory_rows:
                if norm_text(row.get("gallery_name_en")) not in summary_galleries:
                    state.add_error(category="consistency", code="gallery_scope_conflict", check_id="cross_file_gallery_scope", message=f"gallery outside summary scope: {norm_text(row.get('gallery_name_en'))}", file=str(inventory_path))

        lane_filter_class = lane_filter_to_class(norm_text(integration_summary.get("lane")))
        if lane_filter_class:
            for row in inventory_rows:
                if norm_text(row.get("recommended_lane")) != lane_filter_class:
                    state.add_error(category="consistency", code="lane_scope_conflict", check_id="cross_file_lane_scope", message=f"lane outside summary filter: {norm_text(row.get('recommended_lane'))}", file=str(inventory_path))

        required_paths = handoff_paths.get("required_paths") or {}
        for key, path_text in required_paths.items():
            p = Path(norm_text(path_text))
            if not p.exists():
                state.add_error(category="missing_artifact", code="handoff_required_path_missing", check_id="handoff_required_paths_exist", message=f"handoff required path missing: {key} -> {p}", file=str(handoff_path))

        if norm_text(required_paths.get("lane_ready_inventory_csv")) and norm_text(required_paths.get("lane_ready_inventory_csv")) != str(inventory_path):
            state.add_warning(category="consistency", code="handoff_inventory_path_differs_from_input", check_id="handoff_path_vs_input", message="handoff inventory path differs from validator input", file=str(handoff_path))
        if norm_text(required_paths.get("unit_plan_csv")) and norm_text(required_paths.get("unit_plan_csv")) != str(unit_plan_path):
            state.add_warning(category="consistency", code="handoff_unit_plan_path_differs_from_input", check_id="handoff_path_vs_input", message="handoff unit_plan path differs from validator input", file=str(handoff_path))

        handoff_row_count = len(trial_ready_rows)
        handoff_unit_count = len(handoff_unit_ids)

        if state.errors:
            verdict = "FAIL"
            handoff_allowed = False
            manual_review_required = True
            retry_recommended = True
            exit_code = choose_exit_from_errors(state.errors)
            next_action = "fix_bundle_and_revalidate"
        else:
            if integration_status == "hold" or classification_exit_code == 20:
                verdict = "HOLD"
                handoff_allowed = False
                manual_review_required = True
                retry_recommended = False
                exit_code = EXIT_HOLD
                next_action = "manual_review_hold"
            elif handoff_row_count == 0:
                verdict = "HOLD"
                handoff_allowed = False
                manual_review_required = True
                retry_recommended = False
                exit_code = EXIT_EMPTY_HANDOFF_CANDIDATE
                next_action = "no_trial_ready_rows_hold"
            elif integration_status == "success" and classification_exit_code == 0 and next_handoff_allowed is True:
                verdict = "PASS"
                handoff_allowed = True
                manual_review_required = False
                retry_recommended = False
                exit_code = EXIT_PASS
                next_action = "handoff_to_trial_runtime_adapter"
            else:
                verdict = "FAIL"
                handoff_allowed = False
                manual_review_required = True
                retry_recommended = True
                exit_code = EXIT_CONSISTENCY_FAILURE
                next_action = "bundle_state_inconsistent_fix_and_revalidate"

        summary = {
            "task_id": "TASK197",
            "run_id": run_id,
            "started_at": started_at,
            "completed_at": utc_now_iso(),
            "handoff_verdict": verdict,
            "handoff_allowed": handoff_allowed,
            "manual_review_required": manual_review_required,
            "retry_recommended": retry_recommended,
            "exit_code": exit_code,
            "error_count": len(state.errors),
            "warning_count": len(state.warnings),
            "handoff_target_row_count": handoff_row_count,
            "handoff_target_unit_count": handoff_unit_count,
            "bundle_id": bundle_id_summary or bundle_id_bundle or bundle_id_handoff,
            "classification_run_id": run_id_summary or run_id_bundle or run_id_handoff,
            "scope_hash": scope_hash_summary or scope_hash_bundle or scope_hash_handoff,
            "next_action": next_action,
            "resolved_inputs": resolved_paths,
            "output_paths": {k: str(v) for k, v in output_paths.items()},
        }
        write_json(output_paths["summary_json"], summary)
        write_json(output_paths["manifest_json"], {
            "task_id": "TASK197", "run_id": run_id, "created_at": utc_now_iso(),
            "inputs": resolved_paths, "outputs": {k: str(v) for k, v in output_paths.items()},
            "handoff_verdict": verdict, "exit_code": exit_code,
        })

        lines = [
            "# TASK197 Handoff Validation Report", "",
            f"- handoff_verdict: `{verdict}`",
            f"- exit_code: `{exit_code}`",
            f"- handoff_allowed: `{str(handoff_allowed).lower()}`",
            f"- manual_review_required: `{str(manual_review_required).lower()}`",
            f"- retry_recommended: `{str(retry_recommended).lower()}`",
            f"- handoff_target_unit_count: `{handoff_unit_count}`",
            f"- handoff_target_row_count: `{handoff_row_count}`",
            f"- error_count: `{len(state.errors)}`",
            f"- warning_count: `{len(state.warnings)}`",
            f"- next_action: `{next_action}`",
            "", "## Required Failures",
        ]
        if state.errors:
            lines += [f"- [{e['category']}/{e['code']}] {e['message']}" for e in state.errors]
        else:
            lines.append("- (none)")
        lines += ["", "## Warnings"]
        if state.warnings:
            lines += [f"- [{w['category']}/{w['code']}] {w['message']}" for w in state.warnings]
        else:
            lines.append("- (none)")
        write_md(output_paths["report_md"], lines)

        if args.write_errors_csv or state.errors:
            write_csv(output_paths["errors_csv"], state.errors)
        if args.write_warnings_csv or state.warnings:
            write_csv(output_paths["warnings_csv"], state.warnings)
        return exit_code

    except Exception as err:  # pragma: no cover
        write_json(output_paths["summary_json"], {
            "task_id": "TASK197", "run_id": run_id, "started_at": started_at, "completed_at": utc_now_iso(),
            "handoff_verdict": "FAIL", "handoff_allowed": False, "manual_review_required": True,
            "retry_recommended": True, "exit_code": EXIT_INTERNAL_FAILURE, "error_count": 1,
            "warning_count": 0, "next_action": "investigate_internal_failure", "internal_error": str(err),
        })
        write_json(output_paths["manifest_json"], {
            "task_id": "TASK197", "run_id": run_id, "created_at": utc_now_iso(),
            "outputs": {k: str(v) for k, v in output_paths.items()}, "handoff_verdict": "FAIL", "exit_code": EXIT_INTERNAL_FAILURE,
        })
        write_md(output_paths["report_md"], [
            "# TASK197 Handoff Validation Report", "", "- handoff_verdict: `FAIL`",
            f"- exit_code: `{EXIT_INTERNAL_FAILURE}`", f"- internal_error: `{err}`",
        ])
        write_csv(output_paths["errors_csv"], [{
            "severity": "error", "category": "internal", "code": "validator_internal_exception",
            "check_id": "internal_exception", "message": str(err), "file": "", "row_key": "",
        }])
        return EXIT_INTERNAL_FAILURE


if __name__ == "__main__":
    raise SystemExit(main())
