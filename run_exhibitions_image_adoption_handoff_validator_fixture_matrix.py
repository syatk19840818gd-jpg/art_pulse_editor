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
    parser = argparse.ArgumentParser(description="TASK209 adoption handoff validator fixture matrix")
    parser.add_argument(
        "--output-root",
        default="data/phase1_seed10/logs/task_t209_adoption_handoff_fixture_runs",
    )
    parser.add_argument(
        "--validator-path",
        default="run_exhibitions_image_adoption_handoff_validator.py",
    )
    parser.add_argument(
        "--fixture-manifest-json",
        default="data/phase1_seed10/logs/exhibitions_image_task_t209_adoption_handoff_fixture_manifest.json",
    )
    parser.add_argument(
        "--summary-json",
        default="data/phase1_seed10/logs/exhibitions_image_task_t209_adoption_handoff_fixture_matrix_summary.json",
    )
    parser.add_argument(
        "--summary-csv",
        default="data/phase1_seed10/logs/exhibitions_image_task_t209_adoption_handoff_fixture_matrix_summary_table.csv",
    )
    return parser.parse_args()


def find_one(case_dir: Path, pattern: str) -> Path:
    hits = sorted(case_dir.glob(pattern))
    if not hits:
        raise FileNotFoundError(f"pattern_not_found:{pattern}:{case_dir}")
    return hits[0]


def detect_inputs(case_dir: Path) -> dict[str, Path]:
    return {
        "qa_execution_manifest": find_one(
            case_dir, "exhibitions_image_task_t207_qa_execution_manifest_*.json"
        ),
        "qa_execution_summary": find_one(
            case_dir, "exhibitions_image_task_t207_qa_execution_summary_*.json"
        ),
        "qa_execution_report": find_one(
            case_dir, "exhibitions_image_task_t207_qa_execution_report_*.md"
        ),
        "qa_bundle_result_csv": find_one(
            case_dir, "exhibitions_image_task_t207_qa_bundle_result_*.csv"
        ),
        "qa_adoption_handoff_manifest": find_one(
            case_dir, "exhibitions_image_task_t207_qa_adoption_handoff_manifest_*.json"
        ),
    }


def drop_column(csv_path: Path, column: str) -> None:
    fields, rows = read_csv_rows(csv_path)
    fields2 = [f for f in fields if norm_text(f) != column]
    write_csv_rows(csv_path, fields2, rows)


def tail_text(text: str, max_lines: int = 10) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return ""
    return "\n".join(lines[-max_lines:])


def rebase_embedded_paths(case_dir: Path, inputs: dict[str, Path]) -> None:
    bundle_fields, bundle_rows = read_csv_rows(inputs["qa_bundle_result_csv"])
    for row in bundle_rows:
        for key in ["qa_unit_result_json_path", "qa_unit_rows_csv_path"]:
            src = norm_text(row.get(key))
            if not src:
                continue
            local = case_dir / Path(src).name
            if local.exists():
                row[key] = str(local).replace("/", "\\")
    write_csv_rows(inputs["qa_bundle_result_csv"], bundle_fields, bundle_rows)

    handoff = read_json(inputs["qa_adoption_handoff_manifest"])
    paths = []
    for p in handoff.get("qa_unit_result_paths") or []:
        local = case_dir / Path(norm_text(p)).name
        paths.append(str(local).replace("/", "\\") if local.exists() else norm_text(p))
    handoff["qa_unit_result_paths"] = paths
    for key in ["qa_bundle_summary_path", "qa_failure_queue_path", "qa_defer_queue_path"]:
        p = norm_text(handoff.get(key))
        if p:
            local = case_dir / Path(p).name
            if local.exists():
                handoff[key] = str(local).replace("/", "\\")
    write_json(inputs["qa_adoption_handoff_manifest"], handoff)

    qa_manifest = read_json(inputs["qa_execution_manifest"])
    outputs = qa_manifest.get("outputs") or {}
    for key, value in list(outputs.items()):
        p = norm_text(value)
        if p:
            local = case_dir / Path(p).name
            if local.exists():
                outputs[key] = str(local).replace("/", "\\")
    qa_manifest["outputs"] = outputs
    write_json(inputs["qa_execution_manifest"], qa_manifest)


