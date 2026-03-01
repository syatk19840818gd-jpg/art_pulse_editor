#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import html as html_lib
import hashlib
import json
import os
import re
import shutil
import socket
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from PIL import Image, UnidentifiedImageError
from phase1_artist_link_utils import (
    ARTIST_LINK_KEYWORDS,
    ARTIST_LIST_PATH_PATTERNS,
    looks_like_artist_detail_url as shared_looks_like_artist_detail_url,
    looks_like_artist_listing_url as shared_looks_like_artist_listing_url,
    normalize_url_for_link_compare as shared_normalize_url_for_link_compare,
)
from requests.adapters import HTTPAdapter
from r2_auto_sync import auto_sync_after_job, format_auto_sync_brief
try:
    from playwright.sync_api import (
        Error as PlaywrightError,
        TimeoutError as PlaywrightTimeoutError,
        sync_playwright,
    )
except Exception:  # pragma: no cover - optional runtime dependency
    PlaywrightError = Exception
    PlaywrightTimeoutError = Exception
    sync_playwright = None

try:
    from urllib3.util.retry import Retry
except Exception:  # pragma: no cover - fallback if urllib3 retry API changes
    Retry = None

SOURCE_CLI = "run_phase1_seed10_artist_image_collect.py"
TARGET_YEAR_DEFAULT = 2025
TARGET_IMAGES_PER_ARTIST_DEFAULT = 5
SUCCESS_THRESHOLD_DEFAULT = 0.70
# TEMPORARY TEST CAP:
# Keep image collection target list aligned with current artists extraction cap (5 per gallery).
MAX_ARTISTS_PER_GALLERY_FOR_COLLECT = 80
REQUEST_TIMEOUT_SECONDS = 15
USER_AGENT = "art-pulse-editor/phase1-seed10-artist-image-collect"
REQUEST_RETRY_TOTAL = 2
REQUEST_RETRY_BACKOFF_FACTOR = 0.3
DNS_PROBE_HOST = "example.com"
FAILURE_RETRY_COOLDOWN_SECONDS = 3600
MAX_FAILURE_RETRIES_PER_URL = 3
USE_PLAYWRIGHT_HTML_FETCH = os.getenv("PHASE1_USE_PLAYWRIGHT", "1").strip().lower() not in {
    "0",
    "false",
    "no",
    "off",
}
PLAYWRIGHT_NAV_TIMEOUT_MS = max(5000, REQUEST_TIMEOUT_SECONDS * 1000)

PROJECT_ROOT = Path(__file__).resolve().parent
TRASH_ROOT = PROJECT_ROOT / "_trash"
SKIPPED_GALLERIES_REGISTRY_PATH = PROJECT_ROOT / "data" / "gallery_lists" / "skipped_galleries_registry.csv"

RAW_DIR = Path("data/phase1_seed10/raw")
LOG_DIR = Path("data/phase1_seed10/logs")
DERIVED_DIR = Path("data/phase1_seed10/derived")
IMAGE_ROOT_DIR = Path("data/phase1_seed10/derived/images/artist_works_images")
WORKS_META_FILENAME_TEMPLATE = "artist_works_images_{fair_slug}.jsonl"
WORKS_IMAGE_RANK_WINDOW = 20
ARTIST_MASTER_GLOBAL_PATH = LOG_DIR / "artist_master_global.json"
FAILED_FETCH_LEDGER_FILENAME_TEMPLATE = "failed_fetches_artist_image_collect_{target_year}.json"
MANUAL_SEED_TEXT_MARKERS = (
    "Artist page seed for",
)

_PLAYWRIGHT_MANAGER = None
_PLAYWRIGHT_BROWSER = None
_PLAYWRIGHT_CONTEXT = None

SCHEMA_NAME = "phase1_seed10_artist_image_collect_summary"
SCHEMA_VERSION = "v1"
ARTIFACT_KIND = "phase1_seed10_artist_image_collect_summary"

REJECT_TOKENS = (
    "logo",
    "icon",
    "favicon",
    "sprite",
    "placeholder",
    "loading",
    "spacer",
)

POSITIVE_TOKENS = (
    "artwork",
    "artworks",
    "work",
    "works",
    "painting",
    "sculpture",
    "installation",
    "artist",
)

WORKS_ONLY_REJECT_URL_TOKENS = (
    "/exhibition",
    "/exhibitions",
    "main_image_override",
    "profile",
    "biography",
    "/artist_image/",
    "hero",
    "banner",
    "avatar",
)
WORKS_ONLY_REJECT_EVIDENCE_TOKENS = (
    "profile photo",
    "artist photo",
    "headshot",
    "portrait",
    "hero image",
    "banner image",
)

WORKS_LINK_KEYWORDS = ("work", "works")
WORKS_LINK_EXCLUDE_KEYWORDS = (
    "exhibition",
    "exhibitions",
    "profile",
    "bio",
    "about",
    "news",
    "press",
    "contact",
)
GENERIC_ARTIST_LIST_PATHS = {"/artist", "/artists"}
GENERIC_WORKS_NAV_PATHS = {"/artworks", "/publications", "/projects"}

DISALLOWED_EXTENSIONS = {".svg", ".gif", ".ico"}
CACHED_IMAGE_ALLOWED_EXTENSIONS = {".jpg", ".jpeg"}
CONTENT_TYPE_TO_EXTENSION = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/avif": ".avif",
}
IMAGE_TARGET_SIZE_KB = 100
IMAGE_TARGET_SIZE_BYTES = IMAGE_TARGET_SIZE_KB * 1024
IMAGE_MIN_JPEG_QUALITY = 20
IMAGE_MAX_JPEG_QUALITY = 95
IMAGE_RESIZE_SCALE_STEPS = (1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.25, 0.2)
MIN_IMAGE_WIDTH_PX = 120
MIN_IMAGE_HEIGHT_PX = 120
MIN_IMAGE_PAYLOAD_BYTES = 64
IMAGE_REQUEST_ACCEPT_HEADER = "image/jpeg,image/png,image/*;q=0.9,*/*;q=0.8"

IMG_TAG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
A_TAG_RE = re.compile(r"<a\b[^>]*>", re.IGNORECASE)
GENERIC_IMG_ATTR_TAG_RE = re.compile(
    r"""(?is)<(?P<tag>[a-z0-9:_-]+)\b[^>]*?\b(?P<attr>src|data-src|data-original|data-lazy-src|data-lazy|poster)\s*=\s*(?P<quote>"|')(?P<value>.*?)(?P=quote)[^>]*>"""
)
GENERIC_SRCSET_TAG_RE = re.compile(
    r"""(?is)<(?P<tag>[a-z0-9:_-]+)\b[^>]*?\bsrcset\s*=\s*(?P<quote>"|')(?P<value>.*?)(?P=quote)[^>]*>"""
)
INLINE_IMAGE_URL_RE = re.compile(
    r"""(?is)(?P<quote>"|')(?P<value>(?:https?:)?//[^"'\s>]+?\.(?:jpe?g|png|webp|avif)(?:\?[^"'\s>]*)?|/[^"'\s>]+?\.(?:jpe?g|png|webp|avif)(?:\?[^"'\s>]*)?)(?P=quote)"""
)
LIKELY_IMAGE_URL_EXT_RE = re.compile(r"\.(?:jpe?g|png|webp|avif)(?:$|[?#])", re.IGNORECASE)
ATTR_RE = re.compile(r"""([A-Za-z_:][-A-Za-z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+))""")
FIGCAPTION_RE = re.compile(r"(?is)<figcaption\b[^>]*>(.*?)</figcaption>")
HTML_TAG_RE = re.compile(r"(?is)<[^>]+>")
SCRIPT_STYLE_RE = re.compile(r"(?is)<(script|style)\b[^>]*>.*?</\1>")
YEAR_PATTERN = re.compile(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)")
YEAR_MIN = 1900
YEAR_MAX = datetime.now(timezone.utc).year + 1
YEAR_EVIDENCE_TEXT_MAX_LEN = 120
IMAGE_SCALE_SUFFIX_RE = re.compile(r"-(\d{2,5})x(\d{2,5})(?=\.[a-z0-9]{2,5}$)", re.IGNORECASE)
IMAGE_SCALED_SUFFIX_RE = re.compile(r"-scaled(?=\.[a-z0-9]{2,5}$)", re.IGNORECASE)
CDN_TRANSFORM_SEGMENT_RE = re.compile(r"^(?:[a-z]{1,4}_[^/]+)(?:,[a-z]{1,4}_[^/]+)*$", re.IGNORECASE)
WORK_INFO_MEDIUM_PATTERN = re.compile(
    r"\b(oil on|acrylic on|watercolor on|ink on|bronze|charcoal|mixed media|"
    r"photograph|print|etching|lithograph|ceramic|wood|canvas|paper)\b",
    re.IGNORECASE,
)
WORK_INFO_SIZE_PATTERN = re.compile(r"\b\d{2,4}\s?(cm|mm|in|inch|inches)\b", re.IGNORECASE)
HERO_CONTAINER_TOKENS = ("hero", "header", "profile", "portrait", "headshot", "avatar", "bio", "about")
HERO_PERSON_TOKENS = ("portrait", "headshot", "profile photo", "artist photo", "photo of")

ARTIST_URL_NON_NAME_SEGMENTS = {
    "artist",
    "artists",
    "biography",
    "bio",
    "profile",
    "works",
    "work",
    "overview",
    "news",
    "contact",
}

