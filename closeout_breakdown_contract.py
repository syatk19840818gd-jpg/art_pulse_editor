#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gallery_skip_registry import (
    SKIPPED_GALLERIES_REGISTRY_PATH,
    SkipGalleryEntry,
    build_all_rag_zero_skip_entries,
    build_skip_lookup,
    is_all_rag_zero_target_row,
    load_skip_registry_entries,
    normalize_fair_slug,
    normalize_gallery_name,
    remove_skipped_from_gallery_list_csv,
    upsert_skip_registry_entries,
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
from run_r2_sync import (
    DEFAULT_CONFIG as DEFAULT_R2_CONFIG,
    DEFAULT_LOG_DIR as DEFAULT_R2_LOG_DIR,
    PlannedScopeRun,
    append_operation_log,
    apply_prune,
    apply_upload,
    build_r2_client,
    load_scope_config,
    run_plan,
    utc_now_iso,
    validate_sync_scope,
)
from run_rag_gallery_breakdown_update import (
    ScopeTarget as BreakdownScopeTarget,
    build_breakdown_update_report,
)

CurrentWriteCallback = Callable[[bool], dict[str, Any]]

BLOCK_ARTIFACT_CATEGORY_ARTIST = "artist"
BLOCK_ARTIFACT_CATEGORY_EXHIBITION = "exhibition"
BLOCK_ARTIFACT_CATEGORY_ARTIST_WORKS_IMAGES = "artist_works_images"
SUPPORTED_BLOCK_ARTIFACT_CATEGORIES = (
    BLOCK_ARTIFACT_CATEGORY_ARTIST,
    BLOCK_ARTIFACT_CATEGORY_EXHIBITION,
    BLOCK_ARTIFACT_CATEGORY_ARTIST_WORKS_IMAGES,
)
BLOCK_COMPLETION_REQUIRED_STAGES = (
    "current_write",
    "xlsx_update",
    "skip_registry_gallery_list_cleanup",
    "r2_sync",
)
CURRENT_FORMAL_ARTIFACTS_ROOT = Path("data/current")
GALLERY_LIST_PATHS_BY_FAIR = {
    "frieze_london": Path("data/gallery_lists/gallery_list_frieze_london.csv"),
    "liste": Path("data/gallery_lists/gallery_list_liste.csv"),
}
ALL_RAG_ZERO_SKIP_REASON = "all_rag_zero_auto_detected_in_block_closeout"
ALL_RAG_ZERO_SKIP_EVIDENCE = "derived_from_closeout_scope_stats_target_gallery_rows"


@dataclass(frozen=True)
class CurrentFormalArtifactGroup:
    group_key: str
    category: str
    description: str
    paths: tuple[Path, ...]
    required: bool = True


@dataclass(frozen=True)
class CurrentFormalArtifactBundle:
    bundle_name: str
    target_year: int
    categories: tuple[str, ...]
    groups: tuple[CurrentFormalArtifactGroup, ...]
    local_root: Path = CURRENT_FORMAL_ARTIFACTS_ROOT
    r2_prefix: str = CURRENT_FORMAL_ARTIFACTS_ROOT.as_posix()


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", str(value or "").strip()).strip("_").lower()
    return slug or "closeout_scope"


def _short_scope_name(*parts: str, suffix: str) -> str:
    raw = "_".join(str(part or "").strip() for part in parts if str(part or "").strip())
    base = _slugify(raw)
    digest = hashlib.sha256(base.encode("utf-8")).hexdigest()[:12]
    trimmed = base[:48].rstrip("_") or "closeout_scope"
    return f"{trimmed}_{suffix}_{digest}"


def _unique_categories(categories: Sequence[str]) -> tuple[str, ...]:
    ordered: list[str] = []
    seen: set[str] = set()
    for raw in categories:
        value = str(raw or "").strip()
        if not value:
            continue
        if value not in SUPPORTED_BLOCK_ARTIFACT_CATEGORIES:
            supported = ", ".join(SUPPORTED_BLOCK_ARTIFACT_CATEGORIES)
            raise ValueError(f"unsupported_block_artifact_category:{value} supported=[{supported}]")
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    if not ordered:
        raise ValueError("closeout_contract_requires_non_empty_artifact_categories")
    return tuple(ordered)


def _sorted_unique_paths(paths: Sequence[Path]) -> tuple[Path, ...]:
    dedup: dict[str, Path] = {}
    for path in paths:
        normalized = Path(path)
        dedup[normalized.as_posix()] = normalized
    return tuple(sorted(dedup.values(), key=lambda row: row.as_posix()))


