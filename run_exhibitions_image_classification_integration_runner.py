#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


EXIT_OK = 0
EXIT_MISSING_REQUIRED_ARTIFACT = 10
EXIT_SCHEMA_MISMATCH = 11
EXIT_METRIC_CALCULATION_ERROR = 12
EXIT_EMPTY_INPUT = 13
EXIT_HOLD = 20
EXIT_INTERNAL_ERROR = 30


REQUIRED_INPUT_KEYS = [
    "authoritative_master_csv",
    "seed_evaluation_csv",
    "gallery_summary_csv",
    "trial_ready_decision_csv",
]
OPTIONAL_INPUT_KEYS = [
    "authoritative_runtime_csv",
    "defer_queue_csv",
    "reject_queue_csv",
]
ALL_INPUT_KEYS = REQUIRED_INPUT_KEYS + OPTIONAL_INPUT_KEYS


@dataclass
class IntegrationError(Exception):
    code: int
    reason_code: str
    message: str


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def utc_compact() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def norm_text(value: Any) -> str:
    return str(value or "").strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Integration runner for classification CLI (discovery/preflight/orchestration/"
            "bundle/handoff only; no trial/QA/adoption execution)."
        )
    )
    parser.add_argument("--mode", choices=["explicit", "manifest", "scan"], required=True)
    parser.add_argument("--input-root", default="data/phase1_seed10/logs")
    parser.add_argument("--logs-root", default="data/phase1_seed10/logs")
    parser.add_argument("--classification-cli-path", default="run_exhibitions_image_classification_cli.py")
    parser.add_argument("--output-dir", default="data/phase1_seed10/logs")
    parser.add_argument("--manifest-path", default="")
    parser.add_argument("--manifest-case-id", default="")
    parser.add_argument("--target-year", type=int, required=True)
    parser.add_argument("--fair-slug", action="append", default=[])
    parser.add_argument("--lane", choices=["keep", "safe", "guard", "all"], default="all")
    parser.add_argument("--gallery-name", action="append", default=[])
    parser.add_argument("--bundle-id", default="")
    parser.add_argument("--classification-run-id", default="")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--fail-on-ambiguous-input", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--write-report-md", action="store_true")
    parser.add_argument("--write-manifest", action="store_true")

    parser.add_argument("--authoritative-master-csv", default="")
    parser.add_argument("--authoritative-runtime-csv", default="")
    parser.add_argument("--seed-eval-csv", default="")
    parser.add_argument("--gallery-summary-csv", default="")
    parser.add_argument("--trial-ready-decision-csv", default="")
    parser.add_argument("--defer-queue-csv", default="")
    parser.add_argument("--reject-queue-csv", default="")

    parser.add_argument("--safe-max-galleries", type=int, default=10)
    parser.add_argument("--safe-max-seeds", type=int, default=150)
    parser.add_argument("--guard-max-galleries-min", type=int, default=2)
    parser.add_argument("--guard-max-galleries-max", type=int, default=4)
    parser.add_argument("--guard-max-seeds", type=int, default=60)
    parser.add_argument("--allow-unit-size-override", action="store_true")
    return parser.parse_args()


def csv_head_rows(path: Path, max_rows: int = 120) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fp:
        reader = csv.DictReader(fp)
        if reader.fieldnames is None:
            raise IntegrationError(
                EXIT_SCHEMA_MISMATCH,
                "csv_has_no_header",
                f"CSV has no header: {path}",
            )
        fieldnames = [norm_text(v) for v in reader.fieldnames]
        rows: list[dict[str, str]] = []
        for idx, row in enumerate(reader):
            rows.append({norm_text(k): norm_text(v) for k, v in (row or {}).items()})
            if idx + 1 >= max_rows:
                break
    return fieldnames, rows


def ensure_columns(path: Path, fieldnames: list[str], required: list[str]) -> None:
    missing = [c for c in required if c not in fieldnames]
    if missing:
        raise IntegrationError(
            EXIT_SCHEMA_MISMATCH,
            "missing_required_columns",
            f"{path} missing columns: {','.join(missing)}",
        )


