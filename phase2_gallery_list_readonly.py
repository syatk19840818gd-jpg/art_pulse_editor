from __future__ import annotations

import csv
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from gallery_skip_registry import (
    SKIPPED_GALLERIES_REGISTRY_PATH,
    build_skip_lookup,
    find_skip_entry,
    load_skip_registry_entries,
)
from phase2_common_readonly import FAIR_LABEL_TO_SLUG, FAIR_SLUG_TO_LABEL, GALLERY_LIST_PATHS


def _read_rows_with_fallback(path: Path) -> Tuple[List[List[str]], List[str]]:
    warnings: List[str] = []
    if not path.exists():
        return [], [f"missing: {path}"]

    tried: List[str] = []
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        tried.append(enc)
        try:
            with path.open("r", encoding=enc, newline="") as f:
                return list(csv.reader(f)), warnings
        except UnicodeDecodeError:
            continue
        except OSError as exc:
            return [], [f"read_error: {path} ({exc})"]

    return [], [f"decode_error: {path} encodings={tried}"]


def _norm_space(value: str) -> str:
    return " ".join((value or "").strip().split())


def _norm_search(value: str) -> str:
    return _norm_space(unicodedata.normalize("NFKC", value or "")).casefold()


def _short_url(value: str, max_len: int = 80) -> str:
    url = _norm_space(value)
    if len(url) <= max_len:
        return url
    return f"{url[:max_len - 1]}…"


@dataclass
class GalleryListData:
    records: List[dict]
    warnings: List[str]
    warning_counts: Dict[str, int]
    total_rows: int
    fair_rows: Dict[str, int]
    artists_fallback_rows: int
    artists_raw_rows: int
    artists_empty_rows: int
    skip_registry_filtered_rows: int
    count_note: str


def load_gallery_list_records_readonly() -> GalleryListData:
    records: List[dict] = []
    warnings: List[str] = []
    warning_counts: Dict[str, int] = {
        "missing_file": 0,
        "decode_error": 0,
        "read_error": 0,
        "row_skip_empty_gallery": 0,
        "row_missing_exhibitions_url": 0,
        "row_extra_columns_ignored": 0,
        "row_skip_registry_filtered": 0,
    }
    fair_rows: Dict[str, int] = {"frieze_london": 0, "liste": 0}
    artists_fallback_rows = 0
    artists_raw_rows = 0
    artists_empty_rows = 0
    skip_registry_filtered_rows = 0
    skip_lookup = build_skip_lookup(load_skip_registry_entries(SKIPPED_GALLERIES_REGISTRY_PATH))

    for fair_slug, path in GALLERY_LIST_PATHS.items():
        raw_rows, ws = _read_rows_with_fallback(path)
        warnings.extend(ws)
        for w in ws:
            if w.startswith("missing:"):
                warning_counts["missing_file"] += 1
            elif w.startswith("decode_error:"):
                warning_counts["decode_error"] += 1
            elif w.startswith("read_error:"):
                warning_counts["read_error"] += 1

        for idx, cols in enumerate(raw_rows, start=1):
            if not cols or not any((c or "").strip() for c in cols):
                continue

            # CSV contract: no header, 3 columns; keep backward compatibility with 2 columns.
            gallery_name = _norm_space(cols[0] if len(cols) >= 1 else "")
            exhibitions_url = _norm_space(cols[1] if len(cols) >= 2 else "")
            artists_url = _norm_space(cols[2] if len(cols) >= 3 else "")
            artists_mode = "raw"

            if not gallery_name:
                warnings.append(f"row_skip_empty_gallery: {path} line={idx}")
                warning_counts["row_skip_empty_gallery"] += 1
                continue
            if find_skip_entry(skip_lookup, fair_slug=fair_slug, gallery_name_en=gallery_name) is not None:
                warning_counts["row_skip_registry_filtered"] += 1
                skip_registry_filtered_rows += 1
                continue

            if len(cols) < 2:
                warnings.append(f"row_missing_exhibitions_url: {path} line={idx}")
                warning_counts["row_missing_exhibitions_url"] += 1

            if not artists_url:
                artists_url = exhibitions_url
                artists_mode = "fallback_to_exhibitions_url" if exhibitions_url else "empty"
                if artists_mode == "fallback_to_exhibitions_url":
                    artists_fallback_rows += 1
                else:
                    artists_empty_rows += 1
            else:
                artists_raw_rows += 1

            if len(cols) > 3:
                warnings.append(f"row_extra_columns_ignored: {path} line={idx} cols={len(cols)}")
                warning_counts["row_extra_columns_ignored"] += 1

            records.append(
                {
                    "id": f"{fair_slug}:{idx}",
                    "fair_slug": fair_slug,
                    "fair_label": FAIR_SLUG_TO_LABEL.get(fair_slug, fair_slug),
                    "gallery_name": gallery_name,
                    "gallery_name_norm": _norm_search(gallery_name),
                    "exhibitions_url": exhibitions_url,
                    "exhibitions_url_display": _short_url(exhibitions_url),
                    "artists_url": artists_url,
                    "artists_url_display": _short_url(artists_url),
                    "artists_url_mode": artists_mode,
                    "artists_url_mode_label": (
                        "fallback（Exhibitions URLを流用）"
                        if artists_mode == "fallback_to_exhibitions_url"
                        else ("空欄" if artists_mode == "empty" else "独立artists_url")
                    ),
                }
            )

        fair_rows[fair_slug] = sum(1 for r in records if r["fair_slug"] == fair_slug)

    records.sort(
        key=lambda r: (
            str(r.get("fair_label") or ""),
            str(r.get("gallery_name_norm") or ""),
        )
    )

    return GalleryListData(
        records=records,
        warnings=sorted(set(warnings)),
        warning_counts=warning_counts,
        total_rows=len(records),
        fair_rows=fair_rows,
        artists_fallback_rows=artists_fallback_rows,
        artists_raw_rows=artists_raw_rows,
        artists_empty_rows=artists_empty_rows,
        skip_registry_filtered_rows=skip_registry_filtered_rows,
        count_note=(
            "Gallery listはCSV正本（ヘッダーなし、UTF-8想定）を読み取り専用で表示。"
            " 2列行は artists_url を exhibitions_url でfallback。"
            " 表示整形のみ行い、CSV自体は更新しない。"
        ),
    )


def apply_gallery_list_filters(records: List[dict], fair_label: str, keyword: str) -> List[dict]:
    if fair_label == "Frieze London + Liste Art Fair Basel":
        fair_slugs = {"frieze_london", "liste"}
    elif fair_label in FAIR_LABEL_TO_SLUG:
        fair_slugs = {FAIR_LABEL_TO_SLUG[fair_label]}
    else:
        fair_slugs = {"frieze_london", "liste"}

    key = _norm_search(keyword or "")
    out: List[dict] = []
    for row in records:
        if row.get("fair_slug") not in fair_slugs:
            continue
        if key and key not in str(row.get("gallery_name_norm") or ""):
            continue
        out.append(row)
    return out