def _artifact_group(
    *,
    group_key: str,
    category: str,
    description: str,
    paths: Sequence[Path],
    required: bool = True,
) -> CurrentFormalArtifactGroup:
    unique_paths = _sorted_unique_paths(paths)
    if not unique_paths:
        raise ValueError(f"artifact_group_requires_paths:{group_key}")
    return CurrentFormalArtifactGroup(
        group_key=group_key,
        category=category,
        description=description,
        paths=unique_paths,
        required=required,
    )


def _runtime_paths_as_paths(runtime_paths: dict[str, Path | str], keys: Sequence[str]) -> list[Path]:
    out: list[Path] = []
    for key in keys:
        value = runtime_paths.get(key)
        if value is None:
            raise KeyError(f"runtime_path_missing:{key}")
        out.append(Path(value))
    return out


def _collect_optional_vector_dir_group(
    *,
    group_key: str,
    description: str,
    dir_path: Path,
) -> CurrentFormalArtifactGroup | None:
    if not dir_path.exists() or not dir_path.is_dir():
        return None
    files = tuple(sorted((path for path in dir_path.rglob("*") if path.is_file()), key=lambda row: row.as_posix()))
    if not files:
        return None
    return CurrentFormalArtifactGroup(
        group_key=group_key,
        category=BLOCK_ARTIFACT_CATEGORY_EXHIBITION,
        description=description,
        paths=files,
        required=True,
    )


def resolve_current_formal_artifact_bundle(
    *,
    bundle_name: str,
    categories: Sequence[str],
    target_year: int = TARGET_YEAR,
) -> CurrentFormalArtifactBundle:
    resolved_categories = _unique_categories(categories)
    groups: list[CurrentFormalArtifactGroup] = []

    if BLOCK_ARTIFACT_CATEGORY_ARTIST in resolved_categories:
        groups.extend(
            [
                _artifact_group(
                    group_key="artist_raw",
                    category=BLOCK_ARTIFACT_CATEGORY_ARTIST,
                    description="Artist current raw artifacts.",
                    paths=tuple(get_current_raw_paths("artists", target_year).values()),
                ),
                _artifact_group(
                    group_key="artist_image_metadata",
                    category=BLOCK_ARTIFACT_CATEGORY_ARTIST,
                    description="Artist current image metadata artifacts.",
                    paths=tuple(get_current_artist_image_meta_paths().values()),
                ),
                _artifact_group(
                    group_key="artist_enrichment",
                    category=BLOCK_ARTIFACT_CATEGORY_ARTIST,
                    description="Artist current enrichment output and summary.",
                    paths=(
                        get_enrichment_current_output_path("artists", target_year),
                        get_enrichment_current_summary_path("artists", target_year),
                    ),
                ),
                _artifact_group(
                    group_key="artist_text_vector",
                    category=BLOCK_ARTIFACT_CATEGORY_ARTIST,
                    description="Artist current text vector artifacts.",
                    paths=_runtime_paths_as_paths(
                        get_current_artist_text_vector_runtime_paths(target_year=target_year),
                        ("meta", "index", "manifest", "failed", "summary"),
                    ),
                ),
            ]
        )

    if BLOCK_ARTIFACT_CATEGORY_ARTIST_WORKS_IMAGES in resolved_categories:
        groups.append(
            _artifact_group(
                group_key="artist_works_images_vector",
                category=BLOCK_ARTIFACT_CATEGORY_ARTIST_WORKS_IMAGES,
                description="Artist Works Images current OpenCLIP artifacts.",
                paths=_runtime_paths_as_paths(
                    get_current_artist_works_vector_runtime_paths(target_year=target_year),
                    ("embeddings", "id_map", "index", "manifest", "failed", "summary"),
                ),
            )
        )

    if BLOCK_ARTIFACT_CATEGORY_EXHIBITION in resolved_categories:
        groups.extend(
            [
                _artifact_group(
                    group_key="exhibition_raw",
                    category=BLOCK_ARTIFACT_CATEGORY_EXHIBITION,
                    description="Exhibition current raw artifacts.",
                    paths=tuple(get_current_raw_paths("exhibitions", target_year).values()),
                ),
                _artifact_group(
                    group_key="exhibition_image_metadata",
                    category=BLOCK_ARTIFACT_CATEGORY_EXHIBITION,
                    description="Exhibition current image metadata artifacts.",
                    paths=tuple(get_current_exhibitions_image_meta_paths(target_year).values()),
                ),
                _artifact_group(
                    group_key="exhibition_enrichment",
                    category=BLOCK_ARTIFACT_CATEGORY_EXHIBITION,
                    description="Exhibition current enrichment output and summary.",
                    paths=(
                        get_enrichment_current_output_path("exhibitions", target_year),
                        get_enrichment_current_summary_path("exhibitions", target_year),
                    ),
                ),
            ]
        )
        optional_groups = [
            _collect_optional_vector_dir_group(
                group_key="exhibition_text_vector_optional",
                description="Optional exhibition current text/vector artifacts.",
                dir_path=CURRENT_FORMAL_ARTIFACTS_ROOT / "vector" / "exhibitions",
            ),
            _collect_optional_vector_dir_group(
                group_key="exhibition_image_vector_optional",
                description="Optional exhibition current image/vector artifacts.",
                dir_path=CURRENT_FORMAL_ARTIFACTS_ROOT / "vector" / "exhibition_works_images",
            ),
        ]
        groups.extend([group for group in optional_groups if group is not None])

    dedup_group_keys: set[str] = set()
    for group in groups:
        if group.group_key in dedup_group_keys:
            raise ValueError(f"duplicate_artifact_group_key:{group.group_key}")
        dedup_group_keys.add(group.group_key)

    return CurrentFormalArtifactBundle(
        bundle_name=str(bundle_name or "").strip() or "block_closeout_current_formal_artifacts",
        target_year=int(target_year),
        categories=resolved_categories,
        groups=tuple(groups),
    )


