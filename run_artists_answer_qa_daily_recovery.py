#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

QA_SMOKE_SCRIPT = Path("run_artists_answer_qa_smoke.py")
BATCH_REPORT_SCRIPT = Path("run_artists_answer_qa_batch_report.py")
RETRY_MANIFEST_SCRIPT = Path("run_artists_answer_qa_retry_manifest.py")
RETRY_RUN_SCRIPT = Path("run_artists_answer_qa_retry_run.py")
RETRY_RUN_REPORT_SCRIPT = Path("run_artists_answer_qa_retry_run_report.py")

DEFAULT_SUMMARY_DIR = Path("data/phase1_seed10/derived/answer")
SOURCE_CLI = "run_artists_answer_qa_daily_recovery.py"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def utc_timestamp_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"json_not_object:{path}")
    return obj


def tail_lines(text: str, max_lines: int = 20) -> str:
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text
    return "\n".join(lines[-max_lines:])


def run_step(name: str, cmd: list[str]) -> dict[str, Any]:
    completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return {
        "name": name,
        "command": cmd,
        "exit_code": int(completed.returncode),
        "status": "ok" if int(completed.returncode) == 0 else "failed",
        "output_paths": {},
        "stdout_tail": tail_lines(completed.stdout),
        "stderr_tail": tail_lines(completed.stderr),
    }


