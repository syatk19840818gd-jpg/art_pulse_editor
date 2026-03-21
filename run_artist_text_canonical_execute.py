#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from phase1_artist_link_utils import is_invalid_artist_name, sanitize_artist_name_en
from phase2_art_pulse_config import (
    TARGET_YEAR,
    get_enrichment_current_output_path,
    get_enrichment_current_summary_path,
    get_enrichment_history_output_path,
    get_enrichment_history_summary_path,
    promote_history_file_to_current,
)
from phase2_art_pulse_readonly import build_art_pulse_overview
from phase2_artist_search_readonly import load_artist_records_readonly
from run_artist_text_canonical_dryrun import (
    build_artist_identity_key,
    build_artist_name_key,
    normalize_source_url,
    read_jsonl_rows,
    write_json,
)

REPO_ROOT = Path(__file__).resolve().parent
LOG_DIR = REPO_ROOT / "data/phase1_seed10/logs"
RAW_PATHS = {
    "frieze_london": REPO_ROOT / f"data/phase1_seed10/raw/artists_frieze_london_{TARGET_YEAR}.jsonl",
    "liste": REPO_ROOT / f"data/phase1_seed10/raw/artists_liste_{TARGET_YEAR}.jsonl",
}
WORKS_PATHS = {
    "frieze_london": REPO_ROOT / "data/phase1_seed10/derived/artist_works_images_frieze_london.jsonl",
    "liste": REPO_ROOT / "data/phase1_seed10/derived/artist_works_images_liste.jsonl",
}
CURRENT_APPLY_PATH = REPO_ROOT / get_enrichment_current_output_path("artists", TARGET_YEAR)
CURRENT_SUMMARY_PATH = REPO_ROOT / get_enrichment_current_summary_path("artists", TARGET_YEAR)
DRYRUN_MANIFEST_LATEST_PATH = REPO_ROOT / "data/phase1_seed10/logs/artist_text_canonical_dryrun_manifest_latest.json"
DRYRUN_SUMMARY_LATEST_PATH = REPO_ROOT / "data/phase1_seed10/logs/artist_text_canonical_dryrun_summary_latest.json"
TRAILING_DIGIT_RE = re.compile(r".*\s\d+$")

EXPECTED_SHA256 = {
    "dryrun_manifest": "90d488f59fd9a7aae4686a1924e76d957d1f8c43111b74bcec5e1c934e130bb6",
    "dryrun_summary": "57f7c0be09c4df128a03617552ce209e053d8dbb9264fcd7eccf9501df25f0ad",
    "raw_frieze": "75bd8c4b9b4e6f310834779a9426482600d66d542b4affe5b864c2e68f6a149c",
    "raw_liste": "d417b6208cf56ea04854804deae2a11738280f9f5575f9b81d4d8480f7099e09",
    "apply_current": "9474f903540d21eeba65aa6172bf6060c7f6de8c03a89e42fd9f43725abaf30c",
    "works_frieze": "b9bdc13ebe65fbfbca45a84633a580baf5ef8a3dbaaca5beac621e8b0ac865b1",
    "works_liste": "e2186b1c8f3c7093be27a0e8ee9cf61098238694320b532a9309edf5737dde7e",
}
EXPECTED_COUNTS = {
    "keep": 223,
    "drop": 65,
    "quarantine": 2,
    "backfill": 39,
    "review": 2,
    "duplicate_source_groups": 61,
    "multi_applied_source_groups": 57,
    "same_name_collision_groups": 1,
    "raw_total": 290,
    "raw_unique_source": 225,
}
EXPECTED_FAIR_ACTIONS = {
    "frieze_london": {"keep": 126, "drop": 42, "quarantine": 2},
    "liste": {"keep": 97, "drop": 23, "quarantine": 0},
}
EXPECTED_FEATURE3_COUNTS = {"frieze_london": 126, "liste": 97, "total": 223}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utc_now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            payload = json.loads(text)
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")


def atomic_copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target.with_name(f"{target.name}.tmp_copy")
    try:
        shutil.copyfile(source, tmp_path)
        os.replace(tmp_path, target)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def normalize_for_pair(url: str) -> str:
    return normalize_source_url(str(url or ""))


