from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY = "READY_FOR_STEADY_STATE_OPERATION_ADOPTION_PROPOSAL"
HOLD_POLICY = "HOLD_FOR_OPERATION_POLICY_DECISION"
HOLD_REINTEGRATION = "HOLD_FOR_REINTEGRATION_RULE_TUNING"


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


def row_signature(row: dict[str, str]) -> str:
    return "||".join(
        [
            str(row.get("fair_slug") or "").strip(),
            str(row.get("gallery_name_en") or "").strip(),
            str(row.get("target_year") or "").strip(),
            str(row.get("source_url") or "").strip(),
        ]
    )


def by_fair(rows: list[dict[str, str]]) -> dict[str, int]:
    counter = Counter()
    for row in rows:
        counter[str(row.get("fair_slug") or "").strip()] += 1
    return dict(counter)


def by_gallery(rows: list[dict[str, str]]) -> dict[str, int]:
    counter = Counter()
    for row in rows:
        key = f"{str(row.get('gallery_name_en') or '').strip()}|{str(row.get('fair_slug') or '').strip()}"
        counter[key] += 1
    return dict(counter)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="TASK258 Exhibitions Text steady-state operation proposal for READY and ESCALATE lanes"
    )
    parser.add_argument(
        "--task257-ready-input-csv",
        default="data/phase1_seed10/logs/exhibitions_text_ready_restart_with_escalate_monitoring_phase5_continuation_ready_input_task257.csv",
    )
    parser.add_argument(
        "--task257-escalate-input-csv",
        default="data/phase1_seed10/logs/exhibitions_text_ready_restart_with_escalate_monitoring_phase5_continuation_escalate_input_task257.csv",
    )
    parser.add_argument(
        "--task257-ready-summary-json",
        default="data/phase1_seed10/logs/exhibitions_text_ready_restart_with_escalate_monitoring_phase5_continuation_ready_summary_task257.json",
    )
    parser.add_argument(
        "--task257-escalate-summary-json",
        default="data/phase1_seed10/logs/exhibitions_text_ready_restart_with_escalate_monitoring_phase5_continuation_escalate_summary_task257.json",
    )
    parser.add_argument(
        "--task257-monitored-diff-csv",
        default="data/phase1_seed10/logs/exhibitions_text_ready_restart_with_escalate_monitoring_phase5_continuation_monitored_diff_task257.csv",
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
    parser.add_argument("--run-id", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_id = args.run_id.strip() or datetime.now(timezone.utc).strftime("task258_%Y%m%dT%H%M%SZ")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ready_rows = read_csv(Path(args.task257_ready_input_csv))
    escalate_rows = read_csv(Path(args.task257_escalate_input_csv))
    holding_rows = read_csv(Path(args.holding_set_csv))
    reject_rows = read_csv(Path(args.reject_set_csv))
    monitored_diff_rows = read_csv(Path(args.task257_monitored_diff_csv))

    ready_summary = read_json(Path(args.task257_ready_summary_json), default={})
    escalate_summary = read_json(Path(args.task257_escalate_summary_json), default={})

    ready_signatures = {row_signature(r) for r in ready_rows}
    escalate_signatures = {row_signature(r) for r in escalate_rows}
    holding_signatures = {row_signature(r) for r in holding_rows}
    reject_signatures = {row_signature(r) for r in reject_rows}

    overlaps = {
        "ready_vs_escalate": len(ready_signatures & escalate_signatures),
        "ready_vs_holding": len(ready_signatures & holding_signatures),
        "ready_vs_reject": len(ready_signatures & reject_signatures),
        "escalate_vs_holding": len(escalate_signatures & holding_signatures),
        "escalate_vs_reject": len(escalate_signatures & reject_signatures),
    }
    boundary_breach_count = sum(overlaps.values())

    common_ready = dict(ready_summary.get("common_checks") or {})
    common_escalate = dict(escalate_summary.get("common_checks") or {})
    integrity_clear = all(
        [
            int(common_ready.get("coverage_review_count", 0)) == 0,
            int(common_ready.get("reject_candidate_count", 0)) == 0,
            int(common_ready.get("join_blocker_count", 0)) == 0,
            int(common_ready.get("escalate_blocker_count", 0)) == 0,
            int(common_escalate.get("coverage_review_count", 0)) == 0,
            int(common_escalate.get("reject_candidate_count", 0)) == 0,
            int(common_escalate.get("join_blocker_count", 0)) == 0,
            int(common_escalate.get("escalate_blocker_count", 0)) == 0,
        ]
    )

    lane_counts = {
        "READY_LANE": len(ready_rows),
        "ESCALATE_SEPARATE_LANE": len(escalate_rows),
        "HOLDING_LANE": len(holding_rows),
        "REJECT_LANE": len(reject_rows),
    }
    lane_by_fair = {
        "READY_LANE": by_fair(ready_rows),
        "ESCALATE_SEPARATE_LANE": by_fair(escalate_rows),
        "HOLDING_LANE": by_fair(holding_rows),
        "REJECT_LANE": by_fair(reject_rows),
    }
    lane_by_gallery = {
        "READY_LANE": by_gallery(ready_rows),
        "ESCALATE_SEPARATE_LANE": by_gallery(escalate_rows),
        "HOLDING_LANE": by_gallery(holding_rows),
        "REJECT_LANE": by_gallery(reject_rows),
    }

    warning_counter = Counter()
    for row in monitored_diff_rows:
        warning = str(row.get("warning_after") or row.get("warning_before") or "").strip()
        if warning:
            warning_counter[warning] += 1
    route_deg_count = sum(str(r.get("route_degradation_flag") or "").strip().lower() == "true" for r in monitored_diff_rows)
    ratio_two_count = sum(str(r.get("ratio_two_consecutive") or "").strip().lower() == "true" for r in monitored_diff_rows)

    cadence_options = [
        {
            "option_id": "A",
            "cadence_name": "Weekly synchronized dual-lane run (recommended)",
            "ready_run_frequency": "weekly",
            "escalate_run_frequency": "weekly",
            "run_id_model": "single run_id shared by READY and ESCALATE lanes",
            "state_update_frequency": "every run",
            "backup_policy": "backup every run before state update",
            "pros": "Best temporal consistency and lowest anti-mixing drift risk",
            "cons": "Highest regular operations cadence",
            "anti_mixing_impact": "strong positive",
            "fail_safe_impact": "strong positive",
            "ops_load_impact": "medium",
            "fit_for_current_state": "HIGH",
        },
        {
            "option_id": "B",
            "cadence_name": "READY weekly + ESCALATE biweekly (split run_id)",
            "ready_run_frequency": "weekly",
            "escalate_run_frequency": "biweekly",
            "run_id_model": "separate run_id per lane",
            "state_update_frequency": "READY weekly / ESCALATE biweekly",
            "backup_policy": "backup on each lane update",
            "pros": "Lowers monitoring lane workload",
            "cons": "Increases temporal-gap management complexity between lanes",
            "anti_mixing_impact": "neutral to negative if linkage weakens",
            "fail_safe_impact": "neutral",
            "ops_load_impact": "low to medium",
            "fit_for_current_state": "MEDIUM",
        },
        {
            "option_id": "C",
            "cadence_name": "Biweekly synchronized dual-lane run",
            "ready_run_frequency": "biweekly",
            "escalate_run_frequency": "biweekly",
            "run_id_model": "single run_id shared by READY and ESCALATE lanes",
            "state_update_frequency": "every run",
            "backup_policy": "backup every run before state update",
            "pros": "Lower operation cost than weekly sync",
            "cons": "Slower detection and slower reintegration decisions",
            "anti_mixing_impact": "positive",
            "fail_safe_impact": "positive",
            "ops_load_impact": "low",
            "fit_for_current_state": "MEDIUM",
        },
    ]
    recommended_option_id = "A"

    lane_definitions = {
        "READY_LANE": {
            "purpose": "Primary continuation lane for clean carry-forward records",
            "continue_when": [
                "boundary_breach_count == 0",
                "coverage_review_count == 0",
                "reject_candidate_count == 0",
                "join_blocker_count == 0",
                "ESCALATE/HOLDING/REJECT non-mixed",
            ],
        },
        "ESCALATE_SEPARATE_LANE": {
            "purpose": "Dedicated monitoring lane for escalated monitor_keys",
            "continue_when": [
                "escalate_blocker_count == 0",
                "ratio_two_consecutive_fired_count == 0",
                "route_degradation_fired_count == 0",
            ],
            "blocker_when": [
                "ratio_two_consecutive_fired_count > 0",
                "route_degradation_fired_count > 0",
                "boundary_breach_count > 0",
            ],
        },
        "HOLDING_LANE": {
            "purpose": "Out-of-scope holding queue excluded from current continuation streams",
            "exclude_reason": "Avoids contaminating READY/ESCALATE controlled operation boundary",
        },
        "REJECT_LANE": {
            "purpose": "Always-blocked set",
            "exclude_reason": "Rejected records remain outside controlled carry-forward stream",
        },
    }

    hold_restore_noop = {
        "global_hold_conditions": [
            "boundary_breach_count > 0",
            "coverage_review_count > 0",
            "reject_candidate_count > 0",
            "join_blocker_count > 0",
            "escalate_blocker_count > 0",
            "temporal_gap_count > 0",
        ],
        "ready_lane_local_hold_conditions": [
            "READY overlaps with ESCALATE/HOLDING/REJECT",
            "READY lane integrity_clear=false",
        ],
        "escalate_lane_local_hold_conditions": [
            "ratio_two_consecutive_fired_count > 0",
            "route_degradation_fired_count > 0",
            "escalate_blocker_count > 0",
        ],
        "restore_conditions": [
            "JSON/state corruption detected",
            "backup hash mismatch",
            "temporal gap detected after update",
            "post-update boundary/integrity breach",
        ],
        "no_op_conditions": [
            "incoming_run_id already in ingested_snapshot_run_ids",
            "same-run reinvocation with identical monitor snapshot",
        ],
    }

    reintegration_policy = {
        "from_lane": "ESCALATE_SEPARATE_LANE",
        "to_lane": "READY_LANE",
        "minimum_safe_runs": 3,
        "conditions": [
            "ratio_two_consecutive_fired_count == 0 for 3 consecutive runs",
            "route_degradation_fired_count == 0 for 3 consecutive runs",
            "no boundary/integrity breach for 3 consecutive runs",
            "manual reviewer approval recorded for each monitor_key",
        ],
        "persistence_handling": "Persistence remains historical context; reintegration is blocked by ratio/route/integrity signals, not by persistence alone.",
        "verification_before_rejoin": [
            "source signature unchanged",
            "lane boundary diff check PASS",
            "proposal-only guard unchanged",
        ],
    }

    holding_recheck_policy = {
        "cadence": "every 4 synchronized runs or monthly (whichever comes first)",
        "early_trigger_conditions": [
            "READY lane count drops by >=10% against previous monthly baseline",
            "ESCALATE lane grows by >=2 monitor_keys",
            "new stable source evidence appears for existing HOLDING records",
        ],
        "rule": "HOLDING review runs in isolated review lane without mixing into READY/ESCALATE streams.",
    }

    if boundary_breach_count > 0:
        decision = HOLD_POLICY
        blocker_labels = ["BOUNDARY_BREACH_DETECTED"]
    elif not integrity_clear:
        decision = HOLD_POLICY
        blocker_labels = ["INTEGRITY_BLOCKER_DETECTED"]
    elif route_deg_count > 0 or ratio_two_count > 0:
        decision = HOLD_REINTEGRATION
        blocker_labels = ["ESCALATE_SIGNAL_REQUIRES_RULE_TUNING"]
    else:
        decision = READY
        blocker_labels = []

    scope_material = "\n".join(sorted(ready_signatures)) + "\n--ESCALATE--\n" + "\n".join(sorted(escalate_signatures))
    scope_hash = hashlib.sha256(scope_material.encode("utf-8")).hexdigest()

    risk_notes = [
        "ESCALATE 4 monitor_keys persist via persistence trigger; route/ratio deterioration remains zero.",
        "HOLDING 17 remains excluded; prolonged exclusion can delay coverage improvements unless periodic recheck runs are executed.",
        "Single-run-id synchronized cadence reduces anti-mixing drift but requires disciplined operational timing.",
    ]

    summary = {
        "artifact": "exhibitions_text_steady_state_operation_proposal_summary",
        "task": "TASK258",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "inputs": {
            "task257_ready_input_csv": str(Path(args.task257_ready_input_csv)),
            "task257_escalate_input_csv": str(Path(args.task257_escalate_input_csv)),
            "task257_ready_summary_json": str(Path(args.task257_ready_summary_json)),
            "task257_escalate_summary_json": str(Path(args.task257_escalate_summary_json)),
            "task257_monitored_diff_csv": str(Path(args.task257_monitored_diff_csv)),
            "holding_set_csv": str(Path(args.holding_set_csv)),
            "reject_set_csv": str(Path(args.reject_set_csv)),
        },
        "lane_inventory": {
            "counts": lane_counts,
            "by_fair": lane_by_fair,
            "by_gallery": lane_by_gallery,
            "boundary_breach_count": boundary_breach_count,
            "overlap_details": overlaps,
            "integrity_clear": integrity_clear,
        },
        "lane_definitions": lane_definitions,
        "run_cadence_options": cadence_options,
        "recommended_option_id": recommended_option_id,
        "hold_restore_noop_policy": hold_restore_noop,
        "reintegration_policy": reintegration_policy,
        "holding_recheck_policy": holding_recheck_policy,
        "escalate_monitor_snapshot": {
            "monitor_key_count": len(monitored_diff_rows),
            "warning_primary_counts": dict(warning_counter),
            "ratio_two_consecutive_fired_count": ratio_two_count,
            "route_degradation_fired_count": route_deg_count,
        },
        "operational_risk_notes": risk_notes,
        "go_hold_decision": decision,
        "blocker_labels": blocker_labels,
        "next_task_recommendation": {
            "id": "TASK259",
            "title": "EXHIBITIONS-TEXT-STEADY-STATE-OPERATION-CONTROLLED-ADOPTION-PROPOSAL-FINALIZATION",
            "ja": "Finalize controlled steady-state runbook including cadence, reintegration checkpoints, and holding reevaluation gate",
        },
    }

    table_rows: list[dict[str, Any]] = []
    for lane_name, count in lane_counts.items():
        table_rows.append(
            {
                "section": "lane_total",
                "lane": lane_name,
                "fair_slug": "",
                "gallery_name_en": "",
                "count": count,
                "note_ja": "",
            }
        )
    for lane_name, fair_counts in lane_by_fair.items():
        for fair_slug, count in fair_counts.items():
            table_rows.append(
                {
                    "section": "by_fair",
                    "lane": lane_name,
                    "fair_slug": fair_slug,
                    "gallery_name_en": "",
                    "count": count,
                    "note_ja": "",
                }
            )
    for lane_name, gallery_counts in lane_by_gallery.items():
        for gallery_key, count in gallery_counts.items():
            gallery_name, fair_slug = (gallery_key.split("|", 1) + [""])[:2]
            table_rows.append(
                {
                    "section": "by_gallery",
                    "lane": lane_name,
                    "fair_slug": fair_slug,
                    "gallery_name_en": gallery_name,
                    "count": count,
                    "note_ja": "",
                }
            )

    option_rows = [
        {
            "option_id": o["option_id"],
            "cadence_name": o["cadence_name"],
            "ready_run_frequency": o["ready_run_frequency"],
            "escalate_run_frequency": o["escalate_run_frequency"],
            "run_id_model": o["run_id_model"],
            "backup_policy": o["backup_policy"],
            "fit_for_current_state": o["fit_for_current_state"],
            "recommended": o["option_id"] == recommended_option_id,
        }
        for o in cadence_options
    ]

    summary_path = output_dir / "exhibitions_text_steady_state_operation_proposal_summary_task258.json"
    table_path = output_dir / "exhibitions_text_steady_state_operation_proposal_table_task258.csv"
    option_path = output_dir / "exhibitions_text_steady_state_operation_options_task258.csv"
    manifest_path = output_dir / "exhibitions_text_steady_state_operation_proposal_manifest_task258.json"
    report_path = output_dir / "exhibitions_text_steady_state_operation_proposal_task258.md"

    write_json(summary_path, summary)
    write_csv(
        table_path,
        table_rows,
        ["section", "lane", "fair_slug", "gallery_name_en", "count", "note_ja"],
    )
    write_csv(
        option_path,
        option_rows,
        [
            "option_id",
            "cadence_name",
            "ready_run_frequency",
            "escalate_run_frequency",
            "run_id_model",
            "backup_policy",
            "fit_for_current_state",
            "recommended",
        ],
    )

    manifest = {
        "artifact": "exhibitions_text_steady_state_operation_proposal_manifest",
        "task": "TASK258",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "scope_hash": scope_hash,
        "lane_counts": lane_counts,
        "decision": decision,
        "blocker_labels": blocker_labels,
        "outputs": [
            str(summary_path),
            str(table_path),
            str(option_path),
            str(report_path),
        ],
    }
    write_json(manifest_path, manifest)

    report_lines = [
        "# TASK258 Exhibitions Text Steady-State Operation Proposal",
        "",
        "## Lane Definitions",
        f"- READY_LANE: {lane_counts['READY_LANE']}",
        f"- ESCALATE_SEPARATE_LANE: {lane_counts['ESCALATE_SEPARATE_LANE']}",
        f"- HOLDING_LANE (excluded): {lane_counts['HOLDING_LANE']}",
        f"- REJECT_LANE (excluded): {lane_counts['REJECT_LANE']}",
        "",
        "## Recommended Cadence",
        "- Option A (recommended): weekly synchronized run with shared run_id for READY and ESCALATE lanes, backup before each state update.",
        "",
        "## Hold/Restore/No-op",
        "- Global hold: boundary breach, integrity blocker, escalate blocker, temporal gap.",
        "- Restore: JSON/hash inconsistency, post-update blocker detection.",
        "- No-op: incoming run_id already ingested.",
        "",
        "## Reintegration and Holding Recheck",
        "- Reintegration candidate requires 3 consecutive safe runs (ratio/route/integrity clear) plus manual approval.",
        "- HOLDING lane is rechecked every 4 runs or monthly.",
        "",
        "## Decision",
        f"- go_hold_decision: `{decision}`",
        f"- blocker_labels: {', '.join(blocker_labels) if blocker_labels else '(none)'}",
        "",
        "## Next Task",
        "- TASK259: EXHIBITIONS-TEXT-STEADY-STATE-OPERATION-CONTROLLED-ADOPTION-PROPOSAL-FINALIZATION",
    ]
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(
        "[task258] "
        f"run_id={run_id} ready={lane_counts['READY_LANE']} escalate={lane_counts['ESCALATE_SEPARATE_LANE']} "
        f"holding={lane_counts['HOLDING_LANE']} reject={lane_counts['REJECT_LANE']} "
        f"boundary={boundary_breach_count} integrity_clear={integrity_clear} decision={decision}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
