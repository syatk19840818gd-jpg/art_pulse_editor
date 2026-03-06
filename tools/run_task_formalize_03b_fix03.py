#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import run_phase1_seed10_artist_image_collect as collect
from tools import skip_policy
from tools.formal_postflight_gate import run_postflight_gate
from tools.formal_preflight_gate import run_preflight_gate
from tools.run_task_formalize_03_missing_recovery import load_targets_like_dryrun

try:
    import run_phase1_seed10_r2_sync as r2_sync
except Exception:
    r2_sync = None

LOG = ROOT / "data" / "phase1_seed10" / "logs"
TRIAL_BASE = ROOT / "data" / "phase1_seed10" / "_trial"
TRASH_BASE = ROOT / "data" / "phase1_seed10" / "_trash"
FORMAL_RAW = ROOT / "data" / "phase1_seed10" / "raw"
FORMAL_DERIVED = ROOT / "data" / "phase1_seed10" / "derived"
FORMAL_IMG_ROOT = FORMAL_DERIVED / "images" / "artist_works_images"

FORMAL_META = {
    "frieze_london": FORMAL_DERIVED / "artist_works_images_frieze_london.jsonl",
    "liste": FORMAL_DERIVED / "artist_works_images_liste.jsonl",
}
FORMAL_RAW_ARTISTS = {
    "frieze_london": FORMAL_RAW / "artists_frieze_london_2025.jsonl",
    "liste": FORMAL_RAW / "artists_liste_2025.jsonl",
}

INPUT_DRYRUN = LOG / "dryrun_run_phase1_seed10_artist_image_collect_task_formalize_03b_fix02.json"
OUTPUT_DRYRUN = LOG / "dryrun_run_phase1_seed10_artist_image_collect_task_formalize_03b_fix03.json"
OUT_MD = LOG / "phase1_7_artist_images_true_missing_recovery_fix03.md"
OUT_JSON = LOG / "phase1_7_artist_images_true_missing_recovery_fix03.json"