def copy_fixture_case(base_dir: Path, case_output: Path) -> dict[str, Path]:
    case_output.mkdir(parents=True, exist_ok=True)
    base_inputs = detect_inputs(base_dir)

    copied_inputs: dict[str, Path] = {}
    for key, src in base_inputs.items():
        dst = case_output / src.name
        shutil.copy2(src, dst)
        copied_inputs[key] = dst

    bundle_fields, bundle_rows = read_csv_rows(copied_inputs["qa_bundle_result_csv"])
    copied_paths: set[Path] = set()
    for row in bundle_rows:
        for key in ["qa_unit_result_json_path", "qa_unit_rows_csv_path"]:
            src_text = norm_text(row.get(key))
            if not src_text:
                continue
            src = Path(src_text)
            if not src.exists():
                src = base_dir / Path(src_text).name
            if src.exists() and src not in copied_paths:
                shutil.copy2(src, case_output / src.name)
                copied_paths.add(src)

    handoff = read_json(copied_inputs["qa_adoption_handoff_manifest"])
    for key in ["qa_bundle_summary_path", "qa_failure_queue_path", "qa_defer_queue_path"]:
        src_text = norm_text(handoff.get(key))
        if not src_text:
            continue
        src = Path(src_text)
        if not src.exists():
            src = base_dir / Path(src_text).name
        if src.exists() and src not in copied_paths:
            shutil.copy2(src, case_output / src.name)
            copied_paths.add(src)

    qa_manifest = read_json(copied_inputs["qa_execution_manifest"])
    outputs = qa_manifest.get("outputs") or {}
    for value in outputs.values():
        src_text = norm_text(value)
        if not src_text:
            continue
        src = Path(src_text)
        if not src.exists():
            src = base_dir / Path(src_text).name
        if src.exists() and src not in copied_paths:
            shutil.copy2(src, case_output / src.name)
            copied_paths.add(src)

    return copied_inputs


def mutate_case(case_dir: Path, inputs: dict[str, Path], mutate: str) -> None:
    if not mutate:
        return
    if mutate == "remove_required_file":
        inputs["qa_adoption_handoff_manifest"].unlink(missing_ok=True)
        return
    if mutate == "schema_drift_bundle_result":
        drop_column(inputs["qa_bundle_result_csv"], "actual_qa_run_id")
        return
    if mutate == "cross_file_scope_mismatch":
        _, bundle_rows = read_csv_rows(inputs["qa_bundle_result_csv"])
        if not bundle_rows:
            return
        unit_json = Path(norm_text(bundle_rows[0].get("qa_unit_result_json_path")))
        payload = read_json(unit_json)
        payload["scope_hash"] = "scope_hash_mismatch_task209"
        write_json(unit_json, payload)
        return
    if mutate == "empty_executed_units":
        summary = read_json(inputs["qa_execution_summary"])
        summary["executed_unit_count"] = 0
        summary["succeeded_unit_count"] = 0
        summary["failed_unit_count"] = 0
        summary["deferred_unit_count"] = 0
        summary["adoption_handoff_allowed"] = True
        summary["qa_runner_status"] = "SUCCESS"
        write_json(inputs["qa_execution_summary"], summary)
        handoff = read_json(inputs["qa_adoption_handoff_manifest"])
        handoff["executed_unit_ids"] = []
        handoff["qa_unit_result_paths"] = []
        write_json(inputs["qa_adoption_handoff_manifest"], handoff)
        fields, _ = read_csv_rows(inputs["qa_bundle_result_csv"])
        write_csv_rows(inputs["qa_bundle_result_csv"], fields, [])
        return
    if mutate == "manifest_missing_output_path":
        handoff = read_json(inputs["qa_adoption_handoff_manifest"])
        unit_paths = list(handoff.get("qa_unit_result_paths") or [])
        unit_paths.append(str(case_dir / "non_existing_unit_result_task209.json"))
        handoff["qa_unit_result_paths"] = unit_paths
        write_json(inputs["qa_adoption_handoff_manifest"], handoff)
        return
    raise ValueError(f"unsupported_mutation:{mutate}")


