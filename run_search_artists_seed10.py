#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from dotenv import load_dotenv
from google import genai
from google.genai import types

TARGET_YEAR = 2025
RAG_CATEGORY = "artists_text"

INDEX_PATH = Path("data/phase1_seed10/derived/vector/artists_text_index_2025.npy")
META_PATH = Path("data/phase1_seed10/derived/vector/artists_text_meta_2025.jsonl")
OUTPUT_DIR = Path("data/phase1_seed10/derived/vector/search")

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


def get_gemini_api_key() -> str | None:
    for key in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        value = os.getenv(key)
        if value:
            return value
    return None


def build_record_id(fair_slug: str, source_url: str, text_hash: str) -> str:
    payload = f"{fair_slug.strip()}\n{source_url.strip()}\n{text_hash.strip()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


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
    parser = argparse.ArgumentParser(description="artists_text vector search smoke CLI (seed10)")
    parser.add_argument("--query", required=True, help="search query text")
    parser.add_argument("--k", type=int, default=5, help="top-k results (default: 5)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started_at = utc_now_iso()
    print(f"[START] artists_text search at {started_at}")

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

    # Re-normalize index rows defensively to keep cosine behavior stable.
    norms = np.linalg.norm(index, axis=1, keepdims=True)
    if np.any(norms == 0):
        raise RuntimeError("index has zero-norm vectors")
    normalized_index = index / norms
    scores = normalized_index @ query_vector

    scored_rows: list[dict[str, Any]] = []
    for idx in range(int(scores.shape[0])):
        idx_int = int(idx)
        row = meta_rows[idx_int]
        fair_slug = str(row.get("fair_slug", ""))
        source_url = str(row.get("source_url", ""))
        text_hash = str(row.get("text_hash", ""))
        scored_rows.append(
            {
                "vector_index": idx_int,
                "score": float(scores[idx_int]),
                "record_id": build_record_id(
                    fair_slug=fair_slug, source_url=source_url, text_hash=text_hash
                ),
                "fair_slug": fair_slug,
                "gallery_name_en": str(row.get("gallery_name_en", "")),
                "gallery_name_kana": str(row.get("gallery_name_kana", "")),
                "source_url": source_url,
                "text_hash": text_hash,
                "headline_ja": str(row.get("headline_ja", "")),
            }
        )

    scored_rows.sort(key=lambda item: (-item["score"], item["vector_index"]))
    result_rows = []
    for rank, row in enumerate(scored_rows[: args.k], start=1):
        out_row = {"rank": rank, **row}
        result_rows.append(out_row)
        print(
            f"[RANK {rank}] score={float(row['score']):.6f} "
            f"source_url={row['source_url']} record_id={row['record_id']}"
        )

    completed_at = utc_now_iso()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    results_path = OUTPUT_DIR / f"artists_text_search_results_{timestamp}.jsonl"
    summary_path = OUTPUT_DIR / f"artists_text_search_summary_{timestamp}.json"

    write_jsonl(results_path, result_rows)
    summary = {
        "started_at": started_at,
        "completed_at": completed_at,
        "target_year": TARGET_YEAR,
        "rag_category": RAG_CATEGORY,
        "query": raw_query,
        "query_normalized": query,
        "query_raw_len": len(raw_query),
        "query_embed_input_len": len(query),
        "is_query_truncated": is_query_truncated,
        "k_requested": args.k,
        "k_returned": len(result_rows),
        "embedding_model": model,
        "embedding_task_type": QUERY_TASK_TYPE,
        "embedding_dim": EMBED_DIM,
        "input_paths": {
            "index": str(INDEX_PATH),
            "meta": str(META_PATH),
        },
        "output_paths": {
            "results": str(results_path),
            "summary": str(summary_path),
        },
    }
    write_json(summary_path, summary)

    print(
        f"[DONE] artists_text search complete. k_returned={len(result_rows)} "
        f"query_embed_input_len={len(query)}"
    )
    print(f"[DONE] results={results_path}")
    print(f"[DONE] summary={summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
