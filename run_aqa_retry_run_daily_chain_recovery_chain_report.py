#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from qa_artifact_utils import build_artifact_header, resolve_latest_artifact

DEFAULT_SEARCH_DIR = Path("data/phase1_seed10/derived/answer")
SOURCE_CLI = "run_aqa_retry_run_daily_chain_recovery_chain_report.py"
INPUT_ARTIFACT_KIND = "retry_run_daily_chain_recovery_chain_summary"
OUTPUT_ARTIFACT_KIND = "retry_run_daily_chain_recovery_chain_report"


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


def _extract_failed_steps(summary: dict[str, Any]) -> list[dict[str, Any]]:
    failed_steps: list[dict[str, Any]] = []
    steps = summary.get("steps")
    if not isinstance(steps, list):
        return failed_steps

    for raw_step in steps:
        if not isinstance(raw_step, dict):
            continue
        status = str(raw_step.get("status") or "unknown")
        exit_code = _as_int(raw_step.get("exit_code"))
        is_failed = status == "failed" or (exit_code is not None and exit_code != 0)
        if not is_failed:
            continue
        failed_steps.append(
            {
                "name": str(raw_step.get("name") or ""),
                "status": status,
                "exit_code": exit_code,
                "command": raw_step.get("command"),
                "output_paths": raw_step.get("output_paths") if isinstance(raw_step.get("output_paths"), dict) else {},
            }
        )
    return failed_steps


def _collect_child_summary_paths(
    summary: dict[str, Any],
    source_summary_path: Path,
    failed_steps: list[dict[str, Any]],
) -> list[str]:
    collected: list[str] = []
    seen: set[str] = set()

    def add_path(value: Any) -> None:
        if not isinstance(value, str):
            return
        text = value.strip()
        if not text:
            return
        if not (text.endswith(".json") or text.endswith(".jsonl")):
            return
        resolved = str(Path(text).resolve())
        if resolved == str(source_summary_path):
            return
        if resolved in seen:
            return
        seen.add(resolved)
        collected.append(resolved)

    for step in failed_steps:
        output_paths = step.get("output_paths")
        if not isinstance(output_paths, dict):
            continue
        for value in output_paths.values():
            add_path(value)

    if not collected:
        steps = summary.get("steps")
        if isinstance(steps, list):
            for raw_step in steps:
                if not isinstance(raw_step, dict):
                    continue
                output_paths = raw_step.get("output_paths")
                if not isinstance(output_paths, dict):
                    continue
                for value in output_paths.values():
                    add_path(value)

    return collected


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read retry-run daily-chain recovery-chain summary and write a lightweight report."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--summary-path", default="", help="recovery-chain summary path")
    group.add_argument("--latest", action="store_true", help="resolve latest recovery-chain summary")
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
        "all_passed": None,
        "wrapper_exit_code": None,
        "failed_steps": [],
        "child_summary_paths_to_check": [],
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
                else (Path(args.search_dir).resolve() / "artists_answer_qa_retry_run_daily_chain_recovery_chain_report_latest_error.json")
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
        error = f"recovery_chain_summary_not_found:{summary_path}"
        report["notes"].append(error)
        print(f"[ERROR] {error}")
        write_json(output_path, report)
        print(f"[DONE] report={output_path}")
        return 1

    try:
        summary = load_json(summary_path)
    except Exception as exc:  # noqa: BLE001
        error = f"recovery_chain_summary_load_failed:{exc}"
        report["notes"].append(error)
        print(f"[ERROR] {error}")
        write_json(output_path, report)
        print(f"[DONE] report={output_path}")
        return 1

    report["all_passed"] = summary.get("all_passed")
    report["wrapper_exit_code"] = summary.get("wrapper_exit_code")

    notes = summary.get("notes", [])
    if isinstance(notes, list):
        report["notes"] = [str(note) for note in notes]
    elif notes is not None:
        report["notes"] = [str(notes)]

    failed_steps = _extract_failed_steps(summary)
    report["failed_steps"] = failed_steps

    if not isinstance(summary.get("steps"), list):
        report["warnings"].append("steps_missing_or_invalid")

    report["child_summary_paths_to_check"] = _collect_child_summary_paths(summary, summary_path, failed_steps)
    report["report_exit_code"] = 0
    report["exit_reason"] = "report_generated"
    write_json(output_path, report)

    print(
        "[REPORT] "
        f"all_passed={report.get('all_passed')} "
        f"wrapper_exit_code={report.get('wrapper_exit_code')} "
        f"failed_steps={len(report.get('failed_steps', []))}"
    )
    if report["failed_steps"]:
        print("[REPORT] failed_steps:")
        for step in report["failed_steps"]:
            print(
                f"  - {step.get('name')} "
                f"status={step.get('status')} exit_code={step.get('exit_code')}"
            )
    else:
        print("[REPORT] failed_steps: none")

    children = report.get("child_summary_paths_to_check")
    if isinstance(children, list) and children:
        print("[REPORT] child_summary_paths_to_check:")
        for path in children:
            print(f"  - {path}")
    else:
        print("[REPORT] child_summary_paths_to_check: none")

    print(f"[DONE] report={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
