#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
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


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="TASK211 adoption safe-replace runner fixture matrix")
    p.add_argument("--runner-path", default="run_exhibitions_image_adoption_safe_replace_runner.py")
    p.add_argument("--output-root", default="data/phase1_seed10/logs/task_t211_adoption_runner_fixture_runs")
    p.add_argument("--summary-json", default="data/phase1_seed10/logs/exhibitions_image_task_t211_adoption_runner_fixture_matrix_summary.json")
    p.add_argument("--summary-csv", default="data/phase1_seed10/logs/exhibitions_image_task_t211_adoption_runner_fixture_matrix_summary_table.csv")
    p.add_argument("--fixture-manifest-json", default="data/phase1_seed10/logs/exhibitions_image_task_t211_adoption_runner_fixture_manifest.json")
    return p.parse_args()


def create_base_fixture(case_dir: Path) -> dict[str, Path]:
    if case_dir.exists():
        shutil.rmtree(case_dir)
    case_dir.mkdir(parents=True, exist_ok=True)
    formal_root = case_dir / "formal_root"
    candidate_root = case_dir / "candidate_root"
    logs_root = case_dir / "inputs"
    formal_root.mkdir()
    candidate_root.mkdir()
    logs_root.mkdir()

    old_path = (formal_root / "images" / "old_scope_img.txt").resolve()
    out_path = (formal_root / "images" / "out_scope_img.txt").resolve()
    new_path = (formal_root / "images" / "new_scope_img.txt").resolve()
    candidate_path = (candidate_root / "new_scope_img.txt").resolve()
    old_path.parent.mkdir(parents=True, exist_ok=True)
    old_path.write_text("old_scope_content\n", encoding="utf-8")
    out_path.write_text("out_scope_content\n", encoding="utf-8")
    candidate_path.write_text("new_scope_content\n", encoding="utf-8")

    ids = {
        "classification_run_id": "task196-explicit-success-classification",
        "bundle_id": "task196-explicit-success",
        "trial_runtime_bundle_id": "task199-ready_success",
        "trial_runner_bundle_id": "task201-success_single_unit",
        "qa_runtime_bundle_id": "t205c01",
        "qa_runner_bundle_id": "task207-success_single_unit",
    }
    scope_hash = "b4edf412b005f8c1cdea443c627e14b45ba255d2"

    current_targets = logs_root / "current_authoritative_target_list.csv"
    write_csv(
        current_targets,
        [
            "planned_unit_id", "gallery_name_en", "fair_slug", "target_year", "source_url", "lane", "local_path", "scope_hash",
            "classification_run_id", "bundle_id", "trial_runtime_bundle_id", "trial_runner_bundle_id", "qa_runtime_bundle_id", "qa_runner_bundle_id",
        ],
        [
            {
                "planned_unit_id": "U-SAFE-frieze_london-2025-001",
                "gallery_name_en": "Safe Gallery",
                "fair_slug": "frieze_london",
                "target_year": "2025",
                "source_url": "https://example.com/scope-old",
                "lane": "Safe-But-Provenance-Gated",
                "local_path": str(old_path),
                "scope_hash": scope_hash,
                **ids,
            },
            {
                "planned_unit_id": "U-OTHER-frieze_london-2025-001",
                "gallery_name_en": "Other Gallery",
                "fair_slug": "frieze_london",
                "target_year": "2025",
                "source_url": "https://example.com/out-scope",
                "lane": "Guard-First-Then-Upgrade",
                "local_path": str(out_path),
                "scope_hash": "other_scope_hash_task211",
                **ids,
            },
        ],
    )

    formal_manifest = logs_root / "formal_manifest.json"
    write_json(
        formal_manifest,
        {
            "task_id": "TASK211_FIXTURE",
            "formal_root": str(formal_root),
            "target_list_csv": str(current_targets),
        },
    )

    unit_rows_csv = logs_root / "qa_unit_rows_unit1.csv"
    write_csv(
        unit_rows_csv,
        ["planned_unit_id", "gallery_name_en", "fair_slug", "target_year", "lane", "source_url", "local_path", "candidate_local_path"],
        [
            {
                "planned_unit_id": "U-SAFE-frieze_london-2025-001",
                "gallery_name_en": "Safe Gallery",
                "fair_slug": "frieze_london",
                "target_year": "2025",
                "lane": "Safe-But-Provenance-Gated",
                "source_url": "https://example.com/scope-new",
                "local_path": str(new_path),
                "candidate_local_path": str(candidate_path),
            }
        ],
    )
    unit_json = logs_root / "qa_unit_result_unit1.json"
    write_json(
        unit_json,
        {
            "planned_unit_id": "U-SAFE-frieze_london-2025-001",
            "actual_qa_run_id": "task207-success_single_unit-U-SAFE-frieze_london-2025-001",
            "scope_hash": scope_hash,
            "unit_status": "SUCCESS",
            **ids,
        },
    )

    qa_bundle_csv = logs_root / "qa_bundle_result.csv"
    write_csv(
        qa_bundle_csv,
        [
            "planned_unit_id", "actual_trial_run_id", "actual_qa_run_id", "unit_status",
            "executed_row_count", "succeeded_row_count", "failed_row_count", "deferred_row_count",
            "qa_unit_result_json_path", "qa_unit_rows_csv_path",
        ],
        [
            {
                "planned_unit_id": "U-SAFE-frieze_london-2025-001",
                "actual_trial_run_id": "trial-2025-frieze_london-safe-SAFE-frieze_london-2025-001",
                "actual_qa_run_id": "task207-success_single_unit-U-SAFE-frieze_london-2025-001",
                "unit_status": "SUCCESS",
                "executed_row_count": "1",
                "succeeded_row_count": "1",
                "failed_row_count": "0",
                "deferred_row_count": "0",
                "qa_unit_result_json_path": str(unit_json),
                "qa_unit_rows_csv_path": str(unit_rows_csv),
            }
        ],
    )

    qa_execution_summary = logs_root / "qa_execution_summary.json"
    write_json(
        qa_execution_summary,
        {
            "qa_runner_status": "SUCCESS",
            "executed_unit_count": 1,
            "succeeded_unit_count": 1,
            "failed_unit_count": 0,
            "deferred_unit_count": 0,
            "adoption_handoff_allowed": True,
            "ids": ids,
            "scope_hash": scope_hash,
        },
    )
    qa_execution_manifest = logs_root / "qa_execution_manifest.json"
    write_json(
        qa_execution_manifest,
        {"outputs": {"summary_json": str(qa_execution_summary), "bundle_result_csv": str(qa_bundle_csv)}},
    )
    qa_adoption_handoff_manifest = logs_root / "qa_adoption_handoff_manifest.json"
    write_json(
        qa_adoption_handoff_manifest,
        {
            "qa_unit_result_paths": [str(unit_json)],
            "qa_bundle_summary_path": str(qa_execution_summary),
            "qa_failure_queue_path": "",
            "qa_defer_queue_path": "",
            "scope_hash": scope_hash,
        },
    )
    adoption_summary = logs_root / "adoption_handoff_validation_summary.json"
    write_json(
        adoption_summary,
        {
            "adoption_handoff_verdict": "PASS",
            "adoption_handoff_allowed": True,
            "ids": ids,
            "scope_hash": scope_hash,
            "adoption_minimum_set": {
                "qa_execution_summary_json": str(qa_execution_summary),
                "qa_bundle_result_csv": str(qa_bundle_csv),
                "qa_adoption_handoff_manifest_json": str(qa_adoption_handoff_manifest),
            },
        },
    )
    adoption_manifest = logs_root / "adoption_handoff_validation_manifest.json"
    write_json(
        adoption_manifest,
        {
            "inputs": {
                "qa_execution_summary_json": str(qa_execution_summary),
                "qa_execution_manifest_json": str(qa_execution_manifest),
                "qa_bundle_result_csv": str(qa_bundle_csv),
                "qa_adoption_handoff_manifest_json": str(qa_adoption_handoff_manifest),
            },
            "adoption_minimum_set": {
                "qa_execution_summary_json": str(qa_execution_summary),
                "qa_bundle_result_csv": str(qa_bundle_csv),
                "qa_adoption_handoff_manifest_json": str(qa_adoption_handoff_manifest),
            },
        },
    )

    return {
        "formal_root": formal_root,
        "formal_manifest": formal_manifest,
        "current_targets": current_targets,
        "adoption_summary": adoption_summary,
        "adoption_manifest": adoption_manifest,
        "qa_execution_summary": qa_execution_summary,
        "qa_execution_manifest": qa_execution_manifest,
        "qa_bundle_csv": qa_bundle_csv,
        "qa_adoption_handoff_manifest": qa_adoption_handoff_manifest,
        "unit_json": unit_json,
        "unit_rows_csv": unit_rows_csv,
        "old_path": old_path,
        "new_path": new_path,
        "candidate_path": candidate_path,
    }


