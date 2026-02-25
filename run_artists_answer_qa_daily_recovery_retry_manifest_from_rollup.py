#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_SEARCH_DIR = Path("data/phase1_seed10/derived/answer")
DEFAULT_GLOB = "artists_answer_qa_daily_recovery_report_rollup_*.json"
SOURCE_CLI = "run_artists_answer_qa_daily_recovery_retry_manifest_from_rollup.py"


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


def _resolve_latest_rollup(search_dir: Path, pattern: str) -> tuple[Path | None, str | None]:
    candidates = [p for p in search_dir.glob(pattern) if p.is_file()]
    if not candidates:
        return None, f"latest_rollup_not_found:{search_dir}/{pattern}"
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


def _load_batch_manifest_path(source_summary_path: str | None) -> tuple[str | None, str | None]:
    if not source_summary_path:
        return None, "source_summary_path_missing"
    path = Path(source_summary_path)
    if not path.exists():
        return None, f"source_summary_not_found:{path}"
    try:
        obj = load_json(path)
    except Exception as exc:  # noqa: BLE001
        return None, f"source_summary_load_failed:{path}:{exc}"

    batch_manifest_path = _as_optional_str(obj.get("batch_manifest_path"))
    if not batch_manifest_path:
        return None, f"batch_manifest_path_missing_in_source_summary:{path}"
    return batch_manifest_path, None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build retry manifest from artists daily recovery rollup JSON."
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
        print(f"[ERROR] rollup_json_not_found:{rollup_path}")
        return 1

    try:
        rollup_obj = load_json(rollup_path)
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] rollup_json_load_failed:{rollup_path}:{exc}")
        return 1

    raw_failed_runs = rollup_obj.get("failed_runs")
    if raw_failed_runs is None:
        raw_failed_runs = []
    if not isinstance(raw_failed_runs, list):
        print("[ERROR] rollup_failed_runs_not_list")
        return 1

    cases: list[dict[str, Any]] = []
    notes: list[str] = []

    for index, raw_run in enumerate(raw_failed_runs, start=1):
        if not isinstance(raw_run, dict):
            notes.append(f"failed_run_not_object:index={index}")
            continue

        source_summary_path = _as_optional_str(raw_run.get("summary_path"))
        source_report_path = _as_optional_str(raw_run.get("report_path"))
        failed_step_names = _as_string_list(raw_run.get("failed_step_names"))
        child_summary_paths = _as_string_list(raw_run.get("child_summary_paths_to_check"))
        failed_step_count = raw_run.get("failed_step_count")

        batch_manifest_path, batch_manifest_note = _load_batch_manifest_path(source_summary_path)
        if batch_manifest_note:
            notes.append(f"case_{index}:{batch_manifest_note}")

        cases.append(
            {
                "case_id": f"failed_run_{index:03d}",
                "source_summary_path": source_summary_path,
                "source_report_path": source_report_path,
                "failed_step_count": failed_step_count,
                "failed_step_names": failed_step_names,
                "child_summary_paths_to_check": child_summary_paths,
                "batch_manifest_path": batch_manifest_path,
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
        "generated_at": utc_now_iso(),
        "source_cli": SOURCE_CLI,
        "source_rollup_path_requested": requested_rollup_path,
        "source_rollup_path": str(rollup_path),
        "source_rollup_latest_resolved": latest_resolved,
        "rollup_failed_run_count": len(raw_failed_runs),
        "retry_case_count": len(cases),
        "retry_manifest_path": str(output_manifest_path),
        "cases": cases,
        "notes": notes,
    }
    write_json(output_manifest_path, manifest)

    print(
        "[DONE] retry_manifest_from_rollup_generated "
        f"failed_runs={manifest['rollup_failed_run_count']} "
        f"retry_cases={manifest['retry_case_count']}"
    )
    print(f"[DONE] retry_manifest={output_manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