def resolve_dryrun_artifact(kind: str, *, target_year: int) -> Path:
    latest_path = DRYRUN_MANIFEST_LATEST_PATH if kind == "manifest" else DRYRUN_SUMMARY_LATEST_PATH
    if latest_path.exists():
        return latest_path
    pattern = f"artist_text_canonical_dryrun_{kind}_{target_year}_*.json"
    candidates = list(LOG_DIR.glob(pattern))
    if candidates:
        return max(candidates, key=lambda path: path.stat().st_mtime)
    raise FileNotFoundError(f"missing artist canonical dryrun {kind}: {pattern}")


def build_row_ref(path: Path, line_no: int) -> str:
    return f"{path}:{line_no}"


def should_flag_artist_name(name: str) -> bool:
    cleaned = sanitize_artist_name_en(name)
    if not cleaned or is_invalid_artist_name(cleaned):
        return True
    return bool(TRAILING_DIGIT_RE.fullmatch(str(name or "").strip()))


def collect_feature1_metric() -> dict[str, Any]:
    overview = build_art_pulse_overview("Frieze London + Liste Art Fair Basel", "reporter_01", [])
    artist_candidates = list(overview.get("artist_candidates") or [])
    flagged = [
        {
            "artist": str(item.get("artist") or ""),
            "source_url": str(item.get("source_url") or ""),
        }
        for item in artist_candidates
        if should_flag_artist_name(str(item.get("artist") or ""))
    ]
    return {
        "artist_candidate_count": len(artist_candidates),
        "artist_candidate_flagged_count": len(flagged),
        "flagged_examples": flagged[:10],
        "warning_count": len(list(overview.get("warnings") or [])),
    }


