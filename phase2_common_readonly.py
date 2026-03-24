from __future__ import annotations

import json
import os
import re
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Tuple

from phase2_art_pulse_config import (
    CURRENT_IMAGES_METADATA_DIR,
    CURRENT_IMAGES_METADATA_R2_PREFIX,
    CURRENT_RAW_DIR,
    CURRENT_RAW_R2_PREFIX,
    TARGET_YEAR,
    get_enrichment_current_output_path,
    get_current_raw_paths,
    get_current_artist_image_meta_paths,
    get_current_exhibitions_image_meta_paths,
    get_image_cache_dir,
    get_image_r2_key,
)
from phase1_artist_link_utils import (
    build_artist_name_en_from_source_url,
    is_invalid_artist_name,
    sanitize_artist_name_en,
)

try:
    import boto3
except Exception:
    boto3 = None

REPO_ROOT = Path(__file__).resolve().parent

FAIR_LABEL_TO_SLUG = {
    "Frieze London": "frieze_london",
    "Liste Art Fair Basel": "liste",
}
FAIR_SLUG_TO_LABEL = {value: key for key, value in FAIR_LABEL_TO_SLUG.items()}

EXHIBITIONS_TEXT_PATHS = {
    fair_slug: REPO_ROOT / path
    for fair_slug, path in get_current_raw_paths("exhibitions").items()
}
ARTISTS_TEXT_PATHS = {
    fair_slug: REPO_ROOT / path
    for fair_slug, path in get_current_raw_paths("artists").items()
}
EXHIBITIONS_IMAGE_META_PATHS = {
    fair_slug: REPO_ROOT / path
    for fair_slug, path in get_current_exhibitions_image_meta_paths().items()
}
ARTIST_WORKS_IMAGE_PATHS = {
    fair_slug: REPO_ROOT / path
    for fair_slug, path in get_current_artist_image_meta_paths().items()
}

GALLERY_LIST_PATHS = {
    "frieze_london": REPO_ROOT / "data/gallery_lists/gallery_list_frieze_london.csv",
    "liste": REPO_ROOT / "data/gallery_lists/gallery_list_liste.csv",
}

TARUTANI_TEXT_PATH = REPO_ROOT / "data/Tarutani_data/tarutani_text.jsonl"
IMAGE_CACHE_ROOT = REPO_ROOT / get_image_cache_dir()


def resolve_current_first_enrichment_output_path(
    category: str, target_year: int = TARGET_YEAR
) -> tuple[Path | None, str]:
    current_path = REPO_ROOT / get_enrichment_current_output_path(category, target_year)
    # Strict current-only contract: hydrate only the canonical current lane from R2.
    if not current_path.exists():
        r2_key = _local_path_to_r2_key(current_path)
        if r2_key:
            _download_r2_object_to_local(current_path, r2_key)
    if current_path.exists():
        return current_path, "current"
    return None, "missing"


def resolve_fair_slugs(fair_label: str) -> List[str]:
    if fair_label == "Frieze London + Liste Art Fair Basel":
        return ["frieze_london", "liste"]
    if fair_label in FAIR_LABEL_TO_SLUG:
        return [FAIR_LABEL_TO_SLUG[fair_label]]
    return ["frieze_london", "liste"]


def _get_env_value(*keys: str) -> str:
    for key in keys:
        value = os.getenv(key, "").strip()
        if value:
            return value
    return ""


@lru_cache(maxsize=1)
def _get_r2_runtime() -> tuple[object | None, str]:
    if boto3 is None:
        return None, ""
    endpoint = _get_env_value("R2_ENDPOINT", "R2_ENDPOINT_URL", "R2_S3_ENDPOINT")
    bucket = _get_env_value("R2_BUCKET")
    access_key = _get_env_value("R2_ACCESS_KEY_ID")
    secret_key = _get_env_value("R2_SECRET_ACCESS_KEY")
    region = _get_env_value("R2_REGION") or "auto"
    if not endpoint or not bucket or not access_key or not secret_key:
        return None, ""
    try:
        client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )
        return client, bucket
    except Exception:
        return None, ""


