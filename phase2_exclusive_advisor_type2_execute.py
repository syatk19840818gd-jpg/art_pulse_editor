from __future__ import annotations

import base64
import os
from typing import Dict, List

from phase2_exclusive_advisor_draft import EXCLUSIVE_ADVISOR_TEXT_MAX_CHARS

EXCLUSIVE_TYPE2_IMAGE_COUNT = 1
EXCLUSIVE_IMAGE_SOURCE_LABEL = "AI generated"


def _safe_str(value: object) -> str:
    return str(value or "").strip()


def _truncate_text(text: str, limit: int) -> str:
    value = _safe_str(text)
    if len(value) <= limit:
        return value
    head = value[:limit]
    cut = max(head.rfind("。"), head.rfind("、"), head.rfind("！"), head.rfind("？"))
    if cut >= int(limit * 0.7):
        out = head[: cut + 1].rstrip()
    else:
        if limit <= 1:
            out = head[:limit]
        else:
            out = head[: limit - 1].rstrip() + "…"
    if len(out) > limit:
        out = out[:limit]
    return out


def _normalize_answer_for_type2(text: str, question_text: str, limit: int) -> str:
    value = " ".join(_safe_str(text).split())
    if len(value) < 120:
        q = _safe_str(question_text)[:90]
        value = (
            f"{value} 外部参照（展示/作家）で比較軸を確認しつつ、Tarutani抜粋の判断基準に合わせて制作方針を1文で固定してください。"
            f" 相談「{q}」に対しては、素材実験→空間導線→最終選定の順で進めると安定します。"
        ).strip()
    if "外部参照" not in value:
        value = f"{value} 外部参照に基づく比較軸を明示してください。".strip()
    if "Tarutani" not in value and "抜粋" not in value:
        value = f"{value} Tarutani抜粋は判断基準の固定に使い、外部根拠とは役割を分離してください。".strip()
    return _truncate_text(value, limit)


def _build_prompt_preview(
    fair_label: str,
    question_text: str,
    type1_answer: str,
    context: Dict[str, object],
    has_uploaded_image: bool,
) -> str:
    external = context.get("external", {})
    tarutani = context.get("tarutani", {})

    ex_urls = list(external.get("evidence_urls", {}).get("exhibition", []))[:6]
    ar_urls = list(external.get("evidence_urls", {}).get("artist", []))[:6]
    ta_items = list(tarutani.get("context_items", []))[:6]

    ex_lines = "\n".join(f"- {u}" for u in ex_urls) if ex_urls else "- (none)"
    ar_lines = "\n".join(f"- {u}" for u in ar_urls) if ar_urls else "- (none)"
    ta_lines = (
        "\n".join(
            f"- [{row.get('series_name')}] {row.get('source_path')} | {str(row.get('excerpt') or '')[:120]}"
            for row in ta_items
        )
        if ta_items
        else "- (none)"
    )
    attachment = (
        "あり（保存しない・ベクトル化しない・RAG混入しない）"
        if has_uploaded_image
        else "なし"
    )

    return (
        "### Exclusive Advisor type2 prompt preview\n"
        f"- fair: {fair_label}\n"
        f"- user_image: {attachment}\n"
        f"- text max chars: {EXCLUSIVE_ADVISOR_TEXT_MAX_CHARS}\n"
        "- constraints:\n"
        "  - generate exactly one image\n"
        "  - source label: AI generated\n"
        "  - no save for uploaded/generated image\n"
        "  - no R2/formal write\n"
        "  - keep external evidence URLs and Tarutani excerpts separated in output\n\n"
        "#### user question\n"
        f"{_safe_str(question_text)[:1200]}\n\n"
        "#### grounded text draft (type1)\n"
        f"{_safe_str(type1_answer)[:900]}\n\n"
        "#### external evidence urls (exhibitions)\n"
        f"{ex_lines}\n\n"
        "#### external evidence urls (artists)\n"
        f"{ar_lines}\n\n"
        "#### tarutani excerpts\n"
        f"{ta_lines}\n"
    )