def artifact_patterns() -> dict[str, list[str]]:
    return {
        "authoritative_master_csv": ["**/*authoritative_master*.csv"],
        "authoritative_runtime_csv": ["**/*authoritative_runtime*.csv"],
        "seed_evaluation_csv": [
            "**/*seed_evaluation*.csv",
            "**/*guard_seed_evaluation*.csv",
            "**/*provenance_seed_evaluation*.csv",
        ],
        "gallery_summary_csv": ["**/*gallery_summary*.csv"],
        "trial_ready_decision_csv": ["**/*trial_ready_decision*.csv"],
        "defer_queue_csv": ["**/*defer_queue*.csv"],
        "reject_queue_csv": ["**/*reject_queue*.csv"],
    }


def file_matches_scope(
    path: Path,
    target_year: int,
    fair_filter: set[str],
    gallery_filter: set[str],
) -> bool:
    try:
        fieldnames, rows = csv_head_rows(path, max_rows=200)
    except IntegrationError:
        return False
    if not rows:
        return True

    has_year = "target_year" in fieldnames
    has_fair = "fair_slug" in fieldnames
    has_gallery = "gallery_name_en" in fieldnames

    row_matches = 0
    for row in rows:
        ok = True
        if has_year:
            try:
                ok = ok and int(float(norm_text(row.get("target_year", "")))) == target_year
            except ValueError:
                ok = False
        if fair_filter and has_fair:
            ok = ok and norm_text(row.get("fair_slug")) in fair_filter
        if gallery_filter and has_gallery:
            ok = ok and norm_text(row.get("gallery_name_en")) in gallery_filter
        if ok:
            row_matches += 1
    return row_matches > 0


def resolve_explicit_inputs(args: argparse.Namespace) -> tuple[dict[str, str], dict[str, Any]]:
    mapping = {
        "authoritative_master_csv": norm_text(args.authoritative_master_csv),
        "authoritative_runtime_csv": norm_text(args.authoritative_runtime_csv),
        "seed_evaluation_csv": norm_text(args.seed_eval_csv),
        "gallery_summary_csv": norm_text(args.gallery_summary_csv),
        "trial_ready_decision_csv": norm_text(args.trial_ready_decision_csv),
        "defer_queue_csv": norm_text(args.defer_queue_csv),
        "reject_queue_csv": norm_text(args.reject_queue_csv),
    }
    meta = {"resolution_mode": "explicit", "ambiguous_resolution": []}
    return mapping, meta


