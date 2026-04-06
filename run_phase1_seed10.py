#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import ParseResult, parse_qsl, urljoin, urlparse

import requests
from tools import skip_policy
from enrichment_requests_runtime import (
    build_artists_enrichment_requests as build_runtime_artists_enrichment_requests,
)
from phase1_ledger_contract import (
    build_artist_master_entry,
    clear_failed_fetch,
    get_phase1_artist_master_global_path,
    get_phase1_failed_fetches_ledger_path,
    get_phase1_logs_dir,
    get_phase1_run_summary_path,
    get_phase1_visited_pages_ledger_path,
    load_artist_master_global,
    load_phase1_failed_fetches_ledger,
    load_visited_pages_ledger,
    save_artist_master_global,
    save_failed_fetches_ledger,
    save_visited_pages_ledger,
    update_artist_master_summary,
    update_failed_fetches_summary,
    update_visited_pages_summary,
)
from phase2_art_pulse_config import (
    PHASE1_SEED10_ROOT,
    get_current_raw_dir,
    get_current_raw_path,
    get_enrichment_runtime_requests_path,
)
from phase1_artist_link_utils import (
    ARTIST_LINK_KEYWORDS,
    artist_listing_scope_mode as shared_artist_listing_scope_mode,
    build_artist_name_en_from_source_url as shared_build_artist_name_en_from_source_url,
    canonical_artist_source_key as shared_canonical_artist_source_key,
    canonicalize_artist_detail_url as shared_canonicalize_artist_detail_url,
    evaluate_artist_candidate_relation as shared_evaluate_artist_candidate_relation,
    get_artist_master_duplicate_reason as shared_get_artist_master_duplicate_reason,
    is_invalid_artist_name as shared_is_invalid_artist_name,
    looks_like_explicit_artist_detail_url as shared_looks_like_explicit_artist_detail_url,
    looks_like_artist_listing_url as shared_looks_like_artist_listing_url,
    normalize_url_for_link_compare as shared_normalize_url_for_link_compare,
    sanitize_artist_name_en as shared_sanitize_artist_name_en,
    score_artist_detail_url_quality as shared_score_artist_detail_url_quality,
)
from phase1_exhibitions_text_utils import (
    canonicalize_exhibition_url,
    extract_exhibition_dates,
    extract_participating_artists_line,
    fetch_and_extract_pdf_text,
    has_explicit_non_target_year,
    merge_exhibition_text,
    merge_sources,
    normalize_sources,
    should_include_target_year_page,
)
try:
    from bs4 import BeautifulSoup
except ModuleNotFoundError:  # pragma: no cover - environment fallback
    BeautifulSoup = None
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

TARGET_YEAR = 2025
RAG_CATEGORY = "exhibitions_text"
RAG_CATEGORY_ARTISTS = "artists_text"
SEED_PER_FAIR = 5
MAX_EXHIBITION_LINKS_PER_GALLERY = 25
MAX_EXHIBITION_LISTING_EXPANSION_DEPTH = 2
# TEMPORARY TEST CAP:
# User-requested operational override for stability testing.
# SSOT default target remains 80, but current runs are intentionally capped to 5 per gallery.
MAX_ARTISTS_PER_GALLERY = 80
ARTIST_PROBABLE_DETAIL_REJECT_SLUGS = frozenset(
    {
        "artist",
        "artists",
        "about",
        "about-us",
        "contact",
        "news",
        "press",
        "publication",
        "publications",
        "exhibition",
        "exhibitions",
        "fair",
        "fairs",
        "gallery",
        "main-homepage",
        "homepage",
        "home",
        "basket",
        "shop",
        "event",
        "events",
        "archive",
        "main",
        "list",
        "category",
        "of",
        "current",
        "past",
        "upcoming",
        "viewing-room",
        "viewingroom",
        "works",
        "work",
        "search",
    }
)
ARTIST_IDENTITY_SOURCE_WEIGHTS = {
    "h1": 32,
    "meta_title": 28,
    "title": 24,
    "anchor": 18,
    "slug": 8,
}
ARTIST_IDENTITY_STRONG_PAGE_SOURCES = frozenset({"h1", "meta_title", "title"})
ARTIST_IDENTITY_CONNECTOR_TOKENS = frozenset({"and", "et", "plus", "und", "x", "y"})
ARTIST_IDENTITY_NON_NAME_TOKENS = frozenset(
    {
        "address",
        "archive",
        "art",
        "article",
        "artist",
        "artists",
        "category",
        "contact",
        "cookie",
        "cookies",
        "current",
        "editions",
        "email",
        "exhibitions",
        "fairs",
        "first",
        "gallery",
        "home",
        "index",
        "information",
        "last",
        "list",
        "login",
        "mailing",
        "name",
        "newsletter",
        "news",
        "past",
        "password",
        "php",
        "policy",
        "privacy",
        "project",
        "projects",
        "publications",
        "search",
        "space",
        "studio",
        "subscribe",
        "username",
    }
)
ARTIST_IDENTITY_UTILITY_NAME_PHRASES = frozenset(
    {
        "contact us",
        "email address",
        "first name",
        "last name",
        "log in",
        "login",
        "mailing list",
        "privacy policy",
        "sign up",
    }
)
ARTIST_IDENTITY_INDEX_NAME_PHRASES = frozenset(
    {
        "archive",
        "article",
        "category",
        "index",
        "index php",
    }
)
ARTIST_IDENTITY_UTILITY_PAGE_MARKERS = frozenset(
    {
        "email address",
        "first name",
        "last name",
        "mailing list",
        "newsletter",
        "password",
        "privacy policy",
        "subscribe",
        "username",
    }
)
ARTIST_IDENTITY_HUB_PAGE_MARKERS = frozenset(
    {
        "artists",
        "current",
        "editions",
        "exhibitions",
        "fairs",
        "gallery",
        "home",
        "information",
        "news",
        "past",
        "publications",
    }
)
REQUEST_TIMEOUT_SECONDS = 12
USER_AGENT = "art-pulse-editor/phase1-seed10"
MAX_FAILURE_RETRIES_PER_URL = 3
FAILURE_RETRY_COOLDOWN_SECONDS = 3600
USE_PLAYWRIGHT_HTML_FETCH = os.getenv("PHASE1_USE_PLAYWRIGHT", "1").strip().lower() not in {
    "0",
    "false",
    "no",
    "off",
}
PLAYWRIGHT_NAV_TIMEOUT_MS = max(5000, REQUEST_TIMEOUT_SECONDS * 1000)
STARTUP_MIN_SYNC_ENABLED = os.getenv("PHASE1_STARTUP_MIN_SYNC", "1").strip().lower() not in {
    "0",
    "false",
    "no",
    "off",
}

# 一度失敗したら再試行価値が低いものは即スキップ対象にする。
NON_RETRYABLE_FAILURE_REASON_CODES = {
    "HTTP_400",
    "HTTP_401",
    "HTTP_403",
    "HTTP_404",
    "UNSUPPORTED_CONTENT_TYPE",
    "NO_ARTIST_DETAIL_LINKS",
}

CSV_PATHS = {
    "frieze_london": Path("data/gallery_lists/gallery_list_frieze_london.csv"),
    "liste": Path("data/gallery_lists/gallery_list_liste.csv"),
}
SKIPPED_GALLERIES_REGISTRY_PATH = Path("data/gallery_lists/skipped_galleries_registry.csv")

OUTPUT_ROOT = PHASE1_SEED10_ROOT
RAW_DIR = get_current_raw_dir()
MANUAL_SEED_TEXT_MARKERS = (
    "Artist page seed for",
)

_PLAYWRIGHT_MANAGER = None
_PLAYWRIGHT_BROWSER = None
_PLAYWRIGHT_CONTEXT = None

LINK_KEYWORDS = (
    "exhibition",
    "exhibitions",
    "show",
    "shows",
    "programme",
    "program",
    "projects",
    "archive",
    "past",
    "current",
    "viewing-room",
)

EXHIBITION_LISTING_PATH_SEGMENTS = {
    "exhibition",
    "exhibitions",
    "show",
    "shows",
    "programme",
    "program",
    "projects",
    "project",
    "archive",
    "past",
    "past-exhibitions",
    "current",
    "events",
    "event",
    "news",
    "category",
}

class LinkHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self._in_anchor = False
        self._anchor_href = ""
        self._anchor_chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_lower = tag.lower()
        if tag_lower in {"script", "style", "noscript"}:
            self._skip_depth += 1
            return
        if tag_lower == "a":
            href = ""
            for key, value in attrs:
                if key.lower() == "href" and value:
                    href = value.strip()
                    break
            if href:
                self._in_anchor = True
                self._anchor_href = href
                self._anchor_chunks = []

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()
        if tag_lower in {"script", "style", "noscript"}:
            if self._skip_depth > 0:
                self._skip_depth -= 1
            return
        if tag_lower == "a" and self._in_anchor:
            anchor_text = " ".join(chunk for chunk in self._anchor_chunks if chunk).strip()
            self.links.append((self._anchor_href, anchor_text))
            self._in_anchor = False
            self._anchor_href = ""
            self._anchor_chunks = []

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        if self._in_anchor:
            chunk = data.strip()
            if chunk:
                self._anchor_chunks.append(chunk)

    def close(self) -> None:
        super().close()
        if self._in_anchor and self._anchor_href:
            anchor_text = " ".join(chunk for chunk in self._anchor_chunks if chunk).strip()
            self.links.append((self._anchor_href, anchor_text))
            self._in_anchor = False
            self._anchor_href = ""
            self._anchor_chunks = []


class VisibleTextHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._lines: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript"} and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        text = data.strip()
        if text:
            self._lines.append(text)

    def get_text(self) -> str:
        return "\n".join(self._lines)


@dataclass
class GallerySeed:
    fair_slug: str
    gallery_name_raw: str
    gallery_name_en: str
    gallery_name_kana: str
    exhibitions_url: str
    artists_url: str = ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase1 seed10 fetch runner")
    parser.add_argument(
        "--targets-csv",
        default="",
        help=(
            "optional explicit gallery targets CSV. "
            "expected columns: fair_slug,gallery_name_en,exhibitions_url[,artists_url,gallery_name_kana,gallery_name_raw]"
        ),
    )
    parser.add_argument(
        "--include-artists-text",
        action="store_true",
        help="include artists_text minimal fetch loop (default: exhibitions_text only)",
    )
    parser.add_argument(
        "--max-artists-per-gallery",
        type=int,
        default=MAX_ARTISTS_PER_GALLERY,
        help=f"artists_text candidate cap per gallery (default: {MAX_ARTISTS_PER_GALLERY})",
    )
    parser.add_argument(
        "--mode",
        choices=(skip_policy.FILL_MISSING_MODE, skip_policy.REBUILD_MODE),
        default=skip_policy.FILL_MISSING_MODE,
        help="execution mode (default: fill_missing)",
    )
    parser.add_argument(
        "--allow-rebuild",
        action="store_true",
        help="required with --mode rebuild",
    )
    parser.add_argument(
        "--run-id",
        default="",
        help="required with --mode rebuild (trial run_id)",
    )
    parser.add_argument(
        "--trial-root",
        default=str(skip_policy.DEFAULT_TRIAL_ROOT),
        help=f"trial root for rebuild mode (default: {skip_policy.DEFAULT_TRIAL_ROOT})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="no network / no writes; compute fill-missing no-op counters only",
    )
    parser.add_argument(
        "--dry-run-output",
        default="",
        help="optional dry-run summary JSON output path",
    )
    return parser.parse_args()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_gallery_name(raw_name: str) -> tuple[str, str]:
    raw_name = raw_name.strip()
    match = re.match(r"^(.*?)（(.*?)）$", raw_name)
    if not match:
        return raw_name, ""

    gallery_name_en = match.group(1).strip()
    inside = match.group(2).strip()
    gallery_name_kana = inside.split("/")[0].strip()
    return gallery_name_en, gallery_name_kana


def normalize_gallery_name_for_registry(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip().lower())


def load_skipped_gallery_name_set(path: Path) -> set[str]:
    if not path.exists():
        return set()
    names: set[str] = set()
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if not row:
                continue
            name = normalize_gallery_name_for_registry(row[0])
            if name:
                names.add(name)
    return names


def load_seed_galleries(csv_path: Path, fair_slug: str, limit: int) -> list[GallerySeed]:
    galleries: list[GallerySeed] = []
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if len(row) < 2:
                continue
            gallery_name_raw = row[0].strip()
            exhibitions_url = row[1].strip()
            if not exhibitions_url:
                continue
            artists_url = row[2].strip() if len(row) >= 3 else ""
            gallery_name_en, gallery_name_kana = parse_gallery_name(gallery_name_raw)
            galleries.append(
                GallerySeed(
                    fair_slug=fair_slug,
                    gallery_name_raw=gallery_name_raw,
                    gallery_name_en=gallery_name_en,
                    gallery_name_kana=gallery_name_kana,
                    exhibitions_url=exhibitions_url,
                    artists_url=artists_url,
                )
            )
            if len(galleries) >= limit:
                break
    return galleries


def normalize_fair_slug(value: str) -> str:
    token = str(value or "").strip().lower().replace("-", "_")
    if token in {"frieze_london", "liste"}:
        return token
    return ""


def load_seed_galleries_from_targets_csv(path: Path) -> list[GallerySeed]:
    if not path.exists():
        raise FileNotFoundError(f"Missing targets CSV: {path}")
    galleries: list[GallerySeed] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            fair_slug = normalize_fair_slug(row.get("fair_slug") or row.get("fair") or "")
            gallery_name_en = str(row.get("gallery_name_en") or row.get("gallery_name") or "").strip()
            exhibitions_url = str(row.get("exhibitions_url") or row.get("exhibition_url") or "").strip()
            artists_url = str(row.get("artists_url") or row.get("artist_url") or "").strip()
            gallery_name_kana = str(row.get("gallery_name_kana") or "").strip()
            gallery_name_raw = str(row.get("gallery_name_raw") or "").strip()
            if not fair_slug:
                continue
            if not gallery_name_en:
                continue
            if not exhibitions_url:
                continue
            if not gallery_name_raw:
                gallery_name_raw = gallery_name_en
            galleries.append(
                GallerySeed(
                    fair_slug=fair_slug,
                    gallery_name_raw=gallery_name_raw,
                    gallery_name_en=gallery_name_en,
                    gallery_name_kana=gallery_name_kana,
                    exhibitions_url=exhibitions_url,
                    artists_url=artists_url,
                )
            )
    if not galleries:
        raise RuntimeError(f"No valid target rows found in targets CSV: {path}")
    return galleries


def resolve_artists_list_url(gallery: GallerySeed) -> tuple[str, str]:
    if gallery.artists_url:
        return gallery.artists_url, "artists_url"
    return gallery.exhibitions_url, "exhibitions_url_fallback"


