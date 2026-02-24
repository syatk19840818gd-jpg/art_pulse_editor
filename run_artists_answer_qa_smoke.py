#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CONTEXT_SCRIPT = Path("run_build_artists_context_seed10.py")
ANSWER_SCRIPT = Path("run_answer_artists_seed10.py")
COMPARE_SCRIPT = Path("run_compare_artists_answers.py")

DEFAULT_K = 5
SUMMARY_DIR = Path("data/phase1_seed10/derived/answer")
SELF_SCRIPT = Path(__file__).resolve()


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


def latest_file(pattern: str) -> Path | None:
    candidates = sorted(Path().glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        return None
    return candidates[0]


def parse_output_path(stdout: str, marker: str) -> Path | None:
    pattern = re.compile(rf"^\[DONE\]\s+{re.escape(marker)}=(.+?)\s*$")
    for line in reversed(stdout.splitlines()):
        match = pattern.match(line.strip())
        if match:
            return Path(match.group(1).strip())
    return None


def tail_lines(text: str, max_lines: int = 20) -> str:
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text
    return "\n".join(lines[-max_lines:])


def sanitize_case_id(raw: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", raw.strip())
    return cleaned or "case"


def run_step(name: str, cmd: list[str], output_markers: dict[str, str]) -> dict[str, Any]:
    completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
    output_paths: dict[str, str] = {}
    for marker, target_key in output_markers.items():
        parsed = parse_output_path(completed.stdout, marker)
        if parsed is not None:
            output_paths[target_key] = str(parsed)

    status = "ok" if int(completed.returncode) == 0 else "failed"
    return {
        "name": name,
        "command": cmd,
        "exit_code": int(completed.returncode),
        "status": status,
        "output_paths": output_paths,
        "stdout_tail": tail_lines(completed.stdout),
        "stderr_tail": tail_lines(completed.stderr),
    }


def load_batch_cases(manifest_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    defaults: dict[str, Any] = {}

    if manifest_path.suffix.lower() == ".jsonl":
        cases: list[dict[str, Any]] = []
        with manifest_path.open("r", encoding="utf-8") as handle:
            for idx, line in enumerate(handle, start=1):
                raw = line.strip()
                if not raw:
                    continue
                obj = json.loads(raw)
                if not isinstance(obj, dict):
                    raise ValueError(f"batch_manifest_jsonl_line_not_object:{idx}")
                cases.append(obj)
        return cases, defaults

    manifest_obj = json.loads(manifest_path.read_text(encoding="utf-8"))
    if isinstance(manifest_obj, list):
        cases = manifest_obj
    elif isinstance(manifest_obj, dict):
        raw_defaults = manifest_obj.get("defaults", {})
        if raw_defaults:
            if not isinstance(raw_defaults, dict):
                raise ValueError("batch_manifest_defaults_not_object")
            defaults = raw_defaults
        if "cases" in manifest_obj:
            cases = manifest_obj.get("cases", [])
        else:
            cases = [manifest_obj]
    else:
        raise ValueError("batch_manifest_root_not_array_or_object")

    if not isinstance(cases, list):
        raise ValueError("batch_manifest_cases_not_array")

    normalized: list[dict[str, Any]] = []
    for idx, case in enumerate(cases, start=1):
        if not isinstance(case, dict):
            raise ValueError(f"batch_manifest_case_not_object:{idx}")
        merged = dict(defaults)
        merged.update(case)
        normalized.append(merged)
    return normalized, defaults


def build_skipped_step(
    name: str, reason: str, output_paths: dict[str, str] | None = None
) -> dict[str, Any]:
    return {
        "name": name,
        "command": [],
        "exit_code": 0,
        "status": "skipped",
        "output_paths": output_paths or {},
        "stdout_tail": "",
        "stderr_tail": "",
        "skip_reason": reason,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run artists answer QA smoke: context -> answer -> compare."
    )
    parser.add_argument("--question", help="question for artists answer")
    parser.add_argument("--query", help="query for artists retrieval")
    parser.add_argument("--context-path", help="fixed context json path")
    parser.add_argument("--batch-manifest", help="batch manifest path (.json or .jsonl)")
    parser.add_argument("--k", type=int, default=DEFAULT_K, help="top-k")
    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="pass through to compare CLI",
    )
    parser.add_argument(
        "--output-json",
        help="optional output summary path",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started_at = utc_now_iso()
    print(f"[START] artists QA smoke at {started_at}")

    timestamp = utc_timestamp_compact()
    summary_path = (
        Path(args.output_json)
        if args.output_json
        else SUMMARY_DIR / f"artists_answer_qa_smoke_summary_{timestamp}.json"
    )

    if args.batch_manifest:
        errors: list[str] = []
        warnings: list[str] = []
        steps: list[dict[str, Any]] = []
        manifest_path = Path(args.batch_manifest)

        if args.question or args.query or args.context_path:
            errors.append("batch_manifest_mode_conflicts_with_single_mode_args")
        if args.k <= 0:
            errors.append("invalid_k_must_be_positive")
        if not manifest_path.exists():
            errors.append(f"batch_manifest_not_found:{manifest_path}")

        cases: list[dict[str, Any]] = []
        manifest_defaults: dict[str, Any] = {}
        if not errors:
            try:
                cases, manifest_defaults = load_batch_cases(manifest_path)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"batch_manifest_load_failed:{exc}")

        batch_case_results: list[dict[str, Any]] = []
        if not errors:
            if not cases:
                errors.append("batch_manifest_no_cases")
            else:
                for index, case in enumerate(cases, start=1):
                    case_id = sanitize_case_id(
                        str(case.get("case_id") or case.get("id") or f"case_{index:03d}")
                    )
                    question = str(case.get("question") or "").strip()
                    query = str(case.get("query") or "").strip()
                    context_path = str(case.get("context_path") or "").strip()
                    has_query = bool(query)
                    has_context_path = bool(context_path)

                    case_errors: list[str] = []
                    if not question:
                        case_errors.append("missing_question")
                    if has_query == has_context_path:
                        case_errors.append("exactly_one_of_query_or_context_path_required")
                    case_k = case.get("k", args.k)
                    try:
                        case_k_int = int(case_k)
                        if case_k_int <= 0:
                            raise ValueError("non_positive")
                    except Exception:  # noqa: BLE001
                        case_errors.append(f"invalid_k:{case_k}")
                        case_k_int = args.k

                    raw_case_fail_on_regression = case.get(
                        "fail_on_regression", args.fail_on_regression
                    )
                    case_fail_on_regression = bool(raw_case_fail_on_regression)

                    case_summary_path = SUMMARY_DIR / (
                        f"artists_answer_qa_smoke_summary_{timestamp}_{case_id}.json"
                    )

                    if case_errors:
                        case_result = {
                            "case_index": index,
                            "case_id": case_id,
                            "question": question,
                            "query": query or None,
                            "context_path": context_path or None,
                            "k": case_k_int,
                            "fail_on_regression": case_fail_on_regression,
                            "fail_on_regression_effective": case_fail_on_regression,
                            "command": [],
                            "exit_code": 1,
                            "status": "failed",
                            "summary_path": str(case_summary_path),
                            "guard_passed": None,
                            "case_failure_kind": "invalid_case_config",
                            "errors": case_errors,
                            "stdout_tail": "",
                            "stderr_tail": "",
                        }
                        batch_case_results.append(case_result)
                        continue

                    cmd = [
                        sys.executable,
                        str(SELF_SCRIPT),
                        "--question",
                        question,
                        "--k",
                        str(case_k_int),
                        "--output-json",
                        str(case_summary_path),
                    ]
                    if has_query:
                        cmd.extend(["--query", query])
                    else:
                        cmd.extend(["--context-path", context_path])
                    if case_fail_on_regression:
                        cmd.append("--fail-on-regression")

                    completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
                    guard_passed: bool | None = None
                    case_failure_kind = "step_failed_or_unknown"
                    compare_summary_path: str | None = None
                    compare_exit_code: int | None = None
                    regression_reasons: list[str] = []
                    case_warnings: list[str] = []

                    if case_summary_path.exists():
                        try:
                            case_summary_obj = load_json(case_summary_path)
                            steps_obj = case_summary_obj.get("steps", [])
                            if isinstance(steps_obj, list):
                                compare_step = next(
                                    (
                                        step
                                        for step in steps_obj
                                        if isinstance(step, dict)
                                        and str(step.get("name")) == "answer_compare"
                                    ),
                                    None,
                                )
                                if isinstance(compare_step, dict):
                                    compare_status = str(compare_step.get("status", ""))
                                    output_paths_obj = compare_step.get("output_paths", {})
                                    if isinstance(output_paths_obj, dict):
                                        raw_compare_summary_path = output_paths_obj.get(
                                            "compare_summary_path"
                                        )
                                        if isinstance(raw_compare_summary_path, str):
                                            compare_summary_path = raw_compare_summary_path

                                    if compare_status == "ok" and compare_summary_path:
                                        compare_summary_obj = load_json(
                                            Path(compare_summary_path)
                                        )
                                        guard_passed_raw = compare_summary_obj.get("guard_passed")
                                        if isinstance(guard_passed_raw, bool):
                                            guard_passed = guard_passed_raw
                                        compare_exit_raw = compare_summary_obj.get(
                                            "compare_exit_code"
                                        )
                                        if isinstance(compare_exit_raw, int):
                                            compare_exit_code = compare_exit_raw
                                        raw_regression_reasons = compare_summary_obj.get(
                                            "regression_reasons", []
                                        )
                                        if isinstance(raw_regression_reasons, list):
                                            regression_reasons = [
                                                str(reason)
                                                for reason in raw_regression_reasons
                                            ]

                            if guard_passed is False:
                                case_failure_kind = "regression_guard_failed"
                            elif int(completed.returncode) == 0:
                                case_failure_kind = "none"
                            elif case_summary_obj.get("qa_input_mode") == "query_rebuild":
                                case_failure_kind = "query_rebuild_failed"
                            elif case_summary_obj.get("qa_input_mode") == "fixed_context":
                                case_failure_kind = "fixed_context_failed"
                        except Exception as exc:  # noqa: BLE001
                            case_warnings.append(f"case_summary_parse_failed:{exc}")
                    else:
                        case_warnings.append("case_summary_not_found")

                    if (
                        int(completed.returncode) != 0
                        and guard_passed is None
                        and case_failure_kind == "step_failed_or_unknown"
                    ):
                        case_failure_kind = "step_failed_or_unknown"

                    case_result = {
                        "case_index": index,
                        "case_id": case_id,
                        "question": question,
                        "query": query or None,
                        "context_path": context_path or None,
                        "k": case_k_int,
                        "fail_on_regression": case_fail_on_regression,
                        "fail_on_regression_effective": case_fail_on_regression,
                        "command": cmd,
                        "exit_code": int(completed.returncode),
                        "status": "ok" if int(completed.returncode) == 0 else "failed",
                        "summary_path": str(case_summary_path),
                        "guard_passed": guard_passed,
                        "compare_summary_path": compare_summary_path,
                        "compare_exit_code": compare_exit_code,
                        "regression_reasons": regression_reasons,
                        "case_failure_kind": case_failure_kind,
                        "warnings": case_warnings,
                        "stdout_tail": tail_lines(completed.stdout),
                        "stderr_tail": tail_lines(completed.stderr),
                    }
                    batch_case_results.append(case_result)

        passed_cases = sum(1 for case in batch_case_results if case.get("exit_code") == 0)
        failed_cases = len(batch_case_results) - passed_cases
        wrapper_exit_code = 0 if not errors and failed_cases == 0 else 1

        raw_manifest_fail_on_regression_default = manifest_defaults.get(
            "fail_on_regression", args.fail_on_regression
        )
        manifest_fail_on_regression_default = bool(raw_manifest_fail_on_regression_default)
        raw_manifest_k_default = manifest_defaults.get("k", args.k)
        try:
            manifest_k_default = int(raw_manifest_k_default)
        except (TypeError, ValueError):
            manifest_k_default = args.k

        batch_summary = {
            "started_at": started_at,
            "completed_at": utc_now_iso(),
            "source_cli": "run_artists_answer_qa_smoke.py",
            "qa_input_mode": "batch_manifest",
            "batch_manifest_path": str(manifest_path),
            "k_default": manifest_k_default,
            "fail_on_regression_default": manifest_fail_on_regression_default,
            "total_cases": len(batch_case_results),
            "passed_cases": passed_cases,
            "failed_cases": failed_cases,
            "all_passed": wrapper_exit_code == 0,
            "wrapper_exit_code": wrapper_exit_code,
            "cases": batch_case_results,
            "steps": steps,
            "warnings": warnings,
            "errors": errors,
            "output_paths": {
                "qa_summary_json": str(summary_path),
            },
        }
        write_json(summary_path, batch_summary)
        print(
            "[DONE] artists QA smoke batch complete. "
            f"all_passed={batch_summary['all_passed']} total_cases={batch_summary['total_cases']}"
        )
        print(f"[DONE] summary={summary_path}")
        return wrapper_exit_code

    query_value = (args.query or "").strip()
    context_path_value = (args.context_path or "").strip()
    question_value = (args.question or "").strip()
    has_query = bool(query_value)
    has_context_path = bool(context_path_value)

    errors: list[str] = []
    if not question_value:
        errors.append("missing_question")
    if args.k <= 0:
        errors.append("invalid_k_must_be_positive")
    if has_query == has_context_path:
        errors.append("exactly_one_of_query_or_context_path_required")
    context_path = Path(context_path_value) if has_context_path else None
    if context_path is not None and not context_path.exists():
        errors.append(f"context_path_not_found:{context_path}")

    if errors:
        for error in errors:
            print(f"[ERROR] {error}")
        summary = {
            "started_at": started_at,
            "completed_at": utc_now_iso(),
            "source_cli": "run_artists_answer_qa_smoke.py",
            "question": question_value,
            "query": query_value,
            "query_effective": query_value or None,
            "context_path_effective": str(context_path) if context_path else None,
            "qa_input_mode": "invalid_args",
            "k_requested": args.k,
            "fail_on_regression": bool(args.fail_on_regression),
            "all_passed": False,
            "wrapper_exit_code": 1,
            "steps": [],
            "warnings": [],
            "errors": errors,
            "output_paths": {
                "qa_summary_json": str(summary_path),
            },
        }
        write_json(summary_path, summary)
        print(f"[DONE] summary={summary_path}")
        return 1

    qa_input_mode = "query_rebuild" if has_query else "fixed_context"

    warnings: list[str] = []
    steps: list[dict[str, Any]] = []

    context_path_effective: Path | None = context_path
    context_summary_path: Path | None = None
    if qa_input_mode == "query_rebuild":
        context_cmd = [
            sys.executable,
            str(CONTEXT_SCRIPT),
            "--query",
            query_value,
            "--k",
            str(args.k),
        ]
        context_step = run_step(
            name="context_build",
            cmd=context_cmd,
            output_markers={"context": "context_path", "summary": "context_summary_path"},
        )
        steps.append(context_step)

        if context_step["exit_code"] == 0:
            raw_context = context_step["output_paths"].get("context_path")
            raw_context_summary = context_step["output_paths"].get("context_summary_path")
            if raw_context:
                context_path_effective = Path(raw_context)
            if raw_context_summary:
                context_summary_path = Path(raw_context_summary)

            if context_path_effective is None or not context_path_effective.exists():
                context_path_effective = latest_file(
                    "data/phase1_seed10/derived/context/artists_text_context_*.json"
                )
                if context_path_effective is not None:
                    warnings.append("context_path_resolved_from_latest_file")
            if context_summary_path is None or not context_summary_path.exists():
                context_summary_path = latest_file(
                    "data/phase1_seed10/derived/context/artists_text_context_summary_*.json"
                )
                if context_summary_path is not None:
                    warnings.append("context_summary_path_resolved_from_latest_file")
    else:
        context_summary_candidate = Path(
            str(context_path_effective).replace(
                "/artists_text_context_", "/artists_text_context_summary_"
            )
        )
        if context_summary_candidate.exists():
            context_summary_path = context_summary_candidate
        steps.append(
            build_skipped_step(
                "context_build",
                "fixed_context_mode_provided",
                {
                    "context_path": str(context_path_effective),
                    "context_summary_path": str(context_summary_path)
                    if context_summary_path is not None
                    else "",
                },
            )
        )

    if context_path_effective is None or not context_path_effective.exists():
        warnings.append("context_build_output_missing")
        steps.append(build_skipped_step("answer_generate", "context_build_failed_or_missing_output"))
        steps.append(build_skipped_step("answer_compare", "context_build_failed_or_missing_output"))
    else:
        answer_cmd = [
            sys.executable,
            str(ANSWER_SCRIPT),
            "--question",
            question_value,
            "--context-path",
            str(context_path_effective),
            "--k",
            str(args.k),
            "--fail-on-invalid-output",
        ]
        answer_step = run_step(
            name="answer_generate",
            cmd=answer_cmd,
            output_markers={"output": "answer_output_path", "summary": "answer_summary_path"},
        )
        steps.append(answer_step)

        if qa_input_mode == "fixed_context":
            steps.append(
                build_skipped_step(
                    "answer_compare",
                    "compare_skipped_in_fixed_context_mode",
                )
            )
            if args.fail_on_regression:
                warnings.append("fail_on_regression_ignored_without_query")
        else:
            compare_cmd = [
                sys.executable,
                str(COMPARE_SCRIPT),
                "--question",
                question_value,
                "--query",
                query_value,
                "--context-path",
                str(context_path_effective),
                "--k",
                str(args.k),
            ]
            if args.fail_on_regression:
                compare_cmd.append("--fail-on-regression")

            compare_step = run_step(
                name="answer_compare",
                cmd=compare_cmd,
                output_markers={"summary": "compare_summary_path"},
            )
            steps.append(compare_step)

    has_failed_step = any(step.get("status") == "failed" for step in steps)
    all_passed = not has_failed_step
    wrapper_exit_code = 0 if all_passed else 1

    summary = {
        "started_at": started_at,
        "completed_at": utc_now_iso(),
        "source_cli": "run_artists_answer_qa_smoke.py",
        "question": question_value,
        "query": query_value,
        "query_effective": query_value or None,
        "qa_input_mode": qa_input_mode,
        "context_path_effective": str(context_path_effective)
        if context_path_effective is not None
        else None,
        "context_summary_path_effective": str(context_summary_path)
        if context_summary_path is not None
        else None,
        "k_requested": args.k,
        "fail_on_regression": bool(args.fail_on_regression),
        "all_passed": all_passed,
        "wrapper_exit_code": wrapper_exit_code,
        "steps": steps,
        "warnings": warnings,
        "output_paths": {
            "qa_summary_json": str(summary_path),
        },
    }
    write_json(summary_path, summary)

    print(
        "[DONE] artists QA smoke complete. "
        f"all_passed={all_passed} wrapper_exit_code={wrapper_exit_code}"
    )
    print(f"[DONE] summary={summary_path}")
    return wrapper_exit_code


if __name__ == "__main__":
    raise SystemExit(main())
