from __future__ import annotations

import base64
import os
import re
from typing import Dict

from phase2_advisor_type2_design import (
    ADVISOR_TYPE2_IMAGE_COUNT,
    ADVISOR_TYPE2_IMAGE_MODEL,
    ADVISOR_TYPE2_IMAGE_QUALITY,
    ADVISOR_TYPE2_IMAGE_SIZE,
    ADVISOR_TEXT_MAX_CHARS,
    evaluate_type2_gate,
    truncate_type2_grounded_text,
)

TYPE2_FAILSOFT_MESSAGE = "今回は画像補助を表示できなかったため、本文と根拠のみ表示しています。"


_TYPE2_MEDIUM_HINTS = {
    "installation": ("installation", "インスタレーション", "展示空間", "空間", "site-specific", "site specific", "spatial"),
    "sculpture": ("sculpture", "彫刻", "立体", "object", "ceramic", "ceramics", "オブジェ"),
    "painting": ("painting", "paint", "絵画", "油彩", "油絵", "canvas", "アクリル"),
    "collage": ("collage", "コラージュ", "assemblage"),
    "photograph": ("photo", "photograph", "photography", "写真", "print", "プリント"),
    "video still": ("video", "video still", "film still", "moving image", "projection", "映像"),
}

_TYPE2_VISUAL_HINTS = (
    "color", "色", "light", "光", "shadow", "影", "surface", "表面", "texture", "質感",
    "layer", "層", "composition", "構図", "frame", "フレーム", "distance", "距離",
    "scale", "スケール", "wall", "壁", "room", "会場", "space", "空間", "suspend",
    "吊", "hanging", "plinth", "台座", "floor", "床", "depth", "奥行", "view",
    "lighting", "照明", "material", "素材",
)

_TYPE2_OPERATIONAL_HINTS = (
    "workshop", "ワークショップ", "public", "公共", "safety", "安全", "dmx", "電源",
    "power", "荷重", "運営", "schedule", "budget",
)


def _count_hint_hits(text: str, hints: tuple[str, ...]) -> int:
    low = (text or "").lower()
    return sum(1 for hint in hints if hint and hint.lower() in low)


def _infer_type2_primary_medium(question_text: str, grounded_answer: str) -> str:
    question = question_text or ""
    grounded = grounded_answer or ""
    best_medium = ""
    best_score = 0
    for medium, hints in _TYPE2_MEDIUM_HINTS.items():
        score = (_count_hint_hits(question, hints) * 3) + _count_hint_hits(grounded, hints)
        if score > best_score:
            best_medium = medium
            best_score = score
    return best_medium


def _compress_visual_direction(question_text: str, grounded_answer: str, primary_medium: str) -> str:
    medium_hints = _TYPE2_MEDIUM_HINTS.get(primary_medium, ())
    question_sentences = [s.strip() for s in re.split(r"(?<=[。.!?])\s+|\n+", question_text or "") if s.strip()]
    grounded_sentences = [s.strip() for s in re.split(r"(?<=[。.!?])\s+|\n+", grounded_answer or "") if s.strip()]
    scored = []
    for sentence, source_kind in [(s, "question") for s in question_sentences] + [(s, "grounded") for s in grounded_sentences]:
        lower = sentence.lower()
        score = 0
        medium_hits = _count_hint_hits(lower, medium_hints)
        if medium_hits:
            score += 5 * medium_hits
        if any(h.lower() in lower for h in _TYPE2_VISUAL_HINTS):
            score += 2
        if any(h.lower() in lower for h in _TYPE2_OPERATIONAL_HINTS):
            score -= 3
        if source_kind == "question":
            score += 2
        for medium, hints in _TYPE2_MEDIUM_HINTS.items():
            if medium != primary_medium and _count_hint_hits(lower, hints):
                score -= 3
        if len(sentence) < 8:
            score -= 1
        if score > 0:
            scored.append((score, sentence, source_kind))
    scored.sort(key=lambda item: (-item[0], 0 if item[2] == "question" else 1))
    selected = []
    total = 0
    for _, sentence, _ in scored:
        if sentence in selected:
            continue
        if total + len(sentence) > 360 and selected:
            continue
        selected.append(sentence)
        total += len(sentence)
        if len(selected) >= 4:
            break
    if not selected:
        selected = question_sentences[:1] + grounded_sentences[:1]
    return " ".join(selected).strip()


