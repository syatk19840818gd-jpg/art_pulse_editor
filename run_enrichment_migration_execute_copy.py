#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from run_enrichment_exhibitions_preview import utc_now_compact, utc_now_iso

from phase2_art_pulse_config import (
    TARGET_YEAR,
    get_enrichment_current_output_path,
    get_enrichment_current_summary_path,
)

MANIFEST_LATEST_PATH = Path("data/phase1_seed10/logs/enrichment_migration_dryrun_2025_latest.json")
EXECUTION_OUTPUT_DIR = Path("data/phase1_seed10/logs")
CURRENT_DECISION_CHECK_STAMP_ARTISTS = "20260311T042229Z"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target.with_name(f"{target.name}.tmp_copy")
    try:
        shutil.copyfile(source, tmp_path)
        os.replace(tmp_path, target)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def _summary_lookup(manifest: dict[str, Any], category: str, stamp: str) -> dict[str, Any] | None:
    for pair in manifest.get("pairs", []):
        if str(pair.get("category") or "") == category and str(pair.get("stamp") or "") == stamp:
            data = pair.get("summary_data")
            return data if isinstance(data, dict) else None
    return None


def _validate_exhibitions_current(manifest: dict[str, Any], stamp: str) -> tuple[bool, str]:
    summary = _summary_lookup(manifest, "exhibitions", stamp)
    if not isinstance(summary, dict):
        return False, "missing_summary_data"
    if int(summary.get("error_count") or 0) > 0:
        return False, f"error_count={int(summary.get('error_count') or 0)}"
    if int(summary.get("total_applied") or 0) <= 0:
        return False, f"total_applied={int(summary.get('total_applied') or 0)}"
    return True, "manifest_candidate_valid"


def _decide_artists_current_stamp(manifest: dict[str, Any], default_stamp: str) -> tuple[str, str]:
    default_summary = _summary_lookup(manifest, "artists", default_stamp)
    check_summary = _summary_lookup(manifest, "artists", CURRENT_DECISION_CHECK_STAMP_ARTISTS)

    if not isinstance(default_summary, dict):
        return default_stamp, "default_summary_missing_keep_manifest"
    if not isinstance(check_summary, dict):
        return default_stamp, "check_stamp_summary_missing_keep_manifest"

    default_applied = int(default_summary.get("total_applied") or 0)
    check_applied = int(check_summary.get("total_applied") or 0)
    default_skip_nf = int((default_summary.get("counters") or {}).get("skipped_target_row_not_found") or 0)
    check_skip_nf = int((check_summary.get("counters") or {}).get("skipped_target_row_not_found") or 0)
    default_skip_guard = int((default_summary.get("counters") or {}).get("skipped_target_guard_non_artist_utility_url") or 0)
    check_skip_guard = int((check_summary.get("counters") or {}).get("skipped_target_guard_non_artist_utility_url") or 0)

    if check_applied > 0 and check_skip_nf == 0:
        return (
            CURRENT_DECISION_CHECK_STAMP_ARTISTS,
            (
                "override_to_latest_stamp:"
                f"check_applied={check_applied},check_skip_target_row_not_found={check_skip_nf},"
                f"check_skip_guard_non_artist={check_skip_guard}"
            ),
        )
    return (
        default_stamp,
        (
            "keep_manifest_candidate:"
            f"default_applied={default_applied},default_skip_target_row_not_found={default_skip_nf},"
            f"default_skip_guard_non_artist={default_skip_guard},"
            f"check_applied={check_applied},check_skip_target_row_not_found={check_skip_nf},"
            f"check_skip_guard_non_artist={check_skip_guard}"
        ),
    )


