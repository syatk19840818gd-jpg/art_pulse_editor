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

ANSWER_SCRIPT_PATH = Path("run_answer_artists_seed10.py")
OUTPUT_DIR = Path("data/phase1_seed10/derived/answer")
ANSWER_STATUS_PRIORITY = {"ok": 0, "fallback": 1, "error": 2}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_output_path(stdout: str, marker: str) -> Path | None:
    pattern = re.compile(rf"^\[DONE\]\s+{re.escape(marker)}=(.+?)\s*$")
    for line in reversed(stdout.splitlines()):
        match = pattern.match(line.strip())
        if not match:
            continue
        return Path(match.group(1).strip())
    return None


def load_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise RuntimeError(f"Expected JSON object: {path}")
    return obj


def normalize_numeric_token(raw: str) -> str:
    return raw.replace(",", "")


def extract_numeric_tokens(text: str) -> list[str]:
    tokens = re.findall(r"\d[\d,]*", text)
    normalized = [normalize_numeric_token(token) for token in tokens]
    deduped: list[str] = []
    seen: set[str] = set()
    for token in normalized:
        if token in seen:
            continue
        seen.add(token)
        deduped.append(token)
    return deduped


def run_answer(mode_args: list[str]) -> tuple[Path, Path]:
    if not ANSWER_SCRIPT_PATH.exists():
        raise FileNotFoundError(f"Missing answer script: {ANSWER_SCRIPT_PATH}")

    cmd = [sys.executable, str(ANSWER_SCRIPT_PATH), *mode_args]
    completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            "run_answer_artists_seed10.py failed.\n"
            f"command: {' '.join(cmd)}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )

    output_path = parse_output_path(completed.stdout, "output")
    summary_path = parse_output_path(completed.stdout, "summary")
    if output_path is None or not output_path.exists():
        raise RuntimeError("Could not determine answer output path from stdout.")
    if summary_path is None or not summary_path.exists():
        raise RuntimeError("Could not determine answer summary path from stdout.")
    return output_path, summary_path


