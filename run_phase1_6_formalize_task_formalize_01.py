#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.formal_postflight_gate import run_postflight_gate
from tools.formal_preflight_gate import run_preflight_gate

TASK_ID = "TASK_FORMALIZE_01"
BUNDLE_PATH = Path("data/phase2/bundles/PHASE2_INPUT_BUNDLE_TASK293_FREEZE01.json")
PHASE1_ROOT = Path("data/phase1_seed10")
RAW_DIR = PHASE1_ROOT / "raw"
DERIVED_DIR = PHASE1_ROOT / "derived"
IMAGES_DIR = DERIVED_DIR / "images"
LOG_PATH = PHASE1_ROOT / "logs/phase1_6_formalize_task_formalize_01_report.md"
POINTER_PATH = PHASE1_ROOT / "FORMAL_CURRENT_POINTER.json"


def utc_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False))
            f.write("\n")


def norm_path(path: Path) -> str:
    return str(path.resolve()).lower()


def parse_path(raw: str) -> Path:
    return Path(str(raw).replace("\\", "/"))


def collect_required_image_paths(exhibitions_image_paths: list[Path]) -> set[Path]:
    required: set[Path] = set()
    for p in exhibitions_image_paths:
        for row in read_jsonl(p):
            local_path = str(row.get("local_path") or "").strip()
            if not local_path:
                continue
            required.add(Path(local_path))
    return required


def compute_missing(required_paths: set[Path]) -> list[Path]:
    missing = [p for p in sorted(required_paths, key=lambda x: str(x)) if not p.exists()]
    return missing


def find_candidate_for_missing(missing_path: Path) -> Path | None:
    filename = missing_path.name
    for base in [PHASE1_ROOT / "_trial", PHASE1_ROOT / "_trash"]:
        if not base.exists():
            continue
        candidates = list(base.rglob(filename))
        if not candidates:
            continue
        # Deterministic pick: shortest path then lexicographic.
        candidates = sorted(candidates, key=lambda p: (len(str(p)), str(p)))
        return candidates[0]
    return None


def move_with_parents(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))


def split_by_fair(source_jsonl: Path, stage_dir: Path, stem_prefix: str) -> dict[str, Path]:
    rows = read_jsonl(source_jsonl)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        fair = str(row.get("fair_slug") or "").strip()
        grouped[fair].append(row)
    out: dict[str, Path] = {}
    for fair in ["frieze_london", "liste"]:
        fair_rows = grouped.get(fair, [])
        if not fair_rows:
            raise RuntimeError(f"{source_jsonl} has no rows for fair={fair}")
        dst = stage_dir / f"{stem_prefix}_{fair}_2025.jsonl"
        write_jsonl(dst, fair_rows)
        out[fair] = dst
    return out