def resolve_manifest_inputs(args: argparse.Namespace) -> tuple[dict[str, str], dict[str, Any]]:
    manifest_path = Path(args.manifest_path)
    if not args.manifest_path or not manifest_path.exists():
        raise IntegrationError(
            EXIT_MISSING_REQUIRED_ARTIFACT,
            "manifest_missing",
            f"Manifest not found: {manifest_path}",
        )
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    mapping: dict[str, str] = {key: "" for key in ALL_INPUT_KEYS}
    manifest_scope_hash = norm_text(payload.get("scope_hash"))
    target_year_in_manifest = payload.get("target_year")
    if target_year_in_manifest is not None and int(target_year_in_manifest) != int(args.target_year):
        raise IntegrationError(
            EXIT_SCHEMA_MISMATCH,
            "manifest_target_year_mismatch",
            f"Manifest target_year mismatch: {target_year_in_manifest} != {args.target_year}",
        )

    if "resolved_inputs" in payload:
        for key in ALL_INPUT_KEYS:
            mapping[key] = norm_text(payload["resolved_inputs"].get(key))
    elif "input_artifacts" in payload:
        for key in REQUIRED_INPUT_KEYS:
            mapping[key] = norm_text(payload["input_artifacts"].get(key))
        optional = payload.get("optional_input_artifacts", {})
        mapping["authoritative_runtime_csv"] = norm_text(optional.get("authoritative_runtime_csv"))
        mapping["defer_queue_csv"] = norm_text(optional.get("defer_queue_csv"))
        mapping["reject_queue_csv"] = norm_text(optional.get("reject_queue_csv"))
    elif "cases" in payload and args.manifest_case_id:
        case = next((c for c in payload["cases"] if norm_text(c.get("case_id")) == args.manifest_case_id), None)
        if case is None:
            raise IntegrationError(
                EXIT_SCHEMA_MISMATCH,
                "manifest_case_not_found",
                f"Case not found in fixture manifest: {args.manifest_case_id}",
            )
        mapping["authoritative_master_csv"] = norm_text(case.get("authoritative_master_csv"))
        mapping["authoritative_runtime_csv"] = norm_text(case.get("authoritative_runtime_csv"))
        mapping["seed_evaluation_csv"] = norm_text(case.get("seed_eval_csv"))
        mapping["gallery_summary_csv"] = norm_text(case.get("gallery_summary_csv"))
        mapping["trial_ready_decision_csv"] = norm_text(case.get("trial_ready_decision_csv"))
        mapping["defer_queue_csv"] = norm_text(case.get("defer_queue_csv"))
        mapping["reject_queue_csv"] = norm_text(case.get("reject_queue_csv"))
    else:
        raise IntegrationError(
            EXIT_SCHEMA_MISMATCH,
            "manifest_schema_unsupported",
            "Manifest schema unsupported for integration input resolution",
        )
    meta = {
        "resolution_mode": "manifest",
        "manifest_path": str(manifest_path),
        "manifest_scope_hash": manifest_scope_hash,
        "ambiguous_resolution": [],
    }
    return mapping, meta


def resolve_scan_inputs(args: argparse.Namespace) -> tuple[dict[str, str], dict[str, Any]]:
    roots = [Path(args.input_root), Path(args.logs_root)]
    fair_filter = {norm_text(v) for v in args.fair_slug if norm_text(v)}
    gallery_filter = {norm_text(v) for v in args.gallery_name if norm_text(v)}

    patterns = artifact_patterns()
    mapping: dict[str, str] = {key: "" for key in ALL_INPUT_KEYS}
    ambiguous_resolution: list[dict[str, Any]] = []

    for key in ALL_INPUT_KEYS:
        candidates: list[Path] = []
        for root in roots:
            if not root.exists():
                continue
            for pattern in patterns.get(key, []):
                candidates.extend([path for path in root.glob(pattern) if path.is_file()])
        candidates = sorted(set(candidates))
        candidates = [
            path
            for path in candidates
            if file_matches_scope(
                path=path,
                target_year=int(args.target_year),
                fair_filter=fair_filter,
                gallery_filter=gallery_filter,
            )
        ]

        if len(candidates) > 1:
            ambiguous_resolution.append({"artifact": key, "candidate_count": len(candidates)})
            if args.fail_on_ambiguous_input or args.strict:
                raise IntegrationError(
                    EXIT_SCHEMA_MISMATCH,
                    "ambiguous_input_candidates",
                    f"Ambiguous candidates for {key}: {len(candidates)}",
                )
        if candidates:
            latest = max(candidates, key=lambda p: p.stat().st_mtime)
            mapping[key] = str(latest)

    meta = {"resolution_mode": "scan", "ambiguous_resolution": ambiguous_resolution}
    return mapping, meta


def resolve_inputs(args: argparse.Namespace) -> tuple[dict[str, str], dict[str, Any]]:
    if args.mode == "explicit":
        return resolve_explicit_inputs(args)
    if args.mode == "manifest":
        return resolve_manifest_inputs(args)
    if args.mode == "scan":
        return resolve_scan_inputs(args)
    raise IntegrationError(EXIT_SCHEMA_MISMATCH, "unsupported_mode", f"Unsupported mode: {args.mode}")


