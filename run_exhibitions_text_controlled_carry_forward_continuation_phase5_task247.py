from __future__ import annotations

import argparse
import csv
import hashlib
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY = "READY_FOR_CARRY_FORWARD_PHASE_6"
HOLD_STATE = "HOLD_FOR_STATE_UPDATE_FIX"
HOLD_TEMPORAL = "HOLD_FOR_TEMPORAL_RULE_RECHECK"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


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
    parser = argparse.ArgumentParser(description="TASK247 Exhibitions Text controlled carry-forward continuation phase 5")
    parser.add_argument(
        "--state-latest-json",
        default="data/phase1_seed10/logs/exhibitions_text_monitored_state_latest.json",
    )
    parser.add_argument(
        "--task246-summary-json",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_carry_forward_continuation_phase4_summary_task246.json",
    )
    parser.add_argument(
        "--trial-state-json",
        default="data/phase1_seed10/logs/exhibitions_text_monitored_state_trial_task247.json",
    )
    parser.add_argument("--output-dir", default="data/phase1_seed10/logs")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--trial-run-id", default="")
    return parser.parse_args()


def _to_bool(value: Any) -> bool:
    return str(value).strip().lower() == "true"


def _route_rank(label: str) -> int:
    value = str(label or "").strip().lower()
    if value == "detail_candidate":
        return 1
    if value == "soft_suspicious":
        return 2
    if value in {"hard_suspicious", "hard_reject"}:
        return 3
    return 0


def _build_trial_snapshot_from_state(state: dict[str, Any], trial_run_id: str) -> list[dict[str, Any]]:
    monitoring_units = dict(state.get("monitoring_units") or {})
    ratio_scope_state = dict(state.get("ratio_scope_state") or {})
    rows: list[dict[str, Any]] = []
    for monitor_key in sorted(monitoring_units.keys()):
        unit = dict(monitoring_units.get(monitor_key) or {})
        scope_key = str(unit.get("scope_key") or "").strip()
        ratio_unit = dict(ratio_scope_state.get(scope_key) or {})
        scope_total = int(ratio_unit.get("scope_total_count", 0) or 0)
        scope_text_only = int(ratio_unit.get("scope_text_only_count", 0) or 0)
        text_only_ratio = float(ratio_unit.get("text_only_ratio", 0.0) or 0.0)
        ratio_evaluable = scope_total >= 3
        ratio_threshold_exceeded = ratio_evaluable and text_only_ratio > 0.6
        rows.append(
            {
                "monitor_key": monitor_key,
                "scope_key": scope_key,
                "fair_slug": str(unit.get("fair_slug") or "").strip(),
                "gallery_name_en": str(unit.get("gallery_name_en") or "").strip(),
                "source_url": str(unit.get("source_url") or "").strip(),
                "warning_primary": str(unit.get("last_reason") or "").strip(),
                "warning_causes": str(unit.get("last_warning_causes") or "").strip(),
                "route_quality_label": str(unit.get("last_route_quality_label") or "").strip(),
                "year_quality_label": str(unit.get("last_year_quality_label") or "").strip(),
                "scope_total_count": scope_total,
                "scope_text_only_count": scope_text_only,
                "text_only_ratio": round(text_only_ratio, 6),
                "ratio_evaluable": str(ratio_evaluable).lower(),
                "ratio_threshold_exceeded": str(ratio_threshold_exceeded).lower(),
                "ratio_two_consecutive": "false",
                "route_degradation_flag": "false",
                "escalate_now": "false",
                "run_id": trial_run_id,
            }
        )
    return rows


