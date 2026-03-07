from __future__ import annotations

import os
from typing import Dict, List

ADVISOR_TYPE2_IMAGE_COUNT = 1
ADVISOR_TEXT_MAX_CHARS = 500
ADVISOR_REF_IMAGE_TOTAL = 8
IMAGE_TARGET_SIZE_KB_NOT_APPLIED = True


def _safe_str(value: object) -> str:
    return str(value or "").strip()


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
            "Type2 uses gated execution. "
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
    image_model = _safe_str(os.getenv("IMAGE_MODEL") or "gpt-image-1")
    vision_model = _safe_str(os.getenv("VISION_MODEL"))

    type1_answer = _safe_str(type1_draft.get("answer"))
    type1_chars = int(type1_draft.get("answer_chars") or 0)
    evidence_count = int(type1_draft.get("evidence_counts", {}).get("all_unique_urls") or 0)

    checks = [
        {
            "id": "env_openai_api_key",
            "ok": openai_key_set,
            "detail": "OPENAI_API_KEY is required for type2 image generation.",
        },
        {
            "id": "grounded_type1_success",
            "ok": bool(type1_answer) and 0 < type1_chars <= ADVISOR_TEXT_MAX_CHARS and evidence_count > 0,
            "detail": "type1 grounded draft must exist (<=500 chars and evidence>0).",
        },
        {
            "id": "input_fair_valid",
            "ok": fair_label in {
                "Frieze London",
                "Liste Art Fair Basel",
                "Frieze London + Liste Art Fair Basel",
            },
            "detail": "fair must be one of fixed options.",
        },
        {
            "id": "input_question_text_present",
            "ok": bool(_safe_str(question_text)),
            "detail": "question text is required.",
        },
        {
            "id": "evidence_scope_formal_readonly",
            "ok": int(context.get("counts", {}).get("all_unique_url_count") or 0) > 0,
            "detail": "formal read-only evidence URL must exist.",
        },
        {
            "id": "persistence_forbidden",
            "ok": True,
            "detail": "save/R2/formal-write paths are forbidden by design.",
        },
    ]

    prompt_preview = _build_prompt_preview(
        fair_label=fair_label,
        question_text=question_text,
        type1_answer=type1_answer,
        context=context,
        has_uploaded_image=has_uploaded_image,
    )
    gate_ok = all(bool(c["ok"]) for c in checks)
    if "http" not in prompt_preview.lower():
        gate_ok = False
        checks.append(
            {
                "id": "prompt_has_root_evidence_urls",
                "ok": False,
                "detail": "prompt preview must include at least one evidence URL.",
            }
        )
    else:
        checks.append(
            {
                "id": "prompt_has_root_evidence_urls",
                "ok": True,
                "detail": "prompt preview contains evidence URLs.",
            }
        )

    return {
        "gate_ok": gate_ok,
        "checks": checks,
        "required_env_keys": ["OPENAI_API_KEY"],
        "optional_env_keys": ["IMAGE_MODEL", "VISION_MODEL"],
        "resolved_env": {
            "IMAGE_MODEL": image_model or "(unset)",
            "VISION_MODEL": vision_model or "(unset)",
        },
        "design_spec": get_type2_design_spec(),
        "prompt_preview": prompt_preview,
        "note": "Type2 is gated. API call is allowed only when all checks pass.",
    }


def collect_failed_checks(gate_result: Dict[str, object]) -> List[str]:
    failed: List[str] = []
    for c in list(gate_result.get("checks", [])):
        if not bool(c.get("ok")):
            failed.append(f"{c.get('id')}: {c.get('detail')}")
    return failed

