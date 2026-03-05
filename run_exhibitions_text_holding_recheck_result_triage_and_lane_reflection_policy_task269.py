from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY = "READY_FOR_WEEKLY_RUN_WITH_REFLECTED_LANES"
HOLD = "HOLD_FOR_LANE_REFLECTION_POLICY_REVIEW"


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="TASK269 Holding recheck result triage and lane reflection policy"
    )
    parser.add_argument(
        "--holding-bucket-csv",
        default="data/phase1_seed10/logs/holding_recheck_bucket_records_task268.csv",
    )
    parser.add_argument(
        "--holding-run-summary-json",
        default="data/phase1_seed10/logs/holding_recheck_run_summary_task268.json",
    )
    parser.add_argument(
        "--ready-input-csv",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_operation_week6_run_and_holding_recheck_scheduling_ready_input_task266.csv",
    )
    parser.add_argument(
        "--escalate-input-csv",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_operation_week6_run_and_holding_recheck_scheduling_escalate_input_task266.csv",
    )
    parser.add_argument(
        "--holding-original-csv",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_carry_forward_holding_set_task242.csv",
    )
    parser.add_argument(
        "--reject-set-csv",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_carry_forward_reject_set_task242.csv",
    )
    parser.add_argument("--output-dir", default="data/phase1_seed10/logs")
    parser.add_argument("--run-id", default="")
    return parser.parse_args()


def _with_reflection(
    row: dict[str, str],
    run_id: str,
    source: str,
    target_lane: str,
    monitoring_required: str,
    monitor_mode: str,
    reflection_reason: str,
) -> dict[str, str]:
    out = dict(row)
    out["task_run_id"] = run_id
    out["lane_reflection_source"] = source
    out["next_weekly_lane"] = target_lane
    out["monitoring_required"] = monitoring_required
    out["monitoring_mode"] = monitor_mode
    out["lane_reflection_reason"] = reflection_reason
    out["lane_reflection_policy"] = "TASK269_BUCKET_TO_LANE_POLICY_V1"
    return out


