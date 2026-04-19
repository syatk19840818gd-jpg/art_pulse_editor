from __future__ import annotations

import hashlib
import io
import json
import os
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

import numpy as np
from PIL import Image

from phase2_art_pulse_config import (
    TARGET_YEAR,
    get_image_r2_key,
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


def _path_basename(path_text: object) -> str:
    raw = str(path_text or "").strip()
    if not raw:
        return ""
    try:
        return Path(raw).name.lower()
    except Exception:
        return ""


@lru_cache(maxsize=1)
def _load_current_metadata_slots_by_payload_hash() -> tuple[dict[str, list[dict]], List[str]]:
    lookup: dict[str, list[dict]] = {}
    warnings: List[str] = []
    for fair_slug, path in resolve_current_artist_works_image_meta_paths().items():
        image_rows, image_warnings = safe_load_jsonl(path, hydrate_r2=False)
        warnings.extend(image_warnings)
        for row in image_rows:
            local_paths = row.get("works_image_local_paths")
            if not isinstance(local_paths, list) or not local_paths:
                continue
            payload_hashes = row.get("works_image_payload_hashes")
            r2_keys = row.get("works_image_r2_keys")
            image_urls = row.get("works_image_urls")
            source_url = str(row.get("source_url") or "").strip()
            for slot_index, local_path_raw in enumerate(local_paths):
                payload_hash = _pick_list_value(payload_hashes, slot_index)
                if not payload_hash:
                    continue
                lookup.setdefault(payload_hash, []).append(
                    {
                        "payload_hash": payload_hash,
                        "fair_slug": fair_slug,
                        "source_url": source_url,
                        "local_path": str(local_path_raw or "").strip(),
                        "r2_key": _pick_list_value(r2_keys, slot_index),
                        "image_url": _pick_list_value(image_urls, slot_index),
                        "slot_index": int(slot_index),
                    }
                )
    return lookup, sorted(set(warnings))


def _pick_best_metadata_slot_for_row(row: dict, slots: list[dict]) -> dict | None:
    if not slots:
        return None
    fair_slug = str(row.get("fair_slug") or "").strip()
    source_url = str(row.get("source_url") or "").strip()
    local_basename = _path_basename(row.get("local_path"))
    best_slot: dict | None = None
    best_score = -1
    for slot in slots:
        score = 0
        if fair_slug and str(slot.get("fair_slug") or "").strip() == fair_slug:
            score += 4
        if source_url and str(slot.get("source_url") or "").strip() == source_url:
            score += 3
        if local_basename and _path_basename(slot.get("local_path")) == local_basename:
            score += 2
        if str(slot.get("r2_key") or "").strip():
            score += 1
        if best_slot is None or score > best_score:
            best_slot = slot
            best_score = score
    return best_slot


def _repair_existing_record_with_payload_hash_join(
    row: dict,
    payload_lookup: dict[str, list[dict]],
) -> tuple[dict, dict[str, bool]]:
    repaired = dict(row)
    payload_hash = str(repaired.get("payload_hash") or repaired.get("image_id") or "").strip()
    slot = _pick_best_metadata_slot_for_row(repaired, payload_lookup.get(payload_hash) or [])
    fair_slug = str(repaired.get("fair_slug") or "").strip()
    if not fair_slug and slot is not None:
        fair_slug = str(slot.get("fair_slug") or "").strip()
        if fair_slug:
            repaired["fair_slug"] = fair_slug

    local_before = str(repaired.get("local_path") or "").strip()
    local_candidates = [local_before]
    if slot is not None:
        local_candidates.append(str(slot.get("local_path") or "").strip())
    resolved_local_path = ""
    for candidate in local_candidates:
        resolved_local_path = resolve_current_artist_works_local_path(candidate, fair_slug=fair_slug)
        if resolved_local_path:
            break
    if resolved_local_path:
        repaired["local_path"] = resolved_local_path
    else:
        repaired["local_path"] = local_before

    r2_before = str(repaired.get("r2_key") or "").strip()
    if not r2_before:
        r2_candidate = str(slot.get("r2_key") or "").strip() if slot is not None else ""
        if not r2_candidate and resolved_local_path:
            r2_candidate = str(get_image_r2_key(resolved_local_path) or "").strip()
        repaired["r2_key"] = r2_candidate
    else:
        repaired["r2_key"] = r2_before

    # Keep direct URL exactly as existing id_map value in this load-time repair.
    repaired["image_url"] = str(repaired.get("image_url") or "").strip()
    return repaired, {
        "has_payload": bool(payload_hash),
        "payload_joined": slot is not None,
        "local_relinked": bool(resolved_local_path and resolved_local_path != local_before),
        "r2_relinked": bool((not r2_before) and str(repaired.get("r2_key") or "").strip()),
    }


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
    payload_lookup, metadata_warnings = _load_current_metadata_slots_by_payload_hash()
    warnings.extend(metadata_warnings)
    payload_rows = 0
    payload_joined_rows = 0
    local_relinked_rows = 0
    r2_relinked_rows = 0
    keep_positions: list[int] = []
    stabilized_records: list[dict] = []
    for idx, row in enumerate(records):
        repaired_row, repair_stats = _repair_existing_record_with_payload_hash_join(row, payload_lookup)
        if repair_stats["has_payload"]:
            payload_rows += 1
        if repair_stats["payload_joined"]:
            payload_joined_rows += 1
        if repair_stats["local_relinked"]:
            local_relinked_rows += 1
        if repair_stats["r2_relinked"]:
            r2_relinked_rows += 1
        stabilized = _stabilize_artwork_image_record(repaired_row, resolve_local_path=False)
        if stabilized is None:
            continue
        keep_positions.append(idx)
        stabilized_records.append(stabilized)
    if not stabilized_records:
        return None
    warnings.append(
        "artwork_search_payload_join_repair:"
        f" payload_rows={payload_rows}"
        f" joined={payload_joined_rows}"
        f" local_relinked={local_relinked_rows}"
        f" r2_relinked={r2_relinked_rows}"
    )
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
