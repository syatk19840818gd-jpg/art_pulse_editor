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


def _resolve_fair_slugs(fair_label: str) -> List[str]:
    if fair_label == "Frieze London + Liste Art Fair Basel":
        return ["frieze_london", "liste"]
    if fair_label in FAIR_LABEL_TO_SLUG:
        return [FAIR_LABEL_TO_SLUG[fair_label]]
    return ["frieze_london", "liste"]


def _normalize_url(url: str) -> str:
    value = (url or "").strip()
    if not value:
        return ""
    return value.rstrip("/")


def _derive_exhibition_title(row: dict) -> str:
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


def _derive_artist_name(row: dict) -> str:
    explicit = str(row.get("artist_name_en") or "").strip()
    if explicit:
        return explicit
    source_url = (row.get("source_url") or "").strip().rstrip("/")
    if source_url:
        tail = source_url.split("/")[-1]
        if tail:
            tail = re.sub(r"^\d+-", "", tail)
            return tail.replace("-", " ")
    return "(unknown artist)"


def _tokenize_query(query_text: str) -> List[str]:
    tokens: List[str] = []
    for token in re.split(r"[\s,、。/|;:()\[\]{}]+", (query_text or "").strip()):
        token = token.strip().lower()
        if len(token) >= 2:
            tokens.append(token)
    return tokens[:20]


def _score_text(haystack: str, tokens: List[str]) -> int:
    if not tokens:
        return 0
    low = (haystack or "").lower()
    return sum(1 for t in tokens if t in low)


def _pick_top_by_score(rows: List[dict], limit: int) -> List[dict]:
    return sorted(
        rows,
        key=lambda r: (
            -int(r.get("_score", 0)),
            str(r.get("gallery") or ""),
            str(r.get("source_url") or ""),
        ),
    )[:limit]


