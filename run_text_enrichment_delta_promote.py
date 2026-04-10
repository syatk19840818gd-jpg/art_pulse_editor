#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from closeout_breakdown_contract import (
    BLOCK_ARTIFACT_CATEGORY_ARTIST,
    BLOCK_ARTIFACT_CATEGORY_ARTIST_WORKS_IMAGES,
    BLOCK_ARTIFACT_CATEGORY_EXHIBITION,
    execute_closeout_with_breakdown_contract,
    resolve_current_formal_artifact_bundle,
)
from enrichment_batch_common import (
    is_optional_output_enabled,
    read_jsonl,
    utc_now_compact,
    utc_now_iso,
    write_json,
    write_jsonl,
)
from phase2_art_pulse_config import (
    get_enrichment_current_output_path,
    get_enrichment_current_summary_path,
    get_enrichment_history_dir,
    get_enrichment_history_output_path,
    get_enrichment_history_summary_path,
    get_enrichment_runtime_requests_path,
    get_current_raw_paths,
    promote_history_file_to_current,
)
from run_rag_gallery_breakdown_update import DEFAULT_XLSX_PATH, ScopeTarget
from run_enrichment_artists_seed10_apply import normalize_source_url_for_match

SUPPORTED_CATEGORIES = ("artists", "exhibitions")
SUPPORTED_REPAIR_MODES = {"carry_forward_current_applied_row"}
DEFAULT_RUN_ID_PREFIX = "TASK_TEXT_ENRICHMENT_DELTA_PROMOTE"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Apply text enrichment delta promotes without re-extraction, "
            "and close out through xlsx update plus required R2 sync of current formal artifacts."
        )
    )
    parser.add_argument("--manifest", required=True, help="Path to delta manifest JSON.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Write canonical history/current/runtime artifacts, update xlsx, "
            "and execute required R2 sync. Default is dry-run to a trial root."
        ),
    )
    parser.add_argument(
        "--approval-token",
        default="",
        help="required for --apply; dry-run remains available for offline-only diagnosis",
    )
    parser.add_argument(
        "--trial-root",
        default="data/trials/text_enrichment_delta_promote_2025",
        help="Dry-run root directory. Ignored when --apply is used.",
    )
    parser.add_argument(
        "--xlsx-path",
        default=str(DEFAULT_XLSX_PATH),
        help=f"xlsx path (default: {DEFAULT_XLSX_PATH})",
    )
    parser.add_argument(
        "--run-id",
        default="",
        help=f"run_id for closeout contract (default: {DEFAULT_RUN_ID_PREFIX}_<UTCSTAMP>)",
    )
    parser.add_argument(
        "--category",
        action="append",
        default=[],
        help="optional category filter; repeatable. Supported: artists, exhibitions",
    )
    return parser.parse_args()


def require_delta_promote_approval(args: argparse.Namespace) -> None:
    if not args.apply:
        return
    if str(args.approval_token or "").strip():
        return
    raise RuntimeError(
        "approval_required_for_text_delta_promote_apply:"
        "pass --approval-token <user-approved-note>; use dry-run for offline-only diagnosis"
    )


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_path(path_text: str | Path) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return (Path.cwd() / path).resolve()


