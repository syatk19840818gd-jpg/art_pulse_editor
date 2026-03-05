from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY = "READY_FOR_LIVE_NEXT_RUN_EXECUTION"
HOLD_PRECHECK = "HOLD_FOR_LIVE_STATE_PRECHECK_FIX"
HOLD_FAILSAFE = "HOLD_FOR_FAILSAFE_TUNING"


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


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def row_signature(row: dict[str, str]) -> str:
    return "||".join(
        [
            str(row.get("gallery_name_en") or "").strip(),
            str(row.get("fair_slug") or "").strip(),
            str(row.get("target_year") or "").strip(),
            str(row.get("source_url") or "").strip(),
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TASK248 Exhibitions Text carry-forward phase6 live next-run prep")
    parser.add_argument(
        "--state-latest-json",
        default="data/phase1_seed10/logs/exhibitions_text_monitored_state_latest.json",
    )
    parser.add_argument(
        "--task243-summary-json",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_carry_forward_continuation_phase1_summary_task243.json",
    )
    parser.add_argument(
        "--task246-summary-json",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_carry_forward_continuation_phase4_summary_task246.json",
    )
    parser.add_argument(
        "--task247-summary-json",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_carry_forward_continuation_phase5_summary_task247.json",
    )
    parser.add_argument(
        "--continuation-input-csv",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_carry_forward_continuation_input_task243.csv",
    )
    parser.add_argument(
        "--holding-set-csv",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_carry_forward_holding_set_task242.csv",
    )
    parser.add_argument(
        "--escalate-set-csv",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_carry_forward_escalate_set_task242.csv",
    )
    parser.add_argument(
        "--reject-set-csv",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_carry_forward_reject_set_task242.csv",
    )
    parser.add_argument("--output-dir", default="data/phase1_seed10/logs")
    parser.add_argument("--trash-root", default="_trash")
    parser.add_argument("--run-id", default="")
    return parser.parse_args()


def _check_row(label: str, actual: Any, expected: Any, is_blocker: bool) -> dict[str, Any]:
    passed = actual == expected
    return {
        "check_label": label,
        "actual": actual,
        "expected": expected,
        "status": "PASS" if passed else "FAIL",
        "is_blocker": is_blocker,
    }


def main() -> int:
    args = parse_args()
    run_id = args.run_id.strip() or datetime.now(timezone.utc).strftime("task248_%Y%m%dT%H%M%SZ")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    state_path = Path(args.state_latest_json)
    task243_summary = read_json(Path(args.task243_summary_json), default={})
    task246_summary = read_json(Path(args.task246_summary_json), default={})
    task247_summary = read_json(Path(args.task247_summary_json), default={})
    continuation_rows = read_csv(Path(args.continuation_input_csv))
    holding_rows = read_csv(Path(args.holding_set_csv))
    escalate_rows = read_csv(Path(args.escalate_set_csv))
    reject_rows = read_csv(Path(args.reject_set_csv))

    state_exists = state_path.exists()
    state_hash_before = file_sha256(state_path) if state_exists else ""
    state = read_json(state_path, default={})

    baseline_run_id = str(state.get("baseline_run_id") or "").strip()
    baseline_scope_hash = str(state.get("baseline_scope_hash") or "").strip()
    state_rules = dict(state.get("state_rules") or {})
    no_op_rule = str(state_rules.get("same_run_id_reingest_rule") or "").strip().lower()
    no_op_rule_present = "no-op" in no_op_rule

    ready_count = sum(
        1 for row in continuation_rows if str(row.get("continuation_stream") or "").strip() == "READY"
    )
    monitored_count = sum(
        1 for row in continuation_rows if str(row.get("continuation_stream") or "").strip() == "MONITORED"
    )
    invalid_stream_count = sum(
        1
        for row in continuation_rows
        if str(row.get("continuation_stream") or "").strip() not in {"READY", "MONITORED"}
    )

    continuation_signatures = {row_signature(row) for row in continuation_rows}
    excluded_signatures = {row_signature(row) for row in (holding_rows + escalate_rows + reject_rows)}
    boundary_breach_count = len(continuation_signatures & excluded_signatures)

    integrity246 = dict(task246_summary.get("integrity_checks") or {})
    coverage_review_count = int(integrity246.get("coverage_review_count", 0))
    reject_candidate_count = int(integrity246.get("reject_candidate_count", 0))
    join_blocker_count = int(integrity246.get("join_blocker_count", 0))
    escalate_set_count = int(integrity246.get("escalate_set_count", 0))

    trial_validation = dict(task247_summary.get("trial_state_validation") or {})
    case_results = dict(task247_summary.get("case_results") or {})
    trial_all_cases_ok = all(bool(v) for v in case_results.values()) and bool(case_results)
    trial_authoritative_unchanged = bool(trial_validation.get("authoritative_state_unchanged", False))
    trial_temporal_gap_count = int(trial_validation.get("temporal_gap_count", 0))
    trial_boundary_breach_count = int(trial_validation.get("boundary_breach_count", 0))

    checklist_rows = [
        _check_row("AUTHORITATIVE_STATE_EXISTS", state_exists, True, True),
        _check_row("BASELINE_RUN_ID_PRESENT", bool(baseline_run_id), True, True),
        _check_row("BASELINE_SCOPE_HASH_PRESENT", bool(baseline_scope_hash), True, True),
        _check_row("CONTINUATION_STREAM_INVALID_COUNT", invalid_stream_count, 0, True),
        _check_row("BOUNDARY_BREACH_COUNT", boundary_breach_count, 0, True),
        _check_row("INTEGRITY_COVERAGE_REVIEW_COUNT", coverage_review_count, 0, True),
        _check_row("INTEGRITY_REJECT_COUNT", reject_candidate_count, 0, True),
        _check_row("INTEGRITY_JOIN_BLOCKER_COUNT", join_blocker_count, 0, True),
        _check_row("INTEGRITY_ESCALATE_SET_COUNT", escalate_set_count, 0, True),
        _check_row("SAME_RUN_NOOP_RULE_PRESENT", no_op_rule_present, True, True),
        _check_row("TASK247_TRIAL_CASES_ALL_OK", trial_all_cases_ok, True, True),
        _check_row("TASK247_AUTHORITATIVE_UNCHANGED", trial_authoritative_unchanged, True, True),
        _check_row("TASK247_TEMPORAL_GAP_COUNT", trial_temporal_gap_count, 0, True),
        _check_row("TASK247_BOUNDARY_BREACH_COUNT", trial_boundary_breach_count, 0, True),
    ]

    blocker_fail_count = sum(
        1 for row in checklist_rows if bool(row["is_blocker"]) and str(row["status"]) == "FAIL"
    )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = Path(args.trash_root) / f"{timestamp}_pre_live_monitored_state_{run_id}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_state_path = backup_dir / state_path.name
    backup_created = False
    backup_hash = ""
    backup_hash_match = False
    if state_exists:
        shutil.copy2(state_path, backup_state_path)
        backup_created = backup_state_path.exists()
        if backup_created:
            backup_hash = file_sha256(backup_state_path)
            backup_hash_match = backup_hash == state_hash_before

    state_hash_after = file_sha256(state_path) if state_exists else ""
    authoritative_state_unchanged_in_prep = state_hash_before == state_hash_after

    live_update_allowed_conditions = [
        "authoritative_state_exists=true",
        "baseline_run_id and baseline_scope_hash present",
        "continuation stream includes READY/MONITORED only",
        "boundary_breach_count=0",
        "coverage_review_count=0 and reject_count=0 and join_blocker_count=0 and escalate_set_count=0",
        "same-run reingest no-op rule present",
        "backup_created=true and backup_hash_match=true",
    ]
    no_op_conditions = [
        "incoming_run_id already exists in ingested_snapshot_run_ids",
        "same monitor_key set with same run_id re-ingest attempt",
    ]
    restore_conditions = [
        "state write/update failure during live update",
        "temporal_gap_count > 0 in live update pre-commit checks",
        "boundary_breach_count > 0",
        "coverage/reject/join_blocker/escalate_set any > 0",
        "post-write state hash mismatch or corrupted JSON",
    ]
    hold_conditions = [
        "missing authoritative state or missing baseline fields",
        "same-run no-op rule missing",
        "trial validation failed in TASK247 baseline evidence",
        "backup not created or backup hash mismatch",
    ]

    failsafe_policy_coherent = all(
        [live_update_allowed_conditions, no_op_conditions, restore_conditions, hold_conditions]
    )

    if blocker_fail_count > 0 or not authoritative_state_unchanged_in_prep or not backup_created or not backup_hash_match:
        decision = HOLD_PRECHECK
    elif not failsafe_policy_coherent:
        decision = HOLD_FAILSAFE
    else:
        decision = READY

    blocker_labels: list[str] = []
    if blocker_fail_count > 0:
        blocker_labels.append("PREFLIGHT_BLOCKER_FAILED")
    if not authoritative_state_unchanged_in_prep:
        blocker_labels.append("AUTHORITATIVE_STATE_MUTATED_DURING_PREP")
    if not backup_created:
        blocker_labels.append("BACKUP_NOT_CREATED")
    if backup_created and not backup_hash_match:
        blocker_labels.append("BACKUP_HASH_MISMATCH")
    if not failsafe_policy_coherent:
        blocker_labels.append("FAILSAFE_POLICY_INCOMPLETE")

    summary = {
        "artifact": "exhibitions_text_carry_forward_phase6_live_next_run_prep_summary",
        "task": "TASK248",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "inputs": {
            "authoritative_state_latest_json": str(state_path),
            "task243_summary_json": str(Path(args.task243_summary_json)),
            "task246_summary_json": str(Path(args.task246_summary_json)),
            "task247_summary_json": str(Path(args.task247_summary_json)),
            "continuation_input_csv": str(Path(args.continuation_input_csv)),
            "holding_set_csv": str(Path(args.holding_set_csv)),
            "escalate_set_csv": str(Path(args.escalate_set_csv)),
            "reject_set_csv": str(Path(args.reject_set_csv)),
        },
        "continuation_context": {
            "continuation_input_total": len(continuation_rows),
            "ready_count": ready_count,
            "monitored_count": monitored_count,
            "holding_excluded_count": len(holding_rows),
            "escalate_excluded_count": len(escalate_rows),
            "reject_excluded_count": len(reject_rows),
            "boundary_breach_count": boundary_breach_count,
            "baseline_run_id": baseline_run_id,
            "baseline_scope_hash": baseline_scope_hash,
        },
        "preflight_results": {
            "checklist_total": len(checklist_rows),
            "checklist_pass_count": sum(1 for row in checklist_rows if row["status"] == "PASS"),
            "checklist_fail_count": sum(1 for row in checklist_rows if row["status"] == "FAIL"),
            "blocker_fail_count": blocker_fail_count,
            "same_run_noop_rule_present": no_op_rule_present,
            "trial_all_cases_ok": trial_all_cases_ok,
            "trial_authoritative_unchanged": trial_authoritative_unchanged,
            "trial_temporal_gap_count": trial_temporal_gap_count,
        },
        "backup_restore_plan": {
            "backup_root": str(backup_dir),
            "backup_state_path": str(backup_state_path),
            "backup_created": backup_created,
            "state_hash_before": state_hash_before,
            "backup_hash": backup_hash,
            "backup_hash_match": backup_hash_match,
            "authoritative_state_unchanged_in_prep": authoritative_state_unchanged_in_prep,
            "restore_conditions": restore_conditions,
            "restore_target_path": str(state_path),
            "restore_source_path": str(backup_state_path),
            "restore_performed": False,
        },
        "fail_safe_conditions": {
            "live_update_allowed_when": live_update_allowed_conditions,
            "no_op_when": no_op_conditions,
            "restore_when": restore_conditions,
            "hold_when": hold_conditions,
            "temporal_gap_blocker_condition": "temporal_gap_count > 0",
            "failsafe_policy_coherent": failsafe_policy_coherent,
        },
        "integrity_checks": {
            "coverage_review_count": coverage_review_count,
            "reject_candidate_count": reject_candidate_count,
            "join_blocker_count": join_blocker_count,
            "escalate_set_count": escalate_set_count,
            "boundary_breach_count": boundary_breach_count,
            "proposal_only": True,
            "formal_untouched": True,
            "adoption_executed": False,
            "rollback_executed": False,
            "join_contract_changed": False,
            "anti_mixing_enforced": True,
            "authoritative_state_advanced": False,
        },
        "go_hold_decision": decision,
        "blocker_labels": blocker_labels,
        "next_task_recommendation": {
            "id": "TASK249",
            "title": "EXHIBITIONS-TEXT-CARRY-FORWARD-PHASE7-LIVE-NEXT-RUN-CONTINUATION",
            "ja": "Execute first live next-run continuation with authoritative monitored state update and preflight/backup failsafes",
        },
    }

    checklist_path = output_dir / "exhibitions_text_carry_forward_phase6_live_next_run_prep_checklist_task248.csv"
    checklist_fields = ["check_label", "actual", "expected", "status", "is_blocker"]
    write_csv(checklist_path, checklist_rows, checklist_fields)

    summary_path = output_dir / "exhibitions_text_carry_forward_phase6_live_next_run_prep_summary_task248.json"
    manifest_path = output_dir / "exhibitions_text_carry_forward_phase6_live_next_run_prep_manifest_task248.json"
    backup_plan_path = output_dir / "exhibitions_text_carry_forward_phase6_live_next_run_backup_plan_task248.json"
    report_path = output_dir / "exhibitions_text_carry_forward_phase6_live_next_run_prep_task248.md"

    write_json(summary_path, summary)
    write_json(backup_plan_path, summary["backup_restore_plan"])

    manifest = {
        "artifact": "exhibitions_text_carry_forward_phase6_live_next_run_prep_manifest",
        "task": "TASK248",
        "run_id": run_id,
        "inputs": summary["inputs"],
        "outputs": {
            "summary_json": str(summary_path),
            "checklist_csv": str(checklist_path),
            "backup_plan_json": str(backup_plan_path),
            "manifest_json": str(manifest_path),
            "report_md": str(report_path),
        },
        "backup_root": str(backup_dir),
        "integrity_checks": summary["integrity_checks"],
    }
    write_json(manifest_path, manifest)

    report_lines = [
        "# TASK248 Exhibitions Text Carry-Forward Phase6 Live Next-Run Prep",
        "",
        "## preflight",
        f"- continuation_input_total={len(continuation_rows)} (READY={ready_count}, MONITORED={monitored_count})",
        f"- boundary_breach_count={boundary_breach_count}",
        f"- coverage_review_count={coverage_review_count}",
        f"- reject_candidate_count={reject_candidate_count}",
        f"- join_blocker_count={join_blocker_count}",
        f"- escalate_set_count={escalate_set_count}",
        f"- same_run_noop_rule_present={no_op_rule_present}",
        "",
        "## backup_restore",
        f"- backup_created={backup_created}",
        f"- backup_root={backup_dir}",
        f"- backup_hash_match={backup_hash_match}",
        f"- authoritative_state_unchanged_in_prep={authoritative_state_unchanged_in_prep}",
        "",
        "## decision",
        f"- go_hold_decision={decision}",
        f"- blocker_labels={blocker_labels}",
    ]
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(
        "[task248] "
        f"ready={ready_count} monitored={monitored_count} boundary_breach={boundary_breach_count} "
        f"backup_created={backup_created} backup_hash_match={backup_hash_match} "
        f"state_unchanged={authoritative_state_unchanged_in_prep} decision={decision}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
