from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
from collections import Counter
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urljoin, urlparse

import requests

import unicodedata

from enrichment_batch_common import is_optional_output_enabled
from gallery_skip_registry import (
    build_all_rag_zero_skip_entries,
    build_exhibition_text_only_skip_entries,
    build_skip_lookup,
    find_skip_entry,
    is_all_rag_zero_target_row,
    is_exhibition_text_only_target_row,
    load_skip_registry_entries,
    normalize_fair_slug,
    remove_skipped_from_gallery_list_csv,
    upsert_skip_registry_entries,
)
import run_phase1_seed10_artist_image_collect as artist_img
from phase2_art_pulse_config import (
    PHASE1_SEED10_ROOT,
    get_current_raw_dir,
    get_exhibition_image_cache_dir,
    get_current_exhibitions_image_meta_path,
    get_image_r2_key,
    resolve_image_local_path,
)
from phase1_exhibitions_text_utils import should_include_target_year_page
from run_rag_gallery_breakdown_update import (
    ScopeTarget as BreakdownScopeTarget,
    build_scope_source_validation,
    build_stats,
)
from tools import skip_policy

PROJECT_ROOT = Path(__file__).resolve().parent
LOGS_DIR = (PROJECT_ROOT / PHASE1_SEED10_ROOT / "logs").resolve()
SKIPPED_GALLERIES_REGISTRY_PATH = PROJECT_ROOT / "data" / "gallery_lists" / "skipped_galleries_registry.csv"
GALLERY_LIST_PATHS_BY_FAIR = {
    "frieze_london": PROJECT_ROOT / "data" / "gallery_lists" / "gallery_list_frieze_london.csv",
    "liste": PROJECT_ROOT / "data" / "gallery_lists" / "gallery_list_liste.csv",
}
ALL_RAG_ZERO_SKIP_REASON_PRE_ENRICHMENT = "all_rag_zero_auto_detected_after_image_collect"
EXHIBITION_TEXT_ONLY_SKIP_REASON_PRE_ENRICHMENT = "exhibition_text_only_auto_detected_after_image_collect"
AUTO_SKIP_EVIDENCE_PRE_ENRICHMENT = "derived_from_current_raw_and_image_collect_scope_stats"
DEBUG_HTML_DIR_NAME = "debug_exhibitions_listing_html"
DEBUG_LINKS_DIR_NAME = "debug_exhibitions_listing_links"
DEBUG_TRIAGE_DIR_NAME = "debug_exhibitions_listing_triage"
DEBUG_TRIAGE_FILENAME_TEMPLATE = "debug_exhibitions_listing_triage_{run_id}.json"
YEAR_TOKEN_RE = re.compile(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)")
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
EXHIBITION_SCENE_STRONG_TOKENS = (
    "installation view",
    "installation",
    "exhibition view",
    "gallery view",
    "viewing room",
    "螻戊ｦｧ莨夐｢ｨ譎ｯ",
    "螻慕､ｺ鬚ｨ譎ｯ",
)
EXHIBITION_SCENE_WEAK_TOKENS = (
    "gallery",
    "exhibition",
    "works",
    "room",
    "wall",
    "floor",
    "installation",
)
def is_title_like_anchor(text: str) -> bool:
    normalized = (text or "").strip()
    if len(normalized) <= 3:
        return False
    words = normalized.split()
    if not words:
        return False
    return any(word[0].istitle() for word in words if word)


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
WINDOWS_PATH_SOFT_LIMIT = 240
BAD_HARD_ROUTE_SUBSTRINGS = (
    "/viewing-room",
    "/viewing_room",
    "/about",
    "/artists",
    "/artist",
    "/contact",
    "/team",
    "/profile",
    "/biography",
)
BAD_SOFT_ROUTE_SUBSTRINGS = (
    "/past",
    "/upcoming",
    "/art-fairs",
    "/art-fair",
)
DETAIL_PAGE_IMAGE_LIMIT = 1
LISTING_DYNAMIC_TARGET_CAP = 8
LISTING_UNKNOWN_YEAR_TARGET_CAP = 3
DETAIL_PAGE_TARGET_YEAR_SUPPORT_REASONS = {
    "year_signal_present",
    "two_digit_year_signal",
    "year_signal_in_url_path",
    "year_signal_in_url_path_override",
}


def _normalized_path_lower(url: str) -> str:
    return (urlparse(str(url or "")).path or "").strip().lower()


def classify_route_class(url: str) -> str:
    path = _normalized_path_lower(url)
    if not path:
        return "UNKNOWN"
    if any(token in path for token in BAD_HARD_ROUTE_SUBSTRINGS):
        return "BAD_HARD"
    if any(token in path for token in BAD_SOFT_ROUTE_SUBSTRINGS):
        return "BAD_SOFT"
    if classify_seed_url_type(url) == "listing":
        return "LISTING_ROOT"
    return "DETAIL_CANDIDATE"


def evaluate_route_guard(*, detail_url: str, seed_url: str) -> dict[str, Any]:
    detail_class = classify_route_class(detail_url)
    seed_class = classify_route_class(seed_url)
    reasons: list[str] = []
    decision = "allow"
    if detail_class == "BAD_HARD":
        decision = "reject"
        reasons.append("route_bad_hard")
    elif detail_class in {"BAD_SOFT", "LISTING_ROOT"}:
        decision = "quarantine"
        reasons.append("route_bad_soft_or_listing")
    elif detail_class != "DETAIL_CANDIDATE":
        decision = "quarantine"
        reasons.append("route_not_detail_candidate")
    elif seed_class == "BAD_HARD":
        # Listing/archive seed URLs are normal inputs for exhibition discovery.
        # Only keep a soft warning path when the originating seed is clearly non-exhibition.
        decision = "quarantine"
        reasons.append("seed_route_bad_hard")
    return {
        "decision": decision,
        "reasons": reasons,
        "detail_route_class": detail_class,
        "seed_route_class": seed_class,
    }


def evaluate_year_evidence_guard(
    *,
    candidate_year: int | None,
    evidence_text: str,
    detail_url: str,
    seed_url: str,
    target_year: int,
    parent_tag: str,
    detail_page_year_bucket: int | None = None,
    detail_page_year_reason: str = "",
) -> dict[str, Any]:
    reasons: list[str] = []
    decision = "allow"
    text = f"{detail_url}\n{seed_url}\n{evidence_text or ''}"
    year_tokens = extract_year_tokens(text)
    has_target_year = int(target_year) in year_tokens
    has_non_target_year = bool(year_tokens - {int(target_year)})
    metadata_fallback = parent_tag.lower() == "metadata" or "metadata_fallback" in (evidence_text or "").lower()
    detail_page_target_year_supported = detail_page_has_target_year_support(
        detail_page_year_bucket=detail_page_year_bucket,
        detail_page_year_reason=detail_page_year_reason,
    )

    if candidate_year is not None and int(candidate_year) != int(target_year):
        decision = "reject"
        reasons.append("candidate_year_non_target")
        year_confidence = "LOW"
        return {
            "decision": decision,
            "reasons": reasons,
            "year_confidence": year_confidence,
            "metadata_fallback": metadata_fallback,
            "year_tokens": sorted(year_tokens),
        }

    if candidate_year is None and metadata_fallback and not detail_page_target_year_supported:
        decision = "quarantine"
        reasons.append("metadata_fallback_without_candidate_year")

    if candidate_year is not None and int(candidate_year) == int(target_year):
        year_confidence = "HIGH"
    elif has_target_year and not has_non_target_year:
        year_confidence = "MEDIUM" if metadata_fallback else "HIGH"
    elif has_non_target_year:
        year_confidence = "LOW"
        if decision == "allow":
            decision = "reject"
            reasons.append("year_token_non_target")
    else:
        year_confidence = "LOW"
        if decision == "allow" and detail_page_target_year_supported:
            year_confidence = "MEDIUM"
            reasons.append("detail_page_target_year_support")
        elif decision == "allow":
            decision = "quarantine"
            reasons.append("weak_year_signal")

    return {
        "decision": decision,
        "reasons": reasons,
        "year_confidence": year_confidence,
        "metadata_fallback": metadata_fallback,
        "year_tokens": sorted(year_tokens),
    }


def evaluate_provenance_guard(
    *,
    detail_url: str,
    seed_url: str,
    seed_url_type: str,
    selected_reason: str,
    parent_tag: str,
    metadata_fallback: bool,
    detail_page_year_bucket: int | None = None,
    detail_page_year_reason: str = "",
) -> dict[str, Any]:
    reasons: list[str] = []
    decision = "allow"
    detail_domain = artist_img.normalize_domain(detail_url)
    seed_domain = artist_img.normalize_domain(seed_url)
    detail_type = classify_seed_url_type(detail_url)
    trace_coherence = bool(detail_domain and seed_domain and detail_domain == seed_domain and detail_type == "detail")
    detail_page_target_year_supported = detail_page_has_target_year_support(
        detail_page_year_bucket=detail_page_year_bucket,
        detail_page_year_reason=detail_page_year_reason,
    )
    if not trace_coherence:
        decision = "quarantine"
        reasons.append("trace_coherence_missing")
    if selected_reason != "detail_page_candidate_rank":
        decision = "quarantine"
        reasons.append("selected_reason_nonstandard")
    if seed_url_type == "listing" and detail_type != "detail":
        decision = "quarantine"
        reasons.append("listing_without_detail_transition")
    if metadata_fallback and parent_tag.lower() == "metadata" and not detail_page_target_year_supported:
        decision = "quarantine"
        reasons.append("metadata_fallback_weak_provenance")
    return {
        "decision": decision,
        "reasons": reasons,
        "trace_coherence": trace_coherence,
        "detail_type": detail_type,
    }


def build_semantic_key(
    *,
    fair_slug: str,
    gallery_name_en: str,
    source_url: str,
    seed_source_url: str,
    image_url: str,
    payload_hash: str,
) -> str:
    parts = (
        str(fair_slug or "").strip().lower(),
        normalize_gallery_name_for_registry(gallery_name_en),
        artist_img.normalize_url_for_link_compare(source_url),
        artist_img.normalize_url_for_link_compare(seed_source_url),
        artist_img.normalize_image_url_for_dedupe(image_url),
        str(payload_hash or "").strip().lower(),
    )
    return "|".join(parts)


def _add_map_value(mapping: dict[str, set[str]], key: str, value: str) -> None:
    if not key:
        return
    bucket = mapping.setdefault(key, set())
    if value:
        bucket.add(value)


