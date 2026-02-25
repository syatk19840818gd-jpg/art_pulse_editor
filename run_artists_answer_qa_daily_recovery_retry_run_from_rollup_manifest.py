#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_SEARCH_DIR = Path("data/phase1_seed10/derived/answer")
DEFAULT_GLOB = "artists_answer_qa_daily_recovery_report_rollup_*_retry_manifest.json"
DEFAULT_SUMMARY_DIR = Path("data/phase1_seed10/derived/answer")
DAILY_RECOVERY_SCRIPT = Path("run_artists_answer_qa_daily_recovery.py")
SOURCE_CLI = "run_artists_answer_qa_daily_recovery_retry_run_from_rollup_manifest.py"


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


def _resolve_latest_manifest(search_dir: Path, pattern: str) -> tuple[Path | None, str | None]:
    candidates = [p for p in search_dir.glob(pattern) if p.is_file()]
    if not candidates:
        return None, f"latest_retry_manifest_not_found:{search_dir}/{pattern}"
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    return latest.resolve(), None


def _as_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return str(value)


def _tail_lines(text: str, max_lines: int = 20) -> str:
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text
    return "\n".join(lines[-max_lines:])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run daily recovery for failed runs listed in rollup retry manifest."
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
    started_at = utc_now_iso()
    timestamp = utc_timestamp_compact()

    output_summary_path = (
        Path(args.output_json).resolve()
        if args.output_json
        else (DEFAULT_SUMMARY_DIR / f"artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_{timestamp}.json").resolve()
    )

    summary: dict[str, Any] = {
        "started_at": started_at,
        "completed_at": None,
        "source_cli": SOURCE_CLI,
        "retry_manifest_path_requested": args.retry_manifest if args.retry_manifest else "--latest",
        "retry_manifest_latest_resolved": bool(args.latest),
        "retry_manifest_path": None,
        "retry_manifest_case_count": 0,
        "executed_runs": 0,
        "succeeded_runs": 0,
        "failed_runs": 0,
        "all_passed": False,
        "wrapper_exit_code": 1,
        "child_daily_summaries": [],
        "cases": [],
        "notes": [],
        "output_summary_path": str(output_summary_path),
    }

    def finalize(exit_code: int) -> int:
        summary["completed_at"] = utc_now_iso()
        summary["wrapper_exit_code"] = int(exit_code)
        write_json(output_summary_path, summary)
        print(
            "[DONE] retry_run_from_rollup complete. "
            f"executed_runs={summary['executed_runs']} "
            f"failed_runs={summary['failed_runs']} "
            f"wrapper_exit_code={summary['wrapper_exit_code']}"
        )
        print(f"[DONE] summary={output_summary_path}")
        return int(exit_code)

    if args.retry_manifest:
        retry_manifest_path = Path(args.retry_manifest).resolve()
    else:
        latest_path, latest_error = _resolve_latest_manifest(Path(args.search_dir), args.glob)
        if latest_error:
            summary["notes"].append(latest_error)
            print(f"[ERROR] {latest_error}")
            return finalize(1)
        assert latest_path is not None
        retry_manifest_path = latest_path

    summary["retry_manifest_path"] = str(retry_manifest_path)

    if not retry_manifest_path.exists():
        error = f"retry_manifest_not_found:{retry_manifest_path}"
        summary["notes"].append(error)
        print(f"[ERROR] {error}")
        return finalize(1)

    try:
        manifest_obj = load_json(retry_manifest_path)
    except Exception as exc:  # noqa: BLE001
        error = f"retry_manifest_load_failed:{exc}"
        summary["notes"].append(error)
        print(f"[ERROR] {error}")
        return finalize(1)

    raw_cases = manifest_obj.get("cases")
    if not isinstance(raw_cases, list):
        error = "retry_manifest_cases_not_array"
        summary["notes"].append(error)
        print(f"[ERROR] {error}")
        return finalize(1)

    summary["retry_manifest_case_count"] = len(raw_cases)

    if len(raw_cases) == 0:
        summary["executed_runs"] = 0
        summary["all_passed"] = True
        summary["notes"].append("no_failed_runs_in_manifest")
        summary["retry_run_mode"] = "noop_empty_retry_manifest"
        print("[DONE] no-op: empty retry manifest")
        return finalize(0)

    all_passed = True
    for index, raw_case in enumerate(raw_cases, start=1):
        case_record: dict[str, Any] = {
            "case_id": f"failed_run_{index:03d}",
            "status": "failed",
            "exit_code": None,
            "source_summary_path": None,
            "batch_manifest_path": None,
            "daily_summary_path": None,
            "notes": [],
            "stdout_tail": "",
            "stderr_tail": "",
        }

        if not isinstance(raw_case, dict):
            case_record["notes"].append("case_not_object")
            summary["cases"].append(case_record)
            summary["failed_runs"] += 1
            all_passed = False
            continue

        case_id = _as_optional_str(raw_case.get("case_id")) or case_record["case_id"]
        source_summary_path = _as_optional_str(raw_case.get("source_summary_path"))
        batch_manifest_path = _as_optional_str(raw_case.get("batch_manifest_path"))
        case_record["case_id"] = case_id
        case_record["source_summary_path"] = source_summary_path
        case_record["batch_manifest_path"] = batch_manifest_path

        if not batch_manifest_path:
            case_record["notes"].append("batch_manifest_path_missing")
            summary["cases"].append(case_record)
            summary["failed_runs"] += 1
            all_passed = False
            continue

        batch_manifest = Path(batch_manifest_path).resolve()
        if not batch_manifest.exists():
            case_record["notes"].append(f"batch_manifest_not_found:{batch_manifest}")
            summary["cases"].append(case_record)
            summary["failed_runs"] += 1
            all_passed = False
            continue

        child_summary_path = output_summary_path.with_name(
            f"{output_summary_path.stem}_{case_id}_daily_summary.json"
        )
        cmd = [
            sys.executable,
            str(DAILY_RECOVERY_SCRIPT),
            "--batch-manifest",
            str(batch_manifest),
            "--output-json",
            str(child_summary_path),
        ]
        completed = subprocess.run(cmd, capture_output=True, text=True, check=False)

        case_record["command"] = cmd
        case_record["exit_code"] = int(completed.returncode)
        case_record["daily_summary_path"] = str(child_summary_path)
        case_record["stdout_tail"] = _tail_lines(completed.stdout)
        case_record["stderr_tail"] = _tail_lines(completed.stderr)

        summary["executed_runs"] += 1
        summary["child_daily_summaries"].append(str(child_summary_path))

        if int(completed.returncode) == 0:
            case_record["status"] = "ok"
            summary["succeeded_runs"] += 1
        else:
            case_record["status"] = "failed"
            summary["failed_runs"] += 1
            all_passed = False

        summary["cases"].append(case_record)

    summary["all_passed"] = all_passed
    if all_passed:
        summary["notes"].append("all_retry_runs_passed")
        return finalize(0)

    summary["notes"].append("retry_runs_failed_or_invalid_cases_found")
    return finalize(1)


if __name__ == "__main__":
    raise SystemExit(main())