NON_RETRYABLE_FAILURE_REASON_CODES = {
    "UNSUPPORTED_CONTENT_TYPE",
    "IMAGE_PAYLOAD_TOO_SMALL",
    "IMAGE_PAYLOAD_IS_HTML",
    "IMAGE_PAYLOAD_SIGNATURE_DISALLOWED",
    "IMAGE_DECODE_FAILED",
    "IMAGE_DIMENSIONS_TOO_SMALL",
    "CACHED_EXTENSION_NOT_ALLOWED",
    "CACHED_PAYLOAD_TOO_SMALL",
    "CACHED_IMAGE_DECODE_FAILED",
    "CACHED_DIMENSIONS_TOO_SMALL",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def utc_timestamp_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect artists images for Phase1 seed10 and summarize observed success rate.")
    parser.add_argument("--target-year", type=int, default=TARGET_YEAR_DEFAULT, help=f"default: {TARGET_YEAR_DEFAULT}")
    parser.add_argument(
        "--target-images-per-artist",
        type=int,
        default=TARGET_IMAGES_PER_ARTIST_DEFAULT,
        help=f"default: {TARGET_IMAGES_PER_ARTIST_DEFAULT}",
    )
    parser.add_argument("--only-fair-slug", default="", help="optional filter: only this fair_slug")
    parser.add_argument("--only-gallery-name", default="", help="optional filter: only this gallery_name_en")
    parser.add_argument("--only-source-url", default="", help="optional filter: only this artist source_url")
    parser.add_argument(
        "--force-retry-failed",
        action="store_true",
        help="retry failed URLs without cooldown gating (for testing)",
    )
    parser.add_argument(
        "--clear-failed-ledger",
        choices=("none", "target", "all"),
        default="none",
        help="clear failed URL ledger before run (none|target|all)",
    )
    parser.add_argument("--output-json", default="", help="optional summary output path")
    return parser.parse_args()


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl_rows(path: Path) -> list[dict[str, Any]]:
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


def read_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def compute_page_url_hash(url: str) -> str:
    return hashlib.sha256(normalize_url_for_link_compare(url).encode("utf-8")).hexdigest()


def load_failed_fetches_ledger(path: Path) -> dict[str, dict[str, Any]]:
    payload = read_json(path)
    if not isinstance(payload, dict):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for key, row in payload.items():
        if not isinstance(key, str) or not isinstance(row, dict):
            continue
        fail_hash = str(row.get("fail_hash") or key)
        out[fail_hash] = {
            "fail_hash": fail_hash,
            "kind": str(row.get("kind") or "page"),
            "raw_url": str(row.get("raw_url") or ""),
            "parent_source_url": str(row.get("parent_source_url") or ""),
            "last_error": str(row.get("last_error") or ""),
            "http_status": row.get("http_status"),
            "retry_count": int(row.get("retry_count", 0)),
            "attempt_count": int(row.get("attempt_count", row.get("retry_count", 0))),
            "last_attempt_at": str(row.get("last_attempt_at") or row.get("last_failed_at") or ""),
            "first_failed_at": str(row.get("first_failed_at") or row.get("last_failed_at") or ""),
            "last_failed_at": str(row.get("last_failed_at") or ""),
            "reason_code": str(row.get("reason_code") or "REQUEST_ERROR"),
            "target_year": int(row.get("target_year", TARGET_YEAR_DEFAULT)),
        }
    return out


def parse_utc_datetime(value: str) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def should_skip_failed_url(
    entry: dict[str, Any],
    now: datetime,
    *,
    raw_url: str,
    force_retry_failed: bool,
) -> tuple[bool, str]:
    # In test runs, allow re-evaluation of page URLs to recover from stale failure
    # ledgers while preserving non-retry handling for image payload failures.
    if force_retry_failed:
        kind = str(entry.get("kind") or "").strip().lower()
        if kind == "page":
            return False, ""
    reason_code = str(entry.get("reason_code") or "REQUEST_ERROR")
    if reason_code in NON_RETRYABLE_FAILURE_REASON_CODES:
        return True, "KNOWN_FAILED_URL_NON_RETRYABLE"
    retry_count = int(entry.get("retry_count", 0))
    max_retries = int(entry.get("max_retries", MAX_FAILURE_RETRIES_PER_URL) or MAX_FAILURE_RETRIES_PER_URL)
    last_failed_at = parse_utc_datetime(str(entry.get("last_failed_at") or ""))
    cooldown = timedelta(seconds=max(0, int(entry.get("cooldown_seconds", FAILURE_RETRY_COOLDOWN_SECONDS) or 0)))
    if retry_count >= max_retries:
        if last_failed_at is None:
            return True, "KNOWN_FAILED_URL_MAX_RETRIES"
        if now < last_failed_at + cooldown:
            return True, "KNOWN_FAILED_URL_COOLDOWN"
    if retry_count > 0 and last_failed_at is not None and now < last_failed_at + cooldown:
        return True, "KNOWN_FAILED_URL_COOLDOWN"
    return False, ""


def upsert_failed_fetch(
    ledger: dict[str, dict[str, Any]],
    *,
    kind: str,
    raw_url: str,
    parent_source_url: str | None,
    last_error: str,
    http_status: int | None,
    reason_code: str,
    target_year: int,
) -> dict[str, Any]:
    now = utc_now_iso()
    fail_hash = compute_page_url_hash(raw_url)
    prev = ledger.get(fail_hash, {})
    retry_count = int(prev.get("retry_count", 0)) + 1
    record = {
        "fail_hash": fail_hash,
        "kind": kind,
        "raw_url": raw_url,
        "parent_source_url": parent_source_url or "",
        "last_error": last_error,
        "http_status": http_status,
        "retry_count": retry_count,
        "attempt_count": retry_count,
        "last_attempt_at": now,
        "first_failed_at": str(prev.get("first_failed_at") or now),
        "last_failed_at": now,
        "reason_code": reason_code,
        "target_year": int(target_year),
        "max_retries": MAX_FAILURE_RETRIES_PER_URL,
        "cooldown_seconds": FAILURE_RETRY_COOLDOWN_SECONDS,
    }
    ledger[fail_hash] = record
    return record


def clear_failed_fetch(ledger: dict[str, dict[str, Any]], raw_url: str) -> None:
    ledger.pop(compute_page_url_hash(raw_url), None)


def payload_hash(payload: bytes) -> str:
    if not payload:
        return ""
    return hashlib.sha256(payload).hexdigest()


def payload_hash_from_file(path: Path) -> str:
    try:
        return payload_hash(path.read_bytes())
    except OSError:
        return ""


def reason_code_from_error_text(error_text: str) -> str:
    text = str(error_text or "").lower()
    if "dns_resolution_error" in text or "name or service not known" in text:
        return "DNS_ERROR"
    if "connection_refused" in text:
        return "CONNECTION_REFUSED"
    if "timeout" in text:
        return "TIMEOUT"
    if "content_type_unsupported" in text:
        return "UNSUPPORTED_CONTENT_TYPE"
    if "image_payload_too_small" in text:
        return "IMAGE_PAYLOAD_TOO_SMALL"
    if "image_payload_is_html" in text:
        return "IMAGE_PAYLOAD_IS_HTML"
    if "image_payload_signature_disallowed" in text:
        return "IMAGE_PAYLOAD_SIGNATURE_DISALLOWED"
    if "image_decode_failed" in text:
        return "IMAGE_DECODE_FAILED"
    if "image_dimensions_too_small" in text:
        return "IMAGE_DIMENSIONS_TOO_SMALL"
    if "cached_extension_not_allowed" in text:
        return "CACHED_EXTENSION_NOT_ALLOWED"
    if "cached_payload_too_small" in text:
        return "CACHED_PAYLOAD_TOO_SMALL"
    if "cached_image_decode_failed" in text:
        return "CACHED_IMAGE_DECODE_FAILED"
    if "cached_dimensions_too_small" in text:
        return "CACHED_DIMENSIONS_TOO_SMALL"
    if "html_fetch_failed" in text:
        return "HTML_FETCH_FAILED"
    if "image_fetch_failed" in text:
        return "IMAGE_FETCH_FAILED"
    return "REQUEST_ERROR"


def load_skipped_gallery_registry(path: Path) -> dict[str, dict[str, str]]:
    registry: dict[str, dict[str, str]] = {}
    if not path.exists():
        return registry
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            for row in reader:
                if not row:
                    continue
                if len(row) < 3:
                    continue
                gallery_name = str(row[0] or "").strip()
                if not gallery_name:
                    continue
                exhibition_url = str(row[1] or "").strip()
                artists_url = str(row[2] or "").strip()
                skip_reason = str(row[3] or "").strip() if len(row) >= 4 else ""
                registry[gallery_name.lower()] = {
                    "gallery_name": gallery_name,
                    "exhibition_url": exhibition_url,
                    "artists_url": artists_url,
                    "skip_reason": skip_reason,
                }
    except OSError:
        return {}
    return registry


def build_artist_id(row: dict[str, Any]) -> str:
    text_hash = str(row.get("text_hash") or "").strip()
    if text_hash:
        return text_hash
    source_url = str(row.get("source_url") or "").strip()
    return hashlib.sha256(source_url.encode("utf-8")).hexdigest()


def load_artist_targets(target_year: int, *, only_source_url: str = "") -> list[dict[str, Any]]:
    grouped_rows: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    targets: list[dict[str, Any]] = []
    source_filter = str(only_source_url or "").strip()

    def _is_listing_url(url: str) -> bool:
        path = (urlparse(url).path or "").lower().rstrip("/")
        if not path:
            return False
        return any(path.endswith(pattern.rstrip("/")) for pattern in ARTIST_LIST_PATH_PATTERNS)

    def _is_manual_seed_row(row: dict[str, Any]) -> bool:
        text = str(row.get("text") or "")
        return any(marker in text for marker in MANUAL_SEED_TEXT_MARKERS)

    for raw_path in sorted(RAW_DIR.glob(f"artists_*_{target_year}.jsonl")):
        rows = read_jsonl_rows(raw_path)
        fair_slug = str(raw_path.name.replace(f"artists_", "").replace(f"_{target_year}.jsonl", ""))
        for row in rows:
            if _is_manual_seed_row(row):
                continue
            source_url = str(row.get("source_url") or "").strip()
            if not source_url:
                continue
            key = (
                str(row.get("fair_slug") or fair_slug),
                str(row.get("gallery_name_en") or ""),
            )
            grouped_rows[key].append(
                {
                    "fair_slug": key[0],
                    "gallery_name_en": key[1],
                    "headline_ja": str(row.get("headline_ja") or ""),
                    "source_url": source_url,
                    "row": row,
                }
            )

    seen_target_keys: set[tuple[str, str]] = set()
    for (_fair_slug, _gallery_name_en), rows in grouped_rows.items():
        has_detail_row = any(not _is_listing_url(str(item.get("source_url") or "")) for item in rows)
        added_for_gallery = 0
        for item in rows:
            if added_for_gallery >= MAX_ARTISTS_PER_GALLERY_FOR_COLLECT:
                break
            source_url = str(item.get("source_url") or "").strip()
            if not source_url:
                continue
            if source_filter and source_url != source_filter:
                continue
            if has_detail_row and _is_listing_url(source_url) and source_url != source_filter:
                continue
            row = item.get("row") or {}
            artist_name_en = str(row.get("artist_name_en") or "").strip() or build_artist_name_en_from_source_url(source_url)
            artist_name_key = str(row.get("artist_name_key") or "").strip() or build_artist_name_key(artist_name_en, source_url)
            artist_id = build_artist_id(row)
            dedupe_key = (artist_id, source_url)
            if dedupe_key in seen_target_keys:
                continue
            seen_target_keys.add(dedupe_key)
            targets.append(
                {
                    "artist_id": artist_id,
                    "fair_slug": str(item.get("fair_slug") or ""),
                    "gallery_name_en": str(item.get("gallery_name_en") or ""),
                    "headline_ja": str(item.get("headline_ja") or ""),
                    "artist_name_en": artist_name_en,
                    "artist_name_key": artist_name_key,
                    "source_url": source_url,
                }
            )
            added_for_gallery += 1
    return targets


def collect_seed_supply_by_gallery(target_year: int) -> list[dict[str, Any]]:
    grouped_rows: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

    def _is_manual_seed_row(row: dict[str, Any]) -> bool:
        text = str(row.get("text") or "")
        return any(marker in text for marker in MANUAL_SEED_TEXT_MARKERS)

    for raw_path in sorted(RAW_DIR.glob(f"artists_*_{target_year}.jsonl")):
        rows = read_jsonl_rows(raw_path)
        fair_slug = str(raw_path.name.replace("artists_", "").replace(f"_{target_year}.jsonl", ""))
        for row in rows:
            if _is_manual_seed_row(row):
                continue
            source_url = str(row.get("source_url") or "").strip()
            if not source_url:
                continue
            key = (
                str(row.get("fair_slug") or fair_slug),
                str(row.get("gallery_name_en") or ""),
            )
            grouped_rows[key].append(row)

    snapshots: list[dict[str, Any]] = []
    for (fair_slug, gallery_name_en), rows in sorted(grouped_rows.items()):
        raw_total = len(rows)
        detail_total = 0
        for row in rows:
            source_url = str(row.get("source_url") or "").strip()
            if source_url and not looks_like_artist_listing_url(source_url):
                detail_total += 1
        snapshots.append(
            {
                "fair_slug": fair_slug,
                "gallery_name_en": gallery_name_en,
                "raw_seed_total": raw_total,
                "detail_seed_total": detail_total,
                "configured_cap": MAX_ARTISTS_PER_GALLERY_FOR_COLLECT,
                "supply_under_cap": bool(detail_total < MAX_ARTISTS_PER_GALLERY_FOR_COLLECT),
            }
        )
    return snapshots


def normalize_domain(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host or "unknown"


def slugify_token(value: str, fallback: str = "unknown", max_len: int = 80) -> str:
    lowered = (value or "").strip().lower()
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    if not lowered:
        return fallback
    return lowered[:max_len]


def fair_slug_to_meta_token(fair_slug: str) -> str:
    text = (fair_slug or "").strip().lower().replace("-", "_")
    text = re.sub(r"[^a-z0-9_]+", "_", text).strip("_")
    return text or "unknown_fair"


def works_meta_path_for_fair(fair_slug: str) -> Path:
    token = fair_slug_to_meta_token(fair_slug)
    return DERIVED_DIR / WORKS_META_FILENAME_TEMPLATE.format(fair_slug=token)


def build_artist_name_en_from_source_url(source_url: str) -> str:
    slug = artist_slug_from_source_url(source_url)
    if slug == "artist":
        return "Unknown Artist"
    return " ".join(part.capitalize() for part in slug.split("-") if part)


def build_artist_name_key(artist_name_en: str, source_url: str) -> str:
    normalized_name = re.sub(r"\s+", " ", str(artist_name_en or "").strip().lower())
    if normalized_name:
        seed = f"artist_name_en:{normalized_name}"
    else:
        seed = f"source_url:{normalize_url_for_link_compare(source_url)}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def build_artist_identity_key(artist_name_key: str, artist_name_en: str, source_url: str) -> str:
    normalized_key = str(artist_name_key or "").strip().lower()
    if normalized_key:
        return normalized_key
    return build_artist_name_key(artist_name_en, source_url).lower()


def _build_artist_master_entry(
    *,
    identity_key: str,
    artist_name_key: str,
    artist_name_en: str,
    source_url: str,
    fair_slug: str,
    gallery_name_en: str,
    seen_at: str,
) -> dict[str, Any]:
    return {
        "artist_identity_key": identity_key,
        "artist_name_key": str(artist_name_key or "").strip(),
        "artist_name_en": str(artist_name_en or "").strip(),
        "first_source_url": str(source_url or "").strip(),
        "first_fair_slug": str(fair_slug or "").strip(),
        "first_gallery_name_en": str(gallery_name_en or "").strip(),
        "first_seen_at": str(seen_at or "").strip(),
        "updated_at": str(seen_at or "").strip(),
    }


def load_artist_master_global(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}
    records = payload.get("records")
    if not isinstance(records, list):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for item in records:
        if not isinstance(item, dict):
            continue
        key = str(item.get("artist_identity_key") or "").strip().lower()
        if not key:
            continue
        out[key] = item
    return out


def merge_artist_master_from_works_meta(master: dict[str, dict[str, Any]]) -> None:
    for path in sorted(DERIVED_DIR.glob("artist_works_images_*.jsonl")):
        rows = read_jsonl_rows(path)
        for row in rows:
            if not isinstance(row, dict):
                continue
            source_url = str(row.get("source_url") or "").strip()
            if not source_url:
                continue
            artist_name_en = str(row.get("artist_name_en") or "").strip() or build_artist_name_en_from_source_url(source_url)
            artist_name_key = str(row.get("artist_name_key") or "").strip() or build_artist_name_key(artist_name_en, source_url)
            identity_key = build_artist_identity_key(artist_name_key, artist_name_en, source_url)
            if identity_key in master:
                continue
            master[identity_key] = _build_artist_master_entry(
                identity_key=identity_key,
                artist_name_key=artist_name_key,
                artist_name_en=artist_name_en,
                source_url=source_url,
                fair_slug=str(row.get("fair_slug") or ""),
                gallery_name_en=str(row.get("gallery_name_en") or ""),
                seen_at=str(row.get("extracted_at") or ""),
            )


def write_artist_master_global(path: Path, master: dict[str, dict[str, Any]]) -> None:
    records = sorted(master.values(), key=lambda x: str(x.get("artist_identity_key") or ""))
    payload = {
        "schema_name": "artist_master_global",
        "schema_version": "v1",
        "generated_at": utc_now_iso(),
        "records": records,
    }
    write_json(path, payload)


def image_url_hash(url: str) -> str:
    normalized = normalize_image_url_for_dedupe(url)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def local_path_to_r2_key(path: Path) -> str:
    try:
        rel = path.resolve().relative_to(Path.cwd().resolve())
        return rel.as_posix()
    except ValueError:
        return path.as_posix()


def parse_image_index_from_filename(path: Path) -> int:
    match = re.search(r"__img_(\d+)\.[A-Za-z0-9]+$", path.name)
    if not match:
        return 0
    try:
        return int(match.group(1))
    except ValueError:
        return 0


def artist_slug_from_source_url(source_url: str) -> str:
    parsed = urlparse(source_url)
    path = (parsed.path or "").strip("/")
    if not path:
        return "artist"
    parts = [part for part in path.split("/") if part]
    if not parts:
        return "artist"

    candidate = ""
    for part in reversed(parts):
        lowered = part.lower()
        if lowered in ARTIST_URL_NON_NAME_SEGMENTS:
            continue
        if lowered.isdigit():
            continue
        candidate = part
        break
    if not candidate:
        candidate = parts[-1]

    match = re.match(r"^\d+[-_]+(.+)$", candidate.strip())
    if match:
        candidate = match.group(1)
    return slugify_token(candidate, fallback="artist")


def artist_match_tokens_from_source_url(source_url: str) -> list[str]:
    slug = artist_slug_from_source_url(source_url)
    tokens = [token for token in slug.split("-") if len(token) >= 3]
    return tokens


def compact_alnum_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def candidate_matches_artist(candidate: dict[str, Any], source_url: str, page_url: str) -> bool:
    artist_slug = artist_slug_from_source_url(source_url)
    if artist_slug == "artist":
        return True

    artist_phrase = artist_slug.replace("-", " ").strip()
    tokens = artist_match_tokens_from_source_url(source_url)
    candidate_url_text = str(candidate.get("url") or "").lower()
    evidence_text_raw = str(candidate.get("evidence_text") or "")
    evidence_text = evidence_text_raw.lower()
    haystack = " ".join(
        [
            candidate_url_text,
            evidence_text,
        ]
    )

    if artist_phrase and artist_phrase in haystack:
        return True
    # Generic fallback: some pages collapse names like "gan-chin-lee" into "ganchinlee".
    # Compare compacted alnum sequences before token-level checks.
    artist_compact = compact_alnum_text(artist_slug)
    if artist_compact:
        haystack_compact = compact_alnum_text(haystack)
        if artist_compact in haystack_compact:
            return True

    token_matches = 0
    matched_tokens: set[str] = set()
    for token in tokens:
        if re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", haystack):
            token_matches += 1
            matched_tokens.add(token)
    if token_matches == 0 and has_foreign_person_name_text(evidence_text_raw, tokens):
        return False

    if len(tokens) >= 2:
        if token_matches >= 2:
            return True
        # Generic relaxation for artist-detail pages:
        # allow surname-only hits when surrounding context still looks like artwork.
        source_path = (urlparse(source_url).path or "").lower().rstrip("/")
        page_path = (urlparse(page_url).path or "").lower().rstrip("/")
        is_artist_detail_page = (
            source_path.startswith("/artists/")
            and page_path.startswith("/artists/")
            and page_path == source_path
        )
        is_artist_scoped_page = source_path.startswith("/artists/") and (
            page_path == source_path or page_path.startswith(f"{source_path}/")
        )
        surname_token = tokens[-1]
        if (
            is_artist_detail_page
            and surname_token in matched_tokens
            and has_work_info_signal(
                candidate_year=normalize_candidate_year(candidate.get("year")),
                evidence_text=evidence_text,
            )
        ):
            return True
        # Generic relaxation for artist-scoped pages:
        # If the current page belongs to the same artist subtree,
        # allow candidates that carry basic artwork/media signals.
        if is_artist_scoped_page:
            if has_work_info_signal(
                candidate_year=normalize_candidate_year(candidate.get("year")),
                evidence_text=evidence_text,
            ):
                return True
        return False
    if len(tokens) == 1:
        if token_matches >= 1:
            return True
        source_path = (urlparse(source_url).path or "").lower().rstrip("/")
        page_path = (urlparse(page_url).path or "").lower().rstrip("/")
        if source_path.startswith("/artists/") and page_path.startswith(source_path):
            return has_work_info_signal(
                candidate_year=normalize_candidate_year(candidate.get("year")),
                evidence_text=evidence_text,
            )
        return False
    return True


def candidate_matches_artist_lenient_scoped(candidate: dict[str, Any], source_url: str, page_url: str) -> bool:
    source_path = (urlparse(source_url).path or "").lower().rstrip("/")
    page_path = (urlparse(page_url).path or "").lower().rstrip("/")
    if not source_path.startswith("/artists/"):
        return False
    if not page_path.startswith(source_path):
        return False

    candidate_url = str(candidate.get("url") or "")
    evidence_text = str(candidate.get("evidence_text") or "")
    artist_tokens = artist_match_tokens_from_source_url(source_url)
    if has_foreign_person_slug(candidate_url, artist_tokens):
        return False
    if has_foreign_person_name_text(evidence_text, artist_tokens):
        return False

    attrs_raw = candidate.get("attrs")
    attrs = attrs_raw if isinstance(attrs_raw, dict) else {}
    parent_tag = str(candidate.get("parent_tag") or "")
    if has_strong_hero_signal(candidate_url, attrs, parent_tag):
        return False
    return True


def candidate_violates_works_only(candidate: dict[str, Any]) -> bool:
    url_text = str(candidate.get("url") or "").lower()
    evidence_text = str(candidate.get("evidence_text") or "").lower()
    if any(token in url_text for token in WORKS_ONLY_REJECT_URL_TOKENS):
        return True
    if any(token in evidence_text for token in WORKS_ONLY_REJECT_EVIDENCE_TOKENS):
        return True
    return False


def normalize_url_for_link_compare(url: str) -> str:
    return shared_normalize_url_for_link_compare(url)


def normalize_image_url_for_dedupe(url: str) -> str:
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path or ""
    # Collapse CDN transform prefixes like:
    # /w_600,c_limit,f_auto/.../image.jpg -> /.../image.jpg
    parts = path.split("/")
    if len(parts) >= 3:
        transform_seg = parts[1]
        if transform_seg and CDN_TRANSFORM_SEGMENT_RE.match(transform_seg):
            path = "/" + "/".join(parts[2:])
    # Collapse Cargo-style transform prefixes:
    # /w/450/i/<hash>/image.jpg -> /i/<hash>/image.jpg
    # /t/original/i/<hash>/image.jpg -> /i/<hash>/image.jpg
    parts = path.split("/")
    while len(parts) >= 5:
        seg1 = (parts[1] or "").lower()
        seg2 = (parts[2] or "").lower()
        if seg1 in {"w", "h"} and seg2.isdigit():
            path = "/" + "/".join(parts[3:])
            parts = path.split("/")
            continue
        if seg1 == "t" and seg2 in {"original", "optimized", "thumbnail"}:
            path = "/" + "/".join(parts[3:])
            parts = path.split("/")
            continue
        break
    # Collapse common CMS scaled variants:
    # image-1024x683.jpg / image-2048x1365.jpg -> image.jpg
    path = IMAGE_SCALE_SUFFIX_RE.sub("", path)
    # Collapse WordPress-style "scaled" variants:
    # image-scaled.jpg -> image.jpg
    path = IMAGE_SCALED_SUFFIX_RE.sub("", path)
    return f"{scheme}://{netloc}{path}".rstrip("/")


def is_artist_detail_like_path(path: str) -> bool:
    normalized = str(path or "").strip().lower().rstrip("/")
    if not normalized:
        return False
    if normalized in GENERIC_ARTIST_LIST_PATHS:
        return False
    return normalized.startswith("/artists/") or normalized.startswith("/artist/")


def is_redirected_to_generic_listing(request_url: str, final_url: str) -> bool:
    req_path = (urlparse(request_url).path or "").lower().rstrip("/")
    fin_path = (urlparse(final_url).path or "").lower().rstrip("/")
    if req_path == fin_path:
        return False
    if not is_artist_detail_like_path(req_path):
        return False
    return fin_path in GENERIC_ARTIST_LIST_PATHS


def looks_like_artist_listing_url(url: str) -> bool:
    return shared_looks_like_artist_listing_url(url)


def looks_like_artist_detail_url(candidate_url: str, list_page_url: str, anchor_text: str = "") -> bool:
    return shared_looks_like_artist_detail_url(
        candidate_url=candidate_url,
        list_page_url=list_page_url,
        anchor_text=anchor_text,
        same_domain_required=True,
    )


def can_resolve_hostname(hostname: str) -> tuple[bool, str]:
    try:
        socket.gethostbyname(hostname)
        return True, ""
    except OSError as exc:
        return False, str(exc)


def build_url_fetch_candidates(url: str) -> list[str]:
    normalized = str(url or "").strip()
    if not normalized:
        return []

    parsed = urlparse(normalized)
    host = (parsed.hostname or "").strip()
    if not host:
        return [normalized]

    variants = [normalized]

    if host.startswith("www."):
        alt_host = host[4:]
    else:
        alt_host = f"www.{host}"

    if alt_host and alt_host != host:
        alt_parsed = parsed._replace(netloc=parsed.netloc.replace(host, alt_host, 1))
        alt_url = alt_parsed.geturl()
        if alt_url not in variants:
            variants.append(alt_url)

    return variants


def summarize_request_error(prefix: str, url: str, exc: Exception) -> str:
    host = normalize_domain(url)
    message = str(exc)
    lowered = message.lower()
    if "failed to resolve" in lowered or "name or service not known" in lowered or "temporary failure in name resolution" in lowered:
        return f"{prefix}:dns_resolution_error:{host}"
    if "connection refused" in lowered:
        return f"{prefix}:connection_refused:{host}"
    if "timed out" in lowered:
        return f"{prefix}:timeout:{host}"
    return f"{prefix}:{host}:{message}"


def _playwright_enabled() -> bool:
    return bool(USE_PLAYWRIGHT_HTML_FETCH and sync_playwright is not None)


def _ensure_playwright_context():
    global _PLAYWRIGHT_MANAGER, _PLAYWRIGHT_BROWSER, _PLAYWRIGHT_CONTEXT
    if _PLAYWRIGHT_CONTEXT is not None:
        return _PLAYWRIGHT_CONTEXT
    if not _playwright_enabled():
        return None
    try:
        _PLAYWRIGHT_MANAGER = sync_playwright().start()
        _PLAYWRIGHT_BROWSER = _PLAYWRIGHT_MANAGER.chromium.launch(headless=True)
        _PLAYWRIGHT_CONTEXT = _PLAYWRIGHT_BROWSER.new_context(user_agent=USER_AGENT)
        return _PLAYWRIGHT_CONTEXT
    except Exception:
        _PLAYWRIGHT_CONTEXT = None
        if _PLAYWRIGHT_BROWSER is not None:
            try:
                _PLAYWRIGHT_BROWSER.close()
            except Exception:
                pass
            _PLAYWRIGHT_BROWSER = None
        if _PLAYWRIGHT_MANAGER is not None:
            try:
                _PLAYWRIGHT_MANAGER.stop()
            except Exception:
                pass
            _PLAYWRIGHT_MANAGER = None
        return None


def fetch_html_with_playwright(url: str) -> tuple[bool, str, str]:
    context = _ensure_playwright_context()
    if context is None:
        return False, "", "html_fetch_failed:playwright_unavailable"
    page = None
    try:
        page = context.new_page()
        response = page.goto(url, wait_until="domcontentloaded", timeout=PLAYWRIGHT_NAV_TIMEOUT_MS)
        status_code = response.status if response is not None else None
        final_url = page.url or url
        if is_redirected_to_generic_listing(url, final_url):
            return (
                False,
                "",
                "html_redirected_to_generic_listing:"
                f"{normalize_domain(url)}:{urlparse(final_url).path or '/'}",
            )
        content_type = ""
        if response is not None:
            headers = response.headers or {}
            content_type = str(headers.get("content-type") or "").lower()
        if status_code is not None and status_code >= 400:
            return False, "", f"html_fetch_failed:{normalize_domain(final_url)}:PLAYWRIGHT_HTTP_{status_code}"
        if content_type and "text/html" not in content_type and "application/xhtml+xml" not in content_type:
            return (
                False,
                "",
                f"html_content_type_unsupported:{normalize_domain(final_url)}:{content_type or 'unknown'}",
            )
        return True, page.content(), ""
    except PlaywrightTimeoutError as exc:
        return False, "", f"html_fetch_failed:timeout:{normalize_domain(url)}:{exc}"
    except PlaywrightError as exc:
        return False, "", summarize_request_error("html_fetch_failed", url, exc)
    except Exception as exc:  # noqa: BLE001
        return False, "", summarize_request_error("html_fetch_failed", url, exc)
    finally:
        if page is not None:
            try:
                page.close()
            except Exception:
                pass


def parse_srcset_best(srcset: str) -> str:
    best_url = ""
    best_width = -1
    for chunk in srcset.split(","):
        item = chunk.strip()
        if not item:
            continue
        parts = item.split()
        candidate = parts[0].strip()
        width = 0
        if len(parts) > 1 and parts[1].endswith("w"):
            try:
                width = int(parts[1][:-1])
            except ValueError:
                width = 0
        if width >= best_width:
            best_url = candidate
            best_width = width
    return best_url


def parse_img_attrs(tag_html: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for match in ATTR_RE.finditer(tag_html):
        key = (match.group(1) or "").strip().lower()
        value = match.group(2) or match.group(3) or match.group(4) or ""
        if key:
            attrs[key] = value.strip()
    return attrs


def normalize_candidate_url_value(raw_value: str) -> str:
    value = html_lib.unescape(str(raw_value or "").strip())
    if not value:
        return ""
    # Some script payloads escape URL slashes (e.g. https:\/\/...).
    return value.replace("\\/", "/")


def looks_like_image_url_reference(raw_value: str) -> bool:
    value = normalize_candidate_url_value(raw_value)
    if not value:
        return False
    if value.lower().startswith("data:"):
        return False
    if LIKELY_IMAGE_URL_EXT_RE.search(value):
        return True
    parsed = urlparse(urljoin("https://placeholder.local", value))
    path = (parsed.path or "").lower()
    # Some CDNs expose image payloads under "/i/<hash>/..." without <img>.
    if "/i/" in path and not path.endswith((".js", ".css", ".json")):
        return True
    return False


def html_fragment_to_text(fragment: str) -> str:
    if not fragment:
        return ""
    no_script = SCRIPT_STYLE_RE.sub(" ", fragment)
    no_tags = HTML_TAG_RE.sub(" ", no_script)
    text = html_lib.unescape(no_tags)
    return re.sub(r"\s+", " ", text).strip()


def extract_years_from_text(text: str) -> list[int]:
    years: list[int] = []
    seen: set[int] = set()
    for match in YEAR_PATTERN.finditer(text):
        start = match.start(1)
        end = match.end(1)
        prev_char = text[start - 1] if start > 0 else ""
        next_char = text[end] if end < len(text) else ""
        next_next_char = text[end + 1] if end + 1 < len(text) else ""
        prev_prev_char = text[start - 2] if start - 2 >= 0 else ""
        # Ignore dimension-like tokens such as 4000x2667 / 800x800.
        if next_char in {"x", "X", "×"} and next_next_char.isdigit():
            continue
        if prev_char in {"x", "X", "×"} and prev_prev_char.isdigit():
            continue
        # Ignore CSS-like units (e.g. 2024px) and obvious file-dimension patterns.
        if text[end : min(len(text), end + 2)].lower() == "px":
            continue
        try:
            year = int(match.group(1))
        except ValueError:
            continue
        if year < YEAR_MIN or year > YEAR_MAX:
            continue
        if year in seen:
            continue
        seen.add(year)
        years.append(year)
    return years


def normalize_candidate_year(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        year = value
    elif isinstance(value, str) and value.strip().isdigit():
        year = int(value.strip())
    else:
        return None
    if year < YEAR_MIN or year > YEAR_MAX:
        return None
    return year


def normalize_year_candidates(raw: Any, max_items: int = 5) -> list[int]:
    years: list[int] = []
    if not isinstance(raw, list):
        return years
    for item in raw:
        year = normalize_candidate_year(item)
        if year is None or year in years:
            continue
        years.append(year)
        if len(years) >= max_items:
            break
    return years


def shorten_text(text: str, max_len: int = YEAR_EVIDENCE_TEXT_MAX_LEN) -> str:
    normalized = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(normalized) <= max_len:
        return normalized
    if max_len <= 3:
        return normalized[:max_len]
    return normalized[: max_len - 3].rstrip() + "..."


def sanitize_evidence_text(text: str) -> str:
    cleaned = str(text or "")
    # Remove HTML-like attribute fragments that can leak from malformed snippets.
    cleaned = re.sub(r"""\b[A-Za-z_:-][\w:.-]*\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+)""", " ", cleaned)
    # Drop common broken entity fragments and tag residue.
    cleaned = re.sub(r"(?:#\d{2,4};|&(?:nbsp|quot|amp|lt|gt);)", " ", cleaned)
    cleaned = re.sub(r"[<>\"`]+", " ", cleaned)
    cleaned = re.sub(r"[|]{2,}", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def build_year_array_from_evidence(items: list[dict[str, Any]], max_items: int = 5) -> list[int | None]:
    result: list[int | None] = []
    for item in items[:max_items]:
        if not isinstance(item, dict):
            continue
        result.append(normalize_candidate_year(item.get("year")))
    return result


def is_year_desc_with_unknown_tail(years: list[int | None]) -> bool:
    seen_unknown = False
    prev_known: int | None = None
    for year in years:
        if year is None:
            seen_unknown = True
            continue
        if seen_unknown:
            return False
        if prev_known is not None and year > prev_known:
            return False
        prev_known = year
    return True


def format_years_for_note(years: list[int | None]) -> str:
    if not years:
        return "none"
    return ",".join(str(y) if y is not None else "unknown" for y in years)


def has_work_info_signal(*, candidate_year: int | None, evidence_text: str) -> bool:
    if candidate_year is not None:
        return True
    text = str(evidence_text or "")
    if WORK_INFO_MEDIUM_PATTERN.search(text):
        return True
    if WORK_INFO_SIZE_PATTERN.search(text):
        return True
    return False


PERSON_SLUG_RE = re.compile(r"\b([a-z]{3,12}-[a-z]{3,12}(?:-[a-z]{3,12})?)\b", re.IGNORECASE)
PERSON_NAME_TEXT_RE = re.compile(
    r"\b([A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ'’.-]{2,}(?:\s+[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ'’.-]{2,}){1,3})\b"
)


def has_foreign_person_slug(url_text: str, artist_tokens: list[str]) -> bool:
    tokens = {t.lower() for t in artist_tokens if t}
    if not tokens:
        return False
    for match in PERSON_SLUG_RE.finditer(str(url_text or "").lower()):
        slug = str(match.group(1) or "")
        parts = [p for p in slug.split("-") if p]
        if len(parts) < 2:
            continue
        if any(part in tokens for part in parts):
            continue
        return True
    return False


def has_foreign_person_name_text(text: str, artist_tokens: list[str]) -> bool:
    tokens = {t.lower() for t in artist_tokens if t}
    if not tokens:
        return False
    for match in PERSON_NAME_TEXT_RE.finditer(str(text or "")):
        name_text = str(match.group(1) or "").strip()
        if not name_text:
            continue
        name_tokens = [slugify_token(tok, fallback="") for tok in re.split(r"\s+", name_text) if tok]
        name_tokens = [tok for tok in name_tokens if len(tok) >= 3]
        if len(name_tokens) < 2:
            continue
        if any(tok in tokens for tok in name_tokens):
            continue
        return True
    return False


def has_strong_hero_signal(candidate_url: str, attrs: dict[str, str], parent_name: str) -> bool:
    url_lower = candidate_url.lower()
    if any(token in url_lower for token in ("portrait", "headshot", "avatar", "profile-photo", "/profile/", "/bio/")):
        return True

    attr_text = " ".join(
        [
            str(attrs.get("class") or "").lower(),
            str(attrs.get("id") or "").lower(),
            str(attrs.get("aria-label") or "").lower(),
            str(attrs.get("title") or "").lower(),
            str(parent_name or "").lower(),
        ]
    )
    if any(token in attr_text for token in HERO_CONTAINER_TOKENS):
        return True

    alt_text = str(attrs.get("alt") or "").lower()
    if any(token in alt_text for token in HERO_PERSON_TOKENS):
        return True
    return False


def sort_candidates_for_selection(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not candidates:
        return []
    has_known_year = any(normalize_candidate_year(item.get("year")) is not None for item in candidates)
    if has_known_year:
        return sorted(
            candidates,
            key=lambda item: (
                normalize_candidate_year(item.get("year")) or -1,
                int(item.get("score") or 0),
                -int(item.get("page_order") or 0),
            ),
            reverse=True,
        )
    return sorted(candidates, key=lambda item: int(item.get("page_order") or 0))


def normalize_hash_list(values: Any, *, max_items: int | None = None) -> list[str]:
    hashes: list[str] = []
    if not isinstance(values, list):
        return hashes
    for value in values:
        token = str(value or "").strip()
        if not token or token in hashes:
            continue
        hashes.append(token)
        if max_items is not None and len(hashes) >= max_items:
            break
    return hashes


def normalize_year_list(values: Any) -> list[int]:
    years: list[int] = []
    if not isinstance(values, list):
        return years
    for value in values:
        year = normalize_candidate_year(value)
        years.append(year or 0)
    return years


def collect_img_year_context(page_html: str, match: re.Match[str], attrs: dict[str, str]) -> str:
    fragments: list[str] = []
    for key in ("alt", "title", "aria-label", "data-caption", "data-title"):
        value = str(attrs.get(key) or "").strip()
        if value:
            fragments.append(value)

    context_pad = 320
    context_start = max(0, match.start() - context_pad)
    context_end = min(len(page_html), match.end() + context_pad)
    fragments.append(page_html[context_start:context_end])

    fig_start = page_html.rfind("<figure", max(0, match.start() - 4000), match.start() + 1)
    if fig_start != -1:
        fig_end_limit = min(len(page_html), match.end() + 4000)
        fig_end = page_html.find("</figure>", match.end(), fig_end_limit)
        if fig_end != -1:
            fig_end = min(len(page_html), fig_end + len("</figure>"))
            if fig_start <= match.start() <= fig_end:
                fragments.append(page_html[fig_start:fig_end])

    caption_window = page_html[max(0, match.start() - 1600) : min(len(page_html), match.end() + 1600)]
    for cap_match in FIGCAPTION_RE.finditer(caption_window):
        caption_html = cap_match.group(1)
        if caption_html:
            fragments.append(caption_html)

    return html_fragment_to_text(" ".join(fragments))


def extract_candidate_year_from_img(
    page_html: str, match: re.Match[str], attrs: dict[str, str]
) -> tuple[int | None, list[int], str]:
    context_text = collect_img_year_context(page_html, match, attrs)
    evidence_text = shorten_text(sanitize_evidence_text(context_text), YEAR_EVIDENCE_TEXT_MAX_LEN)
    years = extract_years_from_text(context_text)
    if not years:
        return None, [], evidence_text
    # Latest year takes precedence for sorting works-image candidates.
    return max(years), sorted(years, reverse=True), evidence_text


def extract_candidate_year_from_context_window(
    page_html: str,
    start: int,
    end: int,
    attrs: dict[str, str] | None = None,
) -> tuple[int | None, list[int], str]:
    fragments: list[str] = []
    attrs = attrs or {}
    for key in ("alt", "title", "aria-label", "data-caption", "data-title"):
        value = str(attrs.get(key) or "").strip()
        if value:
            fragments.append(value)
    context_pad = 320
    context_start = max(0, int(start) - context_pad)
    context_end = min(len(page_html), int(end) + context_pad)
    fragments.append(page_html[context_start:context_end])

    context_text = html_fragment_to_text(" ".join(fragments))
    evidence_text = shorten_text(sanitize_evidence_text(context_text), YEAR_EVIDENCE_TEXT_MAX_LEN)
    years = extract_years_from_text(context_text)
    if not years:
        return None, [], evidence_text
    return max(years), sorted(years, reverse=True), evidence_text


def guess_parent_tag_from_index(page_html: str, index: int) -> str:
    if not page_html:
        return ""
    lt = page_html.rfind("<", 0, max(0, index))
    if lt == -1:
        return ""
    gt = page_html.rfind(">", 0, max(0, index))
    if gt > lt:
        return ""
    probe = page_html[lt : min(len(page_html), lt + 64)]
    match = re.match(r"<\s*([A-Za-z0-9:_-]+)", probe)
    if not match:
        return ""
    return str(match.group(1) or "").strip().lower()


def extract_artist_detail_urls(list_page_url: str, html: str, max_links: int = 80) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()
    listing_context = looks_like_artist_listing_url(list_page_url)
    for match in A_TAG_RE.finditer(html):
        tag_html = match.group(0)
        attrs = parse_img_attrs(tag_html)
        href = str(attrs.get("href") or "").strip()
        if not href:
            continue
        if href.startswith(("mailto:", "tel:", "javascript:")):
            continue
        absolute_url = urljoin(list_page_url, href)
        parsed = urlparse(absolute_url)
        if parsed.scheme not in {"http", "https"}:
            continue

        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")
        if parsed.query:
            normalized = f"{normalized}?{parsed.query}"
        if normalized in seen:
            continue

        target = " ".join(
            [
                absolute_url.lower(),
                str(attrs.get("alt") or "").lower(),
                str(attrs.get("title") or "").lower(),
                str(attrs.get("aria-label") or "").lower(),
                str(attrs.get("class") or "").lower(),
            ]
        )
        if not listing_context and not any(keyword in target for keyword in ARTIST_LINK_KEYWORDS):
            continue
        anchor_text = " ".join(
            [
                str(attrs.get("title") or ""),
                str(attrs.get("aria-label") or ""),
                str(attrs.get("alt") or ""),
            ]
        ).strip()
        if not looks_like_artist_detail_url(absolute_url, list_page_url, anchor_text):
            continue
        seen.add(normalized)
        candidates.append(normalized)
        if len(candidates) >= max_links:
            break
    return candidates


def extract_works_candidate_urls(detail_url: str, detail_html: str, max_links: int = 12) -> list[str]:
    scoped_candidates: list[str] = []
    fallback_candidates: list[str] = []
    seen: set[str] = set()

    def _append(url: str, *, artist_scoped: bool) -> None:
        normalized = normalize_url_for_link_compare(url)
        if not normalized or normalized in seen:
            return
        seen.add(normalized)
        if artist_scoped:
            scoped_candidates.append(url)
        else:
            fallback_candidates.append(url)

    parsed_detail = urlparse(detail_url)
    detail_path = (parsed_detail.path or "").rstrip("/")
    if not detail_path.endswith("/works"):
        works_url = parsed_detail._replace(path=f"{detail_path}/works").geturl()
        _append(works_url, artist_scoped=True)
    else:
        _append(detail_url, artist_scoped=True)

    for match in A_TAG_RE.finditer(detail_html):
        tag_html = match.group(0)
        attrs = parse_img_attrs(tag_html)
        href = str(attrs.get("href") or "").strip()
        if not href or href.startswith(("mailto:", "tel:", "javascript:")):
            continue
        absolute_url = urljoin(detail_url, href)
        parsed = urlparse(absolute_url)
        if parsed.scheme not in {"http", "https"}:
            continue
        if normalize_domain(absolute_url) != normalize_domain(detail_url):
            continue
        candidate_path = (parsed.path or "").lower().rstrip("/")
        if candidate_path in GENERIC_ARTIST_LIST_PATHS:
            continue
        detail_path_lower = detail_path.lower().rstrip("/")
        is_artist_scoped = bool(detail_path_lower and candidate_path.startswith(detail_path_lower))
        if candidate_path in GENERIC_WORKS_NAV_PATHS and not is_artist_scoped:
            continue

        target = " ".join(
            [
                absolute_url.lower(),
                str(attrs.get("title") or "").lower(),
                str(attrs.get("aria-label") or "").lower(),
                str(attrs.get("class") or "").lower(),
            ]
        )
        if not any(keyword in target for keyword in WORKS_LINK_KEYWORDS):
            continue
        if any(token in target for token in WORKS_LINK_EXCLUDE_KEYWORDS):
            continue
        _append(absolute_url, artist_scoped=is_artist_scoped)
        if len(scoped_candidates) + len(fallback_candidates) >= max_links:
            break

    return (scoped_candidates + fallback_candidates)[:max_links]


def build_image_fetch_variants(image_url: str) -> list[str]:
    raw = str(image_url or "").strip()
    if not raw:
        return []
    variants: list[str] = [raw]
    lower = raw.lower()
    if "-tiny." in lower:
        variants.append(re.sub(r"-tiny(?=\.)", "-large", raw, flags=re.IGNORECASE))
        variants.append(re.sub(r"-tiny(?=\.)", "-medium", raw, flags=re.IGNORECASE))
        variants.append(re.sub(r"-tiny(?=\.)", "", raw, flags=re.IGNORECASE))
    if "/tiny/" in lower:
        variants.append(re.sub(r"/tiny/", "/large/", raw, flags=re.IGNORECASE))
        variants.append(re.sub(r"/tiny/", "/medium/", raw, flags=re.IGNORECASE))
    deduped: list[str] = []
    seen: set[str] = set()
    for item in variants:
        normalized = normalize_url_for_link_compare(item)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(item)
    return deduped


def should_reject_image_candidate(
    candidate_url: str,
    attrs: dict[str, str],
    parent_name: str,
    *,
    candidate_year: int | None,
    evidence_text: str,
) -> tuple[bool, int]:
    url_lower = candidate_url.lower()
    parsed = urlparse(candidate_url)
    ext = Path(parsed.path).suffix.lower()
    if ext in DISALLOWED_EXTENSIONS:
        return True, -10

    alt_text = str(attrs.get("alt") or "").lower()
    class_text = str(attrs.get("class") or "").lower()
    combined = f"{url_lower} {alt_text} {class_text} {parent_name}".strip()
    evidence_lower = str(evidence_text or "").lower()

    if parent_name == "meta":
        return True, -10
    if any(token in combined for token in REJECT_TOKENS):
        return True, -10
    if any(token in evidence_lower for token in ("twitter:image", "og:image", "property=\"og:image\"", "name=\"twitter:image\"")):
        return True, -10
    if has_strong_hero_signal(candidate_url, attrs, parent_name) and not has_work_info_signal(
        candidate_year=candidate_year,
        evidence_text=evidence_text,
    ):
        return True, -10

    width_raw = str(attrs.get("width") or "").strip()
    height_raw = str(attrs.get("height") or "").strip()
    try:
        width = int(width_raw) if width_raw else 0
    except ValueError:
        width = 0
    try:
        height = int(height_raw) if height_raw else 0
    except ValueError:
        height = 0
    if width and height and width <= 240 and height <= 240:
        return True, -10

    score = 0
    if parent_name in {"figure", "picture"}:
        score += 1
    if any(token in combined for token in POSITIVE_TOKENS):
        score += 2
    if alt_text and len(alt_text) >= 12:
        score += 1
    return False, score


def extract_image_candidates(page_url: str, html: str) -> list[dict[str, Any]]:
    best_by_url: dict[str, dict[str, Any]] = {}
    first_seen_order: dict[str, int] = {}
    next_order = 1

    def register_candidate(
        raw_value: str,
        *,
        attrs: dict[str, str],
        parent_name: str,
        candidate_year: int | None,
        year_candidates: list[int],
        evidence_text: str,
    ) -> None:
        nonlocal next_order
        normalized_value = normalize_candidate_url_value(raw_value)
        if not normalized_value:
            return
        absolute_url = urljoin(page_url, normalized_value)
        parsed = urlparse(absolute_url)
        if parsed.scheme not in {"http", "https"}:
            return
        if absolute_url not in first_seen_order:
            first_seen_order[absolute_url] = next_order
            next_order += 1
        reject, score = should_reject_image_candidate(
            absolute_url,
            attrs,
            parent_name,
            candidate_year=candidate_year,
            evidence_text=evidence_text,
        )
        if reject:
            return
        new_rank = (1 if candidate_year is not None else 0, candidate_year or -1, score)
        existing = best_by_url.get(absolute_url)
        existing_year = normalize_candidate_year(existing.get("year")) if isinstance(existing, dict) else None
        existing_rank = (
            1 if existing_year is not None else 0,
            existing_year or -1,
            int(existing.get("score", -999)) if isinstance(existing, dict) else -999,
        )
        if existing is None or new_rank > existing_rank:
            best_by_url[absolute_url] = {
                "url": absolute_url,
                "score": score,
                "year": candidate_year,
                "year_candidates": year_candidates[:5],
                "evidence_text": evidence_text,
                "attrs": {
                    "alt": str(attrs.get("alt") or ""),
                    "class": str(attrs.get("class") or ""),
                    "width": str(attrs.get("width") or ""),
                    "height": str(attrs.get("height") or ""),
                },
                "parent_tag": parent_name,
                "page_order": first_seen_order.get(absolute_url, 0),
            }

    for match in IMG_TAG_RE.finditer(html):
        tag_html = match.group(0)
        attrs = parse_img_attrs(tag_html)
        candidate_year, year_candidates, evidence_text = extract_candidate_year_from_img(html, match, attrs)
        candidate_values: list[str] = []
        for attr_name in ("src", "data-src", "data-original", "data-lazy-src", "data-lazy"):
            value = str(attrs.get(attr_name) or "").strip()
            if value:
                candidate_values.append(value)
        srcset = str(attrs.get("srcset") or "").strip()
        if srcset:
            best_srcset = parse_srcset_best(srcset)
            if best_srcset:
                candidate_values.append(best_srcset)

        parent_name = ""
        context_start = max(0, match.start() - 80)
        context = html[context_start : match.start()].lower()
        if "<figure" in context:
            parent_name = "figure"
        elif "<picture" in context:
            parent_name = "picture"
        for raw_value in candidate_values:
            register_candidate(
                raw_value,
                attrs=attrs,
                parent_name=parent_name,
                candidate_year=candidate_year,
                year_candidates=year_candidates,
                evidence_text=evidence_text,
            )

    # Generic fallback for pages that expose image references outside <img>.
    for match in GENERIC_IMG_ATTR_TAG_RE.finditer(html):
        tag_name = str(match.group("tag") or "").strip().lower()
        if tag_name == "img":
            continue
        tag_html = match.group(0)
        attrs = parse_img_attrs(tag_html)
        raw_value = str(match.group("value") or "").strip()
        if not raw_value:
            continue
        if not looks_like_image_url_reference(raw_value):
            continue
        candidate_year, year_candidates, evidence_text = extract_candidate_year_from_context_window(
            html,
            match.start(),
            match.end(),
            attrs,
        )
        register_candidate(
            raw_value,
            attrs=attrs,
            parent_name=tag_name or "tag",
            candidate_year=candidate_year,
            year_candidates=year_candidates,
            evidence_text=evidence_text,
        )

    for match in GENERIC_SRCSET_TAG_RE.finditer(html):
        tag_name = str(match.group("tag") or "").strip().lower()
        if tag_name == "img":
            continue
        tag_html = match.group(0)
        attrs = parse_img_attrs(tag_html)
        srcset_raw = str(match.group("value") or attrs.get("srcset") or "").strip()
        best_srcset = parse_srcset_best(normalize_candidate_url_value(srcset_raw))
        if not best_srcset:
            continue
        if not looks_like_image_url_reference(best_srcset):
            continue
        candidate_year, year_candidates, evidence_text = extract_candidate_year_from_context_window(
            html,
            match.start(),
            match.end(),
            attrs,
        )
        register_candidate(
            best_srcset,
            attrs=attrs,
            parent_name=tag_name or "tag",
            candidate_year=candidate_year,
            year_candidates=year_candidates,
            evidence_text=evidence_text,
        )

    for match in INLINE_IMAGE_URL_RE.finditer(html):
        raw_value = str(match.group("value") or "").strip()
        if not raw_value:
            continue
        if not looks_like_image_url_reference(raw_value):
            continue
        parent_name = guess_parent_tag_from_index(html, match.start()) or "inline"
        attrs: dict[str, str] = {}
        candidate_year, year_candidates, evidence_text = extract_candidate_year_from_context_window(
            html,
            match.start(),
            match.end(),
            attrs,
        )
        register_candidate(
            raw_value,
            attrs=attrs,
            parent_name=parent_name,
            candidate_year=candidate_year,
            year_candidates=year_candidates,
            evidence_text=evidence_text,
        )

    return sort_candidates_for_selection(list(best_by_url.values()))


def detect_extension(image_url: str, content_type: str) -> str:
    parsed = urlparse(image_url)
    ext = Path(parsed.path).suffix.lower()
    normalized_type = content_type.split(";")[0].strip().lower()
    content_type_ext = CONTENT_TYPE_TO_EXTENSION.get(normalized_type)
    if content_type_ext:
        return content_type_ext
    if ext and ext not in DISALLOWED_EXTENSIONS and len(ext) <= 8:
        return ext
    return ".jpg"


def sniff_extension_from_payload(payload: bytes) -> str | None:
    if len(payload) < 12:
        return None
    head = payload[:16]
    if head.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if head.startswith(b"RIFF") and payload[8:12] == b"WEBP":
        return ".webp"
    # ISO-BMFF brands (AVIF)
    if payload[4:8] == b"ftyp" and b"avif" in payload[:64]:
        return ".avif"
    return None


def looks_like_html_payload(payload: bytes) -> bool:
    probe = payload[:256].lstrip().lower()
    return probe.startswith((b"<!doctype html", b"<html", b"<?xml"))


def _to_rgb_image(image: Image.Image) -> Image.Image:
    if image.mode in {"RGB"}:
        return image
    if image.mode in {"RGBA", "LA"}:
        rgba = image.convert("RGBA")
        white = Image.new("RGB", rgba.size, (255, 255, 255))
        white.paste(rgba, mask=rgba.getchannel("A"))
        return white
    if image.mode == "P":
        rgba = image.convert("RGBA")
        white = Image.new("RGB", rgba.size, (255, 255, 255))
        if "A" in rgba.getbands():
            white.paste(rgba, mask=rgba.getchannel("A"))
        else:
            white.paste(rgba)
        return white
    return image.convert("RGB")


def _resample_filter() -> int:
    if hasattr(Image, "Resampling"):  # Pillow >= 9
        return Image.Resampling.LANCZOS
    return Image.LANCZOS


def _encode_jpeg(image: Image.Image, quality: int) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=quality, optimize=True, progressive=True)
    return buffer.getvalue()


def _choose_jpeg_near_target(image: Image.Image, target_bytes: int) -> bytes | None:
    best_under: bytes | None = None
    best_over: bytes | None = None
    for quality in range(IMAGE_MAX_JPEG_QUALITY, IMAGE_MIN_JPEG_QUALITY - 1, -5):
        encoded = _encode_jpeg(image, quality)
        size = len(encoded)
        if size <= target_bytes:
            if best_under is None or size > len(best_under):
                best_under = encoded
        else:
            if best_over is None or size < len(best_over):
                best_over = encoded
    return best_under or best_over


def normalize_image_payload_for_rag(payload: bytes) -> tuple[bool, bytes, str]:
    try:
        with Image.open(BytesIO(payload)) as image:
            image.load()
            if image.width < MIN_IMAGE_WIDTH_PX or image.height < MIN_IMAGE_HEIGHT_PX:
                return False, b"", f"image_dimensions_too_small:{image.width}x{image.height}"
            rgb = _to_rgb_image(image)
    except (UnidentifiedImageError, OSError, ValueError):
        return False, b"", "image_decode_failed"

    chosen: bytes | None = None
    for scale in IMAGE_RESIZE_SCALE_STEPS:
        if scale < 1.0:
            width = max(1, int(rgb.width * scale))
            height = max(1, int(rgb.height * scale))
            resized = rgb.resize((width, height), _resample_filter())
        else:
            resized = rgb
        encoded = _choose_jpeg_near_target(resized, IMAGE_TARGET_SIZE_BYTES)
        if not encoded:
            continue
        chosen = encoded
        if len(encoded) <= IMAGE_TARGET_SIZE_BYTES:
            break

    if not chosen:
        return False, b"", "image_jpeg_encode_failed"
    return True, chosen, ".jpg"


def validate_cached_image_file(path: Path) -> tuple[bool, str]:
    suffix = path.suffix.lower()
    if suffix not in CACHED_IMAGE_ALLOWED_EXTENSIONS:
        return False, f"cached_extension_not_allowed:{suffix or 'none'}"
    try:
        size = path.stat().st_size
    except OSError:
        return False, "cached_stat_failed"
    if size < MIN_IMAGE_PAYLOAD_BYTES:
        return False, f"cached_payload_too_small:{size}"
    try:
        with Image.open(path) as image:
            image.load()
            width, height = image.size
    except (UnidentifiedImageError, OSError, ValueError):
        return False, "cached_image_decode_failed"
    if width < MIN_IMAGE_WIDTH_PX or height < MIN_IMAGE_HEIGHT_PX:
        return False, f"cached_dimensions_too_small:{width}x{height}"
    return True, ""


def quarantine_invalid_cached_images(
    entries: list[tuple[Path, str]],
    *,
    fair_slug_safe: str,
    target_year: int,
    run_ts: str,
) -> int:
    if not entries:
        return 0
    quarantine_root = TRASH_ROOT / f"invalid_cached_images_{run_ts}" / str(target_year) / fair_slug_safe
    quarantine_root.mkdir(parents=True, exist_ok=True)
    moved = 0
    for source_path, _reason in entries:
        destination = quarantine_root / source_path.name
        if destination.exists():
            stem = destination.stem
            suffix = destination.suffix
            i = 1
            while True:
                candidate = quarantine_root / f"{stem}__dup{i}{suffix}"
                if not candidate.exists():
                    destination = candidate
                    break
                i += 1
        try:
            shutil.move(str(source_path), str(destination))
            moved += 1
        except OSError:
            continue
    return moved


def fetch_html(session: requests.Session, url: str) -> tuple[bool, str, str]:
    errors: list[str] = []
    for candidate_url in build_url_fetch_candidates(url):
        if _playwright_enabled():
            ok_pw_html, pw_html, pw_error = fetch_html_with_playwright(candidate_url)
            if ok_pw_html:
                return True, pw_html, ""
            if pw_error:
                errors.append(pw_error)

        try:
            response = session.get(candidate_url, timeout=REQUEST_TIMEOUT_SECONDS, allow_redirects=True)
            response.raise_for_status()
        except requests.RequestException as exc:
            errors.append(summarize_request_error("html_fetch_failed", candidate_url, exc))
            continue

        content_type = str(response.headers.get("content-type") or "").lower()
        if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
            errors.append(f"html_content_type_unsupported:{normalize_domain(candidate_url)}:{content_type or 'unknown'}")
            continue
        final_url = str(response.url or candidate_url).strip() or candidate_url
        if is_redirected_to_generic_listing(candidate_url, final_url):
            errors.append(
                "html_redirected_to_generic_listing:"
                f"{normalize_domain(candidate_url)}:{urlparse(final_url).path or '/'}"
            )
            continue

        response.encoding = response.encoding or "utf-8"
        return True, response.text, ""

    if errors:
        return False, "", errors[0]
    return False, "", "html_fetch_failed:unknown"


def fetch_image(session: requests.Session, image_url: str) -> tuple[bool, bytes, str, str]:
    errors: list[str] = []
    for candidate_url in build_url_fetch_candidates(image_url):
        try:
            response = session.get(
                candidate_url,
                timeout=REQUEST_TIMEOUT_SECONDS,
                allow_redirects=True,
                headers={"Accept": IMAGE_REQUEST_ACCEPT_HEADER},
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            errors.append(summarize_request_error("image_fetch_failed", candidate_url, exc))
            continue

        content_type = str(response.headers.get("content-type") or "").lower()
        if not content_type.startswith("image/"):
            errors.append(f"image_content_type_unsupported:{normalize_domain(candidate_url)}:{content_type or 'unknown'}")
            continue
        if "svg" in content_type:
            errors.append(f"image_content_type_unsupported:{normalize_domain(candidate_url)}:{content_type or 'unknown'}")
            continue

        payload = response.content
        if not payload:
            errors.append("image_empty_payload")
            continue
        if len(payload) < MIN_IMAGE_PAYLOAD_BYTES:
            errors.append(f"image_payload_too_small:{len(payload)}")
            continue
        if looks_like_html_payload(payload):
            errors.append("image_payload_is_html")
            continue

        sniffed_ext = sniff_extension_from_payload(payload)
        if sniffed_ext in DISALLOWED_EXTENSIONS:
            errors.append(f"image_payload_signature_disallowed:{sniffed_ext}")
            continue

        ok_normalized, normalized_payload, normalized_ext_or_reason = normalize_image_payload_for_rag(payload)
        if not ok_normalized:
            errors.append(str(normalized_ext_or_reason))
            continue

        return True, normalized_payload, str(normalized_ext_or_reason), ""

    if errors:
        return False, b"", "", errors[0]
    return False, b"", "", "image_fetch_failed:unknown"


def build_breakdowns(
    per_artist_counts: list[dict[str, Any]],
    target_images_per_artist: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    fair_breakdown: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "fair_slug": "",
            "artist_count": 0,
            "artists_with_ge_1_image": 0,
            "artists_with_ge_target_images": 0,
            "images_saved_total": 0,
            "success_rate_ge_target": 0.0,
            "success_rate_ge_target_pct": 0.0,
        }
    )
    gallery_breakdown: dict[tuple[str, str], dict[str, Any]] = defaultdict(
        lambda: {
            "fair_slug": "",
            "gallery_name_en": "",
            "artist_count": 0,
            "artists_with_ge_1_image": 0,
            "artists_with_ge_target_images": 0,
            "images_saved_total": 0,
            "success_rate_ge_target": 0.0,
            "success_rate_ge_target_pct": 0.0,
        }
    )

    for row in per_artist_counts:
        fair_slug = str(row.get("fair_slug") or "unknown")
        gallery_name_en = str(row.get("gallery_name_en") or "unknown")
        saved_images = int(row.get("saved_images") or 0)
        ge1 = int(saved_images >= 1)
        ge_target = int(saved_images >= target_images_per_artist)

        fair_item = fair_breakdown[fair_slug]
        fair_item["fair_slug"] = fair_slug
        fair_item["artist_count"] += 1
        fair_item["artists_with_ge_1_image"] += ge1
        fair_item["artists_with_ge_target_images"] += ge_target
        fair_item["images_saved_total"] += saved_images

        gallery_key = (fair_slug, gallery_name_en)
        gallery_item = gallery_breakdown[gallery_key]
        gallery_item["fair_slug"] = fair_slug
        gallery_item["gallery_name_en"] = gallery_name_en
        gallery_item["artist_count"] += 1
        gallery_item["artists_with_ge_1_image"] += ge1
        gallery_item["artists_with_ge_target_images"] += ge_target
        gallery_item["images_saved_total"] += saved_images

    fair_rows = sorted(fair_breakdown.values(), key=lambda x: str(x.get("fair_slug") or ""))
    for item in fair_rows:
        artist_count = int(item.get("artist_count") or 0)
        success_count = int(item.get("artists_with_ge_target_images") or 0)
        rate = round((success_count / artist_count), 6) if artist_count > 0 else 0.0
        item["success_rate_ge_target"] = rate
        item["success_rate_ge_target_pct"] = round(rate * 100.0, 2)

    gallery_rows = sorted(
        gallery_breakdown.values(),
        key=lambda x: (str(x.get("fair_slug") or ""), str(x.get("gallery_name_en") or "")),
    )
    for item in gallery_rows:
        artist_count = int(item.get("artist_count") or 0)
        success_count = int(item.get("artists_with_ge_target_images") or 0)
        rate = round((success_count / artist_count), 6) if artist_count > 0 else 0.0
        item["success_rate_ge_target"] = rate
        item["success_rate_ge_target_pct"] = round(rate * 100.0, 2)

    return fair_rows, gallery_rows


def metadata_record_lookup_key(artist_name_key: str, source_url: str) -> str:
    if artist_name_key:
        return f"artist_name_key:{artist_name_key}"
    return f"source_url:{normalize_url_for_link_compare(source_url)}"


def list_existing_artist_images(fair_dir: Path, artist_key: str) -> list[Path]:
    files = [p for p in fair_dir.glob(f"{artist_key}__img_*") if p.is_file()]
    return sorted(files, key=lambda p: (parse_image_index_from_filename(p), p.name))


def resolve_local_cache_path(path_text: str) -> Path | None:
    raw = str(path_text or "").strip()
    if not raw:
        return None
    path = Path(raw)
    if path.is_absolute():
        return path
    return (Path.cwd() / path).resolve()


def build_valid_existing_metadata_items(
    existing_meta_hashes: list[str],
    existing_meta_by_hash: dict[str, dict[str, Any]],
    *,
    target_images_per_artist: int,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen_local_paths: set[str] = set()
    for url_hash in existing_meta_hashes:
        if len(items) >= target_images_per_artist:
            break
        prev = existing_meta_by_hash.get(url_hash, {})
        local_path_text = str(prev.get("local_path") or "")
        local_path = resolve_local_cache_path(local_path_text)
        if local_path is None or not local_path.exists():
            continue
        local_path_key = str(local_path.resolve())
        if local_path_key in seen_local_paths:
            continue
        ok_cached, _cached_reason = validate_cached_image_file(local_path)
        if not ok_cached:
            continue
        local_payload_hash = payload_hash_from_file(local_path).strip().lower()
        if not local_payload_hash:
            continue
        prev_payload_hash = str(prev.get("payload_hash") or "").strip().lower()
        # Guard against stale metadata pointing to a different payload than
        # the local cache file. Keeping these entries can silently preserve
        # duplicated files across reruns.
        if prev_payload_hash and prev_payload_hash != local_payload_hash:
            continue
        seen_local_paths.add(local_path_key)
        items.append(
            {
                "url": str(prev.get("url") or ""),
                "hash": url_hash,
                "caption": shorten_text(str(prev.get("caption") or ""), YEAR_EVIDENCE_TEXT_MAX_LEN),
                "year": int(prev.get("year") or 0),
                "r2_key": str(prev.get("r2_key") or local_path_to_r2_key(local_path)),
                "local_path": str(local_path),
                "year_source": str(prev.get("year_source") or "none"),
                "year_confidence": str(prev.get("year_confidence") or "low"),
                "payload_hash": str(prev_payload_hash or local_payload_hash),
            }
        )
    return items


def quarantine_orphan_artist_images(
    files: list[Path],
    *,
    fair_slug_safe: str,
    target_year: int,
    artist_key: str,
    run_ts: str,
) -> int:
    moved = 0
    if not files:
        return moved
    dst_root = TRASH_ROOT / f"orphan_artist_images_{run_ts}" / str(target_year) / fair_slug_safe / artist_key
    dst_root.mkdir(parents=True, exist_ok=True)
    for src in files:
        if not src.exists() or not src.is_file():
            continue
        dst = dst_root / src.name
        if dst.exists():
            dst = dst_root / f"{src.stem}__dup{src.suffix}"
        try:
            shutil.move(str(src), str(dst))
            moved += 1
        except Exception:
            continue
    return moved


def build_candidate_evidence(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "url": str(candidate.get("url") or ""),
        "year": normalize_candidate_year(candidate.get("year")),
        "year_candidates": normalize_year_candidates(candidate.get("year_candidates")),
        "evidence_text": shorten_text(str(candidate.get("evidence_text") or ""), YEAR_EVIDENCE_TEXT_MAX_LEN),
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    args = parse_args()
    start_time = utc_now_iso()
    target_year = int(args.target_year)
    target_images_per_artist = max(1, int(args.target_images_per_artist))
    success_threshold = SUCCESS_THRESHOLD_DEFAULT
    run_ts = utc_timestamp_compact()

    summary_path = (
        Path(args.output_json).resolve()
        if args.output_json
        else (LOG_DIR / f"phase1_seed10_artist_image_collect_summary_{run_ts}.json").resolve()
    )

    summary: dict[str, Any] = {
        "artifact_kind": ARTIFACT_KIND,
        "schema_name": SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "generated_at": start_time,
        "generated_by": SOURCE_CLI,
        "source_cli": SOURCE_CLI,
        "target_year": target_year,
        "target_images_per_artist": target_images_per_artist,
        "success_threshold": success_threshold,
        "seed_artist_count": 0,
        "processed_artist_count": 0,
        "artists_with_ge_1_image": 0,
        "artists_with_ge_target_images": 0,
        "success_rate_ge_target": 0.0,
        "success_rate_ge_target_pct": 0.0,
        "threshold_passed": False,
        "total_images_saved": 0,
        "per_artist_counts": [],
        "year_sort_audit": [],
        "failed_cases": [],
        "domain_stats": {},
        "fair_breakdown": [],
        "gallery_breakdown": [],
        "seed_supply_by_gallery": [],
        "seed_supply_under_cap": [],
        "notes": [],
        "wrapper_exit_code": 0,
        "network_dns_probe_host": DNS_PROBE_HOST,
        "network_dns_probe_ok": None,
        "skip_registry_path": str(SKIPPED_GALLERIES_REGISTRY_PATH.resolve()),
        "skip_registry_gallery_count": 0,
        "skipped_by_registry_count": 0,
        "skipped_by_registry": [],
        "artist_master_global_path": str(ARTIST_MASTER_GLOBAL_PATH.resolve()),
        "artist_master_global_record_count": 0,
        "skipped_by_global_artist_dedupe_count": 0,
        "skipped_by_global_artist_dedupe": [],
        "skipped_invalid_artist_seed_count": 0,
        "skipped_invalid_artist_seed": [],
        "failed_fetches_path": "",
        "failed_fetches_new_in_run": 0,
        "failed_fetches_total_ledger": 0,
        "failed_fetches_reason_counts": {},
        "force_retry_failed": bool(args.force_retry_failed),
        "clear_failed_ledger_scope": str(args.clear_failed_ledger),
        "failure_retry_cooldown_seconds": FAILURE_RETRY_COOLDOWN_SECONDS,
        "max_failure_retries_per_url": MAX_FAILURE_RETRIES_PER_URL,
    }

    try:
        dns_probe_ok, dns_probe_error = can_resolve_hostname(DNS_PROBE_HOST)
        summary["network_dns_probe_ok"] = dns_probe_ok
        if not dns_probe_ok:
            summary["notes"].append(f"dns_probe_failed:{DNS_PROBE_HOST}:{dns_probe_error}")

        only_fair_slug = str(args.only_fair_slug or "").strip().lower()
        only_gallery_name = str(args.only_gallery_name or "").strip().lower()
        only_source_url = str(args.only_source_url or "").strip()

        seed_supply_snapshot = collect_seed_supply_by_gallery(target_year)
        summary["seed_supply_by_gallery"] = seed_supply_snapshot
        under_cap_rows = [row for row in seed_supply_snapshot if bool(row.get("supply_under_cap"))]
        summary["seed_supply_under_cap"] = under_cap_rows
        for row in under_cap_rows:
            summary["notes"].append(
                "seed_supply_under_cap:"
                f"{row.get('fair_slug')}/{row.get('gallery_name_en')}:"
                f"detail={row.get('detail_seed_total')}<cap={row.get('configured_cap')}"
            )

        targets = load_artist_targets(target_year, only_source_url=only_source_url)
        if only_fair_slug:
            targets = [row for row in targets if str(row.get("fair_slug") or "").strip().lower() == only_fair_slug]
            summary["notes"].append(f"filter_only_fair_slug:{only_fair_slug}")
        if only_gallery_name:
            targets = [row for row in targets if str(row.get("gallery_name_en") or "").strip().lower() == only_gallery_name]
            summary["notes"].append(f"filter_only_gallery_name:{only_gallery_name}")
        if only_source_url:
            targets = [row for row in targets if str(row.get("source_url") or "").strip() == only_source_url]
            summary["notes"].append(f"filter_only_source_url:{only_source_url}")

        skip_registry = load_skipped_gallery_registry(SKIPPED_GALLERIES_REGISTRY_PATH)
        summary["skip_registry_gallery_count"] = len(skip_registry)
        if not skip_registry:
            summary["notes"].append("skip_registry_empty_or_missing")
        else:
            filtered_targets: list[dict[str, Any]] = []
            for row in targets:
                gallery_name = str(row.get("gallery_name_en") or "").strip()
                if not gallery_name:
                    filtered_targets.append(row)
                    continue
                skip_item = skip_registry.get(gallery_name.lower())
                if skip_item is None:
                    filtered_targets.append(row)
                    continue
                summary["skipped_by_registry"].append(
                    {
                        "gallery_name_en": gallery_name,
                        "fair_slug": str(row.get("fair_slug") or ""),
                        "source_url": str(row.get("source_url") or ""),
                        "exhibition_url": str(skip_item.get("exhibition_url") or ""),
                        "artists_url": str(skip_item.get("artists_url") or ""),
                        "skip_reason": str(skip_item.get("skip_reason") or ""),
                        "reason_code": "auto_skipped_by_registry",
                    }
                )
            targets = filtered_targets
            summary["skipped_by_registry_count"] = len(summary["skipped_by_registry"])
            if summary["skipped_by_registry_count"] > 0:
                summary["notes"].append(f"auto_skipped_by_registry:{summary['skipped_by_registry_count']}")

        artist_master_global = load_artist_master_global(ARTIST_MASTER_GLOBAL_PATH)
        merge_artist_master_from_works_meta(artist_master_global)
        summary["artist_master_global_record_count"] = len(artist_master_global)
        filtered_targets: list[dict[str, Any]] = []
        seen_identity_in_run: set[str] = set()
        for row in targets:
            source_url = str(row.get("source_url") or "").strip()
            if not source_url:
                continue
            fair_slug = str(row.get("fair_slug") or "").strip()
            gallery_name_en = str(row.get("gallery_name_en") or "").strip()
            artist_name_en = str(row.get("artist_name_en") or "").strip() or build_artist_name_en_from_source_url(source_url)
            artist_name_key = str(row.get("artist_name_key") or "").strip() or build_artist_name_key(artist_name_en, source_url)
            identity_key = build_artist_identity_key(artist_name_key, artist_name_en, source_url)
            row["artist_name_en"] = artist_name_en
            row["artist_name_key"] = artist_name_key
            row["artist_identity_key"] = identity_key

            existing = artist_master_global.get(identity_key)
            existing_source = normalize_url_for_link_compare(str(existing.get("first_source_url") or "")) if existing else ""
            current_source = normalize_url_for_link_compare(source_url)
            if existing and existing_source and existing_source != current_source:
                summary["skipped_by_global_artist_dedupe"].append(
                    {
                        "reason_code": "auto_skipped_by_global_artist_dedupe_existing",
                        "artist_identity_key": identity_key,
                        "artist_name_en": artist_name_en,
                        "artist_name_key": artist_name_key,
                        "source_url": source_url,
                        "fair_slug": fair_slug,
                        "gallery_name_en": gallery_name_en,
                        "first_source_url": str(existing.get("first_source_url") or ""),
                        "first_fair_slug": str(existing.get("first_fair_slug") or ""),
                        "first_gallery_name_en": str(existing.get("first_gallery_name_en") or ""),
                    }
                )
                continue
            if identity_key in seen_identity_in_run:
                summary["skipped_by_global_artist_dedupe"].append(
                    {
                        "reason_code": "auto_skipped_by_global_artist_dedupe_in_run",
                        "artist_identity_key": identity_key,
                        "artist_name_en": artist_name_en,
                        "artist_name_key": artist_name_key,
                        "source_url": source_url,
                        "fair_slug": fair_slug,
                        "gallery_name_en": gallery_name_en,
                    }
                )
                continue
            seen_identity_in_run.add(identity_key)
            filtered_targets.append(row)
            if existing is None:
                artist_master_global[identity_key] = _build_artist_master_entry(
                    identity_key=identity_key,
                    artist_name_key=artist_name_key,
                    artist_name_en=artist_name_en,
                    source_url=source_url,
                    fair_slug=fair_slug,
                    gallery_name_en=gallery_name_en,
                    seen_at=start_time,
                )
        targets = filtered_targets
        summary["skipped_by_global_artist_dedupe_count"] = len(summary["skipped_by_global_artist_dedupe"])
        if summary["skipped_by_global_artist_dedupe_count"] > 0:
            summary["notes"].append(
                f"auto_skipped_by_global_artist_dedupe:{summary['skipped_by_global_artist_dedupe_count']}"
            )
        summary["artist_master_global_record_count"] = len(artist_master_global)
        write_artist_master_global(ARTIST_MASTER_GLOBAL_PATH.resolve(), artist_master_global)

        failed_fetches_path = (LOG_DIR / FAILED_FETCH_LEDGER_FILENAME_TEMPLATE.format(target_year=target_year)).resolve()
        failed_fetches_ledger = load_failed_fetches_ledger(failed_fetches_path)
        failed_fetches_in_run: list[dict[str, Any]] = []
        summary["failed_fetches_path"] = str(failed_fetches_path)
        if args.clear_failed_ledger == "all":
            failed_fetches_ledger.clear()
            summary["notes"].append("failed_fetches_cleared:all")
        elif args.clear_failed_ledger == "target":
            target_domains = {
                normalize_domain(str(row.get("source_url") or ""))
                for row in targets
                if str(row.get("source_url") or "").strip()
            }
            clear_keys: list[str] = []
            for fail_hash, item in failed_fetches_ledger.items():
                raw_url = str(item.get("raw_url") or "")
                parent_source_url = str(item.get("parent_source_url") or "")
                raw_domain = normalize_domain(raw_url) if raw_url else ""
                parent_domain = normalize_domain(parent_source_url) if parent_source_url else ""
                if (raw_domain and raw_domain in target_domains) or (parent_domain and parent_domain in target_domains):
                    clear_keys.append(fail_hash)
            for fail_hash in clear_keys:
                failed_fetches_ledger.pop(fail_hash, None)
            summary["notes"].append(f"failed_fetches_cleared:target:{len(clear_keys)}")

        summary["failed_fetches_total_ledger"] = len(failed_fetches_ledger)

        summary["seed_artist_count"] = len(targets)
        summary["max_artists_per_gallery_for_collect"] = MAX_ARTISTS_PER_GALLERY_FOR_COLLECT
        summary["notes"].append("artist_collect_source_rule=detail_pages_only")
        summary["notes"].append("local_image_cache_layout=fair_only_flat_files")
        summary["notes"].append("artist_works_year_sort_rule=desc_unknown_tail")
        summary["notes"].append("artist_dedupe_scope=global_all_fairs_all_galleries")
        if not targets:
            summary["notes"].append(f"no_artist_raw_records_found:artists_*_{target_year}.jsonl")
            failed_fetches_for_save = {
                fail_hash: failed_fetches_ledger[fail_hash]
                for fail_hash in sorted(failed_fetches_ledger)
            }
            write_json(failed_fetches_path, failed_fetches_for_save)
            summary["failed_fetches_new_in_run"] = 0
            summary["failed_fetches_total_ledger"] = len(failed_fetches_ledger)
            failed_reason_counts: dict[str, int] = defaultdict(int)
            for item in failed_fetches_ledger.values():
                reason_key = str(item.get("reason_code") or "REQUEST_ERROR")
                failed_reason_counts[reason_key] += 1
            summary["failed_fetches_reason_counts"] = dict(failed_reason_counts)
            write_json(summary_path, summary)
            print(f"[DONE] no targets. summary={summary_path}")
            return 0

        artists_image_root = (IMAGE_ROOT_DIR / str(target_year)).resolve()
        artists_image_root.mkdir(parents=True, exist_ok=True)
        fair_slug_tokens = sorted({str(row.get("fair_slug") or "").strip() for row in targets if str(row.get("fair_slug") or "").strip()})
        works_meta_rows_by_fair: dict[str, list[dict[str, Any]]] = {}
        works_meta_index_by_fair: dict[str, dict[str, int]] = {}
        works_meta_paths_by_fair: dict[str, Path] = {}
        for fair_slug_token in fair_slug_tokens:
            meta_path = works_meta_path_for_fair(fair_slug_token).resolve()
            rows = read_jsonl_rows(meta_path)
            index: dict[str, int] = {}
            for idx, row in enumerate(rows):
                if not isinstance(row, dict):
                    continue
                key = metadata_record_lookup_key(
                    str(row.get("artist_name_key") or ""),
                    str(row.get("source_url") or ""),
                )
                if key not in index:
                    index[key] = idx
            works_meta_rows_by_fair[fair_slug_token] = rows
            works_meta_index_by_fair[fair_slug_token] = index
            works_meta_paths_by_fair[fair_slug_token] = meta_path

        domain_stats: dict[str, dict[str, int]] = defaultdict(
            lambda: {
                "target_artist_count": 0,
                "success_ge1_count": 0,
                "success_ge_target_count": 0,
                "images_saved_total": 0,
            }
        )

        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/jpeg,image/png,image/*;q=0.8,*/*;q=0.7",
                "Accept-Language": "en-US,en;q=0.8",
            }
        )
        if Retry is not None:
            retry = Retry(
                total=REQUEST_RETRY_TOTAL,
                connect=REQUEST_RETRY_TOTAL,
                read=REQUEST_RETRY_TOTAL,
                status=REQUEST_RETRY_TOTAL,
                backoff_factor=REQUEST_RETRY_BACKOFF_FACTOR,
                status_forcelist=(429, 500, 502, 503, 504),
                allowed_methods=frozenset(["GET", "HEAD"]),
                raise_on_status=False,
            )
            adapter = HTTPAdapter(max_retries=retry)
            session.mount("https://", adapter)
            session.mount("http://", adapter)
        else:
            summary["notes"].append("retry_adapter_unavailable")

        def maybe_skip_failed_url(raw_url: str, *, case_notes: list[str]) -> tuple[bool, str]:
            entry = failed_fetches_ledger.get(compute_page_url_hash(raw_url))
            if entry is None:
                return False, ""
            skip_now, skip_reason = should_skip_failed_url(
                entry,
                datetime.now(timezone.utc),
                raw_url=raw_url,
                force_retry_failed=bool(args.force_retry_failed),
            )
            if skip_now:
                case_notes.append(f"{skip_reason}:{normalize_domain(raw_url)}")
                return True, skip_reason
            return False, ""

        def record_failed_url(
            *,
            kind: str,
            raw_url: str,
            parent_source_url: str | None,
            error_text: str,
        ) -> None:
            reason_code = reason_code_from_error_text(error_text)
            failed_row = upsert_failed_fetch(
                failed_fetches_ledger,
                kind=kind,
                raw_url=raw_url,
                parent_source_url=parent_source_url,
                last_error=error_text,
                http_status=None,
                reason_code=reason_code,
                target_year=target_year,
            )
            failed_fetches_in_run.append(failed_row)

        for target in targets:
            artist_id = str(target["artist_id"])
            source_url = str(target["source_url"])
            fair_slug = str(target["fair_slug"])
            gallery_name_en = str(target["gallery_name_en"])
            artist_name_en = str(target.get("artist_name_en") or "").strip() or build_artist_name_en_from_source_url(source_url)
            artist_name_key = str(target.get("artist_name_key") or "").strip() or build_artist_name_key(artist_name_en, source_url)
            artist_identity_key = str(target.get("artist_identity_key") or "").strip().lower() or build_artist_identity_key(
                artist_name_key, artist_name_en, source_url
            )
            domain = normalize_domain(source_url)
            domain_stats[domain]["target_artist_count"] += 1

            fair_slug_safe = slugify_token(fair_slug, fallback="unknown-fair")
            gallery_slug = slugify_token(gallery_name_en, fallback="unknown-gallery")
            artist_slug = artist_slug_from_source_url(source_url)
            artist_tokens = artist_match_tokens_from_source_url(source_url)
            if not artist_tokens:
                summary["skipped_invalid_artist_seed"].append(
                    {
                        "artist_id": artist_id,
                        "source_url": source_url,
                        "fair_slug": fair_slug,
                        "gallery_name_en": gallery_name_en,
                        "artist_name_en": artist_name_en,
                        "reason_code": "invalid_artist_seed_token_empty",
                    }
                )
                summary["skipped_invalid_artist_seed_count"] = len(summary["skipped_invalid_artist_seed"])
                summary["notes"].append(f"invalid_artist_seed_token_empty:{source_url}")
                continue
            artist_key = f"{gallery_slug}__{artist_slug}__{artist_id[:8]}"
            fair_rows = works_meta_rows_by_fair.setdefault(fair_slug, [])
            fair_index = works_meta_index_by_fair.setdefault(fair_slug, {})
            works_meta_paths_by_fair.setdefault(fair_slug, works_meta_path_for_fair(fair_slug).resolve())
            meta_lookup_key = metadata_record_lookup_key(artist_name_key, source_url)
            existing_meta_idx = fair_index.get(meta_lookup_key)
            existing_meta_row = (
                fair_rows[existing_meta_idx]
                if existing_meta_idx is not None and 0 <= existing_meta_idx < len(fair_rows) and isinstance(fair_rows[existing_meta_idx], dict)
                else None
            )
            existing_meta_hashes = normalize_hash_list(
                existing_meta_row.get("works_image_url_hashes") if isinstance(existing_meta_row, dict) else []
            )
            prev_topn_hashes = normalize_hash_list(
                existing_meta_row.get("works_image_topN_candidate_hashes_prev") if isinstance(existing_meta_row, dict) else [],
                max_items=WORKS_IMAGE_RANK_WINDOW,
            )
            existing_max_year_seen = normalize_candidate_year(
                existing_meta_row.get("max_year_seen") if isinstance(existing_meta_row, dict) else None
            ) or 0
            existing_meta_urls = (
                existing_meta_row.get("works_image_urls") if isinstance(existing_meta_row, dict) else []
            )
            existing_meta_captions = (
                existing_meta_row.get("works_image_captions") if isinstance(existing_meta_row, dict) else []
            )
            existing_meta_years = normalize_year_list(
                existing_meta_row.get("works_image_years") if isinstance(existing_meta_row, dict) else []
            )
            existing_meta_r2_keys = (
                existing_meta_row.get("works_image_r2_keys") if isinstance(existing_meta_row, dict) else []
            )
            existing_meta_local_paths = (
                existing_meta_row.get("works_image_local_paths") if isinstance(existing_meta_row, dict) else []
            )
            existing_meta_year_sources = (
                existing_meta_row.get("works_image_year_sources") if isinstance(existing_meta_row, dict) else []
            )
            existing_meta_year_confidences = (
                existing_meta_row.get("works_image_year_confidences") if isinstance(existing_meta_row, dict) else []
            )
            existing_meta_payload_hashes = (
                existing_meta_row.get("works_image_payload_hashes") if isinstance(existing_meta_row, dict) else []
            )
            existing_meta_by_hash: dict[str, dict[str, Any]] = {}
            for idx, url_hash in enumerate(existing_meta_hashes):
                existing_meta_by_hash[url_hash] = {
                    "url": str(existing_meta_urls[idx]) if isinstance(existing_meta_urls, list) and idx < len(existing_meta_urls) else "",
                    "caption": str(existing_meta_captions[idx]) if isinstance(existing_meta_captions, list) and idx < len(existing_meta_captions) else "",
                    "year": int(existing_meta_years[idx]) if idx < len(existing_meta_years) else 0,
                    "r2_key": str(existing_meta_r2_keys[idx]) if isinstance(existing_meta_r2_keys, list) and idx < len(existing_meta_r2_keys) else "",
                    "local_path": str(existing_meta_local_paths[idx]) if isinstance(existing_meta_local_paths, list) and idx < len(existing_meta_local_paths) else "",
                    "year_source": str(existing_meta_year_sources[idx]) if isinstance(existing_meta_year_sources, list) and idx < len(existing_meta_year_sources) else "none",
                    "year_confidence": str(existing_meta_year_confidences[idx]) if isinstance(existing_meta_year_confidences, list) and idx < len(existing_meta_year_confidences) else "low",
                    "payload_hash": str(existing_meta_payload_hashes[idx]) if isinstance(existing_meta_payload_hashes, list) and idx < len(existing_meta_payload_hashes) else "",
                }
            valid_existing_metadata_items_for_seen = build_valid_existing_metadata_items(
                existing_meta_hashes,
                existing_meta_by_hash,
                target_images_per_artist=max(target_images_per_artist, len(existing_meta_hashes)),
            )
            case_notes: list[str] = []
            rejected_existing_local_paths: set[Path] = set()
            filtered_existing_metadata_items: list[dict[str, Any]] = []
            for existing_item in valid_existing_metadata_items_for_seen:
                existing_candidate = {
                    "url": str(existing_item.get("url") or ""),
                    "evidence_text": str(existing_item.get("caption") or ""),
                    "year": normalize_candidate_year(existing_item.get("year")),
                }
                if candidate_violates_works_only(existing_candidate):
                    local_path = resolve_local_cache_path(str(existing_item.get("local_path") or ""))
                    if local_path is not None:
                        rejected_existing_local_paths.add(local_path.resolve())
                    continue
                # Keep cached images when artist-consistency still passes, even if
                # nearby captions contain other names on multi-artist pages.
                if not candidate_matches_artist(existing_candidate, source_url, source_url):
                    if has_foreign_person_name_text(str(existing_item.get("caption") or ""), artist_tokens):
                        local_path = resolve_local_cache_path(str(existing_item.get("local_path") or ""))
                        if local_path is not None:
                            rejected_existing_local_paths.add(local_path.resolve())
                        continue
                    if has_foreign_person_slug(str(existing_item.get("url") or ""), artist_tokens):
                        local_path = resolve_local_cache_path(str(existing_item.get("local_path") or ""))
                        if local_path is not None:
                            rejected_existing_local_paths.add(local_path.resolve())
                        continue
                filtered_existing_metadata_items.append(existing_item)
            if rejected_existing_local_paths:
                case_notes.append(f"cached_artist_mismatch_filtered:{len(rejected_existing_local_paths)}")
            valid_existing_metadata_items_for_seen = filtered_existing_metadata_items
            valid_existing_hashes = {
                str(item.get("hash") or "")
                for item in valid_existing_metadata_items_for_seen
                if str(item.get("hash") or "")
            }

            fair_dir = artists_image_root / fair_slug_safe
            fair_dir.mkdir(parents=True, exist_ok=True)
            existing_image_candidates = list_existing_artist_images(fair_dir, artist_key)
            existing_images: list[Path] = []
            invalid_cached_images: list[tuple[Path, str]] = []
            for cached_path in existing_image_candidates:
                cached_resolved = cached_path.resolve()
                if cached_resolved in rejected_existing_local_paths:
                    invalid_cached_images.append((cached_path, "CACHED_ARTIST_MISMATCH"))
                    continue
                ok_cached, cached_reason = validate_cached_image_file(cached_path)
                if ok_cached:
                    existing_images.append(cached_path)
                else:
                    invalid_cached_images.append((cached_path, cached_reason))
            if invalid_cached_images:
                moved_invalid = quarantine_invalid_cached_images(
                    invalid_cached_images,
                    fair_slug_safe=fair_slug_safe,
                    target_year=target_year,
                    run_ts=run_ts,
                )
                case_notes.append(f"invalid_cached_images_quarantined:{moved_invalid}")
            saved_count = len(existing_images)
            seen_payload_hashes: set[str] = set()
            for item in valid_existing_metadata_items_for_seen:
                ph = str(item.get("payload_hash") or "").strip().lower()
                if ph:
                    seen_payload_hashes.add(ph)
            if not seen_payload_hashes:
                for cached_path in existing_images:
                    ph = payload_hash_from_file(cached_path).strip().lower()
                    if ph:
                        seen_payload_hashes.add(ph)
            case_reason = ""
            detail_urls_considered: list[str] = []
            works_urls_tried_all: list[str] = []
            works_year_evidence: list[dict[str, Any]] = []
            selected_year_evidence: list[dict[str, Any]] = []
            selected_image_hashes: list[str] = []
            current_topn_hashes: list[str] = []
            works_only_artist_unique_normalized_urls: set[str] = set()
            works_only_artist_unique_urls_top20: list[str] = []
            # Only treat hashes with an actually usable local cache file as "already seen".
            # This allows re-download when stale metadata points to missing/invalid files.
            seen_image_url_hashes: set[str] = set(valid_existing_hashes)
            seen_image_url_identities: set[str] = set()
            for item in valid_existing_metadata_items_for_seen:
                existing_url = str(item.get("url") or "")
                existing_identity = normalize_image_url_for_dedupe(existing_url) if existing_url else ""
                if existing_identity:
                    seen_image_url_identities.add(existing_identity)
            any_known_year_candidate = False
            download_fail_count = 0

            metadata_cover_count = len(valid_existing_metadata_items_for_seen)
            should_refetch_for_metadata_gap = (
                saved_count > 0 and metadata_cover_count < min(saved_count, target_images_per_artist)
            )
            if should_refetch_for_metadata_gap:
                case_notes.append(
                    f"metadata_refetch_required:cached={saved_count},meta={metadata_cover_count}"
                )

            if saved_count < target_images_per_artist or should_refetch_for_metadata_gap:
                if looks_like_artist_listing_url(source_url):
                    skip_source_url, skip_source_reason = maybe_skip_failed_url(source_url, case_notes=case_notes)
                    if skip_source_url:
                        case_reason = skip_source_reason
                        detail_urls_considered = []
                    else:
                        ok_list_html, list_html, list_error = fetch_html(session, source_url)
                        if not ok_list_html:
                            case_reason = list_error
                            record_failed_url(
                                kind="page",
                                raw_url=source_url,
                                parent_source_url=None,
                                error_text=list_error,
                            )
                        else:
                            clear_failed_fetch(failed_fetches_ledger, source_url)
                            detail_urls_considered = extract_artist_detail_urls(source_url, list_html)
                            if not detail_urls_considered:
                                case_reason = "no_artist_detail_links_found"
                            else:
                                case_notes.append(f"resolved_artist_detail_pages:{len(detail_urls_considered)}")
                else:
                    detail_urls_considered = [source_url]

                if detail_urls_considered and saved_count < target_images_per_artist:
                    existing_image_indices: set[int] = set()
                    for existing_path in existing_images:
                        existing_idx = parse_image_index_from_filename(existing_path)
                        if existing_idx > 0:
                            existing_image_indices.add(existing_idx)
                    next_index = 1
                    while next_index in existing_image_indices:
                        next_index += 1
                    any_detail_fetch_ok = False
                    any_image_candidate_found = False
                    seed_redirected_to_listing = False
                    for detail_url in detail_urls_considered:
                        if saved_count >= target_images_per_artist:
                            break
                        skip_detail_url, _skip_detail_reason = maybe_skip_failed_url(detail_url, case_notes=case_notes)
                        if skip_detail_url:
                            continue
                        ok_html, html, html_error = fetch_html(session, detail_url)
                        if not ok_html:
                            case_notes.append(html_error)
                            if str(html_error).startswith("html_redirected_to_generic_listing:"):
                                seed_redirected_to_listing = True
                            record_failed_url(
                                kind="page",
                                raw_url=detail_url,
                                parent_source_url=source_url,
                                error_text=html_error,
                            )
                            continue
                        clear_failed_fetch(failed_fetches_ledger, detail_url)
                        any_detail_fetch_ok = True
                        works_urls = extract_works_candidate_urls(detail_url, html)
                        case_notes.append(f"works_page_tried:{len(works_urls)}")
                        if works_urls:
                            case_notes.append(f"works_page_found:{len(works_urls)}")

                        works_candidates_count = 0
                        works_candidates_found = False
                        works_fetch_404_detected = False
                        artist_mismatch_filtered_total = 0
                        works_only_filtered_total = 0
                        lenient_artist_match_used = 0
                        for works_url in works_urls:
                            if saved_count >= target_images_per_artist:
                                break
                            if works_url not in works_urls_tried_all:
                                works_urls_tried_all.append(works_url)
                            case_notes.append(f"works_url:{works_url}")
                            skip_works_url, _skip_works_reason = maybe_skip_failed_url(works_url, case_notes=case_notes)
                            if skip_works_url:
                                continue
                            ok_works_html, works_html, works_error = fetch_html(session, works_url)
                            if not ok_works_html:
                                case_notes.append(works_error)
                                if "HTTP_404" in str(works_error):
                                    works_fetch_404_detected = True
                                record_failed_url(
                                    kind="page",
                                    raw_url=works_url,
                                    parent_source_url=detail_url,
                                    error_text=works_error,
                                )
                                continue
                            clear_failed_fetch(failed_fetches_ledger, works_url)
                            works_candidates = extract_image_candidates(works_url, works_html)
                            works_candidates_count += len(works_candidates)
                            if not works_candidates:
                                continue
                            for candidate in works_candidates:
                                if saved_count >= target_images_per_artist:
                                    break
                                image_url = str(candidate.get("url") or "").strip()
                                if not image_url:
                                    continue
                                if candidate_violates_works_only(candidate):
                                    works_only_filtered_total += 1
                                    continue
                                if not candidate_matches_artist(candidate, source_url, works_url):
                                    artist_mismatch_filtered_total += 1
                                    continue
                                normalized_candidate_url = normalize_image_url_for_dedupe(image_url)
                                if normalized_candidate_url and normalized_candidate_url in seen_image_url_identities:
                                    continue
                                if normalized_candidate_url and normalized_candidate_url not in works_only_artist_unique_normalized_urls:
                                    works_only_artist_unique_normalized_urls.add(normalized_candidate_url)
                                    if len(works_only_artist_unique_urls_top20) < 20:
                                        works_only_artist_unique_urls_top20.append(normalized_candidate_url)
                                url_hash = image_url_hash(image_url)
                                if not url_hash:
                                    continue
                                if url_hash in seen_image_url_hashes:
                                    continue
                                seen_image_url_hashes.add(url_hash)
                                works_candidates_found = True
                                any_image_candidate_found = True
                                candidate_year = normalize_candidate_year(candidate.get("year"))
                                if candidate_year is not None:
                                    any_known_year_candidate = True
                                if len(current_topn_hashes) < WORKS_IMAGE_RANK_WINDOW:
                                    current_topn_hashes.append(url_hash)
                                if len(works_year_evidence) < WORKS_IMAGE_RANK_WINDOW:
                                    works_year_evidence.append(
                                        {
                                            "url": image_url,
                                            "image_url_hash": url_hash,
                                            "year": candidate_year,
                                            "year_candidates": normalize_year_candidates(candidate.get("year_candidates")),
                                            "evidence_text": shorten_text(
                                                str(candidate.get("evidence_text") or ""),
                                                YEAR_EVIDENCE_TEXT_MAX_LEN,
                                            ),
                                        }
                                    )
                                ok_image = False
                                payload = b""
                                ext = ""
                                selected_image_url = image_url
                                for image_fetch_url in build_image_fetch_variants(image_url):
                                    skip_image_url, _skip_image_reason = maybe_skip_failed_url(
                                        image_fetch_url, case_notes=case_notes
                                    )
                                    if skip_image_url:
                                        continue
                                    ok_try, payload_try, ext_try, image_error = fetch_image(session, image_fetch_url)
                                    if ok_try:
                                        clear_failed_fetch(failed_fetches_ledger, image_fetch_url)
                                        ok_image = True
                                        payload = payload_try
                                        ext = ext_try
                                        selected_image_url = image_fetch_url
                                        break
                                    case_notes.append(image_error)
                                    download_fail_count += 1
                                    record_failed_url(
                                        kind="image",
                                        raw_url=image_fetch_url,
                                        parent_source_url=works_url,
                                        error_text=image_error,
                                    )
                                if not ok_image:
                                    continue
                                current_payload_hash = payload_hash(payload).strip().lower()
                                if current_payload_hash and current_payload_hash in seen_payload_hashes:
                                    case_notes.append(f"duplicate_payload_skipped:{normalize_domain(selected_image_url)}")
                                    continue
                                if current_payload_hash:
                                    seen_payload_hashes.add(current_payload_hash)
                                selected_url_hash = image_url_hash(selected_image_url) or url_hash
                                selected_url_identity = normalize_image_url_for_dedupe(selected_image_url)
                                file_path = fair_dir / f"{artist_key}__img_{next_index:02d}{ext}"
                                file_path.write_bytes(payload)
                                if selected_url_identity:
                                    seen_image_url_identities.add(selected_url_identity)
                                existing_image_indices.add(next_index)
                                while next_index in existing_image_indices:
                                    next_index += 1
                                selected_year_evidence.append(
                                    {
                                        "url": selected_image_url,
                                        "image_url_hash": selected_url_hash,
                                        "local_path": str(file_path),
                                        "r2_key": local_path_to_r2_key(file_path),
                                        "year": candidate_year,
                                        "year_source": "caption" if candidate_year is not None else "none",
                                        "year_confidence": "high" if candidate_year is not None else "low",
                                        "payload_hash": current_payload_hash,
                                        "evidence_text": shorten_text(
                                            str(candidate.get("evidence_text") or ""),
                                            YEAR_EVIDENCE_TEXT_MAX_LEN,
                                        ),
                                    }
                                )
                                selected_image_hashes.append(selected_url_hash)
                                saved_count += 1
                        case_notes.append(f"works_candidates_count:{works_candidates_count}")
                        case_notes.append(f"artist_consistency_filtered:{artist_mismatch_filtered_total}")
                        case_notes.append(f"works_only_filtered:{works_only_filtered_total}")
                        case_notes.append(
                            f"works_only_artist_match_unique:{len(works_only_artist_unique_normalized_urls)}"
                        )

                        if saved_count < target_images_per_artist and not works_candidates_found:
                            case_notes.append("works_not_found_fallback_used")
                            fallback_candidates = extract_image_candidates(detail_url, html)
                            if not fallback_candidates:
                                case_notes.append(f"no_image_candidates_on_detail:{normalize_domain(detail_url)}")
                                continue
                            any_image_candidate_found = True
                            for candidate in fallback_candidates:
                                if saved_count >= target_images_per_artist:
                                    break
                                image_url = str(candidate.get("url") or "").strip()
                                if not image_url:
                                    continue
                                if candidate_violates_works_only(candidate):
                                    continue
                                strict_match = candidate_matches_artist(candidate, source_url, detail_url)
                                if not strict_match:
                                    if works_fetch_404_detected and candidate_matches_artist_lenient_scoped(
                                        candidate, source_url, detail_url
                                    ):
                                        lenient_artist_match_used += 1
                                    else:
                                        continue
                                normalized_candidate_url = normalize_image_url_for_dedupe(image_url)
                                if normalized_candidate_url and normalized_candidate_url in seen_image_url_identities:
                                    continue
                                if normalized_candidate_url and normalized_candidate_url not in works_only_artist_unique_normalized_urls:
                                    works_only_artist_unique_normalized_urls.add(normalized_candidate_url)
                                    if len(works_only_artist_unique_urls_top20) < 20:
                                        works_only_artist_unique_urls_top20.append(normalized_candidate_url)
                                url_hash = image_url_hash(image_url)
                                if not url_hash:
                                    continue
                                if url_hash in seen_image_url_hashes:
                                    continue
                                seen_image_url_hashes.add(url_hash)
                                any_image_candidate_found = True
                                candidate_year = normalize_candidate_year(candidate.get("year"))
                                if candidate_year is not None:
                                    any_known_year_candidate = True
                                if len(current_topn_hashes) < WORKS_IMAGE_RANK_WINDOW:
                                    current_topn_hashes.append(url_hash)
                                ok_image = False
                                payload = b""
                                ext = ""
                                selected_image_url = image_url
                                for image_fetch_url in build_image_fetch_variants(image_url):
                                    skip_image_url, _skip_image_reason = maybe_skip_failed_url(
                                        image_fetch_url, case_notes=case_notes
                                    )
                                    if skip_image_url:
                                        continue
                                    ok_try, payload_try, ext_try, image_error = fetch_image(session, image_fetch_url)
                                    if ok_try:
                                        clear_failed_fetch(failed_fetches_ledger, image_fetch_url)
                                        ok_image = True
                                        payload = payload_try
                                        ext = ext_try
                                        selected_image_url = image_fetch_url
                                        break
                                    case_notes.append(image_error)
                                    download_fail_count += 1
                                    record_failed_url(
                                        kind="image",
                                        raw_url=image_fetch_url,
                                        parent_source_url=detail_url,
                                        error_text=image_error,
                                    )
                                if not ok_image:
                                    continue
                                current_payload_hash = payload_hash(payload).strip().lower()
                                if current_payload_hash and current_payload_hash in seen_payload_hashes:
                                    case_notes.append(f"duplicate_payload_skipped:{normalize_domain(selected_image_url)}")
                                    continue
                                if current_payload_hash:
                                    seen_payload_hashes.add(current_payload_hash)
                                selected_url_hash = image_url_hash(selected_image_url) or url_hash
                                selected_url_identity = normalize_image_url_for_dedupe(selected_image_url)
                                file_path = fair_dir / f"{artist_key}__img_{next_index:02d}{ext}"
                                file_path.write_bytes(payload)
                                if selected_url_identity:
                                    seen_image_url_identities.add(selected_url_identity)
                                existing_image_indices.add(next_index)
                                while next_index in existing_image_indices:
                                    next_index += 1
                                selected_year_evidence.append(
                                    {
                                        "url": selected_image_url,
                                        "image_url_hash": selected_url_hash,
                                        "local_path": str(file_path),
                                        "r2_key": local_path_to_r2_key(file_path),
                                        "year": candidate_year,
                                        "year_source": "caption" if candidate_year is not None else "none",
                                        "year_confidence": "high" if candidate_year is not None else "low",
                                        "payload_hash": current_payload_hash,
                                        "evidence_text": shorten_text(
                                            str(candidate.get("evidence_text") or ""),
                                            YEAR_EVIDENCE_TEXT_MAX_LEN,
                                        ),
                                    }
                                )
                                selected_image_hashes.append(selected_url_hash)
                                saved_count += 1
                        if lenient_artist_match_used > 0:
                            case_notes.append(f"works404_lenient_artist_match_used:{lenient_artist_match_used}")
                    if saved_count < target_images_per_artist and not case_reason:
                        if not any_detail_fetch_ok:
                            if seed_redirected_to_listing:
                                case_reason = "seed_invalid_redirected_to_listing"
                            else:
                                case_reason = "artist_detail_fetch_failed"
                        elif not any_image_candidate_found:
                            case_reason = "no_image_candidates_found_on_artist_detail"
                        elif existing_max_year_seen > 0 and any_known_year_candidate and not selected_year_evidence:
                            case_reason = "no_new_images_ge_max_year_seen"
                        elif download_fail_count > 0:
                            case_reason = "insufficient_image_candidates_after_download"
                        else:
                            case_reason = "insufficient_image_candidates_after_download"

            metadata_items: list[dict[str, Any]] = []
            valid_existing_metadata_items = valid_existing_metadata_items_for_seen[:target_images_per_artist]

            if selected_year_evidence:
                selected_items: list[dict[str, Any]] = []
                selected_hashes: set[str] = set()
                selected_url_identities: set[str] = set()
                selected_payload_hashes: set[str] = set()
                for item in selected_year_evidence[:target_images_per_artist]:
                    url_hash = str(item.get("image_url_hash") or "")
                    if not url_hash:
                        continue
                    if url_hash in selected_hashes:
                        continue
                    prev = existing_meta_by_hash.get(url_hash, {})
                    chosen_url = str(item.get("url") or prev.get("url") or "")
                    chosen_url_identity = normalize_image_url_for_dedupe(chosen_url) if chosen_url else ""
                    if chosen_url_identity and chosen_url_identity in selected_url_identities:
                        continue
                    payload_hash_value = str(item.get("payload_hash") or prev.get("payload_hash") or "").strip().lower()
                    if payload_hash_value and payload_hash_value in selected_payload_hashes:
                        continue
                    selected_hashes.add(url_hash)
                    if chosen_url_identity:
                        selected_url_identities.add(chosen_url_identity)
                    if payload_hash_value:
                        selected_payload_hashes.add(payload_hash_value)
                    year = normalize_candidate_year(item.get("year")) or int(prev.get("year") or 0)
                    selected_items.append(
                        {
                            "url": chosen_url,
                            "hash": url_hash,
                            "caption": shorten_text(str(item.get("evidence_text") or prev.get("caption") or ""), YEAR_EVIDENCE_TEXT_MAX_LEN),
                            "year": year,
                            "r2_key": str(item.get("r2_key") or prev.get("r2_key") or ""),
                            "local_path": str(item.get("local_path") or prev.get("local_path") or ""),
                            "year_source": str(item.get("year_source") or prev.get("year_source") or ("caption" if year > 0 else "none")),
                            "year_confidence": str(item.get("year_confidence") or prev.get("year_confidence") or ("high" if year > 0 else "low")),
                            "payload_hash": payload_hash_value,
                        }
                    )

                metadata_items = selected_items[:target_images_per_artist]
                if len(metadata_items) < target_images_per_artist and valid_existing_metadata_items:
                    for existing_item in valid_existing_metadata_items:
                        existing_hash = str(existing_item.get("hash") or "")
                        if not existing_hash:
                            continue
                        if existing_hash in selected_hashes:
                            continue
                        existing_url = str(existing_item.get("url") or "")
                        existing_url_identity = normalize_image_url_for_dedupe(existing_url) if existing_url else ""
                        if existing_url_identity and existing_url_identity in selected_url_identities:
                            continue
                        existing_payload_hash = str(existing_item.get("payload_hash") or "").strip().lower()
                        if existing_payload_hash and existing_payload_hash in selected_payload_hashes:
                            continue
                        metadata_items.append(existing_item)
                        if existing_url_identity:
                            selected_url_identities.add(existing_url_identity)
                        if existing_payload_hash:
                            selected_payload_hashes.add(existing_payload_hash)
                        if len(metadata_items) >= target_images_per_artist:
                            break
            elif valid_existing_metadata_items:
                identity_seen: set[str] = set()
                payload_seen: set[str] = set()
                for existing_item in valid_existing_metadata_items:
                    existing_url = str(existing_item.get("url") or "")
                    existing_url_identity = normalize_image_url_for_dedupe(existing_url) if existing_url else ""
                    if existing_url_identity and existing_url_identity in identity_seen:
                        continue
                    existing_payload_hash = str(existing_item.get("payload_hash") or "").strip().lower()
                    if existing_payload_hash and existing_payload_hash in payload_seen:
                        continue
                    metadata_items.append(existing_item)
                    if existing_url_identity:
                        identity_seen.add(existing_url_identity)
                    if existing_payload_hash:
                        payload_seen.add(existing_payload_hash)
                    if len(metadata_items) >= target_images_per_artist:
                        break

            if metadata_items:
                kept_local_paths: set[Path] = set()
                for item in metadata_items:
                    local_path = resolve_local_cache_path(str(item.get("local_path") or ""))
                    if local_path is not None and local_path.exists():
                        kept_local_paths.add(local_path.resolve())
                current_artist_files = list_existing_artist_images(fair_dir, artist_key)
                orphan_files = [p for p in current_artist_files if p.resolve() not in kept_local_paths]
                if orphan_files:
                    moved_orphans = quarantine_orphan_artist_images(
                        orphan_files,
                        fair_slug_safe=fair_slug_safe,
                        target_year=target_year,
                        artist_key=artist_key,
                        run_ts=run_ts,
                    )
                    if moved_orphans > 0:
                        case_notes.append(f"orphan_images_quarantined:{moved_orphans}")

            if metadata_items:
                saved_count = len(metadata_items)
                selected_year_evidence = [
                    {
                        "url": str(item.get("url") or ""),
                        "image_url_hash": str(item.get("hash") or ""),
                        "year": normalize_candidate_year(item.get("year")),
                        "evidence_text": shorten_text(str(item.get("caption") or ""), YEAR_EVIDENCE_TEXT_MAX_LEN),
                    }
                    for item in metadata_items[:target_images_per_artist]
                ]
                selected_image_hashes = [str(item.get("hash") or "") for item in metadata_items]

            if not current_topn_hashes:
                current_topn_hashes = prev_topn_hashes
            max_year_seen = existing_max_year_seen
            for item in metadata_items:
                year_val = int(item.get("year") or 0)
                if year_val > max_year_seen:
                    max_year_seen = year_val

            metadata_row = {
                "source_url": str(existing_meta_row.get("source_url") or source_url) if isinstance(existing_meta_row, dict) else source_url,
                "artist_name_key": artist_name_key,
                "artist_identity_key": artist_identity_key,
                "artist_name_en": str(existing_meta_row.get("artist_name_en") or artist_name_en)
                if isinstance(existing_meta_row, dict)
                else artist_name_en,
                "gallery_name_en": gallery_name_en,
                "fair_slug": fair_slug,
                "target_year": target_year,
                "works_image_urls": [str(item.get("url") or "") for item in metadata_items],
                "works_image_url_hashes": [str(item.get("hash") or "") for item in metadata_items],
                "works_image_captions": [str(item.get("caption") or "") for item in metadata_items],
                "works_image_years": [int(item.get("year") or 0) for item in metadata_items],
                "works_image_r2_keys": [str(item.get("r2_key") or "") for item in metadata_items],
                "works_image_local_paths": [str(item.get("local_path") or "") for item in metadata_items],
                "works_image_payload_hashes": [str(item.get("payload_hash") or "") for item in metadata_items],
                "works_image_year_sources": [str(item.get("year_source") or "none") for item in metadata_items],
                "works_image_year_confidences": [str(item.get("year_confidence") or "low") for item in metadata_items],
                "max_year_seen": int(max_year_seen or 0),
                "works_image_topN_candidate_hashes_prev": normalize_hash_list(
                    current_topn_hashes,
                    max_items=WORKS_IMAGE_RANK_WINDOW,
                ),
                "extracted_at": utc_now_iso(),
            }
            existing_master_row = artist_master_global.get(artist_identity_key)
            if existing_master_row is None:
                artist_master_global[artist_identity_key] = _build_artist_master_entry(
                    identity_key=artist_identity_key,
                    artist_name_key=artist_name_key,
                    artist_name_en=artist_name_en,
                    source_url=source_url,
                    fair_slug=fair_slug,
                    gallery_name_en=gallery_name_en,
                    seen_at=str(metadata_row.get("extracted_at") or ""),
                )
            else:
                existing_master_row["artist_name_key"] = artist_name_key
                existing_master_row["artist_name_en"] = artist_name_en
                existing_master_row["updated_at"] = str(metadata_row.get("extracted_at") or "")
                artist_master_global[artist_identity_key] = existing_master_row
            if existing_meta_idx is not None and 0 <= existing_meta_idx < len(fair_rows):
                fair_rows[existing_meta_idx] = metadata_row
            else:
                fair_rows.append(metadata_row)
                fair_index[meta_lookup_key] = len(fair_rows) - 1

            success_ge1 = saved_count >= 1
            success_ge_target = saved_count >= target_images_per_artist
            if success_ge1:
                domain_stats[domain]["success_ge1_count"] += 1
            if success_ge_target:
                domain_stats[domain]["success_ge_target_count"] += 1
            domain_stats[domain]["images_saved_total"] += saved_count

            summary["processed_artist_count"] += 1
            summary["artists_with_ge_1_image"] += int(success_ge1)
            summary["artists_with_ge_target_images"] += int(success_ge_target)
            summary["total_images_saved"] += saved_count
            works_candidate_years_top5 = build_year_array_from_evidence(works_year_evidence, max_items=target_images_per_artist)
            selected_image_years_top5 = build_year_array_from_evidence(selected_year_evidence, max_items=target_images_per_artist)
            works_candidate_year_desc_ok = is_year_desc_with_unknown_tail(works_candidate_years_top5)
            selected_image_year_desc_ok = is_year_desc_with_unknown_tail(selected_image_years_top5)
            case_notes.append(f"works_years_top5:{format_years_for_note(works_candidate_years_top5)}")
            case_notes.append(f"selected_years_top5:{format_years_for_note(selected_image_years_top5)}")
            case_notes.append(f"works_year_desc_ok:{works_candidate_year_desc_ok}")
            case_notes.append(f"selected_year_desc_ok:{selected_image_year_desc_ok}")

            summary["per_artist_counts"].append(
                {
                    "artist_id": artist_id,
                    "artist_storage_key": artist_key,
                    "artist_name_key": artist_name_key,
                    "artist_identity_key": artist_identity_key,
                    "artist_name_en": artist_name_en,
                    "source_url": source_url,
                    "detail_urls_considered": detail_urls_considered,
                    "works_urls_tried": works_urls_tried_all,
                    "works_only_artist_match_unique_count": len(works_only_artist_unique_normalized_urls),
                    "works_only_artist_match_unique_urls_top20": works_only_artist_unique_urls_top20,
                    "fair_slug": fair_slug,
                    "gallery_name_en": gallery_name_en,
                    "saved_images": saved_count,
                    "target_images": target_images_per_artist,
                    "target_met": success_ge_target,
                    "works_candidate_years_top5": works_candidate_years_top5,
                    "works_candidate_year_desc_ok": works_candidate_year_desc_ok,
                    "selected_image_years_top5": selected_image_years_top5,
                    "selected_image_year_desc_ok": selected_image_year_desc_ok,
                    "works_candidate_year_evidence_top5": works_year_evidence[:target_images_per_artist],
                    "selected_image_year_evidence_top5": selected_year_evidence[:target_images_per_artist],
                    "selected_image_hashes_top5": selected_image_hashes[:target_images_per_artist],
                    "max_year_seen": int(max_year_seen or 0),
                    "works_image_topN_candidate_hashes_prev": normalize_hash_list(
                        current_topn_hashes,
                        max_items=WORKS_IMAGE_RANK_WINDOW,
                    ),
                    "notes": case_notes[:20],
                }
            )
            summary["year_sort_audit"].append(
                {
                    "artist_id": artist_id,
                    "artist_storage_key": artist_key,
                    "artist_name_key": artist_name_key,
                    "artist_identity_key": artist_identity_key,
                    "artist_name_en": artist_name_en,
                    "fair_slug": fair_slug,
                    "gallery_name_en": gallery_name_en,
                    "source_url": source_url,
                    "works_only_artist_match_unique_count": len(works_only_artist_unique_normalized_urls),
                    "works_only_artist_match_unique_urls_top20": works_only_artist_unique_urls_top20,
                    "works_candidate_years_top5": works_candidate_years_top5,
                    "works_candidate_year_desc_ok": works_candidate_year_desc_ok,
                    "selected_image_years_top5": selected_image_years_top5,
                    "selected_image_year_desc_ok": selected_image_year_desc_ok,
                    "works_candidate_year_evidence_top5": works_year_evidence[:target_images_per_artist],
                    "selected_image_year_evidence_top5": selected_year_evidence[:target_images_per_artist],
                    "selected_image_hashes_top5": selected_image_hashes[:target_images_per_artist],
                }
            )

            if not success_ge_target:
                fail_reason = case_reason or "target_not_met"
                summary["failed_cases"].append(
                    {
                        "artist_id": artist_id,
                        "source_url": source_url,
                        "detail_urls_considered": detail_urls_considered,
                        "domain": domain,
                        "saved_images": saved_count,
                        "target_images": target_images_per_artist,
                        "reason": fail_reason,
                        "reason_code": fail_reason.split(":", 1)[0] if fail_reason else "target_not_met",
                        "notes": case_notes[:8],
                    }
                )

        written_meta_paths: list[str] = []
        for fair_slug_token, rows in works_meta_rows_by_fair.items():
            meta_path = works_meta_paths_by_fair.get(fair_slug_token) or works_meta_path_for_fair(fair_slug_token).resolve()
            write_jsonl_rows(meta_path, rows)
            written_meta_paths.append(str(meta_path))
        summary["artist_works_metadata_paths"] = sorted(written_meta_paths)
        write_artist_master_global(ARTIST_MASTER_GLOBAL_PATH.resolve(), artist_master_global)
        summary["artist_master_global_record_count"] = len(artist_master_global)

        processed = int(summary["processed_artist_count"])
        success_target = int(summary["artists_with_ge_target_images"])
        rate = (success_target / processed) if processed > 0 else 0.0
        summary["success_rate_ge_target"] = round(rate, 6)
        summary["success_rate_ge_target_pct"] = round(rate * 100.0, 2)
        summary["threshold_passed"] = bool(rate >= success_threshold)
        summary["domain_stats"] = dict(domain_stats)
        fair_rows, gallery_rows = build_breakdowns(
            summary["per_artist_counts"],
            target_images_per_artist=target_images_per_artist,
        )
        summary["fair_breakdown"] = fair_rows
        summary["gallery_breakdown"] = gallery_rows
        if not summary["threshold_passed"]:
            summary["notes"].append(
                f"threshold_not_met:{summary['artists_with_ge_target_images']}/{summary['processed_artist_count']}<{success_threshold:.2f}"
            )
        summary["notes"].append("count_mode=effective_images_after_run")
        summary["notes"].append("breakdown_mode=fair_and_gallery")
        summary["generated_at"] = utc_now_iso()
        failed_fetches_for_save = {
            fail_hash: failed_fetches_ledger[fail_hash]
            for fail_hash in sorted(failed_fetches_ledger)
        }
        write_json(failed_fetches_path, failed_fetches_for_save)
        summary["failed_fetches_new_in_run"] = len(failed_fetches_in_run)
        summary["failed_fetches_total_ledger"] = len(failed_fetches_ledger)
        failed_reason_counts: dict[str, int] = defaultdict(int)
        for item in failed_fetches_ledger.values():
            reason_key = str(item.get("reason_code") or "REQUEST_ERROR")
            failed_reason_counts[reason_key] += 1
        summary["failed_fetches_reason_counts"] = dict(failed_reason_counts)

        write_json(summary_path, summary)
        print(
            "[DONE] "
            f"processed={summary['processed_artist_count']} "
            f"ge_target={summary['artists_with_ge_target_images']} "
            f"success_rate={summary['success_rate_ge_target']:.4f} "
            f"({summary['success_rate_ge_target_pct']:.2f}%) "
            f"threshold_passed={summary['threshold_passed']}"
        )
        if summary["gallery_breakdown"]:
            print("[BREAKDOWN] gallery")
            for row in summary["gallery_breakdown"]:
                print(
                    "  - "
                    f"{row.get('fair_slug')}/{row.get('gallery_name_en')}: "
                    f"artists={row.get('artist_count')} "
                    f"ge1={row.get('artists_with_ge_1_image')} "
                    f"ge_target={row.get('artists_with_ge_target_images')} "
                    f"images={row.get('images_saved_total')} "
                    f"rate={row.get('success_rate_ge_target')} "
                    f"({row.get('success_rate_ge_target_pct')}%)"
                )
        auto_sync_result = auto_sync_after_job(
            target="phase1_derived",
            trigger=SOURCE_CLI,
        )
        print(format_auto_sync_brief(auto_sync_result))
        print(f"[DONE] summary={summary_path}")
        return 0
    except Exception as exc:  # noqa: BLE001
        summary["wrapper_exit_code"] = 1
        summary["notes"].append(f"fatal_error:{exc}")
        if "failed_fetches_path" in locals() and "failed_fetches_ledger" in locals():
            failed_fetches_for_save = {
                fail_hash: failed_fetches_ledger[fail_hash]
                for fail_hash in sorted(failed_fetches_ledger)
            }
            write_json(failed_fetches_path, failed_fetches_for_save)
            summary["failed_fetches_total_ledger"] = len(failed_fetches_ledger)
        summary["generated_at"] = utc_now_iso()
        write_json(summary_path, summary)
        print(f"[ERROR] {exc}")
        print(f"[DONE] summary={summary_path}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
