#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import tempfile
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from phase2_art_pulse_config import (
    TARGET_YEAR,
    get_current_artist_image_meta_paths,
    get_current_artist_works_vector_runtime_paths,
    normalize_image_local_path_text,
)
from phase2_artwork_search_readonly import (
    _build_fallback_image_id,
    _encode_corpus_images,
    _load_id_map,
    _normalize_matrix,
    _pick_list_value,
    _record_quality,
    _save_id_map,
)
from phase2_common_readonly import (
    FAIR_SLUG_TO_LABEL,
    safe_load_jsonl,
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def resolve_io_root(path_text: str | Path) -> Path | None:
    raw = str(path_text or "").strip()
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    return path


IO_ROOT: Path | None = None
IMAGE_META_PATHS: dict[str, Path] = {}
VECTOR_RUNTIME_PATHS: dict[str, Path | str] = {}
ARTIFACT_PATHS: dict[str, Path] = {}
OUTPUT_DIR = Path()
FAILED_PATH = Path()
SUMMARY_PATH = Path()
MANIFEST_PATH = Path()
MANIFEST_R2_PREFIX = ""


def configure_runtime_paths(io_root: Path | None) -> dict[str, Path | str]:
    global IO_ROOT
    global IMAGE_META_PATHS
    global VECTOR_RUNTIME_PATHS
    global ARTIFACT_PATHS
    global OUTPUT_DIR
    global FAILED_PATH
    global SUMMARY_PATH
    global MANIFEST_PATH
    global MANIFEST_R2_PREFIX

    IO_ROOT = io_root
    IMAGE_META_PATHS = get_current_artist_image_meta_paths(root=io_root)
    VECTOR_RUNTIME_PATHS = get_current_artist_works_vector_runtime_paths(
        root=io_root,
        target_year=TARGET_YEAR,
    )
    ARTIFACT_PATHS = {
        "embeddings": Path(VECTOR_RUNTIME_PATHS["embeddings"]),
        "index": Path(VECTOR_RUNTIME_PATHS["index"]),
        "id_map": Path(VECTOR_RUNTIME_PATHS["id_map"]),
    }
    OUTPUT_DIR = Path(VECTOR_RUNTIME_PATHS["output_dir"])
    FAILED_PATH = Path(VECTOR_RUNTIME_PATHS["failed"])
    SUMMARY_PATH = Path(VECTOR_RUNTIME_PATHS["summary"])
    MANIFEST_PATH = Path(VECTOR_RUNTIME_PATHS["manifest"])
    MANIFEST_R2_PREFIX = str(VECTOR_RUNTIME_PATHS["manifest_r2_prefix"] or "")
    return VECTOR_RUNTIME_PATHS


configure_runtime_paths(None)


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
class ExistingArtifactState:
    records: list[dict[str, Any]]
    embeddings: np.ndarray
    index_matrix: np.ndarray
    used_empty_base: bool = False


@dataclass
class PartitionedArtifactState:
    retained_records: list[dict[str, Any]]
    retained_embeddings: list[np.ndarray]
    removed_total: int


@dataclass
class TargetRecordBuildResult:
    records: list[dict[str, Any]]
    warnings: list[str]
    counters: Counter[str]


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
            targets.append(RepairTarget(fair_slug=fair_slug, gallery_name_en=gallery_name_en))
    return targets


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bounded repair for current artist works image vectors."
    )
    parser.add_argument(
        "--approval-token",
        default="",
        help="required for repair execution; perform offline-only diagnosis before any approved repair",
    )
    parser.add_argument(
        "--io-root",
        default="",
        help="optional trial I/O root; when set, metadata input and vector artifacts resolve under this root",
    )
    parser.add_argument(
        "--repair-target",
        action="append",
        default=[],
        help="Repair target in the format fair_slug::gallery_name_en. Repeatable.",
    )
    parser.add_argument(
        "--repair-targets-file",
        type=Path,
        help="CSV file with columns fair_slug,gallery_name_en for bounded repair mode.",
    )
    return parser.parse_args(argv)


def require_repair_approval(args: argparse.Namespace) -> None:
    if str(args.approval_token or "").strip():
        return
    raise RuntimeError(
        "approval_required_for_artist_works_image_repair:"
        "pass --approval-token <user-approved-note>; use offline-only diagnosis before approved repair"
    )