def _derive_seed_actions(
    actions: list[dict[str, Any]],
    category: str,
    stamp: str,
    target_year: int,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for action in actions:
        if str(action.get("category") or "") != category:
            continue
        if str(action.get("stamp") or "") != stamp:
            continue
        if str(action.get("action") or "") != "history_copy":
            continue

        source = str(action.get("source_legacy_path") or "")
        if not source:
            continue

        if source.endswith(".jsonl"):
            target = get_enrichment_current_output_path(category, target_year)
        else:
            target = get_enrichment_current_summary_path(category, target_year)

        out.append(
            {
                "category": category,
                "year": target_year,
                "stamp": stamp,
                "source_legacy_path": source,
                "target_new_path": str(target),
                "action": "seed_current_copy",
                "reason": "derived_from_history_copy_with_final_current_stamp",
                "pair_status": "paired_ok",
            }
        )
    return out


def _promote_current_pair(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not entries:
        return []
    prepared: list[tuple[Path, Path, Path, dict[str, Any]]] = []
    backups: dict[Path, Path] = {}
    promoted: list[dict[str, Any]] = []

    try:
        for entry in entries:
            source = Path(str(entry["source_legacy_path"]))
            target = Path(str(entry["target_new_path"]))
            if not source.exists():
                raise FileNotFoundError(f"missing source: {source}")
            target.parent.mkdir(parents=True, exist_ok=True)
            tmp = target.with_name(f"{target.name}.tmp_promote")
            shutil.copyfile(source, tmp)
            if _sha256(tmp) != _sha256(source):
                raise RuntimeError(f"hash mismatch at temp stage: {source} -> {tmp}")
            prepared.append((source, target, tmp, entry))

        for _, target, _, _ in prepared:
            if target.exists():
                backup = target.with_name(f"{target.name}.bak_migrate")
                if backup.exists():
                    backup.unlink(missing_ok=True)
                os.replace(target, backup)
                backups[target] = backup

        for source, target, tmp, entry in prepared:
            os.replace(tmp, target)
            source_hash = _sha256(source)
            target_hash = _sha256(target)
            if source_hash != target_hash:
                raise RuntimeError(f"hash mismatch after promote: {source} -> {target}")
            promoted.append(
                {
                    "category": entry["category"],
                    "stamp": entry["stamp"],
                    "action": entry["action"],
                    "source_path": str(source),
                    "target_path": str(target),
                    "source_bytes": source.stat().st_size,
                    "target_bytes": target.stat().st_size,
                    "source_sha256": source_hash,
                    "target_sha256": target_hash,
                    "status": "copied",
                }
            )

        for backup in backups.values():
            backup.unlink(missing_ok=True)
        return promoted
    except Exception:
        for _, _, tmp, _ in prepared:
            tmp.unlink(missing_ok=True)
        for target, backup in backups.items():
            if backup.exists():
                target.unlink(missing_ok=True)
                os.replace(backup, target)
        raise


def main() -> int:
    started_at = utc_now_iso()
    stamp = utc_now_compact()
    target_year = TARGET_YEAR

    if not MANIFEST_LATEST_PATH.exists():
        raise FileNotFoundError(f"missing dry-run manifest: {MANIFEST_LATEST_PATH}")
    manifest = json.loads(MANIFEST_LATEST_PATH.read_text(encoding="utf-8"))

    actions: list[dict[str, Any]] = list(manifest.get("actions") or [])
    current_candidates = {str(c.get("category") or ""): c for c in manifest.get("current_candidates") or []}

    artists_default_stamp = str((current_candidates.get("artists") or {}).get("stamp") or "")
    exhibitions_default_stamp = str((current_candidates.get("exhibitions") or {}).get("stamp") or "")
    if not artists_default_stamp or not exhibitions_default_stamp:
        raise RuntimeError("missing current candidate stamps in dry-run manifest")

    artists_final_stamp, artists_reason = _decide_artists_current_stamp(manifest, artists_default_stamp)
    exhibitions_ok, exhibitions_reason = _validate_exhibitions_current(manifest, exhibitions_default_stamp)
    if not exhibitions_ok:
        raise RuntimeError(f"invalid exhibitions current candidate: {exhibitions_reason}")
    exhibitions_final_stamp = exhibitions_default_stamp

    history_actions = [a for a in actions if str(a.get("action") or "") == "history_copy"]
    current_actions = []
    current_actions.extend(_derive_seed_actions(actions, "artists", artists_final_stamp, target_year))
    current_actions.extend(_derive_seed_actions(actions, "exhibitions", exhibitions_final_stamp, target_year))

    if len(current_actions) != 4:
        raise RuntimeError(f"unexpected current action count: {len(current_actions)}")

    history_results: list[dict[str, Any]] = []
    for entry in history_actions:
        source = Path(str(entry.get("source_legacy_path") or ""))
        target = Path(str(entry.get("target_new_path") or ""))
        if not source.exists():
            raise FileNotFoundError(f"missing source for history copy: {source}")
        _atomic_copy(source, target)
        source_hash = _sha256(source)
        target_hash = _sha256(target)
        if source_hash != target_hash:
            raise RuntimeError(f"hash mismatch after history copy: {source} -> {target}")
        history_results.append(
            {
                "category": entry.get("category"),
                "stamp": entry.get("stamp"),
                "action": entry.get("action"),
                "source_path": str(source),
                "target_path": str(target),
                "source_bytes": source.stat().st_size,
                "target_bytes": target.stat().st_size,
                "source_sha256": source_hash,
                "target_sha256": target_hash,
                "status": "copied",
            }
        )

    current_results: list[dict[str, Any]] = []
    grouped_current: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in current_actions:
        grouped_current[str(entry.get("category") or "")].append(entry)
    for category in ("artists", "exhibitions"):
        entries = grouped_current.get(category, [])
        if len(entries) != 2:
            raise RuntimeError(f"expected 2 current seed entries for {category}, got {len(entries)}")
        current_results.extend(_promote_current_pair(entries))

    all_sources = [Path(str(a.get("source_legacy_path") or "")) for a in history_actions + current_actions]
    legacy_missing_after = [str(p) for p in all_sources if p and not p.exists()]

    action_counts = dict(Counter(str(a.get("action") or "") for a in history_actions + current_actions))
    result = {
        "task": "A5_MIGRATION_EXECUTE_COPY_01",
        "mode": "copy_only",
        "started_at": started_at,
        "completed_at": utc_now_iso(),
        "target_year": target_year,
        "dryrun_manifest_path": str(MANIFEST_LATEST_PATH),
        "current_decision": {
            "artists_default_stamp": artists_default_stamp,
            "artists_final_stamp": artists_final_stamp,
            "artists_reason": artists_reason,
            "exhibitions_default_stamp": exhibitions_default_stamp,
            "exhibitions_final_stamp": exhibitions_final_stamp,
            "exhibitions_reason": exhibitions_reason,
        },
        "action_counts_executed": action_counts,
        "history_results": history_results,
        "current_results": current_results,
        "legacy_source_missing_after_copy": legacy_missing_after,
        "legacy_preserved": len(legacy_missing_after) == 0,
    }

    EXECUTION_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = EXECUTION_OUTPUT_DIR / f"enrichment_migration_execute_copy_{target_year}_{stamp}.json"
    latest_path = EXECUTION_OUTPUT_DIR / f"enrichment_migration_execute_copy_{target_year}_latest.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    latest_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"[DONE] execute_output={out_path}")
    print(f"[DONE] execute_latest={latest_path}")
    print(f"[DONE] action_counts_executed={action_counts}")
    print(f"[DONE] legacy_preserved={result['legacy_preserved']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
