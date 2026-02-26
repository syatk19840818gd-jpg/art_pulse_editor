#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import socket
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from requests.adapters import HTTPAdapter

try:
    from urllib3.util.retry import Retry
except Exception:  # pragma: no cover - fallback if urllib3 retry API changes
    Retry = None

SOURCE_CLI = "run_phase1_seed10_artist_image_collect.py"
TARGET_YEAR_DEFAULT = 2025
TARGET_IMAGES_PER_ARTIST_DEFAULT = 5
SUCCESS_THRESHOLD_DEFAULT = 0.70
# TEMPORARY TEST CAP:
# Keep image collection target list aligned with current artists extraction cap (1 per gallery).
MAX_ARTISTS_PER_GALLERY_FOR_COLLECT = 1
REQUEST_TIMEOUT_SECONDS = 15
USER_AGENT = "art-pulse-editor/phase1-seed10-artist-image-collect"
REQUEST_RETRY_TOTAL = 2
REQUEST_RETRY_BACKOFF_FACTOR = 0.3
DNS_PROBE_HOST = "example.com"

RAW_DIR = Path("data/phase1_seed10/raw")
LOG_DIR = Path("data/phase1_seed10/logs")
IMAGE_ROOT_DIR = Path("data/phase1_seed10/derived/images/artist_works_images")

SCHEMA_NAME = "phase1_seed10_artist_image_collect_summary"
SCHEMA_VERSION = "v1"
ARTIFACT_KIND = "phase1_seed10_artist_image_collect_summary"

REJECT_TOKENS = (
    "logo",
    "icon",
    "avatar",
    "portrait",
    "hero",
    "banner",
    "favicon",
    "sprite",
    "placeholder",
    "loading",
    "spacer",
    "profile",
)

POSITIVE_TOKENS = (
    "artwork",
    "artworks",
    "work",
    "works",
    "painting",
    "sculpture",
    "installation",
    "exhibition",
    "artist",
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

DISALLOWED_EXTENSIONS = {".svg", ".gif", ".ico"}
CONTENT_TYPE_TO_EXTENSION = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/avif": ".avif",
}

IMG_TAG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
A_TAG_RE = re.compile(r"<a\b[^>]*>", re.IGNORECASE)
ATTR_RE = re.compile(r"""([A-Za-z_:][-A-Za-z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+))""")

ARTIST_LINK_KEYWORDS = (
    "artist",
    "artists",
    "roster",
    "bio",
    "biography",
)

ARTIST_LIST_PATH_PATTERNS = (
    "/artist",
    "/artists",
    "/artists/",
    "/list-of-artists",
    "/artist-list",
    "/category/artist",
    "/category/artists",
)


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
    parser.add_argument("--output-json", default="", help="optional summary output path")
    return parser.parse_args()


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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


def build_artist_id(row: dict[str, Any]) -> str:
    text_hash = str(row.get("text_hash") or "").strip()
    if text_hash:
        return text_hash
    source_url = str(row.get("source_url") or "").strip()
    return hashlib.sha256(source_url.encode("utf-8")).hexdigest()


def load_artist_targets(target_year: int) -> list[dict[str, Any]]:
    grouped_rows: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    targets: list[dict[str, Any]] = []

    def _is_listing_url(url: str) -> bool:
        path = (urlparse(url).path or "").lower().rstrip("/")
        if not path:
            return False
        return any(path.endswith(pattern.rstrip("/")) for pattern in ARTIST_LIST_PATH_PATTERNS)

    for raw_path in sorted(RAW_DIR.glob(f"artists_*_{target_year}.jsonl")):
        rows = read_jsonl_rows(raw_path)
        fair_slug = str(raw_path.name.replace(f"artists_", "").replace(f"_{target_year}.jsonl", ""))
        for row in rows:
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
            if has_detail_row and _is_listing_url(source_url):
                continue
            row = item.get("row") or {}
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
                    "source_url": source_url,
                }
            )
            added_for_gallery += 1
    return targets


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


def artist_slug_from_source_url(source_url: str) -> str:
    parsed = urlparse(source_url)
    path = (parsed.path or "").strip("/")
    if not path:
        return "artist"
    parts = [part for part in path.split("/") if part]
    if not parts:
        return "artist"
    candidate = parts[-1]
    if not candidate and len(parts) >= 2:
        candidate = parts[-2]
    return slugify_token(candidate, fallback="artist")


