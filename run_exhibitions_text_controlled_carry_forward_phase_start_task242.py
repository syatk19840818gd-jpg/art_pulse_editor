from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CARRY_FORWARD_READY_SET = "CARRY_FORWARD_READY_SET"
CARRY_FORWARD_MONITORED_SET = "CARRY_FORWARD_MONITORED_SET"
HOLDING_SET = "HOLDING_SET"
ESCALATE_SET = "ESCALATE_SET"
REJECT_SET = "REJECT_SET"


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
    parser = argparse.ArgumentParser(description="TASK242 Exhibitions Text controlled carry-forward phase start")
    parser.add_argument(
        "--task241-summary",
        default="data/phase1_seed10/logs/exhibitions_text_post_review_triage_phase_start_summary_task241.json",
    )
    parser.add_argument(
        "--task241-ready-csv",
        default="data/phase1_seed10/logs/exhibitions_text_post_review_ready_carry_forward_task241.csv",
    )
    parser.add_argument(
        "--task241-monitored-csv",
        default="data/phase1_seed10/logs/exhibitions_text_post_review_monitored_stable_warning_task241.csv",
    )
    parser.add_argument(
        "--task241-holding-csv",
        default="data/phase1_seed10/logs/exhibitions_text_post_review_resolution_holding_task241.csv",
    )
    parser.add_argument(
        "--task241-escalate-csv",
        default="data/phase1_seed10/logs/exhibitions_text_post_review_escalate_watch_task241.csv",
    )
    parser.add_argument(
        "--task241-reject-csv",
        default="data/phase1_seed10/logs/exhibitions_text_post_review_reject_candidates_task241.csv",
    )
    parser.add_argument("--output-dir", default="data/phase1_seed10/logs")
    parser.add_argument("--run-id", default="")
    return parser.parse_args()