def build_text_category_breakdown(
    *,
    category: str,
    seed_galleries: list[GallerySeed],
    records_by_fair: dict[str, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    target_gallery_keys: list[tuple[str, str]] = []
    target_gallery_key_set: set[tuple[str, str]] = set()
    target_count_by_fair: Counter[str] = Counter()

    for gallery in seed_galleries:
        key = (gallery.fair_slug, gallery.gallery_name_en)
        if key in target_gallery_key_set:
            continue
        target_gallery_key_set.add(key)
        target_gallery_keys.append(key)
        target_count_by_fair[gallery.fair_slug] += 1

    saved_count_by_gallery: Counter[tuple[str, str]] = Counter()
    for fair_slug, records in records_by_fair.items():
        for record in records:
            gallery_name_en = str(record.get("gallery_name_en") or "unknown")
            saved_count_by_gallery[(fair_slug, gallery_name_en)] += 1

    all_gallery_keys = sorted(set(target_gallery_key_set) | set(saved_count_by_gallery.keys()))

    gallery_rows: list[dict[str, Any]] = []
    for fair_slug, gallery_name_en in all_gallery_keys:
        target_gallery_count = 1 if (fair_slug, gallery_name_en) in target_gallery_key_set else 0
        records_saved_total = int(saved_count_by_gallery.get((fair_slug, gallery_name_en), 0))
        successful_gallery_count = int(target_gallery_count > 0 and records_saved_total >= 1)
        success_rate = (successful_gallery_count / target_gallery_count) if target_gallery_count > 0 else 0.0
        gallery_rows.append(
            {
                "category": category,
                "fair_slug": fair_slug,
                "gallery_name_en": gallery_name_en,
                "target_gallery_count": target_gallery_count,
                "successful_gallery_count": successful_gallery_count,
                "records_saved_total": records_saved_total,
                "success_rate_ge_1_record": round(success_rate, 6),
                "success_rate_ge_1_record_pct": round(success_rate * 100.0, 2),
            }
        )

    fairs_in_breakdown = sorted(
        set(target_count_by_fair.keys()) | set(fair_slug for fair_slug, _ in saved_count_by_gallery.keys())
    )
    fair_rows: list[dict[str, Any]] = []
    for fair_slug in fairs_in_breakdown:
        target_gallery_count = int(target_count_by_fair.get(fair_slug, 0))
        successful_gallery_count = 0
        records_saved_total = 0
        for row in gallery_rows:
            if row["fair_slug"] != fair_slug:
                continue
            records_saved_total += int(row.get("records_saved_total") or 0)
            if int(row.get("target_gallery_count") or 0) > 0 and int(row.get("records_saved_total") or 0) >= 1:
                successful_gallery_count += 1
        success_rate = (successful_gallery_count / target_gallery_count) if target_gallery_count > 0 else 0.0
        fair_rows.append(
            {
                "category": category,
                "fair_slug": fair_slug,
                "target_gallery_count": target_gallery_count,
                "successful_gallery_count": successful_gallery_count,
                "records_saved_total": records_saved_total,
                "success_rate_ge_1_record": round(success_rate, 6),
                "success_rate_ge_1_record_pct": round(success_rate * 100.0, 2),
            }
        )

    return fair_rows, gallery_rows


def _normalized_host(parsed: ParseResult) -> str:
    host = parsed.hostname or ""
    host = host.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _same_domain(url_a: str, url_b: str) -> bool:
    pa = urlparse(url_a)
    pb = urlparse(url_b)
    return _normalized_host(pa) == _normalized_host(pb)


def _normalize_url_for_link_compare(url: str) -> str:
    return shared_normalize_url_for_link_compare(url)


def _canonicalize_artist_detail_url(url: str) -> str:
    return shared_canonicalize_artist_detail_url(url)


def _canonical_artist_source_key(url: str) -> str:
    return shared_canonical_artist_source_key(url)


def _sanitize_artist_name_en(name: str) -> str:
    return shared_sanitize_artist_name_en(name)


def _is_invalid_artist_name(name: str) -> bool:
    return shared_is_invalid_artist_name(name)


def _score_artist_detail_url_quality(url: str) -> int:
    return shared_score_artist_detail_url_quality(url)


def _looks_like_exhibition_link(candidate_url: str, anchor_text: str) -> bool:
    target = f"{candidate_url.lower()} {anchor_text.lower()}"
    return any(keyword in target for keyword in LINK_KEYWORDS)


def _path_segments_from_url(url: str) -> list[str]:
    path = urlparse(url).path or ""
    return [segment for segment in path.lower().split("/") if segment]


def _query_pairs_lower(url: str) -> dict[str, str]:
    parsed = urlparse(str(url or ""))
    return {str(key or "").lower(): str(value or "").lower() for key, value in parse_qsl(parsed.query, keep_blank_values=True)}


def _anchor_text_has_exhibition_date_context(anchor_text: str, target_year: int = TARGET_YEAR) -> bool:
    text = str(anchor_text or "").lower()
    if not text:
        return False
    if str(int(target_year)) in text:
        return True
    if re.search(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)", text):
        return True
    return bool(
        re.search(
            r"\b(?:jan|january|feb|february|mar|march|apr|april|may|jun|june|jul|july|aug|august|sep|sept|september|oct|october|nov|november|dec|december)\b",
            text,
        )
    )


def _is_listing_like_exhibition_url(url: str) -> bool:
    query_pairs = _query_pairs_lower(url)
    if query_pairs.get("view") == "article" and query_pairs.get("id"):
        return False
    if query_pairs.get("view") == "category" or query_pairs.get("layout") == "blog":
        return True
    segments = _path_segments_from_url(url)
    if not segments:
        return True
    last = segments[-1]
    if last in EXHIBITION_LISTING_PATH_SEGMENTS:
        return True
    if len(segments) >= 2 and segments[-2] == "category":
        return True
    return False


def _is_exhibition_family_segment(segment: str) -> bool:
    lowered = segment.lower().strip()
    if not lowered:
        return False
    if lowered in EXHIBITION_LISTING_PATH_SEGMENTS:
        return lowered not in {"category", "news", "events", "event", "archive", "past", "current"}
    return bool(re.match(r"^(exhib|expo|show|project|program|viewing-room|viewingroom)", lowered))


def _exhibition_listing_scope_mode(list_page_url: str) -> str:
    query_pairs = _query_pairs_lower(list_page_url)
    if query_pairs.get("view") == "category" or query_pairs.get("layout") == "blog":
        return "taxonomy"
    segments = _path_segments_from_url(list_page_url)
    if not segments:
        return "unknown"
    if len(segments) == 1 and segments[0] in EXHIBITION_LISTING_PATH_SEGMENTS:
        return "root-listing"
    if segments[0] == "category" and any(_is_exhibition_family_segment(segment) for segment in segments[1:]):
        return "taxonomy"
    if _is_exhibition_family_segment(segments[0]):
        if len(segments) == 1 and segments[0] not in {"exhibition", "exhibitions", "show", "shows", "project", "projects"}:
            return "root-listing"
        return "family"
    if any(_is_exhibition_family_segment(segment) for segment in segments):
        return "root-listing"
    return "unknown"


def _matches_exhibition_listing_scope(candidate_url: str, list_page_url: str, anchor_text: str = "") -> bool:
    candidate_segments = _path_segments_from_url(candidate_url)
    candidate_query_pairs = _query_pairs_lower(candidate_url)
    if not candidate_segments and not candidate_query_pairs:
        return False
    scope_mode = _exhibition_listing_scope_mode(list_page_url)
    if candidate_query_pairs.get("view") == "article" and candidate_query_pairs.get("id"):
        return scope_mode in {"family", "root-listing", "taxonomy"}
    if scope_mode == "family":
        return _is_exhibition_family_segment(candidate_segments[0])
    if scope_mode == "taxonomy":
        return bool(candidate_segments) and _is_exhibition_family_segment(candidate_segments[0])
    if scope_mode == "root-listing":
        if candidate_segments and _is_exhibition_family_segment(candidate_segments[0]):
            return True
        if len(candidate_segments) >= 2 and _is_probable_exhibition_detail_url(candidate_url):
            return True
        return _anchor_text_has_exhibition_date_context(anchor_text) and _is_probable_exhibition_detail_url(candidate_url)
    return False


def _is_probable_exhibition_detail_url(url: str) -> bool:
    query_pairs = _query_pairs_lower(url)
    if query_pairs.get("view") == "article" and query_pairs.get("id"):
        return True
    if query_pairs.get("view") == "category" or query_pairs.get("layout") == "blog":
        return False
    segments = _path_segments_from_url(url)
    if not segments:
        return False
    if _is_listing_like_exhibition_url(url):
        return False
    last = segments[-1]
    if re.search(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)", "/".join(segments)):
        return True
    if "-" in last and len(last) >= 8:
        return True
    if len(segments) >= 2 and segments[-2] in {"exhibitions", "projects", "show", "shows"}:
        return True
    return len(segments) >= 2 and len(last) >= 6


def _score_exhibition_url_quality(url: str, anchor_text: str, target_year: int = TARGET_YEAR) -> int:
    score = 0
    target = f"{url.lower()} {anchor_text.lower()}".strip()
    if _is_probable_exhibition_detail_url(url):
        score += 40
    elif _is_listing_like_exhibition_url(url):
        score -= 20
    if str(int(target_year)) in target:
        score += 30
    if re.search(r"\b(current|now|ongoing)\b", target):
        score += 8
    if re.search(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)", target) and str(int(target_year)) not in target:
        score -= 6
    score += min(len(_path_segments_from_url(url)), 4)
    return score


def _looks_like_artist_listing_url(url: str) -> bool:
    return shared_looks_like_artist_listing_url(url)


def _looks_like_artist_detail_link(candidate_url: str, list_page_url: str, anchor_text: str = "") -> bool:
    return shared_looks_like_explicit_artist_detail_url(
        candidate_url=candidate_url,
        list_page_url=list_page_url,
        anchor_text=anchor_text,
        same_domain_required=False,
    )


def _normalize_artist_name_for_compare(name: str) -> str:
    value = str(name or "").strip()
    if not value:
        return ""
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = _sanitize_artist_name_en(value)
    if not value:
        return ""
    value = re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
    return re.sub(r"\s+", " ", value)


def _artist_anchor_text_looks_like_name(anchor_text: str) -> bool:
    normalized = _normalize_artist_name_for_compare(anchor_text)
    if not normalized:
        return False
    parts = [part for part in normalized.split(" ") if part]
    if len(parts) < 2:
        return False
    return len("".join(parts)) >= 6


def _artist_listing_scope_mode(list_page_url: str) -> str:
    return shared_artist_listing_scope_mode(list_page_url)


def _evaluate_artist_candidate_relation(
    candidate_url: str,
    list_page_url: str,
    anchor_text: str = "",
    *,
    path_family_counts: Counter[str] | None = None,
) -> dict[str, Any]:
    return shared_evaluate_artist_candidate_relation(
        candidate_url=candidate_url,
        list_page_url=list_page_url,
        anchor_text=anchor_text,
        path_family_counts=path_family_counts,
        same_domain_required=True,
    )


def extract_links_from_html(html: str) -> list[tuple[str, str]]:
    if BeautifulSoup is not None:
        soup = BeautifulSoup(html, "lxml")
        links: list[tuple[str, str]] = []
        for anchor in soup.find_all("a", href=True):
            href = str(anchor.get("href") or "").strip()
            if not href:
                continue
            links.append((href, anchor.get_text(" ", strip=True)))
        return links
    parser = LinkHTMLParser()
    parser.feed(html)
    parser.close()
    return parser.links


def extract_candidate_exhibition_urls(list_page_url: str, list_page_html: str) -> list[str]:
    best_by_canonical: dict[str, tuple[int, str]] = {}

    for href, anchor_text in extract_links_from_html(list_page_html):
        href = href.strip()
        if not href:
            continue
        if href.startswith(("mailto:", "tel:", "javascript:")):
            continue
        absolute_url = urljoin(list_page_url, href)
        parsed = urlparse(absolute_url)
        if parsed.scheme not in ("http", "https"):
            continue
        if not _same_domain(absolute_url, list_page_url):
            continue
        normalized = canonicalize_exhibition_url(absolute_url)
        if not _looks_like_exhibition_link(absolute_url, anchor_text):
            # Generic fallback: when starting from a listing-like page, allow
            # detail-like URLs even if anchor/url text lacks explicit exhibition keywords.
            fallback_allowed = (
                _is_listing_like_exhibition_url(list_page_url)
                and _is_probable_exhibition_detail_url(normalized)
                and _matches_exhibition_listing_scope(normalized, list_page_url, anchor_text)
            )
            if not fallback_allowed:
                continue
        score = _score_exhibition_url_quality(normalized, anchor_text)
        previous = best_by_canonical.get(normalized)
        if previous is None or score > previous[0]:
            best_by_canonical[normalized] = (score, normalized)

    if not best_by_canonical:
        return [list_page_url]

    ranked = sorted(best_by_canonical.values(), key=lambda item: (-item[0], item[1]))
    return [url for _score, url in ranked[:MAX_EXHIBITION_LINKS_PER_GALLERY]]


def _upsert_artist_candidate(
    *,
    parsed: ParseResult,
    quality_score: int,
    anchor_text: str,
    candidates: list[dict[str, Any]],
    candidate_scores: list[int],
    is_explicit: bool,
    relation_confidence: str,
    relation_type: str,
    seen_by_canonical: dict[str, int],
) -> None:
    if (parsed.path or "/") == "/":
        normalized = f"{parsed.scheme}://{parsed.netloc}/"
    else:
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")
    if parsed.query:
        normalized = f"{normalized}?{parsed.query}"
    canonical_url = _canonicalize_artist_detail_url(normalized)
    existing_index = seen_by_canonical.get(canonical_url)
    candidate_payload = {
        "anchor_text": str(anchor_text or "").strip(),
        "is_explicit": bool(is_explicit),
        "relation_confidence": str(relation_confidence or "").strip(),
        "relation_type": str(relation_type or "").strip(),
        "url": normalized,
    }
    if existing_index is not None:
        if quality_score > candidate_scores[existing_index]:
            candidates[existing_index] = candidate_payload
            candidate_scores[existing_index] = quality_score
        return
    seen_by_canonical[canonical_url] = len(candidates)
    candidates.append(candidate_payload)
    candidate_scores.append(quality_score)


def _build_artist_path_family_counts(
    candidate_rows: list[tuple[str, str, ParseResult]],
) -> Counter[str]:
    counts: Counter[str] = Counter()
    for absolute_url, anchor_text_raw, parsed in candidate_rows:
        if not _artist_anchor_text_looks_like_name(anchor_text_raw):
            continue
        path_parts = [part for part in (parsed.path or "").split("/") if part]
        if len(path_parts) != 2:
            continue
        family_segment = path_parts[0].strip().lower()
        slug = path_parts[1].strip().lower()
        if (
            not family_segment
            or family_segment in ARTIST_PROBABLE_DETAIL_REJECT_SLUGS
            or family_segment in {"artist", "artists"}
            or not slug
            or slug in ARTIST_PROBABLE_DETAIL_REJECT_SLUGS
            or "." in slug
            or "-" not in slug
            or not re.fullmatch(r"[a-z0-9-]+", slug)
        ):
            continue
        counts[family_segment] += 1
    return counts


def _resolve_artist_candidate_failure_reason(
    *,
    list_page_url: str,
    explicit_candidates_found: bool,
    fallback_relation_counts: Counter[str],
    failure_reason_counts: Counter[str],
) -> str:
    if explicit_candidates_found:
        return ""
    if fallback_relation_counts:
        relation_type = fallback_relation_counts.most_common(1)[0][0]
        return relation_type
    scope_mode = _artist_listing_scope_mode(list_page_url)
    if scope_mode == "unknown":
        return "LISTING_SCOPE_UNKNOWN"
    if failure_reason_counts.get("LOW_CONFIDENCE_NAME_MATCH", 0) > 0:
        return "LOW_CONFIDENCE_NAME_MATCH"
    if (
        scope_mode == "taxonomy_query"
        and failure_reason_counts.get("QUERY_TAXONOMY_UNSUPPORTED", 0) > 0
    ):
        return "QUERY_TAXONOMY_UNSUPPORTED"
    return "NO_RELATION_MATCH_CANDIDATES"


def extract_candidate_artist_urls(
    list_page_url: str,
    list_page_html: str,
    max_artists_per_gallery: int,
) -> tuple[list[dict[str, Any]], str]:
    explicit_candidates: list[dict[str, Any]] = []
    explicit_candidate_scores: list[int] = []
    explicit_seen_by_canonical: dict[str, int] = {}
    fallback_candidates: list[dict[str, Any]] = []
    fallback_candidate_scores: list[int] = []
    fallback_seen_by_canonical: dict[str, int] = {}
    candidate_rows: list[tuple[str, str, ParseResult]] = []
    fallback_relation_counts: Counter[str] = Counter()
    failure_reason_counts: Counter[str] = Counter()
    # Cap should be applied on "saved artists", not on first discovered links.
    # For small caps (e.g. 1 in initial smoke), scan a wider window to avoid
    # stopping at already-saved duplicates.
    candidate_scan_limit = min(200, max(max_artists_per_gallery, max_artists_per_gallery * 20))
    raw_scan_limit = min(400, max(candidate_scan_limit, candidate_scan_limit * 4))
    listing_context = _looks_like_artist_listing_url(list_page_url)
    normalized_listing_url = _normalize_url_for_link_compare(list_page_url)

    for href, anchor_text_raw in extract_links_from_html(list_page_html):
        href = href.strip()
        if not href:
            continue
        if href.startswith(("mailto:", "tel:", "javascript:")):
            continue
        absolute_url = urljoin(list_page_url, href)
        parsed = urlparse(absolute_url)
        if parsed.scheme not in ("http", "https"):
            continue
        if not _same_domain(absolute_url, list_page_url):
            continue
        if _normalize_url_for_link_compare(absolute_url) == normalized_listing_url:
            continue
        anchor_text = anchor_text_raw.lower()
        target = f"{absolute_url.lower()} {anchor_text}"
        if not listing_context and not any(keyword in target for keyword in ARTIST_LINK_KEYWORDS):
            continue
        candidate_rows.append((absolute_url, anchor_text_raw, parsed))
        if len(candidate_rows) >= raw_scan_limit:
            break

    path_family_counts = _build_artist_path_family_counts(candidate_rows)

    for absolute_url, anchor_text_raw, parsed in candidate_rows:
        if _looks_like_artist_detail_link(absolute_url, list_page_url, anchor_text_raw):
            explicit_score = 100 + _score_artist_detail_url_quality(absolute_url)
            _upsert_artist_candidate(
                parsed=parsed,
                quality_score=explicit_score,
                anchor_text=anchor_text_raw,
                candidates=explicit_candidates,
                candidate_scores=explicit_candidate_scores,
                is_explicit=True,
                relation_confidence="high",
                relation_type="explicit_detail",
                seen_by_canonical=explicit_seen_by_canonical,
            )
            if len(explicit_candidates) >= candidate_scan_limit:
                break
            continue

        relation = _evaluate_artist_candidate_relation(
            absolute_url,
            list_page_url,
            anchor_text_raw,
            path_family_counts=path_family_counts,
        )
        failure_reason = str(relation.get("failure_reason") or "").strip()
        if failure_reason:
            failure_reason_counts[failure_reason] += 1
        if not relation.get("accepted"):
            continue

        relation_type = str(relation.get("relation_type") or "").strip()
        if relation_type:
            fallback_relation_counts[relation_type] += 1
        fallback_score = int(relation.get("score") or 0) + _score_artist_detail_url_quality(absolute_url)
        _upsert_artist_candidate(
            parsed=parsed,
            quality_score=fallback_score,
            anchor_text=anchor_text_raw,
            candidates=fallback_candidates,
            candidate_scores=fallback_candidate_scores,
            is_explicit=False,
            relation_confidence=str(relation.get("confidence") or "").strip(),
            relation_type=relation_type,
            seen_by_canonical=fallback_seen_by_canonical,
        )
        if len(fallback_candidates) >= candidate_scan_limit:
            break

    result_reason = _resolve_artist_candidate_failure_reason(
        list_page_url=list_page_url,
        explicit_candidates_found=bool(explicit_candidates),
        fallback_relation_counts=fallback_relation_counts,
        failure_reason_counts=failure_reason_counts,
    )
    if explicit_candidates:
        return explicit_candidates, ""
    if fallback_candidates:
        return fallback_candidates, result_reason
    return [], result_reason


def reason_code_from_status(status_code: int) -> str:
    if status_code == 429:
        return "HTTP_429"
    if status_code == 408:
        return "HTTP_408"
    if 500 <= status_code <= 599:
        return "HTTP_5XX"
    return f"HTTP_{status_code}"


def reason_code_from_exception(exc: Exception) -> str:
    if isinstance(exc, requests.Timeout):
        return "TIMEOUT"
    message = str(exc).lower()
    if any(token in message for token in ("failed to resolve", "name or service not known", "temporary failure in name resolution")):
        return "DNS_ERROR"
    if isinstance(exc, requests.ConnectionError):
        return "CONNECTION_ERROR"
    return "REQUEST_ERROR"


def reason_code_from_error_text(error_text: str | None) -> str:
    text = (error_text or "").lower()
    if "timed out" in text or "timeout" in text:
        return "TIMEOUT"
    if any(token in text for token in ("failed to resolve", "name or service not known", "temporary failure in name resolution")):
        return "DNS_ERROR"
    if "connection" in text:
        return "CONNECTION_ERROR"
    return "REQUEST_ERROR"


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


def fetch_html_with_playwright(url: str) -> dict[str, Any]:
    context = _ensure_playwright_context()
    if context is None:
        return {
            "ok": False,
            "url": url,
            "final_url": url,
            "status_code": None,
            "reason_code": "PLAYWRIGHT_UNAVAILABLE",
            "error": "playwright_context_unavailable",
            "html": "",
        }

    page = None
    try:
        page = context.new_page()
        response = page.goto(url, wait_until="domcontentloaded", timeout=PLAYWRIGHT_NAV_TIMEOUT_MS)
        final_url = page.url or url
        status_code = response.status if response is not None else None
        content_type = ""
        if response is not None:
            headers = response.headers or {}
            content_type = str(headers.get("content-type") or "").lower()
        if status_code is not None and status_code >= 400:
            return {
                "ok": False,
                "url": url,
                "final_url": final_url,
                "status_code": status_code,
                "reason_code": reason_code_from_status(status_code),
                "error": f"PLAYWRIGHT_HTTP_{status_code}",
                "html": "",
            }
        if content_type and "text/html" not in content_type and "application/xhtml+xml" not in content_type:
            return {
                "ok": False,
                "url": url,
                "final_url": final_url,
                "status_code": status_code,
                "reason_code": "UNSUPPORTED_CONTENT_TYPE",
                "error": f"UNSUPPORTED_CONTENT_TYPE:{content_type}",
                "html": "",
            }
        html = page.content()
        return {
            "ok": True,
            "url": url,
            "final_url": final_url,
            "status_code": status_code,
            "reason_code": None,
            "error": None,
            "html": html,
        }
    except PlaywrightTimeoutError as exc:
        return {
            "ok": False,
            "url": url,
            "final_url": page.url if page is not None else url,
            "status_code": None,
            "reason_code": "TIMEOUT",
            "error": f"playwright_timeout:{exc}",
            "html": "",
        }
    except PlaywrightError as exc:
        reason_code = reason_code_from_error_text(str(exc))
        return {
            "ok": False,
            "url": url,
            "final_url": page.url if page is not None else url,
            "status_code": None,
            "reason_code": reason_code,
            "error": f"playwright_error:{exc}",
            "html": "",
        }
    except Exception as exc:  # noqa: BLE001
        reason_code = reason_code_from_error_text(str(exc))
        return {
            "ok": False,
            "url": url,
            "final_url": page.url if page is not None else url,
            "status_code": None,
            "reason_code": reason_code,
            "error": f"playwright_error:{exc}",
            "html": "",
        }
    finally:
        if page is not None:
            try:
                page.close()
            except Exception:
                pass


def fetch_html(session: requests.Session, url: str) -> dict[str, Any]:
    if _playwright_enabled():
        playwright_result = fetch_html_with_playwright(url)
        if playwright_result["ok"]:
            return playwright_result

    try:
        response = session.get(url, timeout=REQUEST_TIMEOUT_SECONDS, allow_redirects=True)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "").lower()
        if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
            return {
                "ok": False,
                "url": url,
                "final_url": response.url,
                "status_code": response.status_code,
                "reason_code": "UNSUPPORTED_CONTENT_TYPE",
                "error": f"UNSUPPORTED_CONTENT_TYPE:{content_type or 'unknown'}",
                "html": "",
            }
        response.encoding = response.encoding or "utf-8"
        return {
            "ok": True,
            "url": url,
            "final_url": response.url,
            "status_code": response.status_code,
            "reason_code": None,
            "error": None,
            "html": response.text,
        }
    except requests.RequestException as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        if status_code is not None:
            reason_code = reason_code_from_status(status_code)
        else:
            reason_code = reason_code_from_exception(exc)
        return {
            "ok": False,
            "url": url,
            "final_url": url,
            "status_code": status_code,
            "reason_code": reason_code,
            "error": str(exc),
            "html": "",
        }


def extract_text(html: str) -> str:
    if BeautifulSoup is not None:
        soup = BeautifulSoup(html, "lxml")
        for node in soup(["script", "style", "noscript"]):
            node.extract()
        text = soup.get_text("\n", strip=True)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)
    parser = VisibleTextHTMLParser()
    parser.feed(html)
    parser.close()
    return parser.get_text()


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        normalized = str(value or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique_values.append(normalized)
    return unique_values


def _split_artist_title_segments(title: str) -> list[str]:
    raw_title = str(title or "").strip()
    if not raw_title:
        return []
    segments = re.split(r"\s+(?:[-\u2013\u2014\|\u00b7])\s+|\s*:\s*", raw_title)
    return _dedupe_preserve_order([segment.strip() for segment in segments if str(segment or "").strip()])


def _extract_artist_page_identity_signals(html: str, text: str) -> dict[str, Any]:
    title = ""
    h1_texts: list[str] = []
    meta_titles: list[str] = []
    if BeautifulSoup is not None:
        soup = BeautifulSoup(html, "lxml")
        if soup.title:
            title = soup.title.get_text(" ", strip=True)
        for node in soup.find_all("h1")[:5]:
            value = node.get_text(" ", strip=True)
            if value:
                h1_texts.append(value)
        for key in ("og:title", "twitter:title"):
            node = soup.find(attrs={"property": key}) or soup.find(attrs={"name": key})
            if node and node.get("content"):
                meta_titles.append(str(node.get("content") or "").strip())
    else:
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html or "", flags=re.IGNORECASE | re.DOTALL)
        if title_match:
            title = re.sub(r"\s+", " ", title_match.group(1)).strip()
        h1_texts = [
            re.sub(r"<[^>]+>", " ", match.group(1))
            for match in re.finditer(r"<h1[^>]*>(.*?)</h1>", html or "", flags=re.IGNORECASE | re.DOTALL)
        ][:5]
        h1_texts = [re.sub(r"\s+", " ", value).strip() for value in h1_texts if str(value or "").strip()]
    body_first_lines = [
        re.sub(r"\s+", " ", line).strip()
        for line in str(text or "").splitlines()
        if str(line or "").strip()
    ][:30]
    return {
        "body_first_lines": body_first_lines,
        "h1_texts": _dedupe_preserve_order(h1_texts),
        "meta_titles": _dedupe_preserve_order(meta_titles),
        "title": str(title or "").strip(),
        "title_segments": _split_artist_title_segments(title),
    }