def build_mode_summary(answer_obj: dict[str, Any], summary_obj: dict[str, Any]) -> dict[str, Any]:
    answer_text = str(answer_obj.get("answer", ""))
    evidence = answer_obj.get("evidence", [])
    evidence_count = len(evidence) if isinstance(evidence, list) else 0
    answer_chars = int(summary_obj.get("answer_chars", len(answer_text)))
    output_valid_raw = summary_obj.get("output_valid")
    if output_valid_raw is None:
        output_valid_raw = answer_obj.get("output_valid")

    output_valid: bool | None
    if isinstance(output_valid_raw, bool):
        output_valid = output_valid_raw
    elif isinstance(output_valid_raw, str):
        normalized = output_valid_raw.strip().lower()
        if normalized in {"true", "1", "yes"}:
            output_valid = True
        elif normalized in {"false", "0", "no"}:
            output_valid = False
        else:
            output_valid = None
    else:
        output_valid = None

    return {
        "context_input_mode": str(summary_obj.get("context_input_mode", "")),
        "answer_status": str(answer_obj.get("answer_status", summary_obj.get("answer_status", ""))),
        "answer_chars": answer_chars,
        "evidence_count": evidence_count,
        "output_valid": output_valid,
        "numeric_tokens": extract_numeric_tokens(answer_text),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare artists answers: query_rebuild vs fixed_context."
    )
    parser.add_argument("--question", required=True, help="question text")
    parser.add_argument("--query", required=True, help="retrieval query for query_rebuild mode")
    parser.add_argument("--context-path", required=True, help="fixed context json path")
    parser.add_argument("--k", type=int, default=5, help="top-k used in query_rebuild mode")
    parser.add_argument(
        "--fail-on-mismatch",
        action="store_true",
        help="return non-zero when mismatch_fields is not empty",
    )
    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="return non-zero when regression (degradation) is detected",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started_at = utc_now_iso()
    print(f"[START] artists answer compare at {started_at}")

    context_path = Path(args.context_path)
    if not context_path.exists():
        raise FileNotFoundError(f"Missing context file: {context_path}")
    if args.k <= 0:
        raise ValueError("--k must be positive")

    query_output_path, query_summary_path = run_answer(
        [
            "--question",
            args.question,
            "--query",
            args.query,
            "--k",
            str(args.k),
        ]
    )
    fixed_output_path, fixed_summary_path = run_answer(
        [
            "--question",
            args.question,
            "--context-path",
            str(context_path),
            "--k",
            str(args.k),
        ]
    )

    query_answer = load_json(query_output_path)
    query_summary = load_json(query_summary_path)
    fixed_answer = load_json(fixed_output_path)
    fixed_summary = load_json(fixed_summary_path)

    query_info = build_mode_summary(query_answer, query_summary)
    fixed_info = build_mode_summary(fixed_answer, fixed_summary)

    query_numeric = set(query_info["numeric_tokens"])
    fixed_numeric = set(fixed_info["numeric_tokens"])

    mismatch_fields: list[str] = []
    if query_info["answer_status"] != fixed_info["answer_status"]:
        mismatch_fields.append("answer_status")
    if int(query_info["answer_chars"]) != int(fixed_info["answer_chars"]):
        mismatch_fields.append("answer_chars")
    if int(query_info["evidence_count"]) != int(fixed_info["evidence_count"]):
        mismatch_fields.append("evidence_count")
    if query_numeric != fixed_numeric:
        mismatch_fields.append("numeric_tokens")

    regression_reasons: list[str] = []
    regression_warnings: list[str] = []
    regression_check_fields = ["answer_status", "output_valid", "evidence_count"]

    baseline_info = query_info
    current_info = fixed_info
    baseline_label = "query_rebuild"
    current_label = "fixed_context"

    baseline_status = str(baseline_info.get("answer_status", "")).strip()
    current_status = str(current_info.get("answer_status", "")).strip()
    baseline_status_rank = ANSWER_STATUS_PRIORITY.get(baseline_status)
    current_status_rank = ANSWER_STATUS_PRIORITY.get(current_status)
    if baseline_status and current_status:
        if baseline_status_rank is None:
            regression_warnings.append(
                f"unknown_answer_status:{baseline_label}:{baseline_status}"
            )
        if current_status_rank is None:
            regression_warnings.append(
                f"unknown_answer_status:{current_label}:{current_status}"
            )
        if (
            baseline_status_rank is not None
            and current_status_rank is not None
            and current_status_rank > baseline_status_rank
        ):
            regression_reasons.append(
                f"answer_status_regressed:{baseline_status}->{current_status}"
            )
    else:
        regression_warnings.append("missing_field_for_regression_check:answer_status")

    baseline_output_valid = baseline_info.get("output_valid")
    current_output_valid = current_info.get("output_valid")
    if isinstance(baseline_output_valid, bool) and isinstance(current_output_valid, bool):
        if baseline_output_valid and not current_output_valid:
            regression_reasons.append("output_valid_regressed:true->false")
    else:
        regression_warnings.append("missing_field_for_regression_check:output_valid")

    baseline_evidence_count = int(baseline_info["evidence_count"])
    current_evidence_count = int(current_info["evidence_count"])
    if current_evidence_count < baseline_evidence_count:
        regression_reasons.append(
            f"evidence_count_decreased:{baseline_evidence_count}->{current_evidence_count}"
        )

    regression_detected = bool(regression_reasons)
    guard_passed = not regression_detected

    exit_code = 0
    exit_reason = "comparison_completed"
    if args.fail_on_regression and regression_detected:
        exit_code = 2
        exit_reason = "regression_detected"
    elif args.fail_on_mismatch and mismatch_fields:
        exit_code = 2
        exit_reason = "mismatch_detected"

    compare_summary = {
        "started_at": started_at,
        "completed_at": utc_now_iso(),
        "question": args.question,
        "query": args.query,
        "context_path": str(context_path),
        "k_requested": args.k,
        "fail_on_mismatch": bool(args.fail_on_mismatch),
        "fail_on_regression": bool(args.fail_on_regression),
        "mismatch_fields": mismatch_fields,
        "guard_passed": guard_passed,
        "regression_detected": regression_detected,
        "regression_reasons": regression_reasons,
        "regression_check_fields": regression_check_fields,
        "regression_warnings": regression_warnings,
        "regression_baseline_mode": baseline_label,
        "regression_current_mode": current_label,
        "compare_exit_code": exit_code,
        "exit_reason": exit_reason,
        "query_rebuild": {
            "output_path": str(query_output_path),
            "summary_path": str(query_summary_path),
            **query_info,
        },
        "fixed_context": {
            "output_path": str(fixed_output_path),
            "summary_path": str(fixed_summary_path),
            **fixed_info,
        },
        "differences": {
            "answer_chars_delta": int(query_info["answer_chars"]) - int(fixed_info["answer_chars"]),
            "evidence_count_delta": int(query_info["evidence_count"]) - int(fixed_info["evidence_count"]),
            "numeric_only_in_query_rebuild": sorted(query_numeric - fixed_numeric, key=int),
            "numeric_only_in_fixed_context": sorted(fixed_numeric - query_numeric, key=int),
        },
    }

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    summary_path = OUTPUT_DIR / f"artists_text_answer_compare_{timestamp}.json"
    write_json(summary_path, compare_summary)

    print(
        "[DONE] artists answer compare complete. "
        f"query_chars={query_info['answer_chars']} fixed_chars={fixed_info['answer_chars']}"
    )
    print(f"[DONE] mismatch_fields={mismatch_fields}")
    print(f"[DONE] guard_passed={guard_passed} regression_reasons={regression_reasons}")
    print(f"[DONE] summary={summary_path}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
