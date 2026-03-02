#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import ParseResult, urljoin, urlparse

import requests
from phase1_artist_link_utils import (
    ARTIST_LINK_KEYWORDS,
    canonicalize_artist_detail_url as shared_canonicalize_artist_detail_url,
    looks_like_artist_detail_url as shared_looks_like_artist_detail_url,
    looks_like_artist_listing_url as shared_looks_like_artist_listing_url,
    normalize_url_for_link_compare as shared_normalize_url_for_link_compare,
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
from r2_auto_sync import auto_sync_after_job, format_auto_sync_brief
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
MAX_EXHIBITION_LINKS_PER_GALLERY = 10
MAX_EXHIBITION_LISTING_EXPANSION_DEPTH = 2
# TEMPORARY TEST CAP:
# User-requested operational override for stability testing.
# SSOT default target remains 80, but current runs are intentionally capped to 5 per gallery.
MAX_ARTISTS_PER_GALLERY = 80
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

OUTPUT_ROOT = Path("data/phase1_seed10")
RAW_DIR = OUTPUT_ROOT / "raw"
LOG_DIR = OUTPUT_ROOT / "logs"
DERIVED_DIR = OUTPUT_ROOT / "derived"
ARTIST_MASTER_GLOBAL_PATH = LOG_DIR / "artist_master_global.json"
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

ARTIST_URL_NON_NAME_SEGMENTS = {
    "artist",
    "artists",
    "works",
    "work",
    "biography",
    "bio",
    "profile",
    "about",
    "overview",
    "detail",
    "details",
    "viewing-room",
    "viewingroom",
    "index",
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


def _score_artist_detail_url_quality(url: str) -> int:
    return shared_score_artist_detail_url_quality(url)


def _looks_like_exhibition_link(candidate_url: str, anchor_text: str) -> bool:
    target = f"{candidate_url.lower()} {anchor_text.lower()}"
    return any(keyword in target for keyword in LINK_KEYWORDS)


def _path_segments_from_url(url: str) -> list[str]:
    path = urlparse(url).path or ""
    return [segment for segment in path.lower().split("/") if segment]


def _is_listing_like_exhibition_url(url: str) -> bool:
    segments = _path_segments_from_url(url)
    if not segments:
        return True
    last = segments[-1]
    if last in EXHIBITION_LISTING_PATH_SEGMENTS:
        return True
    if len(segments) >= 2 and segments[-2] == "category":
        return True
    return False


def _is_probable_exhibition_detail_url(url: str) -> bool:
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
    return shared_looks_like_artist_detail_url(
        candidate_url=candidate_url,
        list_page_url=list_page_url,
        anchor_text=anchor_text,
        same_domain_required=False,
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
        if not _looks_like_exhibition_link(absolute_url, anchor_text):
            continue
        normalized = canonicalize_exhibition_url(absolute_url)
        score = _score_exhibition_url_quality(normalized, anchor_text)
        previous = best_by_canonical.get(normalized)
        if previous is None or score > previous[0]:
            best_by_canonical[normalized] = (score, normalized)

    if not best_by_canonical:
        return [list_page_url]

    ranked = sorted(best_by_canonical.values(), key=lambda item: (-item[0], item[1]))
    return [url for _score, url in ranked[:MAX_EXHIBITION_LINKS_PER_GALLERY]]


def extract_candidate_artist_urls(
    list_page_url: str,
    list_page_html: str,
    max_artists_per_gallery: int,
) -> list[str]:
    candidates: list[str] = []
    candidate_scores: list[int] = []
    seen_by_canonical: dict[str, int] = {}
    # Cap should be applied on "saved artists", not on first discovered links.
    # For small caps (e.g. 1 in initial smoke), scan a wider window to avoid
    # stopping at already-saved duplicates.
    candidate_scan_limit = min(200, max(max_artists_per_gallery, max_artists_per_gallery * 20))
    listing_context = _looks_like_artist_listing_url(list_page_url)

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
        anchor_text = anchor_text_raw.lower()
        target = f"{absolute_url.lower()} {anchor_text}"
        if not listing_context and not any(keyword in target for keyword in ARTIST_LINK_KEYWORDS):
            continue
        if not _looks_like_artist_detail_link(absolute_url, list_page_url, anchor_text_raw):
            continue
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")
        if parsed.query:
            normalized = f"{normalized}?{parsed.query}"
        canonical_url = _canonicalize_artist_detail_url(normalized)
        quality_score = _score_artist_detail_url_quality(normalized)
        existing_index = seen_by_canonical.get(canonical_url)
        if existing_index is not None:
            if quality_score > candidate_scores[existing_index]:
                candidates[existing_index] = normalized
                candidate_scores[existing_index] = quality_score
            continue
        seen_by_canonical[canonical_url] = len(candidates)
        candidates.append(normalized)
        candidate_scores.append(quality_score)
        if len(candidates) >= candidate_scan_limit:
            break

    return candidates


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
    candidate = re.sub(r"[^a-z0-9]+", "-", candidate.strip().lower()).strip("-")
    return candidate or "artist"


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
        seed = f"source_url:{normalize_url_for_hash(source_url)}"
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
    payload = read_json(path)
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


def merge_artist_master_from_artists_raw(master: dict[str, dict[str, Any]], *, target_year: int) -> None:
    for raw_path in sorted(RAW_DIR.glob(f"artists_*_{target_year}.jsonl")):
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
    payload = {
        "schema_name": "artist_master_global",
        "schema_version": "v1",
        "generated_at": utc_now_iso(),
        "records": sorted(master.values(), key=lambda x: str(x.get("artist_identity_key") or "")),
    }
    write_json(path, payload)


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
    result: dict[str, Any] = {
        "enabled": STARTUP_MIN_SYNC_ENABLED,
        "status": "disabled",
        "steps": [],
    }
    if not STARTUP_MIN_SYNC_ENABLED:
        return result

    py_exec = sys.executable
    dry_cmd = [py_exec, "run_phase1_seed10_r2_sync.py", "--scope", "raw", "--dry-run"]
    apply_cmd = [py_exec, "run_phase1_seed10_r2_sync.py", "--scope", "raw", "--require-dry-run-log"]
    for name, cmd in (("dry_run", dry_cmd), ("apply", apply_cmd)):
        proc = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        step = {
            "name": name,
            "command": cmd,
            "exit_code": int(proc.returncode),
            "stdout_tail": [line for line in (proc.stdout or "").splitlines() if line.strip()][-20:],
            "stderr_tail": [line for line in (proc.stderr or "").splitlines() if line.strip()][-20:],
        }
        result["steps"].append(step)
        if proc.returncode != 0:
            result["status"] = f"failed_{name}"
            return result

    result["status"] = "ok"
    return result


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
    counters: Counter[str] = Counter()
    warnings: list[str] = []
    raw_records_by_fair: dict[str, int] = {}
    candidates_by_hash: dict[str, dict[str, Any]] = {}

    for fair_slug, raw_path in raw_input_paths.items():
        if not raw_path.exists():
            warnings.append(f"missing_raw_input:{fair_slug}:{raw_path}")
            raw_records_by_fair[fair_slug] = 0
            continue

        rows = read_jsonl_rows(raw_path)
        raw_records_by_fair[fair_slug] = len(rows)
        for row in rows:
            text_hash = str(row.get("text_hash") or "").strip()
            if not text_hash:
                counters["skipped_missing_text_hash"] += 1
                continue

            text = str(row.get("text") or "").strip()
            if not text:
                counters["skipped_empty_text"] += 1
                continue

            headline_ja = str(row.get("headline_ja") or "").strip()
            summary_ja = str(row.get("summary_ja") or "").strip()

            needs_fields: list[str] = []
            if not headline_ja:
                needs_fields.append("headline_ja")
            if not summary_ja:
                needs_fields.append("summary_ja")
            if not needs_fields:
                counters["skipped_already_enriched"] += 1
                continue

            source_url = str(row.get("source_url") or "").strip()
            existing = candidates_by_hash.get(text_hash)
            if existing is None:
                candidates_by_hash[text_hash] = {
                    "text_hash": text_hash,
                    "fair_slug": fair_slug,
                    "gallery_name_en": str(row.get("gallery_name_en") or ""),
                    "gallery_name_kana": str(row.get("gallery_name_kana") or ""),
                    "target_year": int(row.get("target_year") or TARGET_YEAR),
                    "rag_category": str(row.get("rag_category") or RAG_CATEGORY_ARTISTS),
                    "source_urls": [source_url] if source_url else [],
                    "needs_fields": list(needs_fields),
                    "text_length": len(text),
                    "text": text,
                }
                counters["candidates_new"] += 1
                continue

            counters["candidates_merged_by_text_hash"] += 1
            append_unique(existing["source_urls"], source_url)
            for field_name in needs_fields:
                append_unique(existing["needs_fields"], field_name)

    request_rows: list[dict[str, Any]] = []
    for text_hash in sorted(candidates_by_hash):
        candidate = candidates_by_hash[text_hash]
        request_rows.append(
            {
                "request_id": f"seed10_artists_enrich_{text_hash}",
                "text_hash": candidate["text_hash"],
                "fair_slug": candidate["fair_slug"],
                "gallery_name_en": candidate["gallery_name_en"],
                "gallery_name_kana": candidate["gallery_name_kana"],
                "source_urls": candidate["source_urls"],
                "target_year": candidate["target_year"],
                "rag_category": candidate["rag_category"],
                "needs_fields": candidate["needs_fields"],
                "text_length": candidate["text_length"],
                "text": candidate["text"],
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_path, request_rows)

    return {
        "artists_enrichment_mode": "post_fetch_requests_only",
        "artists_enrichment_candidates_total": len(request_rows),
        "artists_enrichment_requests_created": len(request_rows),
        "artists_enrichment_requests_output_path": str(output_path),
        "artists_enrichment_raw_records_total": sum(raw_records_by_fair.values()),
        "artists_enrichment_raw_records_by_fair": raw_records_by_fair,
        "artists_enrichment_counters": dict(counters),
        "artists_enrichment_warnings": warnings,
    }


def load_visited_pages_ledger(path: Path) -> dict[str, dict[str, Any]]:
    raw = read_json(path)
    ledger: dict[str, dict[str, Any]] = {}
    entries: list[dict[str, Any]]
    if isinstance(raw, list):
        entries = [x for x in raw if isinstance(x, dict)]
    elif isinstance(raw, dict):
        entries = [x for x in raw.values() if isinstance(x, dict)]
    else:
        entries = []

    for entry in entries:
        url = entry.get("url") or entry.get("raw_url")
        page_url_hash = entry.get("page_url_hash")
        if not isinstance(page_url_hash, str) or not page_url_hash:
            if isinstance(url, str) and url:
                page_url_hash = compute_page_url_hash(url)
            else:
                continue
        normalized = dict(entry)
        normalized["page_url_hash"] = page_url_hash
        ledger[page_url_hash] = normalized
    return ledger


def load_failed_fetches_ledger(path: Path) -> dict[str, dict[str, Any]]:
    raw = read_json(path)
    ledger: dict[str, dict[str, Any]] = {}
    entries: list[dict[str, Any]]
    if isinstance(raw, list):
        entries = [x for x in raw if isinstance(x, dict)]
    elif isinstance(raw, dict):
        entries = [x for x in raw.values() if isinstance(x, dict)]
    else:
        entries = []

    for entry in entries:
        raw_url = entry.get("raw_url")
        fail_hash = entry.get("fail_hash")
        if not isinstance(fail_hash, str) or not fail_hash:
            if isinstance(raw_url, str) and raw_url:
                fail_hash = compute_page_url_hash(raw_url)
            else:
                continue
        normalized = dict(entry)
        normalized["fail_hash"] = fail_hash
        if "attempt_count" not in normalized and "retry_count" in normalized:
            normalized["attempt_count"] = normalized.get("retry_count")
        if "last_attempt_at" not in normalized and "last_failed_at" in normalized:
            normalized["last_attempt_at"] = normalized.get("last_failed_at")
        reason_code = str(normalized.get("reason_code") or "")
        if reason_code in {"LIST_FETCH_FAILED", "PAGE_FETCH_FAILED", "REQUEST_ERROR"}:
            status_code = normalized.get("http_status")
            if isinstance(status_code, int):
                normalized["reason_code"] = reason_code_from_status(status_code)
            else:
                normalized["reason_code"] = reason_code_from_error_text(str(normalized.get("last_error") or ""))
        ledger[fail_hash] = normalized
    return ledger


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


def clear_failed_fetch(ledger: dict[str, dict[str, Any]], raw_url: str) -> None:
    fail_hash = compute_page_url_hash(raw_url)
    ledger.pop(fail_hash, None)


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

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    DERIVED_DIR.mkdir(parents=True, exist_ok=True)

    started_at = utc_now_iso()
    categories = [RAG_CATEGORY] + ([RAG_CATEGORY_ARTISTS] if include_artists_text else [])
    print(f"[START] Phase1 seed10 fetch ({'+'.join(categories)}) at {started_at}")
    startup_min_sync_result = run_startup_manifest_min_sync()
    if startup_min_sync_result.get("enabled"):
        print(f"[INFO] startup_min_sync status={startup_min_sync_result.get('status')}")

    seed_galleries: list[GallerySeed] = []
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
        fair_slug: RAW_DIR / f"exhibitions_{fair_slug}_{TARGET_YEAR}.jsonl"
        for fair_slug in CSV_PATHS
    }
    visited_pages_path = LOG_DIR / f"visited_pages_seed10_{TARGET_YEAR}.json"
    failed_fetches_path = LOG_DIR / f"failed_fetches_seed10_{TARGET_YEAR}.json"

    visited_pages_ledger = load_visited_pages_ledger(visited_pages_path)
    failed_fetches_ledger = load_failed_fetches_ledger(failed_fetches_path)
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
        fair_slug: RAW_DIR / f"artists_{fair_slug}_{TARGET_YEAR}.jsonl"
        for fair_slug in CSV_PATHS
    }
    artists_visited_pages_path = LOG_DIR / f"visited_pages_artists_seed10_{TARGET_YEAR}.json"
    artists_failed_fetches_path = LOG_DIR / f"failed_fetches_artists_seed10_{TARGET_YEAR}.json"
    artists_visited_pages_ledger = load_visited_pages_ledger(artists_visited_pages_path)
    artists_failed_fetches_ledger = load_failed_fetches_ledger(artists_failed_fetches_path)
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
    artists_list_source_counter_by_fair: dict[str, Counter[str]] = {
        fair_slug: Counter() for fair_slug in CSV_PATHS
    }
    artist_master_global = load_artist_master_global(ARTIST_MASTER_GLOBAL_PATH)
    merge_artist_master_from_artists_raw(artist_master_global, target_year=TARGET_YEAR)
    artists_seen_identity_keys_in_run: set[str] = set()
    if include_artists_text:
        print(
            f"[INFO] Artists ledgers: visited={len(artists_visited_pages_ledger)} "
            f"failed={len(artists_failed_fetches_ledger)} "
            f"existing_text_hashes={sum(len(v) for v in artists_existing_text_hashes_by_fair.values())} "
            f"artist_master_global={len(artist_master_global)}"
        )

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
        clear_failed_fetch(failed_fetches_ledger, gallery.exhibitions_url)

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
            clear_failed_fetch(failed_fetches_ledger, page_url)
            clear_failed_fetch(failed_fetches_ledger, source_url)

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
            clear_failed_fetch(artists_failed_fetches_ledger, artists_list_url)

            list_page_url = list_result["final_url"]
            candidate_urls = extract_candidate_artist_urls(
                list_page_url=list_page_url,
                list_page_html=list_result["html"],
                max_artists_per_gallery=max_artists_per_gallery,
            )
            if not candidate_urls:
                no_detail_reason = "NO_ARTIST_DETAIL_LINKS"
                artists_failed_fetches_in_run.append(
                    upsert_failed_fetch(
                        artists_failed_fetches_ledger,
                        kind="page",
                        raw_url=list_page_url,
                        parent_source_url=artists_list_url,
                        last_error=no_detail_reason,
                        http_status=list_result["status_code"],
                        reason_code=no_detail_reason,
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
                    parent_source_url=artists_list_url,
                    category=RAG_CATEGORY_ARTISTS,
                )
                continue

            for page_url in candidate_urls:
                if artists_saved_in_gallery >= max_artists_per_gallery:
                    break
                artist_name_en_candidate = build_artist_name_en_from_source_url(page_url)
                artist_name_key_candidate = build_artist_name_key(artist_name_en_candidate, page_url)
                artist_identity_key_candidate = build_artist_identity_key(
                    artist_name_key_candidate,
                    artist_name_en_candidate,
                    page_url,
                )
                existing_artist = artist_master_global.get(artist_identity_key_candidate)
                existing_artist_source = (
                    _canonicalize_artist_detail_url(str(existing_artist.get("first_source_url") or ""))
                    if existing_artist is not None
                    else ""
                )
                current_artist_source = _canonicalize_artist_detail_url(page_url)
                if existing_artist is not None and existing_artist_source and existing_artist_source != current_artist_source:
                    upsert_visited_page_with_canonical_alias(
                        artists_visited_pages_ledger,
                        url=page_url,
                        canonical_url=current_artist_source,
                        fair_slug=gallery.fair_slug,
                        gallery_name_en=gallery.gallery_name_en,
                        decision="skipped",
                        reason_code="DUPLICATE_ARTIST_GLOBAL_EXISTING",
                        parent_source_url=list_page_url,
                        category=RAG_CATEGORY_ARTISTS,
                    )
                    artists_skip_reason_counter["DUPLICATE_ARTIST_GLOBAL_EXISTING"] += 1
                    continue
                if artist_identity_key_candidate in artists_seen_identity_keys_in_run:
                    upsert_visited_page_with_canonical_alias(
                        artists_visited_pages_ledger,
                        url=page_url,
                        canonical_url=current_artist_source,
                        fair_slug=gallery.fair_slug,
                        gallery_name_en=gallery.gallery_name_en,
                        decision="skipped",
                        reason_code="DUPLICATE_ARTIST_GLOBAL_IN_RUN",
                        parent_source_url=list_page_url,
                        category=RAG_CATEGORY_ARTISTS,
                    )
                    artists_skip_reason_counter["DUPLICATE_ARTIST_GLOBAL_IN_RUN"] += 1
                    continue
                artists_seen_identity_keys_in_run.add(artist_identity_key_candidate)

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
                artist_name_en = build_artist_name_en_from_source_url(source_url)
                artist_name_key = build_artist_name_key(artist_name_en, source_url)
                artist_identity_key = build_artist_identity_key(artist_name_key, artist_name_en, source_url)
                clear_failed_fetch(artists_failed_fetches_ledger, page_url)
                clear_failed_fetch(artists_failed_fetches_ledger, canonical_page_url)
                clear_failed_fetch(artists_failed_fetches_ledger, source_url)
                clear_failed_fetch(artists_failed_fetches_ledger, canonical_source_url)
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
                existing_master = artist_master_global.get(artist_identity_key)
                if existing_master is None:
                    artist_master_global[artist_identity_key] = _build_artist_master_entry(
                        identity_key=artist_identity_key,
                        artist_name_key=artist_name_key,
                        artist_name_en=artist_name_en,
                        source_url=source_url,
                        fair_slug=gallery.fair_slug,
                        gallery_name_en=gallery.gallery_name_en,
                        seen_at=str(record.get("extracted_at") or ""),
                    )
                else:
                    existing_master["artist_name_en"] = artist_name_en
                    existing_master["artist_name_key"] = artist_name_key
                    existing_master["updated_at"] = str(record.get("extracted_at") or "")
                    artist_master_global[artist_identity_key] = existing_master
                upsert_visited_page_with_canonical_alias(
                    artists_visited_pages_ledger,
                    url=source_url,
                    canonical_url=canonical_source_url,
                    fair_slug=gallery.fair_slug,
                    gallery_name_en=gallery.gallery_name_en,
                    decision="saved",
                    reason_code="OK",
                    parent_source_url=list_page_url,
                    category=RAG_CATEGORY_ARTISTS,
                )
                artists_saved_in_gallery += 1

    output_files: dict[str, str] = {}
    for fair_slug in CSV_PATHS:
        output_path = output_paths_by_fair[fair_slug]
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
        write_artist_master_global(ARTIST_MASTER_GLOBAL_PATH, artist_master_global)

    artists_enrichment_requests_path = DERIVED_DIR / f"artists_enrichment_requests_{TARGET_YEAR}.jsonl"
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
    failed_fetches_for_save = {
        fail_hash: failed_fetches_ledger[fail_hash]
        for fail_hash in sorted(failed_fetches_ledger)
    }
    visited_pages_for_save = {
        page_url_hash: visited_pages_ledger[page_url_hash]
        for page_url_hash in sorted(visited_pages_ledger)
    }

    write_json(
        failed_fetches_path,
        failed_fetches_for_save,
    )
    write_json(
        visited_pages_path,
        visited_pages_for_save,
    )

    artists_failed_fetches_for_save = {
        fail_hash: artists_failed_fetches_ledger[fail_hash]
        for fail_hash in sorted(artists_failed_fetches_ledger)
    }
    artists_visited_pages_for_save = {
        page_url_hash: artists_visited_pages_ledger[page_url_hash]
        for page_url_hash in sorted(artists_visited_pages_ledger)
    }
    if include_artists_text:
        write_json(
            artists_failed_fetches_path,
            artists_failed_fetches_for_save,
        )
        write_json(
            artists_visited_pages_path,
            artists_visited_pages_for_save,
        )

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
        "failed_fetches_new_in_run": len(failed_fetches_in_run),
        "failed_fetches_total_ledger": len(failed_fetches_ledger),
        "failed_fetches_reason_counts": dict(Counter(x.get("reason_code", "UNKNOWN") for x in failed_fetches_ledger.values())),
        "exhibitions_feature_counts": dict(exhibitions_feature_counter),
        "visited_pages_total_ledger": len(visited_pages_ledger),
        "skipped_total": sum(skip_reason_counter.values()),
        "skipped_known_saved_page": skipped_known_saved_page,
        "skipped_out_of_year": skipped_out_of_year,
        "skipped_by_reason": dict(skip_reason_counter),
        "existing_text_hashes_by_fair": {
            fair_slug: len(existing_text_hashes_by_fair.get(fair_slug, set()))
            for fair_slug in CSV_PATHS
        },
        "output_files": output_files,
        "failed_fetches_path": str(failed_fetches_path),
        "visited_pages_path": str(visited_pages_path),
        "artists_enabled": include_artists_text,
        "artists_records_saved_total": artists_new_records_saved_total,
        "artists_existing_records_total": artists_existing_records_total,
        "artists_records_total_after_run": artists_existing_records_total + artists_new_records_saved_total,
        "artists_records_saved_by_fair": {
            fair_slug: len(artists_records_by_fair.get(fair_slug, []))
            for fair_slug in CSV_PATHS
        },
        "artists_failed_fetches_new_in_run": len(artists_failed_fetches_in_run),
        "artists_failed_fetches_total_ledger": len(artists_failed_fetches_ledger),
        "artists_failed_fetches_reason_counts": dict(
            Counter(x.get("reason_code", "UNKNOWN") for x in artists_failed_fetches_ledger.values())
        ),
        "artists_visited_pages_total_ledger": len(artists_visited_pages_ledger),
        "artists_skipped_total": sum(artists_skip_reason_counter.values()),
        "artists_skipped_by_reason": dict(artists_skip_reason_counter),
        "artists_list_source_counts": dict(artists_list_source_counter),
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
        "artist_master_global_path": str(ARTIST_MASTER_GLOBAL_PATH),
        "artist_master_global_record_count": len(artist_master_global),
        "artists_global_dedupe_in_run_seen_count": len(artists_seen_identity_keys_in_run),
        "artists_existing_text_hashes_by_fair": {
            fair_slug: len(artists_existing_text_hashes_by_fair.get(fair_slug, set()))
            for fair_slug in CSV_PATHS
        },
        "artists_output_files": artists_output_files,
        "artists_failed_fetches_path": str(artists_failed_fetches_path) if include_artists_text else "",
        "artists_visited_pages_path": str(artists_visited_pages_path) if include_artists_text else "",
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

    summary.update(artists_enrichment_summary)
    summary_path = LOG_DIR / f"run_summary_seed10_{TARGET_YEAR}.json"
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
    auto_sync_result = auto_sync_after_job(
        target="phase1_all",
        trigger="run_phase1_seed10.py",
    )
    print(format_auto_sync_brief(auto_sync_result))
    print(f"[DONE] summary={summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
