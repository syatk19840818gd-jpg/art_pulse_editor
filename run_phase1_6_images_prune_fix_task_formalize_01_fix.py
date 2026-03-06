#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.formal_postflight_gate import run_postflight_gate
from tools.formal_preflight_gate import run_preflight_gate

TASK_ID = "TASK_FORMALIZE_01_FIX"
PHASE1_ROOT = Path("data/phase1_seed10")
DERIVED_IMAGES = PHASE1_ROOT / "derived/images"
POINTER_PATH = PHASE1_ROOT / "FORMAL_CURRENT_POINTER.json"
REPORT_PATH = PHASE1_ROOT / "logs/phase1_6_images_prune_fix_report.md"

EXHIBITIONS_IMAGE_META = [
    PHASE1_ROOT / "derived/exhibitions_images_frieze_london_2025.jsonl",
    PHASE1_ROOT / "derived/exhibitions_images_liste_2025.jsonl",
]
ARTIST_IMAGE_META = [
    PHASE1_ROOT / "derived/artist_works_images_frieze_london.jsonl",
    PHASE1_ROOT / "derived/artist_works_images_liste.jsonl",
]


def utc_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def rel_under_images(path_str: str) -> Path | None:
    if not path_str:
        return None
    p = Path(str(path_str))
    if not p.is_absolute():
        p = (Path.cwd() / p).resolve()
    else:
        p = p.resolve()
    try:
        rel = p.relative_to(DERIVED_IMAGES.resolve())
    except Exception:
        return None
    return rel


def norm_rel(rel: Path) -> str:
    return rel.as_posix().lower()


def gather_required_sets() -> tuple[set[str], set[str], set[str]]:
    ex_required: set[str] = set()
    ar_required: set[str] = set()

    for p in EXHIBITIONS_IMAGE_META:
        for row in read_jsonl(p):
            rel = rel_under_images(str(row.get("local_path") or ""))
            if rel is None:
                continue
            ex_required.add(norm_rel(rel))

    for p in ARTIST_IMAGE_META:
        for row in read_jsonl(p):
            local_paths = row.get("works_image_local_paths") or []
            if not isinstance(local_paths, list):
                continue
            for raw in local_paths:
                rel = rel_under_images(str(raw or ""))
                if rel is None:
                    continue
                ar_required.add(norm_rel(rel))

    return ex_required, ar_required, ex_required | ar_required


def list_existing_image_files() -> list[Path]:
    return [p for p in DERIVED_IMAGES.rglob("*") if p.is_file()]


def compute_missing(required_norm_rel: set[str]) -> list[str]:
    missing: list[str] = []
    for rel_norm in sorted(required_norm_rel):
        full = DERIVED_IMAGES / Path(rel_norm)
        if not full.exists():
            missing.append(rel_norm)
    return missing


def move_with_parents(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))


