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
    parser = argparse.ArgumentParser(description="TASK201 actual trial runner controlled fixture matrix")
    parser.add_argument(
        "--output-root",
        default="data/phase1_seed10/logs/task_t201_trial_runner_fixture_runs",
    )
    parser.add_argument(
        "--runner-path",
        default="run_exhibitions_image_actual_trial_runner.py",
    )
    parser.add_argument(
        "--summary-json",
        default="data/phase1_seed10/logs/exhibitions_image_task_t201_trial_runner_fixture_matrix_summary.json",
    )
    parser.add_argument(
        "--summary-csv",
        default="data/phase1_seed10/logs/exhibitions_image_task_t201_trial_runner_fixture_matrix_summary_table.csv",
    )
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def find_one(case_dir: Path, pattern: str) -> Path:
    matches = sorted(case_dir.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"pattern_not_found:{pattern}:{case_dir}")
    return matches[0]


def detect_inputs(case_dir: Path) -> dict[str, Path]:
    return {
        "manifest_json": find_one(
            case_dir, "exhibitions_image_task_t199_trial_runtime_input_manifest_*.json"
        ),
        "unit_summary_json": find_one(
            case_dir, "exhibitions_image_task_t199_trial_runtime_unit_summary_*.json"
        ),
        "target_rows_csv": find_one(
            case_dir, "exhibitions_image_task_t199_trial_runtime_target_rows_*.csv"
        ),
        "target_units_csv": find_one(
            case_dir, "exhibitions_image_task_t199_trial_runtime_target_units_*.csv"
        ),
        "scope_json": find_one(
            case_dir, "exhibitions_image_task_t199_trial_runtime_scope_*.json"
        ),
        "report_md": find_one(
            case_dir, "exhibitions_image_task_t199_trial_runtime_report_*.md"
        ),
        "errors_csv": find_one(
            case_dir, "exhibitions_image_task_t199_trial_runtime_errors_*.csv"
        ),
        "warnings_csv": find_one(
            case_dir, "exhibitions_image_task_t199_trial_runtime_warnings_*.csv"
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


def mutate_case(case_dir: Path, inputs: dict[str, Path], mutate: str) -> None:
    if mutate == "":
        return
    if mutate == "remove_required_target_units":
        inputs["target_units_csv"].unlink(missing_ok=True)
        return
    if mutate == "schema_drift_target_units":
        drop_column(inputs["target_units_csv"], "planned_unit_id")
        return
    if mutate == "scope_mismatch":
        payload = read_json(inputs["scope_json"])
        payload["scope_hash"] = "scope_hash_mismatch_task201"
        write_json(inputs["scope_json"], payload)
        return
    if mutate == "policy_violation_safe":
        fields, rows = read_csv_rows(inputs["target_units_csv"])
        for row in rows:
            row["lane"] = "Safe-But-Provenance-Gated"
            row["trial_ready_seed_count"] = "999"
            row["gallery_count"] = "20"
        write_csv_rows(inputs["target_units_csv"], fields, rows)
        return
    if mutate == "partial_multi_unit":
        unit_fields, unit_rows = read_csv_rows(inputs["target_units_csv"])
        row_fields, target_rows = read_csv_rows(inputs["target_rows_csv"])
        if not unit_rows or not target_rows:
            raise RuntimeError("partial_multi_unit requires non-empty base files")

        new_unit = dict(unit_rows[0])
        new_unit_id = "U-SAFE-frieze_london-2025-002"
        new_unit["planned_unit_id"] = new_unit_id
        new_unit["planned_trial_run_id"] = "trial-2025-frieze_london-safe-SAFE-frieze_london-2025-002"
        unit_rows.append(new_unit)
        write_csv_rows(inputs["target_units_csv"], unit_fields, unit_rows)

        new_row = dict(target_rows[0])
        new_row["planned_unit_id"] = new_unit_id
        new_row["planned_trial_run_id"] = "trial-2025-frieze_london-safe-SAFE-frieze_london-2025-002"
        target_rows.append(new_row)
        write_csv_rows(inputs["target_rows_csv"], row_fields, target_rows)
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

    base_ready = Path("data/phase1_seed10/logs/task_t199_adapter_fixture_runs/ready_success")
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
            "mutate": "policy_violation_safe",
            "extra_args": ["--fail-on-policy-violation"],
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
    matrix_results: list[dict[str, Any]] = []
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
            "--trial-runtime-input-manifest",
            str(inputs["manifest_json"]),
            "--trial-runtime-unit-summary",
            str(inputs["unit_summary_json"]),
            "--trial-runtime-target-rows-csv",
            str(inputs["target_rows_csv"]),
            "--trial-runtime-target-units-csv",
            str(inputs["target_units_csv"]),
            "--trial-runtime-scope-json",
            str(inputs["scope_json"]),
            "--trial-runtime-report-md",
            str(inputs["report_md"]),
            "--trial-runtime-errors-csv",
            str(inputs["errors_csv"]),
            "--trial-runtime-warnings-csv",
            str(inputs["warnings_csv"]),
            "--output-dir",
            str(case_output),
            "--trial-runner-bundle-id",
            f"task201-{case_id}",
            "--dry-run",
        ]
        cmd.extend(case.get("extra_args", []))

        env = dict(os.environ)
        force_map = norm_text(case.get("force_unit_status_json"))
        if force_map:
            env["TASK201_FORCE_UNIT_STATUS_JSON"] = force_map
        if case.get("force_internal_failure", False):
            env["TASK201_FORCE_INTERNAL_FAILURE"] = "1"

        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
        )
        actual_exit = int(completed.returncode)

        summary_path = (
            case_output
            / f"exhibitions_image_task_t201_trial_execution_summary_task201-{case_id}.json"
        )
        actual_status = ""
        summary_checks = {
            "summary_exists": summary_path.exists(),
            "manifest_exists": (
                case_output
                / f"exhibitions_image_task_t201_trial_execution_manifest_task201-{case_id}.json"
            ).exists(),
            "report_exists": (
                case_output
                / f"exhibitions_image_task_t201_trial_execution_report_task201-{case_id}.md"
            ).exists(),
            "bundle_result_exists": (
                case_output
                / f"exhibitions_image_task_t201_trial_bundle_result_task201-{case_id}.csv"
            ).exists(),
            "qa_handoff_exists": (
                case_output
                / f"exhibitions_image_task_t201_trial_qa_handoff_manifest_task201-{case_id}.json"
            ).exists(),
        }
        if summary_path.exists():
            payload = read_json(summary_path)
            actual_status = norm_text(payload.get("trial_runner_status"))

        expected_exit = int(case["expected_exit"])
        expected_status = norm_text(case["expected_status"])
        checks_ok = not any(v is False for v in summary_checks.values())
        case_passed = (
            actual_exit == expected_exit and actual_status == expected_status and checks_ok
        )

        matrix_results.append(
            {
                "case_id": case_id,
                "expected_trial_runner_status": expected_status,
                "actual_trial_runner_status": actual_status,
                "expected_exit_code": expected_exit,
                "actual_exit_code": actual_exit,
                "status": "passed" if case_passed else "failed",
                "stdout_tail": tail_text((completed.stdout or "") + "\n" + (completed.stderr or "")),
                "generated_paths": sorted([str(p) for p in case_output.rglob("*") if p.is_file()]),
                "summary_checks": summary_checks,
            }
        )

    total_cases = len(matrix_results)
    passed_cases = len([r for r in matrix_results if r["status"] == "passed"])
    failed_cases = total_cases - passed_cases
    summary_payload = {
        "task_id": "TASK201",
        "generated_at": utc_now_iso(),
        "output_root": str(output_root),
        "all_passed": failed_cases == 0,
        "total_cases": total_cases,
        "passed_cases": passed_cases,
        "failed_cases": failed_cases,
        "cases": matrix_results,
    }
    write_json(summary_json_path, summary_payload)

    summary_csv_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_csv_path.open("w", encoding="utf-8", newline="") as fp:
        fields = [
            "case_id",
            "expected_trial_runner_status",
            "actual_trial_runner_status",
            "expected_exit_code",
            "actual_exit_code",
            "status",
        ]
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        for row in matrix_results:
            writer.writerow({k: row.get(k, "") for k in fields})
    return 0 if failed_cases == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
