#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from qa_artifact_utils import resolve_latest_artifact

DEFAULT_SEARCH_DIR = Path("data/phase1_seed10/derived/answer")
DELEGATE_SCRIPT = Path("run_aqa_retry_run_report_rollup_retry_run.py")
INPUT_ARTIFACT_KIND = "retry_run_daily_chain_recovery_chain_report_rollup_retry_manifest"
SOURCE_CLI = "run_aqa_retry_run_daily_chain_recovery_chain_retry_run_from_report_rollup_manifest.py"
_SUMMARY_RE = re.compile(r"^\[DONE\]\s+summary=(.+)$", re.MULTILINE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run retry-run from recovery-chain report-rollup retry manifest. "
            "This is a thin wrapper over run_aqa_retry_run_report_rollup_retry_run.py."
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
    parser.add_argument("--glob", default="", help="optional glob override for --latest")
    parser.add_argument("--output-json", default="", help="optional child summary path")
    return parser.parse_args()


def _extract_child_summary_path(text: str) -> str | None:
    match = _SUMMARY_RE.search(text)
    if not match:
        return None
    return match.group(1).strip() or None


def run() -> int:
    args = parse_args()

    if not DELEGATE_SCRIPT.exists():
        print(f"[ERROR] delegate_script_not_found:{DELEGATE_SCRIPT}")
        return 1

    if args.retry_manifest:
        retry_manifest_path = Path(args.retry_manifest).resolve()
    else:
        latest_manifest, latest_error = resolve_latest_artifact(
            Path(args.search_dir).resolve(),
            INPUT_ARTIFACT_KIND,
            glob_pattern=args.glob or None,
        )
        if latest_error:
            print(f"[ERROR] {latest_error}")
            return 1
        assert latest_manifest is not None
        retry_manifest_path = latest_manifest

    delegated_cmd: list[str] = [
        sys.executable,
        str(DELEGATE_SCRIPT),
        "--retry-manifest",
        str(retry_manifest_path),
    ]
    if args.output_json:
        delegated_cmd.extend(["--output-json", args.output_json])

    print(f"[START] {SOURCE_CLI}")
    print(f"[INFO] resolved_retry_manifest_path={retry_manifest_path}")
    print(f"[INFO] delegated_command={' '.join(delegated_cmd)}")

    completed = subprocess.run(delegated_cmd, capture_output=True, text=True, check=False)
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, file=sys.stderr, end="")

    child_summary_path = _extract_child_summary_path(completed.stdout or "")
    if child_summary_path:
        print(f"[INFO] child_summary_path={child_summary_path}")

    print(f"[DONE] {SOURCE_CLI} child_exit_code={completed.returncode}")
    return int(completed.returncode)


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
