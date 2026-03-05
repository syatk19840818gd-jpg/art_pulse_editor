from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY = "READY_FOR_ESCALATE_SEPARATION_PHASE"
HOLD_DECISION = "HOLD_FOR_ESCALATE_POLICY_DECISION"
HOLD_STOP = "HOLD_FOR_CONTINUATION_STOP"


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
    parser = argparse.ArgumentParser(description="TASK251 Exhibitions Text carry-forward phase9 escalate policy handling")
    parser.add_argument(
        "--task245-summary-json",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_carry_forward_continuation_phase3_summary_task245.json",
    )
    parser.add_argument(
        "--task249-summary-json",
        default="data/phase1_seed10/logs/exhibitions_text_carry_forward_phase7_live_next_run_continuation_summary_task249.json",
    )
    parser.add_argument(
        "--task249-monitored-diff-csv",
        default="data/phase1_seed10/logs/exhibitions_text_carry_forward_phase7_live_next_run_continuation_monitored_diff_task249.csv",
    )
    parser.add_argument(
        "--task250-summary-json",
        default="data/phase1_seed10/logs/exhibitions_text_carry_forward_phase8_second_live_run_monitoring_summary_task250.json",
    )
    parser.add_argument(
        "--task250-monitored-diff-csv",
        default="data/phase1_seed10/logs/exhibitions_text_carry_forward_phase8_second_live_run_monitoring_monitored_diff_task250.csv",
    )
    parser.add_argument("--output-dir", default="data/phase1_seed10/logs")
    parser.add_argument("--run-id", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_id = args.run_id.strip() or datetime.now(timezone.utc).strftime("task251_%Y%m%dT%H%M%SZ")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    s245 = read_json(Path(args.task245_summary_json), default={})
    s249 = read_json(Path(args.task249_summary_json), default={})
    d249 = read_csv(Path(args.task249_monitored_diff_csv))
    s250 = read_json(Path(args.task250_summary_json), default={})
    d250 = read_csv(Path(args.task250_monitored_diff_csv))

    rows245 = list(s245.get("monitored_temporal_review", {}).get("monitored_rows", []))
    by_monitor245: dict[str, dict[str, Any]] = {}
    for row in rows245:
        key = "||".join(
            [
                str(row.get("fair_slug") or "").strip(),
                str(row.get("gallery_name_en") or "").strip(),
                str(row.get("source_url") or "").strip(),
            ]
        )
        by_monitor245[key] = row

    by_monitor249 = {str(row.get("monitor_key") or "").strip(): row for row in d249}
    by_monitor250 = {str(row.get("monitor_key") or "").strip(): row for row in d250}

    inventory_rows: list[dict[str, Any]] = []
    class_counter = Counter()
    warning_counter = Counter()

    for key in sorted(by_monitor250.keys()):
        row250 = by_monitor250[key]
        row249 = by_monitor249.get(key, {})
        row245 = by_monitor245.get(key, {})

        trig_persist = str(row250.get("escalate_trigger_persistence") or "").strip().lower() == "true"
        trig_ratio = str(row250.get("escalate_trigger_ratio") or "").strip().lower() == "true"
        trig_route = str(row250.get("escalate_trigger_route") or "").strip().lower() == "true"
        route_deg = str(row250.get("route_degradation_flag") or "").strip().lower() == "true"
        ratio_two = str(row250.get("ratio_two_consecutive") or "").strip().lower() == "true"
        warning_primary = str(row250.get("warning_after") or row250.get("warning_before") or "").strip()

        if trig_route or trig_ratio or route_deg or ratio_two:
            escalate_class = "ESCALATE_BLOCKER"
        elif trig_persist:
            escalate_class = "ESCALATE_SEPARATE_LANE"
        else:
            escalate_class = "ESCALATE_MONITOR_ONLY"

        class_counter[escalate_class] += 1
        warning_counter[warning_primary] += 1

        inventory_rows.append(
            {
                "monitor_key": key,
                "fair_slug": str(row250.get("fair_slug") or "").strip(),
                "gallery_name_en": str(row250.get("gallery_name_en") or "").strip(),
                "source_url": str(row250.get("source_url") or "").strip(),
                "warning_primary": warning_primary,
                "trigger_persistence": trig_persist,
                "trigger_ratio_two_consecutive": trig_ratio or ratio_two,
                "trigger_route_degradation": trig_route or route_deg,
                "task245_persistence": int(row245.get("persistence_count", 0) or 0),
                "task249_persistence_after": int(row249.get("persistence_after", 0) or 0),
                "task250_persistence_after": int(row250.get("persistence_after", 0) or 0),
                "task245_escalate_now": bool(row245.get("escalate_now", False)),
                "task249_escalate_now": str(row249.get("escalate_now") or "").strip().lower() == "true",
                "task250_escalate_now": str(row250.get("escalate_now") or "").strip().lower() == "true",
                "escalate_class": escalate_class,
            }
        )

    live250 = dict(s250.get("second_live_update_result") or {})
    integ250 = dict(s250.get("post_integrity") or {})
    ready_count = int(s250.get("second_live_preflight", {}).get("ready_count", 0))
    monitored_count = int(s250.get("second_live_preflight", {}).get("monitored_count", 0))
    holding_excluded = int(s250.get("second_live_preflight", {}).get("holding_excluded_count", 0))

    integrity_clear = all(
        int(integ250.get(k, 0)) == 0 for k in ["coverage_review_count", "reject_candidate_count", "join_blocker_count", "escalate_set_count"]
    )
    boundary_clear = int(s250.get("second_live_preflight", {}).get("boundary_breach_count", 0)) == 0

    option_rows = [
        {
            "option_id": "A",
            "option_title": "Stop continuation when any ESCALATE is present",
            "pros": "Safest and simple control flow",
            "cons": "Blocks READY 48 progression and slows operations",
            "anti_mixing_impact": "kept",
            "proposal_only_impact": "kept",
            "join_integrity_impact": "kept",
            "fit_for_current_state": "LOW",
        },
        {
            "option_id": "B",
            "option_title": "Separate ESCALATE lane and continue READY lane",
            "pros": "Allows READY progression while isolating escalation targets",
            "cons": "Requires additional lane operations and monitoring",
            "anti_mixing_impact": "kept with stronger boundary control",
            "proposal_only_impact": "kept",
            "join_integrity_impact": "kept",
            "fit_for_current_state": "HIGH",
        },
        {
            "option_id": "C",
            "option_title": "Downgrade ESCALATE back to MONITORED and continue",
            "pros": "Lowest operational overhead",
            "cons": "Suppresses escalation signal and weakens monitoring trust",
            "anti_mixing_impact": "kept",
            "proposal_only_impact": "kept",
            "join_integrity_impact": "kept",
            "fit_for_current_state": "LOW",
        },
    ]

    all_persistence_only = all(
        row.get("trigger_persistence") and not row.get("trigger_ratio_two_consecutive") and not row.get("trigger_route_degradation")
        for row in inventory_rows
    )

    if not integrity_clear or not boundary_clear:
        decision = HOLD_STOP
        recommended = "A"
    elif all_persistence_only and class_counter["ESCALATE_BLOCKER"] == 0:
        decision = READY
        recommended = "B"
    else:
        decision = HOLD_DECISION
        recommended = "A"

    if recommended == "B":
        recommended_ja = "Separate 4 ESCALATE items into dedicated lane and continue READY 48"
    elif recommended == "A":
        recommended_ja = "Stop continuation by treating ESCALATE as global blocker"
    else:
        recommended_ja = "Continue by downgrading ESCALATE to MONITORED (not recommended)"

    summary = {
        "artifact": "exhibitions_text_carry_forward_phase9_escalate_policy_handling_summary",
        "task": "TASK251",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "inputs": {
            "task245_summary_json": str(Path(args.task245_summary_json)),
            "task249_summary_json": str(Path(args.task249_summary_json)),
            "task249_monitored_diff_csv": str(Path(args.task249_monitored_diff_csv)),
            "task250_summary_json": str(Path(args.task250_summary_json)),
            "task250_monitored_diff_csv": str(Path(args.task250_monitored_diff_csv)),
        },
        "escalate_inventory": {
            "escalate_total": len(inventory_rows),
            "class_counts": dict(class_counter),
            "warning_primary_counts": dict(warning_counter),
            "trigger_counts": {
                "persistence_rule_fired_count": sum(1 for r in inventory_rows if r["trigger_persistence"]),
                "ratio_two_consecutive_fired_count": sum(1 for r in inventory_rows if r["trigger_ratio_two_consecutive"]),
                "route_degradation_fired_count": sum(1 for r in inventory_rows if r["trigger_route_degradation"]),
            },
            "history_reference": {
                "task245_escalate_now_count": int(s245.get("monitored_temporal_review", {}).get("escalate_now_count", 0)),
                "task249_escalate_now_count": int(s249.get("live_update_result", {}).get("escalate_now_count", 0)),
                "task250_escalate_now_count": int(live250.get("escalate_now_count", 0)),
            },
        },
        "operational_partition": {
            "ready_count": ready_count,
            "monitored_count": monitored_count,
            "holding_excluded_count": holding_excluded,
            "can_ready_continue": decision == READY,
            "can_escalate_separate_lane": class_counter["ESCALATE_SEPARATE_LANE"] > 0 and class_counter["ESCALATE_BLOCKER"] == 0,
            "holding_stays_out_of_scope": True,
            "boundary_clear": boundary_clear,
            "integrity_clear": integrity_clear,
        },
        "policy_options": option_rows,
        "recommended_option": {
            "option_id": recommended,
            "summary_ja": recommended_ja,
        },
        "go_hold_decision": decision,
        "blocker_labels": [] if decision == READY else ["ESCALATE_POLICY_DECISION_REQUIRED"],
        "next_task_recommendation": {
            "id": "TASK252",
            "title": "EXHIBITIONS-TEXT-ESCALATE-SEPARATION-LANE-CONTROLLED-START",
            "ja": "Separate ESCALATE set into dedicated controlled lane while continuing READY set",
        },
    }

    summary_path = output_dir / "exhibitions_text_carry_forward_phase9_escalate_policy_handling_summary_task251.json"
    table_path = output_dir / "exhibitions_text_carry_forward_phase9_escalate_policy_handling_table_task251.csv"
    option_path = output_dir / "exhibitions_text_carry_forward_phase9_escalate_policy_options_task251.csv"
    manifest_path = output_dir / "exhibitions_text_carry_forward_phase9_escalate_policy_handling_manifest_task251.json"
    report_path = output_dir / "exhibitions_text_carry_forward_phase9_escalate_policy_handling_task251.md"

    write_json(summary_path, summary)

    table_fields = [
        "monitor_key",
        "fair_slug",
        "gallery_name_en",
        "source_url",
        "warning_primary",
        "trigger_persistence",
        "trigger_ratio_two_consecutive",
        "trigger_route_degradation",
        "task245_persistence",
        "task249_persistence_after",
        "task250_persistence_after",
        "task245_escalate_now",
        "task249_escalate_now",
        "task250_escalate_now",
        "escalate_class",
    ]
    write_csv(table_path, inventory_rows, table_fields)

    option_fields = [
        "option_id",
        "option_title",
        "pros",
        "cons",
        "anti_mixing_impact",
        "proposal_only_impact",
        "join_integrity_impact",
        "fit_for_current_state",
    ]
    write_csv(option_path, option_rows, option_fields)

    manifest = {
        "artifact": "exhibitions_text_carry_forward_phase9_escalate_policy_handling_manifest",
        "task": "TASK251",
        "run_id": run_id,
        "inputs": summary["inputs"],
        "outputs": {
            "summary_json": str(summary_path),
            "inventory_table_csv": str(table_path),
            "options_csv": str(option_path),
            "manifest_json": str(manifest_path),
            "report_md": str(report_path),
        },
        "decision": decision,
    }
    write_json(manifest_path, manifest)

    report_lines = [
        "# TASK251 Exhibitions Text Carry-Forward Phase9 Escalate Policy Handling",
        "",
        "## inventory",
        f"- escalate_total={len(inventory_rows)}",
        f"- class_counts={dict(class_counter)}",
        f"- trigger_counts={summary['escalate_inventory']['trigger_counts']}",
        "",
        "## continuation_impact",
        f"- ready_count={ready_count}",
        f"- monitored_count={monitored_count}",
        f"- holding_excluded_count={holding_excluded}",
        f"- can_ready_continue={summary['operational_partition']['can_ready_continue']}",
        f"- can_escalate_separate_lane={summary['operational_partition']['can_escalate_separate_lane']}",
        "",
        "## recommendation",
        f"- option={recommended}",
        f"- summary_ja={recommended_ja}",
        f"- go_hold_decision={decision}",
    ]
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(
        "[task251] "
        f"escalate_total={len(inventory_rows)} class_counts={dict(class_counter)} "
        f"decision={decision} recommended_option={recommended}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
