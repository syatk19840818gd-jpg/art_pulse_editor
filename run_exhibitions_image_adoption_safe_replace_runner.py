#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

EXIT_SUCCESS = 0
EXIT_REQUIRED_MISSING = 10
EXIT_SCHEMA = 11
EXIT_CONSISTENCY = 12
EXIT_IMPOSSIBLE_SET = 13
EXIT_HOLD = 20
EXIT_PARTIAL_SUCCESS = 21
EXIT_ROLLED_BACK = 22
EXIT_INTERNAL = 30

STATUS_SUCCESS = "SUCCESS"
STATUS_PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
STATUS_HOLD = "HOLD"
STATUS_FAIL_FAST = "FAIL_FAST"
STATUS_ROLLED_BACK = "ROLLED_BACK"
STATUS_INTERNAL = "INTERNAL_FAILURE"

VERDICT_PASS = "PASS"
VERDICT_HOLD = "HOLD"
VERDICT_FAIL = "FAIL"


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


def safe_token(value: str, fallback: str = "x") -> str:
    text = norm_text(value)
    if not text:
        return fallback
    out = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in text)
    out = "-".join(part for part in out.split("-") if part)
    return (out[:48] if out else fallback) or fallback


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    ensure_dir(path.parent)
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
    ensure_dir(path.parent)
    fields = default_fields if not rows else list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def write_md(path: Path, lines: list[str]) -> None:
    ensure_dir(path.parent)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fp:
        while True:
            chunk = fp.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


class State:
    def __init__(self) -> None:
        self.errors: list[dict[str, Any]] = []
        self.warnings: list[dict[str, Any]] = []

    def err(self, code: str, check: str, msg: str, cat: str, file: str = "", row: str = "") -> None:
        self.errors.append(
            {
                "severity": "error",
                "category": cat,
                "code": code,
                "check_id": check,
                "message": msg,
                "file": file,
                "row_key": row,
            }
        )

    def warn(self, code: str, check: str, msg: str, cat: str, file: str = "", row: str = "") -> None:
        self.warnings.append(
            {
                "severity": "warning",
                "category": cat,
                "code": code,
                "check_id": check,
                "message": msg,
                "file": file,
                "row_key": row,
            }
        )


