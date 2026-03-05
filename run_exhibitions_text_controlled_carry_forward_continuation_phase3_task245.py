from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY_FOR_PHASE_4 = "READY_FOR_CARRY_FORWARD_PHASE_4"
HOLD_MONITORED = "HOLD_FOR_MONITORED_POLICY_REVIEW"
HOLD_TEMPORAL_GAP = "HOLD_FOR_TEMPORAL_MONITORING_GAP_FIX"


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
    parser = argparse.ArgumentParser(description="TASK245 Exhibitions Text controlled carry-forward continuation phase 3")
    parser.add_argument(
        "--task243-summary",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_carry_forward_continuation_phase1_summary_task243.json",
    )
    parser.add_argument(
        "--task243-continuation-input-csv",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_carry_forward_continuation_input_task243.csv",
    )
    parser.add_argument(
        "--task242-holding-set-csv",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_carry_forward_holding_set_task242.csv",
    )
    parser.add_argument(
        "--task242-escalate-set-csv",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_carry_forward_escalate_set_task242.csv",
    )
    parser.add_argument(
        "--task242-reject-set-csv",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_carry_forward_reject_set_task242.csv",
    )
    parser.add_argument(
        "--previous-monitored-snapshot-csv",
        default="data/phase1_seed10/logs/exhibitions_text_controlled_carry_forward_continuation_phase2_monitored_snapshot_task244.csv",
    )
    parser.add_argument("--ratio-min-scope-total", type=int, default=3)
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


def continuation_scope_hash(rows: list[dict[str, str]]) -> str:
    payload = "\n".join(sorted({row_signature(row) for row in rows}))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest() if payload else ""


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


def route_rank(route_quality: str) -> int:
    value = str(route_quality or "").strip().lower()
    if value == "detail_candidate":
        return 1
    if value == "soft_suspicious":
        return 2
    if value in {"hard_suspicious", "hard_reject"}:
        return 3
    return 0


