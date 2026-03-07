from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

from phase2_art_pulse_config import find_persona, find_persona_angle

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

ART_PULSE_IMAGE_POOL_PER_KIND = 24


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


def _derive_exhibition_title(row: dict) -> str:
    headline = (row.get("headline_ja") or "").strip()
    if headline:
        return headline
    text = (row.get("text") or "").strip()
    if text:
        first_line = text.splitlines()[0].strip()
        if first_line:
            return first_line[:120]
    source = (row.get("source_url") or "").strip().rstrip("/")
    if source:
        tail = source.split("/")[-1]
        if tail:
            return tail.replace("-", " ")
    return "(untitled)"


def _derive_artist_name(row: dict) -> str:
    explicit = str(row.get("artist_name_en") or "").strip()
    if explicit:
        return explicit
    source = (row.get("source_url") or "").strip().rstrip("/")
    if source:
        tail = source.split("/")[-1]
        if tail:
            tail = re.sub(r"^\d+-", "", tail)
            return tail.replace("-", " ")
    return "(unknown artist)"


def _extract_artists_from_exhibition(row: dict) -> List[str]:
    raw = str(row.get("participating_artists") or "").strip()
    if not raw:
        return []
    tokens = [t.strip() for t in re.split(r"[,\n;/|]+", raw) if t.strip()]
    return [t[:120] for t in tokens]


def _resolve_fair_slugs(fair_label: str) -> List[str]:
    if fair_label == "Frieze London + Liste Art Fair Basel":
        return ["frieze_london", "liste"]
    if fair_label in FAIR_LABEL_TO_SLUG:
        return [FAIR_LABEL_TO_SLUG[fair_label]]
    return ["frieze_london", "liste"]


def _round_robin_by_fair(candidates: List[Dict[str, object]], max_count: int) -> List[Dict[str, object]]:
    by_fair: Dict[str, List[Dict[str, object]]] = {}
    for row in candidates:
        fair = str(row.get("fair") or "")
        by_fair.setdefault(fair, []).append(row)
    order = [label for label in ("Frieze London", "Liste Art Fair Basel") if label in by_fair]
    for fair in sorted(by_fair.keys()):
        if fair not in order:
            order.append(fair)
    selected: List[Dict[str, object]] = []
    while len(selected) < max_count and any(by_fair.get(fair) for fair in order):
        for fair in order:
            rows = by_fair.get(fair) or []
            if not rows:
                continue
            selected.append(rows.pop(0))
            if len(selected) >= max_count:
                break
    return selected


