#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from itertools import zip_longest
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
    get_artist_image_cache_dir,
    get_current_artist_image_meta_paths,
    get_current_artist_text_vector_runtime_paths,
    get_current_artist_works_vector_runtime_paths,
    get_current_exhibitions_image_meta_paths,
    get_current_raw_paths,
    get_enrichment_current_output_path,
    get_enrichment_current_summary_path,
    get_exhibition_image_cache_dir,
    get_image_r2_key,
    normalize_image_local_path_text,
    resolve_image_local_path,
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
from run_phase1_seed10_artist_image_collect import (
    image_visual_dedupe_key,
    image_visual_signature,
    is_contextual_near_duplicate_visual_signature,
    normalize_image_url_base_identity_for_dedupe,
)

DEFAULT_RUN_ID_PREFIX = "TASK_PHASE3_BLOCK_CLOSEOUT"
DEFAULT_PLAN_ROOT_DIR = Path("_trial")
FORMAL_REQUIRED_R2_SCOPE_NAME = "current_required_rag_full"
FORMAL_REQUIRED_R2_SEQUENCE = [
    "current_required_rag_full_plan",
    "current_required_rag_full_apply",
    "current_required_rag_full_postcheck",
]
FORMAL_REQUIRED_R2_SUCCESS_CRITERIA = [
    "missing local->R2 = 0",
    "remote_only = 0",
    "size_mismatch = 0",
]
BLOCK_CLOSEOUT_FLOW = [
    "current_write",
    "exhibition_images_current",
    "artist_works_images_duplicate_audit",
    "skip_registry_gallery_list_cleanup",
    "xlsx_update",
    "artist_works_images_openclip_current",
    "workbook_human_confirmation",
    *FORMAL_REQUIRED_R2_SEQUENCE,
    "closeout_report",
    "docs_sync",
    "next_block_restart_decision",
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
            "xlsx update, Artist Works Images OpenCLIP current check, duplicate gate verification, "
            "and one closeout report with the formal post-workbook current_required_rag_full handoff. "
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
        "--artists-raw-trial-root",
        default="",
        help="optional trial root for artist raw artifacts to be bounded-merged into current by scope",
    )
    parser.add_argument(
        "--artists-image-metadata-trial-root",
        default="",
        help="optional trial root for artist image metadata artifacts to be bounded-merged into current by scope",
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
        "--exhibitions-image-metadata-trial-root",
        default="",
        help="optional trial root for exhibition image metadata artifacts to be bounded-merged into current by scope",
    )
    parser.add_argument(
        "--exhibitions-enrichment-trial-root",
        default="",
        help="optional trial root for exhibition enrichment output/summary to be bounded-merged into current",
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
            "current write stage, duplicate gate aware verification, xlsx update, and closeout report "
            "(formal R2 final sync remains the post-workbook current_required_rag_full lane)"
        ),
    )
    parser.add_argument(
        "--current-only",
        action="store_true",
        help=(
            "limit execution to current write + duplicate gate only; skip skip-registry/gallery-list cleanup, "
            "xlsx update, and R2 contract stages"
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


def normalize_enrichment_source_url(value: str) -> str:
    return str(value or "").strip().rstrip("/")


def enrichment_audit_key(row: dict[str, Any]) -> tuple[str, str, str] | None:
    fair_slug = str(row.get("fair_slug") or "").strip().lower().replace("-", "_")
    text_hash = str(row.get("text_hash") or row.get("enrich_input_text_hash") or row.get("record_id") or "").strip()
    source_url = normalize_enrichment_source_url(str(row.get("source_url") or ""))
    if not fair_slug or not source_url:
        return None
    return fair_slug, text_hash, source_url


def canonicalize_applied_enrichment_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    ordered_keys: list[tuple[str, str, str]] = []
    skipped_non_applied = 0
    skipped_missing_key = 0
    duplicate_key_total = 0

    for row in rows:
        if str(row.get("status") or "").strip() != "APPLIED":
            skipped_non_applied += 1
            continue
        key = enrichment_audit_key(row)
        if key is None:
            skipped_missing_key += 1
            continue
        if key in rows_by_key:
            duplicate_key_total += 1
        else:
            ordered_keys.append(key)
        rows_by_key[key] = dict(row)

    canonical_rows = [rows_by_key[key] for key in ordered_keys]
    return canonical_rows, {
        "input_rows_total": len(rows),
        "canonical_rows_total": len(canonical_rows),
        "duplicate_key_total": duplicate_key_total,
        "skipped_non_applied_total": skipped_non_applied,
        "skipped_missing_key_total": skipped_missing_key,
    }


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


def _target_scope_keys_from_report(report: dict[str, Any]) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for raw in report.get("targets", []):
        if not isinstance(raw, dict):
            continue
        fair_slug = str(raw.get("fair_slug") or "").strip().lower().replace("-", "_")
        gallery_name = str(raw.get("gallery_name_en") or "").strip()
        if not fair_slug or not gallery_name:
            continue
        keys.add(ScopeTarget(fair_slug=fair_slug, gallery_name_en=gallery_name).scope_key)
    return keys


def _resolve_duplicate_gate_image_metadata_paths(report: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """
    Pick image metadata paths for duplicate audit.
    For mixed-source verify-first planning, prefer staged planned paths.
    """
    current_paths = report.get("current_paths", {})
    planned_paths = report.get("planned_current_paths", {})
    if not isinstance(current_paths, dict):
        current_paths = {}
    if not isinstance(planned_paths, dict):
        planned_paths = {}

    current_artist_paths = current_paths.get("artist", {})
    planned_artist_paths = planned_paths.get("artist", {})
    if not isinstance(current_artist_paths, dict):
        current_artist_paths = {}
    if not isinstance(planned_artist_paths, dict):
        planned_artist_paths = {}

    current_meta_paths = current_artist_paths.get("image_metadata", {})
    planned_meta_paths = planned_artist_paths.get("image_metadata", {})
    if not isinstance(current_meta_paths, dict):
        current_meta_paths = {}
    if not isinstance(planned_meta_paths, dict):
        planned_meta_paths = {}

    if planned_meta_paths:
        return planned_meta_paths, "planned_current_paths"
    return current_meta_paths, "current_paths"


def _iter_target_artist_work_image_records(report: dict[str, Any]) -> list[dict[str, Any]]:
    image_meta_paths, _path_source = _resolve_duplicate_gate_image_metadata_paths(report)
    target_scope_keys = _target_scope_keys_from_report(report)
    if not target_scope_keys:
        return []

    out: list[dict[str, Any]] = []
    for _fair_slug, path_text in image_meta_paths.items():
        path = Path(path_text)
        if not path.exists():
            continue
        for row in read_jsonl(path):
            if not isinstance(row, dict):
                continue
            fair_slug = str(row.get("fair_slug") or "").strip().lower().replace("-", "_")
            gallery_name = str(row.get("gallery_name_en") or "").strip()
            artist_name = str(row.get("artist_name_en") or "").strip()
            if not fair_slug or not gallery_name:
                continue
            scope_key = ScopeTarget(fair_slug=fair_slug, gallery_name_en=gallery_name).scope_key
            if scope_key not in target_scope_keys:
                continue

            image_urls = row.get("works_image_urls") if isinstance(row.get("works_image_urls"), list) else []
            local_paths = (
                row.get("works_image_local_paths") if isinstance(row.get("works_image_local_paths"), list) else []
            )
            payload_hashes = (
                row.get("works_image_payload_hashes") if isinstance(row.get("works_image_payload_hashes"), list) else []
            )
            r2_keys = row.get("works_image_r2_keys") if isinstance(row.get("works_image_r2_keys"), list) else []

            for slot_index, (url_text, local_path_text, payload_hash, r2_key) in enumerate(
                zip_longest(image_urls, local_paths, payload_hashes, r2_keys, fillvalue=""),
                start=1,
            ):
                url_value = str(url_text or "").strip()
                local_path_value = str(local_path_text or "").strip()
                payload_value = str(payload_hash or "").strip()
                r2_key_value = str(r2_key or "").strip()
                if not url_value and not local_path_value and not payload_value and not r2_key_value:
                    continue
                local_path = Path(local_path_value) if local_path_value else None
                local_exists = bool(local_path and local_path.exists())
                out.append(
                    {
                        "scope_key": scope_key,
                        "fair_slug": fair_slug,
                        "gallery_name_en": gallery_name,
                        "artist_name_en": artist_name,
                        "slot_index": slot_index,
                        "image_url": url_value,
                        "payload_hash": payload_value,
                        "r2_key": r2_key_value,
                        "local_path": local_path.as_posix() if local_path else "",
                        "local_exists": local_exists,
                    }
                )
    return out


def audit_artist_works_image_duplicate_gate(report: dict[str, Any]) -> dict[str, Any]:
    image_meta_paths, path_source = _resolve_duplicate_gate_image_metadata_paths(report)
    records = _iter_target_artist_work_image_records(report)
    gallery_records: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    missing_local_path_count = 0
    for row in records:
        gallery_records[(str(row["fair_slug"]), str(row["gallery_name_en"]))].append(row)
        if not bool(row.get("local_exists")):
            missing_local_path_count += 1

    gallery_reports: list[dict[str, Any]] = []
    duplicate_cluster_count = 0
    duplicate_record_count = 0
    scanned_with_local = 0

    for (fair_slug, gallery_name), gallery_rows in sorted(gallery_records.items()):
        enriched_rows: list[dict[str, Any]] = []
        for row in gallery_rows:
            local_exists = bool(row.get("local_exists"))
            local_path = Path(str(row.get("local_path") or "")) if local_exists else None
            visual_key = image_visual_dedupe_key(local_path) if local_path is not None else ""
            signature = image_visual_signature(local_path) if local_path is not None else None
            url_text = str(row.get("image_url") or "")
            enriched_rows.append(
                {
                    **row,
                    "visual_key": visual_key,
                    "signature": signature,
                    "url_base_identity": normalize_image_url_base_identity_for_dedupe(url_text) if url_text else "",
                }
            )
            if local_exists:
                scanned_with_local += 1

        if len(enriched_rows) <= 1:
            gallery_reports.append(
                {
                    "fair_slug": fair_slug,
                    "gallery_name_en": gallery_name,
                    "record_count": len(enriched_rows),
                    "duplicate_cluster_count": 0,
                    "duplicate_record_count": 0,
                    "clusters": [],
                }
            )
            continue

        parent = list(range(len(enriched_rows)))

        def find(idx: int) -> int:
            while parent[idx] != idx:
                parent[idx] = parent[parent[idx]]
                idx = parent[idx]
            return idx

        def union(left: int, right: int) -> None:
            left_root = find(left)
            right_root = find(right)
            if left_root != right_root:
                parent[right_root] = left_root

        payload_groups: dict[str, list[int]] = defaultdict(list)
        visual_groups: dict[str, list[int]] = defaultdict(list)
        for idx, row in enumerate(enriched_rows):
            payload_hash = str(row.get("payload_hash") or "").strip()
            visual_key = str(row.get("visual_key") or "").strip()
            if payload_hash:
                payload_groups[payload_hash].append(idx)
            if visual_key:
                visual_groups[visual_key].append(idx)

        for groups in (payload_groups, visual_groups):
            for members in groups.values():
                if len(members) <= 1:
                    continue
                head = members[0]
                for idx in members[1:]:
                    union(head, idx)

        for left in range(len(enriched_rows)):
            left_sig = enriched_rows[left].get("signature")
            if left_sig is None:
                continue
            for right in range(left + 1, len(enriched_rows)):
                right_sig = enriched_rows[right].get("signature")
                if right_sig is None:
                    continue
                if is_contextual_near_duplicate_visual_signature(
                    left_sig,
                    right_sig,
                    candidate_url_text=str(enriched_rows[left].get("image_url") or ""),
                    existing_url_text=str(enriched_rows[right].get("image_url") or ""),
                    candidate_url_base_identity=str(enriched_rows[left].get("url_base_identity") or ""),
                    existing_url_base_identity=str(enriched_rows[right].get("url_base_identity") or ""),
                ):
                    union(left, right)

        clusters: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for idx, row in enumerate(enriched_rows):
            clusters[find(idx)].append(row)

        cluster_reports: list[dict[str, Any]] = []
        for members in clusters.values():
            if len(members) <= 1:
                continue
            reason_classes: list[str] = []
            payloads = [str(item.get("payload_hash") or "").strip() for item in members if str(item.get("payload_hash") or "").strip()]
            visuals = [str(item.get("visual_key") or "").strip() for item in members if str(item.get("visual_key") or "").strip()]
            if len(payloads) != len(set(payloads)):
                reason_classes.append("exact_payload_duplicate")
            if len(visuals) != len(set(visuals)):
                reason_classes.append("same_visual_signature_duplicate")
            if not reason_classes:
                reason_classes.append("contextual_near_duplicate")
            cluster_reports.append(
                {
                    "cluster_size": len(members),
                    "reason_classes": reason_classes,
                    "artists": sorted({str(item.get("artist_name_en") or "").strip() for item in members if str(item.get("artist_name_en") or "").strip()}),
                    "records": [
                        {
                            "artist_name_en": str(item.get("artist_name_en") or ""),
                            "slot_index": int(item.get("slot_index") or 0),
                            "file_basename": Path(str(item.get("local_path") or "")).name,
                            "local_path": str(item.get("local_path") or ""),
                            "r2_key": str(item.get("r2_key") or ""),
                        }
                        for item in sorted(
                            members,
                            key=lambda record: (
                                str(record.get("artist_name_en") or ""),
                                int(record.get("slot_index") or 0),
                                str(record.get("local_path") or ""),
                            ),
                        )
                    ],
                }
            )

        gallery_reports.append(
            {
                "fair_slug": fair_slug,
                "gallery_name_en": gallery_name,
                "record_count": len(enriched_rows),
                "duplicate_cluster_count": len(cluster_reports),
                "duplicate_record_count": sum(int(item.get("cluster_size") or 0) for item in cluster_reports),
                "clusters": cluster_reports,
            }
        )
        duplicate_cluster_count += len(cluster_reports)
        duplicate_record_count += sum(int(item.get("cluster_size") or 0) for item in cluster_reports)

    status = "passed"
    if duplicate_cluster_count > 0:
        status = "blocked_duplicate_clusters_detected"

    return {
        "status": status,
        "input_image_metadata_path_source": path_source,
        "input_image_metadata_paths": {
            str(fair_slug): str(path_text)
            for fair_slug, path_text in image_meta_paths.items()
        },
        "target_gallery_count": len(gallery_records),
        "scanned_record_count": len(records),
        "scanned_local_file_count": scanned_with_local,
        "missing_local_path_count": missing_local_path_count,
        "duplicate_cluster_count": duplicate_cluster_count,
        "duplicate_record_count": duplicate_record_count,
        "galleries_with_duplicates": [
            {
                "fair_slug": str(item.get("fair_slug") or ""),
                "gallery_name_en": str(item.get("gallery_name_en") or ""),
                "duplicate_cluster_count": int(item.get("duplicate_cluster_count") or 0),
            }
            for item in gallery_reports
            if int(item.get("duplicate_cluster_count") or 0) > 0
        ],
        "gallery_reports": gallery_reports,
    }


def finalize_current_write_report(report: dict[str, Any], *, apply: bool) -> dict[str, Any]:
    out = dict(report)
    scope_counts = dict(out.get("scope_counts", {}))
    exhibition_status, exhibition_required = derive_exhibition_images_current_status(scope_counts)
    duplicate_audit = audit_artist_works_image_duplicate_gate(out)
    blocking_errors = list(out.get("blocking_errors", []))
    if exhibition_status.startswith("blocked"):
        blocking_errors.append("blocked_exhibition_image_source_missing")
    if int(duplicate_audit.get("duplicate_cluster_count") or 0) > 0:
        blocking_errors.append(
            f"blocked_artist_works_images_duplicate_clusters:{int(duplicate_audit.get('duplicate_cluster_count') or 0)}"
        )
    out["blocking_errors"] = list(dict.fromkeys(str(item) for item in blocking_errors if str(item).strip()))
    out["exhibition_images_current_status"] = exhibition_status
    out["exhibition_images_required_for_block_completion"] = bool(exhibition_required)
    out["artist_works_images_duplicate_audit"] = duplicate_audit
    if out["blocking_errors"]:
        if exhibition_status.startswith("blocked"):
            out["status"] = "blocked_missing_required_exhibition_image_source"
        elif int(duplicate_audit.get("duplicate_cluster_count") or 0) > 0:
            out["status"] = "blocked_artist_works_images_duplicate_clusters"
        else:
            out["status"] = "blocked_required_precloseout_gate"
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


def _sha256_file(path: Path, *, digest_cache: dict[str, str]) -> str:
    resolved = resolve_path(path)
    cache_key = resolved.as_posix()
    cached = digest_cache.get(cache_key)
    if cached is not None:
        return cached
    digest = hashlib.sha256()
    with resolved.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    value = digest.hexdigest()
    digest_cache[cache_key] = value
    return value


def _contains_trial_marker(path_text: str | Path) -> bool:
    return "_trial" in str(path_text or "").replace("/", "\\").lower()


def _is_within_root(path: Path, root: Path) -> bool:
    try:
        resolve_path(path).relative_to(resolve_path(root))
        return True
    except Exception:
        return False


def _cache_fair_dir_name(fair_slug: str) -> str:
    return str(fair_slug or "").strip().lower().replace("_", "-")


def _current_cache_destination_path(
    *,
    current_root: Path,
    family: str,
    fair_slug: str,
    target_year: int,
    basename: str,
) -> Path:
    fair_dir = _cache_fair_dir_name(fair_slug)
    if family == "artist_works_images":
        base_dir = get_artist_image_cache_dir(current_root)
    elif family == "exhibition_works_images":
        base_dir = get_exhibition_image_cache_dir(current_root)
    else:
        raise ValueError(f"unsupported_image_cache_family:{family}")
    return resolve_path(base_dir / str(target_year) / fair_dir / basename)


def _cache_reference_basename(local_path_text: str, r2_key_text: str) -> str:
    for raw in (local_path_text, r2_key_text):
        name = Path(str(raw or "").replace("\\", "/")).name
        if name:
            return name
    return ""


def _trial_cache_source_candidates(
    *,
    trial_root: Path,
    family: str,
    fair_slug: str,
    target_year: int,
    basename: str,
    local_path_text: str,
) -> list[Path]:
    fair_dir = _cache_fair_dir_name(fair_slug)
    candidates: list[Path] = []
    resolved_local = resolve_image_local_path(local_path_text or "")
    if resolved_local is not None and _is_within_root(resolved_local, trial_root):
        candidates.append(resolve_path(resolved_local))
    if family == "artist_works_images":
        candidates.append(resolve_path(trial_root / "images" / "cache" / family / str(target_year) / fair_dir / basename))
        candidates.append(resolve_path(trial_root / "img" / str(target_year) / fair_dir / basename))
    elif family == "exhibition_works_images":
        candidates.append(resolve_path(trial_root / "images" / "cache" / family / str(target_year) / fair_dir / basename))
        candidates.append(resolve_path(trial_root / "img" / str(target_year) / fair_dir / basename))
    else:
        raise ValueError(f"unsupported_image_cache_family:{family}")
    unique: dict[str, Path] = {}
    for candidate in candidates:
        unique[candidate.as_posix()] = candidate
    return list(unique.values())


def _init_cache_promotion_state(*, stage_current_root: Path) -> dict[str, Any]:
    return {
        "stage_current_root": stage_current_root,
        "actions_by_destination": {},
        "metadata_path_normalization_candidates": [],
        "vector_id_map_path_normalization_candidates": [],
        "digest_cache": {},
    }


def _register_cache_promotion_reference(
    *,
    state: dict[str, Any],
    trial_root: Path,
    family: str,
    fair_slug: str,
    target_year: int,
    local_path_text: str,
    r2_key_text: str,
    normalization_kind: str,
    reference_payload: dict[str, Any],
) -> tuple[str, str]:
    basename = _cache_reference_basename(local_path_text, r2_key_text)
    if not basename:
        return local_path_text, r2_key_text

    destination_current_path = _current_cache_destination_path(
        current_root=CURRENT_FORMAL_ARTIFACTS_ROOT,
        family=family,
        fair_slug=fair_slug,
        target_year=target_year,
        basename=basename,
    )
    stage_destination_path = _current_cache_destination_path(
        current_root=Path(state["stage_current_root"]),
        family=family,
        fair_slug=fair_slug,
        target_year=target_year,
        basename=basename,
    )
    normalized_local_path = normalize_image_local_path_text(destination_current_path)
    normalized_r2_key = get_image_r2_key(destination_current_path)
    if local_path_text != normalized_local_path or r2_key_text != normalized_r2_key:
        state[f"{normalization_kind}_path_normalization_candidates"].append(
            {
                **reference_payload,
                "family": family,
                "source_local_path": local_path_text,
                "source_r2_key": r2_key_text,
                "normalized_local_path": normalized_local_path,
                "normalized_r2_key": normalized_r2_key,
            }
        )

    destination_key = destination_current_path.as_posix()
    action = state["actions_by_destination"].get(destination_key)
    if action is None:
        action = {
            "family": family,
            "destination_current_path": destination_key,
            "stage_destination_path": stage_destination_path.as_posix(),
            "fair_slug": fair_slug,
            "basename": basename,
            "source_candidates": [],
            "reference_contexts": [],
        }
        state["actions_by_destination"][destination_key] = action
    for candidate in _trial_cache_source_candidates(
        trial_root=trial_root,
        family=family,
        fair_slug=fair_slug,
        target_year=target_year,
        basename=basename,
        local_path_text=local_path_text,
    ):
        candidate_text = candidate.as_posix()
        if candidate_text not in action["source_candidates"]:
            action["source_candidates"].append(candidate_text)
    action["reference_contexts"].append(
        {
            **reference_payload,
            "kind": normalization_kind,
            "normalized_local_path": normalized_local_path,
            "normalized_r2_key": normalized_r2_key,
        }
    )
    return normalized_local_path, normalized_r2_key


def _summarize_and_stage_cache_promotion(state: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    digest_cache: dict[str, str] = state["digest_cache"]
    actions = sorted(state["actions_by_destination"].values(), key=lambda row: str(row["destination_current_path"]))
    artist_candidates: list[dict[str, Any]] = []
    exhibition_candidates: list[dict[str, Any]] = []
    source_missing: list[dict[str, Any]] = []
    zero_size: list[dict[str, Any]] = []
    destination_bad_prefix: list[dict[str, Any]] = []
    destination_contains_trial: list[dict[str, Any]] = []
    collisions: list[dict[str, Any]] = []
    metadata_missing_after_normalization: list[dict[str, Any]] = []
    vector_missing_after_normalization: list[dict[str, Any]] = []
    blocking_errors: list[str] = []
    apply_actions: list[dict[str, Any]] = []

    current_cache_root = resolve_path(CURRENT_FORMAL_ARTIFACTS_ROOT / "images" / "cache")
    for action in actions:
        destination_current_path = resolve_path(Path(action["destination_current_path"]))
        stage_destination_path = resolve_path(Path(action["stage_destination_path"]))
        blocking_reasons: list[str] = []
        existing_sources = [resolve_path(Path(raw)) for raw in action["source_candidates"] if Path(raw).exists()]
        if not existing_sources:
            source_missing.append(
                {
                    "family": action["family"],
                    "destination_current_path": destination_current_path.as_posix(),
                    "source_candidates": list(action["source_candidates"]),
                }
            )
            blocking_reasons.append("source_missing")
        chosen_source: Path | None = existing_sources[0] if existing_sources else None
        if chosen_source is not None and chosen_source.stat().st_size <= 0:
            zero_size.append(
                {
                    "family": action["family"],
                    "destination_current_path": destination_current_path.as_posix(),
                    "source_trial_path": chosen_source.as_posix(),
                }
            )
            blocking_reasons.append("zero_size")
        if chosen_source is not None:
            source_digest = _sha256_file(chosen_source, digest_cache=digest_cache)
            for other_source in existing_sources[1:]:
                other_digest = _sha256_file(other_source, digest_cache=digest_cache)
                if other_digest != source_digest:
                    collisions.append(
                        {
                            "family": action["family"],
                            "destination_current_path": destination_current_path.as_posix(),
                            "source_trial_path": chosen_source.as_posix(),
                            "colliding_source_path": other_source.as_posix(),
                        }
                    )
                    blocking_reasons.append("same_name_different_content_collision")
                    break
            if destination_current_path.exists():
                current_digest = _sha256_file(destination_current_path, digest_cache=digest_cache)
                if current_digest != source_digest:
                    collisions.append(
                        {
                            "family": action["family"],
                            "destination_current_path": destination_current_path.as_posix(),
                            "source_trial_path": chosen_source.as_posix(),
                            "colliding_source_path": destination_current_path.as_posix(),
                        }
                    )
                    blocking_reasons.append("same_name_different_content_collision")

        if not _is_within_root(destination_current_path, current_cache_root):
            destination_bad_prefix.append(
                {
                    "family": action["family"],
                    "destination_current_path": destination_current_path.as_posix(),
                }
            )
            blocking_reasons.append("destination_bad_prefix")
        if _contains_trial_marker(destination_current_path):
            destination_contains_trial.append(
                {
                    "family": action["family"],
                    "destination_current_path": destination_current_path.as_posix(),
                }
            )
            blocking_reasons.append("destination_contains_trial")

        blocking_reasons = list(dict.fromkeys(blocking_reasons))
        current_status = "missing_in_current"
        if destination_current_path.exists():
            current_status = "already_exists_same_content" if "same_name_different_content_collision" not in blocking_reasons else "different_content_collision"
        action_summary = {
            "family": action["family"],
            "fair_slug": action["fair_slug"],
            "destination_current_path": destination_current_path.as_posix(),
            "stage_destination_path": stage_destination_path.as_posix(),
            "source_trial_path": chosen_source.as_posix() if chosen_source is not None else "",
            "source_candidates": list(action["source_candidates"]),
            "reference_total": len(action["reference_contexts"]),
            "reference_kinds": sorted({str(item["kind"]) for item in action["reference_contexts"]}),
            "current_destination_status": current_status,
            "blocking_reasons": blocking_reasons,
            "status": "blocked" if blocking_reasons else current_status,
        }
        if action["family"] == "artist_works_images":
            artist_candidates.append(action_summary)
        else:
            exhibition_candidates.append(action_summary)

        destination_satisfied = not blocking_reasons
        if destination_satisfied and chosen_source is not None:
            copy_file_if_exists(chosen_source, stage_destination_path)
            apply_actions.append(
                {
                    "source_stage_path": stage_destination_path.as_posix(),
                    "destination_current_path": destination_current_path.as_posix(),
                }
            )
        else:
            for ref in action["reference_contexts"]:
                missing_entry = {
                    **ref,
                    "destination_current_path": destination_current_path.as_posix(),
                    "source_candidates": list(action["source_candidates"]),
                    "blocking_reasons": blocking_reasons,
                }
                if ref["kind"] == "metadata":
                    metadata_missing_after_normalization.append(missing_entry)
                else:
                    vector_missing_after_normalization.append(missing_entry)

        for reason in blocking_reasons:
            blocking_errors.append(f"image_cache_promotion_{reason}:{destination_current_path.as_posix()}")

    summary = {
        "artist_works_cache_copy_candidates": artist_candidates,
        "exhibitions_cache_copy_candidates": exhibition_candidates,
        "source_missing": source_missing,
        "zero_size": zero_size,
        "destination_bad_prefix": destination_bad_prefix,
        "destination_contains_trial": destination_contains_trial,
        "same_name_different_content_collision": collisions,
        "metadata_path_normalization_candidates": list(state["metadata_path_normalization_candidates"]),
        "vector_id_map_path_normalization_candidates": list(state["vector_id_map_path_normalization_candidates"]),
        "metadata_current_cache_missing_after_normalization": metadata_missing_after_normalization,
        "vector_id_map_current_cache_missing_after_normalization": vector_missing_after_normalization,
        "runtime_trial_ref_total_after_normalization": 0,
        "blocking_errors": list(dict.fromkeys(blocking_errors)),
    }
    return summary, apply_actions


def _apply_staged_cache_promotion(cache_apply_actions: list[dict[str, Any]]) -> None:
    for action in cache_apply_actions:
        src = resolve_path(Path(action["source_stage_path"]))
        dst = resolve_path(Path(action["destination_current_path"]))
        if not src.exists():
            raise FileNotFoundError(f"missing_staged_cache_promotion_source:{src}")
        copy_file_if_exists(src, dst)


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
    artists_raw_root = resolve_optional_path(args.artists_raw_trial_root)
    artists_image_metadata_root = resolve_optional_path(args.artists_image_metadata_trial_root)
    artists_enrichment_root = resolve_optional_path(args.artists_enrichment_trial_root)
    artists_text_vector_root = resolve_optional_path(args.artists_text_vector_trial_root)
    artist_image_vector_root = resolve_optional_path(args.artist_works_images_vector_trial_root)
    exhibitions_raw_root = resolve_optional_path(args.exhibitions_raw_trial_root)
    exhibitions_image_metadata_root = resolve_optional_path(args.exhibitions_image_metadata_trial_root)
    exhibitions_enrichment_root = resolve_optional_path(args.exhibitions_enrichment_trial_root)
    if artists_raw_root is not None:
        out["artists_raw"] = artists_raw_root
    if artists_image_metadata_root is not None:
        out["artists_image_metadata"] = artists_image_metadata_root
    if artists_enrichment_root is not None:
        out["artists_enrichment"] = artists_enrichment_root
    if artists_text_vector_root is not None:
        out["artists_text_vector"] = artists_text_vector_root
    if artist_image_vector_root is not None:
        out["artist_works_images_vector"] = artist_image_vector_root
    if exhibitions_raw_root is not None:
        out["exhibitions_raw"] = exhibitions_raw_root
    if exhibitions_image_metadata_root is not None:
        out["exhibitions_image_metadata"] = exhibitions_image_metadata_root
    if exhibitions_enrichment_root is not None:
        out["exhibitions_enrichment"] = exhibitions_enrichment_root
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
    cache_promotion_state = _init_cache_promotion_state(stage_current_root=stage_current_root)

    def merge_enrichment_trial_to_stage(
        *,
        category: str,
        report_key: str,
        current_key: str,
        trial_root: Path,
    ) -> None:
        trial_source = extract_trial_enrichment_source(trial_root, category=category, target_year=target_year)
        current_enrichment_rows = read_jsonl(Path(current_paths[current_key]["enrichment_output"]))
        current_summary_before = (
            read_json(Path(current_paths[current_key]["enrichment_summary"]))
            if Path(current_paths[current_key]["enrichment_summary"]).exists()
            else {}
        )
        current_scoped_source_map, current_fallback_source_map = build_source_scope_maps(
            {fair_slug: read_jsonl(path) for fair_slug, path in current_paths[current_key]["raw"].items()}
        )
        trial_raw_paths = get_current_raw_paths(category, target_year, root=trial_root)
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
        merged_rows, canonicalization = canonicalize_applied_enrichment_rows(retained_current_rows + trial_rows_added)
        staged_scoped_source_map, staged_fallback_source_map = build_source_scope_maps(
            {fair_slug: read_jsonl(path) for fair_slug, path in staged_paths[current_key]["raw"].items()}
        )
        final_target_rows_total = sum(
            1
            for row in merged_rows
            if resolve_enrichment_scope_key(
                row,
                scoped_source_map=staged_scoped_source_map,
                fallback_source_map=staged_fallback_source_map,
            )
            in target_scope_keys
        )
        summary_after = build_enrichment_summary(
            started_at=utc_now_iso(),
            completed_at=utc_now_iso(),
            trial_root=trial_root,
            current_output_path=Path(staged_paths[current_key]["enrichment_output"]),
            current_summary_path=Path(staged_paths[current_key]["enrichment_summary"]),
            current_summary_before=current_summary_before,
            trial_source=trial_source,
            targets=targets,
            current_rows_before=current_enrichment_rows,
            trial_rows_added=trial_rows_added,
            final_rows=merged_rows,
            current_scoped_source_map=current_scoped_source_map,
            current_fallback_source_map=current_fallback_source_map,
            category=category,
        )
        summary_after["current_runtime_canonicalization"] = dict(canonicalization)
        summary_after = mark_summary_for_closeout_plan(summary_after, apply=apply)
        write_jsonl_atomic(Path(staged_paths[current_key]["enrichment_output"]), merged_rows)
        write_json_atomic(Path(staged_paths[current_key]["enrichment_summary"]), summary_after)
        merge_plan[report_key] = {
            "source_root": str(trial_root),
            "trial_output_path": str(trial_source["output_path"]),
            "trial_summary_path": str(trial_source["summary_path"]),
            "current_rows_before": len(current_enrichment_rows),
            "current_rows_after": len(merged_rows),
            "trial_target_rows_added": len(trial_rows_added),
            "retained_non_target_rows_total": len(retained_current_rows),
            "final_target_rows_total": final_target_rows_total,
            "canonicalization": dict(canonicalization),
            "output_path": str(staged_paths[current_key]["enrichment_output"]),
            "summary_path": str(staged_paths[current_key]["enrichment_summary"]),
        }

    if "artists_raw" in trial_roots:
        trial_root = trial_roots["artists_raw"]
        trial_raw_paths = get_current_raw_paths("artists", target_year, root=trial_root)
        by_fair: dict[str, Any] = {}
        current_target_rows_before_total = 0
        trial_target_rows_total = 0
        retained_non_target_rows_total = 0
        final_rows_total = 0
        for fair_slug, current_raw_path in current_paths["artist"]["raw"].items():
            trial_raw_path = Path(trial_raw_paths[fair_slug])
            if not trial_raw_path.exists():
                raise FileNotFoundError(f"missing_trial_artist_raw:{fair_slug}:{trial_raw_path}")
            current_rows = read_jsonl(Path(current_raw_path))
            trial_rows = read_jsonl(trial_raw_path)
            merged = merge_jsonl_rows_by_scope(
                current_rows=current_rows,
                trial_rows=trial_rows,
                target_scope_keys=target_scope_keys,
                label=f"artist_raw_{fair_slug}",
            )
            staged_raw_path = Path(staged_paths["artist"]["raw"][fair_slug])
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
        merge_plan["artist_raw"] = {
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
        for fair_slug, current_raw_path in current_paths["artist"]["raw"].items():
            current_target_rows = count_target_rows(Path(current_raw_path), target_scope_keys)
            current_target_rows_before_total += int(current_target_rows)
            by_fair[fair_slug] = {
                "current_path": str(current_raw_path),
                "output_path": str(staged_paths["artist"]["raw"][fair_slug]),
                "current_target_rows_total": int(current_target_rows),
            }
        merge_plan["artist_raw"] = {
            "source_root": "current",
            "current_target_rows_before_total": current_target_rows_before_total,
            "trial_target_rows_total": 0,
            "by_fair": by_fair,
        }

    if "artists_image_metadata" in trial_roots:
        trial_root = trial_roots["artists_image_metadata"]
        trial_meta_paths = get_current_artist_image_meta_paths(root=trial_root)
        by_fair = {}
        current_target_rows_before_total = 0
        trial_target_rows_total = 0
        retained_non_target_rows_total = 0
        final_rows_total = 0
        for fair_slug, current_meta_path in current_paths["artist"]["image_metadata"].items():
            trial_meta_path = Path(trial_meta_paths[fair_slug])
            if not trial_meta_path.exists():
                raise FileNotFoundError(f"missing_trial_artist_image_metadata:{fair_slug}:{trial_meta_path}")
            current_rows = read_jsonl(Path(current_meta_path))
            trial_rows = read_jsonl(trial_meta_path)
            merged = merge_jsonl_rows_by_scope(
                current_rows=current_rows,
                trial_rows=trial_rows,
                target_scope_keys=target_scope_keys,
                label=f"artist_image_metadata_{fair_slug}",
            )
            final_rows = [dict(row) if isinstance(row, dict) else row for row in merged["final_rows"]]
            for row in final_rows:
                if not isinstance(row, dict):
                    continue
                scope_key = ScopeTarget(
                    fair_slug=str(row.get("fair_slug") or "").strip().lower().replace("-", "_"),
                    gallery_name_en=str(row.get("gallery_name_en") or "").strip(),
                ).scope_key
                if scope_key not in target_scope_keys:
                    continue
                local_paths = row.get("works_image_local_paths") if isinstance(row.get("works_image_local_paths"), list) else []
                r2_keys = row.get("works_image_r2_keys") if isinstance(row.get("works_image_r2_keys"), list) else []
                if not local_paths and not r2_keys:
                    continue
                normalized_locals: list[str] = []
                normalized_r2_keys: list[str] = []
                for slot_index, (local_path_text, r2_key_text) in enumerate(
                    zip_longest(local_paths, r2_keys, fillvalue=""),
                    start=1,
                ):
                    normalized_local, normalized_r2 = _register_cache_promotion_reference(
                        state=cache_promotion_state,
                        trial_root=trial_root,
                        family="artist_works_images",
                        fair_slug=fair_slug,
                        target_year=target_year,
                        local_path_text=str(local_path_text or ""),
                        r2_key_text=str(r2_key_text or ""),
                        normalization_kind="metadata",
                        reference_payload={
                            "record_type": "artist_image_metadata",
                            "fair_slug": fair_slug,
                            "gallery_name_en": str(row.get("gallery_name_en") or ""),
                            "artist_name_en": str(row.get("artist_name_en") or ""),
                            "slot_index": slot_index,
                        },
                    )
                    normalized_locals.append(normalized_local)
                    normalized_r2_keys.append(normalized_r2)
                row["works_image_local_paths"] = normalized_locals
                row["works_image_r2_keys"] = normalized_r2_keys
            staged_meta_path = Path(staged_paths["artist"]["image_metadata"][fair_slug])
            write_jsonl_atomic(staged_meta_path, final_rows)
            current_target_rows_before_total += int(merged["current_target_rows_total"])
            trial_target_rows_total += int(merged["trial_target_rows_total"])
            retained_non_target_rows_total += int(merged["retained_non_target_rows_total"])
            final_rows_total += int(merged["final_rows_total"])
            by_fair[fair_slug] = {
                "current_path": str(current_meta_path),
                "trial_path": str(trial_meta_path),
                "output_path": str(staged_meta_path),
                "current_target_rows_total": int(merged["current_target_rows_total"]),
                "trial_target_rows_total": int(merged["trial_target_rows_total"]),
                "retained_non_target_rows_total": int(merged["retained_non_target_rows_total"]),
                "final_rows_total": int(merged["final_rows_total"]),
            }
        merge_plan["artist_image_metadata"] = {
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
        for fair_slug, current_meta_path in current_paths["artist"]["image_metadata"].items():
            current_target_rows = count_target_rows(Path(current_meta_path), target_scope_keys)
            current_target_rows_before_total += int(current_target_rows)
            by_fair[fair_slug] = {
                "current_path": str(current_meta_path),
                "output_path": str(staged_paths["artist"]["image_metadata"][fair_slug]),
                "current_target_rows_total": int(current_target_rows),
            }
        merge_plan["artist_image_metadata"] = {
            "source_root": "current",
            "current_target_rows_before_total": current_target_rows_before_total,
            "trial_target_rows_total": 0,
            "by_fair": by_fair,
        }

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

    if "exhibitions_image_metadata" in trial_roots:
        trial_root = trial_roots["exhibitions_image_metadata"]
        trial_meta_paths = get_current_exhibitions_image_meta_paths(target_year, root=trial_root)
        by_fair = {}
        current_target_rows_before_total = 0
        trial_target_rows_total = 0
        retained_non_target_rows_total = 0
        final_rows_total = 0
        for fair_slug, current_meta_path in current_paths["exhibition"]["image_metadata"].items():
            trial_meta_path = Path(trial_meta_paths[fair_slug])
            if not trial_meta_path.exists():
                raise FileNotFoundError(f"missing_trial_exhibition_image_metadata:{fair_slug}:{trial_meta_path}")
            current_rows = read_jsonl(Path(current_meta_path))
            trial_rows = read_jsonl(trial_meta_path)
            merged = merge_jsonl_rows_by_scope(
                current_rows=current_rows,
                trial_rows=trial_rows,
                target_scope_keys=target_scope_keys,
                label=f"exhibition_image_metadata_{fair_slug}",
            )
            final_rows = [dict(row) if isinstance(row, dict) else row for row in merged["final_rows"]]
            for row in final_rows:
                if not isinstance(row, dict):
                    continue
                scope_key = ScopeTarget(
                    fair_slug=str(row.get("fair_slug") or "").strip().lower().replace("-", "_"),
                    gallery_name_en=str(row.get("gallery_name_en") or "").strip(),
                ).scope_key
                if scope_key not in target_scope_keys:
                    continue
                normalized_local, normalized_r2 = _register_cache_promotion_reference(
                    state=cache_promotion_state,
                    trial_root=trial_root,
                    family="exhibition_works_images",
                    fair_slug=fair_slug,
                    target_year=target_year,
                    local_path_text=str(row.get("local_path") or ""),
                    r2_key_text=str(row.get("r2_key") or ""),
                    normalization_kind="metadata",
                    reference_payload={
                        "record_type": "exhibition_image_metadata",
                        "fair_slug": fair_slug,
                        "gallery_name_en": str(row.get("gallery_name_en") or ""),
                        "source_url": str(row.get("source_url") or ""),
                    },
                )
                row["local_path"] = normalized_local
                row["r2_key"] = normalized_r2
            staged_meta_path = Path(staged_paths["exhibition"]["image_metadata"][fair_slug])
            write_jsonl_atomic(staged_meta_path, final_rows)
            current_target_rows_before_total += int(merged["current_target_rows_total"])
            trial_target_rows_total += int(merged["trial_target_rows_total"])
            retained_non_target_rows_total += int(merged["retained_non_target_rows_total"])
            final_rows_total += int(merged["final_rows_total"])
            by_fair[fair_slug] = {
                "current_path": str(current_meta_path),
                "trial_path": str(trial_meta_path),
                "output_path": str(staged_meta_path),
                "current_target_rows_total": int(merged["current_target_rows_total"]),
                "trial_target_rows_total": int(merged["trial_target_rows_total"]),
                "retained_non_target_rows_total": int(merged["retained_non_target_rows_total"]),
                "final_rows_total": int(merged["final_rows_total"]),
            }
        merge_plan["exhibition_image_metadata"] = {
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
        for fair_slug, current_meta_path in current_paths["exhibition"]["image_metadata"].items():
            current_target_rows = count_target_rows(Path(current_meta_path), target_scope_keys)
            current_target_rows_before_total += int(current_target_rows)
            by_fair[fair_slug] = {
                "current_path": str(current_meta_path),
                "output_path": str(staged_paths["exhibition"]["image_metadata"][fair_slug]),
                "current_target_rows_total": int(current_target_rows),
            }
        merge_plan["exhibition_image_metadata"] = {
            "source_root": "current",
            "current_target_rows_before_total": current_target_rows_before_total,
            "trial_target_rows_total": 0,
            "by_fair": by_fair,
        }

    if "artists_enrichment" in trial_roots:
        merge_enrichment_trial_to_stage(
            category="artists",
            report_key="artist_enrichment",
            current_key="artist",
            trial_root=trial_roots["artists_enrichment"],
        )
    else:
        merge_plan["artist_enrichment"] = {
            "source_root": "current",
            "current_rows_before": count_target_rows(Path(current_paths["artist"]["enrichment_output"]), target_scope_keys),
            "current_rows_after": count_target_rows(Path(staged_paths["artist"]["enrichment_output"]), target_scope_keys),
            "trial_target_rows_added": 0,
            "output_path": str(staged_paths["artist"]["enrichment_output"]),
            "summary_path": str(staged_paths["artist"]["enrichment_summary"]),
        }

    if "exhibitions_enrichment" in trial_roots:
        merge_enrichment_trial_to_stage(
            category="exhibitions",
            report_key="exhibition_enrichment",
            current_key="exhibition",
            trial_root=trial_roots["exhibitions_enrichment"],
        )
    else:
        merge_plan["exhibition_enrichment"] = {
            "source_root": "current",
            "current_rows_before": count_target_rows(Path(current_paths["exhibition"]["enrichment_output"]), target_scope_keys),
            "current_rows_after": count_target_rows(Path(staged_paths["exhibition"]["enrichment_output"]), target_scope_keys),
            "trial_target_rows_added": 0,
            "output_path": str(staged_paths["exhibition"]["enrichment_output"]),
            "summary_path": str(staged_paths["exhibition"]["enrichment_summary"]),
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
        normalized_final_rows = [dict(row) if isinstance(row, dict) else row for row in merge_result["final_rows"]]
        for row in normalized_final_rows:
            if not isinstance(row, dict):
                continue
            scope_key = ScopeTarget(
                fair_slug=str(row.get("fair_slug") or "").strip().lower().replace("-", "_"),
                gallery_name_en=str(row.get("gallery_name_en") or "").strip(),
            ).scope_key
            if scope_key not in target_scope_keys:
                continue
            normalized_local, normalized_r2 = _register_cache_promotion_reference(
                state=cache_promotion_state,
                trial_root=trial_root,
                family="artist_works_images",
                fair_slug=str(row.get("fair_slug") or ""),
                target_year=target_year,
                local_path_text=str(row.get("local_path") or ""),
                r2_key_text=str(row.get("r2_key") or ""),
                normalization_kind="vector_id_map",
                reference_payload={
                    "record_type": "artist_works_images_vector_id_map",
                    "fair_slug": str(row.get("fair_slug") or ""),
                    "gallery_name_en": str(row.get("gallery_name_en") or ""),
                    "artist_name_en": str(row.get("artist_name_en") or ""),
                    "image_id": str(row.get("image_id") or ""),
                },
            )
            row["local_path"] = normalized_local
            row["r2_key"] = normalized_r2
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
        write_jsonl_atomic(Path(staged_image_paths["id_map"]), normalized_final_rows)
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

    cache_promotion_summary, cache_apply_actions = _summarize_and_stage_cache_promotion(cache_promotion_state)
    merge_plan["image_cache_promotion"] = cache_promotion_summary
    scope_counts = build_scope_counts_from_paths(source_paths=staged_paths, target_scope_keys=target_scope_keys)
    if "artist_enrichment" in merge_plan and "final_target_rows_total" in merge_plan["artist_enrichment"]:
        scope_counts["artist"]["enrichment_output_rows_total"] = int(
            merge_plan["artist_enrichment"].get("final_target_rows_total")
            or merge_plan["artist_enrichment"].get("trial_target_rows_added")
            or 0
        )
    if "exhibition_enrichment" in merge_plan and "final_target_rows_total" in merge_plan["exhibition_enrichment"]:
        scope_counts["exhibition"]["enrichment_output_rows_total"] = int(
            merge_plan["exhibition_enrichment"].get("final_target_rows_total")
            or merge_plan["exhibition_enrichment"].get("trial_target_rows_added")
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
        "image_cache_promotion": cache_promotion_summary,
        "blocking_errors": list(cache_promotion_summary.get("blocking_errors", [])),
    }

    def execute_current_write(apply_flag: bool) -> dict[str, Any]:
        final_report = finalize_current_write_report(current_write_report, apply=apply_flag)
        if apply_flag and str(final_report.get("status") or "").strip() == "applied":
            copy_bundle_files(stage_bundle, current_bundle)
            _apply_staged_cache_promotion(cache_apply_actions)
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
    duplicate_audit = dict(current_write_report.get("artist_works_images_duplicate_audit", {}))
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
    contract["artist_works_images_duplicate_audit_status"] = str(duplicate_audit.get("status") or "").strip() or "unknown"
    contract["artist_works_images_duplicate_cluster_count"] = int(duplicate_audit.get("duplicate_cluster_count") or 0)
    contract["formal_post_workbook_r2_scope"] = FORMAL_REQUIRED_R2_SCOPE_NAME
    contract["formal_post_workbook_r2_sequence"] = list(FORMAL_REQUIRED_R2_SEQUENCE)
    contract["formal_post_workbook_r2_success_criteria"] = list(FORMAL_REQUIRED_R2_SUCCESS_CRITERIA)
    contract["closeout_report_status"] = "generated"
    skip_cleanup_report = report.get("skip_registry_gallery_list_cleanup", {})
    if not isinstance(skip_cleanup_report, dict):
        skip_cleanup_report = {}
    skip_cleanup_status = str(contract.get("skip_registry_gallery_list_cleanup_status") or "").strip()
    all_rag_zero_detected_count = int(skip_cleanup_report.get("all_rag_zero_detected_count") or 0)
    target_total = int(contract.get("target_total") or 0)
    scope_counts = current_write_report.get("scope_counts", {})
    if not isinstance(scope_counts, dict):
        scope_counts = {}

    def _scope_positive(counts: dict[str, Any]) -> bool:
        artist = counts.get("artist", {})
        artist_works = counts.get("artist_works_images", {})
        exhibition = counts.get("exhibition", {})
        candidates = []
        if isinstance(artist, dict):
            candidates.extend(
                [
                    int(artist.get("raw_rows_total") or 0),
                    int(artist.get("image_metadata_rows_total") or 0),
                    int(artist.get("text_vector_rows_total") or 0),
                ]
            )
        if isinstance(artist_works, dict):
            candidates.append(int(artist_works.get("vector_rows_total") or 0))
        if isinstance(exhibition, dict):
            candidates.extend(
                [
                    int(exhibition.get("raw_rows_total") or 0),
                    int(exhibition.get("image_metadata_rows_total") or 0),
                ]
            )
        return any(value > 0 for value in candidates)

    staged_scope_positive = _scope_positive(scope_counts)
    mixed_source_verify_first = (
        contract.get("mode") == "dry_run"
        and str(current_write_report.get("source_of_truth") or "") == "mixed_current_plus_trial_bounded_merge"
    )
    if mixed_source_verify_first:
        projection_source = "current_only_stats"
        projection_source_mismatch = (
            all_rag_zero_detected_count >= target_total > 0
            and staged_scope_positive
            and skip_cleanup_status == "planned"
        )
        skip_cleanup_report["projection_diagnostics"] = {
            "projection_source": projection_source,
            "staged_scope_counts_nonzero": staged_scope_positive,
            "all_rag_zero_detected_count": all_rag_zero_detected_count,
            "target_total": target_total,
            "source_mismatch_detected": projection_source_mismatch,
            "non_blocking_for_verify_first": bool(projection_source_mismatch),
            "non_blocking_reason": (
                "all_rag_zero projection is based on current-only stats while verify-first evaluates staged mixed-source merge"
                if projection_source_mismatch
                else ""
            ),
        }
        report["skip_registry_gallery_list_cleanup"] = skip_cleanup_report
        contract["skip_cleanup_projection_source"] = projection_source
        contract["skip_cleanup_projection_source_mismatch_detected"] = bool(projection_source_mismatch)
        contract["skip_cleanup_projection_non_blocking_for_verify_first"] = bool(projection_source_mismatch)

    if contract.get("mode") == "dry_run":
        if (
            contract.get("current_write_status") == "planned"
            and exhibition_status in {"planned", "not_required"}
            and contract.get("xlsx_update_status") == "planned"
            and contract.get("skip_registry_gallery_list_cleanup_status") == "planned"
            and contract.get("artist_works_images_duplicate_audit_status") == "passed"
            and openclip_status == "planned"
        ):
            contract["block_completion_status"] = "planned_pending_workbook_and_current_required_rag_full"
        else:
            contract["block_completion_status"] = "blocked"
    else:
        if (
            contract.get("current_write_status") == "applied"
            and exhibition_status in {"planned", "not_required"}
            and contract.get("xlsx_update_status") == "applied"
            and contract.get("skip_registry_gallery_list_cleanup_status") == "applied"
            and contract.get("artist_works_images_duplicate_audit_status") == "passed"
            and openclip_status == "planned"
        ):
            contract["block_completion_status"] = "applied_pending_workbook_and_current_required_rag_full"
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
    if args.current_only and args.r2_live_plan:
        raise RuntimeError("--current-only cannot be combined with --r2-live-plan")
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

    if args.current_only:
        current_write_report = current_write_callback(bool(args.apply))
        current_write_status = str(current_write_report.get("status") or "").strip() or (
            "applied" if args.apply else "planned"
        )
        duplicate_audit = dict(current_write_report.get("artist_works_images_duplicate_audit", {}))
        duplicate_status = str(duplicate_audit.get("status") or "").strip() or "unknown"
        duplicate_clusters = int(duplicate_audit.get("duplicate_cluster_count") or 0)
        block_status = (
            "applied_current_only"
            if args.apply and current_write_status == "applied" and duplicate_status == "passed"
            else (
                "blocked_current_only"
                if args.apply
                else ("planned_current_only" if duplicate_status == "passed" else "blocked_current_only")
            )
        )
        report = {
            "contract": {
                "name": "block_closeout_unified",
                "mode": "current_only_apply" if args.apply else "current_only_dry_run",
                "run_id": run_id,
                "target_year": target_year,
                "target_total": len(targets),
                "targets": [target.to_dict() for target in targets],
                "block_completion_status": block_status,
                "current_write_status": current_write_status,
                "exhibition_images_current_status": str(current_write_report.get("exhibition_images_current_status") or ""),
                "artist_works_images_openclip_current_status": str(
                    current_write_report.get("artist_works_images_openclip_current_status") or ""
                ),
                "artist_works_images_duplicate_audit_status": duplicate_status,
                "artist_works_images_duplicate_cluster_count": duplicate_clusters,
                "skip_registry_gallery_list_cleanup_status": "skipped_current_only",
                "xlsx_update_status": "skipped_current_only",
                "r2_sync_status": "skipped_current_only",
                "closeout_report_status": "generated",
            },
            "current_write": current_write_report,
            "skip_registry_gallery_list_cleanup": {
                "stage": "skip_registry_gallery_list_cleanup",
                "mode": "current_only",
                "status": "skipped_current_only",
            },
            "xlsx_update": {
                "stage": "xlsx_update",
                "mode": "current_only",
                "status": "skipped_current_only",
            },
            "r2_sync": {
                "stage": "r2_sync",
                "mode": "current_only",
                "status": "skipped_current_only",
                "required_for_block_completion": False,
                "remote_plan_executed": False,
            },
        }
        report = augment_block_closeout_report(report=report, bundle=r2_bundle, targets_path=targets_path)
    else:
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
