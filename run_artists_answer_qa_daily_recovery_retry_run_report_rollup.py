#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_SEARCH_DIR = Path("data/phase1_seed10/derived/answer")
DEFAULT_GLOB = "artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*_report.json"
SOURCE_CLI = "run_artists_answer_qa_daily_recovery_retry_run_report_rollup.py"


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


def _is_report_rollup_candidate(path: Path) -> bool:
    name = path.name
    if not name.startswith("artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_"):
        return False
    if not name.endswith("_report.json"):
        return False
    # Exclude child artifacts and retry-run report rollup outputs.
    excluded_tokens = ("_failed_run_", "_report_rollup_")
    return not any(token in name for token in excluded_tokens)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Roll up artists retry-run report JSON files and extract failed runs."
    )
    parser.add_argument(
        "--search-dir",
        default=str(DEFAULT_SEARCH_DIR),
        help=f"search directory (default: {DEFAULT_SEARCH_DIR})",
    )
    parser.add_argument(
        "--glob",
        default=DEFAULT_GLOB,
        help=f"glob pattern (default: {DEFAULT_GLOB})",
    )
    parser.add_argument(
        "--latest-n",
        type=int,
        default=20,
        help="max number of latest report files to include (default: 20)",
    )
    parser.add_argument("--output-json", default="", help="optional rollup output path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    latest_n = max(1, int(args.latest_n))
    search_dir = Path(args.search_dir).resolve()

    rollup: dict[str, Any] = {
        "checked_at": utc_now_iso(),
        "source_cli": SOURCE_CLI,
        "search_dir": str(search_dir),
        "glob": args.glob,
        "latest_n_requested": latest_n,
        "total_reports": 0,
        "failed_run_count": 0,
        "failed_runs": [],
        "report_paths_considered": [],
        "warnings": [],
        "rollup_exit_code": 1,
        "exit_reason": "reports_not_found_or_invalid",
    }

    candidates = [p for p in search_dir.glob(args.glob) if p.is_file() and _is_report_rollup_candidate(p)]
    if not candidates:
        message = f"retry_run_reports_not_found:{search_dir}/{args.glob}"
        rollup["warnings"].append(message)
        output_path = (
            Path(args.output_json).resolve()
            if args.output_json
            else (search_dir / f"artists_answer_qa_daily_recovery_retry_run_report_rollup_{utc_timestamp_compact()}.json").resolve()
        )
        write_json(output_path, rollup)
        print(f"[ERROR] {message}")
        print(f"[DONE] rollup={output_path}")
        return 1

    candidates = sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)[:latest_n]
    rollup["report_paths_considered"] = [str(path.resolve()) for path in candidates]

    failed_runs: list[dict[str, Any]] = []
    valid_reports = 0

    for report_path in candidates:
        try:
            report_obj = load_json(report_path)
        except Exception as exc:  # noqa: BLE001
            rollup["warnings"].append(f"report_load_failed:{report_path}:{exc}")
            continue

        valid_reports += 1

        failed_case_ids = _as_string_list(report_obj.get("failed_case_ids"))
        failed_runs_value = _as_int(report_obj.get("failed_runs"))
        all_passed = report_obj.get("all_passed")
        wrapper_exit_code = _as_int(report_obj.get("wrapper_exit_code"))

        failed_case_count = len(failed_case_ids)
        has_failure = False
        if failed_case_count > 0:
            has_failure = True
        elif failed_runs_value is not None and failed_runs_value > 0:
            has_failure = True
            failed_case_count = failed_runs_value
        elif all_passed is False:
            has_failure = True
        elif wrapper_exit_code is not None and wrapper_exit_code != 0:
            has_failure = True

        if not has_failure:
            continue

        failed_runs.append(
            {
                "report_path": str(report_path.resolve()),
                "summary_path": report_obj.get("source_summary_path"),
                "failed_case_count": failed_case_count,
                "failed_case_ids": failed_case_ids,
                "child_daily_summaries_to_check": _as_string_list(report_obj.get("child_daily_summaries_to_check")),
                "all_passed": all_passed,
                "wrapper_exit_code": report_obj.get("wrapper_exit_code"),
            }
        )

    rollup["total_reports"] = valid_reports
    rollup["failed_run_count"] = len(failed_runs)
    rollup["failed_runs"] = failed_runs

    output_path = (
        Path(args.output_json).resolve()
        if args.output_json
        else (search_dir / f"artists_answer_qa_daily_recovery_retry_run_report_rollup_{utc_timestamp_compact()}.json").resolve()
    )

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
                f"failed_case_count={run.get('failed_case_count')} "
                f"failed_case_ids={run.get('failed_case_ids')}"
            )
    else:
        print("[ROLLUP] failed_runs: none")

    print(f"[DONE] rollup={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
