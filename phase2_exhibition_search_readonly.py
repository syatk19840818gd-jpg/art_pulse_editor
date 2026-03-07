from __future__ import annotations

import json
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
    for fair_slug, meta_path in EXHIBITIONS_IMAGE_META_PATHS.items():
        meta_rows, meta_warnings = _safe_load_jsonl(meta_path)
        warnings.extend(meta_warnings)
        for row in meta_rows:
            source_url = _normalize_url(str(row.get("source_url", "")))
            if source_url:
                image_count_by_source[source_url] = image_count_by_source.get(source_url, 0) + 1

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
                "headline_ja": str(row.get("headline_ja") or ""),
                "image_count_hint": image_count_by_source.get(norm_source_url, 0),
            }
            records.append(record)

    return ExhibitionSearchData(
        records=records,
        warnings=sorted(set(warnings)),
        total_rows=len(records),
        fair_rows=fair_rows,
        count_note=(
            "Exhibition rows come from formal raw (exhibitions_*_2025.jsonl). "
            "image_count_hint is read-only source_url match against formal derived image metadata."
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

