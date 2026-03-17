from __future__ import annotations

import re
from typing import Dict, List

from phase1_artist_link_utils import is_invalid_artist_name
from phase2_art_pulse_readonly import build_art_pulse_overview
from phase2_artist_search_readonly import load_artist_records_readonly
from phase2_common_readonly import normalize_url, resolve_current_first_enrichment_output_path, resolve_fair_slugs
from phase2_exhibition_search_readonly import load_exhibition_records_readonly


def _tokenize_query(query_text: str) -> List[str]:
    tokens: List[str] = []
    seen = set()

    def _push(token: str) -> None:
        low = str(token or "").strip().lower()
        if len(low) < 2 or len(low) > 24 or low in seen:
            return
        seen.add(low)
        tokens.append(low)

    q = (query_text or "").strip()
    for token in re.split(r"[\s,、。|;:()\[\]{}]+", q):
        _push(token)
    for token in re.findall(r"[一-龯]{2,4}|[ァ-ンー]{2,12}|[a-z]{3,12}", q.lower()):
        _push(token)
    return tokens[:20]


def _is_broad_query(question_text: str, tokens: List[str]) -> bool:
    q = (question_text or "").strip().lower()
    if not q:
        return False
    starter_hints = ["どんな", "何を", "なにを", "どう", "どうやって"]
    ideation_hints = [
        "考え方",
        "発想",
        "問い",
        "設計",
        "立てる",
        "見せたい",
        "強くしたい",
        "感じさせたい",
        "意味を変えたい",
        "したくない",
    ]
    if not any(hint in q for hint in starter_hints) and not any(hint in q for hint in ideation_hints):
        return False
    narrow_hints = [
        "この作家",
        "この展示",
        "この作品",
        "誰を見る",
        "作家を教えて",
        "artist to watch",
        "which artist",
    ]
    if any(hint in q for hint in narrow_hints):
        return False
    return len(tokens) <= 18 and len(q) <= 90


def _score_text(haystack: str, tokens: List[str]) -> int:
    if not tokens:
        return 0
    low = (haystack or "").lower()
    return sum(2 if len(t) >= 3 else 1 for t in tokens if t in low)


def _is_ideation_query(question_text: str) -> bool:
    q = (question_text or "").strip().lower()
    if not q:
        return False
    hints = [
        "考え方",
        "発想",
        "問い",
        "設計",
        "導線",
        "動線",
        "順番",
        "距離",
        "どうするといい",
        "どう考える",
        "どう発想",
        "どう問い",
        "見せたい",
        "強くしたい",
        "感じさせたい",
        "意味を変えたい",
    ]
    return any(hint in q for hint in hints)


def _page_description_score(text: str) -> int:
    low = (text or "").lower()
    if not low:
        return 0
    markers = [
        "installation view",
        "gallery view",
        "view of the exhibition",
        "会場の様子",
        "展示風景",
        "インスタレーションビュー",
        "掲載され",
        "掲載ページ",
        "複数写真",
        "ウェブページ",
        "overview page",
        "プレスリリース",
        "press release",
        "photo documentation",
        "documentation",
    ]
    return sum(1 for marker in markers if marker in low)


INTENT_FOCUS_ORDER = (
    "video",
    "sound",
    "sculpture",
    "photography",
    "painting",
    "spatial",
    "performance",
    "concept",
    "material",
    "color",
    "artist",
)

INTENT_FOCUS_HINTS = {
    "video": [
        "映像",
        "動画",
        "ビデオ",
        "video",
        "film",
        "projection",
        "moving image",
        "アニメーション",
        "animation",
        "screen",
        "上映",
        "映写",
    ],
    "sound": [
        "音",
        "sound",
        "audio",
        "acoustic",
        "sonic",
        "listening",
        "noise",
        "voice",
        "vibration",
        "録音",
    ],
    "sculpture": [
        "彫刻",
        "sculpture",
        "立体",
        "object",
        "ceramic",
        "ceramics",
        "clay",
        "陶",
        "陶器",
        "オブジェ",
        "物体",
    ],
    "photography": [
        "写真",
        "photography",
        "photo",
        "photographic",
        "staged",
        "fiction",
        "fictional",
        "虚構",
        "演出写真",
        "イメージ",
    ],
    "painting": [
        "絵画",
        "painting",
        "paint",
        "canvas",
        "油彩",
        "油絵",
        "acrylic",
        "アクリル",
        "絵具",
    ],
    "spatial": [
        "インスタレーション",
        "installation",
        "展示空間",
        "spatial",
        "site-specific",
        "site specific",
        "導線",
        "動線",
        "歩かせ",
        "歩く",
        "空間",
        "room",
        "architecture",
    ],
    "performance": [
        "パフォーマンス",
        "performance",
        "lecture-performance",
        "lecture performance",
        "身体",
        "body",
        "gesture",
        "choreography",
        "行為",
        "朗読",
    ],
    "concept": [
        "コンセプト",
        "concept",
        "テーマ",
        "主題",
        "着想",
        "発想",
        "思想",
        "問い",
        "問題意識",
    ],
    "material": [
        "素材",
        "マテリアル",
        "material",
        "質感",
        "手触り",
        "布",
        "木",
        "紙",
        "金属",
    ],
    "color": [
        "色",
        "カラー",
        "色彩",
        "配色",
        "トーン",
        "彩度",
        "明度",
        "グレー",
        "鮮やか",
    ],
    "artist": [
        "artist",
        "アーティスト",
        "作家",
        "誰",
        "who",
    ],
}

