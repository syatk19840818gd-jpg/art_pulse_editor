#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from phase1_ledger_contract import (
    GUARD_REQUIRED_INPUT_FILES_ARTISTS,
    GUARD_REQUIRED_INPUT_FILES_EXHIBITIONS,
)

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
        "required_input_files": list(GUARD_REQUIRED_INPUT_FILES_EXHIBITIONS),
        "required_summary_keys_drop": [],
        "support_mode": "active",
        "activation_conditions": [],
        "reserved_reason": "",
    },
    "artists_text": {
        "required_input_files": list(GUARD_REQUIRED_INPUT_FILES_ARTISTS),
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


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def validate_category_profiles_config(config_obj: Any) -> tuple[bool, str | None, str | None]:
    """
    Validate external category profile config with minimal safety checks.
    Returns:
      (is_valid, error_code, error_detail)
    error_code is normalized as `config_schema_error:*` when invalid.
    """
    if not isinstance(config_obj, dict):
        return False, "config_schema_error:root_not_dict", "config root must be a JSON object"

    config_version_raw = config_obj.get("category_profile_config_version")
    if config_version_raw is not None and not _is_non_empty_string(config_version_raw):
        return (
            False,
            "config_schema_error:type_error:category_profile_config_version",
            "category_profile_config_version must be a non-empty string when present",
        )

    if "categories" not in config_obj:
        return False, "config_schema_error:missing_categories", "missing required key: categories"

    categories_obj = config_obj.get("categories")
    if not isinstance(categories_obj, dict):
        return False, "config_schema_error:type_error:categories", "categories must be a JSON object"

    for required_category in ("exhibitions_text", "artists_text"):
        if required_category not in categories_obj:
            return (
                False,
                f"config_schema_error:missing_category:{required_category}",
                f"missing required category profile: {required_category}",
            )

    for category, profile in categories_obj.items():
        if not isinstance(category, str) or not category:
            return False, "config_schema_error:category_key_invalid", "category keys must be non-empty strings"
        if not isinstance(profile, dict):
            return (
                False,
                f"config_schema_error:type_error:{category}",
                f"category profile must be object: {category}",
            )

        if "required_input_files" not in profile:
            return (
                False,
                f"config_schema_error:missing_key:{category}.required_input_files",
                f"missing required key for {category}: required_input_files",
            )
        if not _is_string_list(profile.get("required_input_files")):
            return (
                False,
                f"config_schema_error:type_error:{category}.required_input_files",
                f"{category}.required_input_files must be list[str]",
            )

        if "support_mode_configured" in profile:
            support_key = "support_mode_configured"
        else:
            support_key = "support_mode"
        if support_key not in profile:
            return (
                False,
                f"config_schema_error:missing_key:{category}.support_mode",
                f"missing required key for {category}: support_mode (or support_mode_configured)",
            )
        if not _is_non_empty_string(profile.get(support_key)):
            return (
                False,
                f"config_schema_error:type_error:{category}.{support_key}",
                f"{category}.{support_key} must be non-empty string",
            )

        has_required_summary_keys = "required_summary_keys" in profile
        has_required_summary_drop = "required_summary_keys_drop" in profile
        has_required_summary_add = "required_summary_keys_add" in profile
        if not (has_required_summary_keys or has_required_summary_drop or has_required_summary_add):
            return (
                False,
                f"config_schema_error:missing_key:{category}.required_summary_keys",
                f"{category} must define required_summary_keys or required_summary_keys_drop/add",
            )

        if has_required_summary_keys and not _is_string_list(profile.get("required_summary_keys")):
            return (
                False,
                f"config_schema_error:type_error:{category}.required_summary_keys",
                f"{category}.required_summary_keys must be list[str]",
            )
        if has_required_summary_drop and not _is_string_list(profile.get("required_summary_keys_drop")):
            return (
                False,
                f"config_schema_error:type_error:{category}.required_summary_keys_drop",
                f"{category}.required_summary_keys_drop must be list[str]",
            )
        if has_required_summary_add and not _is_string_list(profile.get("required_summary_keys_add")):
            return (
                False,
                f"config_schema_error:type_error:{category}.required_summary_keys_add",
                f"{category}.required_summary_keys_add must be list[str]",
            )

        if "activation_conditions" not in profile:
            return (
                False,
                f"config_schema_error:missing_key:{category}.activation_conditions",
                f"missing required key for {category}: activation_conditions",
            )
        if not _is_string_list(profile.get("activation_conditions")):
            return (
                False,
                f"config_schema_error:type_error:{category}.activation_conditions",
                f"{category}.activation_conditions must be list[str]",
            )

        if "reserved_reason" not in profile:
            return (
                False,
                f"config_schema_error:missing_key:{category}.reserved_reason",
                f"missing required key for {category}: reserved_reason",
            )
        reserved_reason = profile.get("reserved_reason")
        if not isinstance(reserved_reason, str):
            return (
                False,
                f"config_schema_error:type_error:{category}.reserved_reason",
                f"{category}.reserved_reason must be string",
            )

        if "profile_version" in profile and not _is_non_empty_string(profile.get("profile_version")):
            return (
                False,
                f"config_schema_error:type_error:{category}.profile_version",
                f"{category}.profile_version must be non-empty string when present",
            )

    return True, None, None


def _normalize_category_profiles_config(
    config_obj: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], str]:
    config_version_raw = config_obj.get("category_profile_config_version")
    if _is_non_empty_string(config_version_raw):
        config_version = str(config_version_raw).strip()
    else:
        config_version = DEFAULT_CATEGORY_PROFILE_CONFIG_VERSION

    categories_obj = config_obj.get("categories", {})
    normalized_profiles: dict[str, dict[str, Any]] = {}
    if isinstance(categories_obj, dict):
        for category, profile in categories_obj.items():
            if isinstance(category, str) and category and isinstance(profile, dict):
                normalized_profile = copy.deepcopy(profile)
                if "support_mode" not in normalized_profile and _is_non_empty_string(
                    normalized_profile.get("support_mode_configured")
                ):
                    normalized_profile["support_mode"] = str(normalized_profile["support_mode_configured"]).strip()
                normalized_profiles[category] = normalized_profile

    return normalized_profiles, config_version


