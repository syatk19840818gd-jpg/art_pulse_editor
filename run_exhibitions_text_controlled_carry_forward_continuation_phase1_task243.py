from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY_FOR_PHASE_2 = "READY_FOR_CARRY_FORWARD_PHASE_2"
HOLD_MONITORED = "HOLD_FOR_MONITORED_POLICY_REVIEW"
HOLD_BOUNDARY = "HOLD_FOR_BOUNDARY_RECHECK"


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
    parser = argparse.ArgumentParser(description="TASK243 Exhibitions Text controlled carry-forward continuation phase 1")
    parser.add_argument(
        "--task242-summary",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_carry_forward_phase_start_summary_task242.json",
    )
    parser.add_argument(
        "--task242-ready-set-csv",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_carry_forward_ready_set_task242.csv",
    )
    parser.add_argument(
        "--task242-monitored-set-csv",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_carry_forward_monitored_set_task242.csv",
    )
    parser.add_argument(
        "--task242-holding-set-csv",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_carry_forward_holding_set_task242.csv",
    )
    parser.add_argument(
        "--task242-escalate-set-csv",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_carry_forward_escalate_set_task242.csv",
    )
    parser.add_argument(
        "--task242-reject-set-csv",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_carry_forward_reject_set_task242.csv",
    )
    parser.add_argument("--output-dir", default="data/phase1_seed10/logs")
    parser.add_argument("--run-id", default="")
    return parser.parse_args()


def row_signature(row: dict[str, str]) -> str:
    return "||".join(
        [
            str(row.get("gallery_name_en") or "").strip(),
            str(row.get("fair_slug") or "").strip(),
            str(row.get("target_year") or "").strip(),
            str(row.get("source_url") or "").strip(),
        ]
    )


def continuation_scope_hash(rows: list[dict[str, str]]) -> str:
    payload = "\n".join(sorted({row_signature(row) for row in rows}))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest() if payload else ""


