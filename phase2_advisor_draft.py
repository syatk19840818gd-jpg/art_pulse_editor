from __future__ import annotations

import os
from typing import Dict, List

from phase2_response_style import PLAIN_JAPANESE_RULE

ADVISOR_TEXT_MAX_CHARS = 500
ADVISOR_REF_IMAGE_TOTAL = 8


def _truncate_text(text: str, limit: int) -> str:
    body = (text or "").strip()
    if len(body) <= limit:
        return body
    return body[:limit].rstrip() + "…"


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


def _fallback_answer(question_text: str, context: Dict[str, object]) -> str:
    ex = list(context.get("exhibition_evidence", []))[:2]
    ar = list(context.get("artist_evidence", []))[:2]
    ex_names = " / ".join([str(x.get("title") or "").strip() for x in ex if x.get("title")]) or "展示事例"
    ar_names = " / ".join([str(x.get("artist_name") or "").strip() for x in ar if x.get("artist_name")]) or "作家事例"

    answer = (
        "相談内容を踏まえ、まずは「素材・スケール・展示導線」の3点を先に固定するのが安全です。"
        f"今回の根拠では、展示側は「{ex_names}」、作家側は「{ar_names}」が参照候補です。"
        "制作方針は、(1)主題を1文で定義、(2)素材テストを小サイズで2案比較、(3)展示空間での視線導線を先に設計、の順で進めると判断しやすくなります。"
        f"質問「{(question_text or '').strip()[:80]}」に対しては、まず試作1点を短期で作り、根拠URLの事例と照らしながら次の改稿点を決める運用を推奨します。"
    )
    return _truncate_text(answer, ADVISOR_TEXT_MAX_CHARS)


def _build_prompt(question_text: str, context: Dict[str, object]) -> str:
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

    return f"""
あなたは日本語で回答するアート制作アドバイザーです。
次の相談に対して、与えられた evidence のみを根拠に回答してください。

制約:
- 本文は日本語500字以内
- {PLAIN_JAPANESE_RULE}
- 断定しすぎる推測を避ける
- evidence にない固有事実を追加しない
- 実制作で使える具体的な次アクションを短く含める
- 出力は JSON のみ: {{"answer":"..."}}

相談:
{question_text}

Exhibitions evidence:
{chr(10).join(ex_lines) if ex_lines else "- none"}

Artists evidence:
{chr(10).join(ar_lines) if ar_lines else "- none"}
""".strip()


def generate_advisor_grounded_draft(
    question_text: str,
    context: Dict[str, object],
    question_type: str = "type1_text_only",
    has_uploaded_image: bool = False,
    uploaded_image_name: str = "",
) -> Dict[str, object]:
    evidence_urls = context.get("evidence_urls", {}) if isinstance(context, dict) else {}
    ex_urls = _dedup_urls(list(evidence_urls.get("exhibition", [])))
    ar_urls = _dedup_urls(list(evidence_urls.get("artist", [])))
    all_urls = _dedup_urls(ex_urls + ar_urls)

    if question_type != "type1_text_only":
        return {
            "question_type": question_type,
            "answer": "type 2（テキスト＋画像生成）は今回未実装です。type 1（テキスト回答のみ）を選択してください。",
            "answer_chars": 51,
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
            raw = (res.output_text or "").strip()
            if raw.startswith("{") and raw.endswith("}"):
                import json

                parsed = json.loads(raw)
                answer = str(parsed.get("answer") or "").strip()
            else:
                answer = raw
            mode = "openai"
        except Exception as exc:
            warnings.append(f"{type(exc).__name__}: {exc}")

    if not answer:
        answer = _fallback_answer(question_text, context)

    answer = _truncate_text(answer, ADVISOR_TEXT_MAX_CHARS)
    attachment_note = (
        f"添付画像（{uploaded_image_name or 'unnamed'}）は保存・ベクトル化せず、今回のtype 1では補助参照扱いです。"
        if has_uploaded_image
        else "添付画像なし。"
    )

    return {
        "question_type": "type1_text_only",
        "answer": answer,
        "answer_chars": len(answer),
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
        "reference_images": context.get("reference_images", {}),
        "warnings": warnings,
        "attachment_note": attachment_note,
    }
