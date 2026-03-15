from __future__ import annotations

import json
import os
import re
from typing import Dict, List, Tuple

from phase2_art_pulse_draft import _google_image_search_url
from phase2_response_style import PLAIN_JAPANESE_RULE

ADVISOR_TEXT_MAX_CHARS = 550
ADVISOR_REF_IMAGE_TOTAL = 8
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


def _build_evidence_digest(context: Dict[str, object], per_kind: int = 3) -> str:
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
        artist = str(row.get("artist_name") or "").strip() or "作家名不明"
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
        ar_items = [str(r.get("artist_name") or "").strip() for r in ar_rows if str(r.get("fair_label") or "").strip() == fair]
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


def _anchor_label(row: dict) -> str:
    if not row:
        return "根拠候補"
    artist = str(row.get("artist_name") or "").strip()
    title = str(row.get("title") or "").strip()
    gallery = str(row.get("gallery") or "").strip()
    return artist or title or gallery or "根拠候補"


def _material_axis_suggestions(question_text: str, rotation_index: int) -> List[str]:
    q = (question_text or "").strip()
    is_color_query = any(token in q for token in ["色", "カラー", "色彩", "配色"])
    if is_color_query:
        palette = [
            ["低彩度グレー + 深い緑", "青灰 + 乳白", "焦げ茶 + 鈍い金属色"],
            ["温白 + 鉄紺", "土色 + 黒", "薄い桃灰 + 炭色"],
            ["青緑 + 生成り", "赤茶 + 鉛色", "黄土 + 墨色"],
        ]
    else:
        palette = [
            ["布/和紙", "木質パネル", "顔料のにじみ層"],
            ["金属メッシュ", "透明樹脂", "半透明フィルム層"],
            ["土系マチエール", "石粉塗料", "粗密の異なる繊維材"],
        ]
    return palette[rotation_index % len(palette)]


def _cross_fair_material_action(question_text: str, fair_a: str, fair_b: str, rotation_index: int) -> str:
    suggestions = _material_axis_suggestions(question_text, rotation_index)
    common_axes = [
        "主題を先に固定してから素材を決める",
        "視線導線を先に設計して素材を重ねる",
        "密度のピーク位置を先に決めてから仕上げる",
    ]
    diff_axes = [
        f"{fair_a}寄りは密度高め・近接視での情報量を強める",
        f"{fair_a}寄りは硬質な層を増やし、{fair_b}寄りは余白を広く取る",
        f"{fair_a}寄りはコントラストを上げ、{fair_b}寄りは中間調で連結する",
    ]
    common = common_axes[rotation_index % len(common_axes)]
    diff = diff_axes[rotation_index % len(diff_axes)]
    suggestion_text = " / ".join(suggestions[:3])
    return (
        f"共通点: {common}。\n"
        f"差分: {diff}。\n"
        f"素材案: {suggestion_text} の中から強い方向を1つ選び、必要なら2つ目まで広げて比べる。"
    )


def _extract_answer(raw_output: str) -> str:
    raw = (raw_output or "").strip()
    if not raw:
        return ""

    candidates = [raw]
    matched = re.search(r"\{[\s\S]*\}", raw)
    if matched:
        candidates.insert(0, matched.group(0))

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except Exception:
            continue
        answer = str(parsed.get("answer") or "").strip()
        if answer:
            return answer
    return raw


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
    body = re.sub(r"([。！？]\s*)([A-CＡ-Ｃ])\s*[:：]\s*", r"\1", body)
    body = re.sub(r"(^|\n)([A-CＡ-Ｃ])\s*[:：]\s*", r"\1", body)
    body = re.sub(r"\s{2,}", " ", body)
    body = re.sub(r"。\s+。", "。", body)
    return body.strip()


def _strip_fair_labels(text: str, fair_labels: List[str]) -> str:
    body = str(text or "")
    replacement = "参照した展示群"
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


def _plain_answer_text(answer: str) -> str:
    return re.sub(r"\[([^\]]+)\]\(https?://[^)]+\)", r"\1", str(answer or ""))


def _build_selected_entity_candidates(context: Dict[str, object]) -> List[dict]:
    candidates: List[dict] = []
    known_artist_labels: set[str] = set()

    for row in list(context.get("exhibition_evidence", [])):
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
                "local_path": str(image_item.get("local_path") or "").strip(),
                "r2_key": str(image_item.get("r2_key") or "").strip(),
                "image_url": str(image_item.get("image_url") or "").strip(),
            }
        )

    for row in list(context.get("artist_evidence", [])):
        artist = str(row.get("artist_name") or "").strip()
        if not artist:
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
                "local_path": str(image_item.get("local_path") or "").strip(),
                "r2_key": str(image_item.get("r2_key") or "").strip(),
                "image_url": str(image_item.get("image_url") or "").strip(),
            }
        )

    for artist, source_url in _collect_exhibition_artist_links(context):
        if not artist or artist in known_artist_labels or not source_url:
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
                "local_path": "",
                "r2_key": "",
                "image_url": "",
            }
        )
    return candidates


