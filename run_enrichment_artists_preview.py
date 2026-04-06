#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from enrichment_batch_common import extract_response_text_from_body, is_truthy_flag, resolve_runtime_requests_path
from enrichment_requests_runtime import build_artists_enrichment_requests
from model_routing import (
    ARTISTS_ENRICHMENT_FIELD_MODELS,
    get_enrichment_model_fingerprint,
)
from phase2_art_pulse_config import (
    get_current_raw_paths,
    get_enrichment_preview_dir,
    get_enrichment_runtime_requests_path,
)
from run_enrichment_exhibitions_preview import (
    ENRICH_BATCH_COMPLETION_WINDOW,
    ENRICH_USE_OPENAI_BATCH,
    MAX_TEXT_CHARS_FOR_PROMPT,
    extract_json_object,
    normalize_whitespace,
    read_jsonl,
    strip_cookie_noise,
    utc_now_compact,
    utc_now_iso,
    write_jsonl,
)

TARGET_YEAR = 2025
RAG_CATEGORY = "artists_text"

ENRICH_PROMPT_VERSION = "artists_preview_v1"
HEADLINE_MAX_CHARS = 56
SUMMARY_MAX_CHARS = 500
ARTIST_NAME_KANA_MAX_CHARS = 80
SAMPLE_PREVIEW_MAX = 3


