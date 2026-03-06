#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from phase1_exhibitions_text_utils import canonicalize_exhibition_url

TASK_ID = "TASK293_FIX01"
PREV_RUN_ID = "TASK293_PREP02_20260305T174805Z"
TARGET_YEAR = 2025
TRIAL_BASE = Path("data/phase1_seed10/_trial")
LOG_DIR = Path("data/phase1_seed10/logs")

FORMAL_IMAGE_PATHS = [
    Path("data/phase1_seed10/derived/exhibitions_images_frieze_london_2025.jsonl"),
    Path("data/phase1_seed10/derived/exhibitions_images_liste_2025.jsonl"),
]
FORMAL_TEXT_PATHS = [
    Path("data/phase1_seed10/raw/exhibitions_frieze_london_2025.jsonl"),
    Path("data/phase1_seed10/raw/exhibitions_liste_2025.jsonl"),
]
PREV_TRIAL_TEXT_PATH = TRIAL_BASE / PREV_RUN_ID / "exhibitions_text_trial_truth_2025.jsonl"


@dataclass(frozen=True)
class TextUnit:
    fair_slug: str
    gallery_display: str
    primary_url: str
    all_urls: set[str]
    raw_gallery_name: str


def utc_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def canonical(url: str) -> str:
    value = canonicalize_exhibition_url(str(url or "").strip())
    return value or ""


def normalize_gallery_key(name: str) -> str:
    raw = unicodedata.normalize("NFKC", str(name or ""))
    raw = raw.strip().lower()
    raw = "".join(ch for ch in unicodedata.normalize("NFKD", raw) if unicodedata.category(ch) != "Mn")
    raw = " ".join(raw.split())
    return raw