def tail_text(text: str, max_lines: int = 10) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    return "\n".join(lines[-max_lines:]) if lines else ""


def main() -> int:
    args = parse_args()
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    cases = [
        {"case_id": "success_scoped_replace", "expected_status": "SUCCESS", "expected_exit": 0},
        {"case_id": "partial_success_with_noop", "expected_status": "PARTIAL_SUCCESS", "expected_exit": 21},
        {"case_id": "hold_validator_holds", "expected_status": "HOLD", "expected_exit": 20},
        {"case_id": "reject_missing_required_file", "expected_status": "FAIL_FAST", "expected_exit": 10},
        {"case_id": "reject_scope_mismatch", "expected_status": "FAIL_FAST", "expected_exit": 12},
        {"case_id": "reject_wrong_scope_delete_attempt", "expected_status": "FAIL_FAST", "expected_exit": 12},
        {"case_id": "rolled_back_after_partial_write", "expected_status": "ROLLED_BACK", "expected_exit": 22},
        {"case_id": "internal_failure_monkeypatch", "expected_status": "INTERNAL_FAILURE", "expected_exit": 30},
    ]
    write_json(Path(args.fixture_manifest_json), {"task_id": "TASK211", "generated_at": utc_now_iso(), "output_root": str(output_root), "cases": cases})

    results: list[dict[str, Any]] = []
    for idx, case in enumerate(cases, start=1):
        case_id = norm_text(case["case_id"])
        run_id = f"t211-c{idx:02d}"
        case_dir = output_root / case_id
        paths = create_base_fixture(case_dir)

        if case_id == "partial_success_with_noop":
            write_csv(paths["unit_rows_csv"], ["planned_unit_id", "gallery_name_en", "fair_slug", "target_year", "lane", "source_url", "local_path", "candidate_local_path"], [{
                "planned_unit_id": "U-SAFE-frieze_london-2025-001", "gallery_name_en": "Safe Gallery", "fair_slug": "frieze_london", "target_year": "2025", "lane": "Safe-But-Provenance-Gated", "source_url": "https://example.com/scope-old", "local_path": str(paths["old_path"]), "candidate_local_path": str(paths["old_path"])
            }])
        elif case_id == "hold_validator_holds":
            payload = read_json(paths["adoption_summary"])
            payload["adoption_handoff_verdict"] = "HOLD"
            payload["adoption_handoff_allowed"] = False
            write_json(paths["adoption_summary"], payload)
        elif case_id == "reject_missing_required_file":
            paths["qa_bundle_csv"].unlink(missing_ok=True)
        elif case_id == "reject_scope_mismatch":
            payload = read_json(paths["qa_execution_summary"])
            payload["scope_hash"] = "scope_hash_mismatch_task211"
            write_json(paths["qa_execution_summary"], payload)
        elif case_id == "reject_wrong_scope_delete_attempt":
            outside = (case_dir / "outside.txt").resolve()
            outside.write_text("outside", encoding="utf-8")
            write_csv(paths["current_targets"], ["planned_unit_id", "gallery_name_en", "fair_slug", "target_year", "source_url", "lane", "local_path", "scope_hash", "classification_run_id", "bundle_id", "trial_runtime_bundle_id", "trial_runner_bundle_id", "qa_runtime_bundle_id", "qa_runner_bundle_id"], [{
                "planned_unit_id": "U-SAFE-frieze_london-2025-001", "gallery_name_en": "Safe Gallery", "fair_slug": "frieze_london", "target_year": "2025", "source_url": "https://example.com/scope-old", "lane": "Safe-But-Provenance-Gated", "local_path": str(outside), "scope_hash": "b4edf412b005f8c1cdea443c627e14b45ba255d2", "classification_run_id": "task196-explicit-success-classification", "bundle_id": "task196-explicit-success", "trial_runtime_bundle_id": "task199-ready_success", "trial_runner_bundle_id": "task201-success_single_unit", "qa_runtime_bundle_id": "t205c01", "qa_runner_bundle_id": "task207-success_single_unit"
            }])

        cmd = [
            sys.executable, args.runner_path,
            "--adoption-handoff-validation-summary", str(paths["adoption_summary"]),
            "--adoption-handoff-validation-manifest", str(paths["adoption_manifest"]),
            "--qa-execution-summary", str(paths["qa_execution_summary"]),
            "--qa-execution-manifest", str(paths["qa_execution_manifest"]),
            "--qa-bundle-result-csv", str(paths["qa_bundle_csv"]),
            "--qa-adoption-handoff-manifest", str(paths["qa_adoption_handoff_manifest"]),
            "--formal-root", str(paths["formal_root"]),
            "--formal-manifest-json", str(paths["formal_manifest"]),
            "--current-authoritative-target-list", str(paths["current_targets"]),
            "--trash-root", str(case_dir / "_trash"),
            "--output-dir", str(case_dir),
            "--adoption-run-id", run_id,
        ]
        env = dict(os.environ)
        if case_id == "internal_failure_monkeypatch":
            env["TASK211_FORCE_INTERNAL_FAILURE"] = "1"
        if case_id == "rolled_back_after_partial_write":
            env["TASK211_FORCE_FAIL_AFTER_REPLACE"] = "1"
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", env=env)
        actual_exit = int(proc.returncode)
        summary_path = case_dir / f"exhibitions_image_task_t211_adoption_execution_summary_{run_id}.json"
        actual_status = ""
        checks = {
            "summary_exists": summary_path.exists(),
            "manifest_exists": (case_dir / f"exhibitions_image_task_t211_adoption_execution_manifest_{run_id}.json").exists(),
            "report_exists": (case_dir / f"exhibitions_image_task_t211_adoption_execution_report_{run_id}.md").exists(),
            "result_exists": (case_dir / f"exhibitions_image_task_t211_adoption_result_{run_id}.json").exists(),
            "trash_manifest_exists": (case_dir / f"exhibitions_image_task_t211_trash_manifest_{run_id}.csv").exists(),
        }
        if summary_path.exists():
            actual_status = norm_text(read_json(summary_path).get("adoption_status"))
        ok = (
            actual_exit == int(case["expected_exit"])
            and actual_status == norm_text(case["expected_status"])
            and not any(v is False for v in checks.values())
        )
        results.append(
            {
                "case_id": case_id,
                "expected_status": norm_text(case["expected_status"]),
                "actual_status": actual_status,
                "expected_exit_code": int(case["expected_exit"]),
                "actual_exit_code": actual_exit,
                "status": "passed" if ok else "failed",
                "stdout_tail": tail_text((proc.stdout or "") + "\n" + (proc.stderr or "")),
                "generated_paths": sorted([str(p) for p in case_dir.rglob("*") if p.is_file()]),
                "summary_checks": checks,
            }
        )

    total = len(results)
    passed = len([r for r in results if r["status"] == "passed"])
    failed = total - passed
    summary = {
        "task_id": "TASK211",
        "generated_at": utc_now_iso(),
        "output_root": str(output_root),
        "all_passed": failed == 0,
        "total_cases": total,
        "passed_cases": passed,
        "failed_cases": failed,
        "cases": results,
    }
    write_json(Path(args.summary_json), summary)
    write_csv(
        Path(args.summary_csv),
        ["case_id", "expected_status", "actual_status", "expected_exit_code", "actual_exit_code", "status"],
        results,
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
