#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOG_DIR = Path("data/phase1_seed10/logs")
DEFAULT_SUMMARY_TEMPLATE = "run_summary_seed10_{target_year}.json"
OUTPUT_TEMPLATE = "phase1_guard_summary_{target_year}_{timestamp}.json"
GUARD_SCHEMA_VERSION = "1.0"
GENERATED_BY = "run_compare_phase1_guard.py"

REQUIRED_SUMMARY_KEYS = {
    "target_year",
    "records_saved_total",
    "existing_records_total",
    "new_records_saved_total",
    "records_total_after_run",
    "records_saved_by_fair",
    "failed_fetches_new_in_run",
    "failed_fetches_total_ledger",
    "visited_pages_total_ledger",
    "skipped_total",
    "skipped_by_reason",
    "output_files",
    "failed_fetches_path",
    "visited_pages_path",
}

MANIFEST_MIN_KEYS = {"target_year", "generated_at", "files"}
FAILED_FETCH_REQUIRED_FIELDS = {"raw_url", "reason_code", "attempt_count_or_retry_count", "last_attempt_at_or_last_failed_at"}


@dataclass
class LedgerLoadResult:
    path: Path
    exists: bool
    format: str
    entries: dict[str, dict[str, Any]]
    load_error: str | None
    key_hash_mismatch_count: int
    missing_hash_field_count: int


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Phase1 seed10 guard checks for Exhibitions/Artists summaries and ledgers."
    )
    parser.add_argument("--target-year", type=int, required=True, help="target year (e.g. 2025)")
    parser.add_argument(
        "--summary-path",
        default="",
        help="run_summary path. Default: data/phase1_seed10/logs/run_summary_seed10_<target_year>.json",
    )
    parser.add_argument("--visited-path", default="", help="override visited_pages path")
    parser.add_argument("--failed-path", default="", help="override failed_fetches path")
    parser.add_argument("--manifest-path", default="", help="optional artifact_manifest path")
    parser.add_argument(
        "--fail-on-mismatch",
        action="store_true",
        help="return non-zero when mismatch_fields is non-empty",
    )
    return parser.parse_args()