def write_report(
    *,
    status: str,
    before_file_count: int,
    after_restore_file_count: int,
    after_prune_file_count: int,
    ex_required_count: int,
    ar_required_count: int,
    union_required_count: int,
    missing_before: int,
    missing_after_restore: int,
    missing_after_prune: int,
    moved_back_count: int,
    moved_pruned_count: int,
    restored_from_paths: list[str],
    rollback_path: str,
    adopt_fix_trash_path: str,
    hold_reason: str | None = None,
    missing_examples: list[str] | None = None,
) -> None:
    lines: list[str] = []
    lines.append(f"# {TASK_ID} report")
    lines.append("")
    lines.append(f"- status: {status}")
    lines.append(f"- before_images_count: {before_file_count}")
    lines.append(f"- after_restore_images_count: {after_restore_file_count}")
    lines.append(f"- after_prune_images_count: {after_prune_file_count}")
    lines.append(f"- exhibitions_required_count: {ex_required_count}")
    lines.append(f"- artist_required_count: {ar_required_count}")
    lines.append(f"- union_required_count: {union_required_count}")
    lines.append("")
    lines.append("## Missing")
    lines.append(f"- missing_before: {missing_before}")
    lines.append(f"- missing_after_restore: {missing_after_restore}")
    lines.append(f"- missing_after_prune: {missing_after_prune}")
    if missing_examples:
        lines.append("- missing_examples:")
        for m in missing_examples[:20]:
            lines.append(f"  - {m}")
    lines.append("")
    lines.append("## Move counts")
    lines.append(f"- moved_back_count: {moved_back_count}")
    lines.append(f"- moved_to_adopt_fix_trash_count: {moved_pruned_count}")
    lines.append("")
    lines.append("## Paths")
    lines.append(f"- rollback_path: {rollback_path}")
    lines.append(f"- adopt_fix_trash_path: {adopt_fix_trash_path}")
    lines.append("- restore_sources:")
    for p in restored_from_paths:
        lines.append(f"  - {p}")
    if hold_reason:
        lines.append(f"- hold_reason: {hold_reason}")
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    preflight = run_preflight_gate(context=TASK_ID)
    if preflight["status"] != "PASS":
        write_report(
            status="HOLD",
            before_file_count=0,
            after_restore_file_count=0,
            after_prune_file_count=0,
            ex_required_count=0,
            ar_required_count=0,
            union_required_count=0,
            missing_before=0,
            missing_after_restore=0,
            missing_after_prune=0,
            moved_back_count=0,
            moved_pruned_count=0,
            restored_from_paths=[],
            rollback_path="n/a",
            adopt_fix_trash_path="n/a",
            hold_reason="preflight_gate_failed",
        )
        return 10

    if not POINTER_PATH.exists():
        raise FileNotFoundError(f"Pointer missing: {POINTER_PATH}")
    pointer = json.loads(POINTER_PATH.read_text(encoding="utf-8"))
    rollback_path = pointer.get("rollback_path")
    if not rollback_path:
        raise RuntimeError("rollback_path not found in FORMAL_CURRENT_POINTER.json")
    rollback_root = Path(str(rollback_path))
    if not rollback_root.exists():
        raise FileNotFoundError(f"rollback_path not found: {rollback_root}")

    adopt_fix_trash_root = PHASE1_ROOT / "_trash" / f"ADOPT_FIX_{utc_compact()}"
    images_pruned_dst_root = adopt_fix_trash_root / "images_pruned"
    images_pruned_dst_root.mkdir(parents=True, exist_ok=True)

    before_count = len(list_existing_image_files())
    ex_required, ar_required, union_required = gather_required_sets()
    missing_before_list = compute_missing(union_required)

    # Restore from rollback images_pruned
    restore_sources = [
        p for p in rollback_root.rglob("images_pruned") if p.is_dir()
    ]
    moved_back_count = 0
    for restore_root in restore_sources:
        for src in sorted([p for p in restore_root.rglob("*") if p.is_file()], key=lambda x: str(x)):
            rel = src.relative_to(restore_root)
            dst = DERIVED_IMAGES / rel
            if dst.exists():
                continue
            move_with_parents(src, dst)
            moved_back_count += 1

    after_restore_count = len(list_existing_image_files())
    missing_after_restore_list = compute_missing(union_required)
    if missing_after_restore_list:
        write_report(
            status="HOLD",
            before_file_count=before_count,
            after_restore_file_count=after_restore_count,
            after_prune_file_count=after_restore_count,
            ex_required_count=len(ex_required),
            ar_required_count=len(ar_required),
            union_required_count=len(union_required),
            missing_before=len(missing_before_list),
            missing_after_restore=len(missing_after_restore_list),
            missing_after_prune=len(missing_after_restore_list),
            moved_back_count=moved_back_count,
            moved_pruned_count=0,
            restored_from_paths=[str(p) for p in restore_sources],
            rollback_path=str(rollback_root),
            adopt_fix_trash_path=str(adopt_fix_trash_root),
            hold_reason="missing_required_images_after_restore",
            missing_examples=missing_after_restore_list,
        )
        return 2

    # Re-prune with union required
    required_norm = set(union_required)
    moved_pruned_count = 0
    for file_path in sorted(list_existing_image_files(), key=lambda x: str(x)):
        rel = file_path.relative_to(DERIVED_IMAGES)
        rel_norm = norm_rel(rel)
        if rel_norm in required_norm:
            continue
        dst = images_pruned_dst_root / rel
        move_with_parents(file_path, dst)
        moved_pruned_count += 1

    after_prune_count = len(list_existing_image_files())
    missing_after_prune_list = compute_missing(union_required)
    if missing_after_prune_list:
        write_report(
            status="HOLD",
            before_file_count=before_count,
            after_restore_file_count=after_restore_count,
            after_prune_file_count=after_prune_count,
            ex_required_count=len(ex_required),
            ar_required_count=len(ar_required),
            union_required_count=len(union_required),
            missing_before=len(missing_before_list),
            missing_after_restore=0,
            missing_after_prune=len(missing_after_prune_list),
            moved_back_count=moved_back_count,
            moved_pruned_count=moved_pruned_count,
            restored_from_paths=[str(p) for p in restore_sources],
            rollback_path=str(rollback_root),
            adopt_fix_trash_path=str(adopt_fix_trash_root),
            hold_reason="missing_required_images_after_reprune",
            missing_examples=missing_after_prune_list,
        )
        return 3

    # Pointer update: append fix_note, keep rollback_path
    note = {
        "task_id": TASK_ID,
        "fixed_at": utc_iso(),
        "rollback_path": str(rollback_root),
        "adopt_fix_trash_path": str(adopt_fix_trash_root),
        "counts": {
            "before_images_count": before_count,
            "after_restore_images_count": after_restore_count,
            "after_prune_images_count": after_prune_count,
            "exhibitions_required_count": len(ex_required),
            "artist_required_count": len(ar_required),
            "union_required_count": len(union_required),
            "missing_before": len(missing_before_list),
            "missing_after_restore": 0,
            "missing_after_prune": 0,
            "moved_back_count": moved_back_count,
            "moved_to_adopt_fix_trash_count": moved_pruned_count,
        },
        "restore_sources": [str(p) for p in restore_sources],
    }
    if "fix_notes" not in pointer or not isinstance(pointer["fix_notes"], list):
        pointer["fix_notes"] = []
    pointer["fix_notes"].append(note)
    POINTER_PATH.write_text(json.dumps(pointer, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    postflight = run_postflight_gate(context=TASK_ID)
    if postflight["status"] != "PASS":
        write_report(
            status="HOLD",
            before_file_count=before_count,
            after_restore_file_count=after_restore_count,
            after_prune_file_count=after_prune_count,
            ex_required_count=len(ex_required),
            ar_required_count=len(ar_required),
            union_required_count=len(union_required),
            missing_before=len(missing_before_list),
            missing_after_restore=0,
            missing_after_prune=postflight.get("union_counts", {}).get("missing_required_count", 0),
            moved_back_count=moved_back_count,
            moved_pruned_count=moved_pruned_count,
            restored_from_paths=[str(p) for p in restore_sources],
            rollback_path=str(rollback_root),
            adopt_fix_trash_path=str(adopt_fix_trash_root),
            hold_reason="postflight_gate_failed",
        )
        return 11

    write_report(
        status="SUCCESS",
        before_file_count=before_count,
        after_restore_file_count=after_restore_count,
        after_prune_file_count=after_prune_count,
        ex_required_count=len(ex_required),
        ar_required_count=len(ar_required),
        union_required_count=len(union_required),
        missing_before=len(missing_before_list),
        missing_after_restore=0,
        missing_after_prune=0,
        moved_back_count=moved_back_count,
        moved_pruned_count=moved_pruned_count,
        restored_from_paths=[str(p) for p in restore_sources],
        rollback_path=str(rollback_root),
        adopt_fix_trash_path=str(adopt_fix_trash_root),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
