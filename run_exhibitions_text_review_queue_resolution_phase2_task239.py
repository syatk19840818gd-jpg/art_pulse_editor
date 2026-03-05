from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

STABLE_TEXT_ONLY_WARNING = "STABLE_TEXT_ONLY_WARNING"
ROUTE_SOFT_REVIEW_KEEP = "ROUTE_SOFT_REVIEW_KEEP"
YEAR_REVIEW_KEEP = "YEAR_REVIEW_KEEP"
RESOLUTION_CANDIDATE = "RESOLUTION_CANDIDATE"
ESCALATE_CANDIDATE = "ESCALATE_CANDIDATE"

ROUTE_SOFT_STABLE_WARNING = "ROUTE_SOFT_STABLE_WARNING"
ROUTE_SOFT_NEEDS_MANUAL = "ROUTE_SOFT_NEEDS_MANUAL"
ROUTE_SOFT_INPUT_EXCLUDE_CANDIDATE = "ROUTE_SOFT_INPUT_EXCLUDE_CANDIDATE"
YEAR_INPUT_EXCLUDE_CANDIDATE = "YEAR_INPUT_EXCLUDE_CANDIDATE"
YEAR_STABLE_WARNING = "YEAR_STABLE_WARNING"


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
    parser = argparse.ArgumentParser(description="TASK239 Exhibitions Text controlled review queue resolution phase 2")
    parser.add_argument(
        "--task238-summary",
        default="data/phase1_seed10/logs/exhibitions_text_review_queue_resolution_phase1_summary_task238.json",
    )
    parser.add_argument(
        "--task238-active-review-csv",
        default="data/phase1_seed10/logs/exhibitions_text_scope_review_phase_review_queue_task238.csv",
    )
    parser.add_argument(
        "--task238-stable-warning-csv",
        default="data/phase1_seed10/logs/exhibitions_text_scope_review_phase_stable_warning_task238.csv",
    )
    parser.add_argument(
        "--task238-resolution-candidates-csv",
        default="data/phase1_seed10/logs/exhibitions_text_scope_review_phase_resolution_candidates_task238.csv",
    )
    parser.add_argument(
        "--task237-clean-csv",
        default="data/phase1_seed10/logs/exhibitions_text_scope_review_phase_clean_pass_candidates_task237.csv",
    )
    parser.add_argument(
        "--task236-coverage-review-csv",
        default="data/phase1_seed10/logs/exhibitions_text_scope_review_gate_coverage_review_task236.csv",
    )
    parser.add_argument(
        "--task237-summary",
        default="data/phase1_seed10/logs/exhibitions_text_scope_review_phase_summary_task237.json",
    )
    parser.add_argument(
        "--output-dir",
        default="data/phase1_seed10/logs",
    )
    parser.add_argument("--run-id", default="")
    return parser.parse_args()


def _path_tokens(url: str) -> set[str]:
    path = (urlparse(str(url or "").strip()).path or "").lower()
    return {token for token in re.split(r"[^a-z0-9]+", path) if token}


def _is_route_soft_input_exclude_candidate(
    *,
    source_url: str,
    join_status: str,
    join_basis: str,
    clean_in_scope: int,
) -> bool:
    tokens = _path_tokens(source_url)
    generic_route_signal = bool({"past", "upcoming", "archive"} & tokens)
    if not generic_route_signal:
        return False
    # generic exclusions only for listing-like text-only entries with existing clean detail support
    listing_like = (
        "location" in tokens
        or "exhibitions" in tokens
        or "archive" in tokens
        or "past" in tokens
        or "upcoming" in tokens
    )
    return (
        join_status == "TEXT_ONLY"
        and join_basis == "no_image_candidate"
        and listing_like
        and clean_in_scope > 0
    )


def _is_route_soft_stable_warning(
    *,
    source_url: str,
    join_status: str,
) -> bool:
    tokens = _path_tokens(source_url)
    # detail-like yearly path that still joins by source_url can stay as stable warning
    has_year_token = any(tok.isdigit() and len(tok) == 4 for tok in tokens)
    return join_status == "JOIN_BY_SOURCE_URL" and has_year_token and ("past" in tokens or "archive" in tokens)


def _is_year_input_exclude_candidate(
    *,
    source_url: str,
    join_status: str,
    join_basis: str,
) -> bool:
    tokens = _path_tokens(source_url)
    # generic listing/project-like pages with no image join and soft year risk
    return (
        join_status == "TEXT_ONLY"
        and join_basis == "no_image_candidate"
        and ("projects" in tokens or "project" in tokens or "archive" in tokens)
    )


