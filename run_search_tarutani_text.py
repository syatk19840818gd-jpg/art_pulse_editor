#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

import numpy as np
from dotenv import load_dotenv
from google import genai
from google.genai import types

INDEX_PATH = Path("data/Tarutani_data/vector/tarutani_text_index.npy")
META_PATH = Path("data/Tarutani_data/vector/tarutani_text_meta.jsonl")
OUTPUT_DIR = Path("data/Tarutani_data/vector/search")
PROFILE_PATH_DEFAULT = Path("config/tarutani_text_search_profile.json")

EMBEDDING_MODEL_DEFAULT = "gemini-embedding-001"
QUERY_TASK_TYPE = "RETRIEVAL_QUERY"
EMBED_DIM = 1536
QUERY_MAX_CHARS = 2000


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


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def l2_normalize(vec: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vec))
    if norm == 0.0:
        raise ValueError("zero_norm_vector")
    return vec / norm


def normalize_for_match(text: str) -> str:
    return normalize_whitespace(text).casefold()


def load_search_profile(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid profile JSON: {path}") from exc
    if not isinstance(obj, dict):
        raise RuntimeError(f"Profile must be a JSON object: {path}")
    return obj


def resolve_score_rule(
    source_path: str,
    query_for_match: str,
    rules: list[dict[str, Any]],
) -> tuple[str, float]:
    source_for_match = source_path.casefold()
    for rule in rules:
        path_glob = str(rule.get("path_glob", "")).strip()
        if not path_glob:
            continue
        if not fnmatch(source_for_match, path_glob.casefold()):
            continue
        terms = rule.get("query_terms_any", [])
        if isinstance(terms, list):
            normalized_terms = [normalize_for_match(str(item)) for item in terms if str(item).strip()]
            if normalized_terms and not any(term in query_for_match for term in normalized_terms):
                continue
        name = str(rule.get("name", "")).strip() or "unnamed_rule"
        try:
            boost = float(rule.get("score_boost", 0.0))
        except (TypeError, ValueError):
            boost = 0.0
        return name, boost
    return "", 0.0


def get_gemini_api_key() -> str | None:
    for key in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        value = os.getenv(key)
        if value:
            return value
    return None


def embed_query(client: genai.Client, model: str, query: str) -> np.ndarray:
    response = client.models.embed_content(
        model=model,
        contents=[query],
        config=types.EmbedContentConfig(
            task_type=QUERY_TASK_TYPE,
            output_dimensionality=EMBED_DIM,
        ),
    )
    embeddings = getattr(response, "embeddings", None) or []
    if len(embeddings) != 1:
        raise RuntimeError(f"unexpected_embedding_count:{len(embeddings)}")
    values = np.asarray(embeddings[0].values, dtype=np.float32)
    if values.shape[0] != EMBED_DIM:
        raise RuntimeError(f"unexpected_embedding_dim:{values.shape[0]}")
    return l2_normalize(values)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tarutani_Text vector search smoke CLI")
    parser.add_argument("--query", required=True, help="search query text")
    parser.add_argument("--k", type=int, default=5, help="top-k results (default: 5)")
    parser.add_argument(
        "--profile",
        default=str(PROFILE_PATH_DEFAULT),
        help=f"search profile json path (default: {PROFILE_PATH_DEFAULT})",
    )
    parser.add_argument(
        "--max-per-source",
        type=int,
        default=None,
        help="cap selected chunks per source_path (default: profile value or unlimited)",
    )
    parser.add_argument(
        "--disable-profile",
        action="store_true",
        help="disable profile-based score boost",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started_at = utc_now_iso()
    print(f"[START] Tarutani_Text search at {started_at}")

    if args.k <= 0:
        raise ValueError("--k must be positive")
    if not INDEX_PATH.exists():
        raise FileNotFoundError(f"Missing index file: {INDEX_PATH}")
    if not META_PATH.exists():
        raise FileNotFoundError(f"Missing meta file: {META_PATH}")

    raw_query = args.query
    query = normalize_whitespace(raw_query)
    if not query:
        raise ValueError("query is empty after normalization")
    is_query_truncated = False
    if len(query) > QUERY_MAX_CHARS:
        query = query[:QUERY_MAX_CHARS].rstrip()
        is_query_truncated = True

    index = np.load(INDEX_PATH).astype(np.float32)
    if index.ndim != 2:
        raise ValueError(f"index must be 2D, got shape={index.shape}")
    if index.shape[1] != EMBED_DIM:
        raise ValueError(f"index dim mismatch: expected {EMBED_DIM}, got {index.shape[1]}")

    meta_rows = read_jsonl(META_PATH)
    if len(meta_rows) != index.shape[0]:
        raise ValueError(
            f"meta length mismatch: meta={len(meta_rows)} index_rows={index.shape[0]}"
        )

    load_dotenv()
    api_key = get_gemini_api_key()
    if not api_key:
        raise RuntimeError("Missing Gemini API key (GEMINI_API_KEY or GOOGLE_API_KEY)")

    model = os.getenv("TEXT_EMBEDDING_MODEL", EMBEDDING_MODEL_DEFAULT)
    client = genai.Client(api_key=api_key)
    query_vector = embed_query(client=client, model=model, query=query)
    query_for_match = normalize_for_match(query)

    # Re-normalize index rows defensively to keep cosine behavior stable.
    norms = np.linalg.norm(index, axis=1, keepdims=True)
    if np.any(norms == 0):
        raise RuntimeError("index has zero-norm vectors")
    normalized_index = index / norms

    scores = normalized_index @ query_vector

    meta_by_vector_index: dict[int, dict[str, Any]] = {}
    for i, row in enumerate(meta_rows):
        vector_index = int(row.get("vector_index", i))
        meta_by_vector_index[vector_index] = row

    profile_path = Path(args.profile)
    profile_applied = False
    profile: dict[str, Any] = {}
    profile_rules: list[dict[str, Any]] = []
    if not args.disable_profile and profile_path.exists():
        profile = load_search_profile(profile_path)
        rules_obj = profile.get("rules", [])
        if isinstance(rules_obj, list):
            profile_rules = [item for item in rules_obj if isinstance(item, dict)]
        profile_applied = True

    max_per_source = args.max_per_source
    if max_per_source is None and profile_applied:
        raw_limit = profile.get("max_per_source")
        if raw_limit is not None:
            try:
                max_per_source = int(raw_limit)
            except (TypeError, ValueError):
                max_per_source = None
    if max_per_source is not None and max_per_source <= 0:
        raise ValueError("--max-per-source must be positive")

    scored_rows: list[dict[str, Any]] = []
    for idx in range(int(scores.shape[0])):
        idx_int = int(idx)
        semantic_score = float(scores[idx_int])
        meta = meta_by_vector_index.get(idx_int, meta_rows[idx_int])
        source_path = str(meta.get("source_path", ""))
        rule_name, score_boost = resolve_score_rule(
            source_path=source_path,
            query_for_match=query_for_match,
            rules=profile_rules,
        )
        rerank_score = semantic_score + score_boost
        scored_rows.append(
            {
                "vector_index": idx_int,
                "semantic_score": semantic_score,
                "score_boost": score_boost,
                "rerank_score": rerank_score,
                "rule_name": rule_name,
                "meta": meta,
            }
        )

    scored_rows.sort(
        key=lambda item: (
            -item["rerank_score"],
            -item["semantic_score"],
            item["vector_index"],
        )
    )

    selected_rows: list[dict[str, Any]] = []
    source_counts: defaultdict[str, int] = defaultdict(int)
    skipped_by_source_cap = 0
    for item in scored_rows:
        source_path = str(item["meta"].get("source_path", ""))
        if max_per_source is not None and source_counts[source_path] >= max_per_source:
            skipped_by_source_cap += 1
            continue
        selected_rows.append(item)
        source_counts[source_path] += 1
        if len(selected_rows) >= args.k:
            break

    result_rows: list[dict[str, Any]] = []
    for rank, item in enumerate(selected_rows, start=1):
        idx_int = int(item["vector_index"])
        semantic_score = float(item["semantic_score"])
        score_boost = float(item["score_boost"])
        rerank_score = float(item["rerank_score"])
        rule_name = str(item["rule_name"])
        meta = item["meta"]
        result = {
            "rank": rank,
            "score": semantic_score,
            "semantic_score": semantic_score,
            "score_boost": score_boost,
            "rerank_score": rerank_score,
            "applied_rule": rule_name,
            "vector_index": idx_int,
            "source_path": str(meta.get("source_path", "")),
            "series_name": str(meta.get("series_name", "")),
            "chunk_index": int(meta.get("chunk_index", -1)),
            "chunk_start": int(meta.get("chunk_start", -1)),
            "chunk_end": int(meta.get("chunk_end", -1)),
            "headline_ja": str(meta.get("headline_ja", "")),
        }
        result_rows.append(result)
        print(
            f"[RANK {rank}] score={semantic_score:.6f} rerank={rerank_score:.6f} "
            f"source_path={result['source_path']} chunk_index={result['chunk_index']}"
        )

    completed_at = utc_now_iso()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    results_path = OUTPUT_DIR / f"tarutani_text_search_results_{timestamp}.jsonl"
    summary_path = OUTPUT_DIR / f"tarutani_text_search_summary_{timestamp}.json"

    write_jsonl(results_path, result_rows)
    summary = {
        "started_at": started_at,
        "completed_at": completed_at,
        "query": raw_query,
        "query_normalized": query,
        "query_raw_len": len(raw_query),
        "query_embed_input_len": len(query),
        "is_query_truncated": is_query_truncated,
        "k_requested": args.k,
        "k_returned": len(result_rows),
        "max_per_source": max_per_source,
        "skipped_by_source_cap": skipped_by_source_cap,
        "index_path": str(INDEX_PATH),
        "meta_path": str(META_PATH),
        "index_rows": int(index.shape[0]),
        "embedding_model": model,
        "embedding_task_type": QUERY_TASK_TYPE,
        "embedding_dim": EMBED_DIM,
        "profile_path": str(profile_path) if profile_applied else "",
        "profile_applied": profile_applied,
        "profile_rules_count": len(profile_rules),
        "output_results_path": str(results_path),
        "output_summary_path": str(summary_path),
    }
    write_json(summary_path, summary)

    print(
        f"[DONE] Tarutani_Text search complete. k_returned={len(result_rows)} "
        f"query_embed_input_len={len(query)}"
    )
    print(f"[DONE] results={results_path}")
    print(f"[DONE] summary={summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
