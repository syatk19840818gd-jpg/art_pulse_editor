from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

from phase2_art_pulse_config import normalize_image_local_path_text
from phase2_common_readonly import (
    FAIR_LABEL_TO_SLUG,
    FAIR_SLUG_TO_LABEL,
    derive_artist_name,
    normalize_url,
    resolve_current_artist_text_artifact_paths,
    resolve_current_artist_text_paths_by_year,
    resolve_current_artist_works_image_meta_paths,
    resolve_current_first_enrichment_output_path,
    safe_load_jsonl,
)

ARTIST_SEARCH_RESULT_COUNT = 3
ARTIST_SEARCH_SUMMARY_MAX_CHARS = 500
ARTIST_SEARCH_THUMB_FROM_ARTIST = 3


def build_artist_summary_ja(row: dict, max_chars: int = ARTIST_SEARCH_SUMMARY_MAX_CHARS) -> str:
    summary_ja = str(row.get("summary_ja") or "").strip()
    if not summary_ja:
        return "未付与"
    if len(summary_ja) <= max_chars:
        return summary_ja
    return summary_ja[:max_chars].rstrip() + "…"


def _load_latest_artist_enrichment_map() -> Tuple[Dict[Tuple[str, str], Dict[str, str]], List[str]]:
    rows, warnings = _load_latest_artist_enrichment_rows()
    enrichment_by_key: Dict[Tuple[str, str], Dict[str, str]] = {}
    for row in rows:
        if str(row.get("status") or "").strip() != "APPLIED":
            continue
        source_url = normalize_url(str(row.get("source_url") or ""))
        text_hash = str(row.get("text_hash") or "").strip()
        if not source_url and not text_hash:
            continue
        headline_ja = str(row.get("headline_ja") or "").strip()
        summary_ja = str(row.get("summary_ja") or "").strip()
        artist_name_kana = str(row.get("artist_name_kana") or "").strip()
        if not headline_ja and not summary_ja and not artist_name_kana:
            continue
        enrichment_by_key[(source_url, text_hash)] = {
            "headline_ja": headline_ja,
            "summary_ja": summary_ja,
            "artist_name_kana": artist_name_kana,
        }
    return enrichment_by_key, warnings


def _load_latest_artist_enrichment_rows() -> Tuple[List[dict], List[str]]:
    source_path, _source_kind = resolve_current_first_enrichment_output_path("artists")
    if source_path is None:
        return [], []

    rows, warnings = safe_load_jsonl(source_path)
    return rows, warnings


@dataclass
class ArtistSearchData:
    records: List[dict]
    warnings: List[str]
    total_rows: int
    fair_rows: Dict[str, int]
    count_note: str


def _artist_record_rank(row: dict) -> tuple[int, int, int, int, int, int]:
    summary_ja = str(row.get("summary_ja") or "").strip()
    headline_ja = str(row.get("headline_ja") or "").strip()
    artist_name_kana = str(row.get("artist_name_kana") or "").strip()
    text = str(row.get("text") or "").strip()
    return (
        1 if summary_ja else 0,
        1 if headline_ja else 0,
        1 if artist_name_kana else 0,
        int(row.get("works_image_count_hint") or 0),
        len(text),
        len(summary_ja),
    )


def _dedup_artist_records(records: List[dict]) -> List[dict]:
    best_by_key: Dict[tuple[str, str, str], dict] = {}
    for row in records:
        fair_slug = str(row.get("fair_slug") or "").strip()
        source_url = normalize_url(str(row.get("source_url") or ""))
        text_hash = str(row.get("text_hash") or "").strip()
        fallback_key = str(row.get("id") or "")
        dedup_key = (
            fair_slug,
            source_url or fallback_key,
            text_hash or fallback_key,
        )
        existing = best_by_key.get(dedup_key)
        if existing is None or _artist_record_rank(row) > _artist_record_rank(existing):
            best_by_key[dedup_key] = row
    return list(best_by_key.values())


def _artist_raw_row_rank(row: dict) -> tuple[int, int, int, int, int]:
    text = str(row.get("text") or "").strip()
    year = row.get("target_year")
    year_value = year if isinstance(year, int) else 0
    return (
        1 if text else 0,
        year_value,
        len(text),
        1 if str(row.get("artist_identity_key") or "").strip() else 0,
        1 if str(row.get("artist_name_key") or "").strip() else 0,
    )


