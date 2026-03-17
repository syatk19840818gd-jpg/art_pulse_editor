from __future__ import annotations

import os
from typing import Dict, List

ADVISOR_TYPE2_IMAGE_COUNT = 1
ADVISOR_TEXT_MAX_CHARS = 500
ADVISOR_REF_IMAGE_TOTAL = 8
ADVISOR_TYPE2_IMAGE_MODEL = "gpt-image-1"
ADVISOR_TYPE2_IMAGE_QUALITY = "low"
ADVISOR_TYPE2_IMAGE_SIZE = "1024x1024"
IMAGE_TARGET_SIZE_KB_NOT_APPLIED = True


def _safe_str(value: object) -> str:
    return str(value or "").strip()


def truncate_type2_grounded_text(text: str, limit: int = ADVISOR_TEXT_MAX_CHARS) -> str:
    value = (text or "").strip()
    if limit <= 0:
        return ""
    if len(value) <= limit:
        return value
    head = value[:limit]
    cut = max(head.rfind("。"), head.rfind("、"), head.rfind("."), head.rfind(","))
    if cut >= int(limit * 0.7):
        return head[: cut + 1].rstrip()
    fallback = value[: max(limit - 1, 0)].rstrip()
    return fallback + "…" if fallback else ""


def get_type2_design_spec() -> Dict[str, object]:
    return {
        "input": {
            "fair": "Frieze London / Liste Art Fair Basel / both",
            "question_text": "required",
            "optional_user_image": "allowed (session only, no persistence)",
            "question_type": "type 2",
        },
        "intermediate": {
            "grounded_text_evidence": "formal read-only (exhibitions text + artists text)",
            "image_reference_candidates": "formal read-only metadata (exhibitions image + artist works images)",
            "prompt_building": "question + grounded answer + evidence URLs (+ optional attachment hint)",
        },
        "output": {
            "text_answer": f"Japanese <= {ADVISOR_TEXT_MAX_CHARS} chars",
            "generated_image_count": ADVISOR_TYPE2_IMAGE_COUNT,
            "generated_image_model": ADVISOR_TYPE2_IMAGE_MODEL,
            "generated_image_quality": ADVISOR_TYPE2_IMAGE_QUALITY,
            "generated_image_size": ADVISOR_TYPE2_IMAGE_SIZE,
            "evidence_urls": "required",
            "reference_images": f"up to {ADVISOR_REF_IMAGE_TOTAL}",
            "image_source_label": "AI generated",
        },
        "forbidden_persistence": [
            "save_uploaded_image",
            "save_generated_image",
            "save_prompt_raw",
            "r2_upload_or_prune",
            "formal_write",
            "embedding_or_vectorize_uploaded_image",
            "mix_trial_or_logs_with_formal",
        ],
        "note": (
            "Type2 uses lightweight precheck execution. "
            "No extraction/R2/formal writes. "
            "IMAGE_TARGET_SIZE_KB does not apply to generated image in type2."
        ),
    }


def _build_prompt_preview(
    fair_label: str,
    question_text: str,
    type1_answer: str,
    context: Dict[str, object],
    has_uploaded_image: bool,
) -> str:
    ex_urls = list(context.get("evidence_urls", {}).get("exhibition", []))[:6]
    ar_urls = list(context.get("evidence_urls", {}).get("artist", []))[:6]
    ex_lines = "\n".join(f"- {u}" for u in ex_urls) if ex_urls else "- (none)"
    ar_lines = "\n".join(f"- {u}" for u in ar_urls) if ar_urls else "- (none)"
    attachment = (
        "あり（保存しない・ベクトル化しない・RAG混入しない）" if has_uploaded_image else "なし"
    )

    return (
        "### Advisor type2 prompt preview\n"
        f"- fair: {fair_label}\n"
        f"- user_image: {attachment}\n"
        "- constraints:\n"
        f"  - text answer must be Japanese and <= {ADVISOR_TEXT_MAX_CHARS} chars\n"
        f"  - generate exactly {ADVISOR_TYPE2_IMAGE_COUNT} image\n"
        "  - source label for generated image: AI generated\n"
        "  - do not store uploaded/generated images\n"
        "  - use grounded evidence only; do not add unsupported facts\n\n"
        "#### user question\n"
        f"{_safe_str(question_text)[:1200]}\n\n"
        "#### grounded text draft (type1) summary\n"
        f"{_safe_str(type1_answer)[:800]}\n\n"
        "#### evidence urls (exhibitions)\n"
        f"{ex_lines}\n\n"
        "#### evidence urls (artists)\n"
        f"{ar_lines}\n"
    )


def evaluate_type2_gate(
    fair_label: str,
    question_text: str,
    type1_draft: Dict[str, object],
    context: Dict[str, object],
    has_uploaded_image: bool,
) -> Dict[str, object]:
    openai_key_set = bool(_safe_str(os.getenv("OPENAI_API_KEY")))
    vision_model = _safe_str(os.getenv("VISION_MODEL"))

    type1_answer = truncate_type2_grounded_text(_safe_str(type1_draft.get("answer")))
    type1_chars = len(type1_answer)
    evidence_count = int(type1_draft.get("evidence_counts", {}).get("all_unique_urls") or 0)

    checks = [
        {
            "id": "env_openai_api_key",
            "ok": openai_key_set,
            "detail": "画像生成には OPENAI_API_KEY が必要です。",
        },
        {
            "id": "grounded_type1_success",
            "ok": bool(type1_answer) and 0 < type1_chars <= ADVISOR_TEXT_MAX_CHARS and evidence_count > 0,
            "detail": "type1 grounded draft（500字以内・根拠1件以上）が必要です。",
        },
        {
            "id": "input_question_text_present",
            "ok": bool(_safe_str(question_text)),
            "detail": "相談内容（テキスト入力）が必要です。",
        },
    ]

    prompt_preview = _build_prompt_preview(
        fair_label=fair_label,
        question_text=question_text,
        type1_answer=type1_answer,
        context=context,
        has_uploaded_image=has_uploaded_image,
    )
    prompt_composable = bool(_safe_str(prompt_preview))
    checks.append(
        {
            "id": "prompt_preview_composable",
            "ok": prompt_composable,
            "detail": "画像生成用promptを組み立てられることが必要です。",
        }
    )
    gate_ok = all(bool(c["ok"]) for c in checks)

    return {
        "gate_ok": gate_ok,
        "checks": checks,
        "required_env_keys": ["OPENAI_API_KEY"],
        "optional_env_keys": ["VISION_MODEL"],
        "resolved_env": {
            "IMAGE_MODEL": ADVISOR_TYPE2_IMAGE_MODEL,
            "VISION_MODEL": vision_model or "(unset)",
        },
        "design_spec": get_type2_design_spec(),
        "prompt_preview": prompt_preview,
        "note": "Type2は軽量precheck制御です。最低条件を満たした場合のみAPIを呼びます。",
    }


def collect_failed_checks(gate_result: Dict[str, object]) -> List[str]:
    failed: List[str] = []
    for c in list(gate_result.get("checks", [])):
        if not bool(c.get("ok")):
            failed.append(f"{c.get('id')}: {c.get('detail')}")
    return failed
