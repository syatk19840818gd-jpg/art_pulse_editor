#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_SEARCH_DIR = Path("data/phase1_seed10/derived/answer")
DEFAULT_GLOB = "artists_answer_qa_smoke_summary_*_cases.jsonl"
SOURCE_CLI = "run_artists_answer_qa_batch_report.py"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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


def _resolve_latest_cases_jsonl(search_dir: Path, pattern: str) -> tuple[Path | None, str | None]:
    candidates = [p for p in search_dir.glob(pattern) if p.is_file()]
    if not candidates:
        return None, f"latest_cases_jsonl_not_found:{search_dir}/{pattern}"
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    return latest.resolve(), None


def _load_cases_jsonl(path: Path) -> tuple[list[dict[str, Any]] | None, str | None]:
    if not path.exists():
        return None, f"cases_jsonl_not_found:{path}"

    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                raw = line.strip()
                if not raw:
                    continue
                obj = json.loads(raw)
                if not isinstance(obj, dict):
                    return None, f"cases_jsonl_line_not_object:{line_no}"
                rows.append(obj)
    except json.JSONDecodeError as exc:
        return None, f"cases_jsonl_json_decode_error:{exc}"
    except OSError as exc:
        return None, f"cases_jsonl_os_error:{exc}"

    return rows, None


def _build_report(cases: list[dict[str, Any]], input_path: Path) -> dict[str, Any]:
    failed_cases: list[dict[str, Any]] = []
    failed_case_ids: list[str] = []
    summary_paths_to_check: list[str] = []
    seen_paths: set[str] = set()

    for case in cases:
        case_id = str(case.get("case_id") or "")
        exit_code = _as_int(case.get("exit_code"))
        summary_path = case.get("summary_path")
        summary_path_text = str(summary_path) if isinstance(summary_path, str) else None
        case_failure_kind = str(case.get("case_failure_kind") or "")
        guard_passed = case.get("guard_passed")

        is_failed = exit_code is None or exit_code != 0
        if is_failed:
            failed_case_ids.append(case_id)
            failed_cases.append(
                {
                    "case_id": case_id,
                    "exit_code": exit_code,
                    "case_failure_kind": case_failure_kind,
                    "guard_passed": guard_passed if isinstance(guard_passed, bool) else None,
                    "summary_path": summary_path_text,
                }
            )
            if summary_path_text and summary_path_text not in seen_paths:
                seen_paths.add(summary_path_text)
                summary_paths_to_check.append(summary_path_text)

    total_cases = len(cases)
    failed_count = len(failed_cases)
    passed_count = total_cases - failed_count

    return {
        "checked_at": utc_now_iso(),
        "source_cli": SOURCE_CLI,
        "input_cases_jsonl_path": str(input_path),
        "total_cases": total_cases,
        "passed_cases": passed_count,
        "failed_cases": failed_count,
        "failed_case_ids": failed_case_ids,
        "summary_paths_to_check": summary_paths_to_check,
        "failed_case_rows": failed_cases,
    }


def _print_report(report: dict[str, Any]) -> None:
    print(
        "[REPORT] "
        f"input_cases_jsonl={report['input_cases_jsonl_path']} "
        f"total_cases={report['total_cases']} "
        f"passed_cases={report['passed_cases']} "
        f"failed_cases={report['failed_cases']}"
    )

    failed_case_ids = report.get("failed_case_ids", [])
    if isinstance(failed_case_ids, list) and failed_case_ids:
        print("[REPORT] failed_case_ids:")
        for case_id in failed_case_ids:
            print(f"  - {case_id}")
    else:
        print("[REPORT] failed_case_ids: none")

    summary_paths_to_check = report.get("summary_paths_to_check", [])
    if isinstance(summary_paths_to_check, list) and summary_paths_to_check:
        print("[REPORT] summary_paths_to_check:")
        for summary_path in summary_paths_to_check:
            print(f"  - {summary_path}")
    else:
        print("[REPORT] summary_paths_to_check: none")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read artists QA batch cases JSONL and write a compact triage report."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--cases-jsonl", default="", help="path to batch cases JSONL")
    group.add_argument("--latest", action="store_true", help="resolve latest cases JSONL")
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
    parser.add_argument("--output-json", default="", help="optional report output path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.cases_jsonl:
        input_path = Path(args.cases_jsonl).resolve()
    else:
        latest_path, latest_error = _resolve_latest_cases_jsonl(Path(args.search_dir), args.glob)
        if latest_error:
            print(f"[ERROR] {latest_error}")
            return 1
        assert latest_path is not None
        input_path = latest_path

    cases, load_error = _load_cases_jsonl(input_path)
    if load_error:
        print(f"[ERROR] {load_error}")
        return 1
    assert cases is not None

    report = _build_report(cases, input_path)
    _print_report(report)

    output_path = Path(args.output_json).resolve() if args.output_json else input_path.with_name(
        f"{input_path.stem}_report.json"
    )
    write_json(output_path, report)
    print(f"[DONE] report={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
