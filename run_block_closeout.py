#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from closeout_breakdown_contract import (
    BLOCK_ARTIFACT_CATEGORY_ARTIST,
    BLOCK_ARTIFACT_CATEGORY_ARTIST_WORKS_IMAGES,
    BLOCK_ARTIFACT_CATEGORY_EXHIBITION,
    CURRENT_FORMAL_ARTIFACTS_ROOT,
    CurrentFormalArtifactBundle,
    CurrentFormalArtifactGroup,
    execute_closeout_with_breakdown_contract,
    resolve_current_formal_artifact_bundle,
)
from phase2_art_pulse_config import (
    TARGET_YEAR,
    get_current_artist_image_meta_paths,
    get_current_artist_text_vector_runtime_paths,
    get_current_artist_works_vector_runtime_paths,
    get_current_exhibitions_image_meta_paths,
    get_current_raw_paths,
    get_enrichment_current_output_path,
    get_enrichment_current_summary_path,
)
from run_closeout_new10_artists_from_trial import (
    build_enrichment_summary,
    build_image_vector_manifest,
    build_image_vector_summary,
    build_source_scope_maps,
    build_text_vector_manifest,
    build_text_vector_summary,
    extract_trial_enrichment_source,
    merge_image_vector_state,
    merge_jsonl_rows_by_scope,
    merge_text_vector_state,
    read_json,
    read_jsonl,
    resolve_enrichment_scope_key,
    write_json_atomic,
    write_jsonl_atomic,
    write_npy_atomic,
)
from run_rag_gallery_breakdown_update import (
    DEFAULT_XLSX_PATH,
    ScopeTarget,
    build_stats,
    load_targets_ordered,
)

DEFAULT_RUN_ID_PREFIX = "TASK_PHASE3_BLOCK_CLOSEOUT"
DEFAULT_PLAN_ROOT_DIR = Path("_trial")
BLOCK_CLOSEOUT_FLOW = [
    "current_write",
    "exhibition_images_current",
    "skip_registry_gallery_list_cleanup",
    "xlsx_update",
    "r2_sync",
    "artist_works_images_openclip_current",
    "closeout_report",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def utc_now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_path(path_text: str | Path) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return (Path.cwd() / path).resolve()


def resolve_optional_path(path_text: str | Path | None) -> Path | None:
    raw = str(path_text or "").strip()
    if not raw:
        return None
    return resolve_path(raw)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Unified block closeout runner. Resolve the block scope from a targets CSV, "
            "then orchestrate current verification, bounded current/trial merge planning, "
            "xlsx update, Artist Works Images OpenCLIP current check, R2 sync, and one closeout report. "
            "Verify-first dry-run is the default; live R2/apply requires explicit approval."
        )
    )
    parser.add_argument("--targets-file", required=True, help="gallery scope CSV for this block")
    parser.add_argument(
        "--xlsx-path",
        default=str(DEFAULT_XLSX_PATH),
        help=f"xlsx path (default: {DEFAULT_XLSX_PATH})",
    )
    parser.add_argument("--target-year", type=int, default=TARGET_YEAR, help=f"default: {TARGET_YEAR}")
    parser.add_argument(
        "--run-id",
        default="",
        help=f"run_id for block closeout report (default: {DEFAULT_RUN_ID_PREFIX}_<UTCSTAMP>)",
    )
    parser.add_argument(
        "--artists-enrichment-trial-root",
        default="",
        help="optional trial root for artist enrichment output/summary to be bounded-merged into current",
    )
    parser.add_argument(
        "--artists-text-vector-trial-root",
        default="",
        help="optional trial root for artist text vector artifacts to be bounded-merged into current",
    )
    parser.add_argument(
        "--artist-works-images-vector-trial-root",
        "--artist-image-vector-trial-root",
        default="",
        help="optional trial root for Artist Works Images OpenCLIP artifacts to be bounded-merged into current",
    )
    parser.add_argument(
        "--exhibitions-raw-trial-root",
        default="",
        help="optional trial root for exhibition raw artifacts to be bounded-merged into current by scope",
    )
    parser.add_argument(
        "--plan-root",
        default="",
        help="optional staging root for verify-first planned current artifacts; default: _trial/<run_id>",
    )
    parser.add_argument(
        "--r2-live-plan",
        action="store_true",
        help="run remote R2 plan during dry-run; default is contract-only dry-run with no remote access",
    )
    parser.add_argument(
        "--no-r2-remote",
        action="store_true",
        help="disable remote R2 plan/apply execution even when --apply is set",
    )
    parser.add_argument(
        "--approval-token",
        default="",
        help="required for --r2-live-plan or --apply; verify-first dry-run remains available without approval",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "execute the full block closeout contract against current source of truth: "
            "current write stage, xlsx update, required R2 sync, and closeout report"
        ),
    )
    return parser.parse_args(argv)


def require_live_closeout_approval(args: argparse.Namespace) -> None:
    if not (args.apply or args.r2_live_plan):
        return
    if str(args.approval_token or "").strip():
        return
    raise RuntimeError(
        "approval_required_for_live_block_closeout:"
        "pass --approval-token <user-approved-note>; offline verify-first remains available without --apply/--r2-live-plan"
    )


