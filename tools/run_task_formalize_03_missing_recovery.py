#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import run_phase1_seed10_artist_image_collect as collect
from phase1_ledger_contract import (
    get_phase1_artist_master_global_path,
    get_phase1_logs_dir,
)
from phase2_art_pulse_config import (
    get_phase1_legacy_trash_root,
    get_phase1_legacy_trial_root,
    resolve_image_local_path,
)

try:
    import run_phase1_seed10_r2_sync as r2_sync
except Exception:  # pragma: no cover
    r2_sync = None


LOG_DIR = (PROJECT_ROOT / get_phase1_logs_dir()).resolve()
TRIAL_ROOT = (PROJECT_ROOT / get_phase1_legacy_trial_root()).resolve()
TRASH_ROOT = (PROJECT_ROOT / get_phase1_legacy_trash_root()).resolve()

INPUT_DRYRUN_PATH = LOG_DIR / "dryrun_run_phase1_seed10_artist_image_collect_task_confirm_01.json"
OUTPUT_DRYRUN_PATH = LOG_DIR / "dryrun_run_phase1_seed10_artist_image_collect_task_formalize_03.json"
OUTPUT_JSON_PATH = LOG_DIR / "phase1_7_missing_recovery_artist_images_task_formalize_03.json"
OUTPUT_MD_PATH = LOG_DIR / "phase1_7_missing_recovery_artist_images_task_formalize_03.md"

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".avif"}
TARGET_YEAR = collect.TARGET_YEAR_DEFAULT
TARGET_IMAGES_PER_ARTIST = collect.TARGET_IMAGES_PER_ARTIST_DEFAULT


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_hashes(value: Any) -> list[str]:
    return collect.normalize_hash_list(value)


def normalize_years(value: Any) -> list[int]:
    return collect.normalize_year_list(value)


def metadata_lookup_key(row: dict[str, Any]) -> str:
    source_url = str(row.get("source_url") or "")
    artist_name_en = str(row.get("artist_name_en") or "").strip() or collect.build_artist_name_en_from_source_url(source_url)
    artist_name_key = str(row.get("artist_name_key") or "").strip() or collect.build_artist_name_key(artist_name_en, source_url)
    return collect.metadata_record_lookup_key(artist_name_key, source_url)


def build_meta_maps(targets: list[dict[str, Any]]) -> tuple[dict[str, list[dict[str, Any]]], dict[str, dict[str, int]]]:
    fair_tokens = sorted({str(row.get("fair_slug") or "").strip() for row in targets if str(row.get("fair_slug") or "").strip()})
    rows_by_fair: dict[str, list[dict[str, Any]]] = {}
    index_by_fair: dict[str, dict[str, int]] = {}
    for fair in fair_tokens:
        path = collect.works_meta_path_for_fair(fair).resolve()
        rows = collect.read_jsonl_rows(path)
        rows_by_fair[fair] = rows
        index: dict[str, int] = {}
        for i, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            key = collect.metadata_record_lookup_key(
                str(row.get("artist_name_key") or ""),
                str(row.get("source_url") or ""),
            )
            if key not in index:
                index[key] = i
        index_by_fair[fair] = index
    return rows_by_fair, index_by_fair


def load_targets_like_dryrun() -> list[dict[str, Any]]:
    targets = collect.load_artist_targets(TARGET_YEAR, only_source_url="")

    skip_registry = collect.load_skipped_gallery_registry(collect.SKIPPED_GALLERIES_REGISTRY_PATH)
    if skip_registry:
        filtered: list[dict[str, Any]] = []
        for row in targets:
            gallery_name = str(row.get("gallery_name_en") or "").strip()
            if not gallery_name:
                filtered.append(row)
                continue
            if skip_registry.get(gallery_name.lower()) is None:
                filtered.append(row)
        targets = filtered

    artist_master_global = collect.load_artist_master_global(get_phase1_artist_master_global_path())
    collect.merge_artist_master_from_works_meta(artist_master_global)

    filtered_targets: list[dict[str, Any]] = []
    seen_identity_in_run: set[str] = set()
    for row in targets:
        source_url = str(row.get("source_url") or "").strip()
        if not source_url:
            continue
        fair_slug = str(row.get("fair_slug") or "").strip()
        gallery_name_en = str(row.get("gallery_name_en") or "").strip()
        artist_name_en = str(row.get("artist_name_en") or "").strip() or collect.build_artist_name_en_from_source_url(source_url)
        artist_name_key = str(row.get("artist_name_key") or "").strip() or collect.build_artist_name_key(artist_name_en, source_url)
        identity_key = collect.build_artist_identity_key(artist_name_key, artist_name_en, source_url)
        row["artist_name_en"] = artist_name_en
        row["artist_name_key"] = artist_name_key
        row["artist_identity_key"] = identity_key

        existing = artist_master_global.get(identity_key)
        existing_source = collect.normalize_url_for_link_compare(str(existing.get("first_source_url") or "")) if existing else ""
        current_source = collect.normalize_url_for_link_compare(source_url)
        if existing and existing_source and existing_source != current_source:
            continue
        if identity_key in seen_identity_in_run:
            continue
        seen_identity_in_run.add(identity_key)
        filtered_targets.append(row)
    return filtered_targets