def _ingest_snapshot(state: dict[str, Any], snapshot_rows: list[dict[str, Any]], run_id: str) -> dict[str, Any]:
    ingested = list(state.get("ingested_snapshot_run_ids") or [])
    ingested_set = {str(v) for v in ingested}
    monitoring_units = dict(state.get("monitoring_units") or {})
    ratio_scope_state = dict(state.get("ratio_scope_state") or {})

    snapshot_keys = {
        str(row.get("monitor_key") or "").strip() for row in snapshot_rows if str(row.get("monitor_key") or "").strip()
    }

    if run_id in ingested_set:
        temporal_gap = len([key for key in snapshot_keys if key not in monitoring_units])
        state["last_ingestion"] = {
            "ingestion_mode": "noop_same_run_id",
            "task_run_id": run_id,
            "snapshot_rows": len(snapshot_rows),
            "updated_units_count": 0,
            "persistence_increment_count": 0,
            "idempotent_noop_count": len(snapshot_rows),
            "temporal_gap_count": temporal_gap,
            "escalate_now_count": 0,
        }
        return {
            "updated_units_count": 0,
            "persistence_increment_count": 0,
            "idempotent_noop_count": len(snapshot_rows),
            "temporal_gap_count": temporal_gap,
            "escalate_now_count": 0,
            "ingestion_mode": "noop_same_run_id",
        }

    updated_units_count = 0
    persistence_increment_count = 0
    temporal_gap_count = 0
    escalate_now_count = 0
    route_degradation_count = 0

    for row in snapshot_rows:
        monitor_key = str(row.get("monitor_key") or "").strip()
        scope_key = str(row.get("scope_key") or "").strip()
        if not monitor_key:
            continue
        prev = dict(monitoring_units.get(monitor_key) or {})
        if not prev:
            temporal_gap_count += 1
        prev_persist = int(prev.get("persistence_count", 0) or 0)
        next_persist = prev_persist + 1
        if prev:
            persistence_increment_count += 1
        prev_route = str(prev.get("last_route_quality_label") or "").strip()
        curr_route = str(row.get("route_quality_label") or "").strip()
        route_degradation = _route_rank(curr_route) > _route_rank(prev_route) if prev_route else False
        if route_degradation:
            route_degradation_count += 1
        escalate_now = bool(route_degradation)
        if escalate_now:
            escalate_now_count += 1

        monitoring_units[monitor_key] = {
            "monitor_key": monitor_key,
            "scope_key": scope_key,
            "fair_slug": str(row.get("fair_slug") or "").strip(),
            "gallery_name_en": str(row.get("gallery_name_en") or "").strip(),
            "source_url": str(row.get("source_url") or "").strip(),
            "last_seen_run_id": run_id,
            "persistence_count": next_persist,
            "last_reason": str(row.get("warning_primary") or "").strip(),
            "last_warning_causes": str(row.get("warning_causes") or "").strip(),
            "last_route_quality_label": curr_route,
            "last_year_quality_label": str(row.get("year_quality_label") or "").strip(),
            "last_flags": {
                "ratio_evaluable": _to_bool(row.get("ratio_evaluable")),
                "ratio_threshold_exceeded": _to_bool(row.get("ratio_threshold_exceeded")),
                "ratio_two_consecutive": _to_bool(row.get("ratio_two_consecutive")),
                "route_degradation_flag": route_degradation,
                "escalate_now": escalate_now,
            },
        }
        ratio_scope_state[scope_key] = {
            "scope_key": scope_key,
            "fair_slug": str(row.get("fair_slug") or "").strip(),
            "gallery_name_en": str(row.get("gallery_name_en") or "").strip(),
            "scope_total_count": int(row.get("scope_total_count", 0) or 0),
            "scope_text_only_count": int(row.get("scope_text_only_count", 0) or 0),
            "text_only_ratio": float(row.get("text_only_ratio", 0.0) or 0.0),
            "last_seen_run_id": run_id,
        }
        updated_units_count += 1

    ingested.append(run_id)
    state["monitoring_units"] = monitoring_units
    state["ratio_scope_state"] = ratio_scope_state
    state["ingested_snapshot_run_ids"] = ingested
    state["last_ingestion"] = {
        "ingestion_mode": "ingested_new_run",
        "task_run_id": run_id,
        "snapshot_rows": len(snapshot_rows),
        "updated_units_count": updated_units_count,
        "persistence_increment_count": persistence_increment_count,
        "idempotent_noop_count": 0,
        "temporal_gap_count": temporal_gap_count,
        "escalate_now_count": escalate_now_count,
        "route_degradation_count": route_degradation_count,
    }

    return {
        "updated_units_count": updated_units_count,
        "persistence_increment_count": persistence_increment_count,
        "idempotent_noop_count": 0,
        "temporal_gap_count": temporal_gap_count,
        "escalate_now_count": escalate_now_count,
        "ingestion_mode": "ingested_new_run",
    }


