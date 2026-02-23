#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from dotenv import load_dotenv
from google import genai
from google.genai import types

INPUT_JSONL_PATH = Path("data/Tarutani_data/tarutani_text.jsonl")
OUTPUT_DIR = Path("data/Tarutani_data/vector")
INDEX_PATH = OUTPUT_DIR / "tarutani_text_index.npy"
META_PATH = OUTPUT_DIR / "tarutani_text_meta.jsonl"
FAILED_PATH = OUTPUT_DIR / "tarutani_text_vectorize_failed.jsonl"
SUMMARY_PATH = OUTPUT_DIR / "tarutani_text_vectorize_summary.json"
MANIFEST_PATH = OUTPUT_DIR / "artifact_manifest.json"

RAG_CATEGORY = "tarutani_text"
EMBEDDING_MODEL_DEFAULT = "gemini-embedding-001"
EMBED_TASK_TYPE = "RETRIEVAL_DOCUMENT"
EMBED_OUTPUT_DIM = 1536
EMBED_BATCH_SIZE = 8
EMBED_INPUT_MAX_CHARS = 2000

# SSOT 5-9 例外（TarutaniRAG）: 先頭2000字1本ではなく、チャンク分割で複数埋め込み
CHUNK_SIZE_CHARS = 1000
CHUNK_OVERLAP_CHARS = 200


@dataclass
class EmbeddingCandidate:
    source_path: str
    series_name: str
    text_hash: str
    headline_ja: str
    source_ext: str
    extract_status: str
    source_text_chars: int
    chunk_index: int
    chunk_start: int
    chunk_end: int
    chunk_text: str
    embedding_input: str
    is_truncated: bool


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


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def split_text_into_chunks(text: str) -> list[tuple[int, int, int, str]]:
    if CHUNK_OVERLAP_CHARS >= CHUNK_SIZE_CHARS:
        raise ValueError("CHUNK_OVERLAP_CHARS must be smaller than CHUNK_SIZE_CHARS")

    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []

    step = CHUNK_SIZE_CHARS - CHUNK_OVERLAP_CHARS
    chunks: list[tuple[int, int, int, str]] = []
    chunk_index = 0
    start = 0

    while start < len(normalized):
        end = min(start + CHUNK_SIZE_CHARS, len(normalized))
        chunk_text = normalized[start:end].strip()
        if chunk_text:
            chunks.append((chunk_index, start, end, chunk_text))
            chunk_index += 1
        if end >= len(normalized):
            break
        start += step

    return chunks


def build_embedding_input(headline_ja: str, chunk_text: str) -> tuple[str, bool]:
    headline = headline_ja.strip()
    body = chunk_text.strip()
    merged = body if not headline else f"{headline}\n\n{body}"
    merged = merged.strip()
    if len(merged) <= EMBED_INPUT_MAX_CHARS:
        return merged, False
    return merged[:EMBED_INPUT_MAX_CHARS].rstrip(), True


def l2_normalize(values: list[float]) -> np.ndarray:
    arr = np.asarray(values, dtype=np.float32)
    norm = float(np.linalg.norm(arr))
    if norm == 0.0:
        raise ValueError("zero_norm_embedding")
    return arr / norm


def get_gemini_api_key() -> str | None:
    for key in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        value = os.getenv(key)
        if value:
            return value
    return None


def embed_batch(client: genai.Client, model: str, contents: list[str]) -> list[list[float]]:
    response = client.models.embed_content(
        model=model,
        contents=contents,
        config=types.EmbedContentConfig(
            task_type=EMBED_TASK_TYPE,
            output_dimensionality=EMBED_OUTPUT_DIM,
        ),
    )
    embeddings = getattr(response, "embeddings", None) or []
    if len(embeddings) != len(contents):
        raise RuntimeError(
            f"unexpected_embedding_count:{len(embeddings)} expected:{len(contents)}"
        )
    return [list(item.values) for item in embeddings]


