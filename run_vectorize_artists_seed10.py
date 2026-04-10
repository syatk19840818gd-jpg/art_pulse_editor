#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
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

from gallery_skip_registry import build_skip_lookup, find_skip_entry, load_skip_registry_entries
from phase2_art_pulse_config import (
    get_current_artist_text_vector_artifact_paths,
    get_current_artist_text_vector_runtime_paths,
    get_current_raw_paths,
)

TARGET_YEAR = 2025
RAG_CATEGORY = "artists_text"

RAW_INPUT_PATHS: dict[str, Path] = {}
OUTPUT_DIR = Path()
CURRENT_VECTOR_ARTIFACT_PATHS: dict[str, Path] = {}
INDEX_PATH = Path()
META_PATH = Path()
FAILED_PATH = Path()
SUMMARY_PATH = Path()
MANIFEST_PATH = Path()
MANIFEST_R2_PREFIX = ""

EMBEDDING_MODEL_DEFAULT = "gemini-embedding-001"
EMBED_TASK_TYPE = "RETRIEVAL_DOCUMENT"
EMBED_OUTPUT_DIM = 1536
EMBED_BATCH_SIZE = 8
EMBED_INPUT_MAX_CHARS = 2000


def resolve_io_root(path_text: str) -> Path | None:
    raw = str(path_text or "").strip()
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    return path


def configure_runtime_paths(io_root: Path | None) -> dict[str, Path | str]:
    global RAW_INPUT_PATHS
    global OUTPUT_DIR
    global CURRENT_VECTOR_ARTIFACT_PATHS
    global INDEX_PATH
    global META_PATH
    global FAILED_PATH
    global SUMMARY_PATH
    global MANIFEST_PATH
    global MANIFEST_R2_PREFIX

    RAW_INPUT_PATHS = get_current_raw_paths("artists", TARGET_YEAR, root=io_root)
    runtime_paths = get_current_artist_text_vector_runtime_paths(
        target_year=TARGET_YEAR,
        root=io_root,
    )
    OUTPUT_DIR = Path(runtime_paths["output_dir"])
    CURRENT_VECTOR_ARTIFACT_PATHS = {
        "index": Path(runtime_paths["index"]),
        "meta": Path(runtime_paths["meta"]),
        "manifest": Path(runtime_paths["manifest"]),
    }
    INDEX_PATH = CURRENT_VECTOR_ARTIFACT_PATHS["index"]
    META_PATH = CURRENT_VECTOR_ARTIFACT_PATHS["meta"]
    MANIFEST_PATH = CURRENT_VECTOR_ARTIFACT_PATHS["manifest"]
    FAILED_PATH = Path(runtime_paths["failed"])
    SUMMARY_PATH = Path(runtime_paths["summary"])
    MANIFEST_R2_PREFIX = str(runtime_paths["manifest_r2_prefix"] or "")
    return runtime_paths


configure_runtime_paths(None)


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


@dataclass(frozen=True)
class RepairTarget:
    fair_slug: str
    gallery_name_en: str

    @property
    def scope_key(self) -> tuple[str, str]:
        return build_repair_scope_key(self.fair_slug, self.gallery_name_en)

    def to_dict(self) -> dict[str, str]:
        return {
            "fair_slug": self.fair_slug,
            "gallery_name_en": self.gallery_name_en,
        }


@dataclass
class CandidateBuildResult:
    candidates: list[EmbeddingCandidate]
    counters: defaultdict[str, int]
    raw_rows_scanned_total: int
    raw_rows_target_total: int


@dataclass
class ExistingArtifactState:
    meta_rows: list[dict[str, Any]]
    index_matrix: np.ndarray
    failed_rows: list[dict[str, Any]]


@dataclass
class PartitionedArtifactState:
    retained_meta_rows: list[dict[str, Any]]
    retained_vectors: list[np.ndarray]
    retained_failed_rows: list[dict[str, Any]]
    removed_meta_total: int
    removed_failed_total: int


