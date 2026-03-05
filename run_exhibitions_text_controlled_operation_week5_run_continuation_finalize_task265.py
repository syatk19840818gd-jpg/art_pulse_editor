from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_utc_iso(value: str) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


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
        description="Finalize TASK265 week5 run and holding recheck readiness artifacts"
    )
    parser.add_argument(
        "--ready-summary-json",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_operation_week5_run_and_holding_recheck_scheduling_ready_summary_task265.json",
    )
    parser.add_argument(
        "--escalate-summary-json",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_operation_week5_run_and_holding_recheck_scheduling_escalate_summary_task265.json",
    )
    parser.add_argument(
        "--preflight-csv",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_operation_week5_run_and_holding_recheck_scheduling_preflight_task265.csv",
    )
    parser.add_argument(
        "--backup-log-json",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_operation_week5_run_and_holding_recheck_scheduling_backup_log_task265.json",
    )
    parser.add_argument(
        "--ready-manifest-json",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_operation_week5_run_and_holding_recheck_scheduling_ready_manifest_task265.json",
    )
    parser.add_argument(
        "--escalate-manifest-json",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_operation_week5_run_and_holding_recheck_scheduling_escalate_manifest_task265.json",
    )
    parser.add_argument(
        "--holding-set-csv",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_carry_forward_holding_set_task242.csv",
    )
    parser.add_argument(
        "--previous-holding-schedule-json",
        default="data/phase1_seed10/logs/holding_recheck_readiness_task264.json",
    )
    parser.add_argument(
        "--previous-week-summary-json",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_operation_week4_run_and_holding_recheck_scheduling_summary_task264.json",
    )
    parser.add_argument("--output-dir", default="data/phase1_seed10/logs")
    return parser.parse_args()


