from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

from phase2_advisor_readonly import build_advisor_grounded_context

REPO_ROOT = Path(__file__).resolve().parent
TARUTANI_TEXT_PATH = REPO_ROOT / "data/Tarutani_data/tarutani_text.jsonl"

EXCLUSIVE_TEXT_MAX_CHARS = 1000
EXCLUSIVE_REF_IMAGE_TOTAL = 8


def _safe_load_jsonl(path: Path) -> Tuple[List[dict], List[str]]:
    rows: List[dict] = []
    warnings: List[str] = []
    if not path.exists():
        warnings.append(f"missing: {path}")
        return rows, warnings
    try:
        with path.open("r", encoding="utf-8") as f:
            for idx, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    warnings.append(f"json_decode_error: {path} line={idx}")
    except OSError as exc:
        warnings.append(f"read_error: {path} ({exc})")
    return rows, warnings


def _tokenize_query(query_text: str) -> List[str]:
    tokens: List[str] = []
    for token in re.split(r"[\s,、。/|;:()\[\]{}]+", (query_text or "").strip()):
        token = token.strip().lower()
        if len(token) >= 2:
            tokens.append(token)
    return tokens[:24]


def _score_text(haystack: str, tokens: List[str]) -> int:
    if not tokens:
        return 0
    low = (haystack or "").lower()
    return sum(1 for t in tokens if t in low)


def _select_tarutani_context_rows(rows: List[dict], tokens: List[str], k: int, per_source_cap: int) -> List[dict]:
    scored: List[dict] = []
    for row in rows:
        text = str(row.get("text") or "")
        source_path = str(row.get("source_path") or "")
        series_name = str(row.get("series_name") or "")
        headline = str(row.get("headline_ja") or "")
        hay = " ".join([series_name, source_path, headline, text[:2000]])
        score = _score_text(hay, tokens)
        if tokens and score <= 0:
            continue
        scored.append(
            {
                "source_path": source_path,
                "series_name": series_name,
                "headline_ja": headline,
                "excerpt": text.strip()[:280],
                "score": score,
            }
        )

    if not scored and rows:
        for row in rows[:k]:
            text = str(row.get("text") or "")
            scored.append(
                {
                    "source_path": str(row.get("source_path") or ""),
                    "series_name": str(row.get("series_name") or ""),
                    "headline_ja": str(row.get("headline_ja") or ""),
                    "excerpt": text.strip()[:280],
                    "score": 0,
                }
            )

    scored.sort(key=lambda r: (-int(r.get("score", 0)), str(r.get("source_path") or "")))

    selected: List[dict] = []
    source_counts: Dict[str, int] = {}
    for row in scored:
        source = str(row.get("source_path") or "")
        source_counts.setdefault(source, 0)
        if source_counts[source] >= per_source_cap:
            continue
        source_counts[source] += 1
        selected.append(row)
        if len(selected) >= k:
            break
    return selected


def build_exclusive_advisor_context(
    fair_label: str,
    question_text: str,
    external_text_limit_per_kind: int = 12,
    tarutani_k: int = 6,
    tarutani_per_source_cap: int = 2,
) -> Dict[str, object]:
    external = build_advisor_grounded_context(
        fair_label=fair_label,
        question_text=question_text,
        text_limit_per_kind=external_text_limit_per_kind,
    )

    tarutani_rows, t_warnings = _safe_load_jsonl(TARUTANI_TEXT_PATH)
    tokens = _tokenize_query(question_text)
    tarutani_context = _select_tarutani_context_rows(
        rows=tarutani_rows,
        tokens=tokens,
        k=tarutani_k,
        per_source_cap=tarutani_per_source_cap,
    )

    warnings = sorted(set(list(external.get("warnings", [])) + t_warnings))
    external_urls = external.get("evidence_urls", {})

    return {
        "selection": {
            "fair_label": fair_label,
            "year": 2025,
            "tokens": tokens,
            "question_text": question_text,
        },
        "external": {
            "exhibition_evidence": list(external.get("exhibition_evidence", [])),
            "artist_evidence": list(external.get("artist_evidence", [])),
            "evidence_urls": dict(external_urls),
            "reference_images": dict(external.get("reference_images", {})),
            "counts": dict(external.get("counts", {})),
            "count_note": str(external.get("count_note") or ""),
        },
        "tarutani": {
            "context_items": tarutani_context,
            "count": len(tarutani_context),
            "count_note": "Tarutani context is used only as internal drafting context (not mixed into external result list).",
        },
        "warnings": warnings,
    }