def main() -> int:
    args = parse_args()
    output_root = Path(args.output_root)
    validator_path = Path(args.validator_path)
    fixture_manifest_path = Path(args.fixture_manifest_json)
    summary_json_path = Path(args.summary_json)
    summary_csv_path = Path(args.summary_csv)

    base_success = Path("data/phase1_seed10/logs/task_t207_qa_runner_fixture_runs/success_single_unit")
    base_partial = Path("data/phase1_seed10/logs/task_t207_qa_runner_fixture_runs/partial_success_multi_unit")
    cases = [
        {"case_id": "pass_success_bundle", "case_run_id": "t209-c01", "base_dir": str(base_success), "mutate": "", "expected_verdict": "PASS", "expected_exit_code": 0},
        {"case_id": "hold_partial_or_warning_bundle", "case_run_id": "t209-c02", "base_dir": str(base_partial), "mutate": "", "expected_verdict": "HOLD", "expected_exit_code": 20},
        {"case_id": "fail_missing_required_file", "case_run_id": "t209-c03", "base_dir": str(base_success), "mutate": "remove_required_file", "expected_verdict": "FAIL", "expected_exit_code": 10},
        {"case_id": "fail_schema_drift", "case_run_id": "t209-c04", "base_dir": str(base_success), "mutate": "schema_drift_bundle_result", "expected_verdict": "FAIL", "expected_exit_code": 11},
        {"case_id": "fail_cross_file_scope_mismatch", "case_run_id": "t209-c05", "base_dir": str(base_success), "mutate": "cross_file_scope_mismatch", "expected_verdict": "FAIL", "expected_exit_code": 12},
        {"case_id": "fail_empty_executed_units", "case_run_id": "t209-c06", "base_dir": str(base_success), "mutate": "empty_executed_units", "expected_verdict": "FAIL", "expected_exit_code": 13},
        {"case_id": "fail_manifest_missing_output_path", "case_run_id": "t209-c07", "base_dir": str(base_success), "mutate": "manifest_missing_output_path", "expected_verdict": "FAIL", "expected_exit_code": 12},
        {"case_id": "internal_failure_monkeypatch", "case_run_id": "t209-c08", "base_dir": str(base_success), "mutate": "", "expected_verdict": "FAIL", "expected_exit_code": 30, "force_internal_failure": True},
    ]

    output_root.mkdir(parents=True, exist_ok=True)
    fixture_manifest = {"task_id": "TASK209", "generated_at": utc_now_iso(), "output_root": str(output_root), "cases": cases}
    write_json(fixture_manifest_path, fixture_manifest)

    results: list[dict[str, Any]] = []
    for case in cases:
        case_id = norm_text(case["case_id"])
        case_run_id = norm_text(case.get("case_run_id")) or f"t209-{case_id}"
        case_output = output_root / case_id
        if case_output.exists():
            shutil.rmtree(case_output)
        inputs = copy_fixture_case(Path(case["base_dir"]), case_output)
        rebase_embedded_paths(case_output, inputs)
        mutate_case(case_output, inputs, norm_text(case.get("mutate")))

        cmd = [
            sys.executable,
            str(validator_path),
            "--qa-execution-manifest",
            str(inputs["qa_execution_manifest"]),
            "--qa-execution-summary",
            str(inputs["qa_execution_summary"]),
            "--qa-execution-report",
            str(inputs["qa_execution_report"]),
            "--qa-bundle-result-csv",
            str(inputs["qa_bundle_result_csv"]),
            "--qa-adoption-handoff-manifest",
            str(inputs["qa_adoption_handoff_manifest"]),
            "--output-dir",
            str(case_output),
            "--run-id",
            case_run_id,
            "--dry-run",
        ]

        maybe_failure = sorted(case_output.glob("exhibitions_image_task_t207_qa_failure_queue_*.csv"))
        maybe_defer = sorted(case_output.glob("exhibitions_image_task_t207_qa_defer_queue_*.csv"))
        if maybe_failure:
            cmd.extend(["--qa-failure-queue-csv", str(maybe_failure[0])])
        if maybe_defer:
            cmd.extend(["--qa-defer-queue-csv", str(maybe_defer[0])])

        env = dict(os.environ)
        if case.get("force_internal_failure"):
            env["TASK209_FORCE_INTERNAL_FAILURE"] = "1"

        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", env=env)
        actual_exit = int(proc.returncode)
        summary_path = case_output / f"exhibitions_image_task_t209_adoption_handoff_validation_summary_{case_run_id}.json"
        actual_verdict = ""
        checks = {
            "summary_exists": summary_path.exists(),
            "manifest_exists": (case_output / f"exhibitions_image_task_t209_adoption_handoff_validation_manifest_{case_run_id}.json").exists(),
            "report_exists": (case_output / f"exhibitions_image_task_t209_adoption_handoff_validation_report_{case_run_id}.md").exists(),
            "errors_exists": (case_output / f"exhibitions_image_task_t209_adoption_handoff_validation_errors_{case_run_id}.csv").exists(),
            "warnings_exists": (case_output / f"exhibitions_image_task_t209_adoption_handoff_validation_warnings_{case_run_id}.csv").exists(),
        }
        if summary_path.exists():
            actual_verdict = norm_text(read_json(summary_path).get("adoption_handoff_verdict"))

        ok = (
            actual_exit == int(case["expected_exit_code"])
            and actual_verdict == norm_text(case["expected_verdict"])
            and not any(v is False for v in checks.values())
        )
        results.append(
            {
                "case_id": case_id,
                "expected_adoption_handoff_verdict": norm_text(case["expected_verdict"]),
                "actual_adoption_handoff_verdict": actual_verdict,
                "expected_exit_code": int(case["expected_exit_code"]),
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
        "task_id": "TASK209",
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
            "expected_adoption_handoff_verdict",
            "actual_adoption_handoff_verdict",
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
