from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import unicodedata
from base64 import b64encode
from typing import Dict, List, Tuple

from phase1_artist_link_utils import is_invalid_artist_name
from phase2_art_pulse_draft import _google_image_search_url
from phase2_response_style import PLAIN_JAPANESE_RULE

ADVISOR_TEXT_MAX_CHARS = 550
ADVISOR_REF_IMAGE_TOTAL = 8
ADVISOR_TEXT_SOFT_OVER_CHARS = 40
ADVISOR_TEXT_EMERGENCY_OVER_CHARS = 80
ADVISOR_MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(https?://[^)]+\)")


def _truncate_text(text: str, limit: int) -> str:
    body = (text or "").strip()
    if len(body) <= limit:
        return body
    head = body[:limit]
    cut = max(head.rfind("。"), head.rfind("、"), head.rfind("！"), head.rfind("？"))
    if cut >= int(limit * 0.7):
        return head[: cut + 1].rstrip()
    return head.rstrip() + "…"


def _soft_limit_answer_text(
    answer: str,
    limit: int = ADVISOR_TEXT_MAX_CHARS,
    soft_over_chars: int = ADVISOR_TEXT_SOFT_OVER_CHARS,
    emergency_over_chars: int = ADVISOR_TEXT_EMERGENCY_OVER_CHARS,
) -> str:
    body = (answer or "").strip()
    if not body:
        return ""

    soft_limit = max(limit, limit + max(0, int(soft_over_chars)))
    visible_chars = _visible_answer_chars(body)
    if visible_chars <= soft_limit:
        return body

    emergency_limit = max(soft_limit + 20, limit + max(0, int(emergency_over_chars)))
    if visible_chars <= emergency_limit:
        return body

    head = body[:emergency_limit]
    cut = max(head.rfind("\n\n"), head.rfind("。"), head.rfind("！"), head.rfind("？"))
    if cut >= int(emergency_limit * 0.75):
        return head[: cut + 1].rstrip()
    return _truncate_text(body, emergency_limit)


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


def _snippet(value: object, limit: int = 64) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


def _uploaded_image_data_uri(uploaded_image_payload: object) -> str:
    if not isinstance(uploaded_image_payload, dict):
        return ""
    raw = uploaded_image_payload.get("bytes")
    if not isinstance(raw, (bytes, bytearray)) or not raw:
        return ""
    mime_type = str(uploaded_image_payload.get("mime_type") or "").strip() or "image/png"
    if not mime_type.startswith("image/"):
        return ""
    return f"data:{mime_type};base64,{b64encode(bytes(raw)).decode('ascii')}"


def _parse_visual_observation(raw_output: str) -> Dict[str, object]:
    raw = str(raw_output or "").strip()
    if not raw:
        return {}
    parsed = None
    candidates = [raw]
    matched = re.search(r"\{[\s\S]*\}", raw)
    if matched:
        candidates.insert(0, matched.group(0))
    for candidate in candidates:
        for parser in (json.loads, ast.literal_eval):
            try:
                parsed = parser(candidate)
                break
            except Exception:
                continue
        if isinstance(parsed, dict):
            break
    if not isinstance(parsed, dict):
        return {}

    def _clean_text(value: object, limit: int = 96) -> str:
        text = re.sub(r"\s+", " ", str(value or "")).strip()
        if not text:
            return ""
        return text[:limit].rstrip(" ,;") if len(text) > limit else text

    def _clean_list(value: object, limit_items: int = 4, item_limit: int = 48) -> List[str]:
        items = value if isinstance(value, list) else [value]
        cleaned: List[str] = []
        seen = set()
        for item in items:
            text = _clean_text(item, limit=item_limit)
            low = text.lower()
            if not text or low in seen:
                continue
            seen.add(low)
            cleaned.append(text)
            if len(cleaned) >= limit_items:
                break
        return cleaned

    observation: Dict[str, object] = {}
    for key in ("summary", "tone", "composition", "depth", "surface", "uncertainty"):
        cleaned = _clean_text(parsed.get(key))
        if cleaned:
            observation[key] = cleaned
    palette = _clean_list(parsed.get("palette"), limit_items=4, item_limit=32)
    if palette:
        observation["palette"] = palette
    focal_areas = _clean_list(parsed.get("focal_areas"), limit_items=4, item_limit=40)
    if focal_areas:
        observation["focal_areas"] = focal_areas
    figuration = _clean_list(parsed.get("figuration"), limit_items=4, item_limit=40)
    if figuration:
        observation["figuration"] = figuration
    return observation


def _observe_uploaded_image(
    client: object,
    model: str,
    question_text: str,
    uploaded_image_payload: object,
) -> Dict[str, object]:
    data_uri = _uploaded_image_data_uri(uploaded_image_payload)
    if not data_uri:
        return {}
    observation_prompt = (
        "Look at the attached artwork image and return compact JSON only. "
        "Describe visible features only. Do not identify artist, movement, style label, era, symbolism, or story. "
        "Keep values short and concrete. "
        "Use exactly these keys: summary, palette, tone, composition, depth, surface, focal_areas, figuration, uncertainty. "
        "Use empty strings or empty arrays when unclear."
    )
    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": observation_prompt + "\nQuestion: " + (question_text or "").strip()},
                    {"type": "input_image", "image_url": data_uri},
                ],
            }
        ],
    )
    return _parse_visual_observation(str(getattr(response, "output_text", "") or ""))


def _build_visual_observation_digest(observation: object) -> str:
    if not isinstance(observation, dict):
        return ""
    lines: List[str] = []

    def _push(label: str, value: object) -> None:
        if isinstance(value, list):
            text = ", ".join(str(item or "").strip() for item in value if str(item or "").strip())
        else:
            text = str(value or "").strip()
        if text:
            lines.append(f"- {label}: {text}")

    _push("summary", observation.get("summary"))
    _push("palette", observation.get("palette"))
    _push("tone", observation.get("tone"))
    _push("composition", observation.get("composition"))
    _push("depth", observation.get("depth"))
    _push("surface", observation.get("surface"))
    _push("focal_areas", observation.get("focal_areas"))
    _push("figuration", observation.get("figuration"))
    _push("uncertainty", observation.get("uncertainty"))
    return "\n".join(lines[:8]).strip()


def _question_requests_named_references(question_text: str) -> bool:
    q = (question_text or "").strip().lower()
    if not q:
        return False
    hints = [
        "似た作家",
        "参考作家",
        "誰を見る",
        "どの作家",
        "どんな作家",
        "作家を教えて",
        "artist",
        "artists",
        "reference artist",
        "similar artist",
        "which artist",
        "who should i look at",
    ]
    return any(token in q for token in hints)


def _question_targets_uploaded_image(question_text: str, has_uploaded_image: bool) -> bool:
    if not has_uploaded_image:
        return False
    q = (question_text or "").strip().lower()
    if not q:
        return False
    direct_hints = [
        "この作品",
        "この画像",
        "この画面",
        "この写真",
        "この絵",
        "この制作",
        "今の作品",
        "添付画像",
        "attached image",
        "this image",
        "this work",
        "this piece",
        "this painting",
        "this photo",
    ]
    evaluation_hints = [
        "良い所",
        "良さ",
        "弱い",
        "強い",
        "改善",
        "良くする",
        "直す",
        "足りない",
        "構図",
        "色",
        "画面",
        "見せたい",
        "どう見える",
        "どう読む",
        "improve",
        "stronger",
        "weak",
        "what works",
        "composition",
        "palette",
    ]
    if any(token in q for token in direct_hints):
        return True
    return not _question_requests_named_references(question_text) and any(token in q for token in evaluation_hints)


def _build_evidence_digest(context: Dict[str, object], per_kind: int = 3) -> str:
    selection = context.get("selection", {}) if isinstance(context, dict) else {}
    question_focus = str(selection.get("intent_focus") or "").strip()
    broad_reference_mode = bool(
        selection.get("broad_query_mode")
        or selection.get("ideation_query")
        or question_focus in {"concept", "material", "color", "spatial"}
    )
    if broad_reference_mode:
        lines: List[str] = []
        for entity in _select_reference_entities_for_output(context, [])[: max(2, per_kind * 2)]:
            fair = str(entity.get("fair_label") or "").strip() or "フェア不明"
            gallery = str(entity.get("gallery") or "").strip() or "ギャラリー不明"
            label = str(entity.get("display_label") or entity.get("label") or "").strip() or "名称不明"
            note = _snippet(entity.get("summary_ja") or entity.get("headline_ja") or entity.get("text") or "", limit=58)
            url = str(entity.get("source_url") or "").strip()
            kind_label = "作家" if str(entity.get("kind") or "").strip() == "artist" else "展示"
            body = f"[{kind_label}] [{fair}] {gallery} / {label}"
            if note:
                body += f" | 要点: {note}"
            if url:
                body += f" | URL: {url}"
            lines.append(body)
        return "\n".join(f"- {line}" for line in lines)

    lines: List[str] = []
    for row in list(context.get("exhibition_evidence", []))[:per_kind]:
        fair = str(row.get("fair_label") or "").strip() or "フェア不明"
        gallery = str(row.get("gallery") or "").strip() or "ギャラリー不明"
        title = str(row.get("title") or "").strip() or "展示名不明"
        note = _snippet(row.get("summary_ja") or row.get("headline_ja") or row.get("text") or "", limit=58)
        url = str(row.get("source_url") or "").strip()
        body = f"[展示] [{fair}] {gallery} / {title}"
        if note:
            body += f" | 要点: {note}"
        if url:
            body += f" | URL: {url}"
        lines.append(body)
    for row in list(context.get("artist_evidence", []))[:per_kind]:
        fair = str(row.get("fair_label") or "").strip() or "フェア不明"
        gallery = str(row.get("gallery") or "").strip() or "ギャラリー不明"
        artist = str(row.get("artist_name") or "").strip()
        if is_invalid_artist_name(artist):
            continue
        note = _snippet(row.get("summary_ja") or row.get("headline_ja") or row.get("text") or "", limit=58)
        url = str(row.get("source_url") or "").strip()
        body = f"[作家] [{fair}] {gallery} / {artist}"
        if note:
            body += f" | 要点: {note}"
        if url:
            body += f" | URL: {url}"
        lines.append(body)
    return "\n".join(f"- {line}" for line in lines)


def _detect_cross_fair_mode(context: Dict[str, object]) -> Tuple[bool, List[str]]:
    fair_order: List[str] = []
    seen = set()
    for key in ("exhibition_evidence", "artist_evidence"):
        for row in list(context.get(key, [])):
            fair = str(row.get("fair_label") or "").strip()
            if not fair or fair in seen:
                continue
            seen.add(fair)
            fair_order.append(fair)
    return len(fair_order) >= 2, fair_order


def _build_cross_fair_digest(context: Dict[str, object], fair_labels: List[str], per_fair_kind: int = 2) -> str:
    lines: List[str] = []
    ex_rows = list(context.get("exhibition_evidence", []))
    ar_rows = list(context.get("artist_evidence", []))
    for fair in fair_labels:
        ex_items = [str(r.get("title") or "").strip() for r in ex_rows if str(r.get("fair_label") or "").strip() == fair]
        ar_items = [
            str(r.get("artist_name") or "").strip()
            for r in ar_rows
            if str(r.get("fair_label") or "").strip() == fair
            and not is_invalid_artist_name(str(r.get("artist_name") or "").strip())
        ]
        ex_text = " / ".join([x for x in ex_items[:per_fair_kind] if x]) or "(展示根拠なし)"
        ar_text = " / ".join([x for x in ar_items[:per_fair_kind] if x]) or "(作家根拠なし)"
        lines.append(f"- [{fair}] 展示: {ex_text} | 作家: {ar_text}")
    return "\n".join(lines)


def _is_broad_query_mode(context: Dict[str, object]) -> bool:
    selection = context.get("selection", {}) if isinstance(context, dict) else {}
    return bool(selection.get("broad_query_mode"))


def _get_rotation_index(context: Dict[str, object]) -> int:
    selection = context.get("selection", {}) if isinstance(context, dict) else {}
    try:
        return max(0, int(selection.get("rotation_index") or 0))
    except Exception:
        return 0


def _get_recent_broad_history(context: Dict[str, object]) -> List[dict]:
    selection = context.get("selection", {}) if isinstance(context, dict) else {}
    values = selection.get("recent_broad_history", [])
    return list(values) if isinstance(values, list) else []


def _classify_broad_query(question_text: str) -> str:
    q = (question_text or "").strip()
    if any(token in q for token in ["色", "カラー", "色彩", "配色"]):
        return "color"
    if any(token in q for token in ["素材", "材", "マテリアル"]):
        return "material"
    return "general"


