from __future__ import annotations

import json
import logging
import os
import re
import time
import unicodedata
from typing import Callable, Dict, List, Tuple
from urllib.parse import parse_qs, quote_plus, urlparse

from phase2_art_pulse_config import (
    ART_PULSE_MAX_OUTPUT_TOKENS,
    ART_PULSE_PAYLOAD_CANDIDATE_CAP,
    ART_PULSE_PROMPT_ARTIST_ROWS,
    ART_PULSE_PROMPT_EXHIBITION_ROWS,
    ART_PULSE_PROMPT_SNIPPET_CHARS,
    ART_PULSE_SECTION1_MIN_CHARS,
    ART_PULSE_SECTION2_MIN_CHARS,
    ART_PULSE_SECTION3_MIN_CHARS,
    ART_PULSE_TEXT_MAX_CHARS,
    ART_PULSE_TEXT_MIN_CHARS,
    ART_PULSE_TEXT_SOFT_OVER_CHARS,
    ART_PULSE_TARGET_CHARS,
    ART_PULSE_TARGET_TOLERANCE,
    MAX_EVIDENCE_URLS,
    MAX_IMAGE_TOTAL,
    MIN_IMAGE_PER_NONEMPTY_SECTION,
    find_persona,
    find_persona_angle,
)
from phase2_response_style import PLAIN_JAPANESE_RULE
logger = logging.getLogger(__name__)

ART_PULSE_TEXT_ACCEPTABLE_MIN_CHARS = 1200

REQUIRED_HEADINGS = [
    "## 今年のトレンド",
    "## トレンドに沿った重要なExhibitionまたはArtist",
    "## トレンドではないが面白かったExhibitionまたはArtist",
]

SECTION_KEYS = ["section1", "section2", "section3"]
MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")
ARTIST_GOOGLE_LINK_PATTERN = re.compile(
    r"\[[^\]]+\]\(https://www\.google\.com/search\?tbm=isch&q=[^)]+\)"
)
ARTIST_WITH_KANA_PATTERN = re.compile(
    r"\[[^\]]+\]\(https://www\.google\.com/search\?tbm=isch&q=[^)]+\)（[^）]+）"
)
ARTIST_DUP_EN_NAME_PATTERN = re.compile(
    r"\[([^\]]+)\]\(https://www\.google\.com/search\?tbm=isch&q=[^)]+\)（\1）"
)

KANA_WORD_MAP = {
    "ALEX": "アレックス",
    "SOPHIA": "ソフィア",
    "MARCUS": "マーカス",
    "KAI": "カイ",
    "ZOE": "ゾーイ",
    "LEO": "レオ",
    "REN": "レン",
    "NADIA": "ナディア",
    "CONNY": "コニー",
    "PURTILL": "パーティル",
    "AGUS": "アグス",
    "SUWAGE": "スワゲ",
    "ANTONIA": "アントニア",
    "KUO": "クオ",
    "PETER": "ピーター",
    "GALLO": "ガロ",
    "JOAN": "ジョアン",
    "NELSON": "ネルソン",
    "JAY": "ジェイ",
    "HEIKES": "ハイクス",
    "MARINA": "マリナ",
    "GRIZE": "グリゼ",
}


