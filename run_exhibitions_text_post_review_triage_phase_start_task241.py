from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY_CARRY_FORWARD = "READY_CARRY_FORWARD"
MONITORED_STABLE_WARNING = "MONITORED_STABLE_WARNING"
RESOLUTION_HOLDING = "RESOLUTION_HOLDING"
ESCALATE_WATCH = "ESCALATE_WATCH"
REJECT_CANDIDATE = "REJECT_CANDIDATE"


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
    parser = argparse.ArgumentParser(description="TASK241 Exhibitions Text post-review triage phase start")
    parser.add_argument(
        "--task240-summary",
        default="data/phase1_seed10/logs/exhibitions_text_review_queue_resolution_phase3_summary_task240.json",
    )
    parser.add_argument(
        "--clean-pass-csv",
        default="data/phase1_seed10/logs/exhibitions_text_scope_review_phase_clean_pass_candidates_task237.csv",
    )
    parser.add_argument(
        "--stable-warning-csv",
        default="data/phase1_seed10/logs/exhibitions_text_scope_review_phase_stable_warning_task240.csv",
    )
    parser.add_argument(
        "--resolution-candidates-csv",
        default="data/phase1_seed10/logs/exhibitions_text_scope_review_phase_resolution_candidates_task240.csv",
    )
    parser.add_argument(
        "--escalate-candidates-csv",
        default="data/phase1_seed10/logs/exhibitions_text_scope_review_phase_escalate_candidates_task240.csv",
    )
    parser.add_argument(
        "--reject-candidates-csv",
        default="data/phase1_seed10/logs/exhibitions_text_scope_review_phase_reject_candidates_task237.csv",
    )
    parser.add_argument(
        "--active-review-csv",
        default="data/phase1_seed10/logs/exhibitions_text_scope_review_phase_review_queue_task240.csv",
    )
    parser.add_argument("--output-dir", default="data/phase1_seed10/logs")
    parser.add_argument("--run-id", default="")
    return parser.parse_args()


def _classify_route_soft_pattern(source_url: str) -> str:
    lower_url = str(source_url or "").lower()
    if "/past" in lower_url:
        return "/past"
    if "/upcoming" in lower_url:
        return "/upcoming"
    if "/archive" in lower_url:
        return "/archive"
    return "other_soft_route"


