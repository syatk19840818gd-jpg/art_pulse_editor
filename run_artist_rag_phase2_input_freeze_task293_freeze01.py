#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TASK_ID = "TASK293_FREEZE_01"
RUN_PREFIX = "TASK293_FREEZE01"
SEED_LIMIT_PER_FAIR = 5

TRIAL_BASE = Path("data/phase1_seed10/_trial")
PHASE2_BUNDLE_PATH = Path("data/phase2/bundles/PHASE2_INPUT_BUNDLE_TASK293_FREEZE01.json")
PREP02_BUNDLE_PATH = Path("data/phase2/bundles/PHASE2_INPUT_BUNDLE_TASK293_PREP02.json")
GALLERY_CSVS = {
    "frieze_london": Path("data/gallery_lists/gallery_list_frieze_london.csv"),
    "liste": Path("data/gallery_lists/gallery_list_liste.csv"),
}
ARTIST_IMAGE_PATHS = [
    Path("data/phase1_seed10/derived/artist_works_images_frieze_london.jsonl"),
    Path("data/phase1_seed10/derived/artist_works_images_liste.jsonl"),
]
ARTIST_TEXT_PATHS = [
    Path("data/phase1_seed10/raw/artists_frieze_london_2025.jsonl"),
    Path("data/phase1_seed10/raw/artists_liste_2025.jsonl"),
]
EXHIBITIONS_IMAGE_PATHS = [
    Path("data/phase1_seed10/derived/exhibitions_images_frieze_london_2025.jsonl"),
    Path("data/phase1_seed10/derived/exhibitions_images_liste_2025.jsonl"),
]
TARUTANI_TEXT_PATH = Path("data/Tarutani_data/tarutani_text.jsonl")
BASELINE_PREFIX = "TASK293_FIX02_"
BASELINE_CSV_NAME = "artist_rag_text_only_diagnosis_after_task293_fix02.csv"
GENERAL_SEGMENTS = {
    "about",
    "contact",
    "cookie-policy",
    "cookies",
    "privacy",
    "privacy-policy",
    "search",
    "sitemap",
    "terms",
    "terms-and-conditions",
}
TRACKING_KEYS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "source",
    "utm_campaign",
    "utm_content",
    "utm_medium",
    "utm_source",
    "utm_term",
}


@dataclass(frozen=True)
class GallerySeed:
    fair_slug: str
    gallery_name: str
    gallery_key: str
    gallery_url: str