def resolve_repair_targets(
    repair_target_specs: list[str],
    repair_targets_file: Path | None,
) -> list[RepairTarget]:
    targets: list[RepairTarget] = []
    for raw_value in repair_target_specs:
        targets.append(parse_repair_target_spec(raw_value))
    if repair_targets_file is not None:
        targets.extend(read_repair_targets_file(repair_targets_file))

    available_fairs = set(IMAGE_META_PATHS.keys())
    seen_scope_keys: set[tuple[str, str]] = set()
    deduped_targets: list[RepairTarget] = []
    for target in targets:
        if target.fair_slug not in available_fairs:
            raise ValueError(f"Unsupported fair_slug in repair scope: {target.fair_slug}")
        if target.scope_key in seen_scope_keys:
            continue
        seen_scope_keys.add(target.scope_key)
        deduped_targets.append(target)
    return deduped_targets


def build_target_records_from_current_metadata(
    repair_targets: list[RepairTarget],
) -> TargetRecordBuildResult:
    target_scope_keys = {target.scope_key for target in repair_targets}
    fair_filter = {target.fair_slug for target in repair_targets}
    warnings: list[str] = []
    counters: Counter[str] = Counter()
    best_by_image_id: dict[str, dict[str, Any]] = {}

    for fair_slug, path in IMAGE_META_PATHS.items():
        if fair_slug not in fair_filter:
            continue
        image_rows, image_warnings = safe_load_jsonl(path, hydrate_r2=IO_ROOT is None)
        warnings.extend(image_warnings)
        fair_label = FAIR_SLUG_TO_LABEL.get(fair_slug, fair_slug)
        for row in image_rows:
            counters["metadata_rows_scanned_total"] += 1
            gallery_name_en = str(row.get("gallery_name_en") or "").strip()
            if build_repair_scope_key(fair_slug, gallery_name_en) not in target_scope_keys:
                continue

            counters["metadata_rows_target_total"] += 1
            local_paths = row.get("works_image_local_paths")
            if not isinstance(local_paths, list) or not local_paths:
                counters["skipped_zero_image_rows"] += 1
                continue

            source_url = str(row.get("source_url") or "").strip()
            payload_hashes = row.get("works_image_payload_hashes")
            url_hashes = row.get("works_image_url_hashes")
            r2_keys = row.get("works_image_r2_keys")
            image_urls = row.get("works_image_urls")
            captions = row.get("works_image_captions")
            years = row.get("works_image_years")

            for slot_index, local_path_raw in enumerate(local_paths):
                counters["metadata_images_target_total"] += 1
                local_path = normalize_image_local_path_text(local_path_raw or "")
                local_file = Path(local_path) if local_path else None
                if local_file is None or not local_file.exists():
                    counters["missing_local_path_total"] += 1
                    continue

                payload_hash = _pick_list_value(payload_hashes, slot_index)
                url_hash = _pick_list_value(url_hashes, slot_index)
                image_id = payload_hash or _build_fallback_image_id(url_hash, source_url, slot_index)
                record = {
                    "image_id": image_id,
                    "fair_slug": fair_slug,
                    "fair_label": fair_label,
                    "artist_identity_key": str(row.get("artist_identity_key") or "").strip(),
                    "artist_name_en": str(row.get("artist_name_en") or "").strip(),
                    "artist_name_key": str(row.get("artist_name_key") or "").strip(),
                    "gallery_name_en": gallery_name_en,
                    "source_url": source_url,
                    "local_path": local_path,
                    "r2_key": _pick_list_value(r2_keys, slot_index),
                    "image_url": _pick_list_value(image_urls, slot_index),
                    "caption": _pick_list_value(captions, slot_index),
                    "year": str(_pick_list_value(years, slot_index) or "").strip(),
                    "slot_index": int(slot_index),
                    "payload_hash": payload_hash,
                    "url_hash": url_hash,
                }

                previous = best_by_image_id.get(image_id)
                if previous is None:
                    best_by_image_id[image_id] = record
                    counters["target_records_total"] += 1
                elif _record_quality(record) > _record_quality(previous):
                    best_by_image_id[image_id] = record
                    counters["target_records_deduped_total"] += 1
                else:
                    counters["target_records_deduped_total"] += 1

    records = sorted(
        best_by_image_id.values(),
        key=lambda row: (
            str(row.get("fair_slug") or ""),
            str(row.get("gallery_name_en") or ""),
            str(row.get("artist_name_en") or ""),
            str(row.get("image_id") or ""),
        ),
    )
    return TargetRecordBuildResult(records=records, warnings=sorted(set(warnings)), counters=counters)