def build_manifest_files(paths: list[Path]) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    for path in paths:
        if not path.exists():
            continue
        files.append(
            {
                "path": path.as_posix(),
                "etag": "",
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )
    return files


def main() -> int:
    started_at = utc_now_iso()
    print(f"[START] Tarutani_Text vectorization at {started_at}")

    if not INPUT_JSONL_PATH.exists():
        raise FileNotFoundError(f"Missing input jsonl: {INPUT_JSONL_PATH}")

    load_dotenv()
    rows = read_jsonl(INPUT_JSONL_PATH)

    counters: defaultdict[str, int] = defaultdict(int)
    seen_source_paths: set[str] = set()
    candidates: list[EmbeddingCandidate] = []

    for row in sorted(rows, key=lambda item: str(item.get("source_path", ""))):
        source_path = str(row.get("source_path", "")).strip()
        series_name = str(row.get("series_name", "")).strip() or "UNKNOWN_SERIES"
        text = str(row.get("text", "")).strip()
        text_hash = str(row.get("text_hash", "")).strip()
        headline_ja = str(row.get("headline_ja", "")).strip()
        source_ext = str(row.get("source_ext", "")).strip().lower()
        extract_status = str(row.get("extract_status", "")).strip()

        if not source_path:
            counters["skipped_missing_source_path"] += 1
            continue
        if source_path in seen_source_paths:
            counters["skipped_duplicate_source_path"] += 1
            continue
        seen_source_paths.add(source_path)

        if not text:
            counters["skipped_empty_text"] += 1
            continue

        chunks = split_text_into_chunks(text)
        if not chunks:
            counters["skipped_empty_after_chunk_split"] += 1
            continue

        counters["source_records_with_text"] += 1
        counters["chunk_candidates_total"] += len(chunks)

        for chunk_index, chunk_start, chunk_end, chunk_text in chunks:
            embedding_input, is_truncated = build_embedding_input(
                headline_ja=headline_ja, chunk_text=chunk_text
            )
            if not embedding_input:
                counters["skipped_empty_embedding_input"] += 1
                continue
            if is_truncated:
                counters["embedding_input_truncated"] += 1

            candidates.append(
                EmbeddingCandidate(
                    source_path=source_path,
                    series_name=series_name,
                    text_hash=text_hash,
                    headline_ja=headline_ja,
                    source_ext=source_ext,
                    extract_status=extract_status,
                    source_text_chars=len(text),
                    chunk_index=chunk_index,
                    chunk_start=chunk_start,
                    chunk_end=chunk_end,
                    chunk_text=chunk_text,
                    embedding_input=embedding_input,
                    is_truncated=is_truncated,
                )
            )

    counters["records_total"] = len(rows)
    counters["embedding_candidates_total"] = len(candidates)

    model = os.getenv("TEXT_EMBEDDING_MODEL", EMBEDDING_MODEL_DEFAULT)
    vectors: list[np.ndarray] = []
    meta_rows: list[dict[str, Any]] = []
    failed_rows: list[dict[str, Any]] = []

    api_key = get_gemini_api_key()
    client: genai.Client | None = genai.Client(api_key=api_key) if api_key else None

    if candidates and client is None:
        for candidate in candidates:
            failed_rows.append(
                {
                    "source_path": candidate.source_path,
                    "chunk_index": candidate.chunk_index,
                    "status": "EMBED_FAILED_MISSING_GEMINI_API_KEY",
                    "error": "Missing GEMINI_API_KEY/GOOGLE_API_KEY",
                }
            )
        counters["failed_embedding_generation"] += len(candidates)

    if candidates and client is not None:
        for i in range(0, len(candidates), EMBED_BATCH_SIZE):
            batch = candidates[i : i + EMBED_BATCH_SIZE]
            batch_contents = [item.embedding_input for item in batch]
            try:
                batch_embeddings = embed_batch(client=client, model=model, contents=batch_contents)
                for candidate, emb_values in zip(batch, batch_embeddings):
                    try:
                        normalized = l2_normalize(emb_values)
                    except Exception as exc:  # noqa: BLE001
                        counters["failed_zero_norm_or_invalid"] += 1
                        failed_rows.append(
                            {
                                "source_path": candidate.source_path,
                                "chunk_index": candidate.chunk_index,
                                "status": "EMBED_FAILED_NORMALIZE",
                                "error": str(exc),
                            }
                        )
                        continue

                    vector_index = len(vectors)
                    vectors.append(normalized)
                    meta_rows.append(
                        {
                            "vector_index": vector_index,
                            "rag_category": RAG_CATEGORY,
                            "source_path": candidate.source_path,
                            "series_name": candidate.series_name,
                            "text_hash": candidate.text_hash,
                            "headline_ja": candidate.headline_ja,
                            "source_ext": candidate.source_ext,
                            "extract_status": candidate.extract_status,
                            "source_text_chars": candidate.source_text_chars,
                            "chunk_index": candidate.chunk_index,
                            "chunk_start": candidate.chunk_start,
                            "chunk_end": candidate.chunk_end,
                            "chunk_chars": len(candidate.chunk_text),
                            "text_len": candidate.source_text_chars,
                            "embed_input_len": len(candidate.embedding_input),
                            "is_truncated": candidate.is_truncated,
                            "embedding_input_chars": len(candidate.embedding_input),
                            "embedding_model": model,
                            "embedding_task_type": EMBED_TASK_TYPE,
                            "embedding_dim": EMBED_OUTPUT_DIM,
                        }
                    )
                    counters["embedded_chunks"] += 1
            except Exception as batch_exc:  # noqa: BLE001
                counters["batch_level_failures"] += 1
                # Batch failure fallback: retry one by one so that one bad chunk doesn't block progress.
                for candidate in batch:
                    try:
                        single_embedding = embed_batch(
                            client=client, model=model, contents=[candidate.embedding_input]
                        )[0]
                        normalized = l2_normalize(single_embedding)
                        vector_index = len(vectors)
                        vectors.append(normalized)
                        meta_rows.append(
                            {
                                "vector_index": vector_index,
                                "rag_category": RAG_CATEGORY,
                                "source_path": candidate.source_path,
                                "series_name": candidate.series_name,
                                "text_hash": candidate.text_hash,
                                "headline_ja": candidate.headline_ja,
                                "source_ext": candidate.source_ext,
                                "extract_status": candidate.extract_status,
                                "source_text_chars": candidate.source_text_chars,
                                "chunk_index": candidate.chunk_index,
                                "chunk_start": candidate.chunk_start,
                                "chunk_end": candidate.chunk_end,
                                "chunk_chars": len(candidate.chunk_text),
                                "text_len": candidate.source_text_chars,
                                "embed_input_len": len(candidate.embedding_input),
                                "is_truncated": candidate.is_truncated,
                                "embedding_input_chars": len(candidate.embedding_input),
                                "embedding_model": model,
                                "embedding_task_type": EMBED_TASK_TYPE,
                                "embedding_dim": EMBED_OUTPUT_DIM,
                            }
                        )
                        counters["embedded_chunks"] += 1
                    except Exception as single_exc:  # noqa: BLE001
                        counters["failed_embedding_generation"] += 1
                        failed_rows.append(
                            {
                                "source_path": candidate.source_path,
                                "chunk_index": candidate.chunk_index,
                                "status": "EMBED_FAILED",
                                "error": str(single_exc),
                                "batch_error": str(batch_exc),
                            }
                        )

    vector_matrix = (
        np.vstack(vectors).astype(np.float32)
        if vectors
        else np.zeros((0, EMBED_OUTPUT_DIM), dtype=np.float32)
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    np.save(INDEX_PATH, vector_matrix)
    write_jsonl(META_PATH, meta_rows)
    write_jsonl(FAILED_PATH, failed_rows)

    completed_at = utc_now_iso()
    manifest = {
        "target_year": "all",
        "generated_at": completed_at,
        "files": build_manifest_files([INDEX_PATH, META_PATH]),
        "rag_category": RAG_CATEGORY,
        "embedding_model": model,
        "embedding_task_type": EMBED_TASK_TYPE,
        "embedding_dim": EMBED_OUTPUT_DIM,
    }
    write_json(MANIFEST_PATH, manifest)

    skipped_source_records_count = (
        counters.get("skipped_missing_source_path", 0)
        + counters.get("skipped_duplicate_source_path", 0)
        + counters.get("skipped_empty_text", 0)
        + counters.get("skipped_empty_after_chunk_split", 0)
    )

    summary = {
        "started_at": started_at,
        "completed_at": completed_at,
        "input_jsonl_path": str(INPUT_JSONL_PATH),
        "records_total": len(rows),
        "source_records_with_text": counters.get("source_records_with_text", 0),
        "chunk_size_chars": CHUNK_SIZE_CHARS,
        "chunk_overlap_chars": CHUNK_OVERLAP_CHARS,
        "chunk_step_chars": CHUNK_SIZE_CHARS - CHUNK_OVERLAP_CHARS,
        "embed_input_max_chars": EMBED_INPUT_MAX_CHARS,
        "embedding_input_count": len(candidates),
        "embedding_model": model,
        "embedding_task_type": EMBED_TASK_TYPE,
        "embedding_dim": EMBED_OUTPUT_DIM,
        "embedded_count": len(meta_rows),
        "skipped_empty_text_count": counters.get("skipped_empty_text", 0),
        "skipped_source_records_count": skipped_source_records_count,
        "failed_count": len(failed_rows),
        "output_index_path": str(INDEX_PATH),
        "output_meta_path": str(META_PATH),
        "output_failed_path": str(FAILED_PATH),
        "output_manifest_path": str(MANIFEST_PATH),
        "counters": dict(counters),
    }
    write_json(SUMMARY_PATH, summary)

    print(
        "[DONE] Tarutani_Text vectorization complete. "
        f"records_total={summary['records_total']} "
        f"chunks={summary['embedding_input_count']} "
        f"embedded={summary['embedded_count']} "
        f"skipped_records={summary['skipped_source_records_count']} "
        f"failed={summary['failed_count']}"
    )
    print(f"[DONE] index={INDEX_PATH}")
    print(f"[DONE] meta={META_PATH}")
    print(f"[DONE] summary={SUMMARY_PATH}")
    print(f"[DONE] manifest={MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