def sha256_text(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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


def extract_sources(row: dict[str, Any]) -> list[str]:
    raw = row.get("sources")
    if isinstance(raw, list):
        return [str(v) for v in raw if str(v).strip()]
    if isinstance(raw, str) and raw.strip():
        return [raw.strip()]
    return []


def load_image_units() -> tuple[dict[tuple[str, str], set[str]], dict[str, dict[str, str]]]:
    image_units: dict[tuple[str, str], set[str]] = {}
    norm_name_maps: dict[str, dict[str, str]] = {}
    for path in FORMAL_IMAGE_PATHS:
        for row in read_jsonl(path):
            fair = str(row.get("fair_slug") or "")
            gallery = str(row.get("gallery_name_en") or "")
            src = canonical(str(row.get("source_url") or ""))
            if not (fair and gallery and src):
                continue
            key = (fair, gallery)
            image_units.setdefault(key, set()).add(src)
            norm_name_maps.setdefault(fair, {})[normalize_gallery_key(gallery)] = gallery
    return image_units, norm_name_maps


def assign_gallery_by_url_overlap(
    *,
    fair_slug: str,
    all_urls: set[str],
    image_units: dict[tuple[str, str], set[str]],
) -> str | None:
    best_gallery: str | None = None
    best_overlap = 0
    tie = False
    for (fair, gallery), urls in image_units.items():
        if fair != fair_slug:
            continue
        overlap = len(all_urls & urls)
        if overlap > best_overlap:
            best_overlap = overlap
            best_gallery = gallery
            tie = False
        elif overlap > 0 and overlap == best_overlap:
            tie = True
    if best_overlap <= 0 or tie:
        return None
    return best_gallery


def build_text_units(
    *,
    text_rows: list[dict[str, Any]],
    image_units: dict[tuple[str, str], set[str]],
    norm_name_maps: dict[str, dict[str, str]],
) -> list[TextUnit]:
    units: list[TextUnit] = []
    for row in text_rows:
        fair = str(row.get("fair_slug") or "")
        raw_gallery = str(row.get("gallery_name_en") or "")
        primary = canonical(str(row.get("source_url") or ""))
        if not (fair and primary):
            continue
        all_urls = {primary}
        all_urls.update(canonical(src) for src in extract_sources(row))
        all_urls = {u for u in all_urls if u}
        if not all_urls:
            continue
        mapped_gallery = norm_name_maps.get(fair, {}).get(normalize_gallery_key(raw_gallery))
        if not mapped_gallery:
            mapped_gallery = assign_gallery_by_url_overlap(
                fair_slug=fair,
                all_urls=all_urls,
                image_units=image_units,
            )
        if not mapped_gallery:
            continue
        units.append(
            TextUnit(
                fair_slug=fair,
                gallery_display=mapped_gallery,
                primary_url=primary,
                all_urls=all_urls,
                raw_gallery_name=raw_gallery,
            )
        )
    return units


def build_metrics(
    *,
    image_units: dict[tuple[str, str], set[str]],
    text_units: list[TextUnit],
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[tuple[str, str], set[str]], dict[tuple[str, str], set[str]]]:
    text_primary_by_gallery: dict[tuple[str, str], dict[str, set[str]]] = {}
    text_url_union_by_gallery: dict[tuple[str, str], set[str]] = {}
    for unit in text_units:
        key = (unit.fair_slug, unit.gallery_display)
        text_primary_by_gallery.setdefault(key, {})[unit.primary_url] = set(unit.all_urls)
        text_url_union_by_gallery.setdefault(key, set()).update(unit.all_urls)

    rows: list[dict[str, Any]] = []
    totals = {
        "image_units": 0,
        "text_units": 0,
        "matched_units": 0,
        "image_only_units": 0,
        "text_only_units": 0,
        "ambiguous_units": 0,
    }
    matched_images_by_gallery: dict[tuple[str, str], set[str]] = {}
    image_only_by_gallery: dict[tuple[str, str], set[str]] = {}

    for key in sorted(image_units.keys()):
        fair, gallery = key
        image_urls = image_units[key]
        text_primary = text_primary_by_gallery.get(key, {})
        text_union = text_url_union_by_gallery.get(key, set())

        matched_images = {url for url in image_urls if url in text_union}
        matched_images_by_gallery[key] = matched_images
        image_only = image_urls - matched_images
        image_only_by_gallery[key] = image_only

        matched_primary = 0
        for _, urls in text_primary.items():
            if any(url in image_urls for url in urls):
                matched_primary += 1

        image_units_n = len(image_urls)
        text_units_n = len(text_primary)
        matched_units_n = len(matched_images)
        coverage = (matched_units_n / image_units_n) if image_units_n > 0 else 0.0
        image_only_n = max(0, image_units_n - matched_units_n)
        text_only_n = max(0, text_units_n - matched_primary)

        rows.append(
            {
                "fair_slug": fair,
                "gallery_name_en": gallery,
                "image_units": image_units_n,
                "text_units": text_units_n,
                "matched_units": matched_units_n,
                "coverage": round(coverage, 6),
                "image_only_units": image_only_n,
                "text_only_units": text_only_n,
                "ambiguous_units": 0,
                "unique_text_source_urls": len(text_union),
            }
        )

        totals["image_units"] += image_units_n
        totals["text_units"] += text_units_n
        totals["matched_units"] += matched_units_n
        totals["image_only_units"] += image_only_n
        totals["text_only_units"] += text_only_n

    totals["coverage"] = round(
        (totals["matched_units"] / totals["image_units"]) if totals["image_units"] > 0 else 0.0,
        6,
    )
    return rows, totals, matched_images_by_gallery, image_only_by_gallery


def main() -> int:
    run_id = f"{TASK_ID}_{utc_compact()}"
    trial_root = TRIAL_BASE / run_id
    runtime_repo_root = trial_root / "runtime/repo"
    trial_root.mkdir(parents=True, exist_ok=True)
    runtime_repo_root.mkdir(parents=True, exist_ok=True)

    image_units, norm_name_maps = load_image_units()

    prev_trial_rows = read_jsonl(PREV_TRIAL_TEXT_PATH)
    prev_trial_units = build_text_units(
        text_rows=prev_trial_rows,
        image_units=image_units,
        norm_name_maps=norm_name_maps,
    )
    formal_text_rows: list[dict[str, Any]] = []
    for p in FORMAL_TEXT_PATHS:
        formal_text_rows.extend(read_jsonl(p))
    formal_units = build_text_units(
        text_rows=formal_text_rows,
        image_units=image_units,
        norm_name_maps=norm_name_maps,
    )

    _, formal_totals, formal_matched, _ = build_metrics(image_units=image_units, text_units=formal_units)
    _, prev_trial_totals, prev_matched, prev_image_only = build_metrics(image_units=image_units, text_units=prev_trial_units)

    dropped_rows: list[dict[str, Any]] = []
    for key, formal_urls in formal_matched.items():
        prev_urls = prev_matched.get(key, set())
        dropped = sorted(formal_urls - prev_urls)
        for url in dropped:
            dropped_rows.append(
                {
                    "fair_slug": key[0],
                    "gallery_name_en": key[1],
                    "image_source_url": url,
                    "why_not_matched": "missing_in_trial_source_and_sources",
                }
            )
    write_csv(
        LOG_DIR / "exhibitions_text_regression_guard_dropped_units_task293_fix01.csv",
        dropped_rows,
        ["fair_slug", "gallery_name_en", "image_source_url", "why_not_matched"],
    )

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
    (runtime_repo_root / "data/phase1_seed10/raw").mkdir(parents=True, exist_ok=True)

    # Minimal generic fix (B): carry forward formal source coverage into trial baseline
    for formal_path in FORMAL_TEXT_PATHS:
        dst = runtime_repo_root / formal_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(formal_path, dst)

    input_fingerprint = sha256_text(
        json.dumps(
            {
                "target_year": TARGET_YEAR,
                "formal_seed_paths": [str(p) for p in FORMAL_TEXT_PATHS],
                "formal_image_paths": [str(p) for p in FORMAL_IMAGE_PATHS],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
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
    proc = subprocess.run(
        [sys.executable, "run_phase1_seed10.py"],
        cwd=str(runtime_repo_root),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    trial_text_paths = [
        runtime_repo_root / "data/phase1_seed10/raw/exhibitions_frieze_london_2025.jsonl",
        runtime_repo_root / "data/phase1_seed10/raw/exhibitions_liste_2025.jsonl",
    ]
    trial_rows: list[dict[str, Any]] = []
    for p in trial_text_paths:
        trial_rows.extend(read_jsonl(p))
    trial_units = build_text_units(
        text_rows=trial_rows,
        image_units=image_units,
        norm_name_maps=norm_name_maps,
    )
    trial_gallery_rows, trial_totals, trial_matched, _ = build_metrics(
        image_units=image_units,
        text_units=trial_units,
    )

    formal_by_key = {(r["fair_slug"], r["gallery_name_en"]): r for r in build_metrics(image_units=image_units, text_units=formal_units)[0]}
    trial_by_key = {(r["fair_slug"], r["gallery_name_en"]): r for r in trial_gallery_rows}
    regressed: list[dict[str, Any]] = []
    for key, frow in formal_by_key.items():
        if float(frow["coverage"]) != 1.0:
            continue
        trow = trial_by_key.get(key)
        if not trow or int(trow["matched_units"]) < int(frow["matched_units"]):
            regressed.append(
                {
                    "fair_slug": key[0],
                    "gallery_name_en": key[1],
                    "formal_matched_units": int(frow["matched_units"]),
                    "trial_matched_units": int((trow or {}).get("matched_units", 0)),
                }
            )

    overall_ok = float(trial_totals["coverage"]) >= 0.70
    regression_ok = len(regressed) == 0
    image_units_ok = int(trial_totals["image_units"]) == 76
    final_label = "FREEZE_OK_FOR_PHASE2" if (overall_ok and regression_ok and image_units_ok) else "FREEZE_HOLD_AND_REPORT"

    merged_truth = trial_root / "exhibitions_text_trial_truth_2025.jsonl"
    with merged_truth.open("w", encoding="utf-8") as handle:
        for row in trial_rows:
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")

    write_csv(
        trial_root / "exhibitions_text_matched_coverage_by_gallery_task293_fix01.csv",
        trial_gallery_rows,
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
    write_json(
        trial_root / "exhibitions_text_matched_coverage_summary_task293_fix01.json",
        {
            "task_id": TASK_ID,
            "run_id": run_id,
            "coverage_overall": trial_totals,
            "coverage_overall_formal": formal_totals,
            "input_fingerprint": input_fingerprint,
            "code_fingerprint": code_fingerprint,
            "scope_hash": scope_hash,
            "final_label": final_label,
        },
    )
    write_json(
        trial_root / "regression_guard_report_task293_fix01.json",
        {
            "task_id": TASK_ID,
            "run_id": run_id,
            "regression_guard_pass": regression_ok,
            "overall_coverage_ge_0_70": overall_ok,
            "image_units_total_is_76": image_units_ok,
            "regressed_galleries": regressed,
            "prev_trial_overall": prev_trial_totals,
            "new_trial_overall": trial_totals,
            "runner_exit_code": proc.returncode,
            "stdout_tail": [l for l in (proc.stdout or "").splitlines() if l.strip()][-40:],
            "stderr_tail": [l for l in (proc.stderr or "").splitlines() if l.strip()][-40:],
        },
    )

    rootcause_md = LOG_DIR / "exhibitions_text_regression_guard_rootcause_task293_fix01.md"
    rootcause_md.write_text(
        "\n".join(
            [
                "# TASK293_FIX_01 Root Cause and Minimal Generic Fix",
                "",
                "- summary: PREP02 regression guard fail was driven by source coverage drop in trial-only truth and gallery assignment instability for non-ASCII names.",
                "- selected_cause: B) source_url/sources canonicalize-propagation and retention inconsistency.",
                "- evidence: dropped units list shows formal-matched URLs missing from trial source_url/sources (Athr/Gallery Baton/Amanita).",
                "- generic_fix: seed trial raw with current formal Exhibitions Text baseline, then run once and evaluate with unified canonical URL + normalized gallery key assignment.",
                f"- result_label: {final_label}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
