#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from qa_artifact_utils import build_artifact_header, resolve_latest_artifact

DEFAULT_SEARCH_DIR = Path("data/phase1_seed10/derived/answer")
SOURCE_CLI = "run_aqa_retry_run_daily_chain_recovery_chain_retry_manifest_from_report_rollup.py"
INPUT_ARTIFACT_KIND = "retry_run_daily_chain_recovery_chain_report_rollup"
OUTPUT_ARTIFACT_KIND = "retry_run_daily_chain_recovery_chain_report_rollup_retry_manifest"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"json_not_object:{path}")
    return obj


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build retry manifest from artists retry-run daily-chain recovery-chain report rollup."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--rollup-json", default="", help="path to rollup JSON")
    group.add_argument("--latest", action="store_true", help="resolve latest rollup JSON")
    parser.add_argument(
        "--search-dir",
        default=str(DEFAULT_SEARCH_DIR),
        help=f"search directory for --latest (default: {DEFAULT_SEARCH_DIR})",
    )
    parser.add_argument(
        "--glob",
        default="",
        help="optional glob override for --latest",
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
        latest_path, latest_error = resolve_latest_artifact(
            Path(args.search_dir).resolve(),
            INPUT_ARTIFACT_KIND,
            glob_pattern=args.glob or None,
        )
        if latest_error:
            print(f"[ERROR] {latest_error}")
            return 1
        assert latest_path is not None
        latest_resolved = True
        rollup_path = latest_path

    if not rollup_path.exists():
        print(f"[ERROR] retry_run_daily_chain_recovery_chain_report_rollup_not_found:{rollup_path}")
        return 1

    try:
        rollup_obj = load_json(rollup_path)
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] retry_run_daily_chain_recovery_chain_report_rollup_load_failed:{rollup_path}:{exc}")
        return 1

    raw_failed_runs = rollup_obj.get("failed_runs")
    if raw_failed_runs is None:
        raw_failed_runs = []
    if not isinstance(raw_failed_runs, list):
        print("[ERROR] retry_run_daily_chain_recovery_chain_report_rollup_failed_runs_not_list")
        return 1

    notes: list[str] = []
    source_summary_paths: list[str] = []
    merged_failed_step_names: list[str] = []
    cases: list[dict[str, Any]] = []

    for index, raw_run in enumerate(raw_failed_runs, start=1):
        if not isinstance(raw_run, dict):
            notes.append(f"failed_run_not_object:index={index}")
            continue

        source_summary_path = _as_optional_str(raw_run.get("summary_path"))
        failed_step_names = _as_string_list(raw_run.get("failed_step_names"))
        child_summary_paths = _as_string_list(raw_run.get("child_summary_paths_to_check"))

        if source_summary_path and source_summary_path not in source_summary_paths:
            source_summary_paths.append(source_summary_path)
        for name in failed_step_names:
            if name not in merged_failed_step_names:
                merged_failed_step_names.append(name)

        cases.append(
            {
                "case_id": f"failed_run_{index:03d}",
                "source_summary_path": source_summary_path,
                "failed_step_names": failed_step_names,
                "child_summary_paths_to_check": child_summary_paths,
                "report_path": _as_optional_str(raw_run.get("report_path")),
                "wrapper_exit_code": raw_run.get("wrapper_exit_code"),
            }
        )

    if not cases:
        notes.append("no_failed_runs_in_rollup")

    output_manifest_path = (
        Path(args.output_manifest).resolve()
        if args.output_manifest
        else rollup_path.with_name(f"{rollup_path.stem}_retry_manifest.json")
    )

    manifest: dict[str, Any] = {
        **build_artifact_header(OUTPUT_ARTIFACT_KIND, generated_by=SOURCE_CLI),
        "source_cli": SOURCE_CLI,
        "source_rollup_path_requested": requested_rollup_path,
        "source_rollup_path": str(rollup_path),
        "source_rollup_latest_resolved": latest_resolved,
        "rollup_failed_run_count": len(raw_failed_runs),
        "retry_case_count": len(cases),
        "retry_manifest_path": str(output_manifest_path),
        "source_summary_path": source_summary_paths[0] if source_summary_paths else None,
        "source_summary_paths": source_summary_paths,
        "failed_step_names": merged_failed_step_names,
        "cases": cases,
        "notes": notes,
    }
    write_json(output_manifest_path, manifest)

    print(
        "[DONE] retry_manifest_from_daily_chain_recovery_chain_report_rollup_generated "
        f"failed_runs={manifest['rollup_failed_run_count']} "
        f"retry_cases={manifest['retry_case_count']}"
    )
    print(f"[DONE] retry_manifest={output_manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