def evaluate_exclusive_type2_gate(
    fair_label: str,
    question_text: str,
    type1_draft: Dict[str, object],
    context: Dict[str, object],
    has_uploaded_image: bool,
) -> Dict[str, object]:
    type1_answer = _safe_str(type1_draft.get("answer"))
    type1_chars = int(type1_draft.get("answer_chars") or 0)
    external_url_count = int(type1_draft.get("counts", {}).get("external_url_count") or 0)
    tarutani_excerpt_count = int(type1_draft.get("counts", {}).get("tarutani_excerpt_count") or 0)

    prompt_preview = _build_prompt_preview(
        fair_label=fair_label,
        question_text=question_text,
        type1_answer=type1_answer,
        context=context,
        has_uploaded_image=has_uploaded_image,
    )

    checks = [
        {
            "id": "env_openai_api_key",
            "ok": bool(_safe_str(os.getenv("OPENAI_API_KEY"))),
            "detail": "type2画像生成には OPENAI_API_KEY が必要です。",
        },
        {
            "id": "grounded_type1_success",
            "ok": bool(type1_answer) and 0 < type1_chars <= EXCLUSIVE_ADVISOR_TEXT_MAX_CHARS,
            "detail": "type1 grounded draft（1000字以内）が必要です。",
        },
        {
            "id": "external_evidence_urls_present",
            "ok": external_url_count > 0,
            "detail": "外部根拠URLが1件以上必要です。",
        },
        {
            "id": "tarutani_excerpt_present",
            "ok": tarutani_excerpt_count > 0,
            "detail": "Tarutani抜粋が1件以上必要です。",
        },
        {
            "id": "input_fair_valid",
            "ok": fair_label
            in {
                "Frieze London",
                "Liste Art Fair Basel",
                "Frieze London + Liste Art Fair Basel",
            },
            "detail": "フェア選択は固定オプションから選ぶ必要があります。",
        },
        {
            "id": "input_question_text_present",
            "ok": bool(_safe_str(question_text)),
            "detail": "相談内容（テキスト入力）が必要です。",
        },
        {
            "id": "prompt_preview_composable",
            "ok": bool(_safe_str(prompt_preview)),
            "detail": "prompt preview を組み立て可能である必要があります。",
        },
        {
            "id": "persistence_forbidden",
            "ok": True,
            "detail": "保存/R2/formal書き込みは設計上禁止です。",
        },
    ]

    gate_ok = all(bool(c.get("ok")) for c in checks)
    return {
        "gate_ok": gate_ok,
        "checks": checks,
        "required_env_keys": ["OPENAI_API_KEY"],
        "optional_env_keys": ["IMAGE_MODEL", "VISION_MODEL"],
        "resolved_env": {
            "IMAGE_MODEL": _safe_str(os.getenv("IMAGE_MODEL") or "gpt-image-1"),
            "VISION_MODEL": _safe_str(os.getenv("VISION_MODEL")),
        },
        "prompt_preview": prompt_preview,
        "note": "Exclusive type2はgate制御です。全条件を満たした場合のみAPIを呼びます。",
    }


def collect_failed_checks(gate_result: Dict[str, object]) -> List[str]:
    failed: List[str] = []
    for row in list(gate_result.get("checks", [])):
        if not bool(row.get("ok")):
            failed.append(f"{row.get('id')}: {row.get('detail')}")
    return failed


def _user_friendly_error(exc: Exception) -> str:
    msg = _safe_str(exc)
    if not msg:
        return "画像生成APIでエラーが発生しました。"
    return f"画像生成APIエラー: {msg.splitlines()[0][:180]}"


def _build_image_prompt(
    fair_label: str,
    question_text: str,
    grounded_answer: str,
    context: Dict[str, object],
    has_uploaded_image: bool,
) -> str:
    external = context.get("external", {})
    tarutani = context.get("tarutani", {})
    ex = list(external.get("exhibition_evidence", []))[:4]
    ar = list(external.get("artist_evidence", []))[:4]
    ta = list(tarutani.get("context_items", []))[:4]

    ex_hint = " / ".join(str(x.get("title") or "") for x in ex if x.get("title")) or "展示根拠候補"
    ar_hint = " / ".join(str(x.get("artist_name") or "") for x in ar if x.get("artist_name")) or "作家根拠候補"
    ta_hint = " / ".join(str(x.get("series_name") or "") for x in ta if x.get("series_name")) or "Tarutani文脈"
    attachment_hint = (
        "ユーザー添付画像あり（保存せず、その場の方向性ヒントとしてのみ扱う）。"
        if has_uploaded_image
        else "ユーザー添付画像なし。"
    )

    return (
        "Create ONE concept image for an exclusive artist advisory response.\n"
        "Safety constraints:\n"
        "- Exactly one image.\n"
        "- Do not copy any specific existing artwork.\n"
        "- Do not imitate named artists, exhibition titles, or Tarutani's past works directly.\n"
        "- Focus on direction: composition, color tone, material feel, density, exhibition atmosphere.\n"
        "- Convert evidence into abstract creative direction, not literal reproduction.\n"
        "- No text overlay.\n\n"
        f"Fair: {fair_label}\n"
        f"User consultation: {question_text[:1200]}\n"
        f"Grounded advisory answer (Japanese): {grounded_answer[:900]}\n"
        f"External exhibition hints: {ex_hint}\n"
        f"External artist hints: {ar_hint}\n"
        f"Tarutani context hints: {ta_hint}\n"
        f"Attachment hint: {attachment_hint}\n"
        "Output: one coherent advisory concept image."
    )


