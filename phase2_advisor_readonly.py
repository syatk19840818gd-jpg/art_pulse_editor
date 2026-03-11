from __future__ import annotations

import re
from typing import Dict, List

from phase2_art_pulse_readonly import build_art_pulse_overview
from phase2_artist_search_readonly import load_artist_records_readonly
from phase2_common_readonly import normalize_url, resolve_current_first_enrichment_output_path, resolve_fair_slugs
from phase2_exhibition_search_readonly import load_exhibition_records_readonly


def _tokenize_query(query_text: str) -> List[str]:
    tokens: List[str] = []
    for token in re.split(r"[\s,、。|;:()\[\]{}]+", (query_text or "").strip()):
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
            str(r.get("fair_label") or ""),
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


def _resolve_art_pulse_snapshot(fair_label: str) -> tuple[dict, List[str]]:
    try:
        overview = build_art_pulse_overview(
            fair_label=fair_label,
            reporter_id="reporter_01",
            angle_keys=["alex_politics_social_message"],
        )
        return overview, []
    except Exception as exc:  # noqa: BLE001
        return {}, [f"art_pulse_snapshot_unavailable: {type(exc).__name__}: {exc}"]


def _build_exhibition_image_hints(rows: List[dict], selected_urls: set[str], limit: int = 4) -> List[dict]:
    hints: List[dict] = []
    for row in rows:
        source_url = str(row.get("source_url") or "").strip()
        norm_source = normalize_url(source_url)
        if selected_urls and norm_source not in selected_urls:
            continue
        local_path = str(row.get("image_preview") or "").strip()
        r2_key = str(row.get("image_preview_r2_key") or "").strip()
        if not local_path and not r2_key:
            continue
        hints.append(
            {
                "kind": "exhibition",
                "fair_label": str(row.get("fair_label") or ""),
                "gallery": str(row.get("gallery_name") or ""),
                "source_url": source_url,
                "local_path": local_path,
                "r2_key": r2_key,
            }
        )
    if len(hints) >= limit:
        return hints[:limit]

    existing = {str(h.get("source_url") or "") for h in hints}
    for row in rows:
        if len(hints) >= limit:
            break
        source_url = str(row.get("source_url") or "").strip()
        if not source_url or source_url in existing:
            continue
        local_path = str(row.get("image_preview") or "").strip()
        r2_key = str(row.get("image_preview_r2_key") or "").strip()
        if not local_path and not r2_key:
            continue
        existing.add(source_url)
        hints.append(
            {
                "kind": "exhibition",
                "fair_label": str(row.get("fair_label") or ""),
                "gallery": str(row.get("gallery_name") or ""),
                "source_url": source_url,
                "local_path": local_path,
                "r2_key": r2_key,
            }
        )
    return hints[:limit]


def _build_artist_image_hints(rows: List[dict], selected_urls: set[str], limit: int = 4) -> List[dict]:
    hints: List[dict] = []
    for row in rows:
        source_url = str(row.get("source_url") or "").strip()
        norm_source = normalize_url(source_url)
        if selected_urls and norm_source not in selected_urls:
            continue
        candidates = list(row.get("artist_image_preview_candidates") or [])
        if not candidates:
            continue
        first = candidates[0] if isinstance(candidates[0], dict) else {}
        local_path = str(first.get("local_path") or "").strip()
        r2_key = str(first.get("r2_key") or "").strip()
        image_url = str(first.get("image_url") or "").strip()
        if not local_path and not r2_key and not image_url:
            continue
        hints.append(
            {
                "kind": "artist",
                "fair_label": str(row.get("fair_label") or ""),
                "gallery": str(row.get("gallery_name") or ""),
                "source_url": source_url,
                "local_path": local_path,
                "r2_key": r2_key,
                "image_url": image_url,
            }
        )
    if len(hints) >= limit:
        return hints[:limit]

    existing = {str(h.get("source_url") or "") for h in hints}
    for row in rows:
        if len(hints) >= limit:
            break
        source_url = str(row.get("source_url") or "").strip()
        if not source_url or source_url in existing:
            continue
        candidates = list(row.get("artist_image_preview_candidates") or [])
        if not candidates:
            continue
        first = candidates[0] if isinstance(candidates[0], dict) else {}
        local_path = str(first.get("local_path") or "").strip()
        r2_key = str(first.get("r2_key") or "").strip()
        image_url = str(first.get("image_url") or "").strip()
        if not local_path and not r2_key and not image_url:
            continue
        existing.add(source_url)
        hints.append(
            {
                "kind": "artist",
                "fair_label": str(row.get("fair_label") or ""),
                "gallery": str(row.get("gallery_name") or ""),
                "source_url": source_url,
                "local_path": local_path,
                "r2_key": r2_key,
                "image_url": image_url,
            }
        )
    return hints[:limit]


