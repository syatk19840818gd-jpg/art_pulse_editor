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
from phase2_art_pulse_config import get_current_raw_paths
TARGET_YEAR = 2025
RAG_CATEGORY = "artists_text"

RAW_INPUT_PATHS = get_current_raw_paths("artists", TARGET_YEAR)

OUTPUT_DIR = Path("data/current/vector/artists")
INDEX_PATH = OUTPUT_DIR / "artists_text_index_2025.npy"
META_PATH = OUTPUT_DIR / "artists_text_meta_2025.jsonl"
FAILED_PATH = OUTPUT_DIR / "artists_text_vectorize_failed_2025.jsonl"
SUMMARY_PATH = OUTPUT_DIR / "artists_text_vectorize_summary_2025.json"
MANIFEST_PATH = OUTPUT_DIR / "artists_text_artifact_manifest_2025.json"
MANIFEST_R2_PREFIX = "data/current/vector/artists"

EMBEDDING_MODEL_DEFAULT = "gemini-embedding-001"
EMBED_TASK_TYPE = "RETRIEVAL_DOCUMENT"
EMBED_OUTPUT_DIM = 1536
EMBED_BATCH_SIZE = 8
EMBED_INPUT_MAX_CHARS = 2000


@dataclass
class EmbeddingCandidate:
    fair_slug: str
    source_url: str
    text_hash: str
    gallery_name_en: str
    gallery_name_kana: str
    headline_ja: str
    text: str
    text_len: int
    embedding_input: str
    embed_input_len: int
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
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
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


