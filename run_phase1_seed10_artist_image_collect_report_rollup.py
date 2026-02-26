#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from qa_artifact_utils import (
    build_artifact_header,
    list_candidate_artifacts,
    utc_timestamp_compact,
)

DEFAULT_SEARCH_DIR = Path("data/phase1_seed10/logs")
DEFAULT_LATEST_N = 20
SOURCE_CLI = "run_phase1_seed10_artist_image_collect_report_rollup.py"
INPUT_ARTIFACT_KIND = "phase1_seed10_artist_image_collect_report"
OUTPUT_ARTIFACT_KIND = "phase1_seed10_artist_image_collect_report_rollup"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"json_not_object:{path}")
    return obj


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if text:
            try:
                return int(text)
            except ValueError:
                return None
    return None


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if text:
            try:
                return float(text)
            except ValueError:
                return None
    return None


def _as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"true", "1", "yes"}:
            return True
        if text in {"false", "0", "no"}:
            return False
    return None


def _normalize_reason_rows(value: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not isinstance(value, list):
        return rows
    for item in value:
        if not isinstance(item, dict):
            continue
        reason = str(item.get("reason") or "").strip()
        count = _as_int(item.get("count"))
        if not reason or count is None:
            continue
        rows.append({"reason": reason, "count": count})
    return rows


def _normalize_domain_rows(value: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not isinstance(value, list):
        return rows
    for item in value:
        if not isinstance(item, dict):
            continue
        domain = str(item.get("domain") or "").strip()
        count = _as_int(item.get("count"))
        if not domain or count is None:
            continue
        rows.append({"domain": domain, "count": count})
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Roll up phase1 seed10 artist image collect reports and summarize trend metrics."
        )
    )
    parser.add_argument(
        "--search-dir",
        default=str(DEFAULT_SEARCH_DIR),
        help=f"search directory (default: {DEFAULT_SEARCH_DIR})",
    )
    parser.add_argument("--glob", default="", help="optional glob override for report files")
    parser.add_argument(
        "--latest-n",
        type=int,
        default=DEFAULT_LATEST_N,
        help=f"max number of latest reports (default: {DEFAULT_LATEST_N})",
    )
    parser.add_argument("--output-json", default="", help="optional rollup output path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    search_dir = Path(args.search_dir).resolve()
    latest_n = max(1, int(args.latest_n))

    output_path = (
        Path(args.output_json).resolve()
        if args.output_json
        else (
            search_dir
            / f"phase1_seed10_artist_image_collect_report_rollup_{utc_timestamp_compact()}.json"
        ).resolve()
    )

    rollup: dict[str, Any] = {
        **build_artifact_header(OUTPUT_ARTIFACT_KIND, generated_by=SOURCE_CLI),
        "source_cli": SOURCE_CLI,
        "search_dir": str(search_dir),
        "glob": args.glob,
        "latest_n": latest_n,
        "total_reports": 0,
        "threshold_passed_count": 0,
        "threshold_passed_rate": 0.0,
        "success_rate_trend": [],
        "top_failed_reasons_trend": [],
        "top_failed_domains_trend": [],
        "gallery_breakdown_trend": [],
        "latest_gallery_breakdown": [],
        "top_failed_reasons_aggregate": [],
        "top_failed_domains_aggregate": [],
        "source_report_paths": [],
        "warnings": [],
        "notes": [],
        "rollup_exit_code": 1,
        "exit_reason": "invalid_input_or_not_found",
    }

    try:
        report_paths = list_candidate_artifacts(
            search_dir,
            INPUT_ARTIFACT_KIND,
            glob_pattern=args.glob or None,
            latest_n=latest_n,
        )
    except Exception as exc:  # noqa: BLE001
        message = f"candidate_listing_failed:{exc}"
        rollup["warnings"].append(message)
        write_json(output_path, rollup)
        print(f"[ERROR] {message}")
        print(f"[DONE] rollup={output_path}")
        return 1

    if not report_paths:
        message = f"artist_image_collect_reports_not_found:{search_dir}:{args.glob or '[default_glob]'}"
        rollup["warnings"].append(message)
        write_json(output_path, rollup)
        print(f"[ERROR] {message}")
        print(f"[DONE] rollup={output_path}")
        return 1

    rollup["source_report_paths"] = [str(path) for path in report_paths]

    reason_counter: Counter[str] = Counter()
    domain_counter: Counter[str] = Counter()
    valid_reports = 0
    threshold_passed_count = 0

    for report_path in reversed(report_paths):
        try:
            report_obj = load_json(report_path)
        except Exception as exc:  # noqa: BLE001
            rollup["warnings"].append(f"report_load_failed:{report_path}:{exc}")
            continue

        valid_reports += 1
        summary_path = str(report_obj.get("summary_path") or "")
        success_rate = _as_float(report_obj.get("success_rate_ge_target"))
        threshold_passed = _as_bool(report_obj.get("threshold_passed"))
        if threshold_passed is True:
            threshold_passed_count += 1

        reason_rows = _normalize_reason_rows(report_obj.get("top_failed_reasons"))
        domain_rows = _normalize_domain_rows(report_obj.get("top_failed_domains"))
        gallery_breakdown_rows = report_obj.get("gallery_breakdown")
        if not isinstance(gallery_breakdown_rows, list):
            gallery_breakdown_rows = []

        for row in reason_rows:
            reason_counter[row["reason"]] += int(row["count"])
        for row in domain_rows:
            domain_counter[row["domain"]] += int(row["count"])

        rollup["success_rate_trend"].append(
            {
                "report_path": str(report_path),
                "summary_path": summary_path,
                "success_rate_ge_target": success_rate,
                "threshold_passed": threshold_passed,
            }
        )
        rollup["top_failed_reasons_trend"].append(
            {
                "report_path": str(report_path),
                "summary_path": summary_path,
                "top_failed_reasons": reason_rows,
            }
        )
        rollup["top_failed_domains_trend"].append(
            {
                "report_path": str(report_path),
                "summary_path": summary_path,
                "top_failed_domains": domain_rows,
            }
        )
        rollup["gallery_breakdown_trend"].append(
            {
                "report_path": str(report_path),
                "summary_path": summary_path,
                "gallery_breakdown": gallery_breakdown_rows,
            }
        )

    if valid_reports == 0:
        rollup["warnings"].append("no_valid_report_json_loaded")
        write_json(output_path, rollup)
        print("[ERROR] no_valid_report_json_loaded")
        print(f"[DONE] rollup={output_path}")
        return 1

    rollup["total_reports"] = valid_reports
    rollup["threshold_passed_count"] = threshold_passed_count
    rollup["threshold_passed_rate"] = round(threshold_passed_count / valid_reports, 6)
    rollup["top_failed_reasons_aggregate"] = [
        {"reason": reason, "count": count}
        for reason, count in reason_counter.most_common(20)
    ]
    rollup["top_failed_domains_aggregate"] = [
        {"domain": domain, "count": count}
        for domain, count in domain_counter.most_common(20)
    ]
    if rollup["gallery_breakdown_trend"]:
        latest_breakdown = rollup["gallery_breakdown_trend"][-1].get("gallery_breakdown")
        rollup["latest_gallery_breakdown"] = latest_breakdown if isinstance(latest_breakdown, list) else []

    rollup["rollup_exit_code"] = 0
    rollup["exit_reason"] = "rollup_generated"
    write_json(output_path, rollup)

    print(
        "[ROLLUP] "
        f"total_reports={rollup['total_reports']} "
        f"threshold_passed_count={rollup['threshold_passed_count']} "
        f"threshold_passed_rate={rollup['threshold_passed_rate']:.4f}"
    )
    if rollup["success_rate_trend"]:
        latest_point = rollup["success_rate_trend"][-1]
        print(
            "[ROLLUP] latest_success_rate "
            f"summary={latest_point.get('summary_path')} "
            f"success_rate={latest_point.get('success_rate_ge_target')}"
        )
    print(f"[DONE] rollup={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
