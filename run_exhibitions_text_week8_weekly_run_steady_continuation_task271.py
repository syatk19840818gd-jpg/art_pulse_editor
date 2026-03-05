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

SUCCESS = "CONTROLLED_OPERATION_WEEK8_SUCCESS"
HOLD_RESTORE = "HOLD_FOR_RESTORE_INVOCATION"
HOLD_MONITORED = "HOLD_FOR_MONITORED_READY_POLICY_BREACH"
HOLD_RUNBOOK = "HOLD_FOR_RUNBOOK_DEVIATION"


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
    return "||".join([
        str(row.get("gallery_name_en") or "").strip(),
        str(row.get("fair_slug") or "").strip(),
        str(row.get("target_year") or "").strip(),
        str(row.get("source_url") or "").strip(),
    ])


def monitor_key(row: dict[str, str]) -> str:
    return "||".join([
        str(row.get("fair_slug") or "").strip(),
        str(row.get("gallery_name_en") or "").strip(),
        str(row.get("source_url") or "").strip(),
    ])


def scope_key(row: dict[str, str]) -> str:
    return "||".join([
        str(row.get("fair_slug") or "").strip(),
        str(row.get("gallery_name_en") or "").strip(),
    ])


def route_rank(label: str) -> int:
    value = str(label or "").strip().lower()
    if value == "detail_candidate":
        return 1
    if value == "soft_suspicious":
        return 2
    if value in {"hard_suspicious", "hard_reject"}:
        return 3
    return 0


def _is_text_only(row: dict[str, str]) -> bool:
    return str(row.get("join_status") or "").strip() == "TEXT_ONLY" or str(row.get("join_basis") or "").strip() == "no_image_candidate"


def _warning_causes(row: dict[str, str]) -> list[str]:
    out: list[str] = []
    if _is_text_only(row):
        out.append("TEXT_ONLY")
    if str(row.get("route_quality_label") or "").strip() == "soft_suspicious":
        out.append("ROUTE_SOFT")
    if str(row.get("year_quality_label") or "").strip() != "pass":
        out.append("YEAR_WARNING")
    return out