def choose_fail_exit(errors: list[dict[str, Any]]) -> int:
    cats = {norm_text(e.get("category")) for e in errors}
    if "internal" in cats:
        return EXIT_INTERNAL
    if "missing_artifact" in cats:
        return EXIT_REQUIRED_MISSING
    if "schema" in cats:
        return EXIT_SCHEMA
    if "impossible_set" in cats:
        return EXIT_IMPOSSIBLE_SET
    return EXIT_CONSISTENCY


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


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="TASK211 adoption safe-replace runner")
    p.add_argument("--adoption-handoff-validation-summary", default="")
    p.add_argument("--adoption-handoff-validation-manifest", default="")
    p.add_argument("--qa-execution-summary", default="")
    p.add_argument("--qa-execution-manifest", default="")
    p.add_argument("--qa-bundle-result-csv", default="")
    p.add_argument("--qa-adoption-handoff-manifest", default="")
    p.add_argument("--qa-unit-result-root", default="")
    p.add_argument("--qa-failure-queue-csv", default="")
    p.add_argument("--qa-defer-queue-csv", default="")
    p.add_argument("--qa-runtime-input-manifest-json", default="")
    p.add_argument("--trial-execution-manifest-json", default="")
    p.add_argument("--qa-handoff-validation-manifest-json", default="")
    p.add_argument("--classification-bundle-manifest-json", default="")
    p.add_argument("--formal-root", default="")
    p.add_argument("--formal-manifest-json", default="")
    p.add_argument("--current-authoritative-target-list", default="")
    p.add_argument("--trash-root", default="_trash")
    p.add_argument("--output-dir", default="data/phase1_seed10/logs")
    p.add_argument("--planned-unit-id", action="append", default=[])
    p.add_argument("--fair-slug", action="append", default=[])
    p.add_argument("--lane", action="append", default=[])
    p.add_argument("--adoption-run-id", default="")
    p.add_argument("--strict", action="store_true")
    p.add_argument("--strict-trace", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--fail-on-output-collision", action="store_true")
    p.add_argument("--fail-on-policy-violation", action="store_true")
    p.add_argument("--rollback-on-failure", action=argparse.BooleanOptionalAction, default=True)
    return p.parse_args()


def resolve_paths(args: argparse.Namespace) -> dict[str, str]:
    r = {
        "adoption_summary_json": norm_text(args.adoption_handoff_validation_summary),
        "adoption_manifest_json": norm_text(args.adoption_handoff_validation_manifest),
        "qa_execution_summary_json": norm_text(args.qa_execution_summary),
        "qa_execution_manifest_json": norm_text(args.qa_execution_manifest),
        "qa_bundle_result_csv": norm_text(args.qa_bundle_result_csv),
        "qa_adoption_handoff_manifest_json": norm_text(args.qa_adoption_handoff_manifest),
        "qa_unit_result_root": norm_text(args.qa_unit_result_root),
        "qa_failure_queue_csv": norm_text(args.qa_failure_queue_csv),
        "qa_defer_queue_csv": norm_text(args.qa_defer_queue_csv),
        "qa_runtime_input_manifest_json": norm_text(args.qa_runtime_input_manifest_json),
        "trial_execution_manifest_json": norm_text(args.trial_execution_manifest_json),
        "qa_handoff_validation_manifest_json": norm_text(args.qa_handoff_validation_manifest_json),
        "classification_bundle_manifest_json": norm_text(args.classification_bundle_manifest_json),
        "formal_manifest_json": norm_text(args.formal_manifest_json),
        "current_target_list_csv": norm_text(args.current_authoritative_target_list),
    }
    m = r["adoption_manifest_json"]
    if m and Path(m).exists():
        payload = read_json(Path(m))
        inputs = payload.get("inputs") or {}
        minimum = payload.get("adoption_minimum_set") or {}
        if not r["qa_execution_summary_json"]:
            r["qa_execution_summary_json"] = norm_text(minimum.get("qa_execution_summary_json") or inputs.get("qa_execution_summary_json"))
        if not r["qa_bundle_result_csv"]:
            r["qa_bundle_result_csv"] = norm_text(minimum.get("qa_bundle_result_csv") or inputs.get("qa_bundle_result_csv"))
        if not r["qa_adoption_handoff_manifest_json"]:
            r["qa_adoption_handoff_manifest_json"] = norm_text(minimum.get("qa_adoption_handoff_manifest_json") or inputs.get("qa_adoption_handoff_manifest_json"))
    return r


def out_paths(out_dir: Path, run_id: str) -> dict[str, Path]:
    return {
        "execution_summary_json": out_dir / f"exhibitions_image_task_t211_adoption_execution_summary_{run_id}.json",
        "execution_report_md": out_dir / f"exhibitions_image_task_t211_adoption_execution_report_{run_id}.md",
        "execution_manifest_json": out_dir / f"exhibitions_image_task_t211_adoption_execution_manifest_{run_id}.json",
        "adoption_result_json": out_dir / f"exhibitions_image_task_t211_adoption_result_{run_id}.json",
        "adoption_result_md": out_dir / f"exhibitions_image_task_t211_adoption_result_{run_id}.md",
        "trash_manifest_csv": out_dir / f"exhibitions_image_task_t211_trash_manifest_{run_id}.csv",
        "rollback_result_json": out_dir / f"exhibitions_image_task_t211_rollback_result_{run_id}.json",
        "rollback_result_md": out_dir / f"exhibitions_image_task_t211_rollback_result_{run_id}.md",
        "errors_csv": out_dir / f"exhibitions_image_task_t211_adoption_errors_{run_id}.csv",
        "warnings_csv": out_dir / f"exhibitions_image_task_t211_adoption_warnings_{run_id}.csv",
    }


def resolve_existing(path_text: str, root: Path | None) -> Path:
    p = Path(norm_text(path_text))
    if p.exists():
        return p
    if root is not None and norm_text(path_text):
        c = root / Path(path_text).name
        if c.exists():
            return c
    return p


def resolve_dst(path_text: str, formal_root: Path) -> Path:
    p = Path(norm_text(path_text))
    if not p.is_absolute():
        p = formal_root / p
    return p.resolve()


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except Exception:
        return False


def semantic_key(row: dict[str, str]) -> tuple[str, ...]:
    return (
        norm_text(row.get("planned_unit_id")),
        norm_text(row.get("gallery_name_en")),
        norm_text(row.get("fair_slug")),
        norm_text(row.get("target_year")),
        norm_text(row.get("source_url")),
        norm_text(row.get("local_path")),
    )


def backup_one(
    src: Path, dst_root: Path, prefix: str, recs: list[dict[str, Any]], scope_hash: str, ids: dict[str, str]
) -> None:
    if not src.exists() or not src.is_file():
        return
    short_prefix = {
        "input_snapshot": "in",
        "formal_manifest": "fm",
        "target_list": "tl",
        "formal_file": "ff",
    }.get(prefix, "bk")
    source_hash = hashlib.sha1(str(src.resolve()).encode("utf-8")).hexdigest()[:12]
    dst = dst_root / f"{short_prefix}_{source_hash}{src.suffix}"
    ensure_dir(dst.parent)
    shutil.copy2(src, dst)
    recs.append(
        {
            "backup_type": prefix,
            "source_path": str(src),
            "backup_path": str(dst),
            "file_size": src.stat().st_size,
            "sha256": file_sha256(src),
            "copied_at": utc_now_iso(),
            "classification_run_id": ids.get("classification_run_id", ""),
            "bundle_id": ids.get("bundle_id", ""),
            "trial_runtime_bundle_id": ids.get("trial_runtime_bundle_id", ""),
            "trial_runner_bundle_id": ids.get("trial_runner_bundle_id", ""),
            "qa_runtime_bundle_id": ids.get("qa_runtime_bundle_id", ""),
            "qa_runner_bundle_id": ids.get("qa_runner_bundle_id", ""),
            "scope_hash": scope_hash,
        }
    )


def write_common_outputs(
    *,
    out: dict[str, Path],
    run_id: str,
    status: str,
    exit_code: int,
    started: str,
    st: State,
    ids: dict[str, str],
    scope_hash: str,
    selected_rows: list[dict[str, str]],
    selected_units: list[str],
    replaced_count: int,
    deleted_count: int,
    noop_count: int,
    rollback_executed: bool,
    adoption_allowed: bool,
    manual_review_required: bool,
    retry_recommended: bool,
    resolved_inputs: dict[str, str],
    trash_dir: Path,
    backup_rows: list[dict[str, Any]],
) -> None:
    summary = {
        "task_id": "TASK211",
        "run_id": run_id,
        "started_at": started,
        "completed_at": utc_now_iso(),
        "adoption_status": status,
        "adoption_allowed": adoption_allowed,
        "manual_review_required": manual_review_required,
        "retry_recommended": retry_recommended,
        "replaced_file_count": replaced_count,
        "deleted_file_count": deleted_count,
        "noop_file_count": noop_count,
        "rollback_executed": rollback_executed,
        "error_count": len(st.errors),
        "warning_count": len(st.warnings),
        "selected_unit_count": len(sorted(set(selected_units))),
        "selected_row_count": len(selected_rows),
        "ids": ids,
        "scope_hash": scope_hash,
        "selected_fair_slug_set": sorted({norm_text(r.get("fair_slug")) for r in selected_rows if norm_text(r.get("fair_slug"))}),
        "selected_lane_set": sorted({norm_text(r.get("lane")) for r in selected_rows if norm_text(r.get("lane"))}),
        "trash_dir": str(trash_dir),
        "resolved_inputs": resolved_inputs,
        "output_paths": {k: str(v) for k, v in out.items()},
        "exit_code": exit_code,
    }
    write_json(out["execution_summary_json"], summary)
    write_json(
        out["execution_manifest_json"],
        {
            "task_id": "TASK211",
            "run_id": run_id,
            "created_at": utc_now_iso(),
            "adoption_status": status,
            "exit_code": exit_code,
            "inputs": resolved_inputs,
            "outputs": {k: str(v) for k, v in out.items()},
            "trash_dir": str(trash_dir),
        },
    )
    write_json(
        out["adoption_result_json"],
        {
            "task_id": "TASK211",
            "run_id": run_id,
            "adoption_status": status,
            "adoption_allowed": adoption_allowed,
            "scope_hash": scope_hash,
            "ids": ids,
            "selected_unit_ids": sorted(set(selected_units)),
            "selected_row_count": len(selected_rows),
            "replaced_file_count": replaced_count,
            "deleted_file_count": deleted_count,
            "noop_file_count": noop_count,
            "rollback_executed": rollback_executed,
        },
    )
    write_md(
        out["execution_report_md"],
        [
            "# TASK211 Adoption Safe-Replace Execution Report",
            "",
            f"- adoption_status: `{status}`",
            f"- exit_code: `{exit_code}`",
            f"- selected_unit_count: `{len(sorted(set(selected_units)))}`",
            f"- selected_row_count: `{len(selected_rows)}`",
            f"- replaced_file_count: `{replaced_count}`",
            f"- deleted_file_count: `{deleted_count}`",
            f"- noop_file_count: `{noop_count}`",
            f"- rollback_executed: `{'true' if rollback_executed else 'false'}`",
            f"- error_count: `{len(st.errors)}`",
            f"- warning_count: `{len(st.warnings)}`",
        ],
    )
    write_md(
        out["adoption_result_md"],
        [
            "# TASK211 Adoption Result",
            "",
            f"- adoption_status: `{status}`",
            f"- adoption_allowed: `{'true' if adoption_allowed else 'false'}`",
            f"- selected_units: `{len(sorted(set(selected_units)))}`",
            f"- selected_rows: `{len(selected_rows)}`",
            f"- replaced_file_count: `{replaced_count}`",
            f"- deleted_file_count: `{deleted_count}`",
            f"- noop_file_count: `{noop_count}`",
            f"- rollback_executed: `{'true' if rollback_executed else 'false'}`",
        ],
    )
    write_csv(out["errors_csv"], st.errors, ["severity", "category", "code", "check_id", "message", "file", "row_key"])
    write_csv(out["warnings_csv"], st.warnings, ["severity", "category", "code", "check_id", "message", "file", "row_key"])
    write_csv(
        out["trash_manifest_csv"],
        backup_rows,
        [
            "backup_type",
            "source_path",
            "backup_path",
            "file_size",
            "sha256",
            "copied_at",
            "classification_run_id",
            "bundle_id",
            "trial_runtime_bundle_id",
            "trial_runner_bundle_id",
            "qa_runtime_bundle_id",
            "qa_runner_bundle_id",
            "scope_hash",
        ],
    )

def main() -> int:
    args = parse_args()
    run_id = norm_text(args.adoption_run_id) or f"{utc_compact()}-adopt"
    started = utc_now_iso()
    st = State()
    resolved = resolve_paths(args)
    out = out_paths(Path(args.output_dir), run_id)
    for key, p in out.items():
        if p.exists():
            if args.fail_on_output_collision:
                st.err("output_collision", "output_collision", f"output already exists: {key} -> {p}", "consistency", str(p))
            else:
                st.warn("output_collision", "output_collision", f"output exists and will be overwritten: {key} -> {p}", "consistency", str(p))

    status = STATUS_FAIL_FAST
    exit_code = EXIT_CONSISTENCY
    replaced_count = 0
    deleted_count = 0
    noop_count = 0
    rollback_executed = False
    selected_rows: list[dict[str, str]] = []
    selected_units: list[str] = []
    backup_rows: list[dict[str, Any]] = []
    scope_before_paths: list[Path] = []
    adopted_dst_paths: list[Path] = []
    ids: dict[str, str] = {}
    scope_hash = ""
    adoption_allowed = False
    manual_review_required = True
    retry_recommended = True
    formal_root = Path(norm_text(args.formal_root)).resolve() if norm_text(args.formal_root) else Path(".").resolve()
    trash_dir = Path(norm_text(args.trash_root)).resolve() / f"{utc_compact()}_pre_adopt_{safe_token('-'.join(args.lane) if args.lane else 'lane')}_{safe_token(run_id)}"

    try:
        if norm_text(os.environ.get("TASK211_FORCE_INTERNAL_FAILURE")).lower() in {"1", "true", "yes"}:
            raise RuntimeError("forced_internal_failure_for_task211")

        adoption_summary_p = required(resolved["adoption_summary_json"], "adoption_handoff_validation_summary.json", st)
        adoption_manifest_p = required(resolved["adoption_manifest_json"], "adoption_handoff_validation_manifest.json", st)
        qa_summary_p = required(resolved["qa_execution_summary_json"], "qa_execution_summary.json", st)
        qa_manifest_p = required(resolved["qa_execution_manifest_json"], "qa_execution_manifest.json", st)
        qa_bundle_p = required(resolved["qa_bundle_result_csv"], "qa_bundle_result.csv", st)
        qa_adopt_manifest_p = required(resolved["qa_adoption_handoff_manifest_json"], "qa_adoption_handoff_manifest.json", st)
        formal_manifest_p = required(resolved["formal_manifest_json"], "formal_manifest_json", st)
        current_targets_p = required(resolved["current_target_list_csv"], "current_authoritative_target_list.csv", st)
        if args.strict_trace:
            required(resolved["qa_runtime_input_manifest_json"], "qa_runtime_input_manifest.json", st)
            required(resolved["trial_execution_manifest_json"], "trial_execution_manifest.json", st)
            required(resolved["qa_handoff_validation_manifest_json"], "qa_handoff_validation_manifest.json", st)
            required(resolved["classification_bundle_manifest_json"], "classification_bundle_manifest.json", st)
        if st.errors:
            raise RuntimeError("required_failed")
        assert adoption_summary_p and adoption_manifest_p and qa_summary_p and qa_manifest_p and qa_bundle_p and qa_adopt_manifest_p and formal_manifest_p and current_targets_p

        adoption_summary = read_json(adoption_summary_p)
        qa_summary = read_json(qa_summary_p)
        formal_manifest = read_json(formal_manifest_p)
        verdict = norm_text(adoption_summary.get("adoption_handoff_verdict"))
        allowed = parse_bool(adoption_summary.get("adoption_handoff_allowed"))
        scope_hash = norm_text(adoption_summary.get("scope_hash"))
        ids = {
            k: norm_text((adoption_summary.get("ids") or {}).get(k))
            for k in [
                "classification_run_id",
                "bundle_id",
                "trial_runtime_bundle_id",
                "trial_runner_bundle_id",
                "qa_runtime_bundle_id",
                "qa_runner_bundle_id",
            ]
        }
        if verdict not in {VERDICT_PASS, VERDICT_HOLD, VERDICT_FAIL}:
            st.err("invalid_verdict", "verdict_gate", f"invalid verdict: {verdict}", "schema", str(adoption_summary_p))
        if verdict == VERDICT_FAIL:
            st.err("verdict_fail", "verdict_gate", "verdict FAIL is not acceptable for adoption runner", "consistency", str(adoption_summary_p))
        if verdict == VERDICT_PASS and allowed is not True:
            st.err("pass_without_allowed", "verdict_gate", "PASS requires adoption_handoff_allowed=true", "consistency", str(adoption_summary_p))
        if not scope_hash:
            st.err("scope_hash_missing", "scope_gate", "scope_hash missing", "schema", str(adoption_summary_p))
        for key, val in ids.items():
            if not val:
                st.err("trace_id_missing", "trace_gate", f"missing trace id: {key}", "schema", str(adoption_summary_p))
        qa_scope = norm_text(qa_summary.get("scope_hash"))
        if qa_scope and scope_hash and qa_scope != scope_hash:
            st.err("qa_scope_mismatch", "cross_scope", f"qa scope_hash mismatch: {qa_scope} vs {scope_hash}", "consistency", str(qa_summary_p))

        bundle_fields, bundle_rows = read_csv(qa_bundle_p)
        ensure_cols(
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
                "qa_unit_result_json_path",
                "qa_unit_rows_csv_path",
            ],
            str(qa_bundle_p),
            st,
        )
        current_fields, current_rows = read_csv(current_targets_p)
        ensure_cols(
            current_fields,
            ["planned_unit_id", "gallery_name_en", "fair_slug", "target_year", "source_url", "lane", "local_path", "scope_hash"],
            str(current_targets_p),
            st,
        )
        if st.errors:
            raise RuntimeError("schema_failed")

        f_units = {norm_text(v) for v in args.planned_unit_id if norm_text(v)}
        f_fair = {norm_text(v) for v in args.fair_slug if norm_text(v)}
        f_lane = {norm_text(v) for v in args.lane if norm_text(v)}
        unit_root = Path(resolved["qa_unit_result_root"]) if norm_text(resolved["qa_unit_result_root"]) else None

        for br in bundle_rows:
            unit_id = norm_text(br.get("planned_unit_id"))
            if not unit_id or norm_text(br.get("unit_status")) != "SUCCESS":
                continue
            if f_units and unit_id not in f_units:
                continue
            ujson_p = resolve_existing(br.get("qa_unit_result_json_path") or "", unit_root)
            urows_p = resolve_existing(br.get("qa_unit_rows_csv_path") or "", unit_root)
            if not ujson_p.exists():
                st.err("unit_json_missing", "per_unit_presence", f"unit result missing: {ujson_p}", "missing_artifact", str(ujson_p), unit_id)
                continue
            if not urows_p.exists():
                st.err("unit_rows_missing", "per_unit_presence", f"unit rows missing: {urows_p}", "missing_artifact", str(urows_p), unit_id)
                continue
            ujson = read_json(ujson_p)
            if norm_text(ujson.get("scope_hash")) and norm_text(ujson.get("scope_hash")) != scope_hash:
                st.err("unit_scope_mismatch", "per_unit_scope", f"unit scope mismatch: {ujson.get('scope_hash')} vs {scope_hash}", "consistency", str(ujson_p), unit_id)
                continue
            uf, urows = read_csv(urows_p)
            ensure_cols(uf, ["planned_unit_id", "gallery_name_en", "fair_slug", "target_year", "lane", "source_url", "local_path"], str(urows_p), st)
            for ur in urows:
                if f_fair and norm_text(ur.get("fair_slug")) not in f_fair:
                    continue
                if f_lane and norm_text(ur.get("lane")) not in f_lane:
                    continue
                if norm_text(ur.get("planned_unit_id")) != unit_id:
                    st.err("unit_row_unit_mismatch", "per_unit_rows", f"planned_unit_id mismatch in {urows_p}", "consistency", str(urows_p), unit_id)
                    continue
                row = dict(ur)
                row["scope_hash"] = scope_hash
                row["classification_run_id"] = ids["classification_run_id"]
                row["bundle_id"] = ids["bundle_id"]
                row["trial_runtime_bundle_id"] = ids["trial_runtime_bundle_id"]
                row["trial_runner_bundle_id"] = ids["trial_runner_bundle_id"]
                row["qa_runtime_bundle_id"] = ids["qa_runtime_bundle_id"]
                row["qa_runner_bundle_id"] = ids["qa_runner_bundle_id"]
                row["actual_qa_run_id"] = norm_text(ujson.get("actual_qa_run_id"))
                selected_rows.append(row)
            selected_units.append(unit_id)

        if st.errors:
            raise RuntimeError("unit_load_failed")

        if verdict == VERDICT_HOLD:
            status = STATUS_HOLD
            exit_code = EXIT_HOLD
            adoption_allowed = False
            manual_review_required = True
            retry_recommended = False
        else:
            if not selected_rows:
                st.err("empty_candidate_set", "candidate_set", "no candidate rows selected", "impossible_set")
                raise RuntimeError("empty_set")
            if {norm_text(r.get("scope_hash")) for r in selected_rows} != {scope_hash}:
                st.err("mixed_scope_rows", "candidate_scope", "selected rows have mixed scope_hash", "consistency")
                raise RuntimeError("scope_mixed")

            scope_rows_before = [r for r in current_rows if norm_text(r.get("scope_hash")) == scope_hash]
            non_scope_before = [r for r in current_rows if norm_text(r.get("scope_hash")) != scope_hash]

            ensure_dir(trash_dir)
            for p, prefix in [
                (adoption_summary_p, "input_snapshot"),
                (adoption_manifest_p, "input_snapshot"),
                (qa_summary_p, "input_snapshot"),
                (qa_manifest_p, "input_snapshot"),
                (qa_bundle_p, "input_snapshot"),
                (qa_adopt_manifest_p, "input_snapshot"),
                (formal_manifest_p, "formal_manifest"),
                (current_targets_p, "target_list"),
            ]:
                backup_one(p, trash_dir, prefix, backup_rows, scope_hash, ids)

            for r in scope_rows_before:
                p = resolve_dst(r.get("local_path") or "", formal_root)
                if not is_within(p, formal_root):
                    st.err("scope_path_outside_root", "scope_guard", f"scope path outside formal root: {p}", "consistency", str(p))
                    continue
                scope_before_paths.append(p)
                if p.exists() and p.is_file():
                    backup_one(p, trash_dir, "formal_file", backup_rows, scope_hash, ids)
            if st.errors:
                raise RuntimeError("scope_guard_failed")

            adopted_dst_set: set[Path] = set()
            for row in selected_rows:
                src_text = norm_text(row.get("candidate_local_path") or row.get("candidate_path") or row.get("source_local_path") or row.get("local_path"))
                src = Path(src_text)
                dst = resolve_dst(row.get("formal_local_path") or row.get("destination_local_path") or row.get("local_path") or "", formal_root)
                if not src.exists():
                    st.err("source_missing", "copy_phase", f"source missing: {src}", "missing_artifact", str(src), norm_text(row.get("planned_unit_id")))
                    continue
                if not is_within(dst, formal_root):
                    st.err("destination_outside_root", "copy_phase", f"destination outside formal root: {dst}", "consistency", str(dst), norm_text(row.get("planned_unit_id")))
                    continue
                adopted_dst_set.add(dst.resolve())
                row["local_path"] = str(dst)
                adopted_dst_paths.append(dst)
                same = dst.exists() and src.resolve() == dst.resolve() and file_sha256(src) == file_sha256(dst)
                if same:
                    noop_count += 1
                    continue
                if not args.dry_run:
                    ensure_dir(dst.parent)
                    shutil.copy2(src, dst)
                replaced_count += 1
                if norm_text(os.environ.get("TASK211_FORCE_FAIL_AFTER_REPLACE")).lower() in {"1", "true", "yes"}:
                    raise RuntimeError("forced_fail_after_replace")

            old_scope_paths = {resolve_dst(r.get("local_path") or "", formal_root).resolve() for r in scope_rows_before}
            delete_targets = sorted(old_scope_paths - adopted_dst_set)
            for p in delete_targets:
                if not is_within(p, formal_root):
                    st.err("delete_outside_root", "delete_phase_guard", f"delete target outside formal root: {p}", "consistency", str(p))
                    continue
                if p in adopted_dst_set:
                    st.err("delete_referenced_path", "delete_phase_guard", f"delete target still referenced: {p}", "consistency", str(p))
                    continue
                if not args.dry_run and p.exists():
                    p.unlink()
                deleted_count += 1

            reconstructed = non_scope_before + [dict(r) for r in selected_rows]
            before_non_scope: dict[tuple[str, ...], int] = {}
            after_non_scope: dict[tuple[str, ...], int] = {}
            for r in non_scope_before:
                k = semantic_key(r)
                before_non_scope[k] = before_non_scope.get(k, 0) + 1
            for r in reconstructed:
                if norm_text(r.get("scope_hash")) != scope_hash:
                    k = semantic_key(r)
                    after_non_scope[k] = after_non_scope.get(k, 0) + 1
            if before_non_scope != after_non_scope:
                st.err("non_scope_changed", "keyed_semantic_diff", "scope outside rows changed", "consistency")
            if st.errors:
                raise RuntimeError("postcheck_failed")

            if not args.dry_run:
                write_csv(current_targets_p, reconstructed, current_fields)
                formal_manifest["last_adoption_run_id"] = run_id
                formal_manifest["last_adoption_scope_hash"] = scope_hash
                formal_manifest["last_adoption_completed_at"] = utc_now_iso()
                formal_manifest["last_replaced_file_count"] = replaced_count
                formal_manifest["last_deleted_file_count"] = deleted_count
                write_json(formal_manifest_p, formal_manifest)

            if noop_count > 0:
                status = STATUS_PARTIAL_SUCCESS
                exit_code = EXIT_PARTIAL_SUCCESS
            else:
                status = STATUS_SUCCESS
                exit_code = EXIT_SUCCESS
            adoption_allowed = True
            manual_review_required = False
            retry_recommended = False

    except Exception as exc:
        if not st.errors:
            st.err("internal_exception", "main_exception", f"{type(exc).__name__}: {exc}", "internal")
        if str(exc) in {"forced_fail_after_replace", "postcheck_failed"} and args.rollback_on_failure and backup_rows:
            rollback_executed = True
            restore_map = {norm_text(r.get("source_path")): norm_text(r.get("backup_path")) for r in backup_rows if norm_text(r.get("backup_type")) in {"formal_file", "target_list", "formal_manifest"}}
            failed: list[str] = []
            restored = 0
            removed_new = 0
            for p in sorted({str(x) for x in scope_before_paths} | {str(x) for x in adopted_dst_paths}):
                target = Path(p)
                bak = Path(restore_map[p]) if p in restore_map else None
                try:
                    if bak and bak.exists():
                        ensure_dir(target.parent)
                        shutil.copy2(bak, target)
                        restored += 1
                    elif target.exists():
                        target.unlink()
                        removed_new += 1
                except Exception as r_exc:
                    failed.append(f"{target}:{type(r_exc).__name__}:{r_exc}")
            write_json(out["rollback_result_json"], {"task_id": "TASK211", "run_id": run_id, "rollback_executed": True, "rollback_ok": len(failed) == 0, "restored_file_count": restored, "removed_new_file_count": removed_new, "failed_paths": failed})
            write_md(out["rollback_result_md"], [
                "# TASK211 Rollback Result",
                "",
                f"- rollback_executed: `true`",
                f"- rollback_ok: `{'true' if len(failed) == 0 else 'false'}`",
                f"- restored_file_count: `{restored}`",
                f"- removed_new_file_count: `{removed_new}`",
                f"- failed_paths_count: `{len(failed)}`",
            ])
            if len(failed) == 0:
                status = STATUS_ROLLED_BACK
                exit_code = EXIT_ROLLED_BACK
                adoption_allowed = False
                manual_review_required = True
                retry_recommended = True
            else:
                status = STATUS_INTERNAL
                exit_code = EXIT_INTERNAL
                adoption_allowed = False
                manual_review_required = True
                retry_recommended = False
        elif status == STATUS_HOLD:
            exit_code = EXIT_HOLD
        elif st.errors:
            fail_exit = choose_fail_exit(st.errors)
            if fail_exit == EXIT_INTERNAL:
                status = STATUS_INTERNAL
                exit_code = EXIT_INTERNAL
            else:
                status = STATUS_FAIL_FAST
                exit_code = fail_exit
        else:
            status = STATUS_INTERNAL
            exit_code = EXIT_INTERNAL

    write_common_outputs(
        out=out,
        run_id=run_id,
        status=status,
        exit_code=exit_code,
        started=started,
        st=st,
        ids=ids,
        scope_hash=scope_hash,
        selected_rows=selected_rows,
        selected_units=selected_units,
        replaced_count=replaced_count,
        deleted_count=deleted_count,
        noop_count=noop_count,
        rollback_executed=rollback_executed,
        adoption_allowed=adoption_allowed,
        manual_review_required=manual_review_required,
        retry_recommended=retry_recommended,
        resolved_inputs=resolved,
        trash_dir=trash_dir,
        backup_rows=backup_rows,
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
