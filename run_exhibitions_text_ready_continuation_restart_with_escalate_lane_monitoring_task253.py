from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY = "READY_FOR_READY_RESTART_WITH_ESCALATE_MONITORING_PHASE_2"
HOLD_BOUNDARY = "HOLD_FOR_BOUNDARY_RECHECK"
HOLD_POLICY = "HOLD_FOR_ESCALATE_LANE_POLICY_TUNING"


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
    parser = argparse.ArgumentParser(description="TASK253 Exhibitions Text ready restart with escalate lane monitoring")
    parser.add_argument(
        "--task252-ready-input-csv",
        default="data/phase1_seed10/logs/exhibitions_text_ready_continuation_restart_input_task252.csv",
    )
    parser.add_argument(
        "--task252-escalate-input-csv",
        default="data/phase1_seed10/logs/exhibitions_text_escalate_separate_lane_input_task252.csv",
    )
    parser.add_argument(
        "--task252-ready-summary-json",
        default="data/phase1_seed10/logs/exhibitions_text_ready_continuation_restart_summary_task252.json",
    )
    parser.add_argument(
        "--task252-escalate-summary-json",
        default="data/phase1_seed10/logs/exhibitions_text_escalate_separation_lane_summary_task252.json",
    )
    parser.add_argument(
        "--task250-summary-json",
        default="data/phase1_seed10/logs/exhibitions_text_carry_forward_phase8_second_live_run_monitoring_summary_task250.json",
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


def by_fair_counter(rows: list[dict[str, str]]) -> dict[str, int]:
    counter = Counter()
    for row in rows:
        counter[str(row.get("fair_slug") or "").strip()] += 1
    return dict(counter)


def by_gallery_counter(rows: list[dict[str, str]]) -> dict[str, int]:
    counter = Counter()
    for row in rows:
        key = f"{str(row.get('gallery_name_en') or '').strip()}|{str(row.get('fair_slug') or '').strip()}"
        counter[key] += 1
    return dict(counter)


def main() -> int:
    args = parse_args()
    run_id = args.run_id.strip() or datetime.now(timezone.utc).strftime("task253_%Y%m%dT%H%M%SZ")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ready_rows = read_csv(Path(args.task252_ready_input_csv))
    escalate_rows = read_csv(Path(args.task252_escalate_input_csv))
    s252_ready = read_json(Path(args.task252_ready_summary_json), default={})
    s252_escalate = read_json(Path(args.task252_escalate_summary_json), default={})
    s250 = read_json(Path(args.task250_summary_json), default={})
    holding_rows = read_csv(Path(args.holding_set_csv))
    reject_rows = read_csv(Path(args.reject_set_csv))

    ready_phase2_rows: list[dict[str, Any]] = []
    for row in ready_rows:
        out = dict(row)
        out["restart_phase"] = "READY_RESTART_PHASE_2"
        out["restart_lane"] = "READY_CONTINUATION_LANE"
        ready_phase2_rows.append(out)

    escalate_phase2_rows: list[dict[str, Any]] = []
    for row in escalate_rows:
        out = dict(row)
        out["monitoring_phase"] = "ESCALATE_MONITORING_PHASE_2"
        out["monitoring_lane"] = "ESCALATE_SEPARATE_LANE"
        out["monitoring_rule_source"] = "task251_option_b"
        escalate_phase2_rows.append(out)

    ready_signatures = {row_signature(r) for r in ready_phase2_rows}
    escalate_signatures = {row_signature(r) for r in escalate_phase2_rows}
    holding_signatures = {row_signature(r) for r in holding_rows}
    reject_signatures = {row_signature(r) for r in reject_rows}

    ready_monitor_keys = {monitor_key(r) for r in ready_phase2_rows}
    escalate_monitor_keys = {monitor_key(r) for r in escalate_phase2_rows}

    boundary_checks = {
        "ready_vs_escalate_signature_overlap": len(ready_signatures & escalate_signatures),
        "ready_vs_holding_overlap": len(ready_signatures & holding_signatures),
        "ready_vs_reject_overlap": len(ready_signatures & reject_signatures),
        "escalate_vs_holding_overlap": len(escalate_signatures & holding_signatures),
        "escalate_vs_reject_overlap": len(escalate_signatures & reject_signatures),
        "ready_vs_escalate_monitor_key_overlap": len(ready_monitor_keys & escalate_monitor_keys),
    }
    boundary_breach_count = sum(boundary_checks.values())

    integrity250 = dict(s250.get("post_integrity") or {})
    coverage_review_count = int(integrity250.get("coverage_review_count", 0))
    reject_count = int(integrity250.get("reject_candidate_count", 0))
    join_blocker_count = int(integrity250.get("join_blocker_count", 0))
    escalate_eval = dict(s250.get("escalate_evaluation") or {})
    escalate_blocker_count = int(escalate_eval.get("ratio_two_consecutive_fired_count", 0)) + int(
        escalate_eval.get("route_degradation_fired_count", 0)
    )
    integrity_clear = all(
        [
            coverage_review_count == 0,
            reject_count == 0,
            join_blocker_count == 0,
            escalate_blocker_count == 0,
        ]
    )
    boundary_clear = boundary_breach_count == 0

    ready_definition = {
        "continue_when": [
            "READY input is isolated from ESCALATE/HOLDING/REJECT",
            "boundary_breach_count=0",
            "coverage_review=0/reject=0/join_blocker=0/escalate_blocker=0",
            "join contract unchanged and proposal-only maintained",
        ],
        "global_hold_when": [
            "boundary breach detected",
            "integrity blocker detected",
            "escalate_blocker_count > 0",
        ],
        "non_blocking_with_escalate_lane_when": [
            "ESCALATE runs in dedicated separate lane",
            "READY lane boundary and integrity remain clear",
        ],
        "temporary_pause_when": [
            "ready_vs_escalate overlap detected",
            "join_blocker or reject appears",
        ],
    }

    escalate_definition = {
        "monitoring_targets": [
            "persistence progression by monitor_key",
            "ratio_two_consecutive emergence",
            "route_degradation emergence",
        ],
        "escalate_blocker_when": [
            "ratio_two_consecutive=true",
            "route_degradation=true",
            "integrity blocker appears",
        ],
        "reintegration_candidate_when": [
            "no escalation trigger for two consecutive controlled runs",
            "lane boundary clear and integrity clear",
        ],
        "lane_hold_when": [
            "escalate_blocker_count > 0",
            "boundary breach in separate lane",
            "integrity blocker > 0",
        ],
        "global_hold_when": [
            "same record enters READY and ESCALATE simultaneously",
            "join/reject blocker appears in global integrity checks",
        ],
    }

    ready_by_fair = by_fair_counter(ready_phase2_rows)
    escalate_by_fair = by_fair_counter(escalate_phase2_rows)
    ready_by_gallery = by_gallery_counter(ready_phase2_rows)
    escalate_by_gallery = by_gallery_counter(escalate_phase2_rows)

    by_fair_rows: list[dict[str, Any]] = []
    by_gallery_rows: list[dict[str, Any]] = []
    for fair in sorted(set(ready_by_fair) | set(escalate_by_fair)):
        by_fair_rows.append(
            {
                "fair_slug": fair,
                "ready_restart_count": ready_by_fair.get(fair, 0),
                "escalate_lane_count": escalate_by_fair.get(fair, 0),
                "holding_excluded_count": len([r for r in holding_rows if str(r.get("fair_slug") or "").strip() == fair]),
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

    if not boundary_clear:
        decision = HOLD_BOUNDARY
    elif not integrity_clear:
        decision = HOLD_POLICY
    else:
        decision = READY

    common_integrity = {
        "coverage_review_count": coverage_review_count,
        "reject_candidate_count": reject_count,
        "join_blocker_count": join_blocker_count,
        "escalate_blocker_count": escalate_blocker_count,
        "boundary_breach_count": boundary_breach_count,
        "boundary_clear": boundary_clear,
        "integrity_clear": integrity_clear,
        "proposal_only": True,
        "formal_untouched": True,
        "adoption_executed": False,
        "rollback_executed": False,
        "join_contract_changed": False,
        "anti_mixing_enforced": True,
    }

    ready_summary = {
        "artifact": "exhibitions_text_ready_continuation_restart_phase2_summary",
        "task": "TASK253",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "inputs": {
            "task252_ready_input_csv": str(Path(args.task252_ready_input_csv)),
            "task252_ready_summary_json": str(Path(args.task252_ready_summary_json)),
            "holding_set_csv": str(Path(args.holding_set_csv)),
            "reject_set_csv": str(Path(args.reject_set_csv)),
        },
        "ready_restart": {
            "input_total": len(ready_phase2_rows),
            "excluded_escalate_count": len(escalate_phase2_rows),
            "excluded_holding_count": len(holding_rows),
            "excluded_reject_count": len(reject_rows),
            "by_fair": ready_by_fair,
            "by_gallery": ready_by_gallery,
            "definition": ready_definition,
        },
        "boundary_checks": boundary_checks,
        "integrity_checks": common_integrity,
        "go_hold_decision": decision,
        "next_task_recommendation": {
            "id": "TASK254",
            "title": "EXHIBITIONS-TEXT-READY-RESTART-WITH-ESCALATE-MONITORING-PHASE-2-CONTINUATION",
            "ja": "Continue READY restart while monitoring ESCALATE lane and keeping strict separation boundaries",
        },
    }

    escalate_summary = {
        "artifact": "exhibitions_text_escalate_lane_monitoring_phase2_summary",
        "task": "TASK253",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "inputs": {
            "task252_escalate_input_csv": str(Path(args.task252_escalate_input_csv)),
            "task252_escalate_summary_json": str(Path(args.task252_escalate_summary_json)),
            "task250_summary_json": str(Path(args.task250_summary_json)),
            "holding_set_csv": str(Path(args.holding_set_csv)),
            "reject_set_csv": str(Path(args.reject_set_csv)),
        },
        "escalate_lane_monitoring": {
            "input_total": len(escalate_phase2_rows),
            "ready_not_mixed_count": len(ready_phase2_rows),
            "holding_excluded_count": len(holding_rows),
            "reject_excluded_count": len(reject_rows),
            "by_fair": escalate_by_fair,
            "by_gallery": escalate_by_gallery,
            "definition": escalate_definition,
        },
        "boundary_checks": boundary_checks,
        "integrity_checks": common_integrity,
        "go_hold_decision": decision,
        "next_task_recommendation": {
            "id": "TASK254",
            "title": "EXHIBITIONS-TEXT-READY-RESTART-WITH-ESCALATE-MONITORING-PHASE-2-CONTINUATION",
            "ja": "Continue READY restart while monitoring ESCALATE lane and keeping strict separation boundaries",
        },
    }

    ready_input_path = output_dir / "exhibitions_text_ready_continuation_restart_phase2_input_task253.csv"
    ready_summary_path = output_dir / "exhibitions_text_ready_continuation_restart_phase2_summary_task253.json"
    ready_manifest_path = output_dir / "exhibitions_text_ready_continuation_restart_phase2_manifest_task253.json"
    escalate_input_path = output_dir / "exhibitions_text_escalate_lane_monitoring_phase2_input_task253.csv"
    escalate_summary_path = output_dir / "exhibitions_text_escalate_lane_monitoring_phase2_summary_task253.json"
    escalate_manifest_path = output_dir / "exhibitions_text_escalate_lane_monitoring_phase2_manifest_task253.json"
    by_fair_path = output_dir / "exhibitions_text_ready_restart_with_escalate_lane_by_fair_task253.csv"
    by_gallery_path = output_dir / "exhibitions_text_ready_restart_with_escalate_lane_by_gallery_task253.csv"
    report_path = output_dir / "exhibitions_text_ready_restart_with_escalate_lane_monitoring_task253.md"

    if ready_phase2_rows:
        write_csv(ready_input_path, ready_phase2_rows, list(ready_phase2_rows[0].keys()))
    else:
        write_csv(ready_input_path, [], ["gallery_name_en", "fair_slug", "target_year", "source_url"])
    if escalate_phase2_rows:
        write_csv(escalate_input_path, escalate_phase2_rows, list(escalate_phase2_rows[0].keys()))
    else:
        write_csv(escalate_input_path, [], ["gallery_name_en", "fair_slug", "target_year", "source_url"])

    write_json(ready_summary_path, ready_summary)
    write_json(escalate_summary_path, escalate_summary)
    write_csv(by_fair_path, by_fair_rows, ["fair_slug", "ready_restart_count", "escalate_lane_count", "holding_excluded_count"])
    write_csv(by_gallery_path, by_gallery_rows, ["gallery_fair_key", "ready_restart_count", "escalate_lane_count"])

    ready_manifest = {
        "artifact": "exhibitions_text_ready_continuation_restart_phase2_manifest",
        "task": "TASK253",
        "run_id": run_id,
        "inputs": ready_summary["inputs"],
        "outputs": {
            "ready_input_csv": str(ready_input_path),
            "ready_summary_json": str(ready_summary_path),
            "by_fair_csv": str(by_fair_path),
            "by_gallery_csv": str(by_gallery_path),
            "manifest_json": str(ready_manifest_path),
            "report_md": str(report_path),
        },
        "decision": decision,
        "boundary_checks": boundary_checks,
        "integrity_checks": common_integrity,
    }
    escalate_manifest = {
        "artifact": "exhibitions_text_escalate_lane_monitoring_phase2_manifest",
        "task": "TASK253",
        "run_id": run_id,
        "inputs": escalate_summary["inputs"],
        "outputs": {
            "escalate_input_csv": str(escalate_input_path),
            "escalate_summary_json": str(escalate_summary_path),
            "by_fair_csv": str(by_fair_path),
            "by_gallery_csv": str(by_gallery_path),
            "manifest_json": str(escalate_manifest_path),
            "report_md": str(report_path),
        },
        "decision": decision,
        "boundary_checks": boundary_checks,
        "integrity_checks": common_integrity,
    }
    write_json(ready_manifest_path, ready_manifest)
    write_json(escalate_manifest_path, escalate_manifest)

    report_lines = [
        "# TASK253 Exhibitions Text Ready Continuation Restart with Escalate Lane Monitoring",
        "",
        "## bundles",
        f"- ready_restart_input_total={len(ready_phase2_rows)}",
        f"- escalate_lane_input_total={len(escalate_phase2_rows)}",
        f"- holding_excluded_count={len(holding_rows)}",
        f"- reject_excluded_count={len(reject_rows)}",
        "",
        "## checks",
        f"- boundary_breach_count={boundary_breach_count}",
        f"- integrity_clear={integrity_clear}",
        "",
        "## decision",
        f"- go_hold_decision={decision}",
    ]
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(
        "[task253] "
        f"ready_restart={len(ready_phase2_rows)} escalate_lane={len(escalate_phase2_rows)} "
        f"holding_excluded={len(holding_rows)} boundary_breach={boundary_breach_count} "
        f"integrity_clear={integrity_clear} decision={decision}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
