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

ADVISOR_SCRIPT_PATH = Path("run_answer_tarutani_advisor.py")
OUTPUT_DIR = Path("data/Tarutani_data/answers")


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


def normalize_numeric_token(raw: str) -> str:
    return raw.replace(",", "")


def extract_numeric_tokens(text: str) -> list[str]:
    tokens = re.findall(r"\d[\d,]*", text)
    normalized = [normalize_numeric_token(token) for token in tokens]
    # Keep first occurrence order while removing duplicates.
    deduped: list[str] = []
    seen: set[str] = set()
    for token in normalized:
        if token in seen:
            continue
        seen.add(token)
        deduped.append(token)
    return deduped


def run_advisor(mode_args: list[str]) -> tuple[Path, Path]:
    if not ADVISOR_SCRIPT_PATH.exists():
        raise FileNotFoundError(f"Missing advisor script: {ADVISOR_SCRIPT_PATH}")

    cmd = [sys.executable, str(ADVISOR_SCRIPT_PATH), *mode_args]
    completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            "run_answer_tarutani_advisor.py failed.\n"
            f"command: {' '.join(cmd)}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )

    output_path = parse_output_path(completed.stdout, "output")
    summary_path = parse_output_path(completed.stdout, "summary")
    if output_path is None or not output_path.exists():
        raise RuntimeError("Could not determine advisor output path from stdout.")
    if summary_path is None or not summary_path.exists():
        raise RuntimeError("Could not determine advisor summary path from stdout.")
    return output_path, summary_path


def load_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise RuntimeError(f"Expected JSON object: {path}")
    return obj


def build_mode_summary(answer_obj: dict[str, Any], summary_obj: dict[str, Any]) -> dict[str, Any]:
    answer_text = str(answer_obj.get("answer_text", ""))
    evidence = answer_obj.get("evidence", [])
    evidence_count = len(evidence) if isinstance(evidence, list) else 0
    numeric_tokens = extract_numeric_tokens(answer_text)
    return {
        "context_input_mode": str(summary_obj.get("context_input_mode", "")),
        "answer_chars": int(answer_obj.get("answer_chars", len(answer_text))),
        "evidence_count": evidence_count,
        "primary_source_path": str(answer_obj.get("primary_source_path", "")),
        "numeric_tokens": numeric_tokens,
        "contains_700": "700" in numeric_tokens,
        "contains_180": "180" in numeric_tokens,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare Tarutani advisor answers: query_rebuild vs fixed_context."
    )
    parser.add_argument("--question", required=True, help="advisor question")
    parser.add_argument("--query", required=True, help="retrieval query for query_rebuild mode")
    parser.add_argument("--context-path", required=True, help="fixed context json for fixed_context mode")
    parser.add_argument("--k", type=int, default=5, help="top-k used in query_rebuild mode")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started_at = utc_now_iso()
    print(f"[START] Tarutani advisor answer compare at {started_at}")

    context_path = Path(args.context_path)
    if not context_path.exists():
        raise FileNotFoundError(f"Missing context file: {context_path}")
    if args.k <= 0:
        raise ValueError("--k must be positive")

    query_output_path, query_summary_path = run_advisor(
        [
            "--question",
            args.question,
            "--query",
            args.query,
            "--k",
            str(args.k),
        ]
    )
    fixed_output_path, fixed_summary_path = run_advisor(
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

    compare_summary = {
        "started_at": started_at,
        "completed_at": utc_now_iso(),
        "question": args.question,
        "query": args.query,
        "context_path": str(context_path),
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
            "contains_700": {
                "query_rebuild": bool(query_info["contains_700"]),
                "fixed_context": bool(fixed_info["contains_700"]),
            },
            "contains_180": {
                "query_rebuild": bool(query_info["contains_180"]),
                "fixed_context": bool(fixed_info["contains_180"]),
            },
        },
    }

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = OUTPUT_DIR / f"tarutani_advisor_answer_compare_{timestamp}.json"
    write_json(output_path, compare_summary)

    print(
        "[DONE] Tarutani advisor compare complete. "
        f"query_chars={query_info['answer_chars']} fixed_chars={fixed_info['answer_chars']}"
    )
    print(f"[DONE] summary={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