TARGET_REASONS = {
    skip_policy.ARTIST_IMAGE_REASON_NO_METADATA_ROW,
    skip_policy.ARTIST_IMAGE_REASON_NO_METADATA_HASHES,
    skip_policy.ARTIST_IMAGE_REASON_PAYLOAD_HASH_MISMATCH,
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def rows_by_fair(meta_map: dict[str, Path]) -> tuple[dict[str, list[dict[str, Any]]], dict[str, dict[str, int]]]:
    by_fair: dict[str, list[dict[str, Any]]] = {}
    idx: dict[str, dict[str, int]] = {}
    for fair, p in meta_map.items():
        rows = read_jsonl(p)
        by_fair[fair] = rows
        sub: dict[str, int] = {}
        for i, row in enumerate(rows):
            k = collect.metadata_record_lookup_key(
                str(row.get("artist_name_key") or ""),
                str(row.get("source_url") or ""),
            )
            sub.setdefault(k, i)
        idx[fair] = sub
    return by_fair, idx


def target_lookup_key(target: dict[str, Any]) -> str:
    source_url = str(target.get("source_url") or "")
    artist_name_en = str(target.get("artist_name_en") or "").strip() or collect.build_artist_name_en_from_source_url(source_url)
    artist_name_key = str(target.get("artist_name_key") or "").strip()
    if not artist_name_key:
        artist_name_key = collect.build_artist_name_key(artist_name_en, source_url)
    return collect.metadata_record_lookup_key(artist_name_key, source_url)


def evaluate_target_reason(
    target: dict[str, Any],
    rows: dict[str, list[dict[str, Any]]],
    idx: dict[str, dict[str, int]],
    *,
    target_images: int = 5,
) -> dict[str, Any]:
    fair = str(target.get("fair_slug") or "")
    lookup = target_lookup_key(target)
    fair_rows = rows.get(fair, [])
    fair_idx = idx.get(fair, {})
    i = fair_idx.get(lookup)
    meta_row = (
        fair_rows[i]
        if i is not None and 0 <= i < len(fair_rows) and isinstance(fair_rows[i], dict)
        else None
    )
    hashes = collect.normalize_hash_list(meta_row.get("works_image_url_hashes") if isinstance(meta_row, dict) else [])
    urls = meta_row.get("works_image_urls") if isinstance(meta_row, dict) else []
    caps = meta_row.get("works_image_captions") if isinstance(meta_row, dict) else []
    years = collect.normalize_year_list(meta_row.get("works_image_years") if isinstance(meta_row, dict) else [])
    r2 = meta_row.get("works_image_r2_keys") if isinstance(meta_row, dict) else []
    local_paths = meta_row.get("works_image_local_paths") if isinstance(meta_row, dict) else []
    year_sources = meta_row.get("works_image_year_sources") if isinstance(meta_row, dict) else []
    year_confs = meta_row.get("works_image_year_confidences") if isinstance(meta_row, dict) else []
    payloads = meta_row.get("works_image_payload_hashes") if isinstance(meta_row, dict) else []

    by_hash: dict[str, dict[str, Any]] = {}
    mismatch_indices: list[int] = []
    for j, h in enumerate(hashes):
        row = {
            "url": str(urls[j]) if isinstance(urls, list) and j < len(urls) else "",
            "caption": str(caps[j]) if isinstance(caps, list) and j < len(caps) else "",
            "year": int(years[j]) if j < len(years) else 0,
            "r2_key": str(r2[j]) if isinstance(r2, list) and j < len(r2) else "",
            "local_path": str(local_paths[j]) if isinstance(local_paths, list) and j < len(local_paths) else "",
            "year_source": str(year_sources[j]) if isinstance(year_sources, list) and j < len(year_sources) else "none",
            "year_confidence": str(year_confs[j]) if isinstance(year_confs, list) and j < len(year_confs) else "low",
            "payload_hash": str(payloads[j]) if isinstance(payloads, list) and j < len(payloads) else "",
        }
        by_hash[h] = row
        p = collect.resolve_local_cache_path(row["local_path"])
        if p and p.exists() and p.is_file():
            local_hash = collect.payload_hash_from_file(p).strip().lower()
            prev_hash = str(row["payload_hash"] or "").strip().lower()
            if prev_hash and local_hash and prev_hash != local_hash:
                mismatch_indices.append(j)

    valid = collect.build_valid_existing_metadata_items(
        hashes,
        by_hash,
        target_images_per_artist=target_images,
    )
    integrity = collect.analyze_existing_metadata_integrity(hashes, by_hash)
    reason = collect.classify_artist_fill_missing_reason(
        has_metadata_row=isinstance(meta_row, dict),
        existing_meta_hashes=hashes,
        valid_existing_count=len(valid),
        target_images_per_artist=target_images,
        integrity_stats=integrity,
    )
    should_fetch, effective_reason = skip_policy.should_fetch_artist_image_in_mode(
        mode=skip_policy.FILL_MISSING_MODE,
        reason=reason,
        fill_missing_topup=skip_policy.FILL_MISSING_TOPUP_DEFAULT,
    )
    return {
        "would_fetch": bool(should_fetch),
        "reason": str(reason),
        "effective_reason": str(effective_reason),
        "lookup_key": lookup,
        "meta_present": isinstance(meta_row, dict),
        "meta_hash_count": len(hashes),
        "valid_count": len(valid),
        "hashes": hashes,
        "mismatch_indices": mismatch_indices,
    }

def build_scoped_raw_files(scope: list[dict[str, Any]], out_raw: Path) -> dict[str, int]:
    by_fair: dict[str, dict[str, dict[str, Any]]] = {"frieze_london": {}, "liste": {}}
    for item in scope:
        t = item["target"]
        fair = str(t.get("fair_slug") or "")
        src = str(t.get("source_url") or "")
        if fair in by_fair and src and src not in by_fair[fair]:
            by_fair[fair][src] = t
    counts: dict[str, int] = {}
    for fair, in_path in FORMAL_RAW_ARTISTS.items():
        src_rows = read_jsonl(in_path)
        src_map: dict[str, dict[str, Any]] = {}
        for row in src_rows:
            src = str(row.get("source_url") or "").strip()
            if src and src not in src_map:
                src_map[src] = row
        out_rows: list[dict[str, Any]] = []
        for src, t in by_fair[fair].items():
            row = src_map.get(src)
            if row is None:
                row = {
                    "fair_slug": fair,
                    "gallery_name_en": str(t.get("gallery_name_en") or ""),
                    "source_url": src,
                    "artist_name_en": str(t.get("artist_name_en") or ""),
                    "artist_name_key": str(t.get("artist_name_key") or ""),
                    "artist_id": str(t.get("artist_id") or ""),
                    "text": "",
                }
            out_rows.append(row)
        out_path = out_raw / in_path.name
        write_jsonl(out_path, out_rows)
        counts[fair] = len(out_rows)
    return counts


def run_cmd(cmd: list[str], cwd: Path, *, timeout_sec: int | None = None) -> dict[str, Any]:
    try:
        proc = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, timeout=timeout_sec)
        return {
            "command": " ".join(cmd),
            "exit_code": proc.returncode,
            "timed_out": False,
            "stdout_tail": "\n".join(proc.stdout.splitlines()[-20:]),
            "stderr_tail": "\n".join(proc.stderr.splitlines()[-20:]),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": " ".join(cmd),
            "exit_code": -999,
            "timed_out": True,
            "stdout_tail": "\n".join(str(exc.stdout or "").splitlines()[-20:]),
            "stderr_tail": "\n".join(str(exc.stderr or "").splitlines()[-20:]),
        }


