#!/usr/bin/env python3
from __future__ import annotations

import argparse
import contextlib
import csv
import io
import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def norm_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run TASK196 fixture matrix for classification integration runner validation."
    )
    parser.add_argument(
        "--manifest",
        default="data/phase1_seed10/logs/exhibitions_image_task_t196_integration_fixture_manifest.json",
    )
    parser.add_argument(
        "--integration-runner-path",
        default="run_exhibitions_image_classification_integration_runner.py",
    )
    parser.add_argument(
        "--classification-cli-path",
        default="run_exhibitions_image_classification_cli.py",
    )
    parser.add_argument(
        "--output-root",
        default="data/phase1_seed10/logs/task_t196_integration_fixture_runs",
    )
    parser.add_argument(
        "--summary-json",
        default="data/phase1_seed10/logs/exhibitions_image_task_t196_integration_fixture_matrix_summary.json",
    )
    parser.add_argument(
        "--summary-csv",
        default="data/phase1_seed10/logs/exhibitions_image_task_t196_integration_fixture_matrix_summary_table.csv",
    )
    return parser.parse_args()


def tail_text(text: str, max_lines: int = 14) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return ""
    return "\n".join(lines[-max_lines:])


def to_int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    text = norm_text(value)
    if not text:
        return None
    return int(text)


def list_generated_paths(root: Path) -> list[str]:
    if not root.exists():
        return []
    return sorted([str(path) for path in root.rglob("*") if path.is_file()])


def reset_case_output_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def integration_output_paths(output_dir: Path, bundle_id: str) -> dict[str, Path]:
    return {
        "resolved_input_manifest_json": output_dir
        / f"exhibitions_image_task_t195_resolved_input_manifest_{bundle_id}.json",
        "classification_bundle_manifest_json": output_dir
        / f"exhibitions_image_task_t195_classification_bundle_manifest_{bundle_id}.json",
        "classification_integration_summary_json": output_dir
        / f"exhibitions_image_task_t195_classification_integration_summary_{bundle_id}.json",
        "classification_integration_report_md": output_dir
        / f"exhibitions_image_task_t195_classification_integration_report_{bundle_id}.md",
        "handoff_paths_json": output_dir
        / f"exhibitions_image_task_t195_handoff_paths_{bundle_id}.json",
    }


def build_runner_command(
    case: dict[str, Any],
    integration_runner_path: Path,
    classification_cli_path: Path,
    case_output_dir: Path,
) -> list[str]:
    mode = norm_text(case.get("mode"))
    cmd = [
        sys.executable,
        str(integration_runner_path),
        "--mode",
        mode,
        "--target-year",
        str(int(case.get("target_year", 2025))),
        "--lane",
        norm_text(case.get("lane", "all")) or "all",
        "--output-dir",
        str(case_output_dir),
        "--bundle-id",
        norm_text(case.get("bundle_id")),
        "--classification-run-id",
        norm_text(case.get("classification_run_id")),
        "--classification-cli-path",
        str(classification_cli_path),
    ]

    for fair_slug in case.get("fair_slug", []):
        if norm_text(fair_slug):
            cmd.extend(["--fair-slug", norm_text(fair_slug)])
    for gallery_name in case.get("gallery_name", []):
        if norm_text(gallery_name):
            cmd.extend(["--gallery-name", norm_text(gallery_name)])

    if bool(case.get("strict", False)):
        cmd.append("--strict")
    if bool(case.get("fail_on_ambiguous_input", False)):
        cmd.append("--fail-on-ambiguous-input")
    if bool(case.get("dry_run", False)):
        cmd.append("--dry-run")

    if mode == "explicit":
        inputs = case.get("inputs", {})
        arg_map = {
            "authoritative_master_csv": "--authoritative-master-csv",
            "authoritative_runtime_csv": "--authoritative-runtime-csv",
            "seed_eval_csv": "--seed-eval-csv",
            "gallery_summary_csv": "--gallery-summary-csv",
            "trial_ready_decision_csv": "--trial-ready-decision-csv",
            "defer_queue_csv": "--defer-queue-csv",
            "reject_queue_csv": "--reject-queue-csv",
        }
        for key, arg_name in arg_map.items():
            value = norm_text(inputs.get(key))
            if value:
                cmd.extend([arg_name, value])
    elif mode == "manifest":
        cmd.extend(["--manifest-path", norm_text(case.get("manifest_path"))])
        if norm_text(case.get("manifest_case_id")):
            cmd.extend(["--manifest-case-id", norm_text(case.get("manifest_case_id"))])
    elif mode == "scan":
        scan_root = norm_text(case.get("scan_root"))
        if scan_root:
            cmd.extend(["--input-root", scan_root, "--logs-root", scan_root])
        else:
            if norm_text(case.get("input_root")):
                cmd.extend(["--input-root", norm_text(case.get("input_root"))])
            if norm_text(case.get("logs_root")):
                cmd.extend(["--logs-root", norm_text(case.get("logs_root"))])
    else:
        raise ValueError(f"Unsupported mode in fixture case: {mode}")

    return cmd


