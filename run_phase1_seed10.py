#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import ParseResult, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

TARGET_YEAR = 2025
RAG_CATEGORY = "exhibitions_text"
RAG_CATEGORY_ARTISTS = "artists_text"
SEED_PER_FAIR = 5
MAX_EXHIBITION_LINKS_PER_GALLERY = 10
REQUEST_TIMEOUT_SECONDS = 12
USER_AGENT = "art-pulse-editor/phase1-seed10"
MAX_FAILURE_RETRIES_PER_URL = 3
FAILURE_RETRY_COOLDOWN_SECONDS = 3600

# 一度失敗したら再試行価値が低いものは即スキップ対象にする。
NON_RETRYABLE_FAILURE_REASON_CODES = {
    "HTTP_400",
    "HTTP_401",
    "HTTP_403",
    "HTTP_404",
    "UNSUPPORTED_CONTENT_TYPE",
}

CSV_PATHS = {
    "frieze_london": Path("data/gallery_lists/gallery_list_frieze_london.csv"),
    "liste": Path("data/gallery_lists/gallery_list_liste.csv"),
}

OUTPUT_ROOT = Path("data/phase1_seed10")
RAW_DIR = OUTPUT_ROOT / "raw"
LOG_DIR = OUTPUT_ROOT / "logs"
DERIVED_DIR = OUTPUT_ROOT / "derived"

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

ARTIST_LINK_KEYWORDS = (
    "artist",
    "artists",
    "roster",
    "team",
    "bio",
    "biography",
)


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


def _looks_like_exhibition_link(candidate_url: str, anchor_text: str) -> bool:
    target = f"{candidate_url.lower()} {anchor_text.lower()}"
    return any(keyword in target for keyword in LINK_KEYWORDS)


def extract_candidate_exhibition_urls(list_page_url: str, list_page_html: str) -> list[str]:
    soup = BeautifulSoup(list_page_html, "lxml")
    candidates: list[str] = []
    seen: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href = (anchor.get("href") or "").strip()
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
        anchor_text = anchor.get_text(" ", strip=True)
        if not _looks_like_exhibition_link(absolute_url, anchor_text):
            continue
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")
        if parsed.query:
            normalized = f"{normalized}?{parsed.query}"
        if normalized in seen:
            continue
        seen.add(normalized)
        candidates.append(normalized)
        if len(candidates) >= MAX_EXHIBITION_LINKS_PER_GALLERY:
            break

    if not candidates:
        return [list_page_url]
    return candidates


def extract_candidate_artist_urls(list_page_url: str, list_page_html: str) -> list[str]:
    soup = BeautifulSoup(list_page_html, "lxml")
    candidates: list[str] = []
    seen: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href = (anchor.get("href") or "").strip()
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
        anchor_text = anchor.get_text(" ", strip=True).lower()
        target = f"{absolute_url.lower()} {anchor_text}"
        if not any(keyword in target for keyword in ARTIST_LINK_KEYWORDS):
            continue
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")
        if parsed.query:
            normalized = f"{normalized}?{parsed.query}"
        if normalized in seen:
            continue
        seen.add(normalized)
        candidates.append(normalized)
        if len(candidates) >= MAX_EXHIBITION_LINKS_PER_GALLERY:
            break

    if not candidates:
        return [list_page_url]
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


def fetch_html(session: requests.Session, url: str) -> dict[str, Any]:
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
    soup = BeautifulSoup(html, "lxml")
    for node in soup(["script", "style", "noscript"]):
        node.extract()
    text = soup.get_text("\n", strip=True)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


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