def _unique_urls(urls: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for url in urls:
        value = (url or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _pick_angle(reporter: Dict[str, object], angle_keys: List[str]) -> Tuple[str, str, str]:
    reporter_angles = list(reporter.get("angles", []) or [])
    if not reporter_angles:
        return "angle_unknown", "切り口未設定", ""
    key = str(angle_keys[0]) if angle_keys else str(reporter_angles[0].get("key") or "")
    angle = find_persona_angle(reporter, key) or reporter_angles[0]
    return (
        str(angle.get("key") or key),
        str(angle.get("label") or key),
        str(angle.get("description") or ""),
    )


def _persona_first_person(reporter: Dict[str, object]) -> str:
    reporter_id = str(reporter.get("id") or "")
    if reporter_id in {"reporter_01", "reporter_03", "reporter_06", "reporter_07"}:
        return "僕"
    return "私"


def _google_image_search_url(name_en: str) -> str:
    # 01章「9.リンクの扱い」に合わせ、qはURLエンコードしつつ +art を付与
    return f"https://www.google.com/search?tbm=isch&q={quote_plus((name_en or '').strip() + ' art')}"


def _clean_artist_name(name: str) -> str:
    text = re.sub(r"\s+", " ", (name or "").strip())
    text = re.sub(r"\s+\d+$", "", text)
    return text.strip()


def _normalize_name_token(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", (text or "").strip())
    no_marks = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r"[^0-9A-Za-z]+", "", no_marks).lower()


def _normalize_exact_match_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", (text or "").strip())
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = re.sub(r"\s+", "", normalized)
    normalized = re.sub(
        r"[\"'`´“”‘’･・,，、。．:：;；!?！？()\[\]{}<>＜＞「」『』【】/\\|＿_‐‑‒–—―\-~〜…]+",
        "",
        normalized,
    )
    return normalized.casefold()


def _contains_cjk(text: str) -> bool:
    return bool(re.search(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]", text or ""))


def _normalize_kana(kana: str) -> str:
    text = (kana or "").strip()
    text = re.sub(r"\s+", "", text)
    return text


def _guess_kana_from_name(name_en: str) -> str:
    words = re.findall(r"[A-Za-z]+", name_en or "")
    if not words:
        return ""
    converted: List[str] = []
    for word in words:
        kana = KANA_WORD_MAP.get(word.upper())
        if not kana:
            return ""
        converted.append(kana)
    return "・".join(converted)


def _clean_exhibition_title(title: str, gallery: str) -> str:
    text = re.sub(r"\s+", " ", (title or "").strip())
    gallery_text = re.sub(r"\s+", " ", (gallery or "").strip())
    if "|" in text:
        parts = [part.strip() for part in text.split("|") if part.strip()]
        if parts:
            text = parts[0]
    if gallery_text:
        text = re.sub(
            rf"\s*[-|@]\s*{re.escape(gallery_text)}\s*$",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()
    text = re.sub(
        r"\b\d{1,2}\s+[A-Za-z]{3,9}\s*-\s*\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}\b",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()
    return text or "(untitled)"


def _build_evidence_payload(overview: Dict[str, object], cap: int = 24) -> Dict[str, object]:
    ex_candidates = list(overview.get("exhibition_candidates", []) or [])
    ar_candidates = list(overview.get("artist_candidates", []) or [])

    ex_deduped: List[Dict[str, object]] = []
    seen_ex = set()
    for row in ex_candidates:
        source_url = str(row.get("source_url") or "").strip()
        title = _clean_exhibition_title(str(row.get("title") or ""), str(row.get("gallery") or ""))
        dedupe_key = (source_url, title)
        if dedupe_key in seen_ex:
            continue
        seen_ex.add(dedupe_key)
        ex_deduped.append(
            {
                "fair": str(row.get("fair") or "").strip(),
                "gallery": str(row.get("gallery") or "").strip(),
                "title": title,
                "source_url": source_url,
                "retrieval_score": int(row.get("_retrieval_score") or 0),
                "retrieval_reason": str(row.get("_retrieval_reason") or ""),
            }
        )

    ar_deduped: List[Dict[str, object]] = []
    seen_ar = set()
    for row in ar_candidates:
        source_url = str(row.get("source_url") or "").strip()
        artist_name_en = _clean_artist_name(str(row.get("artist_name_en") or row.get("artist") or ""))
        dedupe_key = (source_url, artist_name_en)
        if dedupe_key in seen_ar:
            continue
        seen_ar.add(dedupe_key)
        ar_deduped.append(
            {
                "fair": str(row.get("fair") or "").strip(),
                "gallery": str(row.get("gallery") or "").strip(),
                "artist": artist_name_en,
                "artist_name_en": artist_name_en,
                "artist_name_kana": str(row.get("artist_name_kana") or "").strip(),
                "source_url": source_url,
                "text_snippet": str(row.get("text_snippet") or "").strip(),
                "retrieval_score": int(row.get("_retrieval_score") or 0),
                "retrieval_reason": str(row.get("_retrieval_reason") or ""),
            }
        )

    def _fair_order(keys: List[str]) -> List[str]:
        order = [k for k in ("Frieze London", "Liste Art Fair Basel") if k in keys]
        for key in sorted(keys):
            if key not in order:
                order.append(key)
        return order

    def _diversified_pick(rows: List[Dict[str, object]], max_count: int) -> List[Dict[str, object]]:
        if not rows or max_count <= 0:
            return []

        fair_keys = _fair_order(
            sorted(
                {
                    str(row.get("fair") or "").strip() or "(unknown)"
                    for row in rows
                }
            )
        )
        fair_rank = {fair: idx for idx, fair in enumerate(fair_keys)}
        per_gallery_cap = 2

        def _row_fair(row: Dict[str, object]) -> str:
            return str(row.get("fair") or "").strip() or "(unknown)"

        def _row_gallery(row: Dict[str, object]) -> str:
            return str(row.get("gallery") or "").strip() or "(unknown)"

        def _row_uid(row: Dict[str, object]) -> str:
            source_url = str(row.get("source_url") or "").strip()
            if source_url:
                return source_url
            return f"{_row_fair(row)}|{_row_gallery(row)}|{row.get('title') or row.get('artist_name_en') or row.get('artist') or ''}"

        prepared = sorted(
            rows,
            key=lambda row: (
                -int(row.get("retrieval_score") or 0),
                fair_rank.get(_row_fair(row), len(fair_rank)),
                _row_gallery(row),
                _row_uid(row),
            ),
        )

        selected: List[Dict[str, object]] = []
        used_uids = set()
        gallery_use_count: Dict[Tuple[str, str], int] = {}

        # Step 1: score-first selection, then apply gallery concentration cap.
        for row in prepared:
            if len(selected) >= max_count:
                break
            uid = _row_uid(row)
            if uid in used_uids:
                continue
            gkey = (_row_fair(row), _row_gallery(row))
            if gallery_use_count.get(gkey, 0) >= per_gallery_cap:
                continue
            selected.append(row)
            used_uids.add(uid)
            gallery_use_count[gkey] = gallery_use_count.get(gkey, 0) + 1

        # Step 2: cap-relaxed fill if slots remain.
        if len(selected) < max_count:
            for row in prepared:
                if len(selected) >= max_count:
                    break
                uid = _row_uid(row)
                if uid in used_uids:
                    continue
                selected.append(row)
                used_uids.add(uid)

        return selected[:max_count]

    ex_rows = _diversified_pick(ex_deduped, cap)
    ar_rows = _diversified_pick(ar_deduped, cap)

    ex_urls = _unique_urls([str(row.get("source_url") or "") for row in ex_rows])
    ar_urls = _unique_urls([str(row.get("source_url") or "") for row in ar_rows])

    return {
        "exhibition_rows": ex_rows,
        "artist_rows": ar_rows,
        "exhibition_urls": ex_urls,
        "artist_urls": ar_urls,
        "all_urls": _unique_urls(ex_urls + ar_urls),
        "fairs_present": sorted(
            {
                str(row.get("fair") or "")
                for row in ex_rows + ar_rows
                if str(row.get("fair") or "").strip()
            }
        ),
    }


def _body_text_len(body: str) -> int:
    lines: List[str] = []
    for line in (body or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("!["):
            continue
        if stripped.startswith("Source:"):
            continue
        visible = MARKDOWN_LINK_PATTERN.sub(r"\1", line)
        visible = re.sub(r"https?://\S+", "", visible)
        lines.append(visible)
    return len("\n".join(lines).strip())


def _truncate_body_text(
    body: str,
    limit: int = ART_PULSE_TEXT_MAX_CHARS,
    soft_over_chars: int = ART_PULSE_TEXT_SOFT_OVER_CHARS,
) -> str:
    text = (body or "").strip()
    hard_limit = limit + max(0, int(soft_over_chars))
    if _body_text_len(text) <= hard_limit:
        return text
    lines = text.splitlines()
    kept: List[str] = []
    for line in lines:
        trial = "\n".join(kept + [line]).strip()
        if _body_text_len(trial) > hard_limit:
            break
        kept.append(line)
    out = "\n".join(kept).rstrip()
    if out and not out.endswith("…"):
        out += "…"
    return out


def _has_required_structure(body: str) -> bool:
    text = body or ""
    if any(heading not in text for heading in REQUIRED_HEADINGS):
        return False
    slash_runs = max((len(match.group(0)) for match in re.finditer(r"(?:\s*/\s*){4,}", text)), default=0)
    if slash_runs >= 1:
        return False
    return True


def _count_required_headings_present(body: str) -> int:
    text = body or ""
    return sum(1 for heading in REQUIRED_HEADINGS if heading in text)


def _text_contains_exactish_token(text: str, token: str) -> bool:
    haystack = text or ""
    needle = (token or "").strip()
    if not haystack or not needle:
        return False
    if needle in haystack:
        return True
    if needle.startswith(("http://", "https://")):
        return False
    normalized_needle = _normalize_exact_match_text(needle)
    min_len = 2 if _contains_cjk(needle) else 5
    if len(normalized_needle) < min_len:
        return False
    normalized_haystack = _normalize_exact_match_text(haystack)
    return bool(normalized_needle and normalized_needle in normalized_haystack)


def _split_body_by_required_headings(body: str) -> Dict[str, str]:
    text = (body or "").strip()
    starts: List[Tuple[str, int]] = []
    for heading in REQUIRED_HEADINGS:
        pos = text.find(heading)
        if pos < 0:
            return {}
        starts.append((heading, pos))
    starts.sort(key=lambda x: x[1])
    sections: Dict[str, str] = {}
    for idx, (heading, start) in enumerate(starts):
        end = starts[idx + 1][1] if idx + 1 < len(starts) else len(text)
        sections[heading] = text[start:end].strip()
    return sections


def _empty_selection_plan() -> Dict[str, Dict[str, List[str]]]:
    return {
        key: {"exhibition_urls": [], "artist_urls": []}
        for key in SECTION_KEYS
    }


def _dedupe_preserve_order(values: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for value in values:
        normalized = (value or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        out.append(normalized)
    return out


def _infer_selected_evidence_from_body(body: str, payload: Dict[str, object]) -> Dict[str, Dict[str, List[str]]]:
    selection = _empty_selection_plan()
    sections = _split_body_by_required_headings(body)
    if not sections:
        return selection

    ex_rows = list(payload.get("exhibition_rows", []) or [])
    ar_rows = list(payload.get("artist_rows", []) or [])

    for idx, heading in enumerate(REQUIRED_HEADINGS):
        sec_key = SECTION_KEYS[idx]
        text = sections.get(heading, "")
        ex_urls: List[str] = []
        ar_urls: List[str] = []

        for row in ex_rows:
            source_url = str(row.get("source_url") or "").strip()
            title = str(row.get("title") or "").strip()
            if source_url and source_url in text:
                ex_urls.append(source_url)
            elif _text_contains_exactish_token(text, title):
                ex_urls.append(source_url)

        for row in ar_rows:
            source_url = str(row.get("source_url") or "").strip()
            artist_name = str(row.get("artist_name_en") or "").strip()
            if source_url and source_url in text:
                ar_urls.append(source_url)
            elif _text_contains_exactish_token(text, artist_name):
                ar_urls.append(source_url)

        selection[sec_key]["exhibition_urls"] = _dedupe_preserve_order(ex_urls)[:6]
        selection[sec_key]["artist_urls"] = _dedupe_preserve_order(ar_urls)[:6]

    return selection


def _merge_selection_plan(
    primary: Dict[str, Dict[str, List[str]]],
    secondary: Dict[str, Dict[str, List[str]]],
) -> Dict[str, Dict[str, List[str]]]:
    merged = _empty_selection_plan()
    for key in SECTION_KEYS:
        merged[key]["exhibition_urls"] = _dedupe_preserve_order(
            list(primary.get(key, {}).get("exhibition_urls", []) or [])
            + list(secondary.get(key, {}).get("exhibition_urls", []) or [])
        )
        merged[key]["artist_urls"] = _dedupe_preserve_order(
            list(primary.get(key, {}).get("artist_urls", []) or [])
            + list(secondary.get(key, {}).get("artist_urls", []) or [])
        )
    return merged


def _build_image_seed_selection(
    payload: Dict[str, object],
    overview: Dict[str, object],
) -> Dict[str, Dict[str, List[str]]]:
    image_plan = overview.get("image_reference_plan", {}) or {}
    ex_image_sources = {
        str(row.get("source_url") or "").strip()
        for row in list(image_plan.get("exhibition_image_candidates", []) or [])
        if str(row.get("source_url") or "").strip() and str(row.get("image_url") or "").strip()
    }
    ar_image_sources = {
        str(row.get("source_url") or "").strip()
        for row in list(image_plan.get("artist_image_candidates", []) or [])
        if str(row.get("source_url") or "").strip() and str(row.get("image_url") or "").strip()
    }
    ex_all = list(payload.get("exhibition_urls", []) or [])
    ar_all = list(payload.get("artist_urls", []) or [])
    ex_seed = [u for u in ex_all if u in ex_image_sources] or ex_all
    ar_seed = [u for u in ar_all if u in ar_image_sources] or ar_all

    seeded = _empty_selection_plan()
    if not (ex_seed or ar_seed):
        return seeded

    seeded["section1"]["exhibition_urls"] = ex_seed[:1]
    seeded["section2"]["exhibition_urls"] = ex_seed[1:3] or ex_seed[:1]
    seeded["section3"]["exhibition_urls"] = ex_seed[3:5] or ex_seed[:1]
    seeded["section2"]["artist_urls"] = ar_seed[:2]
    seeded["section3"]["artist_urls"] = ar_seed[2:4] or ar_seed[:2]
    return seeded


def _count_selection_urls(selection_plan: Dict[str, Dict[str, List[str]]]) -> int:
    total = 0
    for key in SECTION_KEYS:
        total += len(selection_plan.get(key, {}).get("exhibition_urls", []))
        total += len(selection_plan.get(key, {}).get("artist_urls", []))
    return total


def _build_section_image_buckets(
    overview: Dict[str, object],
    selection_plan: Dict[str, Dict[str, List[str]]],
) -> List[List[Dict[str, object]]]:
    plan = overview.get("image_reference_plan", {}) or {}
    ex_candidates = [
        row for row in list(plan.get("exhibition_image_candidates", []) or [])
        if str(row.get("image_url") or "").strip()
    ]
    ar_candidates = [
        row for row in list(plan.get("artist_image_candidates", []) or [])
        if str(row.get("image_url") or "").strip()
    ]

    ex_by_source: Dict[str, List[Dict[str, object]]] = {}
    ar_by_source: Dict[str, List[Dict[str, object]]] = {}
    for row in ex_candidates:
        source_url = str(row.get("source_url") or "").strip()
        if source_url:
            ex_by_source.setdefault(source_url, []).append(row)
    for row in ar_candidates:
        source_url = str(row.get("source_url") or "").strip()
        if source_url:
            ar_by_source.setdefault(source_url, []).append(row)

    section_pool: Dict[str, List[Dict[str, object]]] = {}
    section_weights: Dict[str, int] = {}
    all_selected_unique_images = set()

    for sec_key in SECTION_KEYS:
        sec = selection_plan.get(sec_key, {}) or {}
        ex_urls = list(sec.get("exhibition_urls", []) or [])
        ar_urls = list(sec.get("artist_urls", []) or [])
        weight = len(ex_urls) + len(ar_urls)
        section_weights[sec_key] = weight

        pool: List[Dict[str, object]] = []
        seen_in_section = set()
        for source_url in ex_urls:
            for row in ex_by_source.get(source_url, []):
                image_url = str(row.get("image_url") or "").strip()
                if not image_url or image_url in seen_in_section:
                    continue
                seen_in_section.add(image_url)
                pool.append(row)
                all_selected_unique_images.add(image_url)
        for source_url in ar_urls:
            for row in ar_by_source.get(source_url, []):
                image_url = str(row.get("image_url") or "").strip()
                if not image_url or image_url in seen_in_section:
                    continue
                seen_in_section.add(image_url)
                pool.append(row)
                all_selected_unique_images.add(image_url)
        section_pool[sec_key] = pool

    target_total = min(MAX_IMAGE_TOTAL, len(all_selected_unique_images))
    if target_total <= 0:
        return [[] for _ in SECTION_KEYS]

    nonempty_sections = [k for k in SECTION_KEYS if section_pool.get(k)]
    if not nonempty_sections:
        return [[] for _ in SECTION_KEYS]

    quotas: Dict[str, int] = {k: 0 for k in SECTION_KEYS}

    # まず各セクションに最低1枚（非空セクションのみ）
    for key in nonempty_sections:
        if sum(quotas.values()) < target_total:
            quotas[key] = MIN_IMAGE_PER_NONEMPTY_SECTION

    remaining = target_total - sum(quotas.values())
    if remaining < 0:
        remaining = 0

    # 残りはセクション重み（参照URL数）に比例配分
    total_weight = sum(section_weights.get(k, 0) for k in nonempty_sections) or len(nonempty_sections)
    fractional: List[Tuple[str, float]] = []
    for key in nonempty_sections:
        weight = section_weights.get(key, 0)
        raw = (remaining * (weight if weight > 0 else 1)) / total_weight
        add_floor = int(raw)
        quotas[key] += add_floor
        fractional.append((key, raw - add_floor))

    left = target_total - sum(quotas.values())
    if left > 0:
        for key, _frac in sorted(fractional, key=lambda kv: kv[1], reverse=True):
            if left <= 0:
                break
            quotas[key] += 1
            left -= 1

    used_images = set()
    buckets: List[List[Dict[str, object]]] = []

    for sec_key in SECTION_KEYS:
        quota = max(0, quotas.get(sec_key, 0))
        selected_rows: List[Dict[str, object]] = []
        for row in section_pool.get(sec_key, []):
            if len(selected_rows) >= quota:
                break
            image_url = str(row.get("image_url") or "").strip()
            if not image_url or image_url in used_images:
                continue
            selected_rows.append(row)
            used_images.add(image_url)
        buckets.append(selected_rows)

    # セクション内重複で穴が出た場合、同一selection内の未使用画像で最低限補完
    if sum(len(b) for b in buckets) < target_total:
        fallback_pool: List[Dict[str, object]] = []
        for key in SECTION_KEYS:
            fallback_pool.extend(section_pool.get(key, []))
        for row in fallback_pool:
            if sum(len(b) for b in buckets) >= target_total:
                break
            image_url = str(row.get("image_url") or "").strip()
            if not image_url or image_url in used_images:
                continue
            min_idx = min(range(len(buckets)), key=lambda i: len(buckets[i]))
            buckets[min_idx].append(row)
            used_images.add(image_url)

    return buckets


def _build_section_image_block(rows: List[Dict[str, object]]) -> str:
    if not rows:
        return ""
    lines = [""]
    for idx, row in enumerate(rows, start=1):
        image_url = str(row.get("image_url") or "").strip()
        source_url = str(row.get("source_url") or "").strip()
        kind = "Exhibition" if str(row.get("kind") or "") == "exhibition" else "Artist"
        gallery = str(row.get("gallery") or "").strip()
        caption = f"{kind} 参考画像 {idx}"
        if gallery:
            caption += f" / {gallery}"
        lines.append(f"![{caption}]({image_url})")
        if source_url:
            lines.append(f"Source: <{source_url}>")
    return "\n".join(lines)


def _inject_images_into_sections(main_body: str, buckets: List[List[Dict[str, object]]]) -> str:
    sections = _split_body_by_required_headings(main_body)
    if not sections:
        return main_body
    merged_sections: List[str] = []
    for idx, heading in enumerate(REQUIRED_HEADINGS):
        section_text = sections.get(heading, heading)
        image_block = _build_section_image_block(buckets[idx] if idx < len(buckets) else [])
        if image_block:
            section_text = f"{section_text}\n{image_block}"
        merged_sections.append(section_text.strip())
    return "\n\n".join(merged_sections).strip()


def _flatten_selection_urls(
    selection_plan: Dict[str, Dict[str, List[str]]]
) -> Tuple[List[str], List[str], List[str]]:
    ex_urls: List[str] = []
    ar_urls: List[str] = []
    for key in SECTION_KEYS:
        sec = selection_plan.get(key, {}) or {}
        ex_urls.extend(list(sec.get("exhibition_urls", []) or []))
        ar_urls.extend(list(sec.get("artist_urls", []) or []))
    ex_urls = _dedupe_preserve_order(ex_urls)
    ar_urls = _dedupe_preserve_order(ar_urls)
    all_urls = _dedupe_preserve_order(ex_urls + ar_urls)
    return ex_urls, ar_urls, all_urls


def _compose_url_block(urls: List[str]) -> str:
    urls = list(urls or [])[:MAX_EVIDENCE_URLS]
    lines = ["**根拠URL**"]
    if urls:
        lines.extend([f"- {url}" for url in urls])
    else:
        lines.append("- 根拠URLは表示できませんでした。")
    return "\n".join(lines)


def _is_google_image_search_url(url: str) -> bool:
    try:
        parsed = urlparse((url or "").strip())
        if parsed.scheme not in {"http", "https"}:
            return False
        if parsed.netloc.lower() != "www.google.com":
            return False
        q = parse_qs(parsed.query)
        return "isch" in [v.lower() for v in q.get("tbm", [])]
    except Exception:
        return False


def _google_query_artist_token(url: str) -> str:
    try:
        q = parse_qs(urlparse((url or "").strip()).query).get("q", [""])[0]
    except Exception:
        return ""
    value = re.sub(r"\bart\s*$", "", (q or ""), flags=re.IGNORECASE).strip()
    return _normalize_name_token(value)


def _validate_links_against_payload(body: str, payload: Dict[str, object]) -> List[str]:
    issues: List[str] = []
    links = MARKDOWN_LINK_PATTERN.findall(body or "")
    if not links:
        return issues

    allowed_rag_urls = {
        str(row.get("source_url") or "").strip()
        for row in list(payload.get("exhibition_rows", []) or []) + list(payload.get("artist_rows", []) or [])
        if str(row.get("source_url") or "").strip()
    }
    known_artist_tokens = {
        _normalize_name_token(_clean_artist_name(str(row.get("artist_name_en") or row.get("artist") or "")))
        for row in list(payload.get("artist_rows", []) or [])
        if str(row.get("artist_name_en") or row.get("artist") or "").strip()
    }

    unknown_rag_links: List[str] = []
    unknown_artist_links: List[str] = []
    malformed_google_links: List[str] = []

    for label, url in links:
        cleaned_url = (url or "").strip()
        cleaned_label = _clean_artist_name(label or "")
        if _is_google_image_search_url(cleaned_url):
            label_token = _normalize_name_token(cleaned_label)
            query_token = _google_query_artist_token(cleaned_url)
            if not label_token or not query_token or label_token != query_token:
                malformed_google_links.append(cleaned_url)
                continue
            if label_token not in known_artist_tokens:
                unknown_artist_links.append(cleaned_label or cleaned_url)
            continue

        if cleaned_url not in allowed_rag_urls:
            unknown_rag_links.append(cleaned_url)

    if unknown_rag_links:
        preview = ", ".join(unknown_rag_links[:3])
        issues.append(
            f"RAG外URLのリンクが含まれています（最大3件表示: {preview}）。事実リンクはpayload由来URLのみ使用してください。"
        )
    if unknown_artist_links:
        preview = ", ".join(unknown_artist_links[:3])
        issues.append(
            f"payload外のArtistリンクが含まれています（最大3件表示: {preview}）。Artistリンクは候補Artist名のみ使用してください。"
        )
    if malformed_google_links:
        preview = ", ".join(malformed_google_links[:3])
        issues.append(
            f"Artistリンク形式が不正です（最大3件表示: {preview}）。[Artist Name](Google画像検索URL) 形式で統一してください。"
        )
    return issues


def _build_prompt(
    fair_label: str,
    reporter: Dict[str, object],
    angle_label: str,
    angle_description: str,
    payload: Dict[str, object],
) -> str:
    first_person = _persona_first_person(reporter)
    fair_balance_rule = "- 対象フェア外の事例を主根拠として混ぜない。"
    ex_lines = [
        f"- fair={row.get('fair')} | gallery={row.get('gallery')} | title={row.get('title')} | source_url={row.get('source_url')}"
        for row in list(payload.get("exhibition_rows", []))[:ART_PULSE_PROMPT_EXHIBITION_ROWS]
    ]
    ar_lines = [
        f"- fair={row.get('fair')} | gallery={row.get('gallery')} | artist={row.get('artist_name_en')} | source_url={row.get('source_url')} | text_snippet={str(row.get('text_snippet') or '')[:ART_PULSE_PROMPT_SNIPPET_CHARS]}"
        for row in list(payload.get("artist_rows", []))[:ART_PULSE_PROMPT_ARTIST_ROWS]
    ]
    return f"""
あなたは日本語の現代アート編集者です。以下のRAG根拠を主軸に Art Pulse 記事を作成してください。

【出力形式】
- JSONのみ:
  {{
    "title":"...",
    "body":"...",
    "selected_evidence": {{
      "section1": {{"exhibition_urls": [], "artist_urls": []}},
      "section2": {{"exhibition_urls": [], "artist_urls": []}},
      "section3": {{"exhibition_urls": [], "artist_urls": []}}
    }}
  }}

【本文ルール】
- 日本語
 - {PLAIN_JAPANESE_RULE}
- 本文テキストは理想として {ART_PULSE_TEXT_MIN_CHARS}～{ART_PULSE_TEXT_MAX_CHARS}字を目指す
- 可視文字数で理想は {ART_PULSE_TEXT_MIN_CHARS}～{ART_PULSE_TEXT_MAX_CHARS}字（MarkdownのリンクURL文字列は字数に含めない）
- ただし 3見出し・第3節の具体名・文章構造が成立している場合は、{ART_PULSE_TEXT_ACCEPTABLE_MIN_CHARS}字以上でも記事として成立する。可能なら {ART_PULSE_TEXT_MIN_CHARS}字以上まで伸ばす
- 最終出力前に可視文字数と見出し構造を自己点検し、特に {ART_PULSE_TEXT_MIN_CHARS}字未満なら不足箇所を増補してから JSON を返す
- 必ず以下の3見出しをこの順で入れる:
  1) ## 今年のトレンド
  2) ## トレンドに沿った重要なExhibitionまたはArtist
  3) ## トレンドではないが面白かったExhibitionまたはArtist
- 一人称で書く（この記者の一人称は「{first_person}」）。「Alexの視点」「◯◯の視点」などの三人称導入は禁止
- Exhibition/Artist名の羅列をしない（解説を必ず伴う）
- 同一段落・同一文の重複を禁止（末尾の繰り返し禁止）
- 第1節「今年のトレンド」は全体傾向の要約に徹し、固有名詞（展示名/作家名）は原則ゼロ。最大でも合計1件まで
- 第2節・第3節は役割を分ける。第2節は「主流トレンドに沿う重要事例」、第3節は「非主流だが重要な事例」を必ず具体名つきで示す
- 第2節と第3節で同じ事例の重複を避ける
- Exhibitionは可能な範囲で「([展示名](source_url) @ ギャラリー英名)」表記
- Exhibition名から開催日程などのノイズは削除する
- Artist表記は「[Artist Name](Google画像検索URL)（カナ読み）」を必須
- 「英名: ...」というラベルは出力しない
- カナ読みは推定でよいが、省略禁止（「（カナ未設定）」は出力禁止）
- RAG根拠（特にExhibitions Text）を厳守し、展示名・作家名・ギャラリー名・URLなどの事実主張は必ずRAG根拠内に限定する
- 補完的に、内部知識（あなたが持つ美術史、現代思想、トレンドの背景知識等、文脈に応じて）活用し、RAGに書かれていない文脈を追加し深掘りすること。
- 内部知識に基づく文脈補完部分は、出典URLの記載は不要（無理にURLを紐付けない）。
{fair_balance_rule}
- selected_evidence は、本文の各節で実際に参照した URL のみを入れる
- 画像候補は selected_evidence を基に提示されるため、機械的選択は避ける

対象フェア: {fair_label}
記者: {reporter.get('label')}（{reporter.get('description')}）
記者style: {reporter.get('style', '')}
記者tone: {reporter.get('tone', '')}
切り口: {angle_label}
切り口の説明: {angle_description}

- 抽象的・感覚的・物語的な語り口は維持してよいが、第3節の最初の段落では payload 由来の Exhibition 名と Artist 名を本文中にそのまま書き、感想だけで終わらせない
- 第3節の固有名詞は省略・言い換えを避け、名前を明示したあとで感覚や解釈を続ける

Exhibition evidence:
{chr(10).join(ex_lines) if ex_lines else '- none'}

Artist evidence:
{chr(10).join(ar_lines) if ar_lines else '- none'}
""".strip()


def _parse_llm_json(raw_text: str) -> Dict[str, object]:
    text = (raw_text or "").strip()
    if not text:
        return {}
    fenced = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE | re.DOTALL).strip()
    candidate = fenced
    if not (candidate.startswith("{") and candidate.endswith("}")):
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start >= 0 and end > start:
            candidate = candidate[start : end + 1]
    parsed = json.loads(candidate)
    if not isinstance(parsed, dict):
        return {}
    return parsed


def _extract_body_like_value(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ("body", "content", "article", "text", "answer", "main_body", "markdown"):
            nested = _extract_body_like_value(value.get(key))
            if nested:
                return nested
    return ""


def _coerce_non_json_output(raw_text: str) -> Tuple[str, str]:
    text = (raw_text or "").strip()
    if not text:
        return "", ""
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE | re.DOTALL).strip()
    if not text:
        return "", ""

    # Try JSON-like recovery first (handles malformed quotes like ""title"").
    candidates = [text]
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        candidates.append(text[start : end + 1])

    for cand in candidates:
        for probe in (cand, cand.replace('""', '"')):
            try:
                parsed = json.loads(probe)
            except Exception:
                continue
            if not isinstance(parsed, dict):
                continue
            title = str(parsed.get("title") or "").strip()
            body = _extract_body_like_value(parsed)
            if body:
                return title, body

    # Regex fallback for key-value style outputs.
    title = ""
    body = text
    title_match = re.search(r'(?is)["\']{0,2}title["\']{0,2}\s*[:：]\s*["\'](.+?)["\']\s*(?:,|$)', text)
    if title_match:
        title = str(title_match.group(1) or "").strip()

    for body_key in ("body", "content", "article", "text", "answer", "main_body", "markdown"):
        body_match = re.search(
            rf'(?is)["\']{{0,2}}{body_key}["\']{{0,2}}\s*[:：]\s*["\'](.+)',
            text,
        )
        if body_match:
            body = str(body_match.group(1) or "").strip()
            break

    body = body.replace("\\n", "\n").replace('\\"', '"').strip()

    # If markdown headings exist, prefer that range as article body.
    heading_pos = body.find("## ")
    if heading_pos >= 0:
        body = body[heading_pos:].strip()

    # Strip leaked selected_evidence fragments from malformed non-JSON outputs.
    for marker in ('"selected_evidence"', ",'selected_evidence'", ',"selected_evidence"'):
        pos = body.find(marker)
        if pos > 0:
            body = body[:pos].rstrip(" \t\r\n,}\"'")
            break

    # Non-JSON救済時の末尾断片（途中切れ）を軽減する。
    if body and body[-1] not in "。！？":
        cut = max(body.rfind("。"), body.rfind("！"), body.rfind("？"))
        if cut > 0 and (len(body) - cut) <= 220:
            body = body[: cut + 1].rstrip()

    return title, body


def _count_duplicate_paragraphs(text: str) -> int:
    paragraphs = [re.sub(r"\s+", " ", p.strip()) for p in (text or "").split("\n\n") if p.strip()]
    return len(paragraphs) - len(set(paragraphs))


def _section3_has_required_mentions(body: str, payload: Dict[str, object]) -> bool:
    sections = _split_body_by_required_headings(body)
    section3 = sections.get(REQUIRED_HEADINGS[2], "")
    if not section3:
        return False
    ex_rows = list(payload.get("exhibition_rows", []) or [])[:12]
    ar_rows = list(payload.get("artist_rows", []) or [])[:12]
    ex_tokens = [str(r.get("title") or "").strip() for r in ex_rows] + [str(r.get("source_url") or "").strip() for r in ex_rows]
    ar_tokens = [str(r.get("artist_name_en") or "").strip() for r in ar_rows] + [str(r.get("source_url") or "").strip() for r in ar_rows]
    has_ex = any(_text_contains_exactish_token(section3, t) for t in ex_tokens if t)
    has_ar = any(_text_contains_exactish_token(section3, t) for t in ar_tokens if t)
    return has_ex and has_ar


def _count_named_mentions_in_section(section_text: str, payload: Dict[str, object]) -> int:
    text = section_text or ""
    if not text:
        return 0
    hits = set()
    for row in list(payload.get("exhibition_rows", []) or []):
        title = str(row.get("title") or "").strip()
        if _text_contains_exactish_token(text, title):
            hits.add(("ex", title))
    for row in list(payload.get("artist_rows", []) or []):
        name = str(row.get("artist_name_en") or "").strip()
        if _text_contains_exactish_token(text, name):
            hits.add(("ar", name))
    return len(hits)


def _section_overlap_count(
    selection_plan: Dict[str, Dict[str, List[str]]],
    section_a: str,
    section_b: str,
) -> int:
    a_ex = set(selection_plan.get(section_a, {}).get("exhibition_urls", []) or [])
    a_ar = set(selection_plan.get(section_a, {}).get("artist_urls", []) or [])
    b_ex = set(selection_plan.get(section_b, {}).get("exhibition_urls", []) or [])
    b_ar = set(selection_plan.get(section_b, {}).get("artist_urls", []) or [])
    return len((a_ex | a_ar) & (b_ex | b_ar))


def _validate_main_body(
    body: str,
    payload: Dict[str, object],
    selection_plan: Dict[str, Dict[str, List[str]]] | None = None,
    fair_label: str = "",
) -> List[str]:
    issues: List[str] = []
    if not body.strip():
        issues.append("本文が空です。")
        return issues
    if not _has_required_structure(body):
        issues.append("3見出し構成が不足しています。")
    chars = _body_text_len(body)
    if chars < ART_PULSE_TEXT_MIN_CHARS:
        issues.append(f"本文文字数が不足しています（{chars}字）。1800字以上にしてください。")
    soft_max = ART_PULSE_TEXT_MAX_CHARS + ART_PULSE_TEXT_SOFT_OVER_CHARS
    if chars > soft_max:
        issues.append(f"本文文字数が超過しています（{chars}字）。{soft_max}字以内にしてください。")
    if _count_duplicate_paragraphs(body) > 0:
        issues.append("同一段落の重複があります。重複を除去してください。")
    if "（カナ未設定）" in body:
        issues.append("Artistのカナ読みが未設定です。全Artist表記にカナ読みを入れてください。")
    if ARTIST_DUP_EN_NAME_PATTERN.search(body):
        issues.append("Artist表記で英名の重複括弧があります。重複を削除し、カナ読みのみを括弧で表示してください。")
    artist_links = ARTIST_GOOGLE_LINK_PATTERN.findall(body)
    artist_with_kana = ARTIST_WITH_KANA_PATTERN.findall(body)
    if artist_links and len(artist_with_kana) < len(artist_links):
        issues.append(
            "Artist表記は全件「[Artist Name](Google画像検索URL)（カナ読み）」形式にしてください。"
        )
    if not _section3_has_required_mentions(body, payload):
        issues.append("第3節に Exhibition と Artist の具体名が不足しています。")
    issues.extend(_validate_links_against_payload(body, payload))

    sections = _split_body_by_required_headings(body)
    if sections:
        section1_text = sections.get(REQUIRED_HEADINGS[0], "")
        named_in_section1 = _count_named_mentions_in_section(section1_text, payload)
        if named_in_section1 > 1:
            issues.append("第1節（今年のトレンド）で固有名詞が多すぎます。展示名/作家名は合計1件以内にしてください。")

    if selection_plan:
        overlap = _section_overlap_count(selection_plan, "section2", "section3")
        if overlap > 0:
            issues.append("第2節と第3節で同一根拠URLが重複しています。役割分担のため重複を避けてください。")

    return issues


def _build_expansion_prompt(
    fair_label: str,
    reporter: Dict[str, object],
    angle_label: str,
    angle_description: str,
    payload: Dict[str, object],
    previous_title: str,
    previous_body: str,
    previous_selected_evidence: Dict[str, Dict[str, List[str]]],
    issues: List[str],
) -> str:
    current_chars = _body_text_len(previous_body)
    shortage = max(0, ART_PULSE_TEXT_MIN_CHARS - current_chars)
    soft_max = ART_PULSE_TEXT_MAX_CHARS + ART_PULSE_TEXT_SOFT_OVER_CHARS
    issue_text = "\n".join([f"- {issue}" for issue in issues]) if issues else "- なし"
    length_only_candidate = (
        current_chars < ART_PULSE_TEXT_MIN_CHARS
        and _has_required_structure(previous_body)
        and _section3_has_required_mentions(previous_body, payload)
        and not _has_structural_fragment_artifacts(previous_body)
    )
    section_extension_notes = _build_section_extension_priority_notes(previous_body)
    return (
        _build_prompt(fair_label, reporter, angle_label, angle_description, payload)
        + "\n\n【後段リライト指示（文字数拡張）】\n"
        + f"- 現在の可視文字数: {current_chars}字（不足: {shortage}字）\n"
        + f"- 可視文字数は理想として {ART_PULSE_TEXT_MIN_CHARS}字以上へ増やす（{ART_PULSE_TEXT_MAX_CHARS}字は目安、上限は{soft_max}字まで許容）\n"
        + f"- ただし 3見出しと第3節が成立している稿は、{ART_PULSE_TEXT_ACCEPTABLE_MIN_CHARS}字以上なら壊さず保持しつつ理想値へ近づける\n"
        + "- 見出し構成と節の役割（第1節=総論、第2節=主流重要、第3節=非主流重要）を維持する\n"
        + "- 既に成立している節は壊さず、足りない節や不足している段落だけを重点的に補う\n"
        + (
            "- 今回は 3見出しと第3節の固有名詞条件がすでに成立しているため、見出し順を固定し、全文を書き直さず、既存3節・既存の Exhibition 名・Artist 名・段落順を保持したまま不足文字数だけを増補する\n"
            if length_only_candidate
            else ""
        )
        + (
            "- 特に不足している節へ、理由・比較・背景説明を追記して伸ばす。既存の固有名詞を消したり、見出し数を減らしたりしない\n"
            if length_only_candidate
            else ""
        )
        + (
            "".join([f"{note}\n" for note in section_extension_notes])
            if length_only_candidate
            else ""
        )
        + f"- 各節の可視文字数下限: 第1節{ART_PULSE_SECTION1_MIN_CHARS}字以上 / 第2節{ART_PULSE_SECTION2_MIN_CHARS}字以上 / 第3節{ART_PULSE_SECTION3_MIN_CHARS}字以上\n"
        + "- 事実追加は禁止。payload外のURL/展示名/作家名/ギャラリー名を新規追加しない\n"
        + "- selected_evidence は本文で実際に使っているURLだけに揃える\n"
        + _build_recovery_target_block(previous_body, payload)
        + "\n【前回稿の問題点】\n"
        + issue_text
        + "\n\n【前回稿】\n"
        + json.dumps(
            {
                "title": previous_title,
                "body": previous_body,
                "selected_evidence": previous_selected_evidence,
            },
            ensure_ascii=False,
        )
    )


def _should_run_structural_salvage(previous_body: str, hard_issues: List[str]) -> bool:
    text = (previous_body or "").strip()
    if not text or not hard_issues:
        return False
    for issue in hard_issues:
        if issue.startswith("本文文字数が不足しています"):
            continue
        if issue in {
            "3見出し構成が不足しています。",
            "第3節に Exhibition と Artist の具体名が不足しています。",
        }:
            continue
        return False
    return True


def _body_missing_required_headings(body: str) -> List[str]:
    text = (body or "").strip()
    return [heading for heading in REQUIRED_HEADINGS if heading not in text]


def _section3_candidate_notes(payload: Dict[str, object]) -> List[str]:
    exhibition_names: List[str] = []
    for row in list(payload.get("exhibition_rows", []) or []):
        title = str(row.get("title") or "").strip()
        if not title or title in exhibition_names:
            continue
        exhibition_names.append(title)
        if len(exhibition_names) >= 3:
            break

    artist_names: List[str] = []
    for row in list(payload.get("artist_rows", []) or []):
        artist_name = _clean_artist_name(str(row.get("artist_name_en") or row.get("artist") or ""))
        if not artist_name or artist_name in artist_names:
            continue
        artist_names.append(artist_name)
        if len(artist_names) >= 3:
            break

    notes: List[str] = []
    if exhibition_names:
        notes.append("- 第3節で使える候補Exhibition: " + " / ".join(exhibition_names))
    if artist_names:
        notes.append("- 第3節で使える候補Artist: " + " / ".join(artist_names))
    if exhibition_names and artist_names:
        pair_notes: List[str] = []
        for idx in range(min(2, len(exhibition_names), len(artist_names))):
            pair_notes.append(
                f"Exhibition「{exhibition_names[idx]}」と Artist「{artist_names[idx]}」"
            )
        if pair_notes:
            notes.append("- 第3節で自然文に入れる候補ペア: " + " / ".join(pair_notes))
    return notes


def _build_recovery_target_block(body: str, payload: Dict[str, object]) -> str:
    current_chars = _body_text_len(body)
    shortage = max(0, ART_PULSE_TEXT_MIN_CHARS - current_chars)
    missing_headings = _body_missing_required_headings(body)
    sections = _split_body_by_required_headings(body)
    section_char_notes = [
        f"第1節={_body_text_len(sections.get(REQUIRED_HEADINGS[0], ''))}字",
        f"第2節={_body_text_len(sections.get(REQUIRED_HEADINGS[1], ''))}字",
        f"第3節={_body_text_len(sections.get(REQUIRED_HEADINGS[2], ''))}字",
    ]
    section_extension_notes = _build_section_extension_priority_notes(body)
    section3_ok = _section3_has_required_mentions(body, payload)
    lines = [
        "",
        "【今回の回復 target】",
        f"- 現在の可視文字数: {current_chars}字",
        f"- 理想文字数: {ART_PULSE_TEXT_MIN_CHARS}字",
        f"- 受理下限文字数: {ART_PULSE_TEXT_ACCEPTABLE_MIN_CHARS}字",
        f"- 理想値まで追加で必要な文字数: {shortage}字",
        f"- 現在の見出し数: {_count_required_headings_present(body)}/3",
        f"- 欠けている見出し: {', '.join(missing_headings) if missing_headings else 'なし'}",
        f"- 第3節の具体名条件: {'OK' if section3_ok else '不足'}",
        f"- 現在の各節文字数: {' / '.join(section_char_notes)}",
    ]
    if not missing_headings and section3_ok:
        lines.append("- 既存稿ですでに3見出しと第3節の固有名詞条件が成立している場合は、その構造と固有名詞を保持したまま増補だけを行う。")
        lines.append("- 既存の Exhibition 名・Artist 名・見出しを消さず、文字数が不足している節にだけ説明・比較・補足を加える。")
    if missing_headings:
        lines.append("- 欠けている見出しは独立した節として追加し、第2節と第3節を混同しない。")
    lines.extend(section_extension_notes)
    if REQUIRED_HEADINGS[1] in missing_headings or _body_text_len(sections.get(REQUIRED_HEADINGS[1], "")) < ART_PULSE_SECTION2_MIN_CHARS:
        lines.append("- 第2節は「トレンドに沿った重要なExhibitionまたはArtist」を独立節として成立させる。")
    if (
        REQUIRED_HEADINGS[2] in missing_headings
        or not section3_ok
        or _body_text_len(sections.get(REQUIRED_HEADINGS[2], "")) < ART_PULSE_SECTION3_MIN_CHARS
    ):
        lines.append("- 第3節は「トレンドではないが面白かったExhibitionまたはArtist」を独立節として成立させる。")
        lines.append("- 第3節には Exhibition 名と Artist 名を最低1件ずつ、本文中の自然な文で明示する。")
        lines.append("- 第3節で使う Exhibition 名と Artist 名は、payload 候補の表記を省略・言い換えせず、そのまま本文に入れる。")
        lines.append("- 第3節の最初の段落の冒頭寄りで、選んだ Exhibition 名と Artist 名を先に明示し、その後に感覚・解釈・評価を続ける。")
        lines.append("- 可能なら第3節の同じ段落の中で、選んだ Exhibition 名と Artist 名の両方を自然につなげて書く。")
        lines.extend(_section3_candidate_notes(payload))
    return "\n" + "\n".join(lines)


def _has_structural_fragment_artifacts(body: str) -> bool:
    text = (body or "").strip()
    if not text:
        return True
    suspicious_markers = (
        '"selected_evidence"',
        '\\"selected_evidence\\"',
        '"memory_summary"',
        '\\"memory_summary\\"',
        "```",
    )
    if any(marker in text for marker in suspicious_markers):
        return True
    if re.search(r'(?i)"(?:title|body)"\s*:', text):
        return True
    return False


def _is_length_only_candidate(body: str, payload: Dict[str, object], hard_issues: List[str]) -> bool:
    text = (body or "").strip()
    if not text:
        return False
    if any(not issue.startswith("本文文字数が不足しています") for issue in hard_issues):
        return False
    if not _has_required_structure(text):
        return False
    if not _section3_has_required_mentions(text, payload):
        return False
    if _has_structural_fragment_artifacts(text):
        return False
    return _body_text_len(text) < ART_PULSE_TEXT_MIN_CHARS


def _is_structured_grounded_seed_candidate(body: str, payload: Dict[str, object]) -> bool:
    text = (body or "").strip()
    if not text:
        return False
    if not _has_required_structure(text):
        return False
    if not _section3_has_required_mentions(text, payload):
        return False
    if _has_structural_fragment_artifacts(text):
        return False
    return True


def _build_section_extension_priority_notes(body: str) -> List[str]:
    sections = _split_body_by_required_headings(body)
    shortages: List[Tuple[int, int, str, int]] = []
    for heading, label, min_chars in (
        (REQUIRED_HEADINGS[0], "第1節", ART_PULSE_SECTION1_MIN_CHARS),
        (REQUIRED_HEADINGS[1], "第2節", ART_PULSE_SECTION2_MIN_CHARS),
        (REQUIRED_HEADINGS[2], "第3節", ART_PULSE_SECTION3_MIN_CHARS),
    ):
        section_chars = _body_text_len(sections.get(heading, ""))
        shortage = max(0, min_chars - section_chars)
        if shortage > 0:
            shortages.append((section_chars, -shortage, label, shortage))

    if not shortages:
        return []

    shortages.sort(key=lambda row: (row[0], row[1], row[2]))
    notes = ["- 増補順は「現在最も短い節→次に短い節」。不足分だけを追記し、全文を書き換えない。"]
    for _, __, label, shortage in shortages:
        notes.append(f"- {label}を優先し、まず +{shortage}字以上を目安に増補する。")
    return notes


def _should_update_last_seed_candidate(candidate_body: str, baseline_body: str, payload: Dict[str, object]) -> bool:
    candidate = (candidate_body or "").strip()
    if not candidate:
        return False

    baseline = (baseline_body or "").strip()
    if not baseline:
        return True

    baseline_heading_count = _count_required_headings_present(baseline)
    candidate_heading_count = _count_required_headings_present(candidate)
    if baseline_heading_count >= 3 and candidate_heading_count < baseline_heading_count:
        return False

    if _is_structured_grounded_seed_candidate(baseline, payload) and not _is_structured_grounded_seed_candidate(candidate, payload):
        return False

    if not _has_structural_fragment_artifacts(baseline) and _has_structural_fragment_artifacts(candidate):
        return False

    return True


def _is_acceptable_pass_candidate(body: str, payload: Dict[str, object], hard_issues: List[str]) -> bool:
    text = (body or "").strip()
    if not _is_length_only_candidate(text, payload, hard_issues):
        return False
    if _body_text_len(text) < ART_PULSE_TEXT_ACCEPTABLE_MIN_CHARS:
        return False
    if _count_duplicate_paragraphs(text) > 0:
        return False
    return True


def _is_near_pass_candidate(body: str, payload: Dict[str, object], hard_issues: List[str]) -> bool:
    text = (body or "").strip()
    if not text:
        return False
    if any(not issue.startswith("本文文字数が不足しています") for issue in hard_issues):
        return False
    if not _has_required_structure(text):
        return False
    if not _section3_has_required_mentions(text, payload):
        return False
    if _body_text_len(text) < 1500:
        return False
    if _count_duplicate_paragraphs(text) > 0:
        return False
    if _has_structural_fragment_artifacts(text):
        return False
    return True


def _is_non_empty_fallback_candidate(body: str) -> bool:
    text = (body or "").strip()
    if not text:
        return False
    if _has_structural_fragment_artifacts(text):
        return False
    if _count_duplicate_paragraphs(text) > 1:
        return False
    if _count_required_headings_present(text) == 0 and _body_text_len(text) < 180:
        return False
    return True


def _non_empty_candidate_score(
    body: str,
    payload: Dict[str, object],
    hard_issues: List[str],
    soft_issues: List[str],
) -> Tuple[int, int, int, int, int, int]:
    text = (body or "").strip()
    if not text:
        return (-1, -1, -1, -999, -999, -999)
    return (
        int(_has_required_structure(text)),
        int(_section3_has_required_mentions(text, payload)),
        _count_required_headings_present(text),
        _body_text_len(text),
        -len(hard_issues),
        -len(soft_issues),
    )


def _recovery_seed_score(
    body: str,
    payload: Dict[str, object],
    hard_issues: List[str],
    soft_issues: List[str],
) -> Tuple[int, int, int, int, int, int, int, int]:
    text = (body or "").strip()
    if not text:
        return (-1, -1, -1, -999, -999, -999, -999, -999)
    sections = _split_body_by_required_headings(text)
    section2_chars = _body_text_len(sections.get(REQUIRED_HEADINGS[1], ""))
    section3_chars = _body_text_len(sections.get(REQUIRED_HEADINGS[2], ""))
    return (
        int(_has_required_structure(text)),
        int(_section3_has_required_mentions(text, payload)),
        _count_required_headings_present(text),
        -len(hard_issues),
        section3_chars,
        section2_chars,
        _body_text_len(text),
        -len(soft_issues),
    )


def _build_salvage_prompt(
    fair_label: str,
    reporter: Dict[str, object],
    angle_label: str,
    angle_description: str,
    payload: Dict[str, object],
    previous_title: str,
    previous_body: str,
    previous_selected_evidence: Dict[str, Dict[str, List[str]]],
    issues: List[str],
) -> str:
    issue_text = "\n".join([f"- {issue}" for issue in issues]) if issues else "- なし"
    length_only_candidate = (
        _body_text_len(previous_body) < ART_PULSE_TEXT_MIN_CHARS
        and _has_required_structure(previous_body)
        and _section3_has_required_mentions(previous_body, payload)
        and not _has_structural_fragment_artifacts(previous_body)
    )
    section_extension_notes = _build_section_extension_priority_notes(previous_body)
    return (
        _build_expansion_prompt(
            fair_label=fair_label,
            reporter=reporter,
            angle_label=angle_label,
            angle_description=angle_description,
            payload=payload,
            previous_title=previous_title,
            previous_body=previous_body,
            previous_selected_evidence=previous_selected_evidence,
            issues=issues,
        )
        + "\n\n【構造回復 salvage 指示】\n"
        + "- これは block 直前の回復用パスです。前回稿の論旨・文体・使える記述を最大限活かし、全面書き直しはしないでください。\n"
        + "- 必ず次の3見出しを、この表記のまま1文字も変えずに使ってください。\n"
        + "".join([f"  - {heading}\n" for heading in REQUIRED_HEADINGS])
        + "- 不足している箇所だけを補って、最終的に3見出し構成を必ず成立させてください。\n"
        + "- 既に成立している節は壊さず、欠けている節や不足している段落だけを補ってください。\n"
        + (
            "- 今回は length-only 回復です。見出し順を固定し、既存の3見出し・Exhibition 名・Artist 名・段落順を保持したまま、全文を書き換えず不足文字数だけを増補してください。\n"
            if length_only_candidate
            else ""
        )
        + f"- 可視文字数が不足している場合は、同じ論旨のまま説明・比較・理由づけを補って理想の {ART_PULSE_TEXT_MIN_CHARS}字以上へ増補してください。\n"
        + (
            "- 既存の固有名詞を消さず、文字数が不足している節へ説明・比較・背景だけを足してください。\n"
            if length_only_candidate
            else ""
        )
        + (
            "".join([f"{note}\n" for note in section_extension_notes])
            if length_only_candidate
            else ""
        )
        + "- 第3節には payload 内の具体的な Exhibition 名を少なくとも1件、Artist 名を少なくとも1件、本文中に必ず明示してください。\n"
        + "- 長さ不足だけが残る run にも対応し、第1節〜第3節へバランスよく説明を足してください。抽象的な言い換えだけで終わらせないでください。\n"
        + "- 返すのは差分ではなく、修復後の title/body/selected_evidence 全体です。\n"
        + "\n【この salvage で必ず解消する hard issue】\n"
        + issue_text
    )


def _build_generation_constraints() -> str:
    target_min = ART_PULSE_TARGET_CHARS - ART_PULSE_TARGET_TOLERANCE
    target_max = ART_PULSE_TARGET_CHARS + ART_PULSE_TARGET_TOLERANCE
    return (
        "\n\n[OUTPUT HARD CONSTRAINTS]\n"
        "- Return JSON only, with keys: title, body, selected_evidence.\n"
        f"- Target body length: around {ART_PULSE_TARGET_CHARS} chars (acceptable {target_min}-{target_max}).\n"
        f"- Ideal body length is at least {ART_PULSE_TEXT_MIN_CHARS} chars.\n"
        f"- If the article keeps all 3 required headings, Section3 grounding, no structural fragments, and no duplicate paragraphs, {ART_PULSE_TEXT_ACCEPTABLE_MIN_CHARS}+ chars can still be accepted.\n"
        "- Use exactly 3 sections with required headings.\n"
        "- Section1 should be trend analysis (no excessive proper nouns).\n"
        "- Section2 should include concrete Exhibition/Artist names and reasoning.\n"
        "- Section3 should include at least one concrete Exhibition and one Artist.\n"
        "- In Section3, write one payload Exhibition title and one payload Artist name verbatim in natural Japanese sentences.\n"
        f"- Minimum section lengths: section1 >= {ART_PULSE_SECTION1_MIN_CHARS}, section2 >= {ART_PULSE_SECTION2_MIN_CHARS}, section3 >= {ART_PULSE_SECTION3_MIN_CHARS} chars.\n"
        "- Keep all three sections substantial; avoid short summaries.\n"
        "- Recommended length balance: Section1 25-35%, Section2 30-40%, Section3 30-40%.\n"
        "- Keep selected_evidence aligned with URLs actually cited in body.\n"
    )


def _art_pulse_output_schema() -> Dict[str, object]:
    section_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "exhibition_urls": {"type": "array", "items": {"type": "string"}},
            "artist_urls": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["exhibition_urls", "artist_urls"],
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "title": {"type": "string"},
            "body": {"type": "string"},
            "selected_evidence": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "section1": section_schema,
                    "section2": section_schema,
                    "section3": section_schema,
                },
                "required": ["section1", "section2", "section3"],
            },
        },
        "required": ["title", "body", "selected_evidence"],
    }


class _ArtPulseResponseProxy:
    def __init__(self, response, output_text: str):
        self._response = response
        self.output_text = output_text
        self.status = getattr(response, "status", None)
        self.incomplete_details = getattr(response, "incomplete_details", None)

    def __getattr__(self, name: str):
        return getattr(self._response, name)


def _response_text_is_empty(response) -> bool:
    return not str(getattr(response, "output_text", "") or "").strip()


def _response_incomplete_reason(response) -> str:
    incomplete = getattr(response, "incomplete_details", None)
    if isinstance(incomplete, dict):
        return str(incomplete.get("reason") or "").strip()
    return str(getattr(incomplete, "reason", "") or "").strip()


def _extract_text_from_response_output(response) -> str:
    if response is None or not hasattr(response, "model_dump"):
        return ""

    texts: List[str] = []

    def _walk(node: object) -> None:
        if isinstance(node, dict):
            node_type = str(node.get("type") or "").strip()
            node_text = str(node.get("text") or "").strip()
            if node_type in {"output_text", "text"} and node_text:
                texts.append(node_text)
            for value in node.values():
                _walk(value)
            return
        if isinstance(node, list):
            for item in node:
                _walk(item)

    try:
        dump = response.model_dump()
    except Exception:
        return ""

    _walk(dump.get("output"))
    return "\n".join(text for text in texts if text).strip()


def _response_with_best_text(response):
    output_text = str(getattr(response, "output_text", "") or "").strip()
    if output_text:
        return response
    structured_text = _extract_text_from_response_output(response)
    if structured_text:
        return _ArtPulseResponseProxy(response, structured_text)
    return response


def _create_art_pulse_response(client, model: str, prompt: str):
    response = _response_with_best_text(
        client.responses.create(
            model=model,
            input=prompt,
            max_output_tokens=ART_PULSE_MAX_OUTPUT_TOKENS,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "art_pulse_draft",
                    "strict": True,
                    "schema": _art_pulse_output_schema(),
                }
            },
        )
    )
    if not _response_text_is_empty(response):
        return response

    if _response_incomplete_reason(response) != "max_output_tokens":
        return response

    try:
        rescue = _response_with_best_text(
            client.responses.create(
                model=model,
                input=prompt,
                max_output_tokens=ART_PULSE_MAX_OUTPUT_TOKENS,
                reasoning={"effort": "low"},
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "art_pulse_draft",
                        "strict": True,
                        "schema": _art_pulse_output_schema(),
                    }
                },
            )
        )
        if not _response_text_is_empty(rescue):
            return rescue
    except Exception:
        rescue = None

    try:
        plain_rescue = _response_with_best_text(
            client.responses.create(
                model=model,
                input=prompt,
                max_output_tokens=ART_PULSE_MAX_OUTPUT_TOKENS,
                reasoning={"effort": "low"},
            )
        )
        if not _response_text_is_empty(plain_rescue):
            return plain_rescue
    except Exception:
        pass

    return rescue or response


