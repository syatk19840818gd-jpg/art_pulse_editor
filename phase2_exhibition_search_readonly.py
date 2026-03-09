from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple


REPO_ROOT = Path(__file__).resolve().parent

EXHIBITIONS_TEXT_PATHS = {
    "frieze_london": REPO_ROOT / "data/phase1_seed10/raw/exhibitions_frieze_london_2025.jsonl",
    "liste": REPO_ROOT / "data/phase1_seed10/raw/exhibitions_liste_2025.jsonl",
}

EXHIBITIONS_IMAGE_META_PATHS = {
    "frieze_london": REPO_ROOT / "data/phase1_seed10/derived/exhibitions_images_frieze_london_2025.jsonl",
    "liste": REPO_ROOT / "data/phase1_seed10/derived/exhibitions_images_liste_2025.jsonl",
}

FAIR_LABEL_TO_SLUG = {
    "Frieze London": "frieze_london",
    "Liste Art Fair Basel": "liste",
}

FAIR_SLUG_TO_LABEL = {value: key for key, value in FAIR_LABEL_TO_SLUG.items()}
EXHIBITION_SEARCH_RESULT_COUNT = 3
EXHIBITION_SEARCH_SUMMARY_MAX_CHARS = 500


def build_exhibition_summary_ja(row: dict, max_chars: int = EXHIBITION_SEARCH_SUMMARY_MAX_CHARS) -> str:
    del max_chars
    summary_ja = str(row.get("summary_ja") or "").strip()
    return summary_ja if summary_ja else "未付与"


def _safe_load_jsonl(path: Path) -> Tuple[List[dict], List[str]]:
    rows: List[dict] = []
    warnings: List[str] = []
    if not path.exists():
        warnings.append(f"missing: {path}")
        return rows, warnings
    try:
        with path.open("r", encoding="utf-8") as f:
            for idx, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    warnings.append(f"json_decode_error: {path} line={idx}")
    except OSError as exc:
        warnings.append(f"read_error: {path} ({exc})")
    return rows, warnings


def _normalize_url(url: str) -> str:
    value = (url or "").strip()
    if not value:
        return ""
    # Read-only match helper for metadata join only.
    return value.rstrip("/")


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
    headline = (row.get("headline_ja") or "").strip()
    if headline:
        return headline

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

    image_count_by_source: Dict[str, int] = {}
    image_preview_by_source: Dict[str, str] = {}
    for fair_slug, meta_path in EXHIBITIONS_IMAGE_META_PATHS.items():
        meta_rows, meta_warnings = _safe_load_jsonl(meta_path)
        warnings.extend(meta_warnings)
        for row in meta_rows:
            source_url = _normalize_url(str(row.get("source_url", "")))
            if source_url:
                image_count_by_source[source_url] = image_count_by_source.get(source_url, 0) + 1
                if source_url not in image_preview_by_source:
                    local_path = str(row.get("local_path") or "").strip()
                    image_url = str(row.get("image_url") or "").strip()
                    if image_url:
                        image_preview_by_source[source_url] = image_url
                    elif local_path and Path(local_path).exists():
                        image_preview_by_source[source_url] = local_path

    for fair_slug, text_path in EXHIBITIONS_TEXT_PATHS.items():
        text_rows, text_warnings = _safe_load_jsonl(text_path)
        warnings.extend(text_warnings)
        fair_rows[fair_slug] = len(text_rows)

        for idx, row in enumerate(text_rows, start=1):
            source_url = str(row.get("source_url", "")).strip()
            norm_source_url = _normalize_url(source_url)
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
                "summary_ja": str(row.get("summary_ja") or ""),
                "summary_display_ja": build_exhibition_summary_ja(row),
                "headline_ja": str(row.get("headline_ja") or ""),
                "image_count_hint": image_count_by_source.get(norm_source_url, 0),
                "image_preview": image_preview_by_source.get(norm_source_url, ""),
            }
            records.append(record)

    return ExhibitionSearchData(
        records=records,
        warnings=sorted(set(warnings)),
        total_rows=len(records),
        fair_rows=fair_rows,
        count_note=(
            "Exhibition行は formal raw（exhibitions_*_2025.jsonl）由来。"
            " image_count_hint は formal derived画像メタとの source_url 厳密一致（読み取り専用）。"
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
    image_hint_text: str = "",
    limit: int = EXHIBITION_SEARCH_RESULT_COUNT,
) -> List[dict]:
    fair_filtered = apply_exhibition_filters(records, fair_label, "")
    combined_query = " ".join([str(query_text or "").strip(), str(image_hint_text or "").strip()]).strip().lower()
    if not combined_query:
        return fair_filtered[: max(1, int(limit))]

    tokens = [t for t in re.findall(r"[a-z0-9]{2,}|[\u3040-\u30ff\u4e00-\u9fff]{2,}", combined_query) if t]
    if not tokens:
        return []

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
    safe_limit = max(1, int(limit))
    return [row for _, row in scored[:safe_limit]]


def answer_exhibition_followup(question_text: str, result_row: dict) -> str:
    question = str(question_text or "").strip()
    if not question:
        return ""

    title = str(result_row.get("exhibition_title") or "検索結果3件").strip()
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
        f"補足: {text[:220] if text else '本文抜粋なし'}\n"
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
            "次の展示検索コンテキストだけを根拠に、質問へ日本語で簡潔に回答してください。"
            "断定できない点は推測せず、比較観点を提示してください。\n"
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

