from __future__ import annotations

import argparse
import csv
import json
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from phase1_exhibitions_text_utils import canonicalize_gallery_scope_name

JOIN_BLOCKERS = {"AMBIGUOUS_JOIN", "DUPLICATE_JOIN_COLLISION", "IMAGE_TEXT_MISMATCH"}
REJECT_BUCKET = "REJECT_CANDIDATE"
YEAR_REVIEW_BUCKET = "YEAR_REVIEW"
ROUTE_SOFT_REVIEW_BUCKET = "ROUTE_SOFT_REVIEW"
TEXT_ONLY_REVIEW_BUCKET = "TEXT_ONLY_REVIEW"
CLEAN_BUCKET = "CLEAN_PASS_CANDIDATE"
COVERAGE_BUCKET = "COVERAGE_REVIEW"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utc_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip().lstrip("\ufeff")
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


@dataclass
class ScopeMatch:
    fair_slug: str
    scope_gallery_name: str
    matched_gallery_name: str
    match_mode: str
    ratio: float
    row_count: int


def _closest_gallery_name(scope_name: str, raw_gallery_names: list[str]) -> tuple[str, float]:
    scope_key = canonicalize_gallery_scope_name(scope_name)
    best_name = ""
    best_ratio = 0.0
    for raw_name in raw_gallery_names:
        raw_key = canonicalize_gallery_scope_name(raw_name)
        ratio = SequenceMatcher(a=scope_key, b=raw_key).ratio()
        if ratio > best_ratio:
            best_name = raw_name
            best_ratio = ratio
    return best_name, best_ratio


def build_controlled_input(
    *,
    scope_manifest: dict[str, Any],
    raw_by_fair: dict[str, list[dict[str, Any]]],
    fuzzy_threshold: float,
) -> tuple[list[dict[str, Any]], list[ScopeMatch], list[dict[str, Any]]]:
    input_rows: list[dict[str, Any]] = []
    scope_matches: list[ScopeMatch] = []
    coverage_rows: list[dict[str, Any]] = []
    seen_keys: set[str] = set()

    scope = scope_manifest.get("scope", {})
    for fair_slug, scope_galleries in scope.items():
        fair_rows = [row for row in raw_by_fair.get(fair_slug, []) if str(row.get("fair_slug") or "").strip() == fair_slug]
        raw_gallery_to_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in fair_rows:
            g = str(row.get("gallery_name_en") or "").strip()
            raw_gallery_to_rows[g].append(row)
        canonical_raw_index: dict[str, list[str]] = defaultdict(list)
        for raw_name in raw_gallery_to_rows:
            canonical_raw_index[canonicalize_gallery_scope_name(raw_name)].append(raw_name)
        raw_gallery_names = sorted(raw_gallery_to_rows.keys())

        for scope_gallery in scope_galleries:
            scope_key = canonicalize_gallery_scope_name(scope_gallery)
            matched_name = ""
            match_mode = "none"
            ratio = 0.0

            exact_names = canonical_raw_index.get(scope_key, [])
            if exact_names:
                matched_name = exact_names[0]
                match_mode = "canonical_exact"
                ratio = 1.0
            elif raw_gallery_names:
                nearest_name, nearest_ratio = _closest_gallery_name(scope_gallery, raw_gallery_names)
                if nearest_name and nearest_ratio >= fuzzy_threshold:
                    matched_name = nearest_name
                    match_mode = "canonical_near_match"
                    ratio = nearest_ratio

            chosen_rows = raw_gallery_to_rows.get(matched_name, [])
            for row in chosen_rows:
                src = str(row.get("source_url") or "").strip()
                key = f"{fair_slug}|{matched_name}|{src}"
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                input_rows.append(row)

            scope_matches.append(
                ScopeMatch(
                    fair_slug=fair_slug,
                    scope_gallery_name=str(scope_gallery),
                    matched_gallery_name=matched_name,
                    match_mode=match_mode,
                    ratio=round(ratio, 6),
                    row_count=len(chosen_rows),
                )
            )

            if len(chosen_rows) == 0:
                coverage_rows.append(
                    {
                        "fair_slug": fair_slug,
                        "gallery_name_en": str(scope_gallery),
                        "coverage_bucket": COVERAGE_BUCKET,
                        "root_cause": "scope_name_variant_mismatch",
                        "detail": "no raw rows found after canonical/fuzzy scope matching",
                    }
                )

    return input_rows, scope_matches, coverage_rows