def _build_medium_focus_guidance(primary_medium: str) -> str:
    if primary_medium == "installation":
        return "Keep the result as an installation or exhibition-space work. Show room context, depth, hanging/support relation, and viewer distance so it does not collapse into a flat standalone abstract image."
    if primary_medium == "sculpture":
        return "Keep the result as a sculpture or three-dimensional object. Show volume, mass, floor/plinth relation, shadows, and how the work occupies real space."
    if primary_medium == "painting":
        return "Keep the result as a painting. Prioritize support, surface, paint layers, edges, and frontal composition; do not drift into a full-room installation view unless explicitly asked."
    if primary_medium == "collage":
        return "Keep the result as a collage or assembled surface. Prioritize cut edges, overlaps, seams, fragments, and layered material contrast."
    if primary_medium == "photograph":
        return "Keep the result as a photograph or photographic print. Prioritize lens-based framing, print surface, crop, and photographic staging over painterly texture."
    if primary_medium == "video still":
        return "Keep the result as a video still or moving-image frame. Prioritize cinematic framing, screen light, temporality, and frame composition over flat painting-like abstraction."
    return "Preserve the medium or format implied by the user, and keep the visual core stronger than operational or logistical context."


def _user_friendly_error(exc: Exception) -> str:
    msg = str(exc or "").strip()
    if not msg:
        return "画像生成APIでエラーが発生しました。"
    short = msg.splitlines()[0]
    return f"画像生成APIエラー: {short[:180]}"


def _image_response_value(item: object, key: str) -> str:
    if isinstance(item, dict):
        return str(item.get(key) or "").strip()
    return str(getattr(item, key, None) or "").strip()


def _build_image_rationale(grounded_answer: str) -> str:
    text = (grounded_answer or "").strip().replace("\n", " ")
    if not text:
        return "回答の方向性を補助的に可視化したコンセプトイメージです。"
    lead = text.split("。", 1)[0].strip()[:70]
    if not lead:
        lead = text[:70]
    return f"回答の要点「{lead}」を補助的に可視化したコンセプトイメージです。"


def _build_type2_image_prompt(
    fair_label: str,
    question_text: str,
    grounded_answer: str,
    context: Dict[str, object],
    has_uploaded_image: bool,
) -> str:
    ex = list(context.get("exhibition_evidence", []))[:4]
    ar = list(context.get("artist_evidence", []))[:4]
    ex_hint = " / ".join(str(x.get("title") or "") for x in ex if x.get("title")) or "exhibition reference candidates"
    ar_hint = " / ".join(str(x.get("artist_name") or "") for x in ar if x.get("artist_name")) or "artist reference candidates"
    attachment_hint = (
        "User attachment present; use it only as a transient direction hint without any persistence."
        if has_uploaded_image
        else "No user attachment."
    )
    primary_medium = _infer_type2_primary_medium(question_text, grounded_answer)
    visual_core = _compress_visual_direction(question_text, grounded_answer, primary_medium)
    medium_guidance = _build_medium_focus_guidance(primary_medium)
    medium_label = primary_medium or "unspecified"

    return (
        "Create ONE image for an art-production advisory response.\n"
        "Safety constraints:\n"
        "- Generate exactly one image.\n"
        "- Do not copy a specific existing artwork, logo, or signature composition.\n"
        "- Treat this as a concept/mood/editorial support image, not artwork reproduction.\n"
        "- No text overlays.\n"
        "- Keep visual fidelity stronger than operational or logistical context.\n"
        "- If workshop/public/safety/power/DMX/logistics notes appear in the source text, treat them as secondary and do not let them override the visual core.\n\n"
        f"Fair context: {fair_label}\n"
        f"User question: {question_text[:1200]}\n"
        f"Primary medium / format to preserve: {medium_label}\n"
        f"Medium fidelity rule: {medium_guidance}\n"
        f"Visual core from grounded text: {visual_core[:900]}\n"
        f"Exhibition hints: {ex_hint}\n"
        f"Artist hints: {ar_hint}\n"
        f"Attachment hint: {attachment_hint}\n"
        "Output: one contemporary concept image that keeps the requested medium/format explicit and visually readable."
    )