def evaluate_target(target: dict[str, Any], rows_by_fair: dict[str, list[dict[str, Any]]], index_by_fair: dict[str, dict[str, int]]) -> dict[str, Any]:
    fair_slug = str(target.get("fair_slug") or "")
    gallery_name = str(target.get("gallery_name_en") or "")
    source_url = str(target.get("source_url") or "")
    lookup_key = metadata_lookup_key(target)
    fair_rows = rows_by_fair.get(fair_slug, [])
    fair_index = index_by_fair.get(fair_slug, {})
    idx = fair_index.get(lookup_key)
    meta_row = fair_rows[idx] if idx is not None and 0 <= idx < len(fair_rows) and isinstance(fair_rows[idx], dict) else None

    meta_hashes = normalize_hashes(meta_row.get("works_image_url_hashes") if isinstance(meta_row, dict) else [])
    meta_urls = meta_row.get("works_image_urls") if isinstance(meta_row, dict) else []
    meta_caps = meta_row.get("works_image_captions") if isinstance(meta_row, dict) else []
    meta_years = normalize_years(meta_row.get("works_image_years") if isinstance(meta_row, dict) else [])
    meta_r2 = meta_row.get("works_image_r2_keys") if isinstance(meta_row, dict) else []
    meta_local = meta_row.get("works_image_local_paths") if isinstance(meta_row, dict) else []
    meta_year_src = meta_row.get("works_image_year_sources") if isinstance(meta_row, dict) else []
    meta_year_conf = meta_row.get("works_image_year_confidences") if isinstance(meta_row, dict) else []
    meta_payload = meta_row.get("works_image_payload_hashes") if isinstance(meta_row, dict) else []

    meta_by_hash: dict[str, dict[str, Any]] = {}
    for i, h in enumerate(meta_hashes):
        meta_by_hash[h] = {
            "url": str(meta_urls[i]) if isinstance(meta_urls, list) and i < len(meta_urls) else "",
            "caption": str(meta_caps[i]) if isinstance(meta_caps, list) and i < len(meta_caps) else "",
            "year": int(meta_years[i]) if i < len(meta_years) else 0,
            "r2_key": str(meta_r2[i]) if isinstance(meta_r2, list) and i < len(meta_r2) else "",
            "local_path": str(meta_local[i]) if isinstance(meta_local, list) and i < len(meta_local) else "",
            "year_source": str(meta_year_src[i]) if isinstance(meta_year_src, list) and i < len(meta_year_src) else "none",
            "year_confidence": str(meta_year_conf[i]) if isinstance(meta_year_conf, list) and i < len(meta_year_conf) else "low",
            "payload_hash": str(meta_payload[i]) if isinstance(meta_payload, list) and i < len(meta_payload) else "",
        }

    valid_items = collect.build_valid_existing_metadata_items(
        meta_hashes,
        meta_by_hash,
        target_images_per_artist=TARGET_IMAGES_PER_ARTIST,
    )
    valid_hashes = {str(item.get("hash") or "") for item in valid_items}

    per_hash_eval: list[dict[str, Any]] = []
    for i, h in enumerate(meta_hashes):
        row = meta_by_hash.get(h, {})
        local_text = str(row.get("local_path") or "")
        local_path = resolve_image_local_path(local_text)
        reason = "OK"
        cached_detail = ""
        if not local_text:
            reason = "LOCAL_PATH_EMPTY"
        elif local_path is None:
            reason = "LOCAL_PATH_RESOLVE_FAILED"
        elif not local_path.exists():
            reason = "FILE_MISSING"
        else:
            ok_cached, cached_reason = collect.validate_cached_image_file(local_path)
            if not ok_cached:
                reason = "CACHED_INVALID"
                cached_detail = cached_reason
            else:
                local_payload = collect.payload_hash_from_file(local_path).strip().lower()
                if not local_payload:
                    reason = "LOCAL_PAYLOAD_HASH_EMPTY"
                else:
                    prev_payload = str(row.get("payload_hash") or "").strip().lower()
                    if prev_payload and prev_payload != local_payload:
                        reason = "PAYLOAD_HASH_MISMATCH"
                    elif h not in valid_hashes:
                        reason = "NOT_SELECTED_IN_VALID_WINDOW"
        per_hash_eval.append(
            {
                "fair_slug": fair_slug,
                "gallery_name": gallery_name,
                "source_url": source_url,
                "expected_local_path": str(local_path) if local_path is not None else local_text,
                "image_url_hash": h,
                "r2_key": str(row.get("r2_key") or ""),
                "reason": reason,
                "reason_detail": cached_detail,
                "meta_index": i,
                "is_valid": h in valid_hashes and reason == "OK",
            }
        )

    missing_for_target = max(0, len(meta_hashes) - len(valid_items))
    invalid_entries: list[dict[str, Any]] = []
    if missing_for_target > 0:
        not_selected = [row for row in per_hash_eval if not row["is_valid"]]
        if len(not_selected) < missing_for_target:
            extra = [row for row in per_hash_eval if row["is_valid"]][missing_for_target - len(not_selected) :]
            for row in extra:
                row = dict(row)
                row["reason"] = "NOT_SELECTED_IN_VALID_WINDOW"
                row["is_valid"] = False
                not_selected.append(row)
        invalid_entries = [dict(row) for row in not_selected[:missing_for_target]]

    would_fetch = len(valid_items) < TARGET_IMAGES_PER_ARTIST
    would_fetch_reason = ""
    if would_fetch:
        if meta_row is None:
            would_fetch_reason = "NO_METADATA_ROW"
        elif not meta_hashes:
            would_fetch_reason = "NO_METADATA_HASHES"
        elif invalid_entries:
            would_fetch_reason = "PARTIAL_AND_INVALID"
        else:
            would_fetch_reason = "PARTIAL_UNDER_TARGET"

    return {
        "fair_slug": fair_slug,
        "gallery_name": gallery_name,
        "source_url": source_url,
        "meta_present": meta_row is not None,
        "meta_hash_count": len(meta_hashes),
        "valid_count": len(valid_items),
        "would_fetch": would_fetch,
        "would_fetch_reason": would_fetch_reason,
        "invalid_entries": invalid_entries,
    }