def _to_post_review_rows(
    rows: list[dict[str, str]],
    bucket: str,
    reason: str,
    source_stream: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["post_review_bucket"] = bucket
        item["post_review_reason"] = reason
        item["source_stream"] = source_stream
        out.append(item)
    return out


def main() -> int:
    args = parse_args()
    run_id = args.run_id.strip() or datetime.now(timezone.utc).strftime("task241_%Y%m%dT%H%M%SZ")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    summary240 = read_json(Path(args.task240_summary), default={})
    clean_rows = read_csv(Path(args.clean_pass_csv))
    stable_rows = read_csv(Path(args.stable_warning_csv))
    resolution_rows = read_csv(Path(args.resolution_candidates_csv))
    escalate_rows = read_csv(Path(args.escalate_candidates_csv))
    reject_rows = read_csv(Path(args.reject_candidates_csv))
    active_rows = read_csv(Path(args.active_review_csv))

    ready_rows = _to_post_review_rows(
        clean_rows,
        READY_CARRY_FORWARD,
        "clean_pass_candidate_without_blocker",
        "clean_pass_candidates",
    )
    monitored_rows = _to_post_review_rows(
        stable_rows,
        MONITORED_STABLE_WARNING,
        "stable_warning_requires_continuous_monitoring",
        "stable_warning",
    )
    holding_rows = _to_post_review_rows(
        resolution_rows,
        RESOLUTION_HOLDING,
        "resolution_candidate_kept_as_proposal_holding_set",
        "resolution_candidates",
    )
    watch_rows = _to_post_review_rows(
        escalate_rows,
        ESCALATE_WATCH,
        "escalate_watch_condition_monitoring",
        "escalate_candidates",
    )
    rejected_rows = _to_post_review_rows(
        reject_rows,
        REJECT_CANDIDATE,
        "reject_candidate_blocker",
        "reject_candidates",
    )

    all_rows = ready_rows + monitored_rows + holding_rows + watch_rows + rejected_rows
    bucket_counts = Counter(str(row.get("post_review_bucket") or "") for row in all_rows)

    by_fair = defaultdict(Counter)
    by_gallery = defaultdict(Counter)
    for row in all_rows:
        fair = str(row.get("fair_slug") or "").strip()
        gallery = str(row.get("gallery_name_en") or "").strip()
        bucket = str(row.get("post_review_bucket") or "").strip()
        by_fair[fair][bucket] += 1
        by_gallery[(gallery, fair)][bucket] += 1

    monitored_text_only_count = sum(
        1
        for row in monitored_rows
        if str(row.get("join_status") or "").strip() == "TEXT_ONLY"
        or str(row.get("join_basis") or "").strip() == "no_image_candidate"
    )
    monitored_route_soft_count = sum(
        1 for row in monitored_rows if str(row.get("route_quality_label") or "").strip() == "soft_suspicious"
    )
    monitored_year_warning_count = sum(
        1 for row in monitored_rows if str(row.get("year_quality_label") or "").strip() != "pass"
    )
    monitored_route_soft_patterns = Counter(
        _classify_route_soft_pattern(str(row.get("source_url") or ""))
        for row in monitored_rows
        if str(row.get("route_quality_label") or "").strip() == "soft_suspicious"
    )

    ready_count = len(ready_rows)
    monitored_count = len(monitored_rows)
    holding_count = len(holding_rows)
    watch_count = len(watch_rows)
    reject_count = len(rejected_rows)

    denominator = ready_count + holding_count
    clean_resolution_ratio = round(ready_count / denominator, 6) if denominator > 0 else 0.0

    integrity = summary240.get("integrity_checks", {})
    coverage_review_count = int(integrity.get("coverage_review_count", 0))
    join_blocker_count = int(integrity.get("join_blocker_count", 0))
    reject_from_integrity = int(integrity.get("reject_candidate_count", 0))
    reject_blocker_count = max(reject_count, reject_from_integrity)

    blocker_labels: list[str] = []
    if coverage_review_count > 0:
        blocker_labels.append("COVERAGE_REVIEW_PRESENT")
    if join_blocker_count > 0:
        blocker_labels.append("JOIN_BLOCKER_PRESENT")
    if reject_blocker_count > 0:
        blocker_labels.append("REJECT_CANDIDATE_PRESENT")

    warning_labels: list[str] = []
    if monitored_count > 0:
        warning_labels.append("MONITORED_STABLE_WARNING_PRESENT")
    if watch_count > 0:
        warning_labels.append("ESCALATE_WATCH_PRESENT")

    if blocker_labels:
        decision = "HOLD_FOR_TRIAGE_RULE_TUNING"
    elif watch_count > 0:
        decision = "HOLD_FOR_WARNING_POLICY_REVIEW"
    else:
        decision = "READY_FOR_CONTROLLED_CARRY_FORWARD_PHASE"

    summary = {
        "artifact": "exhibitions_text_post_review_triage_phase_start_summary",
        "task": "TASK241",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "inputs": {
            "task240_summary": str(Path(args.task240_summary)),
            "clean_pass_csv": str(Path(args.clean_pass_csv)),
            "stable_warning_csv": str(Path(args.stable_warning_csv)),
            "resolution_candidates_csv": str(Path(args.resolution_candidates_csv)),
            "escalate_candidates_csv": str(Path(args.escalate_candidates_csv)),
            "reject_candidates_csv": str(Path(args.reject_candidates_csv)),
            "active_review_csv": str(Path(args.active_review_csv)),
        },
        "precheck": {
            "active_review_queue_count_task240": len(active_rows),
            "coverage_review_count": coverage_review_count,
            "join_blocker_count": join_blocker_count,
            "reject_candidate_count": reject_blocker_count,
        },
        "post_review_triage_buckets": {
            READY_CARRY_FORWARD: ready_count,
            MONITORED_STABLE_WARNING: monitored_count,
            RESOLUTION_HOLDING: holding_count,
            ESCALATE_WATCH: watch_count,
            REJECT_CANDIDATE: reject_count,
            "records_total": len(all_rows),
        },
        "aggregates": {
            "by_fair_bucket_counts": {key: dict(value) for key, value in by_fair.items()},
            "by_gallery_bucket_counts": {
                f"{key[0]}|{key[1]}": dict(value) for key, value in by_gallery.items()
            },
            "text_only_remaining_count": monitored_text_only_count,
            "route_soft_warning_count": monitored_route_soft_count,
            "year_warning_count": monitored_year_warning_count,
            "route_soft_warning_patterns": dict(monitored_route_soft_patterns),
            "clean_pass_to_resolution_holding_ratio": clean_resolution_ratio,
        },
        "carry_forward_policy": {
            READY_CARRY_FORWARD: {
                "carry_allowed": True,
                "condition": "coverage_review=0 AND join_blocker=0 AND reject_candidate=0",
            },
            MONITORED_STABLE_WARNING: {
                "carry_allowed": True,
                "condition": "non-blocking warning with monitoring rules from TASK239/TASK240",
            },
            RESOLUTION_HOLDING: {
                "carry_allowed": "deferred",
                "condition": "revisit on phase boundary or when warning trend worsens",
            },
            ESCALATE_WATCH: {
                "carry_allowed": False,
                "condition": "watch_count>0 triggers warning-policy hold",
                "becomes_blocker_when": [
                    "persisting >=3 controlled runs",
                    "stable_text_only_ratio > 0.6 for two runs",
                    "route quality degradation trend",
                ],
            },
            REJECT_CANDIDATE: {
                "carry_allowed": False,
                "condition": "always blocker until resolved in proposal scope",
            },
        },
        "go_hold_decision": decision,
        "blocker_labels": blocker_labels,
        "warning_labels": warning_labels,
        "policies": {
            "proposal_only": True,
            "formal_untouched": True,
            "adoption_executed": False,
            "rollback_executed": False,
            "join_contract_changed": False,
            "year_filter_redesigned": False,
            "quality_gate_redesigned": False,
            "anti_mixing_enforced": True,
            "domain_specific_hack": False,
        },
        "next_task_recommendation": {
            "id": "TASK242",
            "title": "EXHIBITIONS-TEXT-CONTROLLED-CARRY-FORWARD-PHASE-START",
            "ja": "Start controlled carry-forward processing for READY_CARRY_FORWARD while monitoring warning buckets",
        },
    }

    summary_path = output_dir / "exhibitions_text_post_review_triage_phase_start_summary_task241.json"
    table_path = output_dir / "exhibitions_text_post_review_triage_phase_start_table_task241.csv"
    fair_table_path = output_dir / "exhibitions_text_post_review_triage_phase_start_by_fair_task241.csv"
    records_path = output_dir / "exhibitions_text_post_review_triage_phase_records_task241.csv"
    ready_path = output_dir / "exhibitions_text_post_review_ready_carry_forward_task241.csv"
    monitored_path = output_dir / "exhibitions_text_post_review_monitored_stable_warning_task241.csv"
    holding_path = output_dir / "exhibitions_text_post_review_resolution_holding_task241.csv"
    watch_path = output_dir / "exhibitions_text_post_review_escalate_watch_task241.csv"
    reject_path = output_dir / "exhibitions_text_post_review_reject_candidates_task241.csv"
    manifest_path = output_dir / "exhibitions_text_post_review_triage_phase_start_manifest_task241.json"
    report_path = output_dir / "exhibitions_text_post_review_triage_phase_start_task241.md"

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
        "resolution_label",
        "resolution_reason",
        "phase2_label",
        "phase2_reason",
        "phase3_label",
        "phase3_reason",
        "post_review_bucket",
        "post_review_reason",
        "source_stream",
    ]
    write_csv(records_path, all_rows, record_fields)
    write_csv(ready_path, ready_rows, record_fields)
    write_csv(monitored_path, monitored_rows, record_fields)
    write_csv(holding_path, holding_rows, record_fields)
    write_csv(watch_path, watch_rows, record_fields)
    write_csv(reject_path, rejected_rows, record_fields)

    table_rows: list[dict[str, Any]] = []
    for (gallery, fair), counts in sorted(by_gallery.items(), key=lambda x: (x[0][1], x[0][0])):
        table_rows.append(
            {
                "gallery_name_en": gallery,
                "fair_slug": fair,
                READY_CARRY_FORWARD: int(counts.get(READY_CARRY_FORWARD, 0)),
                MONITORED_STABLE_WARNING: int(counts.get(MONITORED_STABLE_WARNING, 0)),
                RESOLUTION_HOLDING: int(counts.get(RESOLUTION_HOLDING, 0)),
                ESCALATE_WATCH: int(counts.get(ESCALATE_WATCH, 0)),
                REJECT_CANDIDATE: int(counts.get(REJECT_CANDIDATE, 0)),
            }
        )
    write_csv(
        table_path,
        table_rows,
        [
            "gallery_name_en",
            "fair_slug",
            READY_CARRY_FORWARD,
            MONITORED_STABLE_WARNING,
            RESOLUTION_HOLDING,
            ESCALATE_WATCH,
            REJECT_CANDIDATE,
        ],
    )

    fair_rows: list[dict[str, Any]] = []
    for fair, counts in sorted(by_fair.items(), key=lambda x: x[0]):
        fair_rows.append(
            {
                "fair_slug": fair,
                READY_CARRY_FORWARD: int(counts.get(READY_CARRY_FORWARD, 0)),
                MONITORED_STABLE_WARNING: int(counts.get(MONITORED_STABLE_WARNING, 0)),
                RESOLUTION_HOLDING: int(counts.get(RESOLUTION_HOLDING, 0)),
                ESCALATE_WATCH: int(counts.get(ESCALATE_WATCH, 0)),
                REJECT_CANDIDATE: int(counts.get(REJECT_CANDIDATE, 0)),
            }
        )
    write_csv(
        fair_table_path,
        fair_rows,
        [
            "fair_slug",
            READY_CARRY_FORWARD,
            MONITORED_STABLE_WARNING,
            RESOLUTION_HOLDING,
            ESCALATE_WATCH,
            REJECT_CANDIDATE,
        ],
    )

    write_json(summary_path, summary)
    manifest = {
        "artifact": "exhibitions_text_post_review_triage_phase_start_manifest",
        "task": "TASK241",
        "run_id": run_id,
        "inputs": summary["inputs"],
        "outputs": {
            "summary_json": str(summary_path),
            "table_csv": str(table_path),
            "fair_table_csv": str(fair_table_path),
            "records_csv": str(records_path),
            "ready_carry_forward_csv": str(ready_path),
            "monitored_stable_warning_csv": str(monitored_path),
            "resolution_holding_csv": str(holding_path),
            "escalate_watch_csv": str(watch_path),
            "reject_candidates_csv": str(reject_path),
            "report_md": str(report_path),
            "manifest_json": str(manifest_path),
        },
        "policies": summary["policies"],
    }
    write_json(manifest_path, manifest)

    report_lines = [
        "# TASK241 Exhibitions Text Post-Review Triage Phase Start",
        "",
        "## bucket_definition",
        f"- {READY_CARRY_FORWARD}: carry-forward candidates for next controlled phase.",
        f"- {MONITORED_STABLE_WARNING}: non-blocking warnings kept with monitoring.",
        f"- {RESOLUTION_HOLDING}: holding set kept in proposal for later controlled revisit.",
        f"- {ESCALATE_WATCH}: warning-policy watch set; becomes blocker under escalation conditions.",
        f"- {REJECT_CANDIDATE}: blocker set (must not carry forward).",
        "",
        "## bucket_counts",
        f"- {READY_CARRY_FORWARD}={ready_count}",
        f"- {MONITORED_STABLE_WARNING}={monitored_count}",
        f"- {RESOLUTION_HOLDING}={holding_count}",
        f"- {ESCALATE_WATCH}={watch_count}",
        f"- {REJECT_CANDIDATE}={reject_count}",
        f"- records_total={len(all_rows)}",
        "",
        "## residual_warning_patterns",
        f"- text_only_remaining_count={monitored_text_only_count}",
        f"- route_soft_warning_count={monitored_route_soft_count}",
        f"- year_warning_count={monitored_year_warning_count}",
        f"- route_soft_warning_patterns={dict(monitored_route_soft_patterns)}",
        "",
        "## decision",
        f"- go_hold_decision={decision}",
        f"- blocker_labels={blocker_labels}",
        f"- warning_labels={warning_labels}",
    ]
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(
        "[task241] "
        f"ready={ready_count} monitored={monitored_count} holding={holding_count} watch={watch_count} "
        f"reject={reject_count} coverage={coverage_review_count} join_blocker={join_blocker_count} "
        f"decision={decision}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