def safe_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def load_json_object(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, "MISSING_FILE"
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, f"JSON_DECODE_ERROR: {exc}"
    except OSError as exc:
        return None, f"OS_ERROR: {exc}"

    if not isinstance(obj, dict):
        return None, f"INVALID_ROOT_TYPE:{type(obj).__name__}"
    return obj, None


def normalize_entry_key(entry: dict[str, Any], hash_field: str) -> str | None:
    value = entry.get(hash_field)
    return value if isinstance(value, str) and value else None


def load_ledger(path: Path, hash_field: str) -> LedgerLoadResult:
    if not path.exists():
        return LedgerLoadResult(
            path=path,
            exists=False,
            format="missing",
            entries={},
            load_error="MISSING_FILE",
            key_hash_mismatch_count=0,
            missing_hash_field_count=0,
        )

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return LedgerLoadResult(
            path=path,
            exists=True,
            format="unknown",
            entries={},
            load_error=f"JSON_DECODE_ERROR: {exc}",
            key_hash_mismatch_count=0,
            missing_hash_field_count=0,
        )
    except OSError as exc:
        return LedgerLoadResult(
            path=path,
            exists=True,
            format="unknown",
            entries={},
            load_error=f"OS_ERROR: {exc}",
            key_hash_mismatch_count=0,
            missing_hash_field_count=0,
        )

    entries: dict[str, dict[str, Any]] = {}
    key_hash_mismatch_count = 0
    missing_hash_field_count = 0

    if isinstance(raw, dict):
        ledger_format = "dict"
        for key, value in raw.items():
            if not isinstance(value, dict):
                missing_hash_field_count += 1
                continue
            entry_hash = normalize_entry_key(value, hash_field)
            if not entry_hash:
                missing_hash_field_count += 1
                continue
            if entry_hash != key:
                key_hash_mismatch_count += 1
            entries[key] = value
    elif isinstance(raw, list):
        ledger_format = "list"
        for idx, value in enumerate(raw):
            if not isinstance(value, dict):
                missing_hash_field_count += 1
                continue
            entry_hash = normalize_entry_key(value, hash_field)
            if not entry_hash:
                missing_hash_field_count += 1
                continue
            synthetic_key = f"{entry_hash}:{idx}"
            entries[synthetic_key] = value
    else:
        ledger_format = "unknown"
        return LedgerLoadResult(
            path=path,
            exists=True,
            format=ledger_format,
            entries={},
            load_error=f"INVALID_ROOT_TYPE:{type(raw).__name__}",
            key_hash_mismatch_count=0,
            missing_hash_field_count=0,
        )

    return LedgerLoadResult(
        path=path,
        exists=True,
        format=ledger_format,
        entries=entries,
        load_error=None,
        key_hash_mismatch_count=key_hash_mismatch_count,
        missing_hash_field_count=missing_hash_field_count,
    )


def count_jsonl_records(path: Path) -> tuple[int | None, str | None]:
    if not path.exists():
        return None, "MISSING_FILE"
    count = 0
    try:
        with path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line:
                    continue
                count += 1
    except OSError as exc:
        return None, f"OS_ERROR: {exc}"
    return count, None


def resolve_path(override: str, fallback: Any) -> Path | None:
    if override:
        return Path(override)
    if isinstance(fallback, str) and fallback:
        return Path(fallback)
    return None


def load_manifest_check(path: Path | None, target_year: int) -> dict[str, Any]:
    if path is None:
        return {
            "status": "skipped_optional",
            "manifest_path": None,
            "exists": False,
            "passed": True,
            "errors": [],
        }

    result: dict[str, Any] = {
        "status": "checked",
        "manifest_path": str(path),
        "exists": path.exists(),
        "passed": True,
        "errors": [],
    }

    if not path.exists():
        result["passed"] = False
        result["errors"].append("manifest_path_missing")
        return result

    obj, err = load_json_object(path)
    if err:
        result["passed"] = False
        result["errors"].append(f"manifest_load_error:{err}")
        return result

    assert obj is not None
    missing = sorted(MANIFEST_MIN_KEYS - set(obj.keys()))
    if missing:
        result["passed"] = False
        result["errors"].append(f"manifest_missing_keys:{','.join(missing)}")

    files = obj.get("files")
    if not isinstance(files, list):
        result["passed"] = False
        result["errors"].append("manifest_files_not_list")

    manifest_year = safe_int(obj.get("target_year"))
    if manifest_year is not None and manifest_year != target_year:
        result["passed"] = False
        result["errors"].append(f"manifest_target_year_mismatch:{manifest_year}!={target_year}")

    return result


def validate_failed_fetch_schema(entries: dict[str, dict[str, Any]]) -> dict[str, Any]:
    missing_counts = {
        "raw_url": 0,
        "reason_code": 0,
        "attempt_count_or_retry_count": 0,
        "last_attempt_at_or_last_failed_at": 0,
    }

    for entry in entries.values():
        raw_url = entry.get("raw_url")
        reason_code = entry.get("reason_code")
        attempt_count = entry.get("attempt_count")
        retry_count = entry.get("retry_count")
        last_attempt = entry.get("last_attempt_at")
        last_failed = entry.get("last_failed_at")

        if not (isinstance(raw_url, str) and raw_url):
            missing_counts["raw_url"] += 1
        if not (isinstance(reason_code, str) and reason_code):
            missing_counts["reason_code"] += 1
        attempt_valid = safe_int(attempt_count)
        retry_valid = safe_int(retry_count)
        if attempt_valid is None and retry_valid is None:
            missing_counts["attempt_count_or_retry_count"] += 1
        if not ((isinstance(last_attempt, str) and last_attempt) or (isinstance(last_failed, str) and last_failed)):
            missing_counts["last_attempt_at_or_last_failed_at"] += 1

    passed = all(value == 0 for value in missing_counts.values())
    return {
        "passed": passed,
        "entry_count": len(entries),
        "required_fields": sorted(FAILED_FETCH_REQUIRED_FIELDS),
        "missing_counts": missing_counts,
    }


def main() -> int:
    args = parse_args()
    started_at = utc_now_iso()
    print(f"[START] Phase1 guard compare at {started_at}")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    summary_path = Path(args.summary_path) if args.summary_path else LOG_DIR / DEFAULT_SUMMARY_TEMPLATE.format(target_year=args.target_year)

    check_results: dict[str, Any] = {}
    mismatch_fields: list[str] = []

    summary_obj, summary_load_error = load_json_object(summary_path)
    if summary_load_error:
        mismatch_fields.append("run_summary_load_error")
        check_results["run_summary_load"] = {
            "passed": False,
            "path": str(summary_path),
            "error": summary_load_error,
        }
        summary_obj = {}
    else:
        check_results["run_summary_load"] = {
            "passed": True,
            "path": str(summary_path),
            "error": None,
        }

    assert isinstance(summary_obj, dict)

    missing_summary_keys = sorted(REQUIRED_SUMMARY_KEYS - set(summary_obj.keys()))
    required_keys_passed = len(missing_summary_keys) == 0
    check_results["required_summary_keys"] = {
        "passed": required_keys_passed,
        "missing_keys": missing_summary_keys,
        "required_keys": sorted(REQUIRED_SUMMARY_KEYS),
    }
    if not required_keys_passed:
        mismatch_fields.append("required_summary_keys_missing")

    # Input paths (summary values can be overridden by CLI args).
    visited_path = resolve_path(args.visited_path, summary_obj.get("visited_pages_path"))
    failed_path = resolve_path(args.failed_path, summary_obj.get("failed_fetches_path"))

    output_files = summary_obj.get("output_files")
    output_file_paths: dict[str, Path] = {}
    output_file_errors: list[str] = []
    if isinstance(output_files, dict):
        for fair_slug, value in output_files.items():
            if not (isinstance(fair_slug, str) and isinstance(value, str) and value):
                output_file_errors.append(f"invalid_output_file_entry:{fair_slug}")
                continue
            output_file_paths[fair_slug] = Path(value)
    else:
        output_file_errors.append("output_files_not_dict")

    if output_file_errors:
        mismatch_fields.append("output_files_invalid")

    output_file_checks: dict[str, Any] = {}
    output_file_paths_exist = True
    for fair_slug, path in sorted(output_file_paths.items()):
        record_count, record_error = count_jsonl_records(path)
        exists = path.exists()
        if not exists:
            output_file_paths_exist = False
            mismatch_fields.append(f"output_file_missing:{fair_slug}")
        output_file_checks[fair_slug] = {
            "path": str(path),
            "exists": exists,
            "record_count": record_count,
            "record_count_error": record_error,
        }

    check_results["output_files"] = {
        "passed": output_file_paths_exist and not output_file_errors,
        "errors": output_file_errors,
        "items": output_file_checks,
    }

    if visited_path is None:
        mismatch_fields.append("visited_path_missing")
        visited_ledger = LedgerLoadResult(
            path=Path(""),
            exists=False,
            format="missing",
            entries={},
            load_error="MISSING_PATH_IN_SUMMARY",
            key_hash_mismatch_count=0,
            missing_hash_field_count=0,
        )
    else:
        visited_ledger = load_ledger(visited_path, "page_url_hash")
        if visited_ledger.load_error:
            mismatch_fields.append("visited_ledger_load_error")

    if failed_path is None:
        mismatch_fields.append("failed_path_missing")
        failed_ledger = LedgerLoadResult(
            path=Path(""),
            exists=False,
            format="missing",
            entries={},
            load_error="MISSING_PATH_IN_SUMMARY",
            key_hash_mismatch_count=0,
            missing_hash_field_count=0,
        )
    else:
        failed_ledger = load_ledger(failed_path, "fail_hash")
        if failed_ledger.load_error:
            mismatch_fields.append("failed_ledger_load_error")

    check_results["visited_ledger"] = {
        "passed": visited_ledger.load_error is None
        and visited_ledger.key_hash_mismatch_count == 0
        and visited_ledger.missing_hash_field_count == 0,
        "path": str(visited_ledger.path),
        "exists": visited_ledger.exists,
        "format": visited_ledger.format,
        "entry_count": len(visited_ledger.entries),
        "load_error": visited_ledger.load_error,
        "key_hash_mismatch_count": visited_ledger.key_hash_mismatch_count,
        "missing_hash_field_count": visited_ledger.missing_hash_field_count,
    }
    if visited_ledger.key_hash_mismatch_count > 0:
        mismatch_fields.append("visited_key_hash_mismatch")
    if visited_ledger.missing_hash_field_count > 0:
        mismatch_fields.append("visited_missing_hash_field")

    check_results["failed_ledger"] = {
        "passed": failed_ledger.load_error is None
        and failed_ledger.key_hash_mismatch_count == 0
        and failed_ledger.missing_hash_field_count == 0,
        "path": str(failed_ledger.path),
        "exists": failed_ledger.exists,
        "format": failed_ledger.format,
        "entry_count": len(failed_ledger.entries),
        "load_error": failed_ledger.load_error,
        "key_hash_mismatch_count": failed_ledger.key_hash_mismatch_count,
        "missing_hash_field_count": failed_ledger.missing_hash_field_count,
    }
    if failed_ledger.key_hash_mismatch_count > 0:
        mismatch_fields.append("failed_key_hash_mismatch")
    if failed_ledger.missing_hash_field_count > 0:
        mismatch_fields.append("failed_missing_hash_field")

    # Internal consistency checks
    existing_records_total = safe_int(summary_obj.get("existing_records_total"))
    new_records_saved_total = safe_int(summary_obj.get("new_records_saved_total"))
    records_saved_total = safe_int(summary_obj.get("records_saved_total"))
    records_total_after_run = safe_int(summary_obj.get("records_total_after_run"))

    skipped_total = safe_int(summary_obj.get("skipped_total"))
    skipped_by_reason = summary_obj.get("skipped_by_reason")
    skipped_sum = None
    if isinstance(skipped_by_reason, dict):
        skipped_values = [safe_int(value) for value in skipped_by_reason.values()]
        if all(value is not None for value in skipped_values):
            skipped_sum = sum(value for value in skipped_values if value is not None)

    records_saved_by_fair = summary_obj.get("records_saved_by_fair")
    records_saved_by_fair_sum = None
    if isinstance(records_saved_by_fair, dict):
        fair_values = [safe_int(value) for value in records_saved_by_fair.values()]
        if all(value is not None for value in fair_values):
            records_saved_by_fair_sum = sum(value for value in fair_values if value is not None)

    internal_errors: list[str] = []
    if None in {existing_records_total, new_records_saved_total, records_total_after_run}:
        internal_errors.append("records_total_fields_not_int")
    else:
        expected_total = existing_records_total + new_records_saved_total
        if records_total_after_run != expected_total:
            internal_errors.append(
                f"records_total_after_run_mismatch:{records_total_after_run}!={expected_total}"
            )

    if records_saved_total is None or new_records_saved_total is None:
        internal_errors.append("records_saved_fields_not_int")
    elif records_saved_total != new_records_saved_total:
        internal_errors.append(
            f"records_saved_total_mismatch:{records_saved_total}!={new_records_saved_total}"
        )

    if records_saved_by_fair_sum is None or new_records_saved_total is None:
        internal_errors.append("records_saved_by_fair_not_int")
    elif records_saved_by_fair_sum != new_records_saved_total:
        internal_errors.append(
            f"records_saved_by_fair_sum_mismatch:{records_saved_by_fair_sum}!={new_records_saved_total}"
        )

    if skipped_sum is None or skipped_total is None:
        internal_errors.append("skipped_fields_not_int")
    elif skipped_total != skipped_sum:
        internal_errors.append(f"skipped_total_mismatch:{skipped_total}!={skipped_sum}")

    summary_target_year = safe_int(summary_obj.get("target_year"))
    if summary_target_year is None:
        internal_errors.append("summary_target_year_not_int")
    elif summary_target_year != args.target_year:
        internal_errors.append(f"target_year_mismatch:{summary_target_year}!={args.target_year}")

    check_results["internal_consistency"] = {
        "passed": len(internal_errors) == 0,
        "errors": internal_errors,
        "values": {
            "existing_records_total": existing_records_total,
            "new_records_saved_total": new_records_saved_total,
            "records_saved_total": records_saved_total,
            "records_total_after_run": records_total_after_run,
            "records_saved_by_fair_sum": records_saved_by_fair_sum,
            "skipped_total": skipped_total,
            "skipped_by_reason_sum": skipped_sum,
            "summary_target_year": summary_target_year,
            "cli_target_year": args.target_year,
        },
    }
    if internal_errors:
        mismatch_fields.append("internal_consistency_mismatch")

    # Summary vs ledger count consistency
    visited_total_ledger = safe_int(summary_obj.get("visited_pages_total_ledger"))
    failed_total_ledger = safe_int(summary_obj.get("failed_fetches_total_ledger"))

    summary_ledger_errors: list[str] = []
    if visited_total_ledger is None:
        summary_ledger_errors.append("visited_pages_total_ledger_not_int")
    elif visited_total_ledger != len(visited_ledger.entries):
        summary_ledger_errors.append(
            f"visited_count_mismatch:{visited_total_ledger}!={len(visited_ledger.entries)}"
        )

    if failed_total_ledger is None:
        summary_ledger_errors.append("failed_fetches_total_ledger_not_int")
    elif failed_total_ledger != len(failed_ledger.entries):
        summary_ledger_errors.append(
            f"failed_count_mismatch:{failed_total_ledger}!={len(failed_ledger.entries)}"
        )

    check_results["summary_vs_ledger_counts"] = {
        "passed": len(summary_ledger_errors) == 0,
        "errors": summary_ledger_errors,
        "values": {
            "summary_visited_pages_total_ledger": visited_total_ledger,
            "actual_visited_entries": len(visited_ledger.entries),
            "summary_failed_fetches_total_ledger": failed_total_ledger,
            "actual_failed_entries": len(failed_ledger.entries),
        },
    }
    if summary_ledger_errors:
        mismatch_fields.append("summary_ledger_count_mismatch")

    failed_schema_check = validate_failed_fetch_schema(failed_ledger.entries)
    check_results["failed_fetches_schema"] = failed_schema_check
    if not failed_schema_check["passed"]:
        mismatch_fields.append("failed_fetches_schema_invalid")

    manifest_path = Path(args.manifest_path) if args.manifest_path else None
    manifest_check = load_manifest_check(manifest_path, args.target_year)
    check_results["manifest"] = manifest_check
    if not manifest_check.get("passed", False):
        mismatch_fields.append("manifest_invalid")

    # Deduplicate mismatch fields, preserve first-seen order.
    deduped_mismatches: list[str] = []
    seen: set[str] = set()
    for item in mismatch_fields:
        if item in seen:
            continue
        seen.add(item)
        deduped_mismatches.append(item)

    guard_passed = len(deduped_mismatches) == 0

    output_path = LOG_DIR / OUTPUT_TEMPLATE.format(target_year=args.target_year, timestamp=timestamp)
    summary_payload = {
        "started_at": started_at,
        "completed_at": utc_now_iso(),
        "generated_by": GENERATED_BY,
        "guard_schema_version": GUARD_SCHEMA_VERSION,
        "target_year": args.target_year,
        "fail_on_mismatch": bool(args.fail_on_mismatch),
        "guard_passed": guard_passed,
        "mismatches": len(deduped_mismatches),
        "mismatch_fields": deduped_mismatches,
        "input_paths": {
            "run_summary_path": str(summary_path),
            "visited_pages_path": str(visited_path) if visited_path else None,
            "failed_fetches_path": str(failed_path) if failed_path else None,
            "manifest_path": str(manifest_path) if manifest_path else None,
            "output_files": {fair_slug: str(path) for fair_slug, path in sorted(output_file_paths.items())},
        },
        "check_results": check_results,
    }
    write_json(output_path, summary_payload)

    print(
        "[DONE] Phase1 guard compare complete. "
        f"guard_passed={guard_passed} mismatches={len(deduped_mismatches)}"
    )
    if deduped_mismatches:
        print(f"[DONE] mismatch_fields={deduped_mismatches}")
    print(f"[DONE] summary={output_path}")

    if args.fail_on_mismatch and not guard_passed:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
