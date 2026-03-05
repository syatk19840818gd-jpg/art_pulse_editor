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
    parser = argparse.ArgumentParser(description="Finalize TASK262 runbook-stage, post-run verification, and holding recheck scheduling artifacts")
    parser.add_argument(
        "--ready-summary-json",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_operation_week2_run_and_holding_recheck_scheduling_ready_summary_task262.json",
    )
    parser.add_argument(
        "--escalate-summary-json",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_operation_week2_run_and_holding_recheck_scheduling_escalate_summary_task262.json",
    )
    parser.add_argument(
        "--preflight-csv",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_operation_week2_run_and_holding_recheck_scheduling_preflight_task262.csv",
    )
    parser.add_argument(
        "--backup-log-json",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_operation_week2_run_and_holding_recheck_scheduling_backup_log_task262.json",
    )
    parser.add_argument(
        "--ready-manifest-json",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_operation_week2_run_and_holding_recheck_scheduling_ready_manifest_task262.json",
    )
    parser.add_argument(
        "--escalate-manifest-json",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_operation_week2_run_and_holding_recheck_scheduling_escalate_manifest_task262.json",
    )
    parser.add_argument(
        "--holding-set-csv",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_carry_forward_holding_set_task242.csv",
    )
    parser.add_argument("--output-dir", default="data/phase1_seed10/logs")
    return parser.parse_args()


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
        (not bool(restore.get("restore_executed", False))) and decision == "CONTROLLED_OPERATION_WEEK2_SUCCESS",
        f"restore={restore.get('restore_executed', False)} decision={decision}",
    )
    m = re.match(r"^task(\d+)_", run_id)
    task_num = int(m.group(1)) if m else 0
    next_recheck_task_num = task_num + 4 if task_num > 0 else 0
    next_recheck_trigger_run = f"task{next_recheck_task_num}_*" if next_recheck_task_num > 0 else "every_4_runs_from_current"
    holding_schedule = {
        "artifact": "holding_recheck_schedule_task262",
        "task": "TASK262",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "current_holding_count": len(holding_rows),
        "next_recheck_trigger_run": next_recheck_trigger_run,
        "cadence_basis": "every 4 synchronized runs",
        "monthly_backstop": "run monthly recheck if 4-run trigger not reached earlier",
        "early_trigger_conditions": [
            "READY lane count drop >= 10% vs recent monthly baseline",
            "ESCALATE lane count increase >= 2",
            "new stable source evidence observed for existing HOLDING records",
        ],
        "recheck_target_bundle_policy": {
            "target_bundle": "HOLDING_LANE only",
            "do_not_mix_with": ["READY_LANE", "ESCALATE_SEPARATE_LANE", "REJECT_LANE"],
            "execution_note": "scheduling only in TASK262; no holding re-evaluation execution in this run",
        },
    }

    holding_schedule_ok = len(holding_rows) == 17 and bool(holding_schedule.get("next_recheck_trigger_run"))
    add_stage(
        8,
        "HOLDING_RECHECK_SCHEDULING",
        holding_schedule_ok,
        f"holding_count={len(holding_rows)} next_trigger={holding_schedule['next_recheck_trigger_run']}",
    )
    if decision == "CONTROLLED_OPERATION_WEEK2_SUCCESS" and not holding_schedule_ok:
        decision = "HOLD_FOR_HOLDING_RECHECK_SCHEDULING_GAP"
    add_stage(
        9,
        "LOG_MANIFEST_CONFIRM",
        bool(ready_manifest) and bool(escalate_manifest),
        "ready/escalate manifest present",
    )

    post_run_verification = {
        "artifact": "exhibitions_text_controlled_operation_week2_run_and_holding_recheck_scheduling_post_run_verification",
        "task": "TASK262",
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
        "pass": all(r["status"] == "PASS" for r in stage_rows if int(r["step_order"]) >= 4 and int(r["step_order"]) <= 7),
    }

    summary = {
        "artifact": "exhibitions_text_controlled_operation_week2_run_and_holding_recheck_scheduling_summary",
        "task": "TASK262",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "initial_start": False,
        "weekly_run_phase": "WEEK2",
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
        "holding_recheck_scheduling": holding_schedule,
        "restore": restore,
        "go_hold_decision": decision,
        "blocker_labels": list(ready.get("blocker_labels") or []),
        "next_task_recommendation": {
            "id": "TASK263",
            "title": "EXHIBITIONS-TEXT-CONTROLLED-OPERATION-WEEK3-RUN-OR-HOLDING-RECHECK-PREP",
            "ja": "Execute week-3 synchronized dual-lane run or trigger scheduled holding-lane reevaluation prep",
        },
    }

    summary_path = output_dir / "exhibitions_text_controlled_operation_week2_run_and_holding_recheck_scheduling_summary_task262.json"
    post_verification_path = output_dir / "exhibitions_text_controlled_operation_week2_run_and_holding_recheck_scheduling_post_run_verification_task262.json"
    stage_csv_path = output_dir / "exhibitions_text_controlled_operation_week2_run_and_holding_recheck_scheduling_runbook_stage_result_task262.csv"
    holding_schedule_json_path = output_dir / "holding_recheck_schedule_task262.json"
    holding_schedule_csv_path = output_dir / "holding_recheck_schedule_task262.csv"
    manifest_path = output_dir / "exhibitions_text_controlled_operation_week2_run_and_holding_recheck_scheduling_manifest_task262.json"
    report_path = output_dir / "exhibitions_text_controlled_operation_week2_run_and_holding_recheck_scheduling_task262.md"

    write_json(summary_path, summary)
    write_json(post_verification_path, post_run_verification)
    write_csv(stage_csv_path, stage_rows, ["step_order", "step_id", "status", "detail"])
    write_json(holding_schedule_json_path, holding_schedule)
    write_csv(
        holding_schedule_csv_path,
        [
            {
                "run_id": run_id,
                "current_holding_count": holding_schedule["current_holding_count"],
                "next_recheck_trigger_run": holding_schedule["next_recheck_trigger_run"],
                "cadence_basis": holding_schedule["cadence_basis"],
                "monthly_backstop": holding_schedule["monthly_backstop"],
                "early_trigger_1": holding_schedule["early_trigger_conditions"][0],
                "early_trigger_2": holding_schedule["early_trigger_conditions"][1],
                "early_trigger_3": holding_schedule["early_trigger_conditions"][2],
                "target_bundle": holding_schedule["recheck_target_bundle_policy"]["target_bundle"],
                "do_not_mix_with": "|".join(holding_schedule["recheck_target_bundle_policy"]["do_not_mix_with"]),
                "execution_note": holding_schedule["recheck_target_bundle_policy"]["execution_note"],
            }
        ],
        [
            "run_id",
            "current_holding_count",
            "next_recheck_trigger_run",
            "cadence_basis",
            "monthly_backstop",
            "early_trigger_1",
            "early_trigger_2",
            "early_trigger_3",
            "target_bundle",
            "do_not_mix_with",
            "execution_note",
        ],
    )

    manifest = {
        "artifact": "exhibitions_text_controlled_operation_week2_run_and_holding_recheck_scheduling_manifest",
        "task": "TASK262",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "decision": decision,
        "stage_pass_count": sum(1 for r in stage_rows if r["status"] == "PASS"),
        "stage_fail_count": sum(1 for r in stage_rows if r["status"] == "FAIL"),
        "outputs": {
            "summary_json": str(summary_path),
            "post_run_verification_json": str(post_verification_path),
            "runbook_stage_result_csv": str(stage_csv_path),
            "holding_recheck_schedule_json": str(holding_schedule_json_path),
            "holding_recheck_schedule_csv": str(holding_schedule_csv_path),
            "report_md": str(report_path),
        },
    }
    write_json(manifest_path, manifest)

    report_lines = [
        "# TASK262 Controlled Operation Week2 Run And Holding Recheck Scheduling",
        "",
        f"- run_id={run_id}",
        f"- decision={decision}",
        f"- weekly_run_phase=week2",
        "",
        "## runbook_steps_plus_holding_schedule",
    ]
    for row in stage_rows:
        report_lines.append(f"- {row['step_order']}. {row['step_id']}: {row['status']} ({row['detail']})")
    report_lines.extend(
        [
            "",
            "## post_run_verification",
            f"- ready_boundary_breach={post_run_verification['ready_side']['boundary_breach_count']}",
            f"- ready_integrity_clear={post_run_verification['ready_side']['integrity_clear']}",
            f"- escalate_blocker_count={post_run_verification['escalate_side']['escalate_blocker_count']}",
            f"- temporal_gap_count={post_run_verification['common']['temporal_gap_count']}",
            f"- same_run_noop_dry_check={post_run_verification['common']['same_run_noop_dry_check']}",
            f"- restore_executed={restore.get('restore_executed', False)}",
            "",
            "## holding_recheck_scheduling",
            f"- current_holding_count={holding_schedule['current_holding_count']}",
            f"- next_recheck_trigger_run={holding_schedule['next_recheck_trigger_run']}",
            f"- monthly_backstop={holding_schedule['monthly_backstop']}",
            f"- target_bundle={holding_schedule['recheck_target_bundle_policy']['target_bundle']}",
        ]
    )
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(
        "[task262-finalize] "
        f"run_id={run_id} stage_pass={sum(1 for r in stage_rows if r['status']=='PASS')} "
        f"stage_fail={sum(1 for r in stage_rows if r['status']=='FAIL')} decision={decision}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

