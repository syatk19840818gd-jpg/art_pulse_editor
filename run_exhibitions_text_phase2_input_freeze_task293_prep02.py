#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from phase1_exhibitions_text_utils import canonicalize_exhibition_url

TARGET_YEAR = 2025
TASK_ID = "TASK293_PREP02"
TRIAL_BASE = Path("data/phase1_seed10/_trial")
PHASE2_BUNDLE_PATH = Path("data/phase2/bundles/PHASE2_INPUT_BUNDLE_TASK293_PREP02.json")

FORMAL_IMAGE_PATHS = [
    Path("data/phase1_seed10/derived/exhibitions_images_frieze_london_2025.jsonl"),
    Path("data/phase1_seed10/derived/exhibitions_images_liste_2025.jsonl"),
]
FORMAL_TEXT_PATHS = [
    Path("data/phase1_seed10/raw/exhibitions_frieze_london_2025.jsonl"),
    Path("data/phase1_seed10/raw/exhibitions_liste_2025.jsonl"),
]
GALLERY_CSVS = {
    "frieze_london": Path("data/gallery_lists/gallery_list_frieze_london.csv"),
    "liste": Path("data/gallery_lists/gallery_list_liste.csv"),
}
SEED_LIMIT_PER_FAIR = 5


@dataclass(frozen=True)
class GallerySeed:
    fair_slug: str
    gallery_name_en: str
    exhibitions_url: str


def utc_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha256_text(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_gallery_name(raw_name: str) -> str:
    raw = (raw_name or "").strip()
    if "（" in raw:
        return raw.split("（", 1)[0].strip()
    if "(" in raw:
        return raw.split("(", 1)[0].strip()
    return raw


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], headers: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in headers})


def load_seed_galleries() -> list[GallerySeed]:
    seeds: list[GallerySeed] = []
    for fair_slug, csv_path in GALLERY_CSVS.items():
        with csv_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            count = 0
            for row in reader:
                if len(row) < 2:
                    continue
                name_en = parse_gallery_name(row[0])
                exhibitions_url = (row[1] or "").strip()
                if not name_en or not exhibitions_url:
                    continue
                seeds.append(GallerySeed(fair_slug=fair_slug, gallery_name_en=name_en, exhibitions_url=exhibitions_url))
                count += 1
                if count >= SEED_LIMIT_PER_FAIR:
                    break
    return seeds


def extract_sources(row: dict[str, Any]) -> list[str]:
    raw = row.get("sources")
    if isinstance(raw, list):
        return [str(v) for v in raw if str(v).strip()]
    if isinstance(raw, str) and raw.strip():
        return [raw.strip()]
    return []


def canonical(url: str) -> str:
    c = canonicalize_exhibition_url(str(url or "").strip())
    return c or ""


