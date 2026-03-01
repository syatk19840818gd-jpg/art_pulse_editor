from __future__ import annotations

import re
from urllib.parse import urlparse

ARTIST_LINK_KEYWORDS = (
    "artist",
    "artists",
    "roster",
    "team",
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

ARTIST_DETAIL_NON_NAME_SLUGS = {
    "artist",
    "artists",
    "art",
    "about",
    "contact",
    "news",
    "press",
    "publications",
    "publication",
    "exhibitions",
    "exhibition",
    "fairs",
    "fair",
    "gallery",
    "main-homepage",
    "homepage",
    "home",
    "basket",
    "shop",
    "events",
    "event",
    "archive",
    "main",
    "list",
    "category",
    "of",
    "current",
    "past",
}


def normalize_url_for_link_compare(url: str) -> str:
    parsed = urlparse(url)
    normalized = f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{parsed.path}".rstrip("/")
    if parsed.query:
        normalized = f"{normalized}?{parsed.query}"
    return normalized


def canonicalize_artist_detail_url(url: str) -> str:
    parsed = urlparse(normalize_url_for_link_compare(url))
    scheme = (parsed.scheme or "https").lower()
    host = (parsed.netloc or "").lower()
    raw_path = (parsed.path or "/").strip()
    if not raw_path:
        return f"{scheme}://{host}/"
    path = "/" + raw_path.strip("/")
    path_lower = path.lower().rstrip("/")
    segments = [segment for segment in path_lower.split("/") if segment]

    if len(segments) >= 2 and segments[0] in {"artist", "artists"}:
        artist_id = ""
        artist_segment = segments[1]
        m_slug = re.fullmatch(r"(?P<id>\d+)-[a-z0-9][a-z0-9-]*", artist_segment)
        m_dash_only = re.fullmatch(r"(?P<id>\d+)-", artist_segment)
        m_id_only = re.fullmatch(r"(?P<id>\d+)", artist_segment)
        if m_slug:
            artist_id = m_slug.group("id")
        elif m_dash_only:
            artist_id = m_dash_only.group("id")
        elif m_id_only:
            artist_id = m_id_only.group("id")
        if artist_id:
            tail = segments[2] if len(segments) >= 3 else ""
            if tail in {"bio", "biography"}:
                return f"{scheme}://{host}/{segments[0]}/{artist_id}/{tail}"
            return f"{scheme}://{host}/{segments[0]}/{artist_id}"

    if not path_lower:
        path_lower = "/"
    return f"{scheme}://{host}{path_lower}"


def score_artist_detail_url_quality(url: str) -> int:
    path = (urlparse(url).path or "").lower().rstrip("/")
    score = 0
    if re.search(r"/artists?/\d+-[a-z0-9][a-z0-9-]*/(bio|biography)$", path):
        score += 6
    elif re.search(r"/artists?/\d+/(bio|biography)$", path):
        score += 5
    elif re.search(r"/artists?/\d+-$", path):
        score -= 2
    elif re.search(r"/artists?/\d+$", path):
        score += 1
    if path.endswith("/biography") or path.endswith("/bio"):
        score += 1
    return score


def looks_like_artist_listing_url(url: str) -> bool:
    path = (urlparse(url).path or "").lower().rstrip("/")
    if not path:
        return False
    return any(path.endswith(pattern.rstrip("/")) for pattern in ARTIST_LIST_PATH_PATTERNS)


def _normalize_host(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower().strip()
    if host.startswith("www."):
        host = host[4:]
    return host


def looks_like_artist_detail_url(
    candidate_url: str,
    list_page_url: str,
    anchor_text: str = "",
    *,
    same_domain_required: bool = False,
) -> bool:
    candidate_norm = normalize_url_for_link_compare(candidate_url)
    list_norm = normalize_url_for_link_compare(list_page_url)
    if candidate_norm == list_norm:
        return False
    if looks_like_artist_listing_url(candidate_url):
        return False
    if same_domain_required and _normalize_host(candidate_url) != _normalize_host(list_page_url):
        return False

    candidate_path = (urlparse(candidate_url).path or "").lower().rstrip("/")
    list_path = (urlparse(list_page_url).path or "").lower().rstrip("/")
    if not candidate_path:
        return False
    if list_path and "artist" in list_path and candidate_path.startswith(f"{list_path}/"):
        return True
    if "/artist/" in candidate_path or "/artists/" in candidate_path:
        return True

    # Fallback for listing pages that expose artist details at root path.
    if looks_like_artist_listing_url(list_page_url):
        slug = candidate_path.strip("/").split("/")[-1].strip().lower()
        if not slug:
            return False
        slug_tokens = [token for token in slug.split("-") if token]
        if slug in ARTIST_DETAIL_NON_NAME_SLUGS:
            return False
        if slug_tokens and all(token in ARTIST_DETAIL_NON_NAME_SLUGS for token in slug_tokens):
            return False
        if len(slug) < 3:
            return False
        if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)+", slug):
            return True
        anchor = anchor_text.strip()
        if anchor:
            anchor_tokens = [
                token
                for token in re.split(r"\s+", anchor.lower())
                if re.sub(r"[^a-z0-9]+", "", token)
            ]
            if len(anchor_tokens) >= 2 and len(re.sub(r"[^a-z0-9]+", "", anchor)) >= 6:
                return True
    return False