def _load_artist_raw_supplement_by_key() -> tuple[Dict[tuple[str, str, str], dict], List[str]]:
    raw_by_key: Dict[tuple[str, str, str], dict] = {}
    warnings: List[str] = []
    for fair_slug, paths_by_year in resolve_current_artist_text_paths_by_year().items():
        for discovered_year, path in sorted(paths_by_year.items()):
            text_rows, text_warnings = safe_load_jsonl(path)
            warnings.extend(text_warnings)
            for row in text_rows:
                source_url = normalize_url(str(row.get("source_url") or ""))
                text_hash = str(row.get("text_hash") or "").strip()
                if not source_url or not text_hash:
                    continue
                candidate = dict(row)
                if not isinstance(candidate.get("target_year"), int):
                    candidate["target_year"] = discovered_year
                key = (fair_slug, source_url, text_hash)
                existing = raw_by_key.get(key)
                if existing is None or _artist_raw_row_rank(candidate) > _artist_raw_row_rank(existing):
                    raw_by_key[key] = candidate
    return raw_by_key, warnings


def load_artist_records_readonly() -> ArtistSearchData:
    warnings: List[str] = []
    records: List[dict] = []
    fair_rows: Dict[str, int] = {"frieze_london": 0, "liste": 0}
    enrichment_by_key, enrichment_warnings = _load_latest_artist_enrichment_map()
    warnings.extend(enrichment_warnings)
    raw_by_key, raw_warnings = _load_artist_raw_supplement_by_key()
    warnings.extend(raw_warnings)
    artist_vector_paths = resolve_current_artist_text_artifact_paths()
    artist_meta_rows, artist_meta_warnings = safe_load_jsonl(artist_vector_paths["meta"])
    warnings.extend(artist_meta_warnings)
    artist_image_meta_paths = resolve_current_artist_works_image_meta_paths()

    image_hint_by_source: Dict[str, dict] = {}
    for fair_slug, path in artist_image_meta_paths.items():
        image_rows, image_warnings = safe_load_jsonl(path)
        warnings.extend(image_warnings)
        for row in image_rows:
            source_url = normalize_url(str(row.get("source_url", "")))
            if not source_url:
                continue
            works_local_paths = row.get("works_image_local_paths")
            count_hint = len(works_local_paths) if isinstance(works_local_paths, list) else 0
            artist_name_en = str(row.get("artist_name_en") or "")
            works_r2_keys = row.get("works_image_r2_keys")
            works_image_urls = row.get("works_image_urls")
            preview_candidates: List[dict] = []
            if isinstance(works_local_paths, list) or isinstance(works_r2_keys, list) or isinstance(works_image_urls, list):
                max_len = max(
                    len(works_local_paths) if isinstance(works_local_paths, list) else 0,
                    len(works_r2_keys) if isinstance(works_r2_keys, list) else 0,
                    len(works_image_urls) if isinstance(works_image_urls, list) else 0,
                )
                for i in range(max_len):
                    local_path = (
                        normalize_image_local_path_text(works_local_paths[i] or "")
                        if isinstance(works_local_paths, list) and i < len(works_local_paths)
                        else ""
                    )
                    r2_key = str(works_r2_keys[i] or "").strip() if isinstance(works_r2_keys, list) and i < len(works_r2_keys) else ""
                    image_url = str(works_image_urls[i] or "").strip() if isinstance(works_image_urls, list) and i < len(works_image_urls) else ""
                    if not local_path and not r2_key and not image_url:
                        continue
                    preview_candidates.append({"local_path": local_path, "r2_key": r2_key, "image_url": image_url})
            prev = image_hint_by_source.get(source_url)
            if prev is None or int(prev.get("count", 0)) < count_hint:
                image_hint_by_source[source_url] = {
                    "count": count_hint,
                    "artist_name_en": artist_name_en,
                    "artist_name_key": str(row.get("artist_name_key") or "").strip(),
                    "artist_identity_key": str(row.get("artist_identity_key") or "").strip(),
                    "gallery_name_en": str(row.get("gallery_name_en") or "").strip(),
                    "preview_candidates": preview_candidates,
                }

    for idx, row in enumerate(artist_meta_rows, start=1):
        fair_slug = str(row.get("fair_slug") or "").strip()
        if fair_slug not in {"frieze_london", "liste"}:
            continue
        source_url = str(row.get("source_url") or "").strip()
        if not source_url:
            continue
        fair_rows[fair_slug] = fair_rows.get(fair_slug, 0) + 1
        norm_source = normalize_url(source_url)
        hint = image_hint_by_source.get(norm_source, {})
        text_hash = str(row.get("text_hash") or "").strip()
        raw_row = raw_by_key.get((fair_slug, norm_source, text_hash), {})
        enrichment = enrichment_by_key.get((norm_source, text_hash), {})
        if not enrichment and norm_source:
            enrichment = enrichment_by_key.get((norm_source, ""), {})
        if not enrichment and text_hash:
            enrichment = enrichment_by_key.get(("", text_hash), {})

        year = row.get("target_year")
        if not isinstance(year, int):
            raw_year = raw_row.get("target_year")
            year = raw_year if isinstance(raw_year, int) else None
        artist_name = derive_artist_name(
            source_url,
            str(raw_row.get("artist_name_en") or "") or str(hint.get("artist_name_en") or ""),
        )
        artist_name_kana = (
            str(raw_row.get("artist_name_kana") or "").strip()
            or str(enrichment.get("artist_name_kana") or "").strip()
        )
        headline_ja = (
            str(raw_row.get("headline_ja") or "").strip()
            or str(row.get("headline_ja") or "").strip()
            or str(enrichment.get("headline_ja") or "").strip()
        )
        summary_ja = (
            str(raw_row.get("summary_ja") or "").strip()
            or str(enrichment.get("summary_ja") or "").strip()
        )
        records.append(
            {
                "id": f"{fair_slug}:{idx}",
                "fair_slug": fair_slug,
                "fair_label": FAIR_SLUG_TO_LABEL.get(fair_slug, fair_slug),
                "gallery_name": str(row.get("gallery_name_en") or raw_row.get("gallery_name_en") or hint.get("gallery_name_en") or ""),
                "artist_name": artist_name,
                "artist_identity_key": str(raw_row.get("artist_identity_key") or hint.get("artist_identity_key") or "").strip(),
                "artist_name_key": str(raw_row.get("artist_name_key") or hint.get("artist_name_key") or "").strip(),
                "year": year if isinstance(year, int) else None,
                "source_url": source_url,
                "text_hash": text_hash,
                "text": str(raw_row.get("text") or ""),
                "artist_name_kana": artist_name_kana,
                "headline_ja": headline_ja,
                "summary_ja": summary_ja,
                "summary_display_ja": build_artist_summary_ja({"summary_ja": summary_ja}),
                "works_image_count_hint": int(hint.get("count", 0) or 0),
                "artist_image_preview_candidates": list(hint.get("preview_candidates") or [])[:ARTIST_SEARCH_THUMB_FROM_ARTIST],
            }
        )

    if not records and raw_by_key:
        fallback_count_by_fair: Dict[str, int] = {"frieze_london": 0, "liste": 0}
        for idx, ((fair_slug, norm_source, text_hash), row) in enumerate(raw_by_key.items(), start=1):
            source_url = str(row.get("source_url") or "").strip()
            hint = image_hint_by_source.get(norm_source, {})
            enrichment = enrichment_by_key.get((norm_source, text_hash), {})
            if not enrichment and norm_source:
                enrichment = enrichment_by_key.get((norm_source, ""), {})
            if not enrichment and text_hash:
                enrichment = enrichment_by_key.get(("", text_hash), {})
            artist_name = derive_artist_name(
                source_url,
                str(row.get("artist_name_en") or "") or str(hint.get("artist_name_en") or ""),
            )
            artist_name_kana = str(row.get("artist_name_kana") or "").strip() or str(enrichment.get("artist_name_kana") or "").strip()
            headline_ja = str(row.get("headline_ja") or "").strip() or str(enrichment.get("headline_ja") or "").strip()
            summary_ja = str(row.get("summary_ja") or "").strip() or str(enrichment.get("summary_ja") or "").strip()
            records.append(
                {
                    "id": f"{fair_slug}:raw-fallback:{idx}",
                    "fair_slug": fair_slug,
                    "fair_label": FAIR_SLUG_TO_LABEL.get(fair_slug, fair_slug),
                    "gallery_name": str(row.get("gallery_name_en") or hint.get("gallery_name_en") or ""),
                    "artist_name": artist_name,
                    "artist_identity_key": str(row.get("artist_identity_key") or hint.get("artist_identity_key") or "").strip(),
                    "artist_name_key": str(row.get("artist_name_key") or hint.get("artist_name_key") or "").strip(),
                    "year": row.get("target_year") if isinstance(row.get("target_year"), int) else None,
                    "source_url": source_url,
                    "text_hash": text_hash,
                    "text": str(row.get("text") or ""),
                    "artist_name_kana": artist_name_kana,
                    "headline_ja": headline_ja,
                    "summary_ja": summary_ja,
                    "summary_display_ja": build_artist_summary_ja({"summary_ja": summary_ja}),
                    "works_image_count_hint": int(hint.get("count", 0) or 0),
                    "artist_image_preview_candidates": list(hint.get("preview_candidates") or [])[:ARTIST_SEARCH_THUMB_FROM_ARTIST],
                }
            )
            fallback_count_by_fair[fair_slug] = fallback_count_by_fair.get(fair_slug, 0) + 1
        fair_rows = fallback_count_by_fair
        warnings.append(
            "artists_text_vector_meta_missing_or_empty: fallback to all-years raw current family for artist search listing"
        )

    if not records:
        fallback_rows, fallback_warnings = _load_latest_artist_enrichment_rows()
        warnings.extend(fallback_warnings)
        fallback_count_by_fair: Dict[str, int] = {"frieze_london": 0, "liste": 0}
        for idx, row in enumerate(fallback_rows, start=1):
            if str(row.get("status") or "").strip() != "APPLIED":
                continue
            source_url = str(row.get("source_url") or "").strip()
            if not source_url:
                continue
            fair_slug = str(row.get("fair_slug") or "").strip()
            if fair_slug not in {"frieze_london", "liste"}:
                fair_slug = "frieze_london" if "/frieze" in source_url.lower() else "liste"
            norm_source = normalize_url(source_url)
            hint = image_hint_by_source.get(norm_source, {})
            artist_name = derive_artist_name(
                source_url,
                str(row.get("artist_name_en") or "") or str(hint.get("artist_name_en") or ""),
            )
            artist_name_kana = str(row.get("artist_name_kana") or "").strip()
            headline_ja = str(row.get("headline_ja") or "").strip()
            summary_ja = str(row.get("summary_ja") or "").strip()
            records.append(
                {
                    "id": f"{fair_slug}:fallback:{idx}",
                    "fair_slug": fair_slug,
                    "fair_label": FAIR_SLUG_TO_LABEL.get(fair_slug, fair_slug),
                    "gallery_name": "",
                    "artist_name": artist_name,
                    "artist_identity_key": str(row.get("artist_identity_key") or "").strip(),
                    "artist_name_key": str(row.get("artist_name_key") or "").strip(),
                    "year": None,
                    "source_url": source_url,
                    "text_hash": str(row.get("text_hash") or "").strip(),
                    "text": "",
                    "artist_name_kana": artist_name_kana,
                    "headline_ja": headline_ja,
                    "summary_ja": summary_ja,
                    "summary_display_ja": build_artist_summary_ja({"summary_ja": summary_ja}),
                    "works_image_count_hint": int(hint.get("count", 0) or 0),
                    "artist_image_preview_candidates": list(hint.get("preview_candidates") or [])[:ARTIST_SEARCH_THUMB_FROM_ARTIST],
                }
            )
            fallback_count_by_fair[fair_slug] = fallback_count_by_fair.get(fair_slug, 0) + 1

        if records:
            fair_rows = fallback_count_by_fair
            warnings.append(
                "artists_text_raw_missing_or_empty: fallback to current enrichment output for artist search listing"
            )

    records = _dedup_artist_records(records)
    fair_rows = {
        "frieze_london": sum(1 for row in records if str(row.get("fair_slug") or "") == "frieze_london"),
        "liste": sum(1 for row in records if str(row.get("fair_slug") or "") == "liste"),
    }

    return ArtistSearchData(
        records=records,
        warnings=sorted(set(warnings)),
        total_rows=len(records),
        fair_rows=fair_rows,
        count_note=(
            "Artist rows use the yearless app-facing current artist text meta "
            "(data/current/vector/artists/artists_text_meta.jsonl) as the primary listing input. "
            "headline_ja/summary_ja/artist_name_kana uses current-first enrichment output "
            "(data/current/enrichment/artists_enrichment_apply_output.jsonl), "
            "with strict current-only resolution. "
            "Listing identity is fixed to fair_slug + normalized source_url + text_hash, "
            "so multiple text variants on the same artist URL are preserved while exact duplicates are collapsed. "
            "When available, all-years raw current files supplement text/year/identity metadata without pinning runtime to a fixed year. "
            "history is not used as a default query path. "
            "works_image_count_hint is matched by source_url against formal artist works-image metadata. "
            "If artist text meta is unavailable, listing falls back to all-years raw current rows, then to enrichment rows."
        ),
    )