def build_gallery_metrics(
    *,
    image_rows: list[dict[str, Any]],
    text_rows: list[dict[str, Any]],
    seed_set: set[tuple[str, str]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    image_units_by_gallery: dict[tuple[str, str], set[str]] = {}
    for row in image_rows:
        fair = str(row.get("fair_slug") or "")
        gallery = str(row.get("gallery_name_en") or "")
        key = (fair, gallery)
        if key not in seed_set:
            continue
        src = canonical(str(row.get("source_url") or ""))
        if not src:
            continue
        image_units_by_gallery.setdefault(key, set()).add(src)

    text_units_primary_by_gallery: dict[tuple[str, str], dict[str, set[str]]] = {}
    text_all_urls_by_gallery: dict[tuple[str, str], set[str]] = {}
    for row in text_rows:
        fair = str(row.get("fair_slug") or "")
        gallery = str(row.get("gallery_name_en") or "")
        key = (fair, gallery)
        if key not in seed_set:
            continue
        primary = canonical(str(row.get("source_url") or ""))
        if not primary:
            continue
        urls = {primary}
        urls.update(canonical(src) for src in extract_sources(row))
        urls = {u for u in urls if u}
        if not urls:
            continue
        text_units_primary_by_gallery.setdefault(key, {})[primary] = urls
        text_all_urls_by_gallery.setdefault(key, set()).update(urls)

    all_keys = sorted(seed_set)
    out_rows: list[dict[str, Any]] = []
    totals = {
        "image_units": 0,
        "text_units": 0,
        "matched_units": 0,
        "image_only_units": 0,
        "text_only_units": 0,
        "ambiguous_units": 0,
    }
    for fair, gallery in all_keys:
        key = (fair, gallery)
        image_units = image_units_by_gallery.get(key, set())
        text_primary_units = text_units_primary_by_gallery.get(key, {})
        text_all_urls = text_all_urls_by_gallery.get(key, set())

        matched_images = {u for u in image_units if u in text_all_urls}
        matched_units = len(matched_images)
        image_units_n = len(image_units)
        text_units_n = len(text_primary_units)

        matched_primary = 0
        for primary, urls in text_primary_units.items():
            if any(url in image_units for url in urls):
                matched_primary += 1

        image_only = max(0, image_units_n - matched_units)
        text_only = max(0, text_units_n - matched_primary)
        ambiguous = 0
        coverage = (matched_units / image_units_n) if image_units_n > 0 else 0.0

        row = {
            "fair_slug": fair,
            "gallery_name_en": gallery,
            "image_units": image_units_n,
            "text_units": text_units_n,
            "matched_units": matched_units,
            "coverage": round(coverage, 6),
            "image_only_units": image_only,
            "text_only_units": text_only,
            "ambiguous_units": ambiguous,
            "unique_text_source_urls": len(text_all_urls),
        }
        out_rows.append(row)

        totals["image_units"] += image_units_n
        totals["text_units"] += text_units_n
        totals["matched_units"] += matched_units
        totals["image_only_units"] += image_only
        totals["text_only_units"] += text_only
        totals["ambiguous_units"] += ambiguous

    totals["coverage"] = round(
        (totals["matched_units"] / totals["image_units"]) if totals["image_units"] > 0 else 0.0,
        6,
    )
    return out_rows, totals


def main() -> int:
    run_id = f"{TASK_ID}_{utc_compact()}"
    trial_root = TRIAL_BASE / run_id
    runtime_root = trial_root / "runtime"
    runtime_repo_root = runtime_root / "repo"
    trial_root.mkdir(parents=True, exist_ok=True)
    runtime_repo_root.mkdir(parents=True, exist_ok=True)

    log_rows: list[dict[str, Any]] = []
    log_rows.append({"stage": "init", "status": "ok", "detail": f"run_id={run_id}"})

    copy_files = [
        "run_phase1_seed10.py",
        "phase1_exhibitions_text_utils.py",
        "phase1_artist_link_utils.py",
        "r2_auto_sync.py",
        "run_phase1_seed10_r2_sync.py",
        "sync_deletes_ledger.py",
    ]
    for rel in copy_files:
        src = Path(rel)
        if src.exists():
            dst = runtime_repo_root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    shutil.copytree("data/gallery_lists", runtime_repo_root / "data/gallery_lists", dirs_exist_ok=True)
    log_rows.append({"stage": "setup_runtime", "status": "ok", "detail": "copied runner/modules/gallery_lists"})

    seeds = load_seed_galleries()
    seed_set = {(s.fair_slug, s.gallery_name_en) for s in seeds}
    input_fingerprint_payload = json.dumps(
        {
            "target_year": TARGET_YEAR,
            "seed_limit_per_fair": SEED_LIMIT_PER_FAIR,
            "galleries": [f"{s.fair_slug}::{s.gallery_name_en}::{s.exhibitions_url}" for s in seeds],
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    input_fingerprint = sha256_text(input_fingerprint_payload)
    code_fingerprint = sha256_text(
        json.dumps(
            {rel: sha256_file(Path(rel)) for rel in copy_files if Path(rel).exists()},
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    scope_hash = sha256_text(f"{input_fingerprint}:{code_fingerprint}")

    env = os.environ.copy()
    env["PHASE1_STARTUP_MIN_SYNC"] = "0"
    env["R2_AUTO_SYNC_ENABLED"] = "0"
    env["PYTHONUTF8"] = "1"
    cmd = [sys.executable, "run_phase1_seed10.py"]
    proc = subprocess.run(
        cmd,
        cwd=str(runtime_repo_root),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    log_rows.append(
        {
            "stage": "integrated_trial_run",
            "status": "ok" if proc.returncode == 0 else "failed",
            "detail": f"exit_code={proc.returncode}",
        }
    )

    stdout_tail = [line for line in (proc.stdout or "").splitlines() if line.strip()][-40:]
    stderr_tail = [line for line in (proc.stderr or "").splitlines() if line.strip()][-40:]

    trial_text_paths = [
        runtime_repo_root / "data/phase1_seed10/raw/exhibitions_frieze_london_2025.jsonl",
        runtime_repo_root / "data/phase1_seed10/raw/exhibitions_liste_2025.jsonl",
    ]
    if any(not p.exists() for p in trial_text_paths):
        write_json(
            trial_root / "exhibitions_text_integrated_trial_summary_task293_prep02.json",
            {
                "task_id": TASK_ID,
                "run_id": run_id,
                "status": "failed",
                "reason": "trial_text_outputs_missing",
                "trial_text_paths": [str(p) for p in trial_text_paths],
                "stdout_tail": stdout_tail,
                "stderr_tail": stderr_tail,
            },
        )
        write_csv(
            trial_root / "exhibitions_text_integrated_trial_log_task293_prep02.csv",
            log_rows,
            ["stage", "status", "detail"],
        )
        return 1

    trial_text_rows: list[dict[str, Any]] = []
    for p in trial_text_paths:
        trial_text_rows.extend(read_jsonl(p))
    formal_text_rows: list[dict[str, Any]] = []
    for p in FORMAL_TEXT_PATHS:
        formal_text_rows.extend(read_jsonl(p))
    formal_image_rows: list[dict[str, Any]] = []
    for p in FORMAL_IMAGE_PATHS:
        formal_image_rows.extend(read_jsonl(p))

    trial_rows, trial_totals = build_gallery_metrics(
        image_rows=formal_image_rows,
        text_rows=trial_text_rows,
        seed_set=seed_set,
    )
    formal_rows, formal_totals = build_gallery_metrics(
        image_rows=formal_image_rows,
        text_rows=formal_text_rows,
        seed_set=seed_set,
    )

    formal_by_key = {(r["fair_slug"], r["gallery_name_en"]): r for r in formal_rows}
    trial_by_key = {(r["fair_slug"], r["gallery_name_en"]): r for r in trial_rows}
    regressed_one_point_zero: list[dict[str, Any]] = []
    for key, frow in formal_by_key.items():
        if float(frow["coverage"]) != 1.0:
            continue
        trow = trial_by_key.get(key)
        if not trow:
            continue
        if int(trow["matched_units"]) < int(frow["matched_units"]):
            regressed_one_point_zero.append(
                {
                    "fair_slug": key[0],
                    "gallery_name_en": key[1],
                    "formal_matched_units": int(frow["matched_units"]),
                    "trial_matched_units": int(trow["matched_units"]),
                }
            )

    merged_trial_truth = trial_root / "exhibitions_text_trial_truth_2025.jsonl"
    merged_trial_truth.parent.mkdir(parents=True, exist_ok=True)
    with merged_trial_truth.open("w", encoding="utf-8") as handle:
        for row in trial_text_rows:
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")

    coverage_csv = trial_root / "exhibitions_text_matched_coverage_by_gallery_task293_prep02.csv"
    write_csv(
        coverage_csv,
        trial_rows,
        [
            "fair_slug",
            "gallery_name_en",
            "image_units",
            "text_units",
            "matched_units",
            "coverage",
            "image_only_units",
            "text_only_units",
            "ambiguous_units",
            "unique_text_source_urls",
        ],
    )

    overall_ok = float(trial_totals["coverage"]) >= 0.70
    regression_ok = len(regressed_one_point_zero) == 0
    final_label = "FREEZE_OK_FOR_PHASE2" if (overall_ok and regression_ok) else "FREEZE_HOLD_AND_REPORT"

    summary = {
        "task_id": TASK_ID,
        "run_id": run_id,
        "executed_at": utc_iso(),
        "status": "ok" if proc.returncode == 0 else "runner_failed",
        "final_label": final_label,
        "input_fingerprint": input_fingerprint,
        "code_fingerprint": code_fingerprint,
        "scope_hash": scope_hash,
        "counts": {
            "seed_gallery_count": len(seeds),
            "trial_text_rows": len(trial_text_rows),
            "formal_text_rows": len(formal_text_rows),
            "formal_image_rows": len(formal_image_rows),
        },
        "matched_coverage_overall": trial_totals,
        "matched_coverage_overall_formal_baseline": formal_totals,
        "regressed_one_point_zero_galleries": regressed_one_point_zero,
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
        "trial_root": str(trial_root),
    }
    write_json(trial_root / "exhibitions_text_integrated_trial_summary_task293_prep02.json", summary)
    write_json(
        trial_root / "exhibitions_text_matched_coverage_summary_task293_prep02.json",
        {
            "task_id": TASK_ID,
            "run_id": run_id,
            "overall": trial_totals,
            "formal_baseline_overall": formal_totals,
            "final_label": final_label,
        },
    )
    write_csv(
        trial_root / "exhibitions_text_integrated_trial_log_task293_prep02.csv",
        log_rows,
        ["stage", "status", "detail"],
    )

    manifest = {
        "task_id": TASK_ID,
        "run_id": run_id,
        "trial_root": str(trial_root),
        "input_fingerprint": input_fingerprint,
        "code_fingerprint": code_fingerprint,
        "scope_hash": scope_hash,
        "input": {
            "seed_gallery_count": len(seeds),
            "galleries": [f"{s.fair_slug}::{s.gallery_name_en}" for s in seeds],
            "formal_image_paths": [str(p) for p in FORMAL_IMAGE_PATHS],
            "formal_text_paths": [str(p) for p in FORMAL_TEXT_PATHS],
        },
        "outputs": {
            "trial_truth_path": str(merged_trial_truth),
            "coverage_by_gallery_csv": str(coverage_csv),
            "summary_json": str(trial_root / "exhibitions_text_integrated_trial_summary_task293_prep02.json"),
            "coverage_summary_json": str(trial_root / "exhibitions_text_matched_coverage_summary_task293_prep02.json"),
            "trial_log_csv": str(trial_root / "exhibitions_text_integrated_trial_log_task293_prep02.csv"),
        },
        "guards": {
            "overall_coverage_ge_0_70": overall_ok,
            "regression_guard_pass": regression_ok,
        },
    }
    write_json(trial_root / "exhibitions_text_integrated_trial_manifest_task293_prep02.json", manifest)

    PHASE2_BUNDLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_json(
        PHASE2_BUNDLE_PATH,
        {
            "bundle_id": "PHASE2_INPUT_BUNDLE_TASK293_PREP02",
            "created_at": utc_iso(),
            "source_task": TASK_ID,
            "run_id": run_id,
            "scope_hash": scope_hash,
            "input_fingerprint": input_fingerprint,
            "code_fingerprint": code_fingerprint,
            "exhibitions_text_truth": {
                "path": str(merged_trial_truth),
                "sha256": sha256_file(merged_trial_truth),
            },
            "exhibitions_text_metrics": {
                "coverage_by_gallery_csv": str(coverage_csv),
                "coverage_summary_json": str(trial_root / "exhibitions_text_matched_coverage_summary_task293_prep02.json"),
            },
            "anti_mixing": {
                "formal_read_only": True,
                "adoption_without_diff_gate": False,
                "trial_isolated_with_run_id": True,
            },
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