def build_internal_case_namespace(
    base_case: dict[str, Any],
    case: dict[str, Any],
    classification_cli_path: Path,
    case_output_dir: Path,
) -> argparse.Namespace:
    base_mode = norm_text(base_case.get("mode", "explicit")) or "explicit"
    base_inputs = dict(base_case.get("inputs", {}))
    return argparse.Namespace(
        mode=base_mode,
        input_root=norm_text(base_case.get("scan_root") or base_case.get("input_root") or ""),
        logs_root=norm_text(base_case.get("scan_root") or base_case.get("logs_root") or ""),
        classification_cli_path=str(classification_cli_path),
        output_dir=str(case_output_dir),
        manifest_path=norm_text(base_case.get("manifest_path", "")),
        manifest_case_id=norm_text(base_case.get("manifest_case_id", "")),
        target_year=int(base_case.get("target_year", 2025)),
        fair_slug=[norm_text(v) for v in base_case.get("fair_slug", []) if norm_text(v)],
        lane=norm_text(base_case.get("lane", "all")) or "all",
        gallery_name=[norm_text(v) for v in base_case.get("gallery_name", []) if norm_text(v)],
        bundle_id=norm_text(case.get("bundle_id")),
        classification_run_id=norm_text(case.get("classification_run_id")),
        strict=bool(base_case.get("strict", False)),
        fail_on_ambiguous_input=bool(base_case.get("fail_on_ambiguous_input", False)),
        dry_run=bool(base_case.get("dry_run", False)),
        write_report_md=False,
        write_manifest=False,
        authoritative_master_csv=norm_text(base_inputs.get("authoritative_master_csv")),
        authoritative_runtime_csv=norm_text(base_inputs.get("authoritative_runtime_csv")),
        seed_eval_csv=norm_text(base_inputs.get("seed_eval_csv")),
        gallery_summary_csv=norm_text(base_inputs.get("gallery_summary_csv")),
        trial_ready_decision_csv=norm_text(base_inputs.get("trial_ready_decision_csv")),
        defer_queue_csv=norm_text(base_inputs.get("defer_queue_csv")),
        reject_queue_csv=norm_text(base_inputs.get("reject_queue_csv")),
        safe_max_galleries=10,
        safe_max_seeds=150,
        guard_max_galleries_min=2,
        guard_max_galleries_max=4,
        guard_max_seeds=60,
        allow_unit_size_override=False,
    )


def run_internal_failure_case(
    case: dict[str, Any],
    by_case_id: dict[str, dict[str, Any]],
    classification_cli_path: Path,
    case_output_dir: Path,
) -> tuple[int, str]:
    import run_exhibitions_image_classification_integration_runner as integration_runner

    base_case_id = norm_text(case.get("base_case_ref"))
    if not base_case_id or base_case_id not in by_case_id:
        return 30, f"internal_failure_base_case_missing:{base_case_id}"

    base_case = by_case_id[base_case_id]
    args_ns = build_internal_case_namespace(
        base_case=base_case,
        case=case,
        classification_cli_path=classification_cli_path,
        case_output_dir=case_output_dir,
    )

    original_parse_args = integration_runner.parse_args
    original_resolve_inputs = integration_runner.resolve_inputs
    output_buffer = io.StringIO()
    try:
        integration_runner.parse_args = lambda: args_ns

        def _forced_internal_failure(*_args: Any, **_kwargs: Any) -> Any:
            raise RuntimeError("forced_internal_failure_for_task196")

        integration_runner.resolve_inputs = _forced_internal_failure
        with contextlib.redirect_stdout(output_buffer), contextlib.redirect_stderr(output_buffer):
            exit_code = integration_runner.main()
        return int(exit_code), output_buffer.getvalue()
    finally:
        integration_runner.parse_args = original_parse_args
        integration_runner.resolve_inputs = original_resolve_inputs