def _collect_text_marker_hits(lines: list[str], markers: frozenset[str]) -> list[str]:
    lowered_lines = [str(line or "").lower() for line in lines if str(line or "").strip()]
    hits: list[str] = []
    for marker in sorted(markers):
        if any(marker in line for line in lowered_lines):
            hits.append(marker)
    return hits


def _classify_artist_identity_name(name: str) -> dict[str, Any]:
    cleaned = _sanitize_artist_name_en(name)
    normalized = _normalize_artist_name_for_compare(cleaned)
    if not cleaned or not normalized:
        return {
            "cleaned_name": "",
            "invalid_reason": "LOW_CONFIDENCE_IDENTITY",
            "normalized_name": "",
            "score": 0,
            "strength": "invalid",
            "valid": False,
        }

    tokens = [token for token in normalized.split(" ") if token]
    non_connector_tokens = [token for token in tokens if token not in ARTIST_IDENTITY_CONNECTOR_TOKENS]
    if not non_connector_tokens:
        return {
            "cleaned_name": cleaned,
            "invalid_reason": "LOW_CONFIDENCE_IDENTITY",
            "normalized_name": normalized,
            "score": 0,
            "strength": "invalid",
            "valid": False,
        }

    if normalized in ARTIST_IDENTITY_INDEX_NAME_PHRASES:
        return {
            "cleaned_name": cleaned,
            "invalid_reason": "INDEX_LIKE_PAGE_REJECTED",
            "normalized_name": normalized,
            "score": 0,
            "strength": "invalid",
            "valid": False,
        }
    if normalized in ARTIST_IDENTITY_UTILITY_NAME_PHRASES:
        return {
            "cleaned_name": cleaned,
            "invalid_reason": "UTILITY_PAGE_REJECTED",
            "normalized_name": normalized,
            "score": 0,
            "strength": "invalid",
            "valid": False,
        }
    if _is_invalid_artist_name(cleaned):
        invalid_reason = (
            "INDEX_LIKE_PAGE_REJECTED"
            if all(token in {"archive", "article", "category", "index", "list", "php"} for token in non_connector_tokens)
            else "UTILITY_PAGE_REJECTED"
        )
        return {
            "cleaned_name": cleaned,
            "invalid_reason": invalid_reason,
            "normalized_name": normalized,
            "score": 0,
            "strength": "invalid",
            "valid": False,
        }

    letter_count = sum(1 for char in cleaned if unicodedata.category(char).startswith("L"))
    utility_token_hits = [token for token in non_connector_tokens if token in ARTIST_IDENTITY_NON_NAME_TOKENS]
    site_like_hits = [
        token
        for token in non_connector_tokens
        if token in {"art", "arts", "gallery", "project", "projects", "space", "studio"}
    ]

    score = 0
    if len(non_connector_tokens) >= 2:
        score += 30
    else:
        score += 10
    if letter_count >= 6:
        score += 12
    if letter_count >= 12:
        score += 4
    if len(non_connector_tokens) >= 3:
        score += 4
    if any(token in ARTIST_IDENTITY_CONNECTOR_TOKENS for token in tokens) or any(
        mark in str(cleaned or "") for mark in ("&", "+", "/")
    ):
        score += 4
    if len(non_connector_tokens) == 1 and len(non_connector_tokens[0]) < 5:
        score -= 8
    if utility_token_hits:
        score -= 18
    if site_like_hits and len(non_connector_tokens) <= 2:
        score -= 32

    recoverable = False
    if score >= 36:
        strength = "strong"
    elif score >= 18:
        strength = "weak"
    else:
        strength = "invalid"
        if (
            len(non_connector_tokens) == 1
            and letter_count >= 4
            and not utility_token_hits
            and not site_like_hits
            and normalized not in ARTIST_IDENTITY_INDEX_NAME_PHRASES
            and normalized not in ARTIST_IDENTITY_UTILITY_NAME_PHRASES
        ):
            recoverable = True

    return {
        "cleaned_name": cleaned,
        "invalid_reason": "" if strength != "invalid" else "LOW_CONFIDENCE_IDENTITY",
        "normalized_name": normalized,
        "recoverable": recoverable,
        "score": score,
        "strength": strength,
        "valid": strength != "invalid",
    }


def _build_artist_identity_value_variants(value: str) -> list[dict[str, str]]:
    raw_value = str(value or "").strip()
    cleaned = _sanitize_artist_name_en(raw_value)
    if not cleaned:
        return []

    variants: list[dict[str, str]] = [{"variant_type": "raw", "value": cleaned}]
    seen = {_normalize_artist_name_for_compare(cleaned)}

    def add_variant(candidate: str, variant_type: str) -> None:
        cleaned_candidate = _sanitize_artist_name_en(candidate)
        if not cleaned_candidate:
            return
        normalized_candidate = _normalize_artist_name_for_compare(cleaned_candidate)
        if not normalized_candidate or normalized_candidate in seen:
            return
        seen.add(normalized_candidate)
        variants.append({"variant_type": variant_type, "value": cleaned_candidate})

    without_parenthetical = re.sub(r"\s*\([^)]*\)\s*$", "", raw_value).strip(" ,;:-")
    add_variant(without_parenthetical, "trimmed")

    if "," in raw_value:
        add_variant(raw_value.split(",", 1)[0], "trimmed")

    without_year_tail = re.sub(
        r"[\s,;:/-]*(?:born|b\.|d\.)?\s*(?:18|19|20)\d{2}(?:\s*[-/\u2013\u2014]\s*(?:18|19|20)?\d{2})?\s*$",
        "",
        raw_value,
        flags=re.IGNORECASE,
    ).strip(" ,;:-")
    add_variant(without_year_tail, "trimmed")

    descriptor_rich = bool(
        re.search(r"[\(\),]", raw_value)
        or re.search(r"\b(?:18|19|20)\d{2}\b", raw_value)
    )
    if descriptor_rich:
        first_token = cleaned.split(" ", 1)[0].strip()
        if len(first_token) >= 4 and not _is_invalid_artist_name(first_token):
            add_variant(first_token, "trimmed")

    return variants


