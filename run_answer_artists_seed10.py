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

BUILD_CONTEXT_SCRIPT_PATH = Path("run_build_artists_context_seed10.py")
OUTPUT_DIR = Path("data/phase1_seed10/derived/answer")

DEFAULT_TOP_K = 5
DEFAULT_MODEL = "gpt-5-mini"
DEFAULT_MAX_ANSWER_CHARS = 1200
EVIDENCE_REQUIRED_KEYS = ("source_url", "record_id", "score", "excerpt")


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
            "run_build_artists_context_seed10.py failed.\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )

    context_path = parse_output_path(completed.stdout, "context")
    summary_path = parse_output_path(completed.stdout, "summary")

    if context_path is None:
        context_path = latest_file_by_pattern(
            "data/phase1_seed10/derived/context/artists_text_context_*.json"
        )
    if summary_path is None:
        summary_path = latest_file_by_pattern(
            "data/phase1_seed10/derived/context/artists_text_context_summary_*.json"
        )

    if context_path is None or not context_path.exists():
        raise RuntimeError("Could not determine artists context path from TASK59 output.")
    if summary_path is None or not summary_path.exists():
        raise RuntimeError("Could not determine artists context summary path from TASK59 output.")
    return context_path, summary_path


def parse_max_answer_chars() -> int:
    raw = os.getenv("ARTISTS_ANSWER_MAX_CHARS", "").strip()
    if not raw:
        return DEFAULT_MAX_ANSWER_CHARS
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_MAX_ANSWER_CHARS
    return max(200, value)


def sort_context_items_by_rank(context_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        context_items,
        key=lambda item: int(item.get("rank", 10**9)),
    )


