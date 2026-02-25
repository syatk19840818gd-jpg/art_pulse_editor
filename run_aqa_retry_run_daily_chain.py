#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from qa_artifact_utils import build_artifact_header, utc_now_iso, utc_timestamp_compact

DEFAULT_SEARCH_DIR = Path("data/phase1_seed10/derived/answer")
DEFAULT_OUTPUT_DIR = Path("data/phase1_seed10/derived/answer")
DEFAULT_LATEST_N = 1
SOURCE_CLI = "run_aqa_retry_run_daily_chain.py"
OUTPUT_ARTIFACT_KIND = "retry_run_daily_chain_summary"

STEP1_CLI = Path("run_aqa_retry_run_report_rollup.py")
STEP2_CLI = Path("run_aqa_retry_run_report_rollup_manifest.py")
STEP3_CLI = Path("run_aqa_retry_run_report_rollup_retry_run.py")
STEP4_CLI = Path("run_aqa_retry_run_report_rollup_retry_run_report.py")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _tail_lines(text: str, max_lines: int = 30) -> str:
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text
    return "\n".join(lines[-max_lines:])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run TASK85~88 retry-run flow in one shot: rollup -> retry manifest -> retry run -> retry run report."
        )
    )
    parser.add_argument("--latest", action="store_true", help="use latest artifacts from search dir (required)")
    parser.add_argument(
        "--search-dir",
        default=str(DEFAULT_SEARCH_DIR),
        help=f"search directory (default: {DEFAULT_SEARCH_DIR})",
    )
    parser.add_argument(
        "--latest-n",
        type=int,
        default=DEFAULT_LATEST_N,
        help=f"latest-n for rollup step (default: {DEFAULT_LATEST_N})",
    )
    parser.add_argument("--output-json", default="", help="optional output summary path")
    return parser.parse_args()


def _run_step(
    *,
    name: str,
    cmd: list[str],
    output_paths: dict[str, str],
) -> dict[str, Any]:
    completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
    exit_code = int(completed.returncode)
    return {
        "name": name,
        "command": cmd,
        "exit_code": exit_code,
        "status": "ok" if exit_code == 0 else "failed",
        "output_paths": output_paths,
        "stdout_tail": _tail_lines(completed.stdout),
        "stderr_tail": _tail_lines(completed.stderr),
    }


def _build_skipped_step(name: str, skip_reason: str) -> dict[str, Any]:
    return {
        "name": name,
        "command": [],
        "exit_code": None,
        "status": "skipped",
        "skip_reason": skip_reason,
        "output_paths": {},
        "stdout_tail": "",
        "stderr_tail": "",
    }