@dataclass
class EmbeddingRunResult:
    vectors: list[np.ndarray]
    meta_rows: list[dict[str, Any]]
    failed_rows: list[dict[str, Any]]
    counters: defaultdict[str, int]


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


def build_manifest_files(
    paths: list[Path],
    *,
    output_dir: Path,
    manifest_r2_prefix: str,
) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    for path in paths:
        if not path.exists():
            continue
        try:
            rel = path.relative_to(output_dir).as_posix()
        except ValueError:
            rel = path.name
        r2_key = f"{manifest_r2_prefix}/{rel}" if manifest_r2_prefix else rel
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


def build_repair_scope_key(fair_slug: str, gallery_name_en: str) -> tuple[str, str]:
    return (str(fair_slug or "").strip().casefold(), str(gallery_name_en or "").strip().casefold())


def parse_repair_target_spec(raw_value: str) -> RepairTarget:
    fair_slug, separator, gallery_name_en = str(raw_value or "").partition("::")
    if not separator:
        raise ValueError(
            f"Invalid --repair-target '{raw_value}'. Expected format fair_slug::gallery_name_en"
        )
    fair_slug = fair_slug.strip()
    gallery_name_en = gallery_name_en.strip()
    if not fair_slug or not gallery_name_en:
        raise ValueError(
            f"Invalid --repair-target '{raw_value}'. Both fair_slug and gallery_name_en are required"
        )
    return RepairTarget(fair_slug=fair_slug, gallery_name_en=gallery_name_en)


def read_repair_targets_file(path: Path) -> list[RepairTarget]:
    if not path.exists():
        raise FileNotFoundError(f"Missing repair targets file: {path}")
    skip_lookup = build_skip_lookup(load_skip_registry_entries())
    targets: list[RepairTarget] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"fair_slug", "gallery_name_en"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError(
                f"Repair targets file must contain headers {sorted(required)}: {path}"
            )
        for row in reader:
            fair_slug = str(row.get("fair_slug") or "").strip()
            gallery_name_en = str(row.get("gallery_name_en") or "").strip()
            if not fair_slug and not gallery_name_en:
                continue
            if not fair_slug or not gallery_name_en:
                raise ValueError(
                    "Each repair target row must include both fair_slug and gallery_name_en"
                )
            if find_skip_entry(skip_lookup, fair_slug=fair_slug, gallery_name_en=gallery_name_en) is not None:
                continue
            targets.append(RepairTarget(fair_slug=fair_slug, gallery_name_en=gallery_name_en))
    return targets


def resolve_repair_targets(
    repair_target_specs: list[str],
    repair_targets_file: Path | None,
) -> list[RepairTarget]:
    explicit_scope_requested = bool(repair_target_specs or repair_targets_file is not None)
    targets: list[RepairTarget] = []
    for raw_value in repair_target_specs:
        targets.append(parse_repair_target_spec(raw_value))
    if repair_targets_file is not None:
        targets.extend(read_repair_targets_file(repair_targets_file))

    seen_scope_keys: set[tuple[str, str]] = set()
    deduped_targets: list[RepairTarget] = []
    for target in targets:
        if target.fair_slug not in RAW_INPUT_PATHS:
            raise ValueError(f"Unsupported fair_slug in repair scope: {target.fair_slug}")
        if target.scope_key in seen_scope_keys:
            continue
        seen_scope_keys.add(target.scope_key)
        deduped_targets.append(target)
    if explicit_scope_requested and not deduped_targets:
        raise ValueError("repair_scope_empty_after_skip_registry_filter")
    return deduped_targets


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Vectorize artist texts into current artifacts.")
    parser.add_argument(
        "--approval-token",
        default="",
        help="required for live text vectorization; inspect artifacts offline before any approved execution",
    )
    parser.add_argument(
        "--io-root",
        default="",
        help="optional trial I/O root; when set, raw input and vector artifacts resolve under this root",
    )
    parser.add_argument(
        "--repair-target",
        action="append",
        default=[],
        help="Bounded repair target in the format fair_slug::gallery_name_en. Repeatable.",
    )
    parser.add_argument(
        "--repair-targets-file",
        type=Path,
        help="CSV file with columns fair_slug,gallery_name_en for bounded repair mode.",
    )
    return parser.parse_args(argv)


