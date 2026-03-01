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
