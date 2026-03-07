from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple


REPO_ROOT = Path(__file__).resolve().parent

ARTISTS_TEXT_PATHS = {
    "frieze_london": REPO_ROOT / "data/phase1_seed10/raw/artists_frieze_london_2025.jsonl",
    "liste": REPO_ROOT / "data/phase1_seed10/raw/artists_liste_2025.jsonl",
}

ARTIST_WORKS_IMAGE_PATHS = {
    "frieze_london": REPO_ROOT / "data/phase1_seed10/derived/artist_works_images_frieze_london.jsonl",
    "liste": REPO_ROOT / "data/phase1_seed10/derived/artist_works_images_liste.jsonl",
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
    return value.rstrip("/")


def _derive_artist_name(source_url: str, fallback: str = "") -> str:
    if fallback.strip():
        return fallback.strip()
    url = (source_url or "").strip().rstrip("/")
    if not url:
        return "(unknown artist)"
    last = url.split("/")[-1].replace("-", " ").strip()
    return last or "(unknown artist)"


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

    image_hint_by_source: Dict[str, dict] = {}
    for fair_slug, path in ARTIST_WORKS_IMAGE_PATHS.items():
        image_rows, image_warnings = _safe_load_jsonl(path)
        warnings.extend(image_warnings)
        for row in image_rows:
            source_url = _normalize_url(str(row.get("source_url", "")))
            if not source_url:
                continue
            works_local_paths = row.get("works_image_local_paths")
            count_hint = len(works_local_paths) if isinstance(works_local_paths, list) else 0
            artist_name_en = str(row.get("artist_name_en") or "")
            prev = image_hint_by_source.get(source_url)
            if prev is None or int(prev.get("count", 0)) < count_hint:
                image_hint_by_source[source_url] = {"count": count_hint, "artist_name_en": artist_name_en}

    for fair_slug, path in ARTISTS_TEXT_PATHS.items():
        text_rows, text_warnings = _safe_load_jsonl(path)
        warnings.extend(text_warnings)
        fair_rows[fair_slug] = len(text_rows)

        for idx, row in enumerate(text_rows, start=1):
            source_url = str(row.get("source_url") or "").strip()
            norm_source = _normalize_url(source_url)
            hint = image_hint_by_source.get(norm_source, {})

            year = row.get("target_year")
            year_value = year if isinstance(year, int) else None
            artist_name = _derive_artist_name(source_url, str(hint.get("artist_name_en") or ""))

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
                    "headline_ja": str(row.get("headline_ja") or ""),
                    "summary_ja": str(row.get("summary_ja") or ""),
                    "works_image_count_hint": int(hint.get("count", 0) or 0),
                }
            )

    return ArtistSearchData(
        records=records,
        warnings=sorted(set(warnings)),
        total_rows=len(records),
        fair_rows=fair_rows,
        count_note=(
            "Artist rows come from formal raw (artists_*_2025.jsonl). "
            "works_image_count_hint is strict source_url match against formal artist works-image metadata."
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