def safe_print(line: str) -> None:
    text = str(line)
    encoding = sys.stdout.encoding or "utf-8"
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode(encoding, errors="replace").decode(encoding, errors="replace"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate sample preview for artists text enrichment.")
    parser.add_argument(
        "--sample-max",
        type=int,
        default=SAMPLE_PREVIEW_MAX,
        help="Number of preview samples to generate (1-3).",
    )
    parser.add_argument(
        "--io-root",
        default="",
        help="optional trial I/O root; when set, raw/requests/preview paths resolve under this root",
    )
    return parser.parse_args()


def clamp_sample_max(value: int) -> int:
    return max(1, min(SAMPLE_PREVIEW_MAX, int(value or SAMPLE_PREVIEW_MAX)))


def resolve_io_root(path_text: str) -> Path | None:
    raw = str(path_text or "").strip()
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    return path


def resolve_artists_enrichment_io_paths(*, io_root: Path | None = None) -> dict[str, Any]:
    return {
        "raw_input_paths": get_current_raw_paths("artists", TARGET_YEAR, root=io_root),
        "requests_output_path": get_enrichment_runtime_requests_path("artists", TARGET_YEAR, root=io_root),
        "preview_output_dir": get_enrichment_preview_dir("artists", root=io_root),
    }


def sanitize_headline(headline: str) -> str:
    text = normalize_whitespace(headline)
    text = re.sub(r"^[\s\"'「『]+", "", text)
    text = re.sub(r"[\s\"'」』]+$", "", text)
    if len(text) > HEADLINE_MAX_CHARS:
        text = text[:HEADLINE_MAX_CHARS].rstrip()
    return text


def sanitize_artist_name_kana(text: str) -> str:
    output = normalize_whitespace(text)
    output = re.sub(r"[^\u30A0-\u30FF\u30FC・･\s]", "", output)
    output = re.sub(r"\s+", "", output).strip("・･")
    if len(output) > ARTIST_NAME_KANA_MAX_CHARS:
        output = output[:ARTIST_NAME_KANA_MAX_CHARS]
    return output


def sanitize_summary(summary: str) -> str:
    text = strip_cookie_noise(summary)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\.{3,}", "。", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > SUMMARY_MAX_CHARS:
        text = text[:SUMMARY_MAX_CHARS].rstrip(" 、,.;") + "。"
    return text


def infer_artist_name_en(row: dict[str, Any]) -> str:
    for key in ("artist_name_en", "artist", "name"):
        value = normalize_whitespace(str(row.get(key) or ""))
        if value:
            return value

    text = str(row.get("text") or "")
    for line in text.splitlines():
        cleaned = normalize_whitespace(line)
        if not cleaned:
            continue
        cleaned = re.sub(r"\s*[|・].*$", "", cleaned).strip()
        if cleaned:
            return cleaned

    source_url = ""
    source_urls = row.get("source_urls")
    if isinstance(source_urls, list) and source_urls:
        source_url = str(source_urls[0] or "").strip()
    if not source_url:
        source_url = str(row.get("source_url") or "").strip()

    if source_url:
        parsed = urlparse(source_url)
        slug = parsed.path.rstrip("/").split("/")[-1]
        slug = re.sub(r"^\d+[-_]", "", slug)
        slug = normalize_whitespace(re.sub(r"[-_]+", " ", slug))
        if slug:
            return slug.title()

    return "Unknown Artist"


def select_preview_samples(request_rows: list[dict[str, Any]], max_samples: int) -> list[dict[str, Any]]:
    if not request_rows:
        return []

    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()

    def pick_longest(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not rows:
            return None
        return sorted(rows, key=lambda x: int(x.get("text_length") or 0), reverse=True)[0]

    for fair_slug in ("frieze_london", "liste"):
        fair_rows = [r for r in request_rows if str(r.get("fair_slug") or "").strip() == fair_slug]
        chosen = pick_longest(fair_rows)
        if chosen is None:
            continue
        request_id = str(chosen.get("request_id") or "")
        if request_id and request_id not in selected_ids:
            selected.append(chosen)
            selected_ids.add(request_id)
            if len(selected) >= max_samples:
                return selected

    remaining = [r for r in request_rows if str(r.get("request_id") or "") not in selected_ids]
    if remaining and len(selected) < max_samples:
        remaining_sorted = sorted(remaining, key=lambda x: int(x.get("text_length") or 0))
        selected.append(remaining_sorted[len(remaining_sorted) // 2])

    return selected[:max_samples]


def build_openai_request_body(model: str, row: dict[str, Any]) -> dict[str, Any]:
    artist_name_en = infer_artist_name_en(row)
    source_urls = row.get("source_urls")
    source_url = ""
    if isinstance(source_urls, list) and source_urls:
        source_url = str(source_urls[0] or "").strip()
    source_url = source_url or str(row.get("source_url") or "").strip()
    prompt_text = str(row.get("text") or "")[:MAX_TEXT_CHARS_FOR_PROMPT]
    return {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "You are generating enrichment JSON for artist pages."
                            "Return JSON only."
                            "headline_ja must be Japanese under 56 chars."
                            "summary_ja must be Japanese under 500 chars."
                            "artist_name_kana must be Katakana."
                        ),
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            f"fair_slug: {row.get('fair_slug', '')}\n"
                            f"gallery_name_en: {row.get('gallery_name_en', '')}\n"
                            f"artist_name_en: {artist_name_en}\n"
                            f"source_url: {source_url}\n"
                            f"text:\n{prompt_text}\n\n"
                            "Return JSON: "
                            "{\"headline_ja\":\"...\",\"summary_ja\":\"...\",\"artist_name_kana\":\"...\"}"
                        ),
                    }
                ],
            },
        ],
    }


def parse_openai_response_body(body: dict[str, Any]) -> tuple[str, str, str]:
    obj = extract_json_object(extract_response_text_from_body(body))
    if obj is None:
        raise RuntimeError("openai_output_not_json")

    headline = sanitize_headline(str(obj.get("headline_ja") or ""))
    summary = sanitize_summary(str(obj.get("summary_ja") or ""))
    artist_name_kana = sanitize_artist_name_kana(str(obj.get("artist_name_kana") or ""))

    if not headline:
        raise RuntimeError("empty_headline")
    if not summary:
        raise RuntimeError("empty_summary")

    return headline, summary, artist_name_kana


def build_warnings(*, summary_ja: str, artist_name_en: str, artist_name_kana: str) -> list[str]:
    warnings: list[str] = []
    summary = summary_ja or ""

    if re.search(r"https?://", summary):
        warnings.append("url_repeat")
    if len(summary) > SUMMARY_MAX_CHARS:
        warnings.append("summary_over_limit")
    if artist_name_en:
        lowered = summary.lower()
        if lowered.count(artist_name_en.lower()) >= 2:
            warnings.append("artist_name_repeat")
    if not artist_name_kana:
        warnings.append("artist_name_kana_empty")

    return warnings


