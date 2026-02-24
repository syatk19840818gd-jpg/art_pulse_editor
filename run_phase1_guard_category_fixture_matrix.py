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

DEFAULT_MANIFEST_PATH = "tests/fixtures/phase1_guard/category_fixture_manifest.json"
DEFAULT_LOGS_DIR = "data/phase1_seed10/logs"
OUTPUT_TEMPLATE = "phase1_guard_category_fixture_matrix_{timestamp}.json"
GUARD_OUTPUT_TEMPLATE = "phase1_guard_summary_category_fixture_{case_name}_{timestamp}.json"
SOURCE_CLI = "run_phase1_guard_category_fixture_matrix.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run guard category-profile fixtures and validate expected exit codes + summary keys."
    )
    parser.add_argument(
        "--manifest-path",
        default=DEFAULT_MANIFEST_PATH,
        help=f"fixture manifest path (default: {DEFAULT_MANIFEST_PATH})",
    )
    parser.add_argument(
        "--logs-dir",
        default=DEFAULT_LOGS_DIR,
        help=f"directory to save matrix/guard summaries (default: {DEFAULT_LOGS_DIR})",
    )
    parser.add_argument(
        "--output-path",
        default="",
        help="optional matrix summary output path (default: <logs-dir>/phase1_guard_category_fixture_matrix_<timestamp>.json)",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="stop matrix execution at first case failure (exit mismatch or summary check mismatch)",
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


def as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return default


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
    recognized = {"--fail-on-mismatch"}
    return {token for token in tokens if token in recognized}


def get_nested_value(obj: dict[str, Any], path: str) -> tuple[bool, Any]:
    current: Any = obj
    if not path:
        return True, current
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return False, None
        current = current[part]
    return True, current


def is_non_empty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (str, list, dict, tuple, set)):
        return len(value) > 0
    return True


def check_contains(container: Any, expected: Any) -> bool:
    if isinstance(container, list):
        return expected in container
    if isinstance(container, str):
        return str(expected) in container
    if isinstance(container, dict):
        return expected in container or expected in container.values()
    return False


def evaluate_summary_checks(summary_obj: dict[str, Any], checks_raw: Any) -> tuple[bool, list[str]]:
    if checks_raw is None:
        return True, []
    if not isinstance(checks_raw, list):
        return False, ["summary_checks_not_list"]

    failures: list[str] = []
    for index, raw_check in enumerate(checks_raw, start=1):
        if not isinstance(raw_check, dict):
            failures.append(f"check_{index}:invalid_check_object")
            continue
        path = as_text(raw_check.get("path"))
        if not path:
            failures.append(f"check_{index}:missing_path")
            continue

        found, value = get_nested_value(summary_obj, path)

        if "exists" in raw_check:
            expected_exists = as_bool(raw_check.get("exists"), default=False)
            if found != expected_exists:
                failures.append(f"{path}:exists_mismatch:expected={expected_exists}:actual={found}")
                continue
            if not expected_exists:
                # expected missing and confirmed missing => no need to evaluate other predicates
                continue

        if not found:
            failures.append(f"{path}:missing")
            continue

        if "equals" in raw_check and value != raw_check.get("equals"):
            failures.append(f"{path}:equals_mismatch:expected={raw_check.get('equals')!r}:actual={value!r}")

        if "non_empty" in raw_check:
            expected_non_empty = as_bool(raw_check.get("non_empty"), default=False)
            actual_non_empty = is_non_empty(value)
            if expected_non_empty != actual_non_empty:
                failures.append(
                    f"{path}:non_empty_mismatch:expected={expected_non_empty}:actual={actual_non_empty}"
                )

        if "contains" in raw_check and not check_contains(value, raw_check.get("contains")):
            failures.append(f"{path}:contains_missing:{raw_check.get('contains')!r}")

    return len(failures) == 0, failures


