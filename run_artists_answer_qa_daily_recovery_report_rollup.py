#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_SEARCH_DIR = Path("data/phase1_seed10/derived/answer")
DEFAULT_GLOB = "artists_answer_qa_daily_recovery_summary_*_report.json"
SOURCE_CLI = "run_artists_answer_qa_daily_recovery_report_rollup.py"


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


def _is_rollup_candidate(path: Path) -> bool:
    name = path.name
    if not name.startswith("artists_answer_qa_daily_recovery_summary_"):
        return False
    if not name.endswith("_report.json"):
        return False
    # Exclude child report artifacts.
    excluded_tokens = ("_batch_report.json", "_retry_run_report.json")
    return not any(token in name for token in excluded_tokens)


def _as_failed_step_rows(raw_failed_steps: Any) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    names: list[str] = []

    if not isinstance(raw_failed_steps, list):
        return rows, names

    for raw in raw_failed_steps:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("name") or "unknown")
        rows.append(
            {
                "name": name,
                "status": str(raw.get("status") or "unknown"),
                "exit_code": raw.get("exit_code"),
            }
        )
        names.append(name)

    return rows, names


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Roll up artists daily recovery report JSON files and extract failed runs."
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

    candidates = [p for p in search_dir.glob(args.glob) if p.is_file() and _is_rollup_candidate(p)]
    if not candidates:
        message = f"daily_recovery_reports_not_found:{search_dir}/{args.glob}"
        rollup["warnings"].append(message)
        output_path = (
            Path(args.output_json).resolve()
            if args.output_json
            else (search_dir / f"artists_answer_qa_daily_recovery_report_rollup_{utc_timestamp_compact()}.json").resolve()
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
        failed_step_rows, failed_step_names = _as_failed_step_rows(report_obj.get("failed_steps"))
        failed_step_count = len(failed_step_rows)
        if failed_step_count == 0:
            continue

        child_paths = report_obj.get("child_summary_paths_to_check")
        if not isinstance(child_paths, list):
            child_paths = []

        failed_runs.append(
            {
                "report_path": str(report_path.resolve()),
                "summary_path": report_obj.get("source_summary_path"),
                "failed_step_count": failed_step_count,
                "failed_step_names": failed_step_names,
                "failed_steps": failed_step_rows,
                "child_summary_paths_to_check": [str(p) for p in child_paths if isinstance(p, str)],
                "all_passed": report_obj.get("all_passed"),
                "wrapper_exit_code": report_obj.get("wrapper_exit_code"),
            }
        )

    rollup["total_reports"] = valid_reports
    rollup["failed_run_count"] = len(failed_runs)
    rollup["failed_runs"] = failed_runs

    output_path = (
        Path(args.output_json).resolve()
        if args.output_json
        else (search_dir / f"artists_answer_qa_daily_recovery_report_rollup_{utc_timestamp_compact()}.json").resolve()
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
                f"failed_step_count={run.get('failed_step_count')} "
                f"failed_step_names={run.get('failed_step_names')}"
            )
    else:
        print("[ROLLUP] failed_runs: none")

    print(f"[DONE] rollup={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