def _build_raw_row_index(raw_input_paths: dict[str, Path]) -> dict[tuple[str, str, str], dict[str, Any]]:
    index: dict[tuple[str, str, str], dict[str, Any]] = {}
    for fair_slug, raw_path in raw_input_paths.items():
        for row in read_jsonl(raw_path):
            text_hash = str(row.get("text_hash") or "").strip()
            source_url = str(row.get("source_url") or "").strip()
            if not text_hash:
                continue
            index[(fair_slug, text_hash, source_url)] = row
            if (fair_slug, text_hash, "") not in index:
                index[(fair_slug, text_hash, "")] = row
    return index


def _resolve_batch_preview_values(
    *,
    request_row: dict[str, Any],
    raw_row_index: dict[tuple[str, str, str], dict[str, Any]],
) -> tuple[str, str, str, dict[str, Any]]:
    fair_slug = str(request_row.get("fair_slug") or "").strip()
    text_hash = str(request_row.get("text_hash") or "").strip()
    source_url = str(request_row.get("source_url") or "").strip()
    raw_row = raw_row_index.get((fair_slug, text_hash, source_url)) or raw_row_index.get((fair_slug, text_hash, ""))
    if raw_row is None:
        raise RuntimeError(f"preview_source_row_not_found:{fair_slug}:{text_hash}")

    enrich_mode = str(raw_row.get("enrich_mode") or "").strip()
    if enrich_mode != "openai_batch_apply":
        raise RuntimeError(f"preview_batch_enforcement_violation:enrich_mode={enrich_mode or 'missing'}")

    headline = sanitize_headline(str(raw_row.get("headline_ja") or ""))
    summary = sanitize_summary(str(raw_row.get("summary_ja") or ""))
    artist_name_kana = sanitize_artist_name_kana(str(raw_row.get("artist_name_kana") or ""))
    if not headline or not summary or not artist_name_kana:
        raise RuntimeError("preview_batch_enforcement_violation:missing_batch_outputs")
    return headline, summary, artist_name_kana, raw_row


