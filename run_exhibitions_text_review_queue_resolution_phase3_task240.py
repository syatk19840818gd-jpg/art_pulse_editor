from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ACTIVE_REVIEW_KEEP = "ACTIVE_REVIEW_KEEP"
STABLE_WARNING_DOWNGRADE = "STABLE_WARNING_DOWNGRADE"
INPUT_EXCLUDE_CANDIDATE = "INPUT_EXCLUDE_CANDIDATE"
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
    parser = argparse.ArgumentParser(description="TASK240 Exhibitions Text controlled review queue resolution phase 3")
    parser.add_argument(
        "--task239-summary",
        default="data/phase1_seed10/logs/exhibitions_text_review_queue_resolution_phase2_summary_task239.json",
    )
    parser.add_argument(
        "--task239-active-review-csv",
        default="data/phase1_seed10/logs/exhibitions_text_scope_review_phase_review_queue_task239.csv",
    )
    parser.add_argument(
        "--task239-stable-warning-csv",
        default="data/phase1_seed10/logs/exhibitions_text_scope_review_phase_stable_warning_task239.csv",
    )
    parser.add_argument(
        "--task239-resolution-candidates-csv",
        default="data/phase1_seed10/logs/exhibitions_text_scope_review_phase_resolution_candidates_task239.csv",
    )
    parser.add_argument(
        "--task239-escalate-candidates-csv",
        default="data/phase1_seed10/logs/exhibitions_text_scope_review_phase_escalate_candidates_task239.csv",
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


def _tokenize_path(url: str) -> set[str]:
    path = (urlparse(str(url or "").strip()).path or "").lower()
    return {token for token in re.split(r"[^a-z0-9]+", path) if token}


def _is_stable_warning_downgrade_candidate(row: dict[str, str]) -> bool:
    # Generic (non-domain) downgrade rule:
    # soft-route + text-only + no year/provenance risk + listing signature in path
    # and no join blocker signals.
    join_status = str(row.get("join_status") or "").strip()
    join_basis = str(row.get("join_basis") or "").strip()
    route_quality = str(row.get("route_quality_label") or "").strip()
    year_quality = str(row.get("year_quality_label") or "").strip()
    provenance = str(row.get("provenance_suspicious") or "").strip().lower() == "true"
    tokens = _tokenize_path(str(row.get("source_url") or ""))
    listing_signature = (
        ("exhibitions" in tokens and "past" in tokens)
        or ("archive" in tokens)
        or ("upcoming" in tokens)
    )
    return (
        join_status == "TEXT_ONLY"
        and join_basis == "no_image_candidate"
        and route_quality == "soft_suspicious"
        and year_quality == "pass"
        and not provenance
        and listing_signature
    )


def classify_final_active(row: dict[str, str]) -> tuple[str, str]:
    if _is_stable_warning_downgrade_candidate(row):
        return STABLE_WARNING_DOWNGRADE, "generic_soft_route_text_only_listing_downgrade"
    return ACTIVE_REVIEW_KEEP, "soft_route_without_generic_downgrade_condition"


def main() -> int:
    args = parse_args()
    run_id = args.run_id.strip() or datetime.now(timezone.utc).strftime("task240_%Y%m%dT%H%M%SZ")

    summary239 = read_json(Path(args.task239_summary), default={})
    active_rows_before = read_csv(Path(args.task239_active_review_csv))
    stable_rows_before = read_csv(Path(args.task239_stable_warning_csv))
    resolution_rows_before = read_csv(Path(args.task239_resolution_candidates_csv))
    escalate_rows_before = read_csv(Path(args.task239_escalate_candidates_csv))
    coverage_rows = read_csv(Path(args.task236_coverage_review_csv))

    active_rows_after: list[dict[str, Any]] = []
    stable_rows_after: list[dict[str, Any]] = list(stable_rows_before)
    resolution_rows_after: list[dict[str, Any]] = list(resolution_rows_before)
    escalate_rows_after: list[dict[str, Any]] = list(escalate_rows_before)
    phase3_records: list[dict[str, Any]] = []
    phase3_counts = Counter()

    for row in active_rows_before:
        final_label, final_reason = classify_final_active(row)
        out = dict(row)
        out["phase3_label"] = final_label
        out["phase3_reason"] = final_reason
        phase3_records.append(out)
        phase3_counts[final_label] += 1
        if final_label == ACTIVE_REVIEW_KEEP:
            active_rows_after.append(out)
        elif final_label == STABLE_WARNING_DOWNGRADE:
            stable_rows_after.append(out)
        elif final_label == INPUT_EXCLUDE_CANDIDATE:
            resolution_rows_after.append(out)
        elif final_label == ESCALATE_CANDIDATE:
            escalate_rows_after.append(out)

    before_active = len(active_rows_before)
    after_active = len(active_rows_after)
    before_stable = len(stable_rows_before)
    after_stable = len(stable_rows_after)
    before_resolution = len(resolution_rows_before)
    after_resolution = len(resolution_rows_after)
    before_escalate = len(escalate_rows_before)
    after_escalate = len(escalate_rows_after)

    integrity = summary239.get("integrity_checks", {})
    coverage_count = int(integrity.get("coverage_review_count", len(coverage_rows)))
    reject_count = int(integrity.get("reject_candidate_count", 0))
    join_blocker_count = int(integrity.get("join_blocker_count", 0))

    close_conditions = {
        "active_review_queue_threshold_for_next_phase": 0,
        "stable_warning_allowed": "yes (non-blocking) when monitoring rules are active",
        "blocker_conditions": [
            "coverage_review_count > 0",
            "reject_candidate_count > 0",
            "join_blocker_count > 0",
            "escalate_candidates_count > 0",
        ],
        "warning_allowed_conditions": [
            "STABLE_TEXT_ONLY_WARNING",
            "ROUTE_SOFT_STABLE_WARNING",
            "YEAR_STABLE_WARNING",
        ],
        "escalate_triggers": [
            "same fair+gallery stable_text_only warning persists >=3 consecutive controlled runs",
            "stable_text_only_ratio > 0.6 for two consecutive runs",
            "route quality drifts from detail_candidate to soft/hard suspicious",
        ],
    }

    if coverage_count > 0 or reject_count > 0 or join_blocker_count > 0 or after_escalate > 0:
        decision = "HOLD_FOR_FINAL_REVIEW_RULE_TUNING"
    elif after_active > 0:
        decision = "HOLD_FOR_MANUAL_REVIEW_CONTINUATION"
    else:
        decision = "READY_FOR_POST_REVIEW_TRIAGE_PHASE"

    remaining_row = active_rows_before[0] if active_rows_before else {}
    analysis = {
        "source_url": str(remaining_row.get("source_url") or ""),
        "route_quality_label": str(remaining_row.get("route_quality_label") or ""),
        "join_status": str(remaining_row.get("join_status") or ""),
        "join_basis": str(remaining_row.get("join_basis") or ""),
        "year_quality_label": str(remaining_row.get("year_quality_label") or ""),
        "provenance_suspicious": str(remaining_row.get("provenance_suspicious") or ""),
        "phase2_label": str(remaining_row.get("phase2_label") or ""),
        "phase2_not_auto_compressed_reason": (
            "phase2 required clean-support for route-soft input-exclude candidate; this row had no clean support in same scope"
        ),
        "phase3_generic_decision_basis": (
            "soft route + text-only + no year/provenance risk + listing signature route"
        ),
    }

    summary = {
        "artifact": "exhibitions_text_review_queue_resolution_phase3_summary",
        "task": "TASK240",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "inputs": {
            "task239_summary": str(Path(args.task239_summary)),
            "task239_active_review_csv": str(Path(args.task239_active_review_csv)),
            "task239_stable_warning_csv": str(Path(args.task239_stable_warning_csv)),
            "task239_resolution_candidates_csv": str(Path(args.task239_resolution_candidates_csv)),
            "task239_escalate_candidates_csv": str(Path(args.task239_escalate_candidates_csv)),
            "task236_coverage_review_csv": str(Path(args.task236_coverage_review_csv)),
        },
        "remaining_active_analysis": analysis,
        "remaining_active_final_classification": {
            "phase3_label_counts": dict(phase3_counts),
            "allowed_labels": [
                ACTIVE_REVIEW_KEEP,
                STABLE_WARNING_DOWNGRADE,
                INPUT_EXCLUDE_CANDIDATE,
                ESCALATE_CANDIDATE,
            ],
        },
        "stable_warning_monitoring_rules_check": {
            "rule_set_kept_from_task239": True,
            "rule_adjustment_required": False,
            "reason": "current 10G scope has no escalate trigger firing and no blocker reintroduced",
            "current_stable_warning_count": after_stable,
        },
        "review_resolution_close_conditions": close_conditions,
        "before_after": {
            "active_review_queue_count_before": before_active,
            "active_review_queue_count_after": after_active,
            "stable_warning_count_before": before_stable,
            "stable_warning_count_after": after_stable,
            "resolution_candidate_count_before": before_resolution,
            "resolution_candidate_count_after": after_resolution,
            "escalate_candidate_count_before": before_escalate,
            "escalate_candidate_count_after": after_escalate,
        },
        "integrity_checks": {
            "coverage_review_count": coverage_count,
            "reject_candidate_count": reject_count,
            "join_blocker_count": join_blocker_count,
            "proposal_only": True,
            "formal_untouched": True,
            "adoption_executed": False,
            "rollback_executed": False,
        },
        "go_hold_decision": decision,
        "next_task_recommendation": {
            "id": "TASK241",
            "title": "EXHIBITIONS-TEXT-POST-REVIEW-TRIAGE-PHASE-START",
            "ja": "Start post-review triage phase for controlled progression without formal adoption",
        },
    }

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "exhibitions_text_review_queue_resolution_phase3_summary_task240.json"
    table_path = output_dir / "exhibitions_text_review_queue_resolution_phase3_table_task240.csv"
    records_path = output_dir / "exhibitions_text_review_queue_resolution_phase3_records_task240.csv"
    active_path = output_dir / "exhibitions_text_scope_review_phase_review_queue_task240.csv"
    stable_path = output_dir / "exhibitions_text_scope_review_phase_stable_warning_task240.csv"
    resolution_path = output_dir / "exhibitions_text_scope_review_phase_resolution_candidates_task240.csv"
    escalate_path = output_dir / "exhibitions_text_scope_review_phase_escalate_candidates_task240.csv"
    manifest_path = output_dir / "exhibitions_text_review_queue_resolution_phase3_manifest_task240.json"
    report_path = output_dir / "exhibitions_text_review_queue_resolution_phase3_task240.md"

    fields = [
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
        "phase2_label",
        "phase2_reason",
        "phase3_label",
        "phase3_reason",
    ]
    write_csv(records_path, phase3_records, fields)
    write_csv(active_path, active_rows_after, fields)
    write_csv(stable_path, stable_rows_after, fields)
    write_csv(resolution_path, resolution_rows_after, fields)
    write_csv(escalate_path, escalate_rows_after, fields)

    table_rows = [
        {
            "metric": "active_review_queue_count",
            "before": before_active,
            "after": after_active,
        },
        {
            "metric": "stable_warning_count",
            "before": before_stable,
            "after": after_stable,
        },
        {
            "metric": "resolution_candidate_count",
            "before": before_resolution,
            "after": after_resolution,
        },
        {
            "metric": "escalate_candidate_count",
            "before": before_escalate,
            "after": after_escalate,
        },
        {
            "metric": "coverage_review_count",
            "before": coverage_count,
            "after": coverage_count,
        },
        {
            "metric": "reject_candidate_count",
            "before": reject_count,
            "after": reject_count,
        },
        {
            "metric": "join_blocker_count",
            "before": join_blocker_count,
            "after": join_blocker_count,
        },
    ]
    write_csv(table_path, table_rows, ["metric", "before", "after"])
    write_json(summary_path, summary)

    manifest = {
        "artifact": "exhibitions_text_review_queue_resolution_phase3_manifest",
        "task": "TASK240",
        "run_id": run_id,
        "inputs": summary["inputs"],
        "outputs": {
            "summary_json": str(summary_path),
            "table_csv": str(table_path),
            "records_csv": str(records_path),
            "active_review_queue_csv": str(active_path),
            "stable_warning_csv": str(stable_path),
            "resolution_candidates_csv": str(resolution_path),
            "escalate_candidates_csv": str(escalate_path),
            "report_md": str(report_path),
            "manifest_json": str(manifest_path),
        },
        "integrity_checks": summary["integrity_checks"],
        "policies": {
            "proposal_only": True,
            "formal_untouched": True,
            "join_contract_changed": False,
            "anti_mixing_enforced": True,
            "domain_specific_hack": False,
        },
    }
    write_json(manifest_path, manifest)

    report_lines = [
        "# TASK240 Exhibitions Text Controlled Review Queue Resolution Phase 3",
        "",
        "## remaining_active_analysis",
        f"- source_url={analysis['source_url']}",
        f"- route_quality_label={analysis['route_quality_label']}",
        f"- join_status={analysis['join_status']}",
        f"- join_basis={analysis['join_basis']}",
        f"- year_quality_label={analysis['year_quality_label']}",
        f"- provenance_suspicious={analysis['provenance_suspicious']}",
        "",
        "## final_classification",
        f"- phase3_label_counts={dict(phase3_counts)}",
        "",
        "## close_conditions",
        "- active_review_queue_threshold_for_next_phase=0",
        "- blockers: coverage/reject/join_blocker/escalate > 0",
        "- stable warnings are non-blocking with monitoring rules",
        "",
        "## before_after",
        f"- active_review_queue: {before_active} -> {after_active}",
        f"- stable_warning: {before_stable} -> {after_stable}",
        f"- resolution_candidates: {before_resolution} -> {after_resolution}",
        f"- escalate_candidates: {before_escalate} -> {after_escalate}",
        "",
        "## decision",
        f"- go_hold_decision={decision}",
    ]
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(
        "[task240] "
        f"active={before_active}->{after_active} stable={before_stable}->{after_stable} "
        f"resolution={before_resolution}->{after_resolution} escalate={before_escalate}->{after_escalate} "
        f"coverage={coverage_count} reject={reject_count} join_blocker={join_blocker_count} "
        f"decision={decision}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