def normalize_url_for_link_compare(url: str) -> str:
    parsed = urlparse(url)
    normalized = f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{parsed.path}".rstrip("/")
    if parsed.query:
        normalized = f"{normalized}?{parsed.query}"
    return normalized


def looks_like_artist_listing_url(url: str) -> bool:
    path = (urlparse(url).path or "").lower().rstrip("/")
    if not path:
        return False
    return any(path.endswith(pattern.rstrip("/")) for pattern in ARTIST_LIST_PATH_PATTERNS)


def looks_like_artist_detail_url(candidate_url: str, list_page_url: str) -> bool:
    candidate_norm = normalize_url_for_link_compare(candidate_url)
    list_norm = normalize_url_for_link_compare(list_page_url)
    if candidate_norm == list_norm:
        return False
    if looks_like_artist_listing_url(candidate_url):
        return False
    if normalize_domain(candidate_url) != normalize_domain(list_page_url):
        return False

    candidate_path = (urlparse(candidate_url).path or "").lower().rstrip("/")
    list_path = (urlparse(list_page_url).path or "").lower().rstrip("/")
    if not candidate_path:
        return False
    if list_path and "artist" in list_path and candidate_path.startswith(f"{list_path}/"):
        return True
    if "/artist/" in candidate_path or "/artists/" in candidate_path:
        return True
    return False


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


def extract_artist_detail_urls(list_page_url: str, html: str, max_links: int = 80) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()
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
                str(attrs.get("title") or "").lower(),
                str(attrs.get("aria-label") or "").lower(),
                str(attrs.get("class") or "").lower(),
            ]
        )
        if not any(keyword in target for keyword in ARTIST_LINK_KEYWORDS):
            continue
        if not looks_like_artist_detail_url(absolute_url, list_page_url):
            continue
        seen.add(normalized)
        candidates.append(normalized)
        if len(candidates) >= max_links:
            break
    return candidates


def extract_works_candidate_urls(detail_url: str, detail_html: str, max_links: int = 12) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()

    def _append(url: str) -> None:
        normalized = normalize_url_for_link_compare(url)
        if not normalized or normalized in seen:
            return
        seen.add(normalized)
        candidates.append(url)

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
        _append(absolute_url)
        if len(candidates) >= max_links:
            break

    parsed_detail = urlparse(detail_url)
    detail_path = (parsed_detail.path or "").rstrip("/")
    if not detail_path.endswith("/works"):
        works_url = parsed_detail._replace(path=f"{detail_path}/works").geturl()
        _append(works_url)
    else:
        _append(detail_url)

    return candidates[:max_links]


def should_reject_image_candidate(candidate_url: str, attrs: dict[str, str], parent_name: str) -> tuple[bool, int]:
    url_lower = candidate_url.lower()
    parsed = urlparse(candidate_url)
    ext = Path(parsed.path).suffix.lower()
    if ext in DISALLOWED_EXTENSIONS:
        return True, -10

    alt_text = str(attrs.get("alt") or "").lower()
    class_text = str(attrs.get("class") or "").lower()
    combined = f"{url_lower} {alt_text} {class_text} {parent_name}".strip()

    if any(token in combined for token in REJECT_TOKENS):
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

    for match in IMG_TAG_RE.finditer(html):
        tag_html = match.group(0)
        attrs = parse_img_attrs(tag_html)
        candidate_values: list[str] = []
        for attr_name in ("src", "data-src", "data-original", "data-lazy-src"):
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
            absolute_url = urljoin(page_url, raw_value)
            parsed = urlparse(absolute_url)
            if parsed.scheme not in {"http", "https"}:
                continue
            reject, score = should_reject_image_candidate(absolute_url, attrs, parent_name)
            if reject:
                continue
            existing = best_by_url.get(absolute_url)
            if existing is None or score > int(existing.get("score", -999)):
                best_by_url[absolute_url] = {"url": absolute_url, "score": score}

    candidates = sorted(best_by_url.values(), key=lambda x: (int(x.get("score", 0)), str(x.get("url", ""))), reverse=True)
    return candidates


def detect_extension(image_url: str, content_type: str) -> str:
    parsed = urlparse(image_url)
    ext = Path(parsed.path).suffix.lower()
    if ext and ext not in DISALLOWED_EXTENSIONS and len(ext) <= 8:
        return ext
    normalized_type = content_type.split(";")[0].strip().lower()
    return CONTENT_TYPE_TO_EXTENSION.get(normalized_type, ".jpg")