def run_exclusive_type2_gated_image_generation(
    fair_label: str,
    question_text: str,
    type1_draft: Dict[str, object],
    context: Dict[str, object],
    has_uploaded_image: bool,
) -> Dict[str, object]:
    gate = evaluate_exclusive_type2_gate(
        fair_label=fair_label,
        question_text=question_text,
        type1_draft=type1_draft,
        context=context,
        has_uploaded_image=has_uploaded_image,
    )

    text_answer = _truncate_text(str(type1_draft.get("answer") or ""), EXCLUSIVE_ADVISOR_TEXT_MAX_CHARS)
    text_answer = _normalize_answer_for_type2(
        text=text_answer,
        question_text=question_text,
        limit=EXCLUSIVE_ADVISOR_TEXT_MAX_CHARS,
    )
    external_urls = dict(type1_draft.get("external_evidence_urls", {}))
    tarutani_excerpts = list(type1_draft.get("tarutani_evidence_excerpts", []))
    failed_checks = collect_failed_checks(gate)

    result: Dict[str, object] = {
        "question_type": "type2_text_plus_image_generation",
        "gate_ok": bool(gate.get("gate_ok")),
        "checks": list(gate.get("checks", [])),
        "required_env_keys": list(gate.get("required_env_keys", [])),
        "optional_env_keys": list(gate.get("optional_env_keys", [])),
        "resolved_env": dict(gate.get("resolved_env", {})),
        "prompt_preview": str(gate.get("prompt_preview") or ""),
        "note": str(gate.get("note") or ""),
        "api_called": False,
        "text_answer": text_answer,
        "text_chars": len(text_answer),
        "image_source_label": EXCLUSIVE_IMAGE_SOURCE_LABEL,
        "generated_image_count": 0,
        "generated_image_url": "",
        "generated_image_bytes": None,
        "model": _safe_str(os.getenv("IMAGE_MODEL") or "gpt-image-1"),
        "error": "",
        "debug_error": "",
        "external_evidence_urls": external_urls,
        "tarutani_evidence_excerpts": tarutani_excerpts,
        "reference_images": dict(context.get("external", {}).get("reference_images", {})),
        "failed_checks": failed_checks,
        "status": "gate_hold" if not bool(gate.get("gate_ok")) else "ready_for_api",
        "user_message": "",
        "attachment_note": (
            "添付画像あり（保存・ベクトル化・RAG混入なし）。"
            if has_uploaded_image
            else "添付画像なし。"
        ),
    }

    if not result["gate_ok"]:
        result["user_message"] = "type2 の実行条件を満たしていないため、画像生成APIは未実行です。本文と根拠のみ表示します。"
        return result

    openai_key = _safe_str(os.getenv("OPENAI_API_KEY"))
    if not openai_key:
        result["error"] = "OPENAI_API_KEY が未設定のため、画像生成を実行できません。"
        result["status"] = "gate_hold"
        result["user_message"] = "OpenAI APIキー未設定のため、画像生成は実行しません。"
        return result

    prompt = _build_image_prompt(
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
                n=EXCLUSIVE_TYPE2_IMAGE_COUNT,
            )
        except TypeError:
            response = client.images.generate(
                model=str(result["model"]),
                prompt=prompt,
                size="1024x1024",
            )

        data = getattr(response, "data", None) or []
        if not data:
            result["error"] = "画像生成の応答が空でした。本文と根拠のみ表示します。"
            result["status"] = "image_failed"
            result["user_message"] = "画像生成の応答が空のため、本文と根拠のみ表示します。"
            return result

        first = data[0]
        image_url = _safe_str(getattr(first, "url", None))
        b64_json = _safe_str(getattr(first, "b64_json", None))
        if b64_json:
            result["generated_image_bytes"] = base64.b64decode(b64_json)
        if image_url:
            result["generated_image_url"] = image_url

        if result["generated_image_bytes"] is not None or result["generated_image_url"]:
            result["generated_image_count"] = 1
            result["status"] = "success"
            result["user_message"] = "type2 画像生成に成功しました（1枚）。"
        else:
            result["error"] = "画像データが取得できませんでした。本文と根拠のみ表示します。"
            result["status"] = "image_failed"
            result["user_message"] = "画像データ未取得のため、本文と根拠のみ表示します。"
    except Exception as exc:
        result["error"] = _user_friendly_error(exc)
        result["debug_error"] = f"{type(exc).__name__}: {exc}"
        result["status"] = "image_failed"
        result["user_message"] = "画像生成でエラーが発生したため、本文と根拠のみ表示します。"

    return result
