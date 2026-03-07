from __future__ import annotations

import json
import os
import re
from typing import Dict, List, Tuple
from urllib.parse import quote_plus

from phase2_art_pulse_config import ART_PULSE_TEXT_MAX_CHARS, find_persona, find_persona_angle

BODY_CHAR_LIMIT = ART_PULSE_TEXT_MAX_CHARS
BODY_MIN_TARGET_CHARS = 1800
BODY_TARGET_CHARS = 1900
MAX_EVIDENCE_URLS = 8
MAX_IMAGE_TOTAL = 8

REQUIRED_HEADINGS = [
    "## 今年のトレンド",
    "## トレンドに沿った重要なExhibitionまたはArtist",
    "## トレンドではないが面白かったExhibitionまたはArtist",
]

SECTION_IMAGE_QUOTAS = [3, 3, 2]
SECTION_KEYS = ["section1", "section2", "section3"]
MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")

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
    return f"https://www.google.com/search?tbm=isch&q={quote_plus(name_en)}"


def _clean_artist_name(name: str) -> str:
    text = re.sub(r"\s+", " ", (name or "").strip())
    text = re.sub(r"\s+\d+$", "", text)
    return text.strip()


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


def _format_exhibition_marker(row: Dict[str, object]) -> str:
    gallery = str(row.get("gallery") or "").strip() or "(unknown gallery)"
    title = _clean_exhibition_title(str(row.get("title") or ""), gallery)
    source_url = str(row.get("source_url") or "").strip()
    if source_url:
        return f"([{title}]({source_url}) @ {gallery})"
    return f"({title} @ {gallery})"


def _format_artist_marker(row: Dict[str, object]) -> str:
    name_en = _clean_artist_name(str(row.get("artist_name_en") or row.get("artist") or "(unknown artist)"))
    google_url = _google_image_search_url(name_en)
    kana = _normalize_kana(str(row.get("artist_name_kana") or "")) or _guess_kana_from_name(name_en)
    if kana:
        return f"[{name_en}]({google_url})（{kana}）"
    return f"[{name_en}]({google_url})"


def _build_evidence_payload(overview: Dict[str, object], cap: int = 18) -> Dict[str, object]:
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
            }
        )

    def _fair_round_robin(rows: List[Dict[str, object]], max_count: int) -> List[Dict[str, object]]:
        grouped: Dict[str, List[Dict[str, object]]] = {}
        for row in rows:
            grouped.setdefault(str(row.get("fair") or ""), []).append(row)
        order = [k for k in ("Frieze London", "Liste Art Fair Basel") if k in grouped]
        for key in sorted(grouped.keys()):
            if key not in order:
                order.append(key)
        out: List[Dict[str, object]] = []
        while len(out) < max_count and any(grouped.get(key) for key in order):
            for key in order:
                bucket = grouped.get(key) or []
                if not bucket:
                    continue
                out.append(bucket.pop(0))
                if len(out) >= max_count:
                    break
        return out

    ex_rows = _fair_round_robin(ex_deduped, cap)
    ar_rows = _fair_round_robin(ar_deduped, cap)

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


def _truncate_body_text(body: str, limit: int = BODY_CHAR_LIMIT) -> str:
    text = (body or "").strip()
    if _body_text_len(text) <= limit:
        return text
    lines = text.splitlines()
    kept: List[str] = []
    for line in lines:
        trial = "\n".join(kept + [line]).strip()
        if _body_text_len(trial) > limit:
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
    if "### 根拠URL" in text or "### 参考画像（この節）" in text:
        return False
    slash_runs = max((len(match.group(0)) for match in re.finditer(r"(?:\s*/\s*){4,}", text)), default=0)
    if slash_runs >= 1:
        return False
    return True


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


