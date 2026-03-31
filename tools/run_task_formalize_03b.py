#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import run_phase1_seed10_artist_image_collect as collect
from phase2_art_pulse_config import (
    get_current_raw_paths,
    get_current_artist_image_meta_paths,
    get_artist_image_cache_dir,
    get_image_r2_key,
    get_phase1_legacy_logs_dir,
    get_phase1_legacy_trial_root,
    get_phase1_legacy_trash_root,
)
from tools.formal_postflight_gate import run_postflight_gate
from tools.formal_preflight_gate import run_preflight_gate
from tools.run_task_formalize_03_missing_recovery import evaluate_target, load_targets_like_dryrun

LOG = (ROOT / get_phase1_legacy_logs_dir()).resolve()
TRIAL_BASE = (ROOT / get_phase1_legacy_trial_root()).resolve()
TRASH_BASE = (ROOT / get_phase1_legacy_trash_root()).resolve()
TRIAL_BASE_REL = get_phase1_legacy_trial_root().as_posix()
FORMAL_IMG = ROOT / get_artist_image_cache_dir()
FORMAL_META = {
    fair_slug: ROOT / path
    for fair_slug, path in get_current_artist_image_meta_paths().items()
}
FORMAL_RAW_ARTISTS = {
    fair_slug: ROOT / path
    for fair_slug, path in get_current_raw_paths("artists").items()
}

OUT_SCOPE_JSON = LOG / "phase1_7_artist_images_repair_scope_task_formalize_03b.json"
OUT_SCOPE_CSV = LOG / "phase1_7_artist_images_repair_scope_task_formalize_03b.csv"
OUT_REPORT_JSON = LOG / "phase1_7_artist_images_metadata_repair_task_formalize_03b.json"
OUT_REPORT_MD = LOG / "phase1_7_artist_images_metadata_repair_task_formalize_03b.md"
OUT_DRYRUN_FINAL = LOG / "dryrun_run_phase1_seed10_artist_image_collect_task_formalize_03b.json"


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
            key = collect.metadata_record_lookup_key(
                str(row.get("artist_name_key") or ""),
                str(row.get("source_url") or ""),
            )
            sub.setdefault(key, i)
        idx[fair] = sub
    return by_fair, idx


def lookup_key(target: dict[str, Any]) -> str:
    source_url = str(target.get("source_url") or "")
    artist_name_en = str(target.get("artist_name_en") or "").strip() or collect.build_artist_name_en_from_source_url(source_url)
    artist_name_key = str(target.get("artist_name_key") or "").strip()
    if not artist_name_key:
        artist_name_key = collect.build_artist_name_key(artist_name_en, source_url)
    return collect.metadata_record_lookup_key(artist_name_key, source_url)


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


def to_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["fair_slug", "gallery_name", "artist_source_url", "reason", "meta_hash_count", "valid_count", "invalid_reasons"],
        )
        w.writeheader()
        for r in rows:
            w.writerow(r)


def build_scoped_raw_files(scope: list[dict[str, Any]], trial_raw: Path) -> dict[str, int]:
    by_fair_sources: dict[str, list[str]] = {"frieze_london": [], "liste": []}
    by_fair_targets: dict[str, dict[str, dict[str, Any]]] = {"frieze_london": {}, "liste": {}}
    for s in scope:
        t = s["target"]
        fair = str(t.get("fair_slug") or "")
        source_url = str(t.get("source_url") or "")
        if fair not in by_fair_sources or not source_url:
            continue
        if source_url in by_fair_targets[fair]:
            continue
        by_fair_sources[fair].append(source_url)
        by_fair_targets[fair][source_url] = t

    counts: dict[str, int] = {}
    for fair, raw_path in FORMAL_RAW_ARTISTS.items():
        source_rows = read_jsonl(raw_path)
        source_map: dict[str, dict[str, Any]] = {}
        for row in source_rows:
            src = str(row.get("source_url") or "").strip()
            if src and src not in source_map:
                source_map[src] = row

        out_rows: list[dict[str, Any]] = []
        for src in by_fair_sources[fair]:
            row = source_map.get(src)
            if row is None:
                t = by_fair_targets[fair][src]
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

        out_path = trial_raw / raw_path.name
        write_jsonl(out_path, out_rows)
        counts[fair] = len(out_rows)
    return counts


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
            r2_keys[i] = get_image_r2_key(newp)
            changed = True
        row["works_image_local_paths"] = local_paths
        row["works_image_r2_keys"] = r2_keys
    if changed:
        write_jsonl(meta_path, rows)


