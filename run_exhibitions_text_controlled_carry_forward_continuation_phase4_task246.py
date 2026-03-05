from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY = "READY_FOR_CARRY_FORWARD_PHASE_5"
HOLD_STATE = "HOLD_FOR_TEMPORAL_STATE_FIX"
HOLD_POLICY = "HOLD_FOR_MONITORED_POLICY_REVIEW"


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


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TASK246 Exhibitions Text controlled carry-forward continuation phase 4")
    parser.add_argument(
        "--task245-summary",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_carry_forward_continuation_phase3_summary_task245.json",
    )
    parser.add_argument(
        "--task245-monitored-snapshot-csv",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_carry_forward_continuation_phase3_monitored_snapshot_task245.csv",
    )
    parser.add_argument(
        "--state-latest-json",
        default="data/phase1_seed10/logs/exhibitions_text_monitored_state_latest.json",
    )
    parser.add_argument("--output-dir", default="data/phase1_seed10/logs")
    parser.add_argument("--run-id", default="")
    return parser.parse_args()


def _to_bool(value: Any) -> bool:
    return str(value).strip().lower() == "true"


def _monitor_unit_from_snapshot(row: dict[str, str], baseline_run_id: str) -> dict[str, Any]:
    return {
        "monitor_key": str(row.get("monitor_key") or "").strip(),
        "scope_key": str(row.get("scope_key") or "").strip(),
        "fair_slug": str(row.get("fair_slug") or "").strip(),
        "gallery_name_en": str(row.get("gallery_name_en") or "").strip(),
        "source_url": str(row.get("source_url") or "").strip(),
        "last_seen_run_id": baseline_run_id,
        "persistence_count": int(row.get("persistence_count") or 0),
        "last_reason": str(row.get("warning_primary") or "").strip(),
        "last_warning_causes": str(row.get("warning_causes") or "").strip(),
        "last_route_quality_label": str(row.get("route_quality_label") or "").strip(),
        "last_year_quality_label": str(row.get("year_quality_label") or "").strip(),
        "last_flags": {
            "ratio_evaluable": _to_bool(row.get("ratio_evaluable")),
            "ratio_threshold_exceeded": _to_bool(row.get("ratio_threshold_exceeded")),
            "ratio_two_consecutive": _to_bool(row.get("ratio_two_consecutive")),
            "route_degradation_flag": _to_bool(row.get("route_degradation_flag")),
            "escalate_now": _to_bool(row.get("escalate_now")),
        },
    }


