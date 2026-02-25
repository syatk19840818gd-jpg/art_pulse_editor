#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from qa_artifact_utils import (
    build_artifact_header,
    list_candidate_artifacts,
    utc_timestamp_compact,
)

DEFAULT_SEARCH_DIR = Path("data/phase1_seed10/derived/answer")
DEFAULT_LATEST_N = 20
SOURCE_CLI = "run_aqa_retry_run_daily_chain_recovery_chain_report_rollup.py"
INPUT_ARTIFACT_KIND = "retry_run_daily_chain_recovery_chain_report"
OUTPUT_ARTIFACT_KIND = "retry_run_daily_chain_recovery_chain_report_rollup"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"json_not_object:{path}")
    return obj


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        if isinstance(item, str):
            text = item.strip()
            if text:
                out.append(text)
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Roll up retry-run daily-chain recovery-chain reports and extract failed-run trends."
        )
    )
    parser.add_argument(
        "--search-dir",
        default=str(DEFAULT_SEARCH_DIR),
        help=f"search directory (default: {DEFAULT_SEARCH_DIR})",
    )
    parser.add_argument(
        "--glob",
        default="",
        help="optional glob override for report files",
    )
    parser.add_argument(
        "--latest-n",
        type=int,
        default=DEFAULT_LATEST_N,
        help=f"max number of latest reports (default: {DEFAULT_LATEST_N})",
    )
    parser.add_argument("--output-json", default="", help="optional rollup output path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    search_dir = Path(args.search_dir).resolve()
    latest_n = max(1, int(args.latest_n))

    output_path = (
        Path(args.output_json).resolve()
        if args.output_json
        else (
            search_dir
            / f"artists_answer_qa_retry_run_daily_chain_recovery_chain_report_rollup_{utc_timestamp_compact()}.json"
        ).resolve()
    )

    rollup: dict[str, Any] = {
        **build_artifact_header(OUTPUT_ARTIFACT_KIND, generated_by=SOURCE_CLI),
        "source_cli": SOURCE_CLI,
        "search_dir": str(search_dir),
        "glob": args.glob,
        "latest_n": latest_n,
        "total_reports": 0,
        "failed_run_count": 0,
        "failed_runs": [],
        "source_report_paths": [],
        "warnings": [],
        "rollup_exit_code": 1,
        "exit_reason": "invalid_input_or_not_found",
    }

    try:
        report_paths = list_candidate_artifacts(
            search_dir,
            INPUT_ARTIFACT_KIND,
            glob_pattern=args.glob or None,
            latest_n=latest_n,
        )
    except Exception as exc:  # noqa: BLE001
        message = f"candidate_listing_failed:{exc}"
        rollup["warnings"].append(message)
        write_json(output_path, rollup)
        print(f"[ERROR] {message}")
        print(f"[DONE] rollup={output_path}")
        return 1

    if not report_paths:
        message = f"recovery_chain_reports_not_found:{search_dir}:{args.glob or '[default_glob]'}"
        rollup["warnings"].append(message)
        write_json(output_path, rollup)
        print(f"[ERROR] {message}")
        print(f"[DONE] rollup={output_path}")
        return 1

    rollup["source_report_paths"] = [str(path) for path in report_paths]

    failed_runs: list[dict[str, Any]] = []
    valid_reports = 0

    for report_path in report_paths:
        try:
            report_obj = load_json(report_path)
        except Exception as exc:  # noqa: BLE001
            rollup["warnings"].append(f"report_load_failed:{report_path}:{exc}")
            continue

        valid_reports += 1

        failed_steps = report_obj.get("failed_steps")
        failed_step_names: list[str] = []
        failed_step_count = 0
        if isinstance(failed_steps, list):
            for step in failed_steps:
                if isinstance(step, dict):
                    failed_step_count += 1
                    failed_step_names.append(str(step.get("name") or "unknown"))

        all_passed = report_obj.get("all_passed")
        wrapper_exit_code = _as_int(report_obj.get("wrapper_exit_code"))
        has_failure = bool(
            failed_step_count > 0
            or all_passed is False
            or (wrapper_exit_code is not None and wrapper_exit_code != 0)
        )
        if not has_failure:
            continue

        failed_runs.append(
            {
                "report_path": str(report_path),
                "summary_path": report_obj.get("summary_path"),
                "failed_step_count": failed_step_count,
                "failed_step_names": failed_step_names,
                "child_summary_paths_to_check": _as_string_list(
                    report_obj.get("child_summary_paths_to_check")
                ),
                "all_passed": all_passed,
                "wrapper_exit_code": report_obj.get("wrapper_exit_code"),
            }
        )

    rollup["total_reports"] = valid_reports
    rollup["failed_run_count"] = len(failed_runs)
    rollup["failed_runs"] = failed_runs

    if valid_reports == 0:
        rollup["warnings"].append("no_valid_report_json_loaded")
        write_json(output_path, rollup)
        print("[ERROR] no_valid_report_json_loaded")
        print(f"[DONE] rollup={output_path}")
        return 1

    rollup["rollup_exit_code"] = 0
    rollup["exit_reason"] = "rollup_generated"
    write_json(output_path, rollup)

    print(
        "[ROLLUP] "
        f"total_reports={rollup['total_reports']} "
        f"failed_run_count={rollup['failed_run_count']} "
        f"latest_n={latest_n}"
    )
    if failed_runs:
        print("[ROLLUP] failed_runs:")
        for run in failed_runs:
            print(
                f"  - summary_path={run.get('summary_path')} "
                f"failed_step_count={run.get('failed_step_count')} "
                f"failed_step_names={run.get('failed_step_names')}"
            )
    else:
        print("[ROLLUP] failed_runs: none")

    print(f"[DONE] rollup={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