def build_candidate_meta_index() -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    search_roots = [TRIAL_BASE, TRASH_BASE]
    for root in search_roots:
        if not root.exists():
            continue
        for p in root.rglob("artist_works_images_*.jsonl"):
            fair = "frieze_london" if "frieze_london" in p.name else "liste" if "liste" in p.name else ""
            if not fair:
                continue
            rows = read_jsonl(p)
            for row in rows:
                if not isinstance(row, dict):
                    continue
                hashes = collect.normalize_hash_list(row.get("works_image_url_hashes") or [])
                if not hashes:
                    continue
                key = collect.metadata_record_lookup_key(
                    str(row.get("artist_name_key") or ""),
                    str(row.get("source_url") or ""),
                )
                entry = {
                    "fair": fair,
                    "row": row,
                    "meta_path": str(p),
                    "origin": "trial" if "_trial" in str(p) else "trash",
                    "hash_count": len(hashes),
                }
                index[key].append(entry)
    return index


def prefer_candidate(entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not entries:
        return None
    ranked = sorted(entries, key=lambda e: (int(e.get("hash_count") or 0), 1 if e.get("origin") == "trial" else 0), reverse=True)
    return ranked[0]


def move_file_if_local_source(src: Path, dst: Path) -> str:
    src_abs = src.resolve()
    dst_abs = dst.resolve()
    if dst_abs.exists():
        return "already_exists"
    dst_abs.parent.mkdir(parents=True, exist_ok=True)
    src_text = str(src_abs).lower()
    if "\\_trial\\" in src_text or "\\_trash\\" in src_text:
        shutil.move(str(src_abs), str(dst_abs))
        return "moved"
    return "linked_existing"


def patch_trial_row_from_candidate(
    *,
    target: dict[str, Any],
    candidate_row: dict[str, Any],
    fair: str,
    trial_img_year_root: Path,
) -> tuple[dict[str, Any], Counter[str]]:
    move_counts = Counter()
    hashes = collect.normalize_hash_list(candidate_row.get("works_image_url_hashes") or [])
    urls = candidate_row.get("works_image_urls") if isinstance(candidate_row.get("works_image_urls"), list) else []
    caps = candidate_row.get("works_image_captions") if isinstance(candidate_row.get("works_image_captions"), list) else []
    years = collect.normalize_year_list(candidate_row.get("works_image_years") or [])
    r2 = candidate_row.get("works_image_r2_keys") if isinstance(candidate_row.get("works_image_r2_keys"), list) else []
    lp = candidate_row.get("works_image_local_paths") if isinstance(candidate_row.get("works_image_local_paths"), list) else []
    ys = candidate_row.get("works_image_year_sources") if isinstance(candidate_row.get("works_image_year_sources"), list) else []
    yc = candidate_row.get("works_image_year_confidences") if isinstance(candidate_row.get("works_image_year_confidences"), list) else []
    ph = candidate_row.get("works_image_payload_hashes") if isinstance(candidate_row.get("works_image_payload_hashes"), list) else []
    out_urls: list[str] = []
    out_caps: list[str] = []
    out_years: list[int] = []
    out_r2: list[str] = []
    out_lp: list[str] = []
    out_ys: list[str] = []
    out_yc: list[str] = []
    out_ph: list[str] = []
    for i, h in enumerate(hashes):
        raw_local = str(lp[i]) if i < len(lp) else ""
        local_path = collect.resolve_local_cache_path(raw_local) if raw_local else None
        if local_path and local_path.exists() and local_path.is_file():
            fair_safe = collect.slugify_token(fair, fallback="unknown-fair")
            name = local_path.name
            dst = (trial_img_year_root / fair_safe / name).resolve()
            status = move_file_if_local_source(local_path, dst)
            if status == "moved":
                src_text = str(local_path).lower()
                if "\\_trial\\" in src_text:
                    move_counts["restored_from_trial"] += 1
                elif "\\_trash\\" in src_text:
                    move_counts["restored_from_trash"] += 1
                out_lp.append(str(dst))
                out_r2.append(f"phase1_seed10/derived/images/artist_works_images/2025/{fair_safe}/{name}")
            else:
                out_lp.append(str(local_path.resolve()))
                out_r2.append(str(r2[i]) if i < len(r2) else "")
        else:
            out_lp.append(raw_local)
            out_r2.append(str(r2[i]) if i < len(r2) else "")
        out_urls.append(str(urls[i]) if i < len(urls) else "")
        out_caps.append(str(caps[i]) if i < len(caps) else "")
        out_years.append(int(years[i]) if i < len(years) else 0)
        out_ys.append(str(ys[i]) if i < len(ys) else "none")
        out_yc.append(str(yc[i]) if i < len(yc) else "low")
        out_ph.append(str(ph[i]) if i < len(ph) else "")
    patched = {
        "artist_id": str(target.get("artist_id") or ""),
        "artist_storage_key": str(candidate_row.get("artist_storage_key") or ""),
        "artist_name_key": str(target.get("artist_name_key") or ""),
        "artist_identity_key": str(target.get("artist_identity_key") or ""),
        "artist_name_en": str(target.get("artist_name_en") or ""),
        "fair_slug": fair,
        "gallery_name_en": str(target.get("gallery_name_en") or ""),
        "source_url": str(target.get("source_url") or ""),
        "works_image_url_hashes": hashes,
        "works_image_urls": out_urls,
        "works_image_captions": out_caps,
        "works_image_years": out_years,
        "works_image_r2_keys": out_r2,
        "works_image_local_paths": out_lp,
        "works_image_year_sources": out_ys,
        "works_image_year_confidences": out_yc,
        "works_image_payload_hashes": out_ph,
    }
    return patched, move_counts


def rewrite_trial_meta_paths_to_formal(meta_path: Path, trial_img_root: Path, formal_img_root: Path) -> None:
    rows = read_jsonl(meta_path)
    changed = False
    for row in rows:
        local_paths = row.get("works_image_local_paths")
        if not isinstance(local_paths, list):
            continue
        r2_keys = row.get("works_image_r2_keys")
        if not isinstance(r2_keys, list):
            r2_keys = []
        for i, val in enumerate(local_paths):
            p = Path(str(val or ""))
            if not p.is_absolute():
                continue
            try:
                rel = p.resolve().relative_to(trial_img_root.resolve())
            except Exception:
                continue
            newp = (formal_img_root / rel).resolve()
            local_paths[i] = str(newp)
            while len(r2_keys) <= i:
                r2_keys.append("")
            r2_keys[i] = f"phase1_seed10/derived/images/{rel.as_posix()}"
            changed = True
        row["works_image_local_paths"] = local_paths
        row["works_image_r2_keys"] = r2_keys
    if changed:
        write_jsonl(meta_path, rows)

def main() -> int:
    if not INPUT_DRYRUN.exists():
        raise SystemExit(f"missing_input:{INPUT_DRYRUN}")
    dry = read_json(INPUT_DRYRUN)
    expected_total = int(dry.get("would_fetch_count") or 0)
    run_id = f"TASK_FORMALIZE_03B_FIX03_{now_compact()}"
    trial_root = (TRIAL_BASE / run_id).resolve()
    trial_raw = trial_root / "raw"
    trial_derived = trial_root / "derived"
    trial_logs = trial_root / "logs"
    trial_img = trial_derived / "images" / "artist_works_images"
    trial_img_year = trial_img / "2025"
    trial_meta = {
        "frieze_london": trial_derived / "artist_works_images_frieze_london.jsonl",
        "liste": trial_derived / "artist_works_images_liste.jsonl",
    }
    trial_raw.mkdir(parents=True, exist_ok=True)
    trial_derived.mkdir(parents=True, exist_ok=True)
    trial_logs.mkdir(parents=True, exist_ok=True)
    trial_img_year.mkdir(parents=True, exist_ok=True)

    for fair, src in FORMAL_META.items():
        shutil.copy2(src, trial_meta[fair])

    formal_rows, formal_idx = rows_by_fair(FORMAL_META)
    targets = load_targets_like_dryrun()
    scope: list[dict[str, Any]] = []
    reason_counts = Counter()
    for t in targets:
        ev = evaluate_target_reason(t, formal_rows, formal_idx)
        if ev["would_fetch"] and ev["reason"] in TARGET_REASONS:
            scope.append(
                {
                    "target": t,
                    "reason": ev["reason"],
                    "effective_reason": ev["effective_reason"],
                    "lookup_key": ev["lookup_key"],
                    "meta_present": ev["meta_present"],
                    "meta_hash_count": ev["meta_hash_count"],
                    "valid_count": ev["valid_count"],
                    "mismatch_indices": ev["mismatch_indices"],
                }
            )
            reason_counts[ev["reason"]] += 1

    targets_json = trial_root / "targets_true_missing_31.json"
    write_json(
        targets_json,
        {
            "run_id": run_id,
            "generated_at": now_iso(),
            "expected_total_from_dryrun": expected_total,
            "scope_total": len(scope),
            "reason_counts": dict(reason_counts),
            "items": [
                {
                    "fair_slug": str(s["target"].get("fair_slug") or ""),
                    "gallery_name": str(s["target"].get("gallery_name_en") or ""),
                    "artist_source_url": str(s["target"].get("source_url") or ""),
                    "reason": str(s["reason"]),
                    "lookup_key": str(s["lookup_key"]),
                    "meta_hash_count": int(s["meta_hash_count"]),
                    "valid_count": int(s["valid_count"]),
                }
                for s in scope
            ],
        },
    )
    scoped_raw_counts = build_scoped_raw_files(scope, trial_raw)

    trial_rows, trial_idx = rows_by_fair(trial_meta)
    local_resolved = 0
    local_move_counts = Counter()
    local_fixed_counts = Counter()
    candidate_index = build_candidate_meta_index()

    for s in scope:
        t = s["target"]
        fair = str(t.get("fair_slug") or "")
        key = str(s["lookup_key"])
        rows = trial_rows.get(fair, [])
        idx = trial_idx.get(fair, {})
        row_i = idx.get(key)
        row = rows[row_i] if row_i is not None and 0 <= row_i < len(rows) and isinstance(rows[row_i], dict) else None
        reason = str(s["reason"])

        if reason == skip_policy.ARTIST_IMAGE_REASON_PAYLOAD_HASH_MISMATCH and isinstance(row, dict):
            payloads = row.get("works_image_payload_hashes") if isinstance(row.get("works_image_payload_hashes"), list) else []
            local_paths = row.get("works_image_local_paths") if isinstance(row.get("works_image_local_paths"), list) else []
            while len(payloads) < len(local_paths):
                payloads.append("")
            changed = 0
            for idx_i in s.get("mismatch_indices", []):
                if not isinstance(idx_i, int):
                    continue
                if idx_i >= len(local_paths):
                    continue
                p = collect.resolve_local_cache_path(str(local_paths[idx_i] or ""))
                if p and p.exists() and p.is_file():
                    payloads[idx_i] = hashlib.sha256(p.read_bytes()).hexdigest()
                    changed += 1
            if changed > 0:
                row["works_image_payload_hashes"] = payloads
                local_fixed_counts["PAYLOAD_HASH_MISMATCH"] += changed
            continue

        if reason in {
            skip_policy.ARTIST_IMAGE_REASON_NO_METADATA_ROW,
            skip_policy.ARTIST_IMAGE_REASON_NO_METADATA_HASHES,
        }:
            cand = prefer_candidate(candidate_index.get(key, []))
            if cand is None:
                continue
            patched, moved = patch_trial_row_from_candidate(
                target=t,
                candidate_row=dict(cand["row"]),
                fair=fair,
                trial_img_year_root=trial_img_year,
            )
            local_move_counts.update(moved)
            if row_i is None:
                rows.append(patched)
                trial_idx[fair][key] = len(rows) - 1
            else:
                rows[row_i] = patched
            local_fixed_counts[reason] += 1

    for fair, p in trial_meta.items():
        write_jsonl(p, trial_rows.get(fair, []))

    trial_rows_after_local, trial_idx_after_local = rows_by_fair(trial_meta)
    unresolved_after_local: list[dict[str, Any]] = []
    for s in scope:
        ev = evaluate_target_reason(s["target"], trial_rows_after_local, trial_idx_after_local)
        if ev["would_fetch"] and ev["reason"] in TARGET_REASONS:
            unresolved_after_local.append({**s, "reason_after_local": ev["reason"]})
        else:
            local_resolved += 1

    r2_downloaded = 0
    r2_attempted = 0
    r2_failures: list[dict[str, Any]] = []
    if unresolved_after_local and r2_sync is not None:
        try:
            client, bucket = r2_sync.build_r2_client()
            for s in unresolved_after_local:
                t = s["target"]
                fair = str(t.get("fair_slug") or "")
                key = str(s["lookup_key"])
                rows = trial_rows_after_local.get(fair, [])
                idx = trial_idx_after_local.get(fair, {})
                row_i = idx.get(key)
                row = rows[row_i] if row_i is not None and 0 <= row_i < len(rows) and isinstance(rows[row_i], dict) else None
                if not isinstance(row, dict):
                    continue
                local_paths = row.get("works_image_local_paths") if isinstance(row.get("works_image_local_paths"), list) else []
                r2_keys = row.get("works_image_r2_keys") if isinstance(row.get("works_image_r2_keys"), list) else []
                for i, lp in enumerate(local_paths):
                    p = collect.resolve_local_cache_path(str(lp or ""))
                    if p and p.exists() and p.is_file():
                        continue
                    key_text = str(r2_keys[i]) if i < len(r2_keys) else ""
                    if not key_text.strip() or not p:
                        continue
                    r2_attempted += 1
                    try:
                        p.parent.mkdir(parents=True, exist_ok=True)
                        client.download_file(bucket, key_text, str(p))
                        r2_downloaded += 1
                    except Exception as exc:
                        r2_failures.append(
                            {
                                "fair_slug": fair,
                                "gallery_name": str(t.get("gallery_name_en") or ""),
                                "source_url": str(t.get("source_url") or ""),
                                "r2_key": key_text,
                                "error": f"{exc}",
                            }
                        )
        except Exception as exc:
            r2_failures.append({"stage": "r2_client_init", "error": f"{exc}"})

    trial_rows_after_r2, trial_idx_after_r2 = rows_by_fair(trial_meta)
    unresolved_after_r2: list[dict[str, Any]] = []
    r2_resolved = 0
    for s in unresolved_after_local:
        ev = evaluate_target_reason(s["target"], trial_rows_after_r2, trial_idx_after_r2)
        if ev["would_fetch"] and ev["reason"] in TARGET_REASONS:
            unresolved_after_r2.append({**s, "reason_after_r2": ev["reason"]})
        else:
            r2_resolved += 1

    web_executed = False
    web_result: dict[str, Any] = {"status": "not_needed"}
    web_resolved = 0
    if unresolved_after_r2:
        web_executed = True
        build_scoped_raw_files(unresolved_after_r2, trial_raw)
        web_summary_path = trial_logs / "artist_image_collect_web_reextract_summary_task_formalize_03b_fix03.json"
        web_result = run_cmd(
            [
                "python",
                "run_phase1_seed10_artist_image_collect.py",
                "--mode",
                "rebuild",
                "--allow-rebuild",
                "--run-id",
                run_id,
                "--trial-root",
                "data/phase1_seed10/_trial",
                "--output-json",
                str(web_summary_path),
            ],
            ROOT,
            timeout_sec=5400,
        )

    trial_rows_after_web, trial_idx_after_web = rows_by_fair(trial_meta)
    unresolved_after_web: list[dict[str, Any]] = []
    for s in unresolved_after_r2:
        ev = evaluate_target_reason(s["target"], trial_rows_after_web, trial_idx_after_web)
        if ev["would_fetch"] and ev["reason"] in TARGET_REASONS:
            unresolved_after_web.append(
                {
                    "fair_slug": str(s["target"].get("fair_slug") or ""),
                    "gallery_name": str(s["target"].get("gallery_name_en") or ""),
                    "source_url": str(s["target"].get("source_url") or ""),
                    "reason_after_web": ev["reason"],
                }
            )
        else:
            web_resolved += 1

    trial_dryrun_path = trial_logs / "artist_image_collect_dryrun_before_adopt_task_formalize_03b_fix03.json"
    run_cmd(
        [
            "python",
            "run_phase1_seed10_artist_image_collect.py",
            "--mode",
            "rebuild",
            "--allow-rebuild",
            "--run-id",
            run_id,
            "--trial-root",
            "data/phase1_seed10/_trial",
            "--dry-run",
            "--dry-run-output",
            str(trial_dryrun_path),
        ],
        ROOT,
    )
    trial_dryrun = read_json(trial_dryrun_path) if trial_dryrun_path.exists() else {}

    adopt_executed = False
    rollback_path = ""
    adopted_files: list[dict[str, Any]] = []
    pre_gate = {"status": "SKIP", "hold_reasons": ["trial_not_ready"]}
    post_gate = {"status": "SKIP", "hold_reasons": ["trial_not_ready"]}
    if (
        not unresolved_after_web
        and int(trial_dryrun.get("would_fetch_count", 1)) == 0
        and int(trial_dryrun.get("key_present_but_file_missing_count", 1)) == 0
    ):
        pre_gate = run_preflight_gate(
            context="task_formalize_03b_fix03_pre_adopt",
            report_path=LOG / "formal_gate_preflight_report_task_formalize_03b_fix03.md",
        )
        if pre_gate.get("status") == "PASS":
            rollback = TRASH_BASE / f"ADOPT_FIX03_{now_compact()}"
            backup = rollback / "formal_backup" / "derived"
            backup.mkdir(parents=True, exist_ok=True)
            rewrite_trial_meta_paths_to_formal(trial_meta["frieze_london"], trial_img, FORMAL_IMG_ROOT)
            rewrite_trial_meta_paths_to_formal(trial_meta["liste"], trial_img, FORMAL_IMG_ROOT)
            if trial_img_year.exists():
                for src in sorted([p for p in trial_img_year.rglob("*") if p.is_file()]):
                    rel = src.relative_to(trial_img_year)
                    dst = FORMAL_IMG_ROOT / "2025" / rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    if not dst.exists():
                        shutil.move(str(src), str(dst))
            for fair, formal_path in FORMAL_META.items():
                bak = backup / formal_path.name
                if formal_path.exists():
                    shutil.move(str(formal_path), str(bak))
                shutil.move(str(trial_meta[fair]), str(formal_path))
                adopted_files.append(
                    {
                        "formal_path": str(formal_path),
                        "backup_path": str(bak),
                        "sha256": hashlib.sha256(formal_path.read_bytes()).hexdigest(),
                    }
                )
            adopt_executed = True
            rollback_path = str(rollback)
            post_gate = run_postflight_gate(
                context="task_formalize_03b_fix03_post_adopt",
                report_path=LOG / "formal_gate_postflight_report_task_formalize_03b_fix03.md",
            )

    run_cmd(
        [
            "python",
            "run_phase1_seed10_artist_image_collect.py",
            "--mode",
            "fill_missing",
            "--dry-run",
            "--dry-run-output",
            str(OUTPUT_DRYRUN),
        ],
        ROOT,
    )
    final_dryrun = read_json(OUTPUT_DRYRUN) if OUTPUT_DRYRUN.exists() else {}

    status = "HOLD"
    if (
        adopt_executed
        and pre_gate.get("status") == "PASS"
        and post_gate.get("status") == "PASS"
        and int(final_dryrun.get("would_fetch_count", 1)) == 0
        and int(final_dryrun.get("key_present_but_file_missing_count", 1)) == 0
    ):
        status = "SUCCESS"

    payload = {
        "task": "TASK_FORMALIZE_03B_FIX_03",
        "run_id": run_id,
        "generated_at": now_iso(),
        "scope_total": len(scope),
        "scope_reason_counts": dict(reason_counts),
        "expected_total_from_dryrun": expected_total,
        "scoped_raw_counts": scoped_raw_counts,
        "targets_file": str(targets_json),
        "local_fixed_counts": dict(local_fixed_counts),
        "local_move_counts": dict(local_move_counts),
        "local_resolved_count": local_resolved,
        "r2_attempted_count": r2_attempted,
        "r2_downloaded_count": r2_downloaded,
        "r2_failures_top20": r2_failures[:20],
        "r2_resolved_count": r2_resolved,
        "web_executed": web_executed,
        "web_command_result": web_result,
        "web_resolved_count": web_resolved,
        "unresolved_after_web_count": len(unresolved_after_web),
        "unresolved_after_web_top20": unresolved_after_web[:20],
        "trial_dryrun_before_adopt": trial_dryrun,
        "adopt_executed": adopt_executed,
        "adopted_files": adopted_files,
        "rollback_path": rollback_path,
        "preflight": pre_gate,
        "postflight": post_gate,
        "final_dryrun": final_dryrun,
        "result": status,
    }
    write_json(OUT_JSON, payload)

    lines: list[str] = []
    lines.append("# phase1_7_artist_images_true_missing_recovery_fix03")
    lines.append("")
    lines.append("## 5-line summary")
    lines.append(f"- run_id: {run_id}")
    lines.append(f"- scope_total(true_missing): {len(scope)} (expected={expected_total})")
    lines.append(
        f"- recovered_counts(target-level): local={local_resolved}, r2={r2_resolved}, web={web_resolved}"
    )
    lines.append(f"- unresolved_after_web: {len(unresolved_after_web)}")
    lines.append(
        f"- final_dryrun: would_fetch={final_dryrun.get('would_fetch_count')}, file_missing={final_dryrun.get('key_present_but_file_missing_count')}, adopt_executed={adopt_executed}"
    )
    lines.append("")
    lines.append("## details")
    lines.append(f"- local_file_move_counts: {dict(local_move_counts)}")
    lines.append(f"- r2_attempted={r2_attempted}, r2_downloaded={r2_downloaded}")
    lines.append(f"- web_executed={web_executed}")
    lines.append(f"- rollback_path={rollback_path}")
    if unresolved_after_web:
        lines.append("- unresolved_top20:")
        for row in unresolved_after_web[:20]:
            lines.append(
                f"  - {row.get('fair_slug')}/{row.get('gallery_name')} | "
                f"reason={row.get('reason_after_web')} | "
                f"source_url={row.get('source_url')}"
            )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[DONE] {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
