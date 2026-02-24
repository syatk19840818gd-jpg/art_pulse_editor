#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

from phase1_guard_common import EXIT_CODE_MEANING, resolve_logs_dir, utc_now_iso, utc_timestamp_compact, write_summary_json

DEFAULT_MANIFEST_PATH = "tests/fixtures/phase1_guard/fixture_manifest.json"
DEFAULT_LOGS_DIR = "data/phase1_seed10/logs"
OUTPUT_TEMPLATE = "phase1_guard_fixture_matrix_{timestamp}.json"
HISTORY_OUTPUT_TEMPLATE = "phase1_guard_history_compare_fixture_{case_name}_{timestamp}.json"
SOURCE_CLI = "run_phase1_guard_fixture_matrix.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Phase1 guard history fixture matrix and verify expected exit codes."
    )
    parser.add_argument(
        "--manifest-path",
        default=DEFAULT_MANIFEST_PATH,
        help=f"fixture manifest path (default: {DEFAULT_MANIFEST_PATH})",
    )
    parser.add_argument(
        "--logs-dir",
        default=DEFAULT_LOGS_DIR,
        help=f"directory to save matrix/history summaries (default: {DEFAULT_LOGS_DIR})",
    )
    parser.add_argument(
        "--output-path",
        default="",
        help="optional matrix summary output path (default: <logs-dir>/phase1_guard_fixture_matrix_<timestamp>.json)",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="stop matrix execution at first expected/actual exit code mismatch",
    )
    return parser.parse_args()


