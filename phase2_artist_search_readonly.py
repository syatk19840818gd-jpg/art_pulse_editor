from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

from phase2_art_pulse_config import normalize_image_local_path_text
from phase2_common_readonly import (
    ARTISTS_TEXT_PATHS,
    ARTIST_WORKS_IMAGE_PATHS,
    FAIR_LABEL_TO_SLUG,
    FAIR_SLUG_TO_LABEL,
    derive_artist_name,
    normalize_url,
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
    best_by_key: Dict[tuple[str, str], dict] = {}
    for row in records:
        fair_slug = str(row.get("fair_slug") or "").strip()
        source_url = normalize_url(str(row.get("source_url") or ""))
        dedup_key = (fair_slug, source_url or str(row.get("id") or ""))
        existing = best_by_key.get(dedup_key)
        if existing is None or _artist_record_rank(row) > _artist_record_rank(existing):
            best_by_key[dedup_key] = row
    return list(best_by_key.values())


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
            artist_name = derive_artist_name(
                source_url,
                str(row.get("artist_name_en") or "") or str(hint.get("artist_name_en") or ""),
            )
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
                    "artist_identity_key": str(row.get("artist_identity_key") or "").strip(),
                    "artist_name_key": str(row.get("artist_name_key") or "").strip(),
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
            "Artist rows use formal raw (artists_*_2025.jsonl). "
            "headline_ja/summary_ja/artist_name_kana uses current-first enrichment output "
            "(data/current/enrichment/artists_enrichment_apply_output_2025.jsonl), "
            "with strict current-only resolution. "
            "history is not used as a default query path. "
            "works_image_count_hint is matched by source_url against formal artist works-image metadata. "
            "If raw rows are unavailable, listing falls back to enrichment rows."
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


def answer_artist_followup(question_text: str, result_row: dict) -> str:
    question = str(question_text or "").strip()
    if not question:
        return ""

    artist_name = str(result_row.get("artist_name") or "検索結果").strip()
    gallery = str(result_row.get("gallery_name") or "").strip()
    fair = str(result_row.get("fair_label") or "").strip()
    artist_name_kana = str(result_row.get("artist_name_kana") or "").strip()
    summary = str(result_row.get("summary_ja") or "").strip() or "未付与"
    text = str(result_row.get("text") or "").strip()
    source_url = str(result_row.get("source_url") or "").strip()

    fallback = (
        f"質問: {question}\n"
        f"対象: {artist_name}"
        f"{f'（{artist_name_kana}）' if artist_name_kana else ''}"
        f"{f' / {gallery}' if gallery else ''}"
        f"{f' / {fair}' if fair else ''}\n"
        f"要約: {summary}\n"
        f"根拠: {text[:220] if text else '本文抜粋なし'}\n"
        f"Source: {source_url if source_url else 'なし'}"
    )[:500]

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return fallback

    try:
        from openai import OpenAI

        model = os.getenv("TEXT_MODEL", "gpt-5-mini")
        client = OpenAI(api_key=api_key)
        prompt = (
            "次の質問に日本語で簡潔に回答してください。"
            "与えられた検索コンテキストは参考情報として使い、必要なら一般知識（内部知識）も最大限活用して構いません。"
            "人物・用語の意味や背景は、広く知られた事実に基づいて説明してください。"
            "文脈依存の解釈はコンテキストを優先し、最後に要点を短くまとめてください。\n"
            f"質問: {question}\n"
            f"artist_name: {artist_name}\n"
            f"artist_name_kana: {artist_name_kana}\n"
            f"gallery: {gallery}\n"
            f"fair: {fair}\n"
            f"summary: {summary}\n"
            f"text: {text[:900]}\n"
            f"source_url: {source_url}"
        )
        response = client.responses.create(model=model, input=prompt)
        answer = str(response.output_text or "").strip()
        return answer[:500] if answer else fallback
    except Exception:
        return fallback