def now_compact_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def now_iso_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha256_text(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_gallery_key(raw: str) -> str:
    s = unicodedata.normalize("NFKC", str(raw or ""))
    s = "".join(ch for ch in unicodedata.normalize("NFKD", s) if unicodedata.category(ch) != "Mn")
    s = s.lower().strip()
    return " ".join(s.split())


def canonical_url(url: str) -> str:
    if not url:
        return ""
    parts = urlsplit(url.strip())
    scheme = "https"
    netloc = parts.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = parts.path or "/"
    while "//" in path:
        path = path.replace("//", "/")
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    q = [(k, v) for (k, v) in parse_qsl(parts.query, keep_blank_values=True) if k.lower() not in TRACKING_KEYS]
    query = urlencode(q, doseq=True)
    return urlunsplit((scheme, netloc, path, query, ""))


def artist_canonical_url(url: str) -> str:
    cu = canonical_url(url)
    if not cu:
        return ""
    parsed = urlsplit(cu)
    segs = [s for s in parsed.path.split("/") if s]
    lowered = [s.lower() for s in segs]
    if "artists" in lowered:
        idx = lowered.index("artists")
        if idx + 1 < len(segs):
            new_path = "/" + "/".join(segs[: idx + 2])
            return urlunsplit((parsed.scheme, parsed.netloc, new_path, "", ""))
    return cu


def is_general_page(url: str) -> bool:
    cu = canonical_url(url)
    if not cu:
        return False
    segs = [s for s in urlsplit(cu).path.split("/") if s]
    if not segs:
        return False
    return segs[0].lower() in GENERAL_SEGMENTS


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


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")


def load_seed_galleries() -> list[GallerySeed]:
    # Seed scope is fixed to the 10 galleries present in current formal Artist Image truth.
    seeds_map: dict[tuple[str, str], GallerySeed] = {}
    for path in ARTIST_IMAGE_PATHS:
        for row in read_jsonl(path):
            fair_slug = str(row.get("fair_slug") or "")
            gallery_name = str(row.get("gallery_name_en") or "")
            gallery_url = str(row.get("source_url") or "")
            if not fair_slug or not gallery_name:
                continue
            key = (fair_slug, normalize_gallery_key(gallery_name))
            if key in seeds_map:
                continue
            seeds_map[key] = GallerySeed(
                fair_slug=fair_slug,
                gallery_name=gallery_name,
                gallery_key=key[1],
                gallery_url=gallery_url,
            )

    seeds = sorted(seeds_map.values(), key=lambda s: (s.fair_slug, s.gallery_name))
    if len(seeds) != 10:
        raise RuntimeError(f"Expected 10 seed galleries from formal artist image truth, found {len(seeds)}")
    return seeds


def pick_latest_baseline_csv() -> Path:
    dirs = [d for d in TRIAL_BASE.iterdir() if d.is_dir() and d.name.startswith(BASELINE_PREFIX)]
    if not dirs:
        raise FileNotFoundError("No TASK293_FIX02 baseline directory found under trial")
    latest = sorted(dirs, key=lambda p: p.name)[-1]
    csv_path = latest / BASELINE_CSV_NAME
    if not csv_path.exists():
        raise FileNotFoundError(f"Baseline CSV missing: {csv_path}")
    return csv_path


def main() -> int:
    run_id = f"{RUN_PREFIX}_{now_compact_utc()}"
    trial_root = TRIAL_BASE / run_id
    trial_root.mkdir(parents=True, exist_ok=False)

    log_rows: list[dict[str, Any]] = []
    log_rows.append({"stage": "init", "status": "PASS", "detail": f"run_id={run_id}"})

    seeds = load_seed_galleries()
    seed_set = {(s.fair_slug, s.gallery_key) for s in seeds}
    log_rows.append({"stage": "seed_load", "status": "PASS", "detail": f"seed_gallery_count={len(seeds)}"})

    baseline_csv = pick_latest_baseline_csv()
    log_rows.append({"stage": "baseline_pick", "status": "PASS", "detail": str(baseline_csv)})

    image_rows_src: list[dict[str, Any]] = []
    for p in ARTIST_IMAGE_PATHS:
        image_rows_src.extend(read_jsonl(p))
    text_rows_src: list[dict[str, Any]] = []
    for p in ARTIST_TEXT_PATHS:
        text_rows_src.extend(read_jsonl(p))

    trial_image_rows: list[dict[str, Any]] = []
    for row in image_rows_src:
        fair = str(row.get("fair_slug") or "")
        gallery = str(row.get("gallery_name_en") or "")
        gk = normalize_gallery_key(gallery)
        if (fair, gk) not in seed_set:
            continue
        source_url = str(row.get("source_url") or "")
        artist_key = artist_canonical_url(source_url)
        image_urls = row.get("works_image_urls") or []
        image_count = len([u for u in image_urls if isinstance(u, str) and u.strip()])
        out = dict(row)
        out["gallery_key_norm"] = gk
        out["artist_canonical_url"] = artist_key
        out["artist_key"] = artist_key
        out["image_count_non_empty"] = image_count
        trial_image_rows.append(out)

    excluded_samples: list[dict[str, str]] = []
    excluded_count = 0
    trial_text_rows: list[dict[str, Any]] = []
    for row in text_rows_src:
        fair = str(row.get("fair_slug") or "")
        gallery = str(row.get("gallery_name_en") or "")
        gk = normalize_gallery_key(gallery)
        if (fair, gk) not in seed_set:
            continue
        text = str(row.get("text") or "")
        if not text.strip():
            continue
        source_url = str(row.get("source_url") or "")
        if is_general_page(source_url):
            excluded_count += 1
            if len(excluded_samples) < 8:
                excluded_samples.append(
                    {"fair_slug": fair, "gallery_name": gallery, "source_url": source_url, "reason": "general_page"}
                )
            continue
        artist_key = artist_canonical_url(source_url)
        out = dict(row)
        out["gallery_key_norm"] = gk
        out["artist_canonical_url"] = artist_key
        out["artist_key"] = artist_key
        trial_text_rows.append(out)

    image_truth_path = trial_root / "artist_works_images_trial_truth_task293_freeze01.jsonl"
    text_truth_path = trial_root / "artist_text_trial_truth_task293_freeze01.jsonl"
    write_jsonl(image_truth_path, trial_image_rows)
    write_jsonl(text_truth_path, trial_text_rows)
    log_rows.append(
        {
            "stage": "trial_truth_build",
            "status": "PASS",
            "detail": f"image_rows={len(trial_image_rows)}, text_rows={len(trial_text_rows)}, excluded_text_rows={excluded_count}",
        }
    )

    img_artist_sets: dict[tuple[str, str], set[str]] = {}
    img_count_sum: dict[tuple[str, str], int] = {}
    txt_artist_sets: dict[tuple[str, str], set[str]] = {}
    txt_count_sum: dict[tuple[str, str], int] = {}
    display_name: dict[tuple[str, str], str] = {}

    for s in seeds:
        key = (s.fair_slug, s.gallery_key)
        img_artist_sets[key] = set()
        img_count_sum[key] = 0
        txt_artist_sets[key] = set()
        txt_count_sum[key] = 0
        display_name[key] = s.gallery_name

    for row in trial_image_rows:
        fair = str(row.get("fair_slug") or "")
        gallery = str(row.get("gallery_name_en") or "")
        gk = normalize_gallery_key(gallery)
        key = (fair, gk)
        if key not in img_artist_sets:
            continue
        image_count = int(row.get("image_count_non_empty") or 0)
        artist_key = str(row.get("artist_key") or "")
        if image_count > 0 and artist_key:
            img_artist_sets[key].add(artist_key)
        img_count_sum[key] += image_count

    for row in trial_text_rows:
        fair = str(row.get("fair_slug") or "")
        gallery = str(row.get("gallery_name_en") or "")
        gk = normalize_gallery_key(gallery)
        key = (fair, gk)
        if key not in txt_artist_sets:
            continue
        artist_key = str(row.get("artist_key") or "")
        if artist_key:
            txt_artist_sets[key].add(artist_key)
        txt_count_sum[key] += 1

    metrics_rows: list[dict[str, Any]] = []
    totals = {
        "image_artist_count": 0,
        "artist_image_count": 0,
        "text_artist_count": 0,
        "artist_text_count": 0,
        "matched_artist_count": 0,
        "text_only_artist_count": 0,
    }

    for s in seeds:
        key = (s.fair_slug, s.gallery_key)
        image_artists = img_artist_sets[key]
        text_artists = txt_artist_sets[key]
        matched = image_artists & text_artists
        image_artist_count = len(image_artists)
        text_artist_count = len(text_artists)
        matched_count = len(matched)
        text_only_count = len(text_artists - matched)
        rate_vs_image = (matched_count / image_artist_count) if image_artist_count > 0 else 0.0
        rate_vs_text = (matched_count / text_artist_count) if text_artist_count > 0 else 0.0

        row = {
            "fair_slug": s.fair_slug,
            "gallery_name": s.gallery_name,
            "image_artist_count": image_artist_count,
            "artist_image_count": img_count_sum[key],
            "text_artist_count": text_artist_count,
            "artist_text_count": txt_count_sum[key],
            "matched_artist_count": matched_count,
            "text_only_artist_count": text_only_count,
            "match_rate_vs_image_artists": round(rate_vs_image, 6),
            "match_rate_vs_text_artists": round(rate_vs_text, 6),
        }
        metrics_rows.append(row)

        totals["image_artist_count"] += image_artist_count
        totals["artist_image_count"] += img_count_sum[key]
        totals["text_artist_count"] += text_artist_count
        totals["artist_text_count"] += txt_count_sum[key]
        totals["matched_artist_count"] += matched_count
        totals["text_only_artist_count"] += text_only_count

    totals["match_rate_vs_image_artists"] = round(
        (totals["matched_artist_count"] / totals["image_artist_count"]) if totals["image_artist_count"] > 0 else 0.0,
        6,
    )
    totals["match_rate_vs_text_artists"] = round(
        (totals["matched_artist_count"] / totals["text_artist_count"]) if totals["text_artist_count"] > 0 else 0.0,
        6,
    )

    baseline_rows: dict[tuple[str, str], dict[str, Any]] = {}
    with baseline_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            b_key = (str(row.get("fair_slug") or ""), normalize_gallery_key(str(row.get("gallery_name") or "")))
            baseline_rows[b_key] = row

    major_drop_threshold = 0.05
    major_drop_rows: list[dict[str, Any]] = []
    for row in metrics_rows:
        b = baseline_rows.get((row["fair_slug"], normalize_gallery_key(row["gallery_name"])))
        if not b:
            continue
        before_rate = float(b.get("match_rate_vs_text_artists") or 0.0)
        after_rate = float(row["match_rate_vs_text_artists"])
        if before_rate - after_rate > major_drop_threshold:
            major_drop_rows.append(
                {
                    "fair_slug": row["fair_slug"],
                    "gallery_name": row["gallery_name"],
                    "before_match_rate_vs_text_artists": round(before_rate, 6),
                    "after_match_rate_vs_text_artists": round(after_rate, 6),
                    "drop": round(before_rate - after_rate, 6),
                }
            )

    all_image_rate_one = all(abs(float(r["match_rate_vs_image_artists"]) - 1.0) < 1e-9 for r in metrics_rows)
    worst3 = sorted(metrics_rows, key=lambda r: (float(r["match_rate_vs_text_artists"]), r["fair_slug"], r["gallery_name"]))[:3]

    metrics_csv = trial_root / "artist_rag_match_metrics_by_gallery_task293_freeze01.csv"
    write_csv(
        metrics_csv,
        metrics_rows,
        [
            "fair_slug",
            "gallery_name",
            "image_artist_count",
            "artist_image_count",
            "text_artist_count",
            "artist_text_count",
            "matched_artist_count",
            "text_only_artist_count",
            "match_rate_vs_image_artists",
            "match_rate_vs_text_artists",
        ],
    )

    input_hash_material = []
    for p in ARTIST_IMAGE_PATHS + ARTIST_TEXT_PATHS + list(GALLERY_CSVS.values()) + [baseline_csv]:
        input_hash_material.append(f"{p.as_posix()}:{sha256_file(p)}")
    input_fingerprint = sha256_text("\n".join(sorted(input_hash_material)))
    code_fingerprint = sha256_file(Path(__file__))
    scope_hash = sha256_text(f"{input_fingerprint}:{code_fingerprint}")

    final_label = (
        "FREEZE_OK_FOR_PHASE2_ARTIST_RAG"
        if all_image_rate_one and len(major_drop_rows) == 0
        else "FREEZE_HOLD_AND_REPORT"
    )

    metrics_summary_path = trial_root / "artist_rag_match_metrics_summary_task293_freeze01.json"
    write_json(
        metrics_summary_path,
        {
            "task_id": TASK_ID,
            "run_id": run_id,
            "overall": totals,
            "worst3_by_match_rate_vs_text_artists": worst3,
            "regression_guard": {
                "match_rate_vs_image_artists_all_eq_1_0": all_image_rate_one,
                "major_drop_threshold": major_drop_threshold,
                "major_drop_count": len(major_drop_rows),
                "major_drop_rows": major_drop_rows,
            },
            "final_label": final_label,
        },
    )

    manifest_path = trial_root / "artist_rag_integrated_trial_manifest_task293_freeze01.json"
    write_json(
        manifest_path,
        {
            "task_id": TASK_ID,
            "run_id": run_id,
            "trial_root": str(trial_root),
            "input_fingerprint": input_fingerprint,
            "code_fingerprint": code_fingerprint,
            "scope_hash": scope_hash,
            "inputs": {
                "artist_image_paths": [str(p) for p in ARTIST_IMAGE_PATHS],
                "artist_text_paths": [str(p) for p in ARTIST_TEXT_PATHS],
                "gallery_csvs": {k: str(v) for k, v in GALLERY_CSVS.items()},
                "baseline_csv": str(baseline_csv),
            },
            "outputs": {
                "artist_image_truth": str(image_truth_path),
                "artist_text_truth": str(text_truth_path),
                "metrics_by_gallery_csv": str(metrics_csv),
                "metrics_summary_json": str(metrics_summary_path),
            },
            "guard": {
                "match_rate_vs_image_artists_all_eq_1_0": all_image_rate_one,
                "major_drop_rows_count": len(major_drop_rows),
                "major_drop_threshold": major_drop_threshold,
            },
            "rule_scope": {
                "artists_parent_url_only_when_artists_segment_exists": True,
                "non_artists_absence_not_excluded": True,
                "general_page_exclusion_limited": sorted(GENERAL_SEGMENTS),
                "image_artist_count_requires_non_empty_images": True,
            },
        },
    )

    summary_path = trial_root / "artist_rag_integrated_trial_summary_task293_freeze01.json"
    write_json(
        summary_path,
        {
            "task_id": TASK_ID,
            "run_id": run_id,
            "executed_at": now_iso_utc(),
            "final_label": final_label,
            "input_fingerprint": input_fingerprint,
            "code_fingerprint": code_fingerprint,
            "scope_hash": scope_hash,
            "counts": {
                "seed_gallery_count": len(seeds),
                "trial_image_rows": len(trial_image_rows),
                "trial_text_rows": len(trial_text_rows),
                "excluded_text_rows": excluded_count,
            },
            "regression_guard": {
                "match_rate_vs_image_artists_all_eq_1_0": all_image_rate_one,
                "major_drop_rows_count": len(major_drop_rows),
            },
            "totals": totals,
            "worst3": worst3,
            "excluded_text_rows_samples": excluded_samples,
            "baseline_csv": str(baseline_csv),
            "trial_root": str(trial_root),
        },
    )

    log_rows.append(
        {
            "stage": "metrics_calc",
            "status": "PASS",
            "detail": f"all_image_rate_one={all_image_rate_one}; major_drop_rows={len(major_drop_rows)}",
        }
    )
    log_rows.append({"stage": "final_label", "status": "PASS", "detail": final_label})
    log_csv = trial_root / "artist_rag_integrated_trial_log_task293_freeze01.csv"
    write_csv(log_csv, log_rows, ["stage", "status", "detail"])

    prep02_bundle = json.loads(PREP02_BUNDLE_PATH.read_text(encoding="utf-8")) if PREP02_BUNDLE_PATH.exists() else {}
    exhibitions_text_truth = prep02_bundle.get("exhibitions_text_truth", {})

    PHASE2_BUNDLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_json(
        PHASE2_BUNDLE_PATH,
        {
            "bundle_id": "PHASE2_INPUT_BUNDLE_TASK293_FREEZE01",
            "created_at": now_iso_utc(),
            "source_task": TASK_ID,
            "run_id": run_id,
            "scope_hash": scope_hash,
            "input_fingerprint": input_fingerprint,
            "code_fingerprint": code_fingerprint,
            "artist_rag_truth": {
                "artist_text_truth": {
                    "path": str(text_truth_path),
                    "sha256": sha256_file(text_truth_path),
                },
                "artist_works_images_truth": {
                    "path": str(image_truth_path),
                    "sha256": sha256_file(image_truth_path),
                },
            },
            "artist_rag_metrics": {
                "by_gallery_csv": str(metrics_csv),
                "summary_json": str(metrics_summary_path),
            },
            "exhibitions_text_truth": exhibitions_text_truth,
            "exhibitions_image_truth": [
                {"path": str(p), "sha256": sha256_file(p)} for p in EXHIBITIONS_IMAGE_PATHS if p.exists()
            ],
            "tarutani_text_truth": {
                "path": str(TARUTANI_TEXT_PATH),
                "sha256": sha256_file(TARUTANI_TEXT_PATH) if TARUTANI_TEXT_PATH.exists() else "",
            },
            "gallery_lists": {
                fair: {"path": str(path), "sha256": sha256_file(path)}
                for fair, path in GALLERY_CSVS.items()
            },
            "anti_mixing": {
                "formal_read_only": True,
                "trial_isolated_with_run_id": True,
                "adoption_without_diff_gate": False,
                "adoption_without_regression_guard": False,
                "adoption_without_plan": False,
            },
            "gate": {
                "regression_guard_pass": all_image_rate_one and len(major_drop_rows) == 0,
                "final_label": final_label,
            },
        },
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
