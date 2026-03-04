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


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TASK203 QA handoff validator fixture matrix")
    parser.add_argument(
        "--output-root",
        default="data/phase1_seed10/logs/task_t203_qa_handoff_fixture_runs",
    )
    parser.add_argument(
        "--validator-path",
        default="run_exhibitions_image_qa_handoff_validator.py",
    )
    parser.add_argument(
        "--fixture-manifest-json",
        default="data/phase1_seed10/logs/exhibitions_image_task_t203_qa_handoff_fixture_manifest.json",
    )
    parser.add_argument(
        "--summary-json",
        default="data/phase1_seed10/logs/exhibitions_image_task_t203_qa_handoff_fixture_matrix_summary.json",
    )
    parser.add_argument(
        "--summary-csv",
        default="data/phase1_seed10/logs/exhibitions_image_task_t203_qa_handoff_fixture_matrix_summary_table.csv",
    )
    return parser.parse_args()


def find_one(case_dir: Path, pattern: str) -> Path:
    matches = sorted(case_dir.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"pattern_not_found:{pattern}:{case_dir}")
    return matches[0]


def detect_inputs(case_dir: Path) -> dict[str, Path]:
    return {
        "trial_execution_manifest": find_one(
            case_dir, "exhibitions_image_task_t201_trial_execution_manifest_*.json"
        ),
        "trial_execution_summary": find_one(
            case_dir, "exhibitions_image_task_t201_trial_execution_summary_*.json"
        ),
        "trial_execution_report": find_one(
            case_dir, "exhibitions_image_task_t201_trial_execution_report_*.md"
        ),
        "trial_bundle_result_csv": find_one(
            case_dir, "exhibitions_image_task_t201_trial_bundle_result_*.csv"
        ),
        "trial_qa_handoff_manifest": find_one(
            case_dir, "exhibitions_image_task_t201_trial_qa_handoff_manifest_*.json"
        ),
    }


def drop_column(csv_path: Path, column: str) -> None:
    fields, rows = read_csv_rows(csv_path)
    fields2 = [f for f in fields if norm_text(f) != column]
    write_csv_rows(csv_path, fields2, rows)


def tail_text(text: str, max_lines: int = 12) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return ""
    return "\n".join(lines[-max_lines:])


def mutate_case(case_dir: Path, inputs: dict[str, Path], mutate: str) -> None:
    if not mutate:
        return
    if mutate == "remove_required_file":
        inputs["trial_qa_handoff_manifest"].unlink(missing_ok=True)
        return
    if mutate == "schema_drift_bundle_result":
        drop_column(inputs["trial_bundle_result_csv"], "actual_trial_run_id")
        return
    if mutate == "cross_file_scope_mismatch":
        bundle_fields, bundle_rows = read_csv_rows(inputs["trial_bundle_result_csv"])
        if not bundle_rows:
            return
        unit_json_path = Path(norm_text(bundle_rows[0].get("trial_unit_result_json_path")))
        unit_payload = read_json(unit_json_path)
        unit_payload["scope_hash"] = "scope_hash_mismatch_task203"
        write_json(unit_json_path, unit_payload)
        return
    if mutate == "empty_executed_units":
        summary = read_json(inputs["trial_execution_summary"])
        summary["executed_unit_count"] = 0
        summary["succeeded_unit_count"] = 0
        summary["failed_unit_count"] = 0
        summary["deferred_unit_count"] = 0
        summary["qa_handoff_allowed"] = True
        summary["trial_runner_status"] = "SUCCESS"
        write_json(inputs["trial_execution_summary"], summary)

        qa_manifest = read_json(inputs["trial_qa_handoff_manifest"])
        qa_manifest["executed_unit_ids"] = []
        qa_manifest["unit_result_paths"] = []
        write_json(inputs["trial_qa_handoff_manifest"], qa_manifest)

        fields, _ = read_csv_rows(inputs["trial_bundle_result_csv"])
        write_csv_rows(inputs["trial_bundle_result_csv"], fields, [])
        return
    if mutate == "manifest_missing_output_path":
        qa_manifest = read_json(inputs["trial_qa_handoff_manifest"])
        unit_paths = list(qa_manifest.get("unit_result_paths") or [])
        unit_paths.append(str(case_dir / "non_existing_unit_result_task203.json"))
        qa_manifest["unit_result_paths"] = unit_paths
        write_json(inputs["trial_qa_handoff_manifest"], qa_manifest)
        return
    raise ValueError(f"unsupported_mutation:{mutate}")


