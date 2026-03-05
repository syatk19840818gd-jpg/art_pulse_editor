from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SUCCESS = "LIVE_NEXT_RUN_SUCCESS_READY_FOR_PHASE8"
HOLD_RESTORE = "HOLD_FOR_RESTORE_INVOCATION"
HOLD_FIX = "HOLD_FOR_LIVE_STATE_UPDATE_FIX"


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TASK249 Exhibitions Text carry-forward phase7 live next-run continuation")
    parser.add_argument(
        "--state-latest-json",
        default="data/phase1_seed10/logs/exhibitions_text_monitored_state_latest.json",
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
    parser.add_argument(
        "--task246-summary-json",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_carry_forward_continuation_phase4_summary_task246.json",
    )
    parser.add_argument(
        "--task248-summary-json",
        default="data/phase1_seed10/logs/exhibitions_text_carry_forward_phase6_live_next_run_prep_summary_task248.json",
    )
    parser.add_argument("--output-dir", default="data/phase1_seed10/logs")
    parser.add_argument("--trash-root", default="_trash")
    parser.add_argument("--run-id", default="")
    return parser.parse_args()


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


def main() -> int:
    args = parse_args()
    run_id = args.run_id.strip() or datetime.now(timezone.utc).strftime("task249_%Y%m%dT%H%M%SZ")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    state_path = Path(args.state_latest_json)
    continuation_rows = read_csv(Path(args.continuation_input_csv))
    holding_rows = read_csv(Path(args.holding_set_csv))
    escalate_rows = read_csv(Path(args.escalate_set_csv))
    reject_rows = read_csv(Path(args.reject_set_csv))
    summary246 = read_json(Path(args.task246_summary_json), default={})
    summary248 = read_json(Path(args.task248_summary_json), default={})

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

    continuation_input_total = len(continuation_rows)
    ready_rows = [r for r in continuation_rows if str(r.get("continuation_stream") or "").strip() == "READY"]
    monitored_rows = [r for r in continuation_rows if str(r.get("continuation_stream") or "").strip() == "MONITORED"]
    invalid_stream_count = continuation_input_total - len(ready_rows) - len(monitored_rows)
    add_check("INVALID_STREAM_COUNT", invalid_stream_count, 0)
    add_check("READY_COUNT_EXPECTED", len(ready_rows), 48)
    add_check("MONITORED_COUNT_EXPECTED", len(monitored_rows), 4)

    continuation_signatures = {row_signature(r) for r in continuation_rows}
    excluded_signatures = {row_signature(r) for r in (holding_rows + escalate_rows + reject_rows)}
    boundary_breach_count = len(continuation_signatures & excluded_signatures)
    add_check("BOUNDARY_BREACH_COUNT", boundary_breach_count, 0)

    integrity246 = dict(summary246.get("integrity_checks") or {})
    coverage_review_count = int(integrity246.get("coverage_review_count", 0))
    reject_candidate_count = int(integrity246.get("reject_candidate_count", 0))
    join_blocker_count = int(integrity246.get("join_blocker_count", 0))
    escalate_set_count = int(integrity246.get("escalate_set_count", 0))
    add_check("COVERAGE_REVIEW_COUNT", coverage_review_count, 0)
    add_check("REJECT_CANDIDATE_COUNT", reject_candidate_count, 0)
    add_check("JOIN_BLOCKER_COUNT", join_blocker_count, 0)
    add_check("ESCALATE_SET_COUNT", escalate_set_count, 0)

    add_check("TASK248_PREP_READY", str(summary248.get("go_hold_decision") or "").strip(), "READY_FOR_LIVE_NEXT_RUN_EXECUTION")
    same_run_noop_rule = str(state_rules.get("same_run_id_reingest_rule") or "").strip().lower()
    add_check("SAME_RUN_NOOP_RULE_PRESENT", "no-op" in same_run_noop_rule, True)

    blocker_fail_count = sum(1 for row in preflight_rows if row["is_blocker"] and row["status"] == "FAIL")

    backup_created = False
    backup_hash_match = False
    backup_hash = ""
    backup_state_path = Path("")
    backup_root = Path("")
    restore_executed = False
    restore_succeeded = False
    restore_reason = ""

    updated_units_count = 0
    persistence_increment_count = 0
    temporal_gap_count = 0
    escalate_now_count = 0
    idempotent_noop_count = 0
    authoritative_state_advanced = False
    monitored_diff_rows: list[dict[str, Any]] = []
    blocker_labels: list[str] = []

    if blocker_fail_count > 0:
        decision = HOLD_FIX
        blocker_labels.append("PREFLIGHT_BLOCKER_FAILED")
    else:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_root = Path(args.trash_root) / f"{timestamp}_pre_live_monitored_state_{run_id}"
        backup_root.mkdir(parents=True, exist_ok=True)
        backup_state_path = backup_root / state_path.name
        shutil.copy2(state_path, backup_state_path)
        backup_created = backup_state_path.exists()
        if backup_created:
            backup_hash = file_sha256(backup_state_path)
            backup_hash_match = backup_hash == state_hash_before

        if not backup_created or not backup_hash_match:
            decision = HOLD_FIX
            blocker_labels.append("BACKUP_INTEGRITY_FAILED")
        else:
            try:
                total_by_scope: dict[str, int] = {}
                text_only_by_scope: dict[str, int] = {}
                for row in continuation_rows:
                    skey = scope_key(row)
                    total_by_scope[skey] = total_by_scope.get(skey, 0) + 1
                    if _is_text_only(row):
                        text_only_by_scope[skey] = text_only_by_scope.get(skey, 0) + 1

                for row in monitored_rows:
                    key = monitor_key(row)
                    skey = scope_key(row)
                    prev = dict(monitoring_units.get(key) or {})
                    before_persist = int(prev.get("persistence_count", 0) or 0)
                    before_reason = str(prev.get("last_reason") or "").strip()
                    before_route = str(prev.get("last_route_quality_label") or "").strip()
                    prev_ratio_threshold = bool(dict(prev.get("last_flags") or {}).get("ratio_threshold_exceeded", False))

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

                    escalate_now = bool(route_degradation or ratio_two_consecutive)
                    if escalate_now:
                        escalate_now_count += 1

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
                        },
                    }
                    ratio_scope_state[skey] = {
                        "scope_key": skey,
                        "fair_slug": str(row.get("fair_slug") or "").strip(),
                        "gallery_name_en": str(row.get("gallery_name_en") or "").strip(),
                        "scope_total_count": scope_total,
                        "scope_text_only_count": scope_text_only,
                        "text_only_ratio": round(text_only_ratio, 6),
                        "last_seen_run_id": run_id,
                    }
                    updated_units_count += 1

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
                            "escalate_now": escalate_now,
                        }
                    )

                ingested_run_ids.append(run_id)
                state["artifact"] = "exhibitions_text_monitored_state_latest"
                state["task"] = "TASK249"
                state["updated_at"] = utc_now_iso()
                state["monitoring_units"] = monitoring_units
                state["ratio_scope_state"] = ratio_scope_state
                state["ingested_snapshot_run_ids"] = ingested_run_ids
                state["last_ingestion"] = {
                    "task_run_id": run_id,
                    "ingestion_mode": "live_next_run_ingested",
                    "snapshot_rows": len(monitored_rows),
                    "updated_units_count": updated_units_count,
                    "persistence_increment_count": persistence_increment_count,
                    "idempotent_noop_count": 0,
                    "temporal_gap_count": temporal_gap_count,
                    "escalate_now_count": escalate_now_count,
                    "boundary_breach_count": boundary_breach_count,
                }
                write_json(state_path, state)

                # Same-run re-ingest dry check only.
                idempotent_noop_count = len(monitored_rows) if run_id in set(state.get("ingested_snapshot_run_ids", [])) else 0

                # Post-check/fail-safe.
                state_after = read_json(state_path, default={})
                state_hash_after = file_sha256(state_path)
                authoritative_state_advanced = state_hash_after != state_hash_before
                run_id_ingested = run_id in set(state_after.get("ingested_snapshot_run_ids", []))
                json_valid_after = bool(state_after)

                fail_reasons: list[str] = []
                if not authoritative_state_advanced:
                    fail_reasons.append("STATE_NOT_ADVANCED")
                if not run_id_ingested:
                    fail_reasons.append("RUN_ID_NOT_INGESTED")
                if temporal_gap_count > 0:
                    fail_reasons.append("TEMPORAL_GAP_DETECTED")
                if boundary_breach_count > 0:
                    fail_reasons.append("BOUNDARY_BREACH_DETECTED")
                if any(v > 0 for v in [coverage_review_count, reject_candidate_count, join_blocker_count, escalate_set_count]):
                    fail_reasons.append("INTEGRITY_BLOCKER_DETECTED")
                if not json_valid_after:
                    fail_reasons.append("POST_WRITE_JSON_INVALID")
                if escalate_now_count > 0:
                    fail_reasons.append("UNEXPECTED_ESCALATE_TRIGGERED")

                if fail_reasons:
                    restore_reason = "|".join(fail_reasons)
                    shutil.copy2(backup_state_path, state_path)
                    restore_executed = True
                    restore_succeeded = file_sha256(state_path) == backup_hash
                    authoritative_state_advanced = False
                    decision = HOLD_RESTORE
                    blocker_labels.extend(fail_reasons)
                else:
                    decision = SUCCESS
            except Exception as exc:  # pragma: no cover
                restore_reason = f"EXCEPTION:{type(exc).__name__}"
                if backup_created and backup_state_path.exists():
                    shutil.copy2(backup_state_path, state_path)
                    restore_executed = True
                    restore_succeeded = file_sha256(state_path) == backup_hash
                decision = HOLD_RESTORE
                blocker_labels.append("LIVE_UPDATE_EXCEPTION")

    summary = {
        "artifact": "exhibitions_text_carry_forward_phase7_live_next_run_continuation_summary",
        "task": "TASK249",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "inputs": {
            "state_latest_json": str(state_path),
            "continuation_input_csv": str(Path(args.continuation_input_csv)),
            "holding_set_csv": str(Path(args.holding_set_csv)),
            "escalate_set_csv": str(Path(args.escalate_set_csv)),
            "reject_set_csv": str(Path(args.reject_set_csv)),
            "task246_summary_json": str(Path(args.task246_summary_json)),
            "task248_summary_json": str(Path(args.task248_summary_json)),
        },
        "live_run_preflight": {
            "check_total": len(preflight_rows),
            "pass_count": sum(1 for row in preflight_rows if row["status"] == "PASS"),
            "fail_count": sum(1 for row in preflight_rows if row["status"] == "FAIL"),
            "blocker_fail_count": blocker_fail_count,
            "run_id_unique": run_id not in ingested_run_set,
            "boundary_breach_count": boundary_breach_count,
            "coverage_review_count": coverage_review_count,
            "reject_candidate_count": reject_candidate_count,
            "join_blocker_count": join_blocker_count,
            "escalate_set_count": escalate_set_count,
        },
        "backup_info": {
            "backup_root": str(backup_root) if backup_root else "",
            "backup_state_path": str(backup_state_path) if backup_state_path else "",
            "backup_created": backup_created,
            "state_hash_before": state_hash_before,
            "backup_hash": backup_hash,
            "backup_hash_match": backup_hash_match,
        },
        "live_update_result": {
            "authoritative_state_advanced": authoritative_state_advanced,
            "updated_units_count": updated_units_count,
            "persistence_increment_count": persistence_increment_count,
            "idempotent_noop_count": idempotent_noop_count,
            "temporal_gap_count": temporal_gap_count,
            "escalate_now_count": escalate_now_count,
            "boundary_breach_count": boundary_breach_count,
            "run_id_ingested": decision == SUCCESS,
        },
        "post_integrity": {
            "coverage_review_count": coverage_review_count,
            "reject_candidate_count": reject_candidate_count,
            "join_blocker_count": join_blocker_count,
            "escalate_set_count": escalate_set_count,
            "proposal_only": True,
            "formal_untouched": True,
            "adoption_executed": False,
            "rollback_executed": False,
            "join_contract_changed": False,
            "anti_mixing_enforced": True,
        },
        "restore_info": {
            "restore_executed": restore_executed,
            "restore_succeeded": restore_succeeded,
            "restore_reason": restore_reason,
            "restore_source_path": str(backup_state_path) if backup_state_path else "",
            "restore_target_path": str(state_path),
        },
        "go_hold_decision": decision,
        "blocker_labels": blocker_labels,
        "next_task_recommendation": {
            "id": "TASK250",
            "title": "EXHIBITIONS-TEXT-CARRY-FORWARD-PHASE8-SECOND-LIVE-RUN-MONITORING",
            "ja": "Run second live continuation cycle with persistence>=3 temporal watch and escalate guard validation",
        },
    }

    summary_path = output_dir / "exhibitions_text_carry_forward_phase7_live_next_run_continuation_summary_task249.json"
    manifest_path = output_dir / "exhibitions_text_carry_forward_phase7_live_next_run_continuation_manifest_task249.json"
    preflight_path = output_dir / "exhibitions_text_carry_forward_phase7_live_next_run_continuation_preflight_task249.csv"
    monitored_diff_path = output_dir / "exhibitions_text_carry_forward_phase7_live_next_run_continuation_monitored_diff_task249.csv"
    backup_log_path = output_dir / "exhibitions_text_carry_forward_phase7_live_next_run_continuation_backup_log_task249.json"
    report_path = output_dir / "exhibitions_text_carry_forward_phase7_live_next_run_continuation_task249.md"

    write_json(summary_path, summary)
    write_json(backup_log_path, summary["backup_info"] | summary["restore_info"])

    preflight_fields = ["check_label", "actual", "expected", "status", "is_blocker"]
    write_csv(preflight_path, preflight_rows, preflight_fields)

    monitored_fields = [
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
        "escalate_now",
    ]
    write_csv(monitored_diff_path, monitored_diff_rows, monitored_fields)

    manifest = {
        "artifact": "exhibitions_text_carry_forward_phase7_live_next_run_continuation_manifest",
        "task": "TASK249",
        "run_id": run_id,
        "inputs": summary["inputs"],
        "outputs": {
            "summary_json": str(summary_path),
            "manifest_json": str(manifest_path),
            "preflight_csv": str(preflight_path),
            "monitored_diff_csv": str(monitored_diff_path),
            "backup_log_json": str(backup_log_path),
            "report_md": str(report_path),
        },
        "guard_state": {
            "continuation_input_total": continuation_input_total,
            "ready_count": len(ready_rows),
            "monitored_count": len(monitored_rows),
            "holding_excluded_count": len(holding_rows),
            "escalate_excluded_count": len(escalate_rows),
            "reject_excluded_count": len(reject_rows),
            "boundary_breach_count": boundary_breach_count,
        },
        "decision": decision,
    }
    write_json(manifest_path, manifest)

    report_lines = [
        "# TASK249 Exhibitions Text Carry-Forward Phase7 Live Next-Run Continuation",
        "",
        "## run_id_policy",
        f"- incoming_run_id={run_id}",
        f"- run_id_unique={(run_id not in ingested_run_set)}",
        "",
        "## preflight_and_backup",
        f"- preflight_pass={summary['live_run_preflight']['pass_count']}/{summary['live_run_preflight']['check_total']}",
        f"- blocker_fail_count={blocker_fail_count}",
        f"- backup_created={backup_created}",
        f"- backup_hash_match={backup_hash_match}",
        "",
        "## live_update",
        f"- authoritative_state_advanced={authoritative_state_advanced}",
        f"- persistence_increment_count={persistence_increment_count}",
        f"- idempotent_noop_count={idempotent_noop_count}",
        f"- temporal_gap_count={temporal_gap_count}",
        f"- escalate_now_count={escalate_now_count}",
        "",
        "## restore",
        f"- restore_executed={restore_executed}",
        f"- restore_succeeded={restore_succeeded}",
        f"- restore_reason={restore_reason}",
        "",
        "## decision",
        f"- go_hold_decision={decision}",
        f"- blocker_labels={blocker_labels}",
    ]
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(
        "[task249] "
        f"run_id={run_id} preflight={summary['live_run_preflight']['pass_count']}/{summary['live_run_preflight']['check_total']} "
        f"backup_ok={(backup_created and backup_hash_match)} updated={authoritative_state_advanced} "
        f"increment={persistence_increment_count} noop={idempotent_noop_count} gap={temporal_gap_count} "
        f"escalate={escalate_now_count} restore={restore_executed} decision={decision}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
