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

READY = "READY_FOR_READY_RESTART_WITH_ESCALATE_MONITORING_PHASE_4"
HOLD_ESCALATE = "HOLD_FOR_ESCALATE_LANE_BLOCKER"
HOLD_BOUNDARY = "HOLD_FOR_BOUNDARY_RECHECK"
HOLD_RESTORE = "HOLD_FOR_RESTORE_INVOCATION"


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


def scope_key(row: dict[str, str]) -> str:
    return "||".join(
        [
            str(row.get("fair_slug") or "").strip(),
            str(row.get("gallery_name_en") or "").strip(),
        ]
    )


def route_rank(label: str) -> int:
    value = str(label or "").strip().lower()
    if value == "detail_candidate":
        return 1
    if value == "soft_suspicious":
        return 2
    if value in {"hard_suspicious", "hard_reject"}:
        return 3
    return 0


def by_fair_counter(rows: list[dict[str, str]]) -> dict[str, int]:
    out = Counter()
    for row in rows:
        out[str(row.get("fair_slug") or "").strip()] += 1
    return dict(out)


def by_gallery_counter(rows: list[dict[str, str]]) -> dict[str, int]:
    out = Counter()
    for row in rows:
        key = f"{str(row.get('gallery_name_en') or '').strip()}|{str(row.get('fair_slug') or '').strip()}"
        out[key] += 1
    return dict(out)


def _is_text_only(row: dict[str, str]) -> bool:
    return (
        str(row.get("join_status") or "").strip() == "TEXT_ONLY"
        or str(row.get("join_basis") or "").strip() == "no_image_candidate"
    )