def rebase_embedded_paths(case_dir: Path, inputs: dict[str, Path]) -> None:
    summary_payload = read_json(inputs["trial_execution_summary"])
    ids = summary_payload.get("ids") or {}
    summary_scope_hash = norm_text(summary_payload.get("scope_hash"))
    summary_classification_run_id = norm_text(ids.get("classification_run_id"))
    summary_bundle_id = norm_text(ids.get("bundle_id"))
    summary_trial_runner_bundle_id = norm_text(ids.get("trial_runner_bundle_id"))

    bundle_fields, bundle_rows = read_csv_rows(inputs["trial_bundle_result_csv"])
    for row in bundle_rows:
        for key in ["trial_unit_result_json_path", "trial_unit_rows_csv_path"]:
            src = norm_text(row.get(key))
            if not src:
                continue
            local_candidate = case_dir / Path(src).name
            if local_candidate.exists():
                row[key] = str(local_candidate).replace("/", "\\")

        unit_json_path = norm_text(row.get("trial_unit_result_json_path"))
        if unit_json_path:
            unit_json = Path(unit_json_path)
            if unit_json.exists():
                unit_payload = read_json(unit_json)
                if summary_scope_hash:
                    unit_payload["scope_hash"] = summary_scope_hash
                if summary_classification_run_id:
                    unit_payload["classification_run_id"] = summary_classification_run_id
                if summary_bundle_id:
                    unit_payload["bundle_id"] = summary_bundle_id
                if summary_trial_runner_bundle_id:
                    unit_payload["trial_runner_bundle_id"] = summary_trial_runner_bundle_id
                write_json(unit_json, unit_payload)
    write_csv_rows(inputs["trial_bundle_result_csv"], bundle_fields, bundle_rows)

    qa_manifest = read_json(inputs["trial_qa_handoff_manifest"])
    unit_paths = []
    for path_text in qa_manifest.get("unit_result_paths") or []:
        local_candidate = case_dir / Path(norm_text(path_text)).name
        if local_candidate.exists():
            unit_paths.append(str(local_candidate).replace("/", "\\"))
        else:
            unit_paths.append(norm_text(path_text))
    qa_manifest["unit_result_paths"] = unit_paths
    for key in ["bundle_summary_path", "failure_queue_path", "defer_queue_path"]:
        p = norm_text(qa_manifest.get(key))
        if p:
            local_candidate = case_dir / Path(p).name
            if local_candidate.exists():
                qa_manifest[key] = str(local_candidate).replace("/", "\\")
    write_json(inputs["trial_qa_handoff_manifest"], qa_manifest)

    trial_manifest = read_json(inputs["trial_execution_manifest"])
    outputs = trial_manifest.get("outputs") or {}
    for key, value in list(outputs.items()):
        p = norm_text(value)
        if not p:
            continue
        local_candidate = case_dir / Path(p).name
        if local_candidate.exists():
            outputs[key] = str(local_candidate).replace("/", "\\")
    trial_manifest["outputs"] = outputs
    write_json(inputs["trial_execution_manifest"], trial_manifest)