def evaluate_duplicate_collision_guard(
    *,
    local_path: str,
    r2_key: str,
    semantic_key: str,
    known_local_path_map: dict[str, set[str]],
    known_r2_key_map: dict[str, set[str]],
    in_case_local_path_map: dict[str, set[str]],
    in_case_r2_key_map: dict[str, set[str]],
) -> dict[str, Any]:
    reasons: list[str] = []
    decision = "allow"
    no_change_ok = False

    local_semantic_keys = set()
    if local_path:
        local_semantic_keys |= known_local_path_map.get(local_path, set())
        local_semantic_keys |= in_case_local_path_map.get(local_path, set())
    r2_semantic_keys = set()
    if r2_key:
        r2_semantic_keys |= known_r2_key_map.get(r2_key, set())
        r2_semantic_keys |= in_case_r2_key_map.get(r2_key, set())

    collided_semantic_keys = local_semantic_keys | r2_semantic_keys
    if collided_semantic_keys:
        if semantic_key in collided_semantic_keys:
            no_change_ok = True
            decision = "no_change_ok"
            reasons.append("duplicate_semantic_key_observed")
        else:
            decision = "reject"
            if local_semantic_keys:
                reasons.append("local_path_collision_non_semantic")
            if r2_semantic_keys:
                reasons.append("r2_key_collision_non_semantic")

    return {"decision": decision, "reasons": reasons, "no_change_ok": no_change_ok}


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase1 seed10 exhibitions image collect")
    parser.add_argument("--target-year", type=int, default=2025)
    parser.add_argument("--target-images-per-exhibition", type=int, default=1)
    parser.add_argument("--only-fair-slug", default="")
    parser.add_argument("--only-gallery-name", default="")
    parser.add_argument("--only-source-url", default="")
    parser.add_argument("--targets-csv", default="")
    parser.add_argument(
        "--output-json",
        default="",
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
        help="no network / no writes; compute fill-missing counters only",
    )
    parser.add_argument(
        "--dry-run-output",
        default="",
        help="optional dry-run summary JSON output path",
    )
    parser.add_argument(
        "--debug-gallery-triage",
        default="",
        help="Comma-separated gallery_name_en values to emit listing debug artifacts (limited to listing seeds)",
    )
    parser.add_argument(
        "--debug-output-dir",
        default=str(LOGS_DIR),
        help="Base directory for debug html, link JSONs, and triage summary (default under logs)",
    )
    return parser.parse_args()


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def utc_timestamp_compact() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def read_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_gallery_name_for_registry(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip().lower())


def load_skipped_gallery_lookup(path: Path) -> dict[str, dict[Any, Any]]:
    return build_skip_lookup(load_skip_registry_entries(path))


def _build_scope_targets_for_skip_cleanup(targets: list[dict[str, Any]]) -> list[BreakdownScopeTarget]:
    seen: set[tuple[str, str]] = set()
    out: list[BreakdownScopeTarget] = []
    for row in targets:
        fair_slug = normalize_fair_slug(str(row.get("fair_slug") or ""))
        gallery_name_en = str(row.get("gallery_name_en") or "").strip()
        if not fair_slug or not gallery_name_en:
            continue
        scope_key = (fair_slug.casefold(), gallery_name_en.casefold())
        if scope_key in seen:
            continue
        seen.add(scope_key)
        out.append(BreakdownScopeTarget(fair_slug=fair_slug, gallery_name_en=gallery_name_en))
    return out


def execute_auto_skip_registry_cleanup_after_image_collect(
    *,
    targets: list[dict[str, Any]],
    target_year: int,
    run_id: str,
    source_scope_file: str,
) -> dict[str, Any]:
    scope_targets = _build_scope_targets_for_skip_cleanup(targets)
    if not scope_targets:
        return {
            "status": "planned_contract_only",
            "registry_path": str(SKIPPED_GALLERIES_REGISTRY_PATH),
            "target_gallery_row_total": 0,
            "all_rag_zero_detected_count": 0,
            "all_rag_zero_detected_rows": [],
            "exhibition_text_only_detected_count": 0,
            "exhibition_text_only_detected_rows": [],
            "skip_registry_apply": {
                "status": "applied",
                "registry_path": str(SKIPPED_GALLERIES_REGISTRY_PATH),
                "added": 0,
                "updated": 0,
                "unchanged": 0,
                "total": len(load_skip_registry_entries(SKIPPED_GALLERIES_REGISTRY_PATH)),
            },
            "gallery_list_removal_apply": [],
            "blocking_errors": [],
        }

    stats = build_stats(int(target_year))
    scope_validation = build_scope_source_validation(targets=scope_targets, stats=stats)
    target_gallery_rows = [
        row
        for row in scope_validation.get("target_gallery_rows", [])
        if isinstance(row, dict)
    ]
    all_rag_zero_detected_rows = [row for row in target_gallery_rows if is_all_rag_zero_target_row(row)]
    exhibition_text_only_detected_rows = [
        row for row in target_gallery_rows if is_exhibition_text_only_target_row(row)
    ]
    all_rag_zero_entries = build_all_rag_zero_skip_entries(
        target_gallery_rows=all_rag_zero_detected_rows,
        skip_reason=ALL_RAG_ZERO_SKIP_REASON_PRE_ENRICHMENT,
        run_id=run_id,
        source_scope_file=source_scope_file,
        evidence=AUTO_SKIP_EVIDENCE_PRE_ENRICHMENT,
    )
    exhibition_text_only_entries = build_exhibition_text_only_skip_entries(
        target_gallery_rows=exhibition_text_only_detected_rows,
        skip_reason=EXHIBITION_TEXT_ONLY_SKIP_REASON_PRE_ENRICHMENT,
        run_id=run_id,
        source_scope_file=source_scope_file,
        evidence=AUTO_SKIP_EVIDENCE_PRE_ENRICHMENT,
    )
    combined_entries: list[Any] = []
    seen_scope_keys: set[tuple[str, str]] = set()
    for entry in [*all_rag_zero_entries, *exhibition_text_only_entries]:
        if entry.scope_key in seen_scope_keys:
            continue
        seen_scope_keys.add(entry.scope_key)
        combined_entries.append(entry)

    existing_entries = load_skip_registry_entries(SKIPPED_GALLERIES_REGISTRY_PATH)
    skip_registry_apply: dict[str, Any] = {
        "status": "applied",
        "registry_path": str(SKIPPED_GALLERIES_REGISTRY_PATH),
        "added": 0,
        "updated": 0,
        "unchanged": len(combined_entries),
        "total": len(existing_entries),
    }
    if combined_entries:
        skip_registry_apply = upsert_skip_registry_entries(SKIPPED_GALLERIES_REGISTRY_PATH, combined_entries)
        skip_registry_apply["status"] = "applied"

    apply_lookup = build_skip_lookup(load_skip_registry_entries(SKIPPED_GALLERIES_REGISTRY_PATH))
    target_fair_slugs = sorted(
        {
            normalize_fair_slug(str(row.get("fair_slug") or ""))
            for row in [*all_rag_zero_detected_rows, *exhibition_text_only_detected_rows]
            if str(row.get("fair_slug") or "").strip()
        }
    )
    gallery_list_removal_apply: list[dict[str, Any]] = []
    blocking_errors: list[str] = []
    for fair_slug in target_fair_slugs:
        gallery_list_path = GALLERY_LIST_PATHS_BY_FAIR.get(fair_slug)
        if gallery_list_path is None:
            blocking_errors.append(f"missing_gallery_list_path:{fair_slug}")
            continue
        result = remove_skipped_from_gallery_list_csv(
            path=gallery_list_path,
            fair_slug=fair_slug,
            lookup=apply_lookup,
            apply=True,
        )
        gallery_list_removal_apply.append(result)
        if str(result.get("status") or "").startswith("blocked"):
            blocking_errors.append(f"gallery_list_cleanup_blocked:{fair_slug}")

    stage_status = "applied" if not blocking_errors else "blocked_gallery_list_cleanup_apply_failed"
    return {
        "status": stage_status,
        "registry_path": str(SKIPPED_GALLERIES_REGISTRY_PATH),
        "skip_reason_map": {
            "all_rag_zero": ALL_RAG_ZERO_SKIP_REASON_PRE_ENRICHMENT,
            "exhibition_text_only": EXHIBITION_TEXT_ONLY_SKIP_REASON_PRE_ENRICHMENT,
        },
        "skip_evidence": AUTO_SKIP_EVIDENCE_PRE_ENRICHMENT,
        "source_scope_file": source_scope_file,
        "target_gallery_row_total": len(target_gallery_rows),
        "all_rag_zero_detected_count": len(all_rag_zero_detected_rows),
        "all_rag_zero_detected_rows": all_rag_zero_detected_rows,
        "exhibition_text_only_detected_count": len(exhibition_text_only_detected_rows),
        "exhibition_text_only_detected_rows": exhibition_text_only_detected_rows,
        "skip_registry_apply": skip_registry_apply,
        "gallery_list_removal_apply": gallery_list_removal_apply,
        "blocking_errors": blocking_errors,
    }


def gallery_slug(value: str) -> str:
    return artist_img.slugify_token(value or "unknown-gallery", fallback="unknown-gallery", max_len=80)


def fair_slug_to_token(fair_slug: str) -> str:
    return (fair_slug or "").strip().replace("_", "-")


def exhibition_slug_from_source_url(url: str) -> str:
    path = re.sub(r"[?#].*$", "", (url or "").strip())
    last = path.rstrip("/").split("/")[-1] if path else ""
    if not last:
        last = "exhibition"
    return artist_img.slugify_token(last, fallback="exhibition", max_len=48)


def is_windows_path_too_long(path: Path) -> bool:
    return os.name == "nt" and len(str(path)) >= WINDOWS_PATH_SOFT_LIMIT


def compact_image_filename_for_windows(
    *,
    gallery_token: str,
    exhibition_token: str,
    source_hash8: str,
    image_index: int,
    ext_token: str,
) -> str:
    gallery_short = artist_img.slugify_token(gallery_token, fallback="gallery", max_len=18)
    exhibition_hash12 = hashlib.sha1(exhibition_token.encode("utf-8")).hexdigest()[:12]
    return f"{gallery_short}__x{exhibition_hash12}__{source_hash8}__img_{image_index:02d}.{ext_token}"


def extract_year_tokens(text: str) -> set[int]:
    years: set[int] = set()
    for m in YEAR_TOKEN_RE.finditer(str(text or "")):
        try:
            years.add(int(m.group(1)))
        except ValueError:
            continue
    return years


def has_explicit_non_target_year(text: str, target_year: int) -> bool:
    years = extract_year_tokens(text)
    return bool(years) and int(target_year) not in years


def extract_links_from_html(html: str) -> list[tuple[str, str]]:
    parser = LinkHTMLParser()
    parser.feed(html)
    parser.close()
    return parser.links


def path_segments_from_url(url: str) -> list[str]:
    path = urlparse(url).path or ""
    return [segment for segment in path.lower().split("/") if segment]


