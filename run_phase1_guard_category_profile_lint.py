#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from phase1_guard_common import (
    DEFAULT_CATEGORY_PROFILE_CONFIG_PATH,
    resolve_logs_dir,
    load_category_profiles,
    utc_now_iso,
    utc_timestamp_compact,
    write_summary_json,
)

DEFAULT_LOGS_DIR = Path("data/phase1_seed10/logs")
OUTPUT_TEMPLATE = "phase1_guard_category_profile_lint_{timestamp}.json"
SOURCE_CLI = "run_phase1_guard_category_profile_lint.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Lint phase1 guard category profile config without running guard comparisons."
    )
    parser.add_argument(
        "--config-path",
        default=str(DEFAULT_CATEGORY_PROFILE_CONFIG_PATH),
        help=f"category profile config path (default: {DEFAULT_CATEGORY_PROFILE_CONFIG_PATH})",
    )
    parser.add_argument(
        "--logs-dir",
        default=str(DEFAULT_LOGS_DIR),
        help=f"directory for lint summary output (default: {DEFAULT_LOGS_DIR})",
    )
    parser.add_argument(
        "--output-path",
        default="",
        help="optional output summary path (default: <logs-dir>/phase1_guard_category_profile_lint_<timestamp>.json)",
    )
    return parser.parse_args()


def normalize_optional_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized if normalized else None


def normalize_optional_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return None


def ensure_unique_output_path(path: Path) -> Path:
    if not path.exists():
        return path
    index = 1
    while True:
        candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
        if not candidate.exists():
            return candidate
        index += 1


def main() -> int:
    args = parse_args()
    checked_at = utc_now_iso()
    timestamp = utc_timestamp_compact()

    config_path = resolve_logs_dir(args.config_path)
    logs_dir = resolve_logs_dir(args.logs_dir)
    output_path = (
        resolve_logs_dir(args.output_path)
        if args.output_path
        else logs_dir / OUTPUT_TEMPLATE.format(timestamp=timestamp)
    )
    output_path = ensure_unique_output_path(output_path)

    bundle = load_category_profiles(config_path)
    config_source = normalize_optional_string(bundle.get("source")) or "builtin_fallback"
    config_loaded = normalize_optional_bool(bundle.get("config_loaded"))
    config_error_code = normalize_optional_string(bundle.get("config_error"))
    config_error_detail = normalize_optional_string(bundle.get("config_error_detail"))
    config_version_effective = normalize_optional_string(bundle.get("config_version_effective"))

    profiles_obj = bundle.get("profiles")
    if isinstance(profiles_obj, dict):
        categories_effective = sorted([key for key in profiles_obj.keys() if isinstance(key, str) and key])
    else:
        categories_effective = []

    config_exists = config_path.exists()
    config_valid = config_source == "external_config" and bool(config_loaded) and config_error_code is None
    exit_code = 0 if config_valid else 1

    payload = {
        "checked_at": checked_at,
        "source_cli": SOURCE_CLI,
        "config_path": str(config_path),
        "config_exists": config_exists,
        "config_valid": config_valid,
        "config_error_code": config_error_code,
        "config_error_detail": config_error_detail,
        "category_profile_source": config_source,
        "category_profile_config_loaded": config_loaded,
        "category_profile_config_version_effective": config_version_effective,
        "categories_effective": categories_effective,
        "output_path": str(output_path),
        "exit_code": exit_code,
        "exit_code_meaning": {
            "0": "lint_pass",
            "1": "lint_fail",
        },
    }

    write_summary_json(output_path, payload)

    print(f"[DONE] Phase1 category profile lint checked_at={checked_at}")
    print(f"[DONE] config={config_path} valid={config_valid} source={config_source} error={config_error_code}")
    print(f"[DONE] summary={output_path}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