def attach_set_fields(rows: list[dict[str, str]], set_name: str, set_reason: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["carry_forward_set"] = set_name
        item["carry_forward_reason"] = set_reason
        out.append(item)
    return out


def summarize_by_scope(rows: list[dict[str, Any]]) -> tuple[dict[str, dict[str, int]], dict[str, dict[str, int]]]:
    by_fair = defaultdict(Counter)
    by_gallery = defaultdict(Counter)
    for row in rows:
        fair = str(row.get("fair_slug") or "").strip()
        gallery = str(row.get("gallery_name_en") or "").strip()
        set_name = str(row.get("carry_forward_set") or "").strip()
        by_fair[fair][set_name] += 1
        by_gallery[(gallery, fair)][set_name] += 1
    return (
        {k: dict(v) for k, v in by_fair.items()},
        {f"{k[0]}|{k[1]}": dict(v) for k, v in by_gallery.items()},
    )


def main() -> int:
    args = parse_args()
    run_id = args.run_id.strip() or datetime.now(timezone.utc).strftime("task242_%Y%m%dT%H%M%SZ")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    summary241 = read_json(Path(args.task241_summary), default={})
    ready_rows_raw = read_csv(Path(args.task241_ready_csv))
    monitored_rows_raw = read_csv(Path(args.task241_monitored_csv))
    holding_rows_raw = read_csv(Path(args.task241_holding_csv))
    escalate_rows_raw = read_csv(Path(args.task241_escalate_csv))
    reject_rows_raw = read_csv(Path(args.task241_reject_csv))

    ready_rows = attach_set_fields(
        ready_rows_raw,
        CARRY_FORWARD_READY_SET,
        "carry_forward_directly_in_controlled_phase",
    )
    monitored_rows = attach_set_fields(
        monitored_rows_raw,
        CARRY_FORWARD_MONITORED_SET,
        "carry_forward_with_monitoring_rule_set_from_task239_240",
    )
    holding_rows = attach_set_fields(
        holding_rows_raw,
        HOLDING_SET,
        "excluded_from_current_carry_forward_input_boundary",
    )
    escalate_rows = attach_set_fields(
        escalate_rows_raw,
        ESCALATE_SET,
        "escalate_watch_boundary_blocking_if_nonzero",
    )
    reject_rows = attach_set_fields(
        reject_rows_raw,
        REJECT_SET,
        "always_blocker_until_resolved_in_proposal_scope",
    )

    all_rows = ready_rows + monitored_rows + holding_rows + escalate_rows + reject_rows
    carry_forward_input_rows = ready_rows + monitored_rows

    set_counts = Counter(str(row.get("carry_forward_set") or "") for row in all_rows)
    by_fair_counts, by_gallery_counts = summarize_by_scope(all_rows)

    monitored_text_only_count = sum(
        1
        for row in monitored_rows
        if str(row.get("join_status") or "").strip() == "TEXT_ONLY"
        or str(row.get("join_basis") or "").strip() == "no_image_candidate"
    )
    monitored_route_soft_count = sum(
        1 for row in monitored_rows if str(row.get("route_quality_label") or "").strip() == "soft_suspicious"
    )
    monitored_year_warning_count = sum(
        1 for row in monitored_rows if str(row.get("year_quality_label") or "").strip() != "pass"
    )

    holding_by_fair = Counter(str(row.get("fair_slug") or "").strip() for row in holding_rows)
    holding_by_gallery = Counter(
        f"{str(row.get('gallery_name_en') or '').strip()}|{str(row.get('fair_slug') or '').strip()}"
        for row in holding_rows
    )

    coverage_review_count = int(summary241.get("precheck", {}).get("coverage_review_count", 0))
    join_blocker_count = int(summary241.get("precheck", {}).get("join_blocker_count", 0))
    reject_count = max(
        len(reject_rows),
        int(summary241.get("precheck", {}).get("reject_candidate_count", 0)),
    )

    blocker_labels: list[str] = []
    if coverage_review_count > 0:
        blocker_labels.append("COVERAGE_REVIEW_PRESENT")
    if join_blocker_count > 0:
        blocker_labels.append("JOIN_BLOCKER_PRESENT")
    if reject_count > 0:
        blocker_labels.append("REJECT_SET_PRESENT")
    if len(escalate_rows) > 0:
        blocker_labels.append("ESCALATE_SET_PRESENT")

    if blocker_labels:
        decision = "HOLD_FOR_CARRY_FORWARD_POLICY_TUNING"
    elif len(holding_rows) > 0 and len(carry_forward_input_rows) == 0:
        decision = "HOLD_FOR_HOLDING_BOUNDARY_REVIEW"
    else:
        decision = "READY_FOR_CARRY_FORWARD_CONTINUATION"

    summary = {
        "artifact": "exhibitions_text_controlled_carry_forward_phase_start_summary",
        "task": "TASK242",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "inputs": {
            "task241_summary": str(Path(args.task241_summary)),
            "task241_ready_csv": str(Path(args.task241_ready_csv)),
            "task241_monitored_csv": str(Path(args.task241_monitored_csv)),
            "task241_holding_csv": str(Path(args.task241_holding_csv)),
            "task241_escalate_csv": str(Path(args.task241_escalate_csv)),
            "task241_reject_csv": str(Path(args.task241_reject_csv)),
        },
        "carry_forward_sets": {
            CARRY_FORWARD_READY_SET: int(set_counts.get(CARRY_FORWARD_READY_SET, 0)),
            CARRY_FORWARD_MONITORED_SET: int(set_counts.get(CARRY_FORWARD_MONITORED_SET, 0)),
            HOLDING_SET: int(set_counts.get(HOLDING_SET, 0)),
            ESCALATE_SET: int(set_counts.get(ESCALATE_SET, 0)),
            REJECT_SET: int(set_counts.get(REJECT_SET, 0)),
            "carry_forward_candidate_total": len(carry_forward_input_rows),
            "records_total": len(all_rows),
        },
        "aggregates": {
            "by_fair_set_counts": by_fair_counts,
            "by_gallery_set_counts": by_gallery_counts,
            "holding_bias_by_fair": dict(holding_by_fair),
            "holding_bias_by_gallery": dict(holding_by_gallery),
            "monitored_primary_patterns": {
                "text_only_count": monitored_text_only_count,
                "route_soft_count": monitored_route_soft_count,
                "year_warning_count": monitored_year_warning_count,
            },
        },
        "carry_forward_policy": {
            CARRY_FORWARD_READY_SET: {
                "included_in_input_bundle": True,
                "condition": "coverage_review=0 AND join_blocker=0 AND reject=0",
            },
            CARRY_FORWARD_MONITORED_SET: {
                "included_in_input_bundle": True,
                "condition": "non-blocking warning only; keep TASK239/240 escalate rules",
                "escalate_rules": [
                    "persisting >=3 controlled runs",
                    "stable_text_only_ratio > 0.6 for two runs",
                    "route quality degradation trend",
                ],
            },
            HOLDING_SET: {
                "included_in_input_bundle": False,
                "condition": "defer from current carry-forward boundary",
                "revisit_timing": "next controlled boundary review or when monitored warnings worsen",
            },
            ESCALATE_SET: {
                "included_in_input_bundle": False,
                "current_count": len(escalate_rows),
                "condition": "blocker when nonzero",
            },
            REJECT_SET: {
                "included_in_input_bundle": False,
                "current_count": len(reject_rows),
                "condition": "always blocker",
            },
        },
        "integrity_checks": {
            "coverage_review_count": coverage_review_count,
            "reject_candidate_count": reject_count,
            "join_blocker_count": join_blocker_count,
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
            "id": "TASK243",
            "title": "EXHIBITIONS-TEXT-CONTROLLED-CARRY-FORWARD-CONTINUATION-PHASE-1",
            "ja": "Process carry-forward input set (READY + MONITORED) in controlled continuation while keeping HOLDING deferred",
        },
    }

    summary_path = output_dir / "exhibitions_text_controlled_carry_forward_phase_start_summary_task242.json"
    table_path = output_dir / "exhibitions_text_controlled_carry_forward_phase_start_table_task242.csv"
    fair_table_path = output_dir / "exhibitions_text_controlled_carry_forward_phase_start_by_fair_task242.csv"
    records_path = output_dir / "exhibitions_text_controlled_carry_forward_phase_records_task242.csv"
    carry_input_path = output_dir / "exhibitions_text_controlled_carry_forward_input_set_task242.csv"
    ready_path = output_dir / "exhibitions_text_controlled_carry_forward_ready_set_task242.csv"
    monitored_path = output_dir / "exhibitions_text_controlled_carry_forward_monitored_set_task242.csv"
    holding_path = output_dir / "exhibitions_text_controlled_carry_forward_holding_set_task242.csv"
    escalate_path = output_dir / "exhibitions_text_controlled_carry_forward_escalate_set_task242.csv"
    reject_path = output_dir / "exhibitions_text_controlled_carry_forward_reject_set_task242.csv"
    manifest_path = output_dir / "exhibitions_text_controlled_carry_forward_phase_start_manifest_task242.json"
    report_path = output_dir / "exhibitions_text_controlled_carry_forward_phase_start_task242.md"

    fields = [
        "gallery_name_en",
        "fair_slug",
        "target_year",
        "source_url",
        "join_status",
        "join_basis",
        "route_quality_label",
        "year_quality_label",
        "provenance_suspicious",
        "triage_bucket",
        "triage_reason",
        "resolution_label",
        "resolution_reason",
        "phase2_label",
        "phase2_reason",
        "phase3_label",
        "phase3_reason",
        "post_review_bucket",
        "post_review_reason",
        "source_stream",
        "carry_forward_set",
        "carry_forward_reason",
    ]
    write_csv(records_path, all_rows, fields)
    write_csv(carry_input_path, carry_forward_input_rows, fields)
    write_csv(ready_path, ready_rows, fields)
    write_csv(monitored_path, monitored_rows, fields)
    write_csv(holding_path, holding_rows, fields)
    write_csv(escalate_path, escalate_rows, fields)
    write_csv(reject_path, reject_rows, fields)

    table_rows: list[dict[str, Any]] = []
    by_gallery_counter = defaultdict(Counter)
    for row in all_rows:
        gallery = str(row.get("gallery_name_en") or "").strip()
        fair = str(row.get("fair_slug") or "").strip()
        set_name = str(row.get("carry_forward_set") or "").strip()
        by_gallery_counter[(gallery, fair)][set_name] += 1
    for (gallery, fair), counts in sorted(by_gallery_counter.items(), key=lambda x: (x[0][1], x[0][0])):
        table_rows.append(
            {
                "gallery_name_en": gallery,
                "fair_slug": fair,
                CARRY_FORWARD_READY_SET: int(counts.get(CARRY_FORWARD_READY_SET, 0)),
                CARRY_FORWARD_MONITORED_SET: int(counts.get(CARRY_FORWARD_MONITORED_SET, 0)),
                HOLDING_SET: int(counts.get(HOLDING_SET, 0)),
                ESCALATE_SET: int(counts.get(ESCALATE_SET, 0)),
                REJECT_SET: int(counts.get(REJECT_SET, 0)),
            }
        )
    write_csv(
        table_path,
        table_rows,
        [
            "gallery_name_en",
            "fair_slug",
            CARRY_FORWARD_READY_SET,
            CARRY_FORWARD_MONITORED_SET,
            HOLDING_SET,
            ESCALATE_SET,
            REJECT_SET,
        ],
    )

    fair_rows: list[dict[str, Any]] = []
    by_fair_counter = defaultdict(Counter)
    for row in all_rows:
        fair = str(row.get("fair_slug") or "").strip()
        set_name = str(row.get("carry_forward_set") or "").strip()
        by_fair_counter[fair][set_name] += 1
    for fair, counts in sorted(by_fair_counter.items(), key=lambda x: x[0]):
        fair_rows.append(
            {
                "fair_slug": fair,
                CARRY_FORWARD_READY_SET: int(counts.get(CARRY_FORWARD_READY_SET, 0)),
                CARRY_FORWARD_MONITORED_SET: int(counts.get(CARRY_FORWARD_MONITORED_SET, 0)),
                HOLDING_SET: int(counts.get(HOLDING_SET, 0)),
                ESCALATE_SET: int(counts.get(ESCALATE_SET, 0)),
                REJECT_SET: int(counts.get(REJECT_SET, 0)),
            }
        )
    write_csv(
        fair_table_path,
        fair_rows,
        [
            "fair_slug",
            CARRY_FORWARD_READY_SET,
            CARRY_FORWARD_MONITORED_SET,
            HOLDING_SET,
            ESCALATE_SET,
            REJECT_SET,
        ],
    )

    write_json(summary_path, summary)
    manifest = {
        "artifact": "exhibitions_text_controlled_carry_forward_phase_start_manifest",
        "task": "TASK242",
        "run_id": run_id,
        "inputs": summary["inputs"],
        "outputs": {
            "summary_json": str(summary_path),
            "table_csv": str(table_path),
            "by_fair_table_csv": str(fair_table_path),
            "records_csv": str(records_path),
            "carry_forward_input_set_csv": str(carry_input_path),
            "carry_forward_ready_set_csv": str(ready_path),
            "carry_forward_monitored_set_csv": str(monitored_path),
            "holding_set_csv": str(holding_path),
            "escalate_set_csv": str(escalate_path),
            "reject_set_csv": str(reject_path),
            "report_md": str(report_path),
            "manifest_json": str(manifest_path),
        },
        "integrity_checks": summary["integrity_checks"],
    }
    write_json(manifest_path, manifest)

    report_lines = [
        "# TASK242 Exhibitions Text Controlled Carry-Forward Phase Start",
        "",
        "## set_definition",
        f"- {CARRY_FORWARD_READY_SET}: direct controlled carry-forward set.",
        f"- {CARRY_FORWARD_MONITORED_SET}: carry-forward with monitoring.",
        f"- {HOLDING_SET}: excluded from this carry-forward boundary.",
        f"- {ESCALATE_SET}: blocker watch set when nonzero.",
        f"- {REJECT_SET}: always blocker set.",
        "",
        "## counts",
        f"- {CARRY_FORWARD_READY_SET}={len(ready_rows)}",
        f"- {CARRY_FORWARD_MONITORED_SET}={len(monitored_rows)}",
        f"- {HOLDING_SET}={len(holding_rows)}",
        f"- {ESCALATE_SET}={len(escalate_rows)}",
        f"- {REJECT_SET}={len(reject_rows)}",
        f"- carry_forward_candidate_total={len(carry_forward_input_rows)}",
        "",
        "## monitored_patterns",
        f"- text_only_count={monitored_text_only_count}",
        f"- route_soft_count={monitored_route_soft_count}",
        f"- year_warning_count={monitored_year_warning_count}",
        "",
        "## decision",
        f"- go_hold_decision={decision}",
        f"- blocker_labels={blocker_labels}",
    ]
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(
        "[task242] "
        f"ready={len(ready_rows)} monitored={len(monitored_rows)} holding={len(holding_rows)} "
        f"escalate={len(escalate_rows)} reject={len(reject_rows)} carry_total={len(carry_forward_input_rows)} "
        f"coverage={coverage_review_count} join_blocker={join_blocker_count} decision={decision}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
