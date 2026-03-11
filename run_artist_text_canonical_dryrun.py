#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from phase1_artist_link_utils import (
    build_artist_name_en_from_source_url,
    canonical_artist_source_key,
    is_invalid_artist_name,
    normalize_url_for_link_compare,
    sanitize_artist_name_en,
)

REPO_ROOT = Path(__file__).resolve().parent


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utc_now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def normalize_url_for_hash(url: str) -> str:
    parsed = urlparse((url or "").strip())
    path = parsed.path or "/"
    normalized = f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{path}"
    return normalized.rstrip("/")


def build_artist_name_key(name_en: str, source_url: str) -> str:
    normalized_name = re.sub(r"\s+", " ", str(name_en or "").strip().lower())
    if normalized_name and normalized_name != "unknown artist" and not is_invalid_artist_name(normalized_name):
        seed = f"artist_name_en:{normalized_name}"
    else:
        seed = f"source_url:{normalize_url_for_hash(source_url)}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def build_artist_identity_key(name_key: str, name_en: str, source_url: str) -> str:
    normalized_key = str(name_key or "").strip().lower()
    if normalized_key:
        return normalized_key
    return build_artist_name_key(name_en, source_url).lower()


def normalize_source_url(url: str) -> str:
    normalized = normalize_url_for_link_compare(url)
    return normalized.rstrip("/")