def collect_request_urls(row: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    source_urls = row.get("source_urls")
    if isinstance(source_urls, list):
        for value in source_urls:
            text = str(value or "").strip()
            if text:
                urls.append(text)
    fallback = str(row.get("source_url") or "").strip()
    if fallback:
        urls.append(fallback)
    return urls


def build_applied_index_from_rows(rows: list[dict[str, Any]]) -> dict[tuple[str, str, str, str], dict[str, Any]]:
    out: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for row in rows:
        if str(row.get("status") or "").strip() != "APPLIED":
            continue
        request_id = str(row.get("request_id") or "").strip()
        fair_slug = str(row.get("fair_slug") or "").strip()
        text_hash = str(row.get("text_hash") or "").strip()
        source_url_norm = normalize_source_url_for_match(str(row.get("source_url") or ""))
        if not request_id or not fair_slug or not text_hash or not source_url_norm:
            continue
        out[(request_id, fair_slug, text_hash, source_url_norm)] = row
    return out


def build_current_scope_target_maps(category: str, target_year: int) -> tuple[dict[tuple[str, str], ScopeTarget], dict[str, ScopeTarget]]:
    scoped: dict[tuple[str, str], ScopeTarget] = {}
    fallback: dict[str, ScopeTarget] = {}
    for fair_slug, path in get_current_raw_paths(category, target_year).items():
        for row in read_jsonl(path):
            gallery_name_en = str(row.get("gallery_name_en") or "").strip()
            source_url = normalize_source_url_for_match(str(row.get("source_url") or ""))
            if not gallery_name_en or not source_url:
                continue
            target = ScopeTarget(fair_slug=fair_slug, gallery_name_en=gallery_name_en)
            scoped[(fair_slug, source_url)] = target
            fallback.setdefault(source_url, target)
    return scoped, fallback


def collect_manifest_scope_targets(operations: list[dict[str, Any]], target_year: int) -> list[ScopeTarget]:
    ordered_targets: list[ScopeTarget] = []
    seen: set[tuple[str, str]] = set()
    maps_by_category: dict[str, tuple[dict[tuple[str, str], ScopeTarget], dict[str, ScopeTarget]]] = {}

    def add_target(target: ScopeTarget) -> None:
        if target.scope_key in seen:
            return
        seen.add(target.scope_key)
        ordered_targets.append(target)

    for op in operations:
        category = str(op.get("category") or "").strip()
        if category not in SUPPORTED_CATEGORIES:
            continue
        if category not in maps_by_category:
            maps_by_category[category] = build_current_scope_target_maps(category, target_year)
        scoped_map, fallback_map = maps_by_category[category]

        for repair in list(op.get("localized_repairs") or []):
            fair_slug = str(repair.get("fair_slug") or "").strip()
            source_url = normalize_source_url_for_match(str(repair.get("source_url") or ""))
            if not source_url:
                continue
            target = None
            if fair_slug:
                target = scoped_map.get((fair_slug, source_url))
            if target is None:
                target = fallback_map.get(source_url)
            if target is None:
                raise RuntimeError(f"closeout_scope_unresolved_for_repair:{category}:{fair_slug}:{source_url}")
            add_target(target)

        for value in list(op.get("intentional_drop_urls") or []):
            source_url = normalize_source_url_for_match(str(value or ""))
            if not source_url:
                continue
            target = fallback_map.get(source_url)
            if target is None:
                raise RuntimeError(f"closeout_scope_unresolved_for_drop:{category}:{source_url}")
            add_target(target)

    if not ordered_targets:
        raise RuntimeError("closeout_scope_targets_not_found_from_manifest")
    return ordered_targets


def resolve_r2_artifact_categories(operations: list[dict[str, Any]]) -> tuple[str, ...]:
    resolved: list[str] = []
    categories_present = {str(op.get("category") or "").strip() for op in operations}
    if "artists" in categories_present:
        resolved.extend(
            [
                BLOCK_ARTIFACT_CATEGORY_ARTIST,
                BLOCK_ARTIFACT_CATEGORY_ARTIST_WORKS_IMAGES,
            ]
        )
    if "exhibitions" in categories_present:
        resolved.append(BLOCK_ARTIFACT_CATEGORY_EXHIBITION)
    return tuple(resolved)


def build_paths(*, category: str, target_year: int, stamp: str, dry_run: bool, trial_root: Path) -> dict[str, Path]:
    if dry_run:
        base_dir = trial_root / stamp / category
        history_dir = base_dir / "history"
        current_dir = base_dir / "current_preview"
        runtime_dir = base_dir / "runtime_preview"
        diagnostics_dir = base_dir / "diagnostics"
        reports_dir = base_dir / "reports"
        history_output_path = history_dir / f"{category}_enrichment_apply_output_{target_year}_{stamp}.jsonl"
        history_summary_path = history_dir / f"{category}_enrichment_apply_summary_{target_year}_{stamp}.json"
        history_manifest_path = history_dir / f"{category}_enrichment_delta_manifest_{target_year}_{stamp}.json"
        current_output_path = current_dir / f"{category}_enrichment_apply_output_{target_year}.jsonl"
        current_summary_path = current_dir / f"{category}_enrichment_apply_summary_{target_year}.json"
        runtime_requests_path = runtime_dir / f"{category}_enrichment_requests_{target_year}.jsonl"
        diagnostics_path = diagnostics_dir / f"{category}_enrichment_delta_diagnostics_{target_year}_{stamp}.json"
        report_path = reports_dir / f"{category}_enrichment_delta_report_{target_year}_{stamp}.json"
    else:
        history_dir = get_enrichment_history_dir(category)
        history_output_path = get_enrichment_history_output_path(category, stamp, target_year)
        history_summary_path = get_enrichment_history_summary_path(category, stamp, target_year)
        history_manifest_path = history_dir / f"{category}_enrichment_delta_manifest_{target_year}_{stamp}.json"
        current_output_path = get_enrichment_current_output_path(category, target_year)
        current_summary_path = get_enrichment_current_summary_path(category, target_year)
        runtime_requests_path = get_enrichment_runtime_requests_path(category, target_year)
        diagnostics_path = history_dir / f"{category}_enrichment_delta_diagnostics_{target_year}_{stamp}.json"
        report_path = history_dir / f"{category}_enrichment_delta_report_{target_year}_{stamp}.json"
    return {
        "history_output_path": history_output_path,
        "history_summary_path": history_summary_path,
        "history_manifest_path": history_manifest_path,
        "current_output_path": current_output_path,
        "current_summary_path": current_summary_path,
        "runtime_requests_path": runtime_requests_path,
        "diagnostics_path": diagnostics_path,
        "report_path": report_path,
    }


def ensure_parent_dirs(paths: list[Path]) -> None:
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)


