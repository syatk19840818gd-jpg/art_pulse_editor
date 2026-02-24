#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
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
RAW_INPUT_PATHS = {
    "frieze_london": Path("data/phase1_seed10/raw/artists_frieze_london_2025.jsonl"),
    "liste": Path("data/phase1_seed10/raw/artists_liste_2025.jsonl"),
}

DEFAULT_TOP_K = 5
DEFAULT_MODEL = "gpt-5-mini"
DEFAULT_MAX_ANSWER_CHARS = 1200
EVIDENCE_REQUIRED_KEYS = ("source_url", "record_id", "score", "excerpt")
DEFAULT_EXCERPT_FALLBACK_CHARS = 260
DEFAULT_HEADLINE_FALLBACK_CHARS = 80


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            raw = line.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def build_record_id(fair_slug: str, source_url: str, text_hash: str) -> str:
    payload = f"{fair_slug.strip()}\n{source_url.strip()}\n{text_hash.strip()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


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


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 10**9) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def sort_evidence_items(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        evidence,
        key=lambda item: (
            -safe_float(item.get("score", 0.0)),
            safe_int(item.get("rank", 10**9)),
            normalize_whitespace(str(item.get("source_url", ""))),
            normalize_whitespace(str(item.get("record_id", ""))),
            safe_int(item.get("vector_index", 10**9)),
        ),
    )


def dedup_evidence_by_source_record(
    evidence: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    deduped: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str]] = set()
    removed = 0

    for item in evidence:
        source_url = normalize_whitespace(str(item.get("source_url", "")))
        record_id = normalize_whitespace(str(item.get("record_id", "")))
        if source_url and record_id:
            dedup_key = (source_url, record_id)
            if dedup_key in seen_keys:
                removed += 1
                continue
            seen_keys.add(dedup_key)
        deduped.append(item)
    return deduped, removed


def load_artists_raw_indices() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], list[str]]:
    by_record_id: dict[str, dict[str, Any]] = {}
    by_source_url: dict[str, dict[str, Any]] = {}
    warnings: list[str] = []

    for fair_slug, raw_path in RAW_INPUT_PATHS.items():
        if not raw_path.exists():
            warnings.append(f"artists_raw_missing_for_fallback:{fair_slug}:{raw_path}")
            continue
        for row in read_jsonl(raw_path):
            source_url = normalize_whitespace(str(row.get("source_url") or ""))
            if source_url and source_url not in by_source_url:
                by_source_url[source_url] = row

            text_hash = normalize_whitespace(str(row.get("text_hash") or ""))
            fair_slug_value = normalize_whitespace(str(row.get("fair_slug") or fair_slug))
            if not source_url or not text_hash or not fair_slug_value:
                continue
            record_id = build_record_id(
                fair_slug=fair_slug_value,
                source_url=source_url,
                text_hash=text_hash,
            )
            if record_id not in by_record_id:
                by_record_id[record_id] = row
    return by_record_id, by_source_url, warnings


def truncate_for_fallback(text: str, max_chars: int) -> str:
    normalized = normalize_whitespace(text)
    if len(normalized) <= max_chars:
        return normalized
    return normalized[:max_chars].rstrip()


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

    warnings: list[str] = []
    raw_by_record_id, raw_by_source_url, raw_index_warnings = load_artists_raw_indices()
    warnings.extend(raw_index_warnings)

    evidence: list[dict[str, Any]] = []
    for item in context_items:
        source_url = normalize_whitespace(str(item.get("source_url", "")))
        record_id = normalize_whitespace(str(item.get("record_id", "")))
        raw_row = None
        if record_id:
            raw_row = raw_by_record_id.get(record_id)
        if raw_row is None and source_url:
            raw_row = raw_by_source_url.get(source_url)
        source_row_missing = raw_row is None

        headline_ja = normalize_whitespace(str(item.get("headline_ja", "")))
        excerpt = normalize_whitespace(str(item.get("excerpt", "")))
        excerpt_fallback_used = False
        headline_fallback_used = False

        if not excerpt:
            if headline_ja:
                excerpt = truncate_for_fallback(
                    headline_ja, max_chars=DEFAULT_EXCERPT_FALLBACK_CHARS
                )
                excerpt_fallback_used = bool(excerpt)
            if not excerpt and raw_row is not None:
                raw_text = normalize_whitespace(str(raw_row.get("text", "")))
                if raw_text:
                    excerpt = truncate_for_fallback(
                        raw_text, max_chars=DEFAULT_EXCERPT_FALLBACK_CHARS
                    )
                    excerpt_fallback_used = bool(excerpt)

        if not headline_ja and raw_row is not None:
            raw_headline = normalize_whitespace(str(raw_row.get("headline_ja", "")))
            if raw_headline:
                headline_ja = truncate_for_fallback(
                    raw_headline, max_chars=DEFAULT_HEADLINE_FALLBACK_CHARS
                )
                headline_fallback_used = bool(headline_ja)
        if not headline_ja and excerpt:
            headline_ja = truncate_for_fallback(
                excerpt, max_chars=DEFAULT_HEADLINE_FALLBACK_CHARS
            )
            headline_fallback_used = bool(headline_ja)

        evidence.append(
            {
                "rank": int(item.get("rank", -1)),
                "source_url": source_url,
                "record_id": record_id,
                "score": float(item.get("score", 0.0)),
                "excerpt": excerpt,
                "headline_ja": headline_ja,
                "vector_index": int(item.get("vector_index", -1)),
                "fair_slug": str(item.get("fair_slug", "")),
                "excerpt_fallback_used": excerpt_fallback_used,
                "headline_fallback_used": headline_fallback_used,
                "source_row_missing": source_row_missing,
            }
        )

    evidence = sort_evidence_items(evidence)
    evidence, evidence_dedup_removed_count = dedup_evidence_by_source_record(evidence)
    evidence_sorted = True

    evidence_fallback_excerpt_count = sum(
        1 for item in evidence if bool(item.get("excerpt_fallback_used"))
    )
    evidence_fallback_headline_count = sum(
        1 for item in evidence if bool(item.get("headline_fallback_used"))
    )
    evidence_source_row_missing_count = sum(
        1 for item in evidence if bool(item.get("source_row_missing"))
    )

    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("ARTISTS_ANSWER_MODEL", DEFAULT_MODEL)
    max_answer_chars = parse_max_answer_chars()
    answer_status = "ok"

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
        "evidence_fallback_excerpt_count": evidence_fallback_excerpt_count,
        "evidence_fallback_headline_count": evidence_fallback_headline_count,
        "evidence_source_row_missing_count": evidence_source_row_missing_count,
        "evidence_dedup_removed_count": evidence_dedup_removed_count,
        "evidence_sorted": evidence_sorted,
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
        "evidence_fallback_excerpt_count": evidence_fallback_excerpt_count,
        "evidence_fallback_headline_count": evidence_fallback_headline_count,
        "evidence_source_row_missing_count": evidence_source_row_missing_count,
        "evidence_dedup_removed_count": evidence_dedup_removed_count,
        "evidence_sorted": evidence_sorted,
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