def make_preview_rows(
    sample_rows: list[dict[str, Any]],
    *,
    raw_input_paths: dict[str, Path],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    use_batch = os.getenv("ENRICH_USE_OPENAI_BATCH", ENRICH_USE_OPENAI_BATCH).strip() or ENRICH_USE_OPENAI_BATCH
    if not is_truthy_flag(use_batch):
        raise RuntimeError("preview_batch_enforcement_violation:batch_flag_disabled")

    raw_row_index = _build_raw_row_index(raw_input_paths)
    model_fingerprint = get_enrichment_model_fingerprint("artists")
    stats = {"batch_snapshot_ok": 0, "warnings": 0}
    preview_rows: list[dict[str, Any]] = []

    for row in sample_rows:
        artist_name_en = infer_artist_name_en(row)
        source_urls = row.get("source_urls")
        source_url = ""
        if isinstance(source_urls, list) and source_urls:
            source_url = str(source_urls[0] or "").strip()
        source_url = source_url or str(row.get("source_url") or "").strip()
        headline_ja, summary_ja, artist_name_kana, raw_row = _resolve_batch_preview_values(
            request_row=row,
            raw_row_index=raw_row_index,
        )

        warnings = build_warnings(
            summary_ja=summary_ja,
            artist_name_en=artist_name_en,
            artist_name_kana=artist_name_kana,
        )
        stats["warnings"] += len(warnings)
        stats["batch_snapshot_ok"] += 1

        preview_rows.append(
            {
                "request_id": row.get("request_id"),
                "text_hash": row.get("text_hash"),
                "fair_slug": row.get("fair_slug"),
                "rag_category": row.get("rag_category") or RAG_CATEGORY,
                "gallery_name_en": row.get("gallery_name_en"),
                "artist_name_en": artist_name_en,
                "artist_name_kana": artist_name_kana,
                "source_url": source_url,
                "text_excerpt": normalize_whitespace(str(row.get("text") or ""))[:320],
                "headline_ja": headline_ja,
                "summary_ja": summary_ja,
                "headline_ja_chars": len(headline_ja),
                "summary_ja_chars": len(summary_ja),
                "artist_name_kana_chars": len(artist_name_kana),
                "warnings": warnings,
                "enrich_status": "preview_generated_from_batch_output",
                "enrich_model": model_fingerprint,
                "enrich_models_by_field": dict(ARTISTS_ENRICHMENT_FIELD_MODELS),
                "enrich_mode": "openai_batch_apply",
                "api_mode": "openai_batch_apply_snapshot",
                "execution_mode": "sample_preview_batch_snapshot",
                "batch_required": True,
                "batch_used": True,
                "enrich_use_openai_batch": use_batch,
                "enrich_completion_window": str(raw_row.get("enrich_completion_window") or ENRICH_BATCH_COMPLETION_WINDOW),
                "enrich_prompt_version": str(raw_row.get("enrich_prompt_version") or ENRICH_PROMPT_VERSION),
                "enrich_input_text_hash": row.get("text_hash"),
                "enrich_input_chars": int(row.get("text_length") or 0),
                "enrich_generated_at": utc_now_iso(),
                "enrich_notes": "",
                "enrich_generation_method": "batch_snapshot",
            }
        )

    return preview_rows, stats


def ensure_requests_output_path(*, io_root: Path | None = None) -> Path:
    io_paths = resolve_artists_enrichment_io_paths(io_root=io_root)
    requests_path = resolve_runtime_requests_path("artists", target_year=TARGET_YEAR, root=io_root)
    if requests_path.exists():
        return requests_path
    build_artists_enrichment_requests(
        raw_input_paths=io_paths["raw_input_paths"],
        output_path=requests_path,
        target_year=TARGET_YEAR,
        rag_category=RAG_CATEGORY,
    )
    return requests_path


def load_request_rows(*, io_root: Path | None = None) -> list[dict[str, Any]]:
    requests_path = ensure_requests_output_path(io_root=io_root)
    rows = read_jsonl(requests_path)
    out: list[dict[str, Any]] = []
    for row in rows:
        text_hash = str(row.get("text_hash") or "").strip()
        text = str(row.get("text") or "").strip()
        rag_category = str(row.get("rag_category") or "").strip()
        if rag_category and rag_category != RAG_CATEGORY:
            continue
        if not text_hash or not text:
            continue
        out.append(row)
    return out


def main() -> int:
    args = parse_args()
    sample_max = clamp_sample_max(args.sample_max)
    started_at = utc_now_iso()
    io_root = resolve_io_root(args.io_root)
    io_paths = resolve_artists_enrichment_io_paths(io_root=io_root)

    request_rows = load_request_rows(io_root=io_root)
    sample_rows = select_preview_samples(request_rows, max_samples=sample_max)
    preview_rows, preview_stats = make_preview_rows(sample_rows, raw_input_paths=io_paths["raw_input_paths"])

    stamp = utc_now_compact()
    preview_path = io_paths["preview_output_dir"] / f"artists_enrichment_preview_2025_{stamp}.jsonl"
    write_jsonl(preview_path, preview_rows)

    safe_print(f"[START] artists enrichment preview: {started_at}")
    safe_print(f"[DONE] requests={io_paths['requests_output_path']} total={len(request_rows)}")
    safe_print(f"[DONE] preview={preview_path} samples={len(preview_rows)}")
    safe_print(
        "[DONE] preview_stats="
        f"batch_snapshot_ok={preview_stats['batch_snapshot_ok']} warnings={preview_stats['warnings']}"
    )

    for i, row in enumerate(preview_rows, start=1):
        safe_print(
            f"[PREVIEW {i}] fair={row.get('fair_slug')} gallery={row.get('gallery_name_en')} "
            f"artist={row.get('artist_name_en')} request_id={row.get('request_id')}"
        )
        safe_print(f"  headline_ja: {row.get('headline_ja')}")
        safe_print(f"  artist_name_kana: {row.get('artist_name_kana')}")
        safe_print(f"  summary_ja: {row.get('summary_ja')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