def main() -> int:
    args = parse_args()
    run_id = args.run_id.strip() or datetime.now(timezone.utc).strftime("task246_%Y%m%dT%H%M%SZ")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    summary245 = read_json(Path(args.task245_summary), default={})
    snapshot_rows = read_csv(Path(args.task245_monitored_snapshot_csv))
    state_path = Path(args.state_latest_json)
    state = read_json(state_path, default={})

    baseline_run_id = str(summary245.get("run_id") or "").strip()
    baseline_scope_hash = str(
        summary245.get("continuation_phase3_input", {}).get("scope_hash") or ""
    ).strip()
    integrity = summary245.get("integrity_checks", {})

    ingested_runs = list(state.get("ingested_snapshot_run_ids") or [])
    ingested_run_set = set(str(x) for x in ingested_runs)

    monitoring_units: dict[str, Any] = dict(state.get("monitoring_units") or {})
    ratio_scope_state: dict[str, Any] = dict(state.get("ratio_scope_state") or {})
    ingestion_mode = "insert"
    idempotent_noop = False

    if not baseline_run_id:
        ingestion_mode = "invalid_missing_baseline_run_id"
    elif baseline_run_id in ingested_run_set:
        ingestion_mode = "noop_already_ingested"
        idempotent_noop = True
    else:
        # Ingest baseline monitored snapshot as authoritative monitoring state baseline.
        for row in snapshot_rows:
            monitor_key = str(row.get("monitor_key") or "").strip()
            scope_key = str(row.get("scope_key") or "").strip()
            if not monitor_key:
                continue
            monitoring_units[monitor_key] = _monitor_unit_from_snapshot(row, baseline_run_id)
            ratio_scope_state[scope_key] = {
                "scope_key": scope_key,
                "fair_slug": str(row.get("fair_slug") or "").strip(),
                "gallery_name_en": str(row.get("gallery_name_en") or "").strip(),
                "scope_total_count": int(row.get("scope_total_count") or 0),
                "scope_text_only_count": int(row.get("scope_text_only_count") or 0),
                "text_only_ratio": float(row.get("text_only_ratio") or 0.0),
                "last_seen_run_id": baseline_run_id,
            }
        ingested_runs.append(baseline_run_id)
        ingested_run_set.add(baseline_run_id)

    snapshot_keys = {str(row.get("monitor_key") or "").strip() for row in snapshot_rows if str(row.get("monitor_key") or "").strip()}
    state_keys = set(monitoring_units.keys())
    temporal_gap_count = len(snapshot_keys - state_keys)

    coverage_review_count = int(integrity.get("coverage_review_count", 0))
    reject_count = int(integrity.get("reject_candidate_count", 0))
    join_blocker_count = int(integrity.get("join_blocker_count", 0))
    escalate_set_count = int(integrity.get("escalate_set_count", 0))
    boundary_breach_count = int(summary245.get("aggregates", {}).get("boundary_breach_count", 0))

    blocker_labels: list[str] = []
    if coverage_review_count > 0:
        blocker_labels.append("COVERAGE_REVIEW_PRESENT")
    if reject_count > 0:
        blocker_labels.append("REJECT_PRESENT")
    if join_blocker_count > 0:
        blocker_labels.append("JOIN_BLOCKER_PRESENT")
    if escalate_set_count > 0:
        blocker_labels.append("ESCALATE_SET_PRESENT")
    if boundary_breach_count > 0:
        blocker_labels.append("BOUNDARY_BREACH_PRESENT")
    if not baseline_run_id:
        blocker_labels.append("MISSING_BASELINE_RUN_ID")
    if temporal_gap_count > 0:
        blocker_labels.append("TEMPORAL_GAP_REMAINS")

    policy_rules = {
        "next_run_identity_unit": "run_id",
        "persistence_increment_rule": "increment by +1 only when same monitor_key is present in a new run_id consecutive cycle",
        "same_run_id_reingest_rule": "no-op; do not increment persistence_count and do not overwrite counters",
        "stable_text_only_ratio_unit": "fair_slug + gallery_name_en",
        "route_degradation_compare_unit": "same monitor_key",
        "state_usage_scope": "monitoring only; not for record identity, join key, or display fields",
    }

    if any(label in blocker_labels for label in ["COVERAGE_REVIEW_PRESENT", "REJECT_PRESENT", "JOIN_BLOCKER_PRESENT", "ESCALATE_SET_PRESENT", "BOUNDARY_BREACH_PRESENT", "MISSING_BASELINE_RUN_ID", "TEMPORAL_GAP_REMAINS"]):
        decision = HOLD_STATE
    elif not policy_rules:
        decision = HOLD_POLICY
    else:
        decision = READY

    # Persist/refresh latest state store.
    next_state = {
        "artifact": "exhibitions_text_monitored_state_latest",
        "task": "TASK246",
        "state_version": 1,
        "updated_at": utc_now_iso(),
        "baseline_run_id": baseline_run_id,
        "baseline_scope_hash": baseline_scope_hash,
        "ingested_snapshot_run_ids": ingested_runs,
        "monitoring_units": monitoring_units,
        "ratio_scope_state": ratio_scope_state,
        "state_rules": policy_rules,
        "last_ingestion": {
            "task_run_id": run_id,
            "ingestion_mode": ingestion_mode,
            "idempotent_noop": idempotent_noop,
            "snapshot_rows": len(snapshot_rows),
            "monitoring_units_count": len(monitoring_units),
            "ratio_scope_units_count": len(ratio_scope_state),
            "temporal_gap_count": temporal_gap_count,
        },
    }
    write_json(state_path, next_state)

    snapshot_summary_rows = []
    for row in snapshot_rows:
        snapshot_summary_rows.append(
            {
                "monitor_key": str(row.get("monitor_key") or "").strip(),
                "fair_slug": str(row.get("fair_slug") or "").strip(),
                "gallery_name_en": str(row.get("gallery_name_en") or "").strip(),
                "warning_primary": str(row.get("warning_primary") or "").strip(),
                "persistence_count": int(row.get("persistence_count") or 0),
                "ratio_evaluable": _to_bool(row.get("ratio_evaluable")),
                "text_only_ratio": float(row.get("text_only_ratio") or 0.0),
                "route_degradation_flag": _to_bool(row.get("route_degradation_flag")),
                "escalate_now": _to_bool(row.get("escalate_now")),
            }
        )

    monitored_reason_counts = Counter(
        str(row.get("warning_primary") or "").strip() for row in snapshot_rows if str(row.get("warning_primary") or "").strip()
    )

    by_fair = Counter(str(row.get("fair_slug") or "").strip() for row in snapshot_rows)
    by_gallery = Counter(
        f"{str(row.get('gallery_name_en') or '').strip()}|{str(row.get('fair_slug') or '').strip()}"
        for row in snapshot_rows
    )

    summary = {
        "artifact": "exhibitions_text_controlled_carry_forward_continuation_phase4_summary",
        "task": "TASK246",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "inputs": {
            "task245_summary": str(Path(args.task245_summary)),
            "task245_monitored_snapshot_csv": str(Path(args.task245_monitored_snapshot_csv)),
            "state_latest_json": str(state_path),
        },
        "state_store": {
            "path": str(state_path),
            "baseline_run_id": baseline_run_id,
            "baseline_scope_hash": baseline_scope_hash,
            "ingestion_mode": ingestion_mode,
            "idempotent_noop": idempotent_noop,
            "ingested_snapshot_run_ids_count": len(ingested_runs),
            "monitoring_units_count": len(monitoring_units),
            "ratio_scope_units_count": len(ratio_scope_state),
            "temporal_gap_count": temporal_gap_count,
        },
        "continuation_phase4_counts": {
            "continuation_input_total": int(summary245.get("continuation_phase3_input", {}).get("continuation_input_total", 0)),
            "ready_count": int(summary245.get("continuation_phase3_input", {}).get("ready_count", 0)),
            "monitored_count": int(summary245.get("continuation_phase3_input", {}).get("monitored_count", 0)),
            "holding_excluded_count": int(summary245.get("continuation_phase3_input", {}).get("holding_excluded_count", 0)),
            "monitored_reason_counts": dict(monitored_reason_counts),
            "by_fair_monitored_counts": dict(by_fair),
            "by_gallery_monitored_counts": dict(by_gallery),
        },
        "temporal_rules": policy_rules,
        "integrity_checks": {
            "coverage_review_count": coverage_review_count,
            "reject_candidate_count": reject_count,
            "join_blocker_count": join_blocker_count,
            "escalate_set_count": escalate_set_count,
            "boundary_breach_count": boundary_breach_count,
            "proposal_only": True,
            "formal_untouched": True,
            "adoption_executed": False,
            "rollback_executed": False,
            "join_contract_changed": False,
            "anti_mixing_enforced": True,
        },
        "go_hold_decision": decision,
        "blocker_labels": blocker_labels,
        "next_task_recommendation": {
            "id": "TASK247",
            "title": "EXHIBITIONS-TEXT-CONTROLLED-CARRY-FORWARD-CONTINUATION-PHASE-5",
            "ja": "Run next controlled continuation cycle using TASK246 state latest as temporal baseline",
        },
    }

    summary_path = output_dir / "exhibitions_text_controlled_carry_forward_continuation_phase4_summary_task246.json"
    manifest_path = output_dir / "exhibitions_text_controlled_carry_forward_continuation_phase4_manifest_task246.json"
    report_path = output_dir / "exhibitions_text_controlled_carry_forward_continuation_phase4_task246.md"

    snapshot_table_path = output_dir / "exhibitions_text_controlled_carry_forward_continuation_phase4_monitored_table_task246.csv"
    snapshot_fields = [
        "monitor_key",
        "fair_slug",
        "gallery_name_en",
        "warning_primary",
        "persistence_count",
        "ratio_evaluable",
        "text_only_ratio",
        "route_degradation_flag",
        "escalate_now",
    ]
    write_csv(snapshot_table_path, snapshot_summary_rows, snapshot_fields)

    write_json(summary_path, summary)
    manifest = {
        "artifact": "exhibitions_text_controlled_carry_forward_continuation_phase4_manifest",
        "task": "TASK246",
        "run_id": run_id,
        "inputs": summary["inputs"],
        "outputs": {
            "state_latest_json": str(state_path),
            "summary_json": str(summary_path),
            "monitored_table_csv": str(snapshot_table_path),
            "report_md": str(report_path),
            "manifest_json": str(manifest_path),
        },
        "integrity_checks": summary["integrity_checks"],
    }
    write_json(manifest_path, manifest)

    report_lines = [
        "# TASK246 Exhibitions Text Controlled Carry-Forward Continuation Phase 4",
        "",
        "## state_store_baseline_fix",
        f"- baseline_run_id={baseline_run_id}",
        f"- baseline_scope_hash={baseline_scope_hash}",
        f"- ingestion_mode={ingestion_mode}",
        f"- idempotent_noop={idempotent_noop}",
        f"- temporal_gap_count={temporal_gap_count}",
        "",
        "## temporal_rules",
        f"- next_run_identity_unit={policy_rules['next_run_identity_unit']}",
        f"- persistence_increment_rule={policy_rules['persistence_increment_rule']}",
        f"- same_run_id_reingest_rule={policy_rules['same_run_id_reingest_rule']}",
        f"- stable_text_only_ratio_unit={policy_rules['stable_text_only_ratio_unit']}",
        f"- route_degradation_compare_unit={policy_rules['route_degradation_compare_unit']}",
        "",
        "## integrity",
        f"- coverage_review_count={coverage_review_count}",
        f"- reject_candidate_count={reject_count}",
        f"- join_blocker_count={join_blocker_count}",
        f"- escalate_set_count={escalate_set_count}",
        f"- boundary_breach_count={boundary_breach_count}",
        "",
        "## decision",
        f"- go_hold_decision={decision}",
        f"- blocker_labels={blocker_labels}",
    ]
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(
        "[task246] "
        f"baseline={baseline_run_id} mode={ingestion_mode} idempotent_noop={idempotent_noop} "
        f"snapshot_rows={len(snapshot_rows)} temporal_gap={temporal_gap_count} decision={decision}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
