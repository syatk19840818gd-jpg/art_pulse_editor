#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

TARGET_SCRIPT = Path(
    "run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_retry_manifest_report.py"
)


def main() -> int:
    if not TARGET_SCRIPT.exists():
        print(f"[ERROR] target_script_not_found:{TARGET_SCRIPT}")
        return 1
    cmd = [sys.executable, str(TARGET_SCRIPT), *sys.argv[1:]]
    return int(subprocess.run(cmd, check=False).returncode)


if __name__ == "__main__":
    raise SystemExit(main())
