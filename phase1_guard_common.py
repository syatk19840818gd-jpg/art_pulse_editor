#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

REGRESSION_EXIT_CODE = 2
INCOMPATIBLE_EXIT_CODE = 3
GUARD_SCHEMA_VERSION = "1.0"
GUARD_SCHEMA_VERSION_POLICY = "both_present_must_match;missing_allowed_with_warning"
DEFAULT_GUARD_CATEGORY = "exhibitions_text"
GUARD_CATEGORY_PROFILE_VERSION = "1.1"
DEFAULT_CATEGORY_PROFILE_CONFIG_VERSION = "1.0"
DEFAULT_CATEGORY_PROFILE_CONFIG_PATH = Path("config/phase1_guard_category_profiles.json")
DEFAULT_CATEGORY_PROFILES: dict[str, dict[str, Any]] = {
    "exhibitions_text": {
        "required_input_files": ["run_summary_path", "visited_pages_path", "failed_fetches_path", "output_files"],
        "required_summary_keys_drop": [],
        "support_mode": "active",
        "activation_conditions": [],
        "reserved_reason": "",
    },
    "artists_text": {
        "required_input_files": ["run_summary_path", "visited_pages_path", "failed_fetches_path"],
        "required_summary_keys_drop": ["output_files"],
        "required_summary_keys_add": [],
        "support_mode": "reserved_minimal",
        "activation_conditions": [
            "artists_raw_files_pattern_confirmed_under_<logs-dir>/../raw",
            "artists_run_summary_and_ledgers_exist_for_target_year",
            "at_least_one_artists_guard_run_verified_and_saved",
        ],
        "reserved_reason": "artists_summary_and_raw_conventions_not_finalized",
    },
}
# Backward-compatible alias: existing call sites may still reference this symbol.
GUARD_CATEGORY_PROFILES = DEFAULT_CATEGORY_PROFILES
GUARD_CATEGORY_COMPATIBILITY_POLICY = "both_present_must_match;missing_allowed_with_warning;strict_mismatch_incompatible"
EXIT_CODE_MEANING = {
    "0": "pass（差分なし or 差分ありだが回帰なし）",
    "2": "regression（回帰検知）",
    "3": "incompatible（比較不成立）",
}


def resolve_logs_dir(path_value: str | Path) -> Path:
    return Path(path_value).expanduser().resolve()


def paths_equal(left: Path, right: Path) -> bool:
    return left.resolve() == right.resolve()


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_summary_json(path: Path, payload: Mapping[str, Any]) -> None:
    ensure_parent_dir(path)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def utc_timestamp_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _copy_default_profiles() -> dict[str, dict[str, Any]]:
    return copy.deepcopy(DEFAULT_CATEGORY_PROFILES)


def _validate_category_profiles_config(config_obj: Any) -> tuple[dict[str, dict[str, Any]] | None, str | None, str | None]:
    if not isinstance(config_obj, dict):
        return None, None, "config_root_not_dict"

    config_version_raw = config_obj.get("category_profile_config_version")
    if config_version_raw is None:
        config_version = DEFAULT_CATEGORY_PROFILE_CONFIG_VERSION
    elif isinstance(config_version_raw, str) and config_version_raw.strip():
        config_version = config_version_raw.strip()
    else:
        return None, None, "category_profile_config_version_invalid"

    categories_obj = config_obj.get("categories")
    if not isinstance(categories_obj, dict):
        return None, None, "categories_not_dict"

    if DEFAULT_GUARD_CATEGORY not in categories_obj:
        return None, None, f"default_category_missing:{DEFAULT_GUARD_CATEGORY}"

    normalized_profiles: dict[str, dict[str, Any]] = {}
    for category, profile in categories_obj.items():
        if not isinstance(category, str) or not category:
            return None, None, "category_key_invalid"
        if not isinstance(profile, dict):
            return None, None, f"category_profile_not_dict:{category}"
        normalized_profiles[category] = copy.deepcopy(profile)

    if not normalized_profiles:
        return None, None, "categories_empty"

    return normalized_profiles, config_version, None


def load_category_profiles(config_path: str | Path) -> dict[str, Any]:
    resolved_path = Path(config_path).expanduser().resolve()
    default_profiles = _copy_default_profiles()

    if not resolved_path.exists():
        return {
            "profiles": default_profiles,
            "source": "builtin_fallback",
            "config_path": str(resolved_path),
            "config_loaded": False,
            "config_error": "config_path_not_found",
            "config_version_effective": DEFAULT_CATEGORY_PROFILE_CONFIG_VERSION,
        }

    try:
        raw_obj = json.loads(resolved_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {
            "profiles": default_profiles,
            "source": "builtin_fallback",
            "config_path": str(resolved_path),
            "config_loaded": False,
            "config_error": f"config_json_decode_error:{exc}",
            "config_version_effective": DEFAULT_CATEGORY_PROFILE_CONFIG_VERSION,
        }
    except OSError as exc:
        return {
            "profiles": default_profiles,
            "source": "builtin_fallback",
            "config_path": str(resolved_path),
            "config_loaded": False,
            "config_error": f"config_os_error:{exc}",
            "config_version_effective": DEFAULT_CATEGORY_PROFILE_CONFIG_VERSION,
        }

    normalized_profiles, config_version, validation_error = _validate_category_profiles_config(raw_obj)
    if validation_error is not None or normalized_profiles is None:
        return {
            "profiles": default_profiles,
            "source": "builtin_fallback",
            "config_path": str(resolved_path),
            "config_loaded": False,
            "config_error": f"config_schema_error:{validation_error}",
            "config_version_effective": DEFAULT_CATEGORY_PROFILE_CONFIG_VERSION,
        }

    return {
        "profiles": normalized_profiles,
        "source": "external_config",
        "config_path": str(resolved_path),
        "config_loaded": True,
        "config_error": None,
        "config_version_effective": config_version,
    }


def get_effective_category_profiles(config_path: str | Path | None = None) -> dict[str, Any]:
    if config_path is None:
        target_path: Path = DEFAULT_CATEGORY_PROFILE_CONFIG_PATH
    elif isinstance(config_path, Path):
        target_path = config_path
    elif isinstance(config_path, str):
        target_path = Path(config_path) if config_path else DEFAULT_CATEGORY_PROFILE_CONFIG_PATH
    else:
        target_path = DEFAULT_CATEGORY_PROFILE_CONFIG_PATH
    return load_category_profiles(target_path)