def require_vectorize_approval(args: argparse.Namespace) -> None:
    if str(args.approval_token or "").strip():
        return
    raise RuntimeError(
        "approval_required_for_text_vectorize:"
        "pass --approval-token <user-approved-note>; inspect raw/meta artifacts offline before approved execution"
    )


def select_raw_input_paths(repair_targets: list[RepairTarget]) -> dict[str, Path]:
    if not repair_targets:
        return RAW_INPUT_PATHS
    selected_fairs = {target.fair_slug for target in repair_targets}
    return {fair_slug: RAW_INPUT_PATHS[fair_slug] for fair_slug in selected_fairs}


def build_candidate_from_row(
    fair_slug: str,
    row: dict[str, Any],
    counters: defaultdict[str, int],
    seen_source_keys: set[str],
) -> EmbeddingCandidate | None:
    text = str(row.get("text") or "").strip()
    text_hash = str(row.get("text_hash") or "").strip()
    source_url = str(row.get("source_url") or "").strip()
    headline_ja = str(row.get("headline_ja") or "").strip()

    if not text:
        counters["skipped_empty_text"] += 1
        return None
    if not text_hash:
        counters["skipped_missing_text_hash"] += 1
        return None
    if not source_url:
        counters["skipped_missing_source_url"] += 1
        return None

    source_key = build_source_key(fair_slug, source_url, text_hash)
    if source_key in seen_source_keys:
        counters["skipped_duplicate_source_key"] += 1
        return None
    seen_source_keys.add(source_key)

    embedding_input, is_truncated = build_embedding_input(headline_ja=headline_ja, text=text)
    if not embedding_input:
        counters["skipped_empty_embedding_input"] += 1
        return None
    if is_truncated:
        counters["embedding_input_truncated"] += 1

    return EmbeddingCandidate(
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


def build_embedding_candidates(
    raw_input_paths: dict[str, Path],
    *,
    repair_scope_keys: set[tuple[str, str]] | None = None,
) -> CandidateBuildResult:
    counters: defaultdict[str, int] = defaultdict(int)
    candidates: list[EmbeddingCandidate] = []
    seen_source_keys: set[str] = set()
    raw_rows_scanned_total = 0
    raw_rows_target_total = 0

    for fair_slug, raw_path in raw_input_paths.items():
        if not raw_path.exists():
            raise FileNotFoundError(f"Missing artists raw input for {fair_slug}: {raw_path}")
        rows = read_jsonl(raw_path)
        raw_rows_scanned_total += len(rows)
        for row in rows:
            scope_key = build_repair_scope_key(fair_slug, str(row.get("gallery_name_en") or ""))
            if repair_scope_keys is not None and scope_key not in repair_scope_keys:
                continue
            raw_rows_target_total += 1
            candidate = build_candidate_from_row(
                fair_slug=fair_slug,
                row=row,
                counters=counters,
                seen_source_keys=seen_source_keys,
            )
            if candidate is None:
                continue
            candidates.append(candidate)

    counters["input_total"] = len(candidates)
    counters["raw_rows_total"] = raw_rows_target_total
    counters["raw_rows_scanned_total"] = raw_rows_scanned_total
    return CandidateBuildResult(
        candidates=candidates,
        counters=counters,
        raw_rows_scanned_total=raw_rows_scanned_total,
        raw_rows_target_total=raw_rows_target_total,
    )


def load_existing_artifact_state(*, allow_missing_base: bool = False) -> ExistingArtifactState:
    meta_exists = META_PATH.exists()
    index_exists = INDEX_PATH.exists()
    if not meta_exists and not index_exists and allow_missing_base:
        return ExistingArtifactState(
            meta_rows=[],
            index_matrix=np.zeros((0, EMBED_OUTPUT_DIM), dtype=np.float32),
            failed_rows=[],
        )
    if not meta_exists:
        raise FileNotFoundError(f"Missing vector meta artifact for repair mode: {META_PATH}")
    if not index_exists:
        raise FileNotFoundError(f"Missing vector index artifact for repair mode: {INDEX_PATH}")

    meta_rows = read_jsonl(META_PATH)
    index_matrix = np.load(INDEX_PATH)
    if index_matrix.ndim != 2:
        raise ValueError(f"Unexpected current index shape for repair mode: {index_matrix.shape}")
    if len(meta_rows) != int(index_matrix.shape[0]):
        raise ValueError(
            "Current text vector artifacts are inconsistent: "
            f"meta_rows={len(meta_rows)} index_rows={int(index_matrix.shape[0])}"
        )

    failed_rows = read_jsonl(FAILED_PATH) if FAILED_PATH.exists() else []
    return ExistingArtifactState(
        meta_rows=meta_rows,
        index_matrix=index_matrix.astype(np.float32, copy=False),
        failed_rows=failed_rows,
    )


def partition_existing_artifacts_for_repair(
    state: ExistingArtifactState,
    repair_scope_keys: set[tuple[str, str]],
) -> PartitionedArtifactState:
    retained_meta_rows: list[dict[str, Any]] = []
    retained_vectors: list[np.ndarray] = []
    retained_failed_rows: list[dict[str, Any]] = []
    removed_meta_total = 0
    removed_failed_total = 0

    for position, row in enumerate(state.meta_rows):
        scope_key = build_repair_scope_key(
            str(row.get("fair_slug") or ""),
            str(row.get("gallery_name_en") or ""),
        )
        vector_index = int(row.get("vector_index", position))
        if vector_index < 0 or vector_index >= int(state.index_matrix.shape[0]):
            raise ValueError(f"Invalid vector_index in current meta: {vector_index}")
        if scope_key in repair_scope_keys:
            removed_meta_total += 1
            continue
        retained_meta_rows.append(dict(row))
        retained_vectors.append(state.index_matrix[vector_index].astype(np.float32, copy=True))

    for row in state.failed_rows:
        gallery_name_en = str(row.get("gallery_name_en") or "")
        fair_slug = str(row.get("fair_slug") or "")
        if gallery_name_en and build_repair_scope_key(fair_slug, gallery_name_en) in repair_scope_keys:
            removed_failed_total += 1
            continue
        retained_failed_rows.append(dict(row))

    return PartitionedArtifactState(
        retained_meta_rows=retained_meta_rows,
        retained_vectors=retained_vectors,
        retained_failed_rows=retained_failed_rows,
        removed_meta_total=removed_meta_total,
        removed_failed_total=removed_failed_total,
    )


def generate_embeddings(
    candidates: list[EmbeddingCandidate],
    *,
    client: genai.Client | None,
    model: str,
) -> EmbeddingRunResult:
    counters: defaultdict[str, int] = defaultdict(int)
    vectors: list[np.ndarray] = []
    meta_rows: list[dict[str, Any]] = []
    failed_rows: list[dict[str, Any]] = []

    if candidates and client is None:
        for candidate in candidates:
            failed_rows.append(
                {
                    "fair_slug": candidate.fair_slug,
                    "gallery_name_en": candidate.gallery_name_en,
                    "source_url": candidate.source_url,
                    "text_hash": candidate.text_hash,
                    "status": "EMBED_FAILED_MISSING_GEMINI_API_KEY",
                    "error": "Missing GEMINI_API_KEY/GOOGLE_API_KEY",
                }
            )
        counters["failed_embedding_generation"] += len(candidates)
        return EmbeddingRunResult(
            vectors=vectors,
            meta_rows=meta_rows,
            failed_rows=failed_rows,
            counters=counters,
        )

    for offset in range(0, len(candidates), EMBED_BATCH_SIZE):
        batch = candidates[offset : offset + EMBED_BATCH_SIZE]
        contents = [item.embedding_input for item in batch]
        try:
            batch_embeddings = embed_batch(client=client, model=model, contents=contents)  # type: ignore[arg-type]
            for candidate, emb_values in zip(batch, batch_embeddings):
                try:
                    normalized = l2_normalize(emb_values)
                except Exception as exc:  # noqa: BLE001
                    counters["failed_zero_norm_or_invalid"] += 1
                    failed_rows.append(
                        {
                            "fair_slug": candidate.fair_slug,
                            "gallery_name_en": candidate.gallery_name_en,
                            "source_url": candidate.source_url,
                            "text_hash": candidate.text_hash,
                            "status": "EMBED_FAILED_NORMALIZE",
                            "error": str(exc),
                        }
                    )
                    continue

                vectors.append(normalized)
                meta_rows.append(
                    {
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
                        "gallery_name_en": candidate.gallery_name_en,
                        "source_url": candidate.source_url,
                        "text_hash": candidate.text_hash,
                        "status": "EMBED_FAILED_BATCH",
                        "error": str(exc),
                    }
                )
                counters["failed_embedding_generation"] += 1

    return EmbeddingRunResult(
        vectors=vectors,
        meta_rows=meta_rows,
        failed_rows=failed_rows,
        counters=counters,
    )


def merge_artifacts(
    *,
    retained_meta_rows: list[dict[str, Any]],
    retained_vectors: list[np.ndarray],
    repaired_meta_rows: list[dict[str, Any]],
    repaired_vectors: list[np.ndarray],
) -> tuple[list[dict[str, Any]], np.ndarray, defaultdict[str, int]]:
    merge_counters: defaultdict[str, int] = defaultdict(int)
    final_meta_rows: list[dict[str, Any]] = []
    final_vectors: list[np.ndarray] = []
    seen_source_keys: set[str] = set()

    for row, vector in zip(retained_meta_rows, retained_vectors):
        source_key = build_source_key(
            str(row.get("fair_slug") or ""),
            str(row.get("source_url") or ""),
            str(row.get("text_hash") or ""),
        )
        if source_key in seen_source_keys:
            merge_counters["skipped_duplicate_retained_source_key"] += 1
            continue
        seen_source_keys.add(source_key)
        final_meta_rows.append(dict(row))
        final_vectors.append(vector.astype(np.float32, copy=True))

    for row, vector in zip(repaired_meta_rows, repaired_vectors):
        source_key = build_source_key(
            str(row.get("fair_slug") or ""),
            str(row.get("source_url") or ""),
            str(row.get("text_hash") or ""),
        )
        if source_key in seen_source_keys:
            merge_counters["skipped_duplicate_repair_source_key_against_final"] += 1
            continue
        seen_source_keys.add(source_key)
        final_meta_rows.append(dict(row))
        final_vectors.append(vector.astype(np.float32, copy=True))

    for vector_index, row in enumerate(final_meta_rows):
        row["vector_index"] = vector_index

    vector_matrix = (
        np.vstack(final_vectors).astype(np.float32)
        if final_vectors
        else np.zeros((0, EMBED_OUTPUT_DIM), dtype=np.float32)
    )
    return final_meta_rows, vector_matrix, merge_counters


def build_manifest(
    *,
    completed_at: str,
    model: str,
    run_mode: str,
    repair_targets: list[RepairTarget],
) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "target_year": TARGET_YEAR,
        "generated_at": completed_at,
        "rag_category": RAG_CATEGORY,
        "embedding_model": model,
        "embedding_task_type": EMBED_TASK_TYPE,
        "embedding_dim": EMBED_OUTPUT_DIM,
        "run_mode": run_mode,
        "files": build_manifest_files(
            [INDEX_PATH, META_PATH],
            output_dir=OUTPUT_DIR,
            manifest_r2_prefix=MANIFEST_R2_PREFIX,
        ),
    }
    if repair_targets:
        manifest["repair_scope"] = [target.to_dict() for target in repair_targets]
    return manifest