def build_context_blocks(context_items: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for item in context_items:
        blocks.append(
            "\n".join(
                [
                    f"[rank={int(item.get('rank', -1))}]",
                    f"source_url: {str(item.get('source_url', ''))}",
                    f"record_id: {str(item.get('record_id', ''))}",
                    f"score: {float(item.get('score', 0.0)):.6f}",
                    f"headline_ja: {str(item.get('headline_ja', ''))}",
                    f"excerpt: {str(item.get('excerpt', ''))}",
                ]
            )
        )
    return "\n\n".join(blocks)


def validate_output_payload(answer_text: str, evidence: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    invalid_reasons: list[str] = []

    if not normalize_whitespace(answer_text):
        invalid_reasons.append("empty_answer")

    if not isinstance(evidence, list) or not evidence:
        invalid_reasons.append("empty_evidence")
        return False, invalid_reasons

    for idx, item in enumerate(evidence):
        if not isinstance(item, dict):
            invalid_reasons.append(f"invalid_evidence_type:{idx}")
            continue

        for key in EVIDENCE_REQUIRED_KEYS:
            if key not in item:
                invalid_reasons.append(f"missing_evidence_key:{idx}.{key}")

        source_url = normalize_whitespace(str(item.get("source_url", "")))
        record_id = normalize_whitespace(str(item.get("record_id", "")))
        excerpt = normalize_whitespace(str(item.get("excerpt", "")))

        if not source_url:
            invalid_reasons.append(f"empty_evidence_value:{idx}.source_url")
        if not record_id:
            invalid_reasons.append(f"empty_evidence_value:{idx}.record_id")
        if not excerpt:
            invalid_reasons.append(f"empty_evidence_value:{idx}.excerpt")

    return len(invalid_reasons) == 0, invalid_reasons


def generate_answer(
    *,
    client: OpenAI,
    model: str,
    question: str,
    query: str,
    context_items: list[dict[str, Any]],
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
                            "あなたはartists_text検索結果の要約アシスタントです。"
                            "与えられた根拠のみを使って日本語で回答してください。"
                            "断定できない内容は推測しないでください。"
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
                            "参照コンテキスト（artists_text）:\n"
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
        description="artists_text answer smoke CLI (uses TASK59 context)."
    )
    parser.add_argument("--question", required=True, help="user question")
    parser.add_argument("--query", help="retrieval query for artists_text context build")
    parser.add_argument("--context-path", help="fixed artists context path")
    parser.add_argument("--k", type=int, default=DEFAULT_TOP_K, help="top-k context size")
    parser.add_argument(
        "--fail-on-invalid-output",
        action="store_true",
        help="return non-zero when answer/evidence validation fails",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started_at = utc_now_iso()
    print(f"[START] artists_text answer at {started_at}")

    if args.k <= 0:
        raise ValueError("--k must be positive")
    question = normalize_whitespace(args.question)
    if not question:
        raise ValueError("question is empty after normalization")

    context_path: Path
    context_summary_path = Path("")
    query = normalize_whitespace(args.query or "")
    context_input_mode = ""

    if args.context_path:
        context_input_mode = "fixed_context"
        context_path = Path(args.context_path)
        if not context_path.exists():
            raise FileNotFoundError(f"Missing context path: {context_path}")
        summary_candidate = Path(
            str(context_path).replace(
                "/artists_text_context_", "/artists_text_context_summary_"
            )
        )
        if summary_candidate.exists():
            context_summary_path = summary_candidate
    else:
        if not query:
            raise ValueError("--query is required when --context-path is not specified")
        context_input_mode = "query_rebuild"
        context_path, context_summary_path = run_context_builder(query=query, k=args.k)

    context_obj = json.loads(context_path.read_text(encoding="utf-8"))
    context_items = context_obj.get("context_items", [])
    if not isinstance(context_items, list) or not context_items:
        raise RuntimeError("context_items is empty")
    context_items = sort_context_items_by_rank(context_items)

    if not query:
        query = normalize_whitespace(str(context_obj.get("query", "")))
    if not query:
        query = "context_fixed_mode"

    evidence: list[dict[str, Any]] = []
    for item in context_items:
        evidence.append(
            {
                "rank": int(item.get("rank", -1)),
                "source_url": str(item.get("source_url", "")),
                "record_id": str(item.get("record_id", "")),
                "score": float(item.get("score", 0.0)),
                "excerpt": str(item.get("excerpt", "")),
                "headline_ja": str(item.get("headline_ja", "")),
                "vector_index": int(item.get("vector_index", -1)),
                "fair_slug": str(item.get("fair_slug", "")),
            }
        )

    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("ARTISTS_ANSWER_MODEL", DEFAULT_MODEL)
    max_answer_chars = parse_max_answer_chars()
    answer_status = "ok"
    warnings: list[str] = []

    if not api_key:
        answer_status = "fallback"
        warnings.append("missing_openai_api_key")
        answer_text = (
            "OpenAI接続情報が未設定のため、回答生成はフォールバックしました。"
            "以下の根拠候補をご確認ください。"
        )
    else:
        try:
            client = OpenAI(api_key=api_key)
            answer_text = generate_answer(
                client=client,
                model=model,
                question=question,
                query=query,
                context_items=evidence,
                max_answer_chars=max_answer_chars,
            )
        except Exception as exc:  # noqa: BLE001
            answer_status = "fallback"
            warnings.append(f"llm_generation_failed:{exc}")
            answer_text = (
                "LLM接続エラーのため、回答生成はフォールバックしました。"
                "根拠候補一覧を参照してください。"
            )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    answer_path = OUTPUT_DIR / f"artists_text_answer_{timestamp}.json"
    summary_path = OUTPUT_DIR / f"artists_text_answer_summary_{timestamp}.json"

    output_valid, invalid_reasons = validate_output_payload(answer_text=answer_text, evidence=evidence)

    payload = {
        "started_at": started_at,
        "completed_at": utc_now_iso(),
        "question": question,
        "query": query,
        "answer": answer_text,
        "answer_status": answer_status,
        "model": model,
        "max_answer_chars": max_answer_chars,
        "context_path": str(context_path),
        "context_summary_path": str(context_summary_path),
        "evidence": evidence,
        "output_valid": output_valid,
        "invalid_reasons": invalid_reasons,
        "warnings": warnings,
    }
    write_json(answer_path, payload)

    summary = {
        "started_at": started_at,
        "completed_at": utc_now_iso(),
        "source_cli": "run_answer_artists_seed10.py",
        "question": question,
        "query": query,
        "context_input_mode": context_input_mode,
        "context_path": str(context_path),
        "context_summary_path": str(context_summary_path),
        "k_requested": args.k,
        "k_returned": len(evidence),
        "answer_status": answer_status,
        "answer_chars": len(answer_text),
        "output_valid": output_valid,
        "invalid_reasons": invalid_reasons,
        "fail_on_invalid_output": bool(args.fail_on_invalid_output),
        "output_paths": {
            "answer_json": str(answer_path),
            "summary_json": str(summary_path),
        },
        "warnings": warnings,
    }
    write_json(summary_path, summary)

    print(
        "[DONE] artists_text answer complete. "
        f"answer_status={answer_status} k_returned={len(evidence)} output_valid={output_valid}"
    )
    if invalid_reasons:
        print(f"[WARN] invalid_reasons={invalid_reasons}")
    print(f"[DONE] output={answer_path}")
    print(f"[DONE] summary={summary_path}")
    if args.fail_on_invalid_output and not output_valid:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
