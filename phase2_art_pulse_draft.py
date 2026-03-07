from __future__ import annotations

import os
from typing import Dict, List, Tuple

from phase2_art_pulse_config import ANGLES, PERSONAS

BODY_CHAR_LIMIT = 2000


def _unique_urls(urls: List[str]) -> List[str]:
    seen = set()
    out = []
    for url in urls:
        val = (url or "").strip()
        if not val:
            continue
        if val in seen:
            continue
        seen.add(val)
        out.append(val)
    return out


def _pick_angle(angle_keys: List[str]) -> Tuple[str, str]:
    angle_key = angle_keys[0] if angle_keys else ANGLES[0]["key"]
    lookup = {a["key"]: a["label"] for a in ANGLES}
    return angle_key, lookup.get(angle_key, angle_key)


def _find_reporter(reporter_id: str) -> Dict[str, str]:
    reporter = next((p for p in PERSONAS if p["id"] == reporter_id), PERSONAS[0])
    return reporter


def _build_evidence_payload(overview: Dict[str, object], cap: int = 12) -> Dict[str, object]:
    ex_candidates = list(overview.get("exhibition_candidates", []))[:cap]
    ar_candidates = list(overview.get("artist_candidates", []))[:cap]

    ex_urls = _unique_urls([str(x.get("source_url") or "") for x in ex_candidates])
    ar_urls = _unique_urls([str(x.get("source_url") or "") for x in ar_candidates])

    return {
        "exhibition_candidates": ex_candidates,
        "artist_candidates": ar_candidates,
        "exhibition_urls": ex_urls,
        "artist_urls": ar_urls,
        "all_urls": _unique_urls(ex_urls + ar_urls),
    }


def _truncate_body(body: str, limit: int = BODY_CHAR_LIMIT) -> str:
    text = (body or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


def _fallback_draft(
    fair_label: str,
    reporter: Dict[str, str],
    angle_label: str,
    payload: Dict[str, object],
) -> Dict[str, str]:
    top_ex = payload["exhibition_candidates"][:3]
    top_ar = payload["artist_candidates"][:3]
    ex_titles = " / ".join([str(x.get("title") or "") for x in top_ex if x.get("title")]) or "該当展示なし"
    ar_names = " / ".join([str(x.get("artist") or "") for x in top_ar if x.get("artist")]) or "該当作家なし"

    title = f"{fair_label}の現在地：{angle_label}から見るArt Pulse（下書き）"
    body = (
        f"本稿は{fair_label}を対象に、{reporter['label']}（{reporter['description']}）の視点で、"
        f"{angle_label}を軸に観測した傾向の下書きです。\n\n"
        f"展示側では「{ex_titles}」といった流れが見え、作家側では「{ar_names}」が目立ちます。"
        "今回の段階は read-only evidence の整理を優先しており、断定的な結論よりも観測事実の接続を重視しています。\n\n"
        "次の編集工程では、根拠URL群を維持したまま、重複情報の圧縮と論点の優先順位付けを行う想定です。"
    )
    return {"title": title, "body": _truncate_body(body)}


def _build_prompt(
    fair_label: str,
    reporter: Dict[str, str],
    angle_label: str,
    payload: Dict[str, object],
) -> str:
    ex_lines = []
    for row in payload["exhibition_candidates"]:
        ex_lines.append(
            f"- [{row.get('fair')}] {row.get('gallery')} | {row.get('title')} | {row.get('source_url')}"
        )
    ar_lines = []
    for row in payload["artist_candidates"]:
        ar_lines.append(
            f"- [{row.get('fair')}] {row.get('gallery')} | {row.get('artist')} | {row.get('source_url')}"
        )

    prompt = f"""
あなたは日本語のアート編集記者です。
以下の read-only evidence のみを根拠に、Art Pulse の下書きを作成してください。

制約:
- 出力は日本語
- 本文は最大2000字
- evidence に無い固有名詞/事実を追加しない
- 推測は控えめにし、観測事実ベースで書く
- 形式は次のJSONのみ:
  {{
    "title": "...",
    "body": "..."
  }}

条件:
- 対象フェア: {fair_label}
- 記者: {reporter['label']}（{reporter['description']}）
- 切り口: {angle_label}

Exhibition evidence:
{chr(10).join(ex_lines) if ex_lines else "- none"}

Artist evidence:
{chr(10).join(ar_lines) if ar_lines else "- none"}
"""
    return prompt.strip()


def generate_art_pulse_draft(
    overview: Dict[str, object],
    reporter_id: str,
    angle_keys: List[str],
) -> Dict[str, object]:
    selection = overview.get("selection", {})
    fair_label = str(selection.get("fair_label") or "Frieze London + Liste Art Fair Basel")
    reporter = _find_reporter(reporter_id)
    angle_key, angle_label = _pick_angle(angle_keys)
    payload = _build_evidence_payload(overview)

    model = os.getenv("TEXT_MODEL", "gpt-5-mini")
    api_key = os.getenv("OPENAI_API_KEY", "")

    mode = "fallback"
    title = ""
    body = ""
    error = ""

    if api_key.strip():
        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            prompt = _build_prompt(fair_label, reporter, angle_label, payload)
            res = client.responses.create(model=model, input=prompt)
            raw = (res.output_text or "").strip()
            # Loose JSON parse fallback for safety.
            if raw.startswith("{") and raw.endswith("}"):
                import json

                parsed = json.loads(raw)
                title = str(parsed.get("title") or "").strip()
                body = str(parsed.get("body") or "").strip()
            else:
                lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
                title = lines[0][:120] if lines else ""
                body = "\n".join(lines[1:]) if len(lines) > 1 else raw
            mode = "openai"
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"

    if not title or not body:
        fallback = _fallback_draft(fair_label, reporter, angle_label, payload)
        title = fallback["title"]
        body = fallback["body"]

    body = _truncate_body(body, BODY_CHAR_LIMIT)

    return {
        "mode": mode,
        "model": model,
        "title": title,
        "body": body,
        "body_chars": len(body),
        "persona_id": reporter["id"],
        "persona_label": reporter["label"],
        "angle_key": angle_key,
        "angle_label": angle_label,
        "fair_label": fair_label,
        "year": 2025,
        "evidence_counts": {
            "exhibition_candidates": len(payload["exhibition_candidates"]),
            "artist_candidates": len(payload["artist_candidates"]),
            "all_unique_urls": len(payload["all_urls"]),
        },
        "evidence_urls": {
            "exhibition": payload["exhibition_urls"],
            "artist": payload["artist_urls"],
            "all": payload["all_urls"],
        },
        "warnings": [error] if error else [],
        "note": (
            "複数angle選択時は先頭1件のみ生成に使用します。"
            "本文は2000字上限、根拠URLは本文外に表示します。"
        ),
    }
