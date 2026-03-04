from __future__ import annotations

import argparse
import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _read_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def evaluate_rerun_diff_gate_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    label_counts: dict[str, int] = {}
    duplicate_local_groups: dict[str, int] = {}
    duplicate_r2_groups: dict[str, int] = {}

    for row in rows:
        label = str(row.get("diff_label") or "").strip()
        if label:
            label_counts[label] = label_counts.get(label, 0) + 1
        if label == "DUPLICATE_COLLISION":
            local_path = str(row.get("local_path") or "").strip()
            r2_key = str(row.get("r2_key") or "").strip()
            if local_path:
                duplicate_local_groups[local_path] = duplicate_local_groups.get(local_path, 0) + 1
            if r2_key:
                duplicate_r2_groups[r2_key] = duplicate_r2_groups.get(r2_key, 0) + 1

    known_bad = int(label_counts.get("KNOWN_BAD_ROUTE_RECURRED", 0))
    reject_completion = int(label_counts.get("REJECT_FOR_COMPLETION", 0))
    suspicious = int(label_counts.get("SUSPICIOUS_ROUTE", 0)) + int(label_counts.get("SUSPICIOUS_YEAR", 0)) + int(
        label_counts.get("SUSPICIOUS_PROVENANCE", 0)
    )
    safe_only = int(label_counts.get("SAFE_BUT_NOT_NEEDED", 0))
    duplicate_collision = int(label_counts.get("DUPLICATE_COLLISION", 0))
    duplicate_collision_group_count = (
        sum(1 for _, cnt in duplicate_local_groups.items() if cnt > 1)
        + sum(1 for _, cnt in duplicate_r2_groups.items() if cnt > 1)
    )

    if known_bad > 0 or reject_completion > 0 or duplicate_collision_group_count > 0:
        gate_status = "FAIL_REGRESSION_DETECTED"
    elif suspicious > 0:
        gate_status = "HOLD_FOR_SCOPE_REVIEW"
    else:
        # no diff rows or safe-only rows
        gate_status = "PASS_FOR_CLOSURE"

    return {
        "gate_status": gate_status,
        "label_counts": label_counts,
        "known_bad_route_recurred_count": known_bad,
        "reject_for_completion_count": reject_completion,
        "suspicious_total_count": suspicious,
        "safe_but_not_needed_count": safe_only,
        "duplicate_collision_count": duplicate_collision,
        "duplicate_collision_group_count": duplicate_collision_group_count,
        "duplicate_local_path_group_count": sum(1 for _, cnt in duplicate_local_groups.items() if cnt > 1),
        "duplicate_r2_key_group_count": sum(1 for _, cnt in duplicate_r2_groups.items() if cnt > 1),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Exhibitions image rerun diff gate evaluator")
    parser.add_argument("--classification-csv", required=True)
    parser.add_argument(
        "--output-json",
        default="data/phase1_seed10/logs/exhibitions_image_rerun_diff_gate_summary_latest.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    path = Path(args.classification_csv)
    rows = _read_csv_rows(path)
    evaluated = evaluate_rerun_diff_gate_from_rows(rows)
    summary = {
        "artifact": "exhibitions_image_rerun_diff_gate_summary",
        "classification_csv": str(path),
        "row_count": len(rows),
        "evaluated_at": _utc_now_iso(),
        **evaluated,
    }
    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[rerun-diff-gate] gate_status={summary['gate_status']} row_count={summary['row_count']}")
    print(f"[rerun-diff-gate] output={out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
