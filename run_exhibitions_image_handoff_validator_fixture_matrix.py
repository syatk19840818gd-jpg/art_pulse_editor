
#!/usr/bin/env python3
from __future__ import annotations

import argparse
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
    return "" if value is None else str(value).strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run TASK197 handoff validator fixture matrix")
    parser.add_argument("--manifest", default="data/phase1_seed10/logs/exhibitions_image_task_t197_handoff_fixture_manifest.json")
    parser.add_argument("--validator-path", default="run_exhibitions_image_lane_ready_handoff_validator.py")
    parser.add_argument("--output-root", default="data/phase1_seed10/logs/task_t197_handoff_fixture_runs")
    parser.add_argument("--summary-json", default="data/phase1_seed10/logs/exhibitions_image_task_t197_handoff_fixture_matrix_summary.json")
    parser.add_argument("--summary-csv", default="data/phase1_seed10/logs/exhibitions_image_task_t197_handoff_fixture_matrix_summary_table.csv")
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def find_one(case_dir: Path, pattern: str) -> Path:
    matches = sorted(case_dir.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"pattern_not_found:{pattern}:{case_dir}")
    return matches[0]


def detect_inputs(case_dir: Path) -> dict[str, Path]:
    return {
        "bundle_manifest_json": find_one(case_dir, "exhibitions_image_task_t195_classification_bundle_manifest_*.json"),
        "integration_summary_json": find_one(case_dir, "exhibitions_image_task_t195_classification_integration_summary_*.json"),
        "handoff_paths_json": find_one(case_dir, "exhibitions_image_task_t195_handoff_paths_*.json"),
        "lane_ready_inventory_csv": find_one(case_dir, "exhibitions_image_task_t192_lane_ready_inventory_*.csv"),
        "unit_plan_csv": find_one(case_dir, "exhibitions_image_task_t192_unit_plan_*.csv"),
        "resolved_input_manifest_json": find_one(case_dir, "exhibitions_image_task_t195_resolved_input_manifest_*.json"),
    }


def tail_text(text: str, max_lines: int = 12) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return ""
    return "\n".join(lines[-max_lines:])


def drop_column(csv_path: Path, column: str) -> None:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as fp:
        reader = csv.DictReader(fp)
        fields = [f for f in (reader.fieldnames or []) if norm_text(f) and norm_text(f) != column]
        rows = list(reader)
    with csv_path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def mutate_case(case_dir: Path, inputs: dict[str, Path], mutate: str) -> None:
    if mutate == "remove_unit_plan":
        inputs["unit_plan_csv"].unlink(missing_ok=True)
        return
    if mutate == "drop_inventory_recommended_lane":
        drop_column(inputs["lane_ready_inventory_csv"], "recommended_lane")
        return
    if mutate == "scope_hash_mismatch":
        handoff = read_json(inputs["handoff_paths_json"])
        handoff["scope_hash"] = "scope_hash_mismatch_task197"
        write_json(inputs["handoff_paths_json"], handoff)
        return
    if mutate == "bundle_id_mismatch":
        summary = read_json(inputs["integration_summary_json"])
        summary["bundle_id"] = "bundle_id_mismatch_task197"
        write_json(inputs["integration_summary_json"], summary)
        return
    if mutate == "handoff_required_path_missing":
        handoff = read_json(inputs["handoff_paths_json"])
        required = dict(handoff.get("required_paths") or {})
        required["lane_ready_inventory_csv"] = str(case_dir / "does_not_exist_inventory.csv")
        handoff["required_paths"] = required
        write_json(inputs["handoff_paths_json"], handoff)
        return
    raise ValueError(f"unsupported_mutate:{mutate}")