def count_target_rows(path: Path, target_scope_keys: set[tuple[str, str]]) -> int:
    if not path.exists():
        return 0
    count = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            fair_slug = str(row.get("fair_slug") or "").strip().lower().replace("-", "_")
            gallery_name = str(row.get("gallery_name_en") or "").strip()
            if not fair_slug or not gallery_name:
                continue
            scope_key = ScopeTarget(fair_slug=fair_slug, gallery_name_en=gallery_name).scope_key
            if scope_key in target_scope_keys:
                count += 1
    return count


def build_resolved_current_source_paths(target_year: int) -> dict[str, dict[str, Any]]:
    return {
        "artist": {
            "raw": dict(get_current_raw_paths("artists", target_year)),
            "image_metadata": dict(get_current_artist_image_meta_paths()),
            "enrichment_output": get_enrichment_current_output_path("artists", target_year),
            "enrichment_summary": get_enrichment_current_summary_path("artists", target_year),
            "text_vector": {
                key: value
                for key, value in get_current_artist_text_vector_runtime_paths(target_year=target_year).items()
                if key != "manifest_r2_prefix"
            },
        },
        "artist_works_images": {
            key: value
            for key, value in get_current_artist_works_vector_runtime_paths(target_year=target_year).items()
            if key != "manifest_r2_prefix"
        },
        "exhibition": {
            "raw": dict(get_current_raw_paths("exhibitions", target_year)),
            "image_metadata": dict(get_current_exhibitions_image_meta_paths(target_year)),
            "enrichment_output": get_enrichment_current_output_path("exhibitions", target_year),
            "enrichment_summary": get_enrichment_current_summary_path("exhibitions", target_year),
        },
    }


def stringify_paths(payload: Any) -> Any:
    if isinstance(payload, Path):
        return payload.as_posix()
    if isinstance(payload, dict):
        return {str(key): stringify_paths(value) for key, value in payload.items()}
    if isinstance(payload, list):
        return [stringify_paths(item) for item in payload]
    return payload


def build_scope_counts_from_paths(
    *,
    source_paths: dict[str, dict[str, Any]],
    target_scope_keys: set[tuple[str, str]],
) -> dict[str, dict[str, int]]:
    return {
        "artist": {
            "raw_rows_total": sum(count_target_rows(path, target_scope_keys) for path in source_paths["artist"]["raw"].values()),
            "image_metadata_rows_total": sum(
                count_target_rows(path, target_scope_keys) for path in source_paths["artist"]["image_metadata"].values()
            ),
            "enrichment_output_rows_total": count_target_rows(
                Path(source_paths["artist"]["enrichment_output"]),
                target_scope_keys,
            ),
            "text_vector_rows_total": count_target_rows(
                Path(source_paths["artist"]["text_vector"]["meta"]),
                target_scope_keys,
            ),
        },
        "artist_works_images": {
            "vector_rows_total": count_target_rows(
                Path(source_paths["artist_works_images"]["id_map"]),
                target_scope_keys,
            ),
        },
        "exhibition": {
            "raw_rows_total": sum(
                count_target_rows(path, target_scope_keys) for path in source_paths["exhibition"]["raw"].values()
            ),
            "image_metadata_rows_total": sum(
                count_target_rows(path, target_scope_keys) for path in source_paths["exhibition"]["image_metadata"].values()
            ),
            "enrichment_output_rows_total": count_target_rows(
                Path(source_paths["exhibition"]["enrichment_output"]),
                target_scope_keys,
            ),
        },
    }


def build_target_gallery_rows(targets: list[ScopeTarget], target_year: int) -> list[dict[str, Any]]:
    stats = build_stats(target_year)
    rows: list[dict[str, Any]] = []
    for target in targets:
        stat = stats.get(target.scope_key)
        rows.append(
            {
                "fair_slug": target.fair_slug,
                "gallery_name_en": target.gallery_name_en,
                "artist_text_count": int(stat.artist_text_count if stat is not None else 0),
                "artist_image_count": int(stat.artist_image_count if stat is not None else 0),
                "exhibition_text_count": int(stat.exhibition_text_count if stat is not None else 0),
                "exhibition_image_count": int(stat.exhibition_image_count if stat is not None else 0),
            }
        )
    return rows


def build_current_write_report(
    *,
    targets: list[ScopeTarget],
    targets_path: Path,
    target_year: int,
    bundle: CurrentFormalArtifactBundle,
) -> dict[str, Any]:
    target_scope_keys = {target.scope_key for target in targets}
    source_paths = build_resolved_current_source_paths(target_year)
    return {
        "source_of_truth": "current_formal_artifacts",
        "write_strategy": "block_scope_no_op_current_source_bundle",
        "mutation_required": False,
        "targets_file": str(targets_path),
        "target_total": len(targets),
        "targets": [target.to_dict() for target in targets],
        "included_categories": list(bundle.categories),
        "included_groups": [
            {
                "group_key": group.group_key,
                "category": group.category,
                "file_total": len(group.paths),
                "paths": [path.as_posix() for path in group.paths],
            }
            for group in bundle.groups
        ],
        "current_paths": stringify_paths(source_paths),
        "scope_counts": build_scope_counts_from_paths(source_paths=source_paths, target_scope_keys=target_scope_keys),
        "target_gallery_rows": build_target_gallery_rows(targets, target_year),
        "artist_works_images_openclip_required": True,
    }


