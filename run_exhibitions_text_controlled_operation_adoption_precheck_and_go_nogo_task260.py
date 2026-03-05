from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

GO = "GO_FOR_CONTROLLED_OPERATION_START"
HOLD_RUNBOOK = "HOLD_FOR_RUNBOOK_GAP_FIX"
HOLD_POLICY = "HOLD_FOR_POLICY_GAP_REVIEW"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


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
        description="TASK260 Exhibitions Text controlled operation adoption precheck and go/no-go"
    )
    parser.add_argument(
        "--task259-summary-json",
        default="data/phase1_seed10/logs/exhibitions_text_steady_state_operation_controlled_adoption_proposal_summary_task259.json",
    )
    parser.add_argument(
        "--task259-manifest-json",
        default="data/phase1_seed10/logs/exhibitions_text_steady_state_operation_controlled_adoption_proposal_manifest_task259.json",
    )
    parser.add_argument(
        "--task259-lane-matrix-csv",
        default="data/phase1_seed10/logs/exhibitions_text_steady_state_lane_operation_matrix_task259.csv",
    )
    parser.add_argument(
        "--task259-runbook-csv",
        default="data/phase1_seed10/logs/exhibitions_text_steady_state_operation_runbook_checklist_task259.csv",
    )
    parser.add_argument("--output-dir", default="data/phase1_seed10/logs")
    parser.add_argument("--run-id", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_id = args.run_id.strip() or datetime.now(timezone.utc).strftime("task260_%Y%m%dT%H%M%SZ")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    s259 = read_json(Path(args.task259_summary_json), default={})
    m259 = read_json(Path(args.task259_manifest_json), default={})
    lane_matrix = read_csv(Path(args.task259_lane_matrix_csv))
    runbook = read_csv(Path(args.task259_runbook_csv))

    inventory = dict(s259.get("inventory") or {})
    lane_counts = dict(inventory.get("lane_counts") or {})
    lane_by_fair = dict(inventory.get("lane_by_fair") or {})
    lane_by_gallery = dict(inventory.get("lane_by_gallery") or {})
    overlap_details = dict(inventory.get("overlap_details") or {})
    boundary_breach_count = int(inventory.get("boundary_breach_count", 0))
    integrity_clear = bool(inventory.get("integrity_clear", False))

    runbook_steps = list(dict(s259.get("runbook") or {}).get("steps", []))
    hold_restore_noop = dict(s259.get("hold_restore_noop_policy") or {})
    cadence = dict(s259.get("cadence_finalization") or {})
    reintegration = dict(s259.get("reintegration_policy") or {})
    holding_recheck = dict(s259.get("holding_recheck_policy") or {})
    readiness = dict(s259.get("adoption_readiness") or {})

    expected_lanes = {"READY_LANE", "ESCALATE_SEPARATE_LANE", "HOLDING_LANE", "REJECT_LANE"}
    matrix_lane_set = {str(r.get("lane_name") or "").strip() for r in lane_matrix}
    runbook_step_ids = {str(r.get("step_id") or "").strip() for r in runbook}
    expected_step_ids = {
        "RUN_START_VALIDATION",
        "PREFLIGHT",
        "BACKUP",
        "READY_LANE_EXECUTION",
        "ESCALATE_LANE_EXECUTION",
        "POST_RUN_VERIFICATION",
        "HOLD_RESTORE_DECISION",
        "LOG_MANIFEST_CONFIRM",
    }

    checks: list[dict[str, Any]] = []

    def add_check(
        check_id: str,
        passed: bool,
        actual: Any,
        expected: Any,
        severity: str,
        notes: str = "",
    ) -> None:
        checks.append(
            {
                "check_id": check_id,
                "status": "PASS" if passed else "FAIL",
                "severity": severity,
                "actual": actual,
                "expected": expected,
                "notes": notes,
            }
        )

    add_check("TASK259_SUMMARY_EXISTS", bool(s259), bool(True), True, "BLOCKER")
    add_check("TASK259_MANIFEST_EXISTS", bool(m259), True, True, "BLOCKER")
    add_check("LANE_MATRIX_EXISTS", len(lane_matrix) > 0, len(lane_matrix), ">0", "BLOCKER")
    add_check("RUNBOOK_CHECKLIST_EXISTS", len(runbook) > 0, len(runbook), ">0", "BLOCKER")
    add_check("LANE_DEFINITION_COMPLETE", expected_lanes.issubset(matrix_lane_set), sorted(matrix_lane_set), sorted(expected_lanes), "BLOCKER")
    add_check("MIXING_BAN_EXPLICIT", "READY_LANE" in matrix_lane_set and "ESCALATE_SEPARATE_LANE" in matrix_lane_set, True, True, "BLOCKER")
    add_check(
        "HOLDING_REJECT_EXCLUSION_DEFINED",
        "HOLDING_LANE" in matrix_lane_set and "REJECT_LANE" in matrix_lane_set,
        True,
        True,
        "BLOCKER",
    )
    add_check("RUNBOOK_8_STEPS_COVERED", expected_step_ids.issubset(runbook_step_ids), sorted(runbook_step_ids), sorted(expected_step_ids), "BLOCKER")
    add_check("RUNBOOK_STEP_COUNT_MIN_8", len(runbook_step_ids) >= 8, len(runbook_step_ids), ">=8", "BLOCKER")
    add_check(
        "NOOP_RULE_DEFINED",
        len(list(hold_restore_noop.get("no_op_conditions") or [])) > 0,
        len(list(hold_restore_noop.get("no_op_conditions") or [])),
        ">0",
        "BLOCKER",
    )
    add_check(
        "BACKUP_RESTORE_RULE_DEFINED",
        len(list(hold_restore_noop.get("restore_conditions") or [])) > 0,
        len(list(hold_restore_noop.get("restore_conditions") or [])),
        ">0",
        "BLOCKER",
    )
    add_check(
        "MANUAL_APPROVAL_DEFINED",
        "ESCALATE_TO_READY_REINTEGRATION" in list(cadence.get("manual_approval_required_for") or []),
        cadence.get("manual_approval_required_for"),
        "contains ESCALATE_TO_READY_REINTEGRATION",
        "BLOCKER",
    )
    add_check(
        "REINTEGRATION_MIN_SAFE_RUNS",
        int(reintegration.get("minimum_safe_runs", 0)) >= 3,
        reintegration.get("minimum_safe_runs"),
        ">=3",
        "BLOCKER",
    )
    add_check(
        "HOLDING_RECHECK_DEFINED",
        bool(holding_recheck.get("cadence")) and bool(holding_recheck.get("rule")),
        {"cadence": holding_recheck.get("cadence"), "rule": bool(holding_recheck.get("rule"))},
        "cadence+rule",
        "BLOCKER",
    )
    add_check("BOUNDARY_BREACH_ZERO", boundary_breach_count == 0, boundary_breach_count, 0, "BLOCKER")
    add_check("INTEGRITY_CLEAR_TRUE", integrity_clear, integrity_clear, True, "BLOCKER")
    add_check("TASK259_DECISION_READY", str(s259.get("go_hold_decision") or "") == "READY_FOR_CONTROLLED_OPERATION_ADOPTION", s259.get("go_hold_decision"), "READY_FOR_CONTROLLED_OPERATION_ADOPTION", "BLOCKER")
    add_check(
        "OPTION_A_FIXED",
        str(cadence.get("recommended_option_id") or "") == "A",
        cadence.get("recommended_option_id"),
        "A",
        "BLOCKER",
    )
    add_check(
        "SCOPE_COUNTS_EXPECTED",
        lane_counts == {"READY_LANE": 48, "ESCALATE_SEPARATE_LANE": 4, "HOLDING_LANE": 17, "REJECT_LANE": 0},
        lane_counts,
        {"READY_LANE": 48, "ESCALATE_SEPARATE_LANE": 4, "HOLDING_LANE": 17, "REJECT_LANE": 0},
        "WARNING",
    )

    blocker_fails = [c for c in checks if c["severity"] == "BLOCKER" and c["status"] == "FAIL"]
    warning_fails = [c for c in checks if c["severity"] == "WARNING" and c["status"] == "FAIL"]

    if blocker_fails:
        gap_ids = {c["check_id"] for c in blocker_fails}
        if {"RUNBOOK_8_STEPS_COVERED", "RUNBOOK_STEP_COUNT_MIN_8", "RUNBOOK_CHECKLIST_EXISTS"} & gap_ids:
            decision = HOLD_RUNBOOK
        else:
            decision = HOLD_POLICY
    else:
        decision = GO

    required_before_start = []
    if blocker_fails:
        required_before_start = [f"{c['check_id']}={c['actual']}" for c in blocker_fails]
    else:
        required_before_start = ["none"]

    can_after_start = [
        "HOLDING lane periodic recheck execution (every 4 runs or monthly)",
        "ESCALATE lane reintegration candidate review on 3-safe-run windows",
    ]

    warning_summary = list(readiness.get("warning_but_operable") or [])
    if warning_fails:
        warning_summary.extend([f"WARNING_CHECK_FAIL:{c['check_id']}" for c in warning_fails])

    precheck_summary = {
        "artifact": "exhibitions_text_controlled_operation_adoption_precheck_summary",
        "task": "TASK260",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "inputs": {
            "task259_summary_json": str(Path(args.task259_summary_json)),
            "task259_manifest_json": str(Path(args.task259_manifest_json)),
            "task259_lane_matrix_csv": str(Path(args.task259_lane_matrix_csv)),
            "task259_runbook_csv": str(Path(args.task259_runbook_csv)),
        },
        "precheck_totals": {
            "check_total": len(checks),
            "pass_count": sum(1 for c in checks if c["status"] == "PASS"),
            "fail_count": sum(1 for c in checks if c["status"] == "FAIL"),
            "blocker_fail_count": len(blocker_fails),
            "warning_fail_count": len(warning_fails),
        },
        "lane_counts": lane_counts,
        "lane_by_fair": lane_by_fair,
        "lane_by_gallery": lane_by_gallery,
        "overlap_details": overlap_details,
        "boundary_breach_count": boundary_breach_count,
        "integrity_clear": integrity_clear,
        "adoption_readiness_summary": {
            "go_basis": [
                "lane boundaries fixed and non-mixing explicit",
                "runbook/checklist complete for 8-step operation sequence",
                "backup/restore/hash/no-op/manual approval points present",
                "current boundary/integrity/blocker metrics clear",
            ],
            "warnings": warning_summary,
            "potential_blockers": list(readiness.get("blockers") or []),
            "manual_approval_required_points": list(cadence.get("manual_approval_required_for") or []),
        },
        "remaining_tasks": {
            "required_before_start": required_before_start,
            "can_be_done_after_start": can_after_start,
        },
        "go_hold_decision": decision,
        "blocker_labels": [c["check_id"] for c in blocker_fails],
        "warning_labels": [c["check_id"] for c in warning_fails],
        "next_task_recommendation": {
            "id": "TASK261",
            "title": "EXHIBITIONS-TEXT-CONTROLLED-OPERATION-START-WEEKLY-SYNC-DUAL-LANE",
            "ja": "Start weekly synchronized READY+ESCALATE controlled operation under finalized runbook",
        },
    }

    summary_path = output_dir / "exhibitions_text_controlled_operation_adoption_precheck_summary_task260.json"
    check_table_path = output_dir / "exhibitions_text_controlled_operation_adoption_precheck_table_task260.csv"
    gap_table_path = output_dir / "exhibitions_text_controlled_operation_adoption_precheck_gap_task260.csv"
    manifest_path = output_dir / "exhibitions_text_controlled_operation_adoption_precheck_manifest_task260.json"
    report_path = output_dir / "exhibitions_text_controlled_operation_adoption_precheck_task260.md"

    write_json(summary_path, precheck_summary)
    write_csv(
        check_table_path,
        checks,
        ["check_id", "status", "severity", "actual", "expected", "notes"],
    )
    write_csv(
        gap_table_path,
        [c for c in checks if c["status"] == "FAIL"],
        ["check_id", "status", "severity", "actual", "expected", "notes"],
    )

    manifest = {
        "artifact": "exhibitions_text_controlled_operation_adoption_precheck_manifest",
        "task": "TASK260",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "source_task_run_id": str(s259.get("run_id") or ""),
        "source_manifest_run_id": str(m259.get("run_id") or ""),
        "decision": decision,
        "check_total": len(checks),
        "blocker_fail_count": len(blocker_fails),
        "warning_fail_count": len(warning_fails),
        "outputs": [
            str(summary_path),
            str(check_table_path),
            str(gap_table_path),
            str(report_path),
        ],
    }
    write_json(manifest_path, manifest)

    report_lines = [
        "# TASK260 Controlled Operation Adoption Precheck",
        "",
        "## Result",
        f"- go_hold_decision: `{decision}`",
        f"- blocker_fail_count: {len(blocker_fails)}",
        f"- warning_fail_count: {len(warning_fails)}",
        "",
        "## Lane Inventory",
        f"- READY_LANE: {lane_counts.get('READY_LANE', 0)}",
        f"- ESCALATE_SEPARATE_LANE: {lane_counts.get('ESCALATE_SEPARATE_LANE', 0)}",
        f"- HOLDING_LANE: {lane_counts.get('HOLDING_LANE', 0)} (excluded)",
        f"- REJECT_LANE: {lane_counts.get('REJECT_LANE', 0)} (excluded)",
        "",
        "## Required Before Start",
    ]
    for x in required_before_start:
        report_lines.append(f"- {x}")
    report_lines.extend(
        [
            "",
            "## Operational Warnings",
        ]
    )
    for x in warning_summary:
        report_lines.append(f"- {x}")
    report_lines.extend(
        [
            "",
            "## Next Task",
            "- TASK261: EXHIBITIONS-TEXT-CONTROLLED-OPERATION-START-WEEKLY-SYNC-DUAL-LANE",
        ]
    )
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(
        "[task260] "
        f"run_id={run_id} checks={len(checks)} blocker_fail={len(blocker_fails)} warning_fail={len(warning_fails)} "
        f"boundary={boundary_breach_count} integrity_clear={integrity_clear} decision={decision}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
