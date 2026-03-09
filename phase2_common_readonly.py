from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parent

FAIR_LABEL_TO_SLUG = {
    "Frieze London": "frieze_london",
    "Liste Art Fair Basel": "liste",
}
FAIR_SLUG_TO_LABEL = {value: key for key, value in FAIR_LABEL_TO_SLUG.items()}

EXHIBITIONS_TEXT_PATHS = {
    "frieze_london": REPO_ROOT / "data/phase1_seed10/raw/exhibitions_frieze_london_2025.jsonl",
    "liste": REPO_ROOT / "data/phase1_seed10/raw/exhibitions_liste_2025.jsonl",
}
ARTISTS_TEXT_PATHS = {
    "frieze_london": REPO_ROOT / "data/phase1_seed10/raw/artists_frieze_london_2025.jsonl",
    "liste": REPO_ROOT / "data/phase1_seed10/raw/artists_liste_2025.jsonl",
}
EXHIBITIONS_IMAGE_META_PATHS = {
    "frieze_london": REPO_ROOT / "data/phase1_seed10/derived/exhibitions_images_frieze_london_2025.jsonl",
    "liste": REPO_ROOT / "data/phase1_seed10/derived/exhibitions_images_liste_2025.jsonl",
}
ARTIST_WORKS_IMAGE_PATHS = {
    "frieze_london": REPO_ROOT / "data/phase1_seed10/derived/artist_works_images_frieze_london.jsonl",
    "liste": REPO_ROOT / "data/phase1_seed10/derived/artist_works_images_liste.jsonl",
}

GALLERY_LIST_PATHS = {
    "frieze_london": REPO_ROOT / "data/gallery_lists/gallery_list_frieze_london.csv",
    "liste": REPO_ROOT / "data/gallery_lists/gallery_list_liste.csv",
}

TARUTANI_TEXT_PATH = REPO_ROOT / "data/Tarutani_data/tarutani_text.jsonl"
IMAGES_CACHE_DIR = REPO_ROOT / "data/phase1_seed10/derived/images"


def resolve_fair_slugs(fair_label: str) -> List[str]:
    if fair_label == "Frieze London + Liste Art Fair Basel":
        return ["frieze_london", "liste"]
    if fair_label in FAIR_LABEL_TO_SLUG:
        return [FAIR_LABEL_TO_SLUG[fair_label]]
    return ["frieze_london", "liste"]


def safe_load_jsonl(path: Path) -> Tuple[List[dict], List[str]]:
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


def normalize_url(url: str) -> str:
    value = (url or "").strip()
    if not value:
        return ""
    return value.rstrip("/")


def derive_exhibition_title(row: dict) -> str:
    headline = (row.get("headline_ja") or "").strip()
    if headline:
        return headline
    text = (row.get("text") or "").strip()
    if text:
        first_line = text.splitlines()[0].strip()
        if first_line:
            return first_line[:120]
    source_url = (row.get("source_url") or "").strip().rstrip("/")
    if source_url:
        tail = source_url.split("/")[-1]
        if tail:
            return tail.replace("-", " ")
    return "(untitled)"


def derive_artist_name(source_url: str, fallback: str = "") -> str:
    if fallback.strip():
        return fallback.strip()
    url = (source_url or "").strip().rstrip("/")
    if not url:
        return "(unknown artist)"
    last = url.split("/")[-1].replace("-", " ").strip()
    return last or "(unknown artist)"

