from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from phase2_common_readonly import (
    EXHIBITIONS_IMAGE_META_PATHS,
    EXHIBITIONS_TEXT_PATHS,
    FAIR_LABEL_TO_SLUG,
    FAIR_SLUG_TO_LABEL,
    normalize_url,
    resolve_current_first_enrichment_output_path,
    safe_load_jsonl,
)

EXHIBITION_SEARCH_RESULT_COUNT = 3
EXHIBITION_SEARCH_SUMMARY_MAX_CHARS = 500


def build_exhibition_summary_ja(row: dict, max_chars: int = EXHIBITION_SEARCH_SUMMARY_MAX_CHARS) -> str:
    del max_chars
    summary_ja = str(row.get("summary_ja") or "").strip()
    return summary_ja if summary_ja else "\u672a\u4ed8\u4e0e"


def _extract_year_from_date(date_value: str) -> int | None:
    if not isinstance(date_value, str):
        return None
    m = re.match(r"^(\d{4})", date_value.strip())
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return None
    return None


def _derive_title(row: dict) -> str:
    text = (row.get("text") or "").strip()
    if text:
        first_line = text.splitlines()[0].strip()
        if first_line:
            return first_line[:120]

    source_url = (row.get("source_url") or "").strip()
    if source_url:
        tail = source_url.rstrip("/").split("/")[-1]
        if tail:
            return tail.replace("-", " ")
    return "(untitled)"


def _load_latest_exhibition_enrichment_map() -> Tuple[Dict[str, Dict[str, str]], List[str]]:
    source_path, source_kind = resolve_current_first_enrichment_output_path("exhibitions")
    if source_path is None:
        return {}, []

    rows, warnings = safe_load_jsonl(source_path)
    if source_kind == "legacy_latest":
        warnings.append(f"fallback_to_legacy_enrichment_output: {source_path}")

    enrichment_by_source: Dict[str, Dict[str, str]] = {}
    for row in rows:
        source_url = normalize_url(str(row.get("source_url") or ""))
        if not source_url:
            continue
        headline_ja = str(row.get("headline_ja") or "").strip()
        summary_ja = str(row.get("summary_ja") or "").strip()
        if not headline_ja and not summary_ja:
            continue
        current = enrichment_by_source.setdefault(source_url, {})
        if headline_ja and not current.get("headline_ja"):
            current["headline_ja"] = headline_ja
        if summary_ja and not current.get("summary_ja"):
            current["summary_ja"] = summary_ja
    return enrichment_by_source, warnings


@dataclass
class ExhibitionSearchData:
    records: List[dict]
    warnings: List[str]
    total_rows: int
    fair_rows: Dict[str, int]
    count_note: str


def load_exhibition_records_readonly() -> ExhibitionSearchData:
    warnings: List[str] = []
    records: List[dict] = []
    fair_rows: Dict[str, int] = {"frieze_london": 0, "liste": 0}
    enrichment_by_source, enrichment_warnings = _load_latest_exhibition_enrichment_map()
    warnings.extend(enrichment_warnings)

    image_count_by_source: Dict[str, int] = {}
    image_preview_by_source: Dict[str, str] = {}
    image_preview_r2_by_source: Dict[str, str] = {}
    for fair_slug, meta_path in EXHIBITIONS_IMAGE_META_PATHS.items():
        meta_rows, meta_warnings = safe_load_jsonl(meta_path)
        warnings.extend(meta_warnings)
        for row in meta_rows:
            source_url = normalize_url(str(row.get("source_url", "")))
            if source_url:
                image_count_by_source[source_url] = image_count_by_source.get(source_url, 0) + 1
                if source_url not in image_preview_r2_by_source:
                    image_preview_r2_by_source[source_url] = str(row.get("r2_key") or "").strip()
                if source_url not in image_preview_by_source:
                    local_path = str(row.get("local_path") or "").strip()
                    if local_path and Path(local_path).exists():
                        image_preview_by_source[source_url] = local_path

    for fair_slug, text_path in EXHIBITIONS_TEXT_PATHS.items():
        text_rows, text_warnings = safe_load_jsonl(text_path)
        warnings.extend(text_warnings)
        fair_rows[fair_slug] = len(text_rows)

        for idx, row in enumerate(text_rows, start=1):
            source_url = str(row.get("source_url", "")).strip()
            norm_source_url = normalize_url(source_url)
            enrichment = enrichment_by_source.get(norm_source_url, {})
            headline_ja = str(row.get("headline_ja") or "").strip() or str(enrichment.get("headline_ja") or "").strip()
            summary_ja = str(row.get("summary_ja") or "").strip() or str(enrichment.get("summary_ja") or "").strip()
            year = row.get("target_year")
            if not isinstance(year, int):
                year = (
                    _extract_year_from_date(str(row.get("exhibition_start_date", "")))
                    or _extract_year_from_date(str(row.get("exhibition_end_date", "")))
                )
            record = {
                "id": f"{fair_slug}:{idx}",
                "fair_slug": fair_slug,
                "fair_label": FAIR_SLUG_TO_LABEL.get(fair_slug, fair_slug),
                "gallery_name": str(row.get("gallery_name_en") or ""),
                "exhibition_title": _derive_title(row),
                "year": year if isinstance(year, int) else None,
                "artist_names": str(row.get("participating_artists") or ""),
                "source_url": source_url,
                "text": str(row.get("text") or ""),
                "summary_ja": summary_ja,
                "summary_display_ja": build_exhibition_summary_ja({"summary_ja": summary_ja}),
                "headline_ja": headline_ja,
                "image_count_hint": image_count_by_source.get(norm_source_url, 0),
                "image_preview_r2_key": image_preview_r2_by_source.get(norm_source_url, ""),
                "image_preview": image_preview_by_source.get(norm_source_url, ""),
            }
            records.append(record)

    return ExhibitionSearchData(
        records=records,
        warnings=sorted(set(warnings)),
        total_rows=len(records),
        fair_rows=fair_rows,
        count_note=(
            "Exhibition rows come from formal raw (exhibitions_*_2025.jsonl). "
            "summary_ja/headline_ja uses current-first enrichment output "
            "(data/current/enrichment/exhibitions_enrichment_apply_output_2025.jsonl), "
            "with legacy latest fallback only when current is missing. "
            "history is not used as a default query path. "
            "image_count_hint is read-only matched by source_url using formal derived image metadata."
        ),
    )


