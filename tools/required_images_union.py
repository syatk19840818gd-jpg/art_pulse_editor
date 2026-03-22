#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from phase2_art_pulse_config import (
    REPO_ROOT,
    get_current_artist_image_meta_paths,
    get_current_exhibitions_image_meta_paths,
    get_image_cache_dir,
    get_image_cache_rel_path,
)

DEFAULT_IMAGE_CACHE_ROOT = REPO_ROOT / get_image_cache_dir()
DEFAULT_EXHIBITIONS_META = [
    REPO_ROOT / path
    for path in get_current_exhibitions_image_meta_paths().values()
]
DEFAULT_ARTIST_META = [
    REPO_ROOT / path
    for path in get_current_artist_image_meta_paths().values()
]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def build_required_images_union(
    *,
    exhibitions_meta_paths: list[Path] | None = None,
    artist_meta_paths: list[Path] | None = None,
    images_root: Path = DEFAULT_IMAGE_CACHE_ROOT,
    require_exhibitions: bool = True,
) -> dict[str, Any]:
    ex_paths = exhibitions_meta_paths or DEFAULT_EXHIBITIONS_META
    ar_paths = artist_meta_paths or DEFAULT_ARTIST_META

    existing_ex_paths = [p for p in ex_paths if p.exists()]
    existing_ar_paths = [p for p in ar_paths if p.exists()]

    if not existing_ar_paths:
        raise RuntimeError("artist image metadata not found; cannot build union required set")
    if require_exhibitions and not existing_ex_paths:
        raise RuntimeError("exhibitions image metadata not found; cannot build union required set")

    exhibitions_required: set[str] = set()
    artist_required: set[str] = set()

    ex_rows = 0
    for p in existing_ex_paths:
        rows = _read_jsonl(p)
        ex_rows += len(rows)
        for row in rows:
            rel = get_image_cache_rel_path(
                str(row.get("local_path") or ""),
                images_root=images_root,
            )
            if rel:
                exhibitions_required.add(rel)

    ar_rows = 0
    for p in existing_ar_paths:
        rows = _read_jsonl(p)
        ar_rows += len(rows)
        for row in rows:
            local_paths = row.get("works_image_local_paths") or []
            if not isinstance(local_paths, list):
                continue
            for lp in local_paths:
                rel = get_image_cache_rel_path(
                    str(lp or ""),
                    images_root=images_root,
                )
                if rel:
                    artist_required.add(rel)

    if require_exhibitions and not exhibitions_required:
        raise RuntimeError("exhibitions required set is empty; refuse union generation")
    if not artist_required:
        raise RuntimeError("artist required set is empty; refuse union generation")

    union_required = exhibitions_required | artist_required
    return {
        "images_root": str(images_root),
        "exhibitions_meta_paths": [str(p) for p in existing_ex_paths],
        "artist_meta_paths": [str(p) for p in existing_ar_paths],
        "exhibitions_meta_rows": ex_rows,
        "artist_meta_rows": ar_rows,
        "exhibitions_required": exhibitions_required,
        "artist_required": artist_required,
        "union_required": union_required,
        "exhibitions_required_count": len(exhibitions_required),
        "artist_required_count": len(artist_required),
        "union_required_count": len(union_required),
    }


def count_images_under_root(images_root: Path = DEFAULT_IMAGE_CACHE_ROOT) -> int:
    if not images_root.exists():
        return 0
    return sum(1 for p in images_root.rglob("*") if p.is_file())


def compute_missing_required(
    union_required: set[str], *, images_root: Path = DEFAULT_IMAGE_CACHE_ROOT
) -> list[str]:
    missing: list[str] = []
    for rel in sorted(union_required):
        if not (images_root / Path(rel)).exists():
            missing.append(rel)
    return missing


def _cli() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", default="")
    args = parser.parse_args()

    result = build_required_images_union()
    missing = compute_missing_required(result["union_required"])
    payload = {
        "exhibitions_required_count": result["exhibitions_required_count"],
        "artist_required_count": result["artist_required_count"],
        "union_required_count": result["union_required_count"],
        "derived_images_count": count_images_under_root(),
        "missing_required_count": len(missing),
    }
    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