def load_existing_artifact_state(*, allow_missing_base: bool = False) -> ExistingArtifactState:
    existing = {name: path.exists() for name, path in ARTIFACT_PATHS.items()}
    if allow_missing_base and not any(existing.values()):
        return ExistingArtifactState(
            records=[],
            embeddings=np.zeros((0, 0), dtype=np.float32),
            index_matrix=np.zeros((0, 0), dtype=np.float32),
            used_empty_base=True,
        )

    missing = [name for name, exists in existing.items() if not exists]
    if missing:
        raise FileNotFoundError(
            f"Missing artist works image artifact(s) for repair mode: {missing}"
        )

    embeddings = np.load(ARTIFACT_PATHS["embeddings"]).astype(np.float32)
    index_matrix = np.load(ARTIFACT_PATHS["index"]).astype(np.float32)
    records, warnings = _load_id_map(ARTIFACT_PATHS["id_map"])
    if warnings:
        raise RuntimeError(f"Current artist works id_map warnings: {warnings}")
    if embeddings.ndim != 2 or index_matrix.ndim != 2:
        raise ValueError(
            f"Unexpected artifact shapes: embeddings={embeddings.shape} index={index_matrix.shape}"
        )
    if embeddings.shape != index_matrix.shape:
        raise ValueError(
            f"Embeddings/index shape mismatch: embeddings={embeddings.shape} index={index_matrix.shape}"
        )
    if len(records) != int(embeddings.shape[0]):
        raise ValueError(
            f"id_map/artifact row mismatch: id_map={len(records)} embeddings={int(embeddings.shape[0])}"
        )
    return ExistingArtifactState(
        records=records,
        embeddings=embeddings,
        index_matrix=index_matrix,
        used_empty_base=False,
    )


def partition_existing_artifacts_for_repair(
    state: ExistingArtifactState,
    repair_scope_keys: set[tuple[str, str]],
) -> PartitionedArtifactState:
    retained_records: list[dict[str, Any]] = []
    retained_embeddings: list[np.ndarray] = []
    removed_total = 0

    for position, record in enumerate(state.records):
        scope_key = build_repair_scope_key(
            str(record.get("fair_slug") or ""),
            str(record.get("gallery_name_en") or ""),
        )
        if scope_key in repair_scope_keys:
            removed_total += 1
            continue
        retained_records.append(dict(record))
        retained_embeddings.append(state.embeddings[position].astype(np.float32, copy=True))

    return PartitionedArtifactState(
        retained_records=retained_records,
        retained_embeddings=retained_embeddings,
        removed_total=removed_total,
    )


def merge_records_and_embeddings(
    retained_records: list[dict[str, Any]],
    retained_embeddings: list[np.ndarray],
    repaired_records: list[dict[str, Any]],
    repaired_embeddings: np.ndarray,
) -> tuple[list[dict[str, Any]], np.ndarray]:
    final_records: list[dict[str, Any]] = []
    final_embeddings: list[np.ndarray] = []
    seen_image_ids: set[str] = set()

    for record, embedding in zip(retained_records, retained_embeddings):
        image_id = str(record.get("image_id") or "").strip()
        if not image_id:
            raise ValueError("Retained record is missing image_id")
        if image_id in seen_image_ids:
            raise ValueError(f"Duplicate retained image_id detected: {image_id}")
        seen_image_ids.add(image_id)
        final_records.append(dict(record))
        final_embeddings.append(embedding.astype(np.float32, copy=True))

    for position, record in enumerate(repaired_records):
        image_id = str(record.get("image_id") or "").strip()
        if not image_id:
            raise ValueError("Repaired record is missing image_id")
        if image_id in seen_image_ids:
            raise ValueError(f"Repaired image_id collides with retained corpus: {image_id}")
        seen_image_ids.add(image_id)
        final_records.append(dict(record))
        final_embeddings.append(repaired_embeddings[position].astype(np.float32, copy=True))

    final_embedding_matrix = (
        np.vstack(final_embeddings).astype(np.float32)
        if final_embeddings
        else np.zeros((0, 0), dtype=np.float32)
    )
    return final_records, final_embedding_matrix


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


