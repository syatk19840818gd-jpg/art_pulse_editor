from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY = "READY_FOR_CONTROLLED_OPERATION_ADOPTION"
HOLD_RUNBOOK = "HOLD_FOR_OPERATION_RUNBOOK_TUNING"
HOLD_REINTEGRATION = "HOLD_FOR_REINTEGRATION_POLICY_REVIEW"


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


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="TASK259 Exhibitions Text steady-state operation controlled adoption proposal finalization"
    )
    parser.add_argument(
        "--task258-summary-json",
        default="data/phase1_seed10/logs/exhibitions_text_steady_state_operation_proposal_summary_task258.json",
    )
    parser.add_argument(
        "--task258-manifest-json",
        default="data/phase1_seed10/logs/exhibitions_text_steady_state_operation_proposal_manifest_task258.json",
    )
    parser.add_argument(
        "--task257-ready-summary-json",
        default="data/phase1_seed10/logs/exhibitions_text_ready_restart_with_escalate_monitoring_phase5_continuation_ready_summary_task257.json",
    )
    parser.add_argument(
        "--task257-escalate-summary-json",
        default="data/phase1_seed10/logs/exhibitions_text_ready_restart_with_escalate_monitoring_phase5_continuation_escalate_summary_task257.json",
    )
    parser.add_argument("--output-dir", default="data/phase1_seed10/logs")
    parser.add_argument("--run-id", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_id = args.run_id.strip() or datetime.now(timezone.utc).strftime("task259_%Y%m%dT%H%M%SZ")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    s258 = read_json(Path(args.task258_summary_json), default={})
    m258 = read_json(Path(args.task258_manifest_json), default={})
    s257_ready = read_json(Path(args.task257_ready_summary_json), default={})
    s257_escalate = read_json(Path(args.task257_escalate_summary_json), default={})

    lane_inventory = dict(s258.get("lane_inventory") or {})
    lane_counts = dict(lane_inventory.get("counts") or {})
    lane_by_fair = dict(lane_inventory.get("by_fair") or {})
    lane_by_gallery = dict(lane_inventory.get("by_gallery") or {})
    overlap_details = dict(lane_inventory.get("overlap_details") or {})
    boundary_breach_count = int(lane_inventory.get("boundary_breach_count", 0))
    integrity_clear = bool(lane_inventory.get("integrity_clear", False))

    recommended_option_id = str(s258.get("recommended_option_id") or "").strip()
    cadence_options = list(s258.get("run_cadence_options") or [])
    hold_policy = dict(s258.get("hold_restore_noop_policy") or {})
    reintegration_policy = dict(s258.get("reintegration_policy") or {})
    holding_recheck_policy = dict(s258.get("holding_recheck_policy") or {})

    coverage_review_count = int(dict(s257_ready.get("common_checks") or {}).get("coverage_review_count", 0))
    reject_candidate_count = int(dict(s257_ready.get("common_checks") or {}).get("reject_candidate_count", 0))
    join_blocker_count = int(dict(s257_ready.get("common_checks") or {}).get("join_blocker_count", 0))
    escalate_blocker_count = int(dict(s257_escalate.get("escalate_lane_result") or {}).get("escalate_blocker_count", 0))
    ratio_two_consecutive = int(dict(s257_escalate.get("escalate_lane_result") or {}).get("ratio_two_consecutive_fired_count", 0))
    route_degradation = int(dict(s257_escalate.get("escalate_lane_result") or {}).get("route_degradation_fired_count", 0))

    blockers: list[str] = []
    warnings: list[str] = []

    if recommended_option_id != "A":
        blockers.append("RECOMMENDED_CADENCE_OPTION_NOT_FIXED_TO_A")
    if boundary_breach_count != 0:
        blockers.append("BOUNDARY_BREACH_DETECTED")
    if not integrity_clear:
        blockers.append("INTEGRITY_NOT_CLEAR")
    if coverage_review_count != 0:
        blockers.append("COVERAGE_REVIEW_PRESENT")
    if reject_candidate_count != 0:
        blockers.append("REJECT_CANDIDATE_PRESENT")
    if join_blocker_count != 0:
        blockers.append("JOIN_BLOCKER_PRESENT")
    if escalate_blocker_count != 0:
        blockers.append("ESCALATE_BLOCKER_PRESENT")

    if int(lane_counts.get("ESCALATE_SEPARATE_LANE", 0)) > 0:
        warnings.append("ESCALATE_LANE_NONZERO_MONITORED_CONTINUATION_REQUIRED")
    if int(lane_counts.get("HOLDING_LANE", 0)) > 0:
        warnings.append("HOLDING_LANE_REQUIRES_PERIODIC_RECHECK")
    if ratio_two_consecutive != 0 or route_degradation != 0:
        blockers.append("ESCALATE_SIGNAL_DEGRADATION_DETECTED")

    if blockers:
        decision = HOLD_REINTEGRATION if "ESCALATE_SIGNAL_DEGRADATION_DETECTED" in blockers else HOLD_RUNBOOK
    else:
        decision = READY

    lane_matrix_rows = [
        {
            "lane_name": "READY_LANE",
            "target_count": int(lane_counts.get("READY_LANE", 0)),
            "purpose": "Primary continuation stream for carry-forward records",
            "continue_conditions": "boundary=0; coverage=0; reject=0; join_blocker=0; non-mixed with ESCALATE/HOLDING/REJECT",
            "local_hold_conditions": "any boundary overlap or READY integrity_clear=false",
            "global_hold_impact": "YES",
            "reintegration_or_recheck": "N/A (base lane)",
            "notes": "Run weekly with shared run_id under Option A",
        },
        {
            "lane_name": "ESCALATE_SEPARATE_LANE",
            "target_count": int(lane_counts.get("ESCALATE_SEPARATE_LANE", 0)),
            "purpose": "Separate monitoring for escalated monitor_keys",
            "continue_conditions": "escalate_blocker=0; ratio_two_consecutive=0; route_degradation=0",
            "local_hold_conditions": "ratio_two_consecutive>0 or route_degradation>0 or escalate_blocker>0",
            "global_hold_impact": "CONDITIONAL",
            "reintegration_or_recheck": "Candidate for READY only after >=3 consecutive safe runs + manual approval",
            "notes": "Never mixed into READY continuation input",
        },
        {
            "lane_name": "HOLDING_LANE",
            "target_count": int(lane_counts.get("HOLDING_LANE", 0)),
            "purpose": "Out-of-scope holding set not included in continuation",
            "continue_conditions": "excluded from READY/ESCALATE streams",
            "local_hold_conditions": "N/A (already excluded)",
            "global_hold_impact": "NO",
            "reintegration_or_recheck": "Recheck every 4 runs or monthly",
            "notes": "Isolated re-evaluation only; no direct stream merge",
        },
        {
            "lane_name": "REJECT_LANE",
            "target_count": int(lane_counts.get("REJECT_LANE", 0)),
            "purpose": "Always blocked set",
            "continue_conditions": "always excluded",
            "local_hold_conditions": "N/A",
            "global_hold_impact": "YES if >0 appears unexpectedly",
            "reintegration_or_recheck": "No automatic reintegration",
            "notes": "Current count is expected to stay zero",
        },
    ]

    runbook_steps = [
        {
            "step_order": 1,
            "step_id": "RUN_START_VALIDATION",
            "action": "Confirm target run scope uses READY+ESCALATE lanes only; HOLDING/REJECT excluded",
            "pass_criteria": "scope signature and lane counts match expected boundary",
            "on_fail": "GLOBAL_HOLD",
        },
        {
            "step_order": 2,
            "step_id": "PREFLIGHT",
            "action": "Execute preflight checks (boundary/integrity/no-op rule/state availability)",
            "pass_criteria": "all mandatory checks PASS",
            "on_fail": "GLOBAL_HOLD",
        },
        {
            "step_order": 3,
            "step_id": "BACKUP",
            "action": "Create monitored-state backup and verify hash",
            "pass_criteria": "backup exists and hash matches authoritative state",
            "on_fail": "HOLD_AND_STOP",
        },
        {
            "step_order": 4,
            "step_id": "READY_LANE_EXECUTION",
            "action": "Run READY lane continuation stream",
            "pass_criteria": "READY boundary_breach=0 and integrity_clear=true",
            "on_fail": "READY_LOCAL_HOLD",
        },
        {
            "step_order": 5,
            "step_id": "ESCALATE_LANE_EXECUTION",
            "action": "Run ESCALATE separate monitoring stream",
            "pass_criteria": "escalate_blocker=0 and no ratio/route degradation fire",
            "on_fail": "ESCALATE_LOCAL_HOLD",
        },
        {
            "step_order": 6,
            "step_id": "POST_RUN_VERIFICATION",
            "action": "Verify temporal gap, same-run no-op behavior, and post-run integrity",
            "pass_criteria": "temporal_gap=0 and integrity blockers remain zero",
            "on_fail": "RESTORE_OR_HOLD",
        },
        {
            "step_order": 7,
            "step_id": "HOLD_RESTORE_DECISION",
            "action": "Apply global/local hold and restore criteria",
            "pass_criteria": "no hold/restore conditions active",
            "on_fail": "EXECUTE_RESTORE_IF_REQUIRED",
        },
        {
            "step_order": 8,
            "step_id": "LOG_MANIFEST_CONFIRM",
            "action": "Confirm summary/manifest/backup logs are complete and immutable",
            "pass_criteria": "all required artifacts generated with matching run_id",
            "on_fail": "HOLD_FOR_RUNBOOK_TUNING",
        },
    ]

    readiness = {
        "controlled_adoption_possible_when": [
            "recommended_option_id == A",
            "boundary_breach_count == 0",
            "coverage_review_count == 0",
            "reject_candidate_count == 0",
            "join_blocker_count == 0",
            "escalate_blocker_count == 0",
            "restore conditions documented and executable",
        ],
        "hold_when": [
            "boundary/integrity blocker appears",
            "runbook preflight or backup hash check fails",
            "reintegration policy is undefined or contradicted by current signals",
        ],
        "blockers": [
            "BOUNDARY_BREACH_DETECTED",
            "COVERAGE_REVIEW_PRESENT",
            "REJECT_CANDIDATE_PRESENT",
            "JOIN_BLOCKER_PRESENT",
            "ESCALATE_BLOCKER_PRESENT",
            "ESCALATE_SIGNAL_DEGRADATION_DETECTED",
        ],
        "warning_but_operable": [
            "ESCALATE lane remains nonzero with stable monitoring signals",
            "HOLDING lane remains excluded with periodic recheck cadence",
        ],
    }

    summary = {
        "artifact": "exhibitions_text_steady_state_operation_controlled_adoption_proposal_summary",
        "task": "TASK259",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "inputs": {
            "task258_summary_json": str(Path(args.task258_summary_json)),
            "task258_manifest_json": str(Path(args.task258_manifest_json)),
            "task257_ready_summary_json": str(Path(args.task257_ready_summary_json)),
            "task257_escalate_summary_json": str(Path(args.task257_escalate_summary_json)),
        },
        "scope": {
            "lanes_in_scope": ["READY_LANE", "ESCALATE_SEPARATE_LANE", "HOLDING_LANE", "REJECT_LANE"],
            "monitoring_components": ["monitored_state", "preflight", "backup", "restore", "no_op_rule"],
            "proposal_only": True,
            "formal_untouched": True,
            "adoption_executed": False,
            "rollback_executed": False,
            "join_contract_changed": False,
            "anti_mixing_enforced": True,
        },
        "inventory": {
            "lane_counts": lane_counts,
            "lane_by_fair": lane_by_fair,
            "lane_by_gallery": lane_by_gallery,
            "overlap_details": overlap_details,
            "boundary_breach_count": boundary_breach_count,
            "integrity_clear": integrity_clear,
        },
        "runbook": {
            "step_count": len(runbook_steps),
            "steps": runbook_steps,
        },
        "cadence_finalization": {
            "recommended_option_id": recommended_option_id,
            "recommended_option_name": next(
                (x.get("cadence_name") for x in cadence_options if x.get("option_id") == recommended_option_id), ""
            ),
            "run_id_mode": "shared_single_run_id_for_ready_and_escalate",
            "backup_policy": "every_run_before_state_update",
            "manual_approval_required_for": [
                "ESCALATE_TO_READY_REINTEGRATION",
            ],
            "state_update_rule": "update_monitored_state_once_per_run_after_preflight_and_backup",
        },
        "hold_restore_noop_policy": hold_policy,
        "reintegration_policy": reintegration_policy,
        "holding_recheck_policy": holding_recheck_policy,
        "adoption_readiness": readiness,
        "go_hold_decision": decision,
        "blocker_labels": blockers,
        "warning_labels": warnings,
        "next_task_recommendation": {
            "id": "TASK260",
            "title": "EXHIBITIONS-TEXT-CONTROLLED-OPERATION-ADOPTION-PRECHECK-AND-GO-NOGO",
            "ja": "Run final controlled-operation precheck and formal go/no-go before adoption start",
        },
    }

    summary_path = output_dir / "exhibitions_text_steady_state_operation_controlled_adoption_proposal_summary_task259.json"
    lane_matrix_path = output_dir / "exhibitions_text_steady_state_lane_operation_matrix_task259.csv"
    checklist_path = output_dir / "exhibitions_text_steady_state_operation_runbook_checklist_task259.csv"
    runbook_md_path = output_dir / "exhibitions_text_steady_state_operation_runbook_task259.md"
    manifest_path = output_dir / "exhibitions_text_steady_state_operation_controlled_adoption_proposal_manifest_task259.json"

    write_json(summary_path, summary)
    write_csv(
        lane_matrix_path,
        lane_matrix_rows,
        [
            "lane_name",
            "target_count",
            "purpose",
            "continue_conditions",
            "local_hold_conditions",
            "global_hold_impact",
            "reintegration_or_recheck",
            "notes",
        ],
    )
    write_csv(
        checklist_path,
        runbook_steps,
        ["step_order", "step_id", "action", "pass_criteria", "on_fail"],
    )

    runbook_text = [
        "# TASK259 Controlled Adoption Proposal Runbook",
        "",
        "## Scope",
        "- In-scope lanes: READY_LANE, ESCALATE_SEPARATE_LANE",
        "- Excluded lanes: HOLDING_LANE, REJECT_LANE",
        "- Mode: proposal-only (formal untouched, no adoption/rollback execution)",
        "",
        "## Sequential Procedure",
    ]
    for row in runbook_steps:
        runbook_text.append(f"{row['step_order']}. `{row['step_id']}` - {row['action']}")
        runbook_text.append(f"   - pass: {row['pass_criteria']}")
        runbook_text.append(f"   - fail: {row['on_fail']}")
    runbook_text.extend(
        [
            "",
            "## Fixed Cadence",
            "- Recommended Option A: weekly synchronized dual-lane run with shared run_id and per-run backup.",
            "",
            "## Decision",
            f"- go_hold_decision: `{decision}`",
            f"- blockers: {', '.join(blockers) if blockers else '(none)'}",
            f"- warnings: {', '.join(warnings) if warnings else '(none)'}",
            "",
            "## Next",
            "- TASK260: EXHIBITIONS-TEXT-CONTROLLED-OPERATION-ADOPTION-PRECHECK-AND-GO-NOGO",
        ]
    )
    runbook_md_path.write_text("\n".join(runbook_text) + "\n", encoding="utf-8")

    manifest = {
        "artifact": "exhibitions_text_steady_state_operation_controlled_adoption_proposal_manifest",
        "task": "TASK259",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "source_task_run_id": str(s258.get("run_id") or ""),
        "source_manifest_run_id": str(m258.get("run_id") or ""),
        "decision": decision,
        "boundary_breach_count": boundary_breach_count,
        "integrity_clear": integrity_clear,
        "outputs": [
            str(summary_path),
            str(lane_matrix_path),
            str(checklist_path),
            str(runbook_md_path),
        ],
    }
    write_json(manifest_path, manifest)

    print(
        "[task259] "
        f"run_id={run_id} ready={lane_counts.get('READY_LANE', 0)} escalate={lane_counts.get('ESCALATE_SEPARATE_LANE', 0)} "
        f"holding={lane_counts.get('HOLDING_LANE', 0)} reject={lane_counts.get('REJECT_LANE', 0)} "
        f"boundary={boundary_breach_count} integrity_clear={integrity_clear} decision={decision}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