def index_candidate_files(root: Path) -> dict[str, list[Path]]:
    index: dict[str, list[Path]] = defaultdict(list)
    if not root.exists():
        return index
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        index[path.name].append(path)
    return index


def pick_source(candidates: list[Path]) -> Path | None:
    live = [p for p in candidates if p.exists() and p.is_file()]
    if not live:
        return None
    live.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return live[0]


def attempt_r2_download(items: list[dict[str, Any]]) -> tuple[int, list[dict[str, Any]], str]:
    if not items:
        return 0, [], "not_needed"
    if r2_sync is None:
        return 0, [{"item": item, "error": "r2_sync_module_unavailable"} for item in items], "module_unavailable"
    try:
        client, bucket = r2_sync.build_r2_client()
    except Exception as exc:  # noqa: BLE001
        return 0, [{"item": item, "error": f"r2_client_init_failed:{exc}"} for item in items], "client_init_failed"

    downloaded = 0
    failures: list[dict[str, Any]] = []
    for item in items:
        key = str(item.get("r2_key") or "").strip()
        dest_text = str(item.get("expected_local_path") or "").strip()
        if not key or not dest_text:
            failures.append({"item": item, "error": "missing_r2_key_or_path"})
            continue
        dest = Path(dest_text)
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            client.download_file(bucket, key, str(dest))
            downloaded += 1
        except Exception as exc:  # noqa: BLE001
            failures.append({"item": item, "error": f"download_failed:{exc}"})
    return downloaded, failures, "attempted"


def run_final_dryrun() -> dict[str, Any]:
    cmd = [
        "python",
        "run_phase1_seed10_artist_image_collect.py",
        "--mode",
        "fill_missing",
        "--dry-run",
        "--dry-run-output",
        str(OUTPUT_DRYRUN_PATH),
    ]
    proc = subprocess.run(cmd, cwd=PROJECT_ROOT, text=True, capture_output=True)
    payload: dict[str, Any] = {
        "command": " ".join(cmd),
        "exit_code": proc.returncode,
        "stdout_tail": "\n".join(proc.stdout.splitlines()[-20:]),
        "stderr_tail": "\n".join(proc.stderr.splitlines()[-20:]),
    }
    if OUTPUT_DRYRUN_PATH.exists():
        payload["dryrun_output_path"] = str(OUTPUT_DRYRUN_PATH)
        payload["dryrun_output"] = read_json(OUTPUT_DRYRUN_PATH)
    return payload


