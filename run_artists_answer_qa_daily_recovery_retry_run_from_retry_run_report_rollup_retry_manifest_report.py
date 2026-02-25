#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from qa_artifact_utils import build_artifact_header, resolve_latest_artifact

DEFAULT_SEARCH_DIR = Path("data/phase1_seed10/derived/answer")
DEFAULT_GLOB = "artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*.json"
SOURCE_CLI = (
    "run_artists_answer_qa_daily_recovery_retry_run_from_retry_run_report_rollup_retry_manifest_report.py"
)
INPUT_ARTIFACT_KIND = "retry_run_summary_from_rollup"
OUTPUT_ARTIFACT_KIND = "retry_run_summary_from_rollup_report"


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
            "Read retry-run-from-rollup summary generated via retry-run-report-rollup retry-manifest "
            "and write a lightweight report."
        )
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--summary-path", default="", help="retry run from rollup summary path")
    group.add_argument("--latest", action="store_true", help="resolve latest summary")
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
    parser.add_argument("--output-json", default="", help="optional output report path")
    return parser.parse_args()


def _collect_child_daily_summaries(summary: dict[str, Any]) -> list[str]:
    collected: list[str] = []
    seen: set[str] = set()

    def add_path(raw: Any) -> None:
        if not isinstance(raw, str):
            return
        text = raw.strip()
        if not text:
            return
        resolved = str(Path(text).resolve())
        if resolved in seen:
            return
        seen.add(resolved)
        collected.append(resolved)

    for path in _as_string_list(summary.get("child_daily_summaries")):
        add_path(path)

    raw_cases = summary.get("cases")
    if isinstance(raw_cases, list):
        for raw_case in raw_cases:
            if not isinstance(raw_case, dict):
                continue
            add_path(raw_case.get("daily_summary_path"))

    return collected


def _extract_failed_case_ids(summary: dict[str, Any]) -> list[str]:
    failed_case_ids: list[str] = []
    raw_cases = summary.get("cases")
    if not isinstance(raw_cases, list):
        return failed_case_ids

    for raw_case in raw_cases:
        if not isinstance(raw_case, dict):
            continue
        case_id = raw_case.get("case_id")
        status = str(raw_case.get("status") or "")
        exit_code = _as_int(raw_case.get("exit_code"))
        failed = status == "failed" or (exit_code is not None and exit_code != 0)
        if failed and isinstance(case_id, str) and case_id.strip():
            failed_case_ids.append(case_id.strip())
    return failed_case_ids


def main() -> int:
    args = parse_args()

    report: dict[str, Any] = {
        **build_artifact_header(OUTPUT_ARTIFACT_KIND, generated_by=SOURCE_CLI),
        "source_cli": SOURCE_CLI,
        "source_summary_path_requested": args.summary_path if args.summary_path else "--latest",
        "latest_resolved": bool(args.latest),
        "source_summary_path": None,
        "retry_manifest_path": None,
        "executed_runs": None,
        "failed_runs": None,
        "failed_case_ids": [],
        "child_daily_summaries_to_check": [],
        "all_passed": None,
        "wrapper_exit_code": None,
        "notes": [],
        "warnings": [],
        "report_exit_code": 1,
        "exit_reason": "summary_not_found_or_invalid",
    }

    if args.summary_path:
        summary_path = Path(args.summary_path).resolve()
    else:
        latest_path, latest_error = resolve_latest_artifact(
            Path(args.search_dir).resolve(),
            INPUT_ARTIFACT_KIND,
            glob_pattern=args.glob,
        )
        if latest_error:
            report["notes"].append(latest_error)
            print(f"[ERROR] {latest_error}")
            output_path = (
                Path(args.output_json).resolve()
                if args.output_json
                else (
                    Path(args.search_dir)
                    / "artists_answer_qa_daily_recovery_retry_run_from_rollup_retry_manifest_report_latest_error.json"
                ).resolve()
            )
            write_json(output_path, report)
            print(f"[DONE] report={output_path}")
            return 1
        assert latest_path is not None
        summary_path = latest_path

    report["source_summary_path"] = str(summary_path)

    output_path = (
        Path(args.output_json).resolve()
        if args.output_json
        else summary_path.with_name(f"{summary_path.stem}_report.json")
    )

    if not summary_path.exists():
        error = f"retry_run_from_rollup_summary_not_found:{summary_path}"
        report["notes"].append(error)
        print(f"[ERROR] {error}")
        write_json(output_path, report)
        print(f"[DONE] report={output_path}")
        return 1

    try:
        summary = load_json(summary_path)
    except Exception as exc:  # noqa: BLE001
        error = f"retry_run_from_rollup_summary_load_failed:{exc}"
        report["notes"].append(error)
        print(f"[ERROR] {error}")
        write_json(output_path, report)
        print(f"[DONE] report={output_path}")
        return 1

    report["retry_manifest_path"] = summary.get("retry_manifest_path")
    report["executed_runs"] = summary.get("executed_runs")
    report["failed_runs"] = summary.get("failed_runs")
    report["all_passed"] = summary.get("all_passed")
    report["wrapper_exit_code"] = summary.get("wrapper_exit_code")
    report["failed_case_ids"] = _extract_failed_case_ids(summary)
    report["child_daily_summaries_to_check"] = _collect_child_daily_summaries(summary)

    notes = summary.get("notes", [])
    if isinstance(notes, list):
        report["notes"] = [str(note) for note in notes]
    elif notes is not None:
        report["notes"] = [str(notes)]

    if not isinstance(summary.get("cases"), list):
        report["warnings"].append("cases_missing_or_invalid")

    report["report_exit_code"] = 0
    report["exit_reason"] = "report_generated"
    write_json(output_path, report)

    print(
        "[REPORT] "
        f"executed_runs={report.get('executed_runs')} "
        f"failed_runs={report.get('failed_runs')} "
        f"all_passed={report.get('all_passed')} "
        f"wrapper_exit_code={report.get('wrapper_exit_code')}"
    )
    print(f"[REPORT] failed_case_ids={report.get('failed_case_ids')}")
    child_paths = report.get("child_daily_summaries_to_check")
    if isinstance(child_paths, list) and child_paths:
        print("[REPORT] child_daily_summaries_to_check:")
        for path in child_paths:
            print(f"  - {path}")
    else:
        print("[REPORT] child_daily_summaries_to_check: none")
    print(f"[DONE] report={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
