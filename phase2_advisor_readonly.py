from __future__ import annotations

import hashlib
import random
import re
from typing import Dict, List

from phase1_artist_link_utils import is_invalid_artist_name
from phase2_art_pulse_readonly import build_art_pulse_overview
from phase2_artist_search_readonly import load_artist_records_readonly
from phase2_common_readonly import normalize_url, resolve_current_first_enrichment_output_path, resolve_fair_slugs
from phase2_exhibition_search_readonly import load_exhibition_records_readonly


def _score_text(haystack: str, tokens: List[str]) -> int:
    if not tokens:
        return 0
    low = (haystack or "").lower()
    return sum(2 if len(t) >= 3 else 1 for t in tokens if t in low)


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


def _resolve_gallery_cohort_index(
    cohort_map: Dict[str, int],
    fair_slug: str,
    gallery: str,
    source_url: str,
) -> int:
    fair_key = str(fair_slug or "").strip().lower()
    gallery_key = str(gallery or "").strip().lower()
    source_key = normalize_url(str(source_url or ""))
    key = f"{fair_key}::{gallery_key}" if fair_key and gallery_key else source_key
    if not key:
        return -1
    cohort_index = cohort_map.get(key)
    if cohort_index is None:
        cohort_index = len(cohort_map)
        cohort_map[key] = cohort_index
    return cohort_index


def _cohort_penalty_value(cohort_index: int, intent_focus: str = "") -> int:
    if cohort_index < 0:
        return 0
    if intent_focus in {"concept", "material", "color", "spatial"}:
        return max(0, 18 - (min(cohort_index, 9) * 2))
    return max(0, 10 - min(cohort_index, 9))


def _apply_broad_cohort_penalty(rows: List[dict], intent_focus: str = "") -> List[dict]:
    penalized: List[dict] = []
    for row in rows:
        penalty = _cohort_penalty_value(
            int(row.get("_gallery_cohort_index")) if row.get("_gallery_cohort_index") is not None else -1,
            intent_focus=intent_focus,
        )
        updated = dict(row)
        updated["_reuse_penalty"] = int(updated.get("_reuse_penalty", 0) or 0) + penalty
        updated["_rank_score"] = int(updated.get("_score", 0)) * 10 - int(updated.get("_reuse_penalty", 0) or 0)
        penalized.append(updated)
    return penalized


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
        updated["_reuse_penalty"] = int(updated.get("_reuse_penalty", 0) or 0) + penalty
        updated["_rank_score"] = int(updated.get("_score", 0)) * 10 - int(updated.get("_reuse_penalty", 0) or 0)
        penalized.append(updated)
    return penalized