def main() -> int:
    args = parse_args()
    if not args.latest:
        print("[ERROR] latest_mode_required:use_--latest")
        return 1

    for required in (STEP1_CLI, STEP2_CLI, STEP3_CLI, STEP4_CLI):
        if not required.exists():
            print(f"[ERROR] required_cli_not_found:{required}")
            return 1

    ts = utc_timestamp_compact()
    search_dir = Path(args.search_dir).resolve()
    output_summary_path = (
        Path(args.output_json).resolve()
        if args.output_json
        else (DEFAULT_OUTPUT_DIR / f"artists_answer_qa_retry_run_daily_chain_summary_{ts}.json").resolve()
    )

    rollup_path = search_dir / f"artists_answer_qa_daily_recovery_retry_run_report_rollup_{ts}.json"
    retry_manifest_path = search_dir / f"artists_answer_qa_daily_recovery_retry_run_report_rollup_{ts}_retry_manifest.json"
    retry_run_summary_path = search_dir / f"artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_{ts}.json"
    retry_run_report_path = search_dir / f"artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_{ts}_report.json"

    summary: dict[str, Any] = {
        **build_artifact_header(OUTPUT_ARTIFACT_KIND, generated_by=SOURCE_CLI),
        "source_cli": SOURCE_CLI,
        "started_at": utc_now_iso(),
        "completed_at": None,
        "search_dir": str(search_dir),
        "latest_n": max(1, int(args.latest_n)),
        "steps": [],
        "all_passed": False,
        "wrapper_exit_code": 1,
        "notes": [],
        "output_summary_path": str(output_summary_path),
    }

    step1_cmd = [
        sys.executable,
        str(STEP1_CLI),
        "--latest-n",
        str(max(1, int(args.latest_n))),
        "--search-dir",
        str(search_dir),
        "--output-json",
        str(rollup_path),
    ]
    step1 = _run_step(name="retry_run_report_rollup", cmd=step1_cmd, output_paths={"rollup_json": str(rollup_path)})
    summary["steps"].append(step1)

    if step1["exit_code"] != 0:
        summary["steps"].append(_build_skipped_step("retry_manifest_from_rollup", "upstream_failed:retry_run_report_rollup"))
        summary["steps"].append(_build_skipped_step("retry_run_from_manifest", "upstream_failed:retry_run_report_rollup"))
        summary["steps"].append(_build_skipped_step("retry_run_report", "upstream_failed:retry_run_report_rollup"))
        summary["notes"].append("chain_aborted_after_step:retry_run_report_rollup")
    else:
        step2_cmd = [
            sys.executable,
            str(STEP2_CLI),
            "--rollup-json",
            str(rollup_path),
            "--output-manifest",
            str(retry_manifest_path),
        ]
        step2 = _run_step(
            name="retry_manifest_from_rollup",
            cmd=step2_cmd,
            output_paths={"retry_manifest_json": str(retry_manifest_path), "source_rollup_json": str(rollup_path)},
        )
        summary["steps"].append(step2)

        if step2["exit_code"] != 0:
            summary["steps"].append(_build_skipped_step("retry_run_from_manifest", "upstream_failed:retry_manifest_from_rollup"))
            summary["steps"].append(_build_skipped_step("retry_run_report", "upstream_failed:retry_manifest_from_rollup"))
            summary["notes"].append("chain_aborted_after_step:retry_manifest_from_rollup")
        else:
            step3_cmd = [
                sys.executable,
                str(STEP3_CLI),
                "--retry-manifest",
                str(retry_manifest_path),
                "--output-json",
                str(retry_run_summary_path),
            ]
            step3 = _run_step(
                name="retry_run_from_manifest",
                cmd=step3_cmd,
                output_paths={
                    "retry_manifest_json": str(retry_manifest_path),
                    "retry_run_summary_json": str(retry_run_summary_path),
                },
            )
            summary["steps"].append(step3)

            # retry-run step may fail because failed runs remain, but report step should still run.
            step4_cmd = [
                sys.executable,
                str(STEP4_CLI),
                "--summary-path",
                str(retry_run_summary_path),
                "--output-json",
                str(retry_run_report_path),
            ]
            step4 = _run_step(
                name="retry_run_report",
                cmd=step4_cmd,
                output_paths={
                    "retry_run_summary_json": str(retry_run_summary_path),
                    "retry_run_report_json": str(retry_run_report_path),
                },
            )
            summary["steps"].append(step4)

    # Treat chain pass as all steps that actually ran succeeded.
    runnable_steps = [s for s in summary["steps"] if s.get("status") != "skipped"]
    all_passed = len(runnable_steps) > 0 and all((s.get("exit_code") == 0) for s in runnable_steps)
    summary["all_passed"] = all_passed
    summary["wrapper_exit_code"] = 0 if all_passed else 1

    if all_passed:
        summary["notes"].append("daily_chain_passed")
    else:
        summary["notes"].append("daily_chain_has_failed_steps")

    summary["completed_at"] = utc_now_iso()
    write_json(output_summary_path, summary)

    print(
        "[DONE] artists_answer_qa_retry_run_daily_chain "
        f"all_passed={summary['all_passed']} "
        f"wrapper_exit_code={summary['wrapper_exit_code']} "
        f"summary={output_summary_path}"
    )
    return int(summary["wrapper_exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
