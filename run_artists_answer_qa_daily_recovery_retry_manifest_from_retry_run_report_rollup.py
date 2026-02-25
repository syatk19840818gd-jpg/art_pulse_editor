#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_SEARCH_DIR = Path("data/phase1_seed10/derived/answer")
DEFAULT_GLOB = "artists_answer_qa_daily_recovery_retry_run_report_rollup_*.json"
SOURCE_CLI = "run_artists_answer_qa_daily_recovery_retry_manifest_from_retry_run_report_rollup.py"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"json_not_object:{path}")
    return obj


def _is_rollup_candidate(path: Path) -> bool:
    name = path.name
    if not name.startswith("artists_answer_qa_daily_recovery_retry_run_report_rollup_"):
        return False
    if not name.endswith(".json"):
        return False
    # Exclude output manifests created from rollup files.
    return "_retry_manifest.json" not in name


def _resolve_latest_rollup(search_dir: Path, pattern: str) -> tuple[Path | None, str | None]:
    candidates = [p for p in search_dir.glob(pattern) if p.is_file() and _is_rollup_candidate(p)]
    if not candidates:
        return None, f"latest_retry_run_report_rollup_not_found:{search_dir}/{pattern}"
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    return latest.resolve(), None


def _as_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return str(value)


def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        if isinstance(item, str):
            stripped = item.strip()
            if stripped:
                out.append(stripped)
    return out


def _case_key(case_obj: dict[str, Any]) -> str:
    case_id = _as_optional_str(case_obj.get("case_id"))
    return case_id or ""


