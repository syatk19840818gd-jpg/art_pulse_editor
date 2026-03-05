from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

CLEAN_BUCKET = "CLEAN_PASS_CANDIDATE"

STABLE_TEXT_ONLY_WARNING = "STABLE_TEXT_ONLY_WARNING"
ROUTE_SOFT_REVIEW_KEEP = "ROUTE_SOFT_REVIEW_KEEP"
YEAR_REVIEW_KEEP = "YEAR_REVIEW_KEEP"
RESOLUTION_CANDIDATE = "RESOLUTION_CANDIDATE"
ESCALATE_CANDIDATE = "ESCALATE_CANDIDATE"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TASK238 Exhibitions Text controlled review queue resolution phase 1")
    parser.add_argument(
        "--task237-summary",
        default="data/phase1_seed10/logs/exhibitions_text_scope_review_phase_summary_task237.json",
    )
    parser.add_argument(
        "--task237-clean-csv",
        default="data/phase1_seed10/logs/exhibitions_text_scope_review_phase_clean_pass_candidates_task237.csv",
    )
    parser.add_argument(
        "--task237-review-csv",
        default="data/phase1_seed10/logs/exhibitions_text_scope_review_phase_review_queue_task237.csv",
    )
    parser.add_argument(
        "--task236-coverage-review-csv",
        default="data/phase1_seed10/logs/exhibitions_text_scope_review_gate_coverage_review_task236.csv",
    )
    parser.add_argument(
        "--output-dir",
        default="data/phase1_seed10/logs",
    )
    parser.add_argument("--run-id", default="")
    return parser.parse_args()


def _is_listing_like_source(url: str) -> bool:
    path = (urlparse(str(url or "").strip()).path or "").lower().strip("/")
    if not path:
        return False
    token_patterns = (
        r"(^|/)exhibitions?$",
        r"(^|/)projects?$",
        r"(^|/)category/exhibition$",
        r"(^|/)exhibitions/current$",
        r"(^|/)exhibitions/location/\d+$",
        r"(^|/)ko/exhibitions$",
    )
    return any(re.search(pattern, path) for pattern in token_patterns)


def classify_review_row(
    *,
    row: dict[str, str],
    clean_counts_by_scope: dict[tuple[str, str], int],
) -> tuple[str, str]:
    triage_bucket = str(row.get("triage_bucket") or "").strip()
    join_status = str(row.get("join_status") or "").strip()
    join_basis = str(row.get("join_basis") or "").strip()
    route_quality = str(row.get("route_quality_label") or "").strip()
    year_quality = str(row.get("year_quality_label") or "").strip()
    provenance_suspicious = str(row.get("provenance_suspicious") or "").strip().lower() == "true"
    fair_slug = str(row.get("fair_slug") or "").strip()
    gallery = str(row.get("gallery_name_en") or "").strip()
    source_url = str(row.get("source_url") or "").strip()

    if triage_bucket == "YEAR_REVIEW":
        return YEAR_REVIEW_KEEP, "soft_year_risk_kept_for_controlled_review"

    if triage_bucket == "ROUTE_SOFT_REVIEW":
        return ROUTE_SOFT_REVIEW_KEEP, "soft_route_risk_kept_for_controlled_review"

    if triage_bucket == "TEXT_ONLY_REVIEW":
        clean_in_scope = int(clean_counts_by_scope.get((gallery, fair_slug), 0))
        if (
            join_status == "TEXT_ONLY"
            and join_basis == "no_image_candidate"
            and route_quality == "detail_candidate"
            and year_quality == "pass"
            and not provenance_suspicious
            and _is_listing_like_source(source_url)
            and clean_in_scope > 0
        ):
            return RESOLUTION_CANDIDATE, "listing_like_text_only_with_clean_support"
        return STABLE_TEXT_ONLY_WARNING, "text_only_warning_kept"

    return ESCALATE_CANDIDATE, "unexpected_review_bucket_or_signal"