def load_manifest(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, f"MISSING_MANIFEST:{path}"
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, f"MANIFEST_JSON_DECODE_ERROR:{exc}"
    except OSError as exc:
        return None, f"MANIFEST_OS_ERROR:{exc}"
    if not isinstance(obj, dict):
        return None, f"MANIFEST_INVALID_ROOT_TYPE:{type(obj).__name__}"
    return obj, None


def safe_int(value: Any) -> int | None:
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


def as_text(value: Any, default: str = "") -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return default
    return str(value)


def resolve_path(value: str, repo_root: Path) -> Path:
    raw = Path(value).expanduser()
    if raw.is_absolute():
        return raw.resolve()
    return (repo_root / raw).resolve()


def sanitize_case_name(case_name: str) -> str:
    safe_chars = []
    for ch in case_name:
        if ch.isalnum() or ch in {"_", "-"}:
            safe_chars.append(ch)
        else:
            safe_chars.append("_")
    result = "".join(safe_chars).strip("_")
    return result or "case"


def parse_recommended_flags(command_text: str) -> set[str]:
    if not command_text.strip():
        return set()
    try:
        tokens = shlex.split(command_text)
    except ValueError:
        return set()
    recognized = {"--fail-on-regression", "--strict-compatibility"}
    return {token for token in tokens if token in recognized}


def build_history_command(
    *,
    repo_root: Path,
    current_summary: Path,
    baseline_summary: Path,
    output_summary: Path,
    expected_exit_code: int,
    recommended_command: str,
) -> list[str]:
    flags = parse_recommended_flags(recommended_command)
    if "--fail-on-regression" not in flags and "--strict-compatibility" not in flags:
        if expected_exit_code == 3:
            flags.add("--strict-compatibility")
        else:
            flags.add("--fail-on-regression")

    command = [
        sys.executable,
        str((repo_root / "run_compare_phase1_guard_history.py").resolve()),
        "--current-summary",
        str(current_summary),
        "--baseline-summary",
        str(baseline_summary),
        "--output-path",
        str(output_summary),
    ]
    if "--fail-on-regression" in flags:
        command.append("--fail-on-regression")
    if "--strict-compatibility" in flags:
        command.append("--strict-compatibility")
    return command


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parent
    timestamp = utc_timestamp_compact()

    manifest_path = resolve_path(args.manifest_path, repo_root)
    logs_dir = resolve_logs_dir(args.logs_dir)
    output_path = (
        resolve_logs_dir(args.output_path)
        if args.output_path
        else logs_dir / OUTPUT_TEMPLATE.format(timestamp=timestamp)
    )

    manifest_obj, manifest_error = load_manifest(manifest_path)
    if manifest_error:
        payload = {
            "generated_at": utc_now_iso(),
            "source_cli": SOURCE_CLI,
            "fixture_manifest_path": str(manifest_path),
            "manifest_load_error": manifest_error,
            "total_cases": 0,
            "executed_cases": 0,
            "passed_cases": 0,
            "failed_cases": 0,
            "fail_fast": bool(args.fail_fast),
            "all_cases_passed": False,
            "cases": [],
            "exit_code_meaning": EXIT_CODE_MEANING,
            "wrapper_exit_code_meaning": {"0": "matrix_pass", "1": "matrix_fail"},
            "wrapper_exit_code": 1,
        }
        write_summary_json(output_path, payload)
        print(f"[ERROR] {manifest_error}")
        print(f"[MATRIX] summary={output_path}")
        return 1

    raw_cases = manifest_obj.get("cases")
    if not isinstance(raw_cases, list):
        payload = {
            "generated_at": utc_now_iso(),
            "source_cli": SOURCE_CLI,
            "fixture_manifest_path": str(manifest_path),
            "manifest_load_error": "MANIFEST_CASES_NOT_LIST",
            "total_cases": 0,
            "executed_cases": 0,
            "passed_cases": 0,
            "failed_cases": 0,
            "fail_fast": bool(args.fail_fast),
            "all_cases_passed": False,
            "cases": [],
            "exit_code_meaning": EXIT_CODE_MEANING,
            "wrapper_exit_code_meaning": {"0": "matrix_pass", "1": "matrix_fail"},
            "wrapper_exit_code": 1,
        }
        write_summary_json(output_path, payload)
        print("[ERROR] MANIFEST_CASES_NOT_LIST")
        print(f"[MATRIX] summary={output_path}")
        return 1

    case_results: list[dict[str, Any]] = []
    passed_cases = 0
    failed_cases = 0
    stop_reason = ""

    for index, raw_case in enumerate(raw_cases, start=1):
        if not isinstance(raw_case, dict):
            failed_cases += 1
            case_name = f"case_{index}"
            case_results.append(
                {
                    "case_name": case_name,
                    "description": "invalid manifest case (not dict)",
                    "expected_exit_code": None,
                    "actual_exit_code": None,
                    "pass_fail": False,
                    "command": "",
                    "output_summary_path": None,
                    "error": "CASE_NOT_OBJECT",
                }
            )
            print(f"[CASE] {case_name} expected=? actual=? NG")
            if args.fail_fast:
                stop_reason = "fail_fast:CASE_NOT_OBJECT"
                break
            continue

        case_name = as_text(raw_case.get("case_name")) or as_text(raw_case.get("case_id")) or f"case_{index}"
        description = as_text(raw_case.get("description"))
        current_summary_raw = as_text(raw_case.get("current_summary"))
        baseline_summary_raw = as_text(raw_case.get("baseline_summary"))
        expected_exit_code = safe_int(raw_case.get("expected_exit_code"))
        recommended_command = as_text(raw_case.get("recommended_command"))

        case_timestamp = f"{timestamp}_{index:02d}"
        output_summary = logs_dir / HISTORY_OUTPUT_TEMPLATE.format(
            case_name=sanitize_case_name(case_name),
            timestamp=case_timestamp,
        )

        if not current_summary_raw or not baseline_summary_raw or expected_exit_code is None:
            failed_cases += 1
            case_results.append(
                {
                    "case_name": case_name,
                    "description": description,
                    "expected_exit_code": expected_exit_code,
                    "actual_exit_code": None,
                    "pass_fail": False,
                    "command": "",
                    "output_summary_path": str(output_summary),
                    "error": "MISSING_REQUIRED_CASE_FIELDS",
                }
            )
            print(f"[CASE] {case_name} expected={expected_exit_code} actual=? NG")
            if args.fail_fast:
                stop_reason = "fail_fast:MISSING_REQUIRED_CASE_FIELDS"
                break
            continue

        current_summary = resolve_path(current_summary_raw, repo_root)
        baseline_summary = resolve_path(baseline_summary_raw, repo_root)

        command = build_history_command(
            repo_root=repo_root,
            current_summary=current_summary,
            baseline_summary=baseline_summary,
            output_summary=output_summary,
            expected_exit_code=expected_exit_code,
            recommended_command=recommended_command,
        )
        command_text = " ".join(shlex.quote(part) for part in command)

        proc = subprocess.run(command, cwd=repo_root, check=False)
        actual_exit_code = int(proc.returncode)
        pass_fail = actual_exit_code == expected_exit_code

        case_results.append(
            {
                "case_name": case_name,
                "description": description,
                "expected_exit_code": expected_exit_code,
                "actual_exit_code": actual_exit_code,
                "pass_fail": pass_fail,
                "command": command_text,
                "output_summary_path": str(output_summary),
            }
        )

        if pass_fail:
            passed_cases += 1
            print(f"[CASE] {case_name} expected={expected_exit_code} actual={actual_exit_code} OK")
        else:
            failed_cases += 1
            print(f"[CASE] {case_name} expected={expected_exit_code} actual={actual_exit_code} NG")
            if args.fail_fast:
                stop_reason = f"fail_fast:expected_{expected_exit_code}_actual_{actual_exit_code}:{case_name}"
                break

    executed_cases = len(case_results)
    total_cases = len(raw_cases)
    all_cases_passed = failed_cases == 0 and executed_cases == total_cases
    wrapper_exit_code = 0 if all_cases_passed else 1

    summary_payload = {
        "generated_at": utc_now_iso(),
        "source_cli": SOURCE_CLI,
        "fixture_manifest_path": str(manifest_path),
        "total_cases": total_cases,
        "executed_cases": executed_cases,
        "passed_cases": passed_cases,
        "failed_cases": failed_cases,
        "fail_fast": bool(args.fail_fast),
        "all_cases_passed": all_cases_passed,
        "cases": case_results,
        "exit_code_meaning": EXIT_CODE_MEANING,
        "wrapper_exit_code_meaning": {"0": "matrix_pass", "1": "matrix_fail"},
        "wrapper_exit_code": wrapper_exit_code,
        "stop_reason": stop_reason if stop_reason else None,
    }
    write_summary_json(output_path, summary_payload)

    print(
        "[MATRIX] "
        f"total={total_cases} passed={passed_cases} failed={failed_cases} "
        f"all_cases_passed={'true' if all_cases_passed else 'false'}"
    )
    print(f"[MATRIX] summary={output_path}")

    return wrapper_exit_code


if __name__ == "__main__":
    raise SystemExit(main())