def looks_like_target_year(page_url: str, html: str) -> bool:
    year = str(TARGET_YEAR)
    return year in page_url or year in html


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("a", encoding="utf-8") as handle:
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
    args = parse_args()
    include_artists_text = bool(args.include_artists_text)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    DERIVED_DIR.mkdir(parents=True, exist_ok=True)

    started_at = utc_now_iso()
    categories = [RAG_CATEGORY] + ([RAG_CATEGORY_ARTISTS] if include_artists_text else [])
    print(f"[START] Phase1 seed10 fetch ({'+'.join(categories)}) at {started_at}")

    seed_galleries: list[GallerySeed] = []
    for fair_slug, csv_path in CSV_PATHS.items():
        if not csv_path.exists():
            raise FileNotFoundError(f"Missing gallery CSV: {csv_path}")
        galleries = load_seed_galleries(csv_path=csv_path, fair_slug=fair_slug, limit=SEED_PER_FAIR)
        seed_galleries.extend(galleries)

    print(
        "[INFO] Loaded seed galleries: "
        + ", ".join(
            f"{fair_slug}={sum(1 for g in seed_galleries if g.fair_slug == fair_slug)}"
            for fair_slug in CSV_PATHS
        )
    )

    output_paths_by_fair = {
        fair_slug: RAW_DIR / f"exhibitions_{fair_slug}_{TARGET_YEAR}.jsonl"
        for fair_slug in CSV_PATHS
    }
    visited_pages_path = LOG_DIR / f"visited_pages_seed10_{TARGET_YEAR}.json"
    failed_fetches_path = LOG_DIR / f"failed_fetches_seed10_{TARGET_YEAR}.json"

    visited_pages_ledger = load_visited_pages_ledger(visited_pages_path)
    failed_fetches_ledger = load_failed_fetches_ledger(failed_fetches_path)
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
    if include_artists_text:
        print(
            f"[INFO] Artists ledgers: visited={len(artists_visited_pages_ledger)} "
            f"failed={len(artists_failed_fetches_ledger)} "
            f"existing_text_hashes={sum(len(v) for v in artists_existing_text_hashes_by_fair.values())}"
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

        for page_url in candidate_urls:
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
                        parent_source_url=list_page_url,
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
                    parent_source_url=list_page_url,
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
                        parent_source_url=list_page_url,
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
                    parent_source_url=list_page_url,
                )
                continue

            source_url = page_result["final_url"]
            clear_failed_fetch(failed_fetches_ledger, page_url)
            clear_failed_fetch(failed_fetches_ledger, source_url)
            text = extract_text(page_result["html"])
            if not text:
                failed_fetches_in_run.append(
                    upsert_failed_fetch(
                        failed_fetches_ledger,
                        kind="page",
                        raw_url=source_url,
                        parent_source_url=list_page_url,
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
                    parent_source_url=list_page_url,
                )
                continue

            if not looks_like_target_year(source_url, page_result["html"]):
                upsert_visited_page(
                    visited_pages_ledger,
                    url=source_url,
                    fair_slug=gallery.fair_slug,
                    gallery_name_en=gallery.gallery_name_en,
                    decision="skipped",
                    reason_code="OUT_OF_YEAR",
                    parent_source_url=list_page_url,
                )
                skip_reason_counter["OUT_OF_YEAR"] += 1
                continue

            text_hash = compute_text_hash(text=text, source_url=source_url)
            if text_hash in seen_hashes_by_fair[gallery.fair_slug]:
                duplicate_reason = (
                    "DUPLICATE_TEXT_HASH_EXISTING"
                    if text_hash in existing_text_hashes_by_fair.get(gallery.fair_slug, set())
                    else "DUPLICATE_TEXT_HASH_IN_RUN"
                )
                upsert_visited_page(
                    visited_pages_ledger,
                    url=source_url,
                    fair_slug=gallery.fair_slug,
                    gallery_name_en=gallery.gallery_name_en,
                    decision="skipped",
                    reason_code=duplicate_reason,
                    parent_source_url=list_page_url,
                )
                skip_reason_counter[duplicate_reason] += 1
                continue

            seen_hashes_by_fair[gallery.fair_slug].add(text_hash)
            record = {
                "gallery_name_en": gallery.gallery_name_en,
                "gallery_name_kana": gallery.gallery_name_kana,
                "source_url": source_url,
                "text": text,
                "text_hash": text_hash,
                "headline_ja": "",
                "summary_ja": "",
                "extracted_at": utc_now_iso(),
                "target_year": TARGET_YEAR,
                "exhibition_start_date": "",
                "exhibition_end_date": "",
                "date_source": "heuristic_year_match",
                "date_confidence": "low",
                "fair_slug": gallery.fair_slug,
                "rag_category": RAG_CATEGORY,
            }
            records_by_fair[gallery.fair_slug].append(record)
            upsert_visited_page(
                visited_pages_ledger,
                url=source_url,
                fair_slug=gallery.fair_slug,
                gallery_name_en=gallery.gallery_name_en,
                decision="saved",
                reason_code="OK",
                parent_source_url=list_page_url,
            )

    if include_artists_text:
        for gallery in seed_galleries:
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
            )

            for page_url in candidate_urls:
                page_url_hash = compute_page_url_hash(page_url)
                failed_page_entry = artists_failed_fetches_ledger.get(page_url_hash)
                now = datetime.now(timezone.utc)
                if failed_page_entry is not None:
                    should_skip, skip_reason = should_skip_failed_url(failed_page_entry, now)
                    if should_skip:
                        upsert_visited_page(
                            artists_visited_pages_ledger,
                            url=page_url,
                            fair_slug=gallery.fair_slug,
                            gallery_name_en=gallery.gallery_name_en,
                            decision="skipped",
                            reason_code=skip_reason,
                            parent_source_url=list_page_url,
                            category=RAG_CATEGORY_ARTISTS,
                        )
                        artists_skip_reason_counter[skip_reason] += 1
                        continue

                previous_visit = artists_visited_pages_ledger.get(page_url_hash)
                if previous_visit and previous_visit.get("decision") == "saved":
                    upsert_visited_page(
                        artists_visited_pages_ledger,
                        url=page_url,
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
                            raw_url=page_url,
                            parent_source_url=list_page_url,
                            last_error=page_result["error"] or "PAGE_FETCH_FAILED",
                            http_status=page_result["status_code"],
                            reason_code=page_reason_code,
                            category=RAG_CATEGORY_ARTISTS,
                        )
                    )
                    upsert_visited_page(
                        artists_visited_pages_ledger,
                        url=page_url,
                        fair_slug=gallery.fair_slug,
                        gallery_name_en=gallery.gallery_name_en,
                        decision="failed",
                        reason_code=page_reason_code,
                        parent_source_url=list_page_url,
                        category=RAG_CATEGORY_ARTISTS,
                    )
                    continue

                source_url = page_result["final_url"]
                clear_failed_fetch(artists_failed_fetches_ledger, page_url)
                clear_failed_fetch(artists_failed_fetches_ledger, source_url)
                text = extract_text(page_result["html"])
                if not text:
                    artists_failed_fetches_in_run.append(
                        upsert_failed_fetch(
                            artists_failed_fetches_ledger,
                            kind="page",
                            raw_url=source_url,
                            parent_source_url=list_page_url,
                            last_error="EMPTY_TEXT",
                            http_status=page_result["status_code"],
                            reason_code="EMPTY_TEXT",
                            category=RAG_CATEGORY_ARTISTS,
                        )
                    )
                    upsert_visited_page(
                        artists_visited_pages_ledger,
                        url=source_url,
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
                    upsert_visited_page(
                        artists_visited_pages_ledger,
                        url=source_url,
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
                upsert_visited_page(
                    artists_visited_pages_ledger,
                    url=source_url,
                    fair_slug=gallery.fair_slug,
                    gallery_name_en=gallery.gallery_name_en,
                    decision="saved",
                    reason_code="OK",
                    parent_source_url=list_page_url,
                    category=RAG_CATEGORY_ARTISTS,
                )

    output_files: dict[str, str] = {}
    for fair_slug in CSV_PATHS:
        output_path = output_paths_by_fair[fair_slug]
        append_jsonl(output_path, records_by_fair.get(fair_slug, []))
        output_files[fair_slug] = str(output_path)

    artists_output_files: dict[str, str] = {}
    if include_artists_text:
        for fair_slug in CSV_PATHS:
            output_path = artists_output_paths_by_fair[fair_slug]
            append_jsonl(output_path, artists_records_by_fair.get(fair_slug, []))
            artists_output_files[fair_slug] = str(output_path)

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
    )
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
        "max_exhibition_links_per_gallery": MAX_EXHIBITION_LINKS_PER_GALLERY,
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
        "artists_existing_text_hashes_by_fair": {
            fair_slug: len(artists_existing_text_hashes_by_fair.get(fair_slug, set()))
            for fair_slug in CSV_PATHS
        },
        "artists_output_files": artists_output_files,
        "artists_failed_fetches_path": str(artists_failed_fetches_path) if include_artists_text else "",
        "artists_visited_pages_path": str(artists_visited_pages_path) if include_artists_text else "",
    }
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
            "[DONE][artists_enrichment] "
            f"mode={summary['artists_enrichment_mode']} "
            f"candidates={summary['artists_enrichment_candidates_total']} "
            f"requests_created={summary['artists_enrichment_requests_created']}"
        )
        if summary["artists_enrichment_requests_output_path"]:
            print(f"[DONE][artists_enrichment] requests={summary['artists_enrichment_requests_output_path']}")
    print(f"[DONE] summary={summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