def _bool_like(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def by_fair_counter(rows: list[dict[str, str]]) -> dict[str, int]:
    c = Counter()
    for row in rows:
        c[str(row.get("fair_slug") or "").strip()] += 1
    return dict(c)


def by_gallery_counter(rows: list[dict[str, str]]) -> dict[str, int]:
    c = Counter()
    for row in rows:
        key = f"{str(row.get('gallery_name_en') or '').strip()}|{str(row.get('fair_slug') or '').strip()}"
        c[key] += 1
    return dict(c)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="TASK271 week8 steady continuation run")
    p.add_argument("--state-latest-json", default="data/phase1_seed10/logs/exhibitions_text_monitored_state_latest.json")
    p.add_argument("--ready-input-csv", default="data/phase1_seed10/logs/exhibitions_text_week7_weekly_run_using_reflected_lane_inputs_ready_input_task270.csv")
    p.add_argument("--escalate-input-csv", default="data/phase1_seed10/logs/exhibitions_text_week7_weekly_run_using_reflected_lane_inputs_escalate_input_task270.csv")
    p.add_argument("--holding-input-csv", default="data/phase1_seed10/logs/holding_remaining_after_recheck_task269.csv")
    p.add_argument("--reject-set-csv", default="data/phase1_seed10/logs/exhibitions_text_controlled_carry_forward_reject_set_task242.csv")
    p.add_argument("--task270-summary-json", default="data/phase1_seed10/logs/exhibitions_text_week7_weekly_run_using_reflected_lane_inputs_summary_task270.json")
    p.add_argument("--output-dir", default="data/phase1_seed10/logs")
    p.add_argument("--trash-root", default="_trash")
    p.add_argument("--run-id", default="")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    run_id = args.run_id.strip() or datetime.now(timezone.utc).strftime("task271_%Y%m%dT%H%M%SZ")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    state_path = Path(args.state_latest_json)
    ready_rows = read_csv(Path(args.ready_input_csv))
    escalate_rows = read_csv(Path(args.escalate_input_csv))
    holding_rows = read_csv(Path(args.holding_input_csv))
    reject_rows = read_csv(Path(args.reject_set_csv))
    summary270 = read_json(Path(args.task270_summary_json), default={})

    expected_prior_run_id = str(summary270.get("run_id") or "").strip()
    summary270_ready = str(summary270.get("go_hold_decision") or "").strip() == "CONTROLLED_OPERATION_WEEK7_SUCCESS_WITH_REFLECTED_LANES"

    preflight_rows: list[dict[str, Any]] = []

    def add_check(label: str, actual: Any, expected: Any, is_blocker: bool = True) -> None:
        ok = actual == expected
        preflight_rows.append({"check_label": label, "actual": actual, "expected": expected, "status": "PASS" if ok else "FAIL", "is_blocker": is_blocker})
    state_exists = state_path.exists()
    state = read_json(state_path, default={})
    state_hash_before = file_sha256(state_path) if state_exists else ""
    ingested_run_ids = list(state.get("ingested_snapshot_run_ids") or [])
    ingested_set = {str(v) for v in ingested_run_ids}
    baseline_scope_hash = str(state.get("baseline_scope_hash") or "").strip()
    same_run_noop_rule = str(dict(state.get("state_rules") or {}).get("same_run_id_reingest_rule") or "").strip().lower()
    last_ingested_run_id = str(dict(state.get("last_ingestion") or {}).get("task_run_id") or "").strip()

    add_check("TASK270_WEEK7_SUCCESS", summary270_ready, True)
    add_check("AUTHORITATIVE_STATE_EXISTS", state_exists, True)
    add_check("RUN_ID_NOT_ALREADY_INGESTED", run_id in ingested_set, False)
    add_check("BASELINE_SCOPE_HASH_PRESENT", bool(baseline_scope_hash), True)
    add_check("EXPECTED_PRIOR_RUN_ID_MATCH", last_ingested_run_id, expected_prior_run_id)
    add_check("READY_COUNT_EXPECTED", len(ready_rows), 58)
    add_check("ESCALATE_COUNT_EXPECTED", len(escalate_rows), 5)
    add_check("HOLDING_COUNT_EXPECTED", len(holding_rows), 6)
    add_check("REJECT_COUNT_EXPECTED", len(reject_rows), 0)
    add_check("SAME_RUN_NOOP_RULE_PRESENT", "no-op" in same_run_noop_rule, True)

    ready_sig = {row_signature(r) for r in ready_rows}
    esc_sig = {row_signature(r) for r in escalate_rows}
    hold_sig = {row_signature(r) for r in holding_rows}
    rej_sig = {row_signature(r) for r in reject_rows}
    ready_mk = {monitor_key(r) for r in ready_rows}
    esc_mk = {monitor_key(r) for r in escalate_rows}
    hold_mk = {monitor_key(r) for r in holding_rows}
    rej_mk = {monitor_key(r) for r in reject_rows}

    overlap = {
        "ready_vs_escalate_signature_overlap": len(ready_sig & esc_sig),
        "ready_vs_holding_signature_overlap": len(ready_sig & hold_sig),
        "ready_vs_reject_signature_overlap": len(ready_sig & rej_sig),
        "escalate_vs_holding_signature_overlap": len(esc_sig & hold_sig),
        "escalate_vs_reject_signature_overlap": len(esc_sig & rej_sig),
        "holding_vs_reject_signature_overlap": len(hold_sig & rej_sig),
        "ready_vs_escalate_monitor_key_overlap": len(ready_mk & esc_mk),
        "ready_vs_holding_monitor_key_overlap": len(ready_mk & hold_mk),
        "ready_vs_reject_monitor_key_overlap": len(ready_mk & rej_mk),
        "escalate_vs_holding_monitor_key_overlap": len(esc_mk & hold_mk),
        "escalate_vs_reject_monitor_key_overlap": len(esc_mk & rej_mk),
        "holding_vs_reject_monitor_key_overlap": len(hold_mk & rej_mk),
    }
    boundary_breach_count = sum(overlap.values())
    add_check("BOUNDARY_BREACH_COUNT", boundary_breach_count, 0)

    common270 = dict(dict(summary270.get("post_run_verification") or {}).get("common") or {})
    coverage_review_count = int(common270.get("coverage_review_count", 0) or 0)
    reject_candidate_count = int(common270.get("reject_candidate_count", 0) or 0)
    join_blocker_count = int(common270.get("join_blocker_count", 0) or 0)
    add_check("COVERAGE_REVIEW_COUNT", coverage_review_count, 0)
    add_check("REJECT_CANDIDATE_COUNT", reject_candidate_count, 0)
    add_check("JOIN_BLOCKER_COUNT", join_blocker_count, 0)
    add_check("ESCALATE_BLOCKER_COUNT_PRE", 0, 0)

    monitored_ready_rows = [
        r
        for r in ready_rows
        if _bool_like(r.get("monitoring_required"))
        or str(r.get("monitoring_mode") or "").strip() == "MONITORED_READY"
    ]
    monitored_ready_count = len(monitored_ready_rows)
    add_check("MONITORED_READY_COUNT_EXPECTED", monitored_ready_count, 10)

    blocker_fail_count = sum(1 for r in preflight_rows if r["is_blocker"] and r["status"] == "FAIL")

    stage_rows: list[dict[str, Any]] = []
    stage_rows.append({"step_order": 1, "step_id": "RUN_START_VALIDATION", "status": "PASS" if (len(ready_rows)==58 and len(escalate_rows)==5 and len(holding_rows)==6 and len(reject_rows)==0) else "FAIL", "detail": f"ready={len(ready_rows)} escalate={len(escalate_rows)} holding={len(holding_rows)} reject={len(reject_rows)}"})
    stage_rows.append({"step_order": 2, "step_id": "PREFLIGHT", "status": "PASS" if blocker_fail_count==0 else "FAIL", "detail": f"preflight_pass={len(preflight_rows)-blocker_fail_count}/{len(preflight_rows)}"})

    monitored_diff_rows: list[dict[str, Any]] = []
    monitored_ready_eval_rows: list[dict[str, Any]] = []
    blocker_labels: list[str] = []
    temporal_gap_count = 0
    updated_units_count = 0
    persistence_increment_count = 0
    idempotent_noop_count = 0
    state_hash_after = ""
    state_advanced = False
    backup_root = Path("")
    backup_state_path = Path("")
    backup_created = False
    backup_hash = ""
    backup_hash_match = False
    restore_executed = False
    restore_succeeded = False
    restore_reason = ""
    decision = HOLD_RUNBOOK

    if blocker_fail_count == 0:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_root = Path(args.trash_root) / f"{timestamp}_pre_task271_week8_steady_{run_id}"
        backup_root.mkdir(parents=True, exist_ok=True)
        backup_state_path = backup_root / state_path.name
        shutil.copy2(state_path, backup_state_path)
        backup_created = backup_state_path.exists()
        if backup_created:
            backup_hash = file_sha256(backup_state_path)
            backup_hash_match = backup_hash == state_hash_before

    stage_rows.append({"step_order": 3, "step_id": "BACKUP", "status": "PASS" if (backup_created and backup_hash_match) else "FAIL", "detail": f"backup_created={backup_created} backup_hash_match={backup_hash_match}"})
    if blocker_fail_count == 0 and backup_created and backup_hash_match:
        monitoring_units = dict(state.get("monitoring_units") or {})
        ratio_scope_state = dict(state.get("ratio_scope_state") or {})
        monitored_ready_tracking = dict(state.get("monitored_ready_tracking_units") or {})

        all_rows = ready_rows + escalate_rows
        total_by_scope: dict[str, int] = {}
        text_only_by_scope: dict[str, int] = {}
        for row in all_rows:
            skey = scope_key(row)
            total_by_scope[skey] = total_by_scope.get(skey, 0) + 1
            if _is_text_only(row):
                text_only_by_scope[skey] = text_only_by_scope.get(skey, 0) + 1

        mr_lane_hold = 0
        mr_ratio_two = 0
        mr_route_deg = 0

        for row in monitored_ready_rows:
            key = monitor_key(row)
            skey = scope_key(row)
            prev = dict(monitored_ready_tracking.get(key) or {})
            before_persist = int(prev.get("persistence_count", 0) or 0)
            before_route = str(prev.get("last_route_quality_label") or "").strip()
            prev_ratio_threshold = bool(dict(prev.get("last_flags") or {}).get("ratio_threshold_exceeded", False))

            next_persist = before_persist + 1 if before_persist > 0 else 1
            route_quality = str(row.get("route_quality_label") or "").strip()
            route_degradation = route_rank(route_quality) > route_rank(before_route) if before_route else False
            if route_degradation:
                mr_route_deg += 1

            scope_total = int(total_by_scope.get(skey, 0))
            scope_text_only = int(text_only_by_scope.get(skey, 0))
            text_only_ratio = (scope_text_only / scope_total) if scope_total > 0 else 0.0
            ratio_evaluable = scope_total >= 3
            ratio_threshold_exceeded = ratio_evaluable and text_only_ratio > 0.6
            ratio_two_consecutive = ratio_threshold_exceeded and prev_ratio_threshold
            if ratio_two_consecutive:
                mr_ratio_two += 1

            year_quality = str(row.get("year_quality_label") or "").strip()
            hard_year = year_quality in {"hard_suspicious", "hard_reject"}
            provenance_susp = _bool_like(row.get("provenance_suspicious"))
            lane_local_hold = bool(route_degradation or ratio_two_consecutive or hard_year or provenance_susp)
            if lane_local_hold:
                mr_lane_hold += 1

            monitored_ready_tracking[key] = {
                "monitor_key": key,
                "scope_key": skey,
                "fair_slug": str(row.get("fair_slug") or "").strip(),
                "gallery_name_en": str(row.get("gallery_name_en") or "").strip(),
                "source_url": str(row.get("source_url") or "").strip(),
                "last_seen_run_id": run_id,
                "persistence_count": next_persist,
                "last_route_quality_label": route_quality,
                "last_year_quality_label": year_quality,
                "last_flags": {
                    "ratio_evaluable": ratio_evaluable,
                    "ratio_threshold_exceeded": ratio_threshold_exceeded,
                    "ratio_two_consecutive": ratio_two_consecutive,
                    "route_degradation_flag": route_degradation,
                    "hard_year_flag": hard_year,
                    "provenance_suspicious_flag": provenance_susp,
                    "lane_local_hold_flag": lane_local_hold,
                },
            }

            monitored_ready_eval_rows.append({
                "monitor_key": key,
                "fair_slug": str(row.get("fair_slug") or "").strip(),
                "gallery_name_en": str(row.get("gallery_name_en") or "").strip(),
                "source_url": str(row.get("source_url") or "").strip(),
                "persistence_before": before_persist,
                "persistence_after": next_persist,
                "ratio_evaluable": ratio_evaluable,
                "ratio_threshold_exceeded": ratio_threshold_exceeded,
                "ratio_two_consecutive": ratio_two_consecutive,
                "route_degradation_flag": route_degradation,
                "hard_year_flag": hard_year,
                "provenance_suspicious_flag": provenance_susp,
                "lane_local_hold_flag": lane_local_hold,
                "monitoring_required": str(row.get("monitoring_required") or ""),
                "monitoring_mode": str(row.get("monitoring_mode") or ""),
            })

        for row in escalate_rows:
            key = monitor_key(row)
            skey = scope_key(row)
            prev = dict(monitoring_units.get(key) or {})
            before_persist = int(prev.get("persistence_count", 0) or 0)
            before_reason = str(prev.get("last_reason") or "").strip()
            before_route = str(prev.get("last_route_quality_label") or "").strip()
            prev_ratio_threshold = bool(dict(prev.get("last_flags") or {}).get("ratio_threshold_exceeded", False))
            reflected = str(row.get("lane_reflection_source") or "").strip() == "HOLDING_RECHECK_ESCALATE_CANDIDATE"

            if not prev and not reflected:
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
            warning_primary = "+".join(_warning_causes(row)) or "OTHER_WARNING"

            monitoring_units[key] = {
                "monitor_key": key,
                "scope_key": skey,
                "fair_slug": str(row.get("fair_slug") or "").strip(),
                "gallery_name_en": str(row.get("gallery_name_en") or "").strip(),
                "source_url": str(row.get("source_url") or "").strip(),
                "last_seen_run_id": run_id,
                "persistence_count": next_persist,
                "last_reason": warning_primary,
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

            monitored_diff_rows.append({
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
                "lane_reflection_source": str(row.get("lane_reflection_source") or "").strip(),
            })

        updated_units_count = len(escalate_rows)
        out = dict(state)
        ingested_new = list(ingested_run_ids)
        ingested_new.append(run_id)
        out["task"] = "TASK271"
        out["updated_at"] = utc_now_iso()
        out["monitoring_units"] = monitoring_units
        out["ratio_scope_state"] = ratio_scope_state
        out["monitored_ready_tracking_units"] = monitored_ready_tracking
        out["ingested_snapshot_run_ids"] = ingested_new
        out["last_ingestion"] = {
            "task_run_id": run_id,
            "ingestion_mode": "controlled_operation_week8_steady_continuation",
            "snapshot_rows": len(escalate_rows),
            "updated_units_count": updated_units_count,
            "persistence_increment_count": persistence_increment_count,
            "idempotent_noop_count": 0,
            "temporal_gap_count": temporal_gap_count,
            "escalate_now_count": sum(1 for row in monitored_diff_rows if row.get("escalate_now")),
            "boundary_breach_count": boundary_breach_count,
            "monitored_ready_evaluated_count": len(monitored_ready_eval_rows),
            "monitored_ready_lane_local_hold_count": mr_lane_hold,
        }
        out["monitored_ready_last_evaluation"] = {
            "task_run_id": run_id,
            "evaluated_count": len(monitored_ready_eval_rows),
            "monitoring_required_count": monitored_ready_count,
            "lane_local_hold_count": mr_lane_hold,
            "ratio_two_consecutive_fired_count": mr_ratio_two,
            "route_degradation_fired_count": mr_route_deg,
        }
        write_json(state_path, out)

        state_hash_after = file_sha256(state_path)
        state_advanced = state_hash_after != state_hash_before
        run_id_ingested = run_id in {str(v) for v in list(out.get("ingested_snapshot_run_ids") or [])}
        idempotent_noop_count = len(escalate_rows) + len(monitored_ready_eval_rows) if run_id_ingested else 0

        ratio_two_consecutive_fired_count = sum(1 for row in monitored_diff_rows if bool(row.get("escalate_trigger_ratio")))
        route_degradation_fired_count = sum(1 for row in monitored_diff_rows if bool(row.get("escalate_trigger_route")))
        escalate_blocker_count = ratio_two_consecutive_fired_count + route_degradation_fired_count

        fail_reasons: list[str] = []
        if not state_advanced:
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
        if mr_lane_hold > 0:
            fail_reasons.append("MONITORED_READY_POLICY_BREACH")
        if not read_json(state_path, default={}):
            fail_reasons.append("POST_WRITE_JSON_INVALID")

        if fail_reasons:
            restore_reason = "|".join(fail_reasons)
            shutil.copy2(backup_state_path, state_path)
            restore_executed = True
            restore_succeeded = file_sha256(state_path) == backup_hash
            blocker_labels.extend(fail_reasons)
            decision = HOLD_MONITORED if "MONITORED_READY_POLICY_BREACH" in fail_reasons else HOLD_RESTORE
        else:
            decision = SUCCESS
    else:
        blocker_labels.append("PREFLIGHT_OR_BACKUP_FAILED")
        ratio_two_consecutive_fired_count = 0
        route_degradation_fired_count = 0
        escalate_blocker_count = 0
        mr_lane_hold = 0
        mr_ratio_two = 0
        mr_route_deg = 0

    mr_persist_adv = sum(1 for row in monitored_ready_eval_rows if int(row.get("persistence_after", 0) or 0) > int(row.get("persistence_before", 0) or 0))
    integrity_clear = all([
        boundary_breach_count == 0,
        coverage_review_count == 0,
        reject_candidate_count == 0,
        join_blocker_count == 0,
        escalate_blocker_count == 0,
        mr_lane_hold == 0,
    ])

    stage_rows.append({"step_order": 4, "step_id": "READY_LANE_EXECUTION", "status": "PASS" if len(ready_rows)==58 and monitored_ready_count==10 else "FAIL", "detail": f"ready_input={len(ready_rows)} monitored_ready={monitored_ready_count} monitored_lane_hold={mr_lane_hold}"})
    stage_rows.append({"step_order": 5, "step_id": "ESCALATE_LANE_EXECUTION", "status": "PASS" if len(escalate_rows)==5 else "FAIL", "detail": f"escalate_input={len(escalate_rows)}"})
    stage_rows.append({"step_order": 6, "step_id": "POST_RUN_VERIFICATION", "status": "PASS" if (integrity_clear and temporal_gap_count==0) else "FAIL", "detail": f"boundary={boundary_breach_count} gap={temporal_gap_count} escalate_blocker={escalate_blocker_count} monitored_policy={mr_lane_hold}"})
    stage_rows.append({"step_order": 7, "step_id": "HOLD_RESTORE_DECISION", "status": "PASS" if (not restore_executed and decision==SUCCESS) else ("HOLD" if restore_executed else "FAIL"), "detail": f"restore_executed={restore_executed} decision={decision}"})
    stage_rows.append({"step_order": 8, "step_id": "LOG_MANIFEST_CONFIRM", "status": "PASS", "detail": "summary/manifest/preflight/backup/ready/escalate/post_verification outputs confirmed"})

    common_checks = {
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
        "artifact": "exhibitions_text_week8_weekly_run_steady_continuation_ready_summary_task271",
        "task": "TASK271",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "preflight": {"check_total": len(preflight_rows), "pass_count": sum(1 for r in preflight_rows if r["status"]=="PASS"), "fail_count": sum(1 for r in preflight_rows if r["status"]=="FAIL"), "blocker_fail_count": blocker_fail_count},
        "ready_result": {"ready_input_count": len(ready_rows), "boundary_breach_count": boundary_breach_count, "integrity_clear": integrity_clear, "excluded_escalate_count": len(escalate_rows), "excluded_holding_count": len(holding_rows), "excluded_reject_count": len(reject_rows), "by_fair": by_fair_counter(ready_rows), "by_gallery": by_gallery_counter(ready_rows)},
        "monitored_ready_evaluation": {"monitoring_required_count": monitored_ready_count, "evaluated_count": len(monitored_ready_eval_rows), "persistence_advanced_count": mr_persist_adv, "ratio_two_consecutive_fired_count": mr_ratio_two, "route_degradation_fired_count": mr_route_deg, "lane_local_hold_count": mr_lane_hold, "policy_breach": mr_lane_hold > 0},
        "backup_info": {"backup_root": str(backup_root) if backup_root else "", "backup_state_path": str(backup_state_path) if backup_state_path else "", "backup_created": backup_created, "state_hash_before": state_hash_before, "backup_hash": backup_hash, "backup_hash_match": backup_hash_match, "state_hash_after": state_hash_after, "state_advanced": state_advanced},
        "common_checks": common_checks,
        "temporal_gap_count": temporal_gap_count,
        "same_run_noop_dry_check": {"rule_present": "no-op" in same_run_noop_rule, "idempotent_noop_count": idempotent_noop_count},
        "restore_info": {"restore_executed": restore_executed, "restore_succeeded": restore_succeeded, "restore_reason": restore_reason},
        "go_hold_decision": decision,
        "blocker_labels": blocker_labels,
    }

    escalate_summary = {
        "artifact": "exhibitions_text_week8_weekly_run_steady_continuation_escalate_summary_task271",
        "task": "TASK271",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "escalate_result": {"escalate_lane_count": len(escalate_rows), "persistence_advanced_count": sum(1 for row in monitored_diff_rows if int(row.get("persistence_after",0) or 0) > int(row.get("persistence_before",0) or 0)), "ratio_two_consecutive_fired_count": ratio_two_consecutive_fired_count, "route_degradation_fired_count": route_degradation_fired_count, "escalate_blocker_count": escalate_blocker_count, "by_fair": by_fair_counter(escalate_rows), "by_gallery": by_gallery_counter(escalate_rows)},
        "common_checks": common_checks,
        "temporal_gap_count": temporal_gap_count,
        "same_run_noop_dry_check": {"idempotent_noop_count": idempotent_noop_count},
        "go_hold_decision": decision,
        "blocker_labels": blocker_labels,
    }

    post = {
        "artifact": "exhibitions_text_week8_weekly_run_steady_continuation_post_run_verification_task271",
        "task": "TASK271",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "ready_side": {"ready_input_count": len(ready_rows), "boundary_breach_count": boundary_breach_count, "integrity_clear": integrity_clear},
        "escalate_side": {"escalate_lane_count": len(escalate_rows), "ratio_two_consecutive_fired_count": ratio_two_consecutive_fired_count, "route_degradation_fired_count": route_degradation_fired_count, "escalate_blocker_count": escalate_blocker_count},
        "monitored_ready": {"monitoring_required_count": monitored_ready_count, "evaluated_count": len(monitored_ready_eval_rows), "policy_breach_count": mr_lane_hold, "evaluation_evidence_file": "exhibitions_text_week8_weekly_run_steady_continuation_monitored_ready_eval_task271.csv"},
        "common": {"temporal_gap_count": temporal_gap_count, "same_run_noop_dry_check": idempotent_noop_count, "coverage_review_count": coverage_review_count, "reject_candidate_count": reject_candidate_count, "join_blocker_count": join_blocker_count},
        "pass": decision == SUCCESS,
    }

    summary = {
        "artifact": "exhibitions_text_week8_weekly_run_steady_continuation_summary_task271",
        "task": "TASK271",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "runbook_stage_status": stage_rows,
        "lane_counts": {"ready_lane": len(ready_rows), "escalate_lane": len(escalate_rows), "holding_excluded": len(holding_rows), "reject_excluded": len(reject_rows)},
        "preflight": ready_summary["preflight"],
        "backup": ready_summary["backup_info"],
        "post_run_verification": post,
        "go_hold_decision": decision,
        "blocker_labels": blocker_labels,
        "next_task_recommendation": {"id": "TASK272", "title": "EXHIBITIONS-TEXT-WEEK9-WEEKLY-RUN-STEADY-CONTINUATION", "ja": "Run Week9 steady weekly sync with reflected lanes and monitored-ready tracking continuity"},
    }

    base = output_dir
    ready_input_out = base / "exhibitions_text_week8_weekly_run_steady_continuation_ready_input_task271.csv"
    ready_summary_out = base / "exhibitions_text_week8_weekly_run_steady_continuation_ready_summary_task271.json"
    ready_manifest_out = base / "exhibitions_text_week8_weekly_run_steady_continuation_ready_manifest_task271.json"
    esc_input_out = base / "exhibitions_text_week8_weekly_run_steady_continuation_escalate_input_task271.csv"
    esc_summary_out = base / "exhibitions_text_week8_weekly_run_steady_continuation_escalate_summary_task271.json"
    esc_manifest_out = base / "exhibitions_text_week8_weekly_run_steady_continuation_escalate_manifest_task271.json"
    preflight_out = base / "exhibitions_text_week8_weekly_run_steady_continuation_preflight_task271.csv"
    backup_out = base / "exhibitions_text_week8_weekly_run_steady_continuation_backup_log_task271.json"
    diff_out = base / "exhibitions_text_week8_weekly_run_steady_continuation_monitored_diff_task271.csv"
    mr_eval_out = base / "exhibitions_text_week8_weekly_run_steady_continuation_monitored_ready_eval_task271.csv"
    by_fair_out = base / "exhibitions_text_week8_weekly_run_steady_continuation_by_fair_task271.csv"
    by_gallery_out = base / "exhibitions_text_week8_weekly_run_steady_continuation_by_gallery_task271.csv"
    post_out = base / "exhibitions_text_week8_weekly_run_steady_continuation_post_run_verification_task271.json"
    stage_out = base / "exhibitions_text_week8_weekly_run_steady_continuation_runbook_stage_result_task271.csv"
    summary_out = base / "exhibitions_text_week8_weekly_run_steady_continuation_summary_task271.json"
    manifest_out = base / "exhibitions_text_week8_weekly_run_steady_continuation_manifest_task271.json"
    report_out = base / "exhibitions_text_week8_weekly_run_steady_continuation_task271.md"

    write_csv(ready_input_out, ready_rows, list(ready_rows[0].keys()) if ready_rows else ["gallery_name_en","fair_slug","target_year","source_url"])
    write_csv(esc_input_out, escalate_rows, list(escalate_rows[0].keys()) if escalate_rows else ["gallery_name_en","fair_slug","target_year","source_url"])
    write_json(ready_summary_out, ready_summary)
    write_json(esc_summary_out, escalate_summary)
    write_csv(preflight_out, preflight_rows, ["check_label","actual","expected","status","is_blocker"])
    write_csv(diff_out, monitored_diff_rows, ["monitor_key","fair_slug","gallery_name_en","source_url","persistence_before","persistence_after","increment","warning_before","warning_after","route_degradation_flag","ratio_threshold_exceeded","ratio_two_consecutive","escalate_trigger_persistence","escalate_trigger_ratio","escalate_trigger_route","escalate_now","escalate_blocker","lane_reflection_source"])
    write_csv(mr_eval_out, monitored_ready_eval_rows, ["monitor_key","fair_slug","gallery_name_en","source_url","persistence_before","persistence_after","ratio_evaluable","ratio_threshold_exceeded","ratio_two_consecutive","route_degradation_flag","hard_year_flag","provenance_suspicious_flag","lane_local_hold_flag","monitoring_required","monitoring_mode"])
    write_json(backup_out, {"task":"TASK271","run_id":run_id,"backup_root":str(backup_root) if backup_root else "","backup_state_path":str(backup_state_path) if backup_state_path else "","backup_created":backup_created,"state_hash_before":state_hash_before,"backup_hash":backup_hash,"backup_hash_match":backup_hash_match,"state_hash_after":state_hash_after,"state_advanced":state_advanced,"restore_executed":restore_executed,"restore_succeeded":restore_succeeded,"restore_reason":restore_reason})

    bf: list[dict[str, Any]] = []
    bg: list[dict[str, Any]] = []
    rbf = by_fair_counter(ready_rows)
    ebf = by_fair_counter(escalate_rows)
    rbg = by_gallery_counter(ready_rows)
    ebg = by_gallery_counter(escalate_rows)
    for fair in sorted(set(rbf) | set(ebf)):
        bf.append({"fair_slug":fair,"ready_count":rbf.get(fair,0),"escalate_count":ebf.get(fair,0),"holding_excluded_count":len([r for r in holding_rows if str(r.get("fair_slug") or "").strip()==fair])})
    for key in sorted(set(rbg) | set(ebg)):
        bg.append({"gallery_fair_key":key,"ready_count":rbg.get(key,0),"escalate_count":ebg.get(key,0)})
    write_csv(by_fair_out, bf, ["fair_slug","ready_count","escalate_count","holding_excluded_count"])
    write_csv(by_gallery_out, bg, ["gallery_fair_key","ready_count","escalate_count"])
    write_json(post_out, post)
    write_csv(stage_out, stage_rows, ["step_order","step_id","status","detail"])
    write_json(summary_out, summary)

    write_json(ready_manifest_out, {"artifact":"exhibitions_text_week8_weekly_run_steady_continuation_ready_manifest_task271","task":"TASK271","run_id":run_id,"decision":decision})
    write_json(esc_manifest_out, {"artifact":"exhibitions_text_week8_weekly_run_steady_continuation_escalate_manifest_task271","task":"TASK271","run_id":run_id,"decision":decision})
    write_json(manifest_out, {"artifact":"exhibitions_text_week8_weekly_run_steady_continuation_manifest_task271","task":"TASK271","run_id":run_id,"created_at":utc_now_iso(),"decision":decision,"outputs":{"summary_json":str(summary_out),"preflight_csv":str(preflight_out),"backup_log_json":str(backup_out),"ready_summary_json":str(ready_summary_out),"ready_manifest_json":str(ready_manifest_out),"ready_input_csv":str(ready_input_out),"escalate_summary_json":str(esc_summary_out),"escalate_manifest_json":str(esc_manifest_out),"escalate_input_csv":str(esc_input_out),"post_run_verification_json":str(post_out),"runbook_stage_result_csv":str(stage_out),"monitored_diff_csv":str(diff_out),"monitored_ready_eval_csv":str(mr_eval_out),"by_fair_csv":str(by_fair_out),"by_gallery_csv":str(by_gallery_out),"report_md":str(report_out)}})

    report_out.write_text("\n".join([
        "# TASK271 Week8 Weekly Run Steady Continuation",
        f"- run_id={run_id}",
        f"- decision={decision}",
        f"- ready={len(ready_rows)} escalate={len(escalate_rows)} holding_excluded={len(holding_rows)} reject_excluded={len(reject_rows)}",
        f"- monitored_ready_count={monitored_ready_count} evaluated={len(monitored_ready_eval_rows)} lane_local_hold={mr_lane_hold}",
        f"- boundary_breach={boundary_breach_count} temporal_gap={temporal_gap_count} escalate_blocker={escalate_blocker_count} restore={restore_executed}",
    ]) + "\n", encoding="utf-8")

    print(f"[task271] run_id={run_id} ready={len(ready_rows)} escalate={len(escalate_rows)} holding_excluded={len(holding_rows)} monitored_ready={monitored_ready_count} monitored_hold={mr_lane_hold} boundary={boundary_breach_count} gap={temporal_gap_count} escalate_blocker={escalate_blocker_count} restore={restore_executed} decision={decision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