def build_advisor_grounded_context(
    fair_label: str,
    question_text: str,
    text_limit_per_kind: int = 14,
) -> Dict[str, object]:
    fair_slugs = set(resolve_fair_slugs(fair_label))
    tokens = _tokenize_query(question_text)
    warnings: List[str] = []

    ex_data = load_exhibition_records_readonly()
    ar_data = load_artist_records_readonly()
    warnings.extend(ex_data.warnings)
    warnings.extend(ar_data.warnings)

    art_pulse_snapshot, art_pulse_warnings = _resolve_art_pulse_snapshot(fair_label)
    warnings.extend(art_pulse_warnings)

    exhibitions = [r for r in ex_data.records if str(r.get("fair_slug") or "") in fair_slugs]
    artists = [r for r in ar_data.records if str(r.get("fair_slug") or "") in fair_slugs]

    exhibition_rows: List[dict] = []
    for row in exhibitions:
        candidate = {
            "kind": "exhibition",
            "fair_slug": str(row.get("fair_slug") or ""),
            "fair_label": str(row.get("fair_label") or ""),
            "gallery": str(row.get("gallery_name") or ""),
            "title": str(row.get("exhibition_title") or ""),
            "headline_ja": str(row.get("headline_ja") or "").strip(),
            "summary_ja": str(row.get("summary_ja") or "").strip(),
            "source_url": str(row.get("source_url") or ""),
            "text": str(row.get("text") or "").strip(),
            "year": int(row.get("year") or 2025),
        }
        hay = " ".join(
            [
                candidate["gallery"],
                candidate["title"],
                candidate["headline_ja"],
                candidate["summary_ja"],
                candidate["text"][:1200],
            ]
        )
        candidate["_score"] = _score_text(hay, tokens)
        exhibition_rows.append(candidate)

    artist_rows: List[dict] = []
    for row in artists:
        candidate = {
            "kind": "artist",
            "fair_slug": str(row.get("fair_slug") or ""),
            "fair_label": str(row.get("fair_label") or ""),
            "gallery": str(row.get("gallery_name") or ""),
            "artist_name": str(row.get("artist_name") or ""),
            "artist_name_kana": str(row.get("artist_name_kana") or "").strip(),
            "headline_ja": str(row.get("headline_ja") or "").strip(),
            "summary_ja": str(row.get("summary_ja") or "").strip(),
            "source_url": str(row.get("source_url") or ""),
            "text": str(row.get("text") or "").strip(),
            "year": int(row.get("year") or 2025),
        }
        hay = " ".join(
            [
                candidate["gallery"],
                candidate["artist_name"],
                candidate["artist_name_kana"],
                candidate["headline_ja"],
                candidate["summary_ja"],
                candidate["text"][:1200],
            ]
        )
        candidate["_score"] = _score_text(hay, tokens)
        artist_rows.append(candidate)

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

    selected_ex_urls = {normalize_url(str(r.get("source_url") or "")) for r in exhibition_evidence}
    selected_ar_urls = {normalize_url(str(r.get("source_url") or "")) for r in artist_evidence}
    ref_ex_images = _build_exhibition_image_hints(exhibitions, selected_ex_urls, limit=4)
    ref_ar_images = _build_artist_image_hints(artists, selected_ar_urls, limit=4)

    ex_urls = _dedup_urls([str(x.get("source_url") or "") for x in exhibition_evidence])
    ar_urls = _dedup_urls([str(x.get("source_url") or "") for x in artist_evidence])
    all_urls = _dedup_urls(ex_urls + ar_urls)

    ex_enrichment_path, ex_enrichment_kind = resolve_current_first_enrichment_output_path("exhibitions")
    ar_enrichment_path, ar_enrichment_kind = resolve_current_first_enrichment_output_path("artists")

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
            "reference_exhibition_images": len(ref_ex_images),
            "reference_artist_images": len(ref_ar_images),
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
            "exhibition": ref_ex_images,
            "artist": ref_ar_images,
            "all": (ref_ex_images + ref_ar_images)[:8],
        },
        "art_pulse_snapshot": {
            "counts": dict((art_pulse_snapshot.get("counts") or {})),
            "top_galleries": list((art_pulse_snapshot.get("top_galleries") or [])[:6]),
            "top_artists": list((art_pulse_snapshot.get("top_artists") or [])[:6]),
            "warnings_count": len(list(art_pulse_snapshot.get("warnings") or [])),
        },
        "read_paths": {
            "exhibitions_enrichment_output_path": str(ex_enrichment_path) if ex_enrichment_path else "",
            "artists_enrichment_output_path": str(ar_enrichment_path) if ar_enrichment_path else "",
            "exhibitions_enrichment_source_kind": ex_enrichment_kind,
            "artists_enrichment_source_kind": ar_enrichment_kind,
            "history_default_ref_used": False,
        },
        "warnings": sorted(set(warnings)),
        "count_note": (
            "Advisor grounding reuses current-first read-only loaders from Exhibition Search and Artist Search. "
            "Art Pulse overview is attached as a read-only snapshot. "
            "history is not used as a default query path."
        ),
    }