def _validate_main_body_hard_soft(
    body: str,
    payload: Dict[str, object],
    selection_plan: Dict[str, Dict[str, List[str]]] | None = None,
    fair_label: str = "",
) -> Tuple[List[str], List[str]]:
    hard_issues: List[str] = []
    soft_issues: List[str] = []
    text = (body or "").strip()
    if not text:
        hard_issues.append("本文が空です。")
        return hard_issues, soft_issues

    if not _has_required_structure(text):
        hard_issues.append("3見出し構成が不足しています。")

    chars = _body_text_len(text)
    if chars < ART_PULSE_TEXT_MIN_CHARS:
        hard_issues.append(f"本文文字数が不足しています（{chars}字）。{ART_PULSE_TEXT_MIN_CHARS}字以上にしてください。")

    soft_max = ART_PULSE_TEXT_MAX_CHARS + ART_PULSE_TEXT_SOFT_OVER_CHARS
    if chars > soft_max:
        soft_issues.append(f"本文文字数が上限超過です（{chars}字）。{soft_max}字以下を推奨します。")

    if _count_duplicate_paragraphs(text) > 0:
        soft_issues.append("同一段落の重複があります。重複を除去してください。")

    if not _section3_has_required_mentions(text, payload):
        hard_issues.append("第3節に Exhibition と Artist の具体名が不足しています。")

    soft_issues.extend(_validate_links_against_payload(text, payload))

    sections = _split_body_by_required_headings(text)
    if sections:
        section_min_rules = [
            ("第1節", REQUIRED_HEADINGS[0], ART_PULSE_SECTION1_MIN_CHARS),
            ("第2節", REQUIRED_HEADINGS[1], ART_PULSE_SECTION2_MIN_CHARS),
            ("第3節", REQUIRED_HEADINGS[2], ART_PULSE_SECTION3_MIN_CHARS),
        ]
        for section_label, heading, min_chars in section_min_rules:
            section_chars = _body_text_len(sections.get(heading, ""))
            if section_chars < min_chars:
                soft_issues.append(f"{section_label}の文字数が不足しています（{section_chars}字）。{min_chars}字以上にしてください。")

        section1_text = sections.get(REQUIRED_HEADINGS[0], "")
        named_in_section1 = _count_named_mentions_in_section(section1_text, payload)
        if named_in_section1 > 1:
            soft_issues.append("第1節はトレンド分析中心にし、固有名詞の列挙を抑えてください。")

    if selection_plan:
        overlap = _section_overlap_count(selection_plan, "section2", "section3")
        if overlap > 0:
            soft_issues.append("第2節と第3節で同一URLが重複しています。")

    return hard_issues, soft_issues


