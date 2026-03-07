from __future__ import annotations

import os
from typing import Dict, List

EXCLUSIVE_ADVISOR_TEXT_MAX_CHARS = 1000


def _truncate_text(text: str, limit: int) -> str:
    value = (text or "").strip()
    if len(value) <= limit:
        return value
    head = value[:limit]
    cut = max(head.rfind("。"), head.rfind("、"), head.rfind("！"), head.rfind("？"))
    if cut >= int(limit * 0.7):
        return head[: cut + 1].rstrip()
    return head.rstrip() + "…"


def _dedup_urls(urls: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for url in urls:
        v = (url or "").strip()
        if not v or v in seen:
            continue
        seen.add(v)
        out.append(v)
    return out


def _build_prompt(question_text: str, context: Dict[str, object]) -> str:
    external = context.get("external", {})
    tarutani = context.get("tarutani", {})

    ex_lines = []
    for row in list(external.get("exhibition_evidence", []))[:10]:
        ex_lines.append(
            f"- [{row.get('fair_label')}] {row.get('gallery')} | {row.get('title')} | {row.get('source_url')}"
        )
    ar_lines = []
    for row in list(external.get("artist_evidence", []))[:10]:
        ar_lines.append(
            f"- [{row.get('fair_label')}] {row.get('gallery')} | {row.get('artist_name')} | {row.get('source_url')}"
        )
    ta_lines = []
    for row in list(tarutani.get("context_items", []))[:8]:
        ta_lines.append(
            f"- [{row.get('series_name')}] {row.get('source_path')} | excerpt: {str(row.get('excerpt') or '')[:200]}"
        )

    return f"""
あなたは「垂谷知明専属」の制作アドバイザーです。日本語で回答してください。
次の相談に対して、外部RAG根拠（Exhibitions/Artists）と Tarutani_Text 抜粋を使って助言してください。

重要制約:
- 本文は日本語1000字以内
- 外部RAGの事実とTarutani文脈を混同しない
- 根拠にない固有事実を作らない
- 回答は実制作で使える具体的な次アクションを含む
- 出力は JSON のみ: {{"answer":"..."}}

相談:
{question_text}

外部RAG（Exhibitions）:
{chr(10).join(ex_lines) if ex_lines else "- none"}

外部RAG（Artists）:
{chr(10).join(ar_lines) if ar_lines else "- none"}

Tarutani_Text 抜粋:
{chr(10).join(ta_lines) if ta_lines else "- none"}
""".strip()


def _fallback_answer(question_text: str, context: Dict[str, object]) -> str:
    external = context.get("external", {})
    tarutani = context.get("tarutani", {})

    ex = list(external.get("exhibition_evidence", []))[:2]
    ar = list(external.get("artist_evidence", []))[:2]
    ta = list(tarutani.get("context_items", []))[:2]

    ex_hint = " / ".join(str(x.get("title") or "") for x in ex if x.get("title")) or "展示根拠候補"
    ar_hint = " / ".join(str(x.get("artist_name") or "") for x in ar if x.get("artist_name")) or "作家根拠候補"
    ta_hint = " / ".join(str(x.get("series_name") or "") for x in ta if x.get("series_name")) or "Tarutani文脈"

    text = (
        "相談内容を踏まえ、まず制作方針を「主題・素材・空間導線」の3レイヤーで整理してください。"
        f"外部参照では展示側「{ex_hint}」、作家側「{ar_hint}」が比較軸になります。"
        f"Tarutani_Textでは「{ta_hint}」に見られる語りの重心を参照し、制作意図を短い宣言文として固定するのが有効です。"
        "次の実行順は、(1)1文コンセプト、(2)素材テスト2案、(3)展示動線の簡易図、(4)第三者レビューの順を推奨します。"
        f"相談文「{(question_text or '').strip()[:100]}」については、外部比較で方向を確認しつつ、Tarutani文脈の抜粋に沿って判断基準を言語化すると、次の改稿が安定します。"
    )
    return _truncate_text(text, EXCLUSIVE_ADVISOR_TEXT_MAX_CHARS)


def generate_exclusive_advisor_draft(
    question_text: str,
    context: Dict[str, object],
    has_uploaded_image: bool = False,
    uploaded_image_name: str = "",
) -> Dict[str, object]:
    external = context.get("external", {})
    tarutani = context.get("tarutani", {})

    ex_urls = _dedup_urls(list(external.get("evidence_urls", {}).get("exhibition", [])))
    ar_urls = _dedup_urls(list(external.get("evidence_urls", {}).get("artist", [])))
    all_urls = _dedup_urls(ex_urls + ar_urls)

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

    answer = _truncate_text(answer, EXCLUSIVE_ADVISOR_TEXT_MAX_CHARS)

    return {
        "question_type": "type1_text_only",
        "mode": mode,
        "model": model,
        "answer": answer,
        "answer_chars": len(answer),
        "external_evidence_urls": {
            "exhibition": ex_urls,
            "artist": ar_urls,
            "all": all_urls,
        },
        "tarutani_evidence_excerpts": list(tarutani.get("context_items", [])),
        "reference_images": dict(external.get("reference_images", {})),
        "counts": {
            "external_url_count": len(all_urls),
            "tarutani_excerpt_count": len(tarutani.get("context_items", [])),
        },
        "attachment_note": (
            f"添付画像（{uploaded_image_name or 'unnamed'}）は保存せず、その場の補助情報としてのみ扱いました。"
            if has_uploaded_image
            else "添付画像なし。"
        ),
        "warnings": warnings,
    }

