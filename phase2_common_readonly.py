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
    CURRENT_VECTOR_DIR,
    TARGET_YEAR,
    get_artist_image_cache_dir,
    get_current_artist_text_vector_artifact_paths as get_current_artist_text_vector_artifact_paths_config,
    get_current_artist_text_paths,
    get_enrichment_current_output_path,
    get_current_artist_image_meta_paths,
    get_current_artist_works_artifact_paths as get_current_artist_works_artifact_paths_config,
    get_current_exhibitions_image_meta_paths,
    get_current_raw_paths,
    get_image_cache_dir,
    get_image_r2_key,
    normalize_image_local_path_text,
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
CURRENT_RAW_FILE_RE = re.compile(
    r"^(?P<category>artists|exhibitions)_(?P<fair_slug>[a-z0-9_]+)_(?P<year>\d{4})\.jsonl$"
)
CURRENT_EXHIBITIONS_IMAGE_META_FILE_RE = re.compile(
    r"^exhibitions_images_(?P<fair_slug>[a-z0-9_]+)_(?P<year>\d{4})\.jsonl$"
)
CURRENT_EXHIBITIONS_ENRICHMENT_FILE_RE = re.compile(
    r"^exhibitions_enrichment_apply_output_(?P<year>\d{4})\.jsonl$"
)


def _resolve_repo_paths(paths_by_key: Dict[str, Path]) -> Dict[str, Path]:
    return {
        key: REPO_ROOT / path
        for key, path in paths_by_key.items()
    }


def resolve_current_exhibitions_text_paths(
    target_year: int = TARGET_YEAR,
) -> Dict[str, Path]:
    return _resolve_repo_paths(get_current_raw_paths("exhibitions", target_year))


def resolve_current_artist_text_paths(
    target_year: int = TARGET_YEAR,
) -> Dict[str, Path]:
    return _resolve_repo_paths(get_current_artist_text_paths(target_year=target_year))


def resolve_current_exhibitions_image_meta_paths(
    target_year: int = TARGET_YEAR,
) -> Dict[str, Path]:
    return _resolve_repo_paths(get_current_exhibitions_image_meta_paths(target_year))


def resolve_current_artist_works_image_meta_paths() -> Dict[str, Path]:
    return _resolve_repo_paths(get_current_artist_image_meta_paths())


def resolve_current_artist_works_artifact_paths(
    target_year: int = TARGET_YEAR,
) -> Dict[str, Path]:
    return _resolve_repo_paths(
        get_current_artist_works_artifact_paths_config(target_year=target_year)
    )


def resolve_current_artist_text_artifact_paths(
    target_year: int = TARGET_YEAR,
) -> Dict[str, Path]:
    return _resolve_repo_paths(
        get_current_artist_text_vector_artifact_paths_config(target_year=target_year)
    )


EXHIBITIONS_TEXT_PATHS = resolve_current_exhibitions_text_paths()
ARTISTS_TEXT_PATHS = resolve_current_artist_text_paths()
EXHIBITIONS_IMAGE_META_PATHS = resolve_current_exhibitions_image_meta_paths()
ARTIST_WORKS_IMAGE_PATHS = resolve_current_artist_works_image_meta_paths()

GALLERY_LIST_PATHS = {
    "frieze_london": REPO_ROOT / "data/gallery_lists/gallery_list_frieze_london.csv",
    "liste": REPO_ROOT / "data/gallery_lists/gallery_list_liste.csv",
}

IMAGE_CACHE_ROOT = REPO_ROOT / get_image_cache_dir()


@lru_cache(maxsize=8192)
def resolve_current_artist_works_local_path(
    path_text: object,
    *,
    fair_slug: str = "",
    target_year: int = TARGET_YEAR,
    hydrate_from_r2: bool = True,
) -> str:
    normalized = normalize_image_local_path_text(path_text or "")
    if not normalized:
        return ""

    original = Path(normalized)
    basename = original.name.strip()
    current_cache_root = REPO_ROOT / get_artist_image_cache_dir() / str(int(target_year or TARGET_YEAR))
    candidate_paths: list[Path] = []
    fair_dir = str(fair_slug or "").strip().replace("_", "-")

    if basename:
        if fair_dir:
            candidate_paths.append(current_cache_root / fair_dir / basename)
        else:
            candidate_paths.extend(
                (
                    current_cache_root / "frieze-london" / basename,
                    current_cache_root / "liste" / basename,
                )
            )

    for candidate in candidate_paths:
        try:
            if candidate.exists() and candidate.is_file():
                return str(candidate)
            if hydrate_from_r2 and hydrate_path_from_r2(candidate) and candidate.is_file():
                return str(candidate)
        except Exception:
            continue

    try:
        original_rel = original.resolve().relative_to(REPO_ROOT).as_posix()
    except Exception:
        original_rel = ""
    if not original_rel.startswith("data/current/images/cache/"):
        return ""

    try:
        if original.exists() and original.is_file():
            return str(original)
        if hydrate_from_r2 and hydrate_path_from_r2(original) and original.is_file():
            return str(original)
    except Exception:
        return ""
    return ""


def resolve_current_first_enrichment_output_path(
    category: str, target_year: int = TARGET_YEAR
) -> tuple[Path | None, str]:
    current_path = REPO_ROOT / get_enrichment_current_output_path(category, target_year)
    # Strict current-only contract: hydrate only the canonical current lane from R2.
    if hydrate_path_from_r2(current_path):
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