def _extract_task_num(text: str) -> int:
    match = re.match(r"^task(\d+)_", str(text or "").strip())
    return int(match.group(1)) if match else 0


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ready = read_json(Path(args.ready_summary_json), default={})
    escalate = read_json(Path(args.escalate_summary_json), default={})
    preflight_rows = read_csv(Path(args.preflight_csv))
    backup = read_json(Path(args.backup_log_json), default={})
    ready_manifest = read_json(Path(args.ready_manifest_json), default={})
    escalate_manifest = read_json(Path(args.escalate_manifest_json), default={})
    holding_rows = read_csv(Path(args.holding_set_csv))
    previous_holding_schedule = read_json(Path(args.previous_holding_schedule_json), default={})
    previous_week_summary = read_json(Path(args.previous_week_summary_json), default={})

    run_id = str(ready.get("run_id") or "").strip()
    decision = str(ready.get("go_hold_decision") or "").strip()

    ready_result = dict(ready.get("ready_restart_result") or {})
    escalate_result = dict(escalate.get("escalate_lane_result") or {})
    common = dict(ready.get("common_checks") or {})
    same_noop = dict(ready.get("same_run_noop_dry_check") or {})
    preflight = dict(ready.get("preflight") or {})
    restore = dict(ready.get("restore_info") or {})

    stage_rows: list[dict[str, Any]] = []

    def add_stage(step: int, step_id: str, passed: bool, detail: str) -> None:
        stage_rows.append(
            {
                "step_order": step,
                "step_id": step_id,
                "status": "PASS" if passed else "FAIL",
                "detail": detail,
            }
        )

    add_stage(
        1,
        "RUN_START_VALIDATION",
        all(
            [
                int(ready_result.get("ready_input_count", 0)) == 48,
                int(ready_result.get("excluded_escalate_count", 0)) == 4,
                int(ready_result.get("excluded_holding_count", 0)) == 17,
                int(ready_result.get("excluded_reject_count", 0)) == 0,
            ]
        ),
        "READY48/ESCALATE4/HOLDING17/REJECT0 boundary confirmed",
    )
    add_stage(
        2,
        "PREFLIGHT",
        int(preflight.get("blocker_fail_count", 1)) == 0,
        f"pass={preflight.get('pass_count', 0)}/{preflight.get('check_total', 0)}",
    )
    add_stage(
        3,
        "BACKUP",
        bool(backup.get("backup_created", False)) and bool(backup.get("backup_hash_match", False)),
        f"backup_created={backup.get('backup_created', False)} hash_match={backup.get('backup_hash_match', False)}",
    )
    add_stage(
        4,
        "READY_LANE_EXECUTION",
        all(
            [
                int(ready_result.get("ready_input_count", 0)) == 48,
                int(common.get("boundary_breach_count", 1)) == 0,
                bool(common.get("integrity_clear", False)),
            ]
        ),
        f"ready_input={ready_result.get('ready_input_count', 0)} boundary={common.get('boundary_breach_count', 0)}",
    )
    add_stage(
        5,
        "ESCALATE_LANE_EXECUTION",
        int(escalate_result.get("escalate_lane_count", 0)) == 4,
        f"escalate_input={escalate_result.get('escalate_lane_count', 0)}",
    )
    add_stage(
        6,
        "POST_RUN_VERIFICATION",
        all(
            [
                int(common.get("boundary_breach_count", 1)) == 0,
                int(common.get("coverage_review_count", 1)) == 0,
                int(common.get("reject_candidate_count", 1)) == 0,
                int(common.get("join_blocker_count", 1)) == 0,
                int(escalate_result.get("escalate_blocker_count", 1)) == 0,
                int(ready.get("temporal_gap_count", 1)) == 0,
                int(same_noop.get("idempotent_noop_count", 0)) == 4,
            ]
        ),
        (
            f"gap={ready.get('temporal_gap_count', 0)} "
            f"escalate_blocker={escalate_result.get('escalate_blocker_count', 0)} "
            f"noop={same_noop.get('idempotent_noop_count', 0)}"
        ),
    )
    add_stage(
        7,
        "HOLD_RESTORE_DECISION",
        (not bool(restore.get("restore_executed", False))) and decision == "CONTROLLED_OPERATION_WEEK5_SUCCESS",
        f"restore={restore.get('restore_executed', False)} decision={decision}",
    )

    current_task_num = _extract_task_num(run_id)
    next_recheck_trigger_run = str(previous_holding_schedule.get("next_recheck_trigger_run") or "task266_*")
    next_trigger_task_num = _extract_task_num(next_recheck_trigger_run)
    next_recheck_trigger_reached = next_trigger_task_num > 0 and current_task_num >= next_trigger_task_num

    previous_created_at = parse_utc_iso(str(previous_holding_schedule.get("created_at") or ""))
    now_utc = datetime.now(timezone.utc)
    monthly_backstop_due = False
    if previous_created_at is not None:
        monthly_backstop_due = (now_utc - previous_created_at).days >= 30

    previous_lane_counts = dict(previous_week_summary.get("lane_counts") or {})
    previous_ready_count = int(previous_lane_counts.get("ready_lane", ready_result.get("ready_input_count", 0)))
    previous_escalate_count = int(
        previous_lane_counts.get("escalate_lane", escalate_result.get("escalate_lane_count", 0))
    )
    current_ready_count = int(ready_result.get("ready_input_count", 0))
    current_escalate_count = int(escalate_result.get("escalate_lane_count", 0))

    ready_drop_ratio = 0.0
    if previous_ready_count > 0:
        ready_drop_ratio = max(0.0, (previous_ready_count - current_ready_count) / previous_ready_count)
    early_ready_drop_fired = ready_drop_ratio >= 0.10
    early_escalate_increase_fired = (current_escalate_count - previous_escalate_count) >= 2
    early_new_stable_source_fired = False
    early_trigger_fired = any([early_ready_drop_fired, early_escalate_increase_fired, early_new_stable_source_fired])

    holding_recheck_due = any([next_recheck_trigger_reached, monthly_backstop_due, early_trigger_fired])
    holding_readiness_conclusion = "HOLDING_RECHECK_DUE" if holding_recheck_due else "HOLDING_RECHECK_NOT_DUE"
    holding_recheck_readiness = {
        "artifact": "holding_recheck_readiness_task265",
        "task": "TASK265",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "current_holding_count": len(holding_rows),
        "next_recheck_trigger_run": next_recheck_trigger_run,
        "next_recheck_trigger_reached": next_recheck_trigger_reached,
        "monthly_backstop_due": monthly_backstop_due,
        "monthly_backstop_policy": str(
            previous_holding_schedule.get("monthly_backstop") or "run monthly recheck if 4-run trigger not reached earlier"
        ),
        "early_trigger_evaluation": {
            "ready_drop_ratio": round(ready_drop_ratio, 6),
            "ready_drop_threshold": 0.10,
            "ready_drop_fired": early_ready_drop_fired,
            "escalate_increase_count": current_escalate_count - previous_escalate_count,
            "escalate_increase_threshold": 2,
            "escalate_increase_fired": early_escalate_increase_fired,
            "new_stable_source_fired": early_new_stable_source_fired,
            "early_trigger_fired": early_trigger_fired,
        },
        "recheck_target_bundle_policy": {
            "target_bundle": "HOLDING_LANE only",
            "do_not_mix_with": ["READY_LANE", "ESCALATE_SEPARATE_LANE", "REJECT_LANE"],
            "execution_note": "readiness check only in TASK265; no holding re-evaluation execution in this run",
        },
        "conclusion": holding_readiness_conclusion,
    }

    stage8_passed = len(holding_rows) == 17 and holding_readiness_conclusion == "HOLDING_RECHECK_NOT_DUE"
    add_stage(
        8,
        "HOLDING_RECHECK_READINESS_CHECK",
        stage8_passed,
        (
            f"holding_count={len(holding_rows)} "
            f"next_trigger_reached={next_recheck_trigger_reached} "
            f"early_trigger={early_trigger_fired} monthly_due={monthly_backstop_due}"
        ),
    )
    if decision == "CONTROLLED_OPERATION_WEEK5_SUCCESS":
        if holding_recheck_due:
            decision = "HOLD_FOR_HOLDING_RECHECK_TRIGGER"
        elif len(holding_rows) != 17:
            decision = "HOLD_FOR_RUNBOOK_DEVIATION"

    add_stage(
        9,
        "LOG_MANIFEST_CONFIRM",
        bool(ready_manifest) and bool(escalate_manifest),
        "ready/escalate manifest present",
    )

    post_run_verification = {
        "artifact": "exhibitions_text_controlled_operation_week5_run_and_holding_recheck_scheduling_post_run_verification",
        "task": "TASK265",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "ready_side": {
            "ready_input_count": ready_result.get("ready_input_count", 0),
            "boundary_breach_count": common.get("boundary_breach_count", 0),
            "integrity_clear": common.get("integrity_clear", False),
        },
        "escalate_side": {
            "escalate_lane_count": escalate_result.get("escalate_lane_count", 0),
            "persistence_advanced_count": escalate_result.get("persistence_advanced_count", 0),
            "ratio_two_consecutive_fired_count": escalate_result.get("ratio_two_consecutive_fired_count", 0),
            "route_degradation_fired_count": escalate_result.get("route_degradation_fired_count", 0),
            "escalate_blocker_count": escalate_result.get("escalate_blocker_count", 0),
        },
        "common": {
            "temporal_gap_count": ready.get("temporal_gap_count", 0),
            "same_run_noop_dry_check": same_noop.get("idempotent_noop_count", 0),
            "coverage_review_count": common.get("coverage_review_count", 0),
            "reject_candidate_count": common.get("reject_candidate_count", 0),
            "join_blocker_count": common.get("join_blocker_count", 0),
        },
        "pass": all(r["status"] == "PASS" for r in stage_rows if 4 <= int(r["step_order"]) <= 7),
    }

    summary = {
        "artifact": "exhibitions_text_controlled_operation_week5_run_and_holding_recheck_scheduling_summary",
        "task": "TASK265",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "initial_start": False,
        "weekly_run_phase": "WEEK5",
        "runbook_stage_status": stage_rows,
        "preflight": preflight,
        "lane_counts": {
            "ready_lane": ready_result.get("ready_input_count", 0),
            "escalate_lane": escalate_result.get("escalate_lane_count", 0),
            "holding_excluded": ready_result.get("excluded_holding_count", 0),
            "reject_excluded": ready_result.get("excluded_reject_count", 0),
        },
        "backup": backup,
        "post_run_verification": post_run_verification,
        "holding_recheck_readiness": holding_recheck_readiness,
        "restore": restore,
        "go_hold_decision": decision,
        "blocker_labels": list(ready.get("blocker_labels") or []),
        "next_task_recommendation": {
            "id": "TASK266",
            "title": "EXHIBITIONS-TEXT-CONTROLLED-OPERATION-WEEK6-RUN-CONTINUATION",
            "ja": "Execute week-6 synchronized dual-lane run (task266 boundary) while keeping holding readiness checks",
        },
    }

    summary_path = output_dir / "exhibitions_text_controlled_operation_week5_run_and_holding_recheck_scheduling_summary_task265.json"
    post_verification_path = (
        output_dir / "exhibitions_text_controlled_operation_week5_run_and_holding_recheck_scheduling_post_run_verification_task265.json"
    )
    stage_csv_path = (
        output_dir / "exhibitions_text_controlled_operation_week5_run_and_holding_recheck_scheduling_runbook_stage_result_task265.csv"
    )
    holding_readiness_json_path = output_dir / "holding_recheck_readiness_task265.json"
    holding_readiness_csv_path = output_dir / "holding_recheck_readiness_task265.csv"
    manifest_path = output_dir / "exhibitions_text_controlled_operation_week5_run_and_holding_recheck_scheduling_manifest_task265.json"
    report_path = output_dir / "exhibitions_text_controlled_operation_week5_run_and_holding_recheck_scheduling_task265.md"

    write_json(summary_path, summary)
    write_json(post_verification_path, post_run_verification)
    write_csv(stage_csv_path, stage_rows, ["step_order", "step_id", "status", "detail"])
    write_json(holding_readiness_json_path, holding_recheck_readiness)
    write_csv(
        holding_readiness_csv_path,
        [
            {
                "run_id": run_id,
                "current_holding_count": holding_recheck_readiness["current_holding_count"],
                "next_recheck_trigger_run": holding_recheck_readiness["next_recheck_trigger_run"],
                "next_recheck_trigger_reached": holding_recheck_readiness["next_recheck_trigger_reached"],
                "monthly_backstop_due": holding_recheck_readiness["monthly_backstop_due"],
                "early_trigger_fired": holding_recheck_readiness["early_trigger_evaluation"]["early_trigger_fired"],
                "ready_drop_ratio": holding_recheck_readiness["early_trigger_evaluation"]["ready_drop_ratio"],
                "escalate_increase_count": holding_recheck_readiness["early_trigger_evaluation"]["escalate_increase_count"],
                "conclusion": holding_recheck_readiness["conclusion"],
            }
        ],
        [
            "run_id",
            "current_holding_count",
            "next_recheck_trigger_run",
            "next_recheck_trigger_reached",
            "monthly_backstop_due",
            "early_trigger_fired",
            "ready_drop_ratio",
            "escalate_increase_count",
            "conclusion",
        ],
    )

    manifest = {
        "artifact": "exhibitions_text_controlled_operation_week5_run_and_holding_recheck_scheduling_manifest",
        "task": "TASK265",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "decision": decision,
        "stage_pass_count": sum(1 for r in stage_rows if r["status"] == "PASS"),
        "stage_fail_count": sum(1 for r in stage_rows if r["status"] == "FAIL"),
        "outputs": {
            "summary_json": str(summary_path),
            "post_run_verification_json": str(post_verification_path),
            "runbook_stage_result_csv": str(stage_csv_path),
            "holding_readiness_json": str(holding_readiness_json_path),
            "holding_readiness_csv": str(holding_readiness_csv_path),
            "report_md": str(report_path),
        },
    }
    write_json(manifest_path, manifest)

    report_lines = [
        "# TASK265 Controlled Operation Week5 Run And Holding Recheck Readiness",
        "",
        f"- run_id={run_id}",
        f"- decision={decision}",
        "",
        "## runbook_steps_plus_holding_readiness",
    ]
    for row in stage_rows:
        report_lines.append(f"- {row['step_order']}. {row['step_id']}: {row['status']} ({row['detail']})")
    report_lines.extend(
        [
            "",
            "## holding_readiness",
            f"- current_holding_count={holding_recheck_readiness['current_holding_count']}",
            f"- next_recheck_trigger_run={holding_recheck_readiness['next_recheck_trigger_run']}",
            f"- next_recheck_trigger_reached={holding_recheck_readiness['next_recheck_trigger_reached']}",
            f"- early_trigger_fired={holding_recheck_readiness['early_trigger_evaluation']['early_trigger_fired']}",
            f"- monthly_backstop_due={holding_recheck_readiness['monthly_backstop_due']}",
            f"- conclusion={holding_recheck_readiness['conclusion']}",
        ]
    )
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(
        "[task265-finalize] "
        f"run_id={run_id} stage_pass={sum(1 for r in stage_rows if r['status']=='PASS')} "
        f"stage_fail={sum(1 for r in stage_rows if r['status']=='FAIL')} decision={decision}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
