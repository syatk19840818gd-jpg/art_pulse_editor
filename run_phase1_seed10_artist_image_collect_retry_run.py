#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from qa_artifact_utils import build_artifact_header, resolve_latest_artifact, utc_now_iso, utc_timestamp_compact

DEFAULT_SEARCH_DIR = Path("data/phase1_seed10/logs")
DEFAULT_SUMMARY_DIR = Path("data/phase1_seed10/logs")
DEFAULT_TARGET_YEAR = 2025
DEFAULT_TARGET_IMAGES_PER_ARTIST = 5

RETRY_MANIFEST_ARTIFACT_KIND = "phase1_seed10_artist_image_collect_retry_manifest"
OUTPUT_ARTIFACT_KIND = "phase1_seed10_artist_image_collect_retry_run_summary"

CHILD_COLLECT_SCRIPT = Path("run_phase1_seed10_artist_image_collect.py")
SOURCE_CLI = "run_phase1_seed10_artist_image_collect_retry_run.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run artist image collect using retry manifest. "
            "This is a thin wrapper that delegates actual collect execution to "
            "run_phase1_seed10_artist_image_collect.py."
        )
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--retry-manifest", default="", help="retry manifest path")
    group.add_argument("--latest", action="store_true", help="resolve latest retry manifest")
    parser.add_argument(
        "--search-dir",
        default=str(DEFAULT_SEARCH_DIR),
        help=f"search directory for --latest (default: {DEFAULT_SEARCH_DIR})",
    )
    parser.add_argument("--glob", default="", help="optional glob override for --latest")
    parser.add_argument("--target-year", type=int, default=DEFAULT_TARGET_YEAR)
    parser.add_argument("--target-images-per-artist", type=int, default=DEFAULT_TARGET_IMAGES_PER_ARTIST)
    parser.add_argument("--output-json", default="", help="optional wrapper summary path")
    return parser.parse_args()


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
        if not text:
            return None
        try:
            return int(text)
        except ValueError:
            return None
    return None


def _tail_lines(text: str, max_lines: int = 30) -> str:
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text
    return "\n".join(lines[-max_lines:])