def _candidate_has_descriptor_tail(long_name: str, short_name: str) -> bool:
    long_tokens = [token for token in _normalize_artist_name_for_compare(long_name).split(" ") if token]
    short_tokens = [token for token in _normalize_artist_name_for_compare(short_name).split(" ") if token]
    if not long_tokens or not short_tokens or len(short_tokens) >= len(long_tokens):
        return False
    if long_tokens[: len(short_tokens)] != short_tokens:
        return False

    suffix_tokens = long_tokens[len(short_tokens) :]
    if not suffix_tokens:
        return False

    raw_long = str(long_name or "").strip()
    if re.search(r"[\(\),]", raw_long) or re.search(r"\b(?:18|19|20)\d{2}\b", raw_long):
        return True
    if len(short_tokens) == 1 and len(suffix_tokens) <= 3:
        return all(token not in ARTIST_IDENTITY_CONNECTOR_TOKENS for token in suffix_tokens)
    return False


def _promote_shorter_corroborated_artist_candidates(grouped_candidates: dict[str, dict[str, Any]]) -> None:
    candidates = list(grouped_candidates.values())
    for short_candidate in candidates:
        short_name = str(short_candidate.get("display_name") or "").strip()
        short_sources = set(str(source or "").strip() for source in short_candidate.get("sources", []) if source)
        if not short_name or len(short_sources) < 2:
            continue
        if int(short_candidate.get("page_source_score") or 0) < 24:
            continue

        for long_candidate in candidates:
            if long_candidate is short_candidate:
                continue
            long_name = str(long_candidate.get("display_name") or "").strip()
            if not long_name or not _candidate_has_descriptor_tail(long_name, short_name):
                continue
            corroboration_bonus = 12 + 6 * min(len(short_sources), 4)
            short_candidate["raw_score"] = int(short_candidate.get("raw_score") or 0) + corroboration_bonus
            if any(source in ARTIST_IDENTITY_STRONG_PAGE_SOURCES for source in short_sources):
                short_candidate["page_source_score"] = int(short_candidate.get("page_source_score") or 0) + min(
                    16, corroboration_bonus
                )
            break