def compute_scope_hash(target_year: int, fair_filter: list[str], lane: str, gallery_filter: list[str]) -> str:
    scope_payload = {
        "target_year": int(target_year),
        "fair_slug": sorted([norm_text(v) for v in fair_filter if norm_text(v)]),
        "lane": norm_text(lane),
        "gallery_name": sorted([norm_text(v) for v in gallery_filter if norm_text(v)]),
    }
    encoded = json.dumps(scope_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha1(encoded).hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_markdown(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

def filter_csv_by_scope(
    src: Path,
    dst: Path,
    target_year: int,
    fair_filter: set[str],
    gallery_filter: set[str],
) -> tuple[int, int]:
    with src.open("r", encoding="utf-8-sig", newline="") as fin:
        reader = csv.DictReader(fin)
        if reader.fieldnames is None:
            raise IntegrationError(EXIT_SCHEMA_MISMATCH, "csv_has_no_header", f"CSV has no header: {src}")
        fieldnames = [norm_text(v) for v in reader.fieldnames]
        rows: list[dict[str, str]] = []
        for row in reader:
            normalized = {norm_text(k): norm_text(v) for k, v in (row or {}).items()}
            keep = True
            if "target_year" in fieldnames:
                try:
                    keep = keep and int(float(norm_text(normalized.get("target_year", "")))) == int(target_year)
                except ValueError:
                    keep = False
            if fair_filter and "fair_slug" in fieldnames:
                keep = keep and norm_text(normalized.get("fair_slug")) in fair_filter
            if gallery_filter:
                if "gallery_name_en" not in fieldnames:
                    raise IntegrationError(
                        EXIT_SCHEMA_MISMATCH,
                        "gallery_filter_without_gallery_column",
                        f"Gallery filter requested but gallery_name_en missing: {src}",
                    )
                keep = keep and norm_text(normalized.get("gallery_name_en")) in gallery_filter
            if keep:
                rows.append(normalized)

    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w", encoding="utf-8", newline="") as fout:
        writer = csv.DictWriter(fout, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})
    return len(rows), len(fieldnames)


def validate_preflight(
    resolved_inputs: dict[str, str],
    target_year: int,
    fair_filter: set[str],
    gallery_filter: set[str],
    strict: bool,
) -> None:
    for key in REQUIRED_INPUT_KEYS:
        path_text = norm_text(resolved_inputs.get(key))
        if not path_text:
            raise IntegrationError(
                EXIT_MISSING_REQUIRED_ARTIFACT,
                "missing_required_artifact",
                f"Required artifact unresolved: {key}",
            )
        if not Path(path_text).exists():
            raise IntegrationError(
                EXIT_MISSING_REQUIRED_ARTIFACT,
                "missing_required_artifact",
                f"Required artifact not found: {key}:{path_text}",
            )
    if strict:
        runtime_path = norm_text(resolved_inputs.get("authoritative_runtime_csv"))
        if not runtime_path or not Path(runtime_path).exists():
            raise IntegrationError(
                EXIT_MISSING_REQUIRED_ARTIFACT,
                "missing_conditional_required_artifact",
                "authoritative_runtime_csv is required in strict mode",
            )

    master_path = Path(resolved_inputs["authoritative_master_csv"])
    seed_path = Path(resolved_inputs["seed_evaluation_csv"])
    summary_path = Path(resolved_inputs["gallery_summary_csv"])
    decision_path = Path(resolved_inputs["trial_ready_decision_csv"])

    master_fields, master_rows = csv_head_rows(master_path, max_rows=5000)
    ensure_columns(master_path, master_fields, ["fair_slug", "gallery_name_en", "source_url"])
    seed_fields, _ = csv_head_rows(seed_path, max_rows=5000)
    ensure_columns(seed_path, seed_fields, ["gallery_name_en", "fair_slug", "source_url"])
    summary_fields, _ = csv_head_rows(summary_path, max_rows=5000)
    ensure_columns(
        summary_path,
        summary_fields,
        ["gallery_name_en", "route_risk_rate", "year_risk_rate", "provenance_violations", "duplicate_anomaly_groups"],
    )
    decision_fields, _ = csv_head_rows(decision_path, max_rows=5000)
    ensure_columns(
        decision_path,
        decision_fields,
        [
            "gallery_name_en",
            "trial_ready_seed_count",
            "route_risk_rate",
            "year_risk_rate",
            "provenance_violations",
            "duplicate_anomaly_groups",
        ],
    )

    if fair_filter:
        fairs_in_master = {norm_text(row.get("fair_slug")) for row in master_rows}
        if not (fairs_in_master & fair_filter):
            raise IntegrationError(
                EXIT_SCHEMA_MISMATCH,
                "scope_conflict_fair",
                f"No master rows match fair filter: {sorted(fair_filter)}",
            )
    if gallery_filter:
        galleries_in_master = {norm_text(row.get("gallery_name_en")) for row in master_rows}
        if not (galleries_in_master & gallery_filter):
            raise IntegrationError(
                EXIT_SCHEMA_MISMATCH,
                "scope_conflict_gallery",
                f"No master rows match gallery filter: {sorted(gallery_filter)}",
            )

    if "target_year" in master_fields:
        has_year = False
        for row in master_rows:
            try:
                if int(float(norm_text(row.get("target_year")))) == int(target_year):
                    has_year = True
                    break
            except ValueError:
                continue
        if not has_year:
            raise IntegrationError(
                EXIT_EMPTY_INPUT,
                "empty_input_target_year",
                f"No master rows match target_year={target_year}",
            )


def build_classification_command(
    args: argparse.Namespace,
    inputs: dict[str, str],
    output_dir: Path,
    classification_run_id: str,
) -> list[str]:
    cmd = [
        sys.executable,
        str(Path(args.classification_cli_path)),
        "--authoritative-master-csv",
        inputs["authoritative_master_csv"],
        "--seed-eval-csv",
        inputs["seed_evaluation_csv"],
        "--gallery-summary-csv",
        inputs["gallery_summary_csv"],
        "--trial-ready-decision-csv",
        inputs["trial_ready_decision_csv"],
        "--target-year",
        str(args.target_year),
        "--lane",
        args.lane,
        "--output-dir",
        str(output_dir),
        "--run-id",
        classification_run_id,
        "--safe-max-galleries",
        str(args.safe_max_galleries),
        "--safe-max-seeds",
        str(args.safe_max_seeds),
        "--guard-max-galleries-min",
        str(args.guard_max_galleries_min),
        "--guard-max-galleries-max",
        str(args.guard_max_galleries_max),
        "--guard-max-seeds",
        str(args.guard_max_seeds),
    ]
    if norm_text(inputs.get("authoritative_runtime_csv")):
        cmd.extend(["--authoritative-runtime-csv", inputs["authoritative_runtime_csv"]])
    if norm_text(inputs.get("defer_queue_csv")):
        cmd.extend(["--defer-queue-csv", inputs["defer_queue_csv"]])
    if norm_text(inputs.get("reject_queue_csv")):
        cmd.extend(["--reject-queue-csv", inputs["reject_queue_csv"]])
    for fair_slug in args.fair_slug:
        if norm_text(fair_slug):
            cmd.extend(["--fair-slug", norm_text(fair_slug)])
    if args.strict:
        cmd.extend(["--strict", "--fail-on-missing-artifacts", "--fail-on-schema-drift"])
    if args.allow_unit_size_override:
        cmd.append("--allow-unit-size-override")
    if args.write_report_md:
        cmd.append("--write-report-md")
    if args.write_manifest:
        cmd.append("--write-manifest")
    if args.dry_run:
        cmd.append("--dry-run")
    return cmd


def integration_status_from_exit(exit_code: int) -> str:
    if exit_code == EXIT_OK:
        return "success"
    if exit_code == EXIT_HOLD:
        return "hold"
    if exit_code in {EXIT_MISSING_REQUIRED_ARTIFACT, EXIT_SCHEMA_MISMATCH, EXIT_METRIC_CALCULATION_ERROR, EXIT_EMPTY_INPUT}:
        return "fail_fast"
    if exit_code == EXIT_INTERNAL_ERROR:
        return "internal_failure"
    return "internal_failure"


def expected_classification_output_paths(output_dir: Path, classification_run_id: str) -> dict[str, Path]:
    prefix = "exhibitions_image_task_t192_"
    return {
        "classification_summary_json": output_dir / f"{prefix}classification_summary_{classification_run_id}.json",
        "classification_decision_csv": output_dir / f"{prefix}classification_decision_{classification_run_id}.csv",
        "lane_ready_inventory_csv": output_dir / f"{prefix}lane_ready_inventory_{classification_run_id}.csv",
        "unit_plan_csv": output_dir / f"{prefix}unit_plan_{classification_run_id}.csv",
        "defer_queue_csv": output_dir / f"{prefix}defer_queue_{classification_run_id}.csv",
        "reject_queue_csv": output_dir / f"{prefix}reject_queue_{classification_run_id}.csv",
        "classification_report_md": output_dir / f"{prefix}classification_report_{classification_run_id}.md",
        "classification_manifest_json": output_dir / f"{prefix}manifest_{classification_run_id}.json",
    }


def tail_text(text: str, max_lines: int = 14) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return ""
    return "\n".join(lines[-max_lines:])

def main() -> int:
    args = parse_args()
    started_at = utc_now_iso()
    bundle_id = norm_text(args.bundle_id) or f"{utc_compact()}-bundle"
    classification_run_id = norm_text(args.classification_run_id) or f"{utc_compact()}-classification"
    output_dir = Path(args.output_dir)
    fair_filter = {norm_text(v) for v in args.fair_slug if norm_text(v)}
    gallery_filter = {norm_text(v) for v in args.gallery_name if norm_text(v)}
    scope_hash = compute_scope_hash(
        target_year=int(args.target_year),
        fair_filter=list(fair_filter),
        lane=norm_text(args.lane),
        gallery_filter=list(gallery_filter),
    )

    output_paths = {
        "resolved_input_manifest_json": output_dir / f"exhibitions_image_task_t195_resolved_input_manifest_{bundle_id}.json",
        "classification_bundle_manifest_json": output_dir / f"exhibitions_image_task_t195_classification_bundle_manifest_{bundle_id}.json",
        "classification_integration_summary_json": output_dir / f"exhibitions_image_task_t195_classification_integration_summary_{bundle_id}.json",
        "classification_integration_report_md": output_dir / f"exhibitions_image_task_t195_classification_integration_report_{bundle_id}.md",
        "handoff_paths_json": output_dir / f"exhibitions_image_task_t195_handoff_paths_{bundle_id}.json",
    }

    try:
        for path in output_paths.values():
            if path.exists():
                raise IntegrationError(
                    EXIT_SCHEMA_MISMATCH,
                    "output_collision",
                    f"Output collision: {path}",
                )

        resolved_inputs, resolution_meta = resolve_inputs(args)

        validate_preflight(
            resolved_inputs=resolved_inputs,
            target_year=int(args.target_year),
            fair_filter=fair_filter,
            gallery_filter=gallery_filter,
            strict=bool(args.strict),
        )

        scoped_inputs = dict(resolved_inputs)
        scoped_input_counts: dict[str, int] = {}
        if fair_filter or gallery_filter:
            scope_dir = output_dir / f"task_t195_scoped_inputs_{bundle_id}"
            for key in ALL_INPUT_KEYS:
                source_text = norm_text(resolved_inputs.get(key))
                if not source_text:
                    continue
                source = Path(source_text)
                if not source.exists():
                    continue
                dst = scope_dir / f"{key}.csv"
                row_count, _ = filter_csv_by_scope(
                    src=source,
                    dst=dst,
                    target_year=int(args.target_year),
                    fair_filter=fair_filter,
                    gallery_filter=gallery_filter,
                )
                scoped_inputs[key] = str(dst)
                scoped_input_counts[key] = row_count

        resolved_input_payload = {
            "task_id": "TASK195",
            "bundle_id": bundle_id,
            "classification_run_id": classification_run_id,
            "created_at": utc_now_iso(),
            "resolution_mode": resolution_meta.get("resolution_mode"),
            "resolution_meta": resolution_meta,
            "scope": {
                "target_year": int(args.target_year),
                "fair_slug": sorted(list(fair_filter)),
                "lane": args.lane,
                "gallery_name": sorted(list(gallery_filter)),
                "scope_hash": scope_hash,
            },
            "resolved_inputs": scoped_inputs,
            "scoped_input_counts": scoped_input_counts,
        }
        write_json(output_paths["resolved_input_manifest_json"], resolved_input_payload)

        command = build_classification_command(
            args=args,
            inputs=scoped_inputs,
            output_dir=output_dir,
            classification_run_id=classification_run_id,
        )
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        classification_exit_code = int(completed.returncode)
        status = integration_status_from_exit(classification_exit_code)
        classification_outputs = expected_classification_output_paths(output_dir, classification_run_id)
        existing_outputs = {name: str(path) for name, path in classification_outputs.items() if path.exists()}

        next_handoff_allowed = bool(status == "success")
        manual_review_required = bool(status in {"hold", "internal_failure"})
        retry_recommended = bool(status in {"fail_fast", "internal_failure"})
        handoff_payload = {
            "task_id": "TASK195",
            "bundle_id": bundle_id,
            "classification_run_id": classification_run_id,
            "integration_status": status,
            "next_handoff_allowed": next_handoff_allowed,
            "required_paths": {
                "lane_ready_inventory_csv": str(classification_outputs["lane_ready_inventory_csv"]),
                "unit_plan_csv": str(classification_outputs["unit_plan_csv"]),
                "classification_decision_csv": str(classification_outputs["classification_decision_csv"]),
            },
            "optional_paths": {
                "defer_queue_csv": str(classification_outputs["defer_queue_csv"]),
                "reject_queue_csv": str(classification_outputs["reject_queue_csv"]),
                "classification_summary_json": str(classification_outputs["classification_summary_json"]),
                "classification_manifest_json": str(classification_outputs["classification_manifest_json"]),
            },
            "existing_paths": existing_outputs,
            "scope_hash": scope_hash,
        }
        write_json(output_paths["handoff_paths_json"], handoff_payload)

        integration_summary = {
            "task_id": "TASK195",
            "bundle_id": bundle_id,
            "classification_run_id": classification_run_id,
            "started_at": started_at,
            "completed_at": utc_now_iso(),
            "mode": args.mode,
            "target_year": int(args.target_year),
            "lane": args.lane,
            "fair_slug": sorted(list(fair_filter)),
            "gallery_name": sorted(list(gallery_filter)),
            "scope_hash": scope_hash,
            "classification_exit_code": classification_exit_code,
            "integration_status": status,
            "next_handoff_allowed": next_handoff_allowed,
            "manual_review_required": manual_review_required,
            "retry_recommended": retry_recommended,
            "resolved_input_manifest_json": str(output_paths["resolved_input_manifest_json"]),
            "handoff_paths_json": str(output_paths["handoff_paths_json"]),
            "classification_command": command,
            "classification_stdout_tail": tail_text(completed.stdout or ""),
            "classification_stderr_tail": tail_text(completed.stderr or ""),
            "classification_outputs_existing": existing_outputs,
        }
        write_json(output_paths["classification_integration_summary_json"], integration_summary)

        bundle_manifest = {
            "task_id": "TASK195",
            "bundle_id": bundle_id,
            "classification_run_id": classification_run_id,
            "created_at": utc_now_iso(),
            "scope_hash": scope_hash,
            "resolved_input_manifest_json": str(output_paths["resolved_input_manifest_json"]),
            "classification_integration_summary_json": str(output_paths["classification_integration_summary_json"]),
            "classification_integration_report_md": str(output_paths["classification_integration_report_md"]),
            "handoff_paths_json": str(output_paths["handoff_paths_json"]),
            "classification_outputs": {k: str(v) for k, v in classification_outputs.items()},
            "integration_status": status,
        }
        write_json(output_paths["classification_bundle_manifest_json"], bundle_manifest)

        report_lines = [
            "# TASK195 Classification Integration Runner Report",
            "",
            f"- bundle_id: `{bundle_id}`",
            f"- classification_run_id: `{classification_run_id}`",
            f"- mode: `{args.mode}`",
            f"- target_year: `{args.target_year}`",
            f"- lane: `{args.lane}`",
            f"- fair_slug_count: `{len(fair_filter)}`",
            f"- gallery_name_count: `{len(gallery_filter)}`",
            f"- scope_hash: `{scope_hash}`",
            f"- classification_exit_code: `{classification_exit_code}`",
            f"- integration_status: `{status}`",
            f"- next_handoff_allowed: `{str(next_handoff_allowed).lower()}`",
            f"- manual_review_required: `{str(manual_review_required).lower()}`",
            f"- retry_recommended: `{str(retry_recommended).lower()}`",
            "",
            "## Bundle Paths",
            f"- resolved_input_manifest_json: `{output_paths['resolved_input_manifest_json']}`",
            f"- classification_bundle_manifest_json: `{output_paths['classification_bundle_manifest_json']}`",
            f"- classification_integration_summary_json: `{output_paths['classification_integration_summary_json']}`",
            f"- handoff_paths_json: `{output_paths['handoff_paths_json']}`",
            "",
            "## Classification Output Presence",
        ]
        for key, path in classification_outputs.items():
            report_lines.append(f"- {key}: `{path}` (exists={str(path.exists()).lower()})")
        write_markdown(output_paths["classification_integration_report_md"], report_lines)

        return classification_exit_code

    except IntegrationError as err:
        failure_summary = {
            "task_id": "TASK195",
            "bundle_id": bundle_id,
            "classification_run_id": classification_run_id,
            "started_at": started_at,
            "completed_at": utc_now_iso(),
            "integration_status": "preflight_failed",
            "failure_reason_code": err.reason_code,
            "failure_message": err.message,
            "target_year": int(args.target_year),
            "lane": args.lane,
            "fair_slug": sorted(list(fair_filter)),
            "gallery_name": sorted(list(gallery_filter)),
            "scope_hash": scope_hash,
        }
        write_json(output_paths["classification_integration_summary_json"], failure_summary)
        write_markdown(
            output_paths["classification_integration_report_md"],
            [
                "# TASK195 Classification Integration Runner Report",
                "",
                f"- integration_status: `preflight_failed`",
                f"- failure_reason_code: `{err.reason_code}`",
                f"- failure_message: `{err.message}`",
            ],
        )
        return err.code
    except Exception as err:  # pragma: no cover
        failure_summary = {
            "task_id": "TASK195",
            "bundle_id": bundle_id,
            "classification_run_id": classification_run_id,
            "started_at": started_at,
            "completed_at": utc_now_iso(),
            "integration_status": "internal_failure",
            "failure_reason_code": "integration_internal_error",
            "failure_message": str(err),
            "target_year": int(args.target_year),
            "lane": args.lane,
            "fair_slug": sorted(list(fair_filter)),
            "gallery_name": sorted(list(gallery_filter)),
            "scope_hash": scope_hash,
        }
        write_json(output_paths["classification_integration_summary_json"], failure_summary)
        write_markdown(
            output_paths["classification_integration_report_md"],
            [
                "# TASK195 Classification Integration Runner Report",
                "",
                f"- integration_status: `internal_failure`",
                f"- failure_message: `{err}`",
            ],
        )
        return EXIT_INTERNAL_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