def classify_active_review_row(
    *,
    row: dict[str, str],
    clean_counts_by_scope: dict[tuple[str, str], int],
) -> tuple[str, str]:
    label = str(row.get("resolution_label") or "").strip()
    source_url = str(row.get("source_url") or "").strip()
    join_status = str(row.get("join_status") or "").strip()
    join_basis = str(row.get("join_basis") or "").strip()
    fair = str(row.get("fair_slug") or "").strip()
    gallery = str(row.get("gallery_name_en") or "").strip()
    clean_in_scope = int(clean_counts_by_scope.get((gallery, fair), 0))

    if label == ROUTE_SOFT_REVIEW_KEEP:
        if _is_route_soft_input_exclude_candidate(
            source_url=source_url,
            join_status=join_status,
            join_basis=join_basis,
            clean_in_scope=clean_in_scope,
        ):
            return ROUTE_SOFT_INPUT_EXCLUDE_CANDIDATE, "generic_soft_route_listing_exclude_candidate"
        if _is_route_soft_stable_warning(source_url=source_url, join_status=join_status):
            return ROUTE_SOFT_STABLE_WARNING, "soft_route_with_join_and_year_token"
        return ROUTE_SOFT_NEEDS_MANUAL, "soft_route_requires_manual_review"

    if label == YEAR_REVIEW_KEEP:
        if _is_year_input_exclude_candidate(source_url=source_url, join_status=join_status, join_basis=join_basis):
            return YEAR_INPUT_EXCLUDE_CANDIDATE, "generic_year_soft_projects_exclude_candidate"
        return YEAR_STABLE_WARNING, "year_soft_warning_kept"

    if label == STABLE_TEXT_ONLY_WARNING:
        return STABLE_TEXT_ONLY_WARNING, "stable_text_only_warning_kept"

    return ESCALATE_CANDIDATE, "unexpected_phase1_label"


