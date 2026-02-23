#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

BUILD_CONTEXT_SCRIPT_PATH = Path("run_build_tarutani_context.py")
OUTPUT_DIR = Path("data/Tarutani_data/answers")

DEFAULT_TOP_K = 5
DEFAULT_MODEL = "gpt-5-mini"
DEFAULT_MAX_ANSWER_CHARS = 1200


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def parse_output_path(stdout: str, marker: str) -> Path | None:
    pattern = re.compile(rf"^\[DONE\]\s+{re.escape(marker)}=(.+?)\s*$")
    for line in reversed(stdout.splitlines()):
        match = pattern.match(line.strip())
        if not match:
            continue
        return Path(match.group(1).strip())
    return None


def latest_file_by_pattern(pattern: str) -> Path | None:
    candidates = sorted(Path().glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        return None
    return candidates[0]


def run_context_builder(query: str, k: int) -> tuple[Path, Path]:
    if not BUILD_CONTEXT_SCRIPT_PATH.exists():
        raise FileNotFoundError(f"Missing context script: {BUILD_CONTEXT_SCRIPT_PATH}")

    cmd = [sys.executable, str(BUILD_CONTEXT_SCRIPT_PATH), "--query", query, "--k", str(k)]
    completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            "run_build_tarutani_context.py failed.\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )

    context_path = parse_output_path(completed.stdout, "context")
    summary_path = parse_output_path(completed.stdout, "summary")

    if context_path is None:
        context_path = latest_file_by_pattern("data/Tarutani_data/context/tarutani_text_context_*.json")
    if summary_path is None:
        summary_path = latest_file_by_pattern(
            "data/Tarutani_data/context/tarutani_text_context_summary_*.json"
        )

    if context_path is None or not context_path.exists():
        raise RuntimeError("Could not determine context path from TASK12 output.")
    if summary_path is None or not summary_path.exists():
        raise RuntimeError("Could not determine context summary path from TASK12 output.")

    return context_path, summary_path


def parse_max_answer_chars() -> int:
    raw = os.getenv("EXCLUSIVE_ADVISOR_TEXT_MAX_CHARS", "").strip()
    if not raw:
        return DEFAULT_MAX_ANSWER_CHARS
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_MAX_ANSWER_CHARS
    return max(200, value)


def build_context_blocks(context_items: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for item in context_items:
        rank = int(item.get("rank", -1))
        source_path = str(item.get("source_path", ""))
        chunk_index = int(item.get("chunk_index", -1))
        score = float(item.get("score", 0.0))
        excerpt = str(item.get("excerpt", ""))
        blocks.append(
            "\n".join(
                [
                    f"[rank={rank}]",
                    f"source_path: {source_path}",
                    f"chunk_index: {chunk_index}",
                    f"score: {score:.6f}",
                    f"excerpt: {excerpt}",
                ]
            )
        )
    return "\n\n".join(blocks)


def sort_context_items_by_rank(context_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        context_items,
        key=lambda item: int(item.get("rank", 10**9)),
    )


def generate_advisor_answer(
    *,
    client: OpenAI,
    model: str,
    question: str,
    query: str,
    context_items: list[dict[str, Any]],
    primary_source_path: str,
    max_answer_chars: int,
) -> str:
    context_text = build_context_blocks(context_items)
    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "あなたは垂谷知明向けの専属アドバイザーです。"
                            "与えられた Tarutani_Text の根拠だけを使って日本語で回答してください。"
                            "根拠が不足する場合は断定せず、その旨を短く明記してください。"
                            "数値・実績などが根拠間で競合する場合は rank が最上位の根拠を正とし、"
                            "下位rankの競合値で上書きしないでください。必要時のみ『過去資料では』として補足してください。"
                            "回答本文のみを返し、見出しやJSONは返さないでください。"
                            f"回答は {max_answer_chars} 文字以内。"
                        ),
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "質問に回答してください。\n"
                            f"質問: {question}\n"
                            f"検索クエリ: {query}\n\n"
                            f"一次根拠（最優先）: {primary_source_path}\n"
                            "一次根拠と他根拠で数値が競合した場合は、一次根拠の値を採用してください。\n\n"
                            "参照コンテキスト（Tarutani_Text 抜粋）:\n"
                            f"{context_text}"
                        ),
                    }
                ],
            },
        ],
    )
    answer = normalize_whitespace(getattr(response, "output_text", "") or "")
    if not answer:
        raise RuntimeError("empty_answer_output")
    if len(answer) > max_answer_chars:
        answer = answer[:max_answer_chars].rstrip()
    return answer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Tarutani Exclusive Advisor answer smoke CLI (uses TASK12 context)."
    )
    parser.add_argument("--question", required=True, help="user question for advisor")
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--query",
        help="retrieval query for Tarutani_Text (rebuild context via TASK12)",
    )
    mode_group.add_argument(
        "--context-path",
        help="fixed context json path (skip retrieval/context rebuild)",
    )
    parser.add_argument("--k", type=int, default=DEFAULT_TOP_K, help="top-k context size")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started_at = utc_now_iso()
    print(f"[START] Tarutani advisor answer at {started_at}")

    if args.k <= 0:
        raise ValueError("--k must be positive")
    question = normalize_whitespace(args.question)
    if not question:
        raise ValueError("question is empty after normalization")

    context_input_mode = ""
    context_path: Path
    context_summary_path = Path("")
    query = ""

    if args.context_path:
        context_input_mode = "fixed_context"
        context_path = Path(args.context_path)
        if not context_path.exists():
            raise FileNotFoundError(f"Missing context file: {context_path}")
        summary_candidate = Path(
            str(context_path).replace(
                "/tarutani_text_context_", "/tarutani_text_context_summary_"
            )
        )
        if summary_candidate.exists():
            context_summary_path = summary_candidate
    else:
        context_input_mode = "query_rebuild"
        query = normalize_whitespace(args.query or "")
        if not query:
            raise ValueError("query is empty after normalization")
        context_path, context_summary_path = run_context_builder(query=query, k=args.k)

    context_obj = json.loads(context_path.read_text(encoding="utf-8"))
    context_items = context_obj.get("context_items", [])
    if not isinstance(context_items, list) or not context_items:
        raise RuntimeError("context_items is empty")
    context_items = sort_context_items_by_rank(context_items)
    primary_source_path = str(context_items[0].get("source_path", ""))
    if not query:
        query = normalize_whitespace(str(context_obj.get("query", "")))
    if not query:
        query = "context_fixed_mode"

    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing")
    model = os.getenv("EXCLUSIVE_ADVISOR_MODEL", DEFAULT_MODEL)
    max_answer_chars = parse_max_answer_chars()
    client = OpenAI(api_key=api_key)

    answer_text = generate_advisor_answer(
        client=client,
        model=model,
        question=question,
        query=query,
        context_items=context_items,
        primary_source_path=primary_source_path,
        max_answer_chars=max_answer_chars,
    )

    evidence_rows: list[dict[str, Any]] = []
    for item in context_items:
        evidence_rows.append(
            {
                "rank": int(item.get("rank", -1)),
                "source_path": str(item.get("source_path", "")),
                "chunk_index": int(item.get("chunk_index", -1)),
                "score": float(item.get("score", 0.0)),
                "excerpt": str(item.get("excerpt", "")),
            }
        )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = OUTPUT_DIR / f"tarutani_advisor_answer_{timestamp}.json"
    summary_path = OUTPUT_DIR / f"tarutani_advisor_answer_summary_{timestamp}.json"

    payload = {
        "started_at": started_at,
        "completed_at": utc_now_iso(),
        "question": question,
        "query": query,
        "context_input_mode": context_input_mode,
        "model": model,
        "max_answer_chars": max_answer_chars,
        "answer_text": answer_text,
        "answer_chars": len(answer_text),
        "context_path": str(context_path),
        "context_summary_path": str(context_summary_path),
        "primary_source_path": primary_source_path,
        "evidence": evidence_rows,
    }
    write_json(output_path, payload)

    summary = {
        "started_at": started_at,
        "completed_at": utc_now_iso(),
        "question": question,
        "query": query,
        "context_input_mode": context_input_mode,
        "model": model,
        "k_requested": args.k,
        "k_used": len(evidence_rows),
        "answer_chars": len(answer_text),
        "context_path": str(context_path),
        "context_summary_path": str(context_summary_path),
        "primary_source_path": primary_source_path,
        "output_path": str(output_path),
        "summary_path": str(summary_path),
    }
    write_json(summary_path, summary)

    print(
        "[DONE] Tarutani advisor answer complete. "
        f"k_used={summary['k_used']} answer_chars={summary['answer_chars']}"
    )
    print(f"[DONE] output={output_path}")
    print(f"[DONE] summary={summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
