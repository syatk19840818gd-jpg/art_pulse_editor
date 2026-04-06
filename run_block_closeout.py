#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from closeout_breakdown_contract import (
    BLOCK_ARTIFACT_CATEGORY_ARTIST,
    BLOCK_ARTIFACT_CATEGORY_ARTIST_WORKS_IMAGES,
    BLOCK_ARTIFACT_CATEGORY_EXHIBITION,
    CurrentFormalArtifactBundle,
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
from run_rag_gallery_breakdown_update import (
    DEFAULT_XLSX_PATH,
    ScopeTarget,
    build_stats,
    load_targets_ordered,
)

DEFAULT_TARGETS_CSV = Path("data/gallery_lists/phase3_fixed_block_next10_targets.csv")
DEFAULT_RUN_ID_PREFIX = "TASK_PHASE3_BLOCK_CLOSEOUT"
BLOCK_CLOSEOUT_FLOW = [
    "current_write",
    "xlsx_update",
    "artist_works_images_openclip_current",
    "r2_sync",
    "closeout_report",
]


def utc_now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_path(path_text: str | Path) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return (Path.cwd() / path).resolve()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Unified block closeout runner. Resolve the block scope from a targets CSV, "
            "then orchestrate current verification, xlsx update, Artist Works Images "
            "OpenCLIP current check, R2 sync, and one closeout report."
        )
    )
    parser.add_argument(
        "--targets-file",
        default=str(DEFAULT_TARGETS_CSV),
        help=f"gallery scope CSV (default: {DEFAULT_TARGETS_CSV})",
    )
    parser.add_argument(
        "--xlsx-path",
        default=str(DEFAULT_XLSX_PATH),
        help=f"xlsx path (default: {DEFAULT_XLSX_PATH})",
    )
    parser.add_argument(
        "--target-year",
        type=int,
        default=TARGET_YEAR,
        help=f"default: {TARGET_YEAR}",
    )
    parser.add_argument(
        "--run-id",
        default="",
        help=f"run_id for block closeout report (default: {DEFAULT_RUN_ID_PREFIX}_<UTCSTAMP>)",
    )
    parser.add_argument(
        "--r2-live-plan",
        action="store_true",
        help="run remote R2 plan during dry-run; default is contract-only dry-run with no remote access",
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


def build_current_source_paths(target_year: int) -> dict[str, dict[str, Any]]:
    return {
        "artist": {
            "raw": {fair_slug: str(path) for fair_slug, path in get_current_raw_paths("artists", target_year).items()},
            "image_metadata": {
                fair_slug: str(path) for fair_slug, path in get_current_artist_image_meta_paths().items()
            },
            "enrichment_output": str(get_enrichment_current_output_path("artists", target_year)),
            "enrichment_summary": str(get_enrichment_current_summary_path("artists", target_year)),
            "text_vector": {
                key: str(value)
                for key, value in get_current_artist_text_vector_runtime_paths(target_year=target_year).items()
                if key != "manifest_r2_prefix"
            },
        },
        "artist_works_images": {
            key: str(value)
            for key, value in get_current_artist_works_vector_runtime_paths(target_year=target_year).items()
            if key != "manifest_r2_prefix"
        },
        "exhibition": {
            "raw": {
                fair_slug: str(path) for fair_slug, path in get_current_raw_paths("exhibitions", target_year).items()
            },
            "image_metadata": {
                fair_slug: str(path)
                for fair_slug, path in get_current_exhibitions_image_meta_paths(target_year).items()
            },
            "enrichment_output": str(get_enrichment_current_output_path("exhibitions", target_year)),
            "enrichment_summary": str(get_enrichment_current_summary_path("exhibitions", target_year)),
        },
    }


def build_current_scope_counts(
    *,
    target_year: int,
    target_scope_keys: set[tuple[str, str]],
) -> dict[str, dict[str, int]]:
    artist_text_paths = get_current_artist_text_vector_runtime_paths(target_year=target_year)
    image_vector_paths = get_current_artist_works_vector_runtime_paths(target_year=target_year)
    return {
        "artist": {
            "raw_rows_total": sum(
                count_target_rows(path, target_scope_keys)
                for path in get_current_raw_paths("artists", target_year).values()
            ),
            "image_metadata_rows_total": sum(
                count_target_rows(path, target_scope_keys)
                for path in get_current_artist_image_meta_paths().values()
            ),
            "enrichment_output_rows_total": count_target_rows(
                get_enrichment_current_output_path("artists", target_year),
                target_scope_keys,
            ),
            "text_vector_rows_total": count_target_rows(Path(artist_text_paths["meta"]), target_scope_keys),
        },
        "artist_works_images": {
            "vector_rows_total": count_target_rows(Path(image_vector_paths["id_map"]), target_scope_keys),
        },
        "exhibition": {
            "raw_rows_total": sum(
                count_target_rows(path, target_scope_keys)
                for path in get_current_raw_paths("exhibitions", target_year).values()
            ),
            "image_metadata_rows_total": sum(
                count_target_rows(path, target_scope_keys)
                for path in get_current_exhibitions_image_meta_paths(target_year).values()
            ),
            "enrichment_output_rows_total": count_target_rows(
                get_enrichment_current_output_path("exhibitions", target_year),
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
        "current_paths": build_current_source_paths(target_year),
        "scope_counts": build_current_scope_counts(
            target_year=target_year,
            target_scope_keys=target_scope_keys,
        ),
        "target_gallery_rows": build_target_gallery_rows(targets, target_year),
        "artist_works_images_openclip_required": True,
    }


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
    openclip_status = derive_openclip_current_status(bundle)
    contract["block_completion_requires"] = list(BLOCK_CLOSEOUT_FLOW)
    contract["artist_works_images_openclip_current_status"] = openclip_status
    contract["closeout_report_status"] = "generated"
    if contract.get("mode") == "dry_run":
        if (
            contract.get("current_write_status") == "planned"
            and contract.get("xlsx_update_status") == "planned"
            and contract.get("r2_sync_status") == "planned"
            and openclip_status == "planned"
        ):
            contract["block_completion_status"] = "planned"
        else:
            contract["block_completion_status"] = "blocked"
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
    targets_path = resolve_path(args.targets_file)
    xlsx_path = resolve_path(args.xlsx_path)
    target_year = int(args.target_year)
    run_id = str(args.run_id or "").strip() or f"{DEFAULT_RUN_ID_PREFIX}_{utc_now_compact()}"
    targets = load_targets_ordered(targets_path)
    bundle = resolve_current_formal_artifact_bundle(
        bundle_name=f"{targets_path.stem}_block_current_formal_artifacts",
        categories=(
            BLOCK_ARTIFACT_CATEGORY_ARTIST,
            BLOCK_ARTIFACT_CATEGORY_ARTIST_WORKS_IMAGES,
            BLOCK_ARTIFACT_CATEGORY_EXHIBITION,
        ),
        target_year=target_year,
    )
    breakdown_stats = build_stats(target_year)
    current_write_report = build_current_write_report(
        targets=targets,
        targets_path=targets_path,
        target_year=target_year,
        bundle=bundle,
    )

    report = execute_closeout_with_breakdown_contract(
        contract_name="block_closeout_unified",
        apply=bool(args.apply),
        run_id=run_id,
        xlsx_path=xlsx_path,
        target_year=target_year,
        targets=targets,
        current_write_callback=lambda _apply: current_write_report,
        breakdown_stats_override=breakdown_stats,
        r2_artifact_bundle=bundle,
        r2_execute_remote=bool(args.apply or args.r2_live_plan),
    )
    report = augment_block_closeout_report(
        report=report,
        bundle=bundle,
        targets_path=targets_path,
    )

    print(json.dumps(report, ensure_ascii=True, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
