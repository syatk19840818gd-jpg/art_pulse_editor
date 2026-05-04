from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import tempfile
import unicodedata
from datetime import datetime, timezone
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

import numpy as np
from PIL import Image

from phase2_art_pulse_config import (
    TARGET_YEAR,
)
from phase2_common_readonly import (
    FAIR_LABEL_TO_SLUG,
    FAIR_SLUG_TO_LABEL,
    hydrate_path_from_r2,
    resolve_current_artist_works_local_path,
    resolve_current_artist_works_artifact_paths,
    resolve_current_artist_works_image_meta_paths,
    safe_load_jsonl,
)

ARTWORK_SEARCH_TOP_K_DEFAULT = 100
ARTWORK_SEARCH_OPENCLIP_MODEL = os.getenv("ARTWORK_SEARCH_OPENCLIP_MODEL", "ViT-B-32").strip() or "ViT-B-32"
ARTWORK_SEARCH_OPENCLIP_PRETRAINED = (
    os.getenv("ARTWORK_SEARCH_OPENCLIP_PRETRAINED", "laion2b_s34b_b79k").strip() or "laion2b_s34b_b79k"
)
ARTWORK_SEARCH_BATCH_SIZE = max(1, int(os.getenv("ARTWORK_SEARCH_BATCH_SIZE", "16") or "16"))
ARTWORK_SEARCH_QUERY_REWRITE_MODEL = (
    os.getenv("ARTWORK_SEARCH_QUERY_REWRITE_MODEL", "gpt-5-mini").strip() or "gpt-5-mini"
)
ARTWORK_SEARCH_QUERY_REWRITE_MAX_OUTPUT_TOKENS = max(
    64,
    int(os.getenv("ARTWORK_SEARCH_QUERY_REWRITE_MAX_OUTPUT_TOKENS", "128") or "128"),
)
JAPANESE_CHAR_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]")
QUERY_SEP_RE = re.compile(r"[\s/|,;:()\[\]{}<>]+")


@dataclass
class ArtworkSearchState:
    records: List[dict]
    embeddings: np.ndarray
    index_matrix: np.ndarray
    warnings: List[str]
    artifact_status: str
    corpus_stats: dict


def _empty_state(*, warnings: List[str] | None = None, artifact_status: str = "empty") -> ArtworkSearchState:
    return ArtworkSearchState(
        records=[],
        embeddings=np.zeros((0, 0), dtype=np.float32),
        index_matrix=np.zeros((0, 0), dtype=np.float32),
        warnings=list(warnings or []),
        artifact_status=artifact_status,
        corpus_stats={
            "rows_total": 0,
            "images_total": 0,
            "deduped_images": 0,
            "skipped_zero_image_rows": 0,
            "skipped_missing_local_path": 0,
            "available_fair_counts": {"frieze_london": 0, "liste": 0},
        },
    )


def _artifact_paths(target_year: int = TARGET_YEAR) -> dict[str, Path]:
    return resolve_current_artist_works_artifact_paths(target_year)


def _record_quality(record: dict) -> int:
    return sum(
        1
        for key in ("caption", "image_url", "r2_key", "artist_name_en", "gallery_name_en", "source_url")
        if str(record.get(key) or "").strip()
    )


def _build_fallback_image_id(url_hash: str, source_url: str, slot_index: int) -> str:
    seed = f"{url_hash}|{source_url}|{int(slot_index)}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _normalize_year(value: object) -> str:
    text = str(value or "").strip()
    if not text or text == "0":
        return ""
    return text


ARTIST_WORKS_CACHE_R2_PREFIX = "data/current/images/cache/artist_works_images/"


def _derive_artist_works_r2_key_from_current_local_path(local_path: object) -> str:
    path_text = str(local_path or "").strip()
    if not path_text:
        return ""
    normalized = path_text.replace("\\", "/")
    marker = ARTIST_WORKS_CACHE_R2_PREFIX
    lowered = normalized.lower()
    idx = lowered.find(marker)
    if idx < 0:
        return ""
    suffix = normalized[idx + len(marker) :].lstrip("/")
    if not suffix:
        return ""
    return f"{marker}{suffix}"