def build_guard_command(
    *,
    repo_root: Path,
    logs_dir: Path,
    target_year: int,
    category: str,
    output_summary: Path,
    fail_on_mismatch: bool,
    recommended_command: str,
) -> list[str]:
    flags = parse_recommended_flags(recommended_command)
    if fail_on_mismatch:
        flags.add("--fail-on-mismatch")

    command = [
        sys.executable,
        str((repo_root / "run_compare_phase1_guard.py").resolve()),
        "--target-year",
        str(target_year),
        "--logs-dir",
        str(logs_dir),
        "--category",
        category,
        "--summary-path",
        str(output_summary),
    ]
    if "--fail-on-mismatch" in flags:
        command.append("--fail-on-mismatch")
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
                    "summary_checks_passed": False,
                    "summary_check_failures": ["CASE_NOT_OBJECT"],
                    "pass_fail": False,
                    "command": "",
                    "output_summary_path": None,
                }
            )
            print(f"[CASE] {case_name} expected=? actual=? checks=NG")
            if args.fail_fast:
                stop_reason = "fail_fast:CASE_NOT_OBJECT"
                break
            continue

        case_name = as_text(raw_case.get("case_name")) or as_text(raw_case.get("case_id")) or f"case_{index}"
        description = as_text(raw_case.get("description"))
        logs_dir_raw = as_text(raw_case.get("logs_dir"))
        category = as_text(raw_case.get("category"), default="artists_text")
        target_year = safe_int(raw_case.get("target_year"))
        expected_exit_code = safe_int(raw_case.get("expected_exit_code"))
        fail_on_mismatch = as_bool(raw_case.get("fail_on_mismatch"), default=False)
        recommended_command = as_text(raw_case.get("recommended_command"))
        expected_summary_checks = raw_case.get("expected_summary_checks")

        case_timestamp = f"{timestamp}_{index:02d}"
        output_summary = logs_dir / GUARD_OUTPUT_TEMPLATE.format(
            case_name=sanitize_case_name(case_name),
            timestamp=case_timestamp,
        )

        required_fields_ok = bool(logs_dir_raw) and expected_exit_code is not None and target_year is not None
        if not required_fields_ok:
            failed_cases += 1
            case_results.append(
                {
                    "case_name": case_name,
                    "description": description,
                    "expected_exit_code": expected_exit_code,
                    "actual_exit_code": None,
                    "summary_checks_passed": False,
                    "summary_check_failures": ["MISSING_REQUIRED_CASE_FIELDS"],
                    "pass_fail": False,
                    "command": "",
                    "output_summary_path": str(output_summary),
                }
            )
            print(f"[CASE] {case_name} expected={expected_exit_code} actual=? checks=NG")
            if args.fail_fast:
                stop_reason = "fail_fast:MISSING_REQUIRED_CASE_FIELDS"
                break
            continue

        case_logs_dir = resolve_path(logs_dir_raw, repo_root)
        command = build_guard_command(
            repo_root=repo_root,
            logs_dir=case_logs_dir,
            target_year=target_year,
            category=category,
            output_summary=output_summary,
            fail_on_mismatch=fail_on_mismatch,
            recommended_command=recommended_command,
        )
        command_text = " ".join(shlex.quote(part) for part in command)

        proc = subprocess.run(command, cwd=repo_root, check=False)
        actual_exit_code = int(proc.returncode)

        summary_obj, summary_load_error = load_manifest(output_summary)
        if summary_load_error:
            summary_checks_passed = False
            summary_check_failures = [f"SUMMARY_LOAD_ERROR:{summary_load_error}"]
        else:
            assert isinstance(summary_obj, dict)
            summary_checks_passed, summary_check_failures = evaluate_summary_checks(summary_obj, expected_summary_checks)

        exit_code_matches = actual_exit_code == expected_exit_code
        pass_fail = exit_code_matches and summary_checks_passed

        case_results.append(
            {
                "case_name": case_name,
                "description": description,
                "expected_exit_code": expected_exit_code,
                "actual_exit_code": actual_exit_code,
                "exit_code_match": exit_code_matches,
                "summary_checks_passed": summary_checks_passed,
                "summary_check_failures": summary_check_failures,
                "pass_fail": pass_fail,
                "command": command_text,
                "output_summary_path": str(output_summary),
            }
        )

        if pass_fail:
            passed_cases += 1
            print(
                f"[CASE] {case_name} expected={expected_exit_code} actual={actual_exit_code} "
                "checks=OK"
            )
        else:
            failed_cases += 1
            print(
                f"[CASE] {case_name} expected={expected_exit_code} actual={actual_exit_code} "
                "checks=NG"
            )
            if args.fail_fast:
                stop_reason = f"fail_fast:case_failed:{case_name}"
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