def main() -> int:
    args = parse_args()
    run_id = args.run_id.strip() or datetime.now(timezone.utc).strftime("task238_%Y%m%dT%H%M%SZ")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    summary237 = read_json(Path(args.task237_summary), default={})
    clean_rows = read_csv(Path(args.task237_clean_csv))
    review_rows = read_csv(Path(args.task237_review_csv))
    coverage_rows = read_csv(Path(args.task236_coverage_review_csv))

    clean_counts_by_scope: dict[tuple[str, str], int] = Counter(
        (str(r.get("gallery_name_en") or "").strip(), str(r.get("fair_slug") or "").strip()) for r in clean_rows
    )

    reclassified_rows: list[dict[str, Any]] = []
    resolution_rows: list[dict[str, Any]] = []
    stable_warning_rows: list[dict[str, Any]] = []
    active_review_rows: list[dict[str, Any]] = []
    escalate_rows: list[dict[str, Any]] = []

    label_counts = Counter()
    by_gallery_label = defaultdict(Counter)
    by_fair_label = defaultdict(Counter)
    text_only_patterns = Counter()
    route_soft_patterns = Counter()
    year_targets = Counter()

    for row in review_rows:
        label, reason = classify_review_row(row=row, clean_counts_by_scope=clean_counts_by_scope)
        out = dict(row)
        out["resolution_label"] = label
        out["resolution_reason"] = reason
        reclassified_rows.append(out)

        gallery = str(row.get("gallery_name_en") or "").strip()
        fair = str(row.get("fair_slug") or "").strip()
        label_counts[label] += 1
        by_gallery_label[(gallery, fair)][label] += 1
        by_fair_label[fair][label] += 1

        if label == RESOLUTION_CANDIDATE:
            resolution_rows.append(out)
            stable_warning_rows.append(out)
        elif label in {STABLE_TEXT_ONLY_WARNING, ROUTE_SOFT_REVIEW_KEEP, YEAR_REVIEW_KEEP}:
            active_review_rows.append(out)
            stable_warning_rows.append(out)
        elif label == ESCALATE_CANDIDATE:
            escalate_rows.append(out)
            active_review_rows.append(out)

        if label in {STABLE_TEXT_ONLY_WARNING, RESOLUTION_CANDIDATE}:
            key = (str(row.get("join_basis") or "").strip(), str(row.get("route_quality_label") or "").strip())
            text_only_patterns[key] += 1
        if label == ROUTE_SOFT_REVIEW_KEEP:
            src = str(row.get("source_url") or "").lower()
            if "/past" in src:
                route_soft_patterns["/past"] += 1
            elif "/upcoming" in src:
                route_soft_patterns["/upcoming"] += 1
            else:
                route_soft_patterns["other_soft_route"] += 1
        if label == YEAR_REVIEW_KEEP:
            year_targets[(fair, gallery)] += 1

    before_review_count = len(review_rows)
    after_review_count = len(active_review_rows)
    compressed_count = int(label_counts.get(RESOLUTION_CANDIDATE, 0))

    counts237 = summary237.get("counts", {})
    join_blockers = int(counts237.get("join_blocker_count", 0))
    reject_count = int(counts237.get("reject_candidate_count", 0))
    coverage_count = len(coverage_rows)

    go_hold = "READY_FOR_REVIEW_QUEUE_PHASE_2"
    if join_blockers > 0 or reject_count > 0:
        go_hold = "HOLD_FOR_INPUT_PATTERN_REVIEW"
    elif int(label_counts.get(ESCALATE_CANDIDATE, 0)) > 0:
        go_hold = "HOLD_FOR_REVIEW_RULE_TUNING"

    summary = {
        "artifact": "exhibitions_text_review_queue_resolution_phase1_summary",
        "task": "TASK238",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "inputs": {
            "task237_summary": str(Path(args.task237_summary)),
            "task237_clean_csv": str(Path(args.task237_clean_csv)),
            "task237_review_csv": str(Path(args.task237_review_csv)),
            "task236_coverage_review_csv": str(Path(args.task236_coverage_review_csv)),
        },
        "precheck": {
            "coverage_review_count": coverage_count,
            "join_blocker_count": join_blockers,
            "reject_candidate_count": reject_count,
        },
        "review_queue_reclassification": {
            "before_review_queue_count": before_review_count,
            "after_review_queue_count": after_review_count,
            "compressed_count": compressed_count,
            "resolution_label_counts": dict(label_counts),
            "by_fair_resolution_counts": {k: dict(v) for k, v in by_fair_label.items()},
        },
        "review_patterns": {
            "text_only_patterns": [
                {"join_basis": key[0], "route_quality_label": key[1], "count": count}
                for key, count in sorted(text_only_patterns.items(), key=lambda x: (-x[1], x[0]))
            ],
            "route_soft_patterns": dict(route_soft_patterns),
            "year_review_targets": [
                {"fair_slug": key[0], "gallery_name_en": key[1], "count": count}
                for key, count in sorted(year_targets.items(), key=lambda x: (-x[1], x[0]))
            ],
            "sources_fallback_usage": {
                "joinable_to_image_by_sources_fallback_count": int(
                    summary237.get("review_patterns", {})
                    .get("image_fallback_usage", {})
                    .get("joinable_to_image_by_sources_fallback_count", 0)
                ),
                "interpretation": "0 indicates fallback was not required in current 10G proposal set, not a contract failure.",
            },
        },
        "policies": {
            "proposal_only": True,
            "formal_untouched": True,
            "adoption_executed": False,
            "rollback_executed": False,
            "join_contract_changed": False,
            "coverage_canonicalization_scope_only": True,
            "coverage_canonicalization_not_used_for_record_identity": True,
            "anti_mixing_enforced": True,
        },
        "go_hold_decision": go_hold,
        "next_task_recommendation": {
            "id": "TASK239",
            "title": "EXHIBITIONS-TEXT-CONTROLLED-REVIEW-QUEUE-RESOLUTION-PHASE-2",
            "ja": "Continue controlled review queue resolution with focused route/year pattern handling",
        },
    }

    summary_path = output_dir / "exhibitions_text_review_queue_resolution_phase1_summary_task238.json"
    table_path = output_dir / "exhibitions_text_review_queue_resolution_phase1_table_task238.csv"
    records_path = output_dir / "exhibitions_text_review_queue_resolution_phase1_records_task238.csv"
    active_review_path = output_dir / "exhibitions_text_scope_review_phase_review_queue_task238.csv"
    stable_warning_path = output_dir / "exhibitions_text_scope_review_phase_stable_warning_task238.csv"
    resolution_path = output_dir / "exhibitions_text_scope_review_phase_resolution_candidates_task238.csv"
    escalate_path = output_dir / "exhibitions_text_scope_review_phase_escalate_candidates_task238.csv"
    manifest_path = output_dir / "exhibitions_text_review_queue_resolution_phase1_manifest_task238.json"
    report_path = output_dir / "exhibitions_text_review_queue_resolution_phase1_task238.md"

    base_fields = [
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
        "resolution_label",
        "resolution_reason",
    ]
    write_csv(records_path, reclassified_rows, base_fields)
    write_csv(active_review_path, active_review_rows, base_fields)
    write_csv(stable_warning_path, stable_warning_rows, base_fields)
    write_csv(resolution_path, resolution_rows, base_fields)
    write_csv(escalate_path, escalate_rows, base_fields)

    table_rows: list[dict[str, Any]] = []
    for (gallery, fair), counts in sorted(by_gallery_label.items(), key=lambda x: (x[0][1], x[0][0])):
        table_rows.append(
            {
                "gallery_name_en": gallery,
                "fair_slug": fair,
                STABLE_TEXT_ONLY_WARNING: int(counts.get(STABLE_TEXT_ONLY_WARNING, 0)),
                ROUTE_SOFT_REVIEW_KEEP: int(counts.get(ROUTE_SOFT_REVIEW_KEEP, 0)),
                YEAR_REVIEW_KEEP: int(counts.get(YEAR_REVIEW_KEEP, 0)),
                RESOLUTION_CANDIDATE: int(counts.get(RESOLUTION_CANDIDATE, 0)),
                ESCALATE_CANDIDATE: int(counts.get(ESCALATE_CANDIDATE, 0)),
            }
        )
    write_csv(
        table_path,
        table_rows,
        [
            "gallery_name_en",
            "fair_slug",
            STABLE_TEXT_ONLY_WARNING,
            ROUTE_SOFT_REVIEW_KEEP,
            YEAR_REVIEW_KEEP,
            RESOLUTION_CANDIDATE,
            ESCALATE_CANDIDATE,
        ],
    )

    write_json(summary_path, summary)

    manifest = {
        "artifact": "exhibitions_text_review_queue_resolution_phase1_manifest",
        "task": "TASK238",
        "run_id": run_id,
        "inputs": summary["inputs"],
        "outputs": {
            "summary_json": str(summary_path),
            "table_csv": str(table_path),
            "records_csv": str(records_path),
            "active_review_queue_csv": str(active_review_path),
            "stable_warning_csv": str(stable_warning_path),
            "resolution_candidates_csv": str(resolution_path),
            "escalate_candidates_csv": str(escalate_path),
            "report_md": str(report_path),
            "manifest_json": str(manifest_path),
        },
        "policies": summary["policies"],
    }
    write_json(manifest_path, manifest)

    report_lines = [
        "# TASK238 Exhibitions Text Controlled Review Queue Resolution Phase 1",
        "",
        "## scope_and_intent",
        "- Target: TASK237 review queue (21 records) only.",
        "- Proposal-only operation; no formal update/adoption/rollback.",
        "",
        "## reclassification",
        f"- before_review_queue_count={before_review_count}",
        f"- after_review_queue_count={after_review_count}",
        f"- compressed_count={compressed_count}",
        f"- resolution_label_counts={dict(label_counts)}",
        "",
        "## minimal_compression_rule",
        "- If triage_bucket=TEXT_ONLY_REVIEW and route/detail/year/provenance are clean,",
        "- and source_url is listing-like, and same fair+gallery has clean pass candidates,",
        "- then mark as RESOLUTION_CANDIDATE and move out of active review queue.",
        "",
        "## guard_integrity",
        f"- coverage_review_count={coverage_count}",
        f"- reject_candidate_count={reject_count}",
        f"- join_blocker_count={join_blockers}",
        "",
        "## decision",
        f"- go_hold_decision={go_hold}",
        "- next_task: TASK239",
    ]
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(
        "[task238] "
        f"before={before_review_count} after={after_review_count} compressed={compressed_count} "
        f"coverage={coverage_count} reject={reject_count} join_blocker={join_blockers} decision={go_hold}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