def _stabilize_artwork_image_record(record: dict, *, resolve_local_path: bool = True) -> dict | None:
    row = dict(record)
    fair_slug = str(row.get("fair_slug") or "").strip()
    if resolve_local_path:
        row["local_path"] = resolve_current_artist_works_local_path(
            row.get("local_path"),
            fair_slug=fair_slug,
        )
    else:
        row["local_path"] = str(row.get("local_path") or "").strip()
    row["r2_key"] = str(row.get("r2_key") or "").strip()
    if not row["r2_key"]:
        row["r2_key"] = _derive_artist_works_r2_key_from_current_local_path(row.get("local_path"))
    row["image_url"] = str(row.get("image_url") or "").strip()
    if row["r2_key"] or row["image_url"] or row["local_path"]:
        return row
    return None


def _pick_list_value(values: object, idx: int) -> str:
    if not isinstance(values, list) or idx >= len(values):
        return ""
    return str(values[idx] or "").strip()


def _load_corpus_records_current_first() -> tuple[List[dict], List[str], dict]:
    warnings: List[str] = []
    rows_total = 0
    images_total = 0
    deduped_images = 0
    skipped_zero_image_rows = 0
    skipped_missing_local_path = 0
    fair_counts: Dict[str, int] = {"frieze_london": 0, "liste": 0}
    best_by_image_id: Dict[str, dict] = {}

    for fair_slug, path in resolve_current_artist_works_image_meta_paths().items():
        image_rows, image_warnings = safe_load_jsonl(path)
        warnings.extend(image_warnings)
        fair_label = FAIR_SLUG_TO_LABEL.get(fair_slug, fair_slug)
        for row in image_rows:
            rows_total += 1
            local_paths = row.get("works_image_local_paths")
            if not isinstance(local_paths, list) or not local_paths:
                skipped_zero_image_rows += 1
                continue

            image_added = False
            payload_hashes = row.get("works_image_payload_hashes")
            url_hashes = row.get("works_image_url_hashes")
            r2_keys = row.get("works_image_r2_keys")
            image_urls = row.get("works_image_urls")
            captions = row.get("works_image_captions")
            years = row.get("works_image_years")

            for slot_index, local_path_raw in enumerate(local_paths):
                local_path = resolve_current_artist_works_local_path(local_path_raw, fair_slug=fair_slug)
                local_file = Path(local_path) if local_path else None
                if local_file is None or not local_file.exists():
                    skipped_missing_local_path += 1
                    continue

                source_url = str(row.get("source_url") or "").strip()
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
                    "gallery_name_en": str(row.get("gallery_name_en") or "").strip(),
                    "source_url": source_url,
                    "local_path": local_path,
                    "r2_key": _pick_list_value(r2_keys, slot_index),
                    "image_url": _pick_list_value(image_urls, slot_index),
                    "caption": _pick_list_value(captions, slot_index),
                    "year": _normalize_year(_pick_list_value(years, slot_index)),
                    "slot_index": int(slot_index),
                    "payload_hash": payload_hash,
                    "url_hash": url_hash,
                }
                record = _stabilize_artwork_image_record(record)
                if record is None:
                    skipped_missing_local_path += 1
                    continue
                previous = best_by_image_id.get(image_id)
                if previous is None:
                    best_by_image_id[image_id] = record
                    images_total += 1
                    image_added = True
                elif _record_quality(record) > _record_quality(previous):
                    best_by_image_id[image_id] = record
                    deduped_images += 1
                else:
                    deduped_images += 1
            if image_added:
                fair_counts[fair_slug] = fair_counts.get(fair_slug, 0) + 1

    records = sorted(
        best_by_image_id.values(),
        key=lambda row: (
            str(row.get("fair_slug") or ""),
            str(row.get("gallery_name_en") or ""),
            str(row.get("artist_name_en") or ""),
            str(row.get("image_id") or ""),
        ),
    )
    corpus_stats = {
        "rows_total": rows_total,
        "images_total": len(records),
        "deduped_images": deduped_images,
        "skipped_zero_image_rows": skipped_zero_image_rows,
        "skipped_missing_local_path": skipped_missing_local_path,
        "available_fair_counts": fair_counts,
    }
    return records, warnings, corpus_stats