def build_embedding_input(headline_ja: str, text: str) -> tuple[str, bool]:
    headline = (headline_ja or "").strip()
    body = (text or "").strip()
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
    for env_key in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        value = os.getenv(env_key)
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
        try:
            rel = path.relative_to(OUTPUT_DIR).as_posix()
        except ValueError:
            rel = path.name
        r2_key = f"{MANIFEST_R2_PREFIX}/{rel}"
        files.append(
            {
                "path": r2_key,
                "local_path": path.as_posix(),
                "etag": "",
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )
    return files


def build_source_key(fair_slug: str, source_url: str, text_hash: str) -> str:
    payload = f"{fair_slug}\n{source_url.strip()}\n{text_hash.strip()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def main() -> int:
    started_at = utc_now_iso()
    print(f"[START] artists_text vectorization at {started_at}")

    for fair_slug, raw_path in RAW_INPUT_PATHS.items():
        if not raw_path.exists():
            raise FileNotFoundError(f"Missing artists raw input for {fair_slug}: {raw_path}")

    load_dotenv()
    model = os.getenv("TEXT_EMBEDDING_MODEL", EMBEDDING_MODEL_DEFAULT)
    api_key = get_gemini_api_key()
    client: genai.Client | None = genai.Client(api_key=api_key) if api_key else None

    counters: defaultdict[str, int] = defaultdict(int)
    candidates: list[EmbeddingCandidate] = []
    seen_source_keys: set[str] = set()

    raw_rows_by_fair = {fair_slug: read_jsonl(path) for fair_slug, path in RAW_INPUT_PATHS.items()}
    raw_rows_total = 0

    for fair_slug, rows in raw_rows_by_fair.items():
        raw_rows_total += len(rows)
        for row in rows:
            text = str(row.get("text") or "").strip()
            text_hash = str(row.get("text_hash") or "").strip()
            source_url = str(row.get("source_url") or "").strip()
            headline_ja = str(row.get("headline_ja") or "").strip()

            if not text:
                counters["skipped_empty_text"] += 1
                continue
            if not text_hash:
                counters["skipped_missing_text_hash"] += 1
                continue
            if not source_url:
                counters["skipped_missing_source_url"] += 1
                continue

            source_key = build_source_key(fair_slug, source_url, text_hash)
            if source_key in seen_source_keys:
                counters["skipped_duplicate_source_key"] += 1
                continue
            seen_source_keys.add(source_key)

            embedding_input, is_truncated = build_embedding_input(headline_ja=headline_ja, text=text)
            if not embedding_input:
                counters["skipped_empty_embedding_input"] += 1
                continue
            if is_truncated:
                counters["embedding_input_truncated"] += 1

            candidates.append(
                EmbeddingCandidate(
                    fair_slug=fair_slug,
                    source_url=source_url,
                    text_hash=text_hash,
                    gallery_name_en=str(row.get("gallery_name_en") or ""),
                    gallery_name_kana=str(row.get("gallery_name_kana") or ""),
                    headline_ja=headline_ja,
                    text=text,
                    text_len=len(text),
                    embedding_input=embedding_input,
                    embed_input_len=len(embedding_input),
                    is_truncated=is_truncated,
                )
            )

    input_total = len(candidates)
    counters["input_total"] = input_total
    counters["raw_rows_total"] = raw_rows_total

    vectors: list[np.ndarray] = []
    meta_rows: list[dict[str, Any]] = []
    failed_rows: list[dict[str, Any]] = []

    if input_total > 0 and client is None:
        for candidate in candidates:
            failed_rows.append(
                {
                    "fair_slug": candidate.fair_slug,
                    "source_url": candidate.source_url,
                    "text_hash": candidate.text_hash,
                    "status": "EMBED_FAILED_MISSING_GEMINI_API_KEY",
                    "error": "Missing GEMINI_API_KEY/GOOGLE_API_KEY",
                }
            )
        counters["failed_embedding_generation"] += input_total

    if input_total > 0 and client is not None:
        for offset in range(0, input_total, EMBED_BATCH_SIZE):
            batch = candidates[offset : offset + EMBED_BATCH_SIZE]
            contents = [item.embedding_input for item in batch]
            try:
                batch_embeddings = embed_batch(client=client, model=model, contents=contents)
                for candidate, emb_values in zip(batch, batch_embeddings):
                    try:
                        normalized = l2_normalize(emb_values)
                    except Exception as exc:  # noqa: BLE001
                        counters["failed_zero_norm_or_invalid"] += 1
                        failed_rows.append(
                            {
                                "fair_slug": candidate.fair_slug,
                                "source_url": candidate.source_url,
                                "text_hash": candidate.text_hash,
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
                            "target_year": TARGET_YEAR,
                            "fair_slug": candidate.fair_slug,
                            "source_url": candidate.source_url,
                            "text_hash": candidate.text_hash,
                            "gallery_name_en": candidate.gallery_name_en,
                            "gallery_name_kana": candidate.gallery_name_kana,
                            "headline_ja": candidate.headline_ja,
                            "text_len": candidate.text_len,
                            "embed_input_len": candidate.embed_input_len,
                            "is_truncated": candidate.is_truncated,
                            "embedding_model": model,
                            "embedding_task_type": EMBED_TASK_TYPE,
                            "embedding_dim": EMBED_OUTPUT_DIM,
                        }
                    )
                    counters["embedded_total"] += 1
            except Exception as exc:  # noqa: BLE001
                counters["batch_level_failures"] += 1
                for candidate in batch:
                    failed_rows.append(
                        {
                            "fair_slug": candidate.fair_slug,
                            "source_url": candidate.source_url,
                            "text_hash": candidate.text_hash,
                            "status": "EMBED_FAILED_BATCH",
                            "error": str(exc),
                        }
                    )
                    counters["failed_embedding_generation"] += 1

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
        "target_year": TARGET_YEAR,
        "generated_at": completed_at,
        "rag_category": RAG_CATEGORY,
        "embedding_model": model,
        "embedding_task_type": EMBED_TASK_TYPE,
        "embedding_dim": EMBED_OUTPUT_DIM,
        "files": build_manifest_files([INDEX_PATH, META_PATH]),
    }
    write_json(MANIFEST_PATH, manifest)

    skipped_total = (
        counters.get("skipped_empty_text", 0)
        + counters.get("skipped_missing_text_hash", 0)
        + counters.get("skipped_missing_source_url", 0)
        + counters.get("skipped_duplicate_source_key", 0)
        + counters.get("skipped_empty_embedding_input", 0)
    )
    embedded_total = len(meta_rows)
    failed_total = len(failed_rows)

    summary = {
        "started_at": started_at,
        "completed_at": completed_at,
        "target_year": TARGET_YEAR,
        "rag_category": RAG_CATEGORY,
        "raw_input_paths": {k: str(v) for k, v in RAW_INPUT_PATHS.items()},
        "raw_rows_total": raw_rows_total,
        "input_total": input_total,
        "embedded_total": embedded_total,
        "skipped_total": skipped_total,
        "failed_total": failed_total,
        "embedding_model": model,
        "embedding_task_type": EMBED_TASK_TYPE,
        "embedding_dim": EMBED_OUTPUT_DIM,
        "embed_input_max_chars": EMBED_INPUT_MAX_CHARS,
        "output_paths": {
            "index": str(INDEX_PATH),
            "meta": str(META_PATH),
            "failed": str(FAILED_PATH),
            "summary": str(SUMMARY_PATH),
            "manifest": str(MANIFEST_PATH),
        },
        "counters": dict(counters),
    }
    write_json(SUMMARY_PATH, summary)

    print(
        "[DONE] artists_text vectorization complete. "
        f"input_total={input_total} embedded_total={embedded_total} "
        f"skipped_total={skipped_total} failed_total={failed_total}"
    )
    print(f"[DONE] index={INDEX_PATH}")
    print(f"[DONE] meta={META_PATH}")
    print(f"[DONE] summary={SUMMARY_PATH}")
    print(f"[DONE] manifest={MANIFEST_PATH}")
    print("[SYNC] status=manual_sync_only entrypoint=run_r2_sync.py scope_hint=artists_vector_current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
