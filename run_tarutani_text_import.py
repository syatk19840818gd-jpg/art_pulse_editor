#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from docx import Document
from r2_auto_sync import auto_sync_after_job, format_auto_sync_brief

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover
    PdfReader = None

RAG_CATEGORY = "tarutani_text"
DATA_ROOT = Path("data")
TARUTANI_ROOT = DATA_ROOT / "Tarutani_data"
OUTPUT_JSONL_PATH = TARUTANI_ROOT / "tarutani_text.jsonl"
SUMMARY_JSON_PATH = TARUTANI_ROOT / "tarutani_text_import_summary.json"
ALLOWED_SUFFIXES = {".docx", ".pdf"}
EXPECTED_SERIES = {"1_Grains", "2_Slideshow", "3_Curves_and_Straights"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def normalize_text_for_hash(text: str) -> str:
    lowered = text.lower()
    return re.sub(r"\s+", " ", lowered).strip()


def compute_text_hash(text: str, source_path: str) -> str:
    normalized = normalize_text_for_hash(text)
    if normalized:
        payload = f"{RAG_CATEGORY}\n{normalized}"
    else:
        # SSOT 4-5: 空文字PDFの衝突防止は source_path をハッシュの種にする
        payload = f"{RAG_CATEGORY}\n{source_path}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def extract_docx_text(path: Path) -> str:
    try:
        document = Document(str(path))
    except Exception:
        return ""
    lines: list[str] = []
    for paragraph in document.paragraphs:
        text = re.sub(r"\s+", " ", str(paragraph.text or "")).strip()
        if text:
            lines.append(text)
    return "\n".join(lines)


def extract_pdf_text(path: Path) -> tuple[str, str]:
    if PdfReader is None:
        return "", "PDF_TEXT_EXTRACTOR_UNAVAILABLE"
    try:
        reader = PdfReader(str(path))
        page_texts: list[str] = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            normalized = re.sub(r"\s+", " ", page_text).strip()
            if normalized:
                page_texts.append(normalized)
        text = "\n\n".join(page_texts).strip()
        if text:
            return text, "PDF_TEXT_EXTRACTED"
        return "", "PDF_TEXT_EMPTY_AFTER_EXTRACTION"
    except Exception as exc:  # noqa: BLE001
        return "", f"PDF_TEXT_EXTRACT_ERROR:{type(exc).__name__}"


def parse_series_and_source_path(file_path: Path) -> tuple[str, str] | None:
    try:
        rel_from_data = file_path.relative_to(DATA_ROOT)
        rel_from_tarutani = file_path.relative_to(TARUTANI_ROOT)
    except ValueError:
        return None

    parts = rel_from_tarutani.parts
    # 想定: {Series_Name}/Text/{Text_File}
    if len(parts) != 3:
        return None
    if parts[1] != "Text":
        return None

    series_name = parts[0]
    source_path = rel_from_data.as_posix()  # Tarutani_data/... (./data は含めない)
    return series_name, source_path


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    started_at = utc_now_iso()
    print(f"[START] Tarutani_Text import at {started_at}")

    if not TARUTANI_ROOT.exists():
        raise FileNotFoundError(f"Missing root directory: {TARUTANI_ROOT}")

    existing_rows = read_jsonl(OUTPUT_JSONL_PATH)
    existing_source_paths = {
        str(row.get("source_path", "")).strip()
        for row in existing_rows
        if str(row.get("source_path", "")).strip()
    }

    candidates = sorted(
        [path for path in TARUTANI_ROOT.rglob("*") if path.is_file()],
        key=lambda p: p.as_posix(),
    )

    counters: Counter[str] = Counter()
    records_to_append: list[dict[str, Any]] = []
    extract_status_counts: Counter[str] = Counter()
    unexpected_series: set[str] = set()

    for file_path in candidates:
        parsed = parse_series_and_source_path(file_path)
        if parsed is None:
            counters["skipped_unexpected_path_structure"] += 1
            continue
        series_name, source_path = parsed

        if series_name not in EXPECTED_SERIES:
            unexpected_series.add(series_name)

        suffix = file_path.suffix.lower()
        if suffix not in ALLOWED_SUFFIXES:
            counters["skipped_unsupported_suffix"] += 1
            continue

        counters["scanned_files_total"] += 1
        counters[f"scanned_{suffix[1:]}"] += 1

        if source_path in existing_source_paths:
            counters["skipped_existing_source_path"] += 1
            continue

        if suffix == ".docx":
            text = extract_docx_text(file_path)
            extract_status = "DOCX_TEXT_EXTRACTED" if text else "DOCX_TEXT_EMPTY_OR_FAILED"
        else:
            text, extract_status = extract_pdf_text(file_path)

        text_hash = compute_text_hash(text=text, source_path=source_path)

        if not text:
            counters["records_with_empty_text"] += 1

        record = {
            "source_path": source_path,
            "series_name": series_name,
            "text": text,
            "text_hash": text_hash,
            "headline_ja": "",
            "extracted_at": utc_now_iso(),
            "r2_key": f"data/{source_path}",
            "source_ext": suffix,
            "extract_status": extract_status,
        }
        records_to_append.append(record)
        existing_source_paths.add(source_path)
        counters["records_appended"] += 1
        extract_status_counts[extract_status] += 1

    OUTPUT_JSONL_PATH.parent.mkdir(parents=True, exist_ok=True)
    append_jsonl(OUTPUT_JSONL_PATH, records_to_append)

    completed_at = utc_now_iso()
    summary = {
        "started_at": started_at,
        "completed_at": completed_at,
        "root_path": str(TARUTANI_ROOT),
        "output_jsonl_path": str(OUTPUT_JSONL_PATH),
        "records_existing_before_run": len(existing_rows),
        "records_appended_in_run": len(records_to_append),
        "records_total_after_run": len(existing_rows) + len(records_to_append),
        "counters": dict(counters),
        "extract_status_counts": dict(extract_status_counts),
        "unexpected_series_names": sorted(unexpected_series),
    }
    write_json(SUMMARY_JSON_PATH, summary)

    print(
        f"[DONE] Tarutani_Text import complete. "
        f"existing={summary['records_existing_before_run']} "
        f"appended={summary['records_appended_in_run']} "
        f"total={summary['records_total_after_run']}"
    )
    print(f"[DONE] output={OUTPUT_JSONL_PATH}")
    print(f"[DONE] summary={SUMMARY_JSON_PATH}")
    auto_sync_result = auto_sync_after_job(
        target="tarutani_all",
        trigger="run_tarutani_text_import.py",
    )
    print(format_auto_sync_brief(auto_sync_result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
