from __future__ import annotations

import io
import re
from datetime import date, datetime
from html.parser import HTMLParser
from typing import Any
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse

import requests

try:
    from bs4 import BeautifulSoup
except ModuleNotFoundError:  # pragma: no cover - environment fallback
    BeautifulSoup = None

try:
    from pypdf import PdfReader
except ModuleNotFoundError:  # pragma: no cover - optional runtime dependency
    PdfReader = None

YEAR_TOKEN_RE = re.compile(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)")
ISO_DATE_RE = re.compile(r"(?<!\d)((?:19|20)\d{2})[-/.](\d{1,2})[-/.](\d{1,2})(?!\d)")
DATE_ATTR_RE = re.compile(r'datetime=["\']([^"\']+)["\']', re.IGNORECASE)
MONTH_NAME_DATE_RE = re.compile(
    r"(?i)\b("
    r"(?:jan|january|feb|february|mar|march|apr|april|may|jun|june|jul|july|aug|august|sep|sept|september|oct|october|nov|november|dec|december)"
    r"\s+\d{1,2},?\s+(?:19|20)\d{2}"
    r"|"
    r"\d{1,2}\s+"
    r"(?:jan|january|feb|february|mar|march|apr|april|may|jun|june|jul|july|aug|august|sep|sept|september|oct|october|nov|november|dec|december)"
    r"\s+(?:19|20)\d{2}"
    r")\b"
)
PARTICIPATING_ARTISTS_BLOCK_RE = re.compile(
    r"(?is)\bparticipating\s+artists?\b\s*[:\-]?\s*(.+?)(?:\n{2,}|$)"
)
PDF_LINK_RE = re.compile(r"(?i)https?://[^\s\"'>]+\.pdf(?:\?[^\s\"'>]*)?")
URL_DROP_QUERY_KEYS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "gclid",
    "fbclid",
    "mc_cid",
    "mc_eid",
    "ref",
}


class _VisibleTextHTMLParser(HTMLParser):
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


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def canonicalize_exhibition_url(url: str) -> str:
    parsed = urlparse(str(url or "").strip())
    scheme = (parsed.scheme or "https").lower()
    host = (parsed.netloc or "").lower()
    path = (parsed.path or "/").strip()
    if not path:
        path = "/"
    if path != "/":
        path = "/" + path.strip("/")
    query_pairs: list[tuple[str, str]] = []
    for key, value in parse_qsl(parsed.query or "", keep_blank_values=True):
        key_lower = key.lower().strip()
        if key_lower in URL_DROP_QUERY_KEYS:
            continue
        query_pairs.append((key, value))
    query_pairs.sort(key=lambda x: (x[0].lower(), x[1]))
    query = urlencode(query_pairs, doseq=True)
    base = f"{scheme}://{host}{path}"
    return f"{base}?{query}" if query else base


def extract_visible_text(html: str) -> str:
    if BeautifulSoup is not None:
        soup = BeautifulSoup(html, "lxml")
        text = soup.get_text("\n", strip=True)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)
    parser = _VisibleTextHTMLParser()
    parser.feed(html)
    parser.close()
    return parser.get_text()


def extract_year_tokens(text: str) -> set[int]:
    years: set[int] = set()
    for match in YEAR_TOKEN_RE.finditer(str(text or "")):
        try:
            years.add(int(match.group(1)))
        except ValueError:
            continue
    return years


TWO_DIGIT_DATE_RE = re.compile(
    r"(?<!\d)(?:(?:\d{1,2}[./-]){1,2}(?P<year>\d{2}))(?:\D|$)"
)


def extract_two_digit_years_in_date_context(text: str) -> set[int]:
    entries: set[int] = set()
    for match in TWO_DIGIT_DATE_RE.finditer(str(text or "")):
        year = int(match.group("year"))
        entries.add(year)
    return entries


def has_explicit_non_target_year(text: str, target_year: int) -> bool:
    years = extract_year_tokens(text)
    return bool(years) and int(target_year) not in years


def url_path_contains_year(url: str, target_year: int) -> bool:
    normalized = (url or "")
    if not normalized:
        return False
    path = urlparse(normalized).path or ""
    token = re.compile(rf"(?<!\d){int(target_year)}(?!\d)")
    return bool(token.search(path))


def _parse_iso_date(year: str, month: str, day: str) -> date | None:
    try:
        return date(int(year), int(month), int(day))
    except ValueError:
        return None


