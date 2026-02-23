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

SEARCH_SCRIPT_PATH = Path("run_search_tarutani_text.py")
RAW_JSONL_PATH = Path("data/Tarutani_data/tarutani_text.jsonl")
OUTPUT_DIR = Path("data/Tarutani_data/context")

DEFAULT_TOP_K = 5
DEFAULT_EXCERPT_CHARS = 900


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_text_for_slice(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def compact_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def build_excerpt(
    *,
    source_text: str,
    chunk_start: int,
    chunk_end: int,
    max_chars: int,
) -> tuple[str, bool, int]:
    normalized = normalize_text_for_slice(source_text)
    if not normalized:
        return "", False, 0

    if 0 <= chunk_start < len(normalized) and chunk_end > chunk_start:
        sliced = normalized[chunk_start : min(chunk_end, len(normalized))]
    else:
        sliced = normalized

    compacted = compact_whitespace(sliced)
    full_chars = len(compacted)
    if len(compacted) <= max_chars:
        return compacted, False, full_chars
    return compacted[:max_chars].rstrip(), True, full_chars


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


def run_search_cli(query: str, k: int) -> tuple[Path, Path]:
    if not SEARCH_SCRIPT_PATH.exists():
        raise FileNotFoundError(f"Missing search script: {SEARCH_SCRIPT_PATH}")

    cmd = [sys.executable, str(SEARCH_SCRIPT_PATH), "--query", query, "--k", str(k)]
    completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            "run_search_tarutani_text.py failed.\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )

    results_path = parse_output_path(completed.stdout, "results")
    summary_path = parse_output_path(completed.stdout, "summary")

    if results_path is None:
        results_path = latest_file_by_pattern(
            "data/Tarutani_data/vector/search/tarutani_text_search_results_*.jsonl"
        )
    if summary_path is None:
        summary_path = latest_file_by_pattern(
            "data/Tarutani_data/vector/search/tarutani_text_search_summary_*.json"
        )

    if results_path is None or not results_path.exists():
        raise RuntimeError("Could not determine search results path from TASK11 output.")
    if summary_path is None or not summary_path.exists():
        raise RuntimeError("Could not determine search summary path from TASK11 output.")

    return results_path, summary_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Tarutani function-5 context JSON from TASK11 top-k search results."
    )
    parser.add_argument("--query", required=True, help="search query text")
    parser.add_argument("--k", type=int, default=DEFAULT_TOP_K, help="top-k to include in context")
    parser.add_argument(
        "--excerpt-chars",
        type=int,
        default=DEFAULT_EXCERPT_CHARS,
        help="max chars per context excerpt",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started_at = utc_now_iso()
    print(f"[START] Tarutani context build at {started_at}")

    if args.k <= 0:
        raise ValueError("--k must be positive")
    if args.excerpt_chars <= 0:
        raise ValueError("--excerpt-chars must be positive")
    if not RAW_JSONL_PATH.exists():
        raise FileNotFoundError(f"Missing source jsonl: {RAW_JSONL_PATH}")

    results_path, search_summary_path = run_search_cli(query=args.query, k=args.k)
    search_rows = read_jsonl(results_path)
    raw_rows = read_jsonl(RAW_JSONL_PATH)

    raw_by_source: dict[str, dict[str, Any]] = {}
    for row in raw_rows:
        source_path = str(row.get("source_path", "")).strip()
        if source_path and source_path not in raw_by_source:
            raw_by_source[source_path] = row

    context_items: list[dict[str, Any]] = []
    missing_source_count = 0
    excerpt_truncated_count = 0
    empty_excerpt_count = 0

    for i, row in enumerate(search_rows, start=1):
        source_path = str(row.get("source_path", "")).strip()
        source_row = raw_by_source.get(source_path)
        if source_row is None:
            missing_source_count += 1

        source_text = str((source_row or {}).get("text", ""))
        chunk_start = int(row.get("chunk_start", -1))
        chunk_end = int(row.get("chunk_end", -1))
        excerpt, excerpt_truncated, excerpt_full_chars = build_excerpt(
            source_text=source_text,
            chunk_start=chunk_start,
            chunk_end=chunk_end,
            max_chars=args.excerpt_chars,
        )
        if excerpt_truncated:
            excerpt_truncated_count += 1
        if not excerpt:
            empty_excerpt_count += 1

        rank_value = row.get("rank", i)
        try:
            rank = int(rank_value)
        except (TypeError, ValueError):
            rank = i

        score_value = row.get("score", 0.0)
        try:
            score = float(score_value)
        except (TypeError, ValueError):
            score = 0.0

        rerank_value = row.get("rerank_score", score)
        try:
            rerank_score = float(rerank_value)
        except (TypeError, ValueError):
            rerank_score = score

        context_items.append(
            {
                "rank": rank,
                "source_path": source_path,
                "series_name": str(row.get("series_name", "")),
                "chunk_index": int(row.get("chunk_index", -1)),
                "chunk_start": chunk_start,
                "chunk_end": chunk_end,
                "score": score,
                "rerank_score": rerank_score,
                "headline_ja": str(row.get("headline_ja", "")),
                "excerpt": excerpt,
                "excerpt_chars": len(excerpt),
                "excerpt_full_chars": excerpt_full_chars,
                "excerpt_truncated": excerpt_truncated,
            }
        )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    context_path = OUTPUT_DIR / f"tarutani_text_context_{timestamp}.json"
    summary_path = OUTPUT_DIR / f"tarutani_text_context_summary_{timestamp}.json"

    context_payload = {
        "query": args.query,
        "k_requested": args.k,
        "k_returned": len(context_items),
        "generated_at": utc_now_iso(),
        "source": "Tarutani_Text",
        "search_results_path": str(results_path),
        "search_summary_path": str(search_summary_path),
        "context_items": context_items,
    }
    write_json(context_path, context_payload)

    summary_payload = {
        "started_at": started_at,
        "completed_at": utc_now_iso(),
        "query": args.query,
        "k_requested": args.k,
        "k_returned": len(context_items),
        "excerpt_chars": args.excerpt_chars,
        "search_results_path": str(results_path),
        "search_summary_path": str(search_summary_path),
        "raw_jsonl_path": str(RAW_JSONL_PATH),
        "output_context_path": str(context_path),
        "output_summary_path": str(summary_path),
        "missing_source_count": missing_source_count,
        "empty_excerpt_count": empty_excerpt_count,
        "excerpt_truncated_count": excerpt_truncated_count,
    }
    write_json(summary_path, summary_payload)

    print(
        "[DONE] Tarutani context build complete. "
        f"k_returned={len(context_items)} empty_excerpt={empty_excerpt_count}"
    )
    print(f"[DONE] context={context_path}")
    print(f"[DONE] summary={summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
