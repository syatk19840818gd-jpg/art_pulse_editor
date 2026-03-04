#!/usr/bin/env python3
from __future__ import annotations

import argparse
import contextlib
import csv
import io
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run TASK193 fixture matrix for classification CLI exit-code/behavior validation."
    )
    parser.add_argument(
        "--manifest",
        default="data/phase1_seed10/logs/exhibitions_image_task_t193_fixture_manifest.json",
    )
    parser.add_argument(
        "--cli-path",
        default="run_exhibitions_image_classification_cli.py",
    )
    parser.add_argument(
        "--output-root",
        default="data/phase1_seed10/logs/task_t193_fixture_runs",
    )
    parser.add_argument(
        "--summary-json",
        default="data/phase1_seed10/logs/exhibitions_image_task_t193_fixture_matrix_summary.json",
    )
    parser.add_argument(
        "--summary-csv",
        default="data/phase1_seed10/logs/exhibitions_image_task_t193_fixture_matrix_summary_table.csv",
    )
    return parser.parse_args()


def tail_text(text: str, max_lines: int = 12) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return ""
    return "\n".join(lines[-max_lines:])


def read_csv_row_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8-sig", newline="") as fp:
        reader = csv.reader(fp)
        _ = next(reader, None)
        return sum(1 for _ in reader)


