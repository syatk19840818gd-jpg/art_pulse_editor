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
    parser = argparse.ArgumentParser(description="TASK199 runtime adapter controlled fixture matrix")
    parser.add_argument(
        "--output-root",
        default="data/phase1_seed10/logs/task_t199_adapter_fixture_runs",
    )
    parser.add_argument(
        "--adapter-path",
        default="run_exhibitions_image_classification_to_trial_runtime_adapter.py",
    )
    parser.add_argument(
        "--summary-json",
        default="data/phase1_seed10/logs/exhibitions_image_task_t199_adapter_fixture_matrix_summary.json",
    )
    parser.add_argument(
        "--summary-csv",
        default="data/phase1_seed10/logs/exhibitions_image_task_t199_adapter_fixture_matrix_summary_table.csv",
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
        "handoff_summary_json": find_one(
            case_dir, "exhibitions_image_task_t197_handoff_validation_summary_*.json"
        ),
        "handoff_manifest_json": find_one(
            case_dir, "exhibitions_image_task_t197_handoff_validation_manifest_*.json"
        ),
        "classification_bundle_manifest_json": find_one(
            case_dir, "exhibitions_image_task_t195_classification_bundle_manifest_*.json"
        ),
        "classification_integration_summary_json": find_one(
            case_dir, "exhibitions_image_task_t195_classification_integration_summary_*.json"
        ),
        "handoff_paths_json": find_one(
            case_dir, "exhibitions_image_task_t195_handoff_paths_*.json"
        ),
        "lane_ready_inventory_csv": find_one(
            case_dir, "exhibitions_image_task_t192_lane_ready_inventory_*.csv"
        ),
        "unit_plan_csv": find_one(
            case_dir, "exhibitions_image_task_t192_unit_plan_*.csv"
        ),
        "classification_decision_csv": find_one(
            case_dir, "exhibitions_image_task_t192_classification_decision_*.csv"
        ),
        "resolved_input_manifest_json": find_one(
            case_dir, "exhibitions_image_task_t195_resolved_input_manifest_*.json"
        ),
    }


def drop_column(csv_path: Path, column: str) -> None:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as fp:
        reader = csv.DictReader(fp)
        fields = [f for f in (reader.fieldnames or []) if norm_text(f) != column]
        rows = list(reader)
    with csv_path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def mutate_case(case_dir: Path, inputs: dict[str, Path], mutate: str) -> None:
    if mutate == "remove_unit_plan":
        inputs["unit_plan_csv"].unlink(missing_ok=True)
        return
    if mutate == "scope_hash_mismatch":
        payload = read_json(inputs["classification_integration_summary_json"])
        payload["scope_hash"] = "scope_hash_mismatch_task199"
        write_json(inputs["classification_integration_summary_json"], payload)
        return
    if mutate == "unit_inconsistency":
        drop_column(inputs["unit_plan_csv"], "lane")
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
    adapter_path = Path(args.adapter_path)
    summary_json_path = Path(args.summary_json)
    summary_csv_path = Path(args.summary_csv)

    base_success = Path("data/phase1_seed10/logs/task_t197_handoff_fixture_runs/success_handoff_pass")
    base_hold = Path("data/phase1_seed10/logs/task_t197_handoff_fixture_runs/hold_no_trial_ready")

    cases = [
        {
            "case_id": "ready_success",
            "base_dir": str(base_success),
            "mutate": "",
            "extra_args": [],
            "expected_status": "READY",
            "expected_exit": 0,
        },
        {
            "case_id": "hold_no_target_rows",
            "base_dir": str(base_hold),
            "mutate": "",
            "extra_args": [],
            "expected_status": "HOLD",
            "expected_exit": 20,
        },
        {
            "case_id": "reject_missing_required_file",
            "base_dir": str(base_success),
            "mutate": "remove_unit_plan",
            "extra_args": [],
            "expected_status": "REJECT",
            "expected_exit": 10,
        },
        {
            "case_id": "reject_cross_file_scope_mismatch",
            "base_dir": str(base_success),
            "mutate": "scope_hash_mismatch",
            "extra_args": [],
            "expected_status": "REJECT",
            "expected_exit": 12,
        },
        {
            "case_id": "reject_unit_inconsistency",
            "base_dir": str(base_success),
            "mutate": "unit_inconsistency",
            "extra_args": [],
            "expected_status": "REJECT",
            "expected_exit": 11,
        },
        {
            "case_id": "skip_by_scope_filter",
            "base_dir": str(base_success),
            "mutate": "",
            "extra_args": ["--fair-slug", "not_existing_fair_slug"],
            "expected_status": "SKIP",
            "expected_exit": 21,
        },
        {
            "case_id": "internal_failure_monkeypatch",
            "base_dir": str(base_success),
            "mutate": "",
            "extra_args": [],
            "force_internal_failure": True,
            "expected_status": "REJECT",
            "expected_exit": 30,
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
        mutate = norm_text(case.get("mutate"))
        if mutate:
            mutate_case(case_output, inputs, mutate)

        cmd = [
            sys.executable,
            str(adapter_path),
            "--handoff-summary-json",
            str(inputs["handoff_summary_json"]),
            "--handoff-manifest-json",
            str(inputs["handoff_manifest_json"]),
            "--lane-ready-inventory-csv",
            str(inputs["lane_ready_inventory_csv"]),
            "--unit-plan-csv",
            str(inputs["unit_plan_csv"]),
            "--classification-bundle-manifest",
            str(inputs["classification_bundle_manifest_json"]),
            "--classification-integration-summary-json",
            str(inputs["classification_integration_summary_json"]),
            "--handoff-paths-json",
            str(inputs["handoff_paths_json"]),
            "--resolved-input-manifest-json",
            str(inputs["resolved_input_manifest_json"]),
            "--classification-decision-csv",
            str(inputs["classification_decision_csv"]),
            "--output-dir",
            str(case_output),
            "--trial-runtime-bundle-id",
            f"task199-{case_id}",
            "--write-errors-csv",
            "--write-warnings-csv",
        ]
        cmd.extend(case.get("extra_args", []))

        env = dict(os.environ)
        if case.get("force_internal_failure", False):
            env["TASK199_FORCE_INTERNAL_FAILURE"] = "1"
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
            / f"exhibitions_image_task_t199_trial_runtime_unit_summary_task199-{case_id}.json"
        )
        actual_status = ""
        summary_checks = {
            "summary_exists": summary_path.exists(),
            "manifest_exists": (
                case_output
                / f"exhibitions_image_task_t199_trial_runtime_input_manifest_task199-{case_id}.json"
            ).exists(),
            "scope_exists": (
                case_output
                / f"exhibitions_image_task_t199_trial_runtime_scope_task199-{case_id}.json"
            ).exists(),
            "report_exists": (
                case_output
                / f"exhibitions_image_task_t199_trial_runtime_report_task199-{case_id}.md"
            ).exists(),
        }
        if summary_path.exists():
            payload = read_json(summary_path)
            actual_status = norm_text(payload.get("adapter_status"))

        expected_exit = int(case["expected_exit"])
        expected_status = norm_text(case["expected_status"])
        checks_ok = not any(v is False for v in summary_checks.values())
        case_passed = (
            actual_exit == expected_exit and actual_status == expected_status and checks_ok
        )

        matrix_results.append(
            {
                "case_id": case_id,
                "expected_adapter_status": expected_status,
                "actual_adapter_status": actual_status,
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
        "task_id": "TASK199",
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
            "expected_adapter_status",
            "actual_adapter_status",
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