def main() -> int:
    args = parse_args()
    run_id = args.run_id.strip() or datetime.now(timezone.utc).strftime("task269_%Y%m%dT%H%M%SZ")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    bucket_rows = read_csv(Path(args.holding_bucket_csv))
    summary268 = read_json(Path(args.holding_run_summary_json), default={})
    ready_rows = read_csv(Path(args.ready_input_csv))
    escalate_rows = read_csv(Path(args.escalate_input_csv))
    holding_original_rows = read_csv(Path(args.holding_original_csv))
    reject_rows = read_csv(Path(args.reject_set_csv))

    bucket_counts = Counter((r.get("bucket") or "").strip() for r in bucket_rows)
    expected_bucket_counts = {
        "STABLE_WARNING_CANDIDATE": 10,
        "CONTINUE_HOLDING": 6,
        "ESCALATE_CANDIDATE": 1,
        "READY_CANDIDATE": 0,
        "REJECT_CANDIDATE": 0,
    }

    stable_rows = [r for r in bucket_rows if (r.get("bucket") or "").strip() == "STABLE_WARNING_CANDIDATE"]
    continue_holding_rows = [r for r in bucket_rows if (r.get("bucket") or "").strip() == "CONTINUE_HOLDING"]
    escalate_candidate_rows = [r for r in bucket_rows if (r.get("bucket") or "").strip() == "ESCALATE_CANDIDATE"]
    ready_candidate_rows = [r for r in bucket_rows if (r.get("bucket") or "").strip() == "READY_CANDIDATE"]
    reject_candidate_rows = [r for r in bucket_rows if (r.get("bucket") or "").strip() == "REJECT_CANDIDATE"]

    # Reflection policy
    # - STABLE_WARNING_CANDIDATE -> next weekly READY input as MONITORED_READY overlay
    # - CONTINUE_HOLDING -> remain in HOLDING
    # - ESCALATE_CANDIDATE -> next weekly ESCALATE lane
    # - READY/REJECT candidates in this run are zero
    ready_next_rows: list[dict[str, str]] = []
    for row in ready_rows:
        ready_next_rows.append(
            _with_reflection(
                row,
                run_id,
                "READY_BASELINE",
                "READY_LANE",
                "false",
                "none",
                "carry_forward_ready_baseline",
            )
        )

    for row in stable_rows:
        ready_next_rows.append(
            _with_reflection(
                row,
                run_id,
                "HOLDING_RECHECK_STABLE_WARNING",
                "READY_LANE",
                "true",
                "MONITORED_READY",
                "stable_warning_candidate_promoted_to_monitored_ready_for_next_weekly_input",
            )
        )

    escalate_next_rows: list[dict[str, str]] = []
    for row in escalate_rows:
        escalate_next_rows.append(
            _with_reflection(
                row,
                run_id,
                "ESCALATE_BASELINE",
                "ESCALATE_SEPARATE_LANE",
                "true",
                "ESCALATE_MONITORING",
                "carry_forward_escalate_baseline",
            )
        )
    for row in escalate_candidate_rows:
        escalate_next_rows.append(
            _with_reflection(
                row,
                run_id,
                "HOLDING_RECHECK_ESCALATE_CANDIDATE",
                "ESCALATE_SEPARATE_LANE",
                "true",
                "ESCALATE_MONITORING",
                "escalate_candidate_promoted_to_escalate_separate_lane_for_next_weekly_input",
            )
        )

    holding_remaining_rows: list[dict[str, str]] = []
    for row in continue_holding_rows:
        holding_remaining_rows.append(
            _with_reflection(
                row,
                run_id,
                "HOLDING_RECHECK_CONTINUE_HOLDING",
                "HOLDING_LANE",
                "true",
                "HOLDING_RECHECK_PENDING",
                "continue_holding_candidate_kept_in_holding_lane",
            )
        )

    # Boundary validations
    ready_sig = {row_signature(r) for r in ready_next_rows}
    esc_sig = {row_signature(r) for r in escalate_next_rows}
    hold_sig = {row_signature(r) for r in holding_remaining_rows}
    rej_sig = {row_signature(r) for r in reject_rows}
    ready_mk = {monitor_key(r) for r in ready_next_rows}
    esc_mk = {monitor_key(r) for r in escalate_next_rows}
    hold_mk = {monitor_key(r) for r in holding_remaining_rows}
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

    lane_counts_before = {
        "ready": len(ready_rows),
        "escalate": len(escalate_rows),
        "holding": len(holding_original_rows),
        "reject": len(reject_rows),
    }
    lane_counts_after = {
        "ready_next": len(ready_next_rows),
        "escalate_next": len(escalate_next_rows),
        "holding_remaining": len(holding_remaining_rows),
        "reject_next": len(reject_rows),
    }

    delta_rows = [
        {
            "lane": "READY",
            "before_count": lane_counts_before["ready"],
            "after_count": lane_counts_after["ready_next"],
            "delta": lane_counts_after["ready_next"] - lane_counts_before["ready"],
            "delta_reason": "baseline_ready + stable_warning_candidate_as_monitored_ready",
        },
        {
            "lane": "ESCALATE_SEPARATE",
            "before_count": lane_counts_before["escalate"],
            "after_count": lane_counts_after["escalate_next"],
            "delta": lane_counts_after["escalate_next"] - lane_counts_before["escalate"],
            "delta_reason": "baseline_escalate + escalate_candidate_from_holding_recheck",
        },
        {
            "lane": "HOLDING",
            "before_count": lane_counts_before["holding"],
            "after_count": lane_counts_after["holding_remaining"],
            "delta": lane_counts_after["holding_remaining"] - lane_counts_before["holding"],
            "delta_reason": "continue_holding_only_retained",
        },
        {
            "lane": "REJECT",
            "before_count": lane_counts_before["reject"],
            "after_count": lane_counts_after["reject_next"],
            "delta": lane_counts_after["reject_next"] - lane_counts_before["reject"],
            "delta_reason": "no reject candidate from holding recheck",
        },
    ]

    bucket_validation_ok = all(
        int(bucket_counts.get(k, 0)) == v for k, v in expected_bucket_counts.items()
    )
    precondition_ok = (
        str(summary268.get("go_hold_decision") or "").strip() == "READY_FOR_HOLDING_RECHECK_RESULT_TRIAGE"
    )
    counts_ok = (
        lane_counts_after["ready_next"] == 58
        and lane_counts_after["escalate_next"] == 5
        and lane_counts_after["holding_remaining"] == 6
        and lane_counts_after["reject_next"] == 0
    )
    policy_ok = (
        len(ready_candidate_rows) == 0
        and len(reject_candidate_rows) == 0
        and len(stable_rows) == 10
        and len(escalate_candidate_rows) == 1
        and len(continue_holding_rows) == 6
    )
    boundary_ok = boundary_breach_count == 0

    decision = READY if all([precondition_ok, bucket_validation_ok, counts_ok, policy_ok, boundary_ok]) else HOLD
    blocker_labels: list[str] = []
    if not precondition_ok:
        blocker_labels.append("TASK268_DECISION_NOT_READY_FOR_TRIAGE")
    if not bucket_validation_ok:
        blocker_labels.append("BUCKET_COUNT_MISMATCH")
    if not counts_ok:
        blocker_labels.append("LANE_COUNT_DELTA_MISMATCH")
    if not policy_ok:
        blocker_labels.append("POLICY_MAPPING_MISMATCH")
    if not boundary_ok:
        blocker_labels.append("BOUNDARY_OVERLAP_DETECTED")

    ready_out_path = output_dir / "weekly_ready_input_next_task269.csv"
    escalate_out_path = output_dir / "weekly_escalate_input_next_task269.csv"
    holding_out_path = output_dir / "holding_remaining_after_recheck_task269.csv"
    delta_out_path = output_dir / "recheck_lane_reflection_delta_task269.csv"
    boundary_out_path = output_dir / "recheck_lane_reflection_boundary_check_task269.csv"
    summary_out_path = output_dir / "recheck_lane_reflection_policy_summary_task269.json"
    manifest_out_path = output_dir / "recheck_lane_reflection_manifest_task269.json"
    md_out_path = output_dir / "recheck_lane_reflection_policy_task269.md"

    ready_fields = sorted({k for row in ready_next_rows for k in row.keys()}) if ready_next_rows else []
    escalate_fields = sorted({k for row in escalate_next_rows for k in row.keys()}) if escalate_next_rows else []
    holding_fields = sorted({k for row in holding_remaining_rows for k in row.keys()}) if holding_remaining_rows else []
    if not ready_fields:
        ready_fields = ["gallery_name_en", "fair_slug", "target_year", "source_url", "next_weekly_lane"]
    if not escalate_fields:
        escalate_fields = ["gallery_name_en", "fair_slug", "target_year", "source_url", "next_weekly_lane"]
    if not holding_fields:
        holding_fields = ["gallery_name_en", "fair_slug", "target_year", "source_url", "next_weekly_lane"]

    write_csv(ready_out_path, ready_next_rows, ready_fields)
    write_csv(escalate_out_path, escalate_next_rows, escalate_fields)
    write_csv(holding_out_path, holding_remaining_rows, holding_fields)
    write_csv(
        delta_out_path,
        delta_rows,
        ["lane", "before_count", "after_count", "delta", "delta_reason"],
    )
    write_csv(
        boundary_out_path,
        [{"check": k, "value": v, "expected": 0, "status": "PASS" if v == 0 else "FAIL"} for k, v in overlap.items()],
        ["check", "value", "expected", "status"],
    )

    by_fair = {
        "ready_next": dict(Counter(str(r.get("fair_slug") or "").strip() for r in ready_next_rows)),
        "escalate_next": dict(Counter(str(r.get("fair_slug") or "").strip() for r in escalate_next_rows)),
        "holding_remaining": dict(Counter(str(r.get("fair_slug") or "").strip() for r in holding_remaining_rows)),
    }
    by_gallery = {
        "ready_next": dict(
            Counter(
                f"{str(r.get('gallery_name_en') or '').strip()}|{str(r.get('fair_slug') or '').strip()}"
                for r in ready_next_rows
            )
        ),
        "escalate_next": dict(
            Counter(
                f"{str(r.get('gallery_name_en') or '').strip()}|{str(r.get('fair_slug') or '').strip()}"
                for r in escalate_next_rows
            )
        ),
        "holding_remaining": dict(
            Counter(
                f"{str(r.get('gallery_name_en') or '').strip()}|{str(r.get('fair_slug') or '').strip()}"
                for r in holding_remaining_rows
            )
        ),
    }

    summary = {
        "artifact": "recheck_lane_reflection_policy_summary_task269",
        "task": "TASK269",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "inputs": {
            "holding_bucket_csv": str(Path(args.holding_bucket_csv)),
            "holding_run_summary_json": str(Path(args.holding_run_summary_json)),
            "ready_input_csv": str(Path(args.ready_input_csv)),
            "escalate_input_csv": str(Path(args.escalate_input_csv)),
            "holding_original_csv": str(Path(args.holding_original_csv)),
            "reject_set_csv": str(Path(args.reject_set_csv)),
        },
        "bucket_counts": dict(bucket_counts),
        "expected_bucket_counts": expected_bucket_counts,
        "bucket_to_lane_policy": {
            "STABLE_WARNING_CANDIDATE": {
                "target_lane": "READY_LANE",
                "mode": "MONITORED_READY",
                "included_in_next_weekly_input": True,
                "monitoring_required": True,
                "monitoring_signals": ["persistence", "ratio_two_consecutive", "route_degradation"],
            },
            "CONTINUE_HOLDING": {
                "target_lane": "HOLDING_LANE",
                "included_in_next_weekly_input": False,
                "monitoring_required": True,
            },
            "ESCALATE_CANDIDATE": {
                "target_lane": "ESCALATE_SEPARATE_LANE",
                "included_in_next_weekly_input": True,
                "monitoring_required": True,
                "lane_variant": "same_escalate_separate_lane",
            },
            "READY_CANDIDATE": {
                "target_lane": "READY_LANE",
                "included_in_next_weekly_input": True,
                "monitoring_required": False,
            },
            "REJECT_CANDIDATE": {
                "target_lane": "REJECT_LANE",
                "included_in_next_weekly_input": False,
                "monitoring_required": False,
            },
        },
        "lane_counts_before": lane_counts_before,
        "lane_counts_after": lane_counts_after,
        "boundary_overlap_counts": overlap,
        "boundary_breach_count": boundary_breach_count,
        "by_fair": by_fair,
        "by_gallery": by_gallery,
        "decision": decision,
        "blocker_labels": blocker_labels,
        "next_task_recommendation": {
            "id": "TASK270",
            "title": "EXHIBITIONS-TEXT-WEEK7-WEEKLY-RUN-USING-REFLECTED-LANE-INPUTS",
            "ja": "Execute Week7 weekly run using reflected ready/escalate inputs while keeping holding isolated",
        },
    }
    write_json(summary_out_path, summary)

    manifest = {
        "artifact": "recheck_lane_reflection_manifest_task269",
        "task": "TASK269",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "outputs": {
            "weekly_ready_input_next_csv": str(ready_out_path),
            "weekly_escalate_input_next_csv": str(escalate_out_path),
            "holding_remaining_csv": str(holding_out_path),
            "delta_csv": str(delta_out_path),
            "boundary_check_csv": str(boundary_out_path),
            "summary_json": str(summary_out_path),
            "manifest_json": str(manifest_out_path),
            "policy_md": str(md_out_path),
        },
        "decision": decision,
    }
    write_json(manifest_out_path, manifest)

    md_lines = [
        "# TASK269 Holding Recheck Result Triage And Lane Reflection Policy",
        "",
        f"- run_id={run_id}",
        f"- decision={decision}",
        "",
        "## bucket_to_lane_policy",
        "- STABLE_WARNING_CANDIDATE -> READY_LANE (MONITORED_READY, include next weekly input)",
        "- CONTINUE_HOLDING -> HOLDING_LANE (remain isolated)",
        "- ESCALATE_CANDIDATE -> ESCALATE_SEPARATE_LANE (include next weekly input)",
        "- READY_CANDIDATE -> READY_LANE (none in this run)",
        "- REJECT_CANDIDATE -> REJECT_LANE (none in this run)",
        "",
        "## lane_count_delta",
        f"- READY: {lane_counts_before['ready']} -> {lane_counts_after['ready_next']}",
        f"- ESCALATE: {lane_counts_before['escalate']} -> {lane_counts_after['escalate_next']}",
        f"- HOLDING: {lane_counts_before['holding']} -> {lane_counts_after['holding_remaining']}",
        f"- REJECT: {lane_counts_before['reject']} -> {lane_counts_after['reject_next']}",
        "",
        "## boundary",
        f"- boundary_breach_count={boundary_breach_count}",
    ]
    md_out_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(
        "[task269] "
        f"run_id={run_id} "
        f"ready_next={lane_counts_after['ready_next']} "
        f"escalate_next={lane_counts_after['escalate_next']} "
        f"holding_remaining={lane_counts_after['holding_remaining']} "
        f"boundary={boundary_breach_count} decision={decision}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