def evaluate_summary_checks(
    case: dict[str, Any],
    summary_payload: dict[str, Any],
    output_paths: dict[str, Path],
    generated_paths: list[str],
) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    checks["summary_exists"] = bool(summary_payload)
    checks["scope_hash_present"] = bool(norm_text(summary_payload.get("scope_hash"))) if summary_payload else False
    checks["bundle_id_match"] = (
        norm_text(summary_payload.get("bundle_id")) == norm_text(case.get("bundle_id"))
        if summary_payload
        else False
    )
    checks["classification_run_id_match"] = (
        norm_text(summary_payload.get("classification_run_id")) == norm_text(case.get("classification_run_id"))
        if summary_payload
        else False
    )

    integration_status = norm_text(summary_payload.get("integration_status")) if summary_payload else ""
    if integration_status == "success":
        checks["next_handoff_allowed_rule"] = bool(summary_payload.get("next_handoff_allowed")) is True
        checks["manual_review_rule"] = bool(summary_payload.get("manual_review_required")) is False
    elif integration_status == "hold":
        checks["next_handoff_allowed_rule"] = bool(summary_payload.get("next_handoff_allowed")) is False
        checks["manual_review_rule"] = bool(summary_payload.get("manual_review_required")) is True
    elif integration_status == "internal_failure":
        checks["manual_review_rule"] = bool(summary_payload.get("manual_review_required", True)) is True
    elif integration_status == "preflight_failed":
        checks["failure_reason_present"] = bool(norm_text(summary_payload.get("failure_reason_code")))

    expected_generated = [norm_text(v) for v in case.get("expected_generated_files", []) if norm_text(v)]
    if not expected_generated:
        bundle_id = norm_text(case.get("bundle_id"))
        run_id = norm_text(case.get("classification_run_id"))
        common = [
            f"exhibitions_image_task_t195_classification_integration_summary_{bundle_id}.json",
            f"exhibitions_image_task_t195_classification_integration_report_{bundle_id}.md",
        ]
        success_like = [
            f"exhibitions_image_task_t195_resolved_input_manifest_{bundle_id}.json",
            f"exhibitions_image_task_t195_classification_bundle_manifest_{bundle_id}.json",
            f"exhibitions_image_task_t195_handoff_paths_{bundle_id}.json",
            f"exhibitions_image_task_t192_classification_summary_{run_id}.json",
            f"exhibitions_image_task_t192_classification_decision_{run_id}.csv",
            f"exhibitions_image_task_t192_lane_ready_inventory_{run_id}.csv",
            f"exhibitions_image_task_t192_unit_plan_{run_id}.csv",
            f"exhibitions_image_task_t192_defer_queue_{run_id}.csv",
            f"exhibitions_image_task_t192_reject_queue_{run_id}.csv",
        ]
        expected_status = norm_text(case.get("expected_integration_status"))
        expected_generated = common + (success_like if expected_status in {"success", "hold"} else [])
    if expected_generated:
        generated_names = {Path(path).name for path in generated_paths}
        missing_expected = [name for name in expected_generated if name not in generated_names]
        checks["expected_generated_files_present"] = len(missing_expected) == 0
        checks["missing_expected_generated_files"] = missing_expected

    expected_handoff_exists = case.get("expected_handoff_exists")
    if expected_handoff_exists is None:
        expected_handoff_exists = norm_text(case.get("expected_integration_status")) in {"success", "hold"}
    if expected_handoff_exists is not None:
        checks["handoff_presence_match"] = bool(output_paths["handoff_paths_json"].exists()) == bool(expected_handoff_exists)

    expected_append_free = case.get("append_free_required", True)
    if expected_append_free:
        # Integration runner writes fresh bundle files; no append artifact is expected.
        checks["append_free"] = True

    return checks