def current_apply_applied_map(rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        if str(row.get("status") or "").strip() != "APPLIED":
            continue
        key = (
            normalize_for_pair(str(row.get("source_url") or "")),
            str(row.get("text_hash") or "").strip(),
        )
        if not key[0] or not key[1]:
            continue
        out[key] = row
    return out


def stage_request_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    request_rows: list[dict[str, Any]] = []
    for row in rows:
        text_hash = str(row.get("text_hash") or "").strip()
        source_url = str(row.get("source_url") or "").strip()
        request_rows.append(
            {
                "request_id": f"canonical_repair_artists_enrich_{text_hash}",
                "text_hash": text_hash,
                "fair_slug": str(row.get("fair_slug") or "").strip(),
                "gallery_name_en": str(row.get("gallery_name_en") or "").strip(),
                "gallery_name_kana": str(row.get("gallery_name_kana") or "").strip(),
                "source_urls": [source_url] if source_url else [],
                "target_year": int(row.get("target_year") or TARGET_YEAR),
                "rag_category": str(row.get("rag_category") or "artists_text"),
                "needs_fields": [],
                "text_length": len(str(row.get("text") or "")),
                "text": str(row.get("text") or ""),
            }
        )
    return request_rows


def build_preflight(
    manifest: dict[str, Any],
    summary: dict[str, Any],
    *,
    manifest_path: Path,
    summary_path: Path,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def record(name: str, ok: bool, details: dict[str, Any]) -> None:
        checks.append({"name": name, "ok": bool(ok), "details": details})

    manifest_sha = sha256_file(manifest_path)
    summary_sha = sha256_file(summary_path)
    record(
        "dryrun_sha256",
        manifest_sha == EXPECTED_SHA256["dryrun_manifest"] and summary_sha == EXPECTED_SHA256["dryrun_summary"],
        {
            "manifest_actual": manifest_sha,
            "manifest_expected": EXPECTED_SHA256["dryrun_manifest"],
            "summary_actual": summary_sha,
            "summary_expected": EXPECTED_SHA256["dryrun_summary"],
        },
    )

    input_shas = {
        "raw_frieze": sha256_file(RAW_PATHS["frieze_london"]),
        "raw_liste": sha256_file(RAW_PATHS["liste"]),
        "apply_current": sha256_file(CURRENT_APPLY_PATH),
        "works_frieze": sha256_file(WORKS_PATHS["frieze_london"]),
        "works_liste": sha256_file(WORKS_PATHS["liste"]),
    }
    record(
        "input_sha256",
        all(input_shas[key] == EXPECTED_SHA256[key] for key in input_shas),
        {
            "actual": input_shas,
            "expected": {key: EXPECTED_SHA256[key] for key in input_shas},
        },
    )

    action_counts = dict(summary.get("action_counts") or {})
    record(
        "summary_counts",
        (
            int(summary.get("raw_rows_total") or 0) == EXPECTED_COUNTS["raw_total"]
            and int(summary.get("raw_unique_source_count") or 0) == EXPECTED_COUNTS["raw_unique_source"]
            and int(action_counts.get("keep") or 0) == EXPECTED_COUNTS["keep"]
            and int(action_counts.get("drop") or 0) == EXPECTED_COUNTS["drop"]
            and int(action_counts.get("quarantine") or 0) == EXPECTED_COUNTS["quarantine"]
            and int(summary.get("backfill_plan_count") or 0) == EXPECTED_COUNTS["backfill"]
            and int(summary.get("review_item_count") or 0) == EXPECTED_COUNTS["review"]
            and int(summary.get("duplicate_source_group_count") or 0) == EXPECTED_COUNTS["duplicate_source_groups"]
            and int(summary.get("multi_applied_source_group_count") or 0) == EXPECTED_COUNTS["multi_applied_source_groups"]
            and int(summary.get("same_name_collision_group_count") or 0) == EXPECTED_COUNTS["same_name_collision_groups"]
        ),
        {
            "raw_rows_total": int(summary.get("raw_rows_total") or 0),
            "raw_unique_source_count": int(summary.get("raw_unique_source_count") or 0),
            "action_counts": action_counts,
            "backfill_plan_count": int(summary.get("backfill_plan_count") or 0),
            "review_item_count": int(summary.get("review_item_count") or 0),
            "duplicate_source_group_count": int(summary.get("duplicate_source_group_count") or 0),
            "multi_applied_source_group_count": int(summary.get("multi_applied_source_group_count") or 0),
            "same_name_collision_group_count": int(summary.get("same_name_collision_group_count") or 0),
        },
    )

    fair_actions: dict[str, Counter[str]] = defaultdict(Counter)
    for action in manifest.get("actions", []):
        fair_slug = str(action.get("fair_slug") or "")
        fair_actions[fair_slug][str(action.get("action") or "")] += 1
    fair_payload = {
        fair_slug: {key: int(counter.get(key) or 0) for key in ("keep", "drop", "quarantine")}
        for fair_slug, counter in fair_actions.items()
    }
    record("fair_action_counts", fair_payload == EXPECTED_FAIR_ACTIONS, {"actual": fair_payload, "expected": EXPECTED_FAIR_ACTIONS})

    backfill_plan = list(manifest.get("backfill_plan") or [])
    backfill_status = Counter(str(item.get("proposal_status") or "") for item in backfill_plan)
    record(
        "backfill_ready",
        len(backfill_plan) == EXPECTED_COUNTS["backfill"] and backfill_status == Counter({"backfill_ready": EXPECTED_COUNTS["backfill"]}),
        {"status_counts": dict(backfill_status), "count": len(backfill_plan)},
    )

    review_rows = list(manifest.get("review_rows") or [])
    quarantine_rows = list(manifest.get("quarantine_rows") or [])
    record(
        "review_quarantine",
        (
            len(review_rows) == EXPECTED_COUNTS["review"]
            and len(quarantine_rows) == EXPECTED_COUNTS["quarantine"]
            and all(str(item.get("type") or "") == "same_name_collision" for item in review_rows)
            and all("invalid_artist_name" in list(item.get("quarantine_reasons") or []) for item in quarantine_rows)
        ),
        {
            "review_count": len(review_rows),
            "review_types": sorted({str(item.get("type") or "") for item in review_rows}),
            "quarantine_count": len(quarantine_rows),
            "quarantine_reason_sets": [list(item.get("quarantine_reasons") or []) for item in quarantine_rows],
        },
    )

    keep_hash_by_source = {
        str(item.get("canonical_source_key") or ""): str(item.get("text_hash") or "")
        for item in manifest.get("actions", [])
        if str(item.get("action") or "") == "keep"
    }
    multi_groups = list(manifest.get("multi_applied_source_groups") or [])
    resolved_multi = 0
    for group in multi_groups:
        source_key = str(group.get("canonical_source_key") or "")
        keep_hash = keep_hash_by_source.get(source_key, "")
        hashes = {str(row.get("text_hash") or "") for row in group.get("rows", [])}
        if keep_hash and keep_hash in hashes:
            resolved_multi += 1
    record(
        "multi_applied_resolution",
        len(multi_groups) == EXPECTED_COUNTS["multi_applied_source_groups"] and resolved_multi == len(multi_groups),
        {"group_count": len(multi_groups), "resolved_group_count": resolved_multi},
    )

    record("feature1_baseline_smoke", True, collect_feature1_metric())
    return {
        "started_at": utc_now_iso(),
        "checks": checks,
        "ok": all(item["ok"] for item in checks),
    }


def create_backup(stage_dir: Path) -> dict[str, Any]:
    backup_dir = stage_dir / "backup"
    files_dir = backup_dir / "files"
    files_dir.mkdir(parents=True, exist_ok=True)

    targets = [
        RAW_PATHS["frieze_london"],
        RAW_PATHS["liste"],
        CURRENT_APPLY_PATH,
        CURRENT_SUMMARY_PATH,
        REPO_ROOT / "data/phase1_seed10/logs/artist_master_global.json",
        REPO_ROOT / f"data/phase1_seed10/logs/visited_pages_seed10_{TARGET_YEAR}.json",
        REPO_ROOT / f"data/phase1_seed10/logs/failed_fetches_seed10_{TARGET_YEAR}.json",
        REPO_ROOT / f"data/phase1_seed10/logs/skipped_images_seed10_{TARGET_YEAR}.json",
        REPO_ROOT / f"data/phase1_seed10/logs/visited_pages_artists_seed10_{TARGET_YEAR}.json",
        REPO_ROOT / f"data/phase1_seed10/logs/failed_fetches_artists_seed10_{TARGET_YEAR}.json",
    ]

    entries: list[dict[str, Any]] = []
    for path in targets:
        rel = path.relative_to(REPO_ROOT)
        entry: dict[str, Any] = {
            "path": str(path),
            "relative_path": rel.as_posix(),
            "exists_at_start": path.exists(),
        }
        if path.exists():
            backup_path = files_dir / rel
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, backup_path)
            entry["backup_path"] = str(backup_path)
            entry["sha256"] = sha256_file(path)
            entry["bytes"] = path.stat().st_size
        else:
            entry["backup_path"] = ""
            entry["sha256"] = ""
            entry["bytes"] = 0
        entries.append(entry)

    payload = {
        "started_at": utc_now_iso(),
        "entries": entries,
    }
    write_json(backup_dir / "backup_manifest.json", payload)
    return payload


def restore_from_backup(backup_manifest: dict[str, Any]) -> dict[str, Any]:
    restored: list[dict[str, Any]] = []
    for entry in backup_manifest.get("entries", []):
        target = Path(str(entry.get("path") or ""))
        backup_path = Path(str(entry.get("backup_path") or ""))
        exists_at_start = bool(entry.get("exists_at_start"))
        if exists_at_start and backup_path.exists():
            atomic_copy(backup_path, target)
            restored.append(
                {
                    "path": str(target),
                    "restored_sha256": sha256_file(target),
                    "expected_sha256": str(entry.get("sha256") or ""),
                    "status": "restored",
                }
            )
        elif not exists_at_start and target.exists():
            target.unlink(missing_ok=True)
            restored.append({"path": str(target), "status": "removed_created_file"})
    return {
        "restored": restored,
        "ok": all(
            item.get("status") != "restored"
            or str(item.get("restored_sha256") or "") == str(item.get("expected_sha256") or "")
            for item in restored
        ),
    }


def build_staging(manifest: dict[str, Any], stage_dir: Path) -> dict[str, Any]:
    actions_by_ref = {
        str(item.get("row_ref") or ""): item
        for item in manifest.get("actions", [])
    }
    backfill_by_ref = {
        str(item.get("row_ref") or ""): item
        for item in manifest.get("backfill_plan", [])
    }
    same_name_review_refs = {
        str(item.get("row_ref") or "")
        for item in manifest.get("review_rows", [])
        if str(item.get("type") or "") == "same_name_collision"
    }

    staging_dir = stage_dir / "staging"
    raw_stage_dir = staging_dir / "raw"
    raw_stage_dir.mkdir(parents=True, exist_ok=True)

    repaired_rows_by_fair: dict[str, list[dict[str, Any]]] = {"frieze_london": [], "liste": []}
    quarantine_rows: list[dict[str, Any]] = []
    kept_rows_ordered: list[dict[str, Any]] = []
    sanitized_name_changes = 0

    for fair_slug, raw_path in RAW_PATHS.items():
        rows, warnings = read_jsonl_rows(raw_path)
        if warnings:
            raise RuntimeError(f"raw read warnings for {raw_path}: {warnings}")
        for row in rows:
            row_ref = build_row_ref(raw_path, int(row.get("_line_no") or 0))
            action = actions_by_ref.get(row_ref)
            if action is None:
                raise RuntimeError(f"missing dry-run action for {row_ref}")

            base_row = {key: value for key, value in row.items() if not str(key).startswith("_")}
            status = str(action.get("action") or "")
            if status == "drop":
                continue
            if status == "quarantine":
                quarantine_rows.append(
                    {
                        **base_row,
                        "quarantine_reasons": list(action.get("quarantine_reasons") or []),
                        "canonical_source_key": str(action.get("canonical_source_key") or ""),
                        "candidate_name": str(action.get("candidate_name") or ""),
                        "candidate_name_origin": str(action.get("candidate_name_origin") or ""),
                        "invalid_name": bool(action.get("invalid_name")),
                        "source_row_ref": row_ref,
                    }
                )
                continue
            if status != "keep":
                raise RuntimeError(f"unsupported action={status} for {row_ref}")

            repaired_row = deepcopy(base_row)
            source_url = str(repaired_row.get("source_url") or "").strip()
            candidate_name = sanitize_artist_name_en(
                str(action.get("candidate_name") or repaired_row.get("artist_name_en") or "")
            )
            if not candidate_name or is_invalid_artist_name(candidate_name):
                raise RuntimeError(f"invalid keep candidate_name for {row_ref}: {candidate_name!r}")

            if candidate_name != str(repaired_row.get("artist_name_en") or "").strip():
                sanitized_name_changes += 1
            repaired_row["artist_name_en"] = candidate_name
            repaired_row["artist_name_key"] = build_artist_name_key(candidate_name, source_url)
            repaired_row["artist_identity_key"] = build_artist_identity_key(
                str(repaired_row.get("artist_name_key") or ""),
                candidate_name,
                source_url,
            )

            backfill_item = backfill_by_ref.get(row_ref)
            if backfill_item is not None:
                if str(backfill_item.get("proposal_status") or "") != "backfill_ready":
                    raise RuntimeError(f"backfill proposal not ready for {row_ref}")
                repaired_row["artist_name_en"] = str(backfill_item.get("proposal_artist_name_en") or repaired_row["artist_name_en"])
                repaired_row["artist_name_key"] = str(backfill_item.get("proposal_artist_name_key") or repaired_row["artist_name_key"])
                repaired_row["artist_identity_key"] = str(
                    backfill_item.get("proposal_artist_identity_key") or repaired_row["artist_identity_key"]
                )

            repaired_rows_by_fair[fair_slug].append(repaired_row)
            kept_rows_ordered.append(repaired_row)

    raw_stage_paths: dict[str, Path] = {}
    for fair_slug, rows in repaired_rows_by_fair.items():
        stage_path = raw_stage_dir / RAW_PATHS[fair_slug].name
        write_jsonl(stage_path, rows)
        raw_stage_paths[fair_slug] = stage_path

    quarantine_path = staging_dir / f"artists_quarantine_{TARGET_YEAR}.jsonl"
    write_jsonl(quarantine_path, quarantine_rows)

    current_apply_rows = read_jsonl(CURRENT_APPLY_PATH)
    applied_map = current_apply_applied_map(current_apply_rows)
    staged_apply_rows: list[dict[str, Any]] = []
    missing_apply_pairs: list[dict[str, Any]] = []
    for row in kept_rows_ordered:
        key = (normalize_for_pair(str(row.get("source_url") or "")), str(row.get("text_hash") or "").strip())
        apply_row = applied_map.get(key)
        if apply_row is None:
            missing_apply_pairs.append({"source_url": key[0], "text_hash": key[1]})
            continue
        repaired_apply = deepcopy(apply_row)
        repaired_apply["fair_slug"] = str(row.get("fair_slug") or repaired_apply.get("fair_slug") or "")
        repaired_apply["source_url"] = str(row.get("source_url") or repaired_apply.get("source_url") or "")
        repaired_apply["text_hash"] = str(row.get("text_hash") or repaired_apply.get("text_hash") or "")
        staged_apply_rows.append(repaired_apply)
    if missing_apply_pairs:
        raise RuntimeError(f"missing exact apply pairs for keep rows: {missing_apply_pairs[:5]}")

    requests_stage_path = staging_dir / f"artists_enrichment_requests_{TARGET_YEAR}_canonical_repair.jsonl"
    write_jsonl(requests_stage_path, stage_request_rows(kept_rows_ordered))

    apply_stage_path = staging_dir / f"artists_enrichment_apply_output_{TARGET_YEAR}_canonical_repair.jsonl"
    write_jsonl(apply_stage_path, staged_apply_rows)

    summary_stage_path = staging_dir / f"artists_enrichment_apply_summary_{TARGET_YEAR}_canonical_repair.json"
    apply_summary = {
        "started_at": utc_now_iso(),
        "completed_at": utc_now_iso(),
        "target_year": TARGET_YEAR,
        "rag_category": "artists_text",
        "repair_mode": "canonical_rebuild_from_existing_apply",
        "requests_path": str(requests_stage_path),
        "raw_input_paths": {fair_slug: str(path) for fair_slug, path in raw_stage_paths.items()},
        "apply_output_path": str(apply_stage_path),
        "apply_summary_path": str(summary_stage_path),
        "current_output_path": str(CURRENT_APPLY_PATH),
        "current_summary_path": str(CURRENT_SUMMARY_PATH),
        "source_apply_path": str(CURRENT_APPLY_PATH),
        "total_targeted": len(kept_rows_ordered),
        "total_applied": len(staged_apply_rows),
        "total_not_updated": 0,
        "warning_count": 0,
        "warning_rows": 0,
        "generated_openai": 0,
        "generated_fallback": 0,
        "headline_empty_total": sum(1 for row in staged_apply_rows if not str(row.get("headline_ja") or "").strip()),
        "summary_empty_total": sum(1 for row in staged_apply_rows if not str(row.get("summary_ja") or "").strip()),
        "artist_name_kana_empty_total": sum(1 for row in staged_apply_rows if not str(row.get("artist_name_kana") or "").strip()),
        "headline_over_limit": 0,
        "summary_over_limit": 0,
        "artist_name_kana_over_limit": 0,
        "raw_text_changed_count": 0,
        "counters": {
            "canonical_keep_rows": len(kept_rows_ordered),
            "canonical_drop_rows": EXPECTED_COUNTS["drop"],
            "canonical_quarantine_rows": len(quarantine_rows),
            "canonical_backfill_rows": len(backfill_by_ref),
            "canonical_multi_applied_resolved": EXPECTED_COUNTS["multi_applied_source_groups"],
            "canonical_review_rows": len(same_name_review_refs),
            "applied": len(staged_apply_rows),
        },
        "enrich_model": "carry_forward_existing_apply",
        "enrich_use_openai_batch": "0",
        "enrich_completion_window": "",
        "enrich_prompt_version": "artists_canonical_repair_v1",
        "openai_client_available": False,
        "workers": 0,
    }
    write_json(summary_stage_path, apply_summary)

    return {
        "raw_stage_paths": {fair_slug: str(path) for fair_slug, path in raw_stage_paths.items()},
        "quarantine_path": str(quarantine_path),
        "requests_stage_path": str(requests_stage_path),
        "apply_stage_path": str(apply_stage_path),
        "summary_stage_path": str(summary_stage_path),
        "keep_count": len(kept_rows_ordered),
        "drop_count": EXPECTED_COUNTS["drop"],
        "quarantine_count": len(quarantine_rows),
        "backfill_count": len(backfill_by_ref),
        "sanitized_name_changes": sanitized_name_changes,
        "raw_rows_by_fair": {fair_slug: len(rows) for fair_slug, rows in repaired_rows_by_fair.items()},
    }


def promote(stage_dir: Path) -> dict[str, Any]:
    staging_dir = stage_dir / "staging"
    raw_promoted: list[str] = []
    for fair_slug, raw_path in RAW_PATHS.items():
        stage_path = staging_dir / "raw" / raw_path.name
        atomic_copy(stage_path, raw_path)
        raw_promoted.append(str(raw_path))

    history_stamp = utc_now_tag()
    history_output_path = REPO_ROOT / get_enrichment_history_output_path("artists", history_stamp, TARGET_YEAR)
    history_summary_path = REPO_ROOT / get_enrichment_history_summary_path("artists", history_stamp, TARGET_YEAR)
    apply_stage_path = staging_dir / f"artists_enrichment_apply_output_{TARGET_YEAR}_canonical_repair.jsonl"
    summary_stage_path = staging_dir / f"artists_enrichment_apply_summary_{TARGET_YEAR}_canonical_repair.json"

    atomic_copy(apply_stage_path, history_output_path)
    atomic_copy(summary_stage_path, history_summary_path)
    promote_history_file_to_current(history_output_path, CURRENT_APPLY_PATH)
    promote_history_file_to_current(history_summary_path, CURRENT_SUMMARY_PATH)

    return {
        "raw_promoted": raw_promoted,
        "history_output_path": str(history_output_path),
        "history_summary_path": str(history_summary_path),
        "current_output_path": str(CURRENT_APPLY_PATH),
        "current_summary_path": str(CURRENT_SUMMARY_PATH),
    }


def collect_smoke() -> dict[str, Any]:
    feature3 = load_artist_records_readonly()
    feature3_trailing = [
        {
            "artist_name": str(row.get("artist_name") or ""),
            "source_url": str(row.get("source_url") or ""),
        }
        for row in feature3.records
        if TRAILING_DIGIT_RE.fullmatch(str(row.get("artist_name") or "").strip())
    ]

    raw_rows = []
    for raw_path in RAW_PATHS.values():
        raw_rows.extend(read_jsonl(raw_path))
    keep_pairs = {
        (normalize_for_pair(str(row.get("source_url") or "")), str(row.get("text_hash") or "").strip())
        for row in raw_rows
        if str(row.get("source_url") or "").strip() and str(row.get("text_hash") or "").strip()
    }
    current_apply_rows = read_jsonl(CURRENT_APPLY_PATH)
    current_applied_pairs = {
        (normalize_for_pair(str(row.get("source_url") or "")), str(row.get("text_hash") or "").strip())
        for row in current_apply_rows
        if str(row.get("status") or "").strip() == "APPLIED"
        and str(row.get("source_url") or "").strip()
        and str(row.get("text_hash") or "").strip()
    }
    join_exact = sum(1 for pair in keep_pairs if pair in current_applied_pairs)

    multi_applied_groups: dict[str, set[str]] = defaultdict(set)
    for row in current_apply_rows:
        if str(row.get("status") or "").strip() != "APPLIED":
            continue
        source_key = normalize_for_pair(str(row.get("source_url") or ""))
        if not source_key:
            continue
        multi_applied_groups[source_key].add(str(row.get("text_hash") or "").strip())
    unresolved_multi = {
        key: sorted(hashes)
        for key, hashes in multi_applied_groups.items()
        if len([value for value in hashes if value]) > 1
    }

    return {
        "feature3": {
            "total_rows": feature3.total_rows,
            "fair_rows": feature3.fair_rows,
            "trailing_digit_count": len(feature3_trailing),
            "trailing_digit_examples": feature3_trailing[:10],
            "warning_count": len(feature3.warnings),
            "join_exact_pairs": join_exact,
            "keep_pairs_total": len(keep_pairs),
            "multi_applied_unresolved_count": len(unresolved_multi),
            "multi_applied_unresolved_examples": [
                {"source_url": key, "text_hashes": hashes}
                for key, hashes in list(unresolved_multi.items())[:10]
            ],
        },
        "feature1": collect_feature1_metric(),
    }


def evaluate_go(preflight: dict[str, Any], smoke: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if not preflight.get("ok"):
        reasons.append("preflight_failed")

    feature3 = dict(smoke.get("feature3") or {})
    fair_rows = dict(feature3.get("fair_rows") or {})
    if int(feature3.get("trailing_digit_count") or 0) != 0:
        reasons.append("feature3_trailing_digit_nonzero")
    if int(feature3.get("total_rows") or 0) < EXPECTED_FEATURE3_COUNTS["total"]:
        reasons.append("feature3_total_rows_below_threshold")
    if int(fair_rows.get("frieze_london") or 0) < EXPECTED_FEATURE3_COUNTS["frieze_london"]:
        reasons.append("feature3_frieze_rows_below_threshold")
    if int(fair_rows.get("liste") or 0) < EXPECTED_FEATURE3_COUNTS["liste"]:
        reasons.append("feature3_liste_rows_below_threshold")
    if int(feature3.get("join_exact_pairs") or 0) != EXPECTED_COUNTS["keep"]:
        reasons.append("feature3_exact_join_mismatch")
    if int(feature3.get("multi_applied_unresolved_count") or 0) != 0:
        reasons.append("multi_applied_unresolved")

    baseline = None
    for check in preflight.get("checks", []):
        if str(check.get("name") or "") == "feature1_baseline_smoke":
            baseline = dict(check.get("details") or {})
            break
    feature1 = dict(smoke.get("feature1") or {})
    if baseline is not None and int(feature1.get("artist_candidate_flagged_count") or 0) > int(
        baseline.get("artist_candidate_flagged_count") or 0
    ):
        reasons.append("feature1_artist_candidate_issue_worsened")

    return len(reasons) == 0, reasons


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Execute canonical repair for Artist Text RAG.")
    parser.add_argument("--target-year", type=int, default=TARGET_YEAR)
    parser.add_argument("--run-id", type=str, default="P0_ARTIST_TEXT_CANONICAL_REPAIR_EXECUTE_RUN_01A")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    if int(args.target_year) != TARGET_YEAR:
        raise ValueError(f"Unsupported target year: {args.target_year}")

    stamp = utc_now_tag()
    stage_dir = LOG_DIR / f"artist_text_canonical_execute_{stamp}"
    stage_dir.mkdir(parents=True, exist_ok=True)
    preflight_path = stage_dir / "preflight.json"
    verdict_path = stage_dir / "verdict.json"

    dryrun_manifest_path = resolve_dryrun_artifact("manifest", target_year=TARGET_YEAR)
    dryrun_summary_path = resolve_dryrun_artifact("summary", target_year=TARGET_YEAR)
    manifest = read_json(dryrun_manifest_path)
    summary = read_json(dryrun_summary_path)
    preflight = build_preflight(
        manifest,
        summary,
        manifest_path=dryrun_manifest_path,
        summary_path=dryrun_summary_path,
    )
    write_json(preflight_path, preflight)
    if not preflight.get("ok"):
        verdict = {
            "run_id": str(args.run_id),
            "started_at": preflight.get("started_at"),
            "completed_at": utc_now_iso(),
            "status": "NO_GO",
            "stage": "preflight",
            "preflight_path": str(preflight_path),
            "rollback_executed": False,
            "reasons": [check["name"] for check in preflight.get("checks", []) if not check.get("ok")],
        }
        write_json(verdict_path, verdict)
        return 2

    backup_manifest = create_backup(stage_dir)
    promote_result: dict[str, Any] = {}
    rollback_result: dict[str, Any] = {"ok": True, "restored": []}

    try:
        staging = build_staging(manifest, stage_dir)
        promote_result = promote(stage_dir)
        smoke = collect_smoke()
        go, reasons = evaluate_go(preflight, smoke)
        if not go:
            rollback_result = restore_from_backup(backup_manifest)
            verdict = {
                "run_id": str(args.run_id),
                "started_at": preflight.get("started_at"),
                "completed_at": utc_now_iso(),
                "status": "NO_GO",
                "stage": "smoke",
                "preflight_path": str(preflight_path),
                "backup_manifest_path": str(stage_dir / "backup/backup_manifest.json"),
                "staging": staging,
                "promote": promote_result,
                "smoke": smoke,
                "rollback_executed": True,
                "rollback": rollback_result,
                "reasons": reasons,
            }
            write_json(verdict_path, verdict)
            return 3

        verdict = {
            "run_id": str(args.run_id),
            "started_at": preflight.get("started_at"),
            "completed_at": utc_now_iso(),
            "status": "GO",
            "stage": "complete",
            "preflight_path": str(preflight_path),
            "backup_manifest_path": str(stage_dir / "backup/backup_manifest.json"),
            "staging": staging,
            "promote": promote_result,
            "smoke": smoke,
            "rollback_executed": False,
            "reasons": [],
        }
        write_json(verdict_path, verdict)
        return 0
    except Exception as exc:
        rollback_result = restore_from_backup(backup_manifest)
        verdict = {
            "run_id": str(args.run_id),
            "started_at": preflight.get("started_at"),
            "completed_at": utc_now_iso(),
            "status": "NO_GO",
            "stage": "exception",
            "preflight_path": str(preflight_path),
            "backup_manifest_path": str(stage_dir / "backup/backup_manifest.json"),
            "promote": promote_result,
            "rollback_executed": True,
            "rollback": rollback_result,
            "error": f"{type(exc).__name__}: {exc}",
        }
        write_json(verdict_path, verdict)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