def _build_artist_identity_name_rows(
    *,
    anchor_text: str,
    signals: dict[str, Any],
    source_url: str,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for value in signals.get("h1_texts", []):
        rows.append({"source": "h1", "value": str(value or "").strip()})
    for value in signals.get("meta_titles", []):
        rows.append({"source": "meta_title", "value": str(value or "").strip()})
    for value in signals.get("title_segments", []):
        rows.append({"source": "title", "value": str(value or "").strip()})
    if str(anchor_text or "").strip():
        rows.append({"source": "anchor", "value": str(anchor_text or "").strip()})
    slug_name = build_artist_name_en_from_source_url(source_url)
    if slug_name != "Unknown Artist":
        rows.append({"source": "slug", "value": slug_name})
    return rows


def _build_artist_identity_reason_detail(
    *,
    anchor_name: str,
    page_confidence: str,
    relation_confidence: str,
    relation_type: str,
    selected_artist_name: str,
    sources: list[str],
    utility_hits: list[str],
) -> str:
    parts: list[str] = []
    if selected_artist_name:
        parts.append(f"name={selected_artist_name}")
    if page_confidence:
        parts.append(f"page_confidence={page_confidence}")
    if relation_type:
        parts.append(f"relation={relation_type}")
    if relation_confidence:
        parts.append(f"relation_confidence={relation_confidence}")
    if sources:
        parts.append(f"sources={'+'.join(sources)}")
    if anchor_name:
        parts.append(f"anchor={anchor_name}")
    if utility_hits:
        parts.append(f"utility_hits={','.join(utility_hits[:4])}")
    return ";".join(parts)


def _evaluate_artist_identity_gate(
    *,
    anchor_text: str,
    html: str,
    is_explicit: bool,
    relation_confidence: str,
    relation_type: str,
    source_url: str,
    text: str,
) -> dict[str, Any]:
    signals = _extract_artist_page_identity_signals(html, text)
    body_first_lines = list(signals.get("body_first_lines", []))
    utility_hits = _collect_text_marker_hits(body_first_lines, ARTIST_IDENTITY_UTILITY_PAGE_MARKERS)
    hub_hits = _collect_text_marker_hits(body_first_lines[:12], ARTIST_IDENTITY_HUB_PAGE_MARKERS)
    name_rows = _build_artist_identity_name_rows(
        anchor_text=anchor_text,
        signals=signals,
        source_url=source_url,
    )

    grouped_candidates: dict[str, dict[str, Any]] = {}
    anchor_candidate: dict[str, Any] | None = None
    for row in name_rows:
        source = str(row.get("source") or "").strip()
        value = str(row.get("value") or "").strip()
        if not source or not value:
            continue
        row_seen_normalized: set[str] = set()
        for variant in _build_artist_identity_value_variants(value):
            candidate_value = str(variant.get("value") or "").strip()
            variant_type = str(variant.get("variant_type") or "raw").strip()
            if not candidate_value:
                continue
            classified = _classify_artist_identity_name(candidate_value)
            is_recoverable = bool(classified.get("recoverable")) and not bool(classified.get("valid"))
            if source == "anchor" and anchor_candidate is None and (classified.get("valid") or is_recoverable):
                anchor_candidate = classified
            if not classified.get("valid") and not is_recoverable:
                continue
            normalized_name = str(classified.get("normalized_name") or "").strip()
            if not normalized_name or normalized_name in row_seen_normalized:
                continue
            row_seen_normalized.add(normalized_name)

            candidate = grouped_candidates.get(normalized_name)
            if candidate is None:
                candidate = {
                    "display_name": str(classified.get("cleaned_name") or "").strip(),
                    "has_valid_support": False,
                    "normalized_name": normalized_name,
                    "page_source_score": 0,
                    "raw_score": 0,
                    "recoverable_source_count": 0,
                    "sources": [],
                    "strong_source_count": 0,
                }
                grouped_candidates[normalized_name] = candidate

            weight = int(ARTIST_IDENTITY_SOURCE_WEIGHTS.get(source, 0))
            strength_bonus = 14 if classified.get("strength") == "strong" else 4 if classified.get("strength") == "weak" else 0
            recoverable_penalty = 8 if is_recoverable else 0
            candidate["raw_score"] += max(0, int(classified.get("score") or 0) + weight + strength_bonus - recoverable_penalty)
            candidate["sources"].append(source)
            if source in ARTIST_IDENTITY_STRONG_PAGE_SOURCES:
                candidate["page_source_score"] += max(0, weight + strength_bonus - recoverable_penalty)
            if classified.get("strength") == "strong":
                candidate["strong_source_count"] += 1
            if classified.get("valid"):
                candidate["has_valid_support"] = True
            elif is_recoverable:
                candidate["recoverable_source_count"] += 1

            current_display_name = str(candidate.get("display_name") or "").strip()
            next_display_name = str(classified.get("cleaned_name") or "").strip()
            if not current_display_name:
                candidate["display_name"] = next_display_name
            elif source in ARTIST_IDENTITY_STRONG_PAGE_SOURCES:
                if variant_type == "trimmed" and len(next_display_name) < len(current_display_name):
                    candidate["display_name"] = next_display_name
                elif variant_type == "raw":
                    candidate["display_name"] = next_display_name

    grouped_candidates = {
        normalized_name: candidate
        for normalized_name, candidate in grouped_candidates.items()
        if candidate.get("has_valid_support")
        or (
            len(set(str(source or "").strip() for source in candidate.get("sources", []) if source)) >= 2
            and int(candidate.get("page_source_score") or 0) >= 24
        )
    }
    _promote_shorter_corroborated_artist_candidates(grouped_candidates)

    ranked_candidates = sorted(
        grouped_candidates.values(),
        key=lambda item: (
            -int(item.get("raw_score") or 0),
            -int(item.get("page_source_score") or 0),
            -int(item.get("strong_source_count") or 0),
            -len(set(item.get("sources") or [])),
            -len(str(item.get("display_name") or "")),
        ),
    )
    winner = ranked_candidates[0] if ranked_candidates else None
    anchor_name = (
        str(anchor_candidate.get("cleaned_name") or "").strip()
        if anchor_candidate and anchor_candidate.get("valid")
        else ""
    )
    anchor_normalized = (
        str(anchor_candidate.get("normalized_name") or "").strip()
        if anchor_candidate and anchor_candidate.get("valid")
        else ""
    )
    source_path = (urlparse(source_url).path or "").lower()
    source_index_like = (
        source_path.endswith(".php")
        or source_path.endswith("/index")
        or source_path.endswith("/article")
        or source_path.endswith("/category")
    )

    if winner is None:
        if len(utility_hits) >= 2:
            return {
                "identity_gate_verdict": "reject",
                "page_confidence": "none",
                "reason_code": "UTILITY_PAGE_REJECTED",
                "reason_detail": _build_artist_identity_reason_detail(
                    anchor_name=anchor_name,
                    page_confidence="none",
                    relation_confidence=relation_confidence,
                    relation_type=relation_type,
                    selected_artist_name="",
                    sources=[],
                    utility_hits=utility_hits,
                ),
                "selected_artist_name": "",
            }
        reject_reason = "INDEX_LIKE_PAGE_REJECTED" if source_index_like or len(hub_hits) >= 4 else "LOW_CONFIDENCE_IDENTITY"
        return {
            "identity_gate_verdict": "reject",
            "page_confidence": "none",
            "reason_code": reject_reason,
            "reason_detail": _build_artist_identity_reason_detail(
                anchor_name=anchor_name,
                page_confidence="none",
                relation_confidence=relation_confidence,
                relation_type=relation_type,
                selected_artist_name="",
                sources=[],
                utility_hits=utility_hits,
            ),
            "selected_artist_name": "",
        }

    winner_sources = list(dict.fromkeys(str(source or "").strip() for source in winner.get("sources", []) if source))
    selected_artist_name = str(winner.get("display_name") or "").strip()
    page_source_score = int(winner.get("page_source_score") or 0)
    raw_score = int(winner.get("raw_score") or 0)
    winner_normalized = str(winner.get("normalized_name") or "").strip()

    if raw_score >= 90 or page_source_score >= 60 or int(winner.get("strong_source_count") or 0) >= 2:
        page_confidence = "high"
    elif raw_score >= 40 or page_source_score >= 28:
        page_confidence = "medium"
    else:
        page_confidence = "low"

    if len(utility_hits) >= 2 and page_source_score < 60:
        return {
            "identity_gate_verdict": "reject",
            "page_confidence": page_confidence,
            "reason_code": "UTILITY_PAGE_REJECTED",
            "reason_detail": _build_artist_identity_reason_detail(
                anchor_name=anchor_name,
                page_confidence=page_confidence,
                relation_confidence=relation_confidence,
                relation_type=relation_type,
                selected_artist_name=selected_artist_name,
                sources=winner_sources,
                utility_hits=utility_hits,
            ),
            "selected_artist_name": "",
        }
    if source_index_like and page_source_score == 0:
        return {
            "identity_gate_verdict": "reject",
            "page_confidence": page_confidence,
            "reason_code": "INDEX_LIKE_PAGE_REJECTED",
            "reason_detail": _build_artist_identity_reason_detail(
                anchor_name=anchor_name,
                page_confidence=page_confidence,
                relation_confidence=relation_confidence,
                relation_type=relation_type,
                selected_artist_name=selected_artist_name,
                sources=winner_sources,
                utility_hits=utility_hits,
            ),
            "selected_artist_name": "",
        }
    if anchor_normalized and anchor_normalized != winner_normalized and page_source_score < 60:
        return {
            "identity_gate_verdict": "low-confidence",
            "page_confidence": "low",
            "reason_code": "ANCHOR_TITLE_NAME_MISMATCH",
            "reason_detail": _build_artist_identity_reason_detail(
                anchor_name=anchor_name,
                page_confidence="low",
                relation_confidence=relation_confidence,
                relation_type=relation_type,
                selected_artist_name=selected_artist_name,
                sources=winner_sources,
                utility_hits=utility_hits,
            ),
            "selected_artist_name": selected_artist_name,
        }
    if page_confidence == "low" and not (is_explicit and page_source_score >= 24):
        return {
            "identity_gate_verdict": "low-confidence",
            "page_confidence": page_confidence,
            "reason_code": "LOW_CONFIDENCE_IDENTITY",
            "reason_detail": _build_artist_identity_reason_detail(
                anchor_name=anchor_name,
                page_confidence=page_confidence,
                relation_confidence=relation_confidence,
                relation_type=relation_type,
                selected_artist_name=selected_artist_name,
                sources=winner_sources,
                utility_hits=utility_hits,
            ),
            "selected_artist_name": selected_artist_name,
        }

    return {
        "identity_gate_verdict": "accept",
        "page_confidence": page_confidence,
        "reason_code": "OK",
        "reason_detail": _build_artist_identity_reason_detail(
            anchor_name=anchor_name,
            page_confidence=page_confidence,
            relation_confidence=relation_confidence,
            relation_type=relation_type,
            selected_artist_name=selected_artist_name,
            sources=winner_sources,
            utility_hits=utility_hits,
        ),
        "selected_artist_name": selected_artist_name,
    }


def normalize_text_for_hash(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_url_for_hash(url: str) -> str:
    parsed = urlparse(url.strip())
    path = parsed.path or "/"
    normalized = f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{path}"
    return normalized.rstrip("/")


def compute_text_hash(text: str, source_url: str, rag_category: str = RAG_CATEGORY) -> str:
    normalized_text = normalize_text_for_hash(text)
    if normalized_text:
        payload = f"{rag_category}\n{normalized_text}"
    else:
        payload = f"{rag_category}\n{normalize_url_for_hash(source_url)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def artist_slug_from_source_url(source_url: str) -> str:
    artist_name_en = shared_build_artist_name_en_from_source_url(source_url)
    if artist_name_en == "Unknown Artist":
        return "artist"
    slug = re.sub(r"[^a-z0-9]+", "-", artist_name_en.lower()).strip("-")
    return slug or "artist"


def build_artist_name_en_from_source_url(source_url: str) -> str:
    artist_name_en = shared_build_artist_name_en_from_source_url(source_url)
    artist_name_en = _sanitize_artist_name_en(artist_name_en)
    if _is_invalid_artist_name(artist_name_en):
        return "Unknown Artist"
    return artist_name_en


def build_artist_name_key(artist_name_en: str, source_url: str) -> str:
    normalized_name = re.sub(r"\s+", " ", str(artist_name_en or "").strip().lower())
    if normalized_name and normalized_name != "unknown artist" and not _is_invalid_artist_name(normalized_name):
        seed = f"artist_name_en:{normalized_name}"
    else:
        seed = f"source_url:{normalize_url_for_hash(source_url)}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def build_artist_identity_key(artist_name_key: str, artist_name_en: str, source_url: str) -> str:
    normalized_key = str(artist_name_key or "").strip().lower()
    if normalized_key:
        return normalized_key
    return build_artist_name_key(artist_name_en, source_url).lower()


def _should_skip_artist_master_duplicate(
    existing_artist: dict[str, Any] | None,
    candidate_source_url: str,
) -> tuple[bool, str]:
    if existing_artist is None:
        return False, ""
    # Artist Text is first-write-wins across all fairs/galleries, including same-source yearly reruns.
    reason = shared_get_artist_master_duplicate_reason(
        existing_first_source_url=str(existing_artist.get("first_source_url") or ""),
        candidate_source_url=candidate_source_url,
    )
    return True, reason


def merge_artist_master_from_artists_raw(
    master: dict[str, dict[str, Any]],
    *,
    target_year: int,
    raw_dir: Path = RAW_DIR,
) -> None:
    for raw_path in sorted(raw_dir.glob(f"artists_*_{target_year}.jsonl")):
        rows = read_jsonl_rows(raw_path)
        for row in rows:
            if is_manual_seed_row(row):
                continue
            source_url = str(row.get("source_url") or "").strip()
            if not source_url:
                continue
            artist_name_en = str(row.get("artist_name_en") or "").strip() or build_artist_name_en_from_source_url(source_url)
            artist_name_key = str(row.get("artist_name_key") or "").strip() or build_artist_name_key(artist_name_en, source_url)
            identity_key = build_artist_identity_key(artist_name_key, artist_name_en, source_url)
            if identity_key in master:
                continue
            master[identity_key] = build_artist_master_entry(
                identity_key=identity_key,
                artist_name_key=artist_name_key,
                artist_name_en=artist_name_en,
                source_url=source_url,
                fair_slug=str(row.get("fair_slug") or ""),
                gallery_name_en=str(row.get("gallery_name_en") or ""),
                seen_at=str(row.get("extracted_at") or ""),
            )


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def compute_page_url_hash(url: str) -> str:
    return hashlib.sha256(normalize_url_for_hash(url).encode("utf-8")).hexdigest()


def load_existing_text_hashes(jsonl_path: Path) -> set[str]:
    hashes: set[str] = set()
    if not jsonl_path.exists():
        return hashes
    with jsonl_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            text_hash = row.get("text_hash")
            if isinstance(text_hash, str) and text_hash:
                hashes.add(text_hash)
    return hashes


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


def load_existing_exhibitions_rows(
    path: Path,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    rows = read_jsonl_rows(path)
    by_text_hash: dict[str, dict[str, Any]] = {}
    by_source_url: dict[str, dict[str, Any]] = {}
    for row in rows:
        canonical_source_url = canonicalize_exhibition_url(str(row.get("source_url") or ""))
        row["source_url"] = canonical_source_url
        text_hash = str(row.get("text_hash") or "").strip()
        row["sources"] = normalize_sources(row.get("sources"), fallback_source_url=canonical_source_url)
        if text_hash:
            by_text_hash[text_hash] = row
        if canonical_source_url:
            by_source_url[canonical_source_url] = row
    return rows, by_text_hash, by_source_url


def append_source_to_existing_record(
    *,
    by_text_hash: dict[str, dict[str, Any]],
    text_hash: str,
    source_url: str,
) -> bool:
    row = by_text_hash.get(text_hash)
    if row is None:
        return False
    row["sources"] = merge_sources(row.get("sources"), source_url)
    return True


def run_startup_manifest_min_sync() -> dict[str, Any]:
    return {
        "enabled": False,
        "status": "manual_sync_only_current_entry_run_r2_sync",
        "entrypoint": "run_r2_sync.py",
        "steps": [],
    }


def is_manual_seed_row(row: dict[str, Any]) -> bool:
    text = str(row.get("text") or "")
    return any(marker in text for marker in MANUAL_SEED_TEXT_MARKERS)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")


def append_unique(items: list[str], value: str) -> None:
    if value and value not in items:
        items.append(value)


def build_artists_enrichment_requests(
    *,
    raw_input_paths: dict[str, Path],
    output_path: Path,
) -> dict[str, Any]:
    return build_runtime_artists_enrichment_requests(
        raw_input_paths=raw_input_paths,
        output_path=output_path,
        target_year=TARGET_YEAR,
        rag_category=RAG_CATEGORY_ARTISTS,
    )


def parse_iso_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def should_skip_failed_url(entry: dict[str, Any], now: datetime) -> tuple[bool, str]:
    reason_code = str(entry.get("reason_code") or "REQUEST_ERROR")
    retry_count = int(entry.get("retry_count", 0))
    # DNS障害は環境要因の一時ブロッカーになりやすいため、
    # 回復後に即再試行できるよう max-retry / cooldown による恒久スキップを適用しない。
    if reason_code == "DNS_ERROR":
        return False, ""
    if reason_code in NON_RETRYABLE_FAILURE_REASON_CODES and retry_count >= 1:
        return True, "KNOWN_FAILED_URL_NON_RETRYABLE"
    if retry_count >= MAX_FAILURE_RETRIES_PER_URL:
        return True, "KNOWN_FAILED_URL_MAX_RETRIES"

    last_failed_at = parse_iso_utc(entry.get("last_failed_at"))
    if not last_failed_at:
        return False, ""
    elapsed = (now - last_failed_at).total_seconds()
    if elapsed < FAILURE_RETRY_COOLDOWN_SECONDS:
        return True, "KNOWN_FAILED_URL_COOLDOWN"
    return False, ""


def get_ledger_entry_with_canonical(
    ledger: dict[str, dict[str, Any]],
    *,
    url: str,
    canonical_url: str,
) -> tuple[dict[str, Any] | None, str, str]:
    page_hash = compute_page_url_hash(url)
    canonical_hash = compute_page_url_hash(canonical_url)
    entry = ledger.get(page_hash)
    if entry is not None:
        return entry, page_hash, canonical_hash
    if canonical_hash != page_hash:
        canonical_entry = ledger.get(canonical_hash)
        if canonical_entry is not None:
            return canonical_entry, page_hash, canonical_hash
    return None, page_hash, canonical_hash


def upsert_visited_page(
    ledger: dict[str, dict[str, Any]],
    *,
    url: str,
    fair_slug: str,
    gallery_name_en: str,
    decision: str,
    reason_code: str,
    reason_detail: str | None = None,
    parent_source_url: str | None = None,
    category: str = RAG_CATEGORY,
) -> dict[str, Any]:
    now = utc_now_iso()
    page_url_hash = compute_page_url_hash(url)
    prev = ledger.get(page_url_hash, {})
    record = {
        "page_url_hash": page_url_hash,
        "url": url,
        "fair_slug": fair_slug,
        "gallery_name_en": gallery_name_en,
        "decision": decision,
        "reason_code": reason_code,
        "target_year": TARGET_YEAR,
        "category": category,
        "first_seen": prev.get("first_seen", now),
        "last_seen": now,
    }
    if parent_source_url:
        record["parent_source_url"] = parent_source_url
    if reason_detail:
        record["reason_detail"] = reason_detail
    ledger[page_url_hash] = record
    return record


def upsert_visited_page_with_canonical_alias(
    ledger: dict[str, dict[str, Any]],
    *,
    url: str,
    canonical_url: str,
    fair_slug: str,
    gallery_name_en: str,
    decision: str,
    reason_code: str,
    reason_detail: str | None = None,
    parent_source_url: str | None = None,
    category: str = RAG_CATEGORY,
) -> dict[str, Any]:
    record = upsert_visited_page(
        ledger,
        url=url,
        fair_slug=fair_slug,
        gallery_name_en=gallery_name_en,
        decision=decision,
        reason_code=reason_code,
        reason_detail=reason_detail,
        parent_source_url=parent_source_url,
        category=category,
    )
    if canonical_url and normalize_url_for_hash(canonical_url) != normalize_url_for_hash(url):
        upsert_visited_page(
            ledger,
            url=canonical_url,
            fair_slug=fair_slug,
            gallery_name_en=gallery_name_en,
            decision=decision,
            reason_code=reason_code,
            reason_detail=reason_detail,
            parent_source_url=parent_source_url,
            category=category,
        )
    return record


def upsert_failed_fetch(
    ledger: dict[str, dict[str, Any]],
    *,
    kind: str,
    raw_url: str,
    parent_source_url: str | None,
    last_error: str,
    http_status: int | None,
    reason_code: str,
    reason_detail: str | None = None,
    category: str = RAG_CATEGORY,
) -> dict[str, Any]:
    now = utc_now_iso()
    fail_hash = compute_page_url_hash(raw_url)
    prev = ledger.get(fail_hash, {})
    retry_count = int(prev.get("retry_count", 0)) + 1
    record = {
        "fail_hash": fail_hash,
        "kind": kind,
        "raw_url": raw_url,
        "parent_source_url": parent_source_url,
        "last_error": last_error,
        "http_status": http_status,
        "retry_count": retry_count,
        "attempt_count": retry_count,
        "last_attempt_at": now,
        "first_failed_at": prev.get("first_failed_at", now),
        "last_failed_at": now,
        "reason_code": reason_code,
        "target_year": TARGET_YEAR,
        "category": category,
    }
    if reason_detail:
        record["reason_detail"] = reason_detail
    ledger[fail_hash] = record
    return record


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(errors="backslashreplace")
    args = parse_args()
    include_artists_text = bool(args.include_artists_text)
    max_artists_per_gallery = max(1, int(args.max_artists_per_gallery or MAX_ARTISTS_PER_GALLERY))
    policy_mode = skip_policy.resolve_run_mode(
        mode=args.mode,
        allow_rebuild=bool(args.allow_rebuild),
        run_id=str(args.run_id or ""),
    )
    output_root = OUTPUT_ROOT
    if policy_mode == skip_policy.REBUILD_MODE:
        output_root = skip_policy.build_trial_root(
            trial_root=args.trial_root,
            run_id=str(args.run_id or ""),
        )
    raw_dir = get_current_raw_dir(output_root) if policy_mode == skip_policy.REBUILD_MODE else get_current_raw_dir()
    log_dir = get_phase1_logs_dir(output_root)
    artist_master_global_path = get_phase1_artist_master_global_path(logs_dir=log_dir)

    raw_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    started_at = utc_now_iso()
    categories = [RAG_CATEGORY] + ([RAG_CATEGORY_ARTISTS] if include_artists_text else [])
    print(f"[START] Phase1 seed10 fetch ({'+'.join(categories)}) at {started_at} mode={policy_mode}")
    startup_min_sync_result = {"enabled": False, "status": "disabled_by_mode", "steps": []}
    if (not args.dry_run) and policy_mode == skip_policy.FILL_MISSING_MODE:
        startup_min_sync_result = run_startup_manifest_min_sync()
    if startup_min_sync_result.get("enabled"):
        print(f"[INFO] startup_min_sync status={startup_min_sync_result.get('status')}")

    seed_galleries: list[GallerySeed] = []
    if str(args.targets_csv or "").strip():
        targets_csv_path = Path(args.targets_csv)
        if not targets_csv_path.is_absolute():
            targets_csv_path = (Path.cwd() / targets_csv_path).resolve()
        seed_galleries = load_seed_galleries_from_targets_csv(targets_csv_path)
    else:
        for fair_slug, csv_path in CSV_PATHS.items():
            if not csv_path.exists():
                raise FileNotFoundError(f"Missing gallery CSV: {csv_path}")
            galleries = load_seed_galleries(csv_path=csv_path, fair_slug=fair_slug, limit=SEED_PER_FAIR)
            seed_galleries.extend(galleries)

    skipped_gallery_name_set = load_skipped_gallery_name_set(SKIPPED_GALLERIES_REGISTRY_PATH)
    seed_gallery_count_before_registry = len(seed_galleries)
    registry_skipped_gallery_names: list[str] = []
    if skipped_gallery_name_set:
        filtered_seed_galleries: list[GallerySeed] = []
        for gallery in seed_galleries:
            gallery_key = normalize_gallery_name_for_registry(gallery.gallery_name_en)
            if gallery_key in skipped_gallery_name_set:
                registry_skipped_gallery_names.append(gallery.gallery_name_en)
                continue
            filtered_seed_galleries.append(gallery)
        seed_galleries = filtered_seed_galleries

    print(
        "[INFO] Loaded seed galleries: "
        + ", ".join(
            f"{fair_slug}={sum(1 for g in seed_galleries if g.fair_slug == fair_slug)}"
            for fair_slug in CSV_PATHS
        )
    )
    if skipped_gallery_name_set:
        print(
            f"[INFO] skip_registry applied: before={seed_gallery_count_before_registry} "
            f"after={len(seed_galleries)} skipped={seed_gallery_count_before_registry - len(seed_galleries)}"
        )

    output_paths_by_fair = {
        fair_slug: get_current_raw_path(
            "exhibitions",
            fair_slug,
            TARGET_YEAR,
            root=output_root if policy_mode == skip_policy.REBUILD_MODE else None,
        )
        for fair_slug in CSV_PATHS
    }
    visited_pages_path = get_phase1_visited_pages_ledger_path("exhibitions", TARGET_YEAR, logs_dir=log_dir)
    failed_fetches_path = get_phase1_failed_fetches_ledger_path("exhibitions", TARGET_YEAR, logs_dir=log_dir)

    visited_pages_ledger = load_visited_pages_ledger(visited_pages_path, hash_fn=compute_page_url_hash)
    failed_fetches_ledger = load_phase1_failed_fetches_ledger(
        failed_fetches_path,
        hash_fn=compute_page_url_hash,
        reason_code_from_status=reason_code_from_status,
        reason_code_from_error_text=reason_code_from_error_text,
    )
    existing_exhibitions_rows_by_fair: dict[str, list[dict[str, Any]]] = {}
    existing_exhibitions_by_hash_by_fair: dict[str, dict[str, dict[str, Any]]] = {}
    existing_exhibitions_by_source_by_fair: dict[str, dict[str, dict[str, Any]]] = {}
    for fair_slug, output_path in output_paths_by_fair.items():
        rows, by_hash, by_source = load_existing_exhibitions_rows(output_path)
        existing_exhibitions_rows_by_fair[fair_slug] = rows
        existing_exhibitions_by_hash_by_fair[fair_slug] = by_hash
        existing_exhibitions_by_source_by_fair[fair_slug] = by_source
    existing_text_hashes_by_fair = {
        fair_slug: load_existing_text_hashes(output_path)
        for fair_slug, output_path in output_paths_by_fair.items()
    }

    records_by_fair: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen_hashes_by_fair: dict[str, set[str]] = {
        fair_slug: set(existing_text_hashes_by_fair.get(fair_slug, set()))
        for fair_slug in CSV_PATHS
    }
    skip_reason_counter: Counter[str] = Counter()
    failed_fetches_in_run: list[dict[str, Any]] = []
    exhibitions_feature_counter: Counter[str] = Counter()
    saved_source_urls_by_fair: dict[str, set[str]] = {
        fair_slug: set(existing_exhibitions_by_source_by_fair.get(fair_slug, {}).keys())
        for fair_slug in CSV_PATHS
    }

    print(
        f"[INFO] Loaded ledgers: visited={len(visited_pages_ledger)} "
        f"failed={len(failed_fetches_ledger)} "
        f"existing_text_hashes={sum(len(v) for v in existing_text_hashes_by_fair.values())}"
    )

    # artists_text は既存Exhibitions台帳を壊さないため、専用台帳を使う（最小差分）。
    artists_output_paths_by_fair = {
        fair_slug: get_current_raw_path(
            "artists",
            fair_slug,
            TARGET_YEAR,
            root=output_root if policy_mode == skip_policy.REBUILD_MODE else None,
        )
        for fair_slug in CSV_PATHS
    }
    artists_visited_pages_path = get_phase1_visited_pages_ledger_path("artists", TARGET_YEAR, logs_dir=log_dir)
    artists_failed_fetches_path = get_phase1_failed_fetches_ledger_path("artists", TARGET_YEAR, logs_dir=log_dir)
    artists_visited_ledger_exists_at_start = artists_visited_pages_path.exists()
    artists_failed_ledger_exists_at_start = artists_failed_fetches_path.exists()
    artist_master_global_exists_at_start = artist_master_global_path.exists()
    artists_visited_pages_ledger = load_visited_pages_ledger(artists_visited_pages_path, hash_fn=compute_page_url_hash)
    artists_failed_fetches_ledger = load_phase1_failed_fetches_ledger(
        artists_failed_fetches_path,
        hash_fn=compute_page_url_hash,
        reason_code_from_status=reason_code_from_status,
        reason_code_from_error_text=reason_code_from_error_text,
    )
    artists_existing_text_hashes_by_fair = {
        fair_slug: load_existing_text_hashes(output_path)
        for fair_slug, output_path in artists_output_paths_by_fair.items()
    }
    artists_records_by_fair: dict[str, list[dict[str, Any]]] = defaultdict(list)
    artists_seen_hashes_by_fair: dict[str, set[str]] = {
        fair_slug: set(artists_existing_text_hashes_by_fair.get(fair_slug, set()))
        for fair_slug in CSV_PATHS
    }
    artists_skip_reason_counter: Counter[str] = Counter()
    artists_failed_fetches_in_run: list[dict[str, Any]] = []
    artists_list_source_counter: Counter[str] = Counter()
    artists_candidate_fallback_counter: Counter[str] = Counter()
    artists_list_source_counter_by_fair: dict[str, Counter[str]] = {
        fair_slug: Counter() for fair_slug in CSV_PATHS
    }
    artist_master_global = load_artist_master_global(artist_master_global_path)
    merge_artist_master_from_artists_raw(
        artist_master_global,
        target_year=TARGET_YEAR,
        raw_dir=raw_dir,
    )
    artists_seen_identity_keys_in_run: set[str] = set()
    if include_artists_text:
        bootstrap_notes: list[str] = []
        if not artist_master_global_exists_at_start:
            bootstrap_notes.append("artist_master_global_missing_at_start")
        if not artists_visited_ledger_exists_at_start:
            bootstrap_notes.append("artists_visited_ledger_missing_at_start")
        if not artists_failed_ledger_exists_at_start:
            bootstrap_notes.append("artists_failed_ledger_missing_at_start")
        if bootstrap_notes:
            print(f"[WARN] Artists bootstrap state: {', '.join(bootstrap_notes)}")
        print(
            f"[INFO] Artists ledgers: visited={len(artists_visited_pages_ledger)} "
            f"failed={len(artists_failed_fetches_ledger)} "
            f"existing_text_hashes={sum(len(v) for v in artists_existing_text_hashes_by_fair.values())} "
            f"artist_master_global={len(artist_master_global)}"
        )

    if args.dry_run:
        existing_exhibitions_total = sum(len(v) for v in existing_text_hashes_by_fair.values())
        existing_artists_total = (
            sum(len(v) for v in artists_existing_text_hashes_by_fair.values())
            if include_artists_text
            else 0
        )
        candidate_total = existing_exhibitions_total + existing_artists_total
        dry_summary = {
            "runner": "run_phase1_seed10.py",
            "execution_mode": policy_mode,
            "dry_run": True,
            "include_artists_text": include_artists_text,
            "candidate_total": candidate_total,
            "would_skip_count": candidate_total,
            "would_fetch_count": 0,
            "would_write_count": 0,
            "key_present_but_file_missing_count": 0,
            "exhibitions_existing_text_hashes": existing_exhibitions_total,
            "artists_existing_text_hashes": existing_artists_total,
            "notes": ["dry_run_local_only_no_network_no_write"],
            "generated_at": utc_now_iso(),
        }
        dry_summary_path = (
            Path(args.dry_run_output)
            if str(args.dry_run_output or "").strip()
            else (log_dir / f"dryrun_run_phase1_seed10_{TARGET_YEAR}.json")
        )
        if not dry_summary_path.is_absolute():
            dry_summary_path = (Path.cwd() / dry_summary_path).resolve()
        write_json(dry_summary_path, dry_summary)
        print(f"[DRYRUN] summary={dry_summary_path}")
        return 0

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    for gallery in seed_galleries:
        list_url_hash = compute_page_url_hash(gallery.exhibitions_url)
        failed_list_entry = failed_fetches_ledger.get(list_url_hash)
        now = datetime.now(timezone.utc)
        if failed_list_entry is not None:
            should_skip, skip_reason = should_skip_failed_url(failed_list_entry, now)
            if should_skip:
                upsert_visited_page(
                    visited_pages_ledger,
                    url=gallery.exhibitions_url,
                    fair_slug=gallery.fair_slug,
                    gallery_name_en=gallery.gallery_name_en,
                    decision="skipped",
                    reason_code=skip_reason,
                )
                skip_reason_counter[skip_reason] += 1
                continue

        list_result = fetch_html(session, gallery.exhibitions_url)
        if not list_result["ok"]:
            list_reason_code = str(list_result.get("reason_code") or "LIST_FETCH_FAILED")
            failed_fetches_in_run.append(
                upsert_failed_fetch(
                    failed_fetches_ledger,
                    kind="page",
                    raw_url=gallery.exhibitions_url,
                    parent_source_url=None,
                    last_error=list_result["error"] or "LIST_FETCH_FAILED",
                    http_status=list_result["status_code"],
                    reason_code=list_reason_code,
                )
            )
            upsert_visited_page(
                visited_pages_ledger,
                url=gallery.exhibitions_url,
                fair_slug=gallery.fair_slug,
                gallery_name_en=gallery.gallery_name_en,
                decision="failed",
                reason_code=list_reason_code,
            )
            continue
        clear_failed_fetch(failed_fetches_ledger, gallery.exhibitions_url, hash_fn=compute_page_url_hash)

        list_page_url = list_result["final_url"]
        candidate_urls = extract_candidate_exhibition_urls(
            list_page_url=list_page_url,
            list_page_html=list_result["html"],
        )

        candidate_queue: list[dict[str, Any]] = [
            {"url": page_url, "parent_source_url": list_page_url, "depth": 0} for page_url in candidate_urls
        ]
        queued_page_hashes: set[str] = {compute_page_url_hash(str(item["url"])) for item in candidate_queue}

        while candidate_queue:
            queue_item = candidate_queue.pop(0)
            page_url = str(queue_item.get("url") or "")
            parent_source_url = str(queue_item.get("parent_source_url") or list_page_url)
            depth = int(queue_item.get("depth") or 0)
            page_url_hash = compute_page_url_hash(page_url)
            failed_page_entry = failed_fetches_ledger.get(page_url_hash)
            now = datetime.now(timezone.utc)
            if failed_page_entry is not None:
                should_skip, skip_reason = should_skip_failed_url(failed_page_entry, now)
                if should_skip:
                    upsert_visited_page(
                        visited_pages_ledger,
                        url=page_url,
                        fair_slug=gallery.fair_slug,
                        gallery_name_en=gallery.gallery_name_en,
                        decision="skipped",
                        reason_code=skip_reason,
                        parent_source_url=parent_source_url,
                    )
                    skip_reason_counter[skip_reason] += 1
                    continue

            previous_visit = visited_pages_ledger.get(page_url_hash)
            if previous_visit and previous_visit.get("decision") == "saved":
                upsert_visited_page(
                    visited_pages_ledger,
                    url=page_url,
                    fair_slug=gallery.fair_slug,
                    gallery_name_en=gallery.gallery_name_en,
                    decision="skipped",
                    reason_code="KNOWN_SAVED_PAGE",
                    parent_source_url=parent_source_url,
                )
                skip_reason_counter["KNOWN_SAVED_PAGE"] += 1
                continue

            page_result = fetch_html(session, page_url)
            if not page_result["ok"]:
                page_reason_code = str(page_result.get("reason_code") or "PAGE_FETCH_FAILED")
                failed_fetches_in_run.append(
                    upsert_failed_fetch(
                        failed_fetches_ledger,
                        kind="page",
                        raw_url=page_url,
                        parent_source_url=parent_source_url,
                        last_error=page_result["error"] or "PAGE_FETCH_FAILED",
                        http_status=page_result["status_code"],
                        reason_code=page_reason_code,
                    )
                )
                upsert_visited_page(
                    visited_pages_ledger,
                    url=page_url,
                    fair_slug=gallery.fair_slug,
                    gallery_name_en=gallery.gallery_name_en,
                    decision="failed",
                    reason_code=page_reason_code,
                    parent_source_url=parent_source_url,
                )
                continue

            source_url = canonicalize_exhibition_url(page_result["final_url"] or page_url)
            clear_failed_fetch(failed_fetches_ledger, page_url, hash_fn=compute_page_url_hash)
            clear_failed_fetch(failed_fetches_ledger, source_url, hash_fn=compute_page_url_hash)

            if _is_listing_like_exhibition_url(source_url) and depth < (MAX_EXHIBITION_LISTING_EXPANSION_DEPTH - 1):
                expanded_urls = extract_candidate_exhibition_urls(
                    list_page_url=source_url,
                    list_page_html=page_result["html"],
                )
                detail_enqueued = 0
                for expanded_url in expanded_urls:
                    expanded_canonical = canonicalize_exhibition_url(expanded_url)
                    expanded_hash = compute_page_url_hash(expanded_canonical)
                    if expanded_hash in queued_page_hashes:
                        continue
                    if expanded_canonical == source_url:
                        continue
                    if _is_listing_like_exhibition_url(expanded_canonical):
                        continue
                    queued_page_hashes.add(expanded_hash)
                    candidate_queue.append(
                        {
                            "url": expanded_canonical,
                            "parent_source_url": source_url,
                            "depth": depth + 1,
                        }
                    )
                    detail_enqueued += 1
                if detail_enqueued > 0:
                    upsert_visited_page(
                        visited_pages_ledger,
                        url=source_url,
                        fair_slug=gallery.fair_slug,
                        gallery_name_en=gallery.gallery_name_en,
                        decision="skipped",
                        reason_code="LISTING_EXPANDED_TO_DETAIL",
                        parent_source_url=parent_source_url,
                    )
                    skip_reason_counter["LISTING_EXPANDED_TO_DETAIL"] += 1
                    continue

            if has_explicit_non_target_year(source_url, TARGET_YEAR):
                upsert_visited_page(
                    visited_pages_ledger,
                    url=source_url,
                    fair_slug=gallery.fair_slug,
                    gallery_name_en=gallery.gallery_name_en,
                    decision="skipped",
                    reason_code="OUT_OF_YEAR",
                    parent_source_url=parent_source_url,
                )
                skip_reason_counter["OUT_OF_YEAR"] += 1
                continue
            if source_url in saved_source_urls_by_fair[gallery.fair_slug]:
                upsert_visited_page(
                    visited_pages_ledger,
                    url=source_url,
                    fair_slug=gallery.fair_slug,
                    gallery_name_en=gallery.gallery_name_en,
                    decision="skipped",
                    reason_code="KNOWN_SAVED_SOURCE_URL",
                    parent_source_url=parent_source_url,
                )
                skip_reason_counter["KNOWN_SAVED_SOURCE_URL"] += 1
                continue
            base_text = extract_text(page_result["html"])
            target_year_ok, year_reason = should_include_target_year_page(
                page_url=source_url,
                html=page_result["html"],
                target_year=TARGET_YEAR,
            )
            if not target_year_ok:
                upsert_visited_page(
                    visited_pages_ledger,
                    url=source_url,
                    fair_slug=gallery.fair_slug,
                    gallery_name_en=gallery.gallery_name_en,
                    decision="skipped",
                    reason_code="OUT_OF_YEAR",
                    parent_source_url=parent_source_url,
                )
                skip_reason_counter["OUT_OF_YEAR"] += 1
                continue

            participating_artists_line = extract_participating_artists_line(base_text)
            if participating_artists_line:
                exhibitions_feature_counter["participating_artists_appended"] += 1
            pdf_text, pdf_debug_rows = fetch_and_extract_pdf_text(
                session=session,
                page_url=source_url,
                html=page_result["html"],
            )
            if pdf_text:
                exhibitions_feature_counter["pdf_text_merged"] += 1
            text = merge_exhibition_text(
                base_text=base_text,
                participating_artists_line=participating_artists_line,
                pdf_text=pdf_text,
            )
            if not text:
                failed_fetches_in_run.append(
                    upsert_failed_fetch(
                        failed_fetches_ledger,
                        kind="page",
                        raw_url=source_url,
                        parent_source_url=parent_source_url,
                        last_error="EMPTY_TEXT",
                        http_status=page_result["status_code"],
                        reason_code="EMPTY_TEXT",
                    )
                )
                upsert_visited_page(
                    visited_pages_ledger,
                    url=source_url,
                    fair_slug=gallery.fair_slug,
                    gallery_name_en=gallery.gallery_name_en,
                    decision="failed",
                    reason_code="EMPTY_TEXT",
                    parent_source_url=parent_source_url,
                )
                continue

            date_info = extract_exhibition_dates(
                page_url=source_url,
                html=page_result["html"],
                extracted_text=text,
                target_year=TARGET_YEAR,
            )
            if date_info.get("exhibition_start_date") or date_info.get("exhibition_end_date"):
                exhibitions_feature_counter["date_fields_filled"] += 1
            text_hash = compute_text_hash(text=text, source_url=source_url)
            if text_hash in seen_hashes_by_fair[gallery.fair_slug]:
                duplicate_reason = (
                    "DUPLICATE_TEXT_HASH_EXISTING"
                    if text_hash in existing_text_hashes_by_fair.get(gallery.fair_slug, set())
                    else "DUPLICATE_TEXT_HASH_IN_RUN"
                )
                if not append_source_to_existing_record(
                    by_text_hash=existing_exhibitions_by_hash_by_fair[gallery.fair_slug],
                    text_hash=text_hash,
                    source_url=source_url,
                ):
                    for existing_row in reversed(records_by_fair.get(gallery.fair_slug, [])):
                        if str(existing_row.get("text_hash") or "") != text_hash:
                            continue
                        existing_row["sources"] = merge_sources(existing_row.get("sources"), source_url)
                        exhibitions_feature_counter["duplicate_sources_updated"] += 1
                        break
                else:
                    exhibitions_feature_counter["duplicate_sources_updated"] += 1
                upsert_visited_page(
                    visited_pages_ledger,
                    url=source_url,
                    fair_slug=gallery.fair_slug,
                    gallery_name_en=gallery.gallery_name_en,
                    decision="skipped",
                    reason_code=duplicate_reason,
                    parent_source_url=parent_source_url,
                )
                skip_reason_counter[duplicate_reason] += 1
                continue

            seen_hashes_by_fair[gallery.fair_slug].add(text_hash)
            record = {
                "gallery_name_en": gallery.gallery_name_en,
                "gallery_name_kana": gallery.gallery_name_kana,
                "source_url": source_url,
                "sources": normalize_sources([], fallback_source_url=source_url),
                "text": text,
                "text_hash": text_hash,
                "headline_ja": "",
                "summary_ja": "",
                "extracted_at": utc_now_iso(),
                "target_year": TARGET_YEAR,
                "exhibition_start_date": date_info["exhibition_start_date"],
                "exhibition_end_date": date_info["exhibition_end_date"],
                "date_source": date_info["date_source"],
                "date_confidence": date_info["date_confidence"],
                "participating_artists": participating_artists_line,
                "pdf_text_merged": bool(pdf_text),
                "pdf_text_chars": len(pdf_text),
                "pdf_debug": pdf_debug_rows[:3],
                "target_year_signal_reason": year_reason,
                "fair_slug": gallery.fair_slug,
                "rag_category": RAG_CATEGORY,
            }
            records_by_fair[gallery.fair_slug].append(record)
            saved_source_urls_by_fair[gallery.fair_slug].add(source_url)
            existing_exhibitions_by_source_by_fair[gallery.fair_slug][source_url] = record
            upsert_visited_page(
                visited_pages_ledger,
                url=source_url,
                fair_slug=gallery.fair_slug,
                gallery_name_en=gallery.gallery_name_en,
                decision="saved",
                reason_code="OK",
                parent_source_url=parent_source_url,
            )

    if include_artists_text:
        for gallery in seed_galleries:
            artists_saved_in_gallery = 0
            artists_list_url, artists_list_source = resolve_artists_list_url(gallery)
            artists_list_source_counter[artists_list_source] += 1
            artists_list_source_counter_by_fair[gallery.fair_slug][artists_list_source] += 1
            list_url_hash = compute_page_url_hash(artists_list_url)
            failed_list_entry = artists_failed_fetches_ledger.get(list_url_hash)
            now = datetime.now(timezone.utc)
            if failed_list_entry is not None:
                should_skip, skip_reason = should_skip_failed_url(failed_list_entry, now)
                if should_skip:
                    upsert_visited_page(
                        artists_visited_pages_ledger,
                        url=artists_list_url,
                        fair_slug=gallery.fair_slug,
                        gallery_name_en=gallery.gallery_name_en,
                        decision="skipped",
                        reason_code=skip_reason,
                        category=RAG_CATEGORY_ARTISTS,
                    )
                    artists_skip_reason_counter[skip_reason] += 1
                    continue

            list_result = fetch_html(session, artists_list_url)
            if not list_result["ok"]:
                list_reason_code = str(list_result.get("reason_code") or "LIST_FETCH_FAILED")
                artists_failed_fetches_in_run.append(
                    upsert_failed_fetch(
                        artists_failed_fetches_ledger,
                        kind="page",
                        raw_url=artists_list_url,
                        parent_source_url=None,
                        last_error=list_result["error"] or "LIST_FETCH_FAILED",
                        http_status=list_result["status_code"],
                        reason_code=list_reason_code,
                        category=RAG_CATEGORY_ARTISTS,
                    )
                )
                upsert_visited_page(
                    artists_visited_pages_ledger,
                    url=artists_list_url,
                    fair_slug=gallery.fair_slug,
                    gallery_name_en=gallery.gallery_name_en,
                    decision="failed",
                    reason_code=list_reason_code,
                    category=RAG_CATEGORY_ARTISTS,
                )
                continue
            clear_failed_fetch(artists_failed_fetches_ledger, artists_list_url, hash_fn=compute_page_url_hash)

            list_page_url = list_result["final_url"]
            candidate_urls, candidate_fallback_reason = extract_candidate_artist_urls(
                list_page_url=list_page_url,
                list_page_html=list_result["html"],
                max_artists_per_gallery=max_artists_per_gallery,
            )
            if candidate_fallback_reason:
                artists_candidate_fallback_counter[candidate_fallback_reason] += 1
            if not candidate_urls:
                no_detail_reason = "NO_ARTIST_DETAIL_LINKS"
                no_detail_reason_detail = str(candidate_fallback_reason or "").strip()
                artists_failed_fetches_in_run.append(
                    upsert_failed_fetch(
                        artists_failed_fetches_ledger,
                        kind="page",
                        raw_url=list_page_url,
                        parent_source_url=artists_list_url,
                        last_error=f"{no_detail_reason}:{no_detail_reason_detail}" if no_detail_reason_detail else no_detail_reason,
                        http_status=list_result["status_code"],
                        reason_code=no_detail_reason,
                        reason_detail=no_detail_reason_detail or None,
                        category=RAG_CATEGORY_ARTISTS,
                    )
                )
                upsert_visited_page(
                    artists_visited_pages_ledger,
                    url=list_page_url,
                    fair_slug=gallery.fair_slug,
                    gallery_name_en=gallery.gallery_name_en,
                    decision="failed",
                    reason_code=no_detail_reason,
                    reason_detail=no_detail_reason_detail or None,
                    parent_source_url=artists_list_url,
                    category=RAG_CATEGORY_ARTISTS,
                )
                continue

            for candidate in candidate_urls:
                if artists_saved_in_gallery >= max_artists_per_gallery:
                    break
                page_url = str(candidate.get("url") or "").strip()
                if not page_url:
                    continue
                candidate_anchor_text = str(candidate.get("anchor_text") or "").strip()
                candidate_relation_type = str(candidate.get("relation_type") or "").strip()
                candidate_relation_confidence = str(candidate.get("relation_confidence") or "").strip()
                candidate_is_explicit = bool(candidate.get("is_explicit"))
                current_artist_source = _canonical_artist_source_key(page_url)

                canonical_page_url = _canonicalize_artist_detail_url(page_url)
                failed_page_entry, page_url_hash, canonical_page_url_hash = get_ledger_entry_with_canonical(
                    artists_failed_fetches_ledger,
                    url=page_url,
                    canonical_url=canonical_page_url,
                )
                now = datetime.now(timezone.utc)
                if failed_page_entry is not None:
                    should_skip, skip_reason = should_skip_failed_url(failed_page_entry, now)
                    if should_skip:
                        upsert_visited_page_with_canonical_alias(
                            artists_visited_pages_ledger,
                            url=page_url,
                            canonical_url=canonical_page_url,
                            fair_slug=gallery.fair_slug,
                            gallery_name_en=gallery.gallery_name_en,
                            decision="skipped",
                            reason_code=skip_reason,
                            parent_source_url=list_page_url,
                            category=RAG_CATEGORY_ARTISTS,
                        )
                        artists_skip_reason_counter[skip_reason] += 1
                        continue

                previous_visit = (
                    artists_visited_pages_ledger.get(page_url_hash)
                    or artists_visited_pages_ledger.get(canonical_page_url_hash)
                )
                if previous_visit and previous_visit.get("decision") == "saved":
                    upsert_visited_page_with_canonical_alias(
                        artists_visited_pages_ledger,
                        url=page_url,
                        canonical_url=canonical_page_url,
                        fair_slug=gallery.fair_slug,
                        gallery_name_en=gallery.gallery_name_en,
                        decision="skipped",
                        reason_code="KNOWN_SAVED_PAGE",
                        parent_source_url=list_page_url,
                        category=RAG_CATEGORY_ARTISTS,
                    )
                    artists_skip_reason_counter["KNOWN_SAVED_PAGE"] += 1
                    continue

                page_result = fetch_html(session, page_url)
                if not page_result["ok"]:
                    page_reason_code = str(page_result.get("reason_code") or "PAGE_FETCH_FAILED")
                    artists_failed_fetches_in_run.append(
                        upsert_failed_fetch(
                            artists_failed_fetches_ledger,
                            kind="page",
                            raw_url=canonical_page_url,
                            parent_source_url=list_page_url,
                            last_error=page_result["error"] or "PAGE_FETCH_FAILED",
                            http_status=page_result["status_code"],
                            reason_code=page_reason_code,
                            category=RAG_CATEGORY_ARTISTS,
                        )
                    )
                    upsert_visited_page_with_canonical_alias(
                        artists_visited_pages_ledger,
                        url=page_url,
                        canonical_url=canonical_page_url,
                        fair_slug=gallery.fair_slug,
                        gallery_name_en=gallery.gallery_name_en,
                        decision="failed",
                        reason_code=page_reason_code,
                        parent_source_url=list_page_url,
                        category=RAG_CATEGORY_ARTISTS,
                    )
                    continue

                source_url = page_result["final_url"]
                canonical_source_url = _canonicalize_artist_detail_url(source_url)
                clear_failed_fetch(artists_failed_fetches_ledger, page_url, hash_fn=compute_page_url_hash)
                clear_failed_fetch(artists_failed_fetches_ledger, canonical_page_url, hash_fn=compute_page_url_hash)
                clear_failed_fetch(artists_failed_fetches_ledger, source_url, hash_fn=compute_page_url_hash)
                clear_failed_fetch(artists_failed_fetches_ledger, canonical_source_url, hash_fn=compute_page_url_hash)
                text = extract_text(page_result["html"])
                if not text:
                    artists_failed_fetches_in_run.append(
                        upsert_failed_fetch(
                            artists_failed_fetches_ledger,
                            kind="page",
                            raw_url=canonical_source_url,
                            parent_source_url=list_page_url,
                            last_error="EMPTY_TEXT",
                            http_status=page_result["status_code"],
                            reason_code="EMPTY_TEXT",
                            category=RAG_CATEGORY_ARTISTS,
                        )
                    )
                    upsert_visited_page_with_canonical_alias(
                        artists_visited_pages_ledger,
                        url=source_url,
                        canonical_url=canonical_source_url,
                        fair_slug=gallery.fair_slug,
                        gallery_name_en=gallery.gallery_name_en,
                        decision="failed",
                        reason_code="EMPTY_TEXT",
                        parent_source_url=list_page_url,
                        category=RAG_CATEGORY_ARTISTS,
                    )
                    continue

                identity_gate = _evaluate_artist_identity_gate(
                    anchor_text=candidate_anchor_text,
                    html=page_result["html"],
                    is_explicit=candidate_is_explicit,
                    relation_confidence=candidate_relation_confidence,
                    relation_type=candidate_relation_type,
                    source_url=source_url,
                    text=text,
                )
                identity_gate_verdict = str(identity_gate.get("identity_gate_verdict") or "").strip()
                identity_reason_code = str(identity_gate.get("reason_code") or "LOW_CONFIDENCE_IDENTITY").strip()
                identity_reason_detail = str(identity_gate.get("reason_detail") or "").strip()
                artist_name_en = str(identity_gate.get("selected_artist_name") or "").strip()
                if identity_gate_verdict != "accept" or not artist_name_en:
                    artists_failed_fetches_in_run.append(
                        upsert_failed_fetch(
                            artists_failed_fetches_ledger,
                            kind="page",
                            raw_url=canonical_source_url,
                            parent_source_url=list_page_url,
                            last_error=(
                                f"{identity_reason_code}:{identity_reason_detail}"
                                if identity_reason_detail
                                else identity_reason_code
                            ),
                            http_status=page_result["status_code"],
                            reason_code=identity_reason_code,
                            reason_detail=identity_reason_detail or None,
                            category=RAG_CATEGORY_ARTISTS,
                        )
                    )
                    upsert_visited_page_with_canonical_alias(
                        artists_visited_pages_ledger,
                        url=source_url,
                        canonical_url=canonical_source_url,
                        fair_slug=gallery.fair_slug,
                        gallery_name_en=gallery.gallery_name_en,
                        decision="failed",
                        reason_code=identity_reason_code,
                        reason_detail=identity_reason_detail or None,
                        parent_source_url=list_page_url,
                        category=RAG_CATEGORY_ARTISTS,
                    )
                    continue

                artist_name_key = build_artist_name_key(artist_name_en, source_url)
                artist_identity_key = build_artist_identity_key(artist_name_key, artist_name_en, source_url)
                existing_artist_after_fetch = artist_master_global.get(artist_identity_key)
                should_skip_existing_artist, existing_reason = _should_skip_artist_master_duplicate(
                    existing_artist=existing_artist_after_fetch,
                    candidate_source_url=source_url,
                )
                if should_skip_existing_artist:
                    upsert_visited_page_with_canonical_alias(
                        artists_visited_pages_ledger,
                        url=source_url,
                        canonical_url=canonical_source_url,
                        fair_slug=gallery.fair_slug,
                        gallery_name_en=gallery.gallery_name_en,
                        decision="skipped",
                        reason_code=existing_reason,
                        reason_detail=identity_reason_detail or None,
                        parent_source_url=list_page_url,
                        category=RAG_CATEGORY_ARTISTS,
                    )
                    artists_skip_reason_counter[existing_reason] += 1
                    continue
                if artist_identity_key in artists_seen_identity_keys_in_run:
                    upsert_visited_page_with_canonical_alias(
                        artists_visited_pages_ledger,
                        url=source_url,
                        canonical_url=canonical_source_url,
                        fair_slug=gallery.fair_slug,
                        gallery_name_en=gallery.gallery_name_en,
                        decision="skipped",
                        reason_code="DUPLICATE_ARTIST_GLOBAL_IN_RUN",
                        reason_detail=identity_reason_detail or None,
                        parent_source_url=list_page_url,
                        category=RAG_CATEGORY_ARTISTS,
                    )
                    artists_skip_reason_counter["DUPLICATE_ARTIST_GLOBAL_IN_RUN"] += 1
                    continue
                artists_seen_identity_keys_in_run.add(artist_identity_key)

                text_hash = compute_text_hash(
                    text=text,
                    source_url=source_url,
                    rag_category=RAG_CATEGORY_ARTISTS,
                )
                if text_hash in artists_seen_hashes_by_fair[gallery.fair_slug]:
                    duplicate_reason = (
                        "DUPLICATE_TEXT_HASH_EXISTING"
                        if text_hash in artists_existing_text_hashes_by_fair.get(gallery.fair_slug, set())
                        else "DUPLICATE_TEXT_HASH_IN_RUN"
                    )
                    upsert_visited_page_with_canonical_alias(
                        artists_visited_pages_ledger,
                        url=source_url,
                        canonical_url=canonical_source_url,
                        fair_slug=gallery.fair_slug,
                        gallery_name_en=gallery.gallery_name_en,
                        decision="skipped",
                        reason_code=duplicate_reason,
                        parent_source_url=list_page_url,
                        category=RAG_CATEGORY_ARTISTS,
                    )
                    artists_skip_reason_counter[duplicate_reason] += 1
                    continue

                artists_seen_hashes_by_fair[gallery.fair_slug].add(text_hash)
                record = {
                    "gallery_name_en": gallery.gallery_name_en,
                    "gallery_name_kana": gallery.gallery_name_kana,
                    "source_url": source_url,
                    "artist_name_en": artist_name_en,
                    "artist_name_key": artist_name_key,
                    "artist_identity_key": artist_identity_key,
                    "identity_gate_verdict": identity_gate_verdict,
                    "identity_reason_code": identity_reason_code,
                    "identity_reason_detail": identity_reason_detail,
                    "page_confidence": str(identity_gate.get("page_confidence") or "").strip(),
                    "candidate_anchor_text": candidate_anchor_text,
                    "candidate_relation_type": candidate_relation_type,
                    "candidate_relation_confidence": candidate_relation_confidence,
                    "text": text,
                    "text_hash": text_hash,
                    "headline_ja": "",
                    "summary_ja": "",
                    "extracted_at": utc_now_iso(),
                    "target_year": TARGET_YEAR,
                    "fair_slug": gallery.fair_slug,
                    "rag_category": RAG_CATEGORY_ARTISTS,
                }
                artists_records_by_fair[gallery.fair_slug].append(record)
                if artist_identity_key not in artist_master_global:
                    artist_master_global[artist_identity_key] = build_artist_master_entry(
                        identity_key=artist_identity_key,
                        artist_name_key=artist_name_key,
                        artist_name_en=artist_name_en,
                        source_url=source_url,
                        fair_slug=gallery.fair_slug,
                        gallery_name_en=gallery.gallery_name_en,
                        seen_at=str(record.get("extracted_at") or ""),
                    )
                upsert_visited_page_with_canonical_alias(
                    artists_visited_pages_ledger,
                    url=source_url,
                    canonical_url=canonical_source_url,
                    fair_slug=gallery.fair_slug,
                    gallery_name_en=gallery.gallery_name_en,
                    decision="saved",
                    reason_code="OK",
                    reason_detail=identity_reason_detail or None,
                    parent_source_url=list_page_url,
                    category=RAG_CATEGORY_ARTISTS,
                )
                artists_saved_in_gallery += 1

    output_files: dict[str, str] = {}
    for fair_slug in CSV_PATHS:
        output_path = output_paths_by_fair[fair_slug]
        if policy_mode == skip_policy.FILL_MISSING_MODE:
            append_jsonl(output_path, records_by_fair.get(fair_slug, []))
        else:
            merged_rows = list(existing_exhibitions_rows_by_fair.get(fair_slug, []))
            merged_rows.extend(records_by_fair.get(fair_slug, []))
            write_jsonl(output_path, merged_rows)
        output_files[fair_slug] = str(output_path)

    artists_output_files: dict[str, str] = {}
    if include_artists_text:
        for fair_slug in CSV_PATHS:
            output_path = artists_output_paths_by_fair[fair_slug]
            append_jsonl(output_path, artists_records_by_fair.get(fair_slug, []))
            artists_output_files[fair_slug] = str(output_path)
        save_artist_master_global(artist_master_global_path, artist_master_global)

    artists_enrichment_requests_path = get_enrichment_runtime_requests_path(
        "artists",
        TARGET_YEAR,
        root=output_root if policy_mode == skip_policy.REBUILD_MODE else None,
    )
    artists_enrichment_summary: dict[str, Any] = {
        "artists_enrichment_mode": "disabled",
        "artists_enrichment_candidates_total": 0,
        "artists_enrichment_requests_created": 0,
        "artists_enrichment_requests_output_path": "",
        "artists_enrichment_raw_records_total": 0,
        "artists_enrichment_raw_records_by_fair": {fair_slug: 0 for fair_slug in CSV_PATHS},
        "artists_enrichment_counters": {},
        "artists_enrichment_warnings": [],
    }
    if include_artists_text:
        artists_enrichment_summary = build_artists_enrichment_requests(
            raw_input_paths=artists_output_paths_by_fair,
            output_path=artists_enrichment_requests_path,
        )

    # SSOT 4-0-A に合わせ、台帳は hash をキーにした dict で保存する。
    save_failed_fetches_ledger(failed_fetches_path, failed_fetches_ledger)
    save_visited_pages_ledger(visited_pages_path, visited_pages_ledger)

    if include_artists_text:
        save_failed_fetches_ledger(artists_failed_fetches_path, artists_failed_fetches_ledger)
        save_visited_pages_ledger(artists_visited_pages_path, artists_visited_pages_ledger)

    completed_at = utc_now_iso()
    existing_records_total = sum(len(existing_text_hashes_by_fair.get(fair_slug, set())) for fair_slug in CSV_PATHS)
    new_records_saved_total = sum(len(v) for v in records_by_fair.values())
    records_total_after_run = existing_records_total + new_records_saved_total
    skipped_known_saved_page = int(skip_reason_counter.get("KNOWN_SAVED_PAGE", 0)) + int(
        skip_reason_counter.get("DUPLICATE_TEXT_HASH_EXISTING", 0)
    ) + int(skip_reason_counter.get("KNOWN_SAVED_SOURCE_URL", 0))
    skipped_out_of_year = int(skip_reason_counter.get("OUT_OF_YEAR", 0))
    artists_existing_records_total = sum(
        len(artists_existing_text_hashes_by_fair.get(fair_slug, set()))
        for fair_slug in CSV_PATHS
    )
    artists_new_records_saved_total = sum(len(v) for v in artists_records_by_fair.values())

    summary = {
        "started_at": started_at,
        "completed_at": completed_at,
        "target_year": TARGET_YEAR,
        "seed_per_fair": SEED_PER_FAIR,
        "targets_csv_path": str(args.targets_csv or ""),
        "targets_csv_used": bool(str(args.targets_csv or "").strip()),
        "html_parser_backend": "bs4_lxml" if BeautifulSoup is not None else "stdlib_html_parser_fallback",
        "max_exhibition_links_per_gallery": MAX_EXHIBITION_LINKS_PER_GALLERY,
        "max_artists_per_gallery": max_artists_per_gallery,
        "artists_per_gallery_cap_mode": "temporary_test_cap",
        "skip_registry_path": str(SKIPPED_GALLERIES_REGISTRY_PATH),
        "skip_registry_enabled": bool(skipped_gallery_name_set),
        "skip_registry_gallery_count": len(skipped_gallery_name_set),
        "seed_gallery_count_before_registry": seed_gallery_count_before_registry,
        "seed_gallery_count_after_registry": len(seed_galleries),
        "seed_gallery_registry_skipped_count": seed_gallery_count_before_registry - len(seed_galleries),
        "seed_gallery_registry_skipped_names": sorted(set(registry_skipped_gallery_names)),
        "startup_min_sync_enabled": bool(startup_min_sync_result.get("enabled")),
        "startup_min_sync_status": str(startup_min_sync_result.get("status") or ""),
        "startup_min_sync_steps": startup_min_sync_result.get("steps", []),
        "failure_retry_cooldown_seconds": FAILURE_RETRY_COOLDOWN_SECONDS,
        "max_failure_retries_per_url": MAX_FAILURE_RETRIES_PER_URL,
        "records_saved_total": new_records_saved_total,
        "existing_records_total": existing_records_total,
        "new_records_saved_total": new_records_saved_total,
        "records_total_after_run": records_total_after_run,
        "records_saved_by_fair": {fair_slug: len(records_by_fair.get(fair_slug, [])) for fair_slug in CSV_PATHS},
        "exhibitions_feature_counts": dict(exhibitions_feature_counter),
        "skipped_total": sum(skip_reason_counter.values()),
        "skipped_known_saved_page": skipped_known_saved_page,
        "skipped_out_of_year": skipped_out_of_year,
        "skipped_by_reason": dict(skip_reason_counter),
        "existing_text_hashes_by_fair": {
            fair_slug: len(existing_text_hashes_by_fair.get(fair_slug, set()))
            for fair_slug in CSV_PATHS
        },
        "output_files": output_files,
        "artists_enabled": include_artists_text,
        "artists_records_saved_total": artists_new_records_saved_total,
        "artists_existing_records_total": artists_existing_records_total,
        "artists_records_total_after_run": artists_existing_records_total + artists_new_records_saved_total,
        "artists_records_saved_by_fair": {
            fair_slug: len(artists_records_by_fair.get(fair_slug, []))
            for fair_slug in CSV_PATHS
        },
        "artists_skipped_total": sum(artists_skip_reason_counter.values()),
        "artists_skipped_by_reason": dict(artists_skip_reason_counter),
        "artists_list_source_counts": dict(artists_list_source_counter),
        "artists_candidate_fallback_counts": dict(artists_candidate_fallback_counter),
        "artists_list_source_counts_by_fair": {
            fair_slug: dict(artists_list_source_counter_by_fair.get(fair_slug, Counter()))
            for fair_slug in CSV_PATHS
        },
        "artists_list_url_artists_url_used": int(artists_list_source_counter.get("artists_url", 0)),
        "artists_list_url_exhibitions_fallback_used": int(
            artists_list_source_counter.get("exhibitions_url_fallback", 0)
        ),
        "artists_global_dedupe_scope": "all_fairs_all_galleries",
        "artists_global_dedupe_exhibitions_excluded": True,
        "phase1_7_mode": policy_mode,
        "phase1_7_allow_rebuild": bool(args.allow_rebuild),
        "phase1_7_run_id": str(args.run_id or ""),
        "phase1_7_trial_root": str(output_root),
        "artists_global_dedupe_in_run_seen_count": len(artists_seen_identity_keys_in_run),
        "artists_text_contract": "first_write_wins_global_no_refetch",
        "artists_text_same_source_yearly_refetch_enabled": False,
        "artists_existing_text_hashes_by_fair": {
            fair_slug: len(artists_existing_text_hashes_by_fair.get(fair_slug, set()))
            for fair_slug in CSV_PATHS
        },
        "artists_output_files": artists_output_files,
        "artists_visited_ledger_exists_at_start": bool(artists_visited_ledger_exists_at_start)
        if include_artists_text
        else False,
        "artists_failed_ledger_exists_at_start": bool(artists_failed_ledger_exists_at_start)
        if include_artists_text
        else False,
        "exhibitions_text_fair_breakdown": [],
        "exhibitions_text_gallery_breakdown": [],
        "exhibitions_text_seed_gallery_count": 0,
        "exhibitions_text_galleries_with_ge_1_record": 0,
        "exhibitions_text_success_rate_ge_1_record": 0.0,
        "exhibitions_text_success_rate_ge_1_record_pct": 0.0,
        "artists_text_fair_breakdown": [],
        "artists_text_gallery_breakdown": [],
        "artists_text_seed_gallery_count": 0,
        "artists_text_galleries_with_ge_1_record": 0,
        "artists_text_success_rate_ge_1_record": 0.0,
        "artists_text_success_rate_ge_1_record_pct": 0.0,
    }
    update_failed_fetches_summary(
        summary,
        path=failed_fetches_path,
        ledger=failed_fetches_ledger,
        new_in_run=len(failed_fetches_in_run),
    )
    update_visited_pages_summary(
        summary,
        path=visited_pages_path,
        ledger=visited_pages_ledger,
    )
    update_failed_fetches_summary(
        summary,
        path=artists_failed_fetches_path if include_artists_text else None,
        ledger=artists_failed_fetches_ledger,
        new_in_run=len(artists_failed_fetches_in_run),
        prefix="artists_",
    )
    update_visited_pages_summary(
        summary,
        path=artists_visited_pages_path if include_artists_text else None,
        ledger=artists_visited_pages_ledger,
        prefix="artists_",
    )
    update_artist_master_summary(
        summary,
        path=artist_master_global_path if include_artists_text else None,
        master=artist_master_global,
        exists_at_start=bool(artist_master_global_exists_at_start) if include_artists_text else False,
    )

    exhibitions_fair_breakdown, exhibitions_gallery_breakdown = build_text_category_breakdown(
        category=RAG_CATEGORY,
        seed_galleries=seed_galleries,
        records_by_fair=records_by_fair,
    )
    exhibitions_seed_gallery_count = sum(int(row.get("target_gallery_count") or 0) for row in exhibitions_fair_breakdown)
    exhibitions_success_gallery_count = sum(
        int(row.get("successful_gallery_count") or 0) for row in exhibitions_fair_breakdown
    )
    exhibitions_success_rate = (
        exhibitions_success_gallery_count / exhibitions_seed_gallery_count if exhibitions_seed_gallery_count > 0 else 0.0
    )
    summary["exhibitions_text_fair_breakdown"] = exhibitions_fair_breakdown
    summary["exhibitions_text_gallery_breakdown"] = exhibitions_gallery_breakdown
    summary["exhibitions_text_seed_gallery_count"] = exhibitions_seed_gallery_count
    summary["exhibitions_text_galleries_with_ge_1_record"] = exhibitions_success_gallery_count
    summary["exhibitions_text_success_rate_ge_1_record"] = round(exhibitions_success_rate, 6)
    summary["exhibitions_text_success_rate_ge_1_record_pct"] = round(exhibitions_success_rate * 100.0, 2)

    if include_artists_text:
        artists_fair_breakdown, artists_gallery_breakdown = build_text_category_breakdown(
            category=RAG_CATEGORY_ARTISTS,
            seed_galleries=seed_galleries,
            records_by_fair=artists_records_by_fair,
        )
        artists_seed_gallery_count = sum(int(row.get("target_gallery_count") or 0) for row in artists_fair_breakdown)
        artists_success_gallery_count = sum(int(row.get("successful_gallery_count") or 0) for row in artists_fair_breakdown)
        artists_success_rate = (
            artists_success_gallery_count / artists_seed_gallery_count if artists_seed_gallery_count > 0 else 0.0
        )
        summary["artists_text_fair_breakdown"] = artists_fair_breakdown
        summary["artists_text_gallery_breakdown"] = artists_gallery_breakdown
        summary["artists_text_seed_gallery_count"] = artists_seed_gallery_count
        summary["artists_text_galleries_with_ge_1_record"] = artists_success_gallery_count
        summary["artists_text_success_rate_ge_1_record"] = round(artists_success_rate, 6)
        summary["artists_text_success_rate_ge_1_record_pct"] = round(artists_success_rate * 100.0, 2)

    summary["notes"] = summary.get("notes", [])
    if isinstance(summary["notes"], list):
        summary["notes"].append("text_breakdown_mode=fair_and_gallery_with_records_and_success_rate_pct")
        summary["notes"].append("artists_source_rule=artist_list_url_to_artist_detail_pages_only")
        summary["notes"].append("artists_global_dedupe_scope=all_fairs_all_galleries")
        summary["notes"].append("artists_global_dedupe_exhibitions_excluded=true")
        summary["notes"].append("artists_text_contract=first_write_wins_global_no_refetch")

    summary.update(artists_enrichment_summary)
    summary_path = get_phase1_run_summary_path(TARGET_YEAR, logs_dir=log_dir)
    write_json(summary_path, summary)

    print(
        f"[DONE] Phase1 seed10 fetch complete. saved={summary['records_saved_total']} "
        f"failed_new={summary['failed_fetches_new_in_run']} skipped={summary['skipped_total']}"
    )
    print(
        "[DONE] "
        f"existing={summary['existing_records_total']}, "
        f"new_saved={summary['new_records_saved_total']}, "
        f"records_total_after_run={summary['records_total_after_run']}, "
        f"skipped_known_saved={summary['skipped_known_saved_page']}, "
        f"skipped_out_of_year={summary['skipped_out_of_year']}"
    )
    print(
        "[BREAKDOWN][exhibitions_text] "
        f"galleries_with_ge1={summary['exhibitions_text_galleries_with_ge_1_record']}/"
        f"{summary['exhibitions_text_seed_gallery_count']} "
        f"success_rate={summary['exhibitions_text_success_rate_ge_1_record']:.4f} "
        f"({summary['exhibitions_text_success_rate_ge_1_record_pct']:.2f}%)"
    )
    if summary["exhibitions_text_gallery_breakdown"]:
        print("[BREAKDOWN][exhibitions_text][gallery]")
        for row in summary["exhibitions_text_gallery_breakdown"]:
            print(
                "  - "
                f"{row.get('fair_slug')}/{row.get('gallery_name_en')}: "
                f"records={row.get('records_saved_total')} "
                f"ge1={row.get('successful_gallery_count')} "
                f"rate={row.get('success_rate_ge_1_record')} "
                f"({row.get('success_rate_ge_1_record_pct')}%)"
            )
    if summary["skipped_by_reason"]:
        reason_parts = [f"{key}={value}" for key, value in sorted(summary["skipped_by_reason"].items())]
        print(f"[DONE] skip_breakdown: {' '.join(reason_parts)}")
    if include_artists_text:
        print(
            "[DONE][artists] "
            f"saved={summary['artists_records_saved_total']} "
            f"failed_new={summary['artists_failed_fetches_new_in_run']} "
            f"skipped={summary['artists_skipped_total']}"
        )
        if summary["artists_skipped_by_reason"]:
            artists_reason_parts = [
                f"{key}={value}" for key, value in sorted(summary["artists_skipped_by_reason"].items())
            ]
            print(f"[DONE][artists] skip_breakdown: {' '.join(artists_reason_parts)}")
        print(
            "[DONE][artists] "
            f"artists_url_used={summary['artists_list_url_artists_url_used']} "
            f"exhibitions_fallback_used={summary['artists_list_url_exhibitions_fallback_used']}"
        )
        print(
            "[BREAKDOWN][artists_text] "
            f"galleries_with_ge1={summary['artists_text_galleries_with_ge_1_record']}/"
            f"{summary['artists_text_seed_gallery_count']} "
            f"success_rate={summary['artists_text_success_rate_ge_1_record']:.4f} "
            f"({summary['artists_text_success_rate_ge_1_record_pct']:.2f}%)"
        )
        if summary["artists_text_gallery_breakdown"]:
            print("[BREAKDOWN][artists_text][gallery]")
            for row in summary["artists_text_gallery_breakdown"]:
                print(
                    "  - "
                    f"{row.get('fair_slug')}/{row.get('gallery_name_en')}: "
                    f"records={row.get('records_saved_total')} "
                    f"ge1={row.get('successful_gallery_count')} "
                    f"rate={row.get('success_rate_ge_1_record')} "
                    f"({row.get('success_rate_ge_1_record_pct')}%)"
                )
        print(
            "[DONE][artists_enrichment] "
            f"mode={summary['artists_enrichment_mode']} "
            f"candidates={summary['artists_enrichment_candidates_total']} "
            f"requests_created={summary['artists_enrichment_requests_created']}"
        )
        if summary["artists_enrichment_requests_output_path"]:
            print(f"[DONE][artists_enrichment] requests={summary['artists_enrichment_requests_output_path']}")
    sync_status = "manual_sync_only" if policy_mode == skip_policy.FILL_MISSING_MODE else "skipped_by_mode"
    print(f"[SYNC] status={sync_status} entrypoint=run_r2_sync.py scope_hint=raw_current_primary")
    print(f"[DONE] summary={summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
