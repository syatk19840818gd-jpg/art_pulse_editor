from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


REPO_ROOT = Path(__file__).resolve().parent

FAIR_LABEL_TO_SLUG = {
    "Frieze London": "frieze_london",
    "Liste Art Fair Basel": "liste",
}

FAIR_SLUG_TO_LABEL = {v: k for k, v in FAIR_LABEL_TO_SLUG.items()}

FORMAL_JSONL_PATHS = {
    "artist_text": {
        "frieze_london": REPO_ROOT / "data/phase1_seed10/raw/artists_frieze_london_2025.jsonl",
        "liste": REPO_ROOT / "data/phase1_seed10/raw/artists_liste_2025.jsonl",
    },
    "exhibitions_text": {
        "frieze_london": REPO_ROOT / "data/phase1_seed10/raw/exhibitions_frieze_london_2025.jsonl",
        "liste": REPO_ROOT / "data/phase1_seed10/raw/exhibitions_liste_2025.jsonl",
    },
    "artist_works_images": {
        "frieze_london": REPO_ROOT / "data/phase1_seed10/derived/artist_works_images_frieze_london.jsonl",
        "liste": REPO_ROOT / "data/phase1_seed10/derived/artist_works_images_liste.jsonl",
    },
    "exhibitions_images": {
        "frieze_london": REPO_ROOT / "data/phase1_seed10/derived/exhibitions_images_frieze_london_2025.jsonl",
        "liste": REPO_ROOT / "data/phase1_seed10/derived/exhibitions_images_liste_2025.jsonl",
    },
}

TARUTANI_TEXT_PATH = REPO_ROOT / "data/Tarutani_data/tarutani_text.jsonl"
IMAGES_CACHE_DIR = REPO_ROOT / "data/phase1_seed10/derived/images"


@dataclass
class CountResult:
    rows: int = 0
    warnings: List[str] | None = None

    def __post_init__(self) -> None:
        if self.warnings is None:
            self.warnings = []


def _iter_jsonl(path: Path) -> Tuple[Iterable[dict], List[str]]:
    warnings: List[str] = []
    rows: List[dict] = []
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


def _sum_results(results: List[CountResult]) -> CountResult:
    warnings: List[str] = []
    total = 0
    for r in results:
        total += r.rows
        warnings.extend(r.warnings or [])
    return CountResult(rows=total, warnings=warnings)


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
        artist_text = _count_jsonl_rows(FORMAL_JSONL_PATHS["artist_text"][fair_slug])
        exhibitions_text = _count_jsonl_rows(FORMAL_JSONL_PATHS["exhibitions_text"][fair_slug])
        artist_images_meta = _count_jsonl_rows(FORMAL_JSONL_PATHS["artist_works_images"][fair_slug])
        exhibitions_images_meta = _count_jsonl_rows(FORMAL_JSONL_PATHS["exhibitions_images"][fair_slug])
        artist_images_files = _count_referenced_image_files(
            FORMAL_JSONL_PATHS["artist_works_images"][fair_slug], "works_image_local_paths", None
        )
        exhibitions_images_files = _count_referenced_image_files(
            FORMAL_JSONL_PATHS["exhibitions_images"][fair_slug], None, "local_path"
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

