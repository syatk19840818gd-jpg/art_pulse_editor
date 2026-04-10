#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from closeout_breakdown_contract import (
    BLOCK_ARTIFACT_CATEGORY_ARTIST,
    BLOCK_ARTIFACT_CATEGORY_ARTIST_WORKS_IMAGES,
    execute_closeout_with_breakdown_contract,
    resolve_current_formal_artifact_bundle,
)
from phase2_art_pulse_config import (
    TARGET_YEAR,
    get_current_artist_image_meta_paths,
    get_current_artist_text_vector_runtime_paths,
    get_current_artist_works_vector_runtime_paths,
    get_current_exhibitions_image_meta_paths,
    get_current_raw_paths,
    get_enrichment_current_output_path,
    get_enrichment_current_summary_path,
)
from run_rag_gallery_breakdown_update import (
    DEFAULT_XLSX_PATH,
    GalleryStats,
    ScopeTarget,
    SHEET_BY_FAIR,
    first_non_empty,
    infer_artist_image_count,
    load_targets_ordered,
    normalize_gallery_name,
    normalize_url,
)

DEFAULT_RUN_ID_PREFIX = "TASK_PHASE3_ARTISTS_TRIAL_CLOSEOUT"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def utc_now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_path(path_text: str | Path) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return (Path.cwd() / path).resolve()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Stabilization-only helper for closing out artist trial artifacts into current "
            "with bounded merges, xlsx update, and required R2 sync of current formal artifacts."
        )
    )
    parser.add_argument("--trial-root", required=True, help="trial root used as source of truth")
    parser.add_argument(
        "--targets-file",
        required=True,
        help="gallery scope CSV for this bounded trial closeout",
    )
    parser.add_argument(
        "--xlsx-path",
        default=str(DEFAULT_XLSX_PATH),
        help=f"xlsx path (default: {DEFAULT_XLSX_PATH})",
    )
    parser.add_argument(
        "--run-id",
        default="",
        help=f"run_id for xlsx/current summaries (default: {DEFAULT_RUN_ID_PREFIX}_<UTCSTAMP>)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="write current artifacts, update xlsx, and execute required R2 sync for the closeout bundle",
    )
    parser.add_argument(
        "--approval-token",
        default="",
        help="required for --apply; inspect trial/current artifacts offline before any approved closeout",
    )
    return parser.parse_args(argv)


def require_trial_closeout_approval(args: argparse.Namespace) -> None:
    if not args.apply:
        return
    if str(args.approval_token or "").strip():
        return
    raise RuntimeError(
        "approval_required_for_trial_closeout_apply:"
        "pass --approval-token <user-approved-note>; offline diff/audit remains available without --apply"
    )


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
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


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_text = tempfile.mkstemp(prefix=f"{path.name}.", suffix=".tmp", dir=str(path.parent))
    os.close(fd)
    temp_path = Path(temp_text)
    try:
        temp_path.write_text(content, encoding="utf-8")
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)


