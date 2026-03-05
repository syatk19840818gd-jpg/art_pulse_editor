from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY = "READY_FOR_READY_CONTINUATION_WITH_ESCALATE_SEPARATE_LANE"
HOLD_BOUNDARY = "HOLD_FOR_ESCALATE_BOUNDARY_TUNING"
HOLD_POLICY = "HOLD_FOR_SEPARATE_LANE_POLICY_REVIEW"


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
    parser = argparse.ArgumentParser(description="TASK252 Exhibitions Text escalate separation lane controlled start")
    parser.add_argument(
        "--continuation-input-csv",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_carry_forward_continuation_input_task243.csv",
    )
    parser.add_argument(
        "--task251-escalate-table-csv",
        default="data/phase1_seed10/logs/exhibitions_text_carry_forward_phase9_escalate_policy_handling_table_task251.csv",
    )
    parser.add_argument(
        "--task251-summary-json",
        default="data/phase1_seed10/logs/exhibitions_text_carry_forward_phase9_escalate_policy_handling_summary_task251.json",
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


def monitor_key(row: dict[str, str]) -> str:
    return "||".join(
        [
            str(row.get("fair_slug") or "").strip(),
            str(row.get("gallery_name_en") or "").strip(),
            str(row.get("source_url") or "").strip(),
        ]
    )


def row_signature(row: dict[str, str]) -> str:
    return "||".join(
        [
            str(row.get("gallery_name_en") or "").strip(),
            str(row.get("fair_slug") or "").strip(),
            str(row.get("target_year") or "").strip(),
            str(row.get("source_url") or "").strip(),
        ]
    )


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


def main() -> int:
    args = parse_args()
    run_id = args.run_id.strip() or datetime.now(timezone.utc).strftime("task252_%Y%m%dT%H%M%SZ")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    continuation_rows = read_csv(Path(args.continuation_input_csv))
    escalate_table_rows = read_csv(Path(args.task251_escalate_table_csv))
    s251 = read_json(Path(args.task251_summary_json), default={})
    s250 = read_json(Path(args.task250_summary_json), default={})
    holding_rows = read_csv(Path(args.holding_set_csv))
    reject_rows = read_csv(Path(args.reject_set_csv))

    escalate_separate_keys = {
        str(row.get("monitor_key") or "").strip()
        for row in escalate_table_rows
        if str(row.get("escalate_class") or "").strip() == "ESCALATE_SEPARATE_LANE"
    }

    separate_lane_rows: list[dict[str, str]] = []
    ready_restart_rows: list[dict[str, str]] = []
    dropped_other_rows: list[dict[str, str]] = []

    for row in continuation_rows:
        stream = str(row.get("continuation_stream") or "").strip()
        mkey = monitor_key(row)
        if mkey in escalate_separate_keys:
            out = dict(row)
            out["separate_lane_reason"] = "escalate_separate_lane_from_task251"
            separate_lane_rows.append(out)
        elif stream == "READY":
            out = dict(row)
            out["ready_restart_reason"] = "ready_continuation_restart_after_escalate_separation"
            ready_restart_rows.append(out)
        elif stream == "MONITORED":
            dropped_other_rows.append(dict(row))
        else:
            dropped_other_rows.append(dict(row))

    holding_signatures = {row_signature(r) for r in holding_rows}
    reject_signatures = {row_signature(r) for r in reject_rows}
    separate_signatures = {row_signature(r) for r in separate_lane_rows}
    ready_signatures = {row_signature(r) for r in ready_restart_rows}

    boundary_breach = {
        "ready_vs_separate_overlap": len(ready_signatures & separate_signatures),
        "ready_vs_holding_overlap": len(ready_signatures & holding_signatures),
        "ready_vs_reject_overlap": len(ready_signatures & reject_signatures),
        "separate_vs_holding_overlap": len(separate_signatures & holding_signatures),
        "separate_vs_reject_overlap": len(separate_signatures & reject_signatures),
    }
    boundary_breach_count = sum(boundary_breach.values())

    class_counts = dict(s251.get("escalate_inventory", {}).get("class_counts") or {})
    escalate_blocker_count = int(class_counts.get("ESCALATE_BLOCKER", 0))
    integrity = dict(s250.get("post_integrity") or {})
    coverage_review_count = int(integrity.get("coverage_review_count", 0))
    reject_count = int(integrity.get("reject_candidate_count", 0))
    join_blocker_count = int(integrity.get("join_blocker_count", 0))
    integrity_clear = all([coverage_review_count == 0, reject_count == 0, join_blocker_count == 0, escalate_blocker_count == 0])
    boundary_clear = boundary_breach_count == 0

    separate_lane_definition = {
        "label": "ESCALATE_SEPARATE_LANE",
        "definition": "Escalated monitored records triggered by persistence>=3 without ratio/route deterioration; isolated from READY continuation input",
        "monitor_focus": [
            "persistence progression",
            "ratio_two_consecutive emergence",
            "route_degradation emergence",
        ],
        "blocker_when": [
            "ratio_two_consecutive=true",
            "route_degradation=true",
            "integrity blockers present (coverage/reject/join_blocker)",
        ],
        "reintegrate_when": [
            "separate lane re-evaluation shows no escalation trigger for two consecutive controlled runs",
            "boundary/integrity checks remain clear",
        ],
        "separate_lane_hold_when": [
            "boundary breach detected",
            "integrity blocker > 0",
            "escalate_blocker_count > 0",
        ],
        "applied_monitor_keys": sorted(escalate_separate_keys),
    }

    ready_restart_definition = {
        "ready_continuation_allowed_when": [
            "READY set excludes all ESCALATE_SEPARATE_LANE monitor_keys",
            "HOLDING and REJECT non-mixed",
            "boundary_breach_count=0",
            "coverage/reject/join_blocker/escalate_blocker all zero",
        ],
        "separate_lane_presence_non_blocking_when": [
            "ESCALATE items are isolated in separate lane",
            "READY set integrity and join contract stay unchanged",
        ],
        "global_hold_when": [
            "boundary breach in READY or separate lane",
            "integrity blocker appears",
            "escalate_blocker_count > 0",
        ],
        "reintegrate_from_separate_lane_when": [
            "separate lane reintegration rules satisfied",
            "anti-mixing boundaries preserved",
        ],
    }

    by_fair_rows: list[dict[str, Any]] = []
    by_gallery_rows: list[dict[str, Any]] = []
    fair_keys = set(by_fair_counter(ready_restart_rows).keys()) | set(by_fair_counter(separate_lane_rows).keys())
    gallery_keys = set(by_gallery_counter(ready_restart_rows).keys()) | set(by_gallery_counter(separate_lane_rows).keys())

    ready_by_fair = by_fair_counter(ready_restart_rows)
    separate_by_fair = by_fair_counter(separate_lane_rows)
    ready_by_gallery = by_gallery_counter(ready_restart_rows)
    separate_by_gallery = by_gallery_counter(separate_lane_rows)

    for fair in sorted(fair_keys):
        by_fair_rows.append(
            {
                "fair_slug": fair,
                "ready_count": ready_by_fair.get(fair, 0),
                "escalate_separate_count": separate_by_fair.get(fair, 0),
                "holding_excluded_count": len([r for r in holding_rows if str(r.get("fair_slug") or "").strip() == fair]),
            }
        )
    for gallery in sorted(gallery_keys):
        by_gallery_rows.append(
            {
                "gallery_fair_key": gallery,
                "ready_count": ready_by_gallery.get(gallery, 0),
                "escalate_separate_count": separate_by_gallery.get(gallery, 0),
            }
        )

    if not boundary_clear:
        decision = HOLD_BOUNDARY
    elif not integrity_clear:
        decision = HOLD_POLICY
    else:
        decision = READY

    summary_common = {
        "task": "TASK252",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "inputs": {
            "continuation_input_csv": str(Path(args.continuation_input_csv)),
            "task251_escalate_table_csv": str(Path(args.task251_escalate_table_csv)),
            "task251_summary_json": str(Path(args.task251_summary_json)),
            "task250_summary_json": str(Path(args.task250_summary_json)),
            "holding_set_csv": str(Path(args.holding_set_csv)),
            "reject_set_csv": str(Path(args.reject_set_csv)),
        },
        "boundary_checks": boundary_breach | {"boundary_breach_count": boundary_breach_count},
        "integrity_checks": {
            "coverage_review_count": coverage_review_count,
            "reject_candidate_count": reject_count,
            "join_blocker_count": join_blocker_count,
            "escalate_blocker_count": escalate_blocker_count,
            "boundary_clear": boundary_clear,
            "integrity_clear": integrity_clear,
            "proposal_only": True,
            "formal_untouched": True,
            "adoption_executed": False,
            "rollback_executed": False,
            "join_contract_changed": False,
            "anti_mixing_enforced": True,
        },
    }

    separate_summary = {
        "artifact": "exhibitions_text_escalate_separation_lane_summary",
        **summary_common,
        "separate_lane": {
            "input_total": len(separate_lane_rows),
            "monitor_keys_total": len(escalate_separate_keys),
            "by_fair": separate_by_fair,
            "by_gallery": separate_by_gallery,
            "definition": separate_lane_definition,
        },
        "decision": decision,
        "next_task_recommendation": {
            "id": "TASK253",
            "title": "EXHIBITIONS-TEXT-READY-CONTINUATION-RESTART-WITH-ESCALATE-LANE-MONITORING",
            "ja": "Restart READY continuation while operating ESCALATE separate lane in parallel",
        },
    }

    ready_summary = {
        "artifact": "exhibitions_text_ready_continuation_restart_summary",
        **summary_common,
        "ready_restart": {
            "input_total": len(ready_restart_rows),
            "excluded_escalate_count": len(separate_lane_rows),
            "excluded_holding_count": len(holding_rows),
            "excluded_reject_count": len(reject_rows),
            "dropped_other_stream_count": len(dropped_other_rows),
            "by_fair": ready_by_fair,
            "by_gallery": ready_by_gallery,
            "definition": ready_restart_definition,
        },
        "decision": decision,
        "next_task_recommendation": {
            "id": "TASK253",
            "title": "EXHIBITIONS-TEXT-READY-CONTINUATION-RESTART-WITH-ESCALATE-LANE-MONITORING",
            "ja": "Restart READY continuation while operating ESCALATE separate lane in parallel",
        },
    }

    separate_input_path = output_dir / "exhibitions_text_escalate_separate_lane_input_task252.csv"
    ready_input_path = output_dir / "exhibitions_text_ready_continuation_restart_input_task252.csv"
    by_fair_path = output_dir / "exhibitions_text_escalate_separation_lane_by_fair_task252.csv"
    by_gallery_path = output_dir / "exhibitions_text_escalate_separation_lane_by_gallery_task252.csv"
    separate_summary_path = output_dir / "exhibitions_text_escalate_separation_lane_summary_task252.json"
    ready_summary_path = output_dir / "exhibitions_text_ready_continuation_restart_summary_task252.json"
    separate_manifest_path = output_dir / "exhibitions_text_escalate_separation_lane_manifest_task252.json"
    ready_manifest_path = output_dir / "exhibitions_text_ready_continuation_restart_manifest_task252.json"
    report_path = output_dir / "exhibitions_text_escalate_separation_lane_controlled_start_task252.md"

    if separate_lane_rows:
        write_csv(separate_input_path, separate_lane_rows, list(separate_lane_rows[0].keys()))
    else:
        write_csv(separate_input_path, [], ["gallery_name_en", "fair_slug", "target_year", "source_url"])
    if ready_restart_rows:
        write_csv(ready_input_path, ready_restart_rows, list(ready_restart_rows[0].keys()))
    else:
        write_csv(ready_input_path, [], ["gallery_name_en", "fair_slug", "target_year", "source_url"])

    write_csv(by_fair_path, by_fair_rows, ["fair_slug", "ready_count", "escalate_separate_count", "holding_excluded_count"])
    write_csv(by_gallery_path, by_gallery_rows, ["gallery_fair_key", "ready_count", "escalate_separate_count"])

    write_json(separate_summary_path, separate_summary)
    write_json(ready_summary_path, ready_summary)

    separate_manifest = {
        "artifact": "exhibitions_text_escalate_separation_lane_manifest",
        "task": "TASK252",
        "run_id": run_id,
        "inputs": separate_summary["inputs"],
        "outputs": {
            "separate_lane_input_csv": str(separate_input_path),
            "separate_lane_summary_json": str(separate_summary_path),
            "by_fair_csv": str(by_fair_path),
            "by_gallery_csv": str(by_gallery_path),
            "manifest_json": str(separate_manifest_path),
            "report_md": str(report_path),
        },
        "decision": decision,
        "boundary_checks": separate_summary["boundary_checks"],
        "integrity_checks": separate_summary["integrity_checks"],
    }
    ready_manifest = {
        "artifact": "exhibitions_text_ready_continuation_restart_manifest",
        "task": "TASK252",
        "run_id": run_id,
        "inputs": ready_summary["inputs"],
        "outputs": {
            "ready_restart_input_csv": str(ready_input_path),
            "ready_restart_summary_json": str(ready_summary_path),
            "by_fair_csv": str(by_fair_path),
            "by_gallery_csv": str(by_gallery_path),
            "manifest_json": str(ready_manifest_path),
            "report_md": str(report_path),
        },
        "decision": decision,
        "boundary_checks": ready_summary["boundary_checks"],
        "integrity_checks": ready_summary["integrity_checks"],
    }
    write_json(separate_manifest_path, separate_manifest)
    write_json(ready_manifest_path, ready_manifest)

    report_lines = [
        "# TASK252 Exhibitions Text Escalate Separation Lane Controlled Start",
        "",
        "## separate_lane",
        f"- escalate_separate_count={len(separate_lane_rows)}",
        f"- escalate_blocker_count={escalate_blocker_count}",
        "",
        "## ready_restart",
        f"- ready_restart_count={len(ready_restart_rows)}",
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
        "[task252] "
        f"ready_restart={len(ready_restart_rows)} escalate_separate={len(separate_lane_rows)} "
        f"holding_excluded={len(holding_rows)} boundary_breach={boundary_breach_count} "
        f"integrity_clear={integrity_clear} decision={decision}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
