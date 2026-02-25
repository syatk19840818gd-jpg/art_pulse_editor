#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

DEFAULT_SEARCH_DIR = Path("data/phase1_seed10/derived/answer")
DEFAULT_GLOB = "artists_answer_qa_daily_recovery_retry_run_report_rollup_*_retry_manifest.json"
DELEGATE_SCRIPT = Path("run_artists_answer_qa_daily_recovery_retry_run_from_rollup_manifest.py")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run retry runs from retry-run-report-rollup retry manifest. "
            "This is a thin wrapper over run_artists_answer_qa_daily_recovery_retry_run_from_rollup_manifest.py."
        )
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--retry-manifest", default="", help="retry manifest path")
    group.add_argument("--latest", action="store_true", help="resolve latest retry manifest")
    parser.add_argument(
        "--search-dir",
        default=str(DEFAULT_SEARCH_DIR),
        help=f"search directory for --latest (default: {DEFAULT_SEARCH_DIR})",
    )
    parser.add_argument(
        "--glob",
        default=DEFAULT_GLOB,
        help=f"glob for --latest (default: {DEFAULT_GLOB})",
    )
    parser.add_argument("--output-json", default="", help="optional output summary path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not DELEGATE_SCRIPT.exists():
        print(f"[ERROR] delegate_script_not_found:{DELEGATE_SCRIPT}")
        return 1

    cmd: list[str] = [sys.executable, str(DELEGATE_SCRIPT)]
    if args.retry_manifest:
        cmd.extend(["--retry-manifest", args.retry_manifest])
    else:
        cmd.append("--latest")
        cmd.extend(["--search-dir", args.search_dir, "--glob", args.glob])

    if args.output_json:
        cmd.extend(["--output-json", args.output_json])

    print(f"[START] retry_run_from_retry_run_report_rollup_retry_manifest delegate: {' '.join(cmd)}")
    completed = subprocess.run(cmd, check=False)
    print(
        "[DONE] retry_run_from_retry_run_report_rollup_retry_manifest "
        f"delegate_exit_code={completed.returncode}"
    )
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
