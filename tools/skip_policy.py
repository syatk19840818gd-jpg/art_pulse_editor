from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from phase2_art_pulse_config import get_phase1_legacy_trial_root

FILL_MISSING_MODE = "fill_missing"
REBUILD_MODE = "rebuild"
DEFAULT_TRIAL_ROOT = get_phase1_legacy_trial_root()
FILL_MISSING_TOPUP_DEFAULT = False

ARTIST_IMAGE_REASON_NO_METADATA_ROW = "NO_METADATA_ROW"
ARTIST_IMAGE_REASON_NO_METADATA_HASHES = "NO_METADATA_HASHES"
ARTIST_IMAGE_REASON_KEY_PRESENT_BUT_FILE_MISSING = "KEY_PRESENT_BUT_FILE_MISSING"
ARTIST_IMAGE_REASON_PAYLOAD_HASH_MISMATCH = "PAYLOAD_HASH_MISMATCH"
ARTIST_IMAGE_REASON_PARTIAL_UNDER_TARGET = "PARTIAL_UNDER_TARGET"
ARTIST_IMAGE_REASON_COMPLETE = "COMPLETE_EXISTING"
ARTIST_IMAGE_REASON_SAME_SOURCE_YEARLY_DIFF = "SAME_SOURCE_YEARLY_DIFF_APPEND_ONLY"
ARTIST_IMAGE_REASON_PARTIAL_AS_COMPLETE = "PARTIAL_UNDER_TARGET_AS_COMPLETE_IN_FILL_MISSING"
ARTIST_IMAGE_REASON_UNRESOLVABLE_SKIPPED = "UNRESOLVABLE_TARGET_SKIPPED_IN_FILL_MISSING"

_TRACKING_QUERY_KEYS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "gclid",
    "fbclid",
}


def resolve_run_mode(*, mode: str, allow_rebuild: bool, run_id: str) -> str:
    normalized = str(mode or FILL_MISSING_MODE).strip().lower()
    if normalized not in {FILL_MISSING_MODE, REBUILD_MODE}:
        raise ValueError(f"unsupported_mode:{normalized}")
    if normalized == REBUILD_MODE:
        if not allow_rebuild:
            raise ValueError("rebuild_requires_allow_rebuild_flag")
        if not str(run_id or "").strip():
            raise ValueError("rebuild_requires_run_id")
    else:
        if str(run_id or "").strip():
            raise ValueError("fill_missing_mode_disallows_run_id")
    return normalized


def build_trial_root(*, trial_root: str | Path, run_id: str) -> Path:
    base = Path(trial_root)
    return (base / str(run_id).strip()).resolve()


def normalize_url_key(url: str) -> str:
    raw = str(url or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    scheme = "https"
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    query_items = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if str(k or "").lower() not in _TRACKING_QUERY_KEYS
    ]
    query = urlencode(sorted(query_items))
    return urlunparse((scheme, netloc, path, "", query, ""))


def should_skip_text_record(
    *,
    source_url: str,
    text_hash: str,
    existing_source_keys: set[str],
    existing_text_hashes: set[str],
) -> tuple[bool, str]:
    source_key = normalize_url_key(source_url)
    hash_key = str(text_hash or "").strip()
    if source_key and source_key in existing_source_keys:
        return True, "KNOWN_SOURCE_URL_EXISTING"
    if hash_key and hash_key in existing_text_hashes:
        return True, "DUPLICATE_TEXT_HASH_EXISTING"
    return False, ""


def has_local_file(local_path: str | Path) -> bool:
    path = Path(local_path)
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    return path.exists() and path.is_file()


def should_skip_image_record(
    *,
    image_key: str,
    local_path: str,
    existing_image_keys: set[str],
) -> tuple[bool, str]:
    key = str(image_key or "").strip()
    if not key:
        return False, ""
    if key not in existing_image_keys:
        return False, ""
    if not has_local_file(local_path):
        return False, "MISSING_LOCAL_FILE_RECOVERY_REQUIRED"
    return True, "KNOWN_IMAGE_KEY_WITH_LOCAL_FILE"


def should_fetch_artist_image_in_mode(
    *,
    mode: str,
    reason: str,
    fill_missing_topup: bool = FILL_MISSING_TOPUP_DEFAULT,
) -> tuple[bool, str]:
    reason_key = str(reason or "").strip() or ARTIST_IMAGE_REASON_COMPLETE
    if mode == REBUILD_MODE:
        return reason_key != ARTIST_IMAGE_REASON_COMPLETE, reason_key
    if reason_key == ARTIST_IMAGE_REASON_PARTIAL_UNDER_TARGET and not bool(fill_missing_topup):
        return False, ARTIST_IMAGE_REASON_PARTIAL_AS_COMPLETE
    fetch_reasons = {
        ARTIST_IMAGE_REASON_NO_METADATA_ROW,
        ARTIST_IMAGE_REASON_NO_METADATA_HASHES,
        ARTIST_IMAGE_REASON_KEY_PRESENT_BUT_FILE_MISSING,
        ARTIST_IMAGE_REASON_PAYLOAD_HASH_MISMATCH,
    }
    return reason_key in fetch_reasons, reason_key


def should_skip_known_unresolvable_target(
    *,
    mode: str,
    source_url: str,
    known_source_keys: set[str],
) -> tuple[bool, str]:
    if mode != FILL_MISSING_MODE:
        return False, ""
    source_key = normalize_url_key(source_url)
    if source_key and source_key in known_source_keys:
        return True, ARTIST_IMAGE_REASON_UNRESOLVABLE_SKIPPED
    return False, ""