def classify_seed_url_type(url: str) -> str:
    parsed = urlparse(str(url or ""))
    query_pairs = {k.lower(): v.lower() for k, v in parse_qsl(parsed.query, keep_blank_values=True)}
    if query_pairs.get("view") == "category" or query_pairs.get("layout") == "blog":
        return "listing"
    segments = path_segments_from_url(url)
    if not segments:
        return "listing"
    last = segments[-1]
    if last in EXHIBITION_LISTING_PATH_SEGMENTS:
        return "listing"
    if len(segments) >= 2 and segments[-2] == "category":
        return "listing"
    return "detail"


def ensure_debug_dirs(base_dir: Path, run_id: str) -> tuple[Path, Path]:
    html_dir = base_dir / DEBUG_HTML_DIR_NAME / run_id
    links_dir = base_dir / DEBUG_LINKS_DIR_NAME / run_id
    html_dir.mkdir(parents=True, exist_ok=True)
    links_dir.mkdir(parents=True, exist_ok=True)
    return html_dir, links_dir


def normalize_gallery_debug(name: str) -> str:
    if not name:
        return ""
    normalized = unicodedata.normalize("NFKC", name)
    collapsed = re.sub(r"\s+", " ", normalized.strip())
    return collapsed.lower()


def looks_like_exhibition_link(candidate_url: str, anchor_text: str) -> bool:
    target = f"{candidate_url.lower()} {anchor_text.lower()}".strip()
    if any(keyword in target for keyword in LINK_KEYWORDS):
        return True
    return False


def is_candidate_title_like(candidate_url: str, anchor_text: str, base_domain: str) -> bool:
    return (
        bool(anchor_text and is_title_like_anchor(anchor_text))
        and artist_img.normalize_domain(candidate_url) == base_domain
        and classify_seed_url_type(candidate_url) == "detail"
    )


def score_exhibition_detail_candidate(url: str, anchor_text: str, target_year: int) -> int:
    score = 0
    url_type = classify_seed_url_type(url)
    segments = path_segments_from_url(url)
    has_listing_segment = any(segment in EXHIBITION_LISTING_PATH_SEGMENTS for segment in segments)
    if url_type == "detail":
        score += 35
    else:
        score -= 20
    if url_type == "detail" and has_listing_segment:
        score += 20
    elif has_listing_segment:
        score -= 30
    target = f"{url.lower()} {anchor_text.lower()}".strip()
    if str(int(target_year)) in target:
        score += 25
    if re.search(r"\b(current|now|ongoing)\b", target):
        score += 8
    if re.search(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)", target) and str(int(target_year)) not in target:
        score -= 6
    score += min(len(path_segments_from_url(url)), 4)
    return score


def _fetch_html_cached(
    session: requests.Session,
    page_cache: dict[str, tuple[bool, str, str]],
    url: str,
) -> tuple[bool, str, str]:
    canonical = artist_img.normalize_url_for_link_compare(url)
    cached = page_cache.get(canonical)
    if cached is not None:
        return cached
    ok, html, final_url = artist_img.fetch_html(session, url)
    result = (ok, html, final_url)
    page_cache[canonical] = result
    return result


def resolve_exhibition_detail_urls(
    *,
    session: requests.Session,
    page_cache: dict[str, tuple[bool, str, str]],
    seed_url: str,
    seed_html: str,
    target_year: int,
    max_candidates: int = 32,
    max_depth: int = 2,
) -> list[dict[str, Any]]:
    seed_type = classify_seed_url_type(seed_url)
    if seed_type == "detail":
        return [{"url": seed_url, "anchor_text": "", "seed_url_type": seed_type, "score": 100}]

    best_by_canonical: dict[str, dict[str, Any]] = {}
    listing_queue: list[tuple[str, str, int]] = [(seed_url, seed_html, 0)]
    visited_listing: set[str] = {artist_img.normalize_url_for_link_compare(seed_url)}

    while listing_queue:
        parent_url, parent_html, depth = listing_queue.pop(0)
        for href, anchor_text in extract_links_from_html(parent_html):
            href = href.strip()
            if not href:
                continue
            if href.startswith(("mailto:", "tel:", "javascript:")):
                continue
            absolute_url = urljoin(parent_url, href)
            parsed = urlparse(absolute_url)
            if parsed.scheme not in ("http", "https"):
                continue
            if artist_img.normalize_domain(absolute_url) != artist_img.normalize_domain(seed_url):
                continue
            title_candidate = is_candidate_title_like(
                absolute_url,
                anchor_text,
                artist_img.normalize_domain(seed_url),
            )
            if not looks_like_exhibition_link(absolute_url, anchor_text) and not title_candidate:
                continue
            canonical_url = artist_img.normalize_url_for_link_compare(absolute_url)
            score = score_exhibition_detail_candidate(canonical_url, anchor_text, target_year) - (depth * 2)
            previous = best_by_canonical.get(canonical_url)
            if previous is None or score > int(previous.get("score") or 0):
                best_by_canonical[canonical_url] = {
                    "url": canonical_url,
                    "anchor_text": anchor_text,
                    "seed_url_type": classify_seed_url_type(parent_url),
                    "score": score,
                }

            if depth + 1 >= max_depth:
                continue
            if classify_seed_url_type(canonical_url) != "listing":
                continue
            if canonical_url in visited_listing:
                continue
            ok_child, child_html, child_final_url = _fetch_html_cached(session, page_cache, canonical_url)
            if not ok_child or not child_html:
                continue
            child_url = artist_img.normalize_url_for_link_compare(child_final_url or canonical_url)
            if child_url in visited_listing:
                continue
            visited_listing.add(child_url)
            listing_queue.append((child_url, child_html, depth + 1))

    if not best_by_canonical:
        return [{"url": seed_url, "anchor_text": "", "seed_url_type": seed_type, "score": -100}]

    ranked = sorted(
        best_by_canonical.values(),
        key=lambda item: (-int(item.get("score") or 0), str(item.get("url") or "")),
    )
    return ranked[:max_candidates]


def collect_detail_pages(
    *,
    detail_candidates: list[dict[str, Any]],
    session: requests.Session,
    page_cache: dict[str, tuple[bool, str, str]],
    target_year: int,
) -> tuple[list[dict[str, Any]], int]:
    detail_pages: list[dict[str, Any]] = []
    detail_fetch_failed_count = 0
    for candidate in detail_candidates:
        detail_url = str(candidate.get("url") or "").strip()
        if not detail_url:
            continue
        ok_detail, detail_html, detail_final_url = artist_img.fetch_html(
            session, detail_url
        )
        if not ok_detail or not detail_html:
            detail_fetch_failed_count += 1
            continue
        detail_page_url = artist_img.normalize_url_for_link_compare(
            detail_final_url or detail_url
        )
        _year_ok, year_reason = should_include_target_year_page(
            page_url=detail_page_url,
            html=detail_html,
            target_year=target_year,
        )
        if (
            not _year_ok
            and year_reason == "explicit_non_target_year"
            and has_target_year_signal_in_url(detail_page_url, target_year)
        ):
            _year_ok = True
            year_reason = "year_signal_in_url_path_override"
        if year_reason == "no_explicit_year_signal":
            year_bucket = 1
        elif _year_ok:
            year_bucket = 0
        else:
            year_bucket = 2
        detail_pages.append(
            {
                "url": detail_page_url,
                "html": detail_html,
                "score": int(candidate.get("score") or 0),
                "year_bucket": year_bucket,
                "year_reason": year_reason,
            }
        )
    detail_pages = sorted(
        detail_pages,
        key=lambda item: (
            normalize_year_bucket(item.get("year_bucket")),
            -int(item.get("score") or 0),
            str(item.get("url") or ""),
        ),
    )
    return detail_pages, detail_fetch_failed_count


SECOND_PASS_WAIT_MS = 2500


def fetch_hydrated_detail_html(detail_url: str) -> str | None:
    context = artist_img._ensure_playwright_context()
    if context is None:
        return None
    page = None
    try:
        page = context.new_page()
        page.goto(detail_url, wait_until="domcontentloaded", timeout=artist_img.PLAYWRIGHT_NAV_TIMEOUT_MS)
        try:
            page.wait_for_load_state("networkidle", timeout=artist_img.PLAYWRIGHT_NAV_TIMEOUT_MS)
        except artist_img.PlaywrightTimeoutError:
            pass
        page.wait_for_timeout(SECOND_PASS_WAIT_MS)
        return page.content()
    except artist_img.PlaywrightError:
        return None
    except Exception:
        return None
    finally:
        if page is not None:
            try:
                page.close()
            except Exception:
                pass


METADATA_LOGO_KEYWORDS = ("logo", "icon", "avatar", "thumbnail", "badge")


def collect_metadata_image_urls(html: str, base_url: str) -> list[str]:
    urls: list[str] = []
    for tag_html in re.findall(r"<meta[^>]*>", html, re.IGNORECASE):
        name_match = re.search(r"(?:property|name)\s*=\s*['\"](og:image|twitter:image)['\"]", tag_html, re.IGNORECASE)
        if not name_match:
            continue
        content_match = re.search(r"content\s*=\s*['\"]([^'\"]+)['\"]", tag_html, re.IGNORECASE)
        if not content_match:
            continue
        urls.append(urljoin(base_url, content_match.group(1).strip()))
    for link_html in re.findall(r"<link[^>]*rel=['\"][^'\"]*image[^'\"]*['\"][^>]*>", html, re.IGNORECASE):
        href_match = re.search(r"href\s*=\s*['\"]([^'\"]+)['\"]", link_html, re.IGNORECASE)
        if href_match:
            urls.append(urljoin(base_url, href_match.group(1).strip()))
    normalized: list[str] = []
    seen: set[str] = set()
    for candidate in urls:
        canonical = artist_img.normalize_url_for_link_compare(candidate)
        if not canonical or canonical in seen:
            continue
        seen.add(canonical)
        normalized.append(candidate)
    return normalized