def apply_artist_filters(records: List[dict], fair_label: str, keyword: str) -> List[dict]:
    if fair_label == "Frieze London + Liste Art Fair Basel":
        fair_slugs = {"frieze_london", "liste"}
    elif fair_label in FAIR_LABEL_TO_SLUG:
        fair_slugs = {FAIR_LABEL_TO_SLUG[fair_label]}
    else:
        fair_slugs = {"frieze_london", "liste"}

    key = (keyword or "").strip().lower()
    filtered: List[dict] = []
    for row in records:
        if row.get("fair_slug") not in fair_slugs:
            continue
        if key:
            hay = " ".join(
                [
                    str(row.get("artist_name") or ""),
                    str(row.get("gallery_name") or ""),
                    str(row.get("source_url") or ""),
                    str(row.get("text") or "")[:500],
                    str(row.get("artist_name_kana") or ""),
                    str(row.get("headline_ja") or ""),
                    str(row.get("summary_ja") or ""),
                ]
            ).lower()
            if key not in hay:
                continue
        filtered.append(row)

    filtered.sort(
        key=lambda r: (
            -(r.get("year") or 0),
            str(r.get("fair_label") or ""),
            str(r.get("gallery_name") or ""),
            str(r.get("artist_name") or ""),
        )
    )
    return filtered


