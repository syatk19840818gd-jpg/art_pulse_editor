#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

REGRESSION_EXIT_CODE = 2
INCOMPATIBLE_EXIT_CODE = 3
GUARD_SCHEMA_VERSION = "1.0"
GUARD_SCHEMA_VERSION_POLICY = "both_present_must_match;missing_allowed_with_warning"
DEFAULT_GUARD_CATEGORY = "exhibitions_text"
GUARD_CATEGORY_PROFILES: dict[str, dict[str, Any]] = {
    "exhibitions_text": {
        "required_input_files": ["run_summary_path", "visited_pages_path", "failed_fetches_path", "output_files"],
        "required_summary_keys_drop": [],
        "support_mode": "active",
    },
    "artists_text": {
        "required_input_files": ["run_summary_path", "visited_pages_path", "failed_fetches_path"],
        "required_summary_keys_drop": ["output_files"],
        "support_mode": "reserved_minimal",
    },
}
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