def triage_record(row: dict[str, Any]) -> tuple[str, str]:
    source_url = str(row.get("source_url") or "").strip()
    join_status = str(row.get("join_status") or "").strip()
    route_quality = str(row.get("route_quality_label") or "pass").strip()
    year_quality = str(row.get("year_quality_label") or "pass").strip()
    provenance_suspicious = bool(row.get("provenance_suspicious"))
    date_non_target = bool(row.get("date_non_target_year"))

    if (
        not source_url
        or join_status in JOIN_BLOCKERS
        or route_quality == "hard_bad"
        or year_quality == "hard_mismatch"
        or provenance_suspicious
        or date_non_target
    ):
        return REJECT_BUCKET, "blocker_condition"
    if year_quality == "soft_suspicious":
        return YEAR_REVIEW_BUCKET, "soft_year_risk"
    if route_quality == "soft_suspicious":
        return ROUTE_SOFT_REVIEW_BUCKET, "soft_route_risk"
    if join_status == "TEXT_ONLY":
        return TEXT_ONLY_REVIEW_BUCKET, "no_image_candidate"
    return CLEAN_BUCKET, "join_ok_no_risk"


def resolve_scope_gallery_name(
    *,
    fair_slug: str,
    proposal_gallery_name: str,
    scope_matches: list[ScopeMatch],
) -> str:
    proposal_key = canonicalize_gallery_scope_name(proposal_gallery_name)
    if not proposal_key:
        return proposal_gallery_name
    for match in scope_matches:
        if match.fair_slug != fair_slug:
            continue
        scope_key = canonicalize_gallery_scope_name(match.scope_gallery_name)
        matched_key = canonicalize_gallery_scope_name(match.matched_gallery_name)
        if proposal_key == scope_key or (matched_key and proposal_key == matched_key):
            return match.scope_gallery_name
    return proposal_gallery_name


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TASK236 coverage normalization fix + scope review re-evaluation")
    parser.add_argument(
        "--task235-manifest",
        default="data/phase1_seed10/logs/exhibitions_text_scope_review_gate_manifest_task235.json",
    )
    parser.add_argument(
        "--task234-scope-manifest",
        default="data/phase1_seed10/logs/task_t234_controlled_scope_10g_manifest.json",
    )
    parser.add_argument(
        "--raw-frieze-jsonl",
        default="data/phase1_seed10/raw/exhibitions_frieze_london_2025.jsonl",
    )
    parser.add_argument(
        "--raw-liste-jsonl",
        default="data/phase1_seed10/raw/exhibitions_liste_2025.jsonl",
    )
    parser.add_argument(
        "--lane-script",
        default="run_exhibitions_text_standard_lane_minimal.py",
    )
    parser.add_argument(
        "--output-root",
        default="data/phase1_seed10/logs/task_t236_exhibitions_text_scope_review_phase_start",
    )
    parser.add_argument("--target-year", type=int, default=2025)
    parser.add_argument("--fuzzy-threshold", type=float, default=0.93)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_id = f"task236_{utc_compact()}"

    task235_manifest = read_json(Path(args.task235_manifest), default={})
    task234_scope_manifest = read_json(Path(args.task234_scope_manifest), default={})
    raw_by_fair = {
        "frieze_london": read_jsonl(Path(args.raw_frieze_jsonl)),
        "liste": read_jsonl(Path(args.raw_liste_jsonl)),
    }

    controlled_rows, scope_matches, coverage_rows = build_controlled_input(
        scope_manifest=task234_scope_manifest,
        raw_by_fair=raw_by_fair,
        fuzzy_threshold=float(args.fuzzy_threshold),
    )

    controlled_input_path = Path("data/phase1_seed10/logs/task_t236_controlled_scope_input_10g.jsonl")
    controlled_manifest_path = Path("data/phase1_seed10/logs/task_t236_controlled_scope_10g_manifest.json")
    write_jsonl(controlled_input_path, controlled_rows)

    gallery_row_counts = []
    fair_gallery_counts: dict[tuple[str, str], int] = defaultdict(int)
    for row in controlled_rows:
        fair = str(row.get("fair_slug") or "").strip()
        gallery = str(row.get("gallery_name_en") or "").strip()
        fair_gallery_counts[(fair, gallery)] += 1
    for (fair, gallery), count in sorted(fair_gallery_counts.items()):
        gallery_row_counts.append({"fair_slug": fair, "gallery_name_en": gallery, "row_count": count})

    controlled_scope_manifest = {
        "artifact": "exhibitions_text_controlled_scope_manifest",
        "task": "TASK236",
        "run_id": run_id,
        "target_year": int(args.target_year),
        "scope_hash": task234_scope_manifest.get("scope_hash", ""),
        "scope_gallery_count": int(task234_scope_manifest.get("scope_gallery_count") or 0),
        "scope": task234_scope_manifest.get("scope", {}),
        "input_jsonl": str(controlled_input_path),
        "input_row_count": len(controlled_rows),
        "gallery_row_counts": gallery_row_counts,
        "scope_match_mapping": [
            {
                "fair_slug": m.fair_slug,
                "scope_gallery_name": m.scope_gallery_name,
                "matched_gallery_name": m.matched_gallery_name,
                "match_mode": m.match_mode,
                "match_ratio": m.ratio,
                "row_count": m.row_count,
            }
            for m in scope_matches
        ],
        "policies": {
            "canonicalization_scope_only": True,
            "display_name_overwrite": False,
            "proposal_only": True,
            "formal_untouched": True,
            "anti_mixing": True,
        },
    }
    write_json(controlled_manifest_path, controlled_scope_manifest)

    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    lane_cmd = [
        "python",
        str(Path(args.lane_script)),
        "--input-jsonl",
        str(controlled_input_path),
        "--image-jsonl",
        "data/phase1_seed10/derived/exhibitions_images_frieze_london_2025.jsonl",
        "--image-jsonl",
        "data/phase1_seed10/derived/exhibitions_images_liste_2025.jsonl",
        "--output-dir",
        str(output_root),
        "--text-sources-json",
        str(output_root / "text_sources.json"),
        "--target-year",
        str(int(args.target_year)),
        "--run-id",
        run_id,
    ]
    subprocess.run(lane_cmd, check=True)

    proposal_summary_path = output_root / f"exhibitions_text_proposal_summary_{run_id}.json"
    proposal_manifest_path = output_root / f"exhibitions_text_proposal_manifest_{run_id}.json"
    proposal_records_path = output_root / f"exhibitions_text_proposal_records_{run_id}.jsonl"
    proposal_summary = read_json(proposal_summary_path, default={})
    proposal_records = read_jsonl(proposal_records_path)

    triage_rows: list[dict[str, Any]] = []
    triage_counts = Counter()
    by_gallery_bucket = defaultdict(Counter)
    by_fair_bucket = defaultdict(Counter)
    text_only_patterns = Counter()
    route_soft_patterns = Counter()

    for row in proposal_records:
        bucket, reason = triage_record(row)
        triage_counts[bucket] += 1
        gallery = str(row.get("gallery_name_en") or "").strip()
        fair = str(row.get("fair_slug") or "").strip()
        scope_gallery = resolve_scope_gallery_name(
            fair_slug=fair,
            proposal_gallery_name=gallery,
            scope_matches=scope_matches,
        )
        by_gallery_bucket[(scope_gallery, fair)][bucket] += 1
        by_fair_bucket[fair][bucket] += 1
        if bucket == TEXT_ONLY_REVIEW_BUCKET:
            key = (str(row.get("join_basis") or "").strip(), str(row.get("route_quality_label") or "").strip())
            text_only_patterns[key] += 1
        if bucket == ROUTE_SOFT_REVIEW_BUCKET:
            src = str(row.get("source_url") or "").lower()
            if "/past" in src:
                route_soft_patterns["/past"] += 1
            elif "/upcoming" in src:
                route_soft_patterns["/upcoming"] += 1
            else:
                route_soft_patterns["other_soft_route"] += 1
        triage_rows.append(
            {
                "gallery_name_en": gallery,
                "fair_slug": fair,
                "target_year": row.get("target_year", ""),
                "source_url": str(row.get("source_url") or ""),
                "join_status": str(row.get("join_status") or ""),
                "join_basis": str(row.get("join_basis") or ""),
                "route_quality_label": str(row.get("route_quality_label") or ""),
                "year_quality_label": str(row.get("year_quality_label") or ""),
                "provenance_suspicious": bool(row.get("provenance_suspicious")),
                "triage_bucket": bucket,
                "triage_reason": reason,
            }
        )

    coverage_count = len(coverage_rows)
    reject_count = int(triage_counts.get(REJECT_BUCKET, 0))
    join_blockers = int(
        proposal_summary.get("ambiguous_join_count", 0)
        + proposal_summary.get("duplicate_join_group_count", 0)
        + proposal_summary.get("image_text_mismatch_count", 0)
    )
    if reject_count > 0 or join_blockers > 0:
        decision = "HOLD_FOR_INPUT_COVERAGE_REVIEW"
    elif coverage_count > 0:
        decision = "HOLD_FOR_NORMALIZATION_TUNING"
    else:
        decision = "READY_FOR_TEXT_SCOPE_REVIEW_PHASE"

    table_rows: list[dict[str, Any]] = []
    scope = task234_scope_manifest.get("scope", {})
    for fair_slug, galleries in scope.items():
        for scope_gallery in galleries:
            key = (str(scope_gallery), str(fair_slug))
            counter = by_gallery_bucket.get(key, Counter())
            table_rows.append(
                {
                    "gallery_name_en": str(scope_gallery),
                    "fair_slug": str(fair_slug),
                    CLEAN_BUCKET: int(counter.get(CLEAN_BUCKET, 0)),
                    TEXT_ONLY_REVIEW_BUCKET: int(counter.get(TEXT_ONLY_REVIEW_BUCKET, 0)),
                    ROUTE_SOFT_REVIEW_BUCKET: int(counter.get(ROUTE_SOFT_REVIEW_BUCKET, 0)),
                    YEAR_REVIEW_BUCKET: int(counter.get(YEAR_REVIEW_BUCKET, 0)),
                    COVERAGE_BUCKET: 1 if any(
                        r["fair_slug"] == fair_slug and r["gallery_name_en"] == scope_gallery for r in coverage_rows
                    ) else 0,
                    REJECT_BUCKET: int(counter.get(REJECT_BUCKET, 0)),
                }
            )

    triage_summary = {
        "artifact": "exhibitions_text_coverage_normalization_summary",
        "task": "TASK236",
        "created_at": utc_now_iso(),
        "run_id": run_id,
        "scope_hash": task234_scope_manifest.get("scope_hash", ""),
        "scope_match_fix_applied": True,
        "scope_name_variant_mismatch_resolved": coverage_count == 0,
        "coverage_review_count": int(coverage_count),
        "triage_counts": dict(triage_counts),
        "by_fair_bucket_counts": {fair: dict(counter) for fair, counter in by_fair_bucket.items()},
        "review_patterns": {
            "text_only_main_patterns": [
                {"join_basis": key[0], "route_quality_label": key[1], "count": count}
                for key, count in sorted(text_only_patterns.items(), key=lambda x: (-x[1], x[0]))
            ],
            "route_soft_main_patterns": dict(route_soft_patterns),
            "year_review_count": int(triage_counts.get(YEAR_REVIEW_BUCKET, 0)),
            "reject_candidate_count": int(reject_count),
        },
        "proposal_summary_excerpt": {
            "records_total": int(proposal_summary.get("records_total", 0)),
            "ambiguous_join_count": int(proposal_summary.get("ambiguous_join_count", 0)),
            "duplicate_join_group_count": int(proposal_summary.get("duplicate_join_group_count", 0)),
            "image_text_mismatch_count": int(proposal_summary.get("image_text_mismatch_count", 0)),
            "gate_verdict": str(proposal_summary.get("gate_verdict") or ""),
            "blocker_labels": list(proposal_summary.get("blocker_labels") or []),
        },
        "go_hold_decision": decision,
        "next_task_recommendation": {
            "id": "TASK237",
            "title": "EXHIBITIONS-TEXT-SCOPE-REVIEW-PHASE-CONTROLLED-START",
            "ja": "Start controlled text scope review phase after normalization fix",
        },
    }

    summary_path = Path("data/phase1_seed10/logs/exhibitions_text_coverage_normalization_summary_task236.json")
    table_path = Path("data/phase1_seed10/logs/exhibitions_text_coverage_normalization_table_task236.csv")
    coverage_path = Path("data/phase1_seed10/logs/exhibitions_text_scope_review_gate_coverage_review_task236.csv")
    triage_records_path = Path("data/phase1_seed10/logs/exhibitions_text_scope_review_gate_triage_records_task236.csv")
    triage_table_path = Path("data/phase1_seed10/logs/exhibitions_text_scope_review_gate_triage_table_task236.csv")
    report_path = Path("data/phase1_seed10/logs/exhibitions_text_coverage_normalization_task236.md")
    manifest_path = Path("data/phase1_seed10/logs/exhibitions_text_coverage_normalization_manifest_task236.json")

    write_json(summary_path, triage_summary)
    write_csv(
        table_path,
        table_rows,
        [
            "gallery_name_en",
            "fair_slug",
            CLEAN_BUCKET,
            TEXT_ONLY_REVIEW_BUCKET,
            ROUTE_SOFT_REVIEW_BUCKET,
            YEAR_REVIEW_BUCKET,
            COVERAGE_BUCKET,
            REJECT_BUCKET,
        ],
    )
    write_csv(
        coverage_path,
        coverage_rows,
        ["fair_slug", "gallery_name_en", "coverage_bucket", "root_cause", "detail"],
    )
    write_csv(
        triage_records_path,
        triage_rows,
        [
            "gallery_name_en",
            "fair_slug",
            "target_year",
            "source_url",
            "join_status",
            "join_basis",
            "route_quality_label",
            "year_quality_label",
            "provenance_suspicious",
            "triage_bucket",
            "triage_reason",
        ],
    )
    write_csv(
        triage_table_path,
        table_rows,
        [
            "gallery_name_en",
            "fair_slug",
            CLEAN_BUCKET,
            TEXT_ONLY_REVIEW_BUCKET,
            ROUTE_SOFT_REVIEW_BUCKET,
            YEAR_REVIEW_BUCKET,
            COVERAGE_BUCKET,
            REJECT_BUCKET,
        ],
    )

    report = (
        "# TASK236 Exhibitions Text Coverage Normalization Fix and Scope Review Phase Start\n\n"
        "## coverage_mismatch_cause_ja\n"
        "- TASK235 root cause: `scope_name_variant_mismatch` for `Anca Potera?u Gallery`.\n"
        "- Raw input contains diacritic variant (`Anca Potera\\u015fu Gallery`), so exact string scope match dropped one valid row.\n\n"
        "## normalization_fix_ja\n"
        "- Applied generic scope-only canonicalization: Unicode normalization, diacritic removal, case-fold, whitespace absorb, minimal symbol absorb.\n"
        "- Added generic near-match fallback only when canonical exact match is missing.\n"
        "- Display name fields are unchanged; join contract fields (`source_url/sources/text_hash`) unchanged.\n\n"
        "## reevaluation_10g_ja\n"
        f"- coverage_review_count={coverage_count}\n"
        f"- go_hold_decision={decision}\n"
        f"- proposal gate_verdict={proposal_summary.get('gate_verdict', '')}\n"
        f"- join blockers: ambiguous={proposal_summary.get('ambiguous_join_count', 0)}, "
        f"duplicate={proposal_summary.get('duplicate_join_group_count', 0)}, "
        f"mismatch={proposal_summary.get('image_text_mismatch_count', 0)}\n\n"
        "## recommended_next_task\n"
        "- recommended_next_task_id: `TASK237`\n"
        "- recommended_next_task_title: `EXHIBITIONS-TEXT-SCOPE-REVIEW-PHASE-CONTROLLED-START`\n"
        "- recommended_next_task_ja: `Start controlled text scope review phase after normalization fix`\n"
    )
    report_path.write_text(report, encoding="utf-8")

    manifest = {
        "artifact": "exhibitions_text_coverage_normalization_manifest",
        "task": "TASK236",
        "run_id": run_id,
        "inputs": {
            "task235_manifest": str(Path(args.task235_manifest)),
            "task234_scope_manifest": str(Path(args.task234_scope_manifest)),
            "raw_frieze_jsonl": str(Path(args.raw_frieze_jsonl)),
            "raw_liste_jsonl": str(Path(args.raw_liste_jsonl)),
            "lane_script": str(Path(args.lane_script)),
        },
        "intermediate": {
            "controlled_scope_input_jsonl": str(controlled_input_path),
            "controlled_scope_manifest_json": str(controlled_manifest_path),
            "proposal_records_jsonl": str(proposal_records_path),
            "proposal_summary_json": str(proposal_summary_path),
            "proposal_manifest_json": str(proposal_manifest_path),
        },
        "outputs": {
            "summary_json": str(summary_path),
            "table_csv": str(table_path),
            "coverage_review_csv": str(coverage_path),
            "triage_records_csv": str(triage_records_path),
            "triage_table_csv": str(triage_table_path),
            "report_md": str(report_path),
            "manifest_json": str(manifest_path),
        },
        "policies": {
            "proposal_only": True,
            "formal_untouched": True,
            "join_contract_unchanged": True,
            "display_name_overwrite": False,
            "anti_mixing_enforced": True,
            "adoption_executed": False,
            "rollback_executed": False,
        },
    }
    write_json(manifest_path, manifest)
    print(
        f"[task236] run_id={run_id} rows={len(controlled_rows)} "
        f"coverage_review={coverage_count} decision={decision}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
