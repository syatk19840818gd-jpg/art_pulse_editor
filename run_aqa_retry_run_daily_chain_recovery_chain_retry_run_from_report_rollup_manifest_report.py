#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from qa_artifact_utils import build_artifact_header, resolve_latest_artifact

DEFAULT_SEARCH_DIR = Path("data/phase1_seed10/derived/answer")
SOURCE_CLI = "run_aqa_retry_run_daily_chain_recovery_chain_retry_run_from_report_rollup_manifest_report.py"
INPUT_ARTIFACT_KIND = "retry_run_daily_chain_recovery_chain_retry_run_summary_from_report_rollup_manifest"
OUTPUT_ARTIFACT_KIND = "retry_run_daily_chain_recovery_chain_retry_run_summary_from_report_rollup_manifest_report"
EXPECTED_RETRY_MANIFEST_PREFIX = "artists_answer_qa_retry_run_daily_chain_recovery_chain_report_rollup_"
EXPECTED_RETRY_MANIFEST_SUFFIX = "_retry_manifest.json"


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


def _as_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return str(value)


def _extract_failed_case_ids(summary: dict[str, Any]) -> list[str]:
    raw_cases = summary.get("cases")
    if not isinstance(raw_cases, list):
        return []
    failed_ids: list[str] = []
    for raw_case in raw_cases:
        if not isinstance(raw_case, dict):
            continue
        case_id = _as_optional_str(raw_case.get("case_id"))
        status = str(raw_case.get("status") or "unknown")
        exit_code = _as_int(raw_case.get("exit_code"))
        is_failed = bool(status == "failed" or (exit_code is not None and exit_code != 0))
        if is_failed and case_id:
            failed_ids.append(case_id)
    return failed_ids


def _collect_child_daily_summaries(summary: dict[str, Any], source_summary_path: Path) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()

    def add_path(raw_value: Any) -> None:
        if not isinstance(raw_value, str):
            return
        text = raw_value.strip()
        if not text:
            return
        if not text.endswith(".json"):
            return
        resolved = str(Path(text).resolve())
        if resolved == str(source_summary_path):
            return
        if resolved in seen:
            return
        seen.add(resolved)
        out.append(resolved)

    raw_children = summary.get("child_daily_summaries")
    if isinstance(raw_children, list):
        for value in raw_children:
            add_path(value)

    raw_cases = summary.get("cases")
    if isinstance(raw_cases, list):
        for raw_case in raw_cases:
            if not isinstance(raw_case, dict):
                continue
            add_path(raw_case.get("daily_summary_path"))

    return out


def _is_expected_retry_manifest_path(path_value: str | None) -> bool:
    if not path_value:
        return False
    name = Path(path_value).name
    return name.startswith(EXPECTED_RETRY_MANIFEST_PREFIX) and name.endswith(EXPECTED_RETRY_MANIFEST_SUFFIX)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read retry-run summary (from recovery-chain report-rollup manifest) and write a lightweight report."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--summary-path", default="", help="retry-run summary path")
    group.add_argument("--latest", action="store_true", help="resolve latest retry-run summary")
    parser.add_argument(
        "--search-dir",
        default=str(DEFAULT_SEARCH_DIR),
        help=f"search directory for --latest (default: {DEFAULT_SEARCH_DIR})",
    )
    parser.add_argument("--glob", default="", help="optional glob override for --latest")
    parser.add_argument("--output-json", default="", help="optional output report path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    report: dict[str, Any] = {
        **build_artifact_header(OUTPUT_ARTIFACT_KIND, generated_by=SOURCE_CLI),
        "source_cli": SOURCE_CLI,
        "source_summary_path_requested": args.summary_path if args.summary_path else "--latest",
        "latest_resolved": bool(args.latest),
        "summary_path": None,
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
            glob_pattern=args.glob or None,
        )
        if latest_error:
            report["notes"].append(latest_error)
            print(f"[ERROR] {latest_error}")
            output_path = (
                Path(args.output_json).resolve()
                if args.output_json
                else (Path(args.search_dir).resolve() / "artists_answer_qa_retry_run_daily_chain_recovery_chain_retry_run_report_latest_error.json")
            )
            write_json(output_path, report)
            print(f"[DONE] report={output_path}")
            return 1
        assert latest_path is not None
        summary_path = latest_path

    report["summary_path"] = str(summary_path)
    output_path = (
        Path(args.output_json).resolve()
        if args.output_json
        else summary_path.with_name(f"{summary_path.stem}_report.json")
    )

    if not summary_path.exists():
        error = f"retry_run_summary_not_found:{summary_path}"
        report["notes"].append(error)
        print(f"[ERROR] {error}")
        write_json(output_path, report)
        print(f"[DONE] report={output_path}")
        return 1

    try:
        summary = load_json(summary_path)
    except Exception as exc:  # noqa: BLE001
        error = f"retry_run_summary_load_failed:{exc}"
        report["notes"].append(error)
        print(f"[ERROR] {error}")
        write_json(output_path, report)
        print(f"[DONE] report={output_path}")
        return 1

    report["retry_manifest_path"] = _as_optional_str(summary.get("retry_manifest_path"))
    report["executed_runs"] = _as_int(summary.get("executed_runs"))
    report["all_passed"] = summary.get("all_passed")
    report["wrapper_exit_code"] = summary.get("wrapper_exit_code")

    raw_notes = summary.get("notes")
    if isinstance(raw_notes, list):
        report["notes"] = [str(note) for note in raw_notes]
    elif raw_notes is not None:
        report["notes"] = [str(raw_notes)]

    failed_case_ids = _extract_failed_case_ids(summary)
    report["failed_case_ids"] = failed_case_ids

    failed_runs = _as_int(summary.get("failed_runs"))
    if failed_runs is None:
        failed_runs = len(failed_case_ids)
    report["failed_runs"] = failed_runs

    report["child_daily_summaries_to_check"] = _collect_child_daily_summaries(summary, summary_path)

    retry_manifest_ok = _is_expected_retry_manifest_path(report["retry_manifest_path"])
    if not retry_manifest_ok:
        report["notes"].append(
            "retry_manifest_path_mismatch_for_task99:"
            f"expected_prefix={EXPECTED_RETRY_MANIFEST_PREFIX} "
            f"expected_suffix={EXPECTED_RETRY_MANIFEST_SUFFIX} "
            f"actual={report['retry_manifest_path']}"
        )
        report["report_exit_code"] = 1
        report["exit_reason"] = "summary_out_of_scope_for_task99"
        write_json(output_path, report)
        print("[REPORT] target_summary_scope=invalid")
        print(f"[DONE] report={output_path}")
        return 1

    report["report_exit_code"] = 0
    report["exit_reason"] = "report_generated"
    write_json(output_path, report)

    print(
        "[REPORT] "
        f"executed_runs={report.get('executed_runs')} "
        f"failed_runs={report.get('failed_runs')} "
        f"failed_case_ids={len(report.get('failed_case_ids', []))}"
    )
    if report["failed_case_ids"]:
        print("[REPORT] failed_case_ids:")
        for case_id in report["failed_case_ids"]:
            print(f"  - {case_id}")
    else:
        print("[REPORT] failed_case_ids: none")

    children = report.get("child_daily_summaries_to_check")
    if isinstance(children, list) and children:
        print("[REPORT] child_daily_summaries_to_check:")
        for path in children:
            print(f"  - {path}")
    else:
        print("[REPORT] child_daily_summaries_to_check: none")

    print(f"[DONE] report={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

