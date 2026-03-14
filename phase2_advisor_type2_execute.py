from __future__ import annotations

import base64
import os
from typing import Dict

from phase2_advisor_draft import ADVISOR_TEXT_MAX_CHARS
from phase2_advisor_type2_design import evaluate_type2_gate

TYPE2_FAILSOFT_MESSAGE = "今回は画像補助を表示できなかったため、本文と根拠のみ表示しています。"


def _truncate_text(text: str, limit: int) -> str:
    value = (text or "").strip()
    if len(value) <= limit:
        return value
    # Prefer cutting at Japanese punctuation near the boundary.
    head = value[:limit]
    cut = max(head.rfind("。"), head.rfind("、"), head.rfind("！"), head.rfind("？"))
    if cut >= int(limit * 0.7):
        return head[: cut + 1].rstrip()
    return head.rstrip() + "…"


def _user_friendly_error(exc: Exception) -> str:
    msg = str(exc or "").strip()
    if not msg:
        return "画像生成APIでエラーが発生しました。"
    short = msg.splitlines()[0]
    return f"画像生成APIエラー: {short[:180]}"


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
    ex_hint = " / ".join(str(x.get("title") or "") for x in ex if x.get("title")) or "展示根拠候補"
    ar_hint = " / ".join(str(x.get("artist_name") or "") for x in ar if x.get("artist_name")) or "作家根拠候補"
    attachment_hint = (
        "ユーザー添付画像あり（保存せず、その場の方向性ヒントとしてのみ扱う）。"
        if has_uploaded_image
        else "ユーザー添付画像なし。"
    )

    return (
        "Create ONE image for an art-production advisory response.\n"
        "Safety constraints:\n"
        "- Generate exactly one image.\n"
        "- Do not copy a specific existing artwork, logo, or signature composition.\n"
        "- Use abstract direction: composition, color mood, material feel, density, installation atmosphere.\n"
        "- Treat this as a concept/mood/editorial support image, not artwork reproduction.\n"
        "- No text overlays.\n\n"
        f"Fair context: {fair_label}\n"
        f"User question: {question_text[:1200]}\n"
        f"Grounded advisory text (Japanese): {grounded_answer[:900]}\n"
        f"Exhibition hints: {ex_hint}\n"
        f"Artist hints: {ar_hint}\n"
        f"Attachment hint: {attachment_hint}\n"
        "Output: one contemporary concept image that aligns with the advisory direction."
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
    text_answer = _truncate_text(str(type1_draft.get("answer") or ""), ADVISOR_TEXT_MAX_CHARS)

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
        "model": os.getenv("IMAGE_MODEL", "gpt-image-1"),
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
        try:
            response = client.images.generate(
                model=str(result["model"]),
                prompt=prompt,
                size="1024x1024",
                n=1,
            )
        except TypeError:
            # Fallback for clients that do not support n.
            response = client.images.generate(
                model=str(result["model"]),
                prompt=prompt,
                size="1024x1024",
            )

        data = getattr(response, "data", None) or []
        if not data:
            result["error"] = "画像生成の応答が空でした。本文と根拠のみ表示します。"
            result["status"] = "image_failed"
            result["user_message"] = TYPE2_FAILSOFT_MESSAGE
            return result

        first = data[0]
        image_url = getattr(first, "url", None) or ""
        b64_json = getattr(first, "b64_json", None) or ""
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