def _warning_causes(row: dict[str, str]) -> list[str]:
    causes: list[str] = []
    if _is_text_only(row):
        causes.append("TEXT_ONLY")
    if str(row.get("route_quality_label") or "").strip() == "soft_suspicious":
        causes.append("ROUTE_SOFT")
    if str(row.get("year_quality_label") or "").strip() != "pass":
        causes.append("YEAR_WARNING")
    return causes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="TASK255 Exhibitions Text ready restart with escalate monitoring phase3 continuation"
    )
    parser.add_argument(
        "--state-latest-json",
        default="data/phase1_seed10/logs/exhibitions_text_monitored_state_latest.json",
    )
    parser.add_argument(
        "--task254-ready-input-csv",
        default="data/phase1_seed10/logs/exhibitions_text_ready_restart_with_escalate_monitoring_phase2_continuation_ready_input_task254.csv",
    )
    parser.add_argument(
        "--task254-escalate-input-csv",
        default="data/phase1_seed10/logs/exhibitions_text_ready_restart_with_escalate_monitoring_phase2_continuation_escalate_input_task254.csv",
    )
    parser.add_argument(
        "--task254-ready-summary-json",
        default="data/phase1_seed10/logs/exhibitions_text_ready_restart_with_escalate_monitoring_phase2_continuation_ready_summary_task254.json",
    )
    parser.add_argument(
        "--task254-escalate-summary-json",
        default="data/phase1_seed10/logs/exhibitions_text_ready_restart_with_escalate_monitoring_phase2_continuation_escalate_summary_task254.json",
    )
    parser.add_argument(
        "--holding-set-csv",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_carry_forward_holding_set_task242.csv",
    )
    parser.add_argument(
        "--reject-set-csv",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_carry_forward_reject_set_task242.csv",
    )
    parser.add_argument("--output-dir", default="data/phase1_seed10/logs")
    parser.add_argument("--trash-root", default="_trash")
    parser.add_argument("--run-id", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_id = args.run_id.strip() or datetime.now(timezone.utc).strftime("task255_%Y%m%dT%H%M%SZ")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    state_path = Path(args.state_latest_json)
    ready_rows = read_csv(Path(args.task254_ready_input_csv))
    escalate_rows = read_csv(Path(args.task254_escalate_input_csv))
    summary254_ready = read_json(Path(args.task254_ready_summary_json), default={})
    summary254_escalate = read_json(Path(args.task254_escalate_summary_json), default={})
    holding_rows = read_csv(Path(args.holding_set_csv))
    reject_rows = read_csv(Path(args.reject_set_csv))

    preflight_rows: list[dict[str, Any]] = []

    def add_check(label: str, actual: Any, expected: Any, is_blocker: bool = True) -> None:
        passed = actual == expected
        preflight_rows.append(
            {
                "check_label": label,
                "actual": actual,
                "expected": expected,
                "status": "PASS" if passed else "FAIL",
                "is_blocker": is_blocker,
            }
        )

    state_exists = state_path.exists()
    add_check("AUTHORITATIVE_STATE_EXISTS", state_exists, True)
    state_hash_before = file_sha256(state_path) if state_exists else ""
    state = read_json(state_path, default={})

    baseline_run_id = str(state.get("baseline_run_id") or "").strip()
    baseline_scope_hash = str(state.get("baseline_scope_hash") or "").strip()
    ingested_run_ids = list(state.get("ingested_snapshot_run_ids") or [])
    ingested_run_set = {str(v) for v in ingested_run_ids}
    monitoring_units = dict(state.get("monitoring_units") or {})
    ratio_scope_state = dict(state.get("ratio_scope_state") or {})
    state_rules = dict(state.get("state_rules") or {})

    add_check("BASELINE_RUN_ID_PRESENT", bool(baseline_run_id), True)
    add_check("BASELINE_SCOPE_HASH_PRESENT", bool(baseline_scope_hash), True)
    add_check("RUN_ID_NOT_ALREADY_INGESTED", run_id in ingested_run_set, False)

    add_check("READY_COUNT_EXPECTED", len(ready_rows), 48)
    add_check("ESCALATE_COUNT_EXPECTED", len(escalate_rows), 4)

    ready_signatures = {row_signature(r) for r in ready_rows}
    escalate_signatures = {row_signature(r) for r in escalate_rows}
    holding_signatures = {row_signature(r) for r in holding_rows}
    reject_signatures = {row_signature(r) for r in reject_rows}

    ready_monitor_keys = {monitor_key(r) for r in ready_rows}
    escalate_monitor_keys = {monitor_key(r) for r in escalate_rows}

    boundary_checks = {
        "ready_vs_escalate_signature_overlap": len(ready_signatures & escalate_signatures),
        "ready_vs_holding_overlap": len(ready_signatures & holding_signatures),
        "ready_vs_reject_overlap": len(ready_signatures & reject_signatures),
        "escalate_vs_holding_overlap": len(escalate_signatures & holding_signatures),
        "escalate_vs_reject_overlap": len(escalate_signatures & reject_signatures),
        "ready_vs_escalate_monitor_key_overlap": len(ready_monitor_keys & escalate_monitor_keys),
    }
    boundary_breach_count = sum(boundary_checks.values())
    add_check("BOUNDARY_BREACH_COUNT", boundary_breach_count, 0)

    integrity_ready = dict(summary254_ready.get("integrity_checks") or {})
    integrity_escalate = dict(summary254_escalate.get("integrity_checks") or {})
    coverage_review_count = max(
        int(integrity_ready.get("coverage_review_count", 0)),
        int(integrity_escalate.get("coverage_review_count", 0)),
    )
    reject_candidate_count = max(
        int(integrity_ready.get("reject_candidate_count", 0)),
        int(integrity_escalate.get("reject_candidate_count", 0)),
    )
    join_blocker_count = max(
        int(integrity_ready.get("join_blocker_count", 0)),
        int(integrity_escalate.get("join_blocker_count", 0)),
    )
    escalate_blocker_count_pre = max(
        int(integrity_ready.get("escalate_blocker_count", 0)),
        int(integrity_escalate.get("escalate_blocker_count", 0)),
    )
    add_check("COVERAGE_REVIEW_COUNT", coverage_review_count, 0)
    add_check("REJECT_CANDIDATE_COUNT", reject_candidate_count, 0)
    add_check("JOIN_BLOCKER_COUNT", join_blocker_count, 0)
    add_check("ESCALATE_BLOCKER_COUNT_PRE", escalate_blocker_count_pre, 0)

    same_run_noop_rule = str(state_rules.get("same_run_id_reingest_rule") or "").strip().lower()
    add_check("SAME_RUN_NOOP_RULE_PRESENT", "no-op" in same_run_noop_rule, True)

    blocker_fail_count = sum(1 for row in preflight_rows if row["is_blocker"] and row["status"] == "FAIL")

    backup_created = False
    backup_hash_match = False
    backup_hash = ""
    backup_root = Path("")
    backup_state_path = Path("")
    restore_executed = False
    restore_succeeded = False
    restore_reason = ""

    updated_units_count = 0
    persistence_increment_count = 0
    temporal_gap_count = 0
    idempotent_noop_count = 0
    authoritative_state_advanced = False
    monitored_diff_rows: list[dict[str, Any]] = []
    blocker_labels: list[str] = []

    if blocker_fail_count > 0:
        if boundary_breach_count > 0:
            decision = HOLD_BOUNDARY
            blocker_labels.append("BOUNDARY_BREACH_DETECTED")
        elif any(v > 0 for v in [coverage_review_count, reject_candidate_count, join_blocker_count, escalate_blocker_count_pre]):
            decision = HOLD_ESCALATE
            blocker_labels.append("INTEGRITY_OR_ESCALATE_BLOCKER_DETECTED")
        else:
            decision = HOLD_BOUNDARY
            blocker_labels.append("PREFLIGHT_BLOCKER_FAILED")
    else:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_root = Path(args.trash_root) / f"{timestamp}_pre_task255_live_monitored_state_{run_id}"
        backup_root.mkdir(parents=True, exist_ok=True)
        backup_state_path = backup_root / state_path.name
        shutil.copy2(state_path, backup_state_path)
        backup_created = backup_state_path.exists()
        if backup_created:
            backup_hash = file_sha256(backup_state_path)
            backup_hash_match = backup_hash == state_hash_before

        if not backup_created or not backup_hash_match:
            decision = HOLD_RESTORE
            blocker_labels.append("BACKUP_INTEGRITY_FAILED")
        else:
            try:
                all_rows = ready_rows + escalate_rows
                total_by_scope: dict[str, int] = {}
                text_only_by_scope: dict[str, int] = {}
                for row in all_rows:
                    skey = scope_key(row)
                    total_by_scope[skey] = total_by_scope.get(skey, 0) + 1
                    if _is_text_only(row):
                        text_only_by_scope[skey] = text_only_by_scope.get(skey, 0) + 1

                for row in escalate_rows:
                    key = monitor_key(row)
                    skey = scope_key(row)
                    prev = dict(monitoring_units.get(key) or {})
                    before_persist = int(prev.get("persistence_count", 0) or 0)
                    before_reason = str(prev.get("last_reason") or "").strip()
                    before_route = str(prev.get("last_route_quality_label") or "").strip()
                    prev_flags = dict(prev.get("last_flags") or {})
                    prev_ratio_threshold = bool(prev_flags.get("ratio_threshold_exceeded", False))

                    if not prev:
                        temporal_gap_count += 1

                    next_persist = before_persist + 1 if before_persist > 0 else 1
                    if before_persist > 0:
                        persistence_increment_count += 1

                    route_quality = str(row.get("route_quality_label") or "").strip()
                    route_degradation = route_rank(route_quality) > route_rank(before_route) if before_route else False

                    scope_total = int(total_by_scope.get(skey, 0))
                    scope_text_only = int(text_only_by_scope.get(skey, 0))
                    text_only_ratio = (scope_text_only / scope_total) if scope_total > 0 else 0.0
                    ratio_evaluable = scope_total >= 3
                    ratio_threshold_exceeded = ratio_evaluable and text_only_ratio > 0.6
                    ratio_two_consecutive = ratio_threshold_exceeded and prev_ratio_threshold

                    trigger_persistence = next_persist >= 3
                    trigger_ratio = ratio_two_consecutive
                    trigger_route = route_degradation
                    escalate_now = bool(trigger_persistence or trigger_ratio or trigger_route)
                    escalate_blocker = bool(trigger_ratio or trigger_route)

                    causes = _warning_causes(row)
                    warning_primary = "+".join(causes) if causes else "OTHER_WARNING"

                    monitoring_units[key] = {
                        "monitor_key": key,
                        "scope_key": skey,
                        "fair_slug": str(row.get("fair_slug") or "").strip(),
                        "gallery_name_en": str(row.get("gallery_name_en") or "").strip(),
                        "source_url": str(row.get("source_url") or "").strip(),
                        "last_seen_run_id": run_id,
                        "persistence_count": next_persist,
                        "last_reason": warning_primary,
                        "last_warning_causes": "|".join(causes),
                        "last_route_quality_label": route_quality,
                        "last_year_quality_label": str(row.get("year_quality_label") or "").strip(),
                        "last_flags": {
                            "ratio_evaluable": ratio_evaluable,
                            "ratio_threshold_exceeded": ratio_threshold_exceeded,
                            "ratio_two_consecutive": ratio_two_consecutive,
                            "route_degradation_flag": route_degradation,
                            "escalate_now": escalate_now,
                            "escalate_blocker": escalate_blocker,
                            "escalate_trigger_persistence": trigger_persistence,
                            "escalate_trigger_ratio": trigger_ratio,
                            "escalate_trigger_route": trigger_route,
                        },
                    }

                    ratio_scope_state[skey] = {
                        "scope_key": skey,
                        "fair_slug": str(row.get("fair_slug") or "").strip(),
                        "gallery_name_en": str(row.get("gallery_name_en") or "").strip(),
                        "scope_total_count": scope_total,
                        "scope_text_only_count": scope_text_only,
                        "text_only_ratio": text_only_ratio,
                        "last_seen_run_id": run_id,
                    }

                    monitored_diff_rows.append(
                        {
                            "monitor_key": key,
                            "fair_slug": str(row.get("fair_slug") or "").strip(),
                            "gallery_name_en": str(row.get("gallery_name_en") or "").strip(),
                            "source_url": str(row.get("source_url") or "").strip(),
                            "persistence_before": before_persist,
                            "persistence_after": next_persist,
                            "increment": max(next_persist - before_persist, 0),
                            "warning_before": before_reason,
                            "warning_after": warning_primary,
                            "route_degradation_flag": route_degradation,
                            "ratio_threshold_exceeded": ratio_threshold_exceeded,
                            "ratio_two_consecutive": ratio_two_consecutive,
                            "escalate_trigger_persistence": trigger_persistence,
                            "escalate_trigger_ratio": trigger_ratio,
                            "escalate_trigger_route": trigger_route,
                            "escalate_now": escalate_now,
                            "escalate_blocker": escalate_blocker,
                        }
                    )

                updated_units_count = len(escalate_rows)
                ingested_run_ids.append(run_id)
                state["artifact"] = "exhibitions_text_monitored_state_latest"
                state["task"] = "TASK255"
                state["updated_at"] = utc_now_iso()
                state["monitoring_units"] = monitoring_units
                state["ratio_scope_state"] = ratio_scope_state
                state["ingested_snapshot_run_ids"] = ingested_run_ids
                state["last_ingestion"] = {
                    "task_run_id": run_id,
                    "ingestion_mode": "ready_restart_with_escalate_monitoring_phase3_continuation",
                    "snapshot_rows": len(escalate_rows),
                    "updated_units_count": updated_units_count,
                    "persistence_increment_count": persistence_increment_count,
                    "idempotent_noop_count": 0,
                    "temporal_gap_count": temporal_gap_count,
                    "escalate_now_count": sum(1 for row in monitored_diff_rows if row.get("escalate_now")),
                    "boundary_breach_count": boundary_breach_count,
                }
                write_json(state_path, state)

                state_after = read_json(state_path, default={})
                state_hash_after = file_sha256(state_path)
                authoritative_state_advanced = state_hash_after != state_hash_before
                run_id_ingested = run_id in set(state_after.get("ingested_snapshot_run_ids", []))
                idempotent_noop_count = len(escalate_rows) if run_id_ingested else 0

                ratio_two_consecutive_fired_count = sum(
                    1 for row in monitored_diff_rows if bool(row.get("escalate_trigger_ratio"))
                )
                route_degradation_fired_count = sum(
                    1 for row in monitored_diff_rows if bool(row.get("escalate_trigger_route"))
                )
                escalate_blocker_count = ratio_two_consecutive_fired_count + route_degradation_fired_count

                fail_reasons: list[str] = []
                if not authoritative_state_advanced:
                    fail_reasons.append("STATE_NOT_ADVANCED")
                if not run_id_ingested:
                    fail_reasons.append("RUN_ID_NOT_INGESTED")
                if temporal_gap_count > 0:
                    fail_reasons.append("TEMPORAL_GAP_DETECTED")
                if boundary_breach_count > 0:
                    fail_reasons.append("BOUNDARY_BREACH_DETECTED")
                if any(v > 0 for v in [coverage_review_count, reject_candidate_count, join_blocker_count]):
                    fail_reasons.append("INTEGRITY_BLOCKER_DETECTED")
                if escalate_blocker_count > 0:
                    fail_reasons.append("ESCALATE_LANE_BLOCKER_DETECTED")
                if not state_after:
                    fail_reasons.append("POST_WRITE_JSON_INVALID")

                if fail_reasons:
                    restore_reason = "|".join(fail_reasons)
                    shutil.copy2(backup_state_path, state_path)
                    restore_executed = True
                    restore_succeeded = file_sha256(state_path) == backup_hash
                    authoritative_state_advanced = False
                    decision = HOLD_RESTORE
                    blocker_labels.extend(fail_reasons)
                else:
                    decision = READY
            except Exception as exc:  # pragma: no cover
                restore_reason = f"EXCEPTION:{type(exc).__name__}"
                if backup_created and backup_state_path.exists():
                    shutil.copy2(backup_state_path, state_path)
                    restore_executed = True
                    restore_succeeded = file_sha256(state_path) == backup_hash
                decision = HOLD_RESTORE
                blocker_labels.append("TASK255_UPDATE_EXCEPTION")

    ready_by_fair = by_fair_counter(ready_rows)
    escalate_by_fair = by_fair_counter(escalate_rows)
    ready_by_gallery = by_gallery_counter(ready_rows)
    escalate_by_gallery = by_gallery_counter(escalate_rows)

    by_fair_rows: list[dict[str, Any]] = []
    by_gallery_rows: list[dict[str, Any]] = []
    for fair in sorted(set(ready_by_fair) | set(escalate_by_fair)):
        by_fair_rows.append(
            {
                "fair_slug": fair,
                "ready_restart_count": ready_by_fair.get(fair, 0),
                "escalate_lane_count": escalate_by_fair.get(fair, 0),
                "holding_excluded_count": len(
                    [r for r in holding_rows if str(r.get("fair_slug") or "").strip() == fair]
                ),
            }
        )
    for key in sorted(set(ready_by_gallery) | set(escalate_by_gallery)):
        by_gallery_rows.append(
            {
                "gallery_fair_key": key,
                "ready_restart_count": ready_by_gallery.get(key, 0),
                "escalate_lane_count": escalate_by_gallery.get(key, 0),
            }
        )

    ratio_two_consecutive_fired_count = sum(
        1 for row in monitored_diff_rows if bool(row.get("escalate_trigger_ratio"))
    )
    route_degradation_fired_count = sum(
        1 for row in monitored_diff_rows if bool(row.get("escalate_trigger_route"))
    )
    escalate_blocker_count = ratio_two_consecutive_fired_count + route_degradation_fired_count
    persistence_advanced_count = sum(
        1
        for row in monitored_diff_rows
        if int(row.get("persistence_after", 0) or 0) > int(row.get("persistence_before", 0) or 0)
    )
    temporal_gap_count = sum(
        1 for row in monitored_diff_rows if int(row.get("persistence_before", 0) or 0) <= 0
    )
    integrity_clear = all(
        [
            boundary_breach_count == 0,
            coverage_review_count == 0,
            reject_candidate_count == 0,
            join_blocker_count == 0,
            escalate_blocker_count == 0,
        ]
    )

    common_integrity = {
        "boundary_breach_count": boundary_breach_count,
        "coverage_review_count": coverage_review_count,
        "reject_candidate_count": reject_candidate_count,
        "join_blocker_count": join_blocker_count,
        "escalate_blocker_count": escalate_blocker_count,
        "integrity_clear": integrity_clear,
        "proposal_only": True,
        "formal_untouched": True,
        "adoption_executed": False,
        "rollback_executed": False,
        "join_contract_changed": False,
        "anti_mixing_enforced": True,
    }

    ready_summary = {
        "artifact": "exhibitions_text_ready_restart_with_escalate_monitoring_phase3_continuation_ready_summary",
        "task": "TASK255",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "inputs": {
            "task254_ready_input_csv": str(Path(args.task254_ready_input_csv)),
            "task254_ready_summary_json": str(Path(args.task254_ready_summary_json)),
            "holding_set_csv": str(Path(args.holding_set_csv)),
            "reject_set_csv": str(Path(args.reject_set_csv)),
            "state_latest_json": str(state_path),
        },
        "preflight": {
            "check_total": len(preflight_rows),
            "pass_count": sum(1 for row in preflight_rows if row["status"] == "PASS"),
            "fail_count": sum(1 for row in preflight_rows if row["status"] == "FAIL"),
            "blocker_fail_count": blocker_fail_count,
        },
        "ready_restart_result": {
            "ready_input_count": len(ready_rows),
            "boundary_breach_count": boundary_breach_count,
            "integrity_clear": integrity_clear,
            "excluded_escalate_count": len(escalate_rows),
            "excluded_holding_count": len(holding_rows),
            "excluded_reject_count": len(reject_rows),
            "by_fair": ready_by_fair,
            "by_gallery": ready_by_gallery,
        },
        "backup_info": {
            "backup_root": str(backup_root) if backup_root else "",
            "backup_state_path": str(backup_state_path) if backup_state_path else "",
            "backup_created": backup_created,
            "state_hash_before": state_hash_before,
            "backup_hash": backup_hash,
            "backup_hash_match": backup_hash_match,
        },
        "common_checks": common_integrity,
        "state_update": {
            "authoritative_state_advanced": authoritative_state_advanced,
            "updated_units_count": updated_units_count,
            "persistence_increment_count": persistence_increment_count,
        },
        "temporal_gap_count": temporal_gap_count,
        "same_run_noop_dry_check": {
            "rule_present": "no-op" in same_run_noop_rule,
            "idempotent_noop_count": idempotent_noop_count,
        },
        "restore_info": {
            "restore_executed": restore_executed,
            "restore_succeeded": restore_succeeded,
            "restore_reason": restore_reason,
        },
        "go_hold_decision": decision,
        "blocker_labels": blocker_labels,
        "next_task_recommendation": {
            "id": "TASK256",
            "title": "EXHIBITIONS-TEXT-READY-RESTART-WITH-ESCALATE-MONITORING-PHASE-4-CONTINUATION",
            "ja": "Continue READY restart cycle while keeping ESCALATE separate lane monitoring with strict boundaries",
        },
    }

    escalate_summary = {
        "artifact": "exhibitions_text_ready_restart_with_escalate_monitoring_phase3_continuation_escalate_summary",
        "task": "TASK255",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "inputs": {
            "task254_escalate_input_csv": str(Path(args.task254_escalate_input_csv)),
            "task254_escalate_summary_json": str(Path(args.task254_escalate_summary_json)),
            "state_latest_json": str(state_path),
        },
        "escalate_lane_result": {
            "escalate_lane_count": len(escalate_rows),
            "persistence_advanced_count": persistence_advanced_count,
            "ratio_two_consecutive_fired_count": ratio_two_consecutive_fired_count,
            "route_degradation_fired_count": route_degradation_fired_count,
            "escalate_blocker_count": escalate_blocker_count,
            "by_fair": escalate_by_fair,
            "by_gallery": escalate_by_gallery,
        },
        "common_checks": common_integrity,
        "state_update": {
            "authoritative_state_advanced": authoritative_state_advanced,
            "updated_units_count": updated_units_count,
            "persistence_increment_count": persistence_increment_count,
        },
        "temporal_gap_count": temporal_gap_count,
        "same_run_noop_dry_check": {
            "idempotent_noop_count": idempotent_noop_count,
        },
        "go_hold_decision": decision,
        "blocker_labels": blocker_labels,
    }

    ready_input_path = (
        output_dir / "exhibitions_text_ready_restart_with_escalate_monitoring_phase3_continuation_ready_input_task255.csv"
    )
    ready_summary_path = (
        output_dir / "exhibitions_text_ready_restart_with_escalate_monitoring_phase3_continuation_ready_summary_task255.json"
    )
    ready_manifest_path = (
        output_dir / "exhibitions_text_ready_restart_with_escalate_monitoring_phase3_continuation_ready_manifest_task255.json"
    )
    escalate_input_path = (
        output_dir / "exhibitions_text_ready_restart_with_escalate_monitoring_phase3_continuation_escalate_input_task255.csv"
    )
    escalate_summary_path = (
        output_dir / "exhibitions_text_ready_restart_with_escalate_monitoring_phase3_continuation_escalate_summary_task255.json"
    )
    escalate_manifest_path = (
        output_dir
        / "exhibitions_text_ready_restart_with_escalate_monitoring_phase3_continuation_escalate_manifest_task255.json"
    )
    monitored_diff_path = (
        output_dir / "exhibitions_text_ready_restart_with_escalate_monitoring_phase3_continuation_monitored_diff_task255.csv"
    )
    preflight_path = (
        output_dir / "exhibitions_text_ready_restart_with_escalate_monitoring_phase3_continuation_preflight_task255.csv"
    )
    backup_log_path = (
        output_dir / "exhibitions_text_ready_restart_with_escalate_monitoring_phase3_continuation_backup_log_task255.json"
    )
    by_fair_path = (
        output_dir / "exhibitions_text_ready_restart_with_escalate_monitoring_phase3_continuation_by_fair_task255.csv"
    )
    by_gallery_path = (
        output_dir / "exhibitions_text_ready_restart_with_escalate_monitoring_phase3_continuation_by_gallery_task255.csv"
    )
    report_path = output_dir / "exhibitions_text_ready_restart_with_escalate_monitoring_phase3_continuation_task255.md"

    if ready_rows:
        write_csv(ready_input_path, ready_rows, list(ready_rows[0].keys()))
    else:
        write_csv(ready_input_path, [], ["gallery_name_en", "fair_slug", "target_year", "source_url"])

    if escalate_rows:
        write_csv(escalate_input_path, escalate_rows, list(escalate_rows[0].keys()))
    else:
        write_csv(escalate_input_path, [], ["gallery_name_en", "fair_slug", "target_year", "source_url"])

    write_json(ready_summary_path, ready_summary)
    write_json(escalate_summary_path, escalate_summary)
    write_csv(
        preflight_path,
        preflight_rows,
        ["check_label", "actual", "expected", "status", "is_blocker"],
    )
    write_csv(
        monitored_diff_path,
        monitored_diff_rows,
        [
            "monitor_key",
            "fair_slug",
            "gallery_name_en",
            "source_url",
            "persistence_before",
            "persistence_after",
            "increment",
            "warning_before",
            "warning_after",
            "route_degradation_flag",
            "ratio_threshold_exceeded",
            "ratio_two_consecutive",
            "escalate_trigger_persistence",
            "escalate_trigger_ratio",
            "escalate_trigger_route",
            "escalate_now",
            "escalate_blocker",
        ],
    )
    write_json(
        backup_log_path,
        {
            "run_id": run_id,
            "backup_root": str(backup_root) if backup_root else "",
            "backup_state_path": str(backup_state_path) if backup_state_path else "",
            "backup_created": backup_created,
            "state_hash_before": state_hash_before,
            "backup_hash": backup_hash,
            "backup_hash_match": backup_hash_match,
            "restore_executed": restore_executed,
            "restore_succeeded": restore_succeeded,
            "restore_reason": restore_reason,
        },
    )
    write_csv(
        by_fair_path,
        by_fair_rows,
        ["fair_slug", "ready_restart_count", "escalate_lane_count", "holding_excluded_count"],
    )
    write_csv(
        by_gallery_path,
        by_gallery_rows,
        ["gallery_fair_key", "ready_restart_count", "escalate_lane_count"],
    )

    ready_manifest = {
        "artifact": "exhibitions_text_ready_restart_with_escalate_monitoring_phase3_continuation_ready_manifest",
        "task": "TASK255",
        "run_id": run_id,
        "inputs": ready_summary["inputs"],
        "outputs": {
            "ready_input_csv": str(ready_input_path),
            "ready_summary_json": str(ready_summary_path),
            "preflight_csv": str(preflight_path),
            "by_fair_csv": str(by_fair_path),
            "by_gallery_csv": str(by_gallery_path),
            "backup_log_json": str(backup_log_path),
            "manifest_json": str(ready_manifest_path),
            "report_md": str(report_path),
        },
        "decision": decision,
    }
    escalate_manifest = {
        "artifact": "exhibitions_text_ready_restart_with_escalate_monitoring_phase3_continuation_escalate_manifest",
        "task": "TASK255",
        "run_id": run_id,
        "inputs": escalate_summary["inputs"],
        "outputs": {
            "escalate_input_csv": str(escalate_input_path),
            "escalate_summary_json": str(escalate_summary_path),
            "monitored_diff_csv": str(monitored_diff_path),
            "by_fair_csv": str(by_fair_path),
            "by_gallery_csv": str(by_gallery_path),
            "backup_log_json": str(backup_log_path),
            "manifest_json": str(escalate_manifest_path),
            "report_md": str(report_path),
        },
        "decision": decision,
    }
    write_json(ready_manifest_path, ready_manifest)
    write_json(escalate_manifest_path, escalate_manifest)

    report_lines = [
        "# TASK255 Exhibitions Text Ready Restart with Escalate Monitoring Phase3 Continuation",
        "",
        "## run",
        f"- incoming_run_id={run_id}",
        f"- run_id_unique_before_ingest={run_id not in ingested_run_set}",
        "",
        "## preflight_backup",
        f"- preflight_pass={ready_summary['preflight']['pass_count']}/{ready_summary['preflight']['check_total']}",
        f"- backup_created={backup_created}",
        f"- backup_hash_match={backup_hash_match}",
        "",
        "## ready_side",
        f"- ready_input_count={len(ready_rows)}",
        f"- boundary_breach_count={boundary_breach_count}",
        f"- integrity_clear={integrity_clear}",
        "",
        "## escalate_side",
        f"- escalate_lane_count={len(escalate_rows)}",
        f"- persistence_advanced_count={persistence_advanced_count}",
        f"- ratio_two_consecutive_fired_count={ratio_two_consecutive_fired_count}",
        f"- route_degradation_fired_count={route_degradation_fired_count}",
        f"- escalate_blocker_count={escalate_blocker_count}",
        "",
        "## post_checks",
        f"- temporal_gap_count={temporal_gap_count}",
        f"- same_run_noop_dry_count={idempotent_noop_count}",
        f"- restore_executed={restore_executed}",
        f"- restore_succeeded={restore_succeeded}",
        "",
        "## decision",
        f"- go_hold_decision={decision}",
        f"- blocker_labels={blocker_labels}",
    ]
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(
        "[task255] "
        f"run_id={run_id} ready={len(ready_rows)} escalate={len(escalate_rows)} "
        f"boundary={boundary_breach_count} integrity_clear={integrity_clear} "
        f"increment={persistence_advanced_count} ratio={ratio_two_consecutive_fired_count} "
        f"route={route_degradation_fired_count} escalate_blocker={escalate_blocker_count} "
        f"gap={temporal_gap_count} restore={restore_executed} decision={decision}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