def main() -> int:
    args = parse_args()
    run_id = args.run_id.strip() or datetime.now(timezone.utc).strftime("task247_%Y%m%dT%H%M%SZ")
    trial_run_id = args.trial_run_id.strip() or datetime.now(timezone.utc).strftime("task247_trial_next_%Y%m%dT%H%M%SZ")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    state_latest_path = Path(args.state_latest_json)
    task246_summary = read_json(Path(args.task246_summary_json), default={})
    state_latest_raw = state_latest_path.read_text(encoding="utf-8") if state_latest_path.exists() else "{}"
    state_latest_hash_before = hashlib.sha256(state_latest_raw.encode("utf-8")).hexdigest()
    state_latest = read_json(state_latest_path, default={})
    trial_state = deepcopy(state_latest)

    baseline_run_id = str(trial_state.get("baseline_run_id") or "").strip()
    baseline_scope_hash = str(trial_state.get("baseline_scope_hash") or "").strip()
    monitored_units_total = len(dict(trial_state.get("monitoring_units") or {}))

    trial_snapshot_rows = _build_trial_snapshot_from_state(trial_state, trial_run_id)

    # Case A/C/D: new run ingestion with same monitor keys.
    first_ingest = _ingest_snapshot(trial_state, trial_snapshot_rows, trial_run_id)
    # Case B: same run re-ingestion must be idempotent no-op.
    second_ingest = _ingest_snapshot(trial_state, trial_snapshot_rows, trial_run_id)

    trial_state["artifact"] = "exhibitions_text_monitored_state_trial_task247"
    trial_state["task"] = "TASK247"
    trial_state["trial_mode"] = True
    trial_state["baseline_state_source"] = str(state_latest_path)
    trial_state["updated_at"] = utc_now_iso()
    trial_state["phase5_trial_run_id"] = run_id

    trial_state_path = Path(args.trial_state_json)
    write_json(trial_state_path, trial_state)

    state_latest_hash_after = hashlib.sha256(state_latest_path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
    authoritative_state_unchanged = state_latest_hash_before == state_latest_hash_after

    ingested_run_ids = list(trial_state.get("ingested_snapshot_run_ids") or [])
    idempotent_run_id_not_duplicated = ingested_run_ids.count(trial_run_id) == 1

    ratio_scope_state = dict(trial_state.get("ratio_scope_state") or {})
    ratio_continuity_ok = len(ratio_scope_state) >= monitored_units_total

    case_results = {
        "case_a_new_run_persistence_increment": first_ingest.get("persistence_increment_count", 0) == monitored_units_total,
        "case_b_same_run_reingest_noop": (
            second_ingest.get("idempotent_noop_count", 0) == monitored_units_total and idempotent_run_id_not_duplicated
        ),
        "case_c_route_flags_maintained_no_escalate": first_ingest.get("escalate_now_count", 0) == 0,
        "case_d_ratio_basis_continues_readable": ratio_continuity_ok,
    }

    temporal_gap_count = max(
        int(first_ingest.get("temporal_gap_count", 0)),
        int(second_ingest.get("temporal_gap_count", 0)),
    )
    escalate_now_count = int(first_ingest.get("escalate_now_count", 0))
    boundary_breach_count = int(task246_summary.get("integrity_checks", {}).get("boundary_breach_count", 0))
    coverage_review_count = int(task246_summary.get("integrity_checks", {}).get("coverage_review_count", 0))
    reject_candidate_count = int(task246_summary.get("integrity_checks", {}).get("reject_candidate_count", 0))
    join_blocker_count = int(task246_summary.get("integrity_checks", {}).get("join_blocker_count", 0))

    blocker_labels: list[str] = []
    if not authoritative_state_unchanged:
        blocker_labels.append("AUTHORITATIVE_STATE_MUTATED")
    if temporal_gap_count > 0:
        blocker_labels.append("TEMPORAL_GAP_DETECTED")
    if not case_results["case_a_new_run_persistence_increment"]:
        blocker_labels.append("PERSISTENCE_INCREMENT_BROKEN")
    if not case_results["case_b_same_run_reingest_noop"]:
        blocker_labels.append("SAME_RUN_IDEMPOTENT_BROKEN")
    if not case_results["case_d_ratio_basis_continues_readable"]:
        blocker_labels.append("RATIO_BASIS_BROKEN")
    if coverage_review_count > 0:
        blocker_labels.append("COVERAGE_REVIEW_PRESENT")
    if reject_candidate_count > 0:
        blocker_labels.append("REJECT_PRESENT")
    if join_blocker_count > 0:
        blocker_labels.append("JOIN_BLOCKER_PRESENT")
    if boundary_breach_count > 0:
        blocker_labels.append("BOUNDARY_BREACH_PRESENT")

    if any(
        label in blocker_labels
        for label in [
            "TEMPORAL_GAP_DETECTED",
            "RATIO_BASIS_BROKEN",
        ]
    ):
        decision = HOLD_TEMPORAL
    elif blocker_labels:
        decision = HOLD_STATE
    else:
        decision = READY

    summary = {
        "artifact": "exhibitions_text_controlled_carry_forward_continuation_phase5_summary",
        "task": "TASK247",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "inputs": {
            "task246_summary_json": str(Path(args.task246_summary_json)),
            "authoritative_state_latest_json": str(state_latest_path),
            "trial_state_json": str(trial_state_path),
        },
        "trial_state_validation": {
            "baseline_run_id": baseline_run_id,
            "trial_run_id": trial_run_id,
            "monitored_units_total": monitored_units_total,
            "updated_units_count": int(first_ingest.get("updated_units_count", 0)),
            "idempotent_noop_count": int(second_ingest.get("idempotent_noop_count", 0)),
            "persistence_increment_count": int(first_ingest.get("persistence_increment_count", 0)),
            "temporal_gap_count": temporal_gap_count,
            "escalate_now_count": escalate_now_count,
            "boundary_breach_count": boundary_breach_count,
            "coverage_review_count": coverage_review_count,
            "reject_candidate_count": reject_candidate_count,
            "join_blocker_count": join_blocker_count,
            "authoritative_state_unchanged": authoritative_state_unchanged,
            "idempotent_run_id_not_duplicated": idempotent_run_id_not_duplicated,
            "trial_state_only_updated": True,
        },
        "case_results": case_results,
        "integrity_checks": {
            "proposal_only": True,
            "formal_untouched": True,
            "adoption_executed": False,
            "rollback_executed": False,
            "join_contract_changed": False,
            "anti_mixing_enforced": True,
            "holding_mixed": False,
            "escalate_mixed": False,
            "reject_mixed": False,
        },
        "go_hold_decision": decision,
        "blocker_labels": blocker_labels,
        "next_task_recommendation": {
            "id": "TASK248",
            "title": "EXHIBITIONS-TEXT-CARRY-FORWARD-PHASE6-LIVE-NEXT-RUN-PREP",
            "ja": "Use authoritative state latest in first true next-run continuation with state update guards enabled",
        },
    }

    snapshot_csv_path = output_dir / "exhibitions_text_controlled_carry_forward_continuation_phase5_trial_snapshot_task247.csv"
    snapshot_fields = [
        "monitor_key",
        "scope_key",
        "fair_slug",
        "gallery_name_en",
        "source_url",
        "warning_primary",
        "warning_causes",
        "route_quality_label",
        "year_quality_label",
        "scope_total_count",
        "scope_text_only_count",
        "text_only_ratio",
        "ratio_evaluable",
        "ratio_threshold_exceeded",
        "ratio_two_consecutive",
        "route_degradation_flag",
        "escalate_now",
        "run_id",
    ]
    write_csv(snapshot_csv_path, trial_snapshot_rows, snapshot_fields)

    monitored_table_path = output_dir / "exhibitions_text_controlled_carry_forward_continuation_phase5_monitored_table_task247.csv"
    monitored_table_rows = []
    for key in sorted(dict(trial_state.get("monitoring_units") or {}).keys()):
        unit = dict(trial_state.get("monitoring_units", {}).get(key) or {})
        flags = dict(unit.get("last_flags") or {})
        monitored_table_rows.append(
            {
                "monitor_key": key,
                "fair_slug": str(unit.get("fair_slug") or "").strip(),
                "gallery_name_en": str(unit.get("gallery_name_en") or "").strip(),
                "last_seen_run_id": str(unit.get("last_seen_run_id") or "").strip(),
                "persistence_count": int(unit.get("persistence_count", 0) or 0),
                "last_reason": str(unit.get("last_reason") or "").strip(),
                "route_degradation_flag": bool(flags.get("route_degradation_flag", False)),
                "escalate_now": bool(flags.get("escalate_now", False)),
            }
        )
    monitored_fields = [
        "monitor_key",
        "fair_slug",
        "gallery_name_en",
        "last_seen_run_id",
        "persistence_count",
        "last_reason",
        "route_degradation_flag",
        "escalate_now",
    ]
    write_csv(monitored_table_path, monitored_table_rows, monitored_fields)

    summary_path = output_dir / "exhibitions_text_controlled_carry_forward_continuation_phase5_summary_task247.json"
    manifest_path = output_dir / "exhibitions_text_controlled_carry_forward_continuation_phase5_manifest_task247.json"
    report_path = output_dir / "exhibitions_text_controlled_carry_forward_continuation_phase5_task247.md"
    write_json(summary_path, summary)

    manifest = {
        "artifact": "exhibitions_text_controlled_carry_forward_continuation_phase5_manifest",
        "task": "TASK247",
        "run_id": run_id,
        "inputs": summary["inputs"],
        "outputs": {
            "trial_state_json": str(trial_state_path),
            "trial_snapshot_csv": str(snapshot_csv_path),
            "monitored_table_csv": str(monitored_table_path),
            "summary_json": str(summary_path),
            "manifest_json": str(manifest_path),
            "report_md": str(report_path),
        },
        "integrity_checks": {
            **summary["integrity_checks"],
            "authoritative_state_unchanged": authoritative_state_unchanged,
        },
    }
    write_json(manifest_path, manifest)

    report_lines = [
        "# TASK247 Exhibitions Text Controlled Carry-Forward Continuation Phase 5",
        "",
        "## trial_state_setup",
        f"- authoritative_state={state_latest_path}",
        f"- trial_state={trial_state_path}",
        f"- baseline_run_id={baseline_run_id}",
        f"- trial_run_id={trial_run_id}",
        f"- authoritative_state_unchanged={authoritative_state_unchanged}",
        "",
        "## controlled_cases",
        f"- case_a_new_run_persistence_increment={case_results['case_a_new_run_persistence_increment']}",
        f"- case_b_same_run_reingest_noop={case_results['case_b_same_run_reingest_noop']}",
        f"- case_c_route_flags_maintained_no_escalate={case_results['case_c_route_flags_maintained_no_escalate']}",
        f"- case_d_ratio_basis_continues_readable={case_results['case_d_ratio_basis_continues_readable']}",
        "",
        "## phase5_counts",
        f"- monitored_units_total={monitored_units_total}",
        f"- updated_units_count={first_ingest.get('updated_units_count', 0)}",
        f"- persistence_increment_count={first_ingest.get('persistence_increment_count', 0)}",
        f"- idempotent_noop_count={second_ingest.get('idempotent_noop_count', 0)}",
        f"- temporal_gap_count={temporal_gap_count}",
        f"- escalate_now_count={escalate_now_count}",
        "",
        "## decision",
        f"- go_hold_decision={decision}",
        f"- blocker_labels={blocker_labels}",
    ]
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(
        "[task247] "
        f"baseline={baseline_run_id} trial_run={trial_run_id} monitored={monitored_units_total} "
        f"updated={first_ingest.get('updated_units_count', 0)} noop={second_ingest.get('idempotent_noop_count', 0)} "
        f"temporal_gap={temporal_gap_count} escalate={escalate_now_count} decision={decision}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