def _parse_selected_evidence_from_json(parsed: Dict[str, object], payload: Dict[str, object]) -> Dict[str, Dict[str, List[str]]]:
    selection = _empty_selection_plan()
    raw = parsed.get("selected_evidence")
    if not isinstance(raw, dict):
        return selection

    ex_allowed = {str(row.get("source_url") or "").strip() for row in list(payload.get("exhibition_rows", []) or [])}
    ar_allowed = {str(row.get("source_url") or "").strip() for row in list(payload.get("artist_rows", []) or [])}
    heading_to_key = {heading: SECTION_KEYS[idx] for idx, heading in enumerate(REQUIRED_HEADINGS)}

    for raw_key, sec in raw.items():
        if not isinstance(sec, dict):
            continue
        key = str(raw_key or "").strip()
        sec_key = key if key in SECTION_KEYS else heading_to_key.get(key)
        if not sec_key:
            continue
        ex_urls = [str(u or "").strip() for u in list(sec.get("exhibition_urls", []) or [])]
        ar_urls = [str(u or "").strip() for u in list(sec.get("artist_urls", []) or [])]
        selection[sec_key]["exhibition_urls"] = [u for u in _dedupe_preserve_order(ex_urls) if u in ex_allowed]
        selection[sec_key]["artist_urls"] = [u for u in _dedupe_preserve_order(ar_urls) if u in ar_allowed]
    return selection


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
            elif title and title in text:
                ex_urls.append(source_url)

        for row in ar_rows:
            source_url = str(row.get("source_url") or "").strip()
            artist_name = str(row.get("artist_name_en") or "").strip()
            if source_url and source_url in text:
                ar_urls.append(source_url)
            elif artist_name and artist_name in text:
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

    used_images = set()
    buckets: List[List[Dict[str, object]]] = []

    global_pool: List[Dict[str, object]] = []
    for key in SECTION_KEYS:
        sec = selection_plan.get(key, {})
        for source_url in list(sec.get("exhibition_urls", []) or []):
            for row in ex_by_source.get(source_url, []):
                global_pool.append(row)
        for source_url in list(sec.get("artist_urls", []) or []):
            for row in ar_by_source.get(source_url, []):
                global_pool.append(row)

    for idx, sec_key in enumerate(SECTION_KEYS):
        quota = SECTION_IMAGE_QUOTAS[idx] if idx < len(SECTION_IMAGE_QUOTAS) else 0
        sec = selection_plan.get(sec_key, {})
        selected_rows: List[Dict[str, object]] = []

        for source_url in list(sec.get("exhibition_urls", []) or []):
            for row in ex_by_source.get(source_url, []):
                image_url = str(row.get("image_url") or "").strip()
                if not image_url or image_url in used_images:
                    continue
                selected_rows.append(row)
                used_images.add(image_url)
                if len(selected_rows) >= quota:
                    break
            if len(selected_rows) >= quota:
                break

        if len(selected_rows) < quota:
            for source_url in list(sec.get("artist_urls", []) or []):
                for row in ar_by_source.get(source_url, []):
                    image_url = str(row.get("image_url") or "").strip()
                    if not image_url or image_url in used_images:
                        continue
                    selected_rows.append(row)
                    used_images.add(image_url)
                    if len(selected_rows) >= quota:
                        break
                if len(selected_rows) >= quota:
                    break

        if len(selected_rows) < quota:
            for row in global_pool:
                image_url = str(row.get("image_url") or "").strip()
                if not image_url or image_url in used_images:
                    continue
                selected_rows.append(row)
                used_images.add(image_url)
                if len(selected_rows) >= quota:
                    break

        buckets.append(selected_rows[:quota])

    total = sum(len(b) for b in buckets)
    if total < MAX_IMAGE_TOTAL:
        leftovers = [row for row in ex_candidates + ar_candidates if str(row.get("image_url") or "").strip() not in used_images]
        for row in leftovers:
            if sum(len(b) for b in buckets) >= MAX_IMAGE_TOTAL:
                break
            buckets[-1].append(row)
            used_images.add(str(row.get("image_url") or "").strip())

    return buckets


def _build_section_image_block(rows: List[Dict[str, object]]) -> str:
    if not rows:
        return ""
    lines = ["", "**参考画像（この節）**"]
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
    lines = ["### 根拠URL"]
    if urls:
        lines.extend([f"- {url}" for url in urls])
    else:
        lines.append("- 根拠URLは表示できませんでした。")
    return "\n".join(lines)