def fetch_html(session: requests.Session, url: str) -> tuple[bool, str, str]:
    errors: list[str] = []
    for candidate_url in build_url_fetch_candidates(url):
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

        response.encoding = response.encoding or "utf-8"
        return True, response.text, ""

    if errors:
        return False, "", errors[0]
    return False, "", "html_fetch_failed:unknown"


def fetch_image(session: requests.Session, image_url: str) -> tuple[bool, bytes, str, str]:
    errors: list[str] = []
    for candidate_url in build_url_fetch_candidates(image_url):
        try:
            response = session.get(candidate_url, timeout=REQUEST_TIMEOUT_SECONDS, allow_redirects=True)
            response.raise_for_status()
        except requests.RequestException as exc:
            errors.append(summarize_request_error("image_fetch_failed", candidate_url, exc))
            continue

        content_type = str(response.headers.get("content-type") or "").lower()
        if not content_type.startswith("image/"):
            errors.append(f"image_content_type_unsupported:{normalize_domain(candidate_url)}:{content_type or 'unknown'}")
            continue

        payload = response.content
        if not payload:
            errors.append("image_empty_payload")
            continue
        return True, payload, detect_extension(candidate_url, content_type), ""

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


def main() -> int:
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
        "failed_cases": [],
        "domain_stats": {},
        "fair_breakdown": [],
        "gallery_breakdown": [],
        "notes": [],
        "wrapper_exit_code": 0,
        "network_dns_probe_host": DNS_PROBE_HOST,
        "network_dns_probe_ok": None,
    }

    try:
        dns_probe_ok, dns_probe_error = can_resolve_hostname(DNS_PROBE_HOST)
        summary["network_dns_probe_ok"] = dns_probe_ok
        if not dns_probe_ok:
            summary["notes"].append(f"dns_probe_failed:{DNS_PROBE_HOST}:{dns_probe_error}")

        targets = load_artist_targets(target_year)
        only_fair_slug = str(args.only_fair_slug or "").strip().lower()
        only_gallery_name = str(args.only_gallery_name or "").strip().lower()
        only_source_url = str(args.only_source_url or "").strip()
        if only_fair_slug:
            targets = [row for row in targets if str(row.get("fair_slug") or "").strip().lower() == only_fair_slug]
            summary["notes"].append(f"filter_only_fair_slug:{only_fair_slug}")
        if only_gallery_name:
            targets = [row for row in targets if str(row.get("gallery_name_en") or "").strip().lower() == only_gallery_name]
            summary["notes"].append(f"filter_only_gallery_name:{only_gallery_name}")
        if only_source_url:
            targets = [row for row in targets if str(row.get("source_url") or "").strip() == only_source_url]
            summary["notes"].append(f"filter_only_source_url:{only_source_url}")
        summary["seed_artist_count"] = len(targets)
        summary["max_artists_per_gallery_for_collect"] = MAX_ARTISTS_PER_GALLERY_FOR_COLLECT
        summary["notes"].append("artist_collect_source_rule=detail_pages_only")
        summary["notes"].append("local_image_cache_layout=fair_only_flat_files")
        if not targets:
            summary["notes"].append(f"no_artist_raw_records_found:artists_*_{target_year}.jsonl")
            write_json(summary_path, summary)
            print(f"[DONE] no targets. summary={summary_path}")
            return 0

        artists_image_root = (IMAGE_ROOT_DIR / str(target_year)).resolve()
        artists_image_root.mkdir(parents=True, exist_ok=True)

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
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
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

        for target in targets:
            artist_id = str(target["artist_id"])
            source_url = str(target["source_url"])
            fair_slug = str(target["fair_slug"])
            gallery_name_en = str(target["gallery_name_en"])
            domain = normalize_domain(source_url)
            domain_stats[domain]["target_artist_count"] += 1

            fair_slug_safe = slugify_token(fair_slug, fallback="unknown-fair")
            gallery_slug = slugify_token(gallery_name_en, fallback="unknown-gallery")
            artist_slug = artist_slug_from_source_url(source_url)
            artist_key = f"{gallery_slug}__{artist_slug}__{artist_id[:8]}"

            fair_dir = artists_image_root / fair_slug_safe
            fair_dir.mkdir(parents=True, exist_ok=True)
            existing_images = sorted(
                [
                    p
                    for p in fair_dir.glob(f"{artist_key}__img_*")
                    if p.is_file() and p.suffix.lower() not in DISALLOWED_EXTENSIONS and p.stat().st_size > 0
                ]
            )
            saved_count = len(existing_images)
            case_notes: list[str] = []
            case_reason = ""
            detail_urls_considered: list[str] = []

            if saved_count < target_images_per_artist:
                if looks_like_artist_listing_url(source_url):
                    ok_list_html, list_html, list_error = fetch_html(session, source_url)
                    if not ok_list_html:
                        case_reason = list_error
                    else:
                        detail_urls_considered = extract_artist_detail_urls(source_url, list_html)
                        if not detail_urls_considered:
                            case_reason = "no_artist_detail_links_found"
                        else:
                            case_notes.append(f"resolved_artist_detail_pages:{len(detail_urls_considered)}")
                else:
                    detail_urls_considered = [source_url]

                if detail_urls_considered and saved_count < target_images_per_artist:
                    next_index = saved_count + 1
                    any_detail_fetch_ok = False
                    any_image_candidate_found = False
                    for detail_url in detail_urls_considered:
                        if saved_count >= target_images_per_artist:
                            break
                        ok_html, html, html_error = fetch_html(session, detail_url)
                        if not ok_html:
                            case_notes.append(html_error)
                            continue
                        any_detail_fetch_ok = True
                        works_urls = extract_works_candidate_urls(detail_url, html)
                        case_notes.append(f"works_page_tried:{len(works_urls)}")
                        if works_urls:
                            case_notes.append(f"works_page_found:{len(works_urls)}")

                        works_candidates_count = 0
                        works_candidates_found = False
                        for works_url in works_urls:
                            if saved_count >= target_images_per_artist:
                                break
                            ok_works_html, works_html, works_error = fetch_html(session, works_url)
                            if not ok_works_html:
                                case_notes.append(works_error)
                                continue
                            works_candidates = extract_image_candidates(works_url, works_html)
                            works_candidates_count += len(works_candidates)
                            if not works_candidates:
                                continue
                            works_candidates_found = True
                            any_image_candidate_found = True
                            for candidate in works_candidates:
                                if saved_count >= target_images_per_artist:
                                    break
                                image_url = str(candidate.get("url") or "").strip()
                                if not image_url:
                                    continue
                                ok_image, payload, ext, image_error = fetch_image(session, image_url)
                                if not ok_image:
                                    case_notes.append(image_error)
                                    continue
                                file_path = fair_dir / f"{artist_key}__img_{next_index:02d}{ext}"
                                file_path.write_bytes(payload)
                                saved_count += 1
                                next_index += 1
                        case_notes.append(f"works_candidates_count:{works_candidates_count}")

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
                                ok_image, payload, ext, image_error = fetch_image(session, image_url)
                                if not ok_image:
                                    case_notes.append(image_error)
                                    continue
                                file_path = fair_dir / f"{artist_key}__img_{next_index:02d}{ext}"
                                file_path.write_bytes(payload)
                                saved_count += 1
                                next_index += 1
                    if saved_count < target_images_per_artist and not case_reason:
                        if not any_detail_fetch_ok:
                            case_reason = "artist_detail_fetch_failed"
                        elif not any_image_candidate_found:
                            case_reason = "no_image_candidates_found_on_artist_detail"
                        else:
                            case_reason = "insufficient_image_candidates_after_download"

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

            summary["per_artist_counts"].append(
                {
                    "artist_id": artist_id,
                    "artist_storage_key": artist_key,
                    "source_url": source_url,
                    "detail_urls_considered": detail_urls_considered,
                    "fair_slug": fair_slug,
                    "gallery_name_en": gallery_name_en,
                    "saved_images": saved_count,
                    "target_images": target_images_per_artist,
                    "target_met": success_ge_target,
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
                        "notes": case_notes[:5],
                    }
                )

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
        print(f"[DONE] summary={summary_path}")
        return 0
    except Exception as exc:  # noqa: BLE001
        summary["wrapper_exit_code"] = 1
        summary["notes"].append(f"fatal_error:{exc}")
        summary["generated_at"] = utc_now_iso()
        write_json(summary_path, summary)
        print(f"[ERROR] {exc}")
        print(f"[DONE] summary={summary_path}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