def derive_exhibition_images_current_status(scope_counts: dict[str, Any]) -> tuple[str, bool]:
    exhibition_counts = dict(scope_counts.get("exhibition", {}))
    raw_rows_total = int(exhibition_counts.get("raw_rows_total") or 0)
    image_metadata_rows_total = int(exhibition_counts.get("image_metadata_rows_total") or 0)
    required = raw_rows_total > 0
    if not required:
        return "not_required", False
    if image_metadata_rows_total <= 0:
        return "blocked_missing_scope_exhibition_image_metadata", True
    return "planned", True


def finalize_current_write_report(report: dict[str, Any], *, apply: bool) -> dict[str, Any]:
    out = dict(report)
    scope_counts = dict(out.get("scope_counts", {}))
    exhibition_status, exhibition_required = derive_exhibition_images_current_status(scope_counts)
    blocking_errors = list(out.get("blocking_errors", []))
    if exhibition_status.startswith("blocked"):
        blocking_errors.append("blocked_exhibition_image_source_missing")
    out["blocking_errors"] = list(dict.fromkeys(str(item) for item in blocking_errors if str(item).strip()))
    out["exhibition_images_current_status"] = exhibition_status
    out["exhibition_images_required_for_block_completion"] = bool(exhibition_required)
    if out["blocking_errors"]:
        out["status"] = "blocked_missing_required_exhibition_image_source"
        out["mutation_allowed"] = False
        return out
    out["status"] = "applied" if apply else "planned"
    out["mutation_allowed"] = bool(out.get("mutation_required"))
    return out


def current_relative_path(path: Path) -> Path:
    return resolve_path(path).relative_to(CURRENT_FORMAL_ARTIFACTS_ROOT.resolve())


def stage_path_from_current_path(stage_current_root: Path, current_path: Path) -> Path:
    return stage_current_root / current_relative_path(current_path)


def clone_bundle_to_stage_root(
    *,
    bundle: CurrentFormalArtifactBundle,
    stage_current_root: Path,
    bundle_name: str,
) -> CurrentFormalArtifactBundle:
    stage_groups: list[CurrentFormalArtifactGroup] = []
    for group in bundle.groups:
        stage_groups.append(
            CurrentFormalArtifactGroup(
                group_key=group.group_key,
                category=group.category,
                description=group.description,
                required=group.required,
                paths=tuple(stage_path_from_current_path(stage_current_root, path) for path in group.paths),
            )
        )
    return CurrentFormalArtifactBundle(
        bundle_name=bundle_name,
        target_year=bundle.target_year,
        categories=bundle.categories,
        groups=tuple(stage_groups),
        local_root=stage_current_root,
        r2_prefix=CURRENT_FORMAL_ARTIFACTS_ROOT.as_posix(),
    )


