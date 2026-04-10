from __future__ import annotations

import contextlib
import io
import logging
import re
import unicodedata
import warnings
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
PDF_PARSER_LOGGER_NAMES = ("pypdf", "PyPDF2")
PDF_DEBUG_NOTE_LIMIT = 5
PDF_DEBUG_TEXT_LIMIT = 200


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


def canonicalize_gallery_scope_name(name: str) -> str:
    """Build a scope-matching key without mutating display names."""
    raw = str(name or "").strip()
    if not raw:
        return ""
    normalized = unicodedata.normalize("NFKD", raw)
    without_marks = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    folded = without_marks.casefold()
    collapsed = re.sub(r"[_/\-]+", " ", folded)
    collapsed = re.sub(r"[^0-9a-z ]+", " ", collapsed)
    return normalize_whitespace(collapsed)


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
    r"(?<!\d)(?P<day>\d{1,2})(?P<sep>[./-])(?P<month>\d{1,2})(?P=sep)(?P<year>\d{2})(?!\d)"
)
TWO_DIGIT_DATE_RANGE_RE = re.compile(
    r"(?<!\d)"
    r"(?P<start_day>\d{1,2})(?P<start_sep>[./-])(?P<start_month>\d{1,2})(?P=start_sep)(?P<start_year>\d{2})"
    r"\s*(?:-|to)\s*"
    r"(?P<end_day>\d{1,2})(?P<end_sep>[./-])(?P<end_month>\d{1,2})(?P=end_sep)(?P<end_year>\d{2})(?!\d)"
)


def extract_two_digit_years_in_date_context(text: str) -> set[int]:
    entries: set[int] = set()
    normalized = (
        str(text or "")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2212", "-")
    )
    for raw_line in normalized.splitlines():
        line = normalize_whitespace(raw_line)
        if not line or len(line) > 160:
            continue
        if not re.search(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2}\b", line):
            continue
        for match in TWO_DIGIT_DATE_RE.finditer(line):
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


def _expand_two_digit_year(year: str) -> int:
    value = int(year)
    return 2000 + value if value <= 68 else 1900 + value


def _parse_two_digit_year_date(day: str, month: str, year: str) -> date | None:
    try:
        return date(_expand_two_digit_year(year), int(month), int(day))
    except ValueError:
        return None


def _extract_two_digit_date_ranges(extracted_text: str) -> list[tuple[date, date]]:
    ranges: list[tuple[date, date]] = []
    normalized_text = (
        str(extracted_text or "")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2212", "-")
    )
    for raw_line in normalized_text.splitlines():
        line = normalize_whitespace(raw_line)
        if not line or len(line) > 80:
            continue
        for match in TWO_DIGIT_DATE_RANGE_RE.finditer(line):
            start = _parse_two_digit_year_date(
                match.group("start_day"),
                match.group("start_month"),
                match.group("start_year"),
            )
            end = _parse_two_digit_year_date(
                match.group("end_day"),
                match.group("end_month"),
                match.group("end_year"),
            )
            if start is None or end is None:
                continue
            ranges.append((start, end))
    return ranges


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

    normalized_text = (
        str(extracted_text or "")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2212", "-")
    )
    for raw_line in normalized_text.splitlines():
        line = normalize_whitespace(raw_line)
        if not line or len(line) > 160:
            continue
        if not TWO_DIGIT_DATE_RE.search(line):
            continue
        for match in TWO_DIGIT_DATE_RANGE_RE.finditer(line):
            for d in (
                _parse_two_digit_year_date(
                    match.group("start_day"),
                    match.group("start_month"),
                    match.group("start_year"),
                ),
                _parse_two_digit_year_date(
                    match.group("end_day"),
                    match.group("end_month"),
                    match.group("end_year"),
                ),
            ):
                if d is None:
                    continue
                key = d.isoformat()
                if key in seen:
                    continue
                seen.add(key)
                candidates.append(d)
        for match in TWO_DIGIT_DATE_RE.finditer(line):
            d = _parse_two_digit_year_date(
                match.group("day"),
                match.group("month"),
                match.group("year"),
            )
            if d is None:
                continue
            key = d.isoformat()
            if key in seen:
                continue
            seen.add(key)
            candidates.append(d)

    return sorted(candidates)


def _extract_page_title_and_headings(html: str) -> str:
    if BeautifulSoup is None:
        return ""
    try:
        soup = BeautifulSoup(html or "", "lxml")
    except Exception:
        return ""
    chunks: list[str] = []
    if soup.title:
        title = normalize_whitespace(soup.title.get_text(" ", strip=True))
        if title:
            chunks.append(title)
    for tag_name in ("h1", "h2"):
        for node in soup.find_all(tag_name, limit=4):
            value = normalize_whitespace(node.get_text(" ", strip=True))
            if value and value not in chunks:
                chunks.append(value)
    return "\n".join(chunks)


def _build_local_year_signal_text(page_url: str, html: str, extracted_text: str) -> str:
    title_and_headings = _extract_page_title_and_headings(html)
    visible_text = str(extracted_text or "")
    lines: list[str] = []
    for raw_line in visible_text.splitlines():
        line = normalize_whitespace(raw_line)
        if not line:
            continue
        lines.append(line)
        if len(lines) >= 40:
            break
    parts = [str(page_url or "").strip(), title_and_headings]
    parts.extend(lines)
    return "\n".join(part for part in parts if part)


def _is_local_target_year_signal(years: set[int], target_year: int) -> bool:
    if int(target_year) not in years:
        return False
    return len(years) <= 3 and all(abs(year - int(target_year)) <= 1 for year in years)