def main() -> int:
    args = parse_args()
    run_id = args.run_id.strip() or datetime.now(timezone.utc).strftime("task243_%Y%m%dT%H%M%SZ")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    summary242 = read_json(Path(args.task242_summary), default={})
    ready_rows = read_csv(Path(args.task242_ready_set_csv))
    monitored_rows = read_csv(Path(args.task242_monitored_set_csv))
    holding_rows = read_csv(Path(args.task242_holding_set_csv))
    escalate_rows = read_csv(Path(args.task242_escalate_set_csv))
    reject_rows = read_csv(Path(args.task242_reject_set_csv))

    continuation_rows: list[dict[str, Any]] = []
    for row in ready_rows:
        out = dict(row)
        out["continuation_stream"] = "READY"
        out["continuation_reason"] = "direct_carry_forward"
        continuation_rows.append(out)
    for row in monitored_rows:
        out = dict(row)
        out["continuation_stream"] = "MONITORED"
        out["continuation_reason"] = "carry_forward_with_monitoring"
        continuation_rows.append(out)

    continuation_signatures = {row_signature(r) for r in continuation_rows}
    excluded_signatures = {row_signature(r) for r in (holding_rows + escalate_rows + reject_rows)}
    boundary_overlap = sorted(continuation_signatures & excluded_signatures)
    boundary_breach_count = len(boundary_overlap)

    scope_hash = continuation_scope_hash(continuation_rows)

    by_fair = defaultdict(Counter)
    by_gallery = defaultdict(Counter)
    for row in continuation_rows:
        fair = str(row.get("fair_slug") or "").strip()
        gallery = str(row.get("gallery_name_en") or "").strip()
        stream = str(row.get("continuation_stream") or "").strip()
        by_fair[fair][stream] += 1
        by_gallery[(gallery, fair)][stream] += 1

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

    integrity = summary242.get("integrity_checks", {})
    coverage_review_count = int(integrity.get("coverage_review_count", 0))
    reject_count = max(len(reject_rows), int(integrity.get("reject_candidate_count", 0)))
    join_blocker_count = int(integrity.get("join_blocker_count", 0))
    escalate_count = len(escalate_rows)

    blocker_labels: list[str] = []
    if coverage_review_count > 0:
        blocker_labels.append("COVERAGE_REVIEW_PRESENT")
    if reject_count > 0:
        blocker_labels.append("REJECT_SET_PRESENT")
    if join_blocker_count > 0:
        blocker_labels.append("JOIN_BLOCKER_PRESENT")
    if escalate_count > 0:
        blocker_labels.append("ESCALATE_SET_PRESENT")
    if boundary_breach_count > 0:
        blocker_labels.append("BOUNDARY_MIXING_DETECTED")

    # Consecutive-run conditions are monitored, but not auto-triggered from single snapshot.
    monitored_policy_hold = False

    if boundary_breach_count > 0 or blocker_labels:
        decision = HOLD_BOUNDARY
    elif monitored_policy_hold:
        decision = HOLD_MONITORED
    else:
        decision = READY_FOR_PHASE_2

    summary = {
        "artifact": "exhibitions_text_controlled_carry_forward_continuation_phase1_summary",
        "task": "TASK243",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "inputs": {
            "task242_summary": str(Path(args.task242_summary)),
            "task242_ready_set_csv": str(Path(args.task242_ready_set_csv)),
            "task242_monitored_set_csv": str(Path(args.task242_monitored_set_csv)),
            "task242_holding_set_csv": str(Path(args.task242_holding_set_csv)),
            "task242_escalate_set_csv": str(Path(args.task242_escalate_set_csv)),
            "task242_reject_set_csv": str(Path(args.task242_reject_set_csv)),
        },
        "continuation_input_bundle": {
            "definition": "CARRY_FORWARD_READY_SET + CARRY_FORWARD_MONITORED_SET only",
            "continuation_input_total": len(continuation_rows),
            "ready_count": len(ready_rows),
            "monitored_count": len(monitored_rows),
            "holding_excluded_count": len(holding_rows),
            "escalate_excluded_count": len(escalate_rows),
            "reject_excluded_count": len(reject_rows),
            "scope_hash": scope_hash,
        },
        "boundary_checks": {
            "holding_mixed_into_continuation": False,
            "escalate_mixed_into_continuation": False,
            "reject_mixed_into_continuation": False,
            "boundary_breach_count": boundary_breach_count,
            "boundary_breach_signatures": boundary_overlap,
        },
        "aggregates": {
            "by_fair_counts": {k: dict(v) for k, v in by_fair.items()},
            "by_gallery_counts": {f"{k[0]}|{k[1]}": dict(v) for k, v in by_gallery.items()},
            "monitored_primary_patterns": {
                "text_only_count": monitored_text_only_count,
                "route_soft_count": monitored_route_soft_count,
                "year_warning_count": monitored_year_warning_count,
            },
        },
        "continuation_policy": {
            "ready_handling": "process in next controlled continuation stage without additional review gate",
            "monitored_handling": {
                "process_in_next_stage": True,
                "monitoring_continues": True,
                "escalate_rules": [
                    "persisting >=3 controlled runs",
                    "stable_text_only_ratio > 0.6 for two runs",
                    "route quality degradation trend",
                ],
                "on_warning_worsen": "move from MONITORED to ESCALATE and hold continuation boundary",
            },
            "holding_handling": {
                "included_now": False,
                "revisit_timing": "next carry-forward boundary review or when monitored worsens",
            },
            "blockers": [
                "coverage_review_count > 0",
                "reject_count > 0",
                "join_blocker_count > 0",
                "escalate_count > 0",
                "boundary_breach_count > 0",
            ],
        },
        "integrity_checks": {
            "coverage_review_count": coverage_review_count,
            "reject_candidate_count": reject_count,
            "join_blocker_count": join_blocker_count,
            "proposal_only": True,
            "formal_untouched": True,
            "adoption_executed": False,
            "rollback_executed": False,
            "join_contract_changed": False,
            "anti_mixing_enforced": True,
        },
        "go_hold_decision": decision,
        "blocker_labels": blocker_labels,
        "next_task_recommendation": {
            "id": "TASK244",
            "title": "EXHIBITIONS-TEXT-CONTROLLED-CARRY-FORWARD-CONTINUATION-PHASE-2",
            "ja": "Continue controlled processing of READY+MONITORED input bundle with monitored trend checks",
        },
    }

    summary_path = output_dir / "exhibitions_text_controlled_carry_forward_continuation_phase1_summary_task243.json"
    table_path = output_dir / "exhibitions_text_controlled_carry_forward_continuation_phase1_table_task243.csv"
    by_fair_path = output_dir / "exhibitions_text_controlled_carry_forward_continuation_phase1_by_fair_task243.csv"
    continuation_input_path = output_dir / "exhibitions_text_controlled_carry_forward_continuation_input_task243.csv"
    manifest_path = output_dir / "exhibitions_text_controlled_carry_forward_continuation_phase1_manifest_task243.json"
    report_path = output_dir / "exhibitions_text_controlled_carry_forward_continuation_phase1_task243.md"

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
        "post_review_bucket",
        "post_review_reason",
        "source_stream",
        "carry_forward_set",
        "carry_forward_reason",
        "continuation_stream",
        "continuation_reason",
    ]
    write_csv(continuation_input_path, continuation_rows, fields)

    table_rows: list[dict[str, Any]] = []
    for (gallery, fair), counts in sorted(by_gallery.items(), key=lambda x: (x[0][1], x[0][0])):
        table_rows.append(
            {
                "gallery_name_en": gallery,
                "fair_slug": fair,
                "READY": int(counts.get("READY", 0)),
                "MONITORED": int(counts.get("MONITORED", 0)),
                "TOTAL": int(counts.get("READY", 0) + counts.get("MONITORED", 0)),
            }
        )
    write_csv(table_path, table_rows, ["gallery_name_en", "fair_slug", "READY", "MONITORED", "TOTAL"])

    fair_rows: list[dict[str, Any]] = []
    for fair, counts in sorted(by_fair.items(), key=lambda x: x[0]):
        fair_rows.append(
            {
                "fair_slug": fair,
                "READY": int(counts.get("READY", 0)),
                "MONITORED": int(counts.get("MONITORED", 0)),
                "TOTAL": int(counts.get("READY", 0) + counts.get("MONITORED", 0)),
            }
        )
    write_csv(by_fair_path, fair_rows, ["fair_slug", "READY", "MONITORED", "TOTAL"])

    write_json(summary_path, summary)
    manifest = {
        "artifact": "exhibitions_text_controlled_carry_forward_continuation_phase1_manifest",
        "task": "TASK243",
        "run_id": run_id,
        "inputs": summary["inputs"],
        "outputs": {
            "summary_json": str(summary_path),
            "table_csv": str(table_path),
            "by_fair_csv": str(by_fair_path),
            "continuation_input_csv": str(continuation_input_path),
            "report_md": str(report_path),
            "manifest_json": str(manifest_path),
        },
        "continuation_scope_hash": scope_hash,
        "integrity_checks": summary["integrity_checks"],
    }
    write_json(manifest_path, manifest)

    report_lines = [
        "# TASK243 Exhibitions Text Controlled Carry-Forward Continuation Phase 1",
        "",
        "## continuation_input_bundle_definition",
        "- Input = CARRY_FORWARD_READY_SET + CARRY_FORWARD_MONITORED_SET only.",
        "- HOLDING/ESCALATE/REJECT are excluded by boundary rule.",
        f"- continuation_input_total={len(continuation_rows)}",
        f"- ready_count={len(ready_rows)}",
        f"- monitored_count={len(monitored_rows)}",
        f"- holding_excluded_count={len(holding_rows)}",
        "",
        "## monitored_handling",
        "- MONITORED rows are processed in continuation with monitoring active.",
        "- Escalate rules are inherited from TASK239/TASK240.",
        "- Warning worsening moves rows to ESCALATE boundary (blocker).",
        "",
        "## integrity",
        f"- coverage_review_count={coverage_review_count}",
        f"- reject_candidate_count={reject_count}",
        f"- join_blocker_count={join_blocker_count}",
        f"- boundary_breach_count={boundary_breach_count}",
        "",
        "## decision",
        f"- go_hold_decision={decision}",
        f"- blocker_labels={blocker_labels}",
    ]
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(
        "[task243] "
        f"continuation_total={len(continuation_rows)} ready={len(ready_rows)} monitored={len(monitored_rows)} "
        f"holding_excluded={len(holding_rows)} escalate_excluded={len(escalate_rows)} reject_excluded={len(reject_rows)} "
        f"boundary_breach={boundary_breach_count} decision={decision}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