def _select_entities_for_answer(answer: str, context: Dict[str, object]) -> List[dict]:
    plain_answer = _plain_answer_text(answer)
    matches: List[tuple[int, int, int, int, dict]] = []
    for candidate in _build_selected_entity_candidates(context):
        label = str(candidate.get("label") or "").strip()
        if not label:
            continue
        pos = plain_answer.find(label)
        if pos < 0:
            continue
        kind_order = 0 if str(candidate.get("kind") or "") == "exhibition" else 1
        matches.append((pos, pos + len(label), kind_order, -len(label), candidate))

    matches.sort(key=lambda value: (value[0], value[2], value[3]))

    selected: List[dict] = []
    occupied_spans: List[tuple[int, int]] = []
    seen = set()
    order = 0
    for start, end, _kind_order, _label_len, candidate in matches:
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
        if not (item["local_path"] or item["r2_key"] or item["image_url"]):
            continue
        dedup_key = (
            str(item.get("kind") or ""),
            str(item.get("label") or ""),
            str(item.get("source_url") or ""),
            str(item.get("local_path") or ""),
            str(item.get("r2_key") or ""),
            str(item.get("image_url") or ""),
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
        if not artist:
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
            if _looks_like_artist_label(title_head):
                candidates.append(title_head)

        match = re.search(r"Participating Artists:\s*([^\n]+)", text, flags=re.IGNORECASE)
        if match:
            raw_names = [part.strip() for part in match.group(1).split(",")]
            for raw_name in raw_names:
                if _looks_like_artist_label(raw_name):
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

    replacement = "参照した展示群"
    for gallery in _gallery_labels(context):
        body = body.replace(gallery, replacement)

    for token, title in placeholders.items():
        body = body.replace(token, title)

    body = re.sub(rf"{re.escape(replacement)}(?:\s*/\s*{re.escape(replacement)})+", replacement, body)
    body = re.sub(r"\s{2,}", " ", body)
    return body.strip()


def _allowed_current_entity_labels(context: Dict[str, object]) -> List[str]:
    labels: set[str] = set()
    for row in list(context.get("exhibition_evidence", [])):
        title = str(row.get("title") or "").strip()
        gallery = str(row.get("gallery") or "").strip()
        fair = str(row.get("fair_label") or "").strip()
        if title:
            labels.add(title)
        if gallery:
            labels.add(gallery)
        if fair:
            labels.add(fair)

    for row in list(context.get("artist_evidence", [])):
        artist = str(row.get("artist_name") or "").strip()
        gallery = str(row.get("gallery") or "").strip()
        fair = str(row.get("fair_label") or "").strip()
        if artist:
            labels.add(artist)
        if gallery:
            labels.add(gallery)
        if fair:
            labels.add(fair)

    for artist, _source_url in _collect_exhibition_artist_links(context):
        if artist:
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
        body = _replace_once_outside_markdown_links(body, label, inline)

    return body


def _expand_broad_answer_if_short(
    answer: str,
    question_text: str,
    context: Dict[str, object],
) -> str:
    return (answer or "").strip()


def _visible_answer_chars(answer: str) -> int:
    body = str(answer or "")
    body = re.sub(r"\[([^\]]+)\]\(https?://[^)]+\)", r"\1", body)
    return len(body.strip())


def _fallback_evidence_block(row: dict) -> str:
    label = str(row.get("artist_name") or row.get("title") or "").strip()
    note = str(row.get("summary_ja") or row.get("headline_ja") or row.get("text") or "").strip()
    note = re.sub(r"\s+", " ", note)
    if note:
        note = _snippet(note, limit=170)
    if label and note:
        return f"{label} {note}" if label not in note else note
    return label or note


def _fallback_answer(question_text: str, context: Dict[str, object]) -> str:
    _, fair_labels = _detect_cross_fair_mode(context)
    rows = list(context.get("artist_evidence", []))[:3] + list(context.get("exhibition_evidence", []))[:3]
    blocks: List[str] = []
    seen = set()
    for row in rows:
        block = _fallback_evidence_block(row)
        if not block or block in seen:
            continue
        seen.add(block)
        blocks.append(block)

    answer = "\n\n".join(blocks[:4]).strip()
    if not answer:
        answer = "参照可能な根拠が不足しています。"
    answer = _strip_fair_labels(answer, fair_labels)
    return _truncate_text(answer, ADVISOR_TEXT_MAX_CHARS)


def _build_prompt(question_text: str, context: Dict[str, object]) -> str:
    cross_fair_mode, fair_labels = _detect_cross_fair_mode(context)
    broad_query_mode = _is_broad_query_mode(context)
    rotation_index = _get_rotation_index(context)
    broad_plan = _build_broad_diversity_plan(question_text, context)
    ex_lines = []
    for row in list(context.get("exhibition_evidence", []))[:10]:
        ex_lines.append(
            f"- [{row.get('fair_label')}] {row.get('gallery')} | {row.get('title')} | {row.get('source_url')}"
        )
    ar_lines = []
    for row in list(context.get("artist_evidence", []))[:10]:
        ar_lines.append(
            f"- [{row.get('fair_label')}] {row.get('gallery')} | {row.get('artist_name')} | {row.get('source_url')}"
        )
    evidence_digest = _build_evidence_digest(context, per_kind=3)
    cross_fair_digest = _build_cross_fair_digest(context, fair_labels) if cross_fair_mode else ""
    include_action_steps = _should_include_action_steps(question_text)

    cross_fair_rule = ""
    if cross_fair_mode:
        cross_fair_rule = (
            "- フェア横断時は、片側フェアの根拠だけで回答を閉じないこと。\n"
            "- 本文では、どうしても必要な場合を除いてフェア名を出さないこと。\n"
            "- 広い質問では、固定的な型にせず 1〜3 個の異なる方向を自然に示すこと。\n"
        )

    broad_query_rule = ""
    if broad_query_mode:
        broad_query_rule = (
            f"- 広い質問の rotation index={rotation_index}。\n"
            "- 同じギャラリー / 作家の強調を繰り返しすぎないこと。\n"
            f"- 方向のヒント: A={broad_plan['frieze_family']['label']}, B={broad_plan['liste_family']['label']}, bridge={broad_plan['bridge_family']['label']}。\n"
        )

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

    return f"""
与えられた根拠だけを使って、日本語で回答してください。
制約:
- 必ず参照したRAGの Artist名 or Exhibition名 を回答本文内に「2つ以上～5つ以内」で入れる事。
- 400〜550字、自然な 1〜2 段落で書くこと。
- {PLAIN_JAPANESE_RULE}
- 無駄な相槌や前置きを入れず、簡潔で口語的な文体にすること。
-「今回の根拠では」「参照したのは」などのメタ説明は書かないこと。
{action_rule}{gallery_rule}{cross_fair_rule}{broad_query_rule}- 出力は JSON のみ: {{"answer":"..."}}

質問:
{question_text}

根拠要約（優先参照）:
{evidence_digest if evidence_digest else "- なし"}

フェア横断要約:
{cross_fair_digest if cross_fair_digest else "- 単独フェア"}

展示根拠:
{chr(10).join(ex_lines) if ex_lines else "- なし"}

作家根拠:
{chr(10).join(ar_lines) if ar_lines else "- なし"}
""".strip()


def generate_advisor_grounded_draft(
    question_text: str,
    context: Dict[str, object],
    question_type: str = "type1_text_only",
    has_uploaded_image: bool = False,
    uploaded_image_name: str = "",
) -> Dict[str, object]:
    _, fair_labels = _detect_cross_fair_mode(context)
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

    if api_key.strip():
        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            prompt = _build_prompt(question_text, context)
            res = client.responses.create(model=model, input=prompt)
            answer = _extract_answer(str(res.output_text or ""))
            mode = "openai"
        except Exception as exc:
            warnings.append(f"{type(exc).__name__}: {exc}")

    if not answer:
        answer = _fallback_answer(question_text, context)

    answer = _normalize_answer_text(answer)
    answer = _strip_fixed_headings(answer)
    answer = _strip_rigid_template_markers(answer)
    answer = _strip_fair_labels(answer, fair_labels)
    if not _should_allow_gallery_mentions(question_text):
        answer = _strip_gallery_labels(answer, context)
    unsupported_names = _find_unsupported_proper_names(answer, context)
    if unsupported_names:
        warnings.append(
            "unsupported_current_names_detected: " + ", ".join(unsupported_names[:5])
        )
        answer = _fallback_answer(question_text, context)
        answer = _normalize_answer_text(answer)
        answer = _strip_fixed_headings(answer)
        answer = _strip_rigid_template_markers(answer)
        answer = _strip_fair_labels(answer, fair_labels)
        if not _should_allow_gallery_mentions(question_text):
            answer = _strip_gallery_labels(answer, context)
    answer = _expand_broad_answer_if_short(answer, question_text, context)
    answer = _truncate_text(answer, ADVISOR_TEXT_MAX_CHARS)
    selected_entities = _select_entities_for_answer(answer, context)
    reference_images = _build_reference_images(selected_entities)
    answer = _inject_art_pulse_style_inline_links(answer, context, selected_entities)
    answer = _strip_fair_labels(answer, fair_labels)
    answer_chars = _visible_answer_chars(answer)
    reference_examples = _build_art_pulse_style_reference_lines(selected_entities)
    broad_diversity_meta = {}
    if _is_broad_query_mode(context):
        plan = _build_broad_diversity_plan(question_text, context)
        broad_diversity_meta = {
            "query_kind": plan.get("query_kind"),
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
            "rotation_index": plan.get("rotation_index"),
        }
    attachment_note = (
        f"添付画像（{uploaded_image_name or 'unnamed'}）は保存・ベクトル化せず、今回のtype 1では補助参照扱いです。"
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
        "broad_diversity_meta": broad_diversity_meta,
    }