def extract_exhibition_dates(
    *,
    page_url: str,
    html: str,
    extracted_text: str,
    target_year: int,
) -> dict[str, str]:
    two_digit_ranges = _extract_two_digit_date_ranges(extracted_text)
    if two_digit_ranges:
        start, end = two_digit_ranges[0]
        confidence = "high" if start != end else "medium"
        return {
            "exhibition_start_date": start.isoformat(),
            "exhibition_end_date": end.isoformat(),
            "date_source": "regex_date_extraction",
            "date_confidence": confidence,
        }

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

    local_year_text = _build_local_year_signal_text(page_url, html, extracted_text)
    local_years = extract_year_tokens(local_year_text)
    title_and_headings = _extract_page_title_and_headings(html)
    title_years = extract_year_tokens(title_and_headings)
    if (
        url_path_contains_year(page_url, int(target_year))
        or int(target_year) in title_years
        or _is_local_target_year_signal(local_years, int(target_year))
    ):
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
    extracted_text = extract_visible_text(html)
    dates = _collect_date_candidates(page_url, html, extracted_text)
    if dates:
        date_years = {entry.year for entry in dates}
        if target in date_years:
            return True, "year_signal_present"
        return False, "explicit_non_target_year"
    local_year_text = _build_local_year_signal_text(page_url, html, extracted_text)
    title_and_headings = _extract_page_title_and_headings(html)
    title_years = extract_year_tokens(title_and_headings)
    local_years = extract_year_tokens(local_year_text)
    if target in title_years:
        return True, "year_signal_present"
    if _is_local_target_year_signal(local_years, target):
        return True, "year_signal_present"
    if target == 2025:
        two_digit_years = extract_two_digit_years_in_date_context(local_year_text)
        if 25 in two_digit_years and len(two_digit_years) <= 3:
            return True, "two_digit_year_signal"
    if local_years:
        return False, "explicit_non_target_year"
    if url_path_contains_year(page_url, target):
        return True, "year_signal_in_url_path"
    return False, "no_explicit_year_signal"


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


@contextlib.contextmanager
def _capture_pdf_parser_noise() -> Any:
    stderr_buffer = io.StringIO()
    logger_states: list[tuple[logging.Logger, list[logging.Handler], int, bool]] = []
    attached_handlers: list[logging.Handler] = []
    for logger_name in PDF_PARSER_LOGGER_NAMES:
        logger = logging.getLogger(logger_name)
        logger_states.append((logger, list(logger.handlers), logger.level, logger.propagate))
        handler = logging.StreamHandler(stderr_buffer)
        handler.setLevel(logging.WARNING)
        attached_handlers.append(handler)
        logger.handlers = [handler]
        logger.setLevel(logging.WARNING)
        logger.propagate = False
    try:
        with contextlib.redirect_stderr(stderr_buffer), warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            yield stderr_buffer, caught
    finally:
        for logger, handlers, level, propagate in logger_states:
            logger.handlers = handlers
            logger.setLevel(level)
            logger.propagate = propagate
        for handler in attached_handlers:
            handler.close()


def _collect_pdf_debug_notes(stderr_text: str, caught_warnings: list[Any]) -> list[str]:
    notes: list[str] = []
    normalized_stderr = normalize_whitespace(stderr_text)
    if normalized_stderr:
        notes.append(f"parser_stderr:{normalized_stderr[:PDF_DEBUG_TEXT_LIMIT]}")
    for warning_item in caught_warnings:
        message = normalize_whitespace(str(getattr(warning_item, "message", "") or ""))
        if not message:
            continue
        note = f"parser_warning:{message[:PDF_DEBUG_TEXT_LIMIT]}"
        if note not in notes:
            notes.append(note)
        if len(notes) >= PDF_DEBUG_NOTE_LIMIT:
            break
    return notes[:PDF_DEBUG_NOTE_LIMIT]


def _extract_pdf_text(payload: bytes) -> tuple[str, list[str]]:
    if PdfReader is None:
        return "", ["pdf_reader_unavailable"]
    chunks: list[str] = []
    notes: list[str] = []
    with _capture_pdf_parser_noise() as (stderr_buffer, caught_warnings):
        try:
            reader = PdfReader(io.BytesIO(payload))
        except Exception as exc:
            notes.append(f"reader_init_failed:{exc.__class__.__name__}")
            notes.extend(_collect_pdf_debug_notes(stderr_buffer.getvalue(), caught_warnings))
            return "", notes[:PDF_DEBUG_NOTE_LIMIT]

        try:
            page_total = len(reader.pages)
        except Exception as exc:
            notes.append(f"page_count_failed:{exc.__class__.__name__}")
            notes.extend(_collect_pdf_debug_notes(stderr_buffer.getvalue(), caught_warnings))
            return "", notes[:PDF_DEBUG_NOTE_LIMIT]

        for page_index in range(page_total):
            try:
                page = reader.pages[page_index]
            except Exception as exc:
                notes.append(f"page_load_failed:{page_index}:{exc.__class__.__name__}")
                continue
            try:
                chunk = page.extract_text() or ""
            except Exception as exc:
                notes.append(f"page_extract_failed:{page_index}:{exc.__class__.__name__}")
                continue
            chunk = normalize_whitespace(chunk)
            if chunk:
                chunks.append(chunk)

        notes.extend(_collect_pdf_debug_notes(stderr_buffer.getvalue(), caught_warnings))
    return "\n".join(chunks), notes[:PDF_DEBUG_NOTE_LIMIT]


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

        text, pdf_notes = _extract_pdf_text(resp.content or b"")
        if pdf_notes:
            row["pdf_notes"] = pdf_notes
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
