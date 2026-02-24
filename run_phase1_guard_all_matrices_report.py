#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from phase1_guard_common import resolve_logs_dir, utc_now_iso, write_summary_json

DEFAULT_LOGS_DIR = "data/phase1_seed10/logs"
DEFAULT_GLOB = "phase1_guard_all_matrices_*.json"
SOURCE_CLI = "run_phase1_guard_all_matrices_report.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read an integrated all-matrices summary and print a compact report for CI/local triage."
        )
    )
    parser.add_argument("--summary-path", default="", help="path to integrated summary JSON")
    parser.add_argument(
        "--latest",
        action="store_true",
        help="resolve latest integrated summary from --logs-dir",
    )
    parser.add_argument(
        "--logs-dir",
        default=DEFAULT_LOGS_DIR,
        help=f"search directory for --latest (default: {DEFAULT_LOGS_DIR})",
    )
    parser.add_argument(
        "--output-json",
        default="",
        help="optional report output JSON path",
    )
    parser.add_argument(
        "--fail-on-failed-matrix",
        action="store_true",
        help="return exit 1 when summary is readable but all_passed=false",
    )
    return parser.parse_args()


def _load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, f"summary_not_found:{path}"
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, f"summary_json_decode_error:{exc}"
    except OSError as exc:
        return None, f"summary_os_error:{exc}"
    if not isinstance(obj, dict):
        return None, f"summary_root_not_object:{type(obj).__name__}"
    return obj, None


def _resolve_latest_summary(logs_dir: Path) -> tuple[Path | None, str | None]:
    candidates = [p for p in logs_dir.glob(DEFAULT_GLOB) if p.is_file()]
    if not candidates:
        return None, f"latest_summary_not_found:{logs_dir}/{DEFAULT_GLOB}"
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    return latest.resolve(), None


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        if lowered in {"false", "0", "no", "off"}:
            return False
    if isinstance(value, int):
        return value != 0
    return False


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


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _extract_report(summary: dict[str, Any], summary_path: Path) -> dict[str, Any]:
    all_passed = _as_bool(summary.get("all_passed"))
    wrapper_exit_code = _as_int(summary.get("wrapper_exit_code"))
    execution_order = _as_str_list(summary.get("execution_order"))

    raw_matrices = summary.get("matrices")
    matrices = raw_matrices if isinstance(raw_matrices, list) else []

    failed_matrices: list[dict[str, Any]] = []
    child_summary_paths: list[str] = []

    for row in matrices:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name", ""))
        actual_exit_code = _as_int(row.get("actual_exit_code"))
        pass_fail = str(row.get("pass_fail", ""))
        summary_path_value = row.get("summary_path")
        summary_path_text = str(summary_path_value) if isinstance(summary_path_value, str) else None

        if summary_path_text:
            child_summary_paths.append(summary_path_text)

        if pass_fail != "pass":
            failed_matrices.append(
                {
                    "name": name,
                    "actual_exit_code": actual_exit_code,
                    "summary_path": summary_path_text,
                }
            )

    report = {
        "checked_at": utc_now_iso(),
        "source_cli": SOURCE_CLI,
        "input_summary_path": str(summary_path),
        "all_passed": all_passed,
        "wrapper_exit_code": wrapper_exit_code,
        "execution_order": execution_order,
        "failed_matrices": failed_matrices,
        "failed_matrices_count": len(failed_matrices),
        "child_summary_paths": child_summary_paths,
        "warnings": summary.get("warnings") if isinstance(summary.get("warnings"), list) else [],
    }
    return report


def _print_report(report: dict[str, Any]) -> None:
    print(f"[REPORT] input_summary={report['input_summary_path']}")
    print(
        f"[REPORT] all_passed={report['all_passed']} wrapper_exit_code={report['wrapper_exit_code']} "
        f"failed_matrices_count={report['failed_matrices_count']}"
    )
    print(f"[REPORT] execution_order={report['execution_order']}")

    failed_matrices = report.get("failed_matrices")
    if isinstance(failed_matrices, list) and failed_matrices:
        print("[REPORT] failed_matrices:")
        for row in failed_matrices:
            if not isinstance(row, dict):
                continue
            print(
                f"  - name={row.get('name')} actual_exit_code={row.get('actual_exit_code')} "
                f"summary_path={row.get('summary_path')}"
            )
    else:
        print("[REPORT] failed_matrices: none")

    paths = report.get("child_summary_paths")
    if isinstance(paths, list) and paths:
        print("[REPORT] child_summary_paths:")
        for path in paths:
            print(f"  - {path}")


def main() -> int:
    args = parse_args()
    logs_dir = resolve_logs_dir(args.logs_dir)

    if args.summary_path:
        summary_path = resolve_logs_dir(args.summary_path)
    elif args.latest or not args.summary_path:
        latest_path, latest_error = _resolve_latest_summary(logs_dir)
        if latest_error:
            print(f"[ERROR] {latest_error}")
            return 1
        assert latest_path is not None
        summary_path = latest_path
    else:
        print("[ERROR] missing_input: set --summary-path or --latest")
        return 1

    summary_obj, load_error = _load_json(summary_path)
    if load_error:
        print(f"[ERROR] {load_error}")
        return 1
    assert summary_obj is not None

    report = _extract_report(summary_obj, summary_path)
    exit_policy = "fail_on_failed_matrix" if args.fail_on_failed_matrix else "default_report_only"
    if args.fail_on_failed_matrix and not _as_bool(report.get("all_passed")):
        exit_reason = "failed_matrix_detected"
        exit_code = 1
    else:
        exit_reason = "report_generated"
        exit_code = 0

    report["fail_on_failed_matrix"] = bool(args.fail_on_failed_matrix)
    report["exit_policy"] = exit_policy
    report["exit_reason"] = exit_reason
    report["report_exit_code"] = exit_code
    report["report_exit_code_meaning"] = {
        "0": "report_generated",
        "1": "summary_not_found_or_invalid_or_failed_matrix_detected",
    }

    _print_report(report)
    print(f"[REPORT] exit_policy={exit_policy} exit_reason={exit_reason} exit_code={exit_code}")

    if args.output_json:
        output_path = resolve_logs_dir(args.output_json)
        write_summary_json(output_path, report)
        print(f"[REPORT] output_json={output_path}")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