def _dedup_urls(urls: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for url in urls:
        val = (url or "").strip()
        if not val or val in seen:
            continue
        seen.add(val)
        out.append(val)
    return out


def build_advisor_grounded_context(
    fair_label: str,
    question_text: str,
    text_limit_per_kind: int = 14,
) -> Dict[str, object]:
    fair_slugs = _resolve_fair_slugs(fair_label)
    tokens = _tokenize_query(question_text)
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

        for row in ex_rows:
            source_url = str(row.get("source_url") or "").strip()
            candidate = {
                "kind": "exhibition",
                "fair_slug": fair_slug,
                "fair_label": FAIR_SLUG_TO_LABEL[fair_slug],
                "gallery": str(row.get("gallery_name_en") or ""),
                "title": _derive_exhibition_title(row),
                "source_url": source_url,
                "text": str(row.get("text") or "").strip(),
                "year": int(row.get("target_year") or 2025),
            }
            hay = " ".join(
                [
                    candidate["gallery"],
                    candidate["title"],
                    str(row.get("participating_artists") or ""),
                    candidate["text"][:1000],
                ]
            )
            candidate["_score"] = _score_text(hay, tokens)
            exhibition_rows.append(candidate)

        for row in ar_rows:
            source_url = str(row.get("source_url") or "").strip()
            artist_name = _derive_artist_name(row)
            candidate = {
                "kind": "artist",
                "fair_slug": fair_slug,
                "fair_label": FAIR_SLUG_TO_LABEL[fair_slug],
                "gallery": str(row.get("gallery_name_en") or ""),
                "artist_name": artist_name,
                "source_url": source_url,
                "text": str(row.get("text") or "").strip(),
                "year": int(row.get("target_year") or 2025),
            }
            hay = " ".join(
                [
                    candidate["gallery"],
                    candidate["artist_name"],
                    candidate["text"][:1000],
                ]
            )
            candidate["_score"] = _score_text(hay, tokens)
            artist_rows.append(candidate)

        exhibition_image_rows.extend([{**row, "_fair_slug": fair_slug} for row in exi_rows])
        artist_image_rows.extend([{**row, "_fair_slug": fair_slug} for row in ari_rows])

    if tokens:
        ex_scored = [r for r in exhibition_rows if int(r.get("_score", 0)) > 0] or exhibition_rows
        ar_scored = [r for r in artist_rows if int(r.get("_score", 0)) > 0] or artist_rows
    else:
        ex_scored = exhibition_rows
        ar_scored = artist_rows

    exhibition_evidence = _pick_top_by_score(ex_scored, text_limit_per_kind)
    artist_evidence = _pick_top_by_score(ar_scored, text_limit_per_kind)

    for row in exhibition_evidence:
        row.pop("_score", None)
    for row in artist_evidence:
        row.pop("_score", None)

    selected_ex_urls = {_normalize_url(str(r.get("source_url") or "")) for r in exhibition_evidence}
    selected_ar_urls = {_normalize_url(str(r.get("source_url") or "")) for r in artist_evidence}

    ref_ex_images: List[dict] = []
    for row in exhibition_image_rows:
        source_url = _normalize_url(str(row.get("source_url") or ""))
        if selected_ex_urls and source_url not in selected_ex_urls:
            continue
        ref_ex_images.append(
            {
                "kind": "exhibition",
                "fair_label": FAIR_SLUG_TO_LABEL.get(str(row.get("_fair_slug") or ""), ""),
                "gallery": str(row.get("gallery_name_en") or ""),
                "source_url": str(row.get("source_url") or ""),
                "local_path": str(row.get("local_path") or ""),
            }
        )

    ref_ar_images: List[dict] = []
    for row in artist_image_rows:
        source_url = _normalize_url(str(row.get("source_url") or ""))
        if selected_ar_urls and source_url not in selected_ar_urls:
            continue
        local_paths = row.get("works_image_local_paths")
        first_local = ""
        if isinstance(local_paths, list) and local_paths:
            first_local = str(local_paths[0] or "")
        ref_ar_images.append(
            {
                "kind": "artist",
                "fair_label": FAIR_SLUG_TO_LABEL.get(str(row.get("_fair_slug") or ""), ""),
                "gallery": str(row.get("gallery_name_en") or ""),
                "source_url": str(row.get("source_url") or ""),
                "local_path": first_local,
            }
        )

    # Fallback to any rows when strict source_url hit is small.
    if len(ref_ex_images) < 4:
        for row in exhibition_image_rows:
            if len(ref_ex_images) >= 4:
                break
            source_url = str(row.get("source_url") or "")
            if source_url in {x["source_url"] for x in ref_ex_images}:
                continue
            ref_ex_images.append(
                {
                    "kind": "exhibition",
                    "fair_label": FAIR_SLUG_TO_LABEL.get(str(row.get("_fair_slug") or ""), ""),
                    "gallery": str(row.get("gallery_name_en") or ""),
                    "source_url": source_url,
                    "local_path": str(row.get("local_path") or ""),
                }
            )

    if len(ref_ar_images) < 4:
        for row in artist_image_rows:
            if len(ref_ar_images) >= 4:
                break
            source_url = str(row.get("source_url") or "")
            if source_url in {x["source_url"] for x in ref_ar_images}:
                continue
            local_paths = row.get("works_image_local_paths")
            first_local = ""
            if isinstance(local_paths, list) and local_paths:
                first_local = str(local_paths[0] or "")
            ref_ar_images.append(
                {
                    "kind": "artist",
                    "fair_label": FAIR_SLUG_TO_LABEL.get(str(row.get("_fair_slug") or ""), ""),
                    "gallery": str(row.get("gallery_name_en") or ""),
                    "source_url": source_url,
                    "local_path": first_local,
                }
            )

    ex_urls = _dedup_urls([str(x.get("source_url") or "") for x in exhibition_evidence])
    ar_urls = _dedup_urls([str(x.get("source_url") or "") for x in artist_evidence])
    all_urls = _dedup_urls(ex_urls + ar_urls)

    return {
        "selection": {
            "fair_label": fair_label,
            "year": 2025,
            "tokens": tokens,
        },
        "counts": {
            "exhibitions_text_evidence_count": len(exhibition_evidence),
            "artist_text_evidence_count": len(artist_evidence),
            "all_unique_url_count": len(all_urls),
            "reference_exhibition_images": len(ref_ex_images[:4]),
            "reference_artist_images": len(ref_ar_images[:4]),
        },
        "exhibition_evidence": exhibition_evidence,
        "artist_evidence": artist_evidence,
        "evidence_urls": {
            "exhibition": ex_urls,
            "artist": ar_urls,
            "all": all_urls,
        },
        "reference_images": {
            "target_exhibition_images": 4,
            "target_artist_images": 4,
            "exhibition": ref_ex_images[:4],
            "artist": ref_ar_images[:4],
            "all": (ref_ex_images[:4] + ref_ar_images[:4])[:8],
        },
        "warnings": sorted(set(warnings)),
        "count_note": (
            "Advisor grounding uses formal raw texts (exhibitions/artists) as primary evidence. "
            "Image references are read-only metadata hints."
        ),
    }
