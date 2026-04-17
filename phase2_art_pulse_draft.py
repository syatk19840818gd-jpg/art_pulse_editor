from __future__ import annotations

import json
import os
import re
import unicodedata
from typing import Callable, Dict, List, Tuple
from urllib.parse import quote_plus

from phase2_art_pulse_config import (
    ART_PULSE_MAX_OUTPUT_TOKENS,
    ART_PULSE_PAYLOAD_CANDIDATE_CAP,
    ART_PULSE_PROMPT_ARTIST_ROWS,
    ART_PULSE_PROMPT_EXHIBITION_ROWS,
    ART_PULSE_PROMPT_SNIPPET_CHARS,
    MAX_EVIDENCE_URLS,
    find_persona,
    find_persona_angle,
)
from phase2_response_style import PLAIN_JAPANESE_RULE

ART_PULSE_SINGLE_ARTICLE_TARGET_CHARS = 1000
ART_PULSE_SINGLE_ARTICLE_MIN_CHARS = 800
ART_PULSE_SINGLE_ARTICLE_MAX_CHARS = 1200
ART_PULSE_SINGLE_ARTICLE_SOFT_MAX_CHARS = 1300
ART_PULSE_SINGLE_ARTICLE_HARD_MIN_CHARS = 600
ART_PULSE_SINGLE_ARTICLE_MIN_SENTENCES = 5
ART_PULSE_MAX_THUMBNAILS = 4

MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")
IMAGE_LINE_PATTERN = re.compile(r"^!\[[^\]]*\]\([^)]+\)\s*$")
SOURCE_LINE_PATTERN = re.compile(r"^Source:\s*<[^>]+>\s*$")

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
        value = str(url or "").strip()
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
    return f"https://www.google.com/search?tbm=isch&q={quote_plus((name_en or '').strip() + ' art')}"


def _clean_artist_name(name: str) -> str:
    text = re.sub(r"\s+", " ", str(name or "").strip())
    text = re.sub(r"\s+\d+$", "", text)
    return text.strip()


def _normalize_kana(kana: str) -> str:
    text = str(kana or "").strip()
    return re.sub(r"\s+", "", text)


def _guess_kana_from_name(name_en: str) -> str:
    words = re.findall(r"[A-Za-z]+", str(name_en or ""))
    if not words:
        return ""
    converted: List[str] = []
    for word in words:
        kana = KANA_WORD_MAP.get(word.upper())
        if not kana:
            return ""
        converted.append(kana)
    return "・".join(converted)


def _clean_exhibition_title(title: str, gallery: str = "") -> str:
    text = re.sub(r"\s+", " ", str(title or "").strip())
    gallery_text = re.sub(r"\s+", " ", str(gallery or "").strip())
    if "|" in text:
        head = str(text.split("|", 1)[0]).strip()
        if head:
            text = head
    if gallery_text:
        text = re.sub(
            rf"\s*[-|@]\s*{re.escape(gallery_text)}\s*$",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()
    return text or "(untitled)"


def _clip_text(text: str, max_chars: int) -> str:
    compact = re.sub(r"\s+", " ", str(text or "").strip())
    if max_chars <= 0 or len(compact) <= max_chars:
        return compact
    return compact[: max(0, max_chars - 1)].rstrip() + "…"


def _normalize_exact_match_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(text or "").strip())
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = re.sub(r"\s+", "", normalized)
    normalized = re.sub(
        r"[\"'`´“”‘’･・,，、。．:：;；!?！？()\[\]{}<>＜＞「」『』【】/\\|＿_‐‑‒–—―\-~〜…]+",
        "",
        normalized,
    )
    return normalized.casefold()


