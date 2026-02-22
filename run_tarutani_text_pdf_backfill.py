#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pypdf import PdfReader

RAG_CATEGORY = "tarutani_text"
DATA_ROOT = Path("data")
INPUT_JSONL_PATH = DATA_ROOT / "Tarutani_data" / "tarutani_text.jsonl"
OUTPUT_DIR = DATA_ROOT / "Tarutani_data" / "enrichment"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def normalize_text_for_hash(text: str) -> str:
    lowered = text.lower()
    return re.sub(r"\s+", " ", lowered).strip()


def compute_text_hash(text: str, source_path: str) -> str:
    import hashlib

    normalized = normalize_text_for_hash(text)
    if normalized:
        payload = f"{RAG_CATEGORY}\n{normalized}"
    else:
        payload = f"{RAG_CATEGORY}\n{source_path}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def extract_pdf_text(path: Path) -> tuple[str, str]:
    try:
        reader = PdfReader(str(path))
        page_texts: list[str] = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                page_texts.append(page_text.strip())
        text = "\n\n".join(page_texts).strip()
        if text:
            return text, "PDF_TEXT_EXTRACTED"
        return "", "PDF_TEXT_EMPTY_AFTER_EXTRACTION"
    except Exception as exc:  # noqa: BLE001
        return "", f"PDF_TEXT_EXTRACT_ERROR:{type(exc).__name__}"


def main() -> int:
    started_at = utc_now_iso()
    print(f"[START] Tarutani PDF backfill at {started_at}")

    if not INPUT_JSONL_PATH.exists():
        raise FileNotFoundError(f"Missing input jsonl: {INPUT_JSONL_PATH}")

    rows = read_jsonl(INPUT_JSONL_PATH)
    output_rows: list[dict[str, Any]] = []
    counters: dict[str, int] = {
        "records_total": len(rows),
        "pdf_records_total": 0,
        "pdf_records_empty_text_before": 0,
        "pdf_records_updated_with_text": 0,
        "pdf_records_still_empty_after": 0,
        "pdf_records_skipped_non_empty_text": 0,
        "pdf_records_missing_source_file": 0,
    }

    for row in rows:
        source_ext = str(row.get("source_ext", "")).strip().lower()
        if source_ext != ".pdf":
            continue

        counters["pdf_records_total"] += 1
        source_path = str(row.get("source_path", "")).strip()
        current_text = str(row.get("text", "")).strip()

        if current_text:
            counters["pdf_records_skipped_non_empty_text"] += 1
            output_rows.append(
                {
                    "source_path": source_path,
                    "status": "SKIPPED_ALREADY_HAS_TEXT",
                    "text_length": len(current_text),
                }
            )
            continue

        counters["pdf_records_empty_text_before"] += 1
        local_path = DATA_ROOT / source_path
        if not local_path.exists():
            counters["pdf_records_missing_source_file"] += 1
            row["extract_status"] = "PDF_SOURCE_FILE_MISSING"
            row["text"] = ""
            row["text_hash"] = compute_text_hash(text="", source_path=source_path)
            counters["pdf_records_still_empty_after"] += 1
            output_rows.append(
                {
                    "source_path": source_path,
                    "status": "PDF_SOURCE_FILE_MISSING",
                    "local_path": local_path.as_posix(),
                }
            )
            continue

        extracted_text, status = extract_pdf_text(local_path)
        if extracted_text:
            row["text"] = extracted_text
            row["text_hash"] = compute_text_hash(text=extracted_text, source_path=source_path)
            row["extract_status"] = status
            counters["pdf_records_updated_with_text"] += 1
            output_rows.append(
                {
                    "source_path": source_path,
                    "status": status,
                    "text_length": len(extracted_text),
                }
            )
            print(f"[UPDATED] {source_path} text_length={len(extracted_text)}")
        else:
            row["text"] = ""
            row["text_hash"] = compute_text_hash(text="", source_path=source_path)
            row["extract_status"] = status
            counters["pdf_records_still_empty_after"] += 1
            output_rows.append(
                {
                    "source_path": source_path,
                    "status": status,
                    "text_length": 0,
                }
            )
            print(f"[SKIP] {source_path} status={status}")

    write_jsonl(INPUT_JSONL_PATH, rows)

    completed_at = utc_now_iso()
    summary = {
        "started_at": started_at,
        "completed_at": completed_at,
        "input_jsonl_path": str(INPUT_JSONL_PATH),
        "counters": counters,
        "text_non_empty_total_after": sum(1 for r in rows if str(r.get("text", "")).strip()),
        "headline_non_empty_total_after": sum(
            1 for r in rows if str(r.get("headline_ja", "")).strip()
        ),
    }

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = OUTPUT_DIR / f"tarutani_pdf_backfill_output_{timestamp}.jsonl"
    summary_path = OUTPUT_DIR / f"tarutani_pdf_backfill_summary_{timestamp}.json"
    write_jsonl(output_path, output_rows)
    write_json(summary_path, summary)

    print(
        "[DONE] Tarutani PDF backfill complete. "
        f"updated={counters['pdf_records_updated_with_text']} "
        f"still_empty={counters['pdf_records_still_empty_after']}"
    )
    print(f"[DONE] output={output_path}")
    print(f"[DONE] summary={summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