def _select_evidence_with_rotation(
    rows: List[dict],
    limit: int,
    cross_fair_mode: bool,
    broad_query_mode: bool,
    rotation_index: int,
    diversity_seed: int = 0,
    recent_broad_history: List[dict] | None = None,
    kind: str = "",
    intent_focus: str = "",
) -> List[dict]:
    if not rows or limit <= 0:
        return []

    working_rows = rows
    pool_limit = limit
    per_fair_gallery_cap = 2
    broad_pool_limit = 100
    if broad_query_mode:
        pool_limit = min(len(rows), max(broad_pool_limit, limit * 3, limit + 8))
        if cross_fair_mode:
            per_fair_gallery_cap = 1
        if recent_broad_history:
            working_rows = _apply_broad_history_penalty(rows, recent_broad_history, kind=kind, intent_focus=intent_focus)
        working_rows = _apply_broad_cohort_penalty(working_rows, intent_focus=intent_focus)

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
        if selected and int(diversity_seed or 0) != 0:
            seed_value = abs(int(diversity_seed))
            rng = random.Random(
                f"{seed_value}:{kind}:{cross_fair_mode}:{intent_focus}:{rotation_index}:{len(selected)}"
            )
            top_pool = list(selected[: min(len(selected), broad_pool_limit)])
            rank_map = {id(row): idx for idx, row in enumerate(top_pool)}
            sampled: List[dict] = []
            gallery_counts: Dict[str, int] = {}
            artist_counts: Dict[str, int] = {}
            source_seen: set[str] = set()
            gallery_cap = 2 if kind == "artist" else 1
            artist_cap = 1

            def _eligible(row: dict, strict: bool) -> bool:
                source = normalize_url(str(row.get("source_url") or ""))
                gallery = str(row.get("gallery") or "").strip()
                artist = str(row.get("artist_name") or "").strip() if kind == "artist" else ""
                if source and source in source_seen:
                    return False
                if strict and gallery and gallery_counts.get(gallery, 0) >= gallery_cap:
                    return False
                if strict and artist and artist_counts.get(artist, 0) >= artist_cap:
                    return False
                return True

            while top_pool and len(sampled) < limit:
                candidates = [row for row in top_pool if _eligible(row, strict=True)]
                if not candidates:
                    candidates = [row for row in top_pool if _eligible(row, strict=False)]
                if not candidates:
                    break
                weighted = sorted(
                    candidates,
                    key=lambda row: (rank_map.get(id(row), 0), rng.random()),
                )
                pick_band = max(1, min(len(weighted), max(4, len(weighted) // 5)))
                picked = weighted[rng.randrange(pick_band)]
                sampled.append(picked)
                top_pool.remove(picked)
                source = normalize_url(str(picked.get("source_url") or ""))
                gallery = str(picked.get("gallery") or "").strip()
                artist = str(picked.get("artist_name") or "").strip() if kind == "artist" else ""
                if source:
                    source_seen.add(source)
                if gallery:
                    gallery_counts[gallery] = gallery_counts.get(gallery, 0) + 1
                if artist:
                    artist_counts[artist] = artist_counts.get(artist, 0) + 1

            if len(sampled) < limit:
                for row in selected:
                    if row in sampled:
                        continue
                    sampled.append(row)
                    if len(sampled) >= limit:
                        break
            selected = sampled
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


_QUERY_SPLIT_RE = re.compile(r"[\s,;:()\[\]{}\/\\|]+")
_JA_PARTICLE_SPLIT_RE = re.compile(
    r"(?:[\u3000\u3001\u3002\u30fb\u30fb\uff0c\uff0e\uff1f\uff01]|"
    r"(?<=[\u3041-\u3096\u30a1-\u30ff\u4e00-\u9fff])(?:\u306e|\u3092|\u306b|\u3078|\u3068|\u3067|\u304c|\u306f|\u3082|\u3084|\u304b\u3089|\u307e\u3067|"
    r"\u3068\u304b|\u306a\u3069|\u3088\u308a|\u307b\u304b))"
)
_ASCII_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9'._-]{1,23}")
_JA_CORE_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]{2,6}|[\u30a1-\u30ff\u30fc]{2,12}")
_JA_SEGMENT_RE = re.compile(r"[\u3041-\u3096\u30a1-\u30ff\u30fc\u4e00-\u9fff]{2,24}")
_QUERY_TOKEN_STOPWORDS = {
    "\u3042\u308a",
    "\u3044\u3044",
    "\u3044\u3044\u304b",
    "\u3044\u304f\u3064\u304b",
    "\u304a\u3057\u3048\u3066",
    "\u3053\u306e",
    "\u3053\u3068",
    "\u3057\u305f\u3044",
    "\u3057\u3088\u3046",
    "\u3059\u308b",
    "\u305f\u3081",
    "\u3069\u3046",
    "\u3069\u3053",
    "\u3069\u3093\u306a",
    "\u306a\u308b",
    "\u306b\u3064\u3044\u3066",
    "\u307b\u3057\u3044",
    "\u307e\u3059",
    "\u3082\u306e",
    "\u3088\u3046",
    "\u308f\u304b\u308b",
    "\u6559\u3048\u3066",
    "\u77e5\u308a\u305f\u3044",
}


def _tokenize_query(query_text: str) -> List[str]:
    q = str(query_text or "").strip()
    if not q:
        return []

    tokens: List[str] = []
    seen = set()

    def _push(token: str) -> None:
        low = str(token or "").strip().lower()
        if not low or low in seen or low in _QUERY_TOKEN_STOPWORDS:
            return
        if len(low) > 24:
            low = low[:24]
        if len(low) < 2 and not re.fullmatch(r"[\u4e00-\u9fff]", low):
            return
        seen.add(low)
        tokens.append(low)

    for part in _QUERY_SPLIT_RE.split(q):
        text = str(part or "").strip()
        if not text:
            continue
        _push(text)
        for segment in _JA_PARTICLE_SPLIT_RE.split(text):
            chunk = str(segment or "").strip()
            if not chunk:
                continue
            _push(chunk)
            for token in _JA_CORE_TOKEN_RE.findall(chunk):
                _push(token)
        for token in _ASCII_TOKEN_RE.findall(text.lower()):
            _push(token)

    for segment in _JA_SEGMENT_RE.findall(q):
        for chunk in _JA_PARTICLE_SPLIT_RE.split(segment):
            text = str(chunk or "").strip()
            if not text:
                continue
            _push(text)
            for token in _JA_CORE_TOKEN_RE.findall(text):
                _push(token)

    return tokens[:20]


def _is_broad_query(question_text: str, tokens: List[str]) -> bool:
    raw_q = (question_text or "").strip()
    q = raw_q.lower()
    if not q:
        return False
    specific_suffixes = ["について", "の作品", "を見たい", "教えて", "知りたい"]
    looks_like_latin_name = bool(
        re.search(r"[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ'’\-.]+(?:\s+[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ'’\-.]+)+", raw_q)
    )
    looks_like_kana_name = bool(re.search(r"[ァ-ヴー]{2,}(?:[・･\s][ァ-ヴー]{2,})+", raw_q))
    if (looks_like_latin_name or looks_like_kana_name) and any(token in raw_q for token in specific_suffixes):
        return False
    starter_hints = [
        "\u3069\u3093\u306a",
        "\u3069\u3046",
        "\u306a\u306b",
        "\u4f55\u3092",
        "\u4f55\u304c",
        "\u6559\u3048\u3066",
        "\u304a\u3057\u3048\u3066",
        "\u77e5\u308a\u305f\u3044",
        "what kind of",
        "which direction",
        "how should",
    ]
    ideation_hints = [
        "\u8003\u3048\u65b9",
        "\u767a\u60f3",
        "\u554f\u3044",
        "\u8a2d\u8a08",
        "\u65b9\u5411",
        "\u53c2\u8003",
        "\u30b3\u30f3\u30bb\u30d7\u30c8",
        "\u4f5c\u54c1\u30b3\u30f3\u30bb\u30d7\u30c8",
        "\u7d20\u6750",
        "\u9078\u3073\u65b9",
        "\u6bd4\u8f03",
        "\u8907\u6570",
        "\u3044\u304f\u3064\u304b",
        "\u9762\u767d\u3044",
        "\u304a\u3082\u3057\u308d\u3044",
        "\u898b\u305b\u305f\u3044",
        "\u5f37\u304f\u3057\u305f\u3044",
        "\u611f\u3058\u3055\u305b\u305f\u3044",
        "idea",
        "reference",
        "compare",
    ]
    if not any(hint in q for hint in starter_hints) and not any(hint in q for hint in ideation_hints):
        return False
    narrow_hints = [
        "\u3053\u306e\u4f5c\u5bb6",
        "\u3053\u306e\u4f5c\u54c1",
        "\u3053\u306e\u5c55\u793a",
        "\u8ab0\u3092\u898b\u308b",
        "artist to watch",
        "which artist",
        "who is",
    ]
    if any(hint in q for hint in narrow_hints):
        return False
    return len(tokens) <= 18 and len(q) <= 120


def _is_ideation_query(question_text: str) -> bool:
    q = (question_text or "").strip().lower()
    if not q:
        return False
    hints = [
        "\u8003\u3048\u65b9",
        "\u767a\u60f3",
        "\u554f\u3044",
        "\u8a2d\u8a08",
        "\u69cb\u6210",
        "\u30b3\u30f3\u30bb\u30d7\u30c8",
        "\u4f5c\u54c1\u30b3\u30f3\u30bb\u30d7\u30c8",
        "\u7d20\u6750",
        "\u9078\u3073\u65b9",
        "\u65b9\u5411",
        "\u898b\u305b\u305f\u3044",
        "\u5f37\u304f\u3057\u305f\u3044",
        "\u611f\u3058\u3055\u305b\u305f\u3044",
        "\u610f\u5473\u3092\u5909\u3048\u305f\u3044",
        "\u53c2\u8003",
        "\u9762\u767d\u3044",
        "\u304a\u3082\u3057\u308d\u3044",
        "\u3069\u3046\u3059\u308b\u3068\u3044\u3044",
        "\u3069\u3046\u8003\u3048\u308b",
        "\u7a7a\u9593\u5168\u4f53",
        "idea",
        "concept",
        "direction",
        "reference",
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
        "\u4f1a\u5834\u306e\u69d8\u5b50",
        "\u5c55\u793a\u98a8\u666f",
        "\u30a4\u30f3\u30b9\u30bf\u30ec\u30fc\u30b7\u30e7\u30f3\u30d3\u30e5\u30fc",
        "\u63b2\u8f09\u30da\u30fc\u30b8",
        "\u6982\u8981\u30da\u30fc\u30b8",
        "overview page",
        "\u30d7\u30ec\u30b9\u30ea\u30ea\u30fc\u30b9",
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
    "video": ["\u6620\u50cf", "\u52d5\u753b", "\u30d3\u30c7\u30aa", "video", "film", "projection", "moving image", "\u4e0a\u6620", "\u6620\u5199", "animation"],
    "sound": ["\u97f3", "sound", "audio", "acoustic", "sonic", "listening", "noise", "voice", "vibration", "\u9332\u97f3"],
    "sculpture": ["\u5f6b\u523b", "sculpture", "\u7acb\u4f53", "object", "ceramic", "ceramics", "clay", "\u9676", "\u9676\u5668", "\u30aa\u30d6\u30b8\u30a7", "\u7269\u4f53"],
    "photography": ["\u5199\u771f", "photography", "photo", "photographic", "staged", "fiction", "fictional", "\u865a\u69cb", "\u6f14\u51fa\u5199\u771f", "\u30a4\u30e1\u30fc\u30b8"],
    "painting": ["\u7d75\u753b", "painting", "paint", "canvas", "\u6cb9\u5f69", "\u6cb9\u7d75", "acrylic", "\u30a2\u30af\u30ea\u30eb", "\u7d75\u5177"],
    "spatial": ["\u30a4\u30f3\u30b9\u30bf\u30ec\u30fc\u30b7\u30e7\u30f3", "installation", "\u5c55\u793a\u7a7a\u9593", "spatial", "site-specific", "site specific", "\u5c0e\u7dda", "\u52d5\u7dda", "\u6b69\u304b\u305b", "\u7a7a\u9593", "room", "architecture"],
    "performance": ["\u30d1\u30d5\u30a9\u30fc\u30de\u30f3\u30b9", "performance", "lecture-performance", "lecture performance", "\u8eab\u4f53", "body", "gesture", "choreography", "\u884c\u70ba", "\u6717\u8aad"],
    "concept": ["\u30b3\u30f3\u30bb\u30d7\u30c8", "concept", "\u30c6\u30fc\u30de", "\u4e3b\u984c", "\u7740\u60f3", "\u767a\u60f3", "\u601d\u60f3", "\u554f\u3044", "\u554f\u984c\u610f\u8b58", "\u8003\u3048\u65b9", "\u610f\u5473"],
    "material": ["\u7d20\u6750", "\u6750", "\u30de\u30c6\u30ea\u30a2\u30eb", "material", "\u8cea\u611f", "\u624b\u89e6\u308a", "\u5e03", "\u7d19", "\u6728", "\u91d1\u5c5e", "\u6a39\u8102", "\u30d5\u30a3\u30eb\u30e0", "\u5c64"],
    "color": ["\u8272", "\u30ab\u30e9\u30fc", "\u8272\u5f69", "\u914d\u8272", "\u8272\u8abf", "\u30c8\u30fc\u30f3", "\u660e\u5ea6", "\u5f69\u5ea6", "\u30b0\u30ec\u30fc", "\u9752", "\u8d64", "\u9ec4", "\u7dd1", "\u9ed2", "\u767d"],
    "artist": ["artist", "\u30a2\u30fc\u30c6\u30a3\u30b9\u30c8", "\u4f5c\u5bb6", "\u8ab0", "who"],
}

STRICT_INTENT_FOCI = {"video", "sound", "sculpture", "photography", "painting", "spatial", "performance"}


def _intent_signal_score(text: str, focus: str) -> int:
    low = (text or "").lower()
    return sum(1 for hint in INTENT_FOCUS_HINTS.get(focus, []) if hint and hint in low)


def _normalize_broad_intent_score(intent_score: int, intent_focus: str, broad_query_mode: bool, ideation_query: bool) -> int:
    if intent_score <= 0:
        return 0
    if broad_query_mode and (ideation_query or intent_focus in {"concept", "material", "color", "spatial"}):
        return min(intent_score, 2)
    return intent_score


def _candidate_quality_score(row: dict) -> int:
    score = 0
    if str(row.get("summary_ja") or "").strip():
        score += 3
    if str(row.get("headline_ja") or "").strip():
        score += 2
    if str(row.get("text") or "").strip():
        score += min(4, max(1, len(str(row.get("text") or "").strip()) // 280))
    if str(row.get("kind") or "").strip() == "exhibition":
        if str(row.get("image_preview") or "").strip() or str(row.get("image_preview_r2_key") or "").strip():
            score += 1
    elif list(row.get("artist_image_preview_candidates") or []):
        score += 1
    if int(row.get("_page_description_score", 0) or 0) <= 0:
        score += 1
    return score


def _question_tiebreak_value(question_text: str, row: dict) -> int:
    seed = "\n".join(
        [
            str(question_text or "").strip().lower(),
            str(row.get("kind") or "").strip().lower(),
            str(row.get("fair_slug") or row.get("fair_label") or "").strip().lower(),
            str(row.get("gallery") or "").strip().lower(),
            str(row.get("artist_name") or row.get("title") or "").strip().lower(),
            normalize_url(str(row.get("source_url") or "")),
        ]
    )
    digest = hashlib.blake2b(seed.encode("utf-8", "ignore"), digest_size=8).digest()
    return int.from_bytes(digest, "big")


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
            -int(r.get("_quality_score", 0)),
            int(r.get("_query_tiebreak", 0)),
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
            -int(r.get("_quality_score", 0)),
            -int(r.get("_gallery_cohort_index", -1)),
            int(r.get("_query_tiebreak", 0)),
            str(r.get("source_url") or ""),
        ),
    )
    if not prefer_cross_fair_diversity or limit <= 1:
        return sorted_rows[:limit]

    selected: List[dict] = []
    selected_ids: set[int] = set()
    fair_seen: set[str] = set()
    gallery_counts: Dict[tuple[str, str], int] = {}

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

    for idx, row in enumerate(sorted_rows):
        if idx in selected_ids:
            continue
        selected.append(row)
        if len(selected) >= limit:
            return selected
    return selected


def _reference_key_from_row(row: dict, kind: str) -> str:
    source_key = normalize_url(str(row.get("source_url") or ""))
    if source_key:
        return f"{kind}::{source_key}"
    label = str(row.get("artist_name") if kind == "artist" else row.get("title") or "").strip().lower()
    fair = str(row.get("fair_label") or row.get("fair_slug") or "").strip().lower()
    gallery = str(row.get("gallery") or "").strip().lower()
    return f"{kind}::{fair}::{gallery}::{label}"


def _sample_broad_main_references(
    question_text: str,
    ex_rows: List[dict],
    ar_rows: List[dict],
    cross_fair_mode: bool,
    intent_focus: str,
    diversity_seed: int,
    recent_reference_keys: List[str] | None = None,
    target_count: int = 4,
    pool_limit: int = 100,
) -> List[dict]:
    if target_count <= 0:
        return []
    seed_value = abs(int(diversity_seed or 0))
    if seed_value <= 0:
        return []

    q = str(question_text or "").strip().lower()
    asks_artist = any(token in q for token in ["作家", "artist", "アーティスト", "who", "誰"])
    asks_exhibition = any(token in q for token in ["展示", "exhibition", "インスタレーション", "空間"])

    per_fair_gallery_cap = 1 if cross_fair_mode else 2
    ex_pool = _pick_top_by_score(
        ex_rows,
        min(len(ex_rows), pool_limit),
        prefer_cross_fair_diversity=cross_fair_mode,
        per_fair_gallery_cap=per_fair_gallery_cap,
    )
    ar_pool = _pick_top_by_score(
        ar_rows,
        min(len(ar_rows), pool_limit),
        prefer_cross_fair_diversity=cross_fair_mode,
        per_fair_gallery_cap=per_fair_gallery_cap,
    )

    ex_candidates = [
        {
            "kind": "exhibition",
            "row": row,
            "rank": idx,
            "key": _reference_key_from_row(row, "exhibition"),
        }
        for idx, row in enumerate(ex_pool, start=1)
    ]
    ar_candidates = [
        {
            "kind": "artist",
            "row": row,
            "rank": idx,
            "key": _reference_key_from_row(row, "artist"),
        }
        for idx, row in enumerate(ar_pool, start=1)
    ]

    interleaved: List[dict] = []
    if asks_artist and not asks_exhibition:
        interleaved.extend(ar_candidates)
        interleaved.extend(ex_candidates)
    elif asks_exhibition and not asks_artist:
        interleaved.extend(ex_candidates)
        interleaved.extend(ar_candidates)
    else:
        max_len = max(len(ex_candidates), len(ar_candidates))
        for idx in range(max_len):
            if idx < len(ar_candidates):
                interleaved.append(ar_candidates[idx])
            if idx < len(ex_candidates):
                interleaved.append(ex_candidates[idx])
    top_pool = list(interleaved[: min(len(interleaved), pool_limit)])
    if not top_pool:
        return []

    recent_set = {str(key or "").strip() for key in list(recent_reference_keys or []) if str(key or "").strip()}
    rng = random.Random(f"mainrefs:{seed_value}:{intent_focus}:{len(top_pool)}")

    sampled: List[dict] = []
    used_keys: set[str] = set()
    source_seen: set[str] = set()
    gallery_counts: Dict[str, int] = {}
    artist_seen: set[str] = set()
    title_seen: set[str] = set()

    def _eligible(candidate: dict, strict_recent: bool) -> bool:
        key = str(candidate.get("key") or "").strip()
        if not key or key in used_keys:
            return False
        if strict_recent and key in recent_set:
            return False
        row = candidate.get("row") or {}
        source = normalize_url(str(row.get("source_url") or ""))
        if source and source in source_seen:
            return False
        gallery = str(row.get("gallery") or "").strip()
        if gallery and gallery_counts.get(gallery, 0) >= 2:
            return False
        if str(candidate.get("kind") or "") == "artist":
            artist_name = str(row.get("artist_name") or "").strip()
            if artist_name and artist_name in artist_seen:
                return False
        else:
            title = str(row.get("title") or "").strip()
            if title and title in title_seen:
                return False
        return True

    for strict_recent in (True, False):
        if len(sampled) >= target_count:
            break
        while len(sampled) < target_count:
            candidates = [candidate for candidate in top_pool if _eligible(candidate, strict_recent)]
            if not candidates:
                break
            weighted = sorted(
                candidates,
                key=lambda candidate: (int(candidate.get("rank") or 9999), rng.random()),
            )
            pick_band = max(1, min(len(weighted), max(8, len(weighted) // 4)))
            picked = weighted[rng.randrange(pick_band)]
            row = picked.get("row") or {}
            key = str(picked.get("key") or "").strip()
            sampled.append(
                {
                    "kind": str(picked.get("kind") or "").strip(),
                    "key": key,
                    "source_url": str(row.get("source_url") or "").strip(),
                    "label": str(row.get("artist_name") or row.get("title") or "").strip(),
                    "fair_label": str(row.get("fair_label") or "").strip(),
                    "gallery": str(row.get("gallery") or "").strip(),
                }
            )
            used_keys.add(key)
            source = normalize_url(str(row.get("source_url") or ""))
            if source:
                source_seen.add(source)
            gallery = str(row.get("gallery") or "").strip()
            if gallery:
                gallery_counts[gallery] = gallery_counts.get(gallery, 0) + 1
            if str(picked.get("kind") or "") == "artist":
                artist_name = str(row.get("artist_name") or "").strip()
                if artist_name:
                    artist_seen.add(artist_name)
            else:
                title = str(row.get("title") or "").strip()
                if title:
                    title_seen.add(title)
            if len(sampled) >= target_count:
                break

    return sampled[:target_count]


def _promote_main_reference_rows(
    rows: List[dict],
    main_keys: Dict[str, int],
    kind: str,
    limit: int,
    row_lookup: Dict[str, dict] | None = None,
) -> List[dict]:
    if not rows:
        return []
    if not main_keys:
        return rows[:limit]

    promoted: List[dict] = []
    seen_keys: set[str] = set()
    if row_lookup:
        for key, _order in sorted(main_keys.items(), key=lambda item: item[1]):
            if not key.startswith(f"{kind}::"):
                continue
            row = row_lookup.get(key)
            if not isinstance(row, dict):
                continue
            if key in seen_keys:
                continue
            promoted.append(dict(row))
            seen_keys.add(key)
            if len(promoted) >= limit:
                return promoted[:limit]

    indexed: List[tuple[int, int, dict]] = []
    for idx, row in enumerate(rows):
        key = _reference_key_from_row(row, kind)
        if key in seen_keys:
            continue
        priority = main_keys.get(key, 10_000 + idx)
        indexed.append((priority, idx, row))
    indexed.sort(key=lambda item: (item[0], item[1]))
    for _priority, _idx, row in indexed:
        promoted.append(row)
        if len(promoted) >= limit:
            break
    return promoted[:limit]


def build_advisor_grounded_context(
    fair_label: str,
    question_text: str,
    text_limit_per_kind: int = 14,
    rotation_index: int = 0,
    diversity_seed: int = 0,
    recent_broad_history: List[dict] | None = None,
    recent_reference_keys: List[str] | None = None,
) -> Dict[str, object]:
    fair_slugs = set(resolve_fair_slugs(fair_label))
    cross_fair_mode = len(fair_slugs) > 1
    tokens = _tokenize_query(question_text)
    broad_query_mode = _is_broad_query(question_text, tokens)
    ideation_query = _is_ideation_query(question_text)
    intent_focus = _detect_intent_focus(question_text, tokens)
    safe_rotation_index = max(0, int(rotation_index or 0))
    safe_diversity_seed = int(diversity_seed or 0)
    warnings: List[str] = []

    ex_data = load_exhibition_records_readonly()
    ar_data = load_artist_records_readonly()
    warnings.extend(ex_data.warnings)
    warnings.extend(ar_data.warnings)

    art_pulse_snapshot, art_pulse_warnings = _resolve_art_pulse_snapshot(fair_label)
    warnings.extend(art_pulse_warnings)

    exhibitions = [r for r in ex_data.records if str(r.get("fair_slug") or "") in fair_slugs]
    artists = [r for r in ar_data.records if str(r.get("fair_slug") or "") in fair_slugs]
    exhibition_years = [_coerce_year(r.get("year")) for r in exhibitions]
    artist_years = [_coerce_year(r.get("year")) for r in artists]
    exhibitions_latest_year = max((y for y in exhibition_years if y is not None), default=None)
    artists_latest_year = max((y for y in artist_years if y is not None), default=None)
    available_years = [y for y in [exhibitions_latest_year, artists_latest_year] if y is not None]
    reference_year = max(available_years) if available_years else 2025
    reference_year_display = str(reference_year)
    if exhibitions_latest_year and artists_latest_year and exhibitions_latest_year != artists_latest_year:
        reference_year_display = f"Exhibitions:{exhibitions_latest_year} / Artists:{artists_latest_year}"

    exhibition_rows: List[dict] = []
    exhibition_gallery_cohorts: Dict[str, int] = {}
    for row in exhibitions:
        row_year = _coerce_year(row.get("year"))
        if row_year is None:
            row_year = reference_year
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
        candidate["_gallery_cohort_index"] = _resolve_gallery_cohort_index(
            exhibition_gallery_cohorts,
            candidate["fair_slug"],
            candidate["gallery"],
            candidate["source_url"],
        )
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
        intent_score = _normalize_broad_intent_score(intent_score, intent_focus, broad_query_mode, ideation_query)
        page_score = _page_description_score(hay)
        candidate["_intent_score"] = intent_score
        candidate["_page_description_score"] = page_score
        candidate["_score"] = _score_text(hay, tokens) + (intent_score * 3) - (page_score * 2 if ideation_query else 0)
        candidate["_quality_score"] = _candidate_quality_score(candidate)
        candidate["_query_tiebreak"] = _question_tiebreak_value(question_text, candidate)
        exhibition_rows.append(candidate)

    artist_rows: List[dict] = []
    artist_gallery_cohorts: Dict[str, int] = {}
    for row in artists:
        artist_name = str(row.get("artist_name") or "").strip()
        if is_invalid_artist_name(artist_name):
            continue
        row_year = _coerce_year(row.get("year"))
        if row_year is None:
            row_year = reference_year
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
        candidate["_gallery_cohort_index"] = _resolve_gallery_cohort_index(
            artist_gallery_cohorts,
            candidate["fair_slug"],
            candidate["gallery"],
            candidate["source_url"],
        )
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
        intent_score = _normalize_broad_intent_score(intent_score, intent_focus, broad_query_mode, ideation_query)
        page_score = _page_description_score(hay)
        candidate["_intent_score"] = intent_score
        candidate["_page_description_score"] = page_score
        candidate["_score"] = _score_text(hay, tokens) + (intent_score * 3) - (page_score * 2 if ideation_query else 0)
        candidate["_quality_score"] = _candidate_quality_score(candidate)
        candidate["_query_tiebreak"] = _question_tiebreak_value(question_text, candidate)
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
        diversity_seed=safe_diversity_seed,
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
        diversity_seed=safe_diversity_seed,
        recent_broad_history=recent_broad_history,
        kind="artist",
        intent_focus=intent_focus,
    )

    sampled_main_references: List[dict] = []
    sampled_main_keys_order: Dict[str, int] = {}
    if broad_query_mode and safe_diversity_seed:
        sampled_main_references = _sample_broad_main_references(
            question_text=question_text,
            ex_rows=ex_scored,
            ar_rows=ar_scored,
            cross_fair_mode=cross_fair_mode,
            intent_focus=intent_focus,
            diversity_seed=safe_diversity_seed,
            recent_reference_keys=recent_reference_keys,
            target_count=4,
            pool_limit=100,
        )
        for idx, item in enumerate(sampled_main_references):
            key = str(item.get("key") or "").strip()
            if not key or key in sampled_main_keys_order:
                continue
            sampled_main_keys_order[key] = idx
        if sampled_main_keys_order:
            ex_lookup: Dict[str, dict] = {}
            for row in ex_scored:
                key = _reference_key_from_row(row, "exhibition")
                if key and key not in ex_lookup:
                    ex_lookup[key] = row
            ar_lookup: Dict[str, dict] = {}
            for row in ar_scored:
                key = _reference_key_from_row(row, "artist")
                if key and key not in ar_lookup:
                    ar_lookup[key] = row
            exhibition_evidence = _promote_main_reference_rows(
                exhibition_evidence,
                sampled_main_keys_order,
                kind="exhibition",
                limit=exhibition_limit_per_kind,
                row_lookup=ex_lookup,
            )
            artist_evidence = _promote_main_reference_rows(
                artist_evidence,
                sampled_main_keys_order,
                kind="artist",
                limit=artist_limit_per_kind,
                row_lookup=ar_lookup,
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
            "diversity_seed": safe_diversity_seed,
            "recent_broad_history": list(recent_broad_history or [])[-8:],
            "recent_reference_keys": list(recent_reference_keys or [])[-40:],
            "sampled_main_references": [dict(item) for item in sampled_main_references],
            "sampled_main_reference_keys": list(sampled_main_keys_order.keys()),
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
            "Advisor keeps year-selection UI disabled and searches across all available years by default. "
            "Broad-query mode uses a lightweight evidence rotation to reduce fixed candidate repetition. "
            "Art Pulse overview is attached as a read-only snapshot. "
            "history is not used as a default query path."
        ),
    }


def build_advisor_followup_reference_patch(
    fair_label: str,
    question_text: str,
    base_context: Dict[str, object],
    existing_urls: List[str] | None = None,
    limit_total: int = 5,
) -> Dict[str, object]:
    selection = dict((base_context or {}).get("selection", {}) or {})
    tokens = _tokenize_query(question_text)
    if not tokens:
        fallback_seen = set()
        fallback_tokens: List[str] = []
        for token in re.findall(r"[一-龠ぁ-んァ-ヶー]{2,8}|[a-z]{3,12}", (question_text or "").lower()):
            low = str(token or "").strip().lower()
            if len(low) < 2 or low in fallback_seen:
                continue
            fallback_seen.add(low)
            fallback_tokens.append(low)
            if len(fallback_tokens) >= 12:
                break
        tokens = fallback_tokens
    q = (question_text or "").strip().lower()
    existing_norm_urls = {
        normalize_url(str(url or ""))
        for url in list(existing_urls or [])
        if str(url or "").strip()
    }
    base_tokens = {
        str(token or "").strip().lower()
        for token in list(selection.get("tokens", []) or [])
        if str(token or "").strip()
    }
    intent_focus = _detect_intent_focus(question_text, tokens)
    focus_changed = bool(intent_focus and intent_focus != str(selection.get("intent_focus") or "").strip())
    new_token_count = len([token for token in tokens if token not in base_tokens and len(token) >= 2])
    expansion_hints = ("他にも", "ほかに", "別", "別方向", "別案", "違う", "もっと", "寄り", "another", "else")
    needs_refresh = focus_changed or new_token_count >= 1 or any(hint in q for hint in expansion_hints)
    if not needs_refresh:
        return {
            "refreshed": False,
            "selection": {
                "tokens": tokens,
                "intent_focus": intent_focus,
                "focus_changed": focus_changed,
                "new_token_count": new_token_count,
            },
            "exhibition_evidence": [],
            "artist_evidence": [],
        }

    fair_slugs = set(resolve_fair_slugs(fair_label))
    cross_fair_mode = len(fair_slugs) > 1
    broad_query_mode = _is_broad_query(question_text, tokens)
    ideation_query = _is_ideation_query(question_text)
    safe_limit_total = max(2, int(limit_total or 5))
    per_kind_limit = max(1, min(3, (safe_limit_total + 1) // 2))

    ex_data = load_exhibition_records_readonly()
    ar_data = load_artist_records_readonly()
    exhibitions = [r for r in ex_data.records if str(r.get("fair_slug") or "") in fair_slugs]
    artists = [r for r in ar_data.records if str(r.get("fair_slug") or "") in fair_slugs]
    exhibition_years = [_coerce_year(r.get("year")) for r in exhibitions]
    artist_years = [_coerce_year(r.get("year")) for r in artists]
    exhibitions_latest_year = max((y for y in exhibition_years if y is not None), default=None)
    artists_latest_year = max((y for y in artist_years if y is not None), default=None)
    available_years = [y for y in [exhibitions_latest_year, artists_latest_year] if y is not None]
    reference_year = max(available_years) if available_years else 2025

    exhibition_rows: List[dict] = []
    exhibition_gallery_cohorts: Dict[str, int] = {}
    for row in exhibitions:
        source_url = str(row.get("source_url") or "").strip()
        if existing_norm_urls and normalize_url(source_url) in existing_norm_urls:
            continue
        row_year = _coerce_year(row.get("year"))
        if row_year is None:
            row_year = reference_year
        candidate = {
            "kind": "exhibition",
            "fair_slug": str(row.get("fair_slug") or ""),
            "fair_label": str(row.get("fair_label") or ""),
            "gallery": str(row.get("gallery_name") or ""),
            "title": str(row.get("exhibition_title") or ""),
            "headline_ja": str(row.get("headline_ja") or "").strip(),
            "summary_ja": str(row.get("summary_ja") or "").strip(),
            "source_url": source_url,
            "text": str(row.get("text") or "").strip(),
            "image_preview": str(row.get("image_preview") or "").strip(),
            "image_preview_r2_key": str(row.get("image_preview_r2_key") or "").strip(),
            "year": row_year,
        }
        candidate["_gallery_cohort_index"] = _resolve_gallery_cohort_index(
            exhibition_gallery_cohorts,
            candidate["fair_slug"],
            candidate["gallery"],
            candidate["source_url"],
        )
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
        intent_score = _normalize_broad_intent_score(intent_score, intent_focus, broad_query_mode, ideation_query)
        page_score = _page_description_score(hay)
        candidate["_intent_score"] = intent_score
        candidate["_page_description_score"] = page_score
        candidate["_score"] = _score_text(hay, tokens) + (intent_score * 3) - (page_score * 2 if ideation_query else 0)
        candidate["_quality_score"] = _candidate_quality_score(candidate)
        candidate["_query_tiebreak"] = _question_tiebreak_value(question_text, candidate)
        exhibition_rows.append(candidate)

    artist_rows: List[dict] = []
    artist_gallery_cohorts: Dict[str, int] = {}
    for row in artists:
        artist_name = str(row.get("artist_name") or "").strip()
        if is_invalid_artist_name(artist_name):
            continue
        source_url = str(row.get("source_url") or "").strip()
        if existing_norm_urls and normalize_url(source_url) in existing_norm_urls:
            continue
        row_year = _coerce_year(row.get("year"))
        if row_year is None:
            row_year = reference_year
        candidate = {
            "kind": "artist",
            "fair_slug": str(row.get("fair_slug") or ""),
            "fair_label": str(row.get("fair_label") or ""),
            "gallery": str(row.get("gallery_name") or ""),
            "artist_name": artist_name,
            "artist_name_kana": str(row.get("artist_name_kana") or "").strip(),
            "headline_ja": str(row.get("headline_ja") or "").strip(),
            "summary_ja": str(row.get("summary_ja") or "").strip(),
            "source_url": source_url,
            "text": str(row.get("text") or "").strip(),
            "artist_image_preview_candidates": list(row.get("artist_image_preview_candidates") or []),
            "year": row_year,
        }
        candidate["_gallery_cohort_index"] = _resolve_gallery_cohort_index(
            artist_gallery_cohorts,
            candidate["fair_slug"],
            candidate["gallery"],
            candidate["source_url"],
        )
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
        intent_score = _normalize_broad_intent_score(intent_score, intent_focus, broad_query_mode, ideation_query)
        page_score = _page_description_score(hay)
        candidate["_intent_score"] = intent_score
        candidate["_page_description_score"] = page_score
        candidate["_score"] = _score_text(hay, tokens) + (intent_score * 3) - (page_score * 2 if ideation_query else 0)
        candidate["_quality_score"] = _candidate_quality_score(candidate)
        candidate["_query_tiebreak"] = _question_tiebreak_value(question_text, candidate)
        artist_rows.append(candidate)

    ex_scored = [r for r in exhibition_rows if int(r.get("_score", 0)) > 0] or exhibition_rows
    ar_scored = [r for r in artist_rows if int(r.get("_score", 0)) > 0] or artist_rows
    ex_scored, _ = _trim_rows_by_intent(ex_scored, intent_focus, per_kind_limit, [], "advisor_followup_exhibition")
    ar_scored, _ = _trim_rows_by_intent(ar_scored, intent_focus, per_kind_limit, [], "advisor_followup_artist")
    exhibition_evidence = _select_evidence_with_rotation(
        ex_scored,
        per_kind_limit,
        cross_fair_mode=cross_fair_mode,
        broad_query_mode=broad_query_mode,
        rotation_index=0,
        recent_broad_history=[],
        kind="exhibition",
        intent_focus=intent_focus,
    )
    artist_evidence = _select_evidence_with_rotation(
        ar_scored,
        per_kind_limit,
        cross_fair_mode=cross_fair_mode,
        broad_query_mode=broad_query_mode,
        rotation_index=0,
        recent_broad_history=[],
        kind="artist",
        intent_focus=intent_focus,
    )
    for row in exhibition_evidence:
        row.pop("_score", None)
        row.pop("_intent_score", None)
    for row in artist_evidence:
        row.pop("_score", None)
        row.pop("_intent_score", None)
    return {
        "refreshed": bool(exhibition_evidence or artist_evidence),
        "selection": {
            "fair_label": fair_label,
            "tokens": tokens,
            "intent_focus": intent_focus,
            "cross_fair_mode": cross_fair_mode,
            "broad_query_mode": broad_query_mode,
            "focus_changed": focus_changed,
            "new_token_count": new_token_count,
        },
        "exhibition_evidence": exhibition_evidence[:per_kind_limit],
        "artist_evidence": artist_evidence[:per_kind_limit],
    }
