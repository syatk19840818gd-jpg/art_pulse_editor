#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

DEFAULT_IMAGES_ROOT = Path("data/phase1_seed10/derived/images")
DEFAULT_EXHIBITIONS_META = [
    Path("data/phase1_seed10/derived/exhibitions_images_frieze_london_2025.jsonl"),
    Path("data/phase1_seed10/derived/exhibitions_images_liste_2025.jsonl"),
]
DEFAULT_ARTIST_META = [
    Path("data/phase1_seed10/derived/artist_works_images_frieze_london.jsonl"),
    Path("data/phase1_seed10/derived/artist_works_images_liste.jsonl"),
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


def _normalize_abs(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").lower().rstrip("/")


def _to_rel_norm(path_str: str, images_root: Path) -> str | None:
    raw = str(path_str or "").strip()
    if not raw:
        return None
    p = Path(raw)
    if p.is_absolute():
        p_abs = p.resolve()
    else:
        p_abs = (Path.cwd() / p).resolve()
    p_norm = _normalize_abs(p_abs)
    root_norm = _normalize_abs(images_root)
    prefix = root_norm + "/"
    if not p_norm.startswith(prefix):
        return None
    return p_norm[len(prefix) :]


def build_required_images_union(
    *,
    exhibitions_meta_paths: list[Path] | None = None,
    artist_meta_paths: list[Path] | None = None,
    images_root: Path = DEFAULT_IMAGES_ROOT,
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
            rel = _to_rel_norm(str(row.get("local_path") or ""), images_root)
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
                rel = _to_rel_norm(str(lp or ""), images_root)
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


def count_images_under_root(images_root: Path = DEFAULT_IMAGES_ROOT) -> int:
    if not images_root.exists():
        return 0
    return sum(1 for p in images_root.rglob("*") if p.is_file())


def compute_missing_required(
    union_required: set[str], *, images_root: Path = DEFAULT_IMAGES_ROOT
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
