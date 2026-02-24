#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_SEARCH_DIR = Path("data/phase1_seed10/derived/answer")
DEFAULT_GLOB = "artists_answer_qa_retry_run_summary_*.json"
SOURCE_CLI = "run_artists_answer_qa_retry_run_report.py"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"json_not_object:{path}")
    return obj


def resolve_latest_summary(search_dir: Path, pattern: str) -> tuple[Path | None, str | None]:
    candidates = [p for p in search_dir.glob(pattern) if p.is_file()]
    candidates = [
        p
        for p in candidates
        if "_child_batch_summary" not in p.name and "_report" not in p.name
    ]
    if not candidates:
        return None, f"latest_retry_run_summary_not_found:{search_dir}/{pattern}"
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    return latest.resolve(), None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read artists QA retry-run summary and build a lightweight report."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--summary-path", default="", help="retry run summary path")
    group.add_argument("--latest", action="store_true", help="resolve latest retry run summary")
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


def main() -> int:
    args = parse_args()

    report: dict[str, Any] = {
        "checked_at": utc_now_iso(),
        "source_cli": SOURCE_CLI,
        "summary_path_requested": args.summary_path if args.summary_path else "--latest",
        "summary_latest_resolved": bool(args.latest),
        "summary_path": None,
        "retry_manifest_path": None,
        "retry_manifest_case_count": None,
        "executed_cases": None,
        "wrapper_exit_code": None,
        "all_passed": None,
        "child_batch_summary_path": None,
        "child_batch_cases_jsonl_path": None,
        "notes": [],
        "warnings": [],
        "report_exit_code": 1,
        "report_status": "invalid",
    }

    if args.summary_path:
        summary_path = Path(args.summary_path).resolve()
    else:
        latest_path, latest_error = resolve_latest_summary(Path(args.search_dir), args.glob)
        if latest_error:
            report["notes"].append(latest_error)
            print(f"[ERROR] {latest_error}")
            output_path = (
                Path(args.output_json).resolve()
                if args.output_json
                else (Path(args.search_dir) / "artists_answer_qa_retry_run_report_latest_error.json").resolve()
            )
            write_json(output_path, report)
            print(f"[DONE] report={output_path}")
            return 1
        assert latest_path is not None
        summary_path = latest_path

    report["summary_path"] = str(summary_path)

    if not summary_path.exists():
        error = f"retry_run_summary_not_found:{summary_path}"
        report["notes"].append(error)
        print(f"[ERROR] {error}")
        output_path = (
            Path(args.output_json).resolve()
            if args.output_json
            else summary_path.with_name(f"{summary_path.stem}_report.json")
        )
        write_json(output_path, report)
        print(f"[DONE] report={output_path}")
        return 1

    try:
        summary = load_json(summary_path)
    except Exception as exc:  # noqa: BLE001
        error = f"retry_run_summary_load_failed:{exc}"
        report["notes"].append(error)
        print(f"[ERROR] {error}")
        output_path = (
            Path(args.output_json).resolve()
            if args.output_json
            else summary_path.with_name(f"{summary_path.stem}_report.json")
        )
        write_json(output_path, report)
        print(f"[DONE] report={output_path}")
        return 1

    report["retry_manifest_path"] = summary.get("retry_manifest_path")
    report["retry_manifest_case_count"] = summary.get("retry_manifest_case_count")
    report["executed_cases"] = summary.get("executed_cases")
    report["wrapper_exit_code"] = summary.get("wrapper_exit_code")
    report["all_passed"] = summary.get("all_passed")
    report["child_batch_summary_path"] = summary.get("child_batch_summary_path")
    report["child_batch_cases_jsonl_path"] = summary.get("child_batch_cases_jsonl_path")

    notes = summary.get("notes", [])
    if isinstance(notes, list):
        report["notes"] = [str(note) for note in notes]
    elif notes is not None:
        report["notes"] = [str(notes)]

    wrapper_exit_code = summary.get("wrapper_exit_code")
    if wrapper_exit_code == 0:
        report["report_status"] = "ok"
        report["report_exit_code"] = 0
    elif isinstance(wrapper_exit_code, int):
        report["report_status"] = "failed_retry_run"
        report["report_exit_code"] = 0
    else:
        report["warnings"].append("wrapper_exit_code_missing_or_invalid")
        report["report_status"] = "unknown"
        report["report_exit_code"] = 0

    output_path = (
        Path(args.output_json).resolve()
        if args.output_json
        else summary_path.with_name(f"{summary_path.stem}_report.json")
    )
    write_json(output_path, report)

    print(
        "[REPORT] "
        f"all_passed={report.get('all_passed')} wrapper_exit_code={report.get('wrapper_exit_code')} "
        f"executed_cases={report.get('executed_cases')}"
    )
    print(f"[REPORT] retry_manifest_path={report.get('retry_manifest_path')}")
    print(f"[REPORT] child_batch_summary_path={report.get('child_batch_summary_path')}")
    print(f"[REPORT] child_batch_cases_jsonl_path={report.get('child_batch_cases_jsonl_path')}")
    print(f"[DONE] report={output_path}")

    return int(report["report_exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