QUESTION_FOCUS_ORDER = (
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

QUESTION_FOCUS_HINTS = {
    "video": ["映像", "動画", "ビデオ", "video", "film", "projection", "moving image", "上映", "映写", "アニメーション", "animation"],
    "sound": ["音", "sound", "audio", "acoustic", "sonic", "listening", "noise", "voice", "vibration", "録音"],
    "sculpture": ["彫刻", "sculpture", "立体", "object", "ceramic", "ceramics", "clay", "陶", "陶器", "オブジェ", "物体"],
    "photography": ["写真", "photography", "photo", "photographic", "staged", "fiction", "fictional", "虚構", "演出写真", "イメージ"],
    "painting": ["絵画", "painting", "paint", "canvas", "油彩", "油絵", "acrylic", "アクリル", "絵具"],
    "spatial": ["インスタレーション", "installation", "展示空間", "spatial", "site-specific", "site specific", "導線", "動線", "歩かせ", "歩く", "空間", "room", "architecture"],
    "performance": ["パフォーマンス", "performance", "lecture-performance", "lecture performance", "身体", "body", "gesture", "choreography", "行為", "朗読"],
    "concept": ["コンセプト", "concept", "テーマ", "主題", "着想", "発想", "思想", "問い", "問題意識", "考え方", "意味"],
    "material": ["素材", "材", "マテリアル", "material", "質感", "手触り", "布", "紙", "木", "金属", "樹脂", "フィルム", "層"],
    "color": ["色", "カラー", "色彩", "配色", "色調", "トーン", "明度", "彩度", "グレー", "青", "赤", "黄", "緑", "黒", "白"],
    "artist": ["artist", "アーティスト", "作家", "誰", "who"],
}


def _detect_question_focus(question_text: str) -> str:
    q = (question_text or "").strip().lower()
    if not q:
        return "general"

    best_focus = ""
    best_score = 0
    for focus in QUESTION_FOCUS_ORDER:
        score = _focus_signal_score(q, focus)
        if score > best_score:
            best_focus = focus
            best_score = score
    if best_score > 0:
        return best_focus

    query_kind = _classify_broad_query(question_text)
    if query_kind == "color":
        return "color"
    if query_kind == "material":
        return "material"
    return "general"


def _focus_signal_score(text: str, question_focus: str) -> int:
    low = (text or "").lower()
    return sum(1 for hint in QUESTION_FOCUS_HINTS.get(question_focus, []) if hint and hint in low)


def _allows_multiple_directions(question_text: str) -> bool:
    q = (question_text or "").strip().lower()
    if not q:
        return False
    hints = [
        "複数",
        "いくつか",
        "何案",
        "何通り",
        "何パターン",
        "選択肢",
        "候補を",
        "比較",
        "比べ",
        "並べて",
    ]
    return any(token in q for token in hints)


def _candidate_row_mode(question_text: str, question_focus: str) -> str:
    q = (question_text or "").strip().lower()
    asks_artist = any(token in q for token in ["作家", "artist", "アーティスト", "誰", "who"])
    asks_ideation = any(
        token in q
        for token in ["考え方", "発想", "問い", "設計", "立てる", "見せたい", "強くしたい", "感じさせたい", "意味を変えたい"]
    )
    asks_exhibition = any(
        token in q
        for token in ["展示", "インスタレーション", "installation", "展示空間", "空間", "導線", "動線", "spatial"]
    )
    if asks_artist and not asks_exhibition:
        return "artist"
    if asks_exhibition and not asks_artist:
        return "exhibition"
    if asks_ideation and question_focus in {"sound", "spatial", "concept"} and not asks_artist:
        return "exhibition"
    if question_focus in {"video", "sound", "sculpture", "photography", "painting", "performance"} and not asks_exhibition:
        return "artist"
    if question_focus == "spatial" and not asks_artist:
        return "exhibition"
    return "mixed"


def _is_broad_ideation_query(question_text: str, context: Dict[str, object], question_focus: str) -> bool:
    q = (question_text or "").strip().lower()
    if not q or question_focus == "artist":
        return False
    if _is_broad_query_mode(context):
        return True
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
        "空間全体",
    ]
    return any(token in q for token in ideation_hints)


def _family_catalog(query_kind: str) -> List[dict]:
    if query_kind == "color":
        return [
            {"id": "muted_earth", "label": "低彩度土色系", "items": ["低彩度グレー + 深い緑", "青灰 + 乳白", "焦げ茶 + 鈍い金属色"]},
            {"id": "cold_light", "label": "冷光系", "items": ["温白 + 鉄紺", "薄い青白 + 鉛色", "霧のような灰青"]},
            {"id": "industrial_contrast", "label": "産業コントラスト系", "items": ["土色 + 黒", "赤茶 + 鉛色", "黄土 + 墨色"]},
            {"id": "textile_warm", "label": "布系ウォーム", "items": ["薄い桃灰 + 炭色", "生成り + くすんだ赤", "砂色 + オリーブ"]},
            {"id": "signal_participatory", "label": "信号色アクセント系", "items": ["青緑 + 生成り", "黄緑 + グレー", "鈍い橙 + 墨色"]},
            {"id": "afterimage_projection", "label": "残像投影系", "items": ["青紫の残像 + 黒", "薄黄 + 灰青", "白光 + 深い藍"]},
        ]
    return [
        {"id": "paper_drawing", "label": "紙面/ドローイング系", "items": ["和紙", "鉛筆線", "薄いパネル"]},
        {"id": "light_chemical", "label": "光/化学系", "items": ["透明樹脂", "半透明フィルム", "反射面"]},
        {"id": "spatial_build", "label": "立体/建材系", "items": ["木質パネル", "建材端材", "石粉塗料"]},
        {"id": "textile_fiber", "label": "布/繊維系", "items": ["布", "フェルト", "縫製の継ぎ目"]},
        {"id": "sound_tool", "label": "音/道具系", "items": ["金物", "道具痕", "可動パーツ"]},
        {"id": "video_participatory", "label": "映像/参加型系", "items": ["映像投影", "印刷物", "参加型メモ"]},
    ]


def _history_family_counts(history: List[dict], key: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for item in history:
        value = str(item.get(key) or "").strip()
        if not value:
            continue
        counts[value] = counts.get(value, 0) + 1
    return counts


def _choose_proposal_families(question_text: str, context: Dict[str, object]) -> Dict[str, dict]:
    query_kind = _classify_broad_query(question_text)
    rotation_index = _get_rotation_index(context)
    history = _get_recent_broad_history(context)
    family_counts = _history_family_counts(history, "proposal_family")
    catalog = _family_catalog(query_kind)
    ordered = sorted(
        catalog,
        key=lambda family: (
            family_counts.get(family["id"], 0),
            (catalog.index(family) - rotation_index) % len(catalog),
        ),
    )
    return {
        "query_kind": query_kind,
        "frieze": ordered[0],
        "liste": ordered[1 % len(ordered)],
        "bridge": ordered[2 % len(ordered)],
    }


def _history_value_counts(history: List[dict], key: str) -> Dict[str, int]:
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


def _pick_anchor(rows: List[dict], history: List[dict], rotation_index: int) -> dict:
    if not rows:
        return {}
    gallery_counts = _history_value_counts(history, "anchor_galleries")
    artist_counts = _history_value_counts(history, "anchor_artists")
    ordered = sorted(
        rows,
        key=lambda row: (
            gallery_counts.get(str(row.get("gallery") or "").strip(), 0)
            + artist_counts.get(str(row.get("artist_name") or "").strip(), 0),
            len(str(row.get("summary_ja") or row.get("headline_ja") or "").strip()) * -1,
            str(row.get("gallery") or ""),
            str(row.get("artist_name") or row.get("title") or ""),
        ),
    )
    return ordered[rotation_index % len(ordered)]


def _build_broad_diversity_plan(question_text: str, context: Dict[str, object]) -> Dict[str, object]:
    cross_fair_mode, fair_labels = _detect_cross_fair_mode(context)
    history = _get_recent_broad_history(context)
    rotation_index = _get_rotation_index(context)
    families = _choose_proposal_families(question_text, context)
    ex_rows = list(context.get("exhibition_evidence", []))
    ar_rows = list(context.get("artist_evidence", []))

    def fair_rows(rows: List[dict], fair_label: str) -> List[dict]:
        return [row for row in rows if str(row.get("fair_label") or "").strip() == fair_label]

    fair_a = fair_labels[0] if fair_labels else "Frieze London"
    fair_b = fair_labels[1] if len(fair_labels) > 1 else fair_a
    fair_a_anchor = _pick_anchor(fair_rows(ex_rows, fair_a) + fair_rows(ar_rows, fair_a), history, rotation_index)
    fair_b_anchor = _pick_anchor(fair_rows(ex_rows, fair_b) + fair_rows(ar_rows, fair_b), history, rotation_index)
    bridge_anchor = _pick_anchor(ex_rows + ar_rows, history, rotation_index + 1)

    return {
        "cross_fair_mode": cross_fair_mode,
        "fair_a": fair_a,
        "fair_b": fair_b,
        "fair_a_anchor": fair_a_anchor,
        "fair_b_anchor": fair_b_anchor,
        "bridge_anchor": bridge_anchor,
        "query_kind": families["query_kind"],
        "frieze_family": families["frieze"],
        "liste_family": families["liste"],
        "bridge_family": families["bridge"],
        "rotation_index": rotation_index,
    }


def _extract_answer(raw_output: str) -> str:
    raw = (raw_output or "").strip()
    if not raw:
        return ""

    candidates = [raw]
    matched = re.search(r"\{[\s\S]*\}", raw)
    if matched:
        candidates.insert(0, matched.group(0))

    for candidate in candidates:
        parsed = None
        for parser in (json.loads, ast.literal_eval):
            try:
                parsed = parser(candidate)
                break
            except Exception:
                continue
        if parsed is None:
            continue

        if isinstance(parsed, str):
            text = parsed.strip()
            if text:
                return text
            continue

        if isinstance(parsed, dict):
            for key in ("answer", "text", "content", "output_text", "message"):
                value = parsed.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
            continue

        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict):
                    for key in ("answer", "text", "content"):
                        value = item.get(key)
                        if isinstance(value, str) and value.strip():
                            return value.strip()
                elif isinstance(item, str) and item.strip():
                    return item.strip()

    if raw.startswith("{") and raw.endswith("}") and ("answer" in raw or "text" in raw):
        return ""
    return raw


def _ensure_plain_answer_text(answer: str) -> str:
    body = str(answer or "").strip()
    if not body:
        return ""
    body = re.sub(r"^```(?:json)?\s*|\s*```$", "", body, flags=re.IGNORECASE).strip()
    unwrapped = _extract_answer(body)
    if unwrapped and unwrapped != body:
        body = unwrapped.strip()
    if re.match(r"^\s*(\{[\s\S]*\}|\[[\s\S]*\])\s*$", body):
        second = _extract_answer(body).strip()
        if second and second != body:
            body = second
        else:
            return ""
    return body


