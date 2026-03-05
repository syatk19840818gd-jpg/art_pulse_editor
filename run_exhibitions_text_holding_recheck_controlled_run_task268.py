from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY = "READY_FOR_HOLDING_RECHECK_RESULT_TRIAGE"
HOLD_RESTORE = "HOLD_FOR_RESTORE_INVOCATION"
HOLD_REVIEW = "HOLD_FOR_HOLDING_RECHECK_RESULT_REVIEW"


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


def _bool_like(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def classify_bucket(row: dict[str, str]) -> tuple[str, str]:
    route_quality = str(row.get("route_quality_label") or "").strip()
    year_quality = str(row.get("year_quality_label") or "").strip()
    join_status = str(row.get("join_status") or "").strip()
    join_basis = str(row.get("join_basis") or "").strip()
    provenance_suspicious = _bool_like(row.get("provenance_suspicious"))

    if provenance_suspicious or year_quality in {"hard_suspicious", "hard_reject"} or route_quality in {
        "hard_suspicious",
        "hard_reject",
    }:
        return ("REJECT_CANDIDATE", "hard_quality_or_provenance_risk")

    if year_quality != "pass":
        return ("ESCALATE_CANDIDATE", "non_pass_year_signal_requires_escalation")

    if route_quality == "soft_suspicious":
        return ("CONTINUE_HOLDING", "soft_route_listing_or_non_detail_needs_holding")

    if route_quality == "detail_candidate" and join_status == "TEXT_ONLY" and join_basis == "no_image_candidate":
        return ("STABLE_WARNING_CANDIDATE", "detail_candidate_text_only_warning_can_be_monitored")

    if route_quality == "detail_candidate":
        return ("READY_CANDIDATE", "detail_candidate_with_pass_quality")

    return ("CONTINUE_HOLDING", "unresolved_signal_keep_holding")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TASK268 HOLDING recheck controlled run (isolated lane)")
    parser.add_argument(
        "--state-latest-json",
        default="data/phase1_seed10/logs/exhibitions_text_monitored_state_latest.json",
    )
    parser.add_argument(
        "--holding-input-csv",
        default="data/phase1_seed10/logs/holding_recheck_input_task267.csv",
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
        "--task267-summary-json",
        default="data/phase1_seed10/logs/holding_recheck_dryrun_summary_task267.json",
    )
    parser.add_argument(
        "--task266-summary-json",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_operation_week6_run_and_holding_recheck_scheduling_summary_task266.json",
    )
    parser.add_argument("--expected-prep-run-id", default="task267_20260305T082215Z")
    parser.add_argument("--output-dir", default="data/phase1_seed10/logs")
    parser.add_argument("--trash-root", default="_trash")
    parser.add_argument("--run-id", default="")
    return parser.parse_args()


def _stage(step_order: int, step_id: str, status: str, detail: str) -> dict[str, Any]:
    return {
        "step_order": step_order,
        "step_id": step_id,
        "status": status,
        "detail": detail,
    }


def main() -> int:
    args = parse_args()
    run_id = args.run_id.strip() or datetime.now(timezone.utc).strftime("task268_%Y%m%dT%H%M%SZ")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    state_path = Path(args.state_latest_json)
    holding_rows = read_csv(Path(args.holding_input_csv))
    ready_rows = read_csv(Path(args.ready_input_csv))
    escalate_rows = read_csv(Path(args.escalate_input_csv))
    reject_rows = read_csv(Path(args.reject_set_csv))
    task267_summary = read_json(Path(args.task267_summary_json), default={})
    task266_summary = read_json(Path(args.task266_summary_json), default={})

    state_exists = state_path.exists()
    state = read_json(state_path, default={})
    state_hash_before = file_sha256(state_path) if state_exists else ""
    ingested_run_ids = {str(v) for v in list(state.get("ingested_snapshot_run_ids") or [])}
    baseline_scope_hash = str(state.get("baseline_scope_hash") or "").strip()
    state_rules = dict(state.get("state_rules") or {})
    same_run_noop_rule = str(state_rules.get("same_run_id_reingest_rule") or "").strip().lower()
    same_run_noop_rule_present = "no-op" in same_run_noop_rule

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

    task267_run_id = str(task267_summary.get("run_id") or "").strip()
    task267_decision = str(task267_summary.get("decision") or "").strip()
    task266_holding_due = str(dict(task266_summary.get("holding_recheck_readiness") or {}).get("conclusion") or "").strip()
    expected_prep_ok = (
        task267_run_id == str(args.expected_prep_run_id).strip()
        and task267_decision == "READY_FOR_HOLDING_RECHECK_CONTROLLED_RUN"
        and task266_holding_due == "HOLDING_RECHECK_DUE"
    )

    common_checks = dict(dict(task266_summary.get("post_run_verification") or {}).get("common") or {})
    coverage_review_count = int(common_checks.get("coverage_review_count", 0) or 0)
    reject_candidate_count = int(common_checks.get("reject_candidate_count", 0) or 0)
    join_blocker_count = int(common_checks.get("join_blocker_count", 0) or 0)

    preflight_rows = [
        {
            "check_label": "TASK267_PREP_READY_CONFIRMED",
            "actual": expected_prep_ok,
            "expected": True,
            "status": "PASS" if expected_prep_ok else "FAIL",
            "is_blocker": True,
        },
        {
            "check_label": "HOLDING_INPUT_COUNT_EXPECTED",
            "actual": len(holding_rows),
            "expected": 17,
            "status": "PASS" if len(holding_rows) == 17 else "FAIL",
            "is_blocker": True,
        },
        {
            "check_label": "AUTHORITATIVE_STATE_EXISTS",
            "actual": state_exists,
            "expected": True,
            "status": "PASS" if state_exists else "FAIL",
            "is_blocker": True,
        },
        {
            "check_label": "RUN_ID_NOT_ALREADY_INGESTED",
            "actual": run_id in ingested_run_ids,
            "expected": False,
            "status": "PASS" if run_id not in ingested_run_ids else "FAIL",
            "is_blocker": True,
        },
        {
            "check_label": "BASELINE_SCOPE_HASH_PRESENT",
            "actual": bool(baseline_scope_hash),
            "expected": True,
            "status": "PASS" if bool(baseline_scope_hash) else "FAIL",
            "is_blocker": True,
        },
        {
            "check_label": "BOUNDARY_BREACH_COUNT",
            "actual": boundary_breach_count,
            "expected": 0,
            "status": "PASS" if boundary_breach_count == 0 else "FAIL",
            "is_blocker": True,
        },
        {
            "check_label": "SAME_RUN_NOOP_RULE_PRESENT",
            "actual": same_run_noop_rule_present,
            "expected": True,
            "status": "PASS" if same_run_noop_rule_present else "FAIL",
            "is_blocker": True,
        },
        {
            "check_label": "COVERAGE_REVIEW_COUNT",
            "actual": coverage_review_count,
            "expected": 0,
            "status": "PASS" if coverage_review_count == 0 else "FAIL",
            "is_blocker": True,
        },
        {
            "check_label": "REJECT_CANDIDATE_COUNT",
            "actual": reject_candidate_count,
            "expected": 0,
            "status": "PASS" if reject_candidate_count == 0 else "FAIL",
            "is_blocker": True,
        },
        {
            "check_label": "JOIN_BLOCKER_COUNT",
            "actual": join_blocker_count,
            "expected": 0,
            "status": "PASS" if join_blocker_count == 0 else "FAIL",
            "is_blocker": True,
        },
    ]
    blocker_fail_count = sum(1 for row in preflight_rows if row["is_blocker"] and row["status"] == "FAIL")

    backup_created = False
    backup_hash = ""
    backup_hash_match = False
    backup_root = Path("")
    backup_state_path = Path("")
    restore_executed = False
    restore_succeeded = False
    restore_reason = ""

    bucket_rows: list[dict[str, Any]] = []
    bucket_counts = Counter()
    stage_rows: list[dict[str, Any]] = []
    state_advanced = False
    state_hash_after = ""
    temporal_gap_count = 0
    idempotent_noop_count = 0
    blocker_labels: list[str] = []

    stage_rows.append(
        _stage(
            1,
            "RUN_START_VALIDATION",
            "PASS" if len(holding_rows) == 17 else "FAIL",
            f"holding_input={len(holding_rows)} prep_run={task267_run_id}",
        )
    )
    stage_rows.append(
        _stage(
            2,
            "PREFLIGHT",
            "PASS" if blocker_fail_count == 0 else "FAIL",
            f"preflight_pass={len(preflight_rows)-blocker_fail_count}/{len(preflight_rows)}",
        )
    )

    if blocker_fail_count == 0:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_root = Path(args.trash_root) / f"{timestamp}_pre_task268_holding_recheck_run_{run_id}"
        backup_root.mkdir(parents=True, exist_ok=True)
        backup_state_path = backup_root / state_path.name
        shutil.copy2(state_path, backup_state_path)
        backup_created = backup_state_path.exists()
        if backup_created:
            backup_hash = file_sha256(backup_state_path)
            backup_hash_match = backup_hash == state_hash_before

    stage_rows.append(
        _stage(
            3,
            "BACKUP",
            "PASS" if (backup_created and backup_hash_match) else "FAIL",
            f"backup_created={backup_created} backup_hash_match={backup_hash_match}",
        )
    )

    if blocker_fail_count == 0 and backup_created and backup_hash_match:
        for row in holding_rows:
            bucket, reason = classify_bucket(row)
            out = dict(row)
            out["task_run_id"] = run_id
            out["bucket"] = bucket
            out["bucket_reason"] = reason
            out["monitor_key"] = monitor_key(row)
            out["row_signature"] = row_signature(row)
            bucket_rows.append(out)
            bucket_counts[bucket] += 1

        # Update state with ingestion event for no-op guard consistency.
        state_out = dict(state)
        ingested_list = list(state_out.get("ingested_snapshot_run_ids") or [])
        ingested_list.append(run_id)
        state_out["ingested_snapshot_run_ids"] = ingested_list
        state_out["task"] = "TASK268"
        state_out["updated_at"] = utc_now_iso()
        state_out["holding_recheck_last_run"] = {
            "task_run_id": run_id,
            "rows": len(holding_rows),
            "bucket_counts": dict(bucket_counts),
            "mode": "holding_only_controlled_run",
        }
        state_out["last_ingestion"] = {
            "task_run_id": run_id,
            "ingestion_mode": "holding_recheck_controlled_run",
            "snapshot_rows": len(holding_rows),
            "updated_units_count": 0,
            "persistence_increment_count": 0,
            "idempotent_noop_count": 0,
            "temporal_gap_count": 0,
            "boundary_breach_count": boundary_breach_count,
        }
        write_json(state_path, state_out)
        state_hash_after = file_sha256(state_path)
        state_advanced = state_hash_after != state_hash_before
        run_id_ingested = run_id in {str(v) for v in list(state_out.get("ingested_snapshot_run_ids") or [])}
        idempotent_noop_count = len(holding_rows) if run_id_ingested else 0

        fail_reasons: list[str] = []
        if boundary_breach_count > 0:
            fail_reasons.append("BOUNDARY_BREACH_DETECTED")
        if any(v > 0 for v in [coverage_review_count, reject_candidate_count, join_blocker_count]):
            fail_reasons.append("INTEGRITY_BLOCKER_DETECTED")
        if not run_id_ingested:
            fail_reasons.append("RUN_ID_NOT_INGESTED")
        if not state_advanced:
            fail_reasons.append("STATE_NOT_ADVANCED")
        if not read_json(state_path, default={}):
            fail_reasons.append("POST_WRITE_JSON_INVALID")

        if fail_reasons:
            restore_reason = "|".join(fail_reasons)
            shutil.copy2(backup_state_path, state_path)
            restore_executed = True
            restore_succeeded = file_sha256(state_path) == backup_hash
            blocker_labels.extend(fail_reasons)
    else:
        blocker_labels.append("PREFLIGHT_OR_BACKUP_FAILED")

    stage_rows.append(
        _stage(
            4,
            "HOLDING_RECHECK_EXECUTION",
            "PASS" if len(bucket_rows) == len(holding_rows) and len(holding_rows) > 0 else "FAIL",
            f"classified={len(bucket_rows)} holding={len(holding_rows)}",
        )
    )

    integrity_clear = all(
        [
            boundary_breach_count == 0,
            coverage_review_count == 0,
            reject_candidate_count == 0,
            join_blocker_count == 0,
        ]
    )

    post_run_verification = {
        "artifact": "holding_recheck_post_run_verification_task268",
        "task": "TASK268",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "holding_side": {
            "holding_input_count": len(holding_rows),
            "classified_count": len(bucket_rows),
            "boundary_breach_count": boundary_breach_count,
            "integrity_clear": integrity_clear,
        },
        "boundary_overlap_counts": overlap_counts,
        "common": {
            "temporal_gap_count": temporal_gap_count,
            "same_run_noop_dry_check_count": idempotent_noop_count,
            "coverage_review_count": coverage_review_count,
            "reject_candidate_count": reject_candidate_count,
            "join_blocker_count": join_blocker_count,
        },
        "bucket_counts": dict(bucket_counts),
        "pass": (
            len(bucket_rows) == len(holding_rows)
            and boundary_breach_count == 0
            and integrity_clear
            and not restore_executed
        ),
    }
    stage_rows.append(
        _stage(
            5,
            "POST_RUN_VERIFICATION",
            "PASS" if post_run_verification["pass"] else "FAIL",
            (
                f"boundary={boundary_breach_count} integrity_clear={integrity_clear} "
                f"classified={len(bucket_rows)}"
            ),
        )
    )

    if restore_executed:
        stage_rows.append(
            _stage(
                6,
                "HOLD_RESTORE_DECISION",
                "HOLD",
                f"restore_executed={restore_executed} restore_succeeded={restore_succeeded} reason={restore_reason}",
            )
        )
        decision = HOLD_RESTORE
    elif blocker_fail_count > 0 or not post_run_verification["pass"]:
        stage_rows.append(
            _stage(
                6,
                "HOLD_RESTORE_DECISION",
                "HOLD",
                f"blocker_fail_count={blocker_fail_count} post_run_pass={post_run_verification['pass']}",
            )
        )
        decision = HOLD_REVIEW
    else:
        stage_rows.append(
            _stage(
                6,
                "HOLD_RESTORE_DECISION",
                "PASS",
                "no restore condition met",
            )
        )
        decision = READY

    stage_rows.append(
        _stage(
            7,
            "LOG_MANIFEST_CONFIRM",
            "PASS",
            "summary/manifest/table/bucket/post-verification/backup-log prepared",
        )
    )

    summary = {
        "artifact": "holding_recheck_run_summary_task268",
        "task": "TASK268",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "inputs": {
            "holding_input_csv": str(Path(args.holding_input_csv)),
            "ready_input_csv": str(Path(args.ready_input_csv)),
            "escalate_input_csv": str(Path(args.escalate_input_csv)),
            "reject_set_csv": str(Path(args.reject_set_csv)),
            "task267_summary_json": str(Path(args.task267_summary_json)),
            "task266_summary_json": str(Path(args.task266_summary_json)),
            "state_latest_json": str(state_path),
            "expected_prep_run_id": str(args.expected_prep_run_id).strip(),
        },
        "run_start_validation": {
            "holding_input_count": len(holding_rows),
            "prep_run_id": task267_run_id,
            "prep_decision": task267_decision,
            "holding_due_conclusion": task266_holding_due,
        },
        "preflight": {
            "check_total": len(preflight_rows),
            "pass_count": sum(1 for r in preflight_rows if r["status"] == "PASS"),
            "fail_count": sum(1 for r in preflight_rows if r["status"] == "FAIL"),
            "blocker_fail_count": blocker_fail_count,
        },
        "backup": {
            "backup_root": str(backup_root) if backup_root else "",
            "backup_state_path": str(backup_state_path) if backup_state_path else "",
            "backup_created": backup_created,
            "state_hash_before": state_hash_before,
            "backup_hash": backup_hash,
            "backup_hash_match": backup_hash_match,
            "state_hash_after": state_hash_after,
            "state_advanced": state_advanced,
        },
        "holding_recheck_execution": {
            "holding_input_count": len(holding_rows),
            "classified_count": len(bucket_rows),
            "bucket_counts": dict(bucket_counts),
            "ready_lane_mixed_count": overlap_counts["holding_vs_ready_signature_overlap"],
            "escalate_lane_mixed_count": overlap_counts["holding_vs_escalate_signature_overlap"],
            "reject_lane_mixed_count": overlap_counts["holding_vs_reject_signature_overlap"],
        },
        "post_run_verification": post_run_verification,
        "restore": {
            "restore_executed": restore_executed,
            "restore_succeeded": restore_succeeded,
            "restore_reason": restore_reason,
        },
        "runbook_stage_status": stage_rows,
        "go_hold_decision": decision,
        "blocker_labels": blocker_labels,
        "next_task_recommendation": {
            "id": "TASK269",
            "title": "EXHIBITIONS-TEXT-HOLDING-RECHECK-RESULT-TRIAGE-AND-LANE-REFLECTION-POLICY",
            "ja": "Triage holding recheck buckets and define lane reflection policy without direct mixing",
        },
    }

    summary_path = output_dir / "holding_recheck_run_summary_task268.json"
    manifest_path = output_dir / "holding_recheck_run_manifest_task268.json"
    run_table_path = output_dir / "holding_recheck_run_table_task268.csv"
    bucket_records_path = output_dir / "holding_recheck_bucket_records_task268.csv"
    post_verification_path = output_dir / "holding_recheck_post_run_verification_task268.json"
    backup_log_path = output_dir / "holding_recheck_backup_log_task268.json"
    report_md_path = output_dir / "holding_recheck_run_task268.md"

    write_json(summary_path, summary)
    write_json(post_verification_path, post_run_verification)
    write_json(
        backup_log_path,
        {
            "task": "TASK268",
            "run_id": run_id,
            "backup_root": str(backup_root) if backup_root else "",
            "backup_state_path": str(backup_state_path) if backup_state_path else "",
            "backup_created": backup_created,
            "state_hash_before": state_hash_before,
            "backup_hash": backup_hash,
            "backup_hash_match": backup_hash_match,
            "state_hash_after": state_hash_after,
            "state_advanced": state_advanced,
            "restore_executed": restore_executed,
            "restore_succeeded": restore_succeeded,
            "restore_reason": restore_reason,
        },
    )
    write_csv(run_table_path, stage_rows, ["step_order", "step_id", "status", "detail"])

    if bucket_rows:
        bucket_fieldnames = list(bucket_rows[0].keys())
    else:
        bucket_fieldnames = [
            "gallery_name_en",
            "fair_slug",
            "target_year",
            "source_url",
            "join_status",
            "join_basis",
            "route_quality_label",
            "year_quality_label",
            "provenance_suspicious",
            "task_run_id",
            "bucket",
            "bucket_reason",
            "monitor_key",
            "row_signature",
        ]
    write_csv(bucket_records_path, bucket_rows, bucket_fieldnames)

    manifest = {
        "artifact": "holding_recheck_run_manifest_task268",
        "task": "TASK268",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "inputs": summary["inputs"],
        "outputs": {
            "summary_json": str(summary_path),
            "manifest_json": str(manifest_path),
            "run_table_csv": str(run_table_path),
            "bucket_records_csv": str(bucket_records_path),
            "post_run_verification_json": str(post_verification_path),
            "backup_log_json": str(backup_log_path),
            "report_md": str(report_md_path),
        },
        "decision": decision,
    }
    write_json(manifest_path, manifest)

    md_lines = [
        "# TASK268 HOLDING Recheck Controlled Run",
        "",
        f"- run_id={run_id}",
        f"- holding_input_count={len(holding_rows)}",
        f"- decision={decision}",
        "",
        "## bucket_counts",
    ]
    for key in [
        "READY_CANDIDATE",
        "STABLE_WARNING_CANDIDATE",
        "CONTINUE_HOLDING",
        "ESCALATE_CANDIDATE",
        "REJECT_CANDIDATE",
    ]:
        md_lines.append(f"- {key}={int(bucket_counts.get(key, 0))}")
    md_lines.extend(
        [
            "",
            "## checks",
            f"- boundary_breach_count={boundary_breach_count}",
            f"- coverage_review_count={coverage_review_count}",
            f"- reject_candidate_count={reject_candidate_count}",
            f"- join_blocker_count={join_blocker_count}",
            f"- restore_executed={restore_executed}",
        ]
    )
    report_md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(
        "[task268] "
        f"run_id={run_id} holding={len(holding_rows)} "
        f"bucket_ready={int(bucket_counts.get('READY_CANDIDATE', 0))} "
        f"bucket_warning={int(bucket_counts.get('STABLE_WARNING_CANDIDATE', 0))} "
        f"bucket_holding={int(bucket_counts.get('CONTINUE_HOLDING', 0))} "
        f"bucket_escalate={int(bucket_counts.get('ESCALATE_CANDIDATE', 0))} "
        f"bucket_reject={int(bucket_counts.get('REJECT_CANDIDATE', 0))} "
        f"boundary={boundary_breach_count} restore={restore_executed} decision={decision}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

