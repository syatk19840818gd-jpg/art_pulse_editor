from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from run_exhibitions_image_rerun_diff_gate import evaluate_rerun_diff_gate_from_rows
from run_phase1_seed10_exhibition_image_collect import (
    build_semantic_key,
    evaluate_duplicate_collision_guard,
    evaluate_provenance_guard,
    evaluate_route_guard,
    evaluate_year_evidence_guard,
)

LOG_DIR = Path("data/phase1_seed10/logs")


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _case_route_bad_hard() -> tuple[str, str, dict[str, Any]]:
    out = evaluate_route_guard(
        detail_url="https://example.com/viewing-room/abc",
        seed_url="https://example.com/exhibitions/2025/detail",
    )
    return ("route_bad_hard", "reject", {"decision": out["decision"], "reasons": out.get("reasons", [])})


def _case_year_non_target() -> tuple[str, str, dict[str, Any]]:
    out = evaluate_year_evidence_guard(
        candidate_year=2023,
        evidence_text="installation view 2023",
        detail_url="https://example.com/exhibitions/test",
        seed_url="https://example.com/exhibitions/test",
        target_year=2025,
        parent_tag="img",
    )
    return ("year_non_target", "reject", {"decision": out["decision"], "reasons": out.get("reasons", [])})


def _case_year_metadata_fallback() -> tuple[str, str, dict[str, Any]]:
    out = evaluate_year_evidence_guard(
        candidate_year=None,
        evidence_text="metadata_fallback",
        detail_url="https://example.com/exhibitions/overview",
        seed_url="https://example.com/exhibitions/past",
        target_year=2025,
        parent_tag="metadata",
    )
    return ("year_metadata_fallback", "quarantine", {"decision": out["decision"], "reasons": out.get("reasons", [])})


def _case_provenance_weak() -> tuple[str, str, dict[str, Any]]:
    out = evaluate_provenance_guard(
        detail_url="https://example.com/exhibitions",
        seed_url="https://example.com/exhibitions",
        seed_url_type="listing",
        selected_reason="detail_page_candidate_rank",
        parent_tag="metadata",
        metadata_fallback=True,
    )
    return ("provenance_weak", "quarantine", {"decision": out["decision"], "reasons": out.get("reasons", [])})


def _case_duplicate_collision_reject() -> tuple[str, str, dict[str, Any]]:
    known_local = {"L1": {"s1"}}
    known_r2 = {"R1": {"s1"}}
    out = evaluate_duplicate_collision_guard(
        local_path="L1",
        r2_key="R1",
        semantic_key="s2",
        known_local_path_map=known_local,
        known_r2_key_map=known_r2,
        in_case_local_path_map={},
        in_case_r2_key_map={},
    )
    return ("duplicate_collision_reject", "reject", {"decision": out["decision"], "reasons": out.get("reasons", [])})


def _case_duplicate_semantic_no_change() -> tuple[str, str, dict[str, Any]]:
    semantic = build_semantic_key(
        fair_slug="frieze_london",
        gallery_name_en="Gallery X",
        source_url="https://example.com/exhibitions/a",
        seed_source_url="https://example.com/exhibitions",
        image_url="https://example.com/img/a.jpg",
        payload_hash="p1",
    )
    out = evaluate_duplicate_collision_guard(
        local_path="L1",
        r2_key="R1",
        semantic_key=semantic,
        known_local_path_map={"L1": {semantic}},
        known_r2_key_map={"R1": {semantic}},
        in_case_local_path_map={},
        in_case_r2_key_map={},
    )
    return (
        "duplicate_semantic_no_change",
        "no_change_ok",
        {"decision": out["decision"], "reasons": out.get("reasons", [])},
    )


def _case_diff_gate_fail_known_bad() -> tuple[str, str, dict[str, Any]]:
    rows = [{"diff_label": "KNOWN_BAD_ROUTE_RECURRED", "local_path": "a", "r2_key": "a"}]
    out = evaluate_rerun_diff_gate_from_rows(rows)
    return ("diff_gate_fail_known_bad", "FAIL_REGRESSION_DETECTED", {"gate_status": out["gate_status"]})


