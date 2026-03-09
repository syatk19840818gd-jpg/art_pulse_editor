from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from phase2_common_readonly import (
    ARTISTS_TEXT_PATHS,
    ARTIST_WORKS_IMAGE_PATHS,
    EXHIBITIONS_IMAGE_META_PATHS,
    EXHIBITIONS_TEXT_PATHS,
    FAIR_LABEL_TO_SLUG,
    FAIR_SLUG_TO_LABEL,
    IMAGES_CACHE_DIR,
    TARUTANI_TEXT_PATH,
    safe_load_jsonl,
)


@dataclass
class CountResult:
    rows: int = 0
    warnings: List[str] | None = None

    def __post_init__(self) -> None:
        if self.warnings is None:
            self.warnings = []


def _iter_jsonl(path: Path) -> Tuple[Iterable[dict], List[str]]:
    rows, warnings = safe_load_jsonl(path)
    return rows, warnings


def _count_jsonl_rows(path: Path) -> CountResult:
    rows, warnings = _iter_jsonl(path)
    return CountResult(rows=len(rows), warnings=warnings)


def _count_non_empty_text(path: Path) -> CountResult:
    rows, warnings = _iter_jsonl(path)
    count = 0
    for row in rows:
        val = row.get("text")
        if isinstance(val, str) and val.strip():
            count += 1
    return CountResult(rows=count, warnings=warnings)


def _count_referenced_image_files(path: Path, list_key: str | None, item_key: str | None) -> CountResult:
    rows, warnings = _iter_jsonl(path)
    local_paths: List[Path] = []
    for row in rows:
        if list_key:
            vals = row.get(list_key, [])
            if isinstance(vals, list):
                for v in vals:
                    if isinstance(v, str) and v:
                        local_paths.append(Path(v))
        elif item_key:
            v = row.get(item_key)
            if isinstance(v, str) and v:
                local_paths.append(Path(v))
    exists_count = 0
    for lp in local_paths:
        try:
            if lp.exists():
                exists_count += 1
        except OSError:
            continue
    return CountResult(rows=exists_count, warnings=warnings)


def _safe_dir_file_count(path: Path) -> CountResult:
    if not path.exists():
        return CountResult(rows=0, warnings=[f"missing: {path}"])
    try:
        count = sum(1 for p in path.rglob("*") if p.is_file())
        return CountResult(rows=count, warnings=[])
    except OSError as exc:
        return CountResult(rows=0, warnings=[f"scan_error: {path} ({exc})"])


def build_counts(selected_fair: str) -> Dict[str, object]:
    if selected_fair == "Frieze London + Liste Art Fair Basel":
        fair_slugs = ["frieze_london", "liste"]
    else:
        fair_slugs = [FAIR_LABEL_TO_SLUG[selected_fair]]

    breakdown_rows: List[Dict[str, object]] = []
    all_warnings: List[str] = []

    for fair_slug in fair_slugs:
        artist_text = _count_jsonl_rows(ARTISTS_TEXT_PATHS[fair_slug])
        exhibitions_text = _count_jsonl_rows(EXHIBITIONS_TEXT_PATHS[fair_slug])
        artist_images_meta = _count_jsonl_rows(ARTIST_WORKS_IMAGE_PATHS[fair_slug])
        exhibitions_images_meta = _count_jsonl_rows(EXHIBITIONS_IMAGE_META_PATHS[fair_slug])
        artist_images_files = _count_referenced_image_files(
            ARTIST_WORKS_IMAGE_PATHS[fair_slug], "works_image_local_paths", None
        )
        exhibitions_images_files = _count_referenced_image_files(
            EXHIBITIONS_IMAGE_META_PATHS[fair_slug], None, "local_path"
        )

        all_warnings.extend(
            artist_text.warnings
            + exhibitions_text.warnings
            + artist_images_meta.warnings
            + exhibitions_images_meta.warnings
            + artist_images_files.warnings
            + exhibitions_images_files.warnings
        )

        breakdown_rows.append(
            {
                "fair": FAIR_SLUG_TO_LABEL.get(fair_slug, fair_slug),
                "Artist Text (rows)": artist_text.rows,
                "Artist Works Images (meta rows)": artist_images_meta.rows,
                "Artist Works Images (existing files)": artist_images_files.rows,
                "Exhibitions Text (rows)": exhibitions_text.rows,
                "Exhibitions Image (meta rows)": exhibitions_images_meta.rows,
                "Exhibitions Image (existing files)": exhibitions_images_files.rows,
            }
        )

    tarutani_rows = _count_jsonl_rows(TARUTANI_TEXT_PATH)
    tarutani_non_empty = _count_non_empty_text(TARUTANI_TEXT_PATH)
    images_cache = _safe_dir_file_count(IMAGES_CACHE_DIR)
    all_warnings.extend(tarutani_rows.warnings + tarutani_non_empty.warnings + images_cache.warnings)

    total_row = None
    if len(breakdown_rows) > 1:
        total_row = {
            "fair": "Total",
            "Artist Text (rows)": sum(int(r["Artist Text (rows)"]) for r in breakdown_rows),
            "Artist Works Images (meta rows)": sum(int(r["Artist Works Images (meta rows)"]) for r in breakdown_rows),
            "Artist Works Images (existing files)": sum(int(r["Artist Works Images (existing files)"]) for r in breakdown_rows),
            "Exhibitions Text (rows)": sum(int(r["Exhibitions Text (rows)"]) for r in breakdown_rows),
            "Exhibitions Image (meta rows)": sum(int(r["Exhibitions Image (meta rows)"]) for r in breakdown_rows),
            "Exhibitions Image (existing files)": sum(int(r["Exhibitions Image (existing files)"]) for r in breakdown_rows),
        }

    return {
        "breakdown_rows": breakdown_rows,
        "total_row": total_row,
        "tarutani_total_rows": tarutani_rows.rows,
        "tarutani_non_empty_text_rows": tarutani_non_empty.rows,
        "images_cache_file_count": images_cache.rows,
        "warnings": sorted(set(all_warnings)),
        "count_note": (
            "Text件数は formal jsonl の行数。"
            " 画像件数は formal metadata 行数で、existing files は local_path 実在確認（読み取り専用チェック）。"
        ),
    }