def write_json_atomic(path: Path, obj: Any) -> None:
    atomic_write_text(path, json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def write_jsonl_atomic(path: Path, rows: list[dict[str, Any]]) -> None:
    content = ""
    if rows:
        content = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n"
    atomic_write_text(path, content)


def write_npy_atomic(path: Path, matrix: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_text = tempfile.mkstemp(prefix=f"{path.stem}.", suffix=".tmp.npy", dir=str(path.parent))
    os.close(fd)
    temp_path = Path(temp_text)
    try:
        np.save(temp_path, matrix.astype(np.float32))
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def row_signature(row: dict[str, Any]) -> str:
    return sha256_bytes(json.dumps(row, ensure_ascii=False, sort_keys=True).encode("utf-8"))


def build_scope_key(fair_slug: str, gallery_name_en: str) -> tuple[str, str]:
    return (str(fair_slug or "").strip().casefold(), normalize_gallery_name(gallery_name_en))


def target_scope_counter(rows: list[dict[str, Any]], target_scope_keys: set[tuple[str, str]]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for row in rows:
        if build_scope_key(str(row.get("fair_slug") or ""), str(row.get("gallery_name_en") or "")) in target_scope_keys:
            gallery_name_en = str(row.get("gallery_name_en") or "").strip()
            counter[gallery_name_en] += 1
    return dict(counter)


def build_source_scope_maps(rows_by_fair: dict[str, list[dict[str, Any]]]) -> tuple[dict[tuple[str, str], tuple[str, str]], dict[str, tuple[str, str]]]:
    scoped: dict[tuple[str, str], tuple[str, str]] = {}
    fallback: dict[str, tuple[str, str]] = {}
    for fair_slug, rows in rows_by_fair.items():
        for row in rows:
            source_url = normalize_url(str(row.get("source_url") or ""))
            gallery_name_en = str(row.get("gallery_name_en") or "").strip()
            if not source_url or not gallery_name_en:
                continue
            scope_key = build_scope_key(fair_slug, gallery_name_en)
            scoped[(fair_slug, source_url)] = scope_key
            fallback.setdefault(source_url, scope_key)
    return scoped, fallback


def resolve_enrichment_scope_key(
    row: dict[str, Any],
    *,
    scoped_source_map: dict[tuple[str, str], tuple[str, str]],
    fallback_source_map: dict[str, tuple[str, str]],
) -> tuple[str, str]:
    fair_slug = str(row.get("fair_slug") or "").strip()
    gallery_name_en = str(row.get("gallery_name_en") or "").strip()
    if fair_slug and gallery_name_en:
        return build_scope_key(fair_slug, gallery_name_en)
    source_url = normalize_url(str(row.get("source_url") or ""))
    if fair_slug and (fair_slug, source_url) in scoped_source_map:
        return scoped_source_map[(fair_slug, source_url)]
    if source_url in fallback_source_map:
        return fallback_source_map[source_url]
    return ("", "")


def extract_trial_enrichment_source(trial_root: Path) -> dict[str, Any]:
    artists_dir = trial_root / "eh" / "artists"
    if not artists_dir.exists():
        raise FileNotFoundError(f"Missing trial enrichment dir: {artists_dir}")
    nonempty_outputs = sorted(
        (path for path in artists_dir.glob("artists_out_2025_*.jsonl") if path.stat().st_size > 0),
        key=lambda path: path.stat().st_mtime,
    )
    if not nonempty_outputs:
        raise FileNotFoundError(f"No non-empty trial artists apply output found in {artists_dir}")
    output_path = nonempty_outputs[-1]
    stamp = output_path.stem.split("_")[-1]
    summary_path = artists_dir / f"artists_summary_2025_{stamp}.json"
    manifest_path = artists_dir / f"artists_manifest_2025_{stamp}.json"
    if not summary_path.exists():
        raise FileNotFoundError(f"Missing trial enrichment summary matching {output_path.name}")
    return {
        "output_path": output_path,
        "summary_path": summary_path,
        "manifest_path": manifest_path,
        "summary": read_json(summary_path),
        "manifest": read_json(manifest_path) if manifest_path.exists() else {},
    }


def ensure_jsonl_scope_preserved(
    *,
    current_rows: list[dict[str, Any]],
    final_rows: list[dict[str, Any]],
    target_scope_keys: set[tuple[str, str]],
    label: str,
) -> None:
    before_non_target = Counter(
        row_signature(row)
        for row in current_rows
        if build_scope_key(str(row.get("fair_slug") or ""), str(row.get("gallery_name_en") or "")) not in target_scope_keys
    )
    after_non_target = Counter(
        row_signature(row)
        for row in final_rows
        if build_scope_key(str(row.get("fair_slug") or ""), str(row.get("gallery_name_en") or "")) not in target_scope_keys
    )
    if before_non_target != after_non_target:
        raise RuntimeError(f"{label}_non_target_rows_changed")


def merge_jsonl_rows_by_scope(
    *,
    current_rows: list[dict[str, Any]],
    trial_rows: list[dict[str, Any]],
    target_scope_keys: set[tuple[str, str]],
    label: str,
) -> dict[str, Any]:
    retained_rows = [
        dict(row)
        for row in current_rows
        if build_scope_key(str(row.get("fair_slug") or ""), str(row.get("gallery_name_en") or "")) not in target_scope_keys
    ]
    trial_target_rows = [
        dict(row)
        for row in trial_rows
        if build_scope_key(str(row.get("fair_slug") or ""), str(row.get("gallery_name_en") or "")) in target_scope_keys
    ]
    final_rows = retained_rows + trial_target_rows
    ensure_jsonl_scope_preserved(
        current_rows=current_rows,
        final_rows=final_rows,
        target_scope_keys=target_scope_keys,
        label=label,
    )
    return {
        "current_target_rows_total": sum(1 for row in current_rows if build_scope_key(str(row.get("fair_slug") or ""), str(row.get("gallery_name_en") or "")) in target_scope_keys),
        "trial_target_rows_total": len(trial_target_rows),
        "retained_non_target_rows_total": len(retained_rows),
        "final_rows_total": len(final_rows),
        "final_rows": final_rows,
    }


def vector_bytes_digest(vector: np.ndarray) -> str:
    return sha256_bytes(np.asarray(vector, dtype=np.float32).tobytes())


def build_text_source_key(row: dict[str, Any]) -> str:
    return hashlib.sha256(
        (
            f"{str(row.get('fair_slug') or '').strip()}\n"
            f"{normalize_url(str(row.get('source_url') or ''))}\n"
            f"{str(row.get('text_hash') or '').strip()}"
        ).encode("utf-8")
    ).hexdigest()


def build_manifest_files(paths: list[Path], *, output_dir: Path, manifest_r2_prefix: str) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    for path in paths:
        if not path.exists():
            continue
        try:
            rel = path.relative_to(output_dir).as_posix()
        except ValueError:
            rel = path.name
        manifest_key = f"{manifest_r2_prefix}/{rel}" if manifest_r2_prefix else rel
        files.append(
            {
                "path": manifest_key,
                "local_path": path.as_posix(),
                "etag": "",
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )
    return files


def build_empty_matrix(cols: int) -> np.ndarray:
    return np.zeros((0, cols), dtype=np.float32)


def merge_text_vector_state(
    *,
    current_rows: list[dict[str, Any]],
    current_index: np.ndarray,
    current_failed_rows: list[dict[str, Any]],
    trial_rows: list[dict[str, Any]],
    trial_index: np.ndarray,
    trial_failed_rows: list[dict[str, Any]],
    target_scope_keys: set[tuple[str, str]],
) -> dict[str, Any]:
    if current_index.ndim != 2 or trial_index.ndim != 2:
        raise ValueError("artists_text index must be 2-D")
    if len(current_rows) != int(current_index.shape[0]):
        raise ValueError("artists_text current meta/index mismatch")
    if len(trial_rows) != int(trial_index.shape[0]):
        raise ValueError("artists_text trial meta/index mismatch")

    retained_rows: list[dict[str, Any]] = []
    retained_vectors: list[np.ndarray] = []
    current_non_target_map: dict[str, str] = {}
    removed_meta_total = 0
    for position, row in enumerate(current_rows):
        vector_index = int(row.get("vector_index", position))
        if vector_index < 0 or vector_index >= int(current_index.shape[0]):
            raise ValueError(f"artists_text invalid current vector_index={vector_index}")
        scope_key = build_scope_key(str(row.get("fair_slug") or ""), str(row.get("gallery_name_en") or ""))
        source_key = build_text_source_key(row)
        if scope_key in target_scope_keys:
            removed_meta_total += 1
            continue
        vector = current_index[vector_index].astype(np.float32, copy=True)
        retained_rows.append(dict(row))
        retained_vectors.append(vector)
        current_non_target_map[source_key] = vector_bytes_digest(vector)

    retained_failed_rows = [
        dict(row)
        for row in current_failed_rows
        if build_scope_key(str(row.get("fair_slug") or ""), str(row.get("gallery_name_en") or "")) not in target_scope_keys
    ]
    removed_failed_total = len(current_failed_rows) - len(retained_failed_rows)

    trial_target_rows: list[dict[str, Any]] = []
    trial_target_vectors: list[np.ndarray] = []
    trial_target_map: dict[str, str] = {}
    for position, row in enumerate(trial_rows):
        vector_index = int(row.get("vector_index", position))
        if vector_index < 0 or vector_index >= int(trial_index.shape[0]):
            raise ValueError(f"artists_text invalid trial vector_index={vector_index}")
        scope_key = build_scope_key(str(row.get("fair_slug") or ""), str(row.get("gallery_name_en") or ""))
        if scope_key not in target_scope_keys:
            continue
        source_key = build_text_source_key(row)
        if source_key in trial_target_map:
            raise RuntimeError(f"artists_text duplicate trial source_key in closeout: {source_key}")
        if source_key in current_non_target_map:
            raise RuntimeError(f"artists_text trial source_key collides with retained corpus: {source_key}")
        vector = trial_index[vector_index].astype(np.float32, copy=True)
        trial_target_rows.append(dict(row))
        trial_target_vectors.append(vector)
        trial_target_map[source_key] = vector_bytes_digest(vector)

    final_rows: list[dict[str, Any]] = []
    final_vectors: list[np.ndarray] = []
    for row, vector in zip(retained_rows, retained_vectors):
        final_rows.append(dict(row))
        final_vectors.append(vector)
    for row, vector in zip(trial_target_rows, trial_target_vectors):
        final_rows.append(dict(row))
        final_vectors.append(vector)
    for vector_index, row in enumerate(final_rows):
        row["vector_index"] = vector_index

    final_index = (
        np.vstack(final_vectors).astype(np.float32)
        if final_vectors
        else build_empty_matrix(int(current_index.shape[1] if current_index.shape[1:] else trial_index.shape[1]))
    )
    final_failed_rows = retained_failed_rows + [
        dict(row)
        for row in trial_failed_rows
        if build_scope_key(str(row.get("fair_slug") or ""), str(row.get("gallery_name_en") or "")) in target_scope_keys
    ]

    final_non_target_map: dict[str, str] = {}
    for position, row in enumerate(final_rows):
        scope_key = build_scope_key(str(row.get("fair_slug") or ""), str(row.get("gallery_name_en") or ""))
        if scope_key in target_scope_keys:
            continue
        final_non_target_map[build_text_source_key(row)] = vector_bytes_digest(final_index[position])
    if current_non_target_map != final_non_target_map:
        raise RuntimeError("artists_text_non_target_vectors_changed")

    return {
        "current_target_rows_total": removed_meta_total,
        "trial_target_rows_total": len(trial_target_rows),
        "retained_non_target_rows_total": len(retained_rows),
        "removed_failed_total": removed_failed_total,
        "retained_failed_total": len(retained_failed_rows),
        "trial_failed_total": len(final_failed_rows) - len(retained_failed_rows),
        "final_rows": final_rows,
        "final_index": final_index,
        "final_failed_rows": final_failed_rows,
    }


def build_image_vector_row_key(row: dict[str, Any]) -> str:
    image_id = str(row.get("image_id") or "").strip()
    if not image_id:
        raise ValueError("artist_works_images row missing image_id")
    return image_id


def merge_image_vector_state(
    *,
    current_rows: list[dict[str, Any]],
    current_embeddings: np.ndarray,
    current_search_index: np.ndarray,
    current_failed_rows: list[dict[str, Any]],
    trial_rows: list[dict[str, Any]],
    trial_embeddings: np.ndarray,
    trial_search_index: np.ndarray,
    trial_failed_rows: list[dict[str, Any]],
    target_scope_keys: set[tuple[str, str]],
) -> dict[str, Any]:
    if current_embeddings.ndim != 2 or current_search_index.ndim != 2:
        raise ValueError("artist_works_images current matrices must be 2-D")
    if trial_embeddings.ndim != 2 or trial_search_index.ndim != 2:
        raise ValueError("artist_works_images trial matrices must be 2-D")
    if current_embeddings.shape != current_search_index.shape:
        raise ValueError("artist_works_images current embeddings/index mismatch")
    if trial_embeddings.shape != trial_search_index.shape:
        raise ValueError("artist_works_images trial embeddings/index mismatch")
    if len(current_rows) != int(current_embeddings.shape[0]):
        raise ValueError("artist_works_images current id_map/matrix mismatch")
    if len(trial_rows) != int(trial_embeddings.shape[0]):
        raise ValueError("artist_works_images trial id_map/matrix mismatch")

    retained_rows: list[dict[str, Any]] = []
    retained_embeddings: list[np.ndarray] = []
    retained_search_index: list[np.ndarray] = []
    current_non_target_map: dict[str, tuple[str, str]] = {}
    removed_total = 0
    for position, row in enumerate(current_rows):
        scope_key = build_scope_key(str(row.get("fair_slug") or ""), str(row.get("gallery_name_en") or ""))
        row_key = build_image_vector_row_key(row)
        if scope_key in target_scope_keys:
            removed_total += 1
            continue
        emb = current_embeddings[position].astype(np.float32, copy=True)
        idx = current_search_index[position].astype(np.float32, copy=True)
        retained_rows.append(dict(row))
        retained_embeddings.append(emb)
        retained_search_index.append(idx)
        current_non_target_map[row_key] = (vector_bytes_digest(emb), vector_bytes_digest(idx))

    retained_failed_rows = [
        dict(row)
        for row in current_failed_rows
        if build_scope_key(str(row.get("fair_slug") or ""), str(row.get("gallery_name_en") or "")) not in target_scope_keys
    ]

    trial_target_rows: list[dict[str, Any]] = []
    trial_target_embeddings: list[np.ndarray] = []
    trial_target_search_index: list[np.ndarray] = []
    trial_target_keys: set[str] = set()
    for position, row in enumerate(trial_rows):
        scope_key = build_scope_key(str(row.get("fair_slug") or ""), str(row.get("gallery_name_en") or ""))
        if scope_key not in target_scope_keys:
            continue
        row_key = build_image_vector_row_key(row)
        if row_key in trial_target_keys:
            raise RuntimeError(f"artist_works_images duplicate trial image_id in closeout: {row_key}")
        if row_key in current_non_target_map:
            raise RuntimeError(f"artist_works_images trial image_id collides with retained corpus: {row_key}")
        trial_target_keys.add(row_key)
        trial_target_rows.append(dict(row))
        trial_target_embeddings.append(trial_embeddings[position].astype(np.float32, copy=True))
        trial_target_search_index.append(trial_search_index[position].astype(np.float32, copy=True))

    final_rows = retained_rows + trial_target_rows
    final_embeddings = (
        np.vstack(retained_embeddings + trial_target_embeddings).astype(np.float32)
        if retained_embeddings or trial_target_embeddings
        else build_empty_matrix(int(current_embeddings.shape[1] if current_embeddings.shape[1:] else trial_embeddings.shape[1]))
    )
    final_search_index = (
        np.vstack(retained_search_index + trial_target_search_index).astype(np.float32)
        if retained_search_index or trial_target_search_index
        else build_empty_matrix(int(current_search_index.shape[1] if current_search_index.shape[1:] else trial_search_index.shape[1]))
    )
    final_failed_rows = retained_failed_rows + [
        dict(row)
        for row in trial_failed_rows
        if build_scope_key(str(row.get("fair_slug") or ""), str(row.get("gallery_name_en") or "")) in target_scope_keys
    ]

    final_non_target_map: dict[str, tuple[str, str]] = {}
    for position, row in enumerate(final_rows):
        scope_key = build_scope_key(str(row.get("fair_slug") or ""), str(row.get("gallery_name_en") or ""))
        if scope_key in target_scope_keys:
            continue
        row_key = build_image_vector_row_key(row)
        final_non_target_map[row_key] = (
            vector_bytes_digest(final_embeddings[position]),
            vector_bytes_digest(final_search_index[position]),
        )
    if current_non_target_map != final_non_target_map:
        raise RuntimeError("artist_works_images_non_target_vectors_changed")

    return {
        "current_target_rows_total": removed_total,
        "trial_target_rows_total": len(trial_target_rows),
        "retained_non_target_rows_total": len(retained_rows),
        "retained_failed_total": len(retained_failed_rows),
        "trial_failed_total": len(final_failed_rows) - len(retained_failed_rows),
        "final_rows": final_rows,
        "final_embeddings": final_embeddings,
        "final_search_index": final_search_index,
        "final_failed_rows": final_failed_rows,
    }


def build_stats_from_artist_rows(
    *,
    artist_raw_by_fair: dict[str, list[dict[str, Any]]],
    artist_image_by_fair: dict[str, list[dict[str, Any]]],
    target_year: int,
) -> dict[tuple[str, str], GalleryStats]:
    stats: dict[tuple[str, str], GalleryStats] = {}

    def ensure(fair_slug: str, gallery_name: str) -> GalleryStats:
        key = (fair_slug, normalize_gallery_name(gallery_name))
        if key not in stats:
            stats[key] = GalleryStats(
                artist_image_keys=set(),
                artist_image_count=0,
                artist_text_keys=set(),
                artist_text_count=0,
                exhibition_image_keys=set(),
                exhibition_image_count=0,
                exhibition_text_keys=set(),
                exhibition_text_count=0,
            )
        return stats[key]

    for fair_slug, rows in artist_raw_by_fair.items():
        for row in rows:
            gallery_name = str(row.get("gallery_name_en") or "").strip()
            if not gallery_name:
                continue
            item = ensure(fair_slug, gallery_name)
            artist_key = first_non_empty(
                row.get("artist_key"),
                row.get("artist_identity_key"),
                row.get("artist_name_key"),
                normalize_url(str(row.get("source_url") or "")),
            )
            if artist_key:
                item.artist_text_keys.add(artist_key)
            item.artist_text_count += 1

    for fair_slug, rows in artist_image_by_fair.items():
        for row in rows:
            gallery_name = str(row.get("gallery_name_en") or "").strip()
            if not gallery_name:
                continue
            item = ensure(fair_slug, gallery_name)
            artist_key = first_non_empty(
                row.get("artist_key"),
                row.get("artist_identity_key"),
                row.get("artist_name_key"),
                normalize_url(str(row.get("source_url") or "")),
            )
            if artist_key:
                item.artist_image_keys.add(artist_key)
            item.artist_image_count += infer_artist_image_count(row)

    for fair_slug, path in get_current_raw_paths("exhibitions", target_year).items():
        for row in read_jsonl(resolve_path(path)):
            gallery_name = str(row.get("gallery_name_en") or "").strip()
            if not gallery_name:
                continue
            item = ensure(fair_slug, gallery_name)
            exhibition_key = first_non_empty(
                row.get("exhibition_key"),
                normalize_url(str(row.get("source_url") or "")),
            )
            if exhibition_key:
                item.exhibition_text_keys.add(exhibition_key)
            item.exhibition_text_count += 1

    for fair_slug, path in get_current_exhibitions_image_meta_paths(target_year).items():
        for row in read_jsonl(resolve_path(path)):
            gallery_name = str(row.get("gallery_name_en") or "").strip()
            if not gallery_name:
                continue
            item = ensure(fair_slug, gallery_name)
            exhibition_key = first_non_empty(
                row.get("exhibition_key"),
                normalize_url(str(row.get("source_url") or "")),
            )
            if exhibition_key:
                item.exhibition_image_keys.add(exhibition_key)
            item.exhibition_image_count += 1

    return stats


def build_text_vector_manifest(
    *,
    completed_at: str,
    current_paths: dict[str, Path | str],
    trial_summary: dict[str, Any],
    targets: list[ScopeTarget],
) -> dict[str, Any]:
    output_dir = Path(current_paths["output_dir"])
    manifest_r2_prefix = str(current_paths["manifest_r2_prefix"] or "")
    return {
        "target_year": TARGET_YEAR,
        "generated_at": completed_at,
        "rag_category": "artists_text",
        "embedding_model": str(trial_summary.get("embedding_model") or ""),
        "embedding_task_type": str(trial_summary.get("embedding_task_type") or ""),
        "embedding_dim": int(trial_summary.get("embedding_dim") or 0),
        "run_mode": "bounded_closeout_from_trial",
        "closeout_source_trial_root": str(trial_summary.get("output_paths", {}).get("meta") or ""),
        "repair_scope": [target.to_dict() for target in targets],
        "files": build_manifest_files(
            [Path(current_paths["index"]), Path(current_paths["meta"])],
            output_dir=output_dir,
            manifest_r2_prefix=manifest_r2_prefix,
        ),
    }


def build_text_vector_summary(
    *,
    started_at: str,
    completed_at: str,
    current_paths: dict[str, Path | str],
    trial_root: Path,
    trial_summary: dict[str, Any],
    targets: list[ScopeTarget],
    merge_result: dict[str, Any],
) -> dict[str, Any]:
    return {
        "started_at": started_at,
        "completed_at": completed_at,
        "target_year": TARGET_YEAR,
        "rag_category": "artists_text",
        "run_mode": "bounded_closeout_from_trial",
        "closeout_source_trial_root": str(trial_root),
        "trial_output_paths": dict(trial_summary.get("output_paths") or {}),
        "output_paths": {
            "index": str(current_paths["index"]),
            "meta": str(current_paths["meta"]),
            "failed": str(current_paths["failed"]),
            "summary": str(current_paths["summary"]),
            "manifest": str(current_paths["manifest"]),
        },
        "repair_scope": [target.to_dict() for target in targets],
        "repair_scope_total": len(targets),
        "embedding_model": str(trial_summary.get("embedding_model") or ""),
        "embedding_task_type": str(trial_summary.get("embedding_task_type") or ""),
        "embedding_dim": int(trial_summary.get("embedding_dim") or 0),
        "embed_input_max_chars": int(trial_summary.get("embed_input_max_chars") or 0),
        "artifact_totals": {
            "existing_meta_removed": int(merge_result["current_target_rows_total"]),
            "existing_failed_removed": int(merge_result["removed_failed_total"]),
            "retained_meta_total": int(merge_result["retained_non_target_rows_total"]),
            "retained_failed_total": int(merge_result["retained_failed_total"]),
            "repaired_meta_total": int(merge_result["trial_target_rows_total"]),
            "repaired_failed_total": int(merge_result["trial_failed_total"]),
            "final_meta_total": len(merge_result["final_rows"]),
            "final_failed_total": len(merge_result["final_failed_rows"]),
            "final_index_rows_total": int(merge_result["final_index"].shape[0]),
        },
        "counters": {
            "existing_meta_rows_retained": int(merge_result["retained_non_target_rows_total"]),
            "existing_failed_rows_retained": int(merge_result["retained_failed_total"]),
            "closeout_removed_target_rows": int(merge_result["current_target_rows_total"]),
            "closeout_added_trial_rows": int(merge_result["trial_target_rows_total"]),
        },
        "closeout_trial_artifact_totals": dict(trial_summary.get("artifact_totals") or {}),
        "failed_total": len(merge_result["final_failed_rows"]),
        "promoted_to_current": True,
        "promote_verdict": "closeout_merge_applied",
    }


def build_image_vector_manifest(
    *,
    completed_at: str,
    current_paths: dict[str, Path | str],
    trial_summary: dict[str, Any],
    targets: list[ScopeTarget],
) -> dict[str, Any]:
    output_dir = Path(current_paths["output_dir"])
    manifest_r2_prefix = str(current_paths["manifest_r2_prefix"] or "")
    return {
        "target_year": TARGET_YEAR,
        "generated_at": completed_at,
        "run_mode": "bounded_closeout_from_trial",
        "closeout_source_trial_root": str(trial_summary.get("io_root") or ""),
        "repair_scope": [target.to_dict() for target in targets],
        "files": build_manifest_files(
            [
                Path(current_paths["embeddings"]),
                Path(current_paths["index"]),
                Path(current_paths["id_map"]),
                Path(current_paths["failed"]),
            ],
            output_dir=output_dir,
            manifest_r2_prefix=manifest_r2_prefix,
        ),
    }


def build_image_vector_summary(
    *,
    started_at: str,
    completed_at: str,
    current_paths: dict[str, Path | str],
    trial_root: Path,
    trial_summary: dict[str, Any],
    targets: list[ScopeTarget],
    merge_result: dict[str, Any],
) -> dict[str, Any]:
    return {
        "started_at": started_at,
        "completed_at": completed_at,
        "target_year": TARGET_YEAR,
        "run_mode": "bounded_closeout_from_trial",
        "io_root": "",
        "base_contract": "current_existing_plus_trial_target_merge",
        "used_empty_base": False,
        "closeout_source_trial_root": str(trial_root),
        "trial_output_paths": dict(trial_summary.get("output_paths") or {}),
        "output_paths": {
            "embeddings": str(current_paths["embeddings"]),
            "id_map": str(current_paths["id_map"]),
            "search_index": str(current_paths["index"]),
            "failed": str(current_paths["failed"]),
            "summary": str(current_paths["summary"]),
            "manifest": str(current_paths["manifest"]),
        },
        "repair_scope": [target.to_dict() for target in targets],
        "existing_rows_total": int(merge_result["retained_non_target_rows_total"] + merge_result["current_target_rows_total"]),
        "removed_rows_total": int(merge_result["current_target_rows_total"]),
        "retained_rows_total": int(merge_result["retained_non_target_rows_total"]),
        "repaired_rows_total": int(merge_result["trial_target_rows_total"]),
        "final_rows_total": len(merge_result["final_rows"]),
        "trial_target_counters": dict(trial_summary.get("target_counters") or {}),
        "failed_total": len(merge_result["final_failed_rows"]),
        "promoted_to_current": True,
        "promote_verdict": "closeout_merge_applied",
    }


def build_enrichment_summary(
    *,
    started_at: str,
    completed_at: str,
    trial_root: Path,
    current_output_path: Path,
    current_summary_path: Path,
    current_summary_before: dict[str, Any],
    trial_source: dict[str, Any],
    targets: list[ScopeTarget],
    current_rows_before: list[dict[str, Any]],
    trial_rows_added: list[dict[str, Any]],
    final_rows: list[dict[str, Any]],
    current_scoped_source_map: dict[tuple[str, str], tuple[str, str]],
    current_fallback_source_map: dict[str, tuple[str, str]],
) -> dict[str, Any]:
    summary = dict(current_summary_before)
    summary.update(
        {
            "started_at": started_at,
            "completed_at": completed_at,
            "category": "artists",
            "target_year": TARGET_YEAR,
            "execution_mode": "closeout_merge_from_trial",
            "delta_mode": "no_rerun_trial_to_current_bounded_merge",
            "closeout_source_trial_root": str(trial_root),
            "closeout_trial_apply_output_path": str(trial_source["output_path"]),
            "closeout_trial_apply_summary_path": str(trial_source["summary_path"]),
            "closeout_trial_target_rows_total": int(trial_source["summary"].get("total_targeted") or 0),
            "closeout_trial_applied_rows_total": len(trial_rows_added),
            "closeout_removed_current_target_rows": sum(
                1
                for row in current_rows_before
                if resolve_enrichment_scope_key(
                    row,
                    scoped_source_map=current_scoped_source_map,
                    fallback_source_map=current_fallback_source_map,
                ) in {target.scope_key for target in targets}
            ),
            "current_output_path": str(current_output_path),
            "current_summary_path": str(current_summary_path),
            "total_applied": sum(1 for row in final_rows if str(row.get("status") or "").strip() == "APPLIED"),
            "promoted_to_current": True,
            "promote_verdict": "closeout_merge_applied",
            "closeout_scope": [target.to_dict() for target in targets],
        }
    )
    return summary


def write_text_vector_artifacts(
    *,
    current_paths: dict[str, Path | str],
    final_rows: list[dict[str, Any]],
    final_index: np.ndarray,
    final_failed_rows: list[dict[str, Any]],
    summary: dict[str, Any],
    manifest: dict[str, Any],
) -> None:
    write_npy_atomic(Path(current_paths["index"]), final_index)
    write_jsonl_atomic(Path(current_paths["meta"]), final_rows)
    write_jsonl_atomic(Path(current_paths["failed"]), final_failed_rows)
    write_json_atomic(Path(current_paths["summary"]), summary)
    write_json_atomic(Path(current_paths["manifest"]), manifest)


def write_image_vector_artifacts(
    *,
    current_paths: dict[str, Path | str],
    final_rows: list[dict[str, Any]],
    final_embeddings: np.ndarray,
    final_search_index: np.ndarray,
    final_failed_rows: list[dict[str, Any]],
    summary: dict[str, Any],
    manifest: dict[str, Any],
) -> None:
    write_npy_atomic(Path(current_paths["embeddings"]), final_embeddings)
    write_npy_atomic(Path(current_paths["index"]), final_search_index)
    write_jsonl_atomic(Path(current_paths["id_map"]), final_rows)
    write_jsonl_atomic(Path(current_paths["failed"]), final_failed_rows)
    write_json_atomic(Path(current_paths["summary"]), summary)
    write_json_atomic(Path(current_paths["manifest"]), manifest)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    require_trial_closeout_approval(args)
    started_at = utc_now_iso()
    trial_root = resolve_path(args.trial_root)
    targets_path = resolve_path(args.targets_file)
    xlsx_path = resolve_path(args.xlsx_path)
    targets = load_targets_ordered(targets_path)
    target_scope_keys = {target.scope_key for target in targets}
    run_id = str(args.run_id or "").strip() or f"{DEFAULT_RUN_ID_PREFIX}_{utc_now_compact()}"

    trial_raw_paths = get_current_raw_paths("artists", TARGET_YEAR, root=trial_root)
    current_raw_paths = get_current_raw_paths("artists", TARGET_YEAR)
    trial_image_meta_paths = get_current_artist_image_meta_paths(root=trial_root)
    current_image_meta_paths = get_current_artist_image_meta_paths()

    raw_before_counts: dict[str, dict[str, int]] = {}
    raw_after_counts: dict[str, dict[str, int]] = {}
    raw_write_plan: dict[str, list[dict[str, Any]]] = {}
    raw_merge_report: dict[str, Any] = {}
    merged_artist_raw_rows: dict[str, list[dict[str, Any]]] = {}
    for fair_slug in SHEET_BY_FAIR:
        current_rows = read_jsonl(resolve_path(current_raw_paths[fair_slug]))
        trial_rows = read_jsonl(resolve_path(trial_raw_paths[fair_slug]))
        merged = merge_jsonl_rows_by_scope(
            current_rows=current_rows,
            trial_rows=trial_rows,
            target_scope_keys=target_scope_keys,
            label=f"raw_{fair_slug}",
        )
        merged_artist_raw_rows[fair_slug] = merged["final_rows"]
        raw_write_plan[fair_slug] = merged["final_rows"]
        raw_before_counts[fair_slug] = target_scope_counter(current_rows, target_scope_keys)
        raw_after_counts[fair_slug] = target_scope_counter(merged["final_rows"], target_scope_keys)
        raw_merge_report[fair_slug] = {
            "current_target_rows_total": merged["current_target_rows_total"],
            "trial_target_rows_total": merged["trial_target_rows_total"],
            "retained_non_target_rows_total": merged["retained_non_target_rows_total"],
            "final_rows_total": merged["final_rows_total"],
        }

    image_before_counts: dict[str, dict[str, int]] = {}
    image_after_counts: dict[str, dict[str, int]] = {}
    image_merge_report: dict[str, Any] = {}
    merged_artist_image_rows: dict[str, list[dict[str, Any]]] = {}
    for fair_slug in SHEET_BY_FAIR:
        current_rows = read_jsonl(resolve_path(current_image_meta_paths[fair_slug]))
        trial_rows = read_jsonl(resolve_path(trial_image_meta_paths[fair_slug]))
        merged = merge_jsonl_rows_by_scope(
            current_rows=current_rows,
            trial_rows=trial_rows,
            target_scope_keys=target_scope_keys,
            label=f"image_metadata_{fair_slug}",
        )
        merged_artist_image_rows[fair_slug] = merged["final_rows"]
        image_before_counts[fair_slug] = target_scope_counter(current_rows, target_scope_keys)
        image_after_counts[fair_slug] = target_scope_counter(merged["final_rows"], target_scope_keys)
        image_merge_report[fair_slug] = {
            "current_target_rows_total": merged["current_target_rows_total"],
            "trial_target_rows_total": merged["trial_target_rows_total"],
            "retained_non_target_rows_total": merged["retained_non_target_rows_total"],
            "final_rows_total": merged["final_rows_total"],
        }

    trial_enrichment_source = extract_trial_enrichment_source(trial_root)
    current_enrichment_output_path = resolve_path(get_enrichment_current_output_path("artists", TARGET_YEAR))
    current_enrichment_summary_path = resolve_path(get_enrichment_current_summary_path("artists", TARGET_YEAR))
    current_enrichment_rows = read_jsonl(current_enrichment_output_path)
    current_enrichment_summary_before = read_json(current_enrichment_summary_path) if current_enrichment_summary_path.exists() else {}
    current_scoped_source_map, current_fallback_source_map = build_source_scope_maps(
        {fair_slug: read_jsonl(resolve_path(current_raw_paths[fair_slug])) for fair_slug in SHEET_BY_FAIR}
    )
    trial_scoped_source_map, trial_fallback_source_map = build_source_scope_maps(
        {fair_slug: read_jsonl(resolve_path(trial_raw_paths[fair_slug])) for fair_slug in SHEET_BY_FAIR}
    )
    retained_current_enrichment_rows = [
        dict(row)
        for row in current_enrichment_rows
        if resolve_enrichment_scope_key(
            row,
            scoped_source_map=current_scoped_source_map,
            fallback_source_map=current_fallback_source_map,
        ) not in target_scope_keys
    ]
    trial_enrichment_applied_rows = [
        dict(row)
        for row in read_jsonl(trial_enrichment_source["output_path"])
        if resolve_enrichment_scope_key(
            row,
            scoped_source_map=trial_scoped_source_map,
            fallback_source_map=trial_fallback_source_map,
        ) in target_scope_keys
        and str(row.get("status") or "").strip() == "APPLIED"
    ]
    merged_enrichment_rows = retained_current_enrichment_rows + trial_enrichment_applied_rows
    if merged_enrichment_rows[: len(retained_current_enrichment_rows)] != retained_current_enrichment_rows:
        raise RuntimeError("artists_enrichment_non_target_rows_changed")
    enrichment_summary_after = build_enrichment_summary(
        started_at=started_at,
        completed_at=utc_now_iso(),
        trial_root=trial_root,
        current_output_path=current_enrichment_output_path,
        current_summary_path=current_enrichment_summary_path,
        current_summary_before=current_enrichment_summary_before,
        trial_source=trial_enrichment_source,
        targets=targets,
        current_rows_before=current_enrichment_rows,
        trial_rows_added=trial_enrichment_applied_rows,
        final_rows=merged_enrichment_rows,
        current_scoped_source_map=current_scoped_source_map,
        current_fallback_source_map=current_fallback_source_map,
    )

    current_text_paths = get_current_artist_text_vector_runtime_paths(root=None, target_year=TARGET_YEAR)
    trial_text_paths = get_current_artist_text_vector_runtime_paths(root=trial_root, target_year=TARGET_YEAR)
    current_text_rows = read_jsonl(Path(current_text_paths["meta"]))
    current_text_index = np.load(Path(current_text_paths["index"])).astype(np.float32)
    current_text_failed_rows = read_jsonl(Path(current_text_paths["failed"]))
    trial_text_rows = read_jsonl(Path(trial_text_paths["meta"]))
    trial_text_index = np.load(Path(trial_text_paths["index"])).astype(np.float32)
    trial_text_failed_rows = read_jsonl(Path(trial_text_paths["failed"]))
    trial_text_summary = read_json(Path(trial_text_paths["summary"]))
    text_merge_result = merge_text_vector_state(
        current_rows=current_text_rows,
        current_index=current_text_index,
        current_failed_rows=current_text_failed_rows,
        trial_rows=trial_text_rows,
        trial_index=trial_text_index,
        trial_failed_rows=trial_text_failed_rows,
        target_scope_keys=target_scope_keys,
    )
    text_summary_after = build_text_vector_summary(
        started_at=started_at,
        completed_at=utc_now_iso(),
        current_paths=current_text_paths,
        trial_root=trial_root,
        trial_summary=trial_text_summary,
        targets=targets,
        merge_result=text_merge_result,
    )
    text_manifest_after = build_text_vector_manifest(
        completed_at=text_summary_after["completed_at"],
        current_paths=current_text_paths,
        trial_summary=trial_text_summary,
        targets=targets,
    )

    current_image_vector_paths = get_current_artist_works_vector_runtime_paths(root=None, target_year=TARGET_YEAR)
    trial_image_vector_paths = get_current_artist_works_vector_runtime_paths(root=trial_root, target_year=TARGET_YEAR)
    current_image_vector_rows = read_jsonl(Path(current_image_vector_paths["id_map"]))
    current_image_embeddings = np.load(Path(current_image_vector_paths["embeddings"])).astype(np.float32)
    current_image_search_index = np.load(Path(current_image_vector_paths["index"])).astype(np.float32)
    current_image_failed_rows = read_jsonl(Path(current_image_vector_paths["failed"]))
    trial_image_vector_rows = read_jsonl(Path(trial_image_vector_paths["id_map"]))
    trial_image_embeddings = np.load(Path(trial_image_vector_paths["embeddings"])).astype(np.float32)
    trial_image_search_index = np.load(Path(trial_image_vector_paths["index"])).astype(np.float32)
    trial_image_failed_rows = read_jsonl(Path(trial_image_vector_paths["failed"]))
    trial_image_summary = read_json(Path(trial_image_vector_paths["summary"]))
    image_vector_merge_result = merge_image_vector_state(
        current_rows=current_image_vector_rows,
        current_embeddings=current_image_embeddings,
        current_search_index=current_image_search_index,
        current_failed_rows=current_image_failed_rows,
        trial_rows=trial_image_vector_rows,
        trial_embeddings=trial_image_embeddings,
        trial_search_index=trial_image_search_index,
        trial_failed_rows=trial_image_failed_rows,
        target_scope_keys=target_scope_keys,
    )
    image_vector_summary_after = build_image_vector_summary(
        started_at=started_at,
        completed_at=utc_now_iso(),
        current_paths=current_image_vector_paths,
        trial_root=trial_root,
        trial_summary=trial_image_summary,
        targets=targets,
        merge_result=image_vector_merge_result,
    )
    image_vector_manifest_after = build_image_vector_manifest(
        completed_at=image_vector_summary_after["completed_at"],
        current_paths=current_image_vector_paths,
        trial_summary=trial_image_summary,
        targets=targets,
    )

    breakdown_stats_after = build_stats_from_artist_rows(
        artist_raw_by_fair=merged_artist_raw_rows,
        artist_image_by_fair=merged_artist_image_rows,
        target_year=TARGET_YEAR,
    )

    current_write_report = {
        "started_at": started_at,
        "completed_at": utc_now_iso(),
        "apply": bool(args.apply),
        "run_id": run_id,
        "trial_root": str(trial_root),
        "targets_file": str(targets_path),
        "targets": [target.to_dict() for target in targets],
        "raw": {
            "before_counts": raw_before_counts,
            "after_counts": raw_after_counts,
            "merge": raw_merge_report,
        },
        "image_metadata": {
            "before_counts": image_before_counts,
            "after_counts": image_after_counts,
            "merge": image_merge_report,
        },
        "enrichment": {
            "current_rows_before": len(current_enrichment_rows),
            "current_rows_after": len(merged_enrichment_rows),
            "trial_applied_rows_added": len(trial_enrichment_applied_rows),
            "trial_source_output_path": str(trial_enrichment_source["output_path"]),
            "trial_source_summary_path": str(trial_enrichment_source["summary_path"]),
        },
        "text_vector": {
            "current_rows_before": len(current_text_rows),
            "current_target_rows_before": text_merge_result["current_target_rows_total"],
            "trial_target_rows": text_merge_result["trial_target_rows_total"],
            "current_rows_after": len(text_merge_result["final_rows"]),
            "current_index_shape_after": list(text_merge_result["final_index"].shape),
        },
        "image_vector": {
            "current_rows_before": len(current_image_vector_rows),
            "current_target_rows_before": image_vector_merge_result["current_target_rows_total"],
            "trial_target_rows": image_vector_merge_result["trial_target_rows_total"],
            "current_rows_after": len(image_vector_merge_result["final_rows"]),
            "current_embeddings_shape_after": list(image_vector_merge_result["final_embeddings"].shape),
            "current_search_index_shape_after": list(image_vector_merge_result["final_search_index"].shape),
        },
    }

    def execute_current_write(apply: bool) -> dict[str, Any]:
        if apply:
            for fair_slug, rows in raw_write_plan.items():
                write_jsonl_atomic(resolve_path(current_raw_paths[fair_slug]), rows)
            for fair_slug, rows in merged_artist_image_rows.items():
                write_jsonl_atomic(resolve_path(current_image_meta_paths[fair_slug]), rows)
            write_jsonl_atomic(current_enrichment_output_path, merged_enrichment_rows)
            write_json_atomic(current_enrichment_summary_path, enrichment_summary_after)
            write_text_vector_artifacts(
                current_paths=current_text_paths,
                final_rows=text_merge_result["final_rows"],
                final_index=text_merge_result["final_index"],
                final_failed_rows=text_merge_result["final_failed_rows"],
                summary=text_summary_after,
                manifest=text_manifest_after,
            )
            write_image_vector_artifacts(
                current_paths=current_image_vector_paths,
                final_rows=image_vector_merge_result["final_rows"],
                final_embeddings=image_vector_merge_result["final_embeddings"],
                final_search_index=image_vector_merge_result["final_search_index"],
                final_failed_rows=image_vector_merge_result["final_failed_rows"],
                summary=image_vector_summary_after,
                manifest=image_vector_manifest_after,
            )
        return current_write_report

    report = execute_closeout_with_breakdown_contract(
        contract_name="artists_trial_closeout_with_breakdown",
        apply=bool(args.apply),
        run_id=run_id,
        xlsx_path=xlsx_path,
        target_year=TARGET_YEAR,
        targets=targets,
        current_write_callback=execute_current_write,
        breakdown_stats_override=breakdown_stats_after,
        r2_artifact_bundle=resolve_current_formal_artifact_bundle(
            bundle_name=f"{targets_path.stem}_artists_current_formal_artifacts",
            categories=(
                BLOCK_ARTIFACT_CATEGORY_ARTIST,
                BLOCK_ARTIFACT_CATEGORY_ARTIST_WORKS_IMAGES,
            ),
            target_year=TARGET_YEAR,
        ),
    )

    print(json.dumps(report, ensure_ascii=True, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
