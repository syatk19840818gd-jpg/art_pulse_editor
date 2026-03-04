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
EXIT_REJECT_MISSING = 10
EXIT_REJECT_SCHEMA = 11
EXIT_REJECT_CONSISTENCY = 12
EXIT_HOLD = 20
EXIT_SKIP = 21
EXIT_INTERNAL = 30

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


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fp:
        reader = csv.DictReader(fp)
        if reader.fieldnames is None:
            raise ValueError(f"csv_has_no_header:{path}")
        fields = [norm_text(v) for v in reader.fieldnames]
        rows = [{norm_text(k): norm_text(v) for k, v in (row or {}).items()} for row in reader]
    return fields, rows


def write_csv(path: Path, rows: list[dict[str, Any]], default_fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = default_fields if not rows else list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def write_md(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


class State:
    def __init__(self) -> None:
        self.errors: list[dict[str, Any]] = []
        self.warnings: list[dict[str, Any]] = []

    def err(self, code: str, check: str, msg: str, cat: str, file: str = "", row: str = "") -> None:
        self.errors.append({"severity": "error", "category": cat, "code": code, "check_id": check, "message": msg, "file": file, "row_key": row})

    def warn(self, code: str, check: str, msg: str, cat: str, file: str = "", row: str = "") -> None:
        self.warnings.append({"severity": "warning", "category": cat, "code": code, "check_id": check, "message": msg, "file": file, "row_key": row})


def required(path_text: str, label: str, st: State) -> Path | None:
    text = norm_text(path_text)
    if not text:
        st.err("required_path_missing", "required_file", f"required path missing: {label}", "missing_artifact", label)
        return None
    p = Path(text)
    if not p.exists():
        st.err("required_file_not_found", "required_file", f"required file not found: {label} -> {p}", "missing_artifact", str(p))
        return None
    return p


def ensure_cols(fields: list[str], req: list[str], artifact: str, st: State) -> None:
    miss = [c for c in req if c not in fields]
    if miss:
        st.err("missing_required_columns", "required_columns", f"{artifact} missing columns: {','.join(miss)}", "schema", artifact)


def reject_exit(st: State) -> int:
    cats = {norm_text(e.get("category")) for e in st.errors}
    if "missing_artifact" in cats:
        return EXIT_REJECT_MISSING
    if "schema" in cats:
        return EXIT_REJECT_SCHEMA
    return EXIT_REJECT_CONSISTENCY


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="TASK205 post-trial QA runtime adapter")
    p.add_argument("--qa-handoff-validation-summary", default="")
    p.add_argument("--qa-handoff-validation-manifest", default="")
    p.add_argument("--trial-execution-summary", default="")
    p.add_argument("--trial-execution-manifest", default="")
    p.add_argument("--trial-bundle-result-csv", default="")
    p.add_argument("--trial-qa-handoff-manifest", default="")
    p.add_argument("--trial-unit-result-root", default="")
    p.add_argument("--trial-failure-queue-csv", default="")
    p.add_argument("--trial-defer-queue-csv", default="")
    p.add_argument("--trial-runtime-input-manifest-json", default="")
    p.add_argument("--handoff-validation-manifest-json", default="")
    p.add_argument("--classification-bundle-manifest-json", default="")
    p.add_argument("--output-dir", default="data/phase1_seed10/logs")
    p.add_argument("--qa-runtime-bundle-id", default="")
    p.add_argument("--planned-unit-id", action="append", default=[])
    p.add_argument("--fair-slug", action="append", default=[])
    p.add_argument("--lane", action="append", default=[])
    p.add_argument("--gallery-name", action="append", default=[])
    p.add_argument("--target-year", type=int, default=0)
    p.add_argument("--strict", action="store_true")
    p.add_argument("--strict-trace", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--fail-on-output-collision", action="store_true")
    p.add_argument("--fail-on-policy-violation", action="store_true")
    p.add_argument("--write-errors-csv", action="store_true")
    p.add_argument("--write-warnings-csv", action="store_true")
    return p.parse_args()


def resolve_paths(args: argparse.Namespace) -> dict[str, str]:
    r = {
        "qa_handoff_validation_summary_json": norm_text(args.qa_handoff_validation_summary),
        "qa_handoff_validation_manifest_json": norm_text(args.qa_handoff_validation_manifest),
        "trial_execution_summary_json": norm_text(args.trial_execution_summary),
        "trial_execution_manifest_json": norm_text(args.trial_execution_manifest),
        "trial_bundle_result_csv": norm_text(args.trial_bundle_result_csv),
        "trial_qa_handoff_manifest_json": norm_text(args.trial_qa_handoff_manifest),
        "trial_unit_result_root": norm_text(args.trial_unit_result_root),
        "trial_failure_queue_csv": norm_text(args.trial_failure_queue_csv),
        "trial_defer_queue_csv": norm_text(args.trial_defer_queue_csv),
        "trial_runtime_input_manifest_json": norm_text(args.trial_runtime_input_manifest_json),
        "handoff_validation_manifest_json": norm_text(args.handoff_validation_manifest_json),
        "classification_bundle_manifest_json": norm_text(args.classification_bundle_manifest_json),
    }
    m = r["qa_handoff_validation_manifest_json"]
    if m and Path(m).exists():
        payload = read_json(Path(m))
        inputs = payload.get("inputs") or {}
        minimum = payload.get("qa_minimum_handoff_set") or {}
        if not r["trial_execution_summary_json"]:
            r["trial_execution_summary_json"] = norm_text(minimum.get("trial_execution_summary_json") or inputs.get("trial_execution_summary_json"))
        if not r["trial_bundle_result_csv"]:
            r["trial_bundle_result_csv"] = norm_text(minimum.get("trial_bundle_result_csv") or inputs.get("trial_bundle_result_csv"))
        if not r["trial_qa_handoff_manifest_json"]:
            r["trial_qa_handoff_manifest_json"] = norm_text(minimum.get("trial_qa_handoff_manifest_json") or inputs.get("trial_qa_handoff_manifest_json"))
        if not r["trial_execution_manifest_json"]:
            r["trial_execution_manifest_json"] = norm_text(inputs.get("trial_execution_manifest_json"))
        if not r["trial_failure_queue_csv"]:
            r["trial_failure_queue_csv"] = norm_text(minimum.get("trial_failure_queue_csv"))
        if not r["trial_defer_queue_csv"]:
            r["trial_defer_queue_csv"] = norm_text(minimum.get("trial_defer_queue_csv"))
    t = r["trial_execution_manifest_json"]
    if t and Path(t).exists():
        payload = read_json(Path(t))
        outputs = payload.get("outputs") or {}
        inputs = payload.get("inputs") or {}
        if not r["trial_execution_summary_json"]:
            r["trial_execution_summary_json"] = norm_text(outputs.get("summary_json"))
        if not r["trial_bundle_result_csv"]:
            r["trial_bundle_result_csv"] = norm_text(outputs.get("bundle_result_csv"))
        if not r["trial_qa_handoff_manifest_json"]:
            r["trial_qa_handoff_manifest_json"] = norm_text(outputs.get("qa_handoff_manifest_json"))
        if not r["trial_failure_queue_csv"]:
            r["trial_failure_queue_csv"] = norm_text(outputs.get("failure_queue_csv"))
        if not r["trial_defer_queue_csv"]:
            r["trial_defer_queue_csv"] = norm_text(outputs.get("defer_queue_csv"))
        if not r["trial_runtime_input_manifest_json"]:
            r["trial_runtime_input_manifest_json"] = norm_text(inputs.get("trial_runtime_input_manifest_json"))
        if not r["handoff_validation_manifest_json"]:
            r["handoff_validation_manifest_json"] = norm_text(inputs.get("handoff_validation_manifest_json"))
        if not r["classification_bundle_manifest_json"]:
            r["classification_bundle_manifest_json"] = norm_text(inputs.get("classification_bundle_manifest_json"))
    return r

def out_paths(out_dir: Path, run_id: str) -> dict[str, Path]:
    return {
        "summary_json": out_dir / f"exhibitions_image_task_t205_qa_adapter_summary_{run_id}.json",
        "manifest_json": out_dir / f"exhibitions_image_task_t205_qa_adapter_manifest_{run_id}.json",
        "runtime_manifest_json": out_dir / f"exhibitions_image_task_t205_qa_runtime_input_manifest_{run_id}.json",
        "unit_summary_json": out_dir / f"exhibitions_image_task_t205_qa_runtime_unit_summary_{run_id}.json",
        "target_units_csv": out_dir / f"exhibitions_image_task_t205_qa_runtime_target_units_{run_id}.csv",
        "target_rows_csv": out_dir / f"exhibitions_image_task_t205_qa_runtime_target_rows_{run_id}.csv",
        "scope_json": out_dir / f"exhibitions_image_task_t205_qa_runtime_scope_{run_id}.json",
        "report_md": out_dir / f"exhibitions_image_task_t205_qa_runtime_report_{run_id}.md",
        "errors_csv": out_dir / f"exhibitions_image_task_t205_qa_runtime_errors_{run_id}.csv",
        "warnings_csv": out_dir / f"exhibitions_image_task_t205_qa_runtime_warnings_{run_id}.csv",
        "source_paths_json": out_dir / f"exhibitions_image_task_t205_qa_runtime_source_paths_{run_id}.json",
        "failure_context_csv": out_dir / f"exhibitions_image_task_t205_qa_runtime_failure_context_{run_id}.csv",
    }


def maybe_resolve(path_text: str, root: Path | None) -> Path:
    p = Path(norm_text(path_text))
    if p.exists():
        return p
    if root is not None and norm_text(path_text):
        c = root / Path(path_text).name
        if c.exists():
            return c
    return p


def matches_filters(row: dict[str, str], unit_id: str, args: argparse.Namespace) -> bool:
    unit_filter = {norm_text(v) for v in args.planned_unit_id if norm_text(v)}
    fair_filter = {norm_text(v) for v in args.fair_slug if norm_text(v)}
    lane_filter = {norm_text(v) for v in args.lane if norm_text(v)}
    gallery_filter = {norm_text(v) for v in args.gallery_name if norm_text(v)}
    target_year = int(args.target_year) if int(args.target_year or 0) > 0 else None
    if unit_filter and unit_id not in unit_filter:
        return False
    if fair_filter and norm_text(row.get("fair_slug")) not in fair_filter:
        return False
    if lane_filter and norm_text(row.get("lane")) not in lane_filter:
        return False
    if gallery_filter and norm_text(row.get("gallery_name_en")) not in gallery_filter:
        return False
    if target_year is not None and parse_int(row.get("target_year")) != target_year:
        return False
    return True


def main() -> int:
    args = parse_args()
    run_id = norm_text(args.qa_runtime_bundle_id) or f"{utc_compact()}-qa-runtime"
    started = utc_now_iso()
    st = State()
    outputs = out_paths(Path(args.output_dir), run_id)
    selected_rows: list[dict[str, Any]] = []
    selected_units: list[dict[str, Any]] = []
    failure_context: list[dict[str, Any]] = []
    source_paths = {"per_unit_sources": []}

    try:
        if norm_text(os.environ.get("TASK205_FORCE_INTERNAL_FAILURE")).lower() in {"1", "true", "yes"}:
            raise RuntimeError("forced_internal_failure_for_task205")

        resolved = resolve_paths(args)
        qa_summary_p = required(resolved["qa_handoff_validation_summary_json"], "qa_handoff_validation_summary_json", st)
        qa_manifest_p = required(resolved["qa_handoff_validation_manifest_json"], "qa_handoff_validation_manifest_json", st)
        trial_summary_p = required(resolved["trial_execution_summary_json"], "trial_execution_summary_json", st)
        trial_manifest_p = required(resolved["trial_execution_manifest_json"], "trial_execution_manifest_json", st)
        bundle_p = required(resolved["trial_bundle_result_csv"], "trial_bundle_result_csv", st)
        trial_qa_manifest_p = required(resolved["trial_qa_handoff_manifest_json"], "trial_qa_handoff_manifest_json", st)

        if args.strict_trace:
            required(resolved["trial_runtime_input_manifest_json"], "trial_runtime_input_manifest_json", st)
            required(resolved["handoff_validation_manifest_json"], "handoff_validation_manifest_json", st)
            required(resolved["classification_bundle_manifest_json"], "classification_bundle_manifest_json", st)

        for k, p in outputs.items():
            if p.exists():
                st.err("output_collision", "output_collision", f"output path exists: {k} -> {p}", "consistency", str(p))

        if st.errors:
            raise RuntimeError("initial_preflight_failed")

        assert qa_summary_p and qa_manifest_p and trial_summary_p and trial_manifest_p and bundle_p and trial_qa_manifest_p
        qa_summary = read_json(qa_summary_p)
        qa_manifest = read_json(qa_manifest_p)
        trial_summary = read_json(trial_summary_p)
        trial_qa_manifest = read_json(trial_qa_manifest_p)
        bfields, brows = read_csv(bundle_p)

        ensure_cols(
            bfields,
            [
                "planned_unit_id", "actual_trial_run_id", "unit_status", "executed_row_count", "succeeded_row_count", "failed_row_count", "deferred_row_count", "trial_unit_result_json_path", "trial_unit_rows_csv_path",
            ],
            str(bundle_p),
            st,
        )

        verdict = norm_text(qa_summary.get("qa_handoff_verdict"))
        handoff_allowed = parse_bool(qa_summary.get("qa_handoff_allowed"))
        if verdict not in {"PASS", "HOLD", "FAIL"}:
            st.err("invalid_verdict", "verdict_gate", f"invalid verdict: {verdict}", "schema")
        if verdict == "PASS" and handoff_allowed is not True:
            st.err("pass_without_handoff_allowed", "verdict_gate", "PASS requires qa_handoff_allowed=true", "consistency")
        if verdict == "FAIL":
            st.err("fail_verdict_not_accepted", "verdict_gate", "qa_handoff_verdict=FAIL not accepted", "consistency")

        qa_ids = qa_summary.get("ids") or {}
        tr_ids = trial_summary.get("ids") or {}
        ids: dict[str, str] = {}
        for key in ["classification_run_id", "bundle_id", "trial_runtime_bundle_id", "trial_runner_bundle_id"]:
            vals = {norm_text(qa_ids.get(key)), norm_text(tr_ids.get(key))}
            vals = {v for v in vals if v}
            if len(vals) != 1:
                st.err("id_mismatch", "cross_file_id", f"{key} mismatch: {sorted(vals)}", "consistency")
            ids[key] = next(iter(vals)) if vals else ""
            if not ids[key]:
                st.err("id_missing", "cross_file_id", f"{key} missing", "schema")

        scope_vals = {
            norm_text(qa_summary.get("scope_hash")),
            norm_text(trial_summary.get("scope_hash")),
            norm_text((qa_manifest.get("qa_minimum_handoff_set") or {}).get("scope_hash")),
        }
        scope_vals = {v for v in scope_vals if v}
        if len(scope_vals) != 1:
            st.err("scope_hash_mismatch", "cross_file_scope", f"scope_hash mismatch: {sorted(scope_vals)}", "consistency")
        scope_hash = next(iter(scope_vals)) if scope_vals else ""

        root = Path(norm_text(resolved["trial_unit_result_root"])) if norm_text(resolved["trial_unit_result_root"]) else None
        failed_units: set[str] = set()
        seen_units: set[str] = set()
        pre_filter_rows = 0

        for br in brows:
            unit_id = norm_text(br.get("planned_unit_id"))
            if not unit_id:
                st.err("empty_planned_unit_id", "bundle_rows", "planned_unit_id empty", "schema")
                continue
            if unit_id in seen_units:
                st.err("duplicate_planned_unit_id", "bundle_rows", f"duplicate unit: {unit_id}", "consistency", row=unit_id)
                continue
            seen_units.add(unit_id)

            status = norm_text(br.get("unit_status")).upper()
            actual_trial_run_id = norm_text(br.get("actual_trial_run_id"))
            ujson_p = maybe_resolve(norm_text(br.get("trial_unit_result_json_path")), root)
            urows_p = maybe_resolve(norm_text(br.get("trial_unit_rows_csv_path")), root)
            if not ujson_p.exists():
                st.err("unit_json_missing", "per_unit_presence", f"missing unit json: {ujson_p}", "missing_artifact", row=unit_id)
                continue
            if not urows_p.exists():
                st.err("unit_rows_missing", "per_unit_presence", f"missing unit rows: {urows_p}", "missing_artifact", row=unit_id)
                continue
            if args.strict and not ujson_p.with_suffix(".md").exists():
                st.err("unit_md_missing", "strict_presence", f"missing unit md: {ujson_p.with_suffix('.md')}", "missing_artifact", row=unit_id)

            ujson = read_json(ujson_p)
            uf, urows = read_csv(urows_p)
            ensure_cols(uf, ["classification_run_id", "bundle_id", "scope_hash", "planned_unit_id", "trial_runtime_bundle_id", "target_year", "fair_slug", "lane", "gallery_name_en"], str(urows_p), st)
            if norm_text(ujson.get("planned_unit_id")) != unit_id:
                st.err("unit_json_planned_id_mismatch", "per_unit_consistency", f"unit json planned_unit_id mismatch: {unit_id}", "consistency", row=unit_id)
            if norm_text(ujson.get("actual_trial_run_id")) != actual_trial_run_id:
                st.err("unit_json_actual_run_mismatch", "per_unit_consistency", f"unit json actual_trial_run_id mismatch: {unit_id}", "consistency", row=unit_id)
            if norm_text(ujson.get("scope_hash")) != scope_hash:
                st.err("unit_json_scope_hash_mismatch", "cross_file_scope", f"scope_hash mismatch in unit json: {unit_id}", "consistency", row=unit_id)
            for ur in urows:
                if norm_text(ur.get("planned_unit_id")) != unit_id:
                    st.err("unit_rows_planned_id_mismatch", "per_unit_consistency", f"row planned_unit_id mismatch: {unit_id}", "consistency", row=unit_id)
                if norm_text(ur.get("scope_hash")) != scope_hash:
                    st.err("unit_rows_scope_hash_mismatch", "cross_file_scope", f"row scope_hash mismatch: {unit_id}", "consistency", row=unit_id)
                if norm_text(ur.get("classification_run_id")) != ids["classification_run_id"]:
                    st.err("unit_rows_classification_run_id_mismatch", "cross_file_id", f"classification_run_id mismatch: {unit_id}", "consistency", row=unit_id)
                if norm_text(ur.get("bundle_id")) != ids["bundle_id"]:
                    st.err("unit_rows_bundle_id_mismatch", "cross_file_id", f"bundle_id mismatch: {unit_id}", "consistency", row=unit_id)
                if norm_text(ur.get("trial_runtime_bundle_id")) != ids["trial_runtime_bundle_id"]:
                    st.err("unit_rows_trial_runtime_bundle_id_mismatch", "cross_file_id", f"trial_runtime_bundle_id mismatch: {unit_id}", "consistency", row=unit_id)

            source_paths["per_unit_sources"].append({"planned_unit_id": unit_id, "unit_status": status, "unit_result_json_path": str(ujson_p), "unit_rows_csv_path": str(urows_p)})

            if status != "SUCCESS":
                failed_units.add(unit_id)
                failure_context.append({"planned_unit_id": unit_id, "actual_trial_run_id": actual_trial_run_id, "unit_status": status, "trial_unit_result_json_path": str(ujson_p), "trial_unit_rows_csv_path": str(urows_p)})
                continue

            pre_filter_rows += len(urows)
            picked: list[dict[str, Any]] = []
            for ur in urows:
                if not matches_filters(ur, unit_id, args):
                    continue
                picked.append(
                    {
                        "classification_run_id": ids["classification_run_id"],
                        "bundle_id": ids["bundle_id"],
                        "trial_runtime_bundle_id": ids["trial_runtime_bundle_id"],
                        "trial_runner_bundle_id": ids["trial_runner_bundle_id"],
                        "qa_runtime_bundle_id": run_id,
                        "planned_unit_id": unit_id,
                        "actual_trial_run_id": actual_trial_run_id,
                        "scope_hash": scope_hash,
                        "target_year": norm_text(ur.get("target_year")),
                        "fair_slug": norm_text(ur.get("fair_slug")),
                        "lane": norm_text(ur.get("lane")),
                        "gallery_name_en": norm_text(ur.get("gallery_name_en")),
                        "source_url": norm_text(ur.get("source_url")),
                        "selected_reason": norm_text(ur.get("selected_reason")),
                        "local_path": norm_text(ur.get("local_path")),
                    }
                )
            if picked:
                selected_rows.extend(picked)
                selected_units.append({"classification_run_id": ids["classification_run_id"], "bundle_id": ids["bundle_id"], "trial_runtime_bundle_id": ids["trial_runtime_bundle_id"], "trial_runner_bundle_id": ids["trial_runner_bundle_id"], "qa_runtime_bundle_id": run_id, "planned_unit_id": unit_id, "actual_trial_run_id": actual_trial_run_id, "scope_hash": scope_hash, "target_year": norm_text(ujson.get("target_year")), "fair_slug": norm_text(ujson.get("fair_slug")), "lane": norm_text(ujson.get("lane")), "selected_row_count": str(len(picked)), "unit_status": "SUCCESS"})

        if verdict == "PASS" and failed_units:
            st.err("failed_unit_mixed_in_pass_bundle", "policy_gate", f"PASS bundle includes non-success units: {','.join(sorted(failed_units))}", "consistency")

        for key in ["bundle_summary_path", "failure_queue_path", "defer_queue_path"]:
            p = norm_text(trial_qa_manifest.get(key))
            if p and not maybe_resolve(p, root).exists():
                st.err("trial_qa_manifest_missing_output_path", "qa_manifest_paths", f"missing {key}: {p}", "missing_artifact", str(trial_qa_manifest_p))
        for p in trial_qa_manifest.get("unit_result_paths") or []:
            if not maybe_resolve(norm_text(p), root).exists():
                st.err("trial_qa_manifest_missing_output_path", "qa_manifest_paths", f"missing unit_result_path: {p}", "missing_artifact", str(trial_qa_manifest_p))

        if st.errors:
            raise RuntimeError("validation_failed")

        filter_used = any(norm_text(v) for v in args.planned_unit_id + args.fair_slug + args.lane + args.gallery_name) or int(args.target_year or 0) > 0
        if verdict == "HOLD":
            qa_status = STATUS_HOLD
            exit_code = EXIT_HOLD
            mode = "hold_input_bundle"
        elif not selected_rows:
            if filter_used and pre_filter_rows > 0:
                qa_status = STATUS_SKIP
                exit_code = EXIT_SKIP
                mode = "filtered_to_zero"
            else:
                qa_status = STATUS_HOLD
                exit_code = EXIT_HOLD
                mode = "no_target_rows"
        else:
            qa_status = STATUS_READY
            exit_code = EXIT_READY
            mode = "ready"

        scope = {
            "scope_hash": scope_hash,
            "target_year": sorted({norm_text(r.get("target_year")) for r in selected_rows if norm_text(r.get("target_year"))}),
            "fair_slug": sorted({norm_text(r.get("fair_slug")) for r in selected_rows if norm_text(r.get("fair_slug"))}),
            "lane": sorted({norm_text(r.get("lane")) for r in selected_rows if norm_text(r.get("lane"))}),
            "gallery_name_en": sorted({norm_text(r.get("gallery_name_en")) for r in selected_rows if norm_text(r.get("gallery_name_en"))}),
            "filter_applied": {
                "planned_unit_id": [norm_text(v) for v in args.planned_unit_id if norm_text(v)],
                "fair_slug": [norm_text(v) for v in args.fair_slug if norm_text(v)],
                "lane": [norm_text(v) for v in args.lane if norm_text(v)],
                "gallery_name": [norm_text(v) for v in args.gallery_name if norm_text(v)],
                "target_year": int(args.target_year) if int(args.target_year or 0) > 0 else None,
            },
        }

        summary = {
            "task_id": "TASK205",
            "run_id": run_id,
            "started_at": started,
            "completed_at": utc_now_iso(),
            "qa_adapter_status": qa_status,
            "qa_runtime_ready": qa_status == STATUS_READY,
            "manual_review_required": qa_status in {STATUS_HOLD, STATUS_REJECT},
            "retry_recommended": qa_status == STATUS_REJECT,
            "ready_unit_count": len(selected_units),
            "ready_row_count": len(selected_rows),
            "error_count": len(st.errors),
            "warning_count": len(st.warnings),
            "selection_mode": mode,
            "input_verdict": verdict,
            "input_handoff_allowed": handoff_allowed,
            "trial_runner_status": norm_text(trial_summary.get("trial_runner_status")),
            "ids": {**ids, "qa_runtime_bundle_id": run_id},
            "scope_hash": scope_hash,
            "resolved_inputs": resolved,
            "output_paths": {k: str(v) for k, v in outputs.items()},
        }

        runtime_manifest = {
            "task_id": "TASK205",
            "run_id": run_id,
            "created_at": utc_now_iso(),
            "qa_adapter_status": qa_status,
            "qa_runtime_ready": qa_status == STATUS_READY,
            "ids": summary["ids"],
            "scope": scope,
            "inputs": resolved,
            "outputs": {k: str(v) for k, v in outputs.items()},
            "qa_runtime_handoff_set": {
                "trial_execution_summary_json": resolved["trial_execution_summary_json"],
                "trial_bundle_result_csv": resolved["trial_bundle_result_csv"],
                "trial_qa_handoff_manifest_json": resolved["trial_qa_handoff_manifest_json"],
                "qa_runtime_target_units_csv": str(outputs["target_units_csv"]),
                "qa_runtime_target_rows_csv": str(outputs["target_rows_csv"]),
                "qa_runtime_scope_json": str(outputs["scope_json"]),
                "qa_runtime_failure_context_csv": str(outputs["failure_context_csv"]),
            },
        }

        write_json(outputs["summary_json"], summary)
        write_json(outputs["manifest_json"], {"task_id": "TASK205", "run_id": run_id, "created_at": utc_now_iso(), "qa_adapter_status": qa_status, "ids": summary["ids"], "inputs": resolved, "outputs": {k: str(v) for k, v in outputs.items()}, "scope": scope})
        write_json(outputs["runtime_manifest_json"], runtime_manifest)
        write_json(outputs["unit_summary_json"], summary)
        write_json(outputs["scope_json"], scope)
        write_json(outputs["source_paths_json"], source_paths)
        write_csv(outputs["target_rows_csv"], selected_rows, ["planned_unit_id"])
        write_csv(outputs["target_units_csv"], selected_units, ["planned_unit_id"])
        write_csv(outputs["failure_context_csv"], failure_context, ["planned_unit_id"])
        if args.write_errors_csv or st.errors:
            write_csv(outputs["errors_csv"], st.errors, ["severity", "category", "code", "check_id", "message", "file", "row_key"])
        if args.write_warnings_csv or st.warnings:
            write_csv(outputs["warnings_csv"], st.warnings, ["severity", "category", "code", "check_id", "message", "file", "row_key"])
        write_md(outputs["report_md"], ["# TASK205 Post-Trial QA Adapter Report", "", f"- qa_adapter_status: `{qa_status}`", f"- qa_runtime_ready: `{str(qa_status == STATUS_READY).lower()}`", f"- ready_unit_count: `{len(selected_units)}`", f"- ready_row_count: `{len(selected_rows)}`", f"- error_count: `{len(st.errors)}`", f"- warning_count: `{len(st.warnings)}`", f"- next_action: `{'handoff to actual QA runner (not executed in TASK205)' if qa_status == STATUS_READY else 'manual review or input correction'}`"])
        return int(exit_code)
    except Exception as exc:
        code = EXIT_INTERNAL
        if st.errors:
            code = reject_exit(st)
        st.err("adapter_exception", "exception", str(exc), "internal")
        summary = {
            "task_id": "TASK205",
            "run_id": run_id,
            "started_at": started,
            "completed_at": utc_now_iso(),
            "qa_adapter_status": STATUS_REJECT,
            "qa_runtime_ready": False,
            "manual_review_required": True,
            "retry_recommended": True,
            "ready_unit_count": 0,
            "ready_row_count": 0,
            "error_count": len(st.errors),
            "warning_count": len(st.warnings),
            "reason_message": str(exc),
            "output_paths": {k: str(v) for k, v in outputs.items()},
        }
        write_json(outputs["summary_json"], summary)
        write_json(outputs["unit_summary_json"], summary)
        write_json(outputs["manifest_json"], {"task_id": "TASK205", "run_id": run_id, "qa_adapter_status": STATUS_REJECT, "outputs": {k: str(v) for k, v in outputs.items()}})
        write_json(outputs["runtime_manifest_json"], {"task_id": "TASK205", "run_id": run_id, "qa_adapter_status": STATUS_REJECT, "qa_runtime_ready": False, "outputs": {k: str(v) for k, v in outputs.items()}})
        write_json(outputs["scope_json"], {"scope_hash": "", "target_year": [], "fair_slug": [], "lane": [], "gallery_name_en": []})
        write_json(outputs["source_paths_json"], {"per_unit_sources": []})
        write_csv(outputs["target_rows_csv"], [], ["planned_unit_id"])
        write_csv(outputs["target_units_csv"], [], ["planned_unit_id"])
        write_csv(outputs["failure_context_csv"], [], ["planned_unit_id"])
        write_csv(outputs["errors_csv"], st.errors, ["severity", "category", "code", "check_id", "message", "file", "row_key"])
        write_csv(outputs["warnings_csv"], st.warnings, ["severity", "category", "code", "check_id", "message", "file", "row_key"])
        write_md(outputs["report_md"], ["# TASK205 Post-Trial QA Adapter Report", "", "- qa_adapter_status: `REJECT`", f"- reason_message: `{str(exc)}`"])
        return int(code)


if __name__ == "__main__":
    raise SystemExit(main())
