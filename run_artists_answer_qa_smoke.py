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


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def utc_timestamp_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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


def run_step(name: str, cmd: list[str], output_markers: dict[str, str]) -> dict[str, Any]:
    completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
    output_paths: dict[str, str] = {}
    for marker, target_key in output_markers.items():
        parsed = parse_output_path(completed.stdout, marker)
        if parsed is not None:
            output_paths[target_key] = str(parsed)

    return {
        "name": name,
        "command": cmd,
        "exit_code": int(completed.returncode),
        "output_paths": output_paths,
        "stdout_tail": tail_lines(completed.stdout),
        "stderr_tail": tail_lines(completed.stderr),
    }


def build_skipped_step(name: str, reason: str) -> dict[str, Any]:
    return {
        "name": name,
        "command": [],
        "exit_code": 1,
        "output_paths": {},
        "stdout_tail": "",
        "stderr_tail": "",
        "skipped": True,
        "skip_reason": reason,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run artists answer QA smoke: context -> answer -> compare."
    )
    parser.add_argument("--question", required=True, help="question for artists answer")
    parser.add_argument("--query", required=True, help="query for artists retrieval")
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
    if args.k <= 0:
        raise ValueError("--k must be positive")

    started_at = utc_now_iso()
    print(f"[START] artists QA smoke at {started_at}")

    warnings: list[str] = []
    steps: list[dict[str, Any]] = []

    context_cmd = [
        sys.executable,
        str(CONTEXT_SCRIPT),
        "--query",
        args.query,
        "--k",
        str(args.k),
    ]
    context_step = run_step(
        name="context_build",
        cmd=context_cmd,
        output_markers={"context": "context_path", "summary": "context_summary_path"},
    )
    steps.append(context_step)

    context_path: Path | None = None
    context_summary_path: Path | None = None
    if context_step["exit_code"] == 0:
        raw_context = context_step["output_paths"].get("context_path")
        raw_context_summary = context_step["output_paths"].get("context_summary_path")
        if raw_context:
            context_path = Path(raw_context)
        if raw_context_summary:
            context_summary_path = Path(raw_context_summary)

        if context_path is None or not context_path.exists():
            context_path = latest_file("data/phase1_seed10/derived/context/artists_text_context_*.json")
            if context_path is not None:
                warnings.append("context_path_resolved_from_latest_file")
        if context_summary_path is None or not context_summary_path.exists():
            context_summary_path = latest_file(
                "data/phase1_seed10/derived/context/artists_text_context_summary_*.json"
            )
            if context_summary_path is not None:
                warnings.append("context_summary_path_resolved_from_latest_file")

    if context_step["exit_code"] != 0 or context_path is None or not context_path.exists():
        if context_step["exit_code"] == 0:
            warnings.append("context_build_output_missing")
        steps.append(build_skipped_step("answer_generate", "context_build_failed_or_missing_output"))
        steps.append(build_skipped_step("answer_compare", "context_build_failed_or_missing_output"))
    else:
        answer_cmd = [
            sys.executable,
            str(ANSWER_SCRIPT),
            "--question",
            args.question,
            "--context-path",
            str(context_path),
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

        compare_cmd = [
            sys.executable,
            str(COMPARE_SCRIPT),
            "--question",
            args.question,
            "--query",
            args.query,
            "--context-path",
            str(context_path),
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

    all_passed = all(int(step.get("exit_code", 1)) == 0 for step in steps)
    wrapper_exit_code = 0 if all_passed else 1

    timestamp = utc_timestamp_compact()
    summary_path = (
        Path(args.output_json)
        if args.output_json
        else SUMMARY_DIR / f"artists_answer_qa_smoke_summary_{timestamp}.json"
    )

    summary = {
        "started_at": started_at,
        "completed_at": utc_now_iso(),
        "source_cli": "run_artists_answer_qa_smoke.py",
        "question": args.question,
        "query": args.query,
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
