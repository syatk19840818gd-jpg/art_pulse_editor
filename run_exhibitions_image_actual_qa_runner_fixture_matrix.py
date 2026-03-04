#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def norm_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="TASK207 actual QA runner fixture matrix")
    p.add_argument(
        "--output-root",
        default="data/phase1_seed10/logs/task_t207_qa_runner_fixture_runs",
    )
    p.add_argument("--runner-path", default="run_exhibitions_image_actual_qa_runner.py")
    p.add_argument(
        "--summary-json",
        default="data/phase1_seed10/logs/exhibitions_image_task_t207_qa_runner_fixture_matrix_summary.json",
    )
    p.add_argument(
        "--summary-csv",
        default="data/phase1_seed10/logs/exhibitions_image_task_t207_qa_runner_fixture_matrix_summary_table.csv",
    )
    return p.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def find_one(case_dir: Path, pattern: str) -> Path:
    hits = sorted(case_dir.glob(pattern))
    if not hits:
        raise FileNotFoundError(f"pattern_not_found:{pattern}:{case_dir}")
    return hits[0]


def find_optional(case_dir: Path, pattern: str) -> Path | None:
    hits = sorted(case_dir.glob(pattern))
    return hits[0] if hits else None


def detect_inputs(case_dir: Path) -> dict[str, Path | None]:
    return {
        "manifest_json": find_one(
            case_dir, "exhibitions_image_task_t205_qa_runtime_input_manifest_*.json"
        ),
        "unit_summary_json": find_one(
            case_dir, "exhibitions_image_task_t205_qa_runtime_unit_summary_*.json"
        ),
        "target_units_csv": find_one(
            case_dir, "exhibitions_image_task_t205_qa_runtime_target_units_*.csv"
        ),
        "target_rows_csv": find_one(
            case_dir, "exhibitions_image_task_t205_qa_runtime_target_rows_*.csv"
        ),
        "scope_json": find_one(
            case_dir, "exhibitions_image_task_t205_qa_runtime_scope_*.json"
        ),
        "report_md": find_one(
            case_dir, "exhibitions_image_task_t205_qa_runtime_report_*.md"
        ),
        "errors_csv": find_optional(
            case_dir, "exhibitions_image_task_t205_qa_runtime_errors_*.csv"
        ),
        "warnings_csv": find_optional(
            case_dir, "exhibitions_image_task_t205_qa_runtime_warnings_*.csv"
        ),
        "source_paths_json": find_optional(
            case_dir, "exhibitions_image_task_t205_qa_runtime_source_paths_*.json"
        ),
        "failure_context_csv": find_optional(
            case_dir, "exhibitions_image_task_t205_qa_runtime_failure_context_*.csv"
        ),
    }


def read_csv_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fp:
        reader = csv.DictReader(fp)
        fields = list(reader.fieldnames or [])
        rows = [dict(row) for row in reader]
    return fields, rows