def _save_id_map(path: Path, records: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in records:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _load_id_map(path: Path) -> tuple[List[dict], List[str]]:
    return safe_load_jsonl(path)


def _parse_csv_bool(value: object) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes"}


def _atomic_save_npy(path: Path, values: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = Path()
    try:
        with tempfile.NamedTemporaryFile(delete=False, dir=str(path.parent), suffix=".tmp.npy") as tmp:
            tmp_path = Path(tmp.name)
        np.save(tmp_path, values)
        os.replace(tmp_path, path)
    finally:
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def _atomic_save_id_map(path: Path, records: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = Path()
    try:
        with tempfile.NamedTemporaryFile(delete=False, dir=str(path.parent), suffix=".tmp.jsonl") as tmp:
            tmp_path = Path(tmp.name)
        _save_id_map(tmp_path, records)
        os.replace(tmp_path, path)
    finally:
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def _load_liste_vectorize_append_allowlist(
    path: Path | None,
) -> tuple[List[dict], List[str]]:
    warnings: List[str] = []
    rows: List[dict] = []
    if path is None:
        warnings.append("artwork_search_liste_allowlist_path_missing")
        return rows, warnings
    if not path.exists():
        warnings.append(f"artwork_search_liste40_allowlist_missing: {path}")
        return rows, warnings
    seen_payload_hashes: set[str] = set()
    seen_image_ids: set[str] = set()
    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for raw in reader:
                if str(raw.get("fair_slug") or "").strip() != "liste":
                    continue
                if not _parse_csv_bool(raw.get("vectorizable_now")):
                    continue
                if not _parse_csv_bool(raw.get("safe_for_bounded_append")):
                    continue
                payload_hash = str(raw.get("payload_hash") or "").strip()
                image_id = str(raw.get("image_id") or "").strip()
                if not payload_hash or not image_id:
                    continue
                if payload_hash in seen_payload_hashes or image_id in seen_image_ids:
                    warnings.append(f"artwork_search_liste40_allowlist_duplicate_skipped: {payload_hash}")
                    continue
                seen_payload_hashes.add(payload_hash)
                seen_image_ids.add(image_id)
                rows.append(
                    {
                        "payload_hash": payload_hash,
                        "image_id": image_id,
                        "fair_slug": "liste",
                        "source_url": str(raw.get("source_url") or "").strip(),
                        "current_local_path": str(raw.get("current_local_path") or "").strip(),
                    }
                )
    except Exception as exc:
        warnings.append(f"artwork_search_liste40_allowlist_read_failed: {type(exc).__name__}")
        return [], warnings
    return rows, warnings


def bounded_vectorize_append_liste_gap_rows(
    *,
    target_year: int = TARGET_YEAR,
    allowlist_csv_path: Path | None = None,
) -> dict:
    started_at_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    logs_dir = Path(__file__).resolve().parent / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = logs_dir / (
        f"artwork_liste40_bounded_append_result_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    )

    paths = _artifact_paths(target_year)
    missing_artifacts = [name for name, path in paths.items() if not hydrate_path_from_r2(path)]
    result = {
        "started_at_utc": started_at_utc,
        "target_year": int(target_year or TARGET_YEAR),
        "allowlist_csv_path": str(allowlist_csv_path),
        "artifact_paths": {name: str(path) for name, path in paths.items()},
        "missing_artifacts": missing_artifacts,
        "status": "started",
        "warnings": [],
    }
    if missing_artifacts:
        result["status"] = "skipped_missing_artifacts"
        result["completed_at_utc"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        result["manifest_path"] = str(manifest_path)
        with manifest_path.open("w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        return result

    existing_embeddings = np.load(paths["embeddings"]).astype(np.float32)
    existing_index = np.load(paths["index"]).astype(np.float32)
    existing_records, id_map_warnings = _load_id_map(paths["id_map"])
    result["warnings"].extend(id_map_warnings)

    if (
        existing_embeddings.ndim != 2
        or existing_index.ndim != 2
        or existing_embeddings.shape != existing_index.shape
        or len(existing_records) != existing_embeddings.shape[0]
    ):
        result["status"] = "failed_invalid_artifact_shape"
        result["shape_before"] = {
            "id_map_rows": len(existing_records),
            "embeddings_shape": list(existing_embeddings.shape),
            "index_shape": list(existing_index.shape),
        }
        result["completed_at_utc"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        result["manifest_path"] = str(manifest_path)
        with manifest_path.open("w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        return result

    resolved_allowlist_path = Path(allowlist_csv_path) if allowlist_csv_path is not None else None
    allowlist_rows, allowlist_warnings = _load_liste_vectorize_append_allowlist(resolved_allowlist_path)
    result["warnings"].extend(allowlist_warnings)
    result["allowlist_rows"] = len(allowlist_rows)

    corpus_records, corpus_warnings, _ = _load_corpus_records_current_first()
    result["warnings"].extend(corpus_warnings)
    corpus_by_payload: dict[str, dict] = {}
    corpus_by_image_id: dict[str, dict] = {}
    for record in corpus_records:
        payload_hash = str(record.get("payload_hash") or "").strip()
        image_id = str(record.get("image_id") or "").strip()
        if payload_hash and payload_hash not in corpus_by_payload:
            corpus_by_payload[payload_hash] = record
        if image_id and image_id not in corpus_by_image_id:
            corpus_by_image_id[image_id] = record

    existing_payload_hashes = {
        str(row.get("payload_hash") or "").strip() for row in existing_records if str(row.get("payload_hash") or "").strip()
    }
    existing_image_ids = {str(row.get("image_id") or "").strip() for row in existing_records if str(row.get("image_id") or "").strip()}

    append_candidates: List[dict] = []
    candidate_keys: List[str] = []
    skipped: List[dict] = []
    for raw in allowlist_rows:
        payload_hash = str(raw.get("payload_hash") or "").strip()
        image_id = str(raw.get("image_id") or "").strip()
        source_url = str(raw.get("source_url") or "").strip()
        if payload_hash in existing_payload_hashes or image_id in existing_image_ids:
            skipped.append({"payload_hash": payload_hash, "image_id": image_id, "reason": "already_in_artifact"})
            continue
        source_record = corpus_by_payload.get(payload_hash) or corpus_by_image_id.get(image_id)
        if source_record is None:
            skipped.append({"payload_hash": payload_hash, "image_id": image_id, "reason": "missing_in_current_corpus"})
            continue
        if source_url and source_url != str(source_record.get("source_url") or "").strip():
            skipped.append({"payload_hash": payload_hash, "image_id": image_id, "reason": "source_url_mismatch"})
            continue
        normalized = dict(source_record)
        normalized["local_path"] = resolve_current_artist_works_local_path(
            normalized.get("local_path"),
            fair_slug=str(normalized.get("fair_slug") or "").strip(),
        )
        stabilized = _stabilize_artwork_image_record(normalized, resolve_local_path=False)
        if stabilized is None or not Path(str(stabilized.get("local_path") or "")).exists():
            skipped.append({"payload_hash": payload_hash, "image_id": image_id, "reason": "local_path_unavailable"})
            continue
        append_candidates.append(stabilized)
        candidate_keys.append(image_id)
        existing_payload_hashes.add(payload_hash)
        existing_image_ids.add(image_id)

    encoded_rows, append_embeddings = _encode_corpus_images(append_candidates)
    encoded_image_ids = {str(row.get("image_id") or "").strip() for row in encoded_rows}
    for row in append_candidates:
        row_image_id = str(row.get("image_id") or "").strip()
        if row_image_id and row_image_id not in encoded_image_ids:
            skipped.append(
                {
                    "payload_hash": str(row.get("payload_hash") or "").strip(),
                    "image_id": row_image_id,
                    "reason": "encode_failed_or_unreadable",
                }
            )

    append_count = len(encoded_rows)
    if append_count and append_embeddings.ndim == 2 and append_embeddings.shape[1] == existing_embeddings.shape[1]:
        append_index = _normalize_matrix(append_embeddings)
        final_embeddings = np.vstack([existing_embeddings, append_embeddings.astype(np.float32)]).astype(np.float32)
        final_index = np.vstack([existing_index, append_index]).astype(np.float32)
        final_records = list(existing_records) + list(encoded_rows)
        _atomic_save_npy(paths["embeddings"], final_embeddings)
        _atomic_save_npy(paths["index"], final_index)
        _atomic_save_id_map(paths["id_map"], final_records)
        status = "appended"
    elif append_count == 0:
        final_embeddings = existing_embeddings
        final_index = existing_index
        final_records = existing_records
        status = "no_rows_appended"
    else:
        final_embeddings = existing_embeddings
        final_index = existing_index
        final_records = existing_records
        skipped.append({"payload_hash": "", "image_id": "", "reason": "append_embedding_dimension_mismatch"})
        status = "failed_append_dimension_mismatch"

    appended_rows = [
        {
            "payload_hash": str(row.get("payload_hash") or "").strip(),
            "image_id": str(row.get("image_id") or "").strip(),
            "fair_slug": str(row.get("fair_slug") or "").strip(),
            "source_url": str(row.get("source_url") or "").strip(),
            "local_path": str(row.get("local_path") or "").strip(),
            "r2_key": str(row.get("r2_key") or "").strip(),
            "image_url": str(row.get("image_url") or "").strip(),
        }
        for row in encoded_rows
    ]

    result.update(
        {
            "status": status,
            "append_target_rows": len(append_candidates),
            "append_success_rows": append_count,
            "skipped_rows": len(skipped),
            "read_or_encode_failed_rows": sum(
                1 for row in skipped if str(row.get("reason") or "").startswith(("local_path_", "encode_failed"))
            ),
            "shape_before": {
                "id_map_rows": len(existing_records),
                "embeddings_shape": list(existing_embeddings.shape),
                "index_shape": list(existing_index.shape),
            },
            "shape_after": {
                "id_map_rows": len(final_records),
                "embeddings_shape": list(final_embeddings.shape),
                "index_shape": list(final_index.shape),
            },
            "added_rows": appended_rows,
            "added_payload_hashes": [row["payload_hash"] for row in appended_rows],
            "added_image_ids": [row["image_id"] for row in appended_rows],
            "skipped_details": skipped,
            "candidate_image_ids": candidate_keys,
        }
    )

    result["completed_at_utc"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    result["manifest_path"] = str(manifest_path)
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return result


def _normalize_matrix(vectors: np.ndarray) -> np.ndarray:
    if vectors.size == 0:
        return vectors.astype(np.float32)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (vectors / norms).astype(np.float32)


def _normalize_text_query(query_text: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(query_text or "")).strip().lower()
    normalized = QUERY_SEP_RE.sub(" ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _contains_japanese_text(text: str) -> bool:
    return bool(JAPANESE_CHAR_RE.search(str(text or "")))


@lru_cache(maxsize=1)
def _get_openai_rewrite_client() -> tuple[object | None, str]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None, "artwork_query_rewrite_openai_api_key_missing"

    try:
        from openai import OpenAI
    except Exception as exc:
        return None, f"artwork_query_rewrite_runtime_unavailable: {type(exc).__name__}"

    try:
        client = OpenAI(api_key=api_key)
    except Exception as exc:
        return None, f"artwork_query_rewrite_client_init_failed: {type(exc).__name__}"
    return client, ""


def _sanitize_rewritten_query(query_text: str) -> str:
    sanitized = str(query_text or "").strip()
    sanitized = sanitized.strip("`\"' ")
    if not sanitized:
        return ""
    sanitized = sanitized.splitlines()[0].strip()
    sanitized = re.sub(r"^[A-Za-z][A-Za-z\s_-]{0,24}:\s*", "", sanitized)
    sanitized = _normalize_text_query(sanitized)
    return sanitized


def rewrite_japanese_query_for_artwork_search(query_text: str) -> tuple[str, List[str], str]:
    normalized_query = _normalize_text_query(query_text)
    if not normalized_query:
        raise ValueError("text query is empty")
    if not _contains_japanese_text(normalized_query):
        return normalized_query, [], "direct_openclip"

    client, client_warning = _get_openai_rewrite_client()
    warnings: List[str] = []
    if client is None:
        if client_warning:
            warnings.append(client_warning)
        warnings.append("artwork_query_rewrite_fallback_to_original_query")
        return normalized_query, warnings, "fallback_original_query"

    prompt = (
        "Rewrite this Japanese artwork search query into exactly one short English query for OpenCLIP image search.\n"
        "Rules:\n"
        "- Output only the rewritten English query.\n"
        "- No explanation.\n"
        "- No quotes.\n"
        "- No multiple options.\n"
        "- Keep it short and visually descriptive.\n"
        f"Japanese query: {normalized_query}"
    )

    try:
        response = client.responses.create(
            model=ARTWORK_SEARCH_QUERY_REWRITE_MODEL,
            input=prompt,
            max_output_tokens=ARTWORK_SEARCH_QUERY_REWRITE_MAX_OUTPUT_TOKENS,
            reasoning={"effort": "minimal"},
            text={"verbosity": "low"},
        )
    except Exception as exc:
        warnings.append(f"artwork_query_rewrite_failed_fallback_to_original_query: {type(exc).__name__}")
        return normalized_query, warnings, "fallback_original_query"

    rewritten_query = _sanitize_rewritten_query(getattr(response, "output_text", ""))
    if not rewritten_query:
        warnings.append("artwork_query_rewrite_empty_result_fallback_to_original_query")
        return normalized_query, warnings, "fallback_original_query"
    if _contains_japanese_text(rewritten_query):
        warnings.append("artwork_query_rewrite_non_english_result_fallback_to_original_query")
        return normalized_query, warnings, "fallback_original_query"
    return rewritten_query, warnings, "rewritten_to_english"


@lru_cache(maxsize=1)
def _get_openclip_runtime():
    try:
        import open_clip
        import torch
    except Exception as exc:
        raise RuntimeError(
            "OpenCLIP runtime is unavailable. Install `open_clip_torch` and `torch` to use ArtWork Search."
        ) from exc

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model, _, preprocess = open_clip.create_model_and_transforms(
        ARTWORK_SEARCH_OPENCLIP_MODEL,
        pretrained=ARTWORK_SEARCH_OPENCLIP_PRETRAINED,
        device=device,
    )
    tokenizer = open_clip.get_tokenizer(ARTWORK_SEARCH_OPENCLIP_MODEL)
    model.eval()
    return {
        "torch": torch,
        "model": model,
        "preprocess": preprocess,
        "tokenizer": tokenizer,
        "device": device,
    }


def _encode_corpus_images(records: List[dict]) -> tuple[List[dict], np.ndarray]:
    runtime = _get_openclip_runtime()
    torch = runtime["torch"]
    model = runtime["model"]
    preprocess = runtime["preprocess"]
    device = runtime["device"]
    batches: List[np.ndarray] = []
    encoded_rows: List[dict] = []

    with torch.no_grad():
        for start in range(0, len(records), ARTWORK_SEARCH_BATCH_SIZE):
            batch_rows = records[start : start + ARTWORK_SEARCH_BATCH_SIZE]
            images = []
            valid_rows = []
            for row in batch_rows:
                local_path = str(row.get("local_path") or "").strip()
                if not local_path:
                    continue
                try:
                    with Image.open(local_path) as raw_image:
                        images.append(preprocess(raw_image.convert("RGB")))
                    valid_rows.append(row)
                except Exception:
                    continue
            if not images:
                continue
            batch_tensor = torch.stack(images).to(device)
            batch_embeddings = model.encode_image(batch_tensor)
            batch_embeddings = batch_embeddings.detach().cpu().numpy().astype(np.float32)
            batches.append(batch_embeddings)
            encoded_rows.extend(valid_rows)

    if not batches:
        return [], np.zeros((0, 0), dtype=np.float32)
    return encoded_rows, np.vstack(batches).astype(np.float32)


def _encode_text_query(query_text: str) -> np.ndarray:
    runtime = _get_openclip_runtime()
    torch = runtime["torch"]
    model = runtime["model"]
    tokenizer = runtime["tokenizer"]
    device = runtime["device"]
    normalized_query = _normalize_text_query(query_text)
    if not normalized_query:
        raise ValueError("text query is empty")
    with torch.no_grad():
        tokens = tokenizer([normalized_query]).to(device)
        embedding = model.encode_text(tokens).detach().cpu().numpy().astype(np.float32)
    return _normalize_matrix(embedding)[0]


def _encode_image_query(image_bytes: bytes) -> np.ndarray:
    runtime = _get_openclip_runtime()
    torch = runtime["torch"]
    model = runtime["model"]
    preprocess = runtime["preprocess"]
    device = runtime["device"]
    if not image_bytes:
        raise ValueError("image query is empty")
    with Image.open(io.BytesIO(image_bytes)) as raw_image:
        image_tensor = preprocess(raw_image.convert("RGB")).unsqueeze(0).to(device)
    with torch.no_grad():
        embedding = model.encode_image(image_tensor).detach().cpu().numpy().astype(np.float32)
    return _normalize_matrix(embedding)[0]


def _load_existing_state(target_year: int = TARGET_YEAR) -> ArtworkSearchState | None:
    paths = _artifact_paths(target_year)
    missing_artifacts = [name for name, path in paths.items() if not hydrate_path_from_r2(path)]
    if missing_artifacts:
        return None

    warnings: List[str] = []
    try:
        embeddings = np.load(paths["embeddings"]).astype(np.float32)
        index_matrix = np.load(paths["index"]).astype(np.float32)
        records, id_map_warnings = _load_id_map(paths["id_map"])
        warnings.extend(id_map_warnings)
    except Exception:
        return None
    if embeddings.ndim != 2 or index_matrix.ndim != 2 or len(records) != embeddings.shape[0] or embeddings.shape != index_matrix.shape:
        return None
    keep_positions: list[int] = []
    stabilized_records: list[dict] = []
    for idx, row in enumerate(records):
        stabilized = _stabilize_artwork_image_record(row, resolve_local_path=False)
        if stabilized is None:
            continue
        keep_positions.append(idx)
        stabilized_records.append(stabilized)
    if not stabilized_records:
        return None
    if len(stabilized_records) != len(records):
        keep_index = np.asarray(keep_positions, dtype=np.int64)
        embeddings = embeddings[keep_index]
        index_matrix = index_matrix[keep_index]
        warnings.append(
            "artwork_search_filtered_undisplayable_rows:"
            f" removed={len(records) - len(stabilized_records)}"
        )
    records = stabilized_records
    return ArtworkSearchState(
        records=records,
        embeddings=embeddings,
        index_matrix=index_matrix,
        warnings=sorted(set(warnings)),
        artifact_status="loaded",
        corpus_stats={
            "rows_total": 0,
            "images_total": len(records),
            "deduped_images": 0,
            "skipped_zero_image_rows": 0,
            "skipped_missing_local_path": 0,
            "available_fair_counts": {
                "frieze_london": sum(1 for row in records if str(row.get("fair_slug") or "") == "frieze_london"),
                "liste": sum(1 for row in records if str(row.get("fair_slug") or "") == "liste"),
            },
        },
    )


def _build_state_from_local_corpus(target_year: int = TARGET_YEAR) -> ArtworkSearchState:
    records, warnings, corpus_stats = _load_corpus_records_current_first()
    if not records:
        return _empty_state(warnings=warnings, artifact_status="empty")
    records, embeddings = _encode_corpus_images(records)
    if not records or embeddings.size == 0:
        return _empty_state(
            warnings=warnings + ["artwork_search_build_failed: no image embeddings were produced from the local corpus"],
            artifact_status="build_failed",
        )
    corpus_stats["images_total"] = len(records)
    corpus_stats["available_fair_counts"] = {
        "frieze_london": sum(1 for row in records if str(row.get("fair_slug") or "") == "frieze_london"),
        "liste": sum(1 for row in records if str(row.get("fair_slug") or "") == "liste"),
    }
    index_matrix = _normalize_matrix(embeddings)
    paths = _artifact_paths(target_year)
    paths["embeddings"].parent.mkdir(parents=True, exist_ok=True)
    np.save(paths["embeddings"], embeddings)
    np.save(paths["index"], index_matrix)
    _save_id_map(paths["id_map"], records)
    return ArtworkSearchState(
        records=records,
        embeddings=embeddings,
        index_matrix=index_matrix,
        warnings=warnings,
        artifact_status="built",
        corpus_stats=corpus_stats,
    )


@lru_cache(maxsize=4)
def _load_or_build_artwork_search_state_cached(target_year: int) -> ArtworkSearchState:
    existing = _load_existing_state(target_year)
    if existing is not None:
        return existing
    return _build_state_from_local_corpus(target_year)


def load_or_build_artwork_search_state(target_year: int = TARGET_YEAR) -> ArtworkSearchState:
    return _load_or_build_artwork_search_state_cached(int(target_year or TARGET_YEAR))


def _normalize_fair_filter(fair_filter: str) -> str:
    raw = str(fair_filter or "").strip()
    if raw in {"both", "frieze_london", "liste"}:
        return raw
    return FAIR_LABEL_TO_SLUG.get(raw, "both")


def _filter_indices_by_fair(records: List[dict], fair_filter: str) -> np.ndarray:
    normalized_filter = _normalize_fair_filter(fair_filter)
    if normalized_filter == "both":
        return np.arange(len(records), dtype=np.int64)
    return np.array(
        [idx for idx, row in enumerate(records) if str(row.get("fair_slug") or "") == normalized_filter],
        dtype=np.int64,
    )


def _has_http_image_url(value: str) -> bool:
    url = str(value or "").strip().lower()
    return url.startswith("http://") or url.startswith("https://")


def _resolve_preview_local_path(row: dict) -> str:
    local_path = resolve_current_artist_works_local_path(
        row.get("local_path"),
        fair_slug=str(row.get("fair_slug") or "").strip(),
        hydrate_from_r2=False,
    )
    if not local_path:
        return ""
    try:
        return local_path if Path(local_path).exists() else ""
    except OSError:
        return ""


def _has_resolvable_preview(row: dict) -> tuple[bool, str]:
    resolved_local_path = _resolve_preview_local_path(row)
    if resolved_local_path:
        return True, resolved_local_path
    if str(row.get("r2_key") or "").strip():
        return True, ""
    if _has_http_image_url(str(row.get("image_url") or "").strip()):
        return True, ""
    return False, ""


def _score_rows(
    state: ArtworkSearchState,
    query_vectors: list[tuple[np.ndarray, float]],
    fair_filter: str,
    top_k: int,
) -> List[dict]:
    if not state.records or state.index_matrix.size == 0:
        return []
    candidate_indices = _filter_indices_by_fair(state.records, fair_filter)
    if candidate_indices.size == 0:
        return []
    if not query_vectors:
        return []
    candidate_matrix = state.index_matrix[candidate_indices]
    score_columns = []
    for query_vector, weight in query_vectors:
        column = candidate_matrix @ query_vector.astype(np.float32)
        score_columns.append(column * float(weight))
    scores = np.max(np.stack(score_columns, axis=1), axis=1)
    limit = max(1, int(top_k or ARTWORK_SEARCH_TOP_K_DEFAULT))
    order = np.argsort(scores)[::-1]
    preview_rows: List[dict] = []
    fallback_rows: List[dict] = []
    for pos in order:
        pos_int = int(pos)
        corpus_idx = int(candidate_indices[pos_int])
        source_row = state.records[corpus_idx]
        has_preview, resolved_local_path = _has_resolvable_preview(source_row)
        row = dict(source_row)
        if resolved_local_path:
            row["local_path"] = resolved_local_path
        row["score"] = float(scores[pos_int])
        if has_preview:
            preview_rows.append(row)
            if len(preview_rows) >= limit:
                break
        else:
            fallback_rows.append(row)
    rows = preview_rows[:limit]
    if len(rows) < limit:
        rows.extend(fallback_rows[: limit - len(rows)])
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    return rows


def search_artwork_images_by_text(
    query_text: str,
    *,
    fair_filter: str = "both",
    top_k: int = ARTWORK_SEARCH_TOP_K_DEFAULT,
    target_year: int = TARGET_YEAR,
) -> dict:
    state = load_or_build_artwork_search_state(target_year)
    rewritten_query, query_warnings, rewrite_status = rewrite_japanese_query_for_artwork_search(query_text)
    query_vector = _encode_text_query(rewritten_query)
    return {
        "mode": "text",
        "rows": _score_rows(
            state,
            [(query_vector, 1.0)],
            fair_filter,
            top_k,
        ),
        "warnings": list(state.warnings) + query_warnings,
        "artifact_status": state.artifact_status,
        "corpus_stats": dict(state.corpus_stats),
        "query_text_used": rewritten_query,
        "query_rewrite_status": rewrite_status,
    }


def search_artwork_images_by_image(
    image_bytes: bytes,
    *,
    fair_filter: str = "both",
    top_k: int = ARTWORK_SEARCH_TOP_K_DEFAULT,
    target_year: int = TARGET_YEAR,
) -> dict:
    state = load_or_build_artwork_search_state(target_year)
    query_vector = _encode_image_query(image_bytes)
    return {
        "mode": "image",
        "rows": _score_rows(
            state,
            [(query_vector, 1.0)],
            fair_filter,
            top_k,
        ),
        "warnings": list(state.warnings),
        "artifact_status": state.artifact_status,
        "corpus_stats": dict(state.corpus_stats),
    }