def _load_default_r2_global_excludes() -> list[str]:
    _scopes, global_excludes, _raw = load_scope_config(DEFAULT_R2_CONFIG)
    return list(global_excludes)


def _effective_global_excludes_for_local_root(local_root: Path) -> list[str]:
    excludes = _load_default_r2_global_excludes()
    lowered_parts = {str(part).casefold() for part in Path(local_root).parts}
    filtered: list[str] = []
    for pattern in excludes:
        lowered_pattern = str(pattern).casefold()
        if "_trial" in lowered_parts and "_trial" in lowered_pattern:
            continue
        if "_trash" in lowered_parts and "_trash" in lowered_pattern:
            continue
        filtered.append(pattern)
    return filtered


def _bundle_paths(bundle: CurrentFormalArtifactBundle) -> tuple[Path, ...]:
    return _sorted_unique_paths([path for group in bundle.groups for path in group.paths])


def _paths_relative_to_bundle_root(paths: Sequence[Path], local_root: Path) -> tuple[str, ...]:
    rels: list[str] = []
    bundle_root = Path(local_root).resolve()
    for path in paths:
        resolved = path.resolve()
        try:
            rel = resolved.relative_to(bundle_root).as_posix()
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"closeout_r2_path_outside_bundle_root:{path}") from exc
        rels.append(rel)
    return tuple(sorted(dict.fromkeys(rels)))