def main() -> int:
    args = parse_args()
    run_id = args.run_id.strip() or datetime.now(timezone.utc).strftime("task239_%Y%m%dT%H%M%SZ")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    summary238 = read_json(Path(args.task238_summary), default={})
    summary237 = read_json(Path(args.task237_summary), default={})

    active_rows = read_csv(Path(args.task238_active_review_csv))
    _stable_warning_rows_phase1 = read_csv(Path(args.task238_stable_warning_csv))
    resolution_rows_phase1 = read_csv(Path(args.task238_resolution_candidates_csv))
    clean_rows = read_csv(Path(args.task237_clean_csv))
    coverage_rows = read_csv(Path(args.task236_coverage_review_csv))

    clean_counts_by_scope: dict[tuple[str, str], int] = Counter(
        (str(r.get("gallery_name_en") or "").strip(), str(r.get("fair_slug") or "").strip()) for r in clean_rows
    )

    reclassified_active_rows: list[dict[str, Any]] = []
    active_review_after_rows: list[dict[str, Any]] = []
    stable_warning_after_rows: list[dict[str, Any]] = []
    resolution_after_rows: list[dict[str, Any]] = []
    escalate_after_rows: list[dict[str, Any]] = []

    phase2_counts = Counter()
    by_gallery_phase2 = defaultdict(Counter)
    by_fair_phase2 = defaultdict(Counter)
    route_soft_patterns = Counter()
    year_patterns = Counter()

    for row in active_rows:
        new_label, reason = classify_active_review_row(row=row, clean_counts_by_scope=clean_counts_by_scope)
        out = dict(row)
        out["phase2_label"] = new_label
        out["phase2_reason"] = reason
        reclassified_active_rows.append(out)

        gallery = str(row.get("gallery_name_en") or "").strip()
        fair = str(row.get("fair_slug") or "").strip()
        phase2_counts[new_label] += 1
        by_gallery_phase2[(gallery, fair)][new_label] += 1
        by_fair_phase2[fair][new_label] += 1

        if new_label in {ROUTE_SOFT_INPUT_EXCLUDE_CANDIDATE, YEAR_INPUT_EXCLUDE_CANDIDATE}:
            resolution_after_rows.append(out)
        elif new_label in {ROUTE_SOFT_STABLE_WARNING, YEAR_STABLE_WARNING, STABLE_TEXT_ONLY_WARNING}:
            stable_warning_after_rows.append(out)
        elif new_label == ROUTE_SOFT_NEEDS_MANUAL:
            active_review_after_rows.append(out)
        elif new_label == ESCALATE_CANDIDATE:
            escalate_after_rows.append(out)
            active_review_after_rows.append(out)

        if new_label in {ROUTE_SOFT_INPUT_EXCLUDE_CANDIDATE, ROUTE_SOFT_STABLE_WARNING, ROUTE_SOFT_NEEDS_MANUAL}:
            src = str(row.get("source_url") or "").lower()
            if "/past" in src:
                route_soft_patterns["/past"] += 1
            elif "/upcoming" in src:
                route_soft_patterns["/upcoming"] += 1
            elif "/archive" in src:
                route_soft_patterns["/archive"] += 1
            else:
                route_soft_patterns["other"] += 1

        if new_label in {YEAR_INPUT_EXCLUDE_CANDIDATE, YEAR_STABLE_WARNING}:
            year_patterns[str(row.get("source_url") or "")] += 1

    # carry forward phase1 stable/resolution as-is and append phase2 outputs
    resolution_after_rows.extend(resolution_rows_phase1)

    before_active_count = len(active_rows)
    after_active_count = len(active_review_after_rows)
    phase1_label_counts = (
        summary238.get("review_queue_reclassification", {}).get("resolution_label_counts", {})
    )
    before_stable_count = int(phase1_label_counts.get(STABLE_TEXT_ONLY_WARNING, 0))
    after_stable_count = len(stable_warning_after_rows)
    before_resolution_count = int(phase1_label_counts.get(RESOLUTION_CANDIDATE, 0))
    after_resolution_count = before_resolution_count + int(
        phase2_counts.get(ROUTE_SOFT_INPUT_EXCLUDE_CANDIDATE, 0)
        + phase2_counts.get(YEAR_INPUT_EXCLUDE_CANDIDATE, 0)
    )
    clean_count = int(summary237.get("counts", {}).get("clean_pass_candidate_count", 0))

    coverage_count = len(coverage_rows)
    reject_count = int(summary237.get("counts", {}).get("reject_candidate_count", 0))
    join_blocker_count = int(summary237.get("counts", {}).get("join_blocker_count", 0))

    go_hold = "READY_FOR_REVIEW_QUEUE_PHASE_3"
    if join_blocker_count > 0 or reject_count > 0:
        go_hold = "HOLD_FOR_INPUT_PATTERN_REVIEW"
    elif int(phase2_counts.get(ESCALATE_CANDIDATE, 0)) > 0:
        go_hold = "HOLD_FOR_RULE_TUNING"

    summary = {
        "artifact": "exhibitions_text_review_queue_resolution_phase2_summary",
        "task": "TASK239",
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "inputs": {
            "task238_summary": str(Path(args.task238_summary)),
            "task238_active_review_csv": str(Path(args.task238_active_review_csv)),
            "task238_stable_warning_csv": str(Path(args.task238_stable_warning_csv)),
            "task238_resolution_candidates_csv": str(Path(args.task238_resolution_candidates_csv)),
            "task237_clean_csv": str(Path(args.task237_clean_csv)),
            "task237_summary": str(Path(args.task237_summary)),
            "task236_coverage_review_csv": str(Path(args.task236_coverage_review_csv)),
        },
        "phase2_target_inventory": {
            "input_active_review_count": before_active_count,
            "input_active_review_rows": [
                {
                    "fair_slug": str(r.get("fair_slug") or ""),
                    "gallery_name_en": str(r.get("gallery_name_en") or ""),
                    "source_url": str(r.get("source_url") or ""),
                    "resolution_label_phase1": str(r.get("resolution_label") or ""),
                    "route_quality_label": str(r.get("route_quality_label") or ""),
                    "year_quality_label": str(r.get("year_quality_label") or ""),
                }
                for r in active_rows
            ],
        },
        "route_soft_decomposition": {
            "ROUTE_SOFT_STABLE_WARNING": int(phase2_counts.get(ROUTE_SOFT_STABLE_WARNING, 0)),
            "ROUTE_SOFT_NEEDS_MANUAL": int(phase2_counts.get(ROUTE_SOFT_NEEDS_MANUAL, 0)),
            "ROUTE_SOFT_INPUT_EXCLUDE_CANDIDATE": int(phase2_counts.get(ROUTE_SOFT_INPUT_EXCLUDE_CANDIDATE, 0)),
            "route_soft_patterns": dict(route_soft_patterns),
        },
        "year_review_handling": {
            "YEAR_INPUT_EXCLUDE_CANDIDATE": int(phase2_counts.get(YEAR_INPUT_EXCLUDE_CANDIDATE, 0)),
            "YEAR_STABLE_WARNING": int(phase2_counts.get(YEAR_STABLE_WARNING, 0)),
            "year_sources": [{"source_url": k, "count": v} for k, v in year_patterns.items()],
            "policy": "safe-side generic exclusion candidate for project/archive-like text-only soft-year pages",
        },
        "text_only_warning_monitoring_rule": {
            "rule_1": "escalate when same fair+gallery stays in STABLE_TEXT_ONLY_WARNING for >=3 consecutive controlled runs",
            "rule_2": "escalate when (stable_text_only_warning_count / (stable_text_only_warning_count + clean_pass_count_in_scope)) > 0.6 for two consecutive runs",
            "rule_3": "escalate when route quality drifts from detail_candidate to soft/hard suspicious in subsequent run",
            "phase2_escalation_now_count": int(phase2_counts.get(ESCALATE_CANDIDATE, 0)),
        },
        "phase2_compression_rule": {
            "generic_rule": (
                "for active ROUTE_SOFT rows, classify as INPUT_EXCLUDE_CANDIDATE when route token is in "
                "{past,upcoming,archive}, join is TEXT_ONLY/no_image_candidate, and scope has clean support; "
                "for active YEAR_REVIEW rows on project/archive-like text-only routes, classify as YEAR_INPUT_EXCLUDE_CANDIDATE"
            ),
            "join_contract_changed": False,
            "year_filter_redesigned": False,
            "quality_gate_redesigned": False,
            "domain_specific_if_used": False,
        },
        "before_after": {
            "clean_pass_candidate_count_before": clean_count,
            "clean_pass_candidate_count_after": clean_count,
            "active_review_queue_count_before": before_active_count,
            "active_review_queue_count_after": after_active_count,
            "stable_warning_count_before": before_stable_count,
            "stable_warning_count_after": after_stable_count,
            "resolution_candidate_count_before": before_resolution_count,
            "resolution_candidate_count_after": after_resolution_count,
            "phase2_label_counts": dict(phase2_counts),
            "by_fair_phase2_counts": {k: dict(v) for k, v in by_fair_phase2.items()},
        },
        "integrity_checks": {
            "coverage_review_count": coverage_count,
            "reject_candidate_count": reject_count,
            "join_blocker_count": join_blocker_count,
            "proposal_only": True,
            "formal_untouched": True,
        },
        "go_hold_decision": go_hold,
        "next_task_recommendation": {
            "id": "TASK240",
            "title": "EXHIBITIONS-TEXT-CONTROLLED-REVIEW-QUEUE-RESOLUTION-PHASE-3",
            "ja": "Phase 3 for remaining manual route-soft review and escalation policy application",
        },
    }

    summary_path = Path(args.output_dir) / "exhibitions_text_review_queue_resolution_phase2_summary_task239.json"
    table_path = Path(args.output_dir) / "exhibitions_text_review_queue_resolution_phase2_table_task239.csv"
    records_path = Path(args.output_dir) / "exhibitions_text_review_queue_resolution_phase2_records_task239.csv"
    active_path = Path(args.output_dir) / "exhibitions_text_scope_review_phase_review_queue_task239.csv"
    stable_path = Path(args.output_dir) / "exhibitions_text_scope_review_phase_stable_warning_task239.csv"
    resolution_path = Path(args.output_dir) / "exhibitions_text_scope_review_phase_resolution_candidates_task239.csv"
    escalate_path = Path(args.output_dir) / "exhibitions_text_scope_review_phase_escalate_candidates_task239.csv"
    manifest_path = Path(args.output_dir) / "exhibitions_text_review_queue_resolution_phase2_manifest_task239.json"
    report_path = Path(args.output_dir) / "exhibitions_text_review_queue_resolution_phase2_task239.md"

    fieldnames = [
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
    ]
    write_csv(records_path, reclassified_active_rows, fieldnames)
    write_csv(active_path, active_review_after_rows, fieldnames)
    write_csv(stable_path, stable_warning_after_rows, fieldnames)
    write_csv(resolution_path, resolution_after_rows, fieldnames)
    write_csv(escalate_path, escalate_after_rows, fieldnames)

    table_rows: list[dict[str, Any]] = []
    for (gallery, fair), counts in sorted(by_gallery_phase2.items(), key=lambda x: (x[0][1], x[0][0])):
        table_rows.append(
            {
                "gallery_name_en": gallery,
                "fair_slug": fair,
                ROUTE_SOFT_STABLE_WARNING: int(counts.get(ROUTE_SOFT_STABLE_WARNING, 0)),
                ROUTE_SOFT_NEEDS_MANUAL: int(counts.get(ROUTE_SOFT_NEEDS_MANUAL, 0)),
                ROUTE_SOFT_INPUT_EXCLUDE_CANDIDATE: int(counts.get(ROUTE_SOFT_INPUT_EXCLUDE_CANDIDATE, 0)),
                YEAR_INPUT_EXCLUDE_CANDIDATE: int(counts.get(YEAR_INPUT_EXCLUDE_CANDIDATE, 0)),
                YEAR_STABLE_WARNING: int(counts.get(YEAR_STABLE_WARNING, 0)),
                STABLE_TEXT_ONLY_WARNING: int(counts.get(STABLE_TEXT_ONLY_WARNING, 0)),
                ESCALATE_CANDIDATE: int(counts.get(ESCALATE_CANDIDATE, 0)),
            }
        )
    write_csv(
        table_path,
        table_rows,
        [
            "gallery_name_en",
            "fair_slug",
            ROUTE_SOFT_STABLE_WARNING,
            ROUTE_SOFT_NEEDS_MANUAL,
            ROUTE_SOFT_INPUT_EXCLUDE_CANDIDATE,
            YEAR_INPUT_EXCLUDE_CANDIDATE,
            YEAR_STABLE_WARNING,
            STABLE_TEXT_ONLY_WARNING,
            ESCALATE_CANDIDATE,
        ],
    )

    write_json(summary_path, summary)
    manifest = {
        "artifact": "exhibitions_text_review_queue_resolution_phase2_manifest",
        "task": "TASK239",
        "run_id": run_id,
        "inputs": summary["inputs"],
        "outputs": {
            "summary_json": str(summary_path),
            "table_csv": str(table_path),
            "records_csv": str(records_path),
            "active_review_queue_csv": str(active_path),
            "stable_warning_csv": str(stable_path),
            "resolution_candidates_csv": str(resolution_path),
            "escalate_candidates_csv": str(escalate_path),
            "report_md": str(report_path),
            "manifest_json": str(manifest_path),
        },
        "integrity_checks": summary["integrity_checks"],
        "policies": {
            "proposal_only": True,
            "formal_untouched": True,
            "adoption_executed": False,
            "rollback_executed": False,
            "join_contract_changed": False,
            "anti_mixing_enforced": True,
            "coverage_canonicalization_scope_only": True,
            "coverage_canonicalization_not_used_for_record_identity": True,
        },
    }
    write_json(manifest_path, manifest)

    report_lines = [
        "# TASK239 Exhibitions Text Controlled Review Queue Resolution Phase 2",
        "",
        "## phase2_target",
        f"- input_active_review_count={before_active_count}",
        "",
        "## route_soft_decomposition",
        f"- ROUTE_SOFT_STABLE_WARNING={summary['route_soft_decomposition']['ROUTE_SOFT_STABLE_WARNING']}",
        f"- ROUTE_SOFT_NEEDS_MANUAL={summary['route_soft_decomposition']['ROUTE_SOFT_NEEDS_MANUAL']}",
        f"- ROUTE_SOFT_INPUT_EXCLUDE_CANDIDATE={summary['route_soft_decomposition']['ROUTE_SOFT_INPUT_EXCLUDE_CANDIDATE']}",
        "",
        "## year_handling",
        f"- YEAR_INPUT_EXCLUDE_CANDIDATE={summary['year_review_handling']['YEAR_INPUT_EXCLUDE_CANDIDATE']}",
        f"- YEAR_STABLE_WARNING={summary['year_review_handling']['YEAR_STABLE_WARNING']}",
        "",
        "## before_after",
        f"- active_review_queue: {before_active_count} -> {after_active_count}",
        f"- stable_warning: {before_stable_count} -> {after_stable_count}",
        f"- resolution_candidates: {before_resolution_count} -> {after_resolution_count}",
        "",
        "## integrity",
        f"- coverage_review_count={coverage_count}",
        f"- reject_candidate_count={reject_count}",
        f"- join_blocker_count={join_blocker_count}",
        "",
        "## decision",
        f"- go_hold_decision={go_hold}",
    ]
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(
        "[task239] "
        f"active_before={before_active_count} active_after={after_active_count} "
        f"stable_before={before_stable_count} stable_after={after_stable_count} "
        f"resolution_before={before_resolution_count} resolution_after={after_resolution_count} "
        f"coverage={coverage_count} reject={reject_count} join_blocker={join_blocker_count} "
        f"decision={go_hold}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