def write_report(
    *,
    status: str,
    summary_lines: list[str],
    replaced_rows: list[dict[str, str]],
    missing_before: int,
    missing_after: int,
    prune_kept: int,
    prune_moved: int,
    prune_missing: int,
    rollback_path: Path | None,
    hold_reason: str | None = None,
    missing_examples: list[str] | None = None,
) -> None:
    lines: list[str] = []
    lines.append(f"# {TASK_ID} report")
    lines.append("")
    lines.extend([f"- {line}" for line in summary_lines[:5]])
    lines.append("")
    lines.append("## Replaced formal paths")
    if replaced_rows:
        for row in replaced_rows:
            lines.append(f"- {row['dst']}: {row['before']} -> {row['after']}")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Missing check")
    lines.append(f"- before: {missing_before}")
    lines.append(f"- after: {missing_after}")
    if missing_examples:
        lines.append("- examples:")
        for ex in missing_examples[:10]:
            lines.append(f"  - {ex}")
    lines.append("")
    lines.append("## Images prune")
    lines.append(f"- kept_count: {prune_kept}")
    lines.append(f"- moved_to_trash_count: {prune_moved}")
    lines.append(f"- missing_required_count: {prune_missing}")
    lines.append("")
    lines.append(f"- rollback_path: {rollback_path if rollback_path else 'n/a'}")
    if hold_reason:
        lines.append(f"- hold_reason: {hold_reason}")
    lines.append(f"- status: {status}")
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    preflight = run_preflight_gate(context=TASK_ID)
    if preflight["status"] != "PASS":
        write_report(
            status="HOLD",
            summary_lines=[
                "Preflight gate failed.",
                f"context={TASK_ID}",
                f"hold_reasons={len(preflight.get('hold_reasons', []))}",
                "formalize aborted before any replace/prune",
                "see formal_gate_preflight_report.md",
            ],
            replaced_rows=[],
            missing_before=0,
            missing_after=0,
            prune_kept=0,
            prune_moved=0,
            prune_missing=0,
            rollback_path=None,
            hold_reason="preflight_gate_failed",
        )
        return 10

    if not BUNDLE_PATH.exists():
        raise FileNotFoundError(f"Bundle not found: {BUNDLE_PATH}")
    bundle = json.loads(BUNDLE_PATH.read_text(encoding="utf-8"))

    run_ts = utc_compact()
    adopt_trash_root = PHASE1_ROOT / "_trash" / f"ADOPT_{run_ts}"
    stage_dir = PHASE1_ROOT / "_trial" / bundle["run_id"] / "formalize_stage" / run_ts
    stage_dir.mkdir(parents=True, exist_ok=True)

    # F0: target truth paths from bundle
    artist_text_truth = parse_path(bundle["artist_rag_truth"]["artist_text_truth"]["path"])
    artist_images_truth = parse_path(bundle["artist_rag_truth"]["artist_works_images_truth"]["path"])
    exhibitions_text_truth = parse_path(bundle["exhibitions_text_truth"]["path"])
    exhibitions_image_truth_paths = [parse_path(x["path"]) for x in bundle.get("exhibitions_image_truth", [])]

    required_images = collect_required_image_paths(exhibitions_image_truth_paths)
    missing_before_list = compute_missing(required_images)
    missing_before = len(missing_before_list)

    # F1: fill missing (move only) from _trial/_trash
    recovered: list[dict[str, str]] = []
    unresolved: list[Path] = []
    if missing_before_list:
        for miss in missing_before_list:
            found = find_candidate_for_missing(miss)
            if found is None:
                unresolved.append(miss)
                continue
            move_with_parents(found, miss)
            recovered.append({"from": str(found), "to": str(miss)})

    missing_after_list = compute_missing(required_images)
    missing_after = len(missing_after_list)
    if missing_after > 0:
        write_report(
            status="HOLD",
            summary_lines=[
                "Missing required images remain after F1 recovery.",
                f"bundle={bundle.get('bundle_id')}",
                f"missing_before={missing_before}",
                f"missing_after={missing_after}",
                "adoption skipped",
            ],
            replaced_rows=[],
            missing_before=missing_before,
            missing_after=missing_after,
            prune_kept=0,
            prune_moved=0,
            prune_missing=missing_after,
            rollback_path=adopt_trash_root,
            hold_reason="missing_required_images_not_zero_after_fill_missing",
            missing_examples=[str(p) for p in missing_after_list[:20]],
        )
        return 2

    # F2: prepare split sources (integrated trial truth -> fair files)
    artist_text_split = split_by_fair(artist_text_truth, stage_dir, "artists")
    artist_images_split = split_by_fair(artist_images_truth, stage_dir, "artist_works_images")
    exhibitions_text_split = split_by_fair(exhibitions_text_truth, stage_dir, "exhibitions")

    replace_specs = [
        {"src": artist_text_split["frieze_london"], "dst": RAW_DIR / "artists_frieze_london_2025.jsonl"},
        {"src": artist_text_split["liste"], "dst": RAW_DIR / "artists_liste_2025.jsonl"},
        {"src": artist_images_split["frieze_london"], "dst": DERIVED_DIR / "artist_works_images_frieze_london.jsonl"},
        {"src": artist_images_split["liste"], "dst": DERIVED_DIR / "artist_works_images_liste.jsonl"},
        {"src": exhibitions_text_split["frieze_london"], "dst": RAW_DIR / "exhibitions_frieze_london_2025.jsonl"},
        {"src": exhibitions_text_split["liste"], "dst": RAW_DIR / "exhibitions_liste_2025.jsonl"},
    ]

    adopt_trash_root.mkdir(parents=True, exist_ok=True)
    replaced_rows: list[dict[str, str]] = []
    adopted_files: list[dict[str, str]] = []
    for spec in replace_specs:
        src = spec["src"]
        dst = spec["dst"]
        if not src.exists():
            raise FileNotFoundError(f"adopt source missing: {src}")
        before_ref = "none"
        if dst.exists():
            trash_dst = adopt_trash_root / "formal_backup" / dst.relative_to(PHASE1_ROOT)
            move_with_parents(dst, trash_dst)
            before_ref = str(trash_dst)
        move_with_parents(src, dst)
        sha = sha256_file(dst)
        adopted_files.append({"path": str(dst), "sha256": sha})
        replaced_rows.append({"dst": str(dst), "before": before_ref, "after": str(dst)})

    # F3: prune derived/images to required-only set (move extras to trash)
    required_norm = {norm_path(p) for p in required_images}
    kept_count = 0
    moved_count = 0
    images_pruned_root = adopt_trash_root / "images_pruned"
    for file_path in IMAGES_DIR.rglob("*"):
        if not file_path.is_file():
            continue
        if norm_path(file_path) in required_norm:
            kept_count += 1
            continue
        rel = file_path.relative_to(IMAGES_DIR)
        trash_dst = images_pruned_root / rel
        move_with_parents(file_path, trash_dst)
        moved_count += 1

    missing_after_prune_list = compute_missing(required_images)
    missing_after_prune = len(missing_after_prune_list)
    if missing_after_prune > 0:
        write_report(
            status="HOLD",
            summary_lines=[
                "Missing required images detected after prune.",
                f"bundle={bundle.get('bundle_id')}",
                f"missing_before={missing_before}",
                f"missing_after_prune={missing_after_prune}",
                "adoption completed but pointer not finalized",
            ],
            replaced_rows=replaced_rows,
            missing_before=missing_before,
            missing_after=missing_after_prune,
            prune_kept=kept_count,
            prune_moved=moved_count,
            prune_missing=missing_after_prune,
            rollback_path=adopt_trash_root,
            hold_reason="missing_required_images_after_prune",
            missing_examples=[str(p) for p in missing_after_prune_list[:20]],
        )
        return 3

    # F4: write formal pointer
    for p in exhibitions_image_truth_paths:
        adopted_files.append({"path": str(p), "sha256": sha256_file(p)})

    pointer = {
        "pointer_version": 1,
        "adopted_at": utc_iso(),
        "task_id": TASK_ID,
        "source_bundle": {
            "bundle_id": bundle.get("bundle_id"),
            "path": str(BUNDLE_PATH),
            "run_id": bundle.get("run_id"),
            "scope_hash": bundle.get("scope_hash"),
        },
        "adopted_files": adopted_files,
        "images_prune": {
            "kept_count": kept_count,
            "moved_to_trash_count": moved_count,
            "missing_required_count": 0,
        },
        "rollback_path": str(adopt_trash_root),
    }
    POINTER_PATH.write_text(json.dumps(pointer, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    postflight = run_postflight_gate(context=TASK_ID)
    if postflight["status"] != "PASS":
        write_report(
            status="HOLD",
            summary_lines=[
                "Postflight gate failed.",
                f"context={TASK_ID}",
                f"hold_reasons={len(postflight.get('hold_reasons', []))}",
                "pointer written but operation must be treated as HOLD",
                "see formal_gate_postflight_report.md",
            ],
            replaced_rows=replaced_rows,
            missing_before=missing_before,
            missing_after=0,
            prune_kept=kept_count,
            prune_moved=moved_count,
            prune_missing=postflight.get("union_counts", {}).get("missing_required_count", 0),
            rollback_path=adopt_trash_root,
            hold_reason="postflight_gate_failed",
        )
        return 11

    write_report(
        status="SUCCESS",
        summary_lines=[
            "Phase1.6 formal one-folder adoption completed.",
            f"bundle={bundle.get('bundle_id')}",
            f"replaced_files={len(replace_specs)}",
            f"missing_before={missing_before}, missing_after=0",
            f"images_prune kept={kept_count}, moved={moved_count}",
        ],
        replaced_rows=replaced_rows,
        missing_before=missing_before,
        missing_after=0,
        prune_kept=kept_count,
        prune_moved=moved_count,
        prune_missing=0,
        rollback_path=adopt_trash_root,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
