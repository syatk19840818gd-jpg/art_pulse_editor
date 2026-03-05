from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CLEAN_BUCKET = "CLEAN_PASS_CANDIDATE"
REVIEW_BUCKETS = {"TEXT_ONLY_REVIEW", "ROUTE_SOFT_REVIEW", "YEAR_REVIEW"}
REJECT_BUCKET = "REJECT_CANDIDATE"


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
    parser = argparse.ArgumentParser(description="TASK237 Exhibitions Text scope review phase controlled start")
    parser.add_argument(
        "--task236-summary",
        default="data/phase1_seed10/logs/exhibitions_text_coverage_normalization_summary_task236.json",
    )
    parser.add_argument(
        "--task236-triage-records",
        default="data/phase1_seed10/logs/exhibitions_text_scope_review_gate_triage_records_task236.csv",
    )
    parser.add_argument(
        "--task236-coverage-review",
        default="data/phase1_seed10/logs/exhibitions_text_scope_review_gate_coverage_review_task236.csv",
    )
    parser.add_argument(
        "--task236-scope-manifest",
        default="data/phase1_seed10/logs/task_t236_controlled_scope_10g_manifest.json",
    )
    parser.add_argument(
        "--output-dir",
        default="data/phase1_seed10/logs",
    )
    parser.add_argument("--run-id", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_id = args.run_id.strip() or datetime.now(timezone.utc).strftime("task237_%Y%m%dT%H%M%SZ")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    task236_summary = read_json(Path(args.task236_summary), default={})
    scope_manifest = read_json(Path(args.task236_scope_manifest), default={})
    triage_rows = read_csv(Path(args.task236_triage_records))
    coverage_rows = read_csv(Path(args.task236_coverage_review))

    clean_rows: list[dict[str, Any]] = []
    review_rows: list[dict[str, Any]] = []
    reject_rows: list[dict[str, Any]] = []

    triage_counts = Counter()
    by_gallery = defaultdict(Counter)
    by_fair = defaultdict(Counter)
    text_only_patterns = Counter()
    route_soft_patterns = Counter()
    year_review_targets = Counter()

    for row in triage_rows:
        bucket = str(row.get("triage_bucket") or "").strip()
        triage_counts[bucket] += 1
        gallery = str(row.get("gallery_name_en") or "").strip()
        fair = str(row.get("fair_slug") or "").strip()
        by_gallery[(gallery, fair)][bucket] += 1
        by_fair[fair][bucket] += 1

        if bucket == CLEAN_BUCKET:
            clean_rows.append(row)
        elif bucket in REVIEW_BUCKETS:
            review_rows.append(row)
            if bucket == "TEXT_ONLY_REVIEW":
                key = (
                    str(row.get("join_basis") or "").strip(),
                    str(row.get("route_quality_label") or "").strip(),
                )
                text_only_patterns[key] += 1
            elif bucket == "ROUTE_SOFT_REVIEW":
                src = str(row.get("source_url") or "").lower()
                if "/past" in src:
                    route_soft_patterns["/past"] += 1
                elif "/upcoming" in src:
                    route_soft_patterns["/upcoming"] += 1
                else:
                    route_soft_patterns["other_soft_route"] += 1
            elif bucket == "YEAR_REVIEW":
                year_review_targets[(fair, gallery)] += 1
        elif bucket == REJECT_BUCKET:
            reject_rows.append(row)

    coverage_review_count = len(coverage_rows)
    join_blockers = int(
        task236_summary.get("proposal_summary_excerpt", {}).get("ambiguous_join_count", 0)
        + task236_summary.get("proposal_summary_excerpt", {}).get("duplicate_join_group_count", 0)
        + task236_summary.get("proposal_summary_excerpt", {}).get("image_text_mismatch_count", 0)
    )
    reject_count = int(triage_counts.get(REJECT_BUCKET, 0))

    # Controlled scope review phase go/no-go
    # Blockers: coverage/reject/join blockers
    blocker_labels: list[str] = []
    if coverage_review_count > 0:
        blocker_labels.append("COVERAGE_REVIEW_REMAINING")
    if reject_count > 0:
        blocker_labels.append("REJECT_CANDIDATE_PRESENT")
    if join_blockers > 0:
        blocker_labels.append("JOIN_BLOCKER_PRESENT")

    # Warnings are operable in controlled phase.
    warning_labels: list[str] = []
    if triage_counts.get("TEXT_ONLY_REVIEW", 0) > 0:
        warning_labels.append("TEXT_ONLY_REVIEW_PRESENT")
    if triage_counts.get("ROUTE_SOFT_REVIEW", 0) > 0:
        warning_labels.append("ROUTE_SOFT_REVIEW_PRESENT")
    if triage_counts.get("YEAR_REVIEW", 0) > 0:
        warning_labels.append("YEAR_REVIEW_PRESENT")

    go_hold = "GO"
    phase_status = "READY_FOR_CONTROLLED_SCOPE_REVIEW_CONTINUATION"
    if blocker_labels:
        go_hold = "HOLD"
        phase_status = "HOLD_FOR_SCOPE_REVIEW_ALIGNMENT"

    # Candidate rule for future 03/04 sync mention (not updating docs in this task):
    sync_candidate = (
        not blocker_labels
        and int(triage_counts.get("YEAR_REVIEW", 0)) == 0
        and int(triage_counts.get("ROUTE_SOFT_REVIEW", 0)) == 0
        and int(triage_counts.get("TEXT_ONLY_REVIEW", 0)) == 0
    )

    records_total = len(triage_rows)
    clean_count = len(clean_rows)
    review_count = len(review_rows)

    summary = {
        "artifact": "exhibitions_text_scope_review_phase_start_summary",
        "task": "TASK237",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "scope_hash": str(scope_manifest.get("scope_hash") or ""),
        "input_artifacts": {
            "task236_summary": str(Path(args.task236_summary)),
            "task236_triage_records": str(Path(args.task236_triage_records)),
            "task236_coverage_review": str(Path(args.task236_coverage_review)),
            "task236_scope_manifest": str(Path(args.task236_scope_manifest)),
        },
        "counts": {
            "records_total": records_total,
            "clean_pass_candidate_count": clean_count,
            "review_queue_count": review_count,
            "reject_candidate_count": reject_count,
            "coverage_review_count": coverage_review_count,
            "join_blocker_count": join_blockers,
            "triage_bucket_counts": dict(triage_counts),
            "by_fair_bucket_counts": {k: dict(v) for k, v in by_fair.items()},
        },
        "review_patterns": {
            "text_only_main_patterns": [
                {"join_basis": key[0], "route_quality_label": key[1], "count": count}
                for key, count in sorted(text_only_patterns.items(), key=lambda x: (-x[1], x[0]))
            ],
            "route_soft_main_patterns": dict(route_soft_patterns),
            "year_review_targets": [
                {"fair_slug": k[0], "gallery_name_en": k[1], "count": v}
                for k, v in sorted(year_review_targets.items(), key=lambda x: (-x[1], x[0]))
            ],
            "image_fallback_usage": {
                "joinable_to_image_by_sources_fallback_count": int(
                    task236_summary.get("proposal_summary_excerpt", {}).get(
                        "joinable_to_image_by_sources_fallback_count", 0
                    )
                )
            },
        },
        "controlled_review_gate": {
            "go_hold": go_hold,
            "phase_status": phase_status,
            "blocker_labels": blocker_labels,
            "warning_labels": warning_labels,
            "continuation_rules": {
                "continue_when": "coverage_review_count=0 AND reject_candidate_count=0 AND join_blocker_count=0",
                "blocker_when": "coverage_review_count>0 OR reject_candidate_count>0 OR join_blocker_count>0",
                "warnings_operable_in_controlled_phase": [
                    "TEXT_ONLY_REVIEW",
                    "ROUTE_SOFT_REVIEW",
                    "YEAR_REVIEW",
                ],
                "doc_sync_candidate_condition_only": "all review buckets resolved to 0 and blockers remain 0 (document update not executed in TASK237)",
            },
        },
        "policies": {
            "proposal_only": True,
            "formal_untouched": True,
            "adoption_executed": False,
            "rollback_executed": False,
            "join_contract_changed": False,
            "anti_mixing_enforced": True,
            "coverage_canonicalization_scope_only": True,
            "coverage_canonicalization_not_used_for_record_identity": True,
        },
        "next_task_recommendation": {
            "id": "TASK238",
            "title": "EXHIBITIONS-TEXT-CONTROLLED-REVIEW-QUEUE-RESOLUTION-PHASE-1",
            "ja": "Start controlled review queue resolution (text_only / route_soft / year) without formal adoption",
        },
        "sync_candidate_condition_met_now": bool(sync_candidate),
    }

    clean_path = output_dir / "exhibitions_text_scope_review_phase_clean_pass_candidates_task237.csv"
    review_path = output_dir / "exhibitions_text_scope_review_phase_review_queue_task237.csv"
    reject_path = output_dir / "exhibitions_text_scope_review_phase_reject_candidates_task237.csv"
    table_path = output_dir / "exhibitions_text_scope_review_phase_table_task237.csv"
    summary_path = output_dir / "exhibitions_text_scope_review_phase_summary_task237.json"
    manifest_path = output_dir / "exhibitions_text_scope_review_phase_manifest_task237.json"
    report_path = output_dir / "exhibitions_text_scope_review_phase_task237.md"

    record_fields = [
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
    ]
    write_csv(clean_path, clean_rows, record_fields)
    write_csv(review_path, review_rows, record_fields)
    write_csv(reject_path, reject_rows, record_fields)

    table_rows: list[dict[str, Any]] = []
    for (gallery, fair), counts in sorted(by_gallery.items(), key=lambda x: (x[0][1], x[0][0])):
        table_rows.append(
            {
                "gallery_name_en": gallery,
                "fair_slug": fair,
                CLEAN_BUCKET: int(counts.get(CLEAN_BUCKET, 0)),
                "TEXT_ONLY_REVIEW": int(counts.get("TEXT_ONLY_REVIEW", 0)),
                "ROUTE_SOFT_REVIEW": int(counts.get("ROUTE_SOFT_REVIEW", 0)),
                "YEAR_REVIEW": int(counts.get("YEAR_REVIEW", 0)),
                REJECT_BUCKET: int(counts.get(REJECT_BUCKET, 0)),
            }
        )
    write_csv(
        table_path,
        table_rows,
        [
            "gallery_name_en",
            "fair_slug",
            CLEAN_BUCKET,
            "TEXT_ONLY_REVIEW",
            "ROUTE_SOFT_REVIEW",
            "YEAR_REVIEW",
            REJECT_BUCKET,
        ],
    )

    write_json(summary_path, summary)
    manifest = {
        "artifact": "exhibitions_text_scope_review_phase_manifest",
        "task": "TASK237",
        "run_id": run_id,
        "inputs": summary["input_artifacts"],
        "outputs": {
            "summary_json": str(summary_path),
            "table_csv": str(table_path),
            "clean_pass_candidates_csv": str(clean_path),
            "review_queue_csv": str(review_path),
            "reject_candidates_csv": str(reject_path),
            "report_md": str(report_path),
            "manifest_json": str(manifest_path),
        },
        "policies": summary["policies"],
    }
    write_json(manifest_path, manifest)

    report_lines = [
        "# TASK237 Exhibitions Text Scope Review Phase Controlled Start",
        "",
        "## scope_review_phase_definition",
        "- CLEAN_PASS_CANDIDATE: next controlled phase carry-forward candidate.",
        "- TEXT_ONLY_REVIEW: no image candidate but text record valid; review queue.",
        "- ROUTE_SOFT_REVIEW: soft route risk (`/past`, `/upcoming`) review queue.",
        "- YEAR_REVIEW: soft year risk review queue.",
        "- REJECT_CANDIDATE: blocker queue (none in this run).",
        "",
        "## counts",
        f"- records_total={records_total}",
        f"- clean_pass_candidate_count={clean_count}",
        f"- review_queue_count={review_count}",
        f"- reject_candidate_count={reject_count}",
        f"- coverage_review_count={coverage_review_count}",
        "",
        "## gate",
        f"- go_hold={go_hold}",
        f"- phase_status={phase_status}",
        f"- blocker_labels={blocker_labels}",
        f"- warning_labels={warning_labels}",
        "",
        "## recommended_next_task",
        f"- id={summary['next_task_recommendation']['id']}",
        f"- title={summary['next_task_recommendation']['title']}",
        f"- ja={summary['next_task_recommendation']['ja']}",
    ]
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(
        "[task237] "
        f"records={records_total} clean={clean_count} review={review_count} reject={reject_count} "
        f"coverage={coverage_review_count} join_blocker={join_blockers} go_hold={go_hold}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