def read_unit_lane_counts(path: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    if not path.exists():
        return counts
    with path.open("r", encoding="utf-8-sig", newline="") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            lane = (row.get("lane") or "").strip()
            if not lane:
                continue
            counts[lane] = counts.get(lane, 0) + 1
    return counts


def build_cli_command(
    case: dict[str, Any],
    cli_path: Path,
    output_dir: Path,
    run_id: str,
) -> list[str]:
    return [
        sys.executable,
        str(cli_path),
        "--authoritative-master-csv",
        str(case["authoritative_master_csv"]),
        "--authoritative-runtime-csv",
        str(case["authoritative_runtime_csv"]),
        "--seed-eval-csv",
        str(case["seed_eval_csv"]),
        "--gallery-summary-csv",
        str(case["gallery_summary_csv"]),
        "--trial-ready-decision-csv",
        str(case["trial_ready_decision_csv"]),
        "--defer-queue-csv",
        str(case["defer_queue_csv"]),
        "--reject-queue-csv",
        str(case["reject_queue_csv"]),
        "--target-year",
        str(case.get("target_year", 2025)),
        "--output-dir",
        str(output_dir),
        "--run-id",
        run_id,
        "--write-report-md",
        "--write-manifest",
    ]


def run_internal_error_case(
    base_case: dict[str, Any],
    output_dir: Path,
    run_id: str,
) -> tuple[int, str]:
    import run_exhibitions_image_classification_cli as cli

    args_ns = argparse.Namespace(
        input_dir=str(Path(base_case["case_dir"])),
        authoritative_master_csv=str(base_case["authoritative_master_csv"]),
        authoritative_runtime_csv=str(base_case["authoritative_runtime_csv"]),
        seed_eval_csv=str(base_case["seed_eval_csv"]),
        gallery_summary_csv=str(base_case["gallery_summary_csv"]),
        trial_ready_decision_csv=str(base_case["trial_ready_decision_csv"]),
        defer_queue_csv=str(base_case["defer_queue_csv"]),
        reject_queue_csv=str(base_case["reject_queue_csv"]),
        target_year=int(base_case.get("target_year", 2025)),
        fair_slug=[],
        lane="all",
        output_dir=str(output_dir),
        run_id=run_id,
        write_report_md=False,
        write_manifest=False,
        strict=False,
        fail_on_missing_artifacts=False,
        fail_on_schema_drift=False,
        safe_max_galleries=10,
        safe_max_seeds=150,
        guard_max_galleries_min=2,
        guard_max_galleries_max=4,
        guard_max_seeds=60,
        allow_unit_size_override=False,
        dry_run=True,
    )

    original_parse_args = cli.parse_args
    original_load_csv_rows = cli.load_csv_rows
    stdout_buffer = io.StringIO()
    try:
        cli.parse_args = lambda: args_ns

        def _boom(*_args: Any, **_kwargs: Any) -> Any:
            raise RuntimeError("forced_internal_error_for_task193")

        cli.load_csv_rows = _boom
        with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stdout_buffer):
            exit_code = cli.main()
        return int(exit_code), stdout_buffer.getvalue()
    finally:
        cli.parse_args = original_parse_args
        cli.load_csv_rows = original_load_csv_rows


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest)
    cli_path = Path(args.cli_path)
    output_root = Path(args.output_root)
    summary_json_path = Path(args.summary_json)
    summary_csv_path = Path(args.summary_csv)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cases: list[dict[str, Any]] = list(manifest.get("cases", []))
    by_case_id: dict[str, dict[str, Any]] = {
        str(case.get("case_id")): case for case in cases if case.get("case_id")
    }

    output_root.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []

    for case in cases:
        case_id = str(case.get("case_id"))
        case_type = str(case.get("type", "cli"))
        expected_exit = int(case.get("expected_exit_code"))
        case_output_dir = output_root / case_id
        case_output_dir.mkdir(parents=True, exist_ok=True)
        run_id = f"task193-{case_id}"

        actual_exit = 30
        raw_output = ""
        if case_type == "internal_error":
            base_case_id = str(case.get("base_case_id", ""))
            base_case = by_case_id.get(base_case_id)
            if base_case is None:
                actual_exit = 30
                raw_output = f"internal_error_case_base_missing:{base_case_id}"
            else:
                actual_exit, raw_output = run_internal_error_case(base_case, case_output_dir, run_id)
        else:
            cmd = build_cli_command(case, cli_path, case_output_dir, run_id)
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            actual_exit = int(completed.returncode)
            raw_output = "\n".join(
                value for value in [completed.stdout or "", completed.stderr or ""] if value
            )

        generated_paths = sorted([str(path) for path in case_output_dir.glob("*") if path.is_file()])
        summary_json_candidates = [path for path in case_output_dir.glob("*classification_summary*.json")]
        summary_payload: dict[str, Any] = {}
        if summary_json_candidates:
            summary_payload = json.loads(summary_json_candidates[0].read_text(encoding="utf-8"))

        summary_checks: dict[str, Any] = {}
        checks_pass = True
        if "expected_lane_counts" in case and summary_payload:
            expected_lane_counts = dict(case["expected_lane_counts"])
            actual_lane_counts = dict(summary_payload.get("classification_counts", {}))
            lane_check = expected_lane_counts == actual_lane_counts
            summary_checks["lane_counts_match"] = lane_check
            summary_checks["expected_lane_counts"] = expected_lane_counts
            summary_checks["actual_lane_counts"] = actual_lane_counts
            checks_pass = checks_pass and lane_check

        if "expected_trial_ready_seed_total" in case and summary_payload:
            expected_trial_ready = int(case["expected_trial_ready_seed_total"])
            actual_trial_ready = int(summary_payload.get("trial_ready_seed_total", -1))
            trial_ready_check = expected_trial_ready == actual_trial_ready
            summary_checks["trial_ready_seed_total_match"] = trial_ready_check
            summary_checks["expected_trial_ready_seed_total"] = expected_trial_ready
            summary_checks["actual_trial_ready_seed_total"] = actual_trial_ready
            checks_pass = checks_pass and trial_ready_check

        unit_plan_candidates = [path for path in case_output_dir.glob("*unit_plan*.csv")]
        if "expected_unit_count" in case and unit_plan_candidates:
            expected_unit_count = int(case["expected_unit_count"])
            actual_unit_count = read_csv_row_count(unit_plan_candidates[0])
            unit_count_check = expected_unit_count == actual_unit_count
            summary_checks["unit_count_match"] = unit_count_check
            summary_checks["expected_unit_count"] = expected_unit_count
            summary_checks["actual_unit_count"] = actual_unit_count
            checks_pass = checks_pass and unit_count_check

            lane_counts = read_unit_lane_counts(unit_plan_candidates[0])
            if "expected_safe_unit_count" in case:
                expected_safe_units = int(case["expected_safe_unit_count"])
                actual_safe_units = int(lane_counts.get("Safe-But-Provenance-Gated", 0))
                safe_unit_check = expected_safe_units == actual_safe_units
                summary_checks["safe_unit_count_match"] = safe_unit_check
                summary_checks["expected_safe_unit_count"] = expected_safe_units
                summary_checks["actual_safe_unit_count"] = actual_safe_units
                checks_pass = checks_pass and safe_unit_check
            if "expected_guard_unit_count" in case:
                expected_guard_units = int(case["expected_guard_unit_count"])
                actual_guard_units = int(lane_counts.get("Guard-First-Then-Upgrade", 0))
                guard_unit_check = expected_guard_units == actual_guard_units
                summary_checks["guard_unit_count_match"] = guard_unit_check
                summary_checks["expected_guard_unit_count"] = expected_guard_units
                summary_checks["actual_guard_unit_count"] = actual_guard_units
                checks_pass = checks_pass and guard_unit_check

        exit_match = expected_exit == actual_exit
        status = "passed" if (exit_match and checks_pass) else "failed"
        results.append(
            {
                "case_id": case_id,
                "expected_exit_code": expected_exit,
                "actual_exit_code": actual_exit,
                "status": status,
                "stdout_tail": tail_text(raw_output),
                "generated_paths": generated_paths,
                "summary_checks": summary_checks,
            }
        )

    total_cases = len(results)
    passed_cases = len([result for result in results if result["status"] == "passed"])
    failed_cases = total_cases - passed_cases
    all_passed = failed_cases == 0

    summary_payload = {
        "task_id": "TASK193",
        "generated_at": utc_now_iso(),
        "manifest_path": str(manifest_path),
        "cli_path": str(cli_path),
        "output_root": str(output_root),
        "all_passed": all_passed,
        "total_cases": total_cases,
        "passed_cases": passed_cases,
        "failed_cases": failed_cases,
        "cases": results,
    }

    summary_json_path.parent.mkdir(parents=True, exist_ok=True)
    summary_json_path.write_text(json.dumps(summary_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    summary_csv_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_csv_path.open("w", encoding="utf-8", newline="") as fp:
        fieldnames = [
            "case_id",
            "expected_exit_code",
            "actual_exit_code",
            "status",
            "generated_paths_count",
        ]
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "case_id": result["case_id"],
                    "expected_exit_code": result["expected_exit_code"],
                    "actual_exit_code": result["actual_exit_code"],
                    "status": result["status"],
                    "generated_paths_count": len(result.get("generated_paths", [])),
                }
            )

    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