def _contains_cjk(text: str) -> bool:
    return bool(re.search(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]", str(text or "")))


def _text_contains_exactish_token(text: str, token: str) -> bool:
    haystack = str(text or "")
    needle = str(token or "").strip()
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


def _strip_non_article_lines(body: str) -> str:
    lines: List[str] = []
    for raw in str(body or "").splitlines():
        line = raw.strip()
        if not line:
            lines.append("")
            continue
        if IMAGE_LINE_PATTERN.match(line):
            continue
        if SOURCE_LINE_PATTERN.match(line):
            continue
        lines.append(raw)
    merged = "\n".join(lines)
    merged = re.sub(r"\n{3,}", "\n\n", merged)
    return merged.strip()


def _body_text_len(body: str) -> int:
    text = _strip_non_article_lines(body)
    text = MARKDOWN_LINK_PATTERN.sub(lambda m: m.group(1), text)
    text = re.sub(r"\s+", "", text)
    return len(text)


def _article_sentence_count(body: str) -> int:
    text = _strip_non_article_lines(body)
    parts = re.split(r"[。！？!?]+", text)
    return len([part for part in parts if part.strip()])


def _truncate_article_body(body: str, max_chars: int) -> str:
    text = str(body or "").strip()
    if not text or max_chars <= 0:
        return text
    current_chars = _body_text_len(text)
    if current_chars <= max_chars:
        return text

    ratio = max_chars / max(1, current_chars)
    rough_cut = max(200, int(len(text) * ratio))
    clipped = text[:rough_cut].rstrip()
    sentence_break = max(clipped.rfind("。"), clipped.rfind("\n"))
    if sentence_break > 120:
        clipped = clipped[: sentence_break + 1]
    return clipped.strip()


def _build_evidence_payload(overview: Dict[str, object], cap: int = 24) -> Dict[str, object]:
    ex_rows: List[Dict[str, object]] = []
    ar_rows: List[Dict[str, object]] = []
    seen_ex = set()
    seen_ar = set()
    order = 0

    for row in list(overview.get("exhibition_candidates", []) or []):
        source_url = str(row.get("source_url") or "").strip()
        title = _clean_exhibition_title(str(row.get("title") or ""), str(row.get("gallery") or ""))
        if not source_url or not title:
            continue
        key = (source_url, title)
        if key in seen_ex:
            continue
        seen_ex.add(key)
        ex_rows.append(
            {
                "fair": str(row.get("fair") or "").strip(),
                "gallery": str(row.get("gallery") or "").strip(),
                "title": title,
                "source_url": source_url,
                "retrieval_score": int(row.get("_retrieval_score") or 0),
                "order": order,
            }
        )
        order += 1

    order = 0
    for row in list(overview.get("artist_candidates", []) or []):
        source_url = str(row.get("source_url") or "").strip()
        artist_name = _clean_artist_name(str(row.get("artist_name_en") or row.get("artist") or ""))
        if not source_url or not artist_name:
            continue
        key = (source_url, artist_name)
        if key in seen_ar:
            continue
        seen_ar.add(key)
        ar_rows.append(
            {
                "fair": str(row.get("fair") or "").strip(),
                "gallery": str(row.get("gallery") or "").strip(),
                "artist": artist_name,
                "artist_name_en": artist_name,
                "artist_name_kana": _normalize_kana(str(row.get("artist_name_kana") or "")),
                "text_snippet": _clip_text(str(row.get("text_snippet") or ""), ART_PULSE_PROMPT_SNIPPET_CHARS),
                "source_url": source_url,
                "retrieval_score": int(row.get("_retrieval_score") or 0),
                "order": order,
            }
        )
        order += 1

    plan = dict(overview.get("image_reference_plan", {}) or {})
    if len(ex_rows) < 2:
        for row in list(plan.get("exhibition_image_candidates", []) or []):
            source_url = str(row.get("source_url") or "").strip()
            title = _clean_exhibition_title(str(row.get("title") or ""), str(row.get("gallery") or ""))
            if not source_url or not title:
                continue
            key = (source_url, title)
            if key in seen_ex:
                continue
            seen_ex.add(key)
            ex_rows.append(
                {
                    "fair": str(row.get("fair") or "").strip(),
                    "gallery": str(row.get("gallery") or "").strip(),
                    "title": title,
                    "source_url": source_url,
                    "retrieval_score": 0,
                    "order": len(ex_rows),
                }
            )
            if len(ex_rows) >= cap:
                break

    if len(ar_rows) < 2:
        for row in list(plan.get("artist_image_candidates", []) or []):
            source_url = str(row.get("source_url") or "").strip()
            artist_name = _clean_artist_name(str(row.get("artist_name_en") or ""))
            if not source_url or not artist_name:
                continue
            key = (source_url, artist_name)
            if key in seen_ar:
                continue
            seen_ar.add(key)
            ar_rows.append(
                {
                    "fair": str(row.get("fair") or "").strip(),
                    "gallery": str(row.get("gallery") or "").strip(),
                    "artist": artist_name,
                    "artist_name_en": artist_name,
                    "artist_name_kana": _normalize_kana(str(row.get("artist_name_kana") or "")),
                    "text_snippet": "",
                    "source_url": source_url,
                    "retrieval_score": 0,
                    "order": len(ar_rows),
                }
            )
            if len(ar_rows) >= cap:
                break

    ex_rows.sort(key=lambda row: (-int(row.get("retrieval_score") or 0), int(row.get("order") or 0)))
    ar_rows.sort(key=lambda row: (-int(row.get("retrieval_score") or 0), int(row.get("order") or 0)))

    for rows in (ex_rows, ar_rows):
        for row in rows:
            row.pop("order", None)

    return {
        "exhibition_rows": ex_rows[: max(0, cap)],
        "artist_rows": ar_rows[: max(0, cap)],
    }


def _build_prompt(
    fair_label: str,
    reporter: Dict[str, object],
    angle_label: str,
    angle_description: str,
    payload: Dict[str, object],
) -> str:
    first_person = _persona_first_person(reporter)
    ex_rows = list(payload.get("exhibition_rows", []) or [])[:ART_PULSE_PROMPT_EXHIBITION_ROWS]
    ar_rows = list(payload.get("artist_rows", []) or [])[:ART_PULSE_PROMPT_ARTIST_ROWS]

    ex_lines = [
        f"- fair={row.get('fair') or '-'} | gallery={row.get('gallery') or '-'} | title={row.get('title') or '-'} | source={row.get('source_url') or '-'}"
        for row in ex_rows
    ]
    ar_lines = [
        (
            f"- fair={row.get('fair') or '-'} | gallery={row.get('gallery') or '-'} | "
            f"artist={row.get('artist_name_en') or row.get('artist') or '-'} | source={row.get('source_url') or '-'}"
            + (f" | snippet={_clip_text(str(row.get('text_snippet') or ''), ART_PULSE_PROMPT_SNIPPET_CHARS)}" if row.get("text_snippet") else "")
        )
        for row in ar_rows
    ]

    return f"""
あなたはアートフェア取材記者です。以下の取材条件に基づき、読みやすい日本語の単一記事を1本だけ作成してください。

[OUTPUT FORMAT]
- JSON のみを返すこと（コードブロック禁止）
- 必須キー: title, body
- 形式: {{"title": "...", "body": "..."}}

[ARTICLE REQUIREMENTS]
- 本文は単一記事
- 見出しは付けず、空行で読みやすく区切る
- 全体を自然な2構成にする
- 前半では、指定年・指定フェアで見えたトレンドや空気感を整理する
- 後半では、その記者が特に推したい Artist / Exhibition を具体名つきで掘り下げる
- 前半から後半への接続を自然につくり、後半では少なくとも1件の Exhibition または Artist を評価つきで紹介する
- 可視文字数の目安: {ART_PULSE_SINGLE_ARTICLE_TARGET_CHARS}字前後（許容 {ART_PULSE_SINGLE_ARTICLE_MIN_CHARS}〜{ART_PULSE_SINGLE_ARTICLE_MAX_CHARS}字）
- 文体: 日本語
- {PLAIN_JAPANESE_RULE}
- 一人称は {first_person}
- 読者にとって自然な流れで、導入→トレンド観察→推しの具体例→示唆の順に構成する
- 主要な Exhibition 名 / Artist 名は payload の表記を維持し、本文に自然に織り込む
- 根拠一覧や画像マークダウンは本文に入れない（本文だけを返す）

[REPORTER]
- 記者: {reporter.get('label')}
- 記者説明: {reporter.get('description') or '-'}
- 記者style: {reporter.get('style') or '-'}
- 記者tone: {reporter.get('tone') or '-'}

[COVERAGE]
- 取材範囲: {fair_label}
- 切り口: {angle_label}
- 切り口の説明: {angle_description or '-'}

[EXHIBITION EVIDENCE]
{chr(10).join(ex_lines) if ex_lines else '- none'}

[ARTIST EVIDENCE]
{chr(10).join(ar_lines) if ar_lines else '- none'}
""".strip()


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
    return "\n".join(t for t in texts if t).strip()


def _create_openai_response(client, model: str, prompt: str) -> str:
    response = client.responses.create(
        model=model,
        input=prompt,
        max_output_tokens=min(ART_PULSE_MAX_OUTPUT_TOKENS, 1800),
        reasoning={"effort": "low"},
    )
    text = str(getattr(response, "output_text", "") or "").strip()
    if text:
        return text
    return _extract_text_from_response_output(response)


def _strip_code_fence(text: str) -> str:
    cleaned = str(text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
    return cleaned


def _unescape_jsonish_text(text: str) -> str:
    cleaned = str(text or "")
    if not cleaned:
        return ""
    if cleaned.startswith('"') and cleaned.endswith('"'):
        try:
            loaded = json.loads(cleaned)
            if isinstance(loaded, str):
                return loaded
        except Exception:
            pass
    return (
        cleaned.replace("\\r\\n", "\n")
        .replace("\\n", "\n")
        .replace("\\r", "\n")
        .replace("\\t", " ")
        .replace('\\"', '"')
        .replace("\\/", "/")
    )


def _extract_best_effort_article_body(raw_text: str) -> str:
    text = _strip_code_fence(raw_text)
    if not text:
        return ""

    candidates: List[str] = []
    for pattern in (r'(?is)"body"\s*:\s*', r"(?ims)^body\s*[:：]\s*"):
        match = re.search(pattern, text)
        if match:
            candidates.append(text[match.end() :].strip())
    candidates.append(text)

    for candidate in candidates:
        cleaned = _unescape_jsonish_text(candidate).strip()
        cleaned = re.sub(r'(?im)^\s*"?title"?\s*[:：]\s*.+$', "", cleaned).strip()
        cleaned = re.sub(r'(?im)^\s*"?body"?\s*[:：]\s*', "", cleaned).strip()
        cleaned = re.sub(r"(?m)^\s*[{}\[\],]+\s*$", "", cleaned).strip()
        cleaned = re.sub(r'^[\s"\',:]+', "", cleaned)
        cleaned = re.sub(r'[\s"\',}\]]+$', "", cleaned)
        cleaned = _strip_non_article_lines(cleaned)
        if cleaned and not (cleaned.startswith("{") and '"title"' in cleaned):
            return cleaned
    return ""


def _parse_llm_json(raw_text: str) -> Dict[str, object]:
    text = str(raw_text or "").strip()
    if not text:
        raise ValueError("empty response")
    text = _strip_code_fence(text)
    candidate_texts = [text]
    json_match = re.search(r"\{[\s\S]*\"title\"\s*:\s*[\s\S]*\"body\"\s*:\s*[\s\S]*\}", text)
    if json_match:
        candidate_texts.append(json_match.group(0).strip())

    for candidate in candidate_texts:
        try:
            parsed = json.loads(candidate)
        except Exception:
            continue
        if isinstance(parsed, dict):
            return parsed
    raise ValueError("response is not object")


def _extract_body_like_value(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ("body", "content", "article", "text", "answer", "main_body", "markdown"):
            nested = _extract_body_like_value(value.get(key))
            if nested:
                return nested
    return ""


def _sanitize_title_text(title: object) -> str:
    text = str(title or "").strip()
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    if text.startswith("{") or '"body"' in text or '"title"' in text:
        return ""
    return text


def _sanitize_article_body(raw_body: object) -> str:
    text = _extract_body_like_value(raw_body)
    if not text:
        return ""

    cleaned = _strip_code_fence(text)
    cleaned = _unescape_jsonish_text(cleaned).strip()

    try:
        parsed = _parse_llm_json(cleaned)
    except Exception:
        parsed = None
    if isinstance(parsed, dict):
        nested_body = _extract_body_like_value(parsed.get("body"))
        if nested_body:
            cleaned = nested_body.strip()

    if cleaned.startswith("{") and '"title"' in cleaned and '"body"' in cleaned:
        return ""

    leaked_json = re.search(r"^\s*\{[\s\S]*\"title\"\s*:\s*[\s\S]*\"body\"\s*:\s*[\s\S]*\}\s*$", cleaned)
    if leaked_json:
        return ""

    cleaned = cleaned.strip(" \t\r\n\"'")
    return cleaned.strip()


def _prepare_article_body(raw_body: object) -> str:
    cleaned = _sanitize_article_body(raw_body)
    if not cleaned:
        return ""
    cleaned = _ensure_article_paragraph_breaks(cleaned)
    cleaned = _truncate_article_body(cleaned, ART_PULSE_SINGLE_ARTICLE_SOFT_MAX_CHARS)
    return cleaned.strip()


def _is_user_facing_article_body(body: str) -> bool:
    cleaned = _strip_non_article_lines(body)
    if not cleaned:
        return False
    if '"title"' in cleaned or '"body"' in cleaned:
        return False
    if re.search(r"(?im)^\s*(title|body)\s*[:：]", cleaned):
        return False
    if re.search(r"(?m)^\s*[{}\[\],]+\s*$", cleaned):
        return False
    if _body_text_len(cleaned) < ART_PULSE_SINGLE_ARTICLE_HARD_MIN_CHARS:
        return False
    if _article_sentence_count(cleaned) < ART_PULSE_SINGLE_ARTICLE_MIN_SENTENCES:
        return False
    return True


def _coerce_non_json_output(raw_text: str) -> Tuple[str, str]:
    text = str(raw_text or "").strip()
    if not text:
        return "", ""

    try:
        parsed = _parse_llm_json(text)
        return (
            _sanitize_title_text(parsed.get("title")),
            _sanitize_article_body(parsed.get("body")),
        )
    except Exception:
        pass

    title = ""
    body = text

    title_match = re.search(r"(?im)^title\s*[:：]\s*(.+)$", text)
    if title_match:
        title = _sanitize_title_text(title_match.group(1))
        body = re.sub(r"(?im)^title\s*[:：]\s*.+$", "", body).strip()

    body_match = re.search(r"(?ims)^body\s*[:：]\s*(.+)$", body)
    if body_match:
        body = body_match.group(1).strip()

    body = _sanitize_article_body(body)
    return title, body


def _ensure_article_paragraph_breaks(body: str) -> str:
    text = _strip_non_article_lines(body)
    if not text:
        return ""

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    if len(paragraphs) >= 2:
        return "\n\n".join(paragraphs)

    sentences = [part.strip() for part in re.split(r"(?<=。)", text) if part.strip()]
    if len(sentences) >= 4:
        split_at = max(2, len(sentences) // 2)
        first_half = "".join(sentences[:split_at]).strip()
        second_half = "".join(sentences[split_at:]).strip()
        if first_half and second_half:
            return f"{first_half}\n\n{second_half}".strip()
    return text


def _replace_first_plain_occurrence(text: str, token: str, replacement: str) -> Tuple[str, bool]:
    target = str(token or "").strip()
    if not text or not target or replacement in text:
        return text, False
    pattern = re.compile(rf"(?<!\[){re.escape(target)}(?!\]\()")
    updated, count = pattern.subn(replacement, text, count=1)
    return updated, count > 0


def _linkify_artist_label(row: Dict[str, object]) -> str:
    artist_name = _clean_artist_name(str(row.get("artist_name_en") or row.get("artist") or ""))
    if not artist_name:
        return ""
    kana = _normalize_kana(str(row.get("artist_name_kana") or "")) or _guess_kana_from_name(artist_name)
    label = f"[{artist_name}]({_google_image_search_url(artist_name)})"
    if kana and kana != artist_name:
        label += f"（{kana}）"
    return label


def _linkify_article_body(
    body: str,
    payload: Dict[str, object],
    exhibition_urls: List[str],
    artist_urls: List[str],
) -> str:
    text = str(body or "").strip()
    if not text:
        return ""

    ex_url_set = set(_unique_urls(exhibition_urls))
    ar_url_set = set(_unique_urls(artist_urls))
    exhibition_rows = [
        row
        for row in list(payload.get("exhibition_rows", []) or [])
        if str(row.get("source_url") or "").strip() in ex_url_set
    ]
    artist_rows = [
        row
        for row in list(payload.get("artist_rows", []) or [])
        if str(row.get("source_url") or "").strip() in ar_url_set
    ]

    exhibition_rows.sort(key=lambda row: len(str(row.get("title") or "")), reverse=True)
    artist_rows.sort(key=lambda row: len(str(row.get("artist_name_en") or row.get("artist") or "")), reverse=True)

    for row in exhibition_rows:
        title = str(row.get("title") or "").strip()
        source_url = str(row.get("source_url") or "").strip()
        if not title or not source_url:
            continue
        text, _ = _replace_first_plain_occurrence(text, title, f"[{title}]({source_url})")

    for row in artist_rows:
        artist_name = _clean_artist_name(str(row.get("artist_name_en") or row.get("artist") or ""))
        if not artist_name:
            continue
        label = _linkify_artist_label(row)
        if not label:
            continue
        text, _ = _replace_first_plain_occurrence(text, artist_name, label)

    return text


def _select_used_evidence_urls(body: str, payload: Dict[str, object]) -> Tuple[List[str], List[str]]:
    text = str(body or "")
    ex_urls: List[str] = []
    ar_urls: List[str] = []

    for row in list(payload.get("exhibition_rows", []) or []):
        source_url = str(row.get("source_url") or "").strip()
        title = str(row.get("title") or "").strip()
        if not source_url:
            continue
        if source_url in text or _text_contains_exactish_token(text, title):
            ex_urls.append(source_url)

    for row in list(payload.get("artist_rows", []) or []):
        source_url = str(row.get("source_url") or "").strip()
        artist_name = str(row.get("artist_name_en") or row.get("artist") or "").strip()
        if not source_url:
            continue
        if source_url in text or _text_contains_exactish_token(text, artist_name):
            ar_urls.append(source_url)

    if not ex_urls:
        ex_urls = [
            str(row.get("source_url") or "").strip()
            for row in list(payload.get("exhibition_rows", []) or [])
            if str(row.get("source_url") or "").strip()
        ][:2]

    if not ar_urls:
        ar_urls = [
            str(row.get("source_url") or "").strip()
            for row in list(payload.get("artist_rows", []) or [])
            if str(row.get("source_url") or "").strip()
        ][:2]

    return (
        _unique_urls(ex_urls)[: max(1, MAX_EVIDENCE_URLS)],
        _unique_urls(ar_urls)[: max(1, MAX_EVIDENCE_URLS)],
    )


def _compose_url_block(urls: List[str]) -> str:
    lines = ["**根拠URL**"]
    unique_urls = _unique_urls(urls)[:MAX_EVIDENCE_URLS]
    if unique_urls:
        lines.extend([f"- {url}" for url in unique_urls])
    else:
        lines.append("- 根拠URLは表示できませんでした。")
    return "\n".join(lines)


def _build_image_candidates(overview: Dict[str, object]) -> List[Dict[str, str]]:
    plan = dict(overview.get("image_reference_plan", {}) or {})
    candidates: List[Dict[str, str]] = []
    seen_pairs = set()

    for key in ("exhibition_image_candidates", "artist_image_candidates"):
        for row in list(plan.get(key, []) or []):
            source_url = str(row.get("source_url") or "").strip()
            image_url = str(row.get("image_url") or "").strip()
            if not source_url or not image_url:
                continue
            pair = (source_url, image_url)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            label = (
                _clean_exhibition_title(str(row.get("title") or ""), str(row.get("gallery") or ""))
                if key == "exhibition_image_candidates"
                else _clean_artist_name(str(row.get("artist_name_en") or ""))
            )
            if not label:
                label = str(row.get("gallery") or "").strip() or "reference"
            candidates.append(
                {
                    "source_url": source_url,
                    "image_url": image_url,
                    "label": label,
                }
            )
    return candidates


def _select_thumbnail_rows(overview: Dict[str, object], preferred_urls: List[str], max_items: int = 4) -> List[Dict[str, str]]:
    candidates = _build_image_candidates(overview)
    if not candidates or max_items <= 0:
        return []

    by_source: Dict[str, List[Dict[str, str]]] = {}
    for row in candidates:
        by_source.setdefault(str(row.get("source_url") or "").strip(), []).append(row)

    selected: List[Dict[str, str]] = []
    seen_pairs = set()

    for source_url in _unique_urls(preferred_urls):
        for row in by_source.get(source_url, []):
            pair = (row.get("source_url"), row.get("image_url"))
            if pair in seen_pairs:
                continue
            selected.append(row)
            seen_pairs.add(pair)
            break
        if len(selected) >= max_items:
            return selected

    for row in candidates:
        pair = (row.get("source_url"), row.get("image_url"))
        if pair in seen_pairs:
            continue
        selected.append(row)
        seen_pairs.add(pair)
        if len(selected) >= max_items:
            break

    return selected


def _build_thumbnail_block(rows: List[Dict[str, str]]) -> str:
    if not rows:
        return ""

    lines: List[str] = []
    for idx, row in enumerate(rows, start=1):
        label = _clip_text(str(row.get("label") or f"reference {idx}"), 48)
        image_url = str(row.get("image_url") or "").strip()
        source_url = str(row.get("source_url") or "").strip()
        if not image_url or not source_url:
            continue
        lines.append(f"![{label}]({image_url})")
        lines.append(f"Source: <{source_url}>")
        lines.append("")

    return "\n".join(lines).strip()


def generate_art_pulse_draft(
    overview: Dict[str, object],
    reporter_id: str,
    angle_keys: List[str],
    progress_callback: Callable[[int], None] | None = None,
) -> Dict[str, object]:
    def _emit_progress(pct: int) -> None:
        if progress_callback:
            try:
                progress_callback(max(0, min(100, int(pct))))
            except Exception:
                pass

    selection = dict(overview.get("selection", {}) or {})
    fair_label = str(selection.get("fair_label") or "Frieze London + Liste Art Fair Basel")
    reporter = find_persona(reporter_id)
    angle_key, angle_label, angle_description = _pick_angle(reporter, angle_keys)
    payload = _build_evidence_payload(overview, cap=ART_PULSE_PAYLOAD_CANDIDATE_CAP)

    model = os.getenv("TEXT_MODEL", "gpt-5-mini")
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    warnings: List[str] = []

    title = ""
    raw_response = ""
    article_body = ""
    rescued_body = ""
    mode = "no_api_key"
    api_called = False

    _emit_progress(35)

    if api_key:
        try:
            from openai import OpenAI

            prompt = _build_prompt(fair_label, reporter, angle_label, angle_description, payload)
            client = OpenAI(api_key=api_key)
            raw = _create_openai_response(client, model, prompt)
            raw_response = raw
            api_called = True
            rescued_body = _prepare_article_body(_extract_best_effort_article_body(raw_response))

            try:
                parsed = _parse_llm_json(raw)
                title = _sanitize_title_text(parsed.get("title"))
                article_body = _prepare_article_body(parsed.get("body"))
                mode = "openai_single_pass"
            except Exception as parse_exc:
                warnings.append(f"single_pass parse fallback: {type(parse_exc).__name__}")
                cand_title, cand_body = _coerce_non_json_output(raw)
                title = title or _sanitize_title_text(cand_title)
                article_body = article_body or _prepare_article_body(cand_body)
                mode = "openai_single_pass_non_json"
        except Exception as api_exc:
            warnings.append(f"single_pass failed: {type(api_exc).__name__}")
            mode = "openai_single_pass_error"

    _emit_progress(70)

    if not article_body:
        if rescued_body:
            article_body = rescued_body
            mode = "openai_single_pass_best_effort"
        if not api_key:
            warnings.append("OPENAI_API_KEY が未設定のため本文を生成できませんでした。")
        elif not article_body:
            warnings.append("single_pass の本文取得に失敗しました。")
        elif raw_response:
            warnings.append("single_pass の整形式本文を best-effort prose として補完しました。")

    if article_body and not _is_user_facing_article_body(article_body):
        if rescued_body and rescued_body != article_body and _is_user_facing_article_body(rescued_body):
            article_body = rescued_body
            mode = "openai_single_pass_best_effort"
            warnings.append("整形式本文が不安定だったため、best-effort prose を採用しました。")
        else:
            warnings.append("本文候補が短すぎるか壊れているため採用しませんでした。")
            article_body = ""

    if not title:
        title = f"{fair_label}のArt Pulse（{angle_label}）"

    ex_urls: List[str] = []
    ar_urls: List[str] = []
    thumbnail_rows: List[Dict[str, str]] = []
    body_chars = 0

    if article_body:
        ex_urls, ar_urls = _select_used_evidence_urls(article_body, payload)
        article_body = _linkify_article_body(article_body, payload, ex_urls, ar_urls)

        preferred_urls = _unique_urls(ex_urls + ar_urls)
        thumbnail_rows = _select_thumbnail_rows(overview, preferred_urls, max_items=ART_PULSE_MAX_THUMBNAILS)
        thumbnail_block = _build_thumbnail_block(thumbnail_rows)
        url_block = _compose_url_block(preferred_urls)

        body_parts = [article_body]
        if thumbnail_block:
            body_parts.append(thumbnail_block)
        body_parts.append(url_block)
        final_body = "\n\n".join(part for part in body_parts if part).strip()

        body_chars = _body_text_len(article_body)
        if body_chars < ART_PULSE_SINGLE_ARTICLE_MIN_CHARS:
            warnings.append(
                f"本文は目安 {ART_PULSE_SINGLE_ARTICLE_MIN_CHARS}字未満です（{body_chars}字）。"
            )
        if body_chars > ART_PULSE_SINGLE_ARTICLE_MAX_CHARS:
            warnings.append(
                f"本文は目安 {ART_PULSE_SINGLE_ARTICLE_MAX_CHARS}字を超えています（{body_chars}字）。"
            )
    else:
        final_body = "本文を生成できませんでした。設定を確認して再実行してください。"

    all_evidence_urls = _unique_urls(ex_urls + ar_urls)

    _emit_progress(100)

    return {
        "title": title,
        "body": final_body,
        "body_chars": body_chars,
        "mode": mode,
        "warnings": warnings,
        "selected_evidence": {
            "exhibition_urls": ex_urls,
            "artist_urls": ar_urls,
            "all_urls": all_evidence_urls,
        },
        "thumbnails": thumbnail_rows,
        "debug": {
            "persona_id": reporter.get("id"),
            "persona_label": reporter.get("label"),
            "angle_key": angle_key,
            "angle_label": angle_label,
            "article_target_chars": ART_PULSE_SINGLE_ARTICLE_TARGET_CHARS,
            "article_range": [ART_PULSE_SINGLE_ARTICLE_MIN_CHARS, ART_PULSE_SINGLE_ARTICLE_MAX_CHARS],
            "thumbnail_limit": ART_PULSE_MAX_THUMBNAILS,
            "api_called": api_called,
            "evidence_counts": {
                "exhibition_rows": len(list(payload.get("exhibition_rows", []) or [])),
                "artist_rows": len(list(payload.get("artist_rows", []) or [])),
                "selected_urls": len(all_evidence_urls),
                "thumbnails": len(thumbnail_rows),
            },
        },
        "note": (
            "Art Pulse は単一記事モードです。"
            f"本文は{ART_PULSE_SINGLE_ARTICLE_TARGET_CHARS}字前後（{ART_PULSE_SINGLE_ARTICLE_MIN_CHARS}〜{ART_PULSE_SINGLE_ARTICLE_MAX_CHARS}字目安）。"
            f"サムネイルは最大{ART_PULSE_MAX_THUMBNAILS}枚、本文下に表示し、その下に根拠URLを表示します。"
        ),
    }
