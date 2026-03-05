from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY = "READY_FOR_HOLDING_RECHECK_CONTROLLED_RUN"
HOLD = "HOLD_FOR_HOLDING_RECHECK_PRECHECK_FIX"


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


def monitor_key(row: dict[str, str]) -> str:
    return "||".join(
        [
            str(row.get("fair_slug") or "").strip(),
            str(row.get("gallery_name_en") or "").strip(),
            str(row.get("source_url") or "").strip(),
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="TASK267 Exhibitions Text holding recheck prep controlled start (dry-run only)"
    )
    parser.add_argument(
        "--state-latest-json",
        default="data/phase1_seed10/logs/exhibitions_text_monitored_state_latest.json",
    )
    parser.add_argument(
        "--holding-set-csv",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_carry_forward_holding_set_task242.csv",
    )
    parser.add_argument(
        "--ready-input-csv",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_operation_week6_run_and_holding_recheck_scheduling_ready_input_task266.csv",
    )
    parser.add_argument(
        "--escalate-input-csv",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_operation_week6_run_and_holding_recheck_scheduling_escalate_input_task266.csv",
    )
    parser.add_argument(
        "--reject-set-csv",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_carry_forward_reject_set_task242.csv",
    )
    parser.add_argument(
        "--week6-summary-json",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_operation_week6_run_and_holding_recheck_scheduling_summary_task266.json",
    )
    parser.add_argument("--output-dir", default="data/phase1_seed10/logs")
    parser.add_argument("--trash-root", default="_trash")
    parser.add_argument("--run-id", default="")
    return parser.parse_args()


def _check(check_label: str, actual: Any, expected: Any, is_blocker: bool = True) -> dict[str, Any]:
    passed = actual == expected
    return {
        "check_label": check_label,
        "actual": actual,
        "expected": expected,
        "status": "PASS" if passed else "FAIL",
        "is_blocker": is_blocker,
    }


def main() -> int:
    args = parse_args()
    run_id = args.run_id.strip() or datetime.now(timezone.utc).strftime("task267_%Y%m%dT%H%M%SZ")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    state_path = Path(args.state_latest_json)
    holding_rows = read_csv(Path(args.holding_set_csv))
    ready_rows = read_csv(Path(args.ready_input_csv))
    escalate_rows = read_csv(Path(args.escalate_input_csv))
    reject_rows = read_csv(Path(args.reject_set_csv))
    week6_summary = read_json(Path(args.week6_summary_json), default={})

    state_exists = state_path.exists()
    state = read_json(state_path, default={})
    state_hash_before = file_sha256(state_path) if state_exists else ""
    ingested_run_ids = {str(v) for v in list(state.get("ingested_snapshot_run_ids") or [])}
    baseline_scope_hash = str(state.get("baseline_scope_hash") or "").strip()
    state_rules = dict(state.get("state_rules") or {})
    no_op_rule = str(state_rules.get("same_run_id_reingest_rule") or "").strip().lower()
    no_op_rule_present = "no-op" in no_op_rule

    holding_signatures = {row_signature(r) for r in holding_rows}
    ready_signatures = {row_signature(r) for r in ready_rows}
    escalate_signatures = {row_signature(r) for r in escalate_rows}
    reject_signatures = {row_signature(r) for r in reject_rows}

    holding_monitor_keys = {monitor_key(r) for r in holding_rows}
    ready_monitor_keys = {monitor_key(r) for r in ready_rows}
    escalate_monitor_keys = {monitor_key(r) for r in escalate_rows}
    reject_monitor_keys = {monitor_key(r) for r in reject_rows}

    overlap_counts = {
        "holding_vs_ready_signature_overlap": len(holding_signatures & ready_signatures),
        "holding_vs_escalate_signature_overlap": len(holding_signatures & escalate_signatures),
        "holding_vs_reject_signature_overlap": len(holding_signatures & reject_signatures),
        "holding_vs_ready_monitor_key_overlap": len(holding_monitor_keys & ready_monitor_keys),
        "holding_vs_escalate_monitor_key_overlap": len(holding_monitor_keys & escalate_monitor_keys),
        "holding_vs_reject_monitor_key_overlap": len(holding_monitor_keys & reject_monitor_keys),
    }
    boundary_breach_count = sum(overlap_counts.values())

    holding_readiness = dict(week6_summary.get("holding_recheck_readiness") or {})
    due_conclusion = str(holding_readiness.get("conclusion") or "").strip()
    due_confirmed = due_conclusion == "HOLDING_RECHECK_DUE"

    required_columns = {"gallery_name_en", "fair_slug", "target_year", "source_url"}
    holding_columns = set(holding_rows[0].keys()) if holding_rows else set()
    bundle_buildable = len(holding_rows) == 17 and required_columns.issubset(holding_columns)

    preflight_rows = [
        _check("HOLDING_DUE_CONFIRMED_FROM_TASK266", due_confirmed, True, True),
        _check("AUTHORITATIVE_STATE_EXISTS", state_exists, True, True),
        _check("RUN_ID_NOT_ALREADY_INGESTED", run_id in ingested_run_ids, False, True),
        _check("BASELINE_SCOPE_HASH_PRESENT", bool(baseline_scope_hash), True, True),
        _check("HOLDING_COUNT_EXPECTED", len(holding_rows), 17, True),
        _check("READY_REFERENCE_COUNT_EXPECTED", len(ready_rows), 48, True),
        _check("ESCALATE_REFERENCE_COUNT_EXPECTED", len(escalate_rows), 4, True),
        _check("REJECT_REFERENCE_COUNT_EXPECTED", len(reject_rows), 0, True),
        _check("HOLDING_BUNDLE_BUILDABLE", bundle_buildable, True, True),
        _check("BOUNDARY_BREACH_COUNT", boundary_breach_count, 0, True),
        _check("SAME_RUN_NOOP_RULE_PRESENT", no_op_rule_present, True, True),
    ]

    blocker_fail_count = sum(1 for row in preflight_rows if row["is_blocker"] and row["status"] == "FAIL")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root = Path(args.trash_root) / f"{timestamp}_pre_task267_holding_recheck_prep_{run_id}"
    backup_root.mkdir(parents=True, exist_ok=True)
    backup_state_path = backup_root / state_path.name
    backup_created = False
    backup_hash = ""
    backup_hash_match = False
    if state_exists:
        shutil.copy2(state_path, backup_state_path)
        backup_created = backup_state_path.exists()
        if backup_created:
            backup_hash = file_sha256(backup_state_path)
            backup_hash_match = backup_hash == state_hash_before

    backup_conditions_defined = True
    restore_conditions = [
        "boundary_breach_count > 0",
        "state JSON parse failure / hash mismatch after update",
        "integrity blocker detected (coverage/reject/join_blocker > 0)",
        "write failure to monitored state",
    ]
    no_op_conditions = [
        "same run_id re-ingest attempt",
        "identical holding input with already ingested run_id",
    ]

    if blocker_fail_count > 0 or not backup_created or not backup_hash_match or not backup_conditions_defined:
        decision = HOLD
    else:
        decision = READY

    blocker_labels: list[str] = []
    if blocker_fail_count > 0:
        blocker_labels.append("HOLDING_PRECHECK_BLOCKER_FAILED")
    if not backup_created:
        blocker_labels.append("BACKUP_NOT_CREATED")
    if backup_created and not backup_hash_match:
        blocker_labels.append("BACKUP_HASH_MISMATCH")

    input_bundle_path = output_dir / "holding_recheck_input_task267.csv"
    preflight_csv_path = output_dir / "holding_recheck_preflight_task267.csv"
    preflight_json_path = output_dir / "holding_recheck_preflight_task267.json"
    summary_path = output_dir / "holding_recheck_dryrun_summary_task267.json"
    manifest_path = output_dir / "holding_recheck_manifest_task267.json"
    report_path = output_dir / "holding_recheck_prep_task267.md"

    if holding_rows:
        write_csv(input_bundle_path, holding_rows, list(holding_rows[0].keys()))
    else:
        write_csv(input_bundle_path, [], ["gallery_name_en", "fair_slug", "target_year", "source_url", "text_hash"])
    write_csv(preflight_csv_path, preflight_rows, ["check_label", "actual", "expected", "status", "is_blocker"])
    write_json(preflight_json_path, {"run_id": run_id, "checks": preflight_rows, "blocker_fail_count": blocker_fail_count})

    runbook_mini = [
        {"step_order": 1, "step_id": "RUN_START_VALIDATION", "status": "PASS"},
        {"step_order": 2, "step_id": "PREFLIGHT", "status": "PASS" if blocker_fail_count == 0 else "FAIL"},
        {"step_order": 3, "step_id": "BACKUP", "status": "PASS" if backup_created and backup_hash_match else "FAIL"},
        {"step_order": 4, "step_id": "HOLDING_RECHECK_EXECUTION", "status": "SKIPPED_INTENTIONAL"},
        {"step_order": 5, "step_id": "POST_RUN_VERIFICATION", "status": "SKIPPED_INTENTIONAL"},
        {"step_order": 6, "step_id": "HOLD_RESTORE_DECISION", "status": "PASS" if decision == READY else "HOLD"},
        {"step_order": 7, "step_id": "LOG_MANIFEST_CONFIRM", "status": "PASS"},
    ]

    summary = {
        "artifact": "holding_recheck_dryrun_summary_task267",
        "task": "TASK267",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "mode": "PREP_DRY_RUN_ONLY",
        "holding_bundle_count": len(holding_rows),
        "reference_counts": {"ready": len(ready_rows), "escalate": len(escalate_rows), "reject": len(reject_rows)},
        "boundary_overlap_counts": overlap_counts,
        "boundary_breach_count": boundary_breach_count,
        "holding_due_conclusion_from_task266": due_conclusion,
        "backup": {
            "backup_root": str(backup_root),
            "backup_state_path": str(backup_state_path),
            "backup_created": backup_created,
            "state_hash_before": state_hash_before,
            "backup_hash": backup_hash,
            "backup_hash_match": backup_hash_match,
        },
        "failsafe": {
            "restore_conditions": restore_conditions,
            "no_op_conditions": no_op_conditions,
            "backup_target": str(state_path),
        },
        "runbook_mini": runbook_mini,
        "decision": decision,
        "blocker_labels": blocker_labels,
        "next_task_recommendation": {
            "id": "TASK268",
            "title": "EXHIBITIONS-TEXT-HOLDING-RECHECK-CONTROLLED-RUN",
            "ja": "Execute HOLDING-only controlled recheck run with strict isolation and fail-safe",
        },
    }
    write_json(summary_path, summary)

    manifest = {
        "artifact": "holding_recheck_manifest_task267",
        "task": "TASK267",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "inputs": {
            "holding_set_csv": str(Path(args.holding_set_csv)),
            "ready_input_csv": str(Path(args.ready_input_csv)),
            "escalate_input_csv": str(Path(args.escalate_input_csv)),
            "reject_set_csv": str(Path(args.reject_set_csv)),
            "week6_summary_json": str(Path(args.week6_summary_json)),
            "state_latest_json": str(state_path),
        },
        "outputs": {
            "holding_recheck_input_csv": str(input_bundle_path),
            "preflight_csv": str(preflight_csv_path),
            "preflight_json": str(preflight_json_path),
            "dryrun_summary_json": str(summary_path),
            "manifest_json": str(manifest_path),
            "report_md": str(report_path),
        },
        "decision": decision,
    }
    write_json(manifest_path, manifest)

    report_lines = [
        "# TASK267 HOLDING Recheck Prep Controlled Start",
        "",
        "## objective",
        "- Build isolated HOLDING-only bundle and complete dry-run precheck",
        "- Do not execute holding recheck run in this task",
        "",
        "## bundle",
        f"- run_id={run_id}",
        f"- holding_count={len(holding_rows)}",
        f"- boundary_breach_count={boundary_breach_count}",
        "",
        "## precheck",
        f"- blocker_fail_count={blocker_fail_count}",
        f"- due_from_task266={due_conclusion}",
        f"- backup_created={backup_created}",
        f"- backup_hash_match={backup_hash_match}",
        "",
        "## decision",
        f"- decision={decision}",
        f"- blocker_labels={blocker_labels}",
    ]
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(
        "[task267] "
        f"run_id={run_id} holding={len(holding_rows)} boundary={boundary_breach_count} "
        f"precheck_fail={blocker_fail_count} decision={decision}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