def main() -> int:
    run_id = f"TASK293_FORMALIZE03B_{now_compact()}"
    trial_root = (TRIAL_BASE / run_id).resolve()
    trial_raw = trial_root / "raw"
    trial_derived = trial_root / "derived"
    trial_logs = trial_root / "logs"
    trial_img = trial_derived / "images" / "artist_works_images"
    trial_meta = {fair_slug: trial_derived / src.name for fair_slug, src in FORMAL_META.items()}
    trial_raw.mkdir(parents=True, exist_ok=True)
    trial_derived.mkdir(parents=True, exist_ok=True)
    trial_logs.mkdir(parents=True, exist_ok=True)
    trial_img.mkdir(parents=True, exist_ok=True)

    for fair, src in FORMAL_META.items():
        shutil.copy2(src, trial_meta[fair])

    formal_rows, formal_idx = rows_by_fair(FORMAL_META)
    targets = load_targets_like_dryrun()
    scope: list[dict[str, Any]] = []
    for t in targets:
        ev = evaluate_target(t, formal_rows, formal_idx)
        if ev.get("would_fetch"):
            scope.append(
                {
                    "reason": str(ev.get("would_fetch_reason") or "UNKNOWN"),
                    "target": t,
                    "meta_hash_count": int(ev.get("meta_hash_count") or 0),
                    "valid_count": int(ev.get("valid_count") or 0),
                    "invalid_entries": ev.get("invalid_entries") or [],
                }
            )

    scope_csv_rows: list[dict[str, Any]] = []
    for s in scope:
        t = s["target"]
        scope_csv_rows.append(
            {
                "fair_slug": str(t.get("fair_slug") or ""),
                "gallery_name": str(t.get("gallery_name_en") or ""),
                "artist_source_url": str(t.get("source_url") or ""),
                "reason": str(s["reason"]),
                "meta_hash_count": int(s["meta_hash_count"]),
                "valid_count": int(s["valid_count"]),
                "invalid_reasons": "|".join(sorted({str(x.get("reason") or "") for x in s["invalid_entries"]})),
            }
        )
    write_json(OUT_SCOPE_JSON, {"run_id": run_id, "generated_at": now_iso(), "scope_total": len(scope), "items": scope_csv_rows})
    to_csv(scope_csv_rows, OUT_SCOPE_CSV)
    scoped_raw_counts = build_scoped_raw_files(scope, trial_raw)

    # Local repair: payload hash mismatch only.
    trial_rows, _ = rows_by_fair(trial_meta)
    local_fixed = Counter()
    local_fixed_by_reason = Counter()
    for s in scope:
        t = s["target"]
        fair = str(t.get("fair_slug") or "")
        key = lookup_key(t)
        rows = trial_rows.get(fair, [])
        row = None
        for r in rows:
            k = collect.metadata_record_lookup_key(
                str(r.get("artist_name_key") or ""),
                str(r.get("source_url") or ""),
            )
            if k == key:
                row = r
                break
        if not isinstance(row, dict):
            continue
        hashes = row.get("works_image_url_hashes") if isinstance(row.get("works_image_url_hashes"), list) else []
        locals_ = row.get("works_image_local_paths") if isinstance(row.get("works_image_local_paths"), list) else []
        payloads = row.get("works_image_payload_hashes") if isinstance(row.get("works_image_payload_hashes"), list) else []
        while len(payloads) < len(hashes):
            payloads.append("")
        changed = False
        for i, h in enumerate(hashes):
            bad = False
            for inv in s["invalid_entries"]:
                if str(inv.get("image_url_hash") or "") == str(h) and str(inv.get("reason") or "") == "PAYLOAD_HASH_MISMATCH":
                    bad = True
                    break
            if not bad:
                continue
            p = Path(str(locals_[i])) if i < len(locals_) else None
            if p and p.exists() and p.is_file():
                payloads[i] = hashlib.sha256(p.read_bytes()).hexdigest()
                changed = True
        if changed:
            row["works_image_payload_hashes"] = payloads
            local_fixed["PAYLOAD_HASH_MISMATCH"] += 1
            local_fixed_by_reason[str(s.get("reason") or "UNKNOWN")] += 1
    for fair, p in trial_meta.items():
        write_jsonl(p, trial_rows.get(fair, []))

    # Re-evaluate unresolved set after local-only repair.
    trial_rows_after_local, trial_idx_after_local = rows_by_fair(trial_meta)
    unresolved_after_local: list[dict[str, Any]] = []
    local_resolved_by_reason = Counter()
    for s in scope:
        ev = evaluate_target(s["target"], trial_rows_after_local, trial_idx_after_local)
        if ev.get("would_fetch"):
            unresolved_after_local.append(s)
        else:
            local_resolved_by_reason[str(s.get("reason") or "UNKNOWN")] += 1
    unresolved_raw_counts = build_scoped_raw_files(unresolved_after_local, trial_raw)

    dry_local = trial_logs / "artist_image_collect_dryrun_after_local_task_formalize_03b.json"
    dry_web = trial_logs / "artist_image_collect_dryrun_after_web_task_formalize_03b.json"
    web_summary = trial_logs / "artist_image_collect_web_reextract_summary_task_formalize_03b.json"
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
            TRIAL_BASE_REL,
            "--dry-run",
            "--dry-run-output",
            str(dry_local),
        ],
        ROOT,
    )
    local_dry = read_json(dry_local) if dry_local.exists() else {}

    web_executed = False
    web_completed = True
    web_result: dict[str, Any] = {}
    web_new_images = 0
    if unresolved_after_local:
        web_executed = True
        before = len([p for p in (trial_img / "2025").rglob("*") if p.is_file()]) if (trial_img / "2025").exists() else 0
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
                TRIAL_BASE_REL,
                "--output-json",
                str(web_summary),
            ],
            ROOT,
            timeout_sec=3600,
        )
        after = len([p for p in (trial_img / "2025").rglob("*") if p.is_file()]) if (trial_img / "2025").exists() else 0
        web_new_images = max(0, after - before)
        if bool(web_result.get("timed_out")) or int(web_result.get("exit_code", 1)) != 0:
            web_completed = False

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
            TRIAL_BASE_REL,
            "--dry-run",
            "--dry-run-output",
            str(dry_web),
        ],
        ROOT,
    )
    web_dry = read_json(dry_web) if dry_web.exists() else {}

    trial_rows_after_web, trial_idx_after_web = rows_by_fair(trial_meta)
    unresolved_after_web: list[dict[str, Any]] = []
    web_fixed_by_reason = Counter()
    for s in unresolved_after_local:
        ev = evaluate_target(s["target"], trial_rows_after_web, trial_idx_after_web)
        if ev.get("would_fetch"):
            unresolved_after_web.append(
                {
                    "fair_slug": str(s["target"].get("fair_slug") or ""),
                    "gallery_name": str(s["target"].get("gallery_name_en") or ""),
                    "source_url": str(s["target"].get("source_url") or ""),
                    "reason_before": str(s.get("reason") or ""),
                    "reason_after_web": str(ev.get("would_fetch_reason") or "UNKNOWN"),
                    "meta_hash_count_after_web": int(ev.get("meta_hash_count") or 0),
                    "valid_count_after_web": int(ev.get("valid_count") or 0),
                }
            )
        else:
            web_fixed_by_reason[str(s.get("reason") or "UNKNOWN")] += 1

    adopt_executed = False
    rollback_path = ""
    adopted_files: list[dict[str, Any]] = []
    final_dry = {}
    pre_result = {"status": "SKIP", "hold_reasons": ["not_run"]}
    post_result = {"status": "SKIP", "hold_reasons": ["not_run"]}
    if (
        web_completed
        and not unresolved_after_web
        and int(web_dry.get("would_fetch_count", 1)) == 0
        and int(web_dry.get("key_present_but_file_missing_count", 1)) == 0
    ):
        pre = run_preflight_gate(context="task_formalize_03b_pre_adopt", report_path=LOG / "formal_gate_preflight_report_task_formalize_03b.md")
        pre_result = pre
        if pre.get("status") == "PASS":
            rollback = TRASH_BASE / f"ADOPT_FORMALIZE03B_{now_compact()}"
            backup = rollback / "formal_backup" / "derived"
            backup.mkdir(parents=True, exist_ok=True)
            rewrite_trial_meta_paths_to_formal(trial_meta["frieze_london"], trial_img, FORMAL_IMG)
            rewrite_trial_meta_paths_to_formal(trial_meta["liste"], trial_img, FORMAL_IMG)
            if (trial_img / "2025").exists():
                for src in sorted([p for p in (trial_img / "2025").rglob("*") if p.is_file()]):
                    rel = src.relative_to(trial_img / "2025")
                    dst = FORMAL_IMG / "2025" / rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    if dst.exists():
                        bak = rollback / "formal_conflict_images" / rel
                        bak.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(dst), str(bak))
                    shutil.move(str(src), str(dst))
            for fair, fpath in FORMAL_META.items():
                b = backup / fpath.name
                if fpath.exists():
                    shutil.move(str(fpath), str(b))
                shutil.move(str(trial_meta[fair]), str(fpath))
                adopted_files.append({"formal_path": str(fpath), "backup_path": str(b), "sha256": hashlib.sha256(fpath.read_bytes()).hexdigest()})
            adopt_executed = True
            rollback_path = str(rollback)
            post_result = run_postflight_gate(context="task_formalize_03b_post_adopt", report_path=LOG / "formal_gate_postflight_report_task_formalize_03b.md")
            run_cmd(
                [
                    "python",
                    "run_phase1_seed10_artist_image_collect.py",
                    "--mode",
                    "fill_missing",
                    "--dry-run",
                    "--dry-run-output",
                    str(OUT_DRYRUN_FINAL),
                ],
                ROOT,
            )
            final_dry = read_json(OUT_DRYRUN_FINAL) if OUT_DRYRUN_FINAL.exists() else {}

    result = "HOLD"
    if (
        adopt_executed
        and pre_result.get("status") == "PASS"
        and post_result.get("status") == "PASS"
        and int(final_dry.get("would_fetch_count", 1)) == 0
        and int(final_dry.get("key_present_but_file_missing_count", 1)) == 0
    ):
        result = "SUCCESS"

    report = {
        "task": "TASK_FORMALIZE_03B",
        "run_id": run_id,
        "generated_at": now_iso(),
        "scope_total": len(scope),
        "scope_reason_counts": dict(Counter([str(s["reason"]) for s in scope])),
        "scoped_raw_counts": scoped_raw_counts,
        "local_fixed_counts": dict(local_fixed),
        "local_fixed_by_reason": dict(local_fixed_by_reason),
        "local_resolved_by_reason": dict(local_resolved_by_reason),
        "unresolved_after_local_count": len(unresolved_after_local),
        "unresolved_raw_counts": unresolved_raw_counts,
        "local_dryrun": local_dry,
        "web_executed": web_executed,
        "web_completed": web_completed,
        "web_command_result": web_result,
        "web_reextract_target_count": len(unresolved_after_local),
        "web_new_images": web_new_images,
        "web_fixed_by_reason": dict(web_fixed_by_reason),
        "unresolved_after_web_count": len(unresolved_after_web),
        "unresolved_after_web": unresolved_after_web,
        "web_dryrun": web_dry,
        "preflight": pre_result,
        "postflight": post_result,
        "adopt_executed": adopt_executed,
        "adopted_files": adopted_files,
        "rollback_path": rollback_path,
        "final_dryrun": final_dry,
        "result": result,
    }
    write_json(OUT_REPORT_JSON, report)
    md = []
    md.append("# TASK_FORMALIZE_03B report")
    md.append(f"- run_id: {run_id}")
    md.append(f"- scope_total: {len(scope)}")
    md.append(f"- local_fixed_counts: {dict(local_fixed)}")
    md.append(f"- local_resolved_by_reason: {dict(local_resolved_by_reason)}")
    md.append(f"- web_executed: {web_executed}, web_completed: {web_completed}, web_new_images: {web_new_images}")
    md.append(f"- web_fixed_by_reason: {dict(web_fixed_by_reason)}")
    md.append(f"- unresolved_after_web_count: {len(unresolved_after_web)}")
    md.append(f"- adopt_executed: {adopt_executed}")
    md.append(f"- rollback_path: {rollback_path}")
    if final_dry:
        md.append(f"- final_dryrun would_fetch={final_dry.get('would_fetch_count')} file_missing={final_dry.get('key_present_but_file_missing_count')}")
    else:
        md.append(f"- trial_dryrun would_fetch={web_dry.get('would_fetch_count')} file_missing={web_dry.get('key_present_but_file_missing_count')}")
    if unresolved_after_web:
        md.append("- unresolved_examples_top20:")
        for row in unresolved_after_web[:20]:
            md.append(
                f"  - {row.get('fair_slug')}/{row.get('gallery_name')} "
                f"| reason_before={row.get('reason_before')} "
                f"| reason_after_web={row.get('reason_after_web')} "
                f"| source_url={row.get('source_url')}"
            )
    md.append(f"- result: {result}")
    OUT_REPORT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"[DONE] {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