def render_md(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Phase1.7 Missing-Only Recovery (Artist Works Images) - TASK_FORMALIZE_03")
    lines.append("")
    lines.append("## Summary (5 lines)")
    lines.append(f"- started_at: {report['started_at']}")
    lines.append(f"- candidate_targets: {report['candidate_target_count']}")
    lines.append(
        f"- recovered: trial={report['restored_from_trial_count']}, trash={report['restored_from_trash_count']}, r2={report['restored_from_r2_count']}"
    )
    lines.append(f"- still_missing_after_recovery: {report['still_missing_count']}")
    dry = report.get("post_dryrun", {}).get("dryrun_output", {})
    lines.append(
        f"- post_dryrun: would_fetch={dry.get('would_fetch_count')}, file_missing={dry.get('key_present_but_file_missing_count')}"
    )
    lines.append("")
    lines.append("## Recovery Counts")
    lines.append(
        f"- restored_from_trial_count: {report['restored_from_trial_count']}\n"
        f"- restored_from_trash_count: {report['restored_from_trash_count']}\n"
        f"- restored_from_r2_count: {report['restored_from_r2_count']}\n"
        f"- still_missing_count: {report['still_missing_count']}"
    )
    lines.append("")
    lines.append("## Would-Fetch Reason Counts")
    for reason, count in sorted((report.get("would_fetch_reason_counts") or {}).items(), key=lambda x: (-int(x[1]), x[0])):
        lines.append(f"- {reason}: {count}")
    lines.append("")
    lines.append("## Invalid Entry Reason Counts")
    for reason, count in sorted((report.get("invalid_entry_reason_counts") or {}).items(), key=lambda x: (-int(x[1]), x[0])):
        lines.append(f"- {reason}: {count}")
    lines.append("")
    lines.append("## Post Dry-run")
    lines.append(f"- command: `{report['post_dryrun'].get('command', '')}`")
    lines.append(f"- exit_code: {report['post_dryrun'].get('exit_code')}")
    if isinstance(dry, dict) and dry:
        lines.append(f"- candidate_total: {dry.get('candidate_total')}")
        lines.append(f"- would_skip_count: {dry.get('would_skip_count')}")
        lines.append(f"- would_fetch_count: {dry.get('would_fetch_count')}")
        lines.append(f"- key_present_but_file_missing_count: {dry.get('key_present_but_file_missing_count')}")
        lines.append(f"- would_write_count: {dry.get('would_write_count')}")
    unresolved = report.get("unresolved_top20", [])
    if unresolved:
        lines.append("")
        lines.append("## Unresolved Top20")
        for item in unresolved[:20]:
            lines.append(
                "- "
                f"{item.get('fair_slug')}/{item.get('gallery_name')} | "
                f"reason={item.get('reason')} | "
                f"source_url={item.get('source_url')} | "
                f"path={item.get('expected_local_path')}"
            )
    return "\n".join(lines) + "\n"


def main() -> int:
    started_at = utc_now_iso()
    if not INPUT_DRYRUN_PATH.exists():
        raise SystemExit(f"missing_input_dryrun:{INPUT_DRYRUN_PATH}")
    input_dryrun = read_json(INPUT_DRYRUN_PATH)
    targets = load_targets_like_dryrun()
    rows_by_fair, index_by_fair = build_meta_maps(targets)

    evaluations = [evaluate_target(t, rows_by_fair, index_by_fair) for t in targets]

    invalid_entries: list[dict[str, Any]] = []
    would_fetch_items: list[dict[str, Any]] = []
    would_fetch_reason_counts: Counter[str] = Counter()
    invalid_entry_reason_counts: Counter[str] = Counter()
    for ev in evaluations:
        invalid_entries.extend(ev["invalid_entries"])
        for item in ev["invalid_entries"]:
            invalid_entry_reason_counts[str(item.get("reason") or "UNKNOWN")] += 1
        if ev["would_fetch"]:
            would_fetch_reason_counts[ev["would_fetch_reason"]] += 1
            would_fetch_items.append(
                {
                    "fair_slug": ev["fair_slug"],
                    "gallery_name": ev["gallery_name"],
                    "source_url": ev["source_url"],
                    "reason": ev["would_fetch_reason"],
                    "meta_hash_count": ev["meta_hash_count"],
                    "valid_count": ev["valid_count"],
                }
            )

    recovery_items = [item for item in invalid_entries if str(item.get("reason")) in {"FILE_MISSING", "LOCAL_PATH_EMPTY", "LOCAL_PATH_RESOLVE_FAILED"}]

    trial_index = index_candidate_files(TRIAL_ROOT)
    trash_index = index_candidate_files(TRASH_ROOT)

    restored_from_trial = 0
    restored_from_trash = 0
    restored_items: list[dict[str, Any]] = []
    unresolved_items: list[dict[str, Any]] = []

    for item in recovery_items:
        expected = str(item.get("expected_local_path") or "").strip()
        if not expected:
            unresolved_items.append({**item, "recovery_status": "missing_expected_path"})
            continue
        dest = Path(expected)
        if dest.exists():
            restored_items.append({**item, "recovery_status": "already_present"})
            continue
        base = dest.name
        source = pick_source(trial_index.get(base, []))
        source_origin = "trial"
        if source is None:
            source = pick_source(trash_index.get(base, []))
            source_origin = "trash"
        if source is None:
            unresolved_items.append({**item, "recovery_status": "not_found_local"})
            continue
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(dest))
            if source_origin == "trial":
                restored_from_trial += 1
            else:
                restored_from_trash += 1
            restored_items.append({**item, "recovery_status": f"restored_from_{source_origin}", "source_path": str(source)})
        except Exception as exc:  # noqa: BLE001
            unresolved_items.append({**item, "recovery_status": f"move_failed:{exc}", "source_path": str(source)})

    r2_candidates = [
        item
        for item in unresolved_items
        if str(item.get("recovery_status", "")).startswith("not_found_local")
        and str(item.get("r2_key") or "").strip()
        and str(item.get("expected_local_path") or "").strip()
    ]
    restored_from_r2, r2_failures, r2_status = attempt_r2_download(r2_candidates)
    if r2_failures:
        for fail in r2_failures:
            row = dict(fail.get("item") or {})
            row["recovery_status"] = str(fail.get("error") or "r2_failed")
            unresolved_items.append(row)

    # Remove duplicates after r2 attempts and re-check existence.
    dedup: dict[str, dict[str, Any]] = {}
    for item in unresolved_items:
        key = "|".join(
            [
                str(item.get("fair_slug") or ""),
                str(item.get("gallery_name") or ""),
                str(item.get("source_url") or ""),
                str(item.get("image_url_hash") or ""),
                str(item.get("expected_local_path") or ""),
            ]
        )
        dedup[key] = item
    unresolved_items = []
    for item in dedup.values():
        path_text = str(item.get("expected_local_path") or "").strip()
        if path_text and Path(path_text).exists():
            continue
        unresolved_items.append(item)

    post_dryrun = run_final_dryrun()
    post_payload = post_dryrun.get("dryrun_output", {}) if isinstance(post_dryrun, dict) else {}
    unresolved_top20 = unresolved_items[:20]

    report = {
        "task": "TASK_FORMALIZE_03",
        "started_at": started_at,
        "generated_at": utc_now_iso(),
        "input_dryrun_path": str(INPUT_DRYRUN_PATH),
        "input_dryrun": input_dryrun,
        "candidate_target_count": len(targets),
        "recovery_item_count": len(recovery_items),
        "would_fetch_item_count_before_recovery": len(would_fetch_items),
        "would_fetch_reason_counts": dict(would_fetch_reason_counts),
        "invalid_entry_reason_counts": dict(invalid_entry_reason_counts),
        "restored_from_trial_count": restored_from_trial,
        "restored_from_trash_count": restored_from_trash,
        "restored_from_r2_count": restored_from_r2,
        "r2_status": r2_status,
        "still_missing_count": len(unresolved_items),
        "restored_items": restored_items,
        "invalid_entries_top20": invalid_entries[:20],
        "unresolved_items": unresolved_items,
        "unresolved_top20": unresolved_top20,
        "would_fetch_items_top20": would_fetch_items[:20],
        "post_dryrun": post_dryrun,
    }

    write_json(OUTPUT_JSON_PATH, report)
    OUTPUT_MD_PATH.write_text(render_md(report), encoding="utf-8")
    print(f"[DONE] json={OUTPUT_JSON_PATH}")
    print(f"[DONE] md={OUTPUT_MD_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
