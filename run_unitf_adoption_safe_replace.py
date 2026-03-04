#!/usr/bin/env python3
"""
Unit-F adoption safe-replace executor.

Scope:
- Unit-F only (Athr / The Approach)
- Adoption-layer only (no collector / guard / trial extraction logic changes)

Key fixes introduced in TASK173:
1) Delete-phase path protection:
   - Compute adopted local_path set first.
   - Delete only old Unit-F files that are NOT referenced after adoption.
2) non-Unit-F comparison:
   - Replace raw-line comparison with keyed semantic comparison.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


UNIT_F_GALLERIES = {"Athr", "The Approach"}


@dataclass
class Paths:
    repo_root: Path
    runtime_csv: Path
    summary_json: Path
    qa_manifest_json: Path
    formal_jsonl: Path
    formal_img_dir: Path
    trial_jsonl: Path
    trash_root: Path


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False))
            f.write("\n")


def _read_runtime(runtime_csv: Path) -> list[dict[str, str]]:
    with runtime_csv.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _is_unitf_scope_row(row: dict[str, Any], seed_url_set: set[str]) -> bool:
    return (
        row.get("gallery_name_en") in UNIT_F_GALLERIES
        and row.get("source_url") in seed_url_set
    )


def _semantic_key_non_unitf(row: dict[str, Any]) -> tuple[Any, ...]:
    # Keyed semantic comparator (order-insensitive, field-focused)
    return (
        row.get("target_year"),
        row.get("fair_slug"),
        row.get("gallery_name_en"),
        row.get("source_url"),
        row.get("seed_source_url"),
        row.get("seed_url_type"),
        row.get("image_url"),
        row.get("image_url_hash"),
        row.get("payload_hash"),
        row.get("r2_key"),
        row.get("local_path"),
        row.get("selected_reason"),
        row.get("candidate_year"),
    )


def _to_formal_abs(repo_root: Path, row: dict[str, Any]) -> Path:
    r2_key = (row.get("r2_key") or "").strip()
    if r2_key:
        return repo_root / Path(r2_key.replace("/", "\\"))
    local = (row.get("local_path") or "").strip()
    if local:
        return Path(local)
    return Path()


def _safe_copy(src: Path, dst: Path) -> bool:
    """
    Copy file unless source and destination are the same path.

    Returns:
    - True when copy executed
    - False when skipped as same-file no-op
    """
    src_r = src.resolve()
    dst_r = dst.resolve()
    if src_r == dst_r:
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def _materialize_adoption_rows(
    runtime_rows: list[dict[str, str]],
    scoped_trial_rows: list[dict[str, Any]],
    scoped_formal_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    trial_by_key = {
        (r.get("gallery_name_en"), r.get("source_url")): r for r in scoped_trial_rows
    }
    formal_by_key = {
        (r.get("gallery_name_en"), r.get("source_url")): r for r in scoped_formal_rows
    }
    out_rows: list[dict[str, Any]] = []
    row_sources: list[dict[str, str]] = []
    for seed in runtime_rows:
        key = (seed.get("gallery_name_en"), seed.get("source_url"))
        chosen = trial_by_key.get(key)
        source = "trial"
        if chosen is None:
            chosen = formal_by_key.get(key)
            source = "formal_fallback"
        if chosen is None:
            raise RuntimeError(f"missing candidate row for key={key}")
        # Deep copy via json to avoid mutating origin rows.
        out_rows.append(json.loads(json.dumps(chosen, ensure_ascii=False)))
        row_sources.append(
            {
                "gallery_name_en": seed.get("gallery_name_en", ""),
                "source_url": seed.get("source_url", ""),
                "row_source": source,
            }
        )
    return out_rows, row_sources


def _gate_check(
    runtime_rows: list[dict[str, str]],
    summary: dict[str, Any],
    qa_manifest: dict[str, Any],
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    run_ids = sorted({r.get("run_id", "") for r in runtime_rows if r.get("run_id")})
    seed_urls = sorted({r.get("source_url", "") for r in runtime_rows if r.get("source_url")})
    out_of_scope = [r for r in runtime_rows if r.get("gallery_name_en") not in UNIT_F_GALLERIES]

    if qa_manifest.get("qa_result") != "pass":
        errors.append("qa_result_not_pass")
    if qa_manifest.get("adoption_eligibility") != "eligible":
        errors.append("adoption_eligibility_not_eligible")
    if int(summary.get("seed_exhibition_count", -1)) != 8:
        errors.append("seed_count_not_8")
    if int(summary.get("failed_case_count", -1)) != 0:
        errors.append("failed_case_not_0")
    if len(run_ids) != 1:
        errors.append("runtime_run_id_not_single")
    if run_ids and run_ids[0] != qa_manifest.get("run_id"):
        errors.append("runtime_run_id_mismatch_qa")
    if len(seed_urls) != 8:
        errors.append("runtime_source_url_count_not_8")
    if out_of_scope:
        errors.append("runtime_has_out_of_scope_gallery")
    return (len(errors) == 0, errors)


def _non_unitf_unchanged_keyed(
    pre_non_unitf_rows: list[dict[str, Any]],
    post_non_unitf_rows: list[dict[str, Any]],
) -> bool:
    pre_counter = Counter(_semantic_key_non_unitf(r) for r in pre_non_unitf_rows)
    post_counter = Counter(_semantic_key_non_unitf(r) for r in post_non_unitf_rows)
    return pre_counter == post_counter


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Unit-F adoption safe-replace (TASK173-fixed)")
    p.add_argument("--repo-root", default=".")
    p.add_argument(
        "--runtime-csv",
        default="data/gallery_lists/reextract_targets_exhibitions_image_task_t164_unitf_trial_runtime.csv",
    )
    p.add_argument(
        "--summary-json",
        default="data/phase1_seed10/logs/phase1_seed10_exhibition_image_collect_summary_task_t169_unitf_rerun.json",
    )
    p.add_argument(
        "--qa-manifest-json",
        default="data/phase1_seed10/logs/exhibitions_image_task_t164_unitf_trial_qa_manifest.json",
    )
    p.add_argument(
        "--formal-jsonl",
        default="data/phase1_seed10/derived/exhibitions_images_frieze_london_2025.jsonl",
    )
    p.add_argument(
        "--formal-img-dir",
        default="data/phase1_seed10/derived/images/exhibition_works_images/2025/frieze-london",
    )
    p.add_argument(
        "--trial-jsonl",
        default="_trial/task153_revised_run_20260303_191622/data/phase1_seed10/derived/exhibitions_images_frieze_london_2025.jsonl",
    )
    p.add_argument("--trash-root", default="_trash")
    p.add_argument(
        "--result-json",
        default="data/phase1_seed10/logs/exhibitions_image_task_t173_unitf_adoption_fix_result.json",
    )
    p.add_argument(
        "--result-md",
        default="data/phase1_seed10/logs/exhibitions_image_task_t173_unitf_adoption_fix_result.md",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Only validate and print plan. No file mutation.",
    )
    p.add_argument(
        "--execute",
        action="store_true",
        help="Run safe-replace and rollback-capable post QA.",
    )
    return p


def main() -> int:
    args = build_parser().parse_args()
    repo = Path(args.repo_root).resolve()
    paths = Paths(
        repo_root=repo,
        runtime_csv=(repo / args.runtime_csv).resolve(),
        summary_json=(repo / args.summary_json).resolve(),
        qa_manifest_json=(repo / args.qa_manifest_json).resolve(),
        formal_jsonl=(repo / args.formal_jsonl).resolve(),
        formal_img_dir=(repo / args.formal_img_dir).resolve(),
        trial_jsonl=(repo / args.trial_jsonl).resolve(),
        trash_root=(repo / args.trash_root).resolve(),
    )
    result_json_path = (repo / args.result_json).resolve()
    result_md_path = (repo / args.result_md).resolve()

    runtime_rows = _read_runtime(paths.runtime_csv)
    summary = _read_json(paths.summary_json)
    qa_manifest = _read_json(paths.qa_manifest_json)
    ok, gate_errors = _gate_check(runtime_rows, summary, qa_manifest)
    if not ok:
        raise RuntimeError(f"pre-adoption gate failed: {','.join(gate_errors)}")

    seed_urls = {r["source_url"] for r in runtime_rows}
    formal_rows = _read_jsonl(paths.formal_jsonl)
    trial_rows = _read_jsonl(paths.trial_jsonl)
    scoped_formal = [r for r in formal_rows if _is_unitf_scope_row(r, seed_urls)]
    non_scoped_formal = [r for r in formal_rows if not _is_unitf_scope_row(r, seed_urls)]
    scoped_trial = [r for r in trial_rows if _is_unitf_scope_row(r, seed_urls)]

    if len(scoped_formal) != 8:
        raise RuntimeError(f"unexpected scoped formal rows: {len(scoped_formal)} != 8")
    if len(scoped_trial) != 8:
        raise RuntimeError(f"unexpected scoped trial rows: {len(scoped_trial)} != 8")

    adoption_rows, row_sources = _materialize_adoption_rows(
        runtime_rows, scoped_trial, scoped_formal
    )

    # Build adopted path set first (TASK173 fix: delete-phase protection).
    adopted_paths: set[Path] = set()
    for row in adoption_rows:
        abs_path = _to_formal_abs(paths.repo_root, row)
        if not abs_path:
            raise RuntimeError("adoption row missing both r2_key and local_path")
        # Normalize row local_path to formal absolute path.
        row["local_path"] = str(abs_path)
        adopted_paths.add(abs_path)

    old_scoped_paths = {
        Path(r["local_path"])
        for r in scoped_formal
        if (r.get("local_path") and Path(r["local_path"]).exists())
    }
    non_scoped_paths = {
        Path(r["local_path"])
        for r in non_scoped_formal
        if (r.get("local_path") and Path(r["local_path"]).exists())
    }
    # Delete target is strictly limited: old Unit-F and not referenced after adoption.
    delete_targets = sorted(p for p in old_scoped_paths if p not in adopted_paths and p not in non_scoped_paths)

    if args.dry_run:
        print("DRY_RUN_OK")
        print(f"run_id={qa_manifest.get('run_id')}")
        print(f"scoped_formal={len(scoped_formal)} scoped_trial={len(scoped_trial)} adoption_rows={len(adoption_rows)}")
        print(f"adopted_paths={len(adopted_paths)} old_scoped_paths={len(old_scoped_paths)} delete_targets={len(delete_targets)}")
        print("row_source_breakdown=" + json.dumps(Counter(r["row_source"] for r in row_sources), ensure_ascii=False))
        # Keyed non-unitf check planning baseline.
        print(f"non_unitf_semantic_keys={len(Counter(_semantic_key_non_unitf(r) for r in non_scoped_formal))}")
        return 0

    if not args.execute:
        raise RuntimeError("Specify either --dry-run or --execute")

    run_id = str(qa_manifest.get("run_id"))
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    trash_dir = paths.trash_root / f"{ts}_pre_adopt_unitf_{run_id}"
    trash_snap_dir = trash_dir / "snapshots"
    trash_img_dir = trash_dir / "formal_unitf_images"
    trash_snap_dir.mkdir(parents=True, exist_ok=True)
    trash_img_dir.mkdir(parents=True, exist_ok=True)

    manifest_rows: list[dict[str, Any]] = []
    def add_manifest(src: Path, dst: Path, item_type: str, note: str) -> None:
        manifest_rows.append(
            {
                "source_path": str(src),
                "backup_path": str(dst),
                "item_type": item_type,
                "note": note,
            }
        )

    # Backups
    full_snap = trash_snap_dir / "exhibitions_images_frieze_london_2025.full.jsonl"
    shutil.copy2(paths.formal_jsonl, full_snap)
    add_manifest(paths.formal_jsonl, full_snap, "full_jsonl_snapshot", "formal full snapshot")

    scoped_snap = trash_snap_dir / "exhibitions_images_frieze_london_2025.unitf_scoped_rows.jsonl"
    _write_jsonl(scoped_snap, scoped_formal)
    add_manifest(paths.formal_jsonl, scoped_snap, "scoped_jsonl_snapshot", "unitf scoped snapshot")

    for p, n in [
        (paths.runtime_csv, "runtime_csv_snapshot"),
        (paths.summary_json, "summary_snapshot"),
        (paths.qa_manifest_json, "qa_manifest_snapshot"),
    ]:
        dst = trash_snap_dir / p.name
        shutil.copy2(p, dst)
        add_manifest(p, dst, "input_snapshot", n)

    for img in sorted(old_scoped_paths):
        dst = trash_img_dir / img.name
        shutil.copy2(img, dst)
        add_manifest(img, dst, "scoped_image_backup", "old unitf image")

    # Copy adopted images and normalize local_path.
    row_source_by_key = {
        (r["gallery_name_en"], r["source_url"]): r["row_source"] for r in row_sources
    }
    copied_trial_count = 0
    for row in adoption_rows:
        key = (row.get("gallery_name_en"), row.get("source_url"))
        row_source = row_source_by_key.get(key, "unknown")
        dst_abs = _to_formal_abs(paths.repo_root, row)
        if not dst_abs:
            raise RuntimeError(f"adoption row path unresolved: key={key}")

        if row_source == "trial":
            src = Path(str(row.get("local_path", "")))
            if not src.exists():
                raise RuntimeError(f"trial image missing: {src}")
            if _safe_copy(src, dst_abs):
                copied_trial_count += 1
        else:
            # Formal fallback: ensure destination exists.
            if not dst_abs.exists():
                src = Path(str(row.get("local_path", "")))
                if src.exists():
                    _safe_copy(src, dst_abs)
        row["local_path"] = str(dst_abs)

    # TASK173 fix: delete only stale old Unit-F paths not used after adoption.
    deleted_count = 0
    for p in delete_targets:
        if p.exists():
            p.unlink()
            deleted_count += 1

    # Rebuild formal jsonl with scoped replacement only.
    rebuilt_rows = non_scoped_formal + adoption_rows
    _write_jsonl(paths.formal_jsonl, rebuilt_rows)

    # Post-adoption QA (keyed non-unitf comparison)
    post_rows = _read_jsonl(paths.formal_jsonl)
    scoped_post = [r for r in post_rows if _is_unitf_scope_row(r, seed_urls)]
    post_non_scoped = [r for r in post_rows if not _is_unitf_scope_row(r, seed_urls)]
    athr_count = sum(1 for r in scoped_post if r.get("gallery_name_en") == "Athr")
    approach_count = sum(1 for r in scoped_post if r.get("gallery_name_en") == "The Approach")
    wrong_fair = sum(1 for r in scoped_post if r.get("fair_slug") != "frieze_london")
    wrong_year = sum(
        1
        for r in scoped_post
        if ((r.get("target_year") is not None and int(r.get("target_year")) != 2025) or "/20" in str(r.get("source_url", "")) and any(y in str(r.get("source_url", "")) for y in ["/2020/", "/2021/", "/2022/", "/2023/", "/2024/"]))
    )
    non_exhibition_route = sum(
        1
        for r in scoped_post
        if any(t in str(r.get("source_url", "")) for t in ["/artists/", "/books", "/book-", "/viewing-room", "/art-fairs/"])
    )
    obvious_logo_icon = sum(
        1
        for r in scoped_post
        if any(t in (str(r.get("image_url", "")) + " " + str(r.get("r2_key", "")) + " " + str(r.get("local_path", ""))).lower() for t in ["logo", "icon", "favicon", "sprite"])
    )
    dup_payload = sum(1 for _, c in Counter(str(r.get("payload_hash", "")) for r in scoped_post if r.get("payload_hash")).items() if c > 1)
    required_field_missing = sum(
        1
        for r in scoped_post
        if not r.get("fair_slug")
        or not r.get("gallery_name_en")
        or not r.get("source_url")
        or not r.get("selected_reason")
        or not r.get("local_path")
    )
    missing_local_path = sum(1 for r in scoped_post if not Path(str(r.get("local_path", ""))).exists())
    non_unitf_unchanged = _non_unitf_unchanged_keyed(non_scoped_formal, post_non_scoped)

    qa_pass = (
        athr_count == 5
        and approach_count == 3
        and wrong_fair == 0
        and wrong_year == 0
        and non_exhibition_route == 0
        and obvious_logo_icon == 0
        and dup_payload == 0
        and required_field_missing == 0
        and missing_local_path == 0
        and non_unitf_unchanged
    )

    rollback_result = "not_required"
    final_verdict = "A"
    if not qa_pass:
        rollback_result = "started"
        shutil.copy2(full_snap, paths.formal_jsonl)
        # restore old Unit-F files
        for f in trash_img_dir.glob("*"):
            _safe_copy(f, paths.formal_img_dir / f.name)
        rollback_result = "completed"
        final_verdict = "B"

    manifest_path = trash_dir / "trash_manifest_task173.csv"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["source_path", "backup_path", "item_type", "note"])
        w.writeheader()
        w.writerows(manifest_rows)

    result = {
        "adopted_run_id": run_id,
        "delete_phase_fix_enabled": True,
        "non_unitf_compare_mode": "keyed_semantic",
        "pre_adoption_gate": "pass",
        "replace_result": {
            "scoped_formal_rows": len(scoped_formal),
            "scoped_trial_rows": len(scoped_trial),
            "adoption_rows": len(adoption_rows),
            "copied_trial_rows": copied_trial_count,
            "delete_target_count": len(delete_targets),
            "deleted_count": deleted_count,
        },
        "post_adoption_qa": {
            "athr_expected_vs_actual": f"5={athr_count}",
            "the_approach_expected_vs_actual": f"3={approach_count}",
            "wrong_fair": wrong_fair,
            "wrong_year": wrong_year,
            "non_exhibition_route": non_exhibition_route,
            "obvious_logo_icon": obvious_logo_icon,
            "duplicate_payload": dup_payload,
            "required_field_missing": required_field_missing,
            "missing_local_path": missing_local_path,
            "non_unitf_unchanged": non_unitf_unchanged,
        },
        "final_verdict": final_verdict,
        "rollback_result": rollback_result,
        "generated_paths": {
            "trash_dir": str(trash_dir),
            "trash_manifest": str(manifest_path),
            "formal_jsonl": str(paths.formal_jsonl),
        },
    }
    result_json_path.parent.mkdir(parents=True, exist_ok=True)
    result_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Unit-F Adoption Safe-Replace Execution Result",
        "",
        f"- adopted_run_id: {run_id}",
        f"- delete_phase_fix_enabled: {True}",
        f"- non_unitf_compare_mode: keyed_semantic",
        f"- pre_adoption_gate: pass",
        f"- final_verdict: {final_verdict}",
        f"- rollback_result: {rollback_result}",
        f"- result_json: {result_json_path}",
    ]
    result_md_path.parent.mkdir(parents=True, exist_ok=True)
    result_md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print(f"EXECUTE_DONE verdict={final_verdict} result_json={result_json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