def _normalize_answer_text(answer: str) -> str:
    text = (answer or "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not lines:
        return ""

    dedup_lines: List[str] = []
    seen = set()
    for line in lines:
        key = re.sub(r"\s+", "", line)
        if key in seen:
            continue
        seen.add(key)
        dedup_lines.append(line)

    body = "\n".join(dedup_lines)
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip()


def _ensure_natural_ending(answer: str) -> str:
    body = str(answer or "").strip()
    if not body:
        return ""

    bracket_pairs = [("（", "）"), ("(", ")"), ("「", "」"), ("『", "』"), ("【", "】")]
    for left, right in bracket_pairs:
        while body.count(left) > body.count(right):
            cut = body.rfind(left)
            if cut < 0:
                break
            body = body[:cut].rstrip()

    bad_tail_tokens = [
        "…",
        "、",
        ",",
        "で",
        "と",
        "が",
        "を",
        "に",
        "へ",
        "や",
        "から",
        "ので",
        "けど",
        "また",
        "そして",
        "しかし",
    ]
    end_ok = ("。", "！", "？", "!", "?", "」", "』", "】", "）", ")")
    tail_bad = any(body.endswith(token) for token in bad_tail_tokens)
    if tail_bad or not body.endswith(end_ok):
        cut = max(body.rfind("。"), body.rfind("！"), body.rfind("？"), body.rfind("!"), body.rfind("?"))
        if cut >= int(len(body) * 0.45):
            body = body[: cut + 1].rstrip()
        elif not body.endswith(end_ok):
            body = body.rstrip("、,") + "。"
    return body.strip()


def _looks_like_biography_dump(answer: str) -> bool:
    text = _plain_answer_text(answer)
    if not text:
        return False
    year_hits = len(re.findall(r"(?:19|20)\d{2}年?", text))
    bio_markers = sum(text.count(token) for token in ["在住", "生まれ", "出身", "活動", "発表", "制作", "受賞"])
    paragraphs = [line.strip() for line in text.splitlines() if line.strip()]
    long_para_count = sum(1 for line in paragraphs if len(line) >= 60)
    return (year_hits >= 2 and bio_markers >= 3) or (long_para_count >= 3 and bio_markers >= 4)


def _looks_like_intent_mismatch(answer: str, question_text: str) -> bool:
    question_focus = _detect_question_focus(question_text)
    if question_focus in {"general", "artist"}:
        return False
    text = _plain_answer_text(answer).lower()
    if not text:
        return True
    if _focus_signal_score(text, question_focus) > 0:
        return False
    other_focuses = [focus for focus in QUESTION_FOCUS_ORDER if focus not in {"artist", question_focus}]
    return max((_focus_signal_score(text, key) for key in other_focuses), default=0) >= 2


def _is_page_description_like_text(text: str) -> bool:
    low = str(text or "").strip().lower()
    if not low:
        return False
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
    return any(marker in low for marker in markers)


def _trim_trailing_fragment(answer: str, question_focus: str) -> str:
    body = str(answer or "").strip()
    if not body:
        return ""
    sentences = re.findall(r"[^。！？!?]+[。！？!?]?", body)
    if len(sentences) < 2:
        return body
    tail = sentences[-1].strip()
    tail_plain = tail.rstrip("。！？!?").strip()
    if not tail_plain:
        return body
    nounish_tail = bool(re.search(r"(展示|作品|作家|写真|彫刻|映像|空間|インスタレーション|シリーズ|プロジェクト)$", tail_plain))
    weak_tail = _focus_signal_score(tail_plain, question_focus) <= 0 if question_focus != "general" else len(tail_plain) < 28
    if _is_page_description_like_text(tail_plain) or (nounish_tail and weak_tail and len(tail_plain) <= 80):
        trimmed = "".join(sentences[:-1]).strip()
        return trimmed or body
    return body


def _needs_grounded_synthesis(
    question_text: str,
    context: Dict[str, object],
    question_focus: str = "",
) -> bool:
    selection = context.get("selection", {}) if isinstance(context, dict) else {}
    grounded_anchor_count = max(0, int(selection.get("grounded_anchor_count") or 0))
    if grounded_anchor_count <= 0:
        return False
    focus = question_focus or _detect_question_focus(question_text)
    if bool(selection.get("ideation_query")) or _is_broad_ideation_query(question_text, context, focus):
        return True
    q = (question_text or "").strip().lower()
    synthesis_hints = [
        "おすすめ",
        "教えて",
        "参考",
        "誰を見る",
        "どの作家",
        "どの展示",
        "基準",
        "考え方",
        "発想",
        "問い",
        "設計",
        "導線",
        "動線",
        "どうするといい",
        "どう考える",
        "どう発想",
        "どう問い",
        "見せたい",
        "強くしたい",
        "感じさせたい",
        "意味を変えたい",
    ]
    return any(hint in q for hint in synthesis_hints) or focus in {
        "artist",
        "concept",
        "sound",
        "spatial",
        "photography",
        "sculpture",
        "performance",
        "video",
        "painting",
    }


def _should_include_action_steps(question_text: str) -> bool:
    q = (question_text or "").strip().lower()
    if not q:
        return False
    hints = [
        "手順",
        "方法",
        "どうやって",
        "進め方",
        "ステップ",
        "具体的に",
        "段取り",
        "how to",
        "step",
    ]
    return any(token in q for token in hints)


def _should_allow_gallery_mentions(question_text: str) -> bool:
    q = (question_text or "").strip().lower()
    if not q:
        return False
    return any(token in q for token in ["gallery", "galleries", "ギャラリー"])


def _strip_fixed_headings(text: str) -> str:
    if not text:
        return ""
    lines = [ln.strip() for ln in str(text).splitlines() if ln.strip()]
    cleaned: List[str] = []
    for line in lines:
        body = re.sub(r"^(結論|根拠|次アクション)\s*[:：]\s*", "", line).strip()
        if body:
            cleaned.append(body)
    return "\n".join(cleaned).strip()


def _strip_rigid_template_markers(text: str) -> str:
    body = str(text or "")
    for marker in ["結論：", "結論:", "理由：", "理由:", "具体例：", "具体例:"]:
        body = body.replace(marker, "")
    body = re.sub(
        r"^\s*(?:短く言うと|短くまとめると|結論から言うと|結論を先に言うと|例を(?:いくつか)?挙げます|理由(?:と具体案)?を(?:短く)?示します|主軸案|補助案|3点で示します|方向性の例をいくつか出します)[。:\s]*",
        "",
        body,
    )
    body = re.sub(r"([。！？]\s*)([A-CＡ-Ｃ])\s*[:：]\s*", r"\1", body)
    body = re.sub(r"(^|\n)([A-CＡ-Ｃ])\s*[:：]\s*", r"\1", body)
    body = re.sub(r"\s{2,}", " ", body)
    body = re.sub(r"。\s+。", "。", body)
    return body.strip()


def _should_preserve_list_style(question_text: str) -> bool:
    q = (question_text or "").strip().lower()
    if not q:
        return False
    return any(token in q for token in ["箇条書き", "リスト", "整理して", "項目で", "3点", "箇条"])


def _strip_fair_labels(text: str, fair_labels: List[str]) -> str:
    body = str(text or "")
    replacement = "会場"
    aliases: List[str] = []
    for fair in fair_labels:
        key = str(fair or "").strip()
        if not key:
            continue
        aliases.append(key)
        low = key.lower()
        if "frieze" in low:
            aliases.extend(["Frieze London", "Frieze"])
        if "liste" in low:
            aliases.extend(["Liste Art Fair Basel", "Liste Art Fair", "Liste"])
    for alias in sorted(set(aliases), key=len, reverse=True):
        body = body.replace(alias, replacement)
    pattern = re.escape(replacement) + r"(?:\s*/\s*" + re.escape(replacement) + r")+"
    body = re.sub(pattern, replacement, body)
    body = re.sub(r"\s{2,}", " ", body)
    return body.strip()


def _safe_link_label(text: str, limit: int | None = 42) -> str:
    label = str(text or "").strip()
    if limit is not None and limit > 0:
        label = _snippet(label, limit=limit)
    label = label.replace("[", "（").replace("]", "）")
    return label.strip()


def _exhibition_link_label(title: str, limit: int | None = 34) -> str:
    return _safe_link_label(str(title or "").strip(), limit=limit)


def _build_art_pulse_style_reference_lines(selected_entities: List[dict]) -> List[str]:
    lines: List[str] = []
    seen = set()

    for entity in selected_entities:
        if str(entity.get("kind") or "").strip() == "artist" and is_invalid_artist_name(
            str(entity.get("display_label") or entity.get("label") or "").strip()
        ):
            continue
        label = _safe_link_label(str(entity.get("display_label") or entity.get("label") or "").strip(), limit=None)
        link_url = str(entity.get("link_url") or "").strip()
        if not (label and link_url):
            continue
        item = f"- [{label}]({link_url})"
        kana = str(entity.get("artist_name_kana") or "").strip()
        if str(entity.get("kind") or "").strip() == "artist" and kana:
            item += f"（{_safe_link_label(kana, limit=None)}）"
        if item not in seen:
            seen.add(item)
            lines.append(item)

    return lines


def _select_reference_entities_for_output(
    context: Dict[str, object],
    selected_entities: List[dict],
) -> List[dict]:
    # selected_entities がある場合は、その集合だけを参照例正本として返す。
    # selected_entities が空の場合のみ、evidence 起点の候補集合を返す。
    selection = context.get("selection", {}) if isinstance(context, dict) else {}
    question_focus = str(selection.get("intent_focus") or "").strip()
    broad_reference_mode = bool(
        selection.get("broad_query_mode")
        or selection.get("ideation_query")
        or question_focus in {"concept", "material", "color", "spatial"}
    )
    cross_fair_mode, _ = _detect_cross_fair_mode(context)
    candidate_pool: List[dict] = []
    mention_order_map: Dict[tuple[str, str, str, str], int] = {}
    for idx, candidate in enumerate(selected_entities, start=1):
        dedup_key = (
            str(candidate.get("kind") or "").strip(),
            str(candidate.get("display_label") or candidate.get("label") or "").strip(),
            str(candidate.get("link_url") or "").strip(),
            str(candidate.get("source_url") or "").strip(),
        )
        current = mention_order_map.get(dedup_key)
        if current is None or idx < current:
            mention_order_map[dedup_key] = idx

    for candidate in _build_selected_entity_candidates(context):
        item = dict(candidate)
        kind = str(item.get("kind") or "").strip()
        label = str(item.get("display_label") or item.get("label") or "").strip()
        if kind == "artist" and is_invalid_artist_name(label):
            continue
        link_url = str(item.get("link_url") or "").strip()
        source_url = str(item.get("source_url") or "").strip()
        local_path = str(item.get("local_path") or "").strip()
        r2_key = str(item.get("r2_key") or "").strip()
        image_url = str(item.get("image_url") or "").strip()
        if not (kind and label and link_url):
            continue
        dedup_key = (kind, label, link_url, source_url)
        if dedup_key in mention_order_map:
            item["mention_order"] = mention_order_map[dedup_key]
        item["has_image"] = bool(local_path or r2_key or image_url)
        item["display_label"] = label
        item["_tiebreak_seed"] = int.from_bytes(
            hashlib.blake2b(
                "\n".join(
                    [
                        kind.lower(),
                        str(item.get("fair_label") or "").strip().lower(),
                        str(item.get("gallery") or "").strip().lower(),
                        label.lower(),
                        source_url.lower(),
                    ]
                ).encode("utf-8", "ignore"),
                digest_size=8,
            ).digest(),
            "big",
        )
        candidate_pool.append(item)

    remaining: List[dict] = []
    seen = set()
    for candidate in candidate_pool:
        dedup_key = (
            str(candidate.get("kind") or "").strip(),
            str(candidate.get("display_label") or candidate.get("label") or "").strip(),
            str(candidate.get("link_url") or "").strip(),
            str(candidate.get("source_url") or "").strip(),
        )
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        remaining.append(candidate)

    selected: List[dict] = []
    source_counts: Dict[str, int] = {}
    gallery_counts: Dict[str, int] = {}
    fair_counts: Dict[str, int] = {}
    kind_counts: Dict[str, int] = {}
    available_kinds = {
        str(candidate.get("kind") or "").strip()
        for candidate in remaining
        if str(candidate.get("kind") or "").strip()
    }

    def _candidate_dedup_key(candidate: dict) -> tuple[str, str, str, str]:
        return (
            str(candidate.get("kind") or "").strip(),
            str(candidate.get("display_label") or candidate.get("label") or "").strip(),
            str(candidate.get("link_url") or "").strip(),
            str(candidate.get("source_url") or "").strip(),
        )

    def _apply_selected_counts(chosen: dict) -> None:
        source_url = str(chosen.get("source_url") or "").strip()
        gallery = str(chosen.get("gallery") or "").strip()
        fair = str(chosen.get("fair_label") or "").strip()
        kind = str(chosen.get("kind") or "").strip()
        if source_url:
            source_counts[source_url] = source_counts.get(source_url, 0) + 1
        if gallery:
            gallery_counts[gallery] = gallery_counts.get(gallery, 0) + 1
        if fair:
            fair_counts[fair] = fair_counts.get(fair, 0) + 1
        if kind:
            kind_counts[kind] = kind_counts.get(kind, 0) + 1

    if mention_order_map:
        by_dedup_key: Dict[tuple[str, str, str, str], dict] = {
            _candidate_dedup_key(candidate): dict(candidate)
            for candidate in remaining
        }
        by_kind_label: Dict[tuple[str, str], dict] = {}
        for candidate in remaining:
            key = (
                str(candidate.get("kind") or "").strip(),
                str(candidate.get("display_label") or candidate.get("label") or "").strip(),
            )
            by_kind_label.setdefault(key, dict(candidate))
        prioritized: List[dict] = []
        seen_prioritized = set()
        for candidate in remaining:
            dedup_key = _candidate_dedup_key(candidate)
            mention_order = mention_order_map.get(dedup_key)
            if mention_order is None:
                continue
            if dedup_key in seen_prioritized:
                continue
            seen_prioritized.add(dedup_key)
            item = dict(candidate)
            item["mention_order"] = int(mention_order)
            prioritized.append(item)
        for selected_candidate in selected_entities:
            dedup_key = (
                str(selected_candidate.get("kind") or "").strip(),
                str(selected_candidate.get("display_label") or selected_candidate.get("label") or "").strip(),
                str(selected_candidate.get("link_url") or "").strip(),
                str(selected_candidate.get("source_url") or "").strip(),
            )
            mention_order = mention_order_map.get(dedup_key)
            if mention_order is None or dedup_key in seen_prioritized:
                continue
            matched = by_dedup_key.get(dedup_key)
            if matched is None:
                matched = by_kind_label.get((dedup_key[0], dedup_key[1]))
            if matched is None:
                continue
            item = dict(matched)
            item["mention_order"] = int(mention_order)
            prioritized.append(item)
            seen_prioritized.add(dedup_key)
        prioritized.sort(
            key=lambda c: (
                int(c.get("mention_order") or 999),
                int(c.get("evidence_rank") or 999),
                -int(c.get("_tiebreak_seed") or 0),
            )
        )
        return prioritized[:ADVISOR_REF_IMAGE_TOTAL]

    def _base_score(candidate: dict) -> int:
        kind = str(candidate.get("kind") or "").strip()
        label = str(candidate.get("display_label") or candidate.get("label") or "").strip()
        mention_order = int(candidate.get("mention_order") or 0)
        evidence_rank = max(1, int(candidate.get("evidence_rank") or 999))
        gallery_cohort_index = int(candidate.get("gallery_cohort_index")) if candidate.get("gallery_cohort_index") is not None else -1
        text_blob = " ".join(
            [
                label,
                str(candidate.get("headline_ja") or "").strip(),
                str(candidate.get("summary_ja") or "").strip(),
                str(candidate.get("text") or "").strip()[:1200],
            ]
        ).lower()
        focus_score = _focus_signal_score(text_blob, question_focus) if question_focus else 0
        score = 0
        if mention_order > 0:
            if broad_reference_mode and question_focus in {"concept", "material", "color", "spatial"}:
                score += max(18, 78 - ((mention_order - 1) * 12))
            elif broad_reference_mode:
                score += max(28, 108 - ((mention_order - 1) * 16))
            else:
                score += max(40, 180 - ((mention_order - 1) * 24))
        score += max(0, 80 - (evidence_rank * 5))
        score += focus_score * 24
        if str(candidate.get("summary_ja") or "").strip():
            score += 10
        if str(candidate.get("headline_ja") or "").strip():
            score += 6
        if question_focus == "material" and broad_reference_mode:
            if kind == "artist":
                score += 8
            elif kind == "exhibition":
                score += 10
        elif question_focus in {"artist", "material"} and kind == "artist":
            score += 16
        elif question_focus == "concept" and kind == "artist":
            score += 10
        elif question_focus in {"spatial", "color"} and kind == "exhibition":
            score += 12
        if broad_reference_mode and gallery_cohort_index >= 0:
            if question_focus in {"concept", "material", "color", "spatial"}:
                score -= max(0, 16 - (min(gallery_cohort_index, 8) * 2))
            else:
                score -= max(0, 8 - min(gallery_cohort_index, 8))
        return score

    while remaining and len(selected) < ADVISOR_REF_IMAGE_TOTAL:
        scored_candidates: List[tuple[int, dict, int, tuple[int, ...]]] = []
        for idx, candidate in enumerate(remaining):
            kind = str(candidate.get("kind") or "").strip()
            source_url = str(candidate.get("source_url") or "").strip()
            gallery = str(candidate.get("gallery") or "").strip()
            fair = str(candidate.get("fair_label") or "").strip()
            score = _base_score(candidate)
            if source_url:
                score -= source_counts.get(source_url, 0) * 80
            if gallery:
                score -= gallery_counts.get(gallery, 0) * (55 if broad_reference_mode else 35)
            if broad_reference_mode:
                if len(available_kinds) >= 2:
                    kind_penalty = 46 if question_focus in {"concept", "material", "color", "spatial"} else 28
                    score -= kind_counts.get(kind, 0) * kind_penalty
                if cross_fair_mode and fair:
                    score -= fair_counts.get(fair, 0) * 18
            if broad_reference_mode:
                sort_key = (
                    score,
                    -(int(candidate.get("evidence_rank") or 999)),
                    -(int(candidate.get("mention_order") or 999)),
                    -(int(candidate.get("gallery_cohort_index")) if candidate.get("gallery_cohort_index") is not None else -1),
                    -int(candidate.get("_tiebreak_seed") or 0),
                )
            else:
                sort_key = (
                    score,
                    -(int(candidate.get("mention_order") or 999)),
                    -(int(candidate.get("evidence_rank") or 999)),
                    -int(candidate.get("_tiebreak_seed") or 0),
                )
            scored_candidates.append((idx, candidate, score, sort_key))
        if not scored_candidates:
            break
        scored_candidates.sort(key=lambda item: item[3], reverse=True)
        best_index = scored_candidates[0][0]
        if best_index < 0:
            break
        chosen = remaining.pop(best_index)
        selected.append(chosen)
        _apply_selected_counts(chosen)
    return selected


def _plain_answer_text(answer: str) -> str:
    return re.sub(r"\[([^\]]+)\]\(https?://[^)]+\)", r"\1", str(answer or ""))


def _build_selected_entity_candidates(context: Dict[str, object]) -> List[dict]:
    candidates: List[dict] = []
    known_artist_labels: set[str] = set()

    for idx, row in enumerate(list(context.get("exhibition_evidence", [])), start=1):
        title = str(row.get("title") or "").strip()
        source_url = str(row.get("source_url") or "").strip()
        if not (title and source_url):
            continue
        image_item = _build_exhibition_reference_image_item(row) or {}
        candidates.append(
            {
                "kind": "exhibition",
                "label": title,
                "display_label": title,
                "link_url": source_url,
                "source_url": source_url,
                "fair_label": str(row.get("fair_label") or "").strip(),
                "gallery": str(row.get("gallery") or "").strip(),
                "headline_ja": str(row.get("headline_ja") or "").strip(),
                "summary_ja": str(row.get("summary_ja") or "").strip(),
                "text": str(row.get("text") or "").strip(),
                "evidence_rank": idx,
                "gallery_cohort_index": int(row.get("_gallery_cohort_index")) if row.get("_gallery_cohort_index") is not None else -1,
                "local_path": str(image_item.get("local_path") or "").strip(),
                "r2_key": str(image_item.get("r2_key") or "").strip(),
                "image_url": str(image_item.get("image_url") or "").strip(),
            }
        )

    for idx, row in enumerate(list(context.get("artist_evidence", [])), start=1):
        artist = str(row.get("artist_name") or "").strip()
        if not artist or is_invalid_artist_name(artist):
            continue
        google_url = _google_image_search_url(artist)
        if not google_url:
            continue
        known_artist_labels.add(artist)
        image_item = _build_artist_reference_image_item(row) or {}
        candidates.append(
            {
                "kind": "artist",
                "label": artist,
                "display_label": artist,
                "link_url": google_url,
                "source_url": str(row.get("source_url") or "").strip(),
                "artist_name_kana": str(row.get("artist_name_kana") or "").strip(),
                "fair_label": str(row.get("fair_label") or "").strip(),
                "gallery": str(row.get("gallery") or "").strip(),
                "headline_ja": str(row.get("headline_ja") or "").strip(),
                "summary_ja": str(row.get("summary_ja") or "").strip(),
                "text": str(row.get("text") or "").strip(),
                "evidence_rank": idx,
                "gallery_cohort_index": int(row.get("_gallery_cohort_index")) if row.get("_gallery_cohort_index") is not None else -1,
                "local_path": str(image_item.get("local_path") or "").strip(),
                "r2_key": str(image_item.get("r2_key") or "").strip(),
                "image_url": str(image_item.get("image_url") or "").strip(),
            }
        )

    for artist, source_url in _collect_exhibition_artist_links(context):
        if not artist or is_invalid_artist_name(artist) or artist in known_artist_labels or not source_url:
            continue
        candidates.append(
            {
                "kind": "artist",
                "label": artist,
                "display_label": artist,
                "link_url": source_url,
                "source_url": source_url,
                "artist_name_kana": "",
                "fair_label": "",
                "gallery": "",
                "headline_ja": "",
                "summary_ja": "",
                "text": "",
                "evidence_rank": 999,
                "gallery_cohort_index": -1,
                "local_path": "",
                "r2_key": "",
                "image_url": "",
            }
        )
    return candidates


def _select_entities_for_answer(answer: str, context: Dict[str, object]) -> List[dict]:
    def _normalize_alias_text(value: object) -> str:
        text = unicodedata.normalize("NFKC", str(value or ""))
        text = re.sub(r"[\s\u3000]+", " ", text).strip()
        return text

    def _candidate_aliases(candidate: dict) -> List[str]:
        aliases: List[str] = []
        seeds = [str(candidate.get("label") or "").strip()]
        if str(candidate.get("kind") or "").strip() == "artist":
            seeds.append(str(candidate.get("artist_name_kana") or "").strip())
        for seed in seeds:
            base = _normalize_alias_text(seed)
            if not base:
                continue
            variants = [
                base,
                base.replace("・", " "),
                base.replace(" ", "・"),
                base.replace("・", "").replace(" ", ""),
            ]
            for alias in variants:
                cleaned = _normalize_alias_text(alias)
                compact = cleaned.replace(" ", "").replace("・", "")
                if len(compact) < 2:
                    continue
                if cleaned not in aliases:
                    aliases.append(cleaned)
        return aliases

    def _find_alias_span(text: str, alias: str) -> tuple[int, int] | None:
        if not text or not alias:
            return None
        direct = text.find(alias)
        if direct >= 0:
            return direct, direct + len(alias)
        tokens = [token for token in re.split(r"[ \u3000・･]+", alias) if token]
        flags = re.IGNORECASE if re.search(r"[A-Za-z]", alias) else 0
        if len(tokens) >= 2:
            pattern = r"[ \u3000・･\-‐‑‒–—]*".join(re.escape(token) for token in tokens)
            match = re.search(pattern, text, flags=flags)
            if match:
                return int(match.start()), int(match.end())
        compact = re.sub(r"[ \u3000・･\-‐‑‒–—]+", "", alias)
        if len(compact) >= 3:
            pattern = r"[ \u3000・･\-‐‑‒–—]*".join(re.escape(ch) for ch in compact)
            match = re.search(pattern, text, flags=flags)
            if match:
                return int(match.start()), int(match.end())
        return None

    plain_answer = _plain_answer_text(answer)
    matches: List[tuple[int, int, int, int, dict, str]] = []
    for candidate in _build_selected_entity_candidates(context):
        label = str(candidate.get("label") or "").strip()
        if not label:
            continue
        best_span: tuple[int, int] | None = None
        best_alias = ""
        for alias in _candidate_aliases(candidate):
            span = _find_alias_span(plain_answer, alias)
            if span is None:
                continue
            if best_span is None or span[0] < best_span[0] or (span[0] == best_span[0] and (span[1] - span[0]) > (best_span[1] - best_span[0])):
                best_span = span
                best_alias = alias
        if best_span is None:
            continue
        kind_order = 0 if str(candidate.get("kind") or "") == "exhibition" else 1
        matches.append((best_span[0], best_span[1], kind_order, -len(label), candidate, best_alias))

    matches.sort(key=lambda value: (value[0], value[2], value[3]))

    selected: List[dict] = []
    occupied_spans: List[tuple[int, int]] = []
    seen = set()
    order = 0
    for start, end, _kind_order, _label_len, candidate, matched_alias in matches:
        dedup_key = (
            str(candidate.get("kind") or ""),
            str(candidate.get("label") or ""),
            str(candidate.get("link_url") or ""),
        )
        if dedup_key in seen:
            continue
        if any(start >= used_start and end <= used_end for used_start, used_end in occupied_spans):
            continue
        seen.add(dedup_key)
        occupied_spans.append((start, end))
        order += 1
        item = dict(candidate)
        item["mention_order"] = order
        item["matched_alias"] = str(matched_alias or "").strip()
        selected.append(item)
    return selected


def _build_exhibition_reference_image_item(row: dict) -> dict | None:
    local_path = str(row.get("image_preview") or "").strip()
    r2_key = str(row.get("image_preview_r2_key") or "").strip()
    if not local_path and not r2_key:
        return None
    return {
        "kind": "exhibition",
        "fair_label": str(row.get("fair_label") or "").strip(),
        "gallery": str(row.get("gallery") or "").strip(),
        "source_url": str(row.get("source_url") or "").strip(),
        "local_path": local_path,
        "r2_key": r2_key,
    }


def _build_artist_reference_image_item(row: dict) -> dict | None:
    candidates = list(row.get("artist_image_preview_candidates") or [])
    if not candidates:
        return None
    first = candidates[0] if isinstance(candidates[0], dict) else {}
    local_path = str(first.get("local_path") or "").strip()
    r2_key = str(first.get("r2_key") or "").strip()
    image_url = str(first.get("image_url") or "").strip()
    if not local_path and not r2_key and not image_url:
        return None
    return {
        "kind": "artist",
        "fair_label": str(row.get("fair_label") or "").strip(),
        "gallery": str(row.get("gallery") or "").strip(),
        "source_url": str(row.get("source_url") or "").strip(),
        "local_path": local_path,
        "r2_key": r2_key,
        "image_url": image_url,
    }


def _build_reference_images(selected_entities: List[dict]) -> Dict[str, object]:
    selected: List[dict] = []
    seen = set()
    for entity in selected_entities:
        item = {
            "kind": str(entity.get("kind") or "").strip(),
            "label": str(entity.get("display_label") or entity.get("label") or "").strip(),
            "fair_label": str(entity.get("fair_label") or "").strip(),
            "gallery": str(entity.get("gallery") or "").strip(),
            "source_url": str(entity.get("source_url") or "").strip(),
            "local_path": str(entity.get("local_path") or "").strip(),
            "r2_key": str(entity.get("r2_key") or "").strip(),
            "image_url": str(entity.get("image_url") or "").strip(),
        }
        dedup_key = (
            str(item.get("kind") or ""),
            str(item.get("label") or ""),
            str(item.get("source_url") or ""),
        )
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        selected.append(item)
        if len(selected) >= ADVISOR_REF_IMAGE_TOTAL:
            break

    exhibition_items = [item for item in selected if str(item.get("kind") or "") == "exhibition"]
    artist_items = [item for item in selected if str(item.get("kind") or "") == "artist"]
    return {
        "exhibition": exhibition_items,
        "artist": artist_items,
        "all": selected,
    }


def _strip_entity_suffixes(answer: str, context: Dict[str, object]) -> str:
    body = str(answer or "")
    for row in list(context.get("artist_evidence", [])):
        artist = str(row.get("artist_name") or "").strip()
        if not artist or is_invalid_artist_name(artist):
            continue
        pattern = re.escape(artist) + r"(?:\s*（[^）]{1,80}）|\s*\([^)]{1,80}\))"
        body = re.sub(pattern, artist, body)
    for row in list(context.get("exhibition_evidence", [])):
        title = str(row.get("title") or "").strip()
        if not title:
            continue
        pattern = re.escape(title) + r"(?:\s*（[^）]{1,80}）|\s*\([^)]{1,80}\))"
        body = re.sub(pattern, title, body)
    body = re.sub(r"\s{2,}", " ", body)
    return body.strip()


def _looks_like_artist_label(text: str) -> bool:
    value = str(text or "").strip()
    if not value:
        return False
    if len(value) > 48:
        return False
    if any(token in value for token in ["http", "Gallery", "gallery", "|", "@"]):
        return False
    parts = [part for part in re.split(r"\s+", value) if part]
    if len(parts) < 2 or len(parts) > 5:
        return False
    banned_parts = {"Art", "Fine", "Works", "Gallery", "Fair", "Missa", "Approach", "Chamber"}
    if any(part in banned_parts for part in parts):
        return False
    return all(bool(re.match(r"^[A-Z][A-Za-z'`.-]*$", part)) for part in parts)


def _collect_exhibition_artist_links(context: Dict[str, object]) -> List[Tuple[str, str]]:
    links: List[Tuple[str, str]] = []
    seen: set[Tuple[str, str]] = set()
    for row in list(context.get("exhibition_evidence", [])):
        source_url = str(row.get("source_url") or "").strip()
        title = str(row.get("title") or "").strip()
        text = str(row.get("text") or "").strip()
        if not source_url:
            continue

        candidates: List[str] = []
        if ":" in title:
            title_head = re.split(r"\s+-\s+", title, maxsplit=1)[0].strip()
            title_head = title_head.split(":", 1)[0].strip()
            if _looks_like_artist_label(title_head) and not is_invalid_artist_name(title_head):
                candidates.append(title_head)

        match = re.search(r"Participating Artists:\s*([^\n]+)", text, flags=re.IGNORECASE)
        if match:
            raw_names = [part.strip() for part in match.group(1).split(",")]
            for raw_name in raw_names:
                if _looks_like_artist_label(raw_name) and not is_invalid_artist_name(raw_name):
                    candidates.append(raw_name)

        for candidate in candidates:
            pair = (candidate, source_url)
            if pair in seen:
                continue
            seen.add(pair)
            links.append(pair)
    return links


def _gallery_labels(context: Dict[str, object]) -> List[str]:
    labels: set[str] = set()
    for key in ("exhibition_evidence", "artist_evidence"):
        for row in list(context.get(key, [])):
            gallery = str(row.get("gallery") or "").strip()
            if gallery:
                labels.add(gallery)
    return sorted(labels, key=len, reverse=True)


def _strip_gallery_labels(answer: str, context: Dict[str, object]) -> str:
    body = str(answer or "")
    if not body:
        return ""

    placeholders: Dict[str, str] = {}
    for idx, row in enumerate(list(context.get("exhibition_evidence", []))):
        title = str(row.get("title") or "").strip()
        if not title:
            continue
        token = f"__EX_TITLE_{idx}__"
        placeholders[token] = title
        body = body.replace(title, token)

    replacement = "会場"
    for gallery in _gallery_labels(context):
        body = body.replace(gallery, replacement)

    for token, title in placeholders.items():
        body = body.replace(token, title)

    body = re.sub(rf"{re.escape(replacement)}(?:\s*/\s*{re.escape(replacement)})+", replacement, body)
    body = re.sub(r"\s{2,}", " ", body)
    return body.strip()


def _flatten_bulletish_answer(text: str) -> str:
    body = str(text or "").strip()
    if not body:
        return ""
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    if len(lines) < 2:
        return body
    bulletish = 0
    normalized: List[str] = []
    for line in lines:
        if re.match(r"^(?:[-*•・]|\d+[.)])\s+", line):
            bulletish += 1
            line = re.sub(r"^(?:[-*•・]|\d+[.)])\s+", "", line).strip()
        normalized.append(line.rstrip("。！？!?") + "。")
    if bulletish < 2:
        return body
    return " ".join(normalized).strip()


def _soften_ambiguous_reference_phrases(text: str) -> str:
    body = str(text or "")
    replacements = {
        "参照した展示群": "展示",
        "参照した作家群": "作家",
        "ある展示群": "展示",
        "ある作家群": "作家",
        "に近い考え方": "を軸にした発想",
        "に近い方向": "を軸にした方向",
    }
    for src, dst in replacements.items():
        body = body.replace(src, dst)
    body = re.sub(r"\s{2,}", " ", body)
    body = re.sub(r"。\s+。", "。", body)
    return body.strip()


def _allowed_current_entity_labels(context: Dict[str, object]) -> List[str]:
    labels: set[str] = set()
    for row in list(context.get("exhibition_evidence", [])):
        title = str(row.get("title") or "").strip()
        gallery = str(row.get("gallery") or "").strip()
        fair = str(row.get("fair_label") or "").strip()
        if title:
            labels.add(title)
            for sep in ["|", "–", "—"]:
                title_head = title.split(sep, 1)[0].strip()
                if title_head:
                    labels.add(title_head)
            labels.add(_exhibition_link_label(title, limit=20))
            labels.add(_exhibition_link_label(title, limit=34))
        if gallery:
            labels.add(gallery)
        if fair:
            labels.add(fair)

    for row in list(context.get("artist_evidence", [])):
        artist = str(row.get("artist_name") or "").strip()
        gallery = str(row.get("gallery") or "").strip()
        fair = str(row.get("fair_label") or "").strip()
        if artist and not is_invalid_artist_name(artist):
            labels.add(artist)
        if gallery:
            labels.add(gallery)
        if fair:
            labels.add(fair)

    for artist, _source_url in _collect_exhibition_artist_links(context):
        if artist and not is_invalid_artist_name(artist):
            labels.add(artist)

    return sorted([label for label in labels if label], key=len, reverse=True)


def _find_unsupported_proper_names(answer: str, context: Dict[str, object]) -> List[str]:
    text = re.sub(r"\[([^\]]+)\]\(https?://[^)]+\)", r"\1", str(answer or ""))
    for label in _allowed_current_entity_labels(context):
        text = text.replace(label, " ")

    candidates = re.findall(r"\b[A-Z][A-Za-z'`.-]+(?:\s+[A-Z][A-Za-z'`.-]+){1,4}\b", text)
    blocked: List[str] = []
    seen = set()
    for candidate in candidates:
        value = candidate.strip()
        if not _looks_like_artist_label(value):
            continue
        if value in seen:
            continue
        seen.add(value)
        blocked.append(value)
    return blocked


def _replace_once_outside_markdown_links(text: str, needle: str, replacement: str) -> str:
    if not text or not needle:
        return text

    cursor = 0
    replaced = False
    chunks: List[str] = []
    for match in ADVISOR_MARKDOWN_LINK_PATTERN.finditer(text):
        segment = text[cursor : match.start()]
        if not replaced and needle in segment:
            segment = segment.replace(needle, replacement, 1)
            replaced = True
        chunks.append(segment)
        chunks.append(match.group(0))
        cursor = match.end()

    tail = text[cursor:]
    if not replaced and needle in tail:
        tail = tail.replace(needle, replacement, 1)
    chunks.append(tail)
    return "".join(chunks)


def _inject_art_pulse_style_inline_links(answer: str, context: Dict[str, object], selected_entities: List[dict]) -> str:
    def _normalize_alias_text(value: object) -> str:
        text = unicodedata.normalize("NFKC", str(value or ""))
        text = re.sub(r"[\s\u3000]+", " ", text).strip()
        return text

    def _entity_aliases(entity: dict) -> List[str]:
        aliases: List[str] = []
        seeds = [
            str(entity.get("matched_alias") or "").strip(),
            str(entity.get("label") or "").strip(),
        ]
        if str(entity.get("kind") or "").strip() == "artist":
            seeds.append(str(entity.get("artist_name_kana") or "").strip())
        for seed in seeds:
            base = _normalize_alias_text(seed)
            if not base:
                continue
            variants = [
                base,
                base.replace("・", " "),
                base.replace(" ", "・"),
                base.replace("・", "").replace(" ", ""),
            ]
            for alias in variants:
                cleaned = _normalize_alias_text(alias)
                compact = cleaned.replace(" ", "").replace("・", "")
                if len(compact) < 2:
                    continue
                if cleaned not in aliases:
                    aliases.append(cleaned)
        return aliases

    def _find_alias_span(text: str, alias: str) -> tuple[int, int] | None:
        if not text or not alias:
            return None
        direct = text.find(alias)
        if direct >= 0:
            return direct, direct + len(alias)
        tokens = [token for token in re.split(r"[ \u3000・･]+", alias) if token]
        flags = re.IGNORECASE if re.search(r"[A-Za-z]", alias) else 0
        if len(tokens) >= 2:
            pattern = r"[ \u3000・･\-‐‑‒–—]*".join(re.escape(token) for token in tokens)
            match = re.search(pattern, text, flags=flags)
            if match:
                return int(match.start()), int(match.end())
        compact = re.sub(r"[ \u3000・･\-‐‑‒–—]+", "", alias)
        if len(compact) >= 3:
            pattern = r"[ \u3000・･\-‐‑‒–—]*".join(re.escape(ch) for ch in compact)
            match = re.search(pattern, text, flags=flags)
            if match:
                return int(match.start()), int(match.end())
        return None

    def _replace_alias_once_outside_markdown_links(text: str, aliases: List[str], link_url: str) -> str:
        if not text or not aliases or not link_url:
            return text
        cursor = 0
        replaced = False
        chunks: List[str] = []
        for match in ADVISOR_MARKDOWN_LINK_PATTERN.finditer(text):
            segment = text[cursor : match.start()]
            if not replaced:
                best: tuple[int, int] | None = None
                for alias in aliases:
                    span = _find_alias_span(segment, alias)
                    if span is None:
                        continue
                    if best is None or span[0] < best[0] or (span[0] == best[0] and (span[1] - span[0]) > (best[1] - best[0])):
                        best = span
                if best is not None:
                    start, end = best
                    matched_text = segment[start:end]
                    inline = f"[{matched_text}]({link_url})"
                    segment = segment[:start] + inline + segment[end:]
                    replaced = True
            chunks.append(segment)
            chunks.append(match.group(0))
            cursor = match.end()
        tail = text[cursor:]
        if not replaced:
            best: tuple[int, int] | None = None
            for alias in aliases:
                span = _find_alias_span(tail, alias)
                if span is None:
                    continue
                if best is None or span[0] < best[0] or (span[0] == best[0] and (span[1] - span[0]) > (best[1] - best[0])):
                    best = span
            if best is not None:
                start, end = best
                matched_text = tail[start:end]
                inline = f"[{matched_text}]({link_url})"
                tail = tail[:start] + inline + tail[end:]
        chunks.append(tail)
        return "".join(chunks)

    body = _strip_entity_suffixes(answer, context)
    for entity in selected_entities:
        label = str(entity.get("label") or "").strip()
        link_url = str(entity.get("link_url") or "").strip()
        if not (label and link_url):
            continue
        if str(entity.get("kind") or "").strip() == "exhibition":
            inline_label = _exhibition_link_label(str(entity.get("display_label") or label), limit=20)
        else:
            inline_label = label.replace("[", "（").replace("]", "）")
        inline = f"[{inline_label}]({link_url})"
        aliases = _entity_aliases(entity)
        body_after_alias = _replace_alias_once_outside_markdown_links(body, aliases, link_url)
        if body_after_alias != body:
            body = body_after_alias
        else:
            body = _replace_once_outside_markdown_links(body, label, inline)

    return body


def _expand_broad_answer_if_short(
    answer: str,
    question_text: str,
    context: Dict[str, object],
) -> str:
    body = (answer or "").strip()
    if not body:
        return ""
    question_focus = _detect_question_focus(question_text)
    needs_synthesis = _needs_grounded_synthesis(question_text, context, question_focus)
    if not _is_broad_query_mode(context) and not needs_synthesis:
        return body

    visible_chars = _visible_answer_chars(body)
    broad_ideation_mode = _is_broad_ideation_query(question_text, context, question_focus)
    single_axis_ideation = broad_ideation_mode and not _allows_multiple_directions(question_text)
    if _is_broad_query_mode(context):
        target_min_chars = 260 if question_focus in {"general", "material", "color", "concept", "spatial"} else 220
    else:
        target_min_chars = 170 if question_focus in {"artist", "concept", "sound", "spatial", "photography"} else 150
    if visible_chars >= target_min_chars:
        return body

    plain_body = _plain_answer_text(body)
    evidence_rows = list(context.get("exhibition_evidence", [])) + list(context.get("artist_evidence", []))
    if single_axis_ideation:
        evidence_rows = evidence_rows[:1]
    expanded = body
    joiner = "\n\n" if "\n" not in body else "\n"
    seen_notes = {plain_body}
    for row in evidence_rows:
        label = str(row.get("artist_name") or row.get("title") or "").strip()
        if str(row.get("kind") or "").strip() == "artist" and is_invalid_artist_name(label):
            continue
        if broad_ideation_mode and int(row.get("_page_description_score", 0) or 0) > 0:
            continue
        addition = _fallback_reason_snippet(row, question_focus=question_focus)
        if not addition:
            continue
        if broad_ideation_mode and _is_page_description_like_text(addition):
            continue
        if addition in plain_body:
            continue
        if addition in seen_notes:
            continue
        if label and label not in plain_body and label in addition and not needs_synthesis:
            continue
        blocked_names = _find_unsupported_proper_names(addition, context)
        for blocked in blocked_names:
            addition = addition.replace(blocked, "参照作家")
        addition = addition.rstrip("。！？!?") + "。"
        expanded = (expanded + joiner + addition).strip()
        break

    return _ensure_natural_ending(_soft_limit_answer_text(expanded, ADVISOR_TEXT_MAX_CHARS))


def _visible_answer_chars(answer: str) -> int:
    body = str(answer or "")
    body = re.sub(r"\[([^\]]+)\]\(https?://[^)]+\)", r"\1", body)
    return len(body.strip())


def _fallback_reason_snippet(
    row: dict,
    question_focus: str = "general",
    max_segments: int = 1,
    prefer_non_caption: bool = False,
) -> str:
    note = str(row.get("summary_ja") or row.get("headline_ja") or row.get("text") or "").strip()
    note = re.sub(r"https?://\S+", "", note)
    note = re.sub(r"\s+", " ", note)
    note = re.sub(r"(?:19|20)\d{2}年?", "", note)
    note = re.sub(r"[–—-]{2,}", " ", note)
    if not note:
        return ""

    sentences = [part.strip(" 、") for part in re.split(r"[。！？!?]\s*", note) if part.strip(" 、")]
    candidates = sentences[:4] if sentences else [note]
    filtered: List[str] = []
    for candidate in candidates:
        candidate = re.sub(r"^[–—\-/:;・\s]+", "", candidate).strip()
        candidate = re.sub(r"^に(?=\d)", "", candidate)
        if not candidate:
            continue
        if sum(candidate.count(token) for token in ["在住", "生まれ", "出身", "受賞", "活動"]) >= 2:
            continue
        if prefer_non_caption and (_is_page_description_like_text(candidate) or int(row.get("_page_description_score", 0) or 0) > 0):
            continue
        filtered.append(candidate)
    if question_focus != "general":
        focused = [candidate for candidate in filtered if _focus_signal_score(candidate, question_focus) > 0]
        if focused:
            filtered = focused
        elif prefer_non_caption:
            return ""

    def _trim_candidate(text: str, limit: int = 140) -> str:
        value = str(text or "").strip()
        if len(value) <= limit:
            return value
        head = value[:limit]
        cut = max(head.rfind("、"), head.rfind(","), head.rfind(" "), head.rfind("）"), head.rfind(")"))
        if cut >= int(limit * 0.6):
            head = head[:cut]
        return head.rstrip("、, ")

    selected: List[str] = []
    segment_limit = max(1, int(max_segments or 1))
    for candidate in filtered:
        text = _trim_candidate(candidate)
        if len(text) >= 16:
            selected.append(text)
        if len(selected) >= segment_limit:
            break
    if selected:
        return "。".join(selected)
    return _trim_candidate(filtered[0]) if filtered else ""


def _fallback_evidence_block(row: dict, question_focus: str = "general", prefer_non_caption: bool = False) -> str:
    label = str(row.get("artist_name") or row.get("title") or "").strip()
    if str(row.get("kind") or "").strip() == "artist" and is_invalid_artist_name(label):
        label = ""
    note = _fallback_reason_snippet(
        row,
        question_focus=question_focus,
        max_segments=2 if question_focus == "concept" else 1,
        prefer_non_caption=prefer_non_caption,
    )
    if prefer_non_caption and not note:
        return ""
    if note and question_focus in {"concept", "material", "color", "general"}:
        return note
    if label and note:
        return f"{label}は{note}" if label not in note else note
    return note or label


def _fallback_answer(question_text: str, context: Dict[str, object]) -> str:
    _, fair_labels = _detect_cross_fair_mode(context)
    question_focus = _detect_question_focus(question_text)
    q = (question_text or "").strip().lower()
    selection = context.get("selection", {}) if isinstance(context, dict) else {}
    history = _get_recent_broad_history(context)
    tokens = [str(token or "").strip().lower() for token in list(selection.get("tokens", [])) if len(str(token or "").strip()) >= 2][:16]
    if not tokens:
        token_candidates = re.split(r"[\s,、。|;:()\[\]{}]+", q)
        token_candidates.extend(re.findall(r"[一-龯]{2,4}|[ァ-ンー]{2,12}|[a-z]{3,12}", q))
        seen_tokens = set()
        tokens = []
        for token in token_candidates:
            low = str(token or "").strip().lower()
            if len(low) < 2 or low in seen_tokens:
                continue
            seen_tokens.add(low)
            tokens.append(low)
            if len(tokens) >= 16:
                break
    candidate_mode = _candidate_row_mode(question_text, question_focus)
    broad_ideation_mode = _is_broad_ideation_query(question_text, context, question_focus)
    ideation_query = bool(selection.get("ideation_query")) or broad_ideation_mode
    single_axis_concept = question_focus == "concept" and not _allows_multiple_directions(question_text)
    single_axis_ideation = broad_ideation_mode and not _allows_multiple_directions(question_text)
    pick_limit = 2
    same_focus_history = [
        item for item in history if str(item.get("intent_focus") or "").strip() == question_focus
    ]
    history_pool = same_focus_history or history
    history_gallery_counts = _history_value_counts(history_pool, "selected_galleries")
    history_title_counts = _history_value_counts(history_pool, "selected_titles")
    history_artist_counts = _history_value_counts(history_pool, "selected_artists")

    def _relevance(row: dict) -> tuple[int, int, int]:
        label = str(row.get("artist_name") or row.get("title") or "").strip()
        if str(row.get("kind") or "").strip() == "artist" and is_invalid_artist_name(label):
            return (-999, 0, 0)
        hay = " ".join(
            [
                label,
                str(row.get("summary_ja") or "").strip(),
                str(row.get("headline_ja") or "").strip(),
                str(row.get("text") or "").strip()[:1200],
            ]
        ).lower()
        token_score = sum(2 if len(token) >= 3 else 1 for token in tokens if token in hay)
        focus_score = _focus_signal_score(hay, question_focus)
        row_kind = "artist" if str(row.get("artist_name") or "").strip() else "exhibition"
        kind_bonus = 1 if candidate_mode == row_kind else 0
        caption_penalty = int(row.get("_page_description_score", 0) or 0) * 4 if ideation_query else 0
        reuse_penalty = 0
        if broad_ideation_mode and history_pool:
            gallery = str(row.get("gallery") or "").strip()
            title = str(row.get("title") or "").strip()
            artist = str(row.get("artist_name") or "").strip()
            reuse_penalty += history_gallery_counts.get(gallery, 0) * 2
            if title:
                reuse_penalty += history_title_counts.get(title, 0) * 3
            if artist:
                reuse_penalty += history_artist_counts.get(artist, 0) * 3
        return token_score + (focus_score * 3) + kind_bonus - caption_penalty - reuse_penalty, focus_score, token_score

    artist_rows = [
        row
        for row in list(context.get("artist_evidence", []))
        if not is_invalid_artist_name(str(row.get("artist_name") or "").strip())
    ]
    exhibition_rows = list(context.get("exhibition_evidence", []))
    if candidate_mode == "artist":
        candidate_rows = artist_rows or exhibition_rows
    elif candidate_mode == "exhibition":
        candidate_rows = exhibition_rows or artist_rows
    else:
        candidate_rows = exhibition_rows + artist_rows
    if not candidate_rows:
        candidate_rows = exhibition_rows or artist_rows

    ranked_rows = sorted(candidate_rows, key=_relevance, reverse=True)
    if broad_ideation_mode and history_pool and len(ranked_rows) >= 2:
        first = ranked_rows[0]
        second = ranked_rows[1]
        first_label = str(first.get("title") or first.get("artist_name") or "").strip()
        second_score = _relevance(second)[0]
        first_score = _relevance(first)[0]
        first_reused = (
            history_title_counts.get(str(first.get("title") or "").strip(), 0) > 0
            or history_artist_counts.get(str(first.get("artist_name") or "").strip(), 0) > 0
        )
        if first_label and first_reused and second_score >= first_score - 1:
            ranked_rows = [second, first] + ranked_rows[2:]
    picked = [row for row in ranked_rows[:pick_limit] if _relevance(row)[0] >= 0]
    if not picked and ranked_rows:
        picked = ranked_rows[:1]
    if len(picked) == 2:
        top_score = _relevance(picked[0])[0]
        second_score = _relevance(picked[1])[0]
        if single_axis_concept:
            if second_score <= 0 or top_score >= second_score + 4:
                picked = picked[:1]
        elif single_axis_ideation:
            if second_score < top_score or _relevance(picked[1])[1] <= 0:
                picked = picked[:1]
        elif second_score <= 0 or top_score >= second_score + 3:
            picked = picked[:1]

    blocks: List[str] = []
    seen = set()
    for row in picked:
        block = _fallback_evidence_block(row, question_focus=question_focus, prefer_non_caption=ideation_query)
        for blocked in _find_unsupported_proper_names(block, context):
            block = block.replace(blocked, "その要素")
        if not block or block in seen:
            continue
        seen.add(block)
        blocks.append(block.rstrip("。！？!?"))
    if not blocks and ideation_query and candidate_mode == "exhibition" and artist_rows:
        alt_rows = sorted(artist_rows, key=_relevance, reverse=True)
        for row in alt_rows[:pick_limit]:
            block = _fallback_evidence_block(row, question_focus=question_focus, prefer_non_caption=True)
            for blocked in _find_unsupported_proper_names(block, context):
                block = block.replace(blocked, "その要素")
            if not block or block in seen:
                continue
            seen.add(block)
            blocks.append(block.rstrip("。！？!?"))
    if not blocks and ideation_query:
        for row in picked:
            block = _fallback_evidence_block(row, question_focus=question_focus, prefer_non_caption=False)
            for blocked in _find_unsupported_proper_names(block, context):
                block = block.replace(blocked, "その要素")
            if not block or block in seen:
                continue
            seen.add(block)
            blocks.append(block.rstrip("。！？!?"))

    answer = ""
    if broad_ideation_mode and blocks:
        block_limit = 1 if single_axis_ideation else 2
        answer = " ".join(f"{block}。" for block in blocks[:block_limit]).strip()
    if not answer and not blocks:
        answer = "今の根拠だけでは、質問に対して強く言い切れる方向までは絞りきれません。"
    elif not answer:
        answer = " ".join(f"{block}。" for block in blocks).strip()

    answer = _strip_fair_labels(answer, fair_labels)
    answer = _ensure_natural_ending(answer)
    return _soft_limit_answer_text(answer, ADVISOR_TEXT_MAX_CHARS)


def _looks_like_snippet_only_answer(
    answer: str,
    question_text: str,
    context: Dict[str, object],
) -> bool:
    question_focus = _detect_question_focus(question_text)
    if not _needs_grounded_synthesis(question_text, context, question_focus):
        return False
    body = _plain_answer_text(answer)
    if not body:
        return True
    compact_body = re.sub(r"[\s\u3000。、，,・:：;；/／「」『』（）()\[\]{}!?！？…―—-]+", "", body.lower())
    sentences = [part.strip() for part in re.split(r"[。！？!?]\s*", body) if part.strip()]
    short_limit = 150 if _is_broad_query_mode(context) or _is_broad_ideation_query(question_text, context, question_focus) else 115
    if _is_page_description_like_text(body):
        return True
    snippet_like = False
    snippet_blocks: List[str] = []
    for row in list(context.get("exhibition_evidence", []))[:2] + list(context.get("artist_evidence", []))[:2]:
        block = _fallback_evidence_block(row, question_focus=question_focus, prefer_non_caption=False)
        compact_block = re.sub(r"[\s\u3000。、，,・:：;；/／「」『』（）()\[\]{}!?！？…―—-]+", "", _plain_answer_text(block).lower())
        if not compact_block:
            continue
        snippet_blocks.append(compact_block)
        if compact_body == compact_block:
            snippet_like = True
            break
        if compact_block in compact_body and len(compact_body) <= len(compact_block) + 28:
            snippet_like = True
            break
        if compact_body in compact_block and len(compact_body) >= 24:
            snippet_like = True
            break
    sentence_hits = 0
    for sentence in sentences[:3]:
        compact_sentence = re.sub(r"[\s\u3000。、，,・:：;；/／「」『』（）()\[\]{}!?！？…―—-]+", "", sentence.lower())
        if not compact_sentence:
            continue
        if any(
            compact_sentence == block
            or (block in compact_sentence and len(compact_sentence) <= len(block) + 24)
            or (compact_sentence in block and len(compact_sentence) >= 24)
            for block in snippet_blocks
        ):
            sentence_hits += 1
    short_answer = _visible_answer_chars(body) < short_limit
    if len(sentences) <= 2 and (short_answer or snippet_like):
        return True
    if sentences and len(sentences) <= 3 and sentence_hits >= len(sentences):
        return True
    if len(sentences) == 1 and question_focus != "general" and _focus_signal_score(body, question_focus) <= 0:
        return True
    return False


def _is_image_evaluation_request(question_text: str, context: Dict[str, object]) -> bool:
    if not _question_targets_uploaded_image(
        question_text,
        bool(_build_visual_observation_digest(context.get("visual_observation", {}))),
    ):
        return False
    return _image_request_kind(question_text) in {
        "strengths",
        "improve",
        "describe",
        "display",
        "critique",
        "reference",
    }


def _image_request_kind(question_text: str) -> str:
    q = (question_text or "").strip().lower()
    if _question_requests_named_references(question_text):
        return "reference"
    display_hints = [
        "展示",
        "空間",
        "照明",
        "見せ方",
        "壁面",
        "余白",
        "鑑賞距離",
        "単独展示",
        "連作展示",
        "staging",
        "display",
        "lighting",
        "spatial",
        "wall",
        "distance",
    ]
    improve_hints = ["改善", "良くする", "調整", "直す", "強くする", "improve", "adjust", "stronger"]
    critique_hints = ["弱い", "批評", "気になる", "足りない", "弱点", "critique", "weakness", "what feels off"]
    strength_hints = ["良い所", "良さ", "強み", "魅力", "what works", "strength"]
    describe_hints = [
        "何が起きている",
        "どう見える",
        "何に見える",
        "見えている",
        "説明して",
        "describe",
        "what is happening",
        "what is seen",
        "explain what is seen",
    ]
    if any(token in q for token in display_hints):
        return "display"
    if any(token in q for token in improve_hints):
        return "improve"
    if any(token in q for token in critique_hints):
        return "critique"
    if any(token in q for token in strength_hints):
        return "strengths"
    if any(token in q for token in describe_hints):
        return "describe"
    return "general"


def _answer_leads_with_reference_entity(answer: str, context: Dict[str, object]) -> bool:
    body = _plain_answer_text(answer)
    if not body:
        return False
    first_sentence = re.split(r"[。！？!?]\s*", body, maxsplit=1)[0].strip()
    if not first_sentence:
        return False
    for row in list(context.get("artist_evidence", []))[:6] + list(context.get("exhibition_evidence", []))[:6]:
        label = str(row.get("artist_name") or row.get("title") or "").strip()
        if not label:
            continue
        if str(row.get("artist_name") or "").strip() and is_invalid_artist_name(label):
            continue
        plain_label = _plain_answer_text(label)
        if plain_label and first_sentence.startswith(plain_label):
            return True
    return False


def _looks_like_image_observation_only_answer(
    answer: str,
    question_text: str,
    context: Dict[str, object],
) -> bool:
    if not _is_image_evaluation_request(question_text, context):
        return False
    body = _plain_answer_text(answer)
    if not body:
        return True
    low = body.lower()
    request_kind = _image_request_kind(question_text)
    if request_kind in {"strengths", "improve", "describe", "display", "critique"} and _answer_leads_with_reference_entity(answer, context):
        return True
    if request_kind == "improve":
        response_hints = [
            "改善",
            "調整",
            "削る",
            "足す",
            "引く",
            "絞る",
            "整える",
            "強める",
            "弱める",
            "ずらす",
            "抑える",
            "広げる",
            "narrow",
            "adjust",
            "reduce",
            "add",
            "shift",
        ]
    elif request_kind == "strengths":
        response_hints = ["良さ", "強み", "魅力", "効いて", "効く", "支えて", "生きている", "strength", "works"]
    elif request_kind == "display":
        response_hints = [
            "展示",
            "空間",
            "照明",
            "距離",
            "余白",
            "壁",
            "導線",
            "単独",
            "連作",
            "lighting",
            "space",
            "wall",
            "distance",
        ]
    elif request_kind == "critique":
        response_hints = ["弱い", "弱点", "気になる", "散る", "詰まる", "足りない", "off", "weakness", "issue"]
    elif request_kind == "describe":
        if any(
            token in low
            for token in [
                "改善",
                "調整",
                "展示するなら",
                "照明",
                "参考作家",
                "誰を見る",
                "するといい",
                "should",
                "could",
                "lighting",
                "reference",
            ]
        ):
            return True
        return False
    elif request_kind == "reference":
        response_hints = ["作家", "展示", "参考", "artist", "reference", "look at"]
    else:
        response_hints = [
            "良い",
            "強み",
            "魅力",
            "改善",
            "調整",
            "should",
            "could",
            "better",
        ]
    if any(token in low for token in response_hints):
        return False
    if any(token in low for token in ["今の根拠では", "絞りきれません", "情報不足", "判断できません", "強く推せません"]):
        return True
    observation_hints = [
        "背景",
        "色",
        "配色",
        "構図",
        "形",
        "重なり",
        "奥行き",
        "表面",
        "抽象",
        "円",
        "長方形",
        "ストライプ",
        "palette",
        "composition",
        "surface",
        "depth",
    ]
    return sum(1 for token in observation_hints if token in low) >= 3


def _compact_compare_text(text: str) -> str:
    return re.sub(r"[\s\u3000。、，,・:：;；/／「」『』（）()\[\]{}!?！？…―—-]+", "", _plain_answer_text(text).lower())


def _merge_answer_with_supplement(answer: str, supplement: str) -> str:
    base = str(answer or "").strip()
    extra = str(supplement or "").strip()
    if not base:
        return extra
    if not extra:
        return base
    compact_base = _compact_compare_text(base)
    compact_extra = _compact_compare_text(extra)
    if not compact_extra or compact_extra == compact_base:
        return base
    if compact_extra in compact_base:
        return base
    if compact_base and compact_base in compact_extra and len(compact_extra) > len(compact_base) + 24:
        return extra

    seen = {compact_base}
    additions: List[str] = []
    for sentence in [part.strip() for part in re.split(r"[。！？!?]\s*", extra) if part.strip()]:
        compact_sentence = _compact_compare_text(sentence)
        if not compact_sentence or compact_sentence in seen:
            continue
        if any(
            compact_sentence in existing or existing in compact_sentence
            for existing in seen
            if len(compact_sentence) >= 18 and len(existing) >= 18
        ):
            continue
        additions.append(sentence.rstrip("。！？!?") + "。")
        seen.add(compact_sentence)
        if len(additions) >= 2:
            break
    if not additions:
        return base
    joiner = "\n\n" if "\n" not in base else "\n"
    return (base.rstrip() + joiner + " ".join(additions)).strip()


def _salvage_openai_snippet_only_answer(
    answer: str,
    question_text: str,
    context: Dict[str, object],
    fair_labels: List[str],
) -> str:
    body = _clean_answer_text_for_display(answer, question_text, context, fair_labels)
    if not _looks_like_snippet_only_answer(body, question_text, context):
        return body
    fallback_candidate = _clean_answer_text_for_display(_fallback_answer(question_text, context), question_text, context, fair_labels)
    merged = _merge_answer_with_supplement(body, fallback_candidate)
    merged = _clean_answer_text_for_display(merged, question_text, context, fair_labels)
    merged = _expand_broad_answer_if_short(merged, question_text, context)
    merged = _trim_trailing_fragment(merged, _detect_question_focus(question_text))
    return _ensure_natural_ending(merged)


def _looks_like_broad_quality_failure(
    answer: str,
    question_text: str,
    context: Dict[str, object],
) -> bool:
    question_focus = _detect_question_focus(question_text)
    broad_query_mode = _is_broad_query_mode(context) or _is_broad_ideation_query(question_text, context, question_focus)
    if not broad_query_mode:
        return False
    body = _plain_answer_text(answer)
    if not body:
        return True
    if _looks_like_snippet_only_answer(body, question_text, context):
        return True
    compact_body = _compact_compare_text(body)
    if re.search(r"(その要素|その例)\s*[-‐‑–—]+\s*(その要素|その例)", body):
        return True
    if "その要素その要素" in compact_body or "その例その例" in compact_body:
        return True

    sentences = [part.strip() for part in re.split(r"[。！？!?]\s*", body) if part.strip()]
    if not sentences:
        return True
    connector_hits = sum(
        body.count(token)
        for token in [
            "ので",
            "から",
            "ため",
            "一方",
            "ただ",
            "なら",
            "そこで",
            "制作では",
            "展示では",
            "たとえば",
        ]
    )
    reference_mentions = 0
    seen_labels = set()
    for row in list(context.get("artist_evidence", []))[:6] + list(context.get("exhibition_evidence", []))[:6]:
        label = _plain_answer_text(str(row.get("artist_name") or row.get("title") or "").strip())
        if not label or label in seen_labels:
            continue
        seen_labels.add(label)
        if label in body:
            reference_mentions += 1

    if len(sentences) <= 2 and reference_mentions >= 3 and connector_hits <= 0:
        return True
    if _answer_leads_with_reference_entity(body, context) and len(sentences) <= 2 and connector_hits <= 0:
        return True
    if len(sentences) <= 2 and _visible_answer_chars(body) < 150:
        if question_focus == "general" and reference_mentions >= 2:
            return True
        if question_focus != "general" and _focus_signal_score(body, question_focus) <= 0:
            return True
    return False


def _retry_openai_broad_quality_answer(
    client: object,
    model: str,
    answer: str,
    question_text: str,
    context: Dict[str, object],
    fair_labels: List[str],
) -> str:
    if not _looks_like_broad_quality_failure(answer, question_text, context):
        return _clean_answer_text_for_display(answer, question_text, context, fair_labels)
    question_focus = _detect_question_focus(question_text)
    focus_instruction = "Answer the question directly and keep the prose coherent."
    if question_focus == "concept":
        focus_instruction = "Answer with a coherent concept proposal or idea direction, not a list of names or fragments."
    elif question_focus == "material":
        focus_instruction = "Answer by explaining what kind of material direction fits and why, not by only naming examples."
    elif question_focus == "color":
        focus_instruction = "Answer by explaining a usable color direction and why it works, not by only naming references."
    prompt = (
        "Rewrite the draft so it becomes a natural Japanese answer to the user's question. "
        + focus_instruction
        + " "
        "Keep the same grounded evidence and do not swap references. "
        "Avoid broken fragments, repeated placeholders, and bare name-listing. "
        "Do not use headings or bullet points. "
        "Return JSON only as {\"answer\":\"...\"}.\n\n"
        f"Question:\n{question_text}\n\n"
        f"Current draft:\n{answer}\n\n"
        f"Grounded evidence digest:\n{_build_evidence_digest(context, per_kind=3) or '- none'}"
    )
    response = client.responses.create(model=model, input=prompt)
    body = _ensure_plain_answer_text(str(getattr(response, "output_text", "") or ""))
    body = _clean_answer_text_for_display(body, question_text, context, fair_labels)
    body = _expand_broad_answer_if_short(body, question_text, context)
    body = _trim_trailing_fragment(body, question_focus)
    return _ensure_natural_ending(body)


def _salvage_openai_image_subject_answer(
    client: object,
    model: str,
    answer: str,
    question_text: str,
    context: Dict[str, object],
    fair_labels: List[str],
) -> str:
    if not _looks_like_image_observation_only_answer(answer, question_text, context):
        return _clean_answer_text_for_display(answer, question_text, context, fair_labels)
    observation_digest = _build_visual_observation_digest(context.get("visual_observation", {}))
    request_kind = _image_request_kind(question_text)
    mode_instruction = "Answer the user's actual ask directly."
    if request_kind == "describe":
        mode_instruction = "Keep the answer focused on what is visible or what seems to be happening in the image. Do not add unsolicited improvement, display advice, or references."
    elif request_kind == "display":
        mode_instruction = "Answer as staging/display guidance tied to the visible traits in the image: space, lighting, distance, wall relation, sequencing, or room scale."
    elif request_kind == "improve":
        mode_instruction = "Answer as concrete changes or adjustments for the current work, tied to visible traits."
    elif request_kind == "strengths":
        mode_instruction = "Answer as strengths or praise of the current work, tied to visible traits."
    elif request_kind == "critique":
        mode_instruction = "Answer as weaknesses or critique of the current work, tied to visible traits."
    elif request_kind == "reference":
        mode_instruction = "Answer with minimal grounded references that fit the visible traits; keep names useful but not bloated."
    prompt = (
        "Rewrite the draft so it answers the user's question directly about the attached/current work. "
        "Keep the visible observation at the center. "
        + mode_instruction
        + " "
        "Do not invent artist/style attribution or unsupported facts. Keep proper names secondary unless explicitly asked. "
        "Return JSON only as {\"answer\":\"...\"}.\n\n"
        f"Question:\n{question_text}\n\n"
        f"Current draft:\n{answer}\n\n"
        f"Attached image observation:\n{observation_digest or '- none'}\n\n"
        f"Grounded evidence digest:\n{_build_evidence_digest(context, per_kind=2) or '- none'}"
    )
    response = client.responses.create(model=model, input=prompt)
    body = _ensure_plain_answer_text(str(getattr(response, "output_text", "") or ""))
    body = _clean_answer_text_for_display(body, question_text, context, fair_labels)
    return _ensure_natural_ending(body)


def _build_prompt(question_text: str, context: Dict[str, object]) -> str:
    cross_fair_mode, fair_labels = _detect_cross_fair_mode(context)
    broad_query_mode = _is_broad_query_mode(context)
    question_focus = _detect_question_focus(question_text)
    broad_ideation_mode = _is_broad_ideation_query(question_text, context, question_focus)
    selection = context.get("selection", {}) if isinstance(context, dict) else {}
    grounded_anchor_count = max(0, int(selection.get("grounded_anchor_count") or 0))
    needs_grounded_synthesis = _needs_grounded_synthesis(question_text, context, question_focus)
    visual_observation_digest = _build_visual_observation_digest(context.get("visual_observation", {}))
    image_subject_mode = _question_targets_uploaded_image(question_text, bool(visual_observation_digest))
    asks_named_references = _question_requests_named_references(question_text)
    image_request_kind = _image_request_kind(question_text)
    answer_reference_entities = list(context.get("answer_reference_entities", []) or [])
    ex_lines = []
    for row in list(context.get("exhibition_evidence", []))[:10]:
        ex_lines.append(
            f"- [{row.get('fair_label')}] {row.get('gallery')} | {row.get('title')} | {row.get('source_url')}"
        )
    ar_lines = []
    for row in list(context.get("artist_evidence", []))[:10]:
        artist_name = str(row.get("artist_name") or "").strip()
        if is_invalid_artist_name(artist_name):
            continue
        ar_lines.append(
            f"- [{row.get('fair_label')}] {row.get('gallery')} | {artist_name} | {row.get('source_url')}"
        )
    evidence_digest = _build_evidence_digest(context, per_kind=3)
    cross_fair_digest = _build_cross_fair_digest(context, fair_labels) if cross_fair_mode else ""
    allowed_reference_labels: List[str] = []
    for entity in answer_reference_entities:
        label = str(entity.get("display_label") or entity.get("label") or "").strip()
        if not label or label in allowed_reference_labels:
            continue
        allowed_reference_labels.append(label)
        if len(allowed_reference_labels) >= 8:
            break
    include_action_steps = _should_include_action_steps(question_text)
    visual_prompt_rule = ""
    visual_observation_section = ""
    if visual_observation_digest:
        visual_prompt_rule = (
            "- If attached-image observation is available, treat it as visible evidence only and never as artist/style attribution.\n"
        )
        if image_subject_mode:
            visual_prompt_rule += (
                "- For this question, respond from the visible traits in the attached/current work first, then answer the user's ask, and use grounded references only as support.\n"
            )
            if image_request_kind == "describe":
                visual_prompt_rule += "- Keep the answer in describe/explain mode only. Do not add unsolicited improvement, display advice, or references.\n"
            elif image_request_kind == "display":
                visual_prompt_rule += "- Answer as staging/display guidance tied to the visible traits: space, lighting, wall distance, scale, sequencing, or viewing distance. Do not fall back to source snippets or page fragments.\n"
            elif image_request_kind == "improve":
                visual_prompt_rule += "- Answer as concrete change ideas tied to visible traits. Do not stop at neutral description.\n"
            elif image_request_kind == "strengths":
                visual_prompt_rule += "- Answer as strengths or praise tied to visible traits, not as neutral description or improvement advice.\n"
            elif image_request_kind == "critique":
                visual_prompt_rule += "- Answer as weaknesses or critique tied to visible traits, not as praise or display advice.\n"
            elif image_request_kind == "reference":
                visual_prompt_rule += "- Because the user asked for references, minimal grounded names are allowed after the observation-based setup.\n"
            else:
                visual_prompt_rule += "- Match the user's ask directly and do not stop at neutral description.\n"
        else:
            visual_prompt_rule += "- Use the attached-image observation only when it helps answer the user's question.\n"
        if not asks_named_references:
            visual_prompt_rule += "- Unless the user explicitly asked for similar artists or references, do not let proper names lead the answer.\n"
        visual_observation_section = (
            "Attached image observation (visible traits only):\n"
            f"{visual_observation_digest}\n\n"
        )

    cross_fair_rule = ""
    if cross_fair_mode:
        cross_fair_rule = (
            "- フェア横断時でも、比較の枠組みを先に決め打ちせず、質問に効く根拠だけを使うこと。\n"
            "- 本文では、どうしても必要な場合を除いてフェア名を出さないこと。\n"
        )

    broad_query_rule = ""
    if broad_query_mode:
        broad_query_rule = (
            "- broad query では話題を増やしすぎず、最初に選んだ方向の理由を少し深くすること。\n"
            "- 比較の型や複数軸を先に作らず、質問への返答として自然な流れを優先すること。\n"
        )
    prose_rule = ""
    if broad_ideation_mode and not _should_preserve_list_style(question_text):
        prose_rule = (
            "- broad ideation では説明より提案を優先し、冒頭から提案文で入ること。\n"
            "- 箇条書きやカード列挙ではなく、1〜2段落の自然文を優先すること。\n"
        )
    synthesis_rule = ""
    if needs_grounded_synthesis:
        synthesis_rule = (
            "- 関連する根拠がある質問では、展示説明・作家説明・作品断片の要約だけで終わらせず、質問への提案として統合すること。\n"
            "- 関連する根拠がある ideation / recommendation / design 質問では、通常は少なくとも3文以上で、短い説明断片だけで終わらせないこと。\n"
            "- 関連する根拠がある ideation / recommendation / design 質問では、通常は 220〜520字程度を目安にして、痩せた断片回答にしないこと。\n"
            "- 少なくとも一段、なぜその方向が合うか、どう展開できるか、何を軸に絞るか、どう制作や展示へ落とすかのいずれかを含めること。\n"
            "- 1件の根拠を挙げる場合も、その根拠から何を借りるかまで書くこと。\n"
            "- 最終回答が単一の retrieved row の言い換えに近いと感じたら、そのまま出さず質問への提案になるまで統合すること。\n"
        )
    if grounded_anchor_count > 0:
        grounding_rule = (
            "- 関連する根拠が1件以上ある場合は、その根拠を主軸に保ちながら、一般的な美術知識・比較・制作や展示の原理を補助的に使って、回答を提案として統合すること。\n"
            "- 新しい固有名や具体事実を足すときは作り話や矛盾を避け、危うい事実は断定しないこと。\n"
        )
    elif visual_observation_digest:
        grounding_rule = (
            "- grounded reference が弱くても、添付画像から見える特徴に基づく回答は普通にしてよい。ただし画像だけでは断定できない作家名・様式名・背景事情は言い切らないこと。\n"
        )
    else:
        grounding_rule = "- 関連する根拠が弱い場合は、無理に補完せず情報不足を率直に示してよい。\n"

    gallery_rule = (
        "- ギャラリー名は、ユーザーがギャラリーについて明示的に尋ねたときだけ本文に出してよい。\n"
        if _should_allow_gallery_mentions(question_text)
        else "- ギャラリー名は、ユーザーがギャラリーについて明示的に尋ねていない限り本文に出さないこと。\n"
    )

    action_rule = (
        "- 実践的な手順は、ユーザーが方法や手順を明示的に求めたときだけ回答する。\n"
        if include_action_steps
        else "- ユーザーから求められていない限り、手順や次アクションを足さないこと。\n"
    )
    focus_rule = ""
    if question_focus in {"video", "sound", "sculpture", "photography", "painting", "spatial", "performance"}:
        focus_rule = (
            "- 質問で中心にある媒体や実践に沿って答え、別の媒体へ広げすぎないこと。\n"
            "- 強い候補が1件しかない場合は1件だけ提示してよい。\n"
        )
    elif question_focus == "concept":
        focus_rule = (
            "- 質問がコンセプト寄りなら、主文は発想やテーマに合わせ、素材の話だけで終えないこと。\n"
            + (
                "- 複数案を明示的に求められていない限り、主軸を一つに絞って深めること。\n"
                if not _allows_multiple_directions(question_text)
                else "- 方向を増やしすぎず、必要でも二案目までにとどめること。\n"
            )
        )
    elif question_focus == "material":
        focus_rule = "- 質問が素材寄りなら、主文は素材感や手触りの話に合わせ、抽象論へ逃がしすぎないこと。\n"
    elif question_focus == "color":
        focus_rule = "- 質問が色寄りなら、主文は色調や明暗の話に合わせ、別の軸を主役にしないこと。\n"

    if visual_observation_digest and grounded_anchor_count > 0:
        answer_basis = (
            "添付画像の観察を起点にしつつ、与えられた根拠を主軸の補強として保ちながら、日本語で回答してください。"
        )
    elif visual_observation_digest:
        answer_basis = "添付画像の観察を一次根拠として、日本語で回答してください。"
    elif grounded_anchor_count > 0:
        answer_basis = (
            "与えられた根拠を主軸にしつつ、必要なら一般的な美術知識や制作・展示の原理で補助しながら、日本語で回答してください。"
        )
    else:
        answer_basis = "与えられた根拠だけを使って、日本語で回答してください。"

    return f"""
{answer_basis}
制約:
- 質問に自然に必要な範囲で Artist名 or Exhibition名 を使うこと。無理に固有名を増やさないこと。
- 具体的な Artist名 / Exhibition名 をおすすめ対象として出す場合は、Allowed references にある名称のみを使うこと。
- 強く推せる根拠がない場合は、無理に人数合わせせず「今の根拠では強く推せない」と明示してよい。
- broad query でも短すぎる一言で終わらせず、必要な範囲で少し具体化すること。無理に話題を増やして埋めないこと。
- {PLAIN_JAPANESE_RULE}
- 無駄な相槌や前置きを入れず、簡潔で口語的な文体にすること。
- 固定見出し・固定比較・A/B/橋渡しのような骨組みを作らないこと。
- 「今回の根拠では」「参照したのは」などのメタ説明は書かないこと。
- 根拠がある質問では、1件の展示説明・作家説明・作品断片の言い換えだけを最終回答にしないこと。
{action_rule}{gallery_rule}{cross_fair_rule}{broad_query_rule}{prose_rule}{synthesis_rule}{visual_prompt_rule}{grounding_rule}{focus_rule}- 出力は JSON のみ: {{"answer":"..."}}

質問:
{question_text}

Allowed references（この回答で使える固有名）:
{chr(10).join(f"- {label}" for label in allowed_reference_labels) if allowed_reference_labels else "- なし"}

{visual_observation_section}根拠要約（優先参照）:
{evidence_digest if evidence_digest else "- なし"}

フェア横断要約:
{cross_fair_digest if cross_fair_digest else "- 単独フェア"}

展示根拠:
{chr(10).join(ex_lines) if ex_lines else "- なし"}

作家根拠:
{chr(10).join(ar_lines) if ar_lines else "- なし"}
""".strip()


def _clean_answer_text_for_display(
    answer: str,
    question_text: str,
    context: Dict[str, object],
    fair_labels: List[str],
) -> str:
    question_focus = _detect_question_focus(question_text)
    body = _ensure_plain_answer_text(answer)
    body = _normalize_answer_text(body)
    body = _strip_fixed_headings(body)
    body = _strip_rigid_template_markers(body)
    body = _strip_fair_labels(body, fair_labels)
    if not _should_allow_gallery_mentions(question_text):
        body = _strip_gallery_labels(body, context)
    body = _soften_ambiguous_reference_phrases(body)
    if _is_broad_ideation_query(question_text, context, question_focus) and not _should_preserve_list_style(question_text):
        body = _flatten_bulletish_answer(body)
    body = _trim_trailing_fragment(body, question_focus)
    return _ensure_natural_ending(body)


def generate_advisor_grounded_draft(
    question_text: str,
    context: Dict[str, object],
    question_type: str = "type1_text_only",
    has_uploaded_image: bool = False,
    uploaded_image_name: str = "",
    uploaded_image_payload: object = None,
) -> Dict[str, object]:
    working_context = dict(context or {})
    working_selection = dict(working_context.get("selection", {}) or {})
    working_context["selection"] = working_selection
    context = working_context
    _, fair_labels = _detect_cross_fair_mode(context)
    answer_reference_entities = _select_reference_entities_for_output(context, [])
    context["answer_reference_entities"] = [dict(entity) for entity in answer_reference_entities]
    working_selection["answer_reference_entities_count"] = len(answer_reference_entities)
    evidence_urls = context.get("evidence_urls", {}) if isinstance(context, dict) else {}
    ex_urls = _dedup_urls(list(evidence_urls.get("exhibition", [])))
    ar_urls = _dedup_urls(list(evidence_urls.get("artist", [])))
    all_urls = _dedup_urls(ex_urls + ar_urls)

    if question_type != "type1_text_only":
        return {
            "question_type": question_type,
            "answer": "type 2 は type 1 の grounded 回答を基盤に別処理で画像補助を生成します。ここでは type 1 本文のみ作成します。",
            "answer_chars": 70,
            "mode": "disabled",
            "model": "",
            "evidence_urls": {"exhibition": ex_urls, "artist": ar_urls, "all": all_urls},
            "evidence_counts": {
                "exhibition_urls": len(ex_urls),
                "artist_urls": len(ar_urls),
                "all_unique_urls": len(all_urls),
            },
            "reference_images": context.get("reference_images", {}),
            "warnings": [],
            "attachment_note": (
                f"添付画像（{uploaded_image_name}）は受け取りましたが、保存・ベクトル化・RAG混入は行っていません。"
                if has_uploaded_image
                else "添付画像なし。"
            ),
        }

    model = os.getenv("TEXT_MODEL", "gpt-5-mini")
    api_key = os.getenv("OPENAI_API_KEY", "")
    mode = "fallback"
    answer = ""
    warnings: List[str] = []
    client = None
    visual_observation_used = False

    if api_key.strip():
        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            if has_uploaded_image and uploaded_image_payload:
                try:
                    visual_observation = _observe_uploaded_image(
                        client=client,
                        model=os.getenv("VISION_MODEL", model),
                        question_text=question_text,
                        uploaded_image_payload=uploaded_image_payload,
                    )
                    if visual_observation:
                        context["visual_observation"] = visual_observation
                        working_selection["visual_observation_available"] = True
                        visual_observation_used = True
                    else:
                        warnings.append("visual_observation_unavailable")
                except Exception as exc:
                    warnings.append(f"visual_observation_failed:{type(exc).__name__}")
            prompt = _build_prompt(question_text, context)
            res = client.responses.create(model=model, input=prompt)
            answer = _ensure_plain_answer_text(str(res.output_text or ""))
            mode = "openai"
        except Exception as exc:
            warnings.append(f"{type(exc).__name__}: {exc}")

    if not answer:
        answer = _fallback_answer(question_text, context)

    answer = _clean_answer_text_for_display(answer, question_text, context, fair_labels)
    if not answer:
        warnings.append("empty_after_plain_unwrap: fallback_used")
        answer = _clean_answer_text_for_display(_fallback_answer(question_text, context), question_text, context, fair_labels)
    if _looks_like_biography_dump(answer):
        warnings.append("biography_dump_like_output_detected: fallback_used")
        answer = _clean_answer_text_for_display(_fallback_answer(question_text, context), question_text, context, fair_labels)
    if _looks_like_intent_mismatch(answer, question_text):
        warnings.append("intent_mismatch_detected: fallback_used")
        answer = _clean_answer_text_for_display(_fallback_answer(question_text, context), question_text, context, fair_labels)
    if mode == "openai" and client is not None and _looks_like_image_observation_only_answer(answer, question_text, context):
        warnings.append("image_observation_only_output_detected")
        try:
            rescued_answer = _salvage_openai_image_subject_answer(
                client=client,
                model=model,
                answer=answer,
                question_text=question_text,
                context=context,
                fair_labels=fair_labels,
            )
            if rescued_answer and not _looks_like_image_observation_only_answer(rescued_answer, question_text, context):
                warnings.append("image_observation_only_output_detected: openai_salvaged")
                answer = rescued_answer
        except Exception as exc:
            warnings.append(f"image_observation_salvage_failed:{type(exc).__name__}")

    unsupported_names = _find_unsupported_proper_names(answer, context)
    if unsupported_names:
        warnings.append(
            "unsupported_current_names_detected: " + ", ".join(unsupported_names[:5])
        )
        if mode == "openai" and _needs_grounded_synthesis(question_text, context):
            for blocked in unsupported_names[:8]:
                answer = _replace_once_outside_markdown_links(answer, blocked, "その例")
            answer = _clean_answer_text_for_display(answer, question_text, context, fair_labels)
            if _find_unsupported_proper_names(answer, context):
                answer = _clean_answer_text_for_display(_fallback_answer(question_text, context), question_text, context, fair_labels)
        else:
            answer = _clean_answer_text_for_display(_fallback_answer(question_text, context), question_text, context, fair_labels)
    answer = _expand_broad_answer_if_short(answer, question_text, context)
    if mode == "openai" and _looks_like_snippet_only_answer(answer, question_text, context):
        warnings.append("snippet_only_like_output_detected")
        rescued_answer = _salvage_openai_snippet_only_answer(answer, question_text, context, fair_labels)
        if rescued_answer and not _looks_like_snippet_only_answer(rescued_answer, question_text, context):
            warnings.append("snippet_only_like_output_detected: openai_salvaged")
            answer = rescued_answer
        else:
            fallback_candidate = _clean_answer_text_for_display(_fallback_answer(question_text, context), question_text, context, fair_labels)
            fallback_candidate = _expand_broad_answer_if_short(fallback_candidate, question_text, context)
            if fallback_candidate and not _looks_like_snippet_only_answer(fallback_candidate, question_text, context):
                warnings.append("snippet_only_like_output_detected: fallback_used")
                answer = fallback_candidate
    if mode == "openai" and client is not None and _looks_like_broad_quality_failure(answer, question_text, context):
        warnings.append("broad_quality_failure_detected")
        try:
            rescued_answer = _retry_openai_broad_quality_answer(
                client=client,
                model=model,
                answer=answer,
                question_text=question_text,
                context=context,
                fair_labels=fair_labels,
            )
            if rescued_answer and not _looks_like_broad_quality_failure(rescued_answer, question_text, context):
                warnings.append("broad_quality_failure_detected: openai_retried")
                answer = rescued_answer
        except Exception as exc:
            warnings.append(f"broad_quality_retry_failed:{type(exc).__name__}")
    answer = _trim_trailing_fragment(answer, _detect_question_focus(question_text))
    answer = _soft_limit_answer_text(answer, ADVISOR_TEXT_MAX_CHARS)
    answer = _ensure_natural_ending(answer)
    selected_entities = _select_entities_for_answer(answer, context)
    reference_entities = _select_reference_entities_for_output(context, selected_entities)
    reference_images = _build_reference_images(reference_entities)
    answer = _inject_art_pulse_style_inline_links(answer, context, selected_entities)
    answer = _ensure_plain_answer_text(answer)
    answer = _strip_fair_labels(answer, fair_labels)
    answer = _soft_limit_answer_text(answer, ADVISOR_TEXT_MAX_CHARS)
    answer = _ensure_natural_ending(answer)
    if not answer:
        warnings.append("answer_empty_final: fallback_used")
        answer = _clean_answer_text_for_display(_fallback_answer(question_text, context), question_text, context, fair_labels)
    answer_chars = _visible_answer_chars(answer)
    reference_examples = _build_art_pulse_style_reference_lines(reference_entities)
    broad_diversity_meta = {}
    if _is_broad_query_mode(context):
        plan = _build_broad_diversity_plan(question_text, context)
        broad_diversity_meta = {
            "query_kind": plan.get("query_kind"),
            "intent_focus": str((context.get("selection", {}) or {}).get("intent_focus") or ""),
            "proposal_family": str(plan.get("bridge_family", {}).get("id") or ""),
            "anchor_fairs": [str(plan.get("fair_a") or ""), str(plan.get("fair_b") or "")],
            "anchor_galleries": [
                str(plan.get("fair_a_anchor", {}).get("gallery") or ""),
                str(plan.get("fair_b_anchor", {}).get("gallery") or ""),
                str(plan.get("bridge_anchor", {}).get("gallery") or ""),
            ],
            "anchor_artists": [
                str(plan.get("fair_a_anchor", {}).get("artist_name") or ""),
                str(plan.get("fair_b_anchor", {}).get("artist_name") or ""),
                str(plan.get("bridge_anchor", {}).get("artist_name") or ""),
            ],
            "selected_galleries": [
                str(row.get("gallery") or "")
                for row in (list(context.get("exhibition_evidence", [])) + list(context.get("artist_evidence", [])))[:4]
                if str(row.get("gallery") or "").strip()
            ],
            "selected_titles": [
                str(row.get("title") or "")
                for row in list(context.get("exhibition_evidence", []))[:4]
                if str(row.get("title") or "").strip()
            ],
            "selected_artists": [
                str(row.get("artist_name") or "")
                for row in list(context.get("artist_evidence", []))[:4]
                if str(row.get("artist_name") or "").strip()
            ],
            "rotation_index": plan.get("rotation_index"),
        }
    attachment_note = (
        (
            f"添付画像（{uploaded_image_name or 'unnamed'}）は保存・ベクトル化せず、session内の visual observation としてのみ使いました。"
            if visual_observation_used
            else f"添付画像（{uploaded_image_name or 'unnamed'}）は保存・ベクトル化せず、今回のtype 1では補助参照扱いです。"
        )
        if has_uploaded_image
        else "添付画像なし。"
    )

    return {
        "question_type": "type1_text_only",
        "answer": answer,
        "answer_chars": answer_chars,
        "mode": mode,
        "model": model,
        "evidence_urls": {
            "exhibition": ex_urls,
            "artist": ar_urls,
            "all": all_urls,
        },
        "evidence_counts": {
            "exhibition_urls": len(ex_urls),
            "artist_urls": len(ar_urls),
            "all_unique_urls": len(all_urls),
        },
        "reference_images": reference_images,
        "warnings": warnings,
        "attachment_note": attachment_note,
        "reference_examples": reference_examples,
        "answer_reference_entities": [dict(entity) for entity in reference_entities],
        "broad_diversity_meta": broad_diversity_meta,
        "visual_observation_used": visual_observation_used,
    }