def serialize_paths(
    paths: dict[str, Path],
    *,
    dry_run: bool,
    emit_preview: bool,
    emit_diagnostics: bool,
    emit_reports: bool,
) -> dict[str, str]:
    out = {key: str(value) for key, value in paths.items()}
    if dry_run and not emit_preview:
        out["current_output_path"] = ""
        out["current_summary_path"] = ""
        out["runtime_requests_path"] = ""
    if not emit_diagnostics:
        out["diagnostics_path"] = ""
    if not emit_reports:
        out["report_path"] = ""
    return out


def apply_intentional_drops_to_output(
    rows: list[dict[str, Any]], normalized_drop_urls: set[str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    kept: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    for row in rows:
        source_url = str(row.get("source_url") or "").strip()
        if normalize_source_url_for_match(source_url) in normalized_drop_urls:
            dropped.append(deepcopy(row))
            continue
        kept.append(deepcopy(row))
    return kept, dropped


def apply_intentional_drops_to_requests(
    rows: list[dict[str, Any]], normalized_drop_urls: set[str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    kept: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    for row in rows:
        request_urls = [normalize_source_url_for_match(url) for url in collect_request_urls(row)]
        if any(url in normalized_drop_urls for url in request_urls):
            dropped.append(deepcopy(row))
            continue
        kept.append(deepcopy(row))
    return kept, dropped


def apply_localized_repairs(
    *,
    category: str,
    rows: list[dict[str, Any]],
    source_rows: list[dict[str, Any]],
    repairs: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    source_index = build_applied_index_from_rows(source_rows)
    working_rows = [deepcopy(row) for row in rows]
    row_index = {
        (
            str(row.get("request_id") or "").strip(),
            str(row.get("fair_slug") or "").strip(),
            str(row.get("text_hash") or "").strip(),
            normalize_source_url_for_match(str(row.get("source_url") or "")),
        ): idx
        for idx, row in enumerate(working_rows)
    }
    diagnostics: list[dict[str, Any]] = []
    for repair in repairs:
        request_id = str(repair.get("request_id") or "").strip()
        fair_slug = str(repair.get("fair_slug") or "").strip()
        text_hash = str(repair.get("text_hash") or "").strip()
        source_url = str(repair.get("source_url") or "").strip()
        source_url_norm = normalize_source_url_for_match(source_url)
        repair_mode = str(repair.get("repair_mode") or "").strip()
        key = (request_id, fair_slug, text_hash, source_url_norm)
        diagnostic = {
            "category": category,
            "request_id": request_id,
            "fair_slug": fair_slug,
            "text_hash": text_hash,
            "source_url": source_url,
            "source_url_normalized": source_url_norm,
            "repair_mode": repair_mode,
            "applied": False,
            "changed_fields": [],
            "diagnostics_metadata": deepcopy(repair.get("diagnostics_metadata") or {}),
        }
        if repair_mode not in SUPPORTED_REPAIR_MODES:
            diagnostic["disposition"] = "unsupported_repair_mode"
            diagnostics.append(diagnostic)
            continue
        source_row = source_index.get(key)
        if not source_row:
            diagnostic["disposition"] = "source_applied_row_not_found"
            diagnostics.append(diagnostic)
            continue
        row_pos = row_index.get(key)
        if row_pos is None:
            diagnostic["disposition"] = "target_row_not_found"
            diagnostics.append(diagnostic)
            continue
        target_row = working_rows[row_pos]
        changed_fields: list[str] = []
        for field_name in ("headline_ja", "summary_ja", "artist_name_kana"):
            new_value = str(source_row.get(field_name) or "")
            if str(target_row.get(field_name) or "") != new_value:
                target_row[field_name] = new_value
                changed_fields.append(field_name)
        target_row["enrich_notes"] = "localized_carry_forward_current_applied_row"
        diagnostic["applied"] = True
        diagnostic["changed_fields"] = changed_fields
        diagnostic["repair_source_status"] = str(source_row.get("status") or "")
        diagnostic["repair_source_enrich_mode"] = str(source_row.get("enrich_mode") or "")
        diagnostic["repair_source_summary_chars"] = len(str(source_row.get("summary_ja") or ""))
        diagnostic["disposition"] = "carry_forward_current_applied_row"
        diagnostics.append(diagnostic)
    return working_rows, diagnostics


def update_summary(
    *,
    summary: dict[str, Any],
    category: str,
    target_year: int,
    paths: dict[str, Path],
    manifest_path: Path,
    dry_run: bool,
    before_output_rows: int,
    after_output_rows: int,
    before_request_rows: int,
    after_request_rows: int,
    dropped_output_rows: list[dict[str, Any]],
    dropped_request_rows: list[dict[str, Any]],
    repair_diagnostics: list[dict[str, Any]],
) -> dict[str, Any]:
    out = deepcopy(summary)
    out["category"] = category
    out["target_year"] = target_year
    out["completed_at"] = utc_now_iso()
    out["execution_mode"] = "delta_promote"
    out["delta_mode"] = "no_reextraction_text_enrichment"
    out["delta_dry_run"] = bool(dry_run)
    out["delta_manifest_path"] = str(manifest_path)
    out["apply_output_path"] = str(paths["history_output_path"])
    out["apply_summary_path"] = str(paths["history_summary_path"])
    out["current_output_path"] = str(paths["current_output_path"])
    out["current_summary_path"] = str(paths["current_summary_path"])
    out["runtime_requests_path"] = str(paths["runtime_requests_path"])
    out["diagnostics_path"] = str(paths["diagnostics_path"])
    out["delta_before_output_rows"] = int(before_output_rows)
    out["delta_after_output_rows"] = int(after_output_rows)
    out["delta_before_runtime_request_rows"] = int(before_request_rows)
    out["delta_after_runtime_request_rows"] = int(after_request_rows)
    out["delta_intentional_drop_output_rows"] = len(dropped_output_rows)
    out["delta_intentional_drop_runtime_requests"] = len(dropped_request_rows)
    out["delta_localized_repair_targets"] = len(repair_diagnostics)
    out["delta_localized_repair_applied"] = sum(1 for item in repair_diagnostics if item.get("applied"))
    out["delta_localized_repair_changed_rows"] = sum(
        1 for item in repair_diagnostics if item.get("applied") and item.get("changed_fields")
    )
    out["total_applied"] = int(after_output_rows)
    out["promoted_to_current"] = False
    out["promote_verdict"] = "dry_run_only" if dry_run else "delta_promote_ready"
    return out


def build_category_report(
    *,
    category: str,
    paths: dict[str, Path],
    before_output_rows: list[dict[str, Any]],
    after_output_rows: list[dict[str, Any]],
    before_request_rows: list[dict[str, Any]],
    after_request_rows: list[dict[str, Any]],
    dropped_output_rows: list[dict[str, Any]],
    dropped_request_rows: list[dict[str, Any]],
    repair_diagnostics: list[dict[str, Any]],
    normalized_drop_urls: set[str],
) -> dict[str, Any]:
    before_urls = {str(row.get("request_id") or ""): str(row.get("source_url") or "") for row in before_output_rows}
    after_urls = {str(row.get("request_id") or ""): str(row.get("source_url") or "") for row in after_output_rows}
    removed_non_target = [
        {"request_id": req_id, "source_url": source_url}
        for req_id, source_url in before_urls.items()
        if req_id not in after_urls
        and normalize_source_url_for_match(source_url) not in normalized_drop_urls
    ]
    repaired_rows = [
        {
            "request_id": str(item.get("request_id") or ""),
            "source_url": str(item.get("source_url") or ""),
            "changed_fields": list(item.get("changed_fields") or []),
            "repair_mode": str(item.get("repair_mode") or ""),
            "disposition": str(item.get("disposition") or ""),
        }
        for item in repair_diagnostics
        if item.get("applied")
    ]
    return {
        "category": category,
        "history_output_path": str(paths["history_output_path"]),
        "history_summary_path": str(paths["history_summary_path"]),
        "history_manifest_path": str(paths["history_manifest_path"]),
        "current_output_path": str(paths["current_output_path"]),
        "current_summary_path": str(paths["current_summary_path"]),
        "runtime_requests_path": str(paths["runtime_requests_path"]),
        "diagnostics_path": str(paths["diagnostics_path"]),
        "report_path": str(paths["report_path"]),
        "before_output_rows": len(before_output_rows),
        "after_output_rows": len(after_output_rows),
        "before_runtime_request_rows": len(before_request_rows),
        "after_runtime_request_rows": len(after_request_rows),
        "dropped_output_rows": [
            {
                "request_id": str(row.get("request_id") or ""),
                "status": str(row.get("status") or ""),
                "source_url": str(row.get("source_url") or ""),
            }
            for row in dropped_output_rows
        ],
        "dropped_runtime_requests": [
            {
                "request_id": str(row.get("request_id") or ""),
                "source_urls": collect_request_urls(row),
            }
            for row in dropped_request_rows
        ],
        "localized_repair_applied": repaired_rows,
        "non_target_removed_rows": removed_non_target,
    }


def process_category(
    *,
    op: dict[str, Any],
    target_year: int,
    stamp: str,
    dry_run: bool,
    trial_root: Path,
    manifest_path: Path,
) -> dict[str, Any]:
    category = str(op.get("category") or "").strip()
    if category not in SUPPORTED_CATEGORIES:
        raise ValueError(f"Unsupported category in manifest: {category}")
    paths = build_paths(category=category, target_year=target_year, stamp=stamp, dry_run=dry_run, trial_root=trial_root)
    emit_preview = dry_run and is_optional_output_enabled("preview")
    emit_diagnostics = is_optional_output_enabled("diagnostics")
    emit_reports = is_optional_output_enabled("report")
    required_paths = [
        paths["history_output_path"],
        paths["history_summary_path"],
        paths["history_manifest_path"],
    ]
    if dry_run:
        if emit_preview:
            required_paths.extend(
                [
                    paths["current_output_path"],
                    paths["current_summary_path"],
                    paths["runtime_requests_path"],
                ]
            )
    else:
        required_paths.append(paths["runtime_requests_path"])
    if emit_diagnostics:
        required_paths.append(paths["diagnostics_path"])
    if emit_reports:
        required_paths.append(paths["report_path"])
    ensure_parent_dirs(required_paths)

    current_output_path = get_enrichment_current_output_path(category, target_year)
    current_summary_path = get_enrichment_current_summary_path(category, target_year)
    runtime_requests_path = get_enrichment_runtime_requests_path(category, target_year)

    current_output_rows = read_jsonl(current_output_path)
    current_summary = read_json(current_summary_path) if current_summary_path.exists() else {}
    runtime_request_rows = read_jsonl(runtime_requests_path) if runtime_requests_path.exists() else []

    normalized_drop_urls = {
        normalize_source_url_for_match(str(url or ""))
        for url in list(op.get("intentional_drop_urls") or [])
        if str(url or "").strip()
    }
    output_after_drop, dropped_output_rows = apply_intentional_drops_to_output(current_output_rows, normalized_drop_urls)
    requests_after_drop, dropped_request_rows = apply_intentional_drops_to_requests(runtime_request_rows, normalized_drop_urls)
    output_after_repair, repair_diagnostics = apply_localized_repairs(
        category=category,
        rows=output_after_drop,
        source_rows=current_output_rows,
        repairs=list(op.get("localized_repairs") or []),
    )

    summary = update_summary(
        summary=current_summary,
        category=category,
        target_year=target_year,
        paths=paths,
        manifest_path=manifest_path,
        dry_run=dry_run,
        before_output_rows=len(current_output_rows),
        after_output_rows=len(output_after_repair),
        before_request_rows=len(runtime_request_rows),
        after_request_rows=len(requests_after_drop),
        dropped_output_rows=dropped_output_rows,
        dropped_request_rows=dropped_request_rows,
        repair_diagnostics=repair_diagnostics,
    )
    if dry_run and not emit_preview:
        summary["current_output_path"] = ""
        summary["current_summary_path"] = ""
        summary["runtime_requests_path"] = ""
    if not emit_diagnostics:
        summary["diagnostics_path"] = ""
    diagnostics = {
        "category": category,
        "target_year": target_year,
        "delta_manifest_path": str(manifest_path),
        "intentional_drop_urls": list(op.get("intentional_drop_urls") or []),
        "dropped_output_rows": [
            {
                "request_id": str(row.get("request_id") or ""),
                "status": str(row.get("status") or ""),
                "source_url": str(row.get("source_url") or ""),
            }
            for row in dropped_output_rows
        ],
        "dropped_runtime_requests": [
            {
                "request_id": str(row.get("request_id") or ""),
                "source_urls": collect_request_urls(row),
            }
            for row in dropped_request_rows
        ],
        "localized_repairs": repair_diagnostics,
    }
    report = build_category_report(
        category=category,
        paths=paths,
        before_output_rows=current_output_rows,
        after_output_rows=output_after_repair,
        before_request_rows=runtime_request_rows,
        after_request_rows=requests_after_drop,
        dropped_output_rows=dropped_output_rows,
        dropped_request_rows=dropped_request_rows,
        repair_diagnostics=repair_diagnostics,
        normalized_drop_urls=normalized_drop_urls,
    )

    write_jsonl(paths["history_output_path"], output_after_repair)
    write_json(paths["history_summary_path"], summary)
    write_json(paths["history_manifest_path"], deepcopy(op))
    if not dry_run:
        write_jsonl(paths["runtime_requests_path"], requests_after_drop)
    if emit_diagnostics:
        write_json(paths["diagnostics_path"], diagnostics)
    if emit_reports:
        write_json(paths["report_path"], report)

    if dry_run:
        if emit_preview:
            write_jsonl(paths["current_output_path"], output_after_repair)
            write_json(paths["current_summary_path"], summary)
            write_jsonl(paths["runtime_requests_path"], requests_after_drop)
    else:
        promote_history_file_to_current(paths["history_output_path"], paths["current_output_path"])
        promote_history_file_to_current(paths["history_summary_path"], paths["current_summary_path"])
        summary["promoted_to_current"] = True
        summary["promote_verdict"] = "delta_promote_applied"
        write_json(paths["history_summary_path"], summary)
        write_json(paths["current_summary_path"], summary)

    visible_paths = serialize_paths(
        paths,
        dry_run=dry_run,
        emit_preview=emit_preview,
        emit_diagnostics=emit_diagnostics,
        emit_reports=emit_reports,
    )
    return {
        "category": category,
        "paths": visible_paths,
        "summary": summary,
        "diagnostics": diagnostics,
        "report": report,
    }


def validate_manifest(manifest: dict[str, Any]) -> tuple[int, list[dict[str, Any]]]:
    target_year = int(manifest.get("target_year") or 0)
    if target_year <= 0:
        raise ValueError("Manifest target_year is required.")
    operations = list(manifest.get("operations") or [])
    if not operations:
        raise ValueError("Manifest operations are required.")
    for op in operations:
        category = str(op.get("category") or "").strip()
        if category not in SUPPORTED_CATEGORIES:
            raise ValueError(f"Unsupported category in manifest: {category}")
        for repair in list(op.get("localized_repairs") or []):
            if str(repair.get("repair_mode") or "").strip() not in SUPPORTED_REPAIR_MODES:
                raise ValueError(f"Unsupported repair_mode: {repair.get('repair_mode')}")
    return target_year, operations


def filter_operations_by_category(
    operations: list[dict[str, Any]],
    category_filters: list[str],
) -> list[dict[str, Any]]:
    normalized = {str(value or "").strip() for value in category_filters if str(value or "").strip()}
    if not normalized:
        return list(operations)
    invalid = sorted(normalized - set(SUPPORTED_CATEGORIES))
    if invalid:
        raise ValueError(f"Unsupported category filter(s): {invalid}")
    filtered = [op for op in operations if str(op.get("category") or "").strip() in normalized]
    if not filtered:
        raise RuntimeError(f"category_filter_matched_no_operations:{sorted(normalized)}")
    return filtered


def execute_delta_promote_run(
    *,
    manifest_path: Path,
    target_year: int,
    operations: list[dict[str, Any]],
    trial_root: Path,
    apply: bool,
) -> dict[str, Any]:
    dry_run = not apply
    stamp = utc_now_compact()

    category_results = []
    for op in operations:
        category_results.append(
            process_category(
                op=op,
                target_year=target_year,
                stamp=stamp,
                dry_run=dry_run,
                trial_root=trial_root,
                manifest_path=manifest_path,
            )
        )

    run_report_path = ""
    if is_optional_output_enabled("report"):
        run_root = trial_root / stamp if dry_run else get_enrichment_history_dir("artists").parent / "_delta_runs" / stamp
        run_root.mkdir(parents=True, exist_ok=True)
        run_report = {
            "schema_name": "text_enrichment_delta_promote_run_report",
            "started_at": utc_now_iso(),
            "completed_at": utc_now_iso(),
            "dry_run": dry_run,
            "target_year": target_year,
            "manifest_path": str(manifest_path),
            "categories": category_results,
        }
        run_report_obj = run_root / "delta_promote_run_report.json"
        write_json(run_report_obj, run_report)
        run_report_path = str(run_report_obj)

    return {
        "dry_run": dry_run,
        "manifest_path": str(manifest_path),
        "run_report_path": run_report_path,
        "categories": category_results,
    }


def main() -> int:
    args = parse_args()
    require_delta_promote_approval(args)
    manifest_path = resolve_path(args.manifest)
    manifest = read_json(manifest_path)
    target_year, operations = validate_manifest(manifest)
    operations = filter_operations_by_category(operations, list(args.category or []))
    trial_root = resolve_path(args.trial_root)
    xlsx_path = resolve_path(args.xlsx_path)
    run_id = str(args.run_id or "").strip() or f"{DEFAULT_RUN_ID_PREFIX}_{utc_now_compact()}"
    targets = collect_manifest_scope_targets(operations, target_year)

    report = execute_closeout_with_breakdown_contract(
        contract_name="text_enrichment_delta_promote_with_breakdown",
        apply=bool(args.apply),
        run_id=run_id,
        xlsx_path=xlsx_path,
        target_year=target_year,
        targets=targets,
        current_write_callback=lambda apply: execute_delta_promote_run(
            manifest_path=manifest_path,
            target_year=target_year,
            operations=operations,
            trial_root=trial_root,
            apply=apply,
        ),
        r2_artifact_bundle=resolve_current_formal_artifact_bundle(
            bundle_name=f"{manifest_path.stem}_current_formal_artifacts",
            categories=resolve_r2_artifact_categories(operations),
            target_year=target_year,
        ),
    )
    print(json.dumps(report, ensure_ascii=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
