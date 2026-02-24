#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from phase1_guard_common import resolve_logs_dir, utc_now_iso, utc_timestamp_compact, write_summary_json

DEFAULT_LOGS_DIR = "data/phase1_seed10/logs"
OUTPUT_TEMPLATE = "phase1_guard_all_matrices_{timestamp}.json"
SOURCE_CLI = "run_phase1_guard_all_matrices.py"

MATRIX_SPECS = [
    {
        "name": "lint",
        "script": "run_phase1_guard_lint_fixture_matrix.py",
        "summary_template": "phase1_guard_lint_fixture_matrix_{timestamp}.json",
    },
    {
        "name": "category",
        "script": "run_phase1_guard_category_fixture_matrix.py",
        "summary_template": "phase1_guard_category_fixture_matrix_{timestamp}.json",
    },
    {
        "name": "history",
        "script": "run_phase1_guard_fixture_matrix.py",
        "summary_template": "phase1_guard_fixture_matrix_{timestamp}.json",
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run all Phase1 guard matrices (lint/category/history) sequentially and "
            "write one integrated summary."
        )
    )
    parser.add_argument(
        "--logs-dir",
        default=DEFAULT_LOGS_DIR,
        help=f"directory for matrix and integrated summaries (default: {DEFAULT_LOGS_DIR})",
    )
    parser.add_argument(
        "--output-json",
        default="",
        help="optional integrated summary output path (default: <logs-dir>/phase1_guard_all_matrices_<timestamp>.json)",
    )
    parser.add_argument("--pretty", action="store_true", help="print per-matrix summary lines")
    parser.add_argument("--skip-lint", action="store_true", help="skip lint matrix")
    parser.add_argument("--skip-category", action="store_true", help="skip category matrix")
    parser.add_argument("--skip-history", action="store_true", help="skip history matrix")
    return parser.parse_args()


def _tail_text(text: str, max_chars: int = 1200) -> str:
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def _selected_matrix_names(args: argparse.Namespace) -> set[str]:
    selected = {"lint", "category", "history"}
    if args.skip_lint:
        selected.discard("lint")
    if args.skip_category:
        selected.discard("category")
    if args.skip_history:
        selected.discard("history")
    return selected


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parent
    started_at = utc_now_iso()
    timestamp = utc_timestamp_compact()

    logs_dir = resolve_logs_dir(args.logs_dir)
    output_json = (
        resolve_logs_dir(args.output_json)
        if args.output_json
        else logs_dir / OUTPUT_TEMPLATE.format(timestamp=timestamp)
    )

    selected_names = _selected_matrix_names(args)
    warnings: list[str] = []
    matrix_results: list[dict[str, Any]] = []
    execution_order: list[str] = []

    if not selected_names:
        warnings.append("no_matrix_selected:all_skip_flags_enabled")

    for spec in MATRIX_SPECS:
        name = spec["name"]
        if name not in selected_names:
            continue

        execution_order.append(name)
        matrix_summary_path = logs_dir / spec["summary_template"].format(timestamp=timestamp)
        command = [
            sys.executable,
            str((repo_root / spec["script"]).resolve()),
            "--logs-dir",
            str(logs_dir),
            "--output-path",
            str(matrix_summary_path),
        ]

        start_monotonic = time.monotonic()
        matrix_started = utc_now_iso()
        stdout_text = ""
        stderr_text = ""
        error_text = None

        try:
            proc = subprocess.run(
                command,
                cwd=repo_root,
                check=False,
                capture_output=True,
                text=True,
            )
            exit_code = int(proc.returncode)
            stdout_text = proc.stdout or ""
            stderr_text = proc.stderr or ""
        except Exception as exc:  # pragma: no cover - safety path
            exit_code = 1
            error_text = f"wrapper_launch_error:{exc}"
            warnings.append(f"{name}:wrapper_launch_error")

        duration_seconds = round(time.monotonic() - start_monotonic, 3)
        matrix_finished = utc_now_iso()
        pass_fail = "pass" if exit_code == 0 else "fail"

        if not matrix_summary_path.exists():
            warnings.append(f"{name}:summary_not_found:{matrix_summary_path}")
            summary_path_value = None
        else:
            summary_path_value = str(matrix_summary_path)

        matrix_result = {
            "name": name,
            "command": command,
            "expected_exit_code": 0,
            "exit_code": exit_code,
            "actual_exit_code": exit_code,
            "pass_fail": pass_fail,
            "summary_path": summary_path_value,
            "stdout_tail": _tail_text(stdout_text),
            "stderr_tail": _tail_text(stderr_text),
            "error": error_text,
            "started_at_utc": matrix_started,
            "finished_at_utc": matrix_finished,
            "duration_seconds": duration_seconds,
        }
        matrix_results.append(matrix_result)

        if args.pretty:
            print(
                f"[MATRIX] {name} expected=0 actual={exit_code} "
                f"result={'OK' if pass_fail == 'pass' else 'NG'} "
                f"summary={summary_path_value}"
            )

    any_fail = any(item.get("pass_fail") != "pass" for item in matrix_results)
    all_passed = (len(matrix_results) > 0) and (not any_fail)
    if not matrix_results:
        all_passed = False
        warnings.append("no_matrix_executed")

    wrapper_exit_code = 0 if all_passed else 1
    finished_at = utc_now_iso()

    payload = {
        "all_passed": all_passed,
        "wrapper_exit_code": wrapper_exit_code,
        "started_at_utc": started_at,
        "finished_at_utc": finished_at,
        "source_cli": SOURCE_CLI,
        "execution_order": execution_order,
        "executed_matrices": len(matrix_results),
        "matrices": matrix_results,
        "warnings": warnings,
        "matrix_wrapper_exit_code_meaning": {"0": "matrix_pass", "1": "matrix_fail"},
        "wrapper_exit_code_meaning": {"0": "all_pass", "1": "any_fail"},
    }
    write_summary_json(output_json, payload)

    if not args.pretty:
        for row in matrix_results:
            print(
                f"[MATRIX] {row['name']} expected=0 actual={row['actual_exit_code']} "
                f"result={'OK' if row['pass_fail'] == 'pass' else 'NG'}"
            )

    print(
        f"[ALL] executed={len(matrix_results)} all_passed={'true' if all_passed else 'false'} "
        f"wrapper_exit={wrapper_exit_code}"
    )
    print(f"[ALL] summary={output_json}")
    return wrapper_exit_code


if __name__ == "__main__":
    raise SystemExit(main())