def build_manifest_files(paths: list[Path]) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    for path in paths:
        if not path.exists():
            continue
        try:
            rel = path.relative_to(OUTPUT_DIR).as_posix()
        except ValueError:
            rel = path.name
        r2_key = f"{MANIFEST_R2_PREFIX}/{rel}" if MANIFEST_R2_PREFIX else rel
        files.append(
            {
                "path": r2_key,
                "local_path": path.as_posix(),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )
    return files


def build_manifest(
    *,
    completed_at: str,
    run_mode: str,
    repair_targets: list[RepairTarget],
    used_empty_base: bool,
) -> dict[str, Any]:
    return {
        "target_year": TARGET_YEAR,
        "generated_at": completed_at,
        "run_mode": run_mode,
        "io_root": str(IO_ROOT) if IO_ROOT is not None else "",
        "base_contract": "trial_existing_or_empty" if IO_ROOT is not None else "current_existing_required",
        "used_empty_base": used_empty_base,
        "repair_scope": [target.to_dict() for target in repair_targets],
        "files": build_manifest_files(
            [
                ARTIFACT_PATHS["embeddings"],
                ARTIFACT_PATHS["index"],
                ARTIFACT_PATHS["id_map"],
                FAILED_PATH,
            ]
        ),
    }


def build_summary(
    *,
    started_at: str,
    completed_at: str,
    run_mode: str,
    repair_targets: list[RepairTarget],
    target_result: TargetRecordBuildResult,
    existing_state: ExistingArtifactState,
    removed_total: int,
    retained_total: int,
    repaired_total: int,
    final_total: int,
) -> dict[str, Any]:
    return {
        "started_at": started_at,
        "completed_at": completed_at,
        "target_year": TARGET_YEAR,
        "run_mode": run_mode,
        "io_root": str(IO_ROOT) if IO_ROOT is not None else "",
        "base_contract": "trial_existing_or_empty" if IO_ROOT is not None else "current_existing_required",
        "used_empty_base": existing_state.used_empty_base,
        "input_metadata_paths": {fair_slug: str(path) for fair_slug, path in IMAGE_META_PATHS.items()},
        "output_paths": {
            "embeddings": str(ARTIFACT_PATHS["embeddings"]),
            "id_map": str(ARTIFACT_PATHS["id_map"]),
            "search_index": str(ARTIFACT_PATHS["index"]),
            "failed": str(FAILED_PATH),
            "summary": str(SUMMARY_PATH),
            "manifest": str(MANIFEST_PATH),
        },
        "repair_scope": [target.to_dict() for target in repair_targets],
        "target_counters": dict(target_result.counters),
        "existing_rows_total": len(existing_state.records),
        "removed_rows_total": removed_total,
        "retained_rows_total": retained_total,
        "repaired_rows_total": repaired_total,
        "final_rows_total": final_total,
        "warnings": target_result.warnings,
    }


def _write_temp_jsonl(path: Path, rows: list[dict[str, Any]]) -> Path:
    fd, temp_path_text = tempfile.mkstemp(
        prefix=f"{path.stem}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    os.close(fd)
    temp_path = Path(temp_path_text)
    _save_id_map(temp_path, rows)
    return temp_path


def _write_temp_npy(path: Path, matrix: np.ndarray) -> Path:
    fd, temp_path_text = tempfile.mkstemp(
        prefix=f"{path.stem}.",
        suffix=".tmp.npy",
        dir=str(path.parent),
    )
    os.close(fd)
    temp_path = Path(temp_path_text)
    np.save(temp_path, matrix.astype(np.float32))
    return temp_path


def atomic_write_artifacts(
    *,
    embeddings_path: Path,
    index_path: Path,
    id_map_path: Path,
    embeddings: np.ndarray,
    index_matrix: np.ndarray,
    records: list[dict[str, Any]],
) -> None:
    embeddings_path.parent.mkdir(parents=True, exist_ok=True)
    temp_embeddings = _write_temp_npy(embeddings_path, embeddings)
    temp_index = _write_temp_npy(index_path, index_matrix)
    temp_id_map = _write_temp_jsonl(id_map_path, records)
    try:
        os.replace(temp_embeddings, embeddings_path)
        os.replace(temp_index, index_path)
        os.replace(temp_id_map, id_map_path)
    finally:
        for temp_path in (temp_embeddings, temp_index, temp_id_map):
            if temp_path.exists():
                temp_path.unlink()


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    require_repair_approval(args)
    io_root = resolve_io_root(args.io_root)
    configure_runtime_paths(io_root)
    repair_targets = resolve_repair_targets(args.repair_target, args.repair_targets_file)
    if not repair_targets:
        raise ValueError("At least one repair scope is required.")

    started_at = utc_now_iso()
    print(f"[START] artist works image vector repair at {started_at}")

    target_result = build_target_records_from_current_metadata(repair_targets)
    if target_result.counters.get("missing_local_path_total", 0) > 0:
        raise RuntimeError(
            "repair_scope_has_missing_local_image_paths: "
            f"{target_result.counters['missing_local_path_total']}"
        )
    if not target_result.records:
        raise RuntimeError("repair_scope_yielded_no_target_records")

    existing_state = load_existing_artifact_state(allow_missing_base=io_root is not None)
    repair_scope_keys = {target.scope_key for target in repair_targets}
    partitioned = partition_existing_artifacts_for_repair(existing_state, repair_scope_keys)

    repaired_records, repaired_embeddings = _encode_corpus_images(target_result.records)
    expected_repair_rows = len(target_result.records)
    actual_repair_rows = len(repaired_records)
    if actual_repair_rows != expected_repair_rows:
        raise RuntimeError(
            "atomic_guard_failed_target_rows_mismatch: "
            f"expected={expected_repair_rows} actual={actual_repair_rows}"
        )

    repaired_image_ids = {str(record.get("image_id") or "").strip() for record in repaired_records}
    expected_image_ids = {str(record.get("image_id") or "").strip() for record in target_result.records}
    if repaired_image_ids != expected_image_ids:
        raise RuntimeError("atomic_guard_failed_repaired_image_id_set_mismatch")

    final_records, final_embeddings = merge_records_and_embeddings(
        retained_records=partitioned.retained_records,
        retained_embeddings=partitioned.retained_embeddings,
        repaired_records=repaired_records,
        repaired_embeddings=repaired_embeddings,
    )
    final_index = _normalize_matrix(final_embeddings)

    atomic_write_artifacts(
        embeddings_path=ARTIFACT_PATHS["embeddings"],
        index_path=ARTIFACT_PATHS["index"],
        id_map_path=ARTIFACT_PATHS["id_map"],
        embeddings=final_embeddings,
        index_matrix=final_index,
        records=final_records,
    )
    write_jsonl(FAILED_PATH, [])

    completed_at = utc_now_iso()
    manifest = build_manifest(
        completed_at=completed_at,
        run_mode="bounded_repair",
        repair_targets=repair_targets,
        used_empty_base=existing_state.used_empty_base,
    )
    write_json(MANIFEST_PATH, manifest)
    summary = build_summary(
        started_at=started_at,
        completed_at=completed_at,
        run_mode="bounded_repair",
        repair_targets=repair_targets,
        target_result=target_result,
        existing_state=existing_state,
        removed_total=partitioned.removed_total,
        retained_total=len(partitioned.retained_records),
        repaired_total=actual_repair_rows,
        final_total=len(final_records),
    )
    write_json(SUMMARY_PATH, summary)
    print(json.dumps(summary, ensure_ascii=True, indent=2))
    print(f"[DONE] embeddings={ARTIFACT_PATHS['embeddings']}")
    print(f"[DONE] id_map={ARTIFACT_PATHS['id_map']}")
    print(f"[DONE] search_index={ARTIFACT_PATHS['index']}")
    print(f"[DONE] failed={FAILED_PATH}")
    print(f"[DONE] summary={SUMMARY_PATH}")
    print(f"[DONE] manifest={MANIFEST_PATH}")
    sync_scope_hint = "artist_works_images_current" if io_root is None else "artist_works_images_trial"
    print(f"[SYNC] status=manual_sync_only entrypoint=run_r2_sync.py scope_hint={sync_scope_hint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