def run_internal_failure_case(
    case_output_dir: Path,
    case_id: str,
    inputs: dict[str, Path],
) -> tuple[int, str]:
    import run_exhibitions_image_lane_ready_handoff_validator as validator

    args_ns = argparse.Namespace(
        bundle_manifest_json=str(inputs["bundle_manifest_json"]),
        integration_summary_json=str(inputs["integration_summary_json"]),
        handoff_paths_json=str(inputs["handoff_paths_json"]),
        lane_ready_inventory_csv=str(inputs["lane_ready_inventory_csv"]),
        unit_plan_csv=str(inputs["unit_plan_csv"]),
        resolved_input_manifest_json=str(inputs["resolved_input_manifest_json"]),
        output_dir=str(case_output_dir),
        run_id=f"task197-{case_id}",
        write_errors_csv=True,
        write_warnings_csv=True,
    )

    original_parse_args = validator.parse_args
    original_resolve = validator.resolve_input_paths
    buf = io.StringIO()
    try:
        validator.parse_args = lambda: args_ns

        def _boom(*_args: Any, **_kwargs: Any) -> Any:
            raise RuntimeError("forced_internal_failure_for_task197")

        validator.resolve_input_paths = _boom
        with io.StringIO() as _:
            pass
        # validator writes files; stdout/stderr are not needed for semantics
        exit_code = validator.main()
        return int(exit_code), buf.getvalue()
    finally:
        validator.parse_args = original_parse_args
        validator.resolve_input_paths = original_resolve


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest)
    validator_path = Path(args.validator_path)
    output_root = Path(args.output_root)
    summary_json_path = Path(args.summary_json)
    summary_csv_path = Path(args.summary_csv)

    manifest = read_json(manifest_path)
    cases = list(manifest.get("cases", []))
    output_root.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    for case in cases:
        case_id = norm_text(case.get("case_id"))
        case_type = norm_text(case.get("type"))
        base_case_dir = Path(norm_text(case.get("base_case_dir")))
        case_output_dir = output_root / case_id
        if case_output_dir.exists():
            shutil.rmtree(case_output_dir)
        shutil.copytree(base_case_dir, case_output_dir)

        inputs = detect_inputs(case_output_dir)
        mutate = norm_text(case.get("mutate"))
        if mutate:
            mutate_case(case_output_dir, inputs, mutate)

        expected_exit = int(case.get("expected_exit_code"))
        expected_verdict = norm_text(case.get("expected_verdict"))

        raw_output = ""
        if case_type == "internal":
            actual_exit, raw_output = run_internal_failure_case(case_output_dir, case_id, inputs)
        else:
            run_id = f"task197-{case_id}"
            cmd = [
                sys.executable,
                str(validator_path),
                "--bundle-manifest-json", str(inputs["bundle_manifest_json"]),
                "--integration-summary-json", str(inputs["integration_summary_json"]),
                "--handoff-paths-json", str(inputs["handoff_paths_json"]),
                "--lane-ready-inventory-csv", str(inputs["lane_ready_inventory_csv"]),
                "--unit-plan-csv", str(inputs["unit_plan_csv"]),
                "--resolved-input-manifest-json", str(inputs["resolved_input_manifest_json"]),
                "--output-dir", str(case_output_dir),
                "--run-id", run_id,
                "--write-errors-csv",
                "--write-warnings-csv",
            ]
            completed = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
            actual_exit = int(completed.returncode)
            raw_output = "\n".join([v for v in [completed.stdout or "", completed.stderr or ""] if v])

        summary_candidates = sorted(case_output_dir.glob("exhibitions_image_task_t197_handoff_validation_summary_*.json"))
        if summary_candidates:
            validator_summary = read_json(summary_candidates[0])
            actual_verdict = norm_text(validator_summary.get("handoff_verdict"))
            actual_handoff_allowed = bool(validator_summary.get("handoff_allowed"))
            actual_manual_review = bool(validator_summary.get("manual_review_required"))
        else:
            validator_summary = {}
            actual_verdict = ""
            actual_handoff_allowed = False
            actual_manual_review = True

        summary_checks = {
            "summary_exists": bool(summary_candidates),
            "report_exists": bool(list(case_output_dir.glob("exhibitions_image_task_t197_handoff_validation_report_*.md"))),
            "manifest_exists": bool(list(case_output_dir.glob("exhibitions_image_task_t197_handoff_validation_manifest_*.json"))),
        }
        if expected_verdict == "PASS":
            summary_checks["handoff_allowed_rule"] = actual_handoff_allowed is True
        if expected_verdict == "HOLD":
            summary_checks["manual_review_rule"] = actual_manual_review is True

        checks_ok = not any(v is False for v in summary_checks.values() if isinstance(v, bool))
        status = "passed" if (actual_exit == expected_exit and actual_verdict == expected_verdict and checks_ok) else "failed"

        results.append(
            {
                "case_id": case_id,
                "expected_exit_code": expected_exit,
                "actual_exit_code": actual_exit,
                "expected_verdict": expected_verdict,
                "actual_verdict": actual_verdict,
                "status": status,
                "stdout_tail": tail_text(raw_output),
                "generated_paths": sorted([str(p) for p in case_output_dir.rglob("*") if p.is_file()]),
                "summary_checks": summary_checks,
            }
        )

    total_cases = len(results)
    passed_cases = len([r for r in results if r["status"] == "passed"])
    failed_cases = total_cases - passed_cases
    all_passed = failed_cases == 0

    summary = {
        "task_id": "TASK197",
        "generated_at": utc_now_iso(),
        "manifest_path": str(manifest_path),
        "validator_path": str(validator_path),
        "output_root": str(output_root),
        "all_passed": all_passed,
        "total_cases": total_cases,
        "passed_cases": passed_cases,
        "failed_cases": failed_cases,
        "cases": results,
    }
    write_json(summary_json_path, summary)

    summary_csv_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_csv_path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=["case_id", "expected_exit_code", "actual_exit_code", "expected_verdict", "actual_verdict", "status", "generated_paths_count"])
        writer.writeheader()
        for r in results:
            writer.writerow({
                "case_id": r["case_id"],
                "expected_exit_code": r["expected_exit_code"],
                "actual_exit_code": r["actual_exit_code"],
                "expected_verdict": r["expected_verdict"],
                "actual_verdict": r["actual_verdict"],
                "status": r["status"],
                "generated_paths_count": len(r.get("generated_paths", [])),
            })

    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