def build_closeout_r2_scope_payload(
    *,
    bundle: CurrentFormalArtifactBundle,
    scope_name: str,
    description: str,
) -> dict[str, Any]:
    include_globs = list(_paths_relative_to_bundle_root(_bundle_paths(bundle), bundle.local_root))
    if not include_globs:
        raise ValueError("closeout_r2_scope_requires_paths")
    return {
        "version": "v3",
        "global_exclude_globs": _effective_global_excludes_for_local_root(bundle.local_root),
        "scopes": {
            scope_name: {
                "description": description,
                "enabled_by_default": False,
                "sync_mode": "mirror",
                "targets": [
                    {
                        "local_root": Path(bundle.local_root).as_posix(),
                        "r2_prefix": str(bundle.r2_prefix or CURRENT_FORMAL_ARTIFACTS_ROOT.as_posix()),
                        "include_globs": include_globs,
                        "exclude_globs": [],
                    }
                ],
            }
        },
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _build_group_reports(bundle: CurrentFormalArtifactBundle) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for group in bundle.groups:
        existing = [path.as_posix() for path in group.paths if path.exists()]
        missing = [path.as_posix() for path in group.paths if not path.exists()]
        reports.append(
            {
                "group_key": group.group_key,
                "category": group.category,
                "description": group.description,
                "required": group.required,
                "file_total": len(group.paths),
                "existing_file_total": len(existing),
                "missing_file_total": len(missing),
                "paths": [path.as_posix() for path in group.paths],
                "missing_paths": missing,
            }
        )
    return reports


def _map_r2_keys_to_groups(bundle: CurrentFormalArtifactBundle) -> dict[str, dict[str, str]]:
    mapping: dict[str, dict[str, str]] = {}
    r2_prefix = str(bundle.r2_prefix or CURRENT_FORMAL_ARTIFACTS_ROOT.as_posix()).rstrip("/")
    for group in bundle.groups:
        for rel in _paths_relative_to_bundle_root(group.paths, bundle.local_root):
            r2_key = f"{r2_prefix}/{rel}".replace("//", "/")
            mapping[r2_key] = {"group_key": group.group_key, "category": group.category}
    return mapping


def _build_r2_stage_base_report(
    *,
    bundle: CurrentFormalArtifactBundle,
    config_path: Path,
    scope_name: str,
    description: str,
    apply: bool,
) -> dict[str, Any]:
    group_reports = _build_group_reports(bundle)
    category_file_counts = Counter()
    for group in bundle.groups:
        category_file_counts[group.category] += len(group.paths)
    missing_required_paths = [
        path.as_posix()
        for group in bundle.groups
        if group.required
        for path in group.paths
        if not path.exists()
    ]
    return {
        "required_for_block_completion": True,
        "source_of_truth": "current_formal_artifacts",
        "mode": "apply" if apply else "dry_run",
        "status": "planned" if not apply else "pending_apply",
        "scope_name": scope_name,
        "scope_description": description,
        "scope_config_path": config_path.as_posix(),
        "bundle_name": bundle.bundle_name,
        "bundle_categories": list(bundle.categories),
        "artifact_group_total": len(bundle.groups),
        "artifact_file_total": sum(len(group.paths) for group in bundle.groups),
        "category_file_counts": dict(category_file_counts),
        "artifact_groups": group_reports,
        "required_paths_missing": missing_required_paths,
        "scope_contamination_count": 0,
        "scope_contamination_entries": [],
    }


def execute_closeout_r2_contract(
    *,
    bundle: CurrentFormalArtifactBundle,
    apply: bool,
    run_id: str,
    contract_name: str,
    log_dir: Path = DEFAULT_R2_LOG_DIR,
    max_delete: int = 0,
    execute_remote: bool = True,
) -> dict[str, Any]:
    log_dir = Path(log_dir)
    scope_name = _short_scope_name(contract_name, bundle.bundle_name, suffix="r2")
    description = (
        f"Block closeout required R2 sync for {bundle.bundle_name}. "
        "Current formal artifacts only; xlsx is intentionally excluded."
    )
    config_path = log_dir / f"r2_sync_targets_{scope_name}.json"
    payload = build_closeout_r2_scope_payload(
        bundle=bundle,
        scope_name=scope_name,
        description=description,
    )
    _write_json(config_path, payload)

    report = _build_r2_stage_base_report(
        bundle=bundle,
        config_path=config_path,
        scope_name=scope_name,
        description=description,
        apply=apply,
    )
    if report["required_paths_missing"]:
        report["status"] = "blocked_missing_required_paths"
        return report

    if not execute_remote:
        report["remote_plan_executed"] = False
        report["status"] = "planned" if not apply else "blocked_apply_requires_remote_sync"
        return report

    scopes, global_excludes, _raw = load_scope_config(config_path)
    scope = scopes[scope_name]
    plan_payload, local_objects, would_upload, would_prune, _prune_fp = run_plan(
        scope=scope,
        global_excludes=global_excludes,
        config_path=config_path,
        log_dir=log_dir,
        run_id=run_id,
        command="sync" if apply else "plan",
    )
    bundle_key_map = _map_r2_keys_to_groups(bundle)
    contamination_entries = [
        row
        for row in [*would_upload, *would_prune]
        if str(row.get("r2_key", "")) not in bundle_key_map
    ]
    would_upload_by_category = Counter()
    for row in would_upload:
        key = str(row.get("r2_key", ""))
        meta = bundle_key_map.get(key)
        if meta is not None:
            would_upload_by_category[meta["category"]] += 1
    report["scope_contamination_count"] = len(contamination_entries)
    report["scope_contamination_entries"] = contamination_entries
    report["plan"] = {
        "plan_log_path": plan_payload["plan_log_path"],
        "local_count": int(plan_payload.get("local_stats", {}).get("local_count", 0)),
        "roots_missing": list(plan_payload.get("local_stats", {}).get("roots_missing", [])),
        "would_upload_count": len(would_upload),
        "would_prune_count": len(would_prune),
        "would_upload_by_category": dict(would_upload_by_category),
        "scope_hash": str(plan_payload.get("scope_hash", "")),
        "input_fingerprint": str(plan_payload.get("input_fingerprint", "")),
        "code_fingerprint": str(plan_payload.get("code_fingerprint", "")),
        "would_upload": would_upload,
        "would_prune": would_prune,
    }

    if not apply:
        report["remote_plan_executed"] = True
        report["status"] = "planned"
        return report

    planned_scope = PlannedScopeRun(
        scope=scope,
        scope_run_id=run_id,
        plan_payload=plan_payload,
        local_objects=local_objects,
        would_upload=would_upload,
        would_prune=would_prune,
    )
    blocking_errors = validate_sync_scope(
        planned_scope,
        max_delete=int(max_delete),
        confirm_mirror=False,
    )
    if contamination_entries:
        blocking_errors.append(f"scope_contamination_detected:{len(contamination_entries)}")
    if blocking_errors:
        report["status"] = "blocked"
        report["blocking_errors"] = blocking_errors
        return report

    client, bucket = build_r2_client()
    local_by_key = {row.r2_key: row for row in local_objects}
    uploaded: list[dict[str, Any]] = []
    upload_failed: list[dict[str, Any]] = []
    deleted: list[dict[str, Any]] = []
    delete_failed: list[dict[str, Any]] = []
    delete_policy = ""

    if scope.uploads_enabled:
        uploaded, upload_failed = apply_upload(
            client=client,
            bucket=bucket,
            local_by_key=local_by_key,
            would_upload=would_upload,
        )

    if scope.deletes_enabled:
        if scope.sync_mode == "mirror" and upload_failed:
            delete_policy = "skipped_due_upload_failures"
        elif would_prune:
            deleted, delete_failed = apply_prune(
                client=client,
                bucket=bucket,
                would_prune=would_prune,
            )
            delete_policy = "mirror_apply"
        else:
            delete_policy = "no_delete_candidates"
    else:
        delete_policy = "delete_opt_out_upload_only"

    apply_payload = {
        "artifact_kind": "r2_sync_apply",
        "schema_version": "v2",
        "generated_at": utc_now_iso(),
        "scope": scope.name,
        "run_id": run_id,
        "bucket": bucket,
        "sync_mode": scope.sync_mode,
        "plan_log_path": plan_payload["plan_log_path"],
        "local_roots_missing": list(plan_payload.get("local_stats", {}).get("roots_missing", [])),
        "would_upload_count": len(would_upload),
        "would_delete_count": len(would_prune),
        "would_prune_count": len(would_prune),
        "uploaded_count": len(uploaded),
        "upload_failed_count": len(upload_failed),
        "deleted_count": len(deleted),
        "delete_failed_count": len(delete_failed),
        "delete_policy": delete_policy,
        "uploaded": uploaded,
        "upload_failed": upload_failed,
        "deleted": deleted,
        "delete_failed": delete_failed,
    }
    apply_log_path = log_dir / f"r2_sync_apply_{scope.name}_{run_id}.json"
    append_operation_log(apply_log_path, apply_payload)

    postcheck_run_id = f"{run_id}_postcheck"
    post_plan_payload, _post_objects, post_would_upload, post_would_prune, _post_fp = run_plan(
        scope=scope,
        global_excludes=global_excludes,
        config_path=config_path,
        log_dir=log_dir,
        run_id=postcheck_run_id,
        command="plan",
    )
    report["apply"] = {
        "apply_log_path": apply_log_path.as_posix(),
        "uploaded_count": len(uploaded),
        "deleted_count": len(deleted),
        "upload_failed_count": len(upload_failed),
        "delete_failed_count": len(delete_failed),
        "delete_policy": delete_policy,
        "uploaded": uploaded,
        "deleted": deleted,
    }
    report["post_check"] = {
        "plan_log_path": post_plan_payload["plan_log_path"],
        "would_upload_count": len(post_would_upload),
        "would_prune_count": len(post_would_prune),
        "roots_missing": list(post_plan_payload.get("local_stats", {}).get("roots_missing", [])),
        "scope_hash": str(post_plan_payload.get("scope_hash", "")),
        "input_fingerprint": str(post_plan_payload.get("input_fingerprint", "")),
    }
    report["status"] = "applied"
    if upload_failed or delete_failed or post_would_upload or post_would_prune:
        report["status"] = "applied_with_followup_required"
    return report


def _derive_block_completion_status(
    *,
    apply: bool,
    current_write_status: str,
    xlsx_update_status: str,
    skip_registry_gallery_list_cleanup_status: str,
    r2_sync_status: str,
) -> str:
    if apply:
        if (
            current_write_status == "applied"
            and xlsx_update_status == "applied"
            and skip_registry_gallery_list_cleanup_status == "applied"
            and r2_sync_status == "applied"
        ):
            return "completed"
        return "blocked_or_followup_required"
    if (
        current_write_status == "planned"
        and xlsx_update_status == "planned"
        and skip_registry_gallery_list_cleanup_status in {"planned", "planned_contract_only"}
        and r2_sync_status in {"planned", "planned_contract_only"}
    ):
        return "planned"
    return "blocked"


def _default_stage_status(*, apply: bool) -> str:
    return "applied" if apply else "planned"


def _resolve_stage_status(report: dict[str, Any], *, apply: bool) -> str:
    status = str(report.get("status") or "").strip()
    if status:
        return status
    return _default_stage_status(apply=apply)


def _stage_allows_downstream(status: str, *, apply: bool) -> bool:
    if apply:
        return status == "applied"
    return status in {"planned", "planned_contract_only"}


def _blocked_stage_report(*, stage_name: str, reason: str, upstream: dict[str, str]) -> dict[str, Any]:
    return {
        "stage": stage_name,
        "status": "blocked_prereq_failed",
        "blocking_reason": reason,
        "upstream_statuses": dict(upstream),
    }


def _merge_skip_entry(*, current: SkipGalleryEntry, incoming: SkipGalleryEntry) -> SkipGalleryEntry:
    return SkipGalleryEntry(
        fair_slug=incoming.fair_slug or current.fair_slug,
        gallery_name_en=incoming.gallery_name_en or current.gallery_name_en,
        skip_reason=incoming.skip_reason or current.skip_reason,
        detected_at=incoming.detected_at or current.detected_at,
        run_id=incoming.run_id or current.run_id,
        source_scope_file=incoming.source_scope_file or current.source_scope_file,
        evidence=incoming.evidence or current.evidence,
    )


def _build_skip_registry_plan(
    *,
    existing_entries: Sequence[SkipGalleryEntry],
    new_entries: Sequence[SkipGalleryEntry],
    registry_path: Path,
) -> tuple[dict[str, Any], list[SkipGalleryEntry]]:
    registry: dict[tuple[str, str], SkipGalleryEntry] = {entry.scope_key: entry for entry in existing_entries}
    planned_entries: list[dict[str, Any]] = []
    added = 0
    updated = 0
    unchanged = 0
    for entry in new_entries:
        fair_slug, gallery_key = entry.scope_key
        if not gallery_key:
            continue
        key = (fair_slug, gallery_key)
        current = registry.get(key)
        action = "add"
        merged = entry
        if current is None:
            added += 1
        else:
            merged = _merge_skip_entry(current=current, incoming=entry)
            if merged == current:
                action = "unchanged"
                unchanged += 1
            else:
                action = "update"
                updated += 1
        registry[key] = merged
        planned_entries.append({"action": action, **merged.to_row()})
    final_entries = sorted(
        registry.values(),
        key=lambda item: (
            normalize_fair_slug(item.fair_slug),
            normalize_gallery_name(item.gallery_name_en),
        ),
    )
    return (
        {
            "status": "planned",
            "registry_path": str(registry_path),
            "detected_entry_total": len(new_entries),
            "planned_entry_total": len(planned_entries),
            "planned_added": added,
            "planned_updated": updated,
            "planned_unchanged": unchanged,
            "planned_total_after": len(final_entries),
            "entries": planned_entries,
        },
        final_entries,
    )


def _extract_target_gallery_rows_from_xlsx_report(xlsx_report: dict[str, Any]) -> list[dict[str, Any]]:
    source_validation = xlsx_report.get("source_validation")
    if not isinstance(source_validation, dict):
        return []
    raw_rows = source_validation.get("target_gallery_rows")
    if not isinstance(raw_rows, list):
        return []
    rows: list[dict[str, Any]] = []
    for raw in raw_rows:
        if not isinstance(raw, dict):
            continue
        fair_slug = normalize_fair_slug(str(raw.get("fair_slug") or ""))
        gallery_name_en = str(raw.get("gallery_name_en") or "").strip()
        if not fair_slug or not gallery_name_en:
            continue
        row = dict(raw)
        row["fair_slug"] = fair_slug
        row["gallery_name_en"] = gallery_name_en
        rows.append(row)
    return rows


def execute_skip_registry_gallery_list_cleanup_contract(
    *,
    apply: bool,
    run_id: str,
    current_write_report: dict[str, Any],
    xlsx_report: dict[str, Any],
) -> dict[str, Any]:
    mode = "apply" if apply else "dry_run"
    target_gallery_rows = _extract_target_gallery_rows_from_xlsx_report(xlsx_report)
    all_rag_zero_detected_rows = [row for row in target_gallery_rows if is_all_rag_zero_target_row(row)]
    source_scope_file = str(current_write_report.get("targets_file") or "").strip()
    new_entries = build_all_rag_zero_skip_entries(
        target_gallery_rows=all_rag_zero_detected_rows,
        skip_reason=ALL_RAG_ZERO_SKIP_REASON,
        run_id=str(run_id),
        source_scope_file=source_scope_file,
        evidence=ALL_RAG_ZERO_SKIP_EVIDENCE,
    )
    existing_entries = load_skip_registry_entries(SKIPPED_GALLERIES_REGISTRY_PATH)
    skip_registry_plan, planned_registry_entries = _build_skip_registry_plan(
        existing_entries=existing_entries,
        new_entries=new_entries,
        registry_path=SKIPPED_GALLERIES_REGISTRY_PATH,
    )
    planned_lookup = build_skip_lookup(planned_registry_entries)
    target_fair_slugs = sorted(
        {
            normalize_fair_slug(str(row.get("fair_slug") or ""))
            for row in all_rag_zero_detected_rows
            if str(row.get("fair_slug") or "").strip()
        }
    )
    gallery_list_removal_plan: list[dict[str, Any]] = []
    for fair_slug in target_fair_slugs:
        gallery_list_path = GALLERY_LIST_PATHS_BY_FAIR.get(fair_slug)
        if gallery_list_path is None:
            gallery_list_removal_plan.append(
                {
                    "mode": "dry_run",
                    "status": "blocked_missing_gallery_list_path",
                    "gallery_list_path": "",
                    "fair_slug": fair_slug,
                    "removed_count": 0,
                    "removed_galleries": [],
                    "rows_before": 0,
                    "rows_after": 0,
                    "changed": False,
                    "would_write": False,
                    "missing": True,
                }
            )
            continue
        gallery_list_removal_plan.append(
            remove_skipped_from_gallery_list_csv(
                path=gallery_list_path,
                fair_slug=fair_slug,
                lookup=planned_lookup,
                apply=False,
            )
        )
    plan_blocking_errors = [
        f"gallery_list_cleanup_blocked:{item.get('fair_slug', '')}"
        for item in gallery_list_removal_plan
        if str(item.get("status") or "").startswith("blocked")
    ]
    stage_status = "applied" if apply else "planned"
    skip_registry_apply: dict[str, Any] = {
        "status": "applied" if apply else "planned",
        "registry_path": str(SKIPPED_GALLERIES_REGISTRY_PATH),
        "added": 0,
        "updated": 0,
        "unchanged": len(new_entries),
        "total": len(existing_entries),
    }
    gallery_list_removal_apply: list[dict[str, Any]] = []
    apply_blocking_errors: list[str] = []
    if plan_blocking_errors:
        stage_status = "blocked_missing_gallery_list_path"
        apply_blocking_errors.extend(plan_blocking_errors)
    elif apply:
        try:
            if new_entries:
                skip_registry_apply = upsert_skip_registry_entries(SKIPPED_GALLERIES_REGISTRY_PATH, new_entries)
                skip_registry_apply["status"] = "applied"
            apply_lookup = build_skip_lookup(load_skip_registry_entries(SKIPPED_GALLERIES_REGISTRY_PATH))
            for fair_slug in target_fair_slugs:
                gallery_list_path = GALLERY_LIST_PATHS_BY_FAIR.get(fair_slug)
                if gallery_list_path is None:
                    continue
                gallery_list_removal_apply.append(
                    remove_skipped_from_gallery_list_csv(
                        path=gallery_list_path,
                        fair_slug=fair_slug,
                        lookup=apply_lookup,
                        apply=True,
                    )
                )
            apply_blocking_errors.extend(
                [
                    f"gallery_list_cleanup_apply_blocked:{item.get('fair_slug', '')}"
                    for item in gallery_list_removal_apply
                    if str(item.get("status") or "").startswith("blocked")
                ]
            )
            if apply_blocking_errors:
                stage_status = "blocked_gallery_list_cleanup_apply_failed"
            else:
                stage_status = "applied"
        except Exception as exc:  # noqa: BLE001
            stage_status = "blocked_skip_registry_gallery_list_cleanup_exception"
            apply_blocking_errors.append(f"skip_registry_gallery_list_cleanup_exception:{exc}")

    return {
        "stage": "skip_registry_gallery_list_cleanup",
        "mode": mode,
        "status": stage_status,
        "registry_path": str(SKIPPED_GALLERIES_REGISTRY_PATH),
        "skip_reason": ALL_RAG_ZERO_SKIP_REASON,
        "skip_evidence": ALL_RAG_ZERO_SKIP_EVIDENCE,
        "source_scope_file": source_scope_file,
        "target_gallery_row_total": len(target_gallery_rows),
        "all_rag_zero_detected_count": len(all_rag_zero_detected_rows),
        "all_rag_zero_detected_rows": all_rag_zero_detected_rows,
        "skip_registry_plan": skip_registry_plan,
        "gallery_list_removal_plan": gallery_list_removal_plan,
        "skip_registry_apply": skip_registry_apply if apply else {},
        "gallery_list_removal_apply": gallery_list_removal_apply if apply else [],
        "blocking_errors": apply_blocking_errors,
    }


def execute_closeout_with_breakdown_contract(
    *,
    contract_name: str,
    apply: bool,
    run_id: str,
    xlsx_path: Path,
    target_year: int,
    targets: Sequence[BreakdownScopeTarget],
    current_write_callback: CurrentWriteCallback,
    breakdown_stats_override: dict[tuple[str, str], Any] | None = None,
    r2_artifact_bundle: CurrentFormalArtifactBundle,
    r2_log_dir: Path = DEFAULT_R2_LOG_DIR,
    r2_max_delete: int = 0,
    r2_execute_remote: bool = True,
) -> dict[str, Any]:
    ordered_targets = list(targets)
    if not ordered_targets:
        raise ValueError("closeout_contract_requires_non_empty_targets")

    current_write_report = current_write_callback(bool(apply))
    current_write_status = _resolve_stage_status(current_write_report, apply=bool(apply))

    if _stage_allows_downstream(current_write_status, apply=bool(apply)):
        xlsx_report = build_breakdown_update_report(
            targets=ordered_targets,
            xlsx_path=Path(xlsx_path),
            target_year=int(target_year),
            run_id=str(run_id),
            apply=bool(apply),
            stats=None if apply else breakdown_stats_override,
        )
    else:
        xlsx_report = _blocked_stage_report(
            stage_name="xlsx_update",
            reason=f"current_write_status:{current_write_status}",
            upstream={"current_write_status": current_write_status},
        )
    xlsx_update_status = _resolve_stage_status(xlsx_report, apply=bool(apply))

    if _stage_allows_downstream(current_write_status, apply=bool(apply)) and _stage_allows_downstream(
        xlsx_update_status,
        apply=bool(apply),
    ):
        skip_registry_gallery_list_cleanup_report = execute_skip_registry_gallery_list_cleanup_contract(
            apply=bool(apply),
            run_id=str(run_id),
            current_write_report=current_write_report,
            xlsx_report=xlsx_report,
        )
    else:
        blocked_by = "xlsx_update" if not _stage_allows_downstream(xlsx_update_status, apply=bool(apply)) else "current_write"
        blocked_status = xlsx_update_status if blocked_by == "xlsx_update" else current_write_status
        skip_registry_gallery_list_cleanup_report = _blocked_stage_report(
            stage_name="skip_registry_gallery_list_cleanup",
            reason=f"{blocked_by}_status:{blocked_status}",
            upstream={
                "current_write_status": current_write_status,
                "xlsx_update_status": xlsx_update_status,
            },
        )
    skip_registry_gallery_list_cleanup_status = _resolve_stage_status(
        skip_registry_gallery_list_cleanup_report,
        apply=bool(apply),
    )

    if (
        _stage_allows_downstream(current_write_status, apply=bool(apply))
        and _stage_allows_downstream(xlsx_update_status, apply=bool(apply))
        and _stage_allows_downstream(skip_registry_gallery_list_cleanup_status, apply=bool(apply))
    ):
        r2_report = execute_closeout_r2_contract(
            bundle=r2_artifact_bundle,
            apply=bool(apply),
            run_id=str(run_id),
            contract_name=str(contract_name),
            log_dir=Path(r2_log_dir),
            max_delete=int(r2_max_delete),
            execute_remote=bool(r2_execute_remote),
        )
    else:
        if not _stage_allows_downstream(skip_registry_gallery_list_cleanup_status, apply=bool(apply)):
            blocked_by = "skip_registry_gallery_list_cleanup"
            blocked_status = skip_registry_gallery_list_cleanup_status
        elif not _stage_allows_downstream(xlsx_update_status, apply=bool(apply)):
            blocked_by = "xlsx_update"
            blocked_status = xlsx_update_status
        else:
            blocked_by = "current_write"
            blocked_status = current_write_status
        r2_report = _blocked_stage_report(
            stage_name="r2_sync",
            reason=f"{blocked_by}_status:{blocked_status}",
            upstream={
                "current_write_status": current_write_status,
                "xlsx_update_status": xlsx_update_status,
                "skip_registry_gallery_list_cleanup_status": skip_registry_gallery_list_cleanup_status,
            },
        )
    r2_sync_status = str(r2_report.get("status", "")).strip() or "unknown"
    block_completion_status = _derive_block_completion_status(
        apply=bool(apply),
        current_write_status=current_write_status,
        xlsx_update_status=xlsx_update_status,
        skip_registry_gallery_list_cleanup_status=skip_registry_gallery_list_cleanup_status,
        r2_sync_status=r2_sync_status,
    )

    return {
        "contract": {
            "name": str(contract_name or "").strip() or "closeout_with_breakdown_contract",
            "mode": "apply" if apply else "dry_run",
            "run_id": str(run_id),
            "target_year": int(target_year),
            "target_total": len(ordered_targets),
            "targets": [target.to_dict() for target in ordered_targets],
            "block_completion_requires": list(BLOCK_COMPLETION_REQUIRED_STAGES),
            "block_completion_status": block_completion_status,
            "current_write_status": current_write_status,
            "xlsx_update_status": xlsx_update_status,
            "skip_registry_gallery_list_cleanup_status": skip_registry_gallery_list_cleanup_status,
            "r2_sync_status": r2_sync_status,
            "xlsx_path": str(Path(xlsx_path)),
            "xlsx_source_of_truth": "current_formal_artifacts",
            "r2_source_of_truth": "current_formal_artifacts",
            "r2_categories": list(r2_artifact_bundle.categories),
            "r2_sync_required_for_block_completion": True,
        },
        "current_write": current_write_report,
        "xlsx_update": xlsx_report,
        "skip_registry_gallery_list_cleanup": skip_registry_gallery_list_cleanup_report,
        "r2_sync": r2_report,
    }
