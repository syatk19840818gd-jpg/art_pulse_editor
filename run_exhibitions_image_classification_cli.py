#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


EXIT_OK = 0
EXIT_MISSING_REQUIRED_ARTIFACT = 10
EXIT_SCHEMA_MISMATCH = 11
EXIT_METRIC_CALCULATION_ERROR = 12
EXIT_EMPTY_INPUT = 13
EXIT_TRIAL_READY_ZERO = 20
EXIT_INTERNAL_ERROR = 30

CLASS_KEEP = "Keep-Current"
CLASS_SAFE = "Safe-But-Provenance-Gated"
CLASS_GUARD = "Guard-First-Then-Upgrade"

DEFAULT_SAFE_MAX_GALLERIES = 10
DEFAULT_SAFE_MAX_SEEDS = 150
DEFAULT_GUARD_MAX_GALLERIES_MIN = 2
DEFAULT_GUARD_MAX_GALLERIES_MAX = 4
DEFAULT_GUARD_MAX_SEEDS = 60


@dataclass
class CliError(Exception):
    code: int
    message: str


@dataclass
class GalleryMetrics:
    run_id: str
    target_year: int
    fair_slug: str
    gallery_name_en: str
    current_input_grain: str
    route_risk_rate: float
    year_risk_rate: float
    provenance_violations: int
    duplicate_anomaly_groups: int
    expected_count: int
    actual_saved_count: int
    expected_vs_actual_gap: float
    current_saved_count: int
    trial_ready_seed_count: int
    reclassification_triggered: bool
    recommended_lane: str
    trial_ready: bool
    blocking_reasons: list[str]
    required_guard_steps: list[str]
    provenance_gate_required: bool
    recommended_next_action: str
    qa_gate_required: bool
    adoption_allowed: bool
    note_ja: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Classify exhibition-image galleries into lanes and generate "
            "lane-ready inventory/unit plans (no trial/QA/adoption execution)."
        )
    )
    parser.add_argument("--input-dir", default="data/phase1_seed10/logs")
    parser.add_argument("--authoritative-master-csv", required=True)
    parser.add_argument("--authoritative-runtime-csv", default="")
    parser.add_argument("--seed-eval-csv", required=True)
    parser.add_argument("--gallery-summary-csv", required=True)
    parser.add_argument("--trial-ready-decision-csv", required=True)
    parser.add_argument("--defer-queue-csv", default="")
    parser.add_argument("--reject-queue-csv", default="")
    parser.add_argument("--target-year", type=int, default=2025)
    parser.add_argument("--fair-slug", action="append", default=[])
    parser.add_argument("--lane", choices=["keep", "safe", "guard", "all"], default="all")
    parser.add_argument("--output-dir", default="data/phase1_seed10/logs")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--write-report-md", action="store_true")
    parser.add_argument("--write-manifest", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--fail-on-missing-artifacts", action="store_true")
    parser.add_argument("--fail-on-schema-drift", action="store_true")
    parser.add_argument("--safe-max-galleries", type=int, default=DEFAULT_SAFE_MAX_GALLERIES)
    parser.add_argument("--safe-max-seeds", type=int, default=DEFAULT_SAFE_MAX_SEEDS)
    parser.add_argument("--guard-max-galleries-min", type=int, default=DEFAULT_GUARD_MAX_GALLERIES_MIN)
    parser.add_argument("--guard-max-galleries-max", type=int, default=DEFAULT_GUARD_MAX_GALLERIES_MAX)
    parser.add_argument("--guard-max-seeds", type=int, default=DEFAULT_GUARD_MAX_SEEDS)
    parser.add_argument("--allow-unit-size-override", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def utc_timestamp_compact() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def norm_text(value: Any) -> str:
    return str(value or "").strip()


def parse_float(value: Any, *, default: float | None = None) -> float | None:
    text = norm_text(value)
    if text == "":
        return default
    try:
        parsed = float(text)
    except ValueError:
        return default
    if math.isnan(parsed) or math.isinf(parsed):
        return default
    return parsed


def parse_int(value: Any, *, default: int | None = None) -> int | None:
    text = norm_text(value)
    if text == "":
        return default
    try:
        return int(float(text))
    except ValueError:
        return default


def load_csv_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fp:
        reader = csv.DictReader(fp)
        if reader.fieldnames is None:
            raise CliError(EXIT_SCHEMA_MISMATCH, f"csv_has_no_header:{path}")
        fieldnames = [norm_text(name) for name in reader.fieldnames]
        rows: list[dict[str, str]] = []
        for raw in reader:
            normalized: dict[str, str] = {}
            for key, val in (raw or {}).items():
                normalized[norm_text(key)] = norm_text(val)
            rows.append(normalized)
    return fieldnames, rows


def ensure_required_columns(
    artifact_name: str,
    fieldnames: list[str],
    required_columns: list[str],
) -> None:
    missing = [column for column in required_columns if column not in fieldnames]
    if missing:
        raise CliError(
            EXIT_SCHEMA_MISMATCH,
            f"missing_required_columns:{artifact_name}:{','.join(missing)}",
        )


def lane_matches_filter(recommended_lane: str, lane_filter: str) -> bool:
    if lane_filter == "all":
        return True
    if lane_filter == "keep":
        return recommended_lane == CLASS_KEEP
    if lane_filter == "safe":
        return recommended_lane == CLASS_SAFE
    if lane_filter == "guard":
        return recommended_lane == CLASS_GUARD
    return False


def classify_lane(
    route_risk_rate: float,
    year_risk_rate: float,
    provenance_violations: int,
    duplicate_anomaly_groups: int,
    trial_ready_seed_count: int,
    expected_vs_actual_gap: float,
    current_saved_count: int,
    reclassification_triggered: bool,
) -> str:
    if (
        provenance_violations > 0
        or duplicate_anomaly_groups > 0
        or route_risk_rate > 0.25
        or year_risk_rate > 0.25
        or trial_ready_seed_count == 0
    ):
        return CLASS_GUARD
    if (
        route_risk_rate <= 0.05
        and year_risk_rate <= 0.05
        and provenance_violations == 0
        and duplicate_anomaly_groups == 0
        and expected_vs_actual_gap <= 0.10
        and current_saved_count >= 1
        and (not reclassification_triggered)
    ):
        return CLASS_KEEP
    if (
        provenance_violations == 0
        and duplicate_anomaly_groups == 0
        and route_risk_rate <= 0.25
        and year_risk_rate <= 0.25
        and trial_ready_seed_count >= 1
    ):
        return CLASS_SAFE
    return CLASS_GUARD


def build_guard_steps(
    route_risk_rate: float,
    year_risk_rate: float,
    provenance_violations: int,
    duplicate_anomaly_groups: int,
) -> list[str]:
    steps: list[str] = []
    if route_risk_rate > 0.10:
        steps.append("route")
    if year_risk_rate > 0.10:
        steps.append("year")
    if provenance_violations > 0:
        steps.append("provenance")
    if duplicate_anomaly_groups > 0:
        steps.append("duplicate")
    return steps


def build_blocking_reasons(
    lane: str,
    route_risk_rate: float,
    year_risk_rate: float,
    provenance_violations: int,
    duplicate_anomaly_groups: int,
    trial_ready_seed_count: int,
    expected_vs_actual_gap: float,
    reclassification_triggered: bool,
) -> list[str]:
    reasons: list[str] = []
    if lane == CLASS_GUARD:
        if route_risk_rate > 0.25:
            reasons.append("route_risk_gt_0_25")
        if year_risk_rate > 0.25:
            reasons.append("year_risk_gt_0_25")
        if provenance_violations > 0:
            reasons.append("provenance_violation")
        if duplicate_anomaly_groups > 0:
            reasons.append("duplicate_anomaly")
        if trial_ready_seed_count == 0:
            reasons.append("trial_ready_seed_zero")
    if lane == CLASS_KEEP and reclassification_triggered:
        reasons.append("reclassification_triggered")
    if lane == CLASS_SAFE:
        if trial_ready_seed_count < 1:
            reasons.append("trial_ready_seed_zero")
        if provenance_violations > 0:
            reasons.append("provenance_violation")
        if duplicate_anomaly_groups > 0:
            reasons.append("duplicate_anomaly")
        if route_risk_rate > 0.25:
            reasons.append("route_risk_gt_0_25")
        if year_risk_rate > 0.25:
            reasons.append("year_risk_gt_0_25")
    if expected_vs_actual_gap > 0.10 and lane != CLASS_KEEP:
        reasons.append("expected_actual_gap_gt_0_10")
    return reasons


def ensure_unit_size_override_allowed(args: argparse.Namespace) -> None:
    values_changed = (
        args.safe_max_galleries != DEFAULT_SAFE_MAX_GALLERIES
        or args.safe_max_seeds != DEFAULT_SAFE_MAX_SEEDS
        or args.guard_max_galleries_min != DEFAULT_GUARD_MAX_GALLERIES_MIN
        or args.guard_max_galleries_max != DEFAULT_GUARD_MAX_GALLERIES_MAX
        or args.guard_max_seeds != DEFAULT_GUARD_MAX_SEEDS
    )
    if values_changed and not args.allow_unit_size_override:
        raise CliError(
            EXIT_SCHEMA_MISMATCH,
            "unit_size_override_not_allowed_without_flag",
        )


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_markdown(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    run_id = args.run_id or f"{utc_timestamp_compact()}-classification"
    started_at = utc_now_iso()

    try:
        ensure_unit_size_override_allowed(args)

        output_dir = Path(args.output_dir)
        required_inputs = {
            "authoritative_master_csv": Path(args.authoritative_master_csv),
            "seed_evaluation_csv": Path(args.seed_eval_csv),
            "gallery_summary_csv": Path(args.gallery_summary_csv),
            "trial_ready_decision_csv": Path(args.trial_ready_decision_csv),
        }
        optional_inputs = {
            "authoritative_runtime_csv": Path(args.authoritative_runtime_csv) if args.authoritative_runtime_csv else None,
            "defer_queue_csv": Path(args.defer_queue_csv) if args.defer_queue_csv else None,
            "reject_queue_csv": Path(args.reject_queue_csv) if args.reject_queue_csv else None,
        }

        fail_on_missing = bool(args.fail_on_missing_artifacts or args.strict)
        missing_required = [name for name, path in required_inputs.items() if not path.exists()]
        if missing_required:
            raise CliError(
                EXIT_MISSING_REQUIRED_ARTIFACT,
                f"missing_required_artifacts:{','.join(missing_required)}",
            )
        if fail_on_missing:
            missing_optional = [name for name, path in optional_inputs.items() if path is not None and not path.exists()]
            if missing_optional:
                raise CliError(
                    EXIT_MISSING_REQUIRED_ARTIFACT,
                    f"missing_optional_artifacts_in_strict_mode:{','.join(missing_optional)}",
                )

        master_fields, master_rows_all = load_csv_rows(required_inputs["authoritative_master_csv"])
        seed_eval_fields, seed_eval_rows_all = load_csv_rows(required_inputs["seed_evaluation_csv"])
        summary_fields, summary_rows_all = load_csv_rows(required_inputs["gallery_summary_csv"])
        decision_fields, decision_rows_all = load_csv_rows(required_inputs["trial_ready_decision_csv"])

        ensure_required_columns(
            "authoritative_master_csv",
            master_fields,
            ["fair_slug", "gallery_name_en", "source_url"],
        )
        ensure_required_columns(
            "seed_evaluation_csv",
            seed_eval_fields,
            ["gallery_name_en", "fair_slug", "source_url"],
        )
        ensure_required_columns(
            "gallery_summary_csv",
            summary_fields,
            ["gallery_name_en", "route_risk_rate", "year_risk_rate", "provenance_violations", "duplicate_anomaly_groups"],
        )
        ensure_required_columns(
            "trial_ready_decision_csv",
            decision_fields,
            ["gallery_name_en", "trial_ready_seed_count", "route_risk_rate", "year_risk_rate", "provenance_violations", "duplicate_anomaly_groups"],
        )

        target_year = int(args.target_year)
        fair_filter = set([norm_text(v) for v in args.fair_slug if norm_text(v)])

        master_rows: list[dict[str, str]] = []
        for row in master_rows_all:
            row_year = parse_int(row.get("target_year"), default=target_year)
            if row_year != target_year:
                continue
            if fair_filter and norm_text(row.get("fair_slug")) not in fair_filter:
                continue
            master_rows.append(row)
        if not master_rows:
            raise CliError(EXIT_EMPTY_INPUT, "empty_master_scope_after_filters")

        decision_by_gallery: dict[str, dict[str, str]] = {}
        for row in decision_rows_all:
            gallery = norm_text(row.get("gallery_name_en"))
            if gallery:
                decision_by_gallery[gallery] = row

        summary_by_gallery: dict[str, dict[str, str]] = {}
        for row in summary_rows_all:
            gallery = norm_text(row.get("gallery_name_en"))
            if gallery:
                summary_by_gallery[gallery] = row

        fairs_by_gallery: dict[str, set[str]] = {}
        master_by_key: dict[tuple[str, str], list[dict[str, str]]] = {}
        for row in master_rows:
            fair_slug = norm_text(row.get("fair_slug"))
            gallery = norm_text(row.get("gallery_name_en"))
            if not fair_slug or not gallery:
                continue
            key = (fair_slug, gallery)
            master_by_key.setdefault(key, []).append(row)
            fairs_by_gallery.setdefault(gallery, set()).add(fair_slug)

        if args.strict:
            ambiguous = sorted([g for g, fairs in fairs_by_gallery.items() if len(fairs) > 1 and g in summary_by_gallery])
            if ambiguous:
                raise CliError(EXIT_SCHEMA_MISMATCH, f"ambiguous_gallery_name_across_fairs:{','.join(ambiguous)}")

        seed_eval_rows: list[dict[str, str]] = []
        for row in seed_eval_rows_all:
            row_year = parse_int(row.get("target_year"), default=target_year)
            if row_year != target_year:
                continue
            fair_slug = norm_text(row.get("fair_slug"))
            gallery = norm_text(row.get("gallery_name_en"))
            if fair_filter and fair_slug not in fair_filter:
                continue
            if (fair_slug, gallery) not in master_by_key:
                continue
            seed_eval_rows.append(row)

        seed_eval_by_key: dict[tuple[str, str], list[dict[str, str]]] = {}
        for row in seed_eval_rows:
            key = (norm_text(row.get("fair_slug")), norm_text(row.get("gallery_name_en")))
            seed_eval_by_key.setdefault(key, []).append(row)

        classification_rows: list[dict[str, Any]] = []
        inventory_rows: list[dict[str, Any]] = []
        metrics_list: list[GalleryMetrics] = []

        for (fair_slug, gallery), rows in sorted(master_by_key.items(), key=lambda item: (item[0][0], item[0][1])):
            summary_row = summary_by_gallery.get(gallery, {})
            decision_row = decision_by_gallery.get(gallery, {})
            if args.strict and (not summary_row or not decision_row):
                raise CliError(EXIT_SCHEMA_MISMATCH, f"missing_summary_or_decision:{fair_slug}:{gallery}")

            seed_rows = seed_eval_by_key.get((fair_slug, gallery), [])

            route_risk_rate = parse_float(
                decision_row.get("route_risk_rate"),
                default=parse_float(summary_row.get("route_risk_rate")),
            )
            year_risk_rate = parse_float(
                decision_row.get("year_risk_rate"),
                default=parse_float(summary_row.get("year_risk_rate")),
            )
            provenance_violations = parse_int(
                decision_row.get("provenance_violations"),
                default=parse_int(summary_row.get("provenance_violations")),
            )
            duplicate_anomaly_groups = parse_int(
                decision_row.get("duplicate_anomaly_groups"),
                default=parse_int(summary_row.get("duplicate_anomaly_groups")),
            )

            if route_risk_rate is None:
                pre_count = len(seed_rows)
                route_fail = len([r for r in seed_rows if norm_text(r.get("route_guard_result")) == "fail"])
                route_risk_rate = float(route_fail) / float(pre_count) if pre_count > 0 else 0.0
            if year_risk_rate is None:
                route_pass = len([r for r in seed_rows if norm_text(r.get("route_guard_result")) != "fail"])
                year_fail = len([r for r in seed_rows if norm_text(r.get("year_guard_result")) == "fail"])
                year_risk_rate = float(year_fail) / float(route_pass) if route_pass > 0 else 0.0
            if provenance_violations is None:
                provenance_violations = len(
                    [r for r in seed_rows if norm_text(r.get("provenance_guard_result")) == "fail"]
                )
            if duplicate_anomaly_groups is None:
                duplicate_groups = {
                    norm_text(r.get("duplicate_group_id"))
                    for r in seed_rows
                    if norm_text(r.get("duplicate_check_result")) == "fail" and norm_text(r.get("duplicate_group_id"))
                }
                duplicate_anomaly_groups = len(duplicate_groups)

            trial_ready_seed_count = parse_int(
                decision_row.get("trial_ready_seed_count"),
                default=parse_int(summary_row.get("N_trial_ready_seed")),
            )
            if trial_ready_seed_count is None:
                trial_ready_seed_count = len([r for r in seed_rows if norm_text(r.get("next_action")) == "to_trial_seed"])

            expected_count = len({norm_text(r.get("source_url")) for r in rows if norm_text(r.get("source_url"))})
            current_saved_count = parse_int(
                summary_row.get("current_saved_count"),
                default=parse_int(summary_row.get("actual_saved_count")),
            )
            if current_saved_count is None:
                current_saved_count = parse_int(summary_row.get("saved_images_total"), default=trial_ready_seed_count)

            actual_saved_count = parse_int(
                summary_row.get("actual_saved_count"),
                default=parse_int(summary_row.get("saved_images_total")),
            )
            if actual_saved_count is None:
                actual_saved_count = current_saved_count

            expected_vs_actual_gap = parse_float(summary_row.get("expected_vs_actual_gap"))
            if expected_vs_actual_gap is None:
                expected_vs_actual_gap = (
                    float(max(expected_count - int(actual_saved_count or 0), 0)) / float(max(expected_count, 1))
                )

            if any(metric is None for metric in [route_risk_rate, year_risk_rate, provenance_violations, duplicate_anomaly_groups]):
                raise CliError(EXIT_METRIC_CALCULATION_ERROR, f"metric_calculation_failed:{fair_slug}:{gallery}")
            if (
                float(route_risk_rate) < 0.0
                or float(route_risk_rate) > 1.0
                or float(year_risk_rate) < 0.0
                or float(year_risk_rate) > 1.0
                or int(trial_ready_seed_count) < 0
            ):
                raise CliError(
                    EXIT_METRIC_CALCULATION_ERROR,
                    f"metric_out_of_range:{fair_slug}:{gallery}",
                )

            grain_values = {
                norm_text(r.get("input_grain")) for r in rows if norm_text(r.get("input_grain"))
            } or {norm_text(r.get("seed_url_type")) for r in rows if norm_text(r.get("seed_url_type"))}
            if not grain_values:
                current_input_grain = "unknown"
            elif len(grain_values) == 1:
                current_input_grain = list(grain_values)[0]
            else:
                current_input_grain = "mixed"

            explicit_reclassification = norm_text(summary_row.get("reclassification_triggered")).lower()
            if explicit_reclassification in {"true", "1", "yes"}:
                reclassification_triggered = True
            elif explicit_reclassification in {"false", "0", "no"}:
                reclassification_triggered = False
            else:
                reclassification_triggered = bool(
                    expected_vs_actual_gap > 0.10
                    or route_risk_rate > 0.05
                    or year_risk_rate > 0.05
                    or int(provenance_violations) > 0
                    or int(duplicate_anomaly_groups) > 0
                )

            recommended_lane = classify_lane(
                route_risk_rate=float(route_risk_rate),
                year_risk_rate=float(year_risk_rate),
                provenance_violations=int(provenance_violations),
                duplicate_anomaly_groups=int(duplicate_anomaly_groups),
                trial_ready_seed_count=int(trial_ready_seed_count),
                expected_vs_actual_gap=float(expected_vs_actual_gap),
                current_saved_count=int(current_saved_count or 0),
                reclassification_triggered=reclassification_triggered,
            )
            if not lane_matches_filter(recommended_lane, args.lane):
                continue

            guard_trial_ready = bool(
                route_risk_rate <= 0.10
                and year_risk_rate <= 0.10
                and int(provenance_violations) == 0
                and int(duplicate_anomaly_groups) == 0
                and int(trial_ready_seed_count) >= 1
            )
            if recommended_lane == CLASS_KEEP:
                trial_ready = False
            elif recommended_lane == CLASS_SAFE:
                trial_ready = bool(
                    int(trial_ready_seed_count) >= 1
                    and int(provenance_violations) == 0
                    and int(duplicate_anomaly_groups) == 0
                    and route_risk_rate <= 0.25
                    and year_risk_rate <= 0.25
                )
            else:
                trial_ready = guard_trial_ready

            if recommended_lane == CLASS_KEEP:
                recommended_next_action = "monitor_keep_current"
            elif recommended_lane == CLASS_SAFE:
                recommended_next_action = "provenance_gated_trial"
            elif guard_trial_ready:
                recommended_next_action = "guard_cleared_trial"
            else:
                recommended_next_action = "guard_first_remediation"

            required_guard_steps = (
                build_guard_steps(
                    route_risk_rate=float(route_risk_rate),
                    year_risk_rate=float(year_risk_rate),
                    provenance_violations=int(provenance_violations),
                    duplicate_anomaly_groups=int(duplicate_anomaly_groups),
                )
                if recommended_lane == CLASS_GUARD
                else []
            )
            blocking_reasons = build_blocking_reasons(
                lane=recommended_lane,
                route_risk_rate=float(route_risk_rate),
                year_risk_rate=float(year_risk_rate),
                provenance_violations=int(provenance_violations),
                duplicate_anomaly_groups=int(duplicate_anomaly_groups),
                trial_ready_seed_count=int(trial_ready_seed_count),
                expected_vs_actual_gap=float(expected_vs_actual_gap),
                reclassification_triggered=reclassification_triggered,
            )

            metrics = GalleryMetrics(
                run_id=run_id,
                target_year=target_year,
                fair_slug=fair_slug,
                gallery_name_en=gallery,
                current_input_grain=current_input_grain,
                route_risk_rate=float(route_risk_rate),
                year_risk_rate=float(year_risk_rate),
                provenance_violations=int(provenance_violations),
                duplicate_anomaly_groups=int(duplicate_anomaly_groups),
                expected_count=int(expected_count),
                actual_saved_count=int(actual_saved_count or 0),
                expected_vs_actual_gap=float(expected_vs_actual_gap),
                current_saved_count=int(current_saved_count or 0),
                trial_ready_seed_count=int(trial_ready_seed_count),
                reclassification_triggered=reclassification_triggered,
                recommended_lane=recommended_lane,
                trial_ready=trial_ready,
                blocking_reasons=blocking_reasons,
                required_guard_steps=required_guard_steps,
                provenance_gate_required=recommended_lane == CLASS_SAFE,
                recommended_next_action=recommended_next_action,
                qa_gate_required=bool(recommended_lane != CLASS_KEEP and trial_ready),
                adoption_allowed=False,
                note_ja=norm_text(decision_row.get("decision_reason_code")) or norm_text(summary_row.get("decision_reason_code")) or "",
            )
            metrics_list.append(metrics)

        if not metrics_list:
            raise CliError(EXIT_EMPTY_INPUT, "empty_scope_after_lane_filter")

        safe_seed_rows = [r for r in seed_eval_rows if norm_text(r.get("next_action")) == "to_trial_seed"]
        defer_rows = [r for r in seed_eval_rows if norm_text(r.get("next_action")) == "to_defer_seed"]
        reject_rows = [r for r in seed_eval_rows if norm_text(r.get("next_action")) == "to_reject_seed"]

        lane_order = {CLASS_SAFE: 1, CLASS_GUARD: 2, CLASS_KEEP: 3}
        metrics_sorted = sorted(
            metrics_list,
            key=lambda m: (lane_order.get(m.recommended_lane, 9), m.fair_slug, -m.trial_ready_seed_count, m.gallery_name_en),
        )

        grouped: dict[tuple[str, str], list[GalleryMetrics]] = {}
        for m in metrics_sorted:
            grouped.setdefault((m.recommended_lane, m.fair_slug), []).append(m)

        unit_plan_rows: list[dict[str, Any]] = []
        queue_order = 1
        lane_unit_counters: dict[tuple[str, str], int] = {}
        unit_assignments: dict[tuple[str, str], str] = {}

        for (lane, fair_slug), members in grouped.items():
            if lane == CLASS_KEEP:
                max_galleries = 999999
                max_seeds = 999999
                lane_token = "KEEP"
            elif lane == CLASS_SAFE:
                max_galleries = int(args.safe_max_galleries)
                max_seeds = int(args.safe_max_seeds)
                lane_token = "SAFE"
            else:
                max_galleries = int(args.guard_max_galleries_max)
                max_seeds = int(args.guard_max_seeds)
                lane_token = "GUARD"

            chunk: list[GalleryMetrics] = []
            chunk_seeds = 0
            for m in members:
                would_exceed_gallery = len(chunk) >= max_galleries
                would_exceed_seed = (chunk_seeds + m.trial_ready_seed_count) > max_seeds
                if chunk and (would_exceed_gallery or would_exceed_seed):
                    lane_unit_counters[(lane, fair_slug)] = lane_unit_counters.get((lane, fair_slug), 0) + 1
                    seq = lane_unit_counters[(lane, fair_slug)]
                    unit_id = f"U-{lane_token}-{fair_slug}-{target_year}-{seq:03d}"
                    for c in chunk:
                        unit_assignments[(c.fair_slug, c.gallery_name_en)] = unit_id
                    unit_plan_rows.append(
                        {
                            "run_id": run_id,
                            "unit_id": unit_id,
                            "lane": lane,
                            "fair_slug": fair_slug,
                            "target_year": target_year,
                            "gallery_count": len(chunk),
                            "trial_ready_seed_count": sum(item.trial_ready_seed_count for item in chunk),
                            "gallery_names": "|".join(item.gallery_name_en for item in chunk),
                            "queue_order": queue_order,
                            "unit_scope": f"{fair_slug}:{'|'.join(item.gallery_name_en for item in chunk)}",
                            "recommended_next_action": "monitor" if lane == CLASS_KEEP else "trial_prep",
                        }
                    )
                    queue_order += 1
                    chunk = []
                    chunk_seeds = 0

                chunk.append(m)
                chunk_seeds += m.trial_ready_seed_count

            if chunk:
                lane_unit_counters[(lane, fair_slug)] = lane_unit_counters.get((lane, fair_slug), 0) + 1
                seq = lane_unit_counters[(lane, fair_slug)]
                unit_id = f"U-{lane_token}-{fair_slug}-{target_year}-{seq:03d}"
                for c in chunk:
                    unit_assignments[(c.fair_slug, c.gallery_name_en)] = unit_id
                unit_plan_rows.append(
                    {
                        "run_id": run_id,
                        "unit_id": unit_id,
                        "lane": lane,
                        "fair_slug": fair_slug,
                        "target_year": target_year,
                        "gallery_count": len(chunk),
                        "trial_ready_seed_count": sum(item.trial_ready_seed_count for item in chunk),
                        "gallery_names": "|".join(item.gallery_name_en for item in chunk),
                        "queue_order": queue_order,
                        "unit_scope": f"{fair_slug}:{'|'.join(item.gallery_name_en for item in chunk)}",
                        "recommended_next_action": "monitor" if lane == CLASS_KEEP else "trial_prep",
                    }
                )
                queue_order += 1

        for m in metrics_sorted:
            unit_id = unit_assignments.get((m.fair_slug, m.gallery_name_en), "")
            unit_scope = f"{m.fair_slug}:{m.gallery_name_en}"
            classification_rows.append(
                {
                    "run_id": m.run_id,
                    "target_year": m.target_year,
                    "fair_slug": m.fair_slug,
                    "gallery_name_en": m.gallery_name_en,
                    "recommended_lane": m.recommended_lane,
                    "route_risk_rate": f"{m.route_risk_rate:.6f}",
                    "year_risk_rate": f"{m.year_risk_rate:.6f}",
                    "provenance_violations": m.provenance_violations,
                    "duplicate_anomaly_groups": m.duplicate_anomaly_groups,
                    "expected_count": m.expected_count,
                    "actual_saved_count": m.actual_saved_count,
                    "expected_vs_actual_gap": f"{m.expected_vs_actual_gap:.6f}",
                    "current_saved_count": m.current_saved_count,
                    "trial_ready_seed_count": m.trial_ready_seed_count,
                    "reclassification_triggered": str(m.reclassification_triggered).lower(),
                    "trial_ready": str(m.trial_ready).lower(),
                    "blocking_reasons": "|".join(m.blocking_reasons),
                    "required_guard_steps": "|".join(m.required_guard_steps),
                    "decision_reason_code": m.note_ja,
                    "recommended_next_action": m.recommended_next_action,
                    "recommended_unit_id": unit_id,
                    "recommended_unit_scope": unit_scope,
                }
            )
            inventory_rows.append(
                {
                    "run_id": m.run_id,
                    "target_year": m.target_year,
                    "fair_slug": m.fair_slug,
                    "gallery_name_en": m.gallery_name_en,
                    "current_lane": "",
                    "recommended_lane": m.recommended_lane,
                    "current_input_grain": m.current_input_grain,
                    "route_risk_rate": f"{m.route_risk_rate:.6f}",
                    "year_risk_rate": f"{m.year_risk_rate:.6f}",
                    "provenance_violations": m.provenance_violations,
                    "duplicate_anomaly_groups": m.duplicate_anomaly_groups,
                    "expected_vs_actual_gap": f"{m.expected_vs_actual_gap:.6f}",
                    "current_saved_count": m.current_saved_count,
                    "trial_ready_seed_count": m.trial_ready_seed_count,
                    "reclassification_triggered": str(m.reclassification_triggered).lower(),
                    "trial_ready": str(m.trial_ready).lower(),
                    "blocking_reasons": "|".join(m.blocking_reasons),
                    "required_guard_steps": "|".join(m.required_guard_steps),
                    "provenance_gate_required": str(m.provenance_gate_required).lower(),
                    "recommended_unit_id": unit_id,
                    "recommended_unit_scope": unit_scope,
                    "recommended_next_action": m.recommended_next_action,
                    "qa_gate_required": str(m.qa_gate_required).lower(),
                    "adoption_allowed": str(m.adoption_allowed).lower(),
                    "note_ja": m.note_ja,
                }
            )

        defer_queue_rows: list[dict[str, Any]] = []
        reject_queue_rows: list[dict[str, Any]] = []
        for row in defer_rows:
            defer_queue_rows.append(
                {
                    "run_id": run_id,
                    "target_year": target_year,
                    "fair_slug": norm_text(row.get("fair_slug")),
                    "gallery_name_en": norm_text(row.get("gallery_name_en")),
                    "source_url": norm_text(row.get("source_url")),
                    "reason_code": norm_text(row.get("route_guard_reason_code"))
                    or norm_text(row.get("year_guard_reason_code"))
                    or norm_text(row.get("provenance_guard_reason_code"))
                    or "defer",
                    "guard_failure_stage": norm_text(row.get("guard_failure_stage")),
                    "next_action": "defer",
                }
            )
        for row in reject_rows:
            reject_queue_rows.append(
                {
                    "run_id": run_id,
                    "target_year": target_year,
                    "fair_slug": norm_text(row.get("fair_slug")),
                    "gallery_name_en": norm_text(row.get("gallery_name_en")),
                    "source_url": norm_text(row.get("source_url")),
                    "reason_code": norm_text(row.get("route_guard_reason_code"))
                    or norm_text(row.get("year_guard_reason_code"))
                    or norm_text(row.get("provenance_guard_reason_code"))
                    or "reject",
                    "guard_failure_stage": norm_text(row.get("guard_failure_stage")),
                    "next_action": "reject",
                }
            )

        class_counts = {CLASS_KEEP: 0, CLASS_SAFE: 0, CLASS_GUARD: 0}
        class_seed_counts = {CLASS_KEEP: 0, CLASS_SAFE: 0, CLASS_GUARD: 0}
        for m in metrics_sorted:
            class_counts[m.recommended_lane] = class_counts.get(m.recommended_lane, 0) + 1
            class_seed_counts[m.recommended_lane] = class_seed_counts.get(m.recommended_lane, 0) + m.trial_ready_seed_count

        trial_ready_total = sum(m.trial_ready_seed_count for m in metrics_sorted if m.trial_ready)

        prefix = f"exhibitions_image_task_t192_"
        paths = {
            "classification_summary_json": output_dir / f"{prefix}classification_summary_{run_id}.json",
            "classification_decision_csv": output_dir / f"{prefix}classification_decision_{run_id}.csv",
            "lane_ready_inventory_csv": output_dir / f"{prefix}lane_ready_inventory_{run_id}.csv",
            "unit_plan_csv": output_dir / f"{prefix}unit_plan_{run_id}.csv",
            "defer_queue_csv": output_dir / f"{prefix}defer_queue_{run_id}.csv",
            "reject_queue_csv": output_dir / f"{prefix}reject_queue_{run_id}.csv",
            "classification_report_md": output_dir / f"{prefix}classification_report_{run_id}.md",
            "manifest_json": output_dir / f"{prefix}manifest_{run_id}.json",
        }

        summary_payload = {
            "task_id": "TASK192",
            "run_id": run_id,
            "started_at": started_at,
            "completed_at": utc_now_iso(),
            "target_year": target_year,
            "lane_filter": args.lane,
            "fair_filter": sorted(list(fair_filter)),
            "input_counts": {
                "master_rows_in_scope": len(master_rows),
                "seed_eval_rows_in_scope": len(seed_eval_rows),
                "gallery_count": len(metrics_sorted),
            },
            "classification_counts": class_counts,
            "classification_seed_counts": class_seed_counts,
            "trial_ready_seed_total": trial_ready_total,
            "defer_seed_count": len(defer_queue_rows),
            "reject_seed_count": len(reject_queue_rows),
            "outputs": {name: str(path) for name, path in paths.items()},
            "status": "ok" if trial_ready_total > 0 else "hold_trial_ready_zero",
        }

        if not args.dry_run:
            write_json(paths["classification_summary_json"], summary_payload)
            write_csv(
                paths["classification_decision_csv"],
                [
                    "run_id",
                    "target_year",
                    "fair_slug",
                    "gallery_name_en",
                    "recommended_lane",
                    "route_risk_rate",
                    "year_risk_rate",
                    "provenance_violations",
                    "duplicate_anomaly_groups",
                    "expected_count",
                    "actual_saved_count",
                    "expected_vs_actual_gap",
                    "current_saved_count",
                    "trial_ready_seed_count",
                    "reclassification_triggered",
                    "trial_ready",
                    "blocking_reasons",
                    "required_guard_steps",
                    "decision_reason_code",
                    "recommended_next_action",
                    "recommended_unit_id",
                    "recommended_unit_scope",
                ],
                classification_rows,
            )
            write_csv(
                paths["lane_ready_inventory_csv"],
                [
                    "run_id",
                    "target_year",
                    "fair_slug",
                    "gallery_name_en",
                    "current_lane",
                    "recommended_lane",
                    "current_input_grain",
                    "route_risk_rate",
                    "year_risk_rate",
                    "provenance_violations",
                    "duplicate_anomaly_groups",
                    "expected_vs_actual_gap",
                    "current_saved_count",
                    "trial_ready_seed_count",
                    "reclassification_triggered",
                    "trial_ready",
                    "blocking_reasons",
                    "required_guard_steps",
                    "provenance_gate_required",
                    "recommended_unit_id",
                    "recommended_unit_scope",
                    "recommended_next_action",
                    "qa_gate_required",
                    "adoption_allowed",
                    "note_ja",
                ],
                inventory_rows,
            )
            write_csv(
                paths["unit_plan_csv"],
                [
                    "run_id",
                    "unit_id",
                    "lane",
                    "fair_slug",
                    "target_year",
                    "gallery_count",
                    "trial_ready_seed_count",
                    "gallery_names",
                    "queue_order",
                    "unit_scope",
                    "recommended_next_action",
                ],
                unit_plan_rows,
            )
            write_csv(
                paths["defer_queue_csv"],
                [
                    "run_id",
                    "target_year",
                    "fair_slug",
                    "gallery_name_en",
                    "source_url",
                    "reason_code",
                    "guard_failure_stage",
                    "next_action",
                ],
                defer_queue_rows,
            )
            write_csv(
                paths["reject_queue_csv"],
                [
                    "run_id",
                    "target_year",
                    "fair_slug",
                    "gallery_name_en",
                    "source_url",
                    "reason_code",
                    "guard_failure_stage",
                    "next_action",
                ],
                reject_queue_rows,
            )
            if args.write_report_md:
                report_lines = [
                    "# TASK192 Classification CLI Report",
                    "",
                    f"- run_id: `{run_id}`",
                    f"- target_year: `{target_year}`",
                    f"- lane_filter: `{args.lane}`",
                    f"- fair_filter_count: `{len(fair_filter)}`",
                    f"- gallery_count: `{len(metrics_sorted)}`",
                    f"- trial_ready_seed_total: `{trial_ready_total}`",
                    f"- class_count_keep_current: `{class_counts.get(CLASS_KEEP, 0)}`",
                    f"- class_count_safe_but_provenance_gated: `{class_counts.get(CLASS_SAFE, 0)}`",
                    f"- class_count_guard_first_then_upgrade: `{class_counts.get(CLASS_GUARD, 0)}`",
                    "",
                    "## Outputs",
                ]
                for name, path in paths.items():
                    if name in {"classification_report_md", "manifest_json"}:
                        continue
                    report_lines.append(f"- {name}: `{path}`")
                write_markdown(paths["classification_report_md"], report_lines)
            if args.write_manifest:
                manifest_payload = {
                    "task_id": "TASK192",
                    "run_id": run_id,
                    "created_at": utc_now_iso(),
                    "input_artifacts": {k: str(v) for k, v in required_inputs.items()},
                    "optional_input_artifacts": {
                        k: (str(v) if v is not None else "")
                        for k, v in optional_inputs.items()
                    },
                    "output_artifacts": {k: str(v) for k, v in paths.items()},
                    "lane_filter": args.lane,
                    "fair_filter": sorted(list(fair_filter)),
                    "target_year": target_year,
                    "anti_mixing_contract": {
                        "trial_then_qa_then_adoption": True,
                        "trash_before_adoption": True,
                        "scoped_replace_only": True,
                        "append_forbidden": True,
                    },
                }
                write_json(paths["manifest_json"], manifest_payload)

        if trial_ready_total == 0:
            return EXIT_TRIAL_READY_ZERO
        return EXIT_OK

    except CliError as err:
        print(err.message)
        return err.code
    except Exception as err:  # pragma: no cover
        print(f"internal_error:{err}")
        return EXIT_INTERNAL_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