def build_art_pulse_overview(fair_label: str, reporter_id: str, angle_keys: List[str]) -> Dict[str, object]:
    fair_slugs = _resolve_fair_slugs(fair_label)
    warnings: List[str] = []

    exhibition_rows: List[dict] = []
    artist_rows: List[dict] = []
    exhibition_image_rows: List[dict] = []
    artist_image_rows: List[dict] = []

    for fair_slug in fair_slugs:
        ex_rows, ex_warn = _safe_load_jsonl(EXHIBITIONS_TEXT_PATHS[fair_slug])
        ar_rows, ar_warn = _safe_load_jsonl(ARTISTS_TEXT_PATHS[fair_slug])
        exi_rows, exi_warn = _safe_load_jsonl(EXHIBITIONS_IMAGE_META_PATHS[fair_slug])
        ari_rows, ari_warn = _safe_load_jsonl(ARTIST_WORKS_IMAGE_PATHS[fair_slug])
        warnings.extend(ex_warn + ar_warn + exi_warn + ari_warn)
        exhibition_rows.extend(
            [{**row, "_fair_slug": fair_slug, "_fair_label": FAIR_SLUG_TO_LABEL[fair_slug]} for row in ex_rows]
        )
        artist_rows.extend(
            [{**row, "_fair_slug": fair_slug, "_fair_label": FAIR_SLUG_TO_LABEL[fair_slug]} for row in ar_rows]
        )
        exhibition_image_rows.extend(
            [{**row, "_fair_slug": fair_slug, "_fair_label": FAIR_SLUG_TO_LABEL[fair_slug]} for row in exi_rows]
        )
        artist_image_rows.extend(
            [{**row, "_fair_slug": fair_slug, "_fair_label": FAIR_SLUG_TO_LABEL[fair_slug]} for row in ari_rows]
        )

    gallery_counter: Counter[str] = Counter()
    artist_counter: Counter[str] = Counter()

    exhibition_candidates: List[Dict[str, object]] = []
    artist_candidates: List[Dict[str, object]] = []
    for row in exhibition_rows:
        gallery = str(row.get("gallery_name_en") or "")
        if gallery:
            gallery_counter[gallery] += 1
        for artist_name in _extract_artists_from_exhibition(row):
            artist_counter[artist_name] += 1
        exhibition_candidates.append(
            {
                "fair": row.get("_fair_label"),
                "gallery": gallery,
                "title": _derive_exhibition_title(row),
                "year": row.get("target_year") or 2025,
                "source_url": row.get("source_url") or "",
            }
        )

    for row in artist_rows:
        gallery = str(row.get("gallery_name_en") or "")
        if gallery:
            gallery_counter[gallery] += 1
        artist_name = _derive_artist_name(row)
        artist_counter[artist_name] += 1
        artist_candidates.append(
            {
                "fair": row.get("_fair_label"),
                "gallery": gallery,
                "artist": artist_name,
                "artist_name_en": artist_name,
                "artist_name_kana": row.get("artist_name_kana") or "",
                "year": row.get("target_year") or 2025,
                "source_url": row.get("source_url") or "",
                "text_snippet": (str(row.get("text") or "").strip())[:220],
            }
        )

    top_galleries = [{"gallery_name": name, "count": count} for name, count in gallery_counter.most_common(12)]
    top_artists = [{"artist_name": name, "count": count} for name, count in artist_counter.most_common(12)]

    exhibition_candidates.sort(
        key=lambda r: (
            str(r.get("fair") or ""),
            str(r.get("gallery") or ""),
            str(r.get("title") or ""),
        )
    )
    artist_candidates.sort(
        key=lambda r: (
            str(r.get("fair") or ""),
            str(r.get("gallery") or ""),
            str(r.get("artist") or ""),
        )
    )

    exhibition_source_urls = {str(r.get("source_url") or "").strip() for r in exhibition_candidates if r.get("source_url")}
    all_ex_image_candidates: List[Dict[str, object]] = []
    for row in exhibition_image_rows:
        all_ex_image_candidates.append(
            {
                "kind": "exhibition",
                "fair": row.get("_fair_label"),
                "gallery": row.get("gallery_name_en") or "",
                "source_url": row.get("source_url") or "",
                "local_path": row.get("local_path") or "",
                "image_url": row.get("image_url") or "",
            }
        )
    matched_ex = [
        r for r in all_ex_image_candidates if str(r.get("source_url") or "").strip() in exhibition_source_urls
    ]
    ex_image_candidates = _round_robin_by_fair(
        matched_ex or all_ex_image_candidates,
        max_count=ART_PULSE_IMAGE_POOL_PER_KIND,
    )

    artist_source_urls = {str(r.get("source_url") or "").strip() for r in artist_candidates if r.get("source_url")}
    all_ar_image_candidates: List[Dict[str, object]] = []
    for row in artist_image_rows:
        first_local = ""
        local_paths = row.get("works_image_local_paths")
        if isinstance(local_paths, list) and local_paths:
            first_local = str(local_paths[0] or "")
        first_image_url = ""
        image_urls = row.get("works_image_urls")
        if isinstance(image_urls, list) and image_urls:
            first_image_url = str(image_urls[0] or "")
        all_ar_image_candidates.append(
            {
                "kind": "artist",
                "fair": row.get("_fair_label"),
                "gallery": row.get("gallery_name_en") or "",
                "source_url": row.get("source_url") or "",
                "local_path": first_local,
                "image_url": first_image_url,
                "artist_name_en": row.get("artist_name_en") or "",
            }
        )
    matched_ar = [r for r in all_ar_image_candidates if str(r.get("source_url") or "").strip() in artist_source_urls]
    ar_image_candidates = _round_robin_by_fair(
        matched_ar or all_ar_image_candidates,
        max_count=ART_PULSE_IMAGE_POOL_PER_KIND,
    )

    reporter = find_persona(reporter_id)
    normalized_angle_keys = list(angle_keys or [])
    if not normalized_angle_keys and reporter.get("angles"):
        normalized_angle_keys = [str(reporter["angles"][0].get("key"))]
    angle_labels: List[str] = []
    for key in normalized_angle_keys:
        angle_obj = find_persona_angle(reporter, key)
        angle_labels.append(str(angle_obj.get("label")) if angle_obj else key)

    return {
        "selection": {
            "fair_label": fair_label,
            "year": 2025,
            "reporter_id": reporter["id"],
            "reporter_label": reporter["label"],
            "angle_keys": normalized_angle_keys,
            "angle_labels": angle_labels,
        },
        "counts": {
            "exhibitions_text_count": len(exhibition_rows),
            "artist_text_count": len(artist_rows),
            "exhibitions_image_candidate_count": len(exhibition_image_rows),
            "artist_image_candidate_count": len(artist_image_rows),
        },
        "top_galleries": top_galleries,
        "top_artists": top_artists,
        "exhibition_candidates": _round_robin_by_fair(exhibition_candidates, max_count=30),
        "artist_candidates": _round_robin_by_fair(artist_candidates, max_count=30),
        "image_reference_plan": {
            "target_exhibition_images": 4,
            "target_artist_images": 4,
            "available_exhibition_images": len(exhibition_image_rows),
            "available_artist_images": len(artist_image_rows),
            "exhibition_image_candidates": ex_image_candidates,
            "artist_image_candidates": ar_image_candidates,
        },
        "warnings": sorted(set(warnings)),
        "count_note": (
            "formal の Exhibitions Text / Artist Text を主根拠として集計。"
            "画像候補は metadata の読み取り専用参照のみ。"
        ),
        "preview_note": "この overview は記事生成前の根拠確認用です（read-only）。",
    }