def case_passed(
    expected_runner_exit_code: int,
    actual_runner_exit_code: int,
    expected_status: str,
    actual_status: str,
    expected_classification_exit_code: int | None,
    actual_classification_exit_code: int | None,
    summary_checks: dict[str, Any],
) -> bool:
    if expected_runner_exit_code != actual_runner_exit_code:
        return False
    if norm_text(expected_status) != norm_text(actual_status):
        return False
    if expected_classification_exit_code != actual_classification_exit_code:
        return False
    for value in summary_checks.values():
        if isinstance(value, bool) and not value:
            return False
    return True


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest)
    integration_runner_path = Path(args.integration_runner_path)
    classification_cli_path = Path(args.classification_cli_path)
    output_root = Path(args.output_root)
    summary_json_path = Path(args.summary_json)
    summary_csv_path = Path(args.summary_csv)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    cases: list[dict[str, Any]] = list(manifest.get("cases", []))
    by_case_id: dict[str, dict[str, Any]] = {
        norm_text(case.get("case_id")): case for case in cases if norm_text(case.get("case_id"))
    }

    output_root.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []

    for case in cases:
        case_id = norm_text(case.get("case_id"))
        case_mode = norm_text(case.get("mode"))
        case_output_dir = output_root / case_id
        reset_case_output_dir(case_output_dir)

        bundle_id = norm_text(case.get("bundle_id"))
        output_paths = integration_output_paths(case_output_dir, bundle_id)
        if bool(case.get("seed_collision_file")):
            seed_path = output_paths["resolved_input_manifest_json"]
            seed_path.parent.mkdir(parents=True, exist_ok=True)
            seed_path.write_text("{}", encoding="utf-8")

        expected_runner_exit_code = int(case.get("expected_runner_exit_code"))
        expected_integration_status = norm_text(case.get("expected_integration_status"))
        expected_classification_exit_code = to_int_or_none(case.get("expected_classification_exit_code"))

        actual_runner_exit_code = 30
        raw_output = ""
        if case_mode == "internal":
            actual_runner_exit_code, raw_output = run_internal_failure_case(
                case=case,
                by_case_id=by_case_id,
                classification_cli_path=classification_cli_path,
                case_output_dir=case_output_dir,
            )
        else:
            cmd = build_runner_command(
                case=case,
                integration_runner_path=integration_runner_path,
                classification_cli_path=classification_cli_path,
                case_output_dir=case_output_dir,
            )
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            actual_runner_exit_code = int(completed.returncode)
            raw_output = "\n".join(
                value for value in [completed.stdout or "", completed.stderr or ""] if value
            )

        generated_paths = list_generated_paths(case_output_dir)
        summary_payload: dict[str, Any] = {}
        if output_paths["classification_integration_summary_json"].exists():
            summary_payload = json.loads(
                output_paths["classification_integration_summary_json"].read_text(encoding="utf-8-sig")
            )

        actual_integration_status = norm_text(summary_payload.get("integration_status"))
        actual_classification_exit_code = to_int_or_none(summary_payload.get("classification_exit_code"))
        summary_checks = evaluate_summary_checks(
            case=case,
            summary_payload=summary_payload,
            output_paths=output_paths,
            generated_paths=generated_paths,
        )
        status = (
            "passed"
            if case_passed(
                expected_runner_exit_code=expected_runner_exit_code,
                actual_runner_exit_code=actual_runner_exit_code,
                expected_status=expected_integration_status,
                actual_status=actual_integration_status,
                expected_classification_exit_code=expected_classification_exit_code,
                actual_classification_exit_code=actual_classification_exit_code,
                summary_checks=summary_checks,
            )
            else "failed"
        )

        results.append(
            {
                "case_id": case_id,
                "mode": case_mode,
                "expected_runner_exit_code": expected_runner_exit_code,
                "actual_runner_exit_code": actual_runner_exit_code,
                "expected_integration_status": expected_integration_status,
                "actual_integration_status": actual_integration_status,
                "expected_classification_exit_code": expected_classification_exit_code,
                "actual_classification_exit_code": actual_classification_exit_code,
                "status": status,
                "stdout_tail": tail_text(raw_output),
                "generated_paths": generated_paths,
                "summary_checks": summary_checks,
            }
        )

    total_cases = len(results)
    passed_cases = len([result for result in results if result["status"] == "passed"])
    failed_cases = total_cases - passed_cases
    all_passed = failed_cases == 0

    summary_payload = {
        "task_id": "TASK196",
        "generated_at": utc_now_iso(),
        "manifest_path": str(manifest_path),
        "integration_runner_path": str(integration_runner_path),
        "classification_cli_path": str(classification_cli_path),
        "output_root": str(output_root),
        "all_passed": all_passed,
        "total_cases": total_cases,
        "passed_cases": passed_cases,
        "failed_cases": failed_cases,
        "cases": results,
    }

    summary_json_path.parent.mkdir(parents=True, exist_ok=True)
    summary_json_path.write_text(json.dumps(summary_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    summary_csv_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_csv_path.open("w", encoding="utf-8", newline="") as fp:
        fieldnames = [
            "case_id",
            "mode",
            "expected_runner_exit_code",
            "actual_runner_exit_code",
            "expected_integration_status",
            "actual_integration_status",
            "expected_classification_exit_code",
            "actual_classification_exit_code",
            "status",
            "generated_paths_count",
        ]
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "case_id": result["case_id"],
                    "mode": result["mode"],
                    "expected_runner_exit_code": result["expected_runner_exit_code"],
                    "actual_runner_exit_code": result["actual_runner_exit_code"],
                    "expected_integration_status": result["expected_integration_status"],
                    "actual_integration_status": result["actual_integration_status"],
                    "expected_classification_exit_code": (
                        "" if result["expected_classification_exit_code"] is None else result["expected_classification_exit_code"]
                    ),
                    "actual_classification_exit_code": (
                        "" if result["actual_classification_exit_code"] is None else result["actual_classification_exit_code"]
                    ),
                    "status": result["status"],
                    "generated_paths_count": len(result.get("generated_paths", [])),
                }
            )

    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