def main() -> int:
    args = parse_args()
    started_at = utc_now_iso()
    timestamp = utc_timestamp_compact()

    output_summary_path = (
        Path(args.output_json).resolve()
        if args.output_json
        else (DEFAULT_SUMMARY_DIR / f"phase1_seed10_artist_image_collect_retry_run_summary_{timestamp}.json").resolve()
    )

    summary: dict[str, Any] = {
        **build_artifact_header(OUTPUT_ARTIFACT_KIND, generated_by=SOURCE_CLI),
        "source_cli": SOURCE_CLI,
        "started_at": started_at,
        "completed_at": None,
        "retry_manifest_path_requested": args.retry_manifest if args.retry_manifest else "--latest",
        "retry_manifest_latest_resolved": bool(args.latest),
        "retry_manifest_path": None,
        "retry_manifest_case_count": 0,
        "executed_cases": 0,
        "target_year": int(args.target_year),
        "target_images_per_artist_requested": int(args.target_images_per_artist),
        "target_images_per_artist_effective": int(args.target_images_per_artist),
        "collect_run_started": False,
        "collect_run_executed": False,
        "child_collect_exit_code": None,
        "child_collect_command": [],
        "child_collect_stdout_tail": "",
        "child_collect_stderr_tail": "",
        "child_collect_summaries": [],
        "all_passed": False,
        "wrapper_exit_code": 1,
        "notes": [],
        "output_summary_path": str(output_summary_path),
    }

    def finalize(exit_code: int) -> int:
        summary["completed_at"] = utc_now_iso()
        summary["wrapper_exit_code"] = int(exit_code)
        write_json(output_summary_path, summary)
        print(
            "[DONE] artist_image_collect_retry_run "
            f"executed_cases={summary['executed_cases']} "
            f"child_exit={summary['child_collect_exit_code']} "
            f"wrapper_exit={summary['wrapper_exit_code']}"
        )
        print(f"[DONE] summary={output_summary_path}")
        return int(exit_code)

    if not CHILD_COLLECT_SCRIPT.exists():
        summary["notes"].append(f"child_collect_script_not_found:{CHILD_COLLECT_SCRIPT}")
        print(f"[ERROR] child_collect_script_not_found:{CHILD_COLLECT_SCRIPT}")
        return finalize(1)

    if args.retry_manifest:
        retry_manifest_path = Path(args.retry_manifest).resolve()
    else:
        latest_path, latest_error = resolve_latest_artifact(
            Path(args.search_dir).resolve(),
            RETRY_MANIFEST_ARTIFACT_KIND,
            glob_pattern=args.glob or None,
        )
        if latest_error:
            summary["notes"].append(latest_error)
            print(f"[ERROR] {latest_error}")
            return finalize(1)
        assert latest_path is not None
        retry_manifest_path = latest_path

    summary["retry_manifest_path"] = str(retry_manifest_path)

    if not retry_manifest_path.exists():
        summary["notes"].append(f"retry_manifest_not_found:{retry_manifest_path}")
        print(f"[ERROR] retry_manifest_not_found:{retry_manifest_path}")
        return finalize(1)

    try:
        retry_manifest = load_json(retry_manifest_path)
    except Exception as exc:  # noqa: BLE001
        summary["notes"].append(f"retry_manifest_load_failed:{exc}")
        print(f"[ERROR] retry_manifest_load_failed:{exc}")
        return finalize(1)

    raw_cases = retry_manifest.get("cases")
    if not isinstance(raw_cases, list):
        summary["notes"].append("retry_manifest_cases_not_array")
        print("[ERROR] retry_manifest_cases_not_array")
        return finalize(1)

    summary["retry_manifest_case_count"] = len(raw_cases)
    summary["executed_cases"] = len(raw_cases)

    if len(raw_cases) == 0:
        summary["collect_run_started"] = False
        summary["collect_run_executed"] = False
        summary["child_collect_exit_code"] = 0
        summary["all_passed"] = True
        summary["notes"].append("no_retry_cases_in_manifest")
        summary["notes"].append("no_retry_cases_selected")
        summary["retry_run_mode"] = "noop_empty_retry_manifest"
        print("[DONE] no-op: empty retry manifest")
        return finalize(0)

    target_values: set[int] = set()
    for case in raw_cases:
        if not isinstance(case, dict):
            continue
        target_images = _as_int(case.get("target_images"))
        if target_images is not None and target_images > 0:
            target_values.add(target_images)
    if target_values:
        if len(target_values) > 1:
            summary["notes"].append(
                f"mixed_target_images_in_manifest:{sorted(target_values)}:using_requested:{args.target_images_per_artist}"
            )
        if int(args.target_images_per_artist) not in target_values:
            summary["notes"].append(
                f"target_images_per_artist_override:{args.target_images_per_artist}:manifest_values={sorted(target_values)}"
            )

    child_summary_path = output_summary_path.with_name(f"{output_summary_path.stem}_child_collect_summary.json")
    child_cmd = [
        sys.executable,
        str(CHILD_COLLECT_SCRIPT),
        "--target-year",
        str(int(args.target_year)),
        "--target-images-per-artist",
        str(int(args.target_images_per_artist)),
        "--output-json",
        str(child_summary_path),
    ]
    summary["child_collect_command"] = child_cmd
    summary["collect_run_started"] = True
    summary["child_collect_summaries"] = [str(child_summary_path)]

    completed = subprocess.run(child_cmd, capture_output=True, text=True, check=False)
    summary["collect_run_executed"] = True
    summary["child_collect_exit_code"] = int(completed.returncode)
    summary["child_collect_stdout_tail"] = _tail_lines(completed.stdout)
    summary["child_collect_stderr_tail"] = _tail_lines(completed.stderr)

    if not child_summary_path.exists():
        summary["notes"].append(f"child_collect_summary_not_found:{child_summary_path}")
    else:
        try:
            child_summary_obj = load_json(child_summary_path)
            child_threshold_passed = child_summary_obj.get("threshold_passed")
            if isinstance(child_threshold_passed, bool):
                summary["child_threshold_passed"] = child_threshold_passed
        except Exception as exc:  # noqa: BLE001
            summary["notes"].append(f"child_collect_summary_load_failed:{exc}")

    if int(completed.returncode) == 0:
        summary["all_passed"] = True
        summary["notes"].append("collect_retry_run_completed")
        return finalize(0)

    summary["all_passed"] = False
    summary["notes"].append("collect_retry_run_failed")
    return finalize(1)


if __name__ == "__main__":
    raise SystemExit(main())
