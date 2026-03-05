from __future__ import annotations

import argparse
import csv
import json
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
    parser = argparse.ArgumentParser(description="Finalize TASK261 runbook-stage and post-run artifacts")
    parser.add_argument(
        "--ready-summary-json",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_operation_start_weekly_sync_dual_lane_ready_summary_task261.json",
    )
    parser.add_argument(
        "--escalate-summary-json",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_operation_start_weekly_sync_dual_lane_escalate_summary_task261.json",
    )
    parser.add_argument(
        "--preflight-csv",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_operation_start_weekly_sync_dual_lane_preflight_task261.csv",
    )
    parser.add_argument(
        "--backup-log-json",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_operation_start_weekly_sync_dual_lane_backup_log_task261.json",
    )
    parser.add_argument(
        "--ready-manifest-json",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_operation_start_weekly_sync_dual_lane_ready_manifest_task261.json",
    )
    parser.add_argument(
        "--escalate-manifest-json",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_operation_start_weekly_sync_dual_lane_escalate_manifest_task261.json",
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
        (not bool(restore.get("restore_executed", False))) and decision == "CONTROLLED_OPERATION_STARTED_SUCCESSFULLY",
        f"restore={restore.get('restore_executed', False)} decision={decision}",
    )
    add_stage(
        8,
        "LOG_MANIFEST_CONFIRM",
        bool(ready_manifest) and bool(escalate_manifest),
        "ready/escalate manifest present",
    )

    post_run_verification = {
        "artifact": "exhibitions_text_controlled_operation_start_weekly_sync_dual_lane_post_run_verification",
        "task": "TASK261",
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
        "artifact": "exhibitions_text_controlled_operation_start_weekly_sync_dual_lane_summary",
        "task": "TASK261",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "initial_start": True,
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
        "restore": restore,
        "go_hold_decision": decision,
        "blocker_labels": list(ready.get("blocker_labels") or []),
        "next_task_recommendation": {
            "id": "TASK262",
            "title": "EXHIBITIONS-TEXT-CONTROLLED-OPERATION-WEEK2-RUN-AND-HOLDING-RECHECK-SCHEDULING",
            "ja": "Execute week-2 synchronized dual-lane run and start holding-lane reevaluation schedule tracking",
        },
    }

    summary_path = output_dir / "exhibitions_text_controlled_operation_start_weekly_sync_dual_lane_summary_task261.json"
    post_verification_path = output_dir / "exhibitions_text_controlled_operation_start_weekly_sync_dual_lane_post_run_verification_task261.json"
    stage_csv_path = output_dir / "exhibitions_text_controlled_operation_start_weekly_sync_dual_lane_runbook_stage_result_task261.csv"
    manifest_path = output_dir / "exhibitions_text_controlled_operation_start_weekly_sync_dual_lane_manifest_task261.json"
    report_path = output_dir / "exhibitions_text_controlled_operation_start_weekly_sync_dual_lane_task261.md"

    write_json(summary_path, summary)
    write_json(post_verification_path, post_run_verification)
    write_csv(stage_csv_path, stage_rows, ["step_order", "step_id", "status", "detail"])

    manifest = {
        "artifact": "exhibitions_text_controlled_operation_start_weekly_sync_dual_lane_manifest",
        "task": "TASK261",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "decision": decision,
        "stage_pass_count": sum(1 for r in stage_rows if r["status"] == "PASS"),
        "stage_fail_count": sum(1 for r in stage_rows if r["status"] == "FAIL"),
        "outputs": {
            "summary_json": str(summary_path),
            "post_run_verification_json": str(post_verification_path),
            "runbook_stage_result_csv": str(stage_csv_path),
            "report_md": str(report_path),
        },
    }
    write_json(manifest_path, manifest)

    report_lines = [
        "# TASK261 Controlled Operation Start Weekly Sync Dual Lane",
        "",
        f"- run_id={run_id}",
        f"- decision={decision}",
        f"- initial_start=true",
        "",
        "## runbook_8_steps",
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
        ]
    )
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(
        "[task261-finalize] "
        f"run_id={run_id} stage_pass={sum(1 for r in stage_rows if r['status']=='PASS')} "
        f"stage_fail={sum(1 for r in stage_rows if r['status']=='FAIL')} decision={decision}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