def search_artists(
    records: List[dict],
    fair_label: str,
    query_text: str,
    limit: int = ARTIST_SEARCH_RESULT_COUNT,
) -> List[dict]:
    safe_limit = max(1, int(limit))
    fair_filtered = apply_artist_filters(records, fair_label, "")
    keyword_query = str(query_text or "").strip().lower()
    if not keyword_query:
        return fair_filtered[:safe_limit]

    tokens = [t for t in re.findall("[a-z0-9]{2,}|[\u3040-\u30ff\u4e00-\u9fff]{1,}", keyword_query) if t]
    if not tokens:
        return apply_artist_filters(records, fair_label, keyword_query)[:safe_limit]

    scored: List[Tuple[int, dict]] = []
    for row in fair_filtered:
        hay = " ".join(
            [
                str(row.get("artist_name") or ""),
                str(row.get("gallery_name") or ""),
                str(row.get("source_url") or ""),
                str(row.get("text") or "")[:1200],
                str(row.get("artist_name_kana") or ""),
                str(row.get("headline_ja") or ""),
                str(row.get("summary_ja") or ""),
            ]
        ).lower()
        score = sum(1 for token in tokens if token in hay)
        if score > 0:
            scored.append((score, row))

    scored.sort(
        key=lambda x: (
            -x[0],
            -(x[1].get("year") or 0),
            str(x[1].get("fair_label") or ""),
            str(x[1].get("gallery_name") or ""),
            str(x[1].get("artist_name") or ""),
        )
    )
    if scored:
        return [row for _, row in scored[:safe_limit]]
    if keyword_query:
        return apply_artist_filters(records, fair_label, keyword_query)[:safe_limit]
    return fair_filtered[:safe_limit]