def main() -> int:
    args = parse_args()
    run_id = args.run_id.strip() or datetime.now(timezone.utc).strftime("task245_%Y%m%dT%H%M%SZ")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    summary243 = read_json(Path(args.task243_summary), default={})
    continuation_rows = read_csv(Path(args.task243_continuation_input_csv))
    holding_rows = read_csv(Path(args.task242_holding_set_csv))
    escalate_rows = read_csv(Path(args.task242_escalate_set_csv))
    reject_rows = read_csv(Path(args.task242_reject_set_csv))
    previous_snapshot_rows = read_csv(Path(args.previous_monitored_snapshot_csv))

    ready_rows = [r for r in continuation_rows if str(r.get("continuation_stream") or "").strip() == "READY"]
    monitored_rows = [r for r in continuation_rows if str(r.get("continuation_stream") or "").strip() == "MONITORED"]

    continuation_signatures = {row_signature(r) for r in continuation_rows}
    excluded_signatures = {row_signature(r) for r in (holding_rows + escalate_rows + reject_rows)}
    boundary_overlap = sorted(continuation_signatures & excluded_signatures)
    boundary_breach_count = len(boundary_overlap)

    scope_hash = continuation_scope_hash(continuation_rows)

    by_fair = defaultdict(Counter)
    by_gallery = defaultdict(Counter)
    for row in continuation_rows:
        fair = str(row.get("fair_slug") or "").strip()
        gallery = str(row.get("gallery_name_en") or "").strip()
        stream = str(row.get("continuation_stream") or "").strip()
        by_fair[fair][stream] += 1
        by_gallery[(gallery, fair)][stream] += 1

    total_by_scope = Counter(scope_key(r) for r in continuation_rows)
    text_only_by_scope = Counter(
        scope_key(r)
        for r in monitored_rows
        if str(r.get("join_status") or "").strip() == "TEXT_ONLY"
        or str(r.get("join_basis") or "").strip() == "no_image_candidate"
    )

    prev_snapshot_map = {str(r.get("monitor_key") or "").strip(): r for r in previous_snapshot_rows}
    prev_proxy_map = {monitor_key(r): r for r in monitored_rows}
    temporal_source = "snapshot" if previous_snapshot_rows else ("task243_proxy" if prev_proxy_map else "none")

    monitored_snapshot_rows: list[dict[str, Any]] = []
    escalate_now_count = 0
    monitored_reason_counts = Counter()
    monitored_detail_for_summary: list[dict[str, Any]] = []
    temporal_gap_count = 0

    for row in monitored_rows:
        key = monitor_key(row)
        skey = scope_key(row)
        fair = str(row.get("fair_slug") or "").strip()
        gallery = str(row.get("gallery_name_en") or "").strip()
        source = str(row.get("source_url") or "").strip()
        route_quality = str(row.get("route_quality_label") or "").strip()
        year_quality = str(row.get("year_quality_label") or "").strip()

        is_text_only = (
            str(row.get("join_status") or "").strip() == "TEXT_ONLY"
            or str(row.get("join_basis") or "").strip() == "no_image_candidate"
        )
        is_route_soft = route_quality == "soft_suspicious"
        is_year_warning = year_quality != "pass"

        causes: list[str] = []
        if is_text_only:
            causes.append("TEXT_ONLY")
        if is_route_soft:
            causes.append("ROUTE_SOFT")
        if is_year_warning:
            causes.append("YEAR_WARNING")
        warning_primary = "+".join(causes) if causes else "OTHER_WARNING"
        monitored_reason_counts[warning_primary] += 1

        prev = prev_snapshot_map.get(key)
        prev_proxy = prev_proxy_map.get(key)

        if prev:
            prev_persist = int(prev.get("persistence_count", 0) or 0)
            prev_ratio_flag = str(prev.get("ratio_threshold_exceeded") or "").strip().lower() == "true"
            prev_route_quality = str(prev.get("route_quality_label") or "").strip()
            temporal_position = "from_snapshot"
        elif prev_proxy:
            prev_persist = 1
            prev_ratio_flag = False
            prev_route_quality = str(prev_proxy.get("route_quality_label") or "").strip()
            temporal_position = "from_task243_proxy"
        else:
            prev_persist = 0
            prev_ratio_flag = False
            prev_route_quality = ""
            temporal_position = "new_monitored_observation"
            temporal_gap_count += 1

        persistence_count = prev_persist + 1
        scope_total = int(total_by_scope.get(skey, 0))
        scope_text_only = int(text_only_by_scope.get(skey, 0))
        text_only_ratio = (scope_text_only / scope_total) if scope_total > 0 else 0.0
        ratio_evaluable = scope_total >= int(args.ratio_min_scope_total)
        ratio_threshold_exceeded = ratio_evaluable and text_only_ratio > 0.6
        ratio_two_consecutive = ratio_threshold_exceeded and prev_ratio_flag
        persist_three = persistence_count >= 3
        route_degradation = route_rank(route_quality) > route_rank(prev_route_quality) if prev_route_quality else False
        escalate_now = bool(persist_three or ratio_two_consecutive or route_degradation)
        if escalate_now:
            escalate_now_count += 1

        monitored_snapshot_rows.append(
            {
                "monitor_key": key,
                "scope_key": skey,
                "fair_slug": fair,
                "gallery_name_en": gallery,
                "source_url": source,
                "warning_primary": warning_primary,
                "warning_causes": "|".join(causes),
                "route_quality_label": route_quality,
                "year_quality_label": year_quality,
                "persistence_count": persistence_count,
                "scope_total_count": scope_total,
                "scope_text_only_count": scope_text_only,
                "text_only_ratio": round(text_only_ratio, 6),
                "ratio_evaluable": str(ratio_evaluable).lower(),
                "ratio_threshold_exceeded": str(ratio_threshold_exceeded).lower(),
                "ratio_two_consecutive": str(ratio_two_consecutive).lower(),
                "previous_route_quality": prev_route_quality,
                "route_degradation_flag": str(route_degradation).lower(),
                "escalate_now": str(escalate_now).lower(),
                "temporal_position": temporal_position,
                "temporal_source": temporal_source,
                "run_id": run_id,
                "scope_hash": scope_hash,
            }
        )

        monitored_detail_for_summary.append(
            {
                "gallery_name_en": gallery,
                "fair_slug": fair,
                "source_url": source,
                "warning_primary": warning_primary,
                "current_status": "MONITORED",
                "persistence_count": persistence_count,
                "ratio_evaluable": ratio_evaluable,
                "text_only_ratio": round(text_only_ratio, 6),
                "route_degradation_flag": route_degradation,
                "escalate_now": escalate_now,
            }
        )

    integrity = summary243.get("integrity_checks", {})
    coverage_review_count = int(integrity.get("coverage_review_count", 0))
    reject_count = max(len(reject_rows), int(integrity.get("reject_candidate_count", 0)))
    join_blocker_count = int(integrity.get("join_blocker_count", 0))
    escalate_set_count = len(escalate_rows)

    blocker_labels: list[str] = []
    if coverage_review_count > 0:
        blocker_labels.append("COVERAGE_REVIEW_PRESENT")
    if reject_count > 0:
        blocker_labels.append("REJECT_SET_PRESENT")
    if join_blocker_count > 0:
        blocker_labels.append("JOIN_BLOCKER_PRESENT")
    if escalate_set_count > 0:
        blocker_labels.append("ESCALATE_SET_PRESENT")
    if boundary_breach_count > 0:
        blocker_labels.append("BOUNDARY_MIXING_DETECTED")

    label_alignment_note = {
        "task244_label_seen": "READY_FOR_CARRY_FORWARD_PHASE_2",
        "task245_handling": "treated as phase progression label drift; processing continues as Phase 3 by content",
    }

    if blocker_labels:
        decision = HOLD_TEMPORAL_GAP
    elif escalate_now_count > 0:
        decision = HOLD_MONITORED
    elif temporal_source == "none":
        decision = HOLD_TEMPORAL_GAP
        blocker_labels.append("TEMPORAL_BASELINE_MISSING")
    else:
        decision = READY_FOR_PHASE_4

    summary = {
        "artifact": "exhibitions_text_controlled_carry_forward_continuation_phase3_summary",
        "task": "TASK245",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "label_alignment_note": label_alignment_note,
        "inputs": {
            "task243_summary": str(Path(args.task243_summary)),
            "task243_continuation_input_csv": str(Path(args.task243_continuation_input_csv)),
            "task242_holding_set_csv": str(Path(args.task242_holding_set_csv)),
            "task242_escalate_set_csv": str(Path(args.task242_escalate_set_csv)),
            "task242_reject_set_csv": str(Path(args.task242_reject_set_csv)),
            "previous_monitored_snapshot_csv": str(Path(args.previous_monitored_snapshot_csv)),
        },
        "continuation_phase3_input": {
            "continuation_input_total": len(continuation_rows),
            "ready_count": len(ready_rows),
            "monitored_count": len(monitored_rows),
            "holding_excluded_count": len(holding_rows),
            "escalate_excluded_count": len(escalate_rows),
            "reject_excluded_count": len(reject_rows),
            "scope_hash": scope_hash,
        },
        "monitored_temporal_review": {
            "monitored_rows": monitored_detail_for_summary,
            "monitoring_unit": "fair_slug + gallery_name_en + source_url",
            "stable_text_only_ratio_unit": "fair_slug + gallery_name_en",
            "route_degradation_unit": "same monitor_key across runs",
            "temporal_source": temporal_source,
            "temporal_gap_count": temporal_gap_count,
            "escalate_now_count": escalate_now_count,
            "warning_primary_counts": dict(monitored_reason_counts),
        },
        "continuation_phase3_policy": {
            "ready_continuable_when": "coverage_review=0 AND reject=0 AND join_blocker=0 AND boundary_breach=0",
            "monitored_continuable_when": "escalate_now_count=0 and monitoring rules remain active",
            "escalate_transition_when": [
                "persistence_count >= 3",
                "ratio_threshold_exceeded for two consecutive monitored snapshots",
                "route_degradation_flag=true",
            ],
            "hold_for_monitored_policy_review_when": "escalate_now_count > 0",
            "hold_for_temporal_monitoring_gap_fix_when": "temporal_source=none or boundary/integrity blocker present",
            "continuation_close_condition": "READY+MONITORED boundary stable and temporal monitoring outputs generated",
        },
        "aggregates": {
            "by_fair_counts": {k: dict(v) for k, v in by_fair.items()},
            "by_gallery_counts": {f"{k[0]}|{k[1]}": dict(v) for k, v in by_gallery.items()},
            "monitored_primary_patterns": {
                "text_only_count": sum(1 for r in monitored_rows if str(r.get("join_status") or "").strip() == "TEXT_ONLY" or str(r.get("join_basis") or "").strip() == "no_image_candidate"),
                "route_soft_count": sum(1 for r in monitored_rows if str(r.get("route_quality_label") or "").strip() == "soft_suspicious"),
                "year_warning_count": sum(1 for r in monitored_rows if str(r.get("year_quality_label") or "").strip() != "pass"),
            },
            "boundary_breach_count": boundary_breach_count,
        },
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
            "id": "TASK246",
            "title": "EXHIBITIONS-TEXT-CONTROLLED-CARRY-FORWARD-CONTINUATION-PHASE-4",
            "ja": "Continue carry-forward with temporal monitoring history and monitored trend recheck",
        },
    }

    summary_path = output_dir / "exhibitions_text_controlled_carry_forward_continuation_phase3_summary_task245.json"
    table_path = output_dir / "exhibitions_text_controlled_carry_forward_continuation_phase3_table_task245.csv"
    by_fair_path = output_dir / "exhibitions_text_controlled_carry_forward_continuation_phase3_by_fair_task245.csv"
    input_set_path = output_dir / "exhibitions_text_controlled_carry_forward_continuation_phase3_input_task245.csv"
    monitored_snapshot_path = output_dir / "exhibitions_text_controlled_carry_forward_continuation_phase3_monitored_snapshot_task245.csv"
    manifest_path = output_dir / "exhibitions_text_controlled_carry_forward_continuation_phase3_manifest_task245.json"
    report_path = output_dir / "exhibitions_text_controlled_carry_forward_continuation_phase3_task245.md"

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
        "continuation_stream",
        "continuation_reason",
    ]
    write_csv(input_set_path, continuation_rows, fields)

    table_rows: list[dict[str, Any]] = []
    for (gallery, fair), counts in sorted(by_gallery.items(), key=lambda x: (x[0][1], x[0][0])):
        table_rows.append(
            {
                "gallery_name_en": gallery,
                "fair_slug": fair,
                "READY": int(counts.get("READY", 0)),
                "MONITORED": int(counts.get("MONITORED", 0)),
                "TOTAL": int(counts.get("READY", 0) + counts.get("MONITORED", 0)),
            }
        )
    write_csv(table_path, table_rows, ["gallery_name_en", "fair_slug", "READY", "MONITORED", "TOTAL"])

    fair_rows: list[dict[str, Any]] = []
    for fair, counts in sorted(by_fair.items(), key=lambda x: x[0]):
        fair_rows.append(
            {
                "fair_slug": fair,
                "READY": int(counts.get("READY", 0)),
                "MONITORED": int(counts.get("MONITORED", 0)),
                "TOTAL": int(counts.get("READY", 0) + counts.get("MONITORED", 0)),
            }
        )
    write_csv(by_fair_path, fair_rows, ["fair_slug", "READY", "MONITORED", "TOTAL"])

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
        "persistence_count",
        "scope_total_count",
        "scope_text_only_count",
        "text_only_ratio",
        "ratio_evaluable",
        "ratio_threshold_exceeded",
        "ratio_two_consecutive",
        "previous_route_quality",
        "route_degradation_flag",
        "escalate_now",
        "temporal_position",
        "temporal_source",
        "run_id",
        "scope_hash",
    ]
    write_csv(monitored_snapshot_path, monitored_snapshot_rows, snapshot_fields)

    write_json(summary_path, summary)
    manifest = {
        "artifact": "exhibitions_text_controlled_carry_forward_continuation_phase3_manifest",
        "task": "TASK245",
        "run_id": run_id,
        "inputs": summary["inputs"],
        "outputs": {
            "summary_json": str(summary_path),
            "table_csv": str(table_path),
            "by_fair_csv": str(by_fair_path),
            "continuation_input_csv": str(input_set_path),
            "monitored_snapshot_csv": str(monitored_snapshot_path),
            "report_md": str(report_path),
            "manifest_json": str(manifest_path),
        },
        "continuation_scope_hash": scope_hash,
        "integrity_checks": summary["integrity_checks"],
    }
    write_json(manifest_path, manifest)

    report_lines = [
        "# TASK245 Exhibitions Text Controlled Carry-Forward Continuation Phase 3",
        "",
        "## label_alignment_note",
        "- TASK244 decision label remained READY_FOR_CARRY_FORWARD_PHASE_2.",
        "- TASK245 proceeds as Phase 3 by content continuity and emits Phase 4 readiness label when passed.",
        "",
        "## continuation_input",
        f"- continuation_input_total={len(continuation_rows)}",
        f"- ready_count={len(ready_rows)}",
        f"- monitored_count={len(monitored_rows)}",
        f"- holding_excluded_count={len(holding_rows)}",
        f"- boundary_breach_count={boundary_breach_count}",
        "",
        "## monitored_temporal_status",
        f"- temporal_source={temporal_source}",
        f"- temporal_gap_count={temporal_gap_count}",
        f"- monitored_warning_primary_counts={dict(monitored_reason_counts)}",
        f"- escalate_now_count={escalate_now_count}",
        "",
        "## integrity",
        f"- coverage_review_count={coverage_review_count}",
        f"- reject_candidate_count={reject_count}",
        f"- join_blocker_count={join_blocker_count}",
        f"- escalate_set_count={escalate_set_count}",
        "",
        "## decision",
        f"- go_hold_decision={decision}",
        f"- blocker_labels={blocker_labels}",
    ]
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(
        "[task245] "
        f"total={len(continuation_rows)} ready={len(ready_rows)} monitored={len(monitored_rows)} "
        f"holding_excluded={len(holding_rows)} boundary_breach={boundary_breach_count} "
        f"escalate_now={escalate_now_count} temporal_source={temporal_source} decision={decision}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