def _local_path_to_r2_key(path: Path) -> str:
    try:
        rel = path.resolve().relative_to(REPO_ROOT).as_posix()
    except Exception:
        rel = path.as_posix()

    current_raw_prefix = CURRENT_RAW_DIR.as_posix().rstrip("/") + "/"
    if rel.startswith(current_raw_prefix):
        return CURRENT_RAW_R2_PREFIX + "/" + rel[len(current_raw_prefix) :]
    current_images_metadata_prefix = CURRENT_IMAGES_METADATA_DIR.as_posix().rstrip("/") + "/"
    if rel.startswith(current_images_metadata_prefix):
        return CURRENT_IMAGES_METADATA_R2_PREFIX + "/" + rel[len(current_images_metadata_prefix) :]
    image_cache_r2_key = get_image_r2_key(path, repo_root=REPO_ROOT)
    if image_cache_r2_key:
        return image_cache_r2_key
    if rel.startswith("data/current/enrichment/"):
        return "data/current/enrichment/" + rel[len("data/current/enrichment/") :]
    if rel.startswith("data/history/enrichment/artists/"):
        return "data/history/enrichment/artists/" + rel[len("data/history/enrichment/artists/") :]
    if rel.startswith("data/history/enrichment/exhibitions/"):
        return "data/history/enrichment/exhibitions/" + rel[len("data/history/enrichment/exhibitions/") :]
    if rel.startswith("data/Tarutani_data/"):
        return rel
    if rel.startswith("data/gallery_lists/"):
        return rel
    if rel.startswith("docs/"):
        return rel
    return ""


def _download_r2_object_to_local(path: Path, r2_key: str) -> bool:
    client, bucket = _get_r2_runtime()
    if client is None or not bucket or not r2_key:
        return False
    try:
        head = client.head_object(Bucket=bucket, Key=r2_key)
    except Exception:
        return False

    remote_size = int(head.get("ContentLength") or 0)
    try:
        if path.exists() and path.stat().st_size == remote_size:
            return True
    except OSError:
        pass

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, dir=str(path.parent), suffix=".tmp") as tmp:
            tmp_path = tmp.name
            client.download_fileobj(bucket, r2_key, tmp)
        os.replace(tmp_path, path)
        return True
    except Exception:
        if tmp_path:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except Exception:
                pass
        return False


def safe_load_jsonl(path: Path, *, hydrate_r2: bool = True) -> Tuple[List[dict], List[str]]:
    rows: List[dict] = []
    warnings: List[str] = []
    if hydrate_r2:
        r2_key = _local_path_to_r2_key(path)
        if r2_key:
            _download_r2_object_to_local(path, r2_key)
    if not path.exists():
        warnings.append(f"missing: {path}")
        return rows, warnings
    try:
        with path.open("r", encoding="utf-8") as f:
            for idx, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    warnings.append(f"json_decode_error: {path} line={idx}")
    except OSError as exc:
        warnings.append(f"read_error: {path} ({exc})")
    return rows, warnings


def normalize_url(url: str) -> str:
    value = (url or "").strip()
    if not value:
        return ""
    return value.rstrip("/")


def derive_exhibition_title(row: dict) -> str:
    headline = (row.get("headline_ja") or "").strip()
    if headline:
        return headline
    text = (row.get("text") or "").strip()
    if text:
        first_line = text.splitlines()[0].strip()
        if first_line:
            return first_line[:120]
    source_url = (row.get("source_url") or "").strip().rstrip("/")
    if source_url:
        tail = source_url.split("/")[-1]
        if tail:
            return tail.replace("-", " ")
    return "(untitled)"


def derive_artist_name(source_url: str, fallback: str = "") -> str:
    fallback_name = sanitize_artist_name_en(fallback)
    if fallback_name and not is_invalid_artist_name(fallback_name):
        return fallback_name

    source_name = sanitize_artist_name_en(build_artist_name_en_from_source_url(source_url))
    if source_name and not is_invalid_artist_name(source_name):
        return source_name

    url = (source_url or "").strip().rstrip("/")
    if not url:
        return "(unknown artist)"

    last = sanitize_artist_name_en(url.split("/")[-1].replace("-", " ").strip())
    if last and not is_invalid_artist_name(last):
        return last
    return "(unknown artist)"