STRICT_INTENT_FOCI = {"video", "sound", "sculpture", "photography", "painting", "spatial", "performance"}


def _intent_signal_score(text: str, focus: str) -> int:
    low = (text or "").lower()
    return sum(1 for hint in INTENT_FOCUS_HINTS.get(focus, []) if hint and hint in low)


def _detect_intent_focus(question_text: str, tokens: List[str]) -> str:
    q = (question_text or "").strip().lower()
    if not q:
        return ""
    best_focus = ""
    best_score = 0
    token_set = {str(token or "").strip().lower() for token in tokens[:12] if len(str(token or "").strip()) >= 3}
    for focus in INTENT_FOCUS_ORDER:
        score = _intent_signal_score(q, focus)
        if token_set:
            score += sum(1 for hint in INTENT_FOCUS_HINTS.get(focus, []) if hint in token_set)
        if score > best_score:
            best_focus = focus
            best_score = score
    return best_focus if best_score > 0 else ""


def _trim_rows_by_intent(
    rows: List[dict],
    intent_focus: str,
    limit: int,
    warnings: List[str],
    warning_tag: str,
) -> tuple[List[dict], int]:
    if intent_focus not in STRICT_INTENT_FOCI or not rows:
        return rows, limit

    ordered = sorted(
        rows,
        key=lambda r: (
            -int(r.get("_intent_score", 0)),
            -int(r.get("_score", 0)),
            str(r.get("artist_name") or r.get("title") or ""),
            str(r.get("source_url") or ""),
        ),
    )
    strong = [row for row in ordered if int(row.get("_intent_score", 0)) >= 2]
    weak = [row for row in ordered if int(row.get("_intent_score", 0)) == 1]
    keep_cap = max(1, min(limit, 3))

    if strong:
        kept = strong[:keep_cap]
        if len(kept) < keep_cap:
            kept.extend(weak[: keep_cap - len(kept)])
        return kept, max(1, min(limit, len(kept)))

    if weak:
        kept = weak[:keep_cap]
        warnings.append(f"{warning_tag}_intent_medium_confidence: weak_{intent_focus}_signals_only")
        return kept, max(1, min(limit, len(kept)))

    warnings.append(f"{warning_tag}_intent_low_confidence: no_{intent_focus}_signal")
    return ordered[:1], 1


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
    intent_focus: str = "",
) -> List[dict]:
    focus_history = [
        item for item in history if not intent_focus or str(item.get("intent_focus") or "").strip() == intent_focus
    ]
    history_pool = focus_history or history
    fair_counts = _count_history_values(history_pool, "anchor_fairs")
    gallery_counts = _count_history_values(history_pool, "anchor_galleries")
    artist_counts = _count_history_values(history_pool, "anchor_artists")
    selected_gallery_counts = _count_history_values(history_pool, "selected_galleries")
    selected_artist_counts = _count_history_values(history_pool, "selected_artists")
    selected_title_counts = _count_history_values(history_pool, "selected_titles")
    focus_multiplier = 2 if focus_history and intent_focus else 1
    penalized: List[dict] = []
    for row in rows:
        fair = str(row.get("fair_label") or row.get("fair_slug") or "").strip()
        gallery = str(row.get("gallery") or "").strip()
        artist = str(row.get("artist_name") or "").strip() if kind == "artist" else ""
        title = str(row.get("title") or "").strip() if kind == "exhibition" else ""
        penalty = 0
        penalty += fair_counts.get(fair, 0) * focus_multiplier
        penalty += gallery_counts.get(gallery, 0) * (2 * focus_multiplier)
        penalty += selected_gallery_counts.get(gallery, 0) * (4 * focus_multiplier)
        if title:
            penalty += selected_title_counts.get(title, 0) * (6 * focus_multiplier)
        if artist:
            penalty += artist_counts.get(artist, 0) * (2 * focus_multiplier)
            penalty += selected_artist_counts.get(artist, 0) * (6 * focus_multiplier)

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
    intent_focus: str = "",
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
            working_rows = _apply_broad_history_penalty(rows, recent_broad_history, kind=kind, intent_focus=intent_focus)

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
    ideation_query = _is_ideation_query(question_text)
    intent_focus = _detect_intent_focus(question_text, tokens)
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
        intent_score = _intent_signal_score(hay, intent_focus) if intent_focus else 0
        page_score = _page_description_score(hay)
        candidate["_intent_score"] = intent_score
        candidate["_page_description_score"] = page_score
        candidate["_score"] = _score_text(hay, tokens) + (intent_score * 3) - (page_score * 2 if ideation_query else 0)
        exhibition_rows.append(candidate)

    artist_rows: List[dict] = []
    for row in artists:
        artist_name = str(row.get("artist_name") or "").strip()
        if is_invalid_artist_name(artist_name):
            continue
        row_year = _coerce_year(row.get("year"))
        if row_year is None:
            row_year = artists_latest_year if artists_latest_year is not None else reference_year
        candidate = {
            "kind": "artist",
            "fair_slug": str(row.get("fair_slug") or ""),
            "fair_label": str(row.get("fair_label") or ""),
            "gallery": str(row.get("gallery_name") or ""),
            "artist_name": artist_name,
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
        intent_score = _intent_signal_score(hay, intent_focus) if intent_focus else 0
        page_score = _page_description_score(hay)
        candidate["_intent_score"] = intent_score
        candidate["_page_description_score"] = page_score
        candidate["_score"] = _score_text(hay, tokens) + (intent_score * 3) - (page_score * 2 if ideation_query else 0)
        artist_rows.append(candidate)

    matched_exhibition_count = len([r for r in exhibition_rows if int(r.get("_score", 0)) > 0])
    matched_artist_count = len([r for r in artist_rows if int(r.get("_score", 0)) > 0])
    if tokens:
        ex_scored = [r for r in exhibition_rows if int(r.get("_score", 0)) > 0] or exhibition_rows
        ar_scored = [r for r in artist_rows if int(r.get("_score", 0)) > 0] or artist_rows
    else:
        ex_scored = exhibition_rows
        ar_scored = artist_rows

    exhibition_limit_per_kind = text_limit_per_kind
    artist_limit_per_kind = text_limit_per_kind
    ex_scored, exhibition_limit_per_kind = _trim_rows_by_intent(
        ex_scored,
        intent_focus,
        exhibition_limit_per_kind,
        warnings,
        "advisor_exhibition",
    )
    ar_scored, artist_limit_per_kind = _trim_rows_by_intent(
        ar_scored,
        intent_focus,
        artist_limit_per_kind,
        warnings,
        "advisor_artist",
    )

    exhibition_evidence = _select_evidence_with_rotation(
        ex_scored,
        exhibition_limit_per_kind,
        cross_fair_mode=cross_fair_mode,
        broad_query_mode=broad_query_mode,
        rotation_index=safe_rotation_index,
        recent_broad_history=recent_broad_history,
        kind="exhibition",
        intent_focus=intent_focus,
    )
    artist_evidence = _select_evidence_with_rotation(
        ar_scored,
        artist_limit_per_kind,
        cross_fair_mode=cross_fair_mode,
        broad_query_mode=broad_query_mode,
        rotation_index=safe_rotation_index,
        recent_broad_history=recent_broad_history,
        kind="artist",
        intent_focus=intent_focus,
    )

    for row in exhibition_evidence:
        row.pop("_score", None)
        row.pop("_intent_score", None)
    for row in artist_evidence:
        row.pop("_score", None)
        row.pop("_intent_score", None)

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
            "ideation_query": ideation_query,
            "intent_focus": intent_focus,
            "artist_intent_focus": intent_focus,
            "rotation_index": safe_rotation_index,
            "recent_broad_history": list(recent_broad_history or [])[-8:],
            "grounded_anchor_count": matched_exhibition_count + matched_artist_count,
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