def collect_basic_meta_image_urls(html: str, base_url: str) -> list[str]:
    urls: list[str] = []
    for key in ("og:image", "twitter:image"):
        for match in re.finditer(rf'{key}[^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE):
            urls.append(urljoin(base_url, match.group(1).strip()))
    normalized: list[str] = []
    seen: set[str] = set()
    for candidate in urls:
        canonical = artist_img.normalize_url_for_link_compare(candidate)
        if not canonical or canonical in seen:
            continue
        seen.add(canonical)
        normalized.append(candidate)
    return normalized


def build_metadata_fallback_candidates(detail_url: str, html: str) -> list[dict[str, Any]]:
    urls = [
        candidate
        for candidate in collect_metadata_image_urls(html, detail_url)
        if not any(keyword in candidate.lower() for keyword in METADATA_LOGO_KEYWORDS)
    ]
    if not urls:
        urls = [
            candidate
            for candidate in collect_basic_meta_image_urls(html, detail_url)
            if not any(keyword in candidate.lower() for keyword in METADATA_LOGO_KEYWORDS)
        ]
    candidates: list[dict[str, Any]] = []
    for index, candidate_url in enumerate(urls):
        candidates.append(
            {
                "url": candidate_url,
                "score": -5,
                "year": None,
                "year_candidates": [],
                "attrs": {"alt": "", "class": ""},
                "parent_tag": "metadata",
                "evidence_text": "metadata_fallback",
                "page_order": index + 1,
            }
        )
    return candidates

def _parse_int_attr(value: Any) -> int:
    raw = str(value or "").strip()
    if not raw:
        return 0
    try:
        return int(raw)
    except ValueError:
        return 0


def _candidate_size_area(candidate: dict[str, Any]) -> int:
    attrs = candidate.get("attrs") if isinstance(candidate.get("attrs"), dict) else {}
    width = _parse_int_attr(attrs.get("width"))
    height = _parse_int_attr(attrs.get("height"))
    if width <= 0 or height <= 0:
        return 0
    return width * height


def _candidate_scene_score(candidate: dict[str, Any]) -> int:
    candidate_url = str(candidate.get("url") or "").lower()
    evidence_text = str(candidate.get("evidence_text") or "").lower()
    attrs = candidate.get("attrs") if isinstance(candidate.get("attrs"), dict) else {}
    alt_text = str(attrs.get("alt") or "").lower()
    class_text = str(attrs.get("class") or "").lower()
    parent_tag = str(candidate.get("parent_tag") or "").lower()
    merged = " ".join((candidate_url, evidence_text, alt_text, class_text, parent_tag))
    score = 0
    for token in EXHIBITION_SCENE_STRONG_TOKENS:
        if token in merged:
            score += 3
    for token in EXHIBITION_SCENE_WEAK_TOKENS:
        if token in merged:
            score += 1
    if parent_tag in {"figure", "picture"}:
        score += 1
    return score


def sort_exhibition_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not candidates:
        return []
    scene_scores = [_candidate_scene_score(candidate) for candidate in candidates]
    has_scene_signal = any(score > 0 for score in scene_scores)
    decorated = list(zip(candidates, scene_scores))
    if has_scene_signal:
        return [
            candidate
            for candidate, _scene in sorted(
                decorated,
                key=lambda pair: (
                    pair[1],
                    1 if artist_img.normalize_candidate_year(pair[0].get("year")) is not None else 0,
                    artist_img.normalize_candidate_year(pair[0].get("year")) or -1,
                    _candidate_size_area(pair[0]),
                    int(pair[0].get("score") or 0),
                    -int(pair[0].get("page_order") or 0),
                ),
                reverse=True,
            )
        ]
    # If scene蛻､螳壹′蜿悶ｌ縺ｪ縺・ｴ蜷医・譛螟ｧ繧ｵ繧､繧ｺ蜆ｪ蜈医〒繝輔か繝ｼ繝ｫ繝舌ャ繧ｯ縲・
    return [
        candidate
        for candidate, _scene in sorted(
            decorated,
            key=lambda pair: (
                _candidate_size_area(pair[0]),
                1 if artist_img.normalize_candidate_year(pair[0].get("year")) is not None else 0,
                artist_img.normalize_candidate_year(pair[0].get("year")) or -1,
                int(pair[0].get("score") or 0),
                -int(pair[0].get("page_order") or 0),
            ),
            reverse=True,
        )
    ]


def classify_year_bucket(page_url: str, html: str, target_year: int) -> int:
    years = extract_year_tokens(f"{page_url}\n{html}")
    if int(target_year) in years:
        return 0
    if years:
        return 2
    return 1


def has_target_year_signal_in_url(url: str, target_year: int) -> bool:
    token = str(int(target_year))
    path = (urlparse(str(url or "")).path or "").lower()
    return bool(re.search(rf"(?<!\d){re.escape(token)}(?!\d)", path))


def normalize_year_bucket(value: Any) -> int:
    try:
        bucket = int(value)
    except (TypeError, ValueError):
        return 2
    return bucket if bucket in (0, 1, 2) else 2


def detail_page_has_target_year_support(
    *,
    detail_page_year_bucket: Any,
    detail_page_year_reason: str,
) -> bool:
    return normalize_year_bucket(detail_page_year_bucket) == 0 and str(detail_page_year_reason or "").strip() in (
        DETAIL_PAGE_TARGET_YEAR_SUPPORT_REASONS
    )


def derive_case_target_images(
    *,
    seed_url_type: str,
    requested_target_images: int,
    detail_pages: list[dict[str, Any]],
) -> int:
    base_target = max(DETAIL_PAGE_IMAGE_LIMIT, int(requested_target_images or DETAIL_PAGE_IMAGE_LIMIT))
    if seed_url_type != "listing":
        return base_target
    strong_target_pages = sum(
        1
        for page in detail_pages
        if detail_page_has_target_year_support(
            detail_page_year_bucket=page.get("year_bucket"),
            detail_page_year_reason=str(page.get("year_reason") or ""),
        )
    )
    if strong_target_pages > 0:
        listing_target = (strong_target_pages + 1) // 2
        return max(base_target, min(LISTING_DYNAMIC_TARGET_CAP, listing_target))
    weak_target_pages = sum(1 for page in detail_pages if normalize_year_bucket(page.get("year_bucket")) == 1)
    if weak_target_pages > 0:
        return max(base_target, min(LISTING_UNKNOWN_YEAR_TARGET_CAP, weak_target_pages))
    return base_target


def load_targets(
    target_year: int,
    *,
    raw_dir: Path,
    only_fair_slug: str = "",
    only_gallery_name: str = "",
    only_source_url: str = "",
    targets_csv: str = "",
) -> list[dict[str, Any]]:
    if targets_csv:
        path = Path(targets_csv)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        rows: list[dict[str, Any]] = []
        if not path.exists():
            return rows
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                fair_slug = str(row.get("fair_slug") or "").strip()
                gallery_name = str(row.get("gallery_name_en") or "").strip()
                source_url = str(
                    row.get("source_url")
                    or row.get("exhibitions_url")
                    or row.get("exhibition_url")
                    or ""
                ).strip()
                if not fair_slug or not source_url:
                    continue
                csv_target_year_raw = str(row.get("target_year") or "").strip()
                if csv_target_year_raw and csv_target_year_raw.isdigit() and int(csv_target_year_raw) != int(target_year):
                    continue
                if has_explicit_non_target_year(source_url, target_year):
                    continue
                rows.append(
                    {
                        "fair_slug": fair_slug,
                        "gallery_name_en": gallery_name,
                        "source_url": source_url,
                        "target_year": int(target_year),
                    }
                )
        return rows

    targets: list[dict[str, Any]] = []
    only_fair_slug_norm = (only_fair_slug or "").strip().lower()
    only_gallery_name_norm = normalize_gallery_name_for_registry(only_gallery_name)
    only_source_url_raw = str(only_source_url or "").strip()
    only_source_url_norm = (
        artist_img.normalize_url_for_link_compare(only_source_url_raw)
        if only_source_url_raw
        else ""
    )
    for path in sorted(raw_dir.glob(f"exhibitions_*_{target_year}.jsonl")):
        for row in read_jsonl_rows(path):
            fair_slug = str(row.get("fair_slug") or "").strip()
            if only_fair_slug_norm and fair_slug.lower() != only_fair_slug_norm:
                continue
            source_url = str(row.get("source_url") or "").strip()
            if not source_url:
                continue
            row_target_year_raw = str(row.get("target_year") or "").strip()
            if row_target_year_raw and row_target_year_raw.isdigit() and int(row_target_year_raw) != int(target_year):
                continue
            if has_explicit_non_target_year(source_url, target_year):
                continue
            if only_source_url_norm and artist_img.normalize_url_for_link_compare(source_url) != only_source_url_norm:
                continue
            gallery_name = str(row.get("gallery_name_en") or "").strip()
            if only_gallery_name_norm and normalize_gallery_name_for_registry(gallery_name) != only_gallery_name_norm:
                continue
            targets.append(
                {
                    "fair_slug": fair_slug,
                    "gallery_name_en": gallery_name,
                    "source_url": source_url,
                    "target_year": int(row.get("target_year") or target_year),
                }
            )
    return targets


def load_existing_image_hashes(
    meta_path: Path,
) -> tuple[set[str], set[str], Counter[str], dict[str, set[str]], dict[str, set[str]]]:
    url_hashes: set[str] = set()
    payload_hashes: set[str] = set()
    existing_source_counter: Counter[str] = Counter()
    known_local_path_map: dict[str, set[str]] = {}
    known_r2_key_map: dict[str, set[str]] = {}
    for row in read_jsonl_rows(meta_path):
        local_path_resolved = resolve_image_local_path(str(row.get("local_path") or ""))
        has_local_file = bool(local_path_resolved and local_path_resolved.exists() and local_path_resolved.is_file())
        # Phase1.7 missing-only rule:
        # key-only rows with missing local file are treated as missing-recovery targets.
        if not has_local_file:
            continue
        image_url = str(row.get("image_url") or "")
        if image_url:
            url_hashes.add(artist_img.normalize_image_url_for_dedupe(image_url))
        ph = str(row.get("payload_hash") or "").strip()
        if ph:
            payload_hashes.add(ph)
        source_url = artist_img.normalize_url_for_link_compare(str(row.get("source_url") or ""))
        if source_url:
            existing_source_counter[source_url] += 1
        semantic_key = build_semantic_key(
            fair_slug=str(row.get("fair_slug") or ""),
            gallery_name_en=str(row.get("gallery_name_en") or ""),
            source_url=str(row.get("source_url") or ""),
            seed_source_url=str(row.get("seed_source_url") or ""),
            image_url=str(row.get("image_url") or ""),
            payload_hash=ph,
        )
        _add_map_value(known_local_path_map, str(row.get("local_path") or ""), semantic_key)
        _add_map_value(known_r2_key_map, str(row.get("r2_key") or ""), semantic_key)
    return url_hashes, payload_hashes, existing_source_counter, known_local_path_map, known_r2_key_map


def build_breakdowns(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    breakdown: dict[tuple[str, str], int] = {}
    for row in rows:
        fair = str(row.get("fair_slug") or "")
        gallery = str(row.get("gallery_name_en") or "")
        key = (fair, gallery)
        breakdown[key] = breakdown.get(key, 0) + 1
    out: list[dict[str, Any]] = []
    for (fair, gallery), count in sorted(breakdown.items(), key=lambda item: (item[0][0], item[0][1])):
        out.append({"fair_slug": fair, "gallery_name_en": gallery, "saved_exhibitions": count})
    return out


def build_seed_transition_breakdown(cases: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    by_seed_type: dict[str, dict[str, int]] = {}
    for case in cases:
        seed_type = str(case.get("seed_url_type") or "")
        bucket = by_seed_type.setdefault(
            seed_type,
            {
                "case_count": 0,
                "saved_case_count": 0,
                "new_saved_case_count": 0,
                "existing_hit_only_case_count": 0,
            },
        )
        bucket["case_count"] += 1
        if int(case.get("saved_images") or 0) > 0:
            bucket["saved_case_count"] += 1
        if int(case.get("new_saved_images") or 0) > 0:
            bucket["new_saved_case_count"] += 1
        if bool(case.get("existing_hit_only")):
            bucket["existing_hit_only_case_count"] += 1
    return {seed_type: dict(values) for seed_type, values in sorted(by_seed_type.items(), key=lambda item: item[0])}


def build_guard_counter_totals(cases: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    reject_counter: Counter[str] = Counter()
    quarantine_counter: Counter[str] = Counter()
    no_change_counter: Counter[str] = Counter()
    for case in cases:
        reject_counter.update(case.get("guard_reject_counts") or {})
        quarantine_counter.update(case.get("guard_quarantine_counts") or {})
        no_change_counter.update(case.get("guard_no_change_counts") or {})
    return {
        "guard_reject_counts": dict(reject_counter),
        "guard_quarantine_counts": dict(quarantine_counter),
        "guard_no_change_counts": dict(no_change_counter),
    }


def build_exhibition_failed_case_record(
    *,
    fair_slug: str,
    gallery_name_en: str,
    source_url: str,
    seed_url_type: str,
    target_images: int,
    reason: str,
    saved_images: int = 0,
    new_saved_images: int = 0,
    existing_hit_only: bool = False,
    detail_year_bucket_counts: dict[str, int] | None = None,
    guard_reject_counts: dict[str, int] | None = None,
    guard_quarantine_counts: dict[str, int] | None = None,
    guard_no_change_counts: dict[str, int] | None = None,
    detail_urls_considered_top10: list[str] | None = None,
    notes_top20: list[str] | None = None,
    html_fetch_error: str = "",
    playwright_runtime_diagnostics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "fair_slug": fair_slug,
        "gallery_name_en": gallery_name_en,
        "source_url": source_url,
        "seed_url_type": seed_url_type,
        "saved_images": int(saved_images),
        "new_saved_images": int(new_saved_images),
        "existing_hit_only": bool(existing_hit_only),
        "target_images": int(target_images),
        "reason": reason,
        "detail_year_bucket_counts": dict(detail_year_bucket_counts or {}),
        "guard_reject_counts": dict(guard_reject_counts or {}),
        "guard_quarantine_counts": dict(guard_quarantine_counts or {}),
        "guard_no_change_counts": dict(guard_no_change_counts or {}),
        "detail_urls_considered_top10": list(detail_urls_considered_top10 or []),
        "notes_top20": list(notes_top20 or []),
        "html_fetch_error": str(html_fetch_error or ""),
        "playwright_runtime_diagnostics": dict(playwright_runtime_diagnostics or {}),
    }


def main() -> int:
    args = parse_args()
    policy_mode = skip_policy.resolve_run_mode(
        mode=args.mode,
        allow_rebuild=bool(args.allow_rebuild),
        run_id=str(args.run_id or ""),
    )
    io_root = (PROJECT_ROOT / PHASE1_SEED10_ROOT).resolve()
    if policy_mode == skip_policy.REBUILD_MODE:
        io_root = skip_policy.build_trial_root(
            trial_root=args.trial_root,
            run_id=str(args.run_id or ""),
        )
    raw_dir = get_current_raw_dir(io_root) if policy_mode == skip_policy.REBUILD_MODE else PROJECT_ROOT / get_current_raw_dir()
    logs_dir = io_root / "logs"
    image_root_dir = (
        get_exhibition_image_cache_dir(io_root).resolve()
        if policy_mode == skip_policy.REBUILD_MODE
        else (PROJECT_ROOT / get_exhibition_image_cache_dir()).resolve()
    )

    args.target_images_per_exhibition = max(
        DETAIL_PAGE_IMAGE_LIMIT,
        int(args.target_images_per_exhibition or DETAIL_PAGE_IMAGE_LIMIT),
    )
    logs_dir.mkdir(parents=True, exist_ok=True)
    image_root_dir.mkdir(parents=True, exist_ok=True)
    debug_gallery_inputs = [name.strip() for name in args.debug_gallery_triage.split(",") if name.strip()]
    debug_galleries = {normalize_gallery_debug(name) for name in debug_gallery_inputs}
    debug_run_id = utc_timestamp_compact() if debug_galleries else ""
    debug_html_dir = None
    debug_links_dir = None
    debug_output_base: Path | None = None
    if debug_run_id:
        debug_output_base = Path(args.debug_output_dir or logs_dir)
        if not debug_output_base.is_absolute():
            debug_output_base = PROJECT_ROOT / debug_output_base
        debug_html_dir, debug_links_dir = ensure_debug_dirs(debug_output_base, debug_run_id)
    debug_triage_entries: list[dict[str, Any]] = []

    skipped_gallery_lookup = load_skipped_gallery_lookup(SKIPPED_GALLERIES_REGISTRY_PATH)
    targets = load_targets(
        args.target_year,
        raw_dir=raw_dir,
        only_fair_slug=args.only_fair_slug,
        only_gallery_name=args.only_gallery_name,
        only_source_url=args.only_source_url,
        targets_csv=args.targets_csv,
    )

    if args.dry_run:
        meta_rows_by_fair: dict[str, list[dict[str, Any]]] = {}
        candidate_total = len(targets)
        would_skip_count = 0
        would_fetch_count = 0
        key_present_but_file_missing_count = 0
        missing_examples: list[dict[str, Any]] = []

        for target in targets:
            fair_slug = str(target.get("fair_slug") or "")
            gallery_name_en = str(target.get("gallery_name_en") or "")
            source_url = str(target.get("source_url") or "")
            target_images = int(args.target_images_per_exhibition)
            source_norm = artist_img.normalize_url_for_link_compare(source_url)

            rows = meta_rows_by_fair.get(fair_slug)
            if rows is None:
                meta_path = get_current_exhibitions_image_meta_path(
                    fair_slug,
                    args.target_year,
                    root=raw_dir.parent,
                )
                rows = read_jsonl_rows(meta_path)
                meta_rows_by_fair[fair_slug] = rows

            valid_existing = 0
            missing_for_target = 0
            for row in rows:
                row_source_norm = artist_img.normalize_url_for_link_compare(str(row.get("source_url") or ""))
                if not row_source_norm or row_source_norm != source_norm:
                    continue
                local_path = resolve_image_local_path(str(row.get("local_path") or ""))
                has_local = bool(local_path and local_path.exists() and local_path.is_file())
                if has_local:
                    valid_existing += 1
                else:
                    missing_for_target += 1
                    if len(missing_examples) < 20:
                        missing_examples.append(
                            {
                                "fair_slug": fair_slug,
                                "gallery_name_en": gallery_name_en,
                                "source_url": source_url,
                                "local_path": str(row.get("local_path") or ""),
                                "image_url_hash": str(row.get("image_url_hash") or ""),
                            }
                        )

            key_present_but_file_missing_count += missing_for_target
            if valid_existing >= target_images:
                would_skip_count += 1
            else:
                would_fetch_count += 1

        dry_summary = {
            "runner": "run_phase1_seed10_exhibition_image_collect.py",
            "execution_mode": policy_mode,
            "dry_run": True,
            "target_year": int(args.target_year),
            "candidate_total": candidate_total,
            "would_skip_count": would_skip_count,
            "would_fetch_count": would_fetch_count,
            "would_write_count": 0,
            "key_present_but_file_missing_count": key_present_but_file_missing_count,
            "missing_examples_top20": missing_examples,
            "notes": ["dry_run_local_only_no_network_no_write"],
            "generated_at": utc_now_iso(),
        }
        dry_output_path = (
            Path(args.dry_run_output)
            if str(args.dry_run_output or "").strip()
            else (logs_dir / f"dryrun_run_phase1_seed10_exhibition_image_collect_{args.target_year}.json")
        )
        if not dry_output_path.is_absolute():
            dry_output_path = (PROJECT_ROOT / dry_output_path).resolve()
        write_json(dry_output_path, dry_summary)
        print(f"[exhibitions-image-collect][DRYRUN] output={dry_output_path}")
        return 0

    cases: list[dict[str, Any]] = []
    failed_cases: list[dict[str, Any]] = []
    all_saved_rows: list[dict[str, Any]] = []
    reason_counter: Counter[str] = Counter()
    seed_url_type_counter: Counter[str] = Counter()
    listing_resolved_seed_count = 0
    listing_resolved_detail_urls_total = 0

    with requests.Session() as session:
        session.headers.update({"User-Agent": "art-pulse-editor/phase1-exhibitions-image-collector"})
        page_cache: dict[str, tuple[bool, str, str]] = {}
        for target in targets:
            fair_slug = str(target["fair_slug"])
            gallery_name_en = str(target["gallery_name_en"])
            source_url = str(target["source_url"])
            target_images = max(
                DETAIL_PAGE_IMAGE_LIMIT,
                int(args.target_images_per_exhibition or DETAIL_PAGE_IMAGE_LIMIT),
            )
            case_notes: list[str] = []
            seed_url_type = classify_seed_url_type(source_url)
            seed_url_type_counter[seed_url_type] += 1
            if (
                find_skip_entry(
                    skipped_gallery_lookup,
                    fair_slug=fair_slug,
                    gallery_name_en=gallery_name_en,
                )
                is not None
            ):
                case = {
                    **target,
                    "seed_url_type": seed_url_type,
                    "saved_images": 0,
                    "target_images": target_images,
                    "target_met": False,
                    "status": "skipped",
                    "reason": "auto_skipped_by_registry",
                    "notes": ["auto_skipped_by_registry"],
                }
                cases.append(case)
                failed_cases.append(
                    build_exhibition_failed_case_record(
                        fair_slug=fair_slug,
                        gallery_name_en=gallery_name_en,
                        source_url=source_url,
                        seed_url_type=seed_url_type,
                        target_images=target_images,
                        reason="auto_skipped_by_registry",
                        notes_top20=["auto_skipped_by_registry"],
                    )
                )
                reason_counter["auto_skipped_by_registry"] += 1
                continue

            if has_explicit_non_target_year(source_url, args.target_year):
                reason = "source_url_out_of_target_year"
                reason_counter[reason] += 1
                case_notes.append(reason)
                failed_cases.append(
                    build_exhibition_failed_case_record(
                        fair_slug=fair_slug,
                        gallery_name_en=gallery_name_en,
                        source_url=source_url,
                        seed_url_type=seed_url_type,
                        target_images=target_images,
                        reason=reason,
                        notes_top20=case_notes[:20],
                    )
                )
                cases.append(
                    {
                        **target,
                        "seed_url_type": seed_url_type,
                        "saved_images": 0,
                        "target_images": target_images,
                        "target_met": False,
                        "status": "failed",
                        "reason": reason,
                        "notes": case_notes,
                    }
                )
                continue

            fair_token = fair_slug_to_token(fair_slug)
            gallery_token = gallery_slug(gallery_name_en)

            fair_dir = image_root_dir / str(args.target_year) / fair_token
            fair_dir.mkdir(parents=True, exist_ok=True)
            meta_path = get_current_exhibitions_image_meta_path(
                fair_slug,
                args.target_year,
                root=raw_dir.parent,
            )
            (
                known_url_hashes,
                known_payload_hashes,
                existing_source_counter,
                known_local_path_map,
                known_r2_key_map,
            ) = load_existing_image_hashes(meta_path)
            in_case_url_hashes: set[str] = set()
            in_case_payload_hashes: set[str] = set()
            in_case_local_path_map: dict[str, set[str]] = {}
            in_case_r2_key_map: dict[str, set[str]] = {}

            html_ok, html, final_url = artist_img.fetch_html(session, source_url)
            debug_active = (
                bool(debug_run_id)
                and normalize_gallery_debug(gallery_name_en) in debug_galleries
                and seed_url_type == "listing"
            )
            debug_links_raw: list[tuple[str, str]] = []
            html_dump_path = None
            link_debug_path = None
            if debug_active and html:
                html_dump_path = debug_html_dir / f"{fair_slug}_{gallery_token}_listing.html"
                html_dump_path.write_text(html, encoding="utf-8")
                debug_links_raw = extract_links_from_html(html)
            if not html_ok or not html:
                reason = "html_fetch_failed"
                reason_counter[reason] += 1
                html_fetch_error = str(final_url or "").strip()
                if html_fetch_error:
                    case_notes.append(html_fetch_error)
                playwright_runtime_diagnostics = artist_img.get_playwright_runtime_diagnostics()
                failed_cases.append(
                    build_exhibition_failed_case_record(
                        fair_slug=fair_slug,
                        gallery_name_en=gallery_name_en,
                        source_url=source_url,
                        seed_url_type=seed_url_type,
                        target_images=target_images,
                        reason=reason,
                        notes_top20=case_notes[:20],
                        html_fetch_error=html_fetch_error,
                        playwright_runtime_diagnostics=playwright_runtime_diagnostics,
                    )
                )
                cases.append(
                    {
                        **target,
                        "seed_url_type": seed_url_type,
                        "saved_images": 0,
                        "target_images": target_images,
                        "target_met": False,
                        "status": "failed",
                        "reason": reason,
                        "html_fetch_error": html_fetch_error,
                        "playwright_runtime_diagnostics": playwright_runtime_diagnostics,
                        "notes": case_notes,
                    }
                )
                continue

            page_url = final_url or source_url
            if has_explicit_non_target_year(page_url, args.target_year):
                reason = "page_url_out_of_target_year"
                reason_counter[reason] += 1
                case_notes.append(reason)
                failed_cases.append(
                    build_exhibition_failed_case_record(
                        fair_slug=fair_slug,
                        gallery_name_en=gallery_name_en,
                        source_url=source_url,
                        seed_url_type=seed_url_type,
                        target_images=target_images,
                        reason=reason,
                        notes_top20=case_notes[:20],
                    )
                )
                cases.append(
                    {
                        **target,
                        "seed_url_type": seed_url_type,
                        "saved_images": 0,
                        "target_images": target_images,
                        "target_met": False,
                        "status": "failed",
                        "reason": reason,
                        "notes": case_notes,
                    }
                )
                continue

            detail_candidates = resolve_exhibition_detail_urls(
                session=session,
                page_cache=page_cache,
                seed_url=page_url,
                seed_html=html,
                target_year=args.target_year,
                max_depth=2,
            )
            detail_pages, detail_fetch_failed_count = collect_detail_pages(
                detail_candidates=detail_candidates,
                session=session,
                page_cache=page_cache,
                target_year=args.target_year,
            )

            listing_resolved_to_detail_count = len(detail_pages)
            if seed_url_type == "listing" and listing_resolved_to_detail_count > 0:
                listing_resolved_seed_count += 1
                listing_resolved_detail_urls_total += listing_resolved_to_detail_count

            target_images = derive_case_target_images(
                seed_url_type=seed_url_type,
                requested_target_images=int(args.target_images_per_exhibition),
                detail_pages=detail_pages,
            )

            if not detail_pages:
                reason = "detail_page_fetch_failed"
                reason_counter[reason] += 1
                case_notes.append(f"detail_fetch_failed_count:{detail_fetch_failed_count}")
                failed_cases.append(
                    build_exhibition_failed_case_record(
                        fair_slug=fair_slug,
                        gallery_name_en=gallery_name_en,
                        source_url=source_url,
                        seed_url_type=seed_url_type,
                        target_images=target_images,
                        reason=reason,
                        notes_top20=case_notes[:20],
                    )
                )
                cases.append(
                    {
                        **target,
                        "seed_url_type": seed_url_type,
                        "listing_resolved_to_detail_count": listing_resolved_to_detail_count,
                        "saved_images": 0,
                        "target_images": target_images,
                        "target_met": False,
                        "status": "failed",
                        "reason": reason,
                        "notes": case_notes,
                    }
                )
                continue

            selected_urls: list[str] = []
            selected_reasons: list[str] = []
            selected_years: list[int | None] = []
            selected_evidence: list[str] = []
            saved_rows: list[dict[str, Any]] = []
            chosen_detail_url = ""
            year_bucket_counter: Counter[int] = Counter()
            for page in detail_pages:
                year_bucket_counter[normalize_year_bucket(page.get("year_bucket"))] += 1
            quota_eligible_detail_page_count = sum(
                1 for page in detail_pages if normalize_year_bucket(page.get("year_bucket")) in (0, 1)
            )
            existing_hit_detail_urls: set[str] = set()
            for page in detail_pages:
                detail_url_norm = artist_img.normalize_url_for_link_compare(str(page.get("url") or ""))
                if not detail_url_norm:
                    continue
                if existing_source_counter.get(detail_url_norm, 0) >= DETAIL_PAGE_IMAGE_LIMIT:
                    existing_hit_detail_urls.add(detail_url_norm)
            existing_hit = bool(existing_hit_detail_urls)
            existing_hit_detail_url = next(iter(existing_hit_detail_urls), "")

            image_index = 1
            listing_detail_reresolved = False
            metadata_collision_detected = False
            guard_reject_counter: Counter[str] = Counter()
            guard_quarantine_counter: Counter[str] = Counter()
            guard_no_change_counter: Counter[str] = Counter()
            raw_candidate_total = 0
            guard_pass_candidate_total = 0
            download_surviving_candidate_total = 0
            detail_pages_with_saved_image: set[str] = set()

            def build_failed_case_record(
                reason: str,
                *,
                saved_images: int,
                new_saved_images: int,
                existing_hit_only: bool,
            ) -> dict[str, Any]:
                return build_exhibition_failed_case_record(
                    fair_slug=fair_slug,
                    gallery_name_en=gallery_name_en,
                    source_url=source_url,
                    seed_url_type=seed_url_type,
                    target_images=target_images,
                    reason=reason,
                    saved_images=saved_images,
                    new_saved_images=new_saved_images,
                    existing_hit_only=existing_hit_only,
                    detail_year_bucket_counts={
                        "target_year": int(year_bucket_counter.get(0, 0)),
                        "unknown_year": int(year_bucket_counter.get(1, 0)),
                        "non_target_year": int(year_bucket_counter.get(2, 0)),
                    },
                    guard_reject_counts=dict(guard_reject_counter),
                    guard_quarantine_counts=dict(guard_quarantine_counter),
                    guard_no_change_counts=dict(guard_no_change_counter),
                    detail_urls_considered_top10=[str(item.get("url") or "") for item in detail_pages[:10]],
                    notes_top20=case_notes[:20],
                    playwright_runtime_diagnostics=artist_img.get_playwright_runtime_diagnostics(),
                )
            # always attempt candidate loop; skip existing detail during iteration
            def process_sorted_candidates(sorted_candidates: list[dict[str, Any]]) -> bool:
                nonlocal image_index, chosen_detail_url, saved_rows, selected_urls, selected_reasons, selected_years, selected_evidence
                nonlocal metadata_collision_detected
                nonlocal guard_pass_candidate_total, download_surviving_candidate_total
                saved_before = len(saved_rows)
                for candidate in sorted_candidates:
                    if image_index > target_images:
                        break
                    candidate_url = str(candidate.get("url") or "").strip()
                    if not candidate_url:
                        continue
                    dedupe_url = artist_img.normalize_image_url_for_dedupe(candidate_url)
                    if dedupe_url in known_url_hashes or dedupe_url in in_case_url_hashes:
                        if candidate.get("parent_tag") == "metadata":
                            metadata_collision_detected = True
                            case_notes.append("second_pass:metadata_candidate_dedupe_collision")
                        continue
                    attrs = candidate.get("attrs") if isinstance(candidate.get("attrs"), dict) else {}
                    parent_tag = str(candidate.get("parent_tag") or "")
                    candidate_year = artist_img.normalize_candidate_year(candidate.get("year"))
                    evidence_text = str(candidate.get("evidence_text") or "")
                    route_guard = evaluate_route_guard(detail_url=detail_page_url, seed_url=source_url)
                    route_decision = str(route_guard.get("decision") or "allow")
                    if route_decision in {"reject", "quarantine"}:
                        counter = guard_reject_counter if route_decision == "reject" else guard_quarantine_counter
                        for reason in route_guard.get("reasons") or []:
                            counter[str(reason)] += 1
                        case_notes.append(
                            f"guard:{route_decision}:route:{'|'.join(str(x) for x in (route_guard.get('reasons') or []))}"
                        )
                        continue

                    year_guard = evaluate_year_evidence_guard(
                        candidate_year=candidate_year,
                        evidence_text=evidence_text,
                        detail_url=detail_page_url,
                        seed_url=source_url,
                        target_year=int(args.target_year),
                        parent_tag=parent_tag,
                        detail_page_year_bucket=normalize_year_bucket(page.get("year_bucket")),
                        detail_page_year_reason=str(page.get("year_reason") or ""),
                    )
                    year_decision = str(year_guard.get("decision") or "allow")
                    metadata_fallback = bool(year_guard.get("metadata_fallback"))
                    if year_decision in {"reject", "quarantine"}:
                        counter = guard_reject_counter if year_decision == "reject" else guard_quarantine_counter
                        for reason in year_guard.get("reasons") or []:
                            counter[str(reason)] += 1
                        case_notes.append(
                            f"guard:{year_decision}:year:{'|'.join(str(x) for x in (year_guard.get('reasons') or []))}"
                        )
                        continue

                    provenance_guard = evaluate_provenance_guard(
                        detail_url=detail_page_url,
                        seed_url=source_url,
                        seed_url_type=seed_url_type,
                        selected_reason="detail_page_candidate_rank",
                        parent_tag=parent_tag,
                        metadata_fallback=metadata_fallback,
                        detail_page_year_bucket=normalize_year_bucket(page.get("year_bucket")),
                        detail_page_year_reason=str(page.get("year_reason") or ""),
                    )
                    provenance_decision = str(provenance_guard.get("decision") or "allow")
                    if provenance_decision in {"reject", "quarantine"}:
                        counter = (
                            guard_reject_counter if provenance_decision == "reject" else guard_quarantine_counter
                        )
                        for reason in provenance_guard.get("reasons") or []:
                            counter[str(reason)] += 1
                        case_notes.append(
                            "guard:"
                            f"{provenance_decision}:provenance:{'|'.join(str(x) for x in (provenance_guard.get('reasons') or []))}"
                        )
                        continue

                    reject, _ = artist_img.should_reject_image_candidate(
                        candidate_url,
                        attrs,
                        parent_tag,
                        candidate_year=candidate_year,
                        evidence_text=evidence_text,
                    )
                    if reject:
                        continue
                    guard_pass_candidate_total += 1

                    img_ok, payload, content_type, _ = artist_img.fetch_image(session, candidate_url)
                    if not img_ok or not payload:
                        continue
                    payload_ok, normalized_payload, ext = artist_img.normalize_image_payload_for_rag(payload)
                    if not payload_ok:
                        continue
                    ext_token = (ext or "jpg").lstrip(".")
                    payload_digest = artist_img.payload_hash(normalized_payload)
                    if payload_digest in known_payload_hashes or payload_digest in in_case_payload_hashes:
                        continue

                    chosen_detail_url = detail_page_url
                    exhibition_token = exhibition_slug_from_source_url(chosen_detail_url)
                    source_hash8 = artist_img.compute_page_url_hash(chosen_detail_url)[:8]
                    filename = (
                        f"{gallery_token}__{exhibition_token}__{source_hash8}__img_{image_index:02d}.{ext_token}"
                    )
                    local_path = fair_dir / filename
                    if is_windows_path_too_long(local_path):
                        filename = compact_image_filename_for_windows(
                            gallery_token=gallery_token,
                            exhibition_token=exhibition_token,
                            source_hash8=source_hash8,
                            image_index=image_index,
                            ext_token=ext_token,
                        )
                        local_path = fair_dir / filename
                        case_notes.append("path_safe:compact_filename")
                        if is_windows_path_too_long(local_path):
                            gallery_hash8 = hashlib.sha1(gallery_token.encode("utf-8")).hexdigest()[:8]
                            filename = f"g{gallery_hash8}__{source_hash8}__img_{image_index:02d}.{ext_token}"
                            local_path = fair_dir / filename
                            case_notes.append("path_safe:ultra_compact_filename")
                    r2_key = get_image_r2_key(local_path)
                    semantic_key = build_semantic_key(
                        fair_slug=fair_slug,
                        gallery_name_en=gallery_name_en,
                        source_url=chosen_detail_url,
                        seed_source_url=source_url,
                        image_url=candidate_url,
                        payload_hash=payload_digest,
                    )
                    collision_guard = evaluate_duplicate_collision_guard(
                        local_path=str(local_path),
                        r2_key=r2_key,
                        semantic_key=semantic_key,
                        known_local_path_map=known_local_path_map,
                        known_r2_key_map=known_r2_key_map,
                        in_case_local_path_map=in_case_local_path_map,
                        in_case_r2_key_map=in_case_r2_key_map,
                    )
                    collision_decision = str(collision_guard.get("decision") or "allow")
                    if collision_decision == "reject":
                        for reason in collision_guard.get("reasons") or []:
                            guard_reject_counter[str(reason)] += 1
                        case_notes.append(
                            "guard:reject:collision:"
                            f"{'|'.join(str(x) for x in (collision_guard.get('reasons') or []))}"
                        )
                        continue
                    if collision_decision == "no_change_ok":
                        for reason in collision_guard.get("reasons") or []:
                            guard_no_change_counter[str(reason)] += 1
                        case_notes.append(
                            "guard:no_change:collision:"
                            f"{'|'.join(str(x) for x in (collision_guard.get('reasons') or []))}"
                        )
                        continue

                    download_surviving_candidate_total += 1
                    # Ensure trial/worktree runs never fail on missing parent output dir.
                    local_path.parent.mkdir(parents=True, exist_ok=True)
                    local_path.write_bytes(normalized_payload)
                    in_case_url_hashes.add(dedupe_url)
                    in_case_payload_hashes.add(payload_digest)
                    known_url_hashes.add(dedupe_url)
                    known_payload_hashes.add(payload_digest)
                    _add_map_value(in_case_local_path_map, str(local_path), semantic_key)
                    _add_map_value(in_case_r2_key_map, r2_key, semantic_key)
                    _add_map_value(known_local_path_map, str(local_path), semantic_key)
                    _add_map_value(known_r2_key_map, r2_key, semantic_key)

                    selected_urls.append(candidate_url)
                    selected_reasons.append("detail_page_candidate_rank")
                    selected_years.append(candidate_year)
                    selected_evidence.append(
                        artist_img.shorten_text(artist_img.sanitize_evidence_text(evidence_text), 120)
                    )

                    saved_rows.append(
                        {
                            "target_year": int(args.target_year),
                            "fair_slug": fair_slug,
                            "gallery_name_en": gallery_name_en,
                            "source_url": chosen_detail_url,
                            "seed_source_url": source_url,
                            "seed_url_type": seed_url_type,
                            "image_url": candidate_url,
                            "image_url_hash": artist_img.image_url_hash(candidate_url),
                            "payload_hash": payload_digest,
                            "r2_key": r2_key,
                            "selected_reason": "detail_page_candidate_rank",
                            "candidate_year": candidate_year,
                            "evidence_text": artist_img.shorten_text(
                                artist_img.sanitize_evidence_text(evidence_text),
                                120,
                            ),
                            "content_type": content_type,
                            "local_path": str(local_path),
                            "extracted_at": utc_now_iso(),
                        }
                    )
                    detail_pages_with_saved_image.add(artist_img.normalize_url_for_link_compare(detail_page_url))
                    image_index += 1
                    break
                return len(saved_rows) > saved_before

            for page in detail_pages:
                if image_index > target_images:
                    break
                detail_page_url = str(page.get("url") or "")
                detail_url_norm = artist_img.normalize_url_for_link_compare(detail_page_url)
                if detail_url_norm in existing_hit_detail_urls:
                    continue
                detail_html = str(page.get("html") or "")
                detail_html_source = detail_html
                raw_candidates = artist_img.extract_image_candidates(detail_page_url, detail_html)
                raw_candidates_existed = bool(raw_candidates)
                fallback_note = ""
                metadata_fallback_tried = False
                usable_candidate_found = False
                if (
                    not raw_candidates
                    and seed_url_type == "listing"
                    and not listing_detail_reresolved
                ):
                    hydrated_listing_html = fetch_hydrated_detail_html(page_url)
                    listing_detail_reresolved = True
                    if hydrated_listing_html and hydrated_listing_html != html:
                        new_detail_candidates = resolve_exhibition_detail_urls(
                            session=session,
                            page_cache=page_cache,
                            seed_url=page_url,
                            seed_html=hydrated_listing_html,
                            target_year=args.target_year,
                            max_depth=2,
                        )
                        new_detail_pages, _ = collect_detail_pages(
                            detail_candidates=new_detail_candidates,
                            session=session,
                            page_cache=page_cache,
                            target_year=args.target_year,
                        )
                        if new_detail_pages:
                            detail_pages.extend(new_detail_pages)
                            case_notes.append("second_pass:listing_detail_reresolve")
                if not raw_candidates:
                    hydrated_html = fetch_hydrated_detail_html(detail_page_url)
                    if hydrated_html and hydrated_html != detail_html:
                        detail_html_source = hydrated_html
                        raw_candidates = artist_img.extract_image_candidates(detail_page_url, hydrated_html)
                        if raw_candidates:
                            fallback_note = "networkidle_hydration"
                    if not raw_candidates:
                        metadata_candidates = build_metadata_fallback_candidates(
                            detail_page_url, detail_html_source
                        )
                        if metadata_candidates:
                            raw_candidates = metadata_candidates
                            fallback_note = fallback_note or "metadata_fallback"
                            metadata_fallback_tried = True
                raw_candidate_total += len(raw_candidates)
                sorted_candidates = sort_exhibition_candidates(raw_candidates)
                usable_candidate_found |= process_sorted_candidates(sorted_candidates)
                if not usable_candidate_found and raw_candidates_existed and not metadata_fallback_tried:
                    metadata_candidates = build_metadata_fallback_candidates(detail_page_url, detail_html_source)
                    if metadata_candidates:
                        metadata_fallback_tried = True
                        fallback_note = fallback_note or "metadata_fallback_priority"
                        case_notes.append(f"second_pass:{fallback_note}")
                        raw_candidate_total += len(metadata_candidates)
                        sorted_candidates = sort_exhibition_candidates(metadata_candidates)
                        usable_candidate_found |= process_sorted_candidates(sorted_candidates)
                if fallback_note:
                    case_notes.append(f"second_pass:{fallback_note}")

            if saved_rows:
                append_jsonl(meta_path, saved_rows)
                all_saved_rows.extend(saved_rows)

            new_saved_count = len(saved_rows)
            existing_hit_only = False
            existing_saved_count = min(target_images, len(existing_hit_detail_urls))
            saved_count = min(target_images, new_saved_count + existing_saved_count)
            if metadata_collision_detected and not usable_candidate_found and target_images <= DETAIL_PAGE_IMAGE_LIMIT:
                case_notes.append("metadata_collision:known_url_hash")
                existing_hit_only = True
                saved_count = target_images
                metadata_collision_detected = False
            elif saved_count > 0 and new_saved_count == 0 and existing_saved_count >= target_images:
                existing_hit_only = True
            if existing_hit and saved_count > new_saved_count:
                selected_reasons.append("existing_image_kept")
                selected_urls.append(existing_hit_detail_url or chosen_detail_url or source_url)
                selected_years.append(None)
                selected_evidence.append("existing_image_kept")
            target_met = saved_count >= target_images
            target_met_new = new_saved_count >= target_images
            case_status = "ok" if saved_count > 0 else ("existing_hit_only" if existing_hit_only else "failed")
            if saved_count == 0:
                has_target_or_unknown = any(
                    normalize_year_bucket(item.get("year_bucket")) in (0, 1) for item in detail_pages
                )
                reason = (
                    "insufficient_image_candidates_after_download"
                    if has_target_or_unknown
                    else "target_year_signal_missing"
                )
                failed_cases.append(
                    build_failed_case_record(
                        reason,
                        saved_images=saved_count,
                        new_saved_images=new_saved_count,
                        existing_hit_only=existing_hit_only,
                    )
                )
                reason_counter[reason] += 1
            elif not target_met:
                reason = "insufficient_image_candidates_after_download"
                failed_cases.append(
                    build_failed_case_record(
                        reason,
                        saved_images=saved_count,
                        new_saved_images=new_saved_count,
                        existing_hit_only=existing_hit_only,
                    )
                )
                reason_counter[reason] += 1

            cases.append(
                {
                    **target,
                    "seed_url_type": seed_url_type,
                    "source_url_effective": chosen_detail_url or existing_hit_detail_url,
                    "listing_resolved_to_detail_count": listing_resolved_to_detail_count,
                    "detail_urls_considered_top10": [str(item.get("url") or "") for item in detail_pages[:10]],
                    "detail_year_bucket_counts": {
                        "target_year": int(year_bucket_counter.get(0, 0)),
                        "unknown_year": int(year_bucket_counter.get(1, 0)),
                        "non_target_year": int(year_bucket_counter.get(2, 0)),
                    },
                    "guard_reject_counts": dict(guard_reject_counter),
                    "guard_quarantine_counts": dict(guard_quarantine_counter),
                    "guard_no_change_counts": dict(guard_no_change_counter),
                    "saved_images": saved_count,
                    "new_saved_images": new_saved_count,
                    "existing_hit_only": existing_hit_only,
                    "existing_hit": existing_hit,
                    "existing_detail_hit_count": len(existing_hit_detail_urls),
                    "quota_eligible_detail_page_count": quota_eligible_detail_page_count,
                    "raw_candidate_total": raw_candidate_total,
                    "guard_pass_candidate_total": guard_pass_candidate_total,
                    "download_surviving_candidate_total": download_surviving_candidate_total,
                    "saved_detail_page_count": len(detail_pages_with_saved_image),
                    "target_images": target_images,
                    "target_met": target_met,
                    "target_met_new": target_met_new,
                    "status": case_status,
                    "selected_image_urls_top5": selected_urls[:5],
                    "selected_image_years_top5": selected_years[:5],
                    "selected_image_evidence_top5": selected_evidence[:5],
                    "selected_reasons_top5": selected_reasons[:5],
                    "notes": case_notes,
                }
            )
            if debug_active:
                detail_url_set = {
                    artist_img.normalize_url_for_link_compare(str(item.get("url") or ""))
                    for item in detail_pages
                }
                link_entries: list[dict[str, Any]] = []
                for href_raw, anchor_text in debug_links_raw:
                    href_raw = href_raw.strip()
                    if not href_raw:
                        continue
                    href_joined = urljoin(page_url, href_raw)
                    canonical = artist_img.normalize_url_for_link_compare(href_joined)
                    seed_type = classify_seed_url_type(href_joined)
                    keyword_matches = [
                        kw
                        for kw in LINK_KEYWORDS
                        if kw in f"{href_joined.lower()} {anchor_text.lower()}"
                    ]
                    link_entries.append(
                        {
                            "href_raw": href_raw,
                            "href_joined": href_joined,
                            "anchor_text": anchor_text,
                            "same_domain": artist_img.normalize_domain(href_joined)
                            == artist_img.normalize_domain(source_url),
                            "keyword_hit": bool(keyword_matches),
                            "keyword_matches": keyword_matches,
                            "listing_or_detail": seed_type,
                            "accepted": canonical in detail_url_set,
                            "reject_reason": "" if canonical in detail_url_set else "not_detail_candidate",
                        }
                    )
                if not html_dump_path:
                    html_dump_path = debug_html_dir / f"{fair_slug}_{gallery_token}_listing.html"
                    html_dump_path.write_text(html or "", encoding="utf-8")
                link_debug_path = debug_links_dir / f"{fair_slug}_{gallery_token}_links.json"
                write_json(
                    link_debug_path,
                    {
                        "fair_slug": fair_slug,
                        "gallery_name_en": gallery_name_en,
                        "source_url": source_url,
                        "link_count_total": len(link_entries),
                        "links": link_entries,
                    },
                )
                accepted_detail_urls_top20 = [item.get("url") or "" for item in detail_pages[:20]]
                year_counts = {
                    "target_year": int(year_bucket_counter.get(0, 0)),
                    "unknown_year": int(year_bucket_counter.get(1, 0)),
                    "non_target_year": int(year_bucket_counter.get(2, 0)),
                }
                if not detail_pages:
                    provisional_root_cause = "detail候補が見つかりません"
                elif year_counts["target_year"] == 0:
                    provisional_root_cause = "2025年のdetail候補がありません"
                else:
                    provisional_root_cause = "detail候補はあるが1画像に至りません"
                debug_triage_entries.append(
                    {
                        "fair_slug": fair_slug,
                        "gallery_name_en": gallery_name_en,
                        "html_dump_path": str(html_dump_path.relative_to(PROJECT_ROOT)) if html_dump_path else "",
                        "link_debug_path": str(link_debug_path.relative_to(PROJECT_ROOT)),
                        "total_links": len(link_entries),
                        "accepted_candidate_count": len(detail_pages),
                        "accepted_detail_urls_top20": accepted_detail_urls_top20,
                        "provisional_root_cause": provisional_root_cause,
                        "evidence_summary_ja": (
                            f"{len(detail_pages)}件のdetail候補 "
                            f"(2025:{year_counts['target_year']} / unknown:{year_counts['unknown_year']} / "
                            f"non-target:{year_counts['non_target_year']})"
                        ),
                    }
                )

    success_cases = [c for c in cases if int(c.get("saved_images") or 0) > 0]
    target_met_cases = [c for c in cases if bool(c.get("target_met"))]
    success_cases_new = [c for c in cases if int(c.get("new_saved_images") or 0) > 0]
    target_met_cases_new = [c for c in cases if bool(c.get("target_met_new"))]
    summary = {
        "artifact": "phase1_seed10_exhibition_image_collect_summary",
        "execution_mode": policy_mode,
        "allow_rebuild": bool(args.allow_rebuild),
        "run_id_external": str(args.run_id or ""),
        "io_root": str(io_root),
        "target_year": int(args.target_year),
        "target_images_per_exhibition": int(args.target_images_per_exhibition),
        "detail_page_image_limit": DETAIL_PAGE_IMAGE_LIMIT,
        "listing_dynamic_target_cap": LISTING_DYNAMIC_TARGET_CAP,
        "listing_dynamic_target_policy": "ceil(strong_target_year_detail_pages/2), capped",
        "seed_exhibition_count": len(targets),
        "seed_url_type_breakdown": dict(seed_url_type_counter),
        "listing_resolved_to_detail_count": int(listing_resolved_seed_count),
        "listing_resolved_detail_urls_total": int(listing_resolved_detail_urls_total),
        "exhibitions_with_ge_1_image": len(success_cases),
        "success_rate_ge_1_image": round((len(success_cases) / len(targets)) if targets else 0.0, 6),
        "exhibitions_with_ge_target_images": len(target_met_cases),
        "success_rate_ge_target_images": round((len(target_met_cases) / len(targets)) if targets else 0.0, 6),
        "exhibitions_with_ge_1_new_image": len(success_cases_new),
        "success_rate_ge_1_new_image": round((len(success_cases_new) / len(targets)) if targets else 0.0, 6),
        "exhibitions_with_ge_target_new_images": len(target_met_cases_new),
        "success_rate_ge_target_new_images": round((len(target_met_cases_new) / len(targets)) if targets else 0.0, 6),
        "saved_images_total": sum(int(c.get("saved_images") or 0) for c in cases),
        "new_saved_images_total": sum(int(c.get("new_saved_images") or 0) for c in cases),
        "existing_hit_only_case_count": sum(1 for c in cases if bool(c.get("existing_hit_only"))),
        "failed_case_count": len(failed_cases),
        "failed_reason_counts": dict(reason_counter),
        "seed_transition_breakdown": build_seed_transition_breakdown(cases),
        "guard_counter_totals": build_guard_counter_totals(cases),
        "playwright_runtime_diagnostics": artist_img.get_playwright_runtime_diagnostics(),
        "gallery_breakdown": build_breakdowns(success_cases),
        "cases": cases,
        "failed_cases": failed_cases,
        "saved_rows_sample_top10": all_saved_rows[:10],
        "generated_at": utc_now_iso(),
        "run_id": utc_timestamp_compact(),
    }
    auto_skip_cleanup_report = execute_auto_skip_registry_cleanup_after_image_collect(
        targets=targets,
        target_year=int(args.target_year),
        run_id=str(args.run_id or summary["run_id"]),
        source_scope_file=str(args.targets_csv or ""),
    )
    summary["auto_skip_cleanup"] = auto_skip_cleanup_report
    if debug_triage_entries and debug_run_id and debug_output_base:
        triage_path = debug_output_base / DEBUG_TRIAGE_FILENAME_TEMPLATE.format(run_id=debug_run_id)
        write_json(triage_path, debug_triage_entries)
    default_output_path = logs_dir / f"phase1_seed10_exhibition_image_collect_summary_{summary['run_id']}.json"
    output_json_path = Path(args.output_json) if str(args.output_json or "").strip() else default_output_path
    if not output_json_path.is_absolute():
        output_json_path = (PROJECT_ROOT / output_json_path).resolve()
    write_json(output_json_path, summary)
    latest_output_path: Path | None = None
    if not str(args.output_json or "").strip() and is_optional_output_enabled("latest"):
        latest_output_path = logs_dir / "phase1_seed10_exhibition_image_collect_summary_latest.json"
        if not latest_output_path.is_absolute():
            latest_output_path = (PROJECT_ROOT / latest_output_path).resolve()
        write_json(latest_output_path, summary)
    print(f"[exhibitions-image-collect] output={output_json_path}")
    if latest_output_path is not None:
        print(f"[exhibitions-image-collect] latest={latest_output_path}")
    print(
        "[exhibitions-image-collect] "
        f"seed={summary['seed_exhibition_count']} "
        f"ge1={summary['exhibitions_with_ge_1_image']} "
        f"ge_target={summary['exhibitions_with_ge_target_images']} "
        f"saved_images_total={summary['saved_images_total']} "
        f"auto_skip_status={auto_skip_cleanup_report.get('status', '')} "
        f"auto_skip_detected={int(auto_skip_cleanup_report.get('all_rag_zero_detected_count', 0)) + int(auto_skip_cleanup_report.get('exhibition_text_only_detected_count', 0))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