def _parse_month_name_date(raw_text: str) -> date | None:
    text = normalize_whitespace(raw_text).replace(",", "")
    for fmt in ("%b %d %Y", "%B %d %Y", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _collect_date_candidates(page_url: str, html: str, extracted_text: str) -> list[date]:
    candidates: list[date] = []
    seen: set[str] = set()
    combined_sources = [str(page_url or ""), str(html or ""), str(extracted_text or "")]
    for source in combined_sources:
        for match in ISO_DATE_RE.finditer(source):
            d = _parse_iso_date(match.group(1), match.group(2), match.group(3))
            if d is None:
                continue
            key = d.isoformat()
            if key in seen:
                continue
            seen.add(key)
            candidates.append(d)

    for match in DATE_ATTR_RE.finditer(str(html or "")):
        raw = normalize_whitespace(match.group(1))
        if not raw:
            continue
        raw_head = raw[:10]
        iso_match = ISO_DATE_RE.search(raw_head)
        if iso_match:
            d = _parse_iso_date(iso_match.group(1), iso_match.group(2), iso_match.group(3))
            if d is not None and d.isoformat() not in seen:
                seen.add(d.isoformat())
                candidates.append(d)

    for match in MONTH_NAME_DATE_RE.finditer(str(extracted_text or "")):
        d = _parse_month_name_date(match.group(1))
        if d is None:
            continue
        key = d.isoformat()
        if key in seen:
            continue
        seen.add(key)
        candidates.append(d)

    return sorted(candidates)


def extract_exhibition_dates(
    *,
    page_url: str,
    html: str,
    extracted_text: str,
    target_year: int,
) -> dict[str, str]:
    dates = _collect_date_candidates(page_url, html, extracted_text)
    if dates:
        start = dates[0]
        end = dates[-1]
        confidence = "high" if start != end else "medium"
        return {
            "exhibition_start_date": start.isoformat(),
            "exhibition_end_date": end.isoformat(),
            "date_source": "regex_date_extraction",
            "date_confidence": confidence,
        }

    years = extract_year_tokens(f"{page_url}\n{html}\n{extracted_text}")
    if int(target_year) in years:
        return {
            "exhibition_start_date": f"{target_year}-01-01",
            "exhibition_end_date": f"{target_year}-12-31",
            "date_source": "year_signal_fallback",
            "date_confidence": "low",
        }

    return {
        "exhibition_start_date": "",
        "exhibition_end_date": "",
        "date_source": "unknown",
        "date_confidence": "none",
    }


def should_include_target_year_page(*, page_url: str, html: str, target_year: int) -> tuple[bool, str]:
    target = int(target_year)
    combined = f"{page_url}\n{html}"
    years = extract_year_tokens(combined)
    if target in years:
        return True, "year_signal_present"
    if target == 2025:
        two_digit_years = extract_two_digit_years_in_date_context(combined)
        if 25 in two_digit_years:
            return True, "two_digit_year_signal"
    if years:
        return False, "explicit_non_target_year"
    if url_path_contains_year(page_url, target):
        return True, "year_signal_in_url_path"
    # If no explicit year signal exists, keep page as potentially valid candidate.
    return True, "no_explicit_year_signal"


def extract_participating_artists_line(extracted_text: str) -> str:
    text = str(extracted_text or "")
    match = PARTICIPATING_ARTISTS_BLOCK_RE.search(text)
    if not match:
        lines = [normalize_whitespace(line) for line in text.splitlines()]
        lines = [line for line in lines if line]
        name_like = re.compile(r"^[A-Z][A-Za-z'’.\-]+(?:\s+[A-Z][A-Za-z'’.\-]+){1,3}$")
        best_block: list[str] = []
        current_block: list[str] = []
        for line in lines:
            if name_like.fullmatch(line):
                current_block.append(line)
                continue
            if len(current_block) >= 2 and len(current_block) > len(best_block):
                best_block = current_block[:]
            current_block = []
        if len(current_block) >= 2 and len(current_block) > len(best_block):
            best_block = current_block[:]
        if not best_block:
            return ""
        cleaned = ", ".join(best_block)
        return f"Participating Artists: {cleaned}"
    raw_block = normalize_whitespace(match.group(1))
    if not raw_block:
        return ""
    cleaned = re.sub(r"\s*(?:\||/|•|·)\s*", ", ", raw_block)
    cleaned = re.sub(r"\s*,\s*", ", ", cleaned)
    cleaned = cleaned.strip(" ,;")
    if not cleaned:
        return ""
    return f"Participating Artists: {cleaned}"


def extract_pdf_urls(page_url: str, html: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    if BeautifulSoup is not None:
        soup = BeautifulSoup(html, "lxml")
        for anchor in soup.find_all("a", href=True):
            href = str(anchor.get("href") or "").strip()
            if not href:
                continue
            absolute = urljoin(page_url, href)
            lowered = absolute.lower()
            anchor_text = normalize_whitespace(anchor.get_text(" ", strip=True)).lower()
            if ".pdf" not in lowered and "pdf" not in anchor_text:
                continue
            canon = canonicalize_exhibition_url(absolute)
            if canon in seen:
                continue
            seen.add(canon)
            urls.append(absolute)
        return urls

    for match in PDF_LINK_RE.finditer(str(html or "")):
        absolute = match.group(0).strip()
        canon = canonicalize_exhibition_url(absolute)
        if canon in seen:
            continue
        seen.add(canon)
        urls.append(absolute)
    return urls


def _extract_pdf_text(payload: bytes) -> str:
    if PdfReader is None:
        return ""
    try:
        reader = PdfReader(io.BytesIO(payload))
    except Exception:
        return ""
    chunks: list[str] = []
    for page in reader.pages:
        try:
            chunk = page.extract_text() or ""
        except Exception:
            chunk = ""
        chunk = normalize_whitespace(chunk)
        if chunk:
            chunks.append(chunk)
    return "\n".join(chunks)


def fetch_and_extract_pdf_text(
    *,
    session: requests.Session,
    page_url: str,
    html: str,
    max_pdfs: int = 3,
    max_chars: int = 12000,
    timeout_seconds: int = 15,
) -> tuple[str, list[dict[str, Any]]]:
    pdf_urls = extract_pdf_urls(page_url, html)
    debug_rows: list[dict[str, Any]] = []
    if not pdf_urls:
        return "", debug_rows

    chunks: list[str] = []
    for pdf_url in pdf_urls[:max_pdfs]:
        row: dict[str, Any] = {"pdf_url": pdf_url, "status": "unknown", "chars": 0}
        try:
            resp = session.get(pdf_url, timeout=timeout_seconds, allow_redirects=True)
        except Exception as exc:  # noqa: BLE001
            row["status"] = "fetch_failed"
            row["error"] = str(exc)
            debug_rows.append(row)
            continue

        content_type = str(resp.headers.get("Content-Type") or "").lower()
        if resp.status_code >= 400:
            row["status"] = "http_error"
            row["http_status"] = int(resp.status_code)
            debug_rows.append(row)
            continue
        if "pdf" not in content_type and ".pdf" not in str(resp.url).lower():
            row["status"] = "not_pdf"
            row["content_type"] = content_type
            debug_rows.append(row)
            continue

        text = _extract_pdf_text(resp.content or b"")
        if not text:
            row["status"] = "empty_pdf_text"
            debug_rows.append(row)
            continue

        text = text.strip()
        if text:
            chunks.append(text)
            row["status"] = "ok"
            row["chars"] = len(text)
        debug_rows.append(row)

    merged = "\n\n".join(chunks).strip()
    if len(merged) > max_chars:
        merged = merged[:max_chars].rstrip()
    return merged, debug_rows


def merge_exhibition_text(
    *,
    base_text: str,
    participating_artists_line: str,
    pdf_text: str,
) -> str:
    parts: list[str] = [str(base_text or "").strip()]
    if participating_artists_line:
        parts.append(participating_artists_line)
    if pdf_text:
        parts.append(f"[PDF_TEXT]\n{pdf_text.strip()}")
    merged = "\n\n".join(part for part in parts if part)
    return merged.strip()


def normalize_sources(existing: Any, fallback_source_url: str = "") -> list[str]:
    values: list[str] = []
    if isinstance(existing, list):
        iterable = existing
    elif isinstance(existing, str):
        iterable = [existing]
    else:
        iterable = []
    seen: set[str] = set()
    for raw in iterable:
        url = canonicalize_exhibition_url(str(raw or "").strip())
        if not url or url in seen:
            continue
        seen.add(url)
        values.append(url)
    if fallback_source_url:
        fallback = canonicalize_exhibition_url(fallback_source_url)
        if fallback and fallback not in seen:
            values.append(fallback)
    return values


def merge_sources(existing: Any, new_source_url: str) -> list[str]:
    sources = normalize_sources(existing, fallback_source_url="")
    incoming = canonicalize_exhibition_url(new_source_url)
    if incoming and incoming not in sources:
        sources.append(incoming)
    return sources