def load_category_profiles(config_path: str | Path) -> dict[str, Any]:
    resolved_path = Path(config_path).expanduser().resolve()
    default_profiles = _copy_default_profiles()

    if not resolved_path.exists():
        return {
            "profiles": default_profiles,
            "source": "builtin_fallback",
            "config_path": str(resolved_path),
            "config_loaded": False,
            "config_error": "config_missing:file_not_found",
            "config_error_detail": f"config path does not exist: {resolved_path}",
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
            "config_error": "config_json_decode_error:invalid_json",
            "config_error_detail": str(exc),
            "config_version_effective": DEFAULT_CATEGORY_PROFILE_CONFIG_VERSION,
        }
    except OSError as exc:
        return {
            "profiles": default_profiles,
            "source": "builtin_fallback",
            "config_path": str(resolved_path),
            "config_loaded": False,
            "config_error": "config_missing:read_error",
            "config_error_detail": str(exc),
            "config_version_effective": DEFAULT_CATEGORY_PROFILE_CONFIG_VERSION,
        }

    is_valid, error_code, error_detail = validate_category_profiles_config(raw_obj)
    if not is_valid:
        return {
            "profiles": default_profiles,
            "source": "builtin_fallback",
            "config_path": str(resolved_path),
            "config_loaded": False,
            "config_error": error_code or "config_schema_error:unknown",
            "config_error_detail": error_detail,
            "config_version_effective": DEFAULT_CATEGORY_PROFILE_CONFIG_VERSION,
        }

    assert isinstance(raw_obj, dict)
    normalized_profiles, config_version = _normalize_category_profiles_config(raw_obj)
    return {
        "profiles": normalized_profiles,
        "source": "external_config",
        "config_path": str(resolved_path),
        "config_loaded": True,
        "config_error": None,
        "config_error_detail": None,
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
