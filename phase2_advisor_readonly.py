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


def _is_broad_query(question_text: str, tokens: List[str]) -> bool:
    q = (question_text or "").strip().lower()
    if not q:
        return False
    starter_hints = ["どんな", "何を", "なにを"]
    if not any(hint in q for hint in starter_hints):
        return False
    specific_scope_hints = [
        "展示",
        "作家",
        "ギャラリー",
        "導線",
        "スケール",
        "インスタレーション",
        "ステートメント",
        "会場",
    ]
    if any(hint in q for hint in specific_scope_hints):
        return False
    return len(tokens) <= 8 and len(q) <= 40


def _score_text(haystack: str, tokens: List[str]) -> int:
    if not tokens:
        return 0
    low = (haystack or "").lower()
    return sum(1 for t in tokens if t in low)


def _pick_top_by_score(
    rows: List[dict],
    limit: int,
    prefer_cross_fair_diversity: bool = False,
    per_fair_gallery_cap: int = 2,
) -> List[dict]:
    sorted_rows = sorted(
        rows,
        key=lambda r: (
            -int(r.get("_rank_score", r.get("_score", 0))),
            int(r.get("_reuse_penalty", 0)),
            str(r.get("fair_label") or ""),
            str(r.get("gallery") or ""),
            str(r.get("source_url") or ""),
        ),
    )
    if not prefer_cross_fair_diversity or limit <= 1:
        return sorted_rows[:limit]

    selected: List[dict] = []
    selected_ids: set[int] = set()
    fair_seen: set[str] = set()
    gallery_counts: Dict[tuple[str, str], int] = {}

    # Pass 1: ensure at least one evidence row per fair when available.
    for idx, row in enumerate(sorted_rows):
        fair_key = str(row.get("fair_slug") or row.get("fair_label") or "").strip()
        gallery_key = str(row.get("gallery") or "").strip()
        if not fair_key or fair_key in fair_seen:
            continue
        fair_gallery_key = (fair_key, gallery_key)
        if gallery_key and gallery_counts.get(fair_gallery_key, 0) >= per_fair_gallery_cap:
            continue
        selected.append(row)
        selected_ids.add(idx)
        fair_seen.add(fair_key)
        if gallery_key:
            gallery_counts[fair_gallery_key] = gallery_counts.get(fair_gallery_key, 0) + 1
        if len(selected) >= limit:
            return selected

    # Pass 2: fill by score while capping concentration by same fair+gallery.
    for idx, row in enumerate(sorted_rows):
        if idx in selected_ids:
            continue
        fair_key = str(row.get("fair_slug") or row.get("fair_label") or "").strip()
        gallery_key = str(row.get("gallery") or "").strip()
        fair_gallery_key = (fair_key, gallery_key)
        if gallery_key and gallery_counts.get(fair_gallery_key, 0) >= per_fair_gallery_cap:
            continue
        selected.append(row)
        selected_ids.add(idx)
        if gallery_key:
            gallery_counts[fair_gallery_key] = gallery_counts.get(fair_gallery_key, 0) + 1
        if len(selected) >= limit:
            return selected

    # Pass 3: if cap filtered too much, backfill remaining by score.
    for idx, row in enumerate(sorted_rows):
        if idx in selected_ids:
            continue
        selected.append(row)
        if len(selected) >= limit:
            return selected
    return selected


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