def run_type2_gated_image_generation(
    fair_label: str,
    question_text: str,
    type1_draft: Dict[str, object],
    context: Dict[str, object],
    has_uploaded_image: bool,
) -> Dict[str, object]:
    gate = evaluate_type2_gate(
        fair_label=fair_label,
        question_text=question_text,
        type1_draft=type1_draft,
        context=context,
        has_uploaded_image=has_uploaded_image,
    )
    evidence_urls = type1_draft.get("evidence_urls", {}) if isinstance(type1_draft, dict) else {}
    text_answer = truncate_type2_grounded_text(str(type1_draft.get("answer") or ""), ADVISOR_TEXT_MAX_CHARS)

    result: Dict[str, object] = {
        "question_type": "type2_text_plus_image_generation",
        "gate_ok": bool(gate.get("gate_ok")),
        "checks": list(gate.get("checks", [])),
        "required_env_keys": list(gate.get("required_env_keys", [])),
        "optional_env_keys": list(gate.get("optional_env_keys", [])),
        "resolved_env": dict(gate.get("resolved_env", {})),
        "design_spec": dict(gate.get("design_spec", {})),
        "prompt_preview": str(gate.get("prompt_preview") or ""),
        "note": str(gate.get("note") or ""),
        "api_called": False,
        "text_answer": text_answer,
        "text_chars": len(text_answer),
        "image_source_label": "AI generated",
        "generated_image_count": 0,
        "generated_image_url": "",
        "generated_image_bytes": None,
        "model": ADVISOR_TYPE2_IMAGE_MODEL,
        "error": "",
        "debug_error": "",
        "status": "precheck_failed" if not bool(gate.get("gate_ok")) else "ready_for_api",
        "user_message": "",
        "image_rationale": "",
        "evidence_urls": evidence_urls,
        "reference_images": context.get("reference_images", {}),
        "attachment_note": (
            "添付画像あり（保存・ベクトル化・RAG混入なし）。"
            if has_uploaded_image
            else "添付画像なし。"
        ),
    }

    if not result["gate_ok"]:
        result["user_message"] = TYPE2_FAILSOFT_MESSAGE
        return result

    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not openai_key:
        result["error"] = "OPENAI_API_KEY が未設定のため、画像生成を実行できません。"
        result["status"] = "precheck_failed"
        result["user_message"] = TYPE2_FAILSOFT_MESSAGE
        return result

    prompt = _build_type2_image_prompt(
        fair_label=fair_label,
        question_text=question_text,
        grounded_answer=result["text_answer"],
        context=context,
        has_uploaded_image=has_uploaded_image,
    )
    result["prompt_preview"] = prompt

    try:
        from openai import OpenAI

        client = OpenAI(api_key=openai_key)
        result["api_called"] = True
        response = client.images.generate(
            model=ADVISOR_TYPE2_IMAGE_MODEL,
            prompt=prompt,
            quality=ADVISOR_TYPE2_IMAGE_QUALITY,
            size=ADVISOR_TYPE2_IMAGE_SIZE,
            n=ADVISOR_TYPE2_IMAGE_COUNT,
        )

        data = getattr(response, "data", None) or []
        if not data:
            result["error"] = "画像生成の応答が空でした。本文と根拠のみ表示します。"
            result["status"] = "image_failed"
            result["user_message"] = TYPE2_FAILSOFT_MESSAGE
            return result

        first = data[0]
        image_url = _image_response_value(first, "url")
        b64_json = _image_response_value(first, "b64_json")
        if b64_json:
            result["generated_image_bytes"] = base64.b64decode(b64_json)
        if image_url:
            result["generated_image_url"] = image_url

        if result["generated_image_bytes"] is not None or result["generated_image_url"]:
            result["generated_image_count"] = 1
            result["status"] = "success"
            result["user_message"] = "type2 画像生成に成功しました（1枚）。"
            result["image_rationale"] = _build_image_rationale(result["text_answer"])
        else:
            result["error"] = "画像データが取得できませんでした。本文と根拠のみ表示します。"
            result["status"] = "image_failed"
            result["user_message"] = TYPE2_FAILSOFT_MESSAGE
    except Exception as exc:
        result["error"] = _user_friendly_error(exc)
        result["debug_error"] = f"{type(exc).__name__}: {exc}"
        result["status"] = "image_failed"
        result["user_message"] = TYPE2_FAILSOFT_MESSAGE

    return result
