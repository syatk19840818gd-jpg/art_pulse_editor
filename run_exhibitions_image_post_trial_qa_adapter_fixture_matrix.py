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


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="TASK205 post-trial QA adapter fixture matrix")
    p.add_argument("--output-root", default="data/phase1_seed10/logs/task_t205_qa_adapter_fixture_runs")
    p.add_argument("--adapter-path", default="run_exhibitions_image_post_trial_qa_adapter.py")
    p.add_argument("--fixture-manifest-json", default="data/phase1_seed10/logs/exhibitions_image_task_t205_qa_adapter_fixture_manifest.json")
    p.add_argument("--summary-json", default="data/phase1_seed10/logs/exhibitions_image_task_t205_qa_adapter_fixture_matrix_summary.json")
    p.add_argument("--summary-csv", default="data/phase1_seed10/logs/exhibitions_image_task_t205_qa_adapter_fixture_matrix_summary_table.csv")
    return p.parse_args()


def find_one(case_dir: Path, pattern: str) -> Path:
    hits = sorted(case_dir.glob(pattern))
    if not hits:
        raise FileNotFoundError(f"pattern_not_found:{pattern}:{case_dir}")
    return hits[0]


def detect_inputs(case_dir: Path) -> dict[str, Path]:
    return {
        "qa_handoff_validation_summary": find_one(case_dir, "exhibitions_image_task_t203_qa_handoff_validation_summary_*.json"),
        "qa_handoff_validation_manifest": find_one(case_dir, "exhibitions_image_task_t203_qa_handoff_validation_manifest_*.json"),
        "trial_execution_summary": find_one(case_dir, "exhibitions_image_task_t201_trial_execution_summary_*.json"),
        "trial_execution_manifest": find_one(case_dir, "exhibitions_image_task_t201_trial_execution_manifest_*.json"),
        "trial_bundle_result_csv": find_one(case_dir, "exhibitions_image_task_t201_trial_bundle_result_*.csv"),
        "trial_qa_handoff_manifest": find_one(case_dir, "exhibitions_image_task_t201_trial_qa_handoff_manifest_*.json"),
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


def mutate_case(case_dir: Path, inputs: dict[str, Path], mutate: str) -> None:
    if not mutate:
        return
    if mutate == "remove_required_file":
        inputs["trial_bundle_result_csv"].unlink(missing_ok=True)
        return
    if mutate == "cross_file_scope_mismatch":
        payload = read_json(inputs["qa_handoff_validation_summary"])
        payload["scope_hash"] = "scope_hash_mismatch_task205"
        write_json(inputs["qa_handoff_validation_summary"], payload)
        return
    if mutate == "failed_unit_mixed_in":
        fields, rows = read_csv_rows(inputs["trial_bundle_result_csv"])
        if rows:
            rows[0]["unit_status"] = "FAILED"
            rows[0]["succeeded_row_count"] = "0"
            rows[0]["failed_row_count"] = "1"
            rows[0]["deferred_row_count"] = "0"
            write_csv_rows(inputs["trial_bundle_result_csv"], fields, rows)
        ts = read_json(inputs["trial_execution_summary"])
        ts["succeeded_unit_count"] = 0
        ts["failed_unit_count"] = 1
        ts["deferred_unit_count"] = 0
        ts["executed_unit_count"] = 1
        write_json(inputs["trial_execution_summary"], ts)
        return
    if mutate == "manifest_missing_output_path":
        payload = read_json(inputs["trial_qa_handoff_manifest"])
        paths = list(payload.get("unit_result_paths") or [])
        paths.append(str(case_dir / "missing_task205_unit_result.json"))
        payload["unit_result_paths"] = paths
        write_json(inputs["trial_qa_handoff_manifest"], payload)
        return
    raise ValueError(f"unsupported_mutation:{mutate}")


def tail_text(text: str, max_lines: int = 10) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return ""
    return "\n".join(lines[-max_lines:])


def main() -> int:
    args = parse_args()
    out_root = Path(args.output_root)
    adapter_path = Path(args.adapter_path)
    fixture_manifest_path = Path(args.fixture_manifest_json)
    summary_json_path = Path(args.summary_json)
    summary_csv_path = Path(args.summary_csv)

    base_pass = Path("data/phase1_seed10/logs/task_t203_qa_handoff_fixture_runs/pass_success_bundle")
    base_hold = Path("data/phase1_seed10/logs/task_t203_qa_handoff_fixture_runs/hold_partial_or_warning_bundle")

    cases = [
        {"case_id": "ready_pass_bundle", "base_dir": str(base_pass), "mutate": "", "extra_args": [], "expected_status": "READY", "expected_exit": 0},
        {"case_id": "hold_input_bundle", "base_dir": str(base_hold), "mutate": "", "extra_args": [], "expected_status": "HOLD", "expected_exit": 20},
        {"case_id": "reject_missing_required_file", "base_dir": str(base_pass), "mutate": "remove_required_file", "extra_args": [], "expected_status": "REJECT", "expected_exit": 10},
        {"case_id": "reject_cross_file_scope_mismatch", "base_dir": str(base_pass), "mutate": "cross_file_scope_mismatch", "extra_args": [], "expected_status": "REJECT", "expected_exit": 12},
        {"case_id": "reject_failed_unit_mixed_in", "base_dir": str(base_pass), "mutate": "failed_unit_mixed_in", "extra_args": [], "expected_status": "REJECT", "expected_exit": 12},
        {"case_id": "skip_by_scope_filter", "base_dir": str(base_pass), "mutate": "", "extra_args": ["--gallery-name", "not_existing_gallery_task205"], "expected_status": "SKIP", "expected_exit": 21},
        {"case_id": "reject_manifest_missing_output_path", "base_dir": str(base_pass), "mutate": "manifest_missing_output_path", "extra_args": [], "expected_status": "REJECT", "expected_exit": 10},
        {"case_id": "internal_failure_monkeypatch", "base_dir": str(base_pass), "mutate": "", "extra_args": [], "force_internal_failure": True, "expected_status": "REJECT", "expected_exit": 30},
    ]

    fixture_manifest_payload = {"task_id": "TASK205", "generated_at": utc_now_iso(), "output_root": str(out_root), "cases": cases}
    write_json(fixture_manifest_path, fixture_manifest_payload)

    out_root.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for idx, c in enumerate(cases, start=1):
        case_id = norm_text(c["case_id"])
        case_run_id = f"t205c{idx:02d}"
        case_dir = out_root / case_id
        if case_dir.exists():
            shutil.rmtree(case_dir)
        shutil.copytree(Path(c["base_dir"]), case_dir)
        inputs = detect_inputs(case_dir)
        mutate_case(case_dir, inputs, norm_text(c.get("mutate")))

        cmd = [
            sys.executable,
            str(adapter_path),
            "--qa-handoff-validation-summary", str(inputs["qa_handoff_validation_summary"]),
            "--qa-handoff-validation-manifest", str(inputs["qa_handoff_validation_manifest"]),
            "--trial-execution-summary", str(inputs["trial_execution_summary"]),
            "--trial-execution-manifest", str(inputs["trial_execution_manifest"]),
            "--trial-bundle-result-csv", str(inputs["trial_bundle_result_csv"]),
            "--trial-qa-handoff-manifest", str(inputs["trial_qa_handoff_manifest"]),
            "--output-dir", str(case_dir),
            "--qa-runtime-bundle-id", case_run_id,
            "--write-errors-csv",
            "--write-warnings-csv",
        ]
        cmd.extend(c.get("extra_args", []))
        env = dict(os.environ)
        if c.get("force_internal_failure", False):
            env["TASK205_FORCE_INTERNAL_FAILURE"] = "1"

        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", env=env)
        actual_exit = int(proc.returncode)
        summary_path = case_dir / f"exhibitions_image_task_t205_qa_adapter_summary_{case_run_id}.json"
        actual_status = ""
        checks = {
            "summary_exists": summary_path.exists(),
            "manifest_exists": (case_dir / f"exhibitions_image_task_t205_qa_adapter_manifest_{case_run_id}.json").exists(),
            "runtime_manifest_exists": (case_dir / f"exhibitions_image_task_t205_qa_runtime_input_manifest_{case_run_id}.json").exists(),
            "report_exists": (case_dir / f"exhibitions_image_task_t205_qa_runtime_report_{case_run_id}.md").exists(),
        }
        if summary_path.exists():
            actual_status = norm_text(read_json(summary_path).get("qa_adapter_status"))

        expected_status = norm_text(c["expected_status"])
        expected_exit = int(c["expected_exit"])
        ok = actual_status == expected_status and actual_exit == expected_exit and not any(v is False for v in checks.values())

        results.append(
            {
                "case_id": case_id,
                "expected_qa_adapter_status": expected_status,
                "actual_qa_adapter_status": actual_status,
                "expected_exit_code": expected_exit,
                "actual_exit_code": actual_exit,
                "status": "passed" if ok else "failed",
                "stdout_tail": tail_text((proc.stdout or "") + "\n" + (proc.stderr or "")),
                "generated_paths": sorted([str(p) for p in case_dir.rglob("*") if p.is_file()]),
                "summary_checks": checks,
            }
        )

    total = len(results)
    passed = len([r for r in results if r["status"] == "passed"])
    failed = total - passed
    summary_payload = {"task_id": "TASK205", "generated_at": utc_now_iso(), "output_root": str(out_root), "all_passed": failed == 0, "total_cases": total, "passed_cases": passed, "failed_cases": failed, "cases": results}
    write_json(summary_json_path, summary_payload)

    summary_csv_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_csv_path.open("w", encoding="utf-8", newline="") as fp:
        fields = ["case_id", "expected_qa_adapter_status", "actual_qa_adapter_status", "expected_exit_code", "actual_exit_code", "status"]
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        for row in results:
            writer.writerow({k: row.get(k, "") for k in fields})

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