def write_csv_rows(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def drop_column(csv_path: Path, column: str) -> None:
    fields, rows = read_csv_rows(csv_path)
    fields = [f for f in fields if norm_text(f) != column]
    write_csv_rows(csv_path, fields, rows)


def mutate_case(case_dir: Path, inputs: dict[str, Path | None], mutate: str) -> None:
    if mutate == "":
        return
    target_units = inputs["target_units_csv"]
    target_rows = inputs["target_rows_csv"]
    scope_json = inputs["scope_json"]
    assert target_units and target_rows and scope_json

    if mutate == "remove_required_target_units":
        target_units.unlink(missing_ok=True)
        return
    if mutate == "schema_drift_target_units":
        drop_column(target_units, "planned_unit_id")
        return
    if mutate == "scope_mismatch":
        payload = read_json(scope_json)
        payload["scope_hash"] = "scope_hash_mismatch_task207"
        write_json(scope_json, payload)
        return
    if mutate == "partial_multi_unit":
        unit_fields, unit_rows = read_csv_rows(target_units)
        row_fields, rows = read_csv_rows(target_rows)
        if not unit_rows or not rows:
            raise RuntimeError("partial_multi_unit requires non-empty base files")

        base_u = dict(unit_rows[0])
        base_r = dict(rows[0])
        new_unit_id = "U-SAFE-frieze_london-2025-002"
        base_u["planned_unit_id"] = new_unit_id
        base_u["actual_trial_run_id"] = "trial-2025-frieze_london-safe-SAFE-frieze_london-2025-002"
        base_u["selected_row_count"] = "1"
        unit_rows.append(base_u)
        write_csv_rows(target_units, unit_fields, unit_rows)

        base_r["planned_unit_id"] = new_unit_id
        base_r["actual_trial_run_id"] = "trial-2025-frieze_london-safe-SAFE-frieze_london-2025-002"
        rows.append(base_r)
        write_csv_rows(target_rows, row_fields, rows)
        return
    raise ValueError(f"unsupported_mutation:{mutate}")


def tail_text(text: str, max_lines: int = 12) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return ""
    return "\n".join(lines[-max_lines:])


def main() -> int:
    args = parse_args()
    output_root = Path(args.output_root)
    runner_path = Path(args.runner_path)
    summary_json_path = Path(args.summary_json)
    summary_csv_path = Path(args.summary_csv)

    base_ready = Path("data/phase1_seed10/logs/task_t205_qa_adapter_fixture_runs/ready_pass_bundle")
    cases = [
        {
            "case_id": "success_single_unit",
            "base_dir": str(base_ready),
            "mutate": "",
            "extra_args": [],
            "expected_status": "SUCCESS",
            "expected_exit": 0,
        },
        {
            "case_id": "partial_success_multi_unit",
            "base_dir": str(base_ready),
            "mutate": "partial_multi_unit",
            "extra_args": ["--continue-on-unit-failure"],
            "expected_status": "PARTIAL_SUCCESS",
            "expected_exit": 21,
            "force_unit_status_json": '{"U-SAFE-frieze_london-2025-002":"failed"}',
        },
        {
            "case_id": "hold_no_executable_units",
            "base_dir": str(base_ready),
            "mutate": "",
            "extra_args": ["--planned-unit-id", "UNIT_NOT_IN_SCOPE"],
            "expected_status": "HOLD",
            "expected_exit": 20,
        },
        {
            "case_id": "reject_missing_required_file",
            "base_dir": str(base_ready),
            "mutate": "remove_required_target_units",
            "extra_args": [],
            "expected_status": "FAIL_FAST",
            "expected_exit": 10,
        },
        {
            "case_id": "reject_schema_drift",
            "base_dir": str(base_ready),
            "mutate": "schema_drift_target_units",
            "extra_args": [],
            "expected_status": "FAIL_FAST",
            "expected_exit": 11,
        },
        {
            "case_id": "reject_scope_mismatch",
            "base_dir": str(base_ready),
            "mutate": "scope_mismatch",
            "extra_args": [],
            "expected_status": "FAIL_FAST",
            "expected_exit": 12,
        },
        {
            "case_id": "reject_policy_violation",
            "base_dir": str(base_ready),
            "mutate": "partial_multi_unit",
            "extra_args": ["--max-units-per-run", "1", "--fail-on-policy-violation"],
            "expected_status": "FAIL_FAST",
            "expected_exit": 12,
        },
        {
            "case_id": "internal_failure_monkeypatch",
            "base_dir": str(base_ready),
            "mutate": "",
            "extra_args": [],
            "expected_status": "INTERNAL_FAILURE",
            "expected_exit": 30,
            "force_internal_failure": True,
        },
    ]

    output_root.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for case in cases:
        case_id = norm_text(case["case_id"])
        case_output = output_root / case_id
        if case_output.exists():
            shutil.rmtree(case_output)
        shutil.copytree(Path(case["base_dir"]), case_output)
        inputs = detect_inputs(case_output)
        mutate_case(case_output, inputs, norm_text(case.get("mutate")))

        cmd = [
            sys.executable,
            str(runner_path),
            "--qa-runtime-input-manifest",
            str(inputs["manifest_json"]),
            "--qa-runtime-unit-summary",
            str(inputs["unit_summary_json"]),
            "--qa-runtime-target-units-csv",
            str(inputs["target_units_csv"]),
            "--qa-runtime-target-rows-csv",
            str(inputs["target_rows_csv"]),
            "--qa-runtime-scope-json",
            str(inputs["scope_json"]),
            "--qa-runtime-report-md",
            str(inputs["report_md"]),
            "--output-dir",
            str(case_output),
            "--qa-runner-bundle-id",
            f"task207-{case_id}",
            "--dry-run",
        ]
        if inputs.get("errors_csv"):
            cmd.extend(["--qa-runtime-errors-csv", str(inputs["errors_csv"])])
        if inputs.get("warnings_csv"):
            cmd.extend(["--qa-runtime-warnings-csv", str(inputs["warnings_csv"])])
        if inputs.get("source_paths_json"):
            cmd.extend(["--qa-runtime-source-paths-json", str(inputs["source_paths_json"])])
        if inputs.get("failure_context_csv"):
            cmd.extend(["--qa-runtime-failure-context-csv", str(inputs["failure_context_csv"])])
        cmd.extend(case.get("extra_args", []))

        env = dict(os.environ)
        force_map = norm_text(case.get("force_unit_status_json"))
        if force_map:
            env["TASK207_FORCE_UNIT_STATUS_JSON"] = force_map
        if case.get("force_internal_failure", False):
            env["TASK207_FORCE_INTERNAL_FAILURE"] = "1"

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
        )
        actual_exit = int(proc.returncode)

        summary_path = (
            case_output
            / f"exhibitions_image_task_t207_qa_execution_summary_task207-{case_id}.json"
        )
        actual_status = ""
        checks = {
            "summary_exists": summary_path.exists(),
            "manifest_exists": (
                case_output
                / f"exhibitions_image_task_t207_qa_execution_manifest_task207-{case_id}.json"
            ).exists(),
            "report_exists": (
                case_output
                / f"exhibitions_image_task_t207_qa_execution_report_task207-{case_id}.md"
            ).exists(),
            "bundle_result_exists": (
                case_output
                / f"exhibitions_image_task_t207_qa_bundle_result_task207-{case_id}.csv"
            ).exists(),
            "adoption_handoff_exists": (
                case_output
                / f"exhibitions_image_task_t207_qa_adoption_handoff_manifest_task207-{case_id}.json"
            ).exists(),
        }
        if summary_path.exists():
            actual_status = norm_text(read_json(summary_path).get("qa_runner_status"))

        expected_exit = int(case["expected_exit"])
        expected_status = norm_text(case["expected_status"])
        ok = (
            actual_exit == expected_exit
            and actual_status == expected_status
            and not any(v is False for v in checks.values())
        )

        results.append(
            {
                "case_id": case_id,
                "expected_qa_runner_status": expected_status,
                "actual_qa_runner_status": actual_status,
                "expected_exit_code": expected_exit,
                "actual_exit_code": actual_exit,
                "status": "passed" if ok else "failed",
                "stdout_tail": tail_text((proc.stdout or "") + "\n" + (proc.stderr or "")),
                "generated_paths": sorted([str(p) for p in case_output.rglob("*") if p.is_file()]),
                "summary_checks": checks,
            }
        )

    total = len(results)
    passed = len([r for r in results if r["status"] == "passed"])
    failed = total - passed
    summary_payload = {
        "task_id": "TASK207",
        "generated_at": utc_now_iso(),
        "output_root": str(output_root),
        "all_passed": failed == 0,
        "total_cases": total,
        "passed_cases": passed,
        "failed_cases": failed,
        "cases": results,
    }
    write_json(summary_json_path, summary_payload)

    summary_csv_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_csv_path.open("w", encoding="utf-8", newline="") as fp:
        fields = [
            "case_id",
            "expected_qa_runner_status",
            "actual_qa_runner_status",
            "expected_exit_code",
            "actual_exit_code",
            "status",
        ]
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        for row in results:
            writer.writerow({k: row.get(k, "") for k in fields})

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
