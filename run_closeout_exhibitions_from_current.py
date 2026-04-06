#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from closeout_breakdown_contract import (
    BLOCK_ARTIFACT_CATEGORY_EXHIBITION,
    execute_closeout_with_breakdown_contract,
    resolve_current_formal_artifact_bundle,
)
from phase2_art_pulse_config import (
    TARGET_YEAR,
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

DEFAULT_TARGETS_CSV = Path("data/gallery_lists/phase3_initial10_targets.csv")
DEFAULT_RUN_ID_PREFIX = "TASK_PHASE3_EXHIBITIONS_BLOCK_CLOSEOUT"


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
            "Close out an exhibitions block from current formal artifacts through "
            "xlsx update and required R2 sync."
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
        help=f"run_id for closeout contract (default: {DEFAULT_RUN_ID_PREFIX}_<UTCSTAMP>)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "treat current formal artifacts as canonical source, then update xlsx "
            "and execute required R2 sync for the exhibitions block"
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
            scope_key = ScopeTarget(fair_slug=fair_slug, gallery_name_en=gallery_name).scope_key
            if scope_key in target_scope_keys:
                count += 1
    return count


def build_current_write_report(
    *,
    targets: list[ScopeTarget],
    targets_path: Path,
    target_year: int,
) -> dict[str, Any]:
    target_scope_keys = {target.scope_key for target in targets}
    current_raw_paths = get_current_raw_paths("exhibitions", target_year)
    current_image_meta_paths = get_current_exhibitions_image_meta_paths(target_year)
    current_enrichment_output_path = get_enrichment_current_output_path("exhibitions", target_year)
    current_enrichment_summary_path = get_enrichment_current_summary_path("exhibitions", target_year)
    stats = build_stats(int(target_year))

    target_gallery_rows: list[dict[str, Any]] = []
    for target in targets:
        stat = stats.get(target.scope_key)
        target_gallery_rows.append(
            {
                "fair_slug": target.fair_slug,
                "gallery_name_en": target.gallery_name_en,
                "current_exhibition_text_count": int(stat.exhibition_text_count if stat is not None else 0),
                "current_exhibition_image_count": int(stat.exhibition_image_count if stat is not None else 0),
            }
        )

    return {
        "source_of_truth": "current_formal_artifacts",
        "write_strategy": "no_op_current_source_bundle",
        "mutation_required": False,
        "targets_file": str(targets_path),
        "target_total": len(targets),
        "targets": [target.to_dict() for target in targets],
        "current_paths": {
            "raw": {fair_slug: str(path) for fair_slug, path in current_raw_paths.items()},
            "image_metadata": {fair_slug: str(path) for fair_slug, path in current_image_meta_paths.items()},
            "enrichment_output": str(current_enrichment_output_path),
            "enrichment_summary": str(current_enrichment_summary_path),
        },
        "scope_counts": {
            "raw_rows_total": sum(count_target_rows(path, target_scope_keys) for path in current_raw_paths.values()),
            "image_metadata_rows_total": sum(
                count_target_rows(path, target_scope_keys) for path in current_image_meta_paths.values()
            ),
            "enrichment_output_rows_total": count_target_rows(current_enrichment_output_path, target_scope_keys),
        },
        "target_gallery_rows": target_gallery_rows,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    targets_path = resolve_path(args.targets_file)
    xlsx_path = resolve_path(args.xlsx_path)
    target_year = int(args.target_year)
    run_id = str(args.run_id or "").strip() or f"{DEFAULT_RUN_ID_PREFIX}_{utc_now_compact()}"
    targets = load_targets_ordered(targets_path)
    breakdown_stats = build_stats(target_year)
    current_write_report = build_current_write_report(
        targets=targets,
        targets_path=targets_path,
        target_year=target_year,
    )

    report = execute_closeout_with_breakdown_contract(
        contract_name="exhibitions_current_block_closeout",
        apply=bool(args.apply),
        run_id=run_id,
        xlsx_path=xlsx_path,
        target_year=target_year,
        targets=targets,
        current_write_callback=lambda _apply: current_write_report,
        breakdown_stats_override=breakdown_stats,
        r2_artifact_bundle=resolve_current_formal_artifact_bundle(
            bundle_name=f"{targets_path.stem}_exhibitions_current_formal_artifacts",
            categories=(BLOCK_ARTIFACT_CATEGORY_EXHIBITION,),
            target_year=target_year,
        ),
        r2_execute_remote=bool(args.apply),
    )

    print(json.dumps(report, ensure_ascii=True, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