@lru_cache(maxsize=16)
def _list_r2_keys_with_prefix(prefix: str) -> Tuple[str, ...]:
    client, bucket = _get_r2_runtime()
    if client is None or not bucket:
        return ()

    keys: List[str] = []
    continuation_token = ""
    normalized_prefix = prefix.rstrip("/") + "/"
    while True:
        kwargs = {
            "Bucket": bucket,
            "Prefix": normalized_prefix,
        }
        if continuation_token:
            kwargs["ContinuationToken"] = continuation_token
        try:
            response = client.list_objects_v2(**kwargs)
        except Exception:
            return tuple(keys)
        for item in list(response.get("Contents") or []):
            key = str(item.get("Key") or "").strip()
            if key and not key.endswith("/"):
                keys.append(key)
        if not response.get("IsTruncated"):
            return tuple(keys)
        continuation_token = str(response.get("NextContinuationToken") or "").strip()
        if not continuation_token:
            return tuple(keys)


def _collect_current_family_paths(
    local_dir: Path,
    r2_prefix: str,
    filename_re: re.Pattern[str],
) -> Dict[str, Path]:
    matched: Dict[str, Path] = {}
    local_root = REPO_ROOT / local_dir
    if local_root.exists():
        for path in local_root.iterdir():
            if path.is_file() and filename_re.fullmatch(path.name):
                matched[path.name] = path

    for r2_key in _list_r2_keys_with_prefix(r2_prefix):
        name = Path(r2_key).name
        if not filename_re.fullmatch(name) or name in matched:
            continue
        matched[name] = REPO_ROOT / Path(r2_key)
    return matched


def _resolve_current_raw_paths_by_year(category: str) -> Dict[str, Dict[int, Path]]:
    grouped: Dict[str, Dict[int, Path]] = {}
    for name, path in _collect_current_family_paths(
        CURRENT_RAW_DIR,
        CURRENT_RAW_R2_PREFIX,
        CURRENT_RAW_FILE_RE,
    ).items():
        match = CURRENT_RAW_FILE_RE.fullmatch(name)
        if match is None or match.group("category") != category:
            continue
        fair_slug = str(match.group("fair_slug"))
        year = int(match.group("year"))
        grouped.setdefault(fair_slug, {})[year] = path
    return grouped


def resolve_current_exhibitions_text_paths_by_year() -> Dict[str, Dict[int, Path]]:
    return _resolve_current_raw_paths_by_year("exhibitions")


def resolve_current_artist_text_paths_by_year() -> Dict[str, Dict[int, Path]]:
    return _resolve_current_raw_paths_by_year("artists")


def resolve_current_exhibitions_available_years() -> List[int]:
    years = {
        year
        for paths_by_year in resolve_current_exhibitions_text_paths_by_year().values()
        for year in paths_by_year.keys()
    }
    return sorted(years, reverse=True)


def resolve_current_exhibitions_image_meta_paths_by_year() -> Dict[str, Dict[int, Path]]:
    grouped: Dict[str, Dict[int, Path]] = {}
    for name, path in _collect_current_family_paths(
        CURRENT_IMAGES_METADATA_DIR,
        CURRENT_IMAGES_METADATA_R2_PREFIX,
        CURRENT_EXHIBITIONS_IMAGE_META_FILE_RE,
    ).items():
        match = CURRENT_EXHIBITIONS_IMAGE_META_FILE_RE.fullmatch(name)
        if match is None:
            continue
        fair_slug = str(match.group("fair_slug"))
        year = int(match.group("year"))
        grouped.setdefault(fair_slug, {})[year] = path
    return grouped


def resolve_current_exhibitions_enrichment_output_paths_by_year() -> Dict[int, Path]:
    grouped: Dict[int, Path] = {}
    for name, path in _collect_current_family_paths(
        Path("data/current/enrichment"),
        "data/current/enrichment",
        CURRENT_EXHIBITIONS_ENRICHMENT_FILE_RE,
    ).items():
        match = CURRENT_EXHIBITIONS_ENRICHMENT_FILE_RE.fullmatch(name)
        if match is None:
            continue
        year = int(match.group("year"))
        grouped[year] = path
    return grouped


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
    current_vector_prefix = CURRENT_VECTOR_DIR.as_posix().rstrip("/") + "/"
    if rel.startswith(current_vector_prefix):
        return rel
    image_cache_r2_key = get_image_r2_key(path, repo_root=REPO_ROOT)
    if image_cache_r2_key:
        return image_cache_r2_key
    if rel.startswith("data/current/enrichment/"):
        return "data/current/enrichment/" + rel[len("data/current/enrichment/") :]
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


def hydrate_path_from_r2(path: Path) -> bool:
    local_path = Path(path)
    if not local_path.is_absolute():
        local_path = REPO_ROOT / local_path
    r2_key = _local_path_to_r2_key(local_path)
    if r2_key:
        _download_r2_object_to_local(local_path, r2_key)
    return local_path.exists()


def safe_load_jsonl(path: Path, *, hydrate_r2: bool = True) -> Tuple[List[dict], List[str]]:
    rows: List[dict] = []
    warnings: List[str] = []
    if hydrate_r2:
        hydrate_path_from_r2(path)
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