def read_jsonl_rows(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    if not path.exists():
        warnings.append(f"missing: {path}")
        return rows, warnings

    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                warnings.append(f"json_decode_error: {path} line={line_no}")
                continue
            if isinstance(payload, dict):
                payload["_source_file"] = str(path)
                payload["_line_no"] = line_no
                rows.append(payload)
    return rows, warnings


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def collect_works_name_by_source(paths: list[Path]) -> tuple[dict[str, str], list[str]]:
    name_by_source: dict[str, str] = {}
    warnings: list[str] = []
    for path in paths:
        rows, row_warnings = read_jsonl_rows(path)
        warnings.extend(row_warnings)
        for row in rows:
            source_url = normalize_source_url(str(row.get("source_url") or ""))
            if not source_url:
                continue
            current_name = sanitize_artist_name_en(str(row.get("artist_name_en") or ""))
            prev_name = name_by_source.get(source_url, "")
            if current_name and not is_invalid_artist_name(current_name):
                if not prev_name:
                    name_by_source[source_url] = current_name
            elif source_url not in name_by_source:
                name_by_source[source_url] = ""
    return name_by_source, warnings


def collect_apply_applied_groups(path: Path) -> tuple[set[tuple[str, str]], dict[str, list[dict[str, str]]], list[str]]:
    applied_pairs: set[tuple[str, str]] = set()
    by_source_key: dict[str, list[dict[str, str]]] = defaultdict(list)
    rows, warnings = read_jsonl_rows(path)
    for row in rows:
        status = str(row.get("status") or "").strip()
        if status != "APPLIED":
            continue
        source_url = normalize_source_url(str(row.get("source_url") or ""))
        text_hash = str(row.get("text_hash") or "").strip()
        if not source_url or not text_hash:
            continue
        applied_pairs.add((source_url, text_hash))
        source_key = canonical_artist_source_key(source_url)
        by_source_key[source_key].append(
            {
                "source_url": source_url,
                "text_hash": text_hash,
                "status": status,
            }
        )
    return applied_pairs, by_source_key, warnings


def pick_candidate_name(
    *,
    row_name_en: str,
    works_name_en: str,
    source_url: str,
) -> tuple[str, str]:
    existing_name = sanitize_artist_name_en(row_name_en)
    if existing_name and not is_invalid_artist_name(existing_name):
        return existing_name, "raw_artist_name_en"

    works_name = sanitize_artist_name_en(works_name_en)
    if works_name and not is_invalid_artist_name(works_name):
        return works_name, "works_artist_name_en"

    from_source = sanitize_artist_name_en(build_artist_name_en_from_source_url(source_url))
    if from_source and not is_invalid_artist_name(from_source):
        return from_source, "source_slug"

    return "", "invalid"


def row_schema_score(row: dict[str, Any]) -> int:
    required_fields = (
        "fair_slug",
        "gallery_name_en",
        "source_url",
        "text",
        "text_hash",
        "artist_name_en",
        "artist_name_key",
        "artist_identity_key",
    )
    return sum(1 for key in required_fields if str(row.get(key) or "").strip())


def row_quality_key(
    row: dict[str, Any],
    *,
    source_url: str,
    candidate_name: str,
    applied_pairs: set[tuple[str, str]],
    works_name_by_source: dict[str, str],
) -> tuple[int, int, int, int, int, int, int, str, int]:
    text_hash = str(row.get("text_hash") or "").strip()
    has_identity = int(
        bool(str(row.get("artist_identity_key") or "").strip())
        and bool(str(row.get("artist_name_key") or "").strip())
        and bool(str(row.get("artist_name_en") or "").strip())
    )
    has_exact_apply = int((source_url, text_hash) in applied_pairs)
    has_works_match = int(source_url in works_name_by_source)
    has_valid_name = int(bool(candidate_name) and not is_invalid_artist_name(candidate_name))
    text_len = len(str(row.get("text") or "").strip())
    schema_score = row_schema_score(row)
    has_existing_name = int(bool(sanitize_artist_name_en(str(row.get("artist_name_en") or ""))))
    extracted_at = str(row.get("extracted_at") or "")
    line_no = int(row.get("_line_no") or 0)
    return (
        has_valid_name,
        has_identity,
        has_exact_apply,
        has_works_match,
        schema_score,
        text_len,
        has_existing_name,
        extracted_at,
        -line_no,
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Dry-run canonical incident manifest generator for Artist Text RAG."
    )
    parser.add_argument("--target-year", type=int, default=2025)
    parser.add_argument("--run-id", type=str, default="")
    parser.add_argument("--output-dir", type=Path, default=Path("data/phase1_seed10/logs"))
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    target_year = int(args.target_year)
    output_dir = (REPO_ROOT / args.output_dir).resolve()

    raw_paths = [
        REPO_ROOT / f"data/phase1_seed10/raw/artists_frieze_london_{target_year}.jsonl",
        REPO_ROOT / f"data/phase1_seed10/raw/artists_liste_{target_year}.jsonl",
    ]
    works_paths = [
        REPO_ROOT / "data/phase1_seed10/derived/artist_works_images_frieze_london.jsonl",
        REPO_ROOT / "data/phase1_seed10/derived/artist_works_images_liste.jsonl",
    ]
    apply_path = REPO_ROOT / f"data/current/enrichment/artists_enrichment_apply_output_{target_year}.jsonl"

    raw_rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    for path in raw_paths:
        rows, row_warnings = read_jsonl_rows(path)
        raw_rows.extend(rows)
        warnings.extend(row_warnings)

    works_name_by_source, works_warnings = collect_works_name_by_source(works_paths)
    warnings.extend(works_warnings)
    applied_pairs, applied_by_source_key, apply_warnings = collect_apply_applied_groups(apply_path)
    warnings.extend(apply_warnings)

    actions: list[dict[str, Any]] = []
    quarantine_rows: list[dict[str, Any]] = []
    backfill_plan: list[dict[str, Any]] = []
    review_rows: list[dict[str, Any]] = []

    raw_by_source_group: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    row_meta_by_ref: dict[str, dict[str, Any]] = {}

    for row in raw_rows:
        fair_slug = str(row.get("fair_slug") or "").strip()
        source_url = normalize_source_url(str(row.get("source_url") or ""))
        source_key = canonical_artist_source_key(source_url)
        text_hash = str(row.get("text_hash") or "").strip()
        line_no = int(row.get("_line_no") or 0)
        row_ref = f"{row.get('_source_file')}:{line_no}"

        works_name = works_name_by_source.get(source_url, "")
        candidate_name, candidate_name_origin = pick_candidate_name(
            row_name_en=str(row.get("artist_name_en") or ""),
            works_name_en=works_name,
            source_url=source_url,
        )
        invalid_name = is_invalid_artist_name(candidate_name)

        quarantine_reasons: list[str] = []
        if not source_url:
            quarantine_reasons.append("missing_source_url")
        if source_url and not source_key:
            quarantine_reasons.append("missing_canonical_source_key")
        if invalid_name:
            quarantine_reasons.append("invalid_artist_name")

        meta = {
            "row_ref": row_ref,
            "fair_slug": fair_slug,
            "source_url": source_url,
            "canonical_source_key": source_key,
            "text_hash": text_hash,
            "candidate_name": candidate_name,
            "candidate_name_origin": candidate_name_origin,
            "invalid_name": invalid_name,
            "quarantine_reasons": quarantine_reasons,
        }
        row_meta_by_ref[row_ref] = meta

        if quarantine_reasons:
            quarantine_entry = {
                **meta,
                "action": "quarantine",
            }
            quarantine_rows.append(quarantine_entry)
            actions.append(quarantine_entry)
            continue

        raw_by_source_group[(fair_slug, source_key)].append(row)

    keep_row_refs: set[str] = set()
    duplicate_source_groups: list[dict[str, Any]] = []

    for (fair_slug, source_key), group_rows in raw_by_source_group.items():
        scored: list[tuple[tuple[int, int, int, int, int, int, int, str, int], dict[str, Any]]] = []
        for row in group_rows:
            row_ref = f"{row.get('_source_file')}:{int(row.get('_line_no') or 0)}"
            meta = row_meta_by_ref[row_ref]
            score = row_quality_key(
                row,
                source_url=meta["source_url"],
                candidate_name=meta["candidate_name"],
                applied_pairs=applied_pairs,
                works_name_by_source=works_name_by_source,
            )
            scored.append((score, row))

        scored.sort(key=lambda item: item[0], reverse=True)
        keep_row = scored[0][1]
        keep_ref = f"{keep_row.get('_source_file')}:{int(keep_row.get('_line_no') or 0)}"
        keep_row_refs.add(keep_ref)

        if len(group_rows) > 1:
            duplicate_source_groups.append(
                {
                    "fair_slug": fair_slug,
                    "canonical_source_key": source_key,
                    "group_size": len(group_rows),
                    "keep_row_ref": keep_ref,
                    "row_refs": [
                        f"{r.get('_source_file')}:{int(r.get('_line_no') or 0)}"
                        for r in group_rows
                    ],
                    "source_urls": sorted(
                        {
                            normalize_source_url(str(r.get("source_url") or ""))
                            for r in group_rows
                            if str(r.get("source_url") or "").strip()
                        }
                    ),
                    "text_hashes": sorted({str(r.get("text_hash") or "").strip() for r in group_rows}),
                }
            )

    keep_rows_for_collision: list[dict[str, Any]] = []
    for (fair_slug, source_key), group_rows in raw_by_source_group.items():
        del fair_slug, source_key
        for row in group_rows:
            row_ref = f"{row.get('_source_file')}:{int(row.get('_line_no') or 0)}"
            meta = row_meta_by_ref[row_ref]
            if row_ref in keep_row_refs:
                keep_rows_for_collision.append(
                    {
                        "row_ref": row_ref,
                        "canonical_source_key": meta["canonical_source_key"],
                        "candidate_name": meta["candidate_name"],
                        "source_url": meta["source_url"],
                    }
                )

            action = "keep" if row_ref in keep_row_refs else "drop"
            reasons: list[str] = []
            if action == "drop":
                reasons.append("duplicate_source_group")
            action_entry = {
                **meta,
                "action": action,
                "reasons": reasons,
            }
            actions.append(action_entry)

            if action == "keep":
                missing_fields = [
                    key
                    for key in ("artist_name_en", "artist_name_key", "artist_identity_key")
                    if not str(row.get(key) or "").strip()
                ]
                if missing_fields:
                    proposal_name = meta["candidate_name"]
                    proposal_name_origin = meta["candidate_name_origin"]
                    proposal_status = "backfill_ready"
                    if not proposal_name or is_invalid_artist_name(proposal_name):
                        proposal_status = "backfill_unresolved_invalid_name"
                    proposal_name_key = (
                        build_artist_name_key(proposal_name, meta["source_url"])
                        if proposal_status == "backfill_ready"
                        else ""
                    )
                    proposal_identity_key = (
                        build_artist_identity_key(
                            proposal_name_key,
                            proposal_name,
                            meta["source_url"],
                        )
                        if proposal_status == "backfill_ready"
                        else ""
                    )
                    backfill_item = {
                        "row_ref": row_ref,
                        "fair_slug": meta["fair_slug"],
                        "source_url": meta["source_url"],
                        "canonical_source_key": meta["canonical_source_key"],
                        "missing_fields": missing_fields,
                        "proposal_status": proposal_status,
                        "proposal_artist_name_en": proposal_name,
                        "proposal_artist_name_origin": proposal_name_origin,
                        "proposal_artist_name_key": proposal_name_key,
                        "proposal_artist_identity_key": proposal_identity_key,
                    }
                    backfill_plan.append(backfill_item)
                    if proposal_status != "backfill_ready":
                        review_rows.append(
                            {
                                "type": "unresolved_backfill",
                                **backfill_item,
                            }
                        )

    collisions_by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in keep_rows_for_collision:
        name = str(item.get("candidate_name") or "").strip()
        if not name:
            continue
        collisions_by_name[name.lower()].append(item)

    same_name_collision_groups: list[dict[str, Any]] = []
    for name_key, items in sorted(collisions_by_name.items()):
        source_keys = {str(x.get("canonical_source_key") or "") for x in items if str(x.get("canonical_source_key") or "")}
        if len(source_keys) <= 1:
            continue
        group = {
            "canonical_name_key": name_key,
            "group_size": len(items),
            "canonical_source_key_count": len(source_keys),
            "rows": items,
        }
        same_name_collision_groups.append(group)
        for item in items:
            review_rows.append(
                {
                    "type": "same_name_collision",
                    "canonical_name_key": name_key,
                    "row_ref": item["row_ref"],
                    "canonical_source_key": item["canonical_source_key"],
                    "source_url": item["source_url"],
                }
            )

    multi_applied_source_groups: list[dict[str, Any]] = []
    for source_key, rows in sorted(applied_by_source_key.items()):
        if not source_key or len(rows) <= 1:
            continue
        multi_applied_source_groups.append(
            {
                "canonical_source_key": source_key,
                "group_size": len(rows),
                "rows": rows,
            }
        )

    keep_count = sum(1 for action in actions if action.get("action") == "keep")
    drop_count = sum(1 for action in actions if action.get("action") == "drop")
    quarantine_count = sum(1 for action in actions if action.get("action") == "quarantine")

    run_tag = utc_now_tag()
    run_id = str(args.run_id or "").strip()
    suffix = run_id if run_id else run_tag
    manifest_path = output_dir / f"artist_text_canonical_dryrun_manifest_{target_year}_{suffix}.json"
    summary_path = output_dir / f"artist_text_canonical_dryrun_summary_{target_year}_{suffix}.json"
    manifest_latest = output_dir / "artist_text_canonical_dryrun_manifest_latest.json"
    summary_latest = output_dir / "artist_text_canonical_dryrun_summary_latest.json"

    summary_payload: dict[str, Any] = {
        "runner": "run_artist_text_canonical_dryrun.py",
        "dry_run": True,
        "generated_at": utc_now_iso(),
        "target_year": target_year,
        "run_id": run_id,
        "raw_rows_total": len(raw_rows),
        "raw_unique_source_count": len(
            {
                normalize_source_url(str(row.get("source_url") or ""))
                for row in raw_rows
                if str(row.get("source_url") or "").strip()
            }
        ),
        "action_counts": {
            "keep": keep_count,
            "drop": drop_count,
            "quarantine": quarantine_count,
        },
        "duplicate_source_group_count": len(duplicate_source_groups),
        "multi_applied_source_group_count": len(multi_applied_source_groups),
        "same_name_collision_group_count": len(same_name_collision_groups),
        "backfill_plan_count": len(backfill_plan),
        "review_item_count": len(review_rows),
        "warning_count": len(warnings),
        "warnings": warnings,
        "inputs": {
            "raw_paths": [str(path) for path in raw_paths],
            "apply_path": str(apply_path),
            "works_paths": [str(path) for path in works_paths],
        },
        "outputs": {
            "manifest_path": str(manifest_path),
            "summary_path": str(summary_path),
            "manifest_latest": str(manifest_latest),
            "summary_latest": str(summary_latest),
        },
    }

    manifest_payload: dict[str, Any] = {
        "schema_name": "artist_text_canonical_dryrun_manifest",
        "schema_version": "v1",
        "generated_at": summary_payload["generated_at"],
        "target_year": target_year,
        "run_id": run_id,
        "summary": summary_payload,
        "actions": sorted(
            actions,
            key=lambda item: (
                str(item.get("action") or ""),
                str(item.get("fair_slug") or ""),
                str(item.get("canonical_source_key") or ""),
                str(item.get("row_ref") or ""),
            ),
        ),
        "duplicate_source_groups": duplicate_source_groups,
        "multi_applied_source_groups": multi_applied_source_groups,
        "same_name_collision_groups": same_name_collision_groups,
        "backfill_plan": backfill_plan,
        "quarantine_rows": quarantine_rows,
        "review_rows": review_rows,
    }

    write_json(manifest_path, manifest_payload)
    write_json(summary_path, summary_payload)
    write_json(manifest_latest, manifest_payload)
    write_json(summary_latest, summary_payload)

    print(f"[DRYRUN] target_year={target_year} rows={len(raw_rows)}")
    print(
        "[DRYRUN] actions "
        f"keep={keep_count} drop={drop_count} quarantine={quarantine_count} "
        f"backfill={len(backfill_plan)} review={len(review_rows)}"
    )
    print(
        "[DRYRUN] groups "
        f"duplicate_source={len(duplicate_source_groups)} "
        f"multi_applied_source={len(multi_applied_source_groups)} "
        f"same_name_collision={len(same_name_collision_groups)}"
    )
    print(f"[DRYRUN] manifest={manifest_path}")
    print(f"[DRYRUN] summary={summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