def _coerce_year(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        year = value
    else:
        text = str(value or "").strip()
        if not text or not text.isdigit():
            return None
        year = int(text)
    if 1900 <= year <= 2100:
        return year
    return None


def _filter_latest_available_year_rows(rows: List[dict]) -> tuple[List[dict], int | None]:
    if not rows:
        return rows, None
    valid_years = [_coerce_year(r.get("year")) for r in rows]
    filtered_years = [y for y in valid_years if y is not None]
    if not filtered_years:
        return rows, None
    latest_year = max(filtered_years)
    filtered_rows = [r for r in rows if _coerce_year(r.get("year")) == latest_year]
    return filtered_rows, latest_year


def _snippet(value: object, limit: int = 88) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


def _build_evidence_rows(exhibition_evidence: List[dict], artist_evidence: List[dict], limit_per_kind: int = 8) -> List[dict]:
    rows: List[dict] = []
    for idx, row in enumerate(exhibition_evidence[:limit_per_kind], start=1):
        label = str(row.get("title") or "").strip() or "展示名不明"
        snippet = _snippet(row.get("summary_ja") or row.get("headline_ja") or row.get("text") or "")
        rows.append(
            {
                "ref": f"EX-{idx:02d}",
                "kind": "Exhibition",
                "fair": str(row.get("fair_label") or ""),
                "gallery": str(row.get("gallery") or ""),
                "label": label,
                "snippet": snippet,
                "source_url": str(row.get("source_url") or ""),
            }
        )
    for idx, row in enumerate(artist_evidence[:limit_per_kind], start=1):
        label = str(row.get("artist_name") or "").strip() or "作家名不明"
        snippet = _snippet(row.get("summary_ja") or row.get("headline_ja") or row.get("text") or "")
        rows.append(
            {
                "ref": f"AR-{idx:02d}",
                "kind": "Artist",
                "fair": str(row.get("fair_label") or ""),
                "gallery": str(row.get("gallery") or ""),
                "label": label,
                "snippet": snippet,
                "source_url": str(row.get("source_url") or ""),
            }
        )
    return rows


def _order_cross_fair_rows(rows: List[dict]) -> List[dict]:
    if not rows:
        return rows
    fair_order: List[str] = []
    buckets: Dict[str, List[dict]] = {}
    for row in rows:
        fair = str(row.get("fair_label") or row.get("fair_slug") or "").strip()
        if fair not in buckets:
            buckets[fair] = []
            fair_order.append(fair)
        buckets[fair].append(row)
    if len([fair for fair in fair_order if fair]) <= 1:
        return rows

    ordered: List[dict] = []
    while True:
        moved = False
        for fair in fair_order:
            bucket = buckets.get(fair, [])
            if not bucket:
                continue
            ordered.append(bucket.pop(0))
            moved = True
        if not moved:
            break
    return ordered


def _rotate_rows(rows: List[dict], rotation_index: int) -> List[dict]:
    if not rows:
        return rows
    offset = int(rotation_index or 0) % len(rows)
    if offset <= 0:
        return rows
    return rows[offset:] + rows[:offset]


def _count_history_values(history: List[dict], key: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for item in history:
        values = item.get(key, [])
        if not isinstance(values, list):
            continue
        for value in values:
            text = str(value or "").strip()
            if not text:
                continue
            counts[text] = counts.get(text, 0) + 1
    return counts


def _apply_broad_history_penalty(
    rows: List[dict],
    history: List[dict],
    kind: str,
) -> List[dict]:
    fair_counts = _count_history_values(history, "anchor_fairs")
    gallery_counts = _count_history_values(history, "anchor_galleries")
    artist_counts = _count_history_values(history, "anchor_artists")
    penalized: List[dict] = []
    for row in rows:
        fair = str(row.get("fair_label") or row.get("fair_slug") or "").strip()
        gallery = str(row.get("gallery") or "").strip()
        artist = str(row.get("artist_name") or "").strip() if kind == "artist" else ""
        penalty = 0
        penalty += fair_counts.get(fair, 0) * 1
        penalty += gallery_counts.get(gallery, 0) * 2
        if artist:
            penalty += artist_counts.get(artist, 0) * 2

        updated = dict(row)
        updated["_reuse_penalty"] = penalty
        updated["_rank_score"] = int(updated.get("_score", 0)) * 10 - penalty
        penalized.append(updated)
    return penalized


def _select_evidence_with_rotation(
    rows: List[dict],
    limit: int,
    cross_fair_mode: bool,
    broad_query_mode: bool,
    rotation_index: int,
    recent_broad_history: List[dict] | None = None,
    kind: str = "",
) -> List[dict]:
    if not rows or limit <= 0:
        return []

    working_rows = rows
    pool_limit = limit
    per_fair_gallery_cap = 2
    if broad_query_mode:
        pool_limit = min(len(rows), max(limit * 3, limit + 8))
        if cross_fair_mode:
            per_fair_gallery_cap = 1
        if recent_broad_history:
            working_rows = _apply_broad_history_penalty(rows, recent_broad_history, kind=kind)

    selected = _pick_top_by_score(
        working_rows,
        pool_limit,
        prefer_cross_fair_diversity=cross_fair_mode,
        per_fair_gallery_cap=per_fair_gallery_cap,
    )
    if cross_fair_mode:
        selected = _order_cross_fair_rows(selected)
    if broad_query_mode:
        selected = _rotate_rows(selected, rotation_index)
    return selected[:limit]


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
    rotation_index: int = 0,
    recent_broad_history: List[dict] | None = None,
) -> Dict[str, object]:
    fair_slugs = set(resolve_fair_slugs(fair_label))
    cross_fair_mode = len(fair_slugs) > 1
    tokens = _tokenize_query(question_text)
    broad_query_mode = _is_broad_query(question_text, tokens)
    safe_rotation_index = max(0, int(rotation_index or 0))
    warnings: List[str] = []

    ex_data = load_exhibition_records_readonly()
    ar_data = load_artist_records_readonly()
    warnings.extend(ex_data.warnings)
    warnings.extend(ar_data.warnings)

    art_pulse_snapshot, art_pulse_warnings = _resolve_art_pulse_snapshot(fair_label)
    warnings.extend(art_pulse_warnings)

    exhibitions = [r for r in ex_data.records if str(r.get("fair_slug") or "") in fair_slugs]
    artists = [r for r in ar_data.records if str(r.get("fair_slug") or "") in fair_slugs]
    exhibitions, exhibitions_latest_year = _filter_latest_available_year_rows(exhibitions)
    artists, artists_latest_year = _filter_latest_available_year_rows(artists)

    available_years = [y for y in [exhibitions_latest_year, artists_latest_year] if y is not None]
    reference_year = max(available_years) if available_years else 2025
    reference_year_display = str(reference_year)
    if exhibitions_latest_year and artists_latest_year and exhibitions_latest_year != artists_latest_year:
        reference_year_display = f"Exhibitions:{exhibitions_latest_year} / Artists:{artists_latest_year}"
        warnings.append(
            f"advisor_latest_year_split: exhibitions={exhibitions_latest_year}, artists={artists_latest_year}"
        )

    exhibition_rows: List[dict] = []
    for row in exhibitions:
        row_year = _coerce_year(row.get("year"))
        if row_year is None:
            row_year = exhibitions_latest_year if exhibitions_latest_year is not None else reference_year
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
            "image_preview": str(row.get("image_preview") or "").strip(),
            "image_preview_r2_key": str(row.get("image_preview_r2_key") or "").strip(),
            "year": row_year,
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
        row_year = _coerce_year(row.get("year"))
        if row_year is None:
            row_year = artists_latest_year if artists_latest_year is not None else reference_year
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
            "artist_image_preview_candidates": list(row.get("artist_image_preview_candidates") or []),
            "year": row_year,
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

    exhibition_evidence = _select_evidence_with_rotation(
        ex_scored,
        text_limit_per_kind,
        cross_fair_mode=cross_fair_mode,
        broad_query_mode=broad_query_mode,
        rotation_index=safe_rotation_index,
        recent_broad_history=recent_broad_history,
        kind="exhibition",
    )
    artist_evidence = _select_evidence_with_rotation(
        ar_scored,
        text_limit_per_kind,
        cross_fair_mode=cross_fair_mode,
        broad_query_mode=broad_query_mode,
        rotation_index=safe_rotation_index,
        recent_broad_history=recent_broad_history,
        kind="artist",
    )

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
    evidence_rows = _build_evidence_rows(exhibition_evidence, artist_evidence, limit_per_kind=8)

    ex_enrichment_path, ex_enrichment_kind = resolve_current_first_enrichment_output_path("exhibitions")
    ar_enrichment_path, ar_enrichment_kind = resolve_current_first_enrichment_output_path("artists")

    return {
        "selection": {
            "fair_label": fair_label,
            "year": reference_year,
            "reference_year_display": reference_year_display,
            "tokens": tokens,
            "cross_fair_mode": cross_fair_mode,
            "broad_query_mode": broad_query_mode,
            "rotation_index": safe_rotation_index,
            "recent_broad_history": list(recent_broad_history or [])[-8:],
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
        "evidence_rows": evidence_rows,
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
            "When year metadata exists, Advisor uses latest available year rows only. "
            "Broad-query mode uses a lightweight evidence rotation to reduce fixed candidate repetition. "
            "Art Pulse overview is attached as a read-only snapshot. "
            "history is not used as a default query path."
        ),
    }