def apply_exhibition_filters(records: List[dict], fair_label: str, keyword: str) -> List[dict]:
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
                    str(row.get("gallery_name") or ""),
                    str(row.get("exhibition_title") or ""),
                    str(row.get("artist_names") or ""),
                    str(row.get("source_url") or ""),
                    str(row.get("text") or "")[:500],
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
            str(r.get("exhibition_title") or ""),
        )
    )
    return filtered


def search_exhibitions(
    records: List[dict],
    fair_label: str,
    query_text: str,
    limit: int = EXHIBITION_SEARCH_RESULT_COUNT,
) -> List[dict]:
    safe_limit = max(1, int(limit))
    fair_filtered = apply_exhibition_filters(records, fair_label, "")
    keyword_query = str(query_text or "").strip().lower()
    if not keyword_query:
        return fair_filtered[:safe_limit]

    tokens = [t for t in re.findall("[a-z0-9]{2,}|[\u3040-\u30ff\u4e00-\u9fff]{1,}", keyword_query) if t]
    if not tokens:
        return apply_exhibition_filters(records, fair_label, keyword_query)[:safe_limit]

    scored: List[Tuple[int, dict]] = []
    for row in fair_filtered:
        hay = " ".join(
            [
                str(row.get("gallery_name") or ""),
                str(row.get("exhibition_title") or ""),
                str(row.get("artist_names") or ""),
                str(row.get("source_url") or ""),
                str(row.get("text") or "")[:1200],
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
            str(x[1].get("exhibition_title") or ""),
        )
    )
    if scored:
        return [row for _, row in scored[:safe_limit]]
    if keyword_query:
        return apply_exhibition_filters(records, fair_label, keyword_query)[:safe_limit]
    return fair_filtered[:safe_limit]


def answer_exhibition_followup(question_text: str, result_row: dict) -> str:
    question = str(question_text or "").strip()
    if not question:
        return ""

    title = str(result_row.get("exhibition_title") or "検索結果").strip()
    gallery = str(result_row.get("gallery_name") or "").strip()
    fair = str(result_row.get("fair_label") or "").strip()
    artists = str(result_row.get("artist_names") or "").strip()
    summary = str(result_row.get("summary_ja") or "").strip() or "未付与"
    text = str(result_row.get("text") or "").strip()
    source_url = str(result_row.get("source_url") or "").strip()

    fallback = (
        f"質問: {question}\n"
        f"対象: {title}"
        f"{f' / {gallery}' if gallery else ''}"
        f"{f' / {fair}' if fair else ''}\n"
        f"要約: {summary}\n"
        f"作家: {artists if artists else '記載なし'}\n"
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
            f"title: {title}\n"
            f"gallery: {gallery}\n"
            f"fair: {fair}\n"
            f"artists: {artists}\n"
            f"summary: {summary}\n"
            f"text: {text[:900]}\n"
            f"source_url: {source_url}"
        )
        response = client.responses.create(model=model, input=prompt)
        answer = str(response.output_text or "").strip()
        return (answer[:500] if answer else fallback)
    except Exception:
        return fallback
