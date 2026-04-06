from __future__ import annotations

import re
import unicodedata
from typing import Any, Mapping
from urllib.parse import parse_qsl, urlencode, urlparse

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

ARTIST_CANONICAL_NON_NAME_SEGMENTS = {
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

ARTIST_DETAIL_CANONICAL_QUERY_KEYS = {
    "id",
    "lang",
    "option",
    "view",
}

ARTIST_IDENTITY_NON_NAME_PHRASES = {
    "contact us",
    "email address",
    "first name",
    "index php",
    "last name",
    "log in",
    "login",
    "mailing list",
    "privacy policy",
    "sign up",
}

ARTIST_IDENTITY_NON_NAME_TOKENS = ARTIST_DETAIL_NON_NAME_SLUGS | {
    "address",
    "article",
    "cookie",
    "cookies",
    "email",
    "first",
    "index",
    "last",
    "list",
    "login",
    "mailing",
    "name",
    "newsletter",
    "password",
    "php",
    "policy",
    "privacy",
    "search",
    "sign",
    "subscribe",
    "up",
    "username",
}


def normalize_url_for_link_compare(url: str) -> str:
    parsed = urlparse(url)
    normalized = f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{parsed.path}".rstrip("/")
    if parsed.query:
        query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
        normalized_query = urlencode(sorted(query_pairs), doseq=True) if query_pairs else parsed.query
        normalized = f"{normalized}?{normalized_query}"
    return normalized


def _query_pairs_lower(url: str) -> dict[str, str]:
    parsed = urlparse(str(url or ""))
    return {
        str(key or "").lower().strip(): str(value or "").lower().strip()
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
    }


def _canonical_artist_query_pairs(url: str) -> list[tuple[str, str]]:
    parsed = urlparse(str(url or "").strip())
    raw_pairs = parse_qsl(parsed.query or "", keep_blank_values=True)
    lower_pairs = {
        str(key or "").lower().strip(): str(value or "").strip()
        for key, value in raw_pairs
    }
    if lower_pairs.get("view", "").lower() != "article" or not lower_pairs.get("id"):
        return []

    canonical_pairs: list[tuple[str, str]] = []
    for key, value in raw_pairs:
        key_lower = str(key or "").lower().strip()
        if key_lower in URL_DROP_QUERY_KEYS or key_lower not in ARTIST_DETAIL_CANONICAL_QUERY_KEYS:
            continue
        value_text = str(value or "").strip()
        if not value_text:
            continue
        canonical_pairs.append((key_lower, value_text))
    canonical_pairs.sort(key=lambda item: (item[0], item[1]))
    return canonical_pairs


def canonical_artist_source_key(source_url: str) -> str:
    return canonicalize_artist_detail_url(source_url)


def canonicalize_artist_detail_url(url: str) -> str:
    parsed = urlparse(str(url or "").strip())
    scheme = (parsed.scheme or "https").lower()
    host = (parsed.netloc or "").lower()
    raw_path = (parsed.path or "/").strip()
    if not raw_path:
        raw_path = "/"
    path = "/" + raw_path.strip("/")
    path_lower = path.lower().rstrip("/")
    segments = [segment for segment in path_lower.split("/") if segment]
    canonical_query_pairs = _canonical_artist_query_pairs(url)
    if canonical_query_pairs and path_lower in {"", "/", "/index.php"}:
        path_lower = "/index.php"
        segments = ["index.php"]

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
    base = f"{scheme}://{host}{path_lower}"
    if canonical_query_pairs:
        return f"{base}?{urlencode(canonical_query_pairs, doseq=True)}"
    return base


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
        if lowered.endswith(".php") or lowered.endswith(".asp") or lowered.endswith(".aspx"):
            continue
        if lowered in ARTIST_CANONICAL_NON_NAME_SEGMENTS:
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


def sanitize_artist_name_en(name: str) -> str:
    value = str(name or "").strip()
    if not value:
        return ""
    value = re.sub(r"[_-]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    if not value:
        return ""

    parts = [part for part in value.split(" ") if part]
    if len(parts) >= 2 and re.fullmatch(r"\d+", parts[-1]):
        has_alpha_before = any(re.search(r"[a-zA-Z]", token) for token in parts[:-1])
        if has_alpha_before:
            parts = parts[:-1]
    return " ".join(parts).strip()


def is_invalid_artist_name(name: str) -> bool:
    cleaned = sanitize_artist_name_en(name)
    if not cleaned:
        return True
    lowered = cleaned.lower()
    if lowered in {"unknown artist", "unknown"} or cleaned == "作家名不明":
        return True
    if re.fullmatch(r"\d+", cleaned):
        return True
    if lowered in ARTIST_DETAIL_NON_NAME_SLUGS:
        return True
    if lowered in ARTIST_IDENTITY_NON_NAME_PHRASES:
        return True
    tokens = [token for token in lowered.split() if token]
    if tokens and all(token in ARTIST_IDENTITY_NON_NAME_TOKENS for token in tokens):
        return True
    return False


def _normalize_artist_name_for_compare(name: str) -> str:
    value = str(name or "").strip()
    if not value:
        return ""
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = sanitize_artist_name_en(value)
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


def _is_artist_query_listing(query_pairs: Mapping[str, str]) -> bool:
    return query_pairs.get("view") == "category"


def _is_artist_query_detail(query_pairs: Mapping[str, str]) -> bool:
    return query_pairs.get("view") == "article" and bool(str(query_pairs.get("id") or "").strip())


def _artist_slug_looks_detail_like(slug: str) -> bool:
    lowered = str(slug or "").strip().lower()
    if not lowered or lowered in ARTIST_DETAIL_NON_NAME_SLUGS:
        return False
    if "." in lowered or len(lowered) < 3:
        return False
    if not re.fullmatch(r"[a-z0-9-]+", lowered):
        return False
    if "-" not in lowered:
        return False
    slug_tokens = [token for token in lowered.split("-") if token]
    if slug_tokens and all(token in ARTIST_DETAIL_NON_NAME_SLUGS for token in slug_tokens):
        return False
    return True


def _path_artist_name_matches_anchor(candidate_url: str, anchor_text: str) -> bool:
    anchor_name = _normalize_artist_name_for_compare(anchor_text)
    if not anchor_name:
        return False
    url_artist_name = build_artist_name_en_from_source_url(candidate_url)
    if url_artist_name == "Unknown Artist" or is_invalid_artist_name(url_artist_name):
        return False
    return anchor_name == _normalize_artist_name_for_compare(url_artist_name)


def _looks_like_plural_family_segment(segment: str) -> bool:
    lowered = str(segment or "").strip().lower()
    if not lowered or lowered in ARTIST_DETAIL_NON_NAME_SLUGS:
        return False
    if lowered in {"artist", "artists"}:
        return False
    if len(lowered) < 4 or not re.fullmatch(r"[a-z0-9-]+", lowered):
        return False
    return lowered.endswith(("s", "es"))


def get_artist_master_duplicate_reason(
    *,
    existing_first_source_url: str,
    candidate_source_url: str,
) -> str:
    existing_source_key = canonical_artist_source_key(existing_first_source_url)
    candidate_source_key = canonical_artist_source_key(candidate_source_url)
    if existing_source_key and candidate_source_key and existing_source_key == candidate_source_key:
        return "ARTIST_TEXT_FROZEN_GLOBAL_EXISTING_SAME_SOURCE"
    return "ARTIST_TEXT_FROZEN_GLOBAL_EXISTING"


def looks_like_artist_listing_url(url: str) -> bool:
    query_pairs = _query_pairs_lower(url)
    if _is_artist_query_listing(query_pairs):
        return True
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


def _path_segments(url: str) -> list[str]:
    path = (urlparse(url).path or "").lower()
    return [segment for segment in path.split("/") if segment]


def artist_listing_scope_mode(list_page_url: str) -> str:
    query_pairs = _query_pairs_lower(list_page_url)
    if _is_artist_query_listing(query_pairs):
        return "taxonomy_query"
    segments = _path_segments(list_page_url)
    if not segments:
        return "unknown"
    if segments[0] == "category" and any(segment.startswith("artist") for segment in segments[1:]):
        return "taxonomy_path"
    if segments[0] in {"artist", "artists"}:
        return "family"
    if any("artist" in segment for segment in segments):
        return "root_listing"
    return "unknown"


def _artist_listing_scope_mode(list_page_url: str) -> str:
    return artist_listing_scope_mode(list_page_url)


def evaluate_artist_candidate_relation(
    candidate_url: str,
    list_page_url: str,
    anchor_text: str = "",
    *,
    path_family_counts: Mapping[str, int] | None = None,
    same_domain_required: bool = False,
) -> dict[str, Any]:
    candidate_norm = normalize_url_for_link_compare(candidate_url)
    list_norm = normalize_url_for_link_compare(list_page_url)
    scope_mode = artist_listing_scope_mode(list_page_url)
    candidate_query_pairs = _query_pairs_lower(candidate_url)
    candidate_segments = _path_segments(candidate_url)
    candidate_path = (urlparse(candidate_url).path or "").lower().rstrip("/")
    list_path = (urlparse(list_page_url).path or "").lower().rstrip("/")
    family_counts = path_family_counts or {}
    same_domain = _normalize_host(candidate_url) == _normalize_host(list_page_url)
    anchor_name_like = _artist_anchor_text_looks_like_name(anchor_text)
    path_name_match = _path_artist_name_matches_anchor(candidate_url, anchor_text)
    is_query_detail = _is_artist_query_detail(candidate_query_pairs)
    candidate_listing_like = looks_like_artist_listing_url(candidate_url)
    candidate_path_depth = len(candidate_segments)
    relation_type = ""
    failure_reason = ""
    is_explicit = False
    alias_family_segment = ""
    alias_family_count = 0
    matched_pattern_without_name = False
    query_detail_path_compatible = False

    if candidate_norm == list_norm:
        failure_reason = "SELF_LINK"
    elif same_domain_required and not same_domain:
        failure_reason = "CROSS_DOMAIN"
    elif candidate_listing_like:
        failure_reason = "CANDIDATE_IS_LISTING"
    else:
        if list_path and "artist" in list_path and candidate_path.startswith(f"{list_path}/"):
            relation_type = "explicit_detail"
            is_explicit = True
        elif "/artist/" in candidate_path or "/artists/" in candidate_path:
            relation_type = "explicit_detail"
            is_explicit = True
        else:
            if candidate_segments:
                slug = candidate_segments[-1]
                slug_like_detail = _artist_slug_looks_detail_like(slug)
            else:
                slug_like_detail = False
            if is_query_detail:
                candidate_script_path = candidate_path or "/"
                listing_script_path = list_path or "/"
                query_detail_path_compatible = candidate_script_path == listing_script_path or candidate_script_path in {"/", "/index.php"}
                if scope_mode in {"taxonomy_path", "taxonomy_query"} and query_detail_path_compatible:
                    if anchor_name_like:
                        relation_type = "taxonomy_to_detail"
                    else:
                        matched_pattern_without_name = True
            elif scope_mode in {"family", "root_listing"} and candidate_path_depth == 1 and slug_like_detail:
                if path_name_match and anchor_name_like:
                    relation_type = "family_to_root_detail"
                else:
                    matched_pattern_without_name = True
            elif scope_mode == "family" and candidate_path_depth == 2 and slug_like_detail:
                alias_family_segment = candidate_segments[0]
                alias_family_count = int(family_counts.get(alias_family_segment, 0))
                if (
                    path_name_match
                    and anchor_name_like
                    and (_looks_like_plural_family_segment(alias_family_segment) or alias_family_count >= 2)
                ):
                    relation_type = "family_to_alias_subpath_detail"
                else:
                    matched_pattern_without_name = True
            elif scope_mode in {"taxonomy_path", "taxonomy_query"} and candidate_path_depth in {1, 2} and slug_like_detail:
                if path_name_match and anchor_name_like:
                    relation_type = "taxonomy_to_detail"
                else:
                    matched_pattern_without_name = True

    score = 0
    if same_domain:
        score += 20
    if relation_type == "explicit_detail":
        score += 60
    elif relation_type == "family_to_root_detail":
        score += 40
    elif relation_type == "family_to_alias_subpath_detail":
        score += 42
    elif relation_type == "taxonomy_to_detail":
        score += 38
    if anchor_name_like:
        score += 10
    if path_name_match:
        score += 18
    if is_query_detail:
        score += 12
    if candidate_path_depth == 1:
        score += 4
    elif candidate_path_depth == 2:
        score += 3
    elif candidate_path_depth >= 3 and relation_type == "explicit_detail":
        score += 2
    if alias_family_count >= 2:
        score += min(alias_family_count, 4)
    if candidate_listing_like:
        score -= 50
    if scope_mode == "unknown":
        score -= 15

    if relation_type:
        if score >= 75:
            confidence = "high"
        elif score >= 58:
            confidence = "medium"
        elif score >= 45:
            confidence = "low"
        else:
            confidence = "none"
    else:
        confidence = "none"

    accepted = bool(
        relation_type
        and same_domain
        and (
            is_explicit
            or score >= 58
        )
    )

    if not failure_reason and not relation_type:
        if scope_mode == "unknown":
            failure_reason = "LISTING_SCOPE_UNKNOWN"
        elif matched_pattern_without_name:
            failure_reason = "LOW_CONFIDENCE_NAME_MATCH"
        elif scope_mode == "taxonomy_query" and not query_detail_path_compatible:
            failure_reason = "QUERY_TAXONOMY_UNSUPPORTED"
        else:
            failure_reason = "NO_RELATION_MATCH_CANDIDATES"

    return {
        "accepted": accepted,
        "confidence": confidence,
        "failure_reason": failure_reason,
        "is_explicit": is_explicit,
        "listing_scope": scope_mode,
        "path_family_count": alias_family_count,
        "path_family_segment": alias_family_segment,
        "query_detail": is_query_detail,
        "relation_type": relation_type,
        "same_domain": same_domain,
        "score": score,
    }


def looks_like_artist_detail_url(
    candidate_url: str,
    list_page_url: str,
    anchor_text: str = "",
    *,
    same_domain_required: bool = False,
) -> bool:
    relation = evaluate_artist_candidate_relation(
        candidate_url=candidate_url,
        list_page_url=list_page_url,
        anchor_text=anchor_text,
        same_domain_required=same_domain_required,
    )
    return bool(relation.get("accepted"))


def looks_like_explicit_artist_detail_url(
    candidate_url: str,
    list_page_url: str,
    anchor_text: str = "",
    *,
    same_domain_required: bool = False,
) -> bool:
    relation = evaluate_artist_candidate_relation(
        candidate_url=candidate_url,
        list_page_url=list_page_url,
        anchor_text=anchor_text,
        same_domain_required=same_domain_required,
    )
    return bool(relation.get("is_explicit"))