def generate_art_pulse_draft(
    overview: Dict[str, object],
    reporter_id: str,
    angle_keys: List[str],
    progress_callback: Callable[[int], None] | None = None,
) -> Dict[str, object]:
    started_at = time.perf_counter()
    openai_elapsed_ms = 0

    def _emit_progress(pct: int) -> None:
        if progress_callback:
            try:
                progress_callback(max(0, min(100, int(pct))))
            except Exception:
                pass

    selection = overview.get("selection", {})
    fair_label = str(selection.get("fair_label") or "Frieze London + Liste Art Fair Basel")
    reporter = find_persona(reporter_id)
    angle_key, angle_label, angle_description = _pick_angle(reporter, angle_keys)
    _emit_progress(30)
    payload = _build_evidence_payload(overview, cap=ART_PULSE_PAYLOAD_CANDIDATE_CAP)

    model = os.getenv("TEXT_MODEL", "gpt-5-mini")
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    mode = "no_api_key"
    title = ""
    main_body = ""
    selected_plan = _empty_selection_plan()
    warnings: List[str] = []
    debug_trace: List[Dict[str, object]] = []
    retry_metrics = {
        "attempts_total": 0,
        "expand_attempts_total": 0,
        "salvage_attempts_total": 0,
        "json_parse_fail": 0,
        "empty_title_body": 0,
        "validation_fail": 0,
        "expand_validation_fail": 0,
        "salvage_validation_fail": 0,
        "selected_evidence_empty": 0,
        "success_attempt": 0,
    }

    if not api_key:
        warnings.append("OPENAI_API_KEY が未設定のため、Art Pulse 本文を生成できません。")
    else:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            prompt = _build_prompt(fair_label, reporter, angle_label, angle_description, payload) + _build_generation_constraints()
            last_title = ""
            last_body = ""
            last_selected_plan = _empty_selection_plan()
            last_hard_issues: List[str] = []
            last_issues: List[str] = []
            recovery_seed_title = ""
            recovery_seed_body = ""
            recovery_seed_selection = _empty_selection_plan()
            recovery_seed_hard_issues: List[str] = []
            recovery_seed_issues: List[str] = []
            recovery_seed_score = (-1, -1, -1, -999, -999, -999, -999, -999)
            best_length_only_title = ""
            best_length_only_body = ""
            best_length_only_selection = _empty_selection_plan()
            best_length_only_issues: List[str] = []
            best_length_only_soft_issues: List[str] = []
            best_length_only_score = (-1, -1)
            best_acceptable_title = ""
            best_acceptable_body = ""
            best_acceptable_selection = _empty_selection_plan()
            best_acceptable_soft_issues: List[str] = []
            best_acceptable_score = (-1, -1)
            best_valid_title = ""
            best_valid_body = ""
            best_valid_selection = _empty_selection_plan()
            best_valid_soft_issues: List[str] = []
            best_valid_score = (-1, -1)
            best_non_empty_title = ""
            best_non_empty_body = ""
            best_non_empty_selection = _empty_selection_plan()
            best_non_empty_issues: List[str] = []
            best_non_empty_soft_issues: List[str] = []
            best_non_empty_score = (-1, -1, -1, -999, -999, -999)
            near_pass_title = ""
            near_pass_body = ""
            near_pass_selection = _empty_selection_plan()
            near_pass_soft_issues: List[str] = []
            near_pass_score = (-1, -1)
            max_attempts = 1
            max_expand_attempts = 2
            max_salvage_attempts = 1

            for attempt in range(1, max_attempts + 1):
                # 35-85% を執筆リトライ枠に割り当てる
                attempt_pct = 35 + int(((attempt - 1) / max_attempts) * 50)
                _emit_progress(attempt_pct)
                retry_metrics["attempts_total"] += 1
                _openai_t0 = time.perf_counter()
                response = _create_art_pulse_response(client, model, prompt)
                openai_elapsed_ms += int((time.perf_counter() - _openai_t0) * 1000)
                raw = (response.output_text or "").strip()
                parsed: Dict[str, object] = {}
                cand_from_non_json = False
                try:
                    parsed = _parse_llm_json(raw)
                    cand_title = str(parsed.get("title") or "").strip()
                    cand_body = _extract_body_like_value(parsed)
                except Exception as exc:
                    retry_metrics["json_parse_fail"] += 1
                    warnings.append(f"attempt_{attempt}: JSON解析失敗({type(exc).__name__})")
                    debug_trace.append(
                        {
                            "stage": "attempt",
                            "attempt": attempt,
                            "status": "json_parse_fail",
                            "error": type(exc).__name__,
                            "raw_preview": raw[:240],
                        }
                    )
                    cand_title, cand_body = _coerce_non_json_output(raw)
                    if cand_body:
                        warnings.append(f"attempt_{attempt}: JSON以外の出力を本文として解釈")
                        cand_from_non_json = True
                    else:
                        prompt = (
                            _build_prompt(fair_label, reporter, angle_label, angle_description, payload)
                            + "\n\nJSON形式を厳守してください。"
                        )
                        continue

                if not cand_body:
                    salvage_title, salvage_body = _coerce_non_json_output(raw)
                    if salvage_body:
                        cand_title = cand_title or salvage_title
                        cand_body = salvage_body
                        cand_from_non_json = True
                        warnings.append(f"attempt_{attempt}: 非JSON救済を優先して本文を採用")

                if not cand_body:
                    retry_metrics["empty_title_body"] += 1
                    warnings.append(f"attempt_{attempt}: title/body が空です")
                    debug_trace.append(
                        {
                            "stage": "attempt",
                            "attempt": attempt,
                            "status": "empty_title_body",
                        }
                    )
                    prompt = (
                        _build_prompt(fair_label, reporter, angle_label, angle_description, payload)
                        + "\n\ntitle と body を必ず埋めてください。"
                    )
                    continue

                cand_selection = _infer_selected_evidence_from_body(cand_body, payload)
                if _count_selection_urls(cand_selection) == 0:
                    cand_selection = _build_image_seed_selection(payload, overview)

                baseline_seed_body = best_length_only_body or recovery_seed_body or last_body
                if _should_update_last_seed_candidate(cand_body, baseline_seed_body, payload):
                    last_title, last_body = cand_title, cand_body
                    last_selected_plan = cand_selection

                hard_issues, soft_issues = _validate_main_body_hard_soft(
                    cand_body,
                    payload,
                    selection_plan=cand_selection,
                    fair_label=fair_label,
                )
                issues = list(hard_issues)
                if _count_selection_urls(cand_selection) == 0:
                    retry_metrics["selected_evidence_empty"] += 1
                    soft_issues.append(
                        "selected_evidence が本文に対応していません。本文で参照したURLを selected_evidence に必ず入れてください。"
                    )
                if _is_non_empty_fallback_candidate(cand_body):
                    candidate_score = _non_empty_candidate_score(cand_body, payload, issues, soft_issues)
                    if candidate_score > best_non_empty_score:
                        best_non_empty_title = cand_title
                        best_non_empty_body = cand_body
                        best_non_empty_selection = cand_selection
                        best_non_empty_issues = list(issues + soft_issues)
                        best_non_empty_soft_issues = list(soft_issues)
                        best_non_empty_score = candidate_score
                last_hard_issues = list(issues)
                last_issues = list(issues + soft_issues)
                cand_chars = _body_text_len(cand_body)
                candidate_seed_score = _recovery_seed_score(cand_body, payload, issues, soft_issues)
                if candidate_seed_score > recovery_seed_score:
                    recovery_seed_title = cand_title
                    recovery_seed_body = cand_body
                    recovery_seed_selection = cand_selection
                    recovery_seed_hard_issues = list(issues)
                    recovery_seed_issues = list(issues + soft_issues)
                    recovery_seed_score = candidate_seed_score
                if _is_length_only_candidate(cand_body, payload, issues):
                    candidate_score = (cand_chars, -len(soft_issues))
                    if candidate_score > best_length_only_score:
                        best_length_only_title = cand_title
                        best_length_only_body = cand_body
                        best_length_only_selection = cand_selection
                        best_length_only_issues = list(issues + soft_issues)
                        best_length_only_soft_issues = list(soft_issues)
                        best_length_only_score = candidate_score
                if _is_acceptable_pass_candidate(cand_body, payload, issues):
                    candidate_score = (cand_chars, -len(soft_issues))
                    if candidate_score > best_acceptable_score:
                        best_acceptable_title = cand_title
                        best_acceptable_body = cand_body
                        best_acceptable_selection = cand_selection
                        best_acceptable_soft_issues = list(soft_issues)
                        best_acceptable_score = candidate_score
                debug_trace.append(
                    {
                        "stage": "attempt",
                        "attempt": attempt,
                        "status": "validated" if not issues else "validation_fail",
                        "chars": cand_chars,
                        "issue_count": len(issues) + len(soft_issues),
                        "hard_issues": list(issues[:8]),
                        "soft_issues": list(soft_issues[:8]),
                    }
                )
                if _is_near_pass_candidate(cand_body, payload, issues):
                    candidate_score = (cand_chars, -len(soft_issues))
                    if candidate_score > near_pass_score:
                        near_pass_title = cand_title
                        near_pass_body = cand_body
                        near_pass_selection = cand_selection
                        near_pass_soft_issues = list(soft_issues)
                        near_pass_score = candidate_score

                if not issues:
                    candidate_score = (cand_chars, -len(soft_issues))
                    if candidate_score > best_valid_score:
                        best_valid_title = cand_title
                        best_valid_body = cand_body
                        best_valid_selection = cand_selection
                        best_valid_soft_issues = list(soft_issues)
                        best_valid_score = candidate_score
                    title, main_body = best_valid_title, best_valid_body
                    selected_plan = best_valid_selection
                    mode = "openai"
                    if best_valid_soft_issues:
                        warnings.append(f"attempt_{attempt}: " + " / ".join(best_valid_soft_issues))
                    retry_metrics["success_attempt"] = attempt
                    break

                _emit_progress(90)
                retry_metrics["validation_fail"] += 1
                warnings.append(f"attempt_{attempt}: " + " / ".join(issues + soft_issues))

            if not main_body:
                if recovery_seed_body and recovery_seed_hard_issues and max_expand_attempts > 0:
                    expand_source_title = best_length_only_title or best_non_empty_title or recovery_seed_title or last_title
                    expand_source_body = best_length_only_body or best_non_empty_body or recovery_seed_body
                    expand_source_selection = (
                        best_length_only_selection
                        if best_length_only_body
                        else (best_non_empty_selection if best_non_empty_body else recovery_seed_selection)
                    )
                    expand_source_issues = best_length_only_issues or best_non_empty_issues or recovery_seed_issues or last_issues
                    expand_prompt = _build_expansion_prompt(
                        fair_label=fair_label,
                        reporter=reporter,
                        angle_label=angle_label,
                        angle_description=angle_description,
                        payload=payload,
                        previous_title=expand_source_title,
                        previous_body=expand_source_body,
                        previous_selected_evidence=expand_source_selection,
                        issues=expand_source_issues,
                    )
                    expand_prompt += _build_generation_constraints()
                    for expand_attempt in range(1, max_expand_attempts + 1):
                        _emit_progress(88 + int((expand_attempt / max_expand_attempts) * 6))
                        retry_metrics["attempts_total"] += 1
                        retry_metrics["expand_attempts_total"] += 1
                        _openai_t0 = time.perf_counter()
                        response = _create_art_pulse_response(client, model, expand_prompt)
                        openai_elapsed_ms += int((time.perf_counter() - _openai_t0) * 1000)
                        raw = (response.output_text or "").strip()
                        parsed: Dict[str, object] = {}
                        cand_from_non_json = False
                        try:
                            parsed = _parse_llm_json(raw)
                            cand_title = str(parsed.get("title") or "").strip()
                            cand_body = _extract_body_like_value(parsed)
                        except Exception as exc:
                            retry_metrics["json_parse_fail"] += 1
                            warnings.append(f"expand_attempt_{expand_attempt}: JSON解析失敗({type(exc).__name__})")
                            cand_title, cand_body = _coerce_non_json_output(raw)
                            if cand_body:
                                warnings.append(f"expand_attempt_{expand_attempt}: JSON以外の出力を本文として解釈")
                                cand_from_non_json = True
                            else:
                                continue

                        if not cand_body:
                            salvage_title, salvage_body = _coerce_non_json_output(raw)
                            if salvage_body:
                                cand_title = cand_title or salvage_title
                                cand_body = salvage_body
                                cand_from_non_json = True
                                warnings.append(f"expand_attempt_{expand_attempt}: 非JSON救済を優先して本文を採用")

                        if not cand_body:
                            retry_metrics["empty_title_body"] += 1
                            warnings.append(f"expand_attempt_{expand_attempt}: title/body が空です")
                            if best_non_empty_body:
                                warnings.append(f"expand_attempt_{expand_attempt}: empty output ignored; preserving best non-empty draft.")
                            continue

                        cand_selection = _infer_selected_evidence_from_body(cand_body, payload)
                        if _count_selection_urls(cand_selection) == 0:
                            cand_selection = _build_image_seed_selection(payload, overview)
                        baseline_seed_body = best_length_only_body or recovery_seed_body or last_body
                        if _should_update_last_seed_candidate(cand_body, baseline_seed_body, payload):
                            last_title, last_body = cand_title, cand_body
                            last_selected_plan = cand_selection

                        hard_issues, soft_issues = _validate_main_body_hard_soft(
                            cand_body,
                            payload,
                            selection_plan=cand_selection,
                            fair_label=fair_label,
                        )
                        issues = list(hard_issues)
                        if _count_selection_urls(cand_selection) == 0:
                            retry_metrics["selected_evidence_empty"] += 1
                            soft_issues.append(
                                "selected_evidence が本文に対応していません。本文で参照したURLを selected_evidence に必ず入れてください。"
                            )
                        if _is_non_empty_fallback_candidate(cand_body):
                            candidate_score = _non_empty_candidate_score(cand_body, payload, issues, soft_issues)
                            if candidate_score > best_non_empty_score:
                                best_non_empty_title = cand_title
                                best_non_empty_body = cand_body
                                best_non_empty_selection = cand_selection
                                best_non_empty_issues = list(issues + soft_issues)
                                best_non_empty_soft_issues = list(soft_issues)
                                best_non_empty_score = candidate_score
                        last_hard_issues = list(issues)
                        last_issues = list(issues + soft_issues)
                        cand_chars = _body_text_len(cand_body)
                        candidate_seed_score = _recovery_seed_score(cand_body, payload, issues, soft_issues)
                        if candidate_seed_score > recovery_seed_score:
                            recovery_seed_title = cand_title
                            recovery_seed_body = cand_body
                            recovery_seed_selection = cand_selection
                            recovery_seed_hard_issues = list(issues)
                            recovery_seed_issues = list(issues + soft_issues)
                            recovery_seed_score = candidate_seed_score
                        if _is_length_only_candidate(cand_body, payload, issues):
                            candidate_score = (cand_chars, -len(soft_issues))
                            if candidate_score > best_length_only_score:
                                best_length_only_title = cand_title
                                best_length_only_body = cand_body
                                best_length_only_selection = cand_selection
                                best_length_only_issues = list(issues + soft_issues)
                                best_length_only_soft_issues = list(soft_issues)
                                best_length_only_score = candidate_score
                        if _is_acceptable_pass_candidate(cand_body, payload, issues):
                            candidate_score = (cand_chars, -len(soft_issues))
                            if candidate_score > best_acceptable_score:
                                best_acceptable_title = cand_title
                                best_acceptable_body = cand_body
                                best_acceptable_selection = cand_selection
                                best_acceptable_soft_issues = list(soft_issues)
                                best_acceptable_score = candidate_score
                        if _is_near_pass_candidate(cand_body, payload, issues):
                            candidate_score = (cand_chars, -len(soft_issues))
                            if candidate_score > near_pass_score:
                                near_pass_title = cand_title
                                near_pass_body = cand_body
                                near_pass_selection = cand_selection
                                near_pass_soft_issues = list(soft_issues)
                                near_pass_score = candidate_score

                        if not issues:
                            candidate_score = (cand_chars, -len(soft_issues))
                            if candidate_score > best_valid_score:
                                best_valid_title = cand_title
                                best_valid_body = cand_body
                                best_valid_selection = cand_selection
                                best_valid_soft_issues = list(soft_issues)
                                best_valid_score = candidate_score
                            title, main_body = best_valid_title, best_valid_body
                            selected_plan = best_valid_selection
                            mode = "openai_expand"
                            if best_valid_soft_issues:
                                warnings.append(f"expand_attempt_{expand_attempt}: " + " / ".join(best_valid_soft_issues))
                            retry_metrics["success_attempt"] = max_attempts + expand_attempt
                            break

                        retry_metrics["validation_fail"] += 1
                        retry_metrics["expand_validation_fail"] += 1
                        warnings.append(f"expand_attempt_{expand_attempt}: " + " / ".join(issues + soft_issues))
                        expand_source_title = best_length_only_title or best_non_empty_title or recovery_seed_title or cand_title
                        expand_source_body = best_length_only_body or best_non_empty_body or recovery_seed_body or cand_body
                        expand_source_selection = (
                            best_length_only_selection
                            if best_length_only_body
                            else (
                                best_non_empty_selection
                                if best_non_empty_body
                                else (recovery_seed_selection if recovery_seed_body else cand_selection)
                            )
                        )
                        expand_source_issues = best_length_only_issues or best_non_empty_issues or recovery_seed_issues or last_issues
                        expand_prompt = _build_expansion_prompt(
                            fair_label=fair_label,
                            reporter=reporter,
                            angle_label=angle_label,
                            angle_description=angle_description,
                            payload=payload,
                            previous_title=expand_source_title,
                            previous_body=expand_source_body,
                            previous_selected_evidence=expand_source_selection,
                            issues=expand_source_issues,
                        )

                if not main_body:
                    if (
                        _should_run_structural_salvage(
                            best_length_only_body or best_non_empty_body or recovery_seed_body or last_body,
                            recovery_seed_hard_issues or last_hard_issues,
                        )
                        and max_salvage_attempts > 0
                    ):
                        salvage_issues = list(best_length_only_issues or best_non_empty_issues or recovery_seed_issues or last_issues or last_hard_issues)
                        salvage_prompt = _build_salvage_prompt(
                            fair_label=fair_label,
                            reporter=reporter,
                            angle_label=angle_label,
                            angle_description=angle_description,
                            payload=payload,
                            previous_title=best_length_only_title or best_non_empty_title or recovery_seed_title or last_title,
                            previous_body=best_length_only_body or best_non_empty_body or recovery_seed_body or last_body,
                            previous_selected_evidence=(
                                best_length_only_selection
                                if best_length_only_body
                                else (
                                    best_non_empty_selection
                                    if best_non_empty_body
                                    else (recovery_seed_selection if recovery_seed_body else last_selected_plan)
                                )
                            ),
                            issues=salvage_issues,
                        )
                        salvage_prompt += _build_generation_constraints()
                        for salvage_attempt in range(1, max_salvage_attempts + 1):
                            _emit_progress(95)
                            retry_metrics["attempts_total"] += 1
                            retry_metrics["salvage_attempts_total"] += 1
                            _openai_t0 = time.perf_counter()
                            response = _create_art_pulse_response(client, model, salvage_prompt)
                            openai_elapsed_ms += int((time.perf_counter() - _openai_t0) * 1000)
                            raw = (response.output_text or "").strip()
                            parsed: Dict[str, object] = {}
                            cand_from_non_json = False
                            try:
                                parsed = _parse_llm_json(raw)
                                cand_title = str(parsed.get("title") or "").strip()
                                cand_body = _extract_body_like_value(parsed)
                            except Exception as exc:
                                retry_metrics["json_parse_fail"] += 1
                                warnings.append(f"salvage_attempt_{salvage_attempt}: JSON解析失敗({type(exc).__name__})")
                                debug_trace.append(
                                    {
                                        "stage": "salvage",
                                        "attempt": salvage_attempt,
                                        "status": "json_parse_fail",
                                        "error": type(exc).__name__,
                                        "raw_preview": raw[:240],
                                    }
                                )
                                cand_title, cand_body = _coerce_non_json_output(raw)
                                if cand_body:
                                    warnings.append(f"salvage_attempt_{salvage_attempt}: JSON以外の出力を本文として解釈")
                                    cand_from_non_json = True
                                else:
                                    continue

                            if not cand_body:
                                salvage_title, salvage_body = _coerce_non_json_output(raw)
                                if salvage_body:
                                    cand_title = cand_title or salvage_title
                                    cand_body = salvage_body
                                    cand_from_non_json = True
                                    warnings.append(f"salvage_attempt_{salvage_attempt}: 非JSON救済を優先して本文を採用")

                            if not cand_body:
                                retry_metrics["empty_title_body"] += 1
                                warnings.append(f"salvage_attempt_{salvage_attempt}: title/body が空です")
                                if best_non_empty_body:
                                    warnings.append(f"salvage_attempt_{salvage_attempt}: empty output ignored; preserving best non-empty draft.")
                                debug_trace.append(
                                    {
                                        "stage": "salvage",
                                        "attempt": salvage_attempt,
                                        "status": "empty_title_body",
                                    }
                                )
                                continue

                            cand_selection = _infer_selected_evidence_from_body(cand_body, payload)
                            if _count_selection_urls(cand_selection) == 0:
                                cand_selection = _build_image_seed_selection(payload, overview)
                            baseline_seed_body = best_length_only_body or recovery_seed_body or last_body
                            if _should_update_last_seed_candidate(cand_body, baseline_seed_body, payload):
                                last_title, last_body = cand_title, cand_body
                                last_selected_plan = cand_selection

                            hard_issues, soft_issues = _validate_main_body_hard_soft(
                                cand_body,
                                payload,
                                selection_plan=cand_selection,
                                fair_label=fair_label,
                            )
                            issues = list(hard_issues)
                            if _count_selection_urls(cand_selection) == 0:
                                retry_metrics["selected_evidence_empty"] += 1
                                soft_issues.append(
                                    "selected_evidence が本文に対応していません。本文で参照したURLを selected_evidence に必ず入れてください。"
                                )
                            if _is_non_empty_fallback_candidate(cand_body):
                                candidate_score = _non_empty_candidate_score(cand_body, payload, issues, soft_issues)
                                if candidate_score > best_non_empty_score:
                                    best_non_empty_title = cand_title
                                    best_non_empty_body = cand_body
                                    best_non_empty_selection = cand_selection
                                    best_non_empty_issues = list(issues + soft_issues)
                                    best_non_empty_soft_issues = list(soft_issues)
                                    best_non_empty_score = candidate_score
                            last_hard_issues = list(issues)
                            last_issues = list(issues + soft_issues)
                            cand_chars = _body_text_len(cand_body)
                            candidate_seed_score = _recovery_seed_score(cand_body, payload, issues, soft_issues)
                            if candidate_seed_score > recovery_seed_score:
                                recovery_seed_title = cand_title
                                recovery_seed_body = cand_body
                                recovery_seed_selection = cand_selection
                                recovery_seed_hard_issues = list(issues)
                                recovery_seed_issues = list(issues + soft_issues)
                                recovery_seed_score = candidate_seed_score
                            if _is_length_only_candidate(cand_body, payload, issues):
                                candidate_score = (cand_chars, -len(soft_issues))
                                if candidate_score > best_length_only_score:
                                    best_length_only_title = cand_title
                                    best_length_only_body = cand_body
                                    best_length_only_selection = cand_selection
                                    best_length_only_issues = list(issues + soft_issues)
                                    best_length_only_soft_issues = list(soft_issues)
                                    best_length_only_score = candidate_score
                            if _is_acceptable_pass_candidate(cand_body, payload, issues):
                                candidate_score = (cand_chars, -len(soft_issues))
                                if candidate_score > best_acceptable_score:
                                    best_acceptable_title = cand_title
                                    best_acceptable_body = cand_body
                                    best_acceptable_selection = cand_selection
                                    best_acceptable_soft_issues = list(soft_issues)
                                    best_acceptable_score = candidate_score
                            debug_trace.append(
                                {
                                    "stage": "salvage",
                                    "attempt": salvage_attempt,
                                    "status": "validated" if not issues else "validation_fail",
                                    "chars": cand_chars,
                                    "issue_count": len(issues) + len(soft_issues),
                                    "hard_issues": list(issues[:8]),
                                    "soft_issues": list(soft_issues[:8]),
                                }
                            )
                            if _is_near_pass_candidate(cand_body, payload, issues):
                                candidate_score = (cand_chars, -len(soft_issues))
                                if candidate_score > near_pass_score:
                                    near_pass_title = cand_title
                                    near_pass_body = cand_body
                                    near_pass_selection = cand_selection
                                    near_pass_soft_issues = list(soft_issues)
                                    near_pass_score = candidate_score

                            if not issues:
                                candidate_score = (cand_chars, -len(soft_issues))
                                if candidate_score > best_valid_score:
                                    best_valid_title = cand_title
                                    best_valid_body = cand_body
                                    best_valid_selection = cand_selection
                                    best_valid_soft_issues = list(soft_issues)
                                    best_valid_score = candidate_score
                                title, main_body = best_valid_title, best_valid_body
                                selected_plan = best_valid_selection
                                mode = "openai_salvage"
                                if best_valid_soft_issues:
                                    warnings.append(f"salvage_attempt_{salvage_attempt}: " + " / ".join(best_valid_soft_issues))
                                retry_metrics["success_attempt"] = retry_metrics["attempts_total"]
                                break

                            retry_metrics["validation_fail"] += 1
                            retry_metrics["salvage_validation_fail"] += 1
                            warnings.append(f"salvage_attempt_{salvage_attempt}: " + " / ".join(issues + soft_issues))

                    if not main_body:
                        if best_valid_body:
                            title = best_valid_title or best_length_only_title or recovery_seed_title or last_title or f"{fair_label}のArt Pulse（{angle_label}）"
                            main_body = best_valid_body
                            selected_plan = best_valid_selection
                            mode = mode if mode.startswith("openai") else "openai_best_valid"
                            retry_metrics["success_attempt"] = retry_metrics["attempts_total"]
                            if best_valid_soft_issues:
                                warnings.append("best_valid soft issues: " + " / ".join(best_valid_soft_issues))
                        elif best_acceptable_body:
                            title = best_acceptable_title or best_length_only_title or recovery_seed_title or last_title or f"{fair_label}のArt Pulse（{angle_label}）"
                            main_body = best_acceptable_body
                            selected_plan = best_acceptable_selection
                            mode = "openai_acceptable_pass"
                            retry_metrics["success_attempt"] = retry_metrics["attempts_total"]
                            warnings.append(
                                f"acceptable_pass accepted: body is under ideal {ART_PULSE_TEXT_MIN_CHARS} chars but >= {ART_PULSE_TEXT_ACCEPTABLE_MIN_CHARS} chars with 3 headings and Section3 grounding."
                            )
                            warnings.append(
                                f"acceptable_pass warning: below ideal target ({ART_PULSE_TEXT_MIN_CHARS} chars); article accepted for production use."
                            )
                            if best_acceptable_soft_issues:
                                warnings.append("acceptable_pass soft issues: " + " / ".join(best_acceptable_soft_issues))
                        elif near_pass_body:
                            title = near_pass_title or best_length_only_title or recovery_seed_title or last_title or f"{fair_label}のArt Pulse（{angle_label}）"
                            main_body = near_pass_body
                            selected_plan = near_pass_selection
                            mode = "openai_near_pass"
                            retry_metrics["success_attempt"] = retry_metrics["attempts_total"]
                            warnings.append(
                                f"near_pass accepted: body remains under {ART_PULSE_TEXT_MIN_CHARS} chars but preserves 3 headings, section3 requirements, and >=1500 visible chars."
                            )
                            if near_pass_soft_issues:
                                warnings.append("near_pass soft issues: " + " / ".join(near_pass_soft_issues))
                        elif (
                            best_length_only_body
                            and _body_text_len(best_length_only_body) >= ART_PULSE_TEXT_ACCEPTABLE_MIN_CHARS
                        ):
                            title = best_length_only_title or recovery_seed_title or last_title or f"{fair_label}のArt Pulse（{angle_label}）"
                            main_body = best_length_only_body
                            selected_plan = best_length_only_selection
                            mode = "openai_length_only_fallback"
                            retry_metrics["success_attempt"] = retry_metrics["attempts_total"]
                            warnings.append(
                                f"length_only fallback: preserving 3-heading draft below ideal {ART_PULSE_TEXT_MIN_CHARS} chars but above acceptable floor {ART_PULSE_TEXT_ACCEPTABLE_MIN_CHARS} chars."
                            )
                            if best_length_only_soft_issues:
                                warnings.append("length_only fallback soft issues: " + " / ".join(best_length_only_soft_issues))
                        else:
                            if best_length_only_body and _body_text_len(best_length_only_body) < ART_PULSE_TEXT_ACCEPTABLE_MIN_CHARS:
                                warnings.append(
                                    f"length_only fallback blocked: body is under {ART_PULSE_TEXT_ACCEPTABLE_MIN_CHARS} chars."
                                )
                            if best_non_empty_body:
                                warnings.append(
                                    "non_empty fallback retained as recovery seed only: blocked from user-facing output."
                                )
                                if best_non_empty_soft_issues:
                                    warnings.append("non_empty recovery soft issues: " + " / ".join(best_non_empty_soft_issues))
                            title = recovery_seed_title or last_title or f"{fair_label}のArt Pulse（{angle_label}）"
                            mode = "openai_validation_blocked"
                            selected_plan = _empty_selection_plan()
                            main_body = ""
                            warnings.append("validation_blocked: no draft satisfied hard body constraints after retries.")
        except Exception as exc:
            mode = "openai_error"
            warnings.append(f"{type(exc).__name__}: {exc}")

    if not title:
        title = f"{fair_label}のArt Pulse（{angle_label}）"

    if main_body and _count_selection_urls(selected_plan) == 0:
        seeded = _build_image_seed_selection(payload, overview)
        if _count_selection_urls(seeded) > 0:
            selected_plan = seeded
            warnings.append("selected_evidence fallback: seeded from payload urls for continuity.")

    if main_body:
        _emit_progress(96)
        truncated_body = _truncate_body_text(main_body, ART_PULSE_TEXT_MAX_CHARS, ART_PULSE_TEXT_SOFT_OVER_CHARS)
        truncated_hard_issues, _ = _validate_main_body_hard_soft(
            truncated_body,
            payload,
            selection_plan=selected_plan,
            fair_label=fair_label,
        )
        if truncated_hard_issues:
            warnings.append("truncate skipped: preserving pre-truncate body because truncation broke hard body constraints.")
        else:
            main_body = truncated_body
        buckets = _build_section_image_buckets(overview, selected_plan)
        if sum(len(bucket) for bucket in buckets) == 0:
            seeded = _build_image_seed_selection(payload, overview)
            if _count_selection_urls(seeded) > 0:
                selected_plan = _merge_selection_plan(selected_plan, seeded)
                buckets = _build_section_image_buckets(overview, selected_plan)
                if sum(len(bucket) for bucket in buckets) > 0:
                    warnings.append("image fallback: merged image-capable urls into selected_evidence.")
        main_body = _inject_images_into_sections(main_body, buckets)
    else:
        main_body = "本文を生成できませんでした。設定を確認して再実行してください。"

    selected_ex_urls, selected_ar_urls, selected_all_urls = _flatten_selection_urls(selected_plan)
    if not selected_all_urls:
        warnings.append("selected_evidence からURLを抽出できなかったため、候補URLで代替表示しています。")
        selected_ex_urls = list(payload.get("exhibition_urls", []) or [])
        selected_ar_urls = list(payload.get("artist_urls", []) or [])
        selected_all_urls = _unique_urls(selected_ex_urls + selected_ar_urls)

    url_block = _compose_url_block(selected_all_urls)
    body = "\n\n".join([main_body, url_block]).strip()
    body_chars = _body_text_len(main_body)
    elapsed_ms_total = int((time.perf_counter() - started_at) * 1000)
    first_pass_success = bool(mode == "openai" and retry_metrics.get("success_attempt", 0) == 1)

    logger.info(
        "art_pulse_retry_metrics mode=%s reporter=%s angle=%s fair=%s metrics=%s",
        mode,
        reporter.get("id"),
        angle_key,
        fair_label,
        json.dumps(retry_metrics, ensure_ascii=False),
    )

    return {
        "mode": mode,
        "model": model,
        "title": title,
        "body": body,
        "body_chars": body_chars,
        "persona_id": reporter.get("id"),
        "persona_label": reporter.get("label"),
        "angle_key": angle_key,
        "angle_label": angle_label,
        "angle_description": angle_description,
        "fair_label": fair_label,
        "year": 2025,
        "evidence_counts": {
            "exhibition_candidates": len(payload.get("exhibition_rows", [])),
            "artist_candidates": len(payload.get("artist_rows", [])),
            "selected_exhibition_urls": len(selected_ex_urls),
            "selected_artist_urls": len(selected_ar_urls),
            "all_unique_urls": len(payload.get("all_urls", [])),
        },
        "evidence_urls": {
            "exhibition": selected_ex_urls,
            "artist": selected_ar_urls,
            "all": selected_all_urls,
        },
        "selected_evidence": selected_plan,
        "retry_metrics": retry_metrics,
        "warnings": warnings,
        "debug": {
            "mode": mode,
            "max_attempts": 1,
            "max_expand_attempts": 2,
            "max_salvage_attempts": 1,
            "attempt_trace": debug_trace,
            "metrics": {
                "first_pass_success": first_pass_success,
                "body_chars": body_chars,
                "elapsed_ms_total": elapsed_ms_total,
                "elapsed_ms_openai": openai_elapsed_ms,
                "mode": mode,
            },
        },
        "note": (
            f"本文は理想として{ART_PULSE_TEXT_MIN_CHARS}字以上、{ART_PULSE_TEXT_MAX_CHARS}字を目安"
            f"（上限{ART_PULSE_TEXT_MAX_CHARS + ART_PULSE_TEXT_SOFT_OVER_CHARS}字まで許容）。"
            f"{ART_PULSE_TEXT_ACCEPTABLE_MIN_CHARS}字以上でも、3見出しと第3節の具体名が成立していれば記事として受理可能。"
            "3見出しの構成・重複禁止・画像挿入・根拠URLを適用。"
        ),
    }