def _extract_failed_cases_from_retry_run_summary(
    retry_run_summary_path: str | None,
    failed_case_ids: list[str],
) -> tuple[list[dict[str, Any]], list[str]]:
    notes: list[str] = []
    cases: list[dict[str, Any]] = []

    if not retry_run_summary_path:
        notes.append("retry_run_summary_path_missing")
        return cases, notes

    summary_path = Path(retry_run_summary_path)
    if not summary_path.exists():
        notes.append(f"retry_run_summary_not_found:{summary_path}")
        return cases, notes

    try:
        summary_obj = load_json(summary_path)
    except Exception as exc:  # noqa: BLE001
        notes.append(f"retry_run_summary_load_failed:{summary_path}:{exc}")
        return cases, notes

    raw_cases = summary_obj.get("cases")
    if not isinstance(raw_cases, list):
        notes.append(f"retry_run_summary_cases_not_list:{summary_path}")
        return cases, notes

    case_map: dict[str, dict[str, Any]] = {}
    for raw_case in raw_cases:
        if not isinstance(raw_case, dict):
            continue
        key = _case_key(raw_case)
        if key:
            case_map[key] = raw_case

    picked_ids: list[str]
    if failed_case_ids:
        picked_ids = failed_case_ids
    else:
        picked_ids = []
        for raw_case in raw_cases:
            if not isinstance(raw_case, dict):
                continue
            status = _as_optional_str(raw_case.get("status")) or ""
            exit_code = raw_case.get("exit_code")
            failed = status == "failed" or (isinstance(exit_code, int) and exit_code != 0)
            if failed:
                key = _case_key(raw_case)
                if key:
                    picked_ids.append(key)

    if not picked_ids:
        notes.append(f"no_failed_cases_detected_in_retry_run_summary:{summary_path}")
        return cases, notes

    for case_id in picked_ids:
        case_obj = case_map.get(case_id)
        if case_obj is None:
            notes.append(f"failed_case_id_not_found_in_retry_run_summary:{summary_path}:{case_id}")
            continue
        cases.append(
            {
                "case_id": case_id,
                "source_retry_run_summary_path": str(summary_path.resolve()),
                "source_summary_path": _as_optional_str(case_obj.get("source_summary_path")),
                "batch_manifest_path": _as_optional_str(case_obj.get("batch_manifest_path")),
                "daily_summary_path": _as_optional_str(case_obj.get("daily_summary_path")),
            }
        )

    return cases, notes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build retry manifest from artists retry-run report rollup JSON."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--rollup-json", default="", help="path to retry-run report rollup JSON")
    group.add_argument("--latest", action="store_true", help="resolve latest retry-run report rollup JSON")
    parser.add_argument(
        "--search-dir",
        default=str(DEFAULT_SEARCH_DIR),
        help=f"search directory for --latest (default: {DEFAULT_SEARCH_DIR})",
    )
    parser.add_argument(
        "--glob",
        default=DEFAULT_GLOB,
        help=f"glob for --latest (default: {DEFAULT_GLOB})",
    )
    parser.add_argument("--output-manifest", default="", help="optional output manifest path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    requested_rollup_path = _as_optional_str(args.rollup_json)
    latest_resolved = False

    if requested_rollup_path:
        rollup_path = Path(requested_rollup_path).resolve()
    else:
        latest_path, latest_error = _resolve_latest_rollup(Path(args.search_dir), args.glob)
        if latest_error:
            print(f"[ERROR] {latest_error}")
            return 1
        assert latest_path is not None
        latest_resolved = True
        rollup_path = latest_path

    if not rollup_path.exists():
        print(f"[ERROR] retry_run_report_rollup_not_found:{rollup_path}")
        return 1

    try:
        rollup_obj = load_json(rollup_path)
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] retry_run_report_rollup_load_failed:{rollup_path}:{exc}")
        return 1

    raw_failed_runs = rollup_obj.get("failed_runs")
    if raw_failed_runs is None:
        raw_failed_runs = []
    if not isinstance(raw_failed_runs, list):
        print("[ERROR] retry_run_report_rollup_failed_runs_not_list")
        return 1

    notes: list[str] = []
    cases: list[dict[str, Any]] = []
    source_summary_paths: list[str] = []
    merged_failed_case_ids: list[str] = []

    for index, raw_run in enumerate(raw_failed_runs, start=1):
        if not isinstance(raw_run, dict):
            notes.append(f"failed_run_not_object:index={index}")
            continue

        retry_run_summary_path = _as_optional_str(raw_run.get("summary_path"))
        report_path = _as_optional_str(raw_run.get("report_path"))
        failed_case_ids = _as_string_list(raw_run.get("failed_case_ids"))
        child_daily_summaries = _as_string_list(raw_run.get("child_daily_summaries_to_check"))

        extracted_cases, extract_notes = _extract_failed_cases_from_retry_run_summary(
            retry_run_summary_path=retry_run_summary_path,
            failed_case_ids=failed_case_ids,
        )
        notes.extend([f"failed_run_{index}:{note}" for note in extract_notes])

        for case in extracted_cases:
            case["source_retry_run_report_path"] = report_path
            case["failed_case_ids"] = failed_case_ids
            case["child_daily_summaries_to_check"] = child_daily_summaries
            cases.append(case)

            summary_path = _as_optional_str(case.get("source_summary_path"))
            if summary_path and summary_path not in source_summary_paths:
                source_summary_paths.append(summary_path)

            case_id = _as_optional_str(case.get("case_id"))
            if case_id and case_id not in merged_failed_case_ids:
                merged_failed_case_ids.append(case_id)

    if not cases:
        notes.append("no_failed_cases_extracted_from_rollup")

    output_manifest_path = (
        Path(args.output_manifest).resolve()
        if args.output_manifest
        else rollup_path.with_name(f"{rollup_path.stem}_retry_manifest.json")
    )

    manifest: dict[str, Any] = {
        "generated_at": utc_now_iso(),
        "source_cli": SOURCE_CLI,
        "source_rollup_path_requested": requested_rollup_path,
        "source_rollup_path": str(rollup_path),
        "source_rollup_latest_resolved": latest_resolved,
        "rollup_failed_run_count": len(raw_failed_runs),
        "retry_case_count": len(cases),
        "retry_manifest_path": str(output_manifest_path),
        "source_summary_path": source_summary_paths[0] if source_summary_paths else None,
        "source_summary_paths": source_summary_paths,
        "failed_case_ids": merged_failed_case_ids,
        "cases": cases,
        "notes": notes,
    }
    write_json(output_manifest_path, manifest)

    print(
        "[DONE] retry_manifest_from_retry_run_report_rollup_generated "
        f"failed_runs={manifest['rollup_failed_run_count']} "
        f"retry_cases={manifest['retry_case_count']}"
    )
    print(f"[DONE] retry_manifest={output_manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