def _build_prompt(
    fair_label: str,
    reporter: Dict[str, object],
    angle_label: str,
    angle_description: str,
    payload: Dict[str, object],
) -> str:
    ex_lines = [
        f"- fair={row.get('fair')} | gallery={row.get('gallery')} | title={row.get('title')} | source_url={row.get('source_url')}"
        for row in list(payload.get("exhibition_rows", []))[:12]
    ]
    ar_lines = [
        f"- fair={row.get('fair')} | gallery={row.get('gallery')} | artist={row.get('artist_name_en')} | source_url={row.get('source_url')} | text_snippet={str(row.get('text_snippet') or '')[:120]}"
        for row in list(payload.get("artist_rows", []))[:12]
    ]
    return f"""
あなたは日本語の現代アート編集者です。以下の根拠だけを使って Art Pulse 記事を作成してください。

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
- 本文テキストは 1800〜2000字を目標（上限は2000字）
- 可視文字数で 1800〜2000字（MarkdownのリンクURL文字列は字数に含めない）
- 必ず以下の3見出しをこの順で入れる:
  1) ## 今年のトレンド
  2) ## トレンドに沿った重要なExhibitionまたはArtist
  3) ## トレンドではないが面白かったExhibitionまたはArtist
- 一人称で書く（私/僕）。「Alexの視点」「◯◯の視点」などの三人称導入は禁止
- Exhibition/Artist名の羅列をしない（解説を必ず伴う）
- 同一段落・同一文の重複を禁止（末尾の繰り返し禁止）
- Exhibitionは可能な範囲で「([展示名](source_url) @ ギャラリー英名)」表記
- Exhibition名から開催日程などのノイズは削除する
- 「A+ Works of Art @ A+ Works of Art」のような重複は絶対に避ける
- Artist表記は「[Artist Name](Google画像検索URL)（カナ読み）」を優先
- 「英名: ...」というラベルは出力しない
- カナ読みは推定してよい
- RAG根拠（特にExhibitions Text）を厳守しつつ、必要に応じて内部知識で文脈補完してよい
- 内部知識による補完部分に、無理な出典URL付与は不要
- 過度な断定を避け、根拠に沿って論を組み立てる
- selected_evidence は、本文の各節で実際に参照した URL のみを入れる
- 画像候補は selected_evidence を基に提示されるため、機械的選択は避ける

対象フェア: {fair_label}
記者: {reporter.get('label')}（{reporter.get('description')}）
記者style: {reporter.get('style', '')}
記者tone: {reporter.get('tone', '')}
切り口: {angle_label}
切り口の説明: {angle_description}

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
    has_ex = any(t and t in section3 for t in ex_tokens)
    has_ar = any(t and t in section3 for t in ar_tokens)
    return has_ex and has_ar


def _validate_main_body(body: str, payload: Dict[str, object]) -> List[str]:
    issues: List[str] = []
    if not body.strip():
        issues.append("本文が空です。")
        return issues
    if not _has_required_structure(body):
        issues.append("3見出し構成が不足しています。")
    chars = _body_text_len(body)
    if chars < BODY_MIN_TARGET_CHARS:
        issues.append(f"本文文字数が不足しています（{chars}字）。1800字以上にしてください。")
    if chars > BODY_CHAR_LIMIT:
        issues.append(f"本文文字数が超過しています（{chars}字）。2000字以内にしてください。")
    if _count_duplicate_paragraphs(body) > 0:
        issues.append("同一段落の重複があります。重複を除去してください。")
    if not _section3_has_required_mentions(body, payload):
        issues.append("第3節に Exhibition と Artist の具体名が不足しています。")
    return issues


def _build_revision_prompt(
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
    return (
        _build_prompt(fair_label, reporter, angle_label, angle_description, payload)
        + "\n\n【前回稿の修正指示】\n"
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


def generate_art_pulse_draft(
    overview: Dict[str, object],
    reporter_id: str,
    angle_keys: List[str],
) -> Dict[str, object]:
    selection = overview.get("selection", {})
    fair_label = str(selection.get("fair_label") or "Frieze London + Liste Art Fair Basel")
    reporter = find_persona(reporter_id)
    angle_key, angle_label, angle_description = _pick_angle(reporter, angle_keys)
    payload = _build_evidence_payload(overview)

    model = os.getenv("TEXT_MODEL", "gpt-5-mini")
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    mode = "no_api_key"
    title = ""
    main_body = ""
    selected_plan = _empty_selection_plan()
    warnings: List[str] = []

    if not api_key:
        warnings.append("OPENAI_API_KEY が未設定のため、Art Pulse 本文を生成できません。")
    else:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            prompt = _build_prompt(fair_label, reporter, angle_label, angle_description, payload)
            last_title = ""
            last_body = ""
            last_selected_plan = _empty_selection_plan()
            max_attempts = 3

            for attempt in range(1, max_attempts + 1):
                response = client.responses.create(model=model, input=prompt)
                raw = (response.output_text or "").strip()
                try:
                    parsed = _parse_llm_json(raw)
                    cand_title = str(parsed.get("title") or "").strip()
                    cand_body = str(parsed.get("body") or "").strip()
                except Exception as exc:
                    warnings.append(f"attempt_{attempt}: JSON解析失敗({type(exc).__name__})")
                    prompt = (
                        _build_prompt(fair_label, reporter, angle_label, angle_description, payload)
                        + "\n\nJSON形式を厳守してください。"
                    )
                    continue

                if not cand_title or not cand_body:
                    warnings.append(f"attempt_{attempt}: title/body が空です")
                    prompt = (
                        _build_prompt(fair_label, reporter, angle_label, angle_description, payload)
                        + "\n\ntitle と body を必ず埋めてください。"
                    )
                    continue

                json_selection = _parse_selected_evidence_from_json(parsed, payload)
                body_selection = _infer_selected_evidence_from_body(cand_body, payload)
                cand_selection = _merge_selection_plan(json_selection, body_selection)

                last_title, last_body = cand_title, cand_body
                last_selected_plan = cand_selection

                issues = _validate_main_body(cand_body, payload)
                if _count_selection_urls(cand_selection) == 0:
                    issues.append(
                        "selected_evidence が本文に対応していません。本文で参照したURLを selected_evidence に必ず入れてください。"
                    )

                if not issues:
                    title, main_body = cand_title, cand_body
                    selected_plan = cand_selection
                    mode = "openai"
                    break

                warnings.append(f"attempt_{attempt}: " + " / ".join(issues))
                prompt = _build_revision_prompt(
                    fair_label=fair_label,
                    reporter=reporter,
                    angle_label=angle_label,
                    angle_description=angle_description,
                    payload=payload,
                    previous_title=cand_title,
                    previous_body=cand_body,
                    previous_selected_evidence=cand_selection,
                    issues=issues,
                )

            if not main_body:
                title = last_title or f"{fair_label}のArt Pulse（{angle_label}）"
                main_body = (last_body or "").strip()
                selected_plan = last_selected_plan
                mode = "openai_validation_hold"
                if not main_body:
                    warnings.append("本文を生成できませんでした。設定を確認して再実行してください。")
        except Exception as exc:
            mode = "openai_error"
            warnings.append(f"{type(exc).__name__}: {exc}")

    if not title:
        title = f"{fair_label}のArt Pulse（{angle_label}）"

    if main_body:
        main_body = _truncate_body_text(main_body, BODY_CHAR_LIMIT)
        buckets = _build_section_image_buckets(overview, selected_plan)
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

    return {
        "mode": mode,
        "model": model,
        "title": title,
        "body": body,
        "body_chars": _body_text_len(main_body),
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
        "warnings": warnings,
        "note": (
            "本文は1800〜2000字を目標（上限2000字）。"
            "3見出しの構成・重複禁止・画像挿入・根拠URLを適用。"
        ),
    }

