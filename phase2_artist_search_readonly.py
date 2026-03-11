from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from phase2_common_readonly import (
    ARTISTS_TEXT_PATHS,
    ARTIST_WORKS_IMAGE_PATHS,
    FAIR_LABEL_TO_SLUG,
    FAIR_SLUG_TO_LABEL,
    derive_artist_name,
    normalize_url,
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
    derived_dir = Path(__file__).resolve().parent / "data/phase1_seed10/derived"
    candidates = sorted(
        derived_dir.glob("artists_enrichment_apply_output_2025_*.jsonl"),
        key=lambda p: p.name,
        reverse=True,
    )
    if not candidates:
        return {}, []

    warnings: List[str] = []
    best_map: Dict[Tuple[str, str], Dict[str, str]] = {}
    for candidate in candidates:
        rows, row_warnings = safe_load_jsonl(candidate)
        warnings.extend(row_warnings)
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
        if len(enrichment_by_key) > len(best_map):
            best_map = enrichment_by_key
    return best_map, warnings


@dataclass
class ArtistSearchData:
    records: List[dict]
    warnings: List[str]
    total_rows: int
    fair_rows: Dict[str, int]
    count_note: str


def load_artist_records_readonly() -> ArtistSearchData:
    warnings: List[str] = []
    records: List[dict] = []
    fair_rows: Dict[str, int] = {"frieze_london": 0, "liste": 0}
    enrichment_by_key, enrichment_warnings = _load_latest_artist_enrichment_map()
    warnings.extend(enrichment_warnings)

    image_hint_by_source: Dict[str, dict] = {}
    for fair_slug, path in ARTIST_WORKS_IMAGE_PATHS.items():
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
                    local_path = str(works_local_paths[i] or "").strip() if isinstance(works_local_paths, list) and i < len(works_local_paths) else ""
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
                    "preview_candidates": preview_candidates,
                }

    for fair_slug, path in ARTISTS_TEXT_PATHS.items():
        text_rows, text_warnings = safe_load_jsonl(path)
        warnings.extend(text_warnings)
        fair_rows[fair_slug] = len(text_rows)

        for idx, row in enumerate(text_rows, start=1):
            source_url = str(row.get("source_url") or "").strip()
            norm_source = normalize_url(source_url)
            hint = image_hint_by_source.get(norm_source, {})
            text_hash = str(row.get("text_hash") or "").strip()
            enrichment = enrichment_by_key.get((norm_source, text_hash), {})
            if not enrichment and norm_source:
                enrichment = enrichment_by_key.get((norm_source, ""), {})
            if not enrichment and text_hash:
                enrichment = enrichment_by_key.get(("", text_hash), {})

            year = row.get("target_year")
            year_value = year if isinstance(year, int) else None
            artist_name = derive_artist_name(source_url, str(hint.get("artist_name_en") or ""))
            artist_name_kana = str(row.get("artist_name_kana") or "").strip() or str(enrichment.get("artist_name_kana") or "").strip()
            headline_ja = str(row.get("headline_ja") or "").strip() or str(enrichment.get("headline_ja") or "").strip()
            summary_ja = str(row.get("summary_ja") or "").strip() or str(enrichment.get("summary_ja") or "").strip()

            records.append(
                {
                    "id": f"{fair_slug}:{idx}",
                    "fair_slug": fair_slug,
                    "fair_label": FAIR_SLUG_TO_LABEL.get(fair_slug, fair_slug),
                    "gallery_name": str(row.get("gallery_name_en") or ""),
                    "artist_name": artist_name,
                    "year": year_value,
                    "source_url": source_url,
                    "text": str(row.get("text") or ""),
                    "artist_name_kana": artist_name_kana,
                    "headline_ja": headline_ja,
                    "summary_ja": summary_ja,
                    "summary_display_ja": build_artist_summary_ja({"summary_ja": summary_ja}),
                    "works_image_count_hint": int(hint.get("count", 0) or 0),
                    "artist_image_preview_candidates": list(hint.get("preview_candidates") or [])[:ARTIST_SEARCH_THUMB_FROM_ARTIST],
                }
            )

    return ArtistSearchData(
        records=records,
        warnings=sorted(set(warnings)),
        total_rows=len(records),
        fair_rows=fair_rows,
        count_note=(
            "Artist行は formal raw（artists_*_2025.jsonl）由来。"
            " headline_ja/summary_ja/artist_name_kana は raw空時に latest artists_enrichment_apply_output をfallback参照。"
            " works_image_count_hint は formal artist works-imageメタとの source_url 厳密一致。"
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
            str(r.get("fair_label") or ""),
            str(r.get("gallery_name") or ""),
            str(r.get("artist_name") or ""),
            -(r.get("year") or 0),
        )
    )
    return filtered