def build_summary(
    *,
    started_at: str,
    completed_at: str,
    run_mode: str,
    repair_targets: list[RepairTarget],
    raw_input_paths: dict[str, Path],
    candidate_build: CandidateBuildResult,
    model: str,
    failed_total: int,
    artifact_totals: dict[str, int],
    counters: dict[str, int],
) -> dict[str, Any]:
    skipped_total = (
        counters.get("skipped_empty_text", 0)
        + counters.get("skipped_missing_text_hash", 0)
        + counters.get("skipped_missing_source_url", 0)
        + counters.get("skipped_duplicate_source_key", 0)
        + counters.get("skipped_empty_embedding_input", 0)
        + counters.get("skipped_duplicate_retained_source_key", 0)
        + counters.get("skipped_duplicate_repair_source_key_against_final", 0)
    )

    summary: dict[str, Any] = {
        "started_at": started_at,
        "completed_at": completed_at,
        "target_year": TARGET_YEAR,
        "rag_category": RAG_CATEGORY,
        "run_mode": run_mode,
        "raw_input_paths": {k: str(v) for k, v in raw_input_paths.items()},
        "raw_rows_total": candidate_build.raw_rows_target_total,
        "raw_rows_scanned_total": candidate_build.raw_rows_scanned_total,
        "input_total": counters.get("input_total", 0),
        "embedded_total": counters.get("embedded_total", 0),
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
        "artifact_totals": artifact_totals,
        "counters": counters,
    }
    if repair_targets:
        summary["repair_scope"] = [target.to_dict() for target in repair_targets]
        summary["repair_scope_total"] = len(repair_targets)
    return summary