def build_skipped_step(name: str, reason: str) -> dict[str, Any]:
    return {
        "name": name,
        "command": [],
        "exit_code": 0,
        "status": "skipped",
        "output_paths": {},
        "stdout_tail": "",
        "stderr_tail": "",
        "skip_reason": reason,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run artists QA daily recovery pipeline in one shot: "
            "batch smoke -> batch report -> retry manifest -> retry run -> retry run report."
        )
    )
    parser.add_argument("--batch-manifest", required=True, help="input batch manifest path")
    parser.add_argument("--output-json", default="", help="optional daily summary output path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    started_at = utc_now_iso()
    timestamp = utc_timestamp_compact()

    summary_path = (
        Path(args.output_json).resolve()
        if args.output_json
        else (DEFAULT_SUMMARY_DIR / f"artists_answer_qa_daily_recovery_summary_{timestamp}.json").resolve()
    )
    summary_stem = summary_path.stem

    batch_manifest_path = Path(args.batch_manifest).resolve()

    daily_summary: dict[str, Any] = {
        "started_at": started_at,
        "completed_at": None,
        "source_cli": SOURCE_CLI,
        "batch_manifest_path": str(batch_manifest_path),
        "all_passed": False,
        "wrapper_exit_code": 1,
        "steps": [],
        "notes": [],
        "errors": [],
        "output_paths": {
            "daily_summary_json": str(summary_path),
        },
    }

    def finalize(exit_code: int) -> int:
        daily_summary["completed_at"] = utc_now_iso()
        daily_summary["wrapper_exit_code"] = int(exit_code)
        write_json(summary_path, daily_summary)
        print(
            "[DONE] artists QA daily recovery complete. "
            f"all_passed={daily_summary['all_passed']} wrapper_exit_code={daily_summary['wrapper_exit_code']}"
        )
        print(f"[DONE] summary={summary_path}")
        return int(exit_code)

    if not batch_manifest_path.exists():
        daily_summary["errors"].append(f"batch_manifest_not_found:{batch_manifest_path}")
        print(f"[ERROR] batch_manifest_not_found:{batch_manifest_path}")
        return finalize(1)

    batch_smoke_summary_path = summary_path.with_name(f"{summary_stem}_batch_smoke_summary.json")
    batch_report_path = summary_path.with_name(f"{summary_stem}_batch_report.json")
    retry_manifest_path = summary_path.with_name(f"{summary_stem}_retry_manifest.json")
    retry_run_summary_path = summary_path.with_name(f"{summary_stem}_retry_run_summary.json")
    retry_run_report_path = summary_path.with_name(f"{summary_stem}_retry_run_report.json")

    # Step 1: batch smoke
    step1_cmd = [
        sys.executable,
        str(QA_SMOKE_SCRIPT),
        "--batch-manifest",
        str(batch_manifest_path),
        "--output-json",
        str(batch_smoke_summary_path),
    ]
    step1 = run_step("batch_smoke", step1_cmd)
    step1["output_paths"]["batch_smoke_summary_path"] = str(batch_smoke_summary_path)

    batch_cases_jsonl_path: Path | None = None
    if batch_smoke_summary_path.exists():
        try:
            batch_smoke_summary = load_json(batch_smoke_summary_path)
            raw_cases_path = batch_smoke_summary.get("batch_cases_jsonl_path")
            if isinstance(raw_cases_path, str) and raw_cases_path.strip():
                batch_cases_jsonl_path = Path(raw_cases_path).resolve()
            else:
                output_paths = batch_smoke_summary.get("output_paths")
                if isinstance(output_paths, dict):
                    raw_cases_path = output_paths.get("batch_cases_jsonl_path")
                    if isinstance(raw_cases_path, str) and raw_cases_path.strip():
                        batch_cases_jsonl_path = Path(raw_cases_path).resolve()
        except Exception as exc:  # noqa: BLE001
            daily_summary["errors"].append(f"batch_smoke_summary_parse_failed:{exc}")

    if batch_cases_jsonl_path is not None:
        step1["output_paths"]["batch_cases_jsonl_path"] = str(batch_cases_jsonl_path)

    if step1["exit_code"] != 0:
        step1["status"] = "warning"
        daily_summary["notes"].append("batch_smoke_nonzero_detected")

    if batch_cases_jsonl_path is None or not batch_cases_jsonl_path.exists():
        daily_summary["errors"].append("batch_cases_jsonl_path_missing_after_batch_smoke")
        step1["status"] = "failed"
    daily_summary["steps"].append(step1)

    # Step 2: batch report
    if batch_cases_jsonl_path is None or not batch_cases_jsonl_path.exists():
        step2 = build_skipped_step(
            "batch_report",
            "batch_cases_jsonl_missing",
        )
        daily_summary["steps"].append(step2)
    else:
        step2_cmd = [
            sys.executable,
            str(BATCH_REPORT_SCRIPT),
            "--cases-jsonl",
            str(batch_cases_jsonl_path),
            "--output-json",
            str(batch_report_path),
        ]
        step2 = run_step("batch_report", step2_cmd)
        step2["output_paths"]["batch_report_path"] = str(batch_report_path)
        if not batch_report_path.exists():
            daily_summary["errors"].append("batch_report_output_missing")
            step2["status"] = "failed"
        daily_summary["steps"].append(step2)

    # Step 3: retry manifest
    if batch_cases_jsonl_path is None or not batch_cases_jsonl_path.exists():
        step3 = build_skipped_step(
            "retry_manifest_build",
            "batch_cases_jsonl_missing",
        )
        daily_summary["steps"].append(step3)
    else:
        step3_cmd = [
            sys.executable,
            str(RETRY_MANIFEST_SCRIPT),
            "--cases-jsonl",
            str(batch_cases_jsonl_path),
            "--output-manifest",
            str(retry_manifest_path),
        ]
        step3 = run_step("retry_manifest_build", step3_cmd)
        step3["output_paths"]["retry_manifest_path"] = str(retry_manifest_path)
        if not retry_manifest_path.exists():
            daily_summary["errors"].append("retry_manifest_output_missing")
            step3["status"] = "failed"
        daily_summary["steps"].append(step3)

    # Step 4: retry run
    if not retry_manifest_path.exists():
        step4 = build_skipped_step(
            "retry_run",
            "retry_manifest_missing",
        )
        daily_summary["steps"].append(step4)
    else:
        step4_cmd = [
            sys.executable,
            str(RETRY_RUN_SCRIPT),
            "--retry-manifest",
            str(retry_manifest_path),
            "--output-summary",
            str(retry_run_summary_path),
        ]
        step4 = run_step("retry_run", step4_cmd)
        step4["output_paths"]["retry_run_summary_path"] = str(retry_run_summary_path)
        if not retry_run_summary_path.exists():
            daily_summary["errors"].append("retry_run_summary_missing")
            step4["status"] = "failed"
        daily_summary["steps"].append(step4)

    # Step 5: retry run report
    if not retry_run_summary_path.exists():
        step5 = build_skipped_step(
            "retry_run_report",
            "retry_run_summary_missing",
        )
        daily_summary["steps"].append(step5)
    else:
        step5_cmd = [
            sys.executable,
            str(RETRY_RUN_REPORT_SCRIPT),
            "--summary-path",
            str(retry_run_summary_path),
            "--output-json",
            str(retry_run_report_path),
        ]
        step5 = run_step("retry_run_report", step5_cmd)
        step5["output_paths"]["retry_run_report_path"] = str(retry_run_report_path)
        if not retry_run_report_path.exists():
            daily_summary["errors"].append("retry_run_report_output_missing")
            step5["status"] = "failed"
        daily_summary["steps"].append(step5)

    retry_run_wrapper_exit_code: int | None = None
    retry_run_noop = False
    if retry_run_summary_path.exists():
        try:
            retry_run_summary = load_json(retry_run_summary_path)
            raw_wrapper_exit = retry_run_summary.get("wrapper_exit_code")
            if isinstance(raw_wrapper_exit, int):
                retry_run_wrapper_exit_code = raw_wrapper_exit
            if retry_run_summary.get("retry_run_mode") == "noop_empty_retry_manifest":
                retry_run_noop = True
                daily_summary["notes"].append("retry_run_noop_empty_retry_manifest")
            child_batch_summary_path = retry_run_summary.get("child_batch_summary_path")
            child_batch_cases_jsonl_path = retry_run_summary.get("child_batch_cases_jsonl_path")
            if isinstance(child_batch_summary_path, str) and child_batch_summary_path.strip():
                daily_summary["output_paths"]["child_batch_summary_path"] = child_batch_summary_path
            if isinstance(child_batch_cases_jsonl_path, str) and child_batch_cases_jsonl_path.strip():
                daily_summary["output_paths"]["child_batch_cases_jsonl_path"] = child_batch_cases_jsonl_path
        except Exception as exc:  # noqa: BLE001
            daily_summary["errors"].append(f"retry_run_summary_parse_failed:{exc}")

    daily_summary["retry_run_wrapper_exit_code"] = retry_run_wrapper_exit_code
    daily_summary["retry_run_noop"] = retry_run_noop
    daily_summary["output_paths"].update(
        {
            "batch_smoke_summary_path": str(batch_smoke_summary_path),
            "batch_report_path": str(batch_report_path),
            "retry_manifest_path": str(retry_manifest_path),
            "retry_run_summary_path": str(retry_run_summary_path),
            "retry_run_report_path": str(retry_run_report_path),
        }
    )

    # Final policy:
    # - batch_smoke can be non-zero and still continue (recovery target)
    # - all_passed requires no orchestration errors and retry run finished with wrapper_exit_code==0
    hard_failed_steps = [
        s
        for s in daily_summary["steps"]
        if isinstance(s, dict) and s.get("status") == "failed" and s.get("name") != "batch_smoke"
    ]

    all_passed = (
        len(daily_summary["errors"]) == 0
        and len(hard_failed_steps) == 0
        and retry_run_wrapper_exit_code == 0
    )
    daily_summary["all_passed"] = all_passed

    if all_passed:
        daily_summary["notes"].append("daily_recovery_passed")
        return finalize(0)

    if retry_run_wrapper_exit_code is not None and retry_run_wrapper_exit_code != 0:
        daily_summary["notes"].append("retry_run_not_fully_recovered")

    return finalize(1)


if __name__ == "__main__":
    raise SystemExit(main())
