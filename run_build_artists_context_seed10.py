#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SEARCH_SCRIPT_PATH = Path("run_search_artists_seed10.py")
RAW_INPUT_PATHS = {
    "frieze_london": Path("data/phase1_seed10/raw/artists_frieze_london_2025.jsonl"),
    "liste": Path("data/phase1_seed10/raw/artists_liste_2025.jsonl"),
}
OUTPUT_DIR = Path("data/phase1_seed10/derived/context")

DEFAULT_TOP_K = 5
DEFAULT_EXCERPT_CHARS = 700


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


def normalize_text_for_excerpt(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"\s+", " ", normalized).strip()


def build_excerpt(source_text: str, max_chars: int) -> tuple[str, bool, int]:
    normalized = normalize_text_for_excerpt(source_text)
    full_chars = len(normalized)
    if full_chars <= max_chars:
        return normalized, False, full_chars
    return normalized[:max_chars].rstrip(), True, full_chars


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


def run_search_cli(query: str, k: int) -> tuple[Path, Path]:
    if not SEARCH_SCRIPT_PATH.exists():
        raise FileNotFoundError(f"Missing search script: {SEARCH_SCRIPT_PATH}")

    cmd = [sys.executable, str(SEARCH_SCRIPT_PATH), "--query", query, "--k", str(k)]
    completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            "run_search_artists_seed10.py failed.\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )

    results_path = parse_output_path(completed.stdout, "results")
    summary_path = parse_output_path(completed.stdout, "summary")

    if results_path is None:
        results_path = latest_file_by_pattern(
            "data/phase1_seed10/derived/vector/search/artists_text_search_results_*.jsonl"
        )
    if summary_path is None:
        summary_path = latest_file_by_pattern(
            "data/phase1_seed10/derived/vector/search/artists_text_search_summary_*.json"
        )

    if results_path is None or not results_path.exists():
        raise RuntimeError("Could not determine artists search results path from CLI output.")
    if summary_path is None or not summary_path.exists():
        raise RuntimeError("Could not determine artists search summary path from CLI output.")
    return results_path, summary_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build artists_text context JSON from top-k vector search results."
    )
    parser.add_argument("--query", required=True, help="search query text")
    parser.add_argument("--k", type=int, default=DEFAULT_TOP_K, help="top-k to include")
    parser.add_argument(
        "--excerpt-chars",
        type=int,
        default=DEFAULT_EXCERPT_CHARS,
        help="max excerpt chars per context item",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started_at = utc_now_iso()
    print(f"[START] artists_text context build at {started_at}")

    if args.k <= 0:
        raise ValueError("--k must be positive")
    if args.excerpt_chars <= 0:
        raise ValueError("--excerpt-chars must be positive")

    for fair_slug, raw_path in RAW_INPUT_PATHS.items():
        if not raw_path.exists():
            raise FileNotFoundError(f"Missing artists raw input for {fair_slug}: {raw_path}")

    search_results_path, search_summary_path = run_search_cli(query=args.query, k=args.k)
    search_rows = read_jsonl(search_results_path)

    raw_by_record_id: dict[str, dict[str, Any]] = {}
    for fair_slug, raw_path in RAW_INPUT_PATHS.items():
        rows = read_jsonl(raw_path)
        for row in rows:
            source_url = str(row.get("source_url") or "").strip()
            text_hash = str(row.get("text_hash") or "").strip()
            if not source_url or not text_hash:
                continue
            record_id = build_record_id(
                fair_slug=str(row.get("fair_slug") or fair_slug),
                source_url=source_url,
                text_hash=text_hash,
            )
            if record_id not in raw_by_record_id:
                raw_by_record_id[record_id] = row

    context_items: list[dict[str, Any]] = []
    missing_source_count = 0
    empty_excerpt_count = 0
    excerpt_truncated_count = 0

    for i, row in enumerate(search_rows, start=1):
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

        fair_slug = str(row.get("fair_slug") or "").strip()
        source_url = str(row.get("source_url") or "").strip()
        text_hash = str(row.get("text_hash") or "").strip()
        record_id = str(row.get("record_id") or "").strip()
        if not record_id and fair_slug and source_url and text_hash:
            record_id = build_record_id(
                fair_slug=fair_slug,
                source_url=source_url,
                text_hash=text_hash,
            )

        source_row = raw_by_record_id.get(record_id) if record_id else None
        if source_row is None:
            missing_source_count += 1

        source_text = str((source_row or {}).get("text", ""))
        excerpt, excerpt_truncated, excerpt_full_chars = build_excerpt(
            source_text=source_text, max_chars=args.excerpt_chars
        )
        if excerpt_truncated:
            excerpt_truncated_count += 1
        if not excerpt:
            empty_excerpt_count += 1

        context_items.append(
            {
                "rank": rank,
                "record_id": record_id,
                "score": score,
                "source_url": source_url,
                "fair_slug": fair_slug,
                "gallery_name_en": str(row.get("gallery_name_en") or ""),
                "gallery_name_kana": str(row.get("gallery_name_kana") or ""),
                "headline_ja": str(row.get("headline_ja") or ""),
                "vector_index": int(row.get("vector_index", -1)),
                "excerpt": excerpt,
                "excerpt_chars": len(excerpt),
                "excerpt_full_chars": excerpt_full_chars,
                "excerpt_truncated": excerpt_truncated,
            }
        )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    context_path = OUTPUT_DIR / f"artists_text_context_{timestamp}.json"
    summary_path = OUTPUT_DIR / f"artists_text_context_summary_{timestamp}.json"

    context_payload = {
        "query": args.query,
        "k_requested": args.k,
        "k_returned": len(context_items),
        "generated_at": utc_now_iso(),
        "rag_category": "artists_text",
        "search_results_path": str(search_results_path),
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
        "input_paths": {
            "search_results": str(search_results_path),
            "search_summary": str(search_summary_path),
            "raw_by_fair": {k: str(v) for k, v in RAW_INPUT_PATHS.items()},
        },
        "output_paths": {
            "context": str(context_path),
            "summary": str(summary_path),
        },
        "missing_source_count": missing_source_count,
        "empty_excerpt_count": empty_excerpt_count,
        "excerpt_truncated_count": excerpt_truncated_count,
    }
    write_json(summary_path, summary_payload)

    print(
        "[DONE] artists_text context build complete. "
        f"k_returned={len(context_items)} empty_excerpt={empty_excerpt_count}"
    )
    print(f"[DONE] context={context_path}")
    print(f"[DONE] summary={summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