def copy_file_if_exists(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def copy_bundle_files(src_bundle: CurrentFormalArtifactBundle, dst_bundle: CurrentFormalArtifactBundle) -> None:
    for src_group, dst_group in zip(src_bundle.groups, dst_bundle.groups, strict=True):
        if src_group.group_key != dst_group.group_key:
            raise RuntimeError("bundle_group_key_mismatch_during_stage_copy")
        for src_path, dst_path in zip(src_group.paths, dst_group.paths, strict=True):
            copy_file_if_exists(src_path, dst_path)


def stage_runtime_paths(stage_current_root: Path, runtime_paths: dict[str, Path | str]) -> dict[str, Path | str]:
    out: dict[str, Path | str] = {}
    for key, value in runtime_paths.items():
        if key == "manifest_r2_prefix":
            out[key] = value
            continue
        out[key] = stage_path_from_current_path(stage_current_root, Path(value))
    return out


def build_staged_source_paths(stage_current_root: Path, target_year: int) -> dict[str, dict[str, Any]]:
    current_paths = build_resolved_current_source_paths(target_year)
    return {
        "artist": {
            "raw": {
                fair_slug: stage_path_from_current_path(stage_current_root, Path(path))
                for fair_slug, path in current_paths["artist"]["raw"].items()
            },
            "image_metadata": {
                fair_slug: stage_path_from_current_path(stage_current_root, Path(path))
                for fair_slug, path in current_paths["artist"]["image_metadata"].items()
            },
            "enrichment_output": stage_path_from_current_path(stage_current_root, Path(current_paths["artist"]["enrichment_output"])),
            "enrichment_summary": stage_path_from_current_path(stage_current_root, Path(current_paths["artist"]["enrichment_summary"])),
            "text_vector": stage_runtime_paths(
                stage_current_root,
                get_current_artist_text_vector_runtime_paths(target_year=target_year),
            ),
        },
        "artist_works_images": stage_runtime_paths(
            stage_current_root,
            get_current_artist_works_vector_runtime_paths(target_year=target_year),
        ),
        "exhibition": {
            "raw": {
                fair_slug: stage_path_from_current_path(stage_current_root, Path(path))
                for fair_slug, path in current_paths["exhibition"]["raw"].items()
            },
            "image_metadata": {
                fair_slug: stage_path_from_current_path(stage_current_root, Path(path))
                for fair_slug, path in current_paths["exhibition"]["image_metadata"].items()
            },
            "enrichment_output": stage_path_from_current_path(stage_current_root, Path(current_paths["exhibition"]["enrichment_output"])),
            "enrichment_summary": stage_path_from_current_path(stage_current_root, Path(current_paths["exhibition"]["enrichment_summary"])),
        },
    }


def load_text_vector_state(
    *,
    runtime_paths: dict[str, Path | str],
    fallback_dim: int,
) -> tuple[list[dict[str, Any]], np.ndarray, list[dict[str, Any]]]:
    meta_path = Path(runtime_paths["meta"])
    index_path = Path(runtime_paths["index"])
    failed_path = Path(runtime_paths["failed"])
    if meta_path.exists() and index_path.exists():
        rows = read_jsonl(meta_path)
        index = np.load(index_path).astype(np.float32)
        if len(rows) != int(index.shape[0]):
            raise ValueError("artists_text current meta/index mismatch")
        return rows, index, read_jsonl(failed_path)
    if meta_path.exists() or index_path.exists():
        raise FileNotFoundError("artists_text current artifact set is incomplete")
    return [], np.zeros((0, fallback_dim), dtype=np.float32), []


def load_image_vector_state(
    *,
    runtime_paths: dict[str, Path | str],
    fallback_dim: int,
) -> tuple[list[dict[str, Any]], np.ndarray, np.ndarray, list[dict[str, Any]]]:
    id_map_path = Path(runtime_paths["id_map"])
    embeddings_path = Path(runtime_paths["embeddings"])
    index_path = Path(runtime_paths["index"])
    failed_path = Path(runtime_paths["failed"])
    if id_map_path.exists() and embeddings_path.exists() and index_path.exists():
        rows = read_jsonl(id_map_path)
        embeddings = np.load(embeddings_path).astype(np.float32)
        search_index = np.load(index_path).astype(np.float32)
        if len(rows) != int(embeddings.shape[0]):
            raise ValueError("artist_works_images current id_map/matrix mismatch")
        return rows, embeddings, search_index, read_jsonl(failed_path)
    if id_map_path.exists() or embeddings_path.exists() or index_path.exists():
        raise FileNotFoundError("artist_works_images current artifact set is incomplete")
    empty = np.zeros((0, fallback_dim), dtype=np.float32)
    return [], empty, empty, []


def mark_summary_for_closeout_plan(summary: dict[str, Any], *, apply: bool) -> dict[str, Any]:
    out = dict(summary)
    if apply:
        out["promoted_to_current"] = True
        out["promote_verdict"] = str(out.get("promote_verdict") or "closeout_merge_applied")
        out["closeout_plan_only"] = False
        return out
    out["promoted_to_current"] = False
    out["promote_verdict"] = "closeout_merge_planned"
    out["closeout_plan_only"] = True
    return out


def build_mixed_source_trial_roots(args: argparse.Namespace) -> dict[str, Path]:
    out: dict[str, Path] = {}
    artists_enrichment_root = resolve_optional_path(args.artists_enrichment_trial_root)
    artists_text_vector_root = resolve_optional_path(args.artists_text_vector_trial_root)
    artist_image_vector_root = resolve_optional_path(args.artist_works_images_vector_trial_root)
    exhibitions_raw_root = resolve_optional_path(args.exhibitions_raw_trial_root)
    if artists_enrichment_root is not None:
        out["artists_enrichment"] = artists_enrichment_root
    if artists_text_vector_root is not None:
        out["artists_text_vector"] = artists_text_vector_root
    if artist_image_vector_root is not None:
        out["artist_works_images_vector"] = artist_image_vector_root
    if exhibitions_raw_root is not None:
        out["exhibitions_raw"] = exhibitions_raw_root
    return out


def prepare_mixed_source_closeout_plan(
    *,
    targets: list[ScopeTarget],
    targets_path: Path,
    target_year: int,
    run_id: str,
    apply: bool,
    trial_roots: dict[str, Path],
    current_bundle: CurrentFormalArtifactBundle,
    plan_root: Path | None,
) -> tuple[CurrentFormalArtifactBundle, dict[str, Any], Any]:
    if not trial_roots:
        raise ValueError("mixed_source_closeout_requires_at_least_one_trial_root")

    target_scope_keys = {target.scope_key for target in targets}
    stage_root = plan_root or resolve_path(DEFAULT_PLAN_ROOT_DIR / run_id)
    stage_current_root = stage_root / "data" / "current"
    stage_bundle = clone_bundle_to_stage_root(
        bundle=current_bundle,
        stage_current_root=stage_current_root,
        bundle_name=f"{targets_path.stem}_block_planned_current_formal_artifacts",
    )
    copy_bundle_files(current_bundle, stage_bundle)

    current_paths = build_resolved_current_source_paths(target_year)
    staged_paths = build_staged_source_paths(stage_current_root, target_year)
    merge_plan: dict[str, Any] = {}

    if "exhibitions_raw" in trial_roots:
        trial_root = trial_roots["exhibitions_raw"]
        trial_raw_paths = get_current_raw_paths("exhibitions", target_year, root=trial_root)
        by_fair: dict[str, Any] = {}
        current_target_rows_before_total = 0
        trial_target_rows_total = 0
        retained_non_target_rows_total = 0
        final_rows_total = 0
        for fair_slug, current_raw_path in current_paths["exhibition"]["raw"].items():
            trial_raw_path = Path(trial_raw_paths[fair_slug])
            if not trial_raw_path.exists():
                raise FileNotFoundError(f"missing_trial_exhibition_raw:{fair_slug}:{trial_raw_path}")
            current_rows = read_jsonl(Path(current_raw_path))
            trial_rows = read_jsonl(trial_raw_path)
            merged = merge_jsonl_rows_by_scope(
                current_rows=current_rows,
                trial_rows=trial_rows,
                target_scope_keys=target_scope_keys,
                label=f"exhibition_raw_{fair_slug}",
            )
            staged_raw_path = Path(staged_paths["exhibition"]["raw"][fair_slug])
            write_jsonl_atomic(staged_raw_path, merged["final_rows"])
            current_target_rows_before_total += int(merged["current_target_rows_total"])
            trial_target_rows_total += int(merged["trial_target_rows_total"])
            retained_non_target_rows_total += int(merged["retained_non_target_rows_total"])
            final_rows_total += int(merged["final_rows_total"])
            by_fair[fair_slug] = {
                "current_path": str(current_raw_path),
                "trial_path": str(trial_raw_path),
                "output_path": str(staged_raw_path),
                "current_target_rows_total": int(merged["current_target_rows_total"]),
                "trial_target_rows_total": int(merged["trial_target_rows_total"]),
                "retained_non_target_rows_total": int(merged["retained_non_target_rows_total"]),
                "final_rows_total": int(merged["final_rows_total"]),
            }
        merge_plan["exhibition_raw"] = {
            "source_root": str(trial_root),
            "current_target_rows_before_total": current_target_rows_before_total,
            "trial_target_rows_total": trial_target_rows_total,
            "retained_non_target_rows_total": retained_non_target_rows_total,
            "final_rows_total": final_rows_total,
            "by_fair": by_fair,
        }
    else:
        by_fair = {}
        current_target_rows_before_total = 0
        for fair_slug, current_raw_path in current_paths["exhibition"]["raw"].items():
            current_target_rows = count_target_rows(Path(current_raw_path), target_scope_keys)
            current_target_rows_before_total += int(current_target_rows)
            by_fair[fair_slug] = {
                "current_path": str(current_raw_path),
                "output_path": str(staged_paths["exhibition"]["raw"][fair_slug]),
                "current_target_rows_total": int(current_target_rows),
            }
        merge_plan["exhibition_raw"] = {
            "source_root": "current",
            "current_target_rows_before_total": current_target_rows_before_total,
            "trial_target_rows_total": 0,
            "by_fair": by_fair,
        }

    if "artists_enrichment" in trial_roots:
        trial_root = trial_roots["artists_enrichment"]
        trial_source = extract_trial_enrichment_source(trial_root)
        current_enrichment_rows = read_jsonl(Path(current_paths["artist"]["enrichment_output"]))
        current_summary_before = (
            read_json(Path(current_paths["artist"]["enrichment_summary"]))
            if Path(current_paths["artist"]["enrichment_summary"]).exists()
            else {}
        )
        current_scoped_source_map, current_fallback_source_map = build_source_scope_maps(
            {fair_slug: read_jsonl(path) for fair_slug, path in current_paths["artist"]["raw"].items()}
        )
        trial_raw_paths = get_current_raw_paths("artists", target_year, root=trial_root)
        trial_scoped_source_map, trial_fallback_source_map = build_source_scope_maps(
            {fair_slug: read_jsonl(path) for fair_slug, path in trial_raw_paths.items()}
        )
        retained_current_rows = [
            dict(row)
            for row in current_enrichment_rows
            if resolve_enrichment_scope_key(
                row,
                scoped_source_map=current_scoped_source_map,
                fallback_source_map=current_fallback_source_map,
            )
            not in target_scope_keys
        ]
        trial_rows_added = [
            dict(row)
            for row in read_jsonl(Path(trial_source["output_path"]))
            if resolve_enrichment_scope_key(
                row,
                scoped_source_map=trial_scoped_source_map,
                fallback_source_map=trial_fallback_source_map,
            )
            in target_scope_keys
            and str(row.get("status") or "").strip() == "APPLIED"
        ]
        merged_rows = retained_current_rows + trial_rows_added
        summary_after = build_enrichment_summary(
            started_at=utc_now_iso(),
            completed_at=utc_now_iso(),
            trial_root=trial_root,
            current_output_path=Path(staged_paths["artist"]["enrichment_output"]),
            current_summary_path=Path(staged_paths["artist"]["enrichment_summary"]),
            current_summary_before=current_summary_before,
            trial_source=trial_source,
            targets=targets,
            current_rows_before=current_enrichment_rows,
            trial_rows_added=trial_rows_added,
            final_rows=merged_rows,
            current_scoped_source_map=current_scoped_source_map,
            current_fallback_source_map=current_fallback_source_map,
        )
        summary_after = mark_summary_for_closeout_plan(summary_after, apply=apply)
        write_jsonl_atomic(Path(staged_paths["artist"]["enrichment_output"]), merged_rows)
        write_json_atomic(Path(staged_paths["artist"]["enrichment_summary"]), summary_after)
        merge_plan["artist_enrichment"] = {
            "source_root": str(trial_root),
            "trial_output_path": str(trial_source["output_path"]),
            "trial_summary_path": str(trial_source["summary_path"]),
            "current_rows_before": len(current_enrichment_rows),
            "current_rows_after": len(merged_rows),
            "trial_target_rows_added": len(trial_rows_added),
            "retained_non_target_rows_total": len(retained_current_rows),
            "final_target_rows_total": len(merged_rows) - len(retained_current_rows),
            "output_path": str(staged_paths["artist"]["enrichment_output"]),
            "summary_path": str(staged_paths["artist"]["enrichment_summary"]),
        }
    else:
        merge_plan["artist_enrichment"] = {
            "source_root": "current",
            "current_rows_before": count_target_rows(Path(current_paths["artist"]["enrichment_output"]), target_scope_keys),
            "current_rows_after": count_target_rows(Path(staged_paths["artist"]["enrichment_output"]), target_scope_keys),
            "trial_target_rows_added": 0,
            "output_path": str(staged_paths["artist"]["enrichment_output"]),
            "summary_path": str(staged_paths["artist"]["enrichment_summary"]),
        }

    if "artists_text_vector" in trial_roots:
        trial_root = trial_roots["artists_text_vector"]
        trial_text_paths = get_current_artist_text_vector_runtime_paths(root=trial_root, target_year=target_year)
        trial_rows = read_jsonl(Path(trial_text_paths["meta"]))
        trial_index = np.load(Path(trial_text_paths["index"])).astype(np.float32)
        trial_failed_rows = read_jsonl(Path(trial_text_paths["failed"]))
        trial_summary = read_json(Path(trial_text_paths["summary"]))
        current_rows, current_index, current_failed_rows = load_text_vector_state(
            runtime_paths=get_current_artist_text_vector_runtime_paths(target_year=target_year),
            fallback_dim=int(trial_index.shape[1]),
        )
        merge_result = merge_text_vector_state(
            current_rows=current_rows,
            current_index=current_index,
            current_failed_rows=current_failed_rows,
            trial_rows=trial_rows,
            trial_index=trial_index,
            trial_failed_rows=trial_failed_rows,
            target_scope_keys=target_scope_keys,
        )
        staged_text_paths = staged_paths["artist"]["text_vector"]
        summary_after = build_text_vector_summary(
            started_at=utc_now_iso(),
            completed_at=utc_now_iso(),
            current_paths=staged_text_paths,
            trial_root=trial_root,
            trial_summary=trial_summary,
            targets=targets,
            merge_result=merge_result,
        )
        summary_after = mark_summary_for_closeout_plan(summary_after, apply=apply)
        manifest_after = build_text_vector_manifest(
            completed_at=str(summary_after.get("completed_at") or utc_now_iso()),
            current_paths=staged_text_paths,
            trial_summary=trial_summary,
            targets=targets,
        )
        write_npy_atomic(Path(staged_text_paths["index"]), merge_result["final_index"])
        write_jsonl_atomic(Path(staged_text_paths["meta"]), merge_result["final_rows"])
        write_jsonl_atomic(Path(staged_text_paths["failed"]), merge_result["final_failed_rows"])
        write_json_atomic(Path(staged_text_paths["summary"]), summary_after)
        write_json_atomic(Path(staged_text_paths["manifest"]), manifest_after)
        merge_plan["artist_text_vector"] = {
            "source_root": str(trial_root),
            "current_target_rows_before": int(merge_result["current_target_rows_total"]),
            "trial_target_rows_total": int(merge_result["trial_target_rows_total"]),
            "retained_non_target_rows_total": int(merge_result["retained_non_target_rows_total"]),
            "final_rows_total": len(merge_result["final_rows"]),
            "final_index_shape": list(merge_result["final_index"].shape),
            "output_paths": stringify_paths(staged_text_paths),
        }
    else:
        merge_plan["artist_text_vector"] = {
            "source_root": "current",
            "final_rows_total": count_target_rows(Path(staged_paths["artist"]["text_vector"]["meta"]), target_scope_keys),
            "output_paths": stringify_paths(staged_paths["artist"]["text_vector"]),
        }

    if "artist_works_images_vector" in trial_roots:
        trial_root = trial_roots["artist_works_images_vector"]
        trial_image_paths = get_current_artist_works_vector_runtime_paths(root=trial_root, target_year=target_year)
        trial_rows = read_jsonl(Path(trial_image_paths["id_map"]))
        trial_embeddings = np.load(Path(trial_image_paths["embeddings"])).astype(np.float32)
        trial_search_index = np.load(Path(trial_image_paths["index"])).astype(np.float32)
        trial_failed_rows = read_jsonl(Path(trial_image_paths["failed"]))
        trial_summary = read_json(Path(trial_image_paths["summary"]))
        current_rows, current_embeddings, current_search_index, current_failed_rows = load_image_vector_state(
            runtime_paths=get_current_artist_works_vector_runtime_paths(target_year=target_year),
            fallback_dim=int(trial_embeddings.shape[1]),
        )
        merge_result = merge_image_vector_state(
            current_rows=current_rows,
            current_embeddings=current_embeddings,
            current_search_index=current_search_index,
            current_failed_rows=current_failed_rows,
            trial_rows=trial_rows,
            trial_embeddings=trial_embeddings,
            trial_search_index=trial_search_index,
            trial_failed_rows=trial_failed_rows,
            target_scope_keys=target_scope_keys,
        )
        staged_image_paths = staged_paths["artist_works_images"]
        summary_after = build_image_vector_summary(
            started_at=utc_now_iso(),
            completed_at=utc_now_iso(),
            current_paths=staged_image_paths,
            trial_root=trial_root,
            trial_summary=trial_summary,
            targets=targets,
            merge_result=merge_result,
        )
        summary_after = mark_summary_for_closeout_plan(summary_after, apply=apply)
        manifest_after = build_image_vector_manifest(
            completed_at=str(summary_after.get("completed_at") or utc_now_iso()),
            current_paths=staged_image_paths,
            trial_summary=trial_summary,
            targets=targets,
        )
        write_npy_atomic(Path(staged_image_paths["embeddings"]), merge_result["final_embeddings"])
        write_npy_atomic(Path(staged_image_paths["index"]), merge_result["final_search_index"])
        write_jsonl_atomic(Path(staged_image_paths["id_map"]), merge_result["final_rows"])
        write_jsonl_atomic(Path(staged_image_paths["failed"]), merge_result["final_failed_rows"])
        write_json_atomic(Path(staged_image_paths["summary"]), summary_after)
        write_json_atomic(Path(staged_image_paths["manifest"]), manifest_after)
        merge_plan["artist_works_images_vector"] = {
            "source_root": str(trial_root),
            "current_target_rows_before": int(merge_result["current_target_rows_total"]),
            "trial_target_rows_total": int(merge_result["trial_target_rows_total"]),
            "retained_non_target_rows_total": int(merge_result["retained_non_target_rows_total"]),
            "final_rows_total": len(merge_result["final_rows"]),
            "final_embeddings_shape": list(merge_result["final_embeddings"].shape),
            "final_search_index_shape": list(merge_result["final_search_index"].shape),
            "output_paths": stringify_paths(staged_image_paths),
        }
    else:
        merge_plan["artist_works_images_vector"] = {
            "source_root": "current",
            "final_rows_total": count_target_rows(Path(staged_paths["artist_works_images"]["id_map"]), target_scope_keys),
            "output_paths": stringify_paths(staged_paths["artist_works_images"]),
        }

    scope_counts = build_scope_counts_from_paths(source_paths=staged_paths, target_scope_keys=target_scope_keys)
    if "artist_enrichment" in merge_plan:
        scope_counts["artist"]["enrichment_output_rows_total"] = int(
            merge_plan["artist_enrichment"].get("final_target_rows_total")
            or merge_plan["artist_enrichment"].get("trial_target_rows_added")
            or 0
        )
    current_write_report = {
        "source_of_truth": "mixed_current_plus_trial_bounded_merge",
        "write_strategy": "block_scope_stage_then_promote_to_current",
        "mutation_required": True,
        "targets_file": str(targets_path),
        "target_total": len(targets),
        "targets": [target.to_dict() for target in targets],
        "included_categories": list(stage_bundle.categories),
        "included_groups": [
            {
                "group_key": group.group_key,
                "category": group.category,
                "file_total": len(group.paths),
                "paths": [path.as_posix() for path in group.paths],
            }
            for group in stage_bundle.groups
        ],
        "current_paths": stringify_paths(current_paths),
        "planned_current_paths": stringify_paths(staged_paths),
        "scope_counts": scope_counts,
        "target_gallery_rows": build_target_gallery_rows(targets, target_year),
        "artist_works_images_openclip_required": True,
        "trial_roots": {key: str(value) for key, value in trial_roots.items()},
        "plan_root": str(stage_root),
        "plan_current_root": str(stage_current_root),
        "merge_plan": merge_plan,
    }

    def execute_current_write(apply_flag: bool) -> dict[str, Any]:
        final_report = finalize_current_write_report(current_write_report, apply=apply_flag)
        if apply_flag and str(final_report.get("status") or "").strip() == "applied":
            copy_bundle_files(stage_bundle, current_bundle)
        return final_report

    return stage_bundle, current_write_report, execute_current_write


def derive_openclip_current_status(bundle: CurrentFormalArtifactBundle) -> str:
    for group in bundle.groups:
        if group.group_key == "artist_works_images_vector":
            missing = [path for path in group.paths if not path.exists()]
            if missing:
                return "blocked_missing_required_paths"
            return "planned"
    return "blocked_missing_group"


def augment_block_closeout_report(
    *,
    report: dict[str, Any],
    bundle: CurrentFormalArtifactBundle,
    targets_path: Path,
) -> dict[str, Any]:
    r2_report = dict(report.get("r2_sync", {}))
    contract = dict(report.get("contract", {}))
    current_write_report = dict(report.get("current_write", {}))
    openclip_status = derive_openclip_current_status(bundle)
    exhibition_status = str(current_write_report.get("exhibition_images_current_status") or "").strip()
    if not exhibition_status:
        exhibition_status, _ = derive_exhibition_images_current_status(current_write_report.get("scope_counts", {}))
    contract["block_completion_requires"] = list(BLOCK_CLOSEOUT_FLOW)
    contract["exhibition_images_current_status"] = exhibition_status
    contract["exhibition_images_required_for_block_completion"] = bool(
        current_write_report.get("exhibition_images_required_for_block_completion", False)
    )
    contract["artist_works_images_openclip_current_status"] = openclip_status
    contract["artist_works_images_openclip_required"] = bool(
        current_write_report.get("artist_works_images_openclip_required", True)
    )
    contract["closeout_report_status"] = "generated"
    if contract.get("mode") == "dry_run":
        if (
            contract.get("current_write_status") == "planned"
            and exhibition_status in {"planned", "not_required"}
            and contract.get("xlsx_update_status") == "planned"
            and contract.get("skip_registry_gallery_list_cleanup_status") == "planned"
            and contract.get("r2_sync_status") == "planned"
            and openclip_status == "planned"
        ):
            contract["block_completion_status"] = "planned"
        else:
            contract["block_completion_status"] = "blocked"
    else:
        if (
            contract.get("current_write_status") == "applied"
            and exhibition_status in {"planned", "not_required"}
            and contract.get("xlsx_update_status") == "applied"
            and contract.get("skip_registry_gallery_list_cleanup_status") == "applied"
            and contract.get("r2_sync_status") == "applied"
            and openclip_status == "planned"
        ):
            contract["block_completion_status"] = "completed"
        else:
            contract["block_completion_status"] = "blocked_or_followup_required"
    report["contract"] = contract
    report["block_scope"] = {
        "targets_file": str(targets_path),
        "target_total": contract.get("target_total", 0),
        "targets": contract.get("targets", []),
    }
    report["included_bundle"] = {
        "bundle_name": bundle.bundle_name,
        "categories": list(bundle.categories),
        "group_total": int(r2_report.get("artifact_group_total", 0)),
        "file_total": int(r2_report.get("artifact_file_total", 0)),
        "missing_required_paths": list(r2_report.get("required_paths_missing", [])),
        "artifact_groups": list(r2_report.get("artifact_groups", [])),
    }
    return report


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    require_live_closeout_approval(args)
    targets_path = resolve_path(args.targets_file)
    xlsx_path = resolve_path(args.xlsx_path)
    target_year = int(args.target_year)
    run_id = str(args.run_id or "").strip() or f"{DEFAULT_RUN_ID_PREFIX}_{utc_now_compact()}"
    targets = load_targets_ordered(targets_path)
    current_bundle = resolve_current_formal_artifact_bundle(
        bundle_name=f"{targets_path.stem}_block_current_formal_artifacts",
        categories=(
            BLOCK_ARTIFACT_CATEGORY_ARTIST,
            BLOCK_ARTIFACT_CATEGORY_ARTIST_WORKS_IMAGES,
            BLOCK_ARTIFACT_CATEGORY_EXHIBITION,
        ),
        target_year=target_year,
    )
    breakdown_stats = build_stats(target_year)
    trial_roots = build_mixed_source_trial_roots(args)

    if trial_roots:
        plan_root = resolve_optional_path(args.plan_root)
        plan_bundle, _current_write_report, current_write_callback = prepare_mixed_source_closeout_plan(
            targets=targets,
            targets_path=targets_path,
            target_year=target_year,
            run_id=run_id,
            apply=bool(args.apply),
            trial_roots=trial_roots,
            current_bundle=current_bundle,
            plan_root=plan_root,
        )
        r2_bundle = current_bundle if args.apply else plan_bundle
    else:
        current_write_report_template = build_current_write_report(
            targets=targets,
            targets_path=targets_path,
            target_year=target_year,
            bundle=current_bundle,
        )
        current_write_callback = lambda apply_flag: finalize_current_write_report(
            current_write_report_template,
            apply=bool(apply_flag),
        )
        r2_bundle = current_bundle

    report = execute_closeout_with_breakdown_contract(
        contract_name="block_closeout_unified",
        apply=bool(args.apply),
        run_id=run_id,
        xlsx_path=xlsx_path,
        target_year=target_year,
        targets=targets,
        current_write_callback=current_write_callback,
        breakdown_stats_override=breakdown_stats,
        r2_artifact_bundle=r2_bundle,
        r2_execute_remote=bool(args.r2_live_plan or (args.apply and not args.no_r2_remote)),
    )
    report = augment_block_closeout_report(report=report, bundle=r2_bundle, targets_path=targets_path)

    print(json.dumps(report, ensure_ascii=True, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