def main() -> int:
    args = parse_args()
    output_root = Path(args.output_root)
    validator_path = Path(args.validator_path)
    fixture_manifest_path = Path(args.fixture_manifest_json)
    summary_json_path = Path(args.summary_json)
    summary_csv_path = Path(args.summary_csv)

    base_success = Path(
        "data/phase1_seed10/logs/task_t201_trial_runner_fixture_runs/success_single_unit"
    )
    base_partial = Path(
        "data/phase1_seed10/logs/task_t201_trial_runner_fixture_runs/partial_success_multi_unit"
    )

    cases = [
        {
            "case_id": "pass_success_bundle",
            "base_dir": str(base_success),
            "mutate": "",
            "expected_verdict": "PASS",
            "expected_exit_code": 0,
        },
        {
            "case_id": "hold_partial_or_warning_bundle",
            "base_dir": str(base_partial),
            "mutate": "",
            "expected_verdict": "HOLD",
            "expected_exit_code": 20,
        },
        {
            "case_id": "fail_missing_required_file",
            "base_dir": str(base_success),
            "mutate": "remove_required_file",
            "expected_verdict": "FAIL",
            "expected_exit_code": 10,
        },
        {
            "case_id": "fail_schema_drift",
            "base_dir": str(base_success),
            "mutate": "schema_drift_bundle_result",
            "expected_verdict": "FAIL",
            "expected_exit_code": 11,
        },
        {
            "case_id": "fail_cross_file_scope_mismatch",
            "base_dir": str(base_success),
            "mutate": "cross_file_scope_mismatch",
            "expected_verdict": "FAIL",
            "expected_exit_code": 12,
        },
        {
            "case_id": "fail_empty_executed_units",
            "base_dir": str(base_success),
            "mutate": "empty_executed_units",
            "expected_verdict": "FAIL",
            "expected_exit_code": 13,
        },
        {
            "case_id": "fail_manifest_missing_output_path",
            "base_dir": str(base_success),
            "mutate": "manifest_missing_output_path",
            "expected_verdict": "FAIL",
            "expected_exit_code": 10,
        },
        {
            "case_id": "internal_failure_monkeypatch",
            "base_dir": str(base_success),
            "mutate": "",
            "expected_verdict": "FAIL",
            "expected_exit_code": 30,
            "force_internal_failure": True,
        },
    ]

    output_root.mkdir(parents=True, exist_ok=True)
    write_json(
        fixture_manifest_path,
        {
            "task_id": "TASK203",
            "generated_at": utc_now_iso(),
            "output_root": str(output_root),
            "validator_path": str(validator_path),
            "cases": cases,
        },
    )

    matrix_results: list[dict[str, Any]] = []
    for case_index, case in enumerate(cases, start=1):
        case_id = norm_text(case.get("case_id"))
        case_output = output_root / case_id
        if case_output.exists():
            shutil.rmtree(case_output)
        shutil.copytree(Path(case["base_dir"]), case_output)
        inputs = detect_inputs(case_output)
        rebase_embedded_paths(case_output, inputs)
        mutate_case(case_output, inputs, norm_text(case.get("mutate")))

        run_token = f"t203c{case_index:02d}"
        cmd = [
            sys.executable,
            str(validator_path),
            "--trial-execution-manifest",
            str(inputs["trial_execution_manifest"]),
            "--trial-execution-summary",
            str(inputs["trial_execution_summary"]),
            "--trial-execution-report",
            str(inputs["trial_execution_report"]),
            "--trial-bundle-result-csv",
            str(inputs["trial_bundle_result_csv"]),
            "--trial-qa-handoff-manifest",
            str(inputs["trial_qa_handoff_manifest"]),
            "--output-dir",
            str(case_output),
            "--run-id",
            run_token,
        ]
        env = dict(os.environ)
        if case.get("force_internal_failure", False):
            env["TASK203_FORCE_INTERNAL_FAILURE"] = "1"
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
            / f"exhibitions_image_task_t203_qa_handoff_validation_summary_{run_token}.json"
        )
        actual_verdict = ""
        summary_checks = {
            "summary_exists": summary_path.exists(),
            "manifest_exists": (
                case_output
                / f"exhibitions_image_task_t203_qa_handoff_validation_manifest_{run_token}.json"
            ).exists(),
            "report_exists": (
                case_output
                / f"exhibitions_image_task_t203_qa_handoff_validation_report_{run_token}.md"
            ).exists(),
            "errors_csv_exists": (
                case_output
                / f"exhibitions_image_task_t203_qa_handoff_validation_errors_{run_token}.csv"
            ).exists(),
            "warnings_csv_exists": (
                case_output
                / f"exhibitions_image_task_t203_qa_handoff_validation_warnings_{run_token}.csv"
            ).exists(),
        }
        if summary_path.exists():
            payload = read_json(summary_path)
            actual_verdict = norm_text(payload.get("qa_handoff_verdict"))

        expected_exit = int(case["expected_exit_code"])
        expected_verdict = norm_text(case["expected_verdict"])
        status = "passed" if actual_exit == expected_exit and actual_verdict == expected_verdict else "failed"
        generated_paths = sorted(
            str(path).replace("/", "\\")
            for path in case_output.glob("exhibitions_image_task_t203_*")
            if path.is_file()
        )
        matrix_results.append(
            {
                "case_id": case_id,
                "expected_verdict": expected_verdict,
                "actual_verdict": actual_verdict,
                "expected_exit_code": expected_exit,
                "actual_exit_code": actual_exit,
                "status": status,
                "stdout_tail": tail_text(completed.stdout),
                "stderr_tail": tail_text(completed.stderr),
                "generated_paths": generated_paths,
                "summary_checks": summary_checks,
            }
        )

    passed_cases = sum(1 for row in matrix_results if row["status"] == "passed")
    payload = {
        "task_id": "TASK203",
        "generated_at": utc_now_iso(),
        "output_root": str(output_root),
        "all_passed": passed_cases == len(matrix_results),
        "total_cases": len(matrix_results),
        "passed_cases": passed_cases,
        "failed_cases": len(matrix_results) - passed_cases,
        "cases": matrix_results,
    }
    write_json(summary_json_path, payload)

    summary_csv_rows = [
        {
            "case_id": row["case_id"],
            "expected_verdict": row["expected_verdict"],
            "actual_verdict": row["actual_verdict"],
            "expected_exit_code": row["expected_exit_code"],
            "actual_exit_code": row["actual_exit_code"],
            "status": row["status"],
            "summary_exists": row["summary_checks"]["summary_exists"],
            "manifest_exists": row["summary_checks"]["manifest_exists"],
            "report_exists": row["summary_checks"]["report_exists"],
            "errors_csv_exists": row["summary_checks"]["errors_csv_exists"],
            "warnings_csv_exists": row["summary_checks"]["warnings_csv_exists"],
        }
        for row in matrix_results
    ]
    summary_csv_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_csv_path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(
            fp,
            fieldnames=[
                "case_id",
                "expected_verdict",
                "actual_verdict",
                "expected_exit_code",
                "actual_exit_code",
                "status",
                "summary_exists",
                "manifest_exists",
                "report_exists",
                "errors_csv_exists",
                "warnings_csv_exists",
            ],
        )
        writer.writeheader()
        for row in summary_csv_rows:
            writer.writerow(row)

    return 0 if payload["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