def _case_diff_gate_fail_reject_completion() -> tuple[str, str, dict[str, Any]]:
    rows = [{"diff_label": "REJECT_FOR_COMPLETION", "local_path": "a", "r2_key": "a"}]
    out = evaluate_rerun_diff_gate_from_rows(rows)
    return ("diff_gate_fail_reject_completion", "FAIL_REGRESSION_DETECTED", {"gate_status": out["gate_status"]})


def _case_diff_gate_fail_collision_group() -> tuple[str, str, dict[str, Any]]:
    rows = [
        {"diff_label": "DUPLICATE_COLLISION", "local_path": "same", "r2_key": "same"},
        {"diff_label": "DUPLICATE_COLLISION", "local_path": "same", "r2_key": "same"},
    ]
    out = evaluate_rerun_diff_gate_from_rows(rows)
    return (
        "diff_gate_fail_collision_group",
        "FAIL_REGRESSION_DETECTED",
        {"gate_status": out["gate_status"], "duplicate_collision_group_count": out["duplicate_collision_group_count"]},
    )


def _case_diff_gate_hold_suspicious() -> tuple[str, str, dict[str, Any]]:
    rows = [{"diff_label": "SUSPICIOUS_ROUTE", "local_path": "a", "r2_key": "a"}]
    out = evaluate_rerun_diff_gate_from_rows(rows)
    return ("diff_gate_hold_suspicious", "HOLD_FOR_SCOPE_REVIEW", {"gate_status": out["gate_status"]})


def _case_diff_gate_pass_safe_only() -> tuple[str, str, dict[str, Any]]:
    rows = [{"diff_label": "SAFE_BUT_NOT_NEEDED", "local_path": "a", "r2_key": "a"}]
    out = evaluate_rerun_diff_gate_from_rows(rows)
    return ("diff_gate_pass_safe_only", "PASS_FOR_CLOSURE", {"gate_status": out["gate_status"]})


def run_fixture_matrix() -> dict[str, Any]:
    cases = [
        _case_route_bad_hard,
        _case_year_non_target,
        _case_year_metadata_fallback,
        _case_provenance_weak,
        _case_duplicate_collision_reject,
        _case_duplicate_semantic_no_change,
        _case_diff_gate_fail_known_bad,
        _case_diff_gate_fail_reject_completion,
        _case_diff_gate_fail_collision_group,
        _case_diff_gate_hold_suspicious,
        _case_diff_gate_pass_safe_only,
    ]
    rows: list[dict[str, Any]] = []
    for fn in cases:
        case_id, expected, actual_obj = fn()
        actual = str(actual_obj.get("decision") or actual_obj.get("gate_status") or "")
        rows.append(
            {
                "case_id": case_id,
                "expected": expected,
                "actual": actual,
                "pass": str(expected == actual).lower(),
                "actual_json": json.dumps(actual_obj, ensure_ascii=False),
            }
        )
    passed = sum(1 for r in rows if r["pass"] == "true")
    return {
        "artifact": "exhibitions_image_rerun_regression_guard_validation_summary_task226",
        "evaluated_at": _utc_now_iso(),
        "total_cases": len(rows),
        "passed_cases": passed,
        "all_passed": passed == len(rows),
        "cases": rows,
    }


def main() -> int:
    summary = run_fixture_matrix()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = LOG_DIR / "exhibitions_image_rerun_regression_guard_validation_summary_task226.json"
    table_path = LOG_DIR / "exhibitions_image_rerun_regression_guard_validation_table_task226.csv"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    with table_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["case_id", "expected", "actual", "pass", "actual_json"])
        writer.writeheader()
        for row in summary["cases"]:
            writer.writerow(row)
    print(
        "[rerun-guard-fixture] "
        f"total={summary['total_cases']} passed={summary['passed_cases']} all_passed={summary['all_passed']}"
    )
    print(f"[rerun-guard-fixture] summary={summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
