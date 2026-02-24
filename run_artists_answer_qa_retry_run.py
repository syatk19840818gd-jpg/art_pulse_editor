#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_SEARCH_DIR = Path("data/phase1_seed10/derived/answer")
DEFAULT_GLOB = "artists_answer_qa_smoke_summary_*_retry_manifest.json"
DEFAULT_SUMMARY_DIR = Path("data/phase1_seed10/derived/answer")
QA_SMOKE_SCRIPT = Path("run_artists_answer_qa_smoke.py")
SOURCE_CLI = "run_artists_answer_qa_retry_run.py"


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


def resolve_latest_manifest(search_dir: Path, pattern: str) -> tuple[Path | None, str | None]:
    candidates = [p for p in search_dir.glob(pattern) if p.is_file()]
    if not candidates:
        return None, f"latest_retry_manifest_not_found:{search_dir}/{pattern}"
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    return latest.resolve(), None


def as_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else None
    return str(value)


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return False


def normalize_case(case_obj: Any, index: int) -> tuple[dict[str, Any] | None, str | None, str]:
    fallback_case_id = f"case_{index:03d}"
    if not isinstance(case_obj, dict):
        return None, "case_not_object", fallback_case_id

    case_id = as_optional_str(case_obj.get("case_id")) or fallback_case_id
    question = as_optional_str(case_obj.get("question"))
    query = as_optional_str(case_obj.get("query"))
    context_path = as_optional_str(case_obj.get("context_path"))
    fail_on_regression = as_bool(case_obj.get("fail_on_regression"))

    if not question:
        return None, "missing_question", case_id

    has_query = bool(query)
    has_context = bool(context_path)
    if has_query == has_context:
        return None, "exactly_one_of_query_or_context_path_required", case_id

    normalized = {
        "case_id": case_id,
        "question": question,
        "query": query,
        "context_path": context_path,
        "fail_on_regression": fail_on_regression,
    }
    return normalized, None, case_id


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run artists QA retry manifest in one shot via batch QA smoke CLI."
    )
    parser.add_argument("--retry-manifest", default="", help="retry manifest path")
    parser.add_argument("--latest", action="store_true", help="resolve latest retry manifest")
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
    parser.add_argument(
        "--output-summary",
        default="",
        help="optional output summary path",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started_at = utc_now_iso()
    timestamp = utc_timestamp_compact()

    output_summary_path = (
        Path(args.output_summary).resolve()
        if args.output_summary
        else (DEFAULT_SUMMARY_DIR / f"artists_answer_qa_retry_run_summary_{timestamp}.json").resolve()
    )

    summary: dict[str, Any] = {
        "started_at": started_at,
        "completed_at": None,
        "source_cli": SOURCE_CLI,
        "retry_manifest_path_requested": args.retry_manifest if args.retry_manifest else "--latest",
        "retry_manifest_latest_resolved": bool(args.latest),
        "retry_manifest_path": None,
        "retry_manifest_case_count": 0,
        "executed_cases": 0,
        "wrapper_exit_code": 1,
        "all_passed": False,
        "child_batch_exit_code": None,
        "child_batch_summary_path": None,
        "child_batch_cases_jsonl_path": None,
        "output_summary_path": str(output_summary_path),
        "invalid_case_count": 0,
        "invalid_case_ids": [],
        "notes": [],
    }

    def finalize(exit_code: int) -> int:
        summary["completed_at"] = utc_now_iso()
        summary["wrapper_exit_code"] = int(exit_code)
        write_json(output_summary_path, summary)
        print(f"[DONE] retry_run_summary={output_summary_path}")
        return int(exit_code)

    if bool(args.retry_manifest) == bool(args.latest):
        error = "exactly_one_of_retry_manifest_or_latest_required"
        summary["notes"].append(error)
        print(f"[ERROR] {error}")
        return finalize(1)

    if args.retry_manifest:
        retry_manifest_path = Path(args.retry_manifest).resolve()
    else:
        latest_path, latest_error = resolve_latest_manifest(Path(args.search_dir), args.glob)
        if latest_error:
            summary["notes"].append(latest_error)
            print(f"[ERROR] {latest_error}")
            return finalize(1)
        assert latest_path is not None
        retry_manifest_path = latest_path

    summary["retry_manifest_path"] = str(retry_manifest_path)

    if not retry_manifest_path.exists():
        error = f"retry_manifest_not_found:{retry_manifest_path}"
        summary["notes"].append(error)
        print(f"[ERROR] {error}")
        return finalize(1)

    try:
        manifest_obj = load_json(retry_manifest_path)
    except Exception as exc:  # noqa: BLE001
        error = f"retry_manifest_load_failed:{exc}"
        summary["notes"].append(error)
        print(f"[ERROR] {error}")
        return finalize(1)

    raw_cases = manifest_obj.get("cases")
    if not isinstance(raw_cases, list):
        error = "retry_manifest_cases_not_array"
        summary["notes"].append(error)
        print(f"[ERROR] {error}")
        return finalize(1)

    summary["retry_manifest_case_count"] = len(raw_cases)

    valid_cases: list[dict[str, Any]] = []
    invalid_case_ids: list[str] = []
    invalid_reasons: list[str] = []

    for index, case_obj in enumerate(raw_cases, start=1):
        normalized, error, case_id = normalize_case(case_obj, index)
        if error:
            invalid_case_ids.append(case_id)
            invalid_reasons.append(f"invalid_case:{case_id}:{error}")
            continue
        assert normalized is not None
        valid_case_payload: dict[str, Any] = {
            "case_id": normalized["case_id"],
            "question": normalized["question"],
            "fail_on_regression": normalized["fail_on_regression"],
        }
        if normalized["query"] is not None:
            valid_case_payload["query"] = normalized["query"]
        if normalized["context_path"] is not None:
            valid_case_payload["context_path"] = normalized["context_path"]
        valid_cases.append(valid_case_payload)

    summary["invalid_case_count"] = len(invalid_case_ids)
    summary["invalid_case_ids"] = invalid_case_ids
    summary["notes"].extend(invalid_reasons)

    if len(raw_cases) == 0:
        summary["executed_cases"] = 0
        summary["all_passed"] = True
        summary["wrapper_exit_code"] = 0
        summary["retry_run_mode"] = "noop_empty_retry_manifest"
        summary["notes"].append("no_failed_cases_in_manifest")
        print("[DONE] retry_run_noop empty retry manifest")
        return finalize(0)

    if not valid_cases:
        summary["executed_cases"] = 0
        summary["all_passed"] = False
        summary["notes"].append("no_valid_cases_to_execute")
        print("[ERROR] no_valid_cases_to_execute")
        return finalize(1)

    retry_batch_manifest = {
        "defaults": {},
        "cases": valid_cases,
    }

    child_summary_path = output_summary_path.with_name(
        f"{output_summary_path.stem}_child_batch_summary.json"
    )

    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix="_retry_batch_manifest.json", delete=False
    ) as tmp_file:
        tmp_file.write(json.dumps(retry_batch_manifest, ensure_ascii=False, indent=2) + "\n")
        temp_manifest_path = Path(tmp_file.name)

    child_cmd = [
        sys.executable,
        str(QA_SMOKE_SCRIPT),
        "--batch-manifest",
        str(temp_manifest_path),
        "--output-json",
        str(child_summary_path),
    ]
    summary["child_batch_command"] = child_cmd

    completed = subprocess.run(child_cmd, capture_output=True, text=True, check=False)
    summary["executed_cases"] = len(valid_cases)
    summary["child_batch_exit_code"] = int(completed.returncode)
    summary["child_batch_summary_path"] = str(child_summary_path)
    summary["child_batch_stdout_tail"] = "\n".join(completed.stdout.splitlines()[-30:])
    summary["child_batch_stderr_tail"] = "\n".join(completed.stderr.splitlines()[-30:])

    if child_summary_path.exists():
        try:
            child_summary = load_json(child_summary_path)
            top_level_cases_jsonl = child_summary.get("batch_cases_jsonl_path")
            if isinstance(top_level_cases_jsonl, str) and top_level_cases_jsonl.strip():
                summary["child_batch_cases_jsonl_path"] = top_level_cases_jsonl
            else:
                output_paths = child_summary.get("output_paths")
                if isinstance(output_paths, dict):
                    output_cases_jsonl = output_paths.get("batch_cases_jsonl_path")
                    if isinstance(output_cases_jsonl, str) and output_cases_jsonl.strip():
                        summary["child_batch_cases_jsonl_path"] = output_cases_jsonl
        except Exception as exc:  # noqa: BLE001
            summary["notes"].append(f"child_batch_summary_parse_failed:{exc}")
    else:
        summary["notes"].append("child_batch_summary_not_found")

    child_failed = int(completed.returncode) != 0
    invalid_cases_exist = summary["invalid_case_count"] > 0
    summary["all_passed"] = not child_failed and not invalid_cases_exist

    if invalid_cases_exist:
        summary["notes"].append("invalid_cases_present_wrapper_failed")
    if child_failed:
        summary["notes"].append("child_batch_failed")

    wrapper_exit_code = 0 if summary["all_passed"] else 1

    if summary["all_passed"]:
        print(
            "[DONE] retry_run_complete "
            f"executed_cases={summary['executed_cases']} child_exit={summary['child_batch_exit_code']}"
        )
    else:
        print(
            "[ERROR] retry_run_failed "
            f"executed_cases={summary['executed_cases']} child_exit={summary['child_batch_exit_code']}"
        )

    return finalize(wrapper_exit_code)


if __name__ == "__main__":
    raise SystemExit(main())