def ensure_atomic_repair_success(
    *,
    run_mode: str,
    input_total: int,
    embedded_total: int,
    failed_total: int,
) -> None:
    if run_mode != "bounded_repair":
        return
    if input_total <= 0:
        raise RuntimeError("bounded_repair_scope_yielded_no_embedding_candidates")
    if failed_total > 0 or embedded_total != input_total:
        raise RuntimeError(
            "bounded_repair_requires_full_target_success: "
            f"input_total={input_total} embedded_total={embedded_total} failed_total={failed_total}"
        )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    require_vectorize_approval(args)
    io_root = resolve_io_root(args.io_root)
    configure_runtime_paths(io_root)
    repair_targets = resolve_repair_targets(args.repair_target, args.repair_targets_file)
    repair_scope_keys = {target.scope_key for target in repair_targets}
    run_mode = "bounded_repair" if repair_targets else "whole_current_rebuild"

    started_at = utc_now_iso()
    print(f"[START] artists_text vectorization at {started_at} mode={run_mode}")

    raw_input_paths = select_raw_input_paths(repair_targets)

    load_dotenv()
    model = os.getenv("TEXT_EMBEDDING_MODEL", EMBEDDING_MODEL_DEFAULT)
    api_key = get_gemini_api_key()
    client: genai.Client | None = genai.Client(api_key=api_key) if api_key else None

    candidate_build = build_embedding_candidates(
        raw_input_paths,
        repair_scope_keys=repair_scope_keys if repair_scope_keys else None,
    )

    counters = candidate_build.counters
    embedding_run = generate_embeddings(
        candidate_build.candidates,
        client=client,
        model=model,
    )
    counters.update(embedding_run.counters)

    retained_failed_rows: list[dict[str, Any]] = []
    retained_meta_rows: list[dict[str, Any]] = []
    retained_vectors: list[np.ndarray] = []
    removed_meta_total = 0
    removed_failed_total = 0

    if run_mode == "bounded_repair":
        existing_state = load_existing_artifact_state(allow_missing_base=io_root is not None)
        partitioned = partition_existing_artifacts_for_repair(existing_state, repair_scope_keys)
        retained_failed_rows = partitioned.retained_failed_rows
        retained_meta_rows = partitioned.retained_meta_rows
        retained_vectors = partitioned.retained_vectors
        removed_meta_total = partitioned.removed_meta_total
        removed_failed_total = partitioned.removed_failed_total
    else:
        counters["existing_meta_rows_retained"] = 0
        counters["existing_failed_rows_retained"] = 0

    embedded_total = len(embedding_run.meta_rows)
    failed_total = len(embedding_run.failed_rows)
    counters["embedded_total"] = embedded_total
    counters["failed_total"] = failed_total

    ensure_atomic_repair_success(
        run_mode=run_mode,
        input_total=len(candidate_build.candidates),
        embedded_total=embedded_total,
        failed_total=failed_total,
    )

    if run_mode == "bounded_repair":
        final_meta_rows, vector_matrix, merge_counters = merge_artifacts(
            retained_meta_rows=retained_meta_rows,
            retained_vectors=retained_vectors,
            repaired_meta_rows=embedding_run.meta_rows,
            repaired_vectors=embedding_run.vectors,
        )
        counters.update(merge_counters)
        final_failed_rows = retained_failed_rows + embedding_run.failed_rows
        counters["existing_meta_rows_retained"] = len(retained_meta_rows)
        counters["existing_failed_rows_retained"] = len(retained_failed_rows)
    else:
        final_meta_rows, vector_matrix, merge_counters = merge_artifacts(
            retained_meta_rows=[],
            retained_vectors=[],
            repaired_meta_rows=embedding_run.meta_rows,
            repaired_vectors=embedding_run.vectors,
        )
        counters.update(merge_counters)
        final_failed_rows = embedding_run.failed_rows
        removed_meta_total = 0
        removed_failed_total = 0

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    np.save(INDEX_PATH, vector_matrix)
    write_jsonl(META_PATH, final_meta_rows)
    write_jsonl(FAILED_PATH, final_failed_rows)

    completed_at = utc_now_iso()
    manifest = build_manifest(
        completed_at=completed_at,
        model=model,
        run_mode=run_mode,
        repair_targets=repair_targets,
    )
    write_json(MANIFEST_PATH, manifest)

    artifact_totals = {
        "existing_meta_removed": removed_meta_total,
        "existing_failed_removed": removed_failed_total,
        "retained_meta_total": len(retained_meta_rows),
        "retained_failed_total": len(retained_failed_rows),
        "repaired_meta_total": len(embedding_run.meta_rows),
        "repaired_failed_total": len(embedding_run.failed_rows),
        "final_meta_total": len(final_meta_rows),
        "final_failed_total": len(final_failed_rows),
        "final_index_rows_total": int(vector_matrix.shape[0]),
    }

    summary = build_summary(
        started_at=started_at,
        completed_at=completed_at,
        run_mode=run_mode,
        repair_targets=repair_targets,
        raw_input_paths=raw_input_paths,
        candidate_build=candidate_build,
        model=model,
        failed_total=len(final_failed_rows) if run_mode == "bounded_repair" else failed_total,
        artifact_totals=artifact_totals,
        counters=dict(counters),
    )
    write_json(SUMMARY_PATH, summary)

    print(
        "[DONE] artists_text vectorization complete. "
        f"mode={run_mode} input_total={len(candidate_build.candidates)} "
        f"embedded_total={embedded_total} final_meta_total={len(final_meta_rows)} "
        f"failed_total={len(final_failed_rows)}"
    )
    print(f"[DONE] index={INDEX_PATH}")
    print(f"[DONE] meta={META_PATH}")
    print(f"[DONE] summary={SUMMARY_PATH}")
    print(f"[DONE] manifest={MANIFEST_PATH}")
    sync_scope_hint = "artists_vector_current" if io_root is None else "artists_vector_trial"
    print(f"[SYNC] status=manual_sync_only entrypoint=run_r2_sync.py scope_hint={sync_scope_hint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
