from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from phase2_art_pulse_config import DATA_ROOT, PHASE1_SEED10_ROOT

# Ledger lane policy (2026-03 closeout):
# - Retained lane (behavior-heavy): visited_pages*, failed_fetches*,
#   failed_fetches_artist_image_collect_{year}, artist_master_global.json
#   stay under data/phase1_seed10/logs via PHASE1_LEDGER_DIR.
# - Single moved exception: artist_works_images_known_unresolvable.json
#   lives under data/current/ledgers via CURRENT_LEDGER_DIR.
PHASE1_LEDGER_DIR = PHASE1_SEED10_ROOT / "logs"
CURRENT_LEDGER_DIR = DATA_ROOT / "current" / "ledgers"
RUN_SUMMARY_FILENAME_TEMPLATE = "run_summary_seed10_{target_year}.json"
VISITED_PAGES_FILENAME_TEMPLATES = {
    "exhibitions": "visited_pages_seed10_{target_year}.json",
    "artists": "visited_pages_artists_seed10_{target_year}.json",
}
FAILED_FETCHES_FILENAME_TEMPLATES = {
    "exhibitions": "failed_fetches_seed10_{target_year}.json",
    "artists": "failed_fetches_artists_seed10_{target_year}.json",
    "artist_image_collect": "failed_fetches_artist_image_collect_{target_year}.json",
}
ARTIST_MASTER_GLOBAL_FILENAME = "artist_master_global.json"
KNOWN_UNRESOLVABLE_ARTIST_IMAGES_FILENAME = "artist_works_images_known_unresolvable.json"

GUARD_REQUIRED_INPUT_FILES_EXHIBITIONS = (
    "run_summary_path",
    "visited_pages_path",
    "failed_fetches_path",
    "output_files",
)
GUARD_REQUIRED_INPUT_FILES_ARTISTS = (
    "run_summary_path",
    "visited_pages_path",
    "failed_fetches_path",
)
GUARD_BASE_REQUIRED_SUMMARY_KEYS = {
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
FAILED_FETCH_REQUIRED_FIELDS = {
    "raw_url",
    "reason_code",
    "attempt_count_or_retry_count",
    "last_attempt_at_or_last_failed_at",
}

HashFn = Callable[[str], str]
ReasonCodeFromStatusFn = Callable[[int], str]
ReasonCodeFromErrorFn = Callable[[str], str]
NormalizeUrlKeyFn = Callable[[str], str]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def get_phase1_logs_dir(root: Path | None = None) -> Path:
    # Retained-lane resolver used by behavior-heavy ledgers.
    if root is None:
        return PHASE1_LEDGER_DIR
    return Path(root) / "logs"


def _resolve_logs_dir(*, logs_dir: Path | None = None, root: Path | None = None) -> Path:
    if logs_dir is not None:
        return Path(logs_dir)
    return get_phase1_logs_dir(root)


def _get_template(mapping: dict[str, str], key: str, *, label: str) -> str:
    template = mapping.get(key)
    if template is None:
        supported = ", ".join(sorted(mapping))
        raise ValueError(f"unsupported_{label}:{key}; expected one of [{supported}]")
    return template


def get_phase1_run_summary_path(
    target_year: int,
    *,
    logs_dir: Path | None = None,
    root: Path | None = None,
) -> Path:
    base_dir = _resolve_logs_dir(logs_dir=logs_dir, root=root)
    return base_dir / RUN_SUMMARY_FILENAME_TEMPLATE.format(target_year=target_year)


def get_phase1_visited_pages_ledger_path(
    category: str,
    target_year: int,
    *,
    logs_dir: Path | None = None,
    root: Path | None = None,
) -> Path:
    base_dir = _resolve_logs_dir(logs_dir=logs_dir, root=root)
    template = _get_template(VISITED_PAGES_FILENAME_TEMPLATES, category, label="visited_category")
    return base_dir / template.format(target_year=target_year)


def get_phase1_failed_fetches_ledger_path(
    category: str,
    target_year: int,
    *,
    logs_dir: Path | None = None,
    root: Path | None = None,
) -> Path:
    base_dir = _resolve_logs_dir(logs_dir=logs_dir, root=root)
    template = _get_template(FAILED_FETCHES_FILENAME_TEMPLATES, category, label="failed_category")
    return base_dir / template.format(target_year=target_year)


def get_phase1_artist_master_global_path(
    *,
    logs_dir: Path | None = None,
    root: Path | None = None,
) -> Path:
    base_dir = _resolve_logs_dir(logs_dir=logs_dir, root=root)
    return base_dir / ARTIST_MASTER_GLOBAL_FILENAME


def get_current_ledgers_dir() -> Path:
    return CURRENT_LEDGER_DIR


def get_phase1_known_unresolvable_artist_images_path() -> Path:
    # Single-family exception that already moved to current ledgers.
    return get_current_ledgers_dir() / KNOWN_UNRESOLVABLE_ARTIST_IMAGES_FILENAME


def _read_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_visited_pages_ledger(path: Path, *, hash_fn: HashFn) -> dict[str, dict[str, Any]]:
    raw = _read_json(path)
    ledger: dict[str, dict[str, Any]] = {}
    entries: list[dict[str, Any]]
    if isinstance(raw, list):
        entries = [x for x in raw if isinstance(x, dict)]
    elif isinstance(raw, dict):
        entries = [x for x in raw.values() if isinstance(x, dict)]
    else:
        entries = []

    for entry in entries:
        url = entry.get("url") or entry.get("raw_url")
        page_url_hash = entry.get("page_url_hash")
        if not isinstance(page_url_hash, str) or not page_url_hash:
            if isinstance(url, str) and url:
                page_url_hash = hash_fn(url)
            else:
                continue
        normalized = dict(entry)
        normalized["page_url_hash"] = page_url_hash
        ledger[page_url_hash] = normalized
    return ledger


def save_visited_pages_ledger(path: Path, ledger: dict[str, dict[str, Any]]) -> None:
    payload = {page_url_hash: ledger[page_url_hash] for page_url_hash in sorted(ledger)}
    _write_json(path, payload)


def load_phase1_failed_fetches_ledger(
    path: Path,
    *,
    hash_fn: HashFn,
    reason_code_from_status: ReasonCodeFromStatusFn,
    reason_code_from_error_text: ReasonCodeFromErrorFn,
) -> dict[str, dict[str, Any]]:
    raw = _read_json(path)
    ledger: dict[str, dict[str, Any]] = {}
    entries: list[dict[str, Any]]
    if isinstance(raw, list):
        entries = [x for x in raw if isinstance(x, dict)]
    elif isinstance(raw, dict):
        entries = [x for x in raw.values() if isinstance(x, dict)]
    else:
        entries = []

    for entry in entries:
        raw_url = entry.get("raw_url")
        fail_hash = entry.get("fail_hash")
        if not isinstance(fail_hash, str) or not fail_hash:
            if isinstance(raw_url, str) and raw_url:
                fail_hash = hash_fn(raw_url)
            else:
                continue
        normalized = dict(entry)
        normalized["fail_hash"] = fail_hash
        if "attempt_count" not in normalized and "retry_count" in normalized:
            normalized["attempt_count"] = normalized.get("retry_count")
        if "last_attempt_at" not in normalized and "last_failed_at" in normalized:
            normalized["last_attempt_at"] = normalized.get("last_failed_at")
        reason_code = str(normalized.get("reason_code") or "")
        if reason_code in {"LIST_FETCH_FAILED", "PAGE_FETCH_FAILED", "REQUEST_ERROR"}:
            status_code = normalized.get("http_status")
            if isinstance(status_code, int):
                normalized["reason_code"] = reason_code_from_status(status_code)
            else:
                normalized["reason_code"] = reason_code_from_error_text(str(normalized.get("last_error") or ""))
        ledger[fail_hash] = normalized
    return ledger


def load_artist_image_failed_fetches_ledger(
    path: Path,
    *,
    hash_fn: HashFn,
    default_target_year: int,
) -> dict[str, dict[str, Any]]:
    payload = _read_json(path)
    if not isinstance(payload, dict):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for key, row in payload.items():
        if not isinstance(key, str) or not isinstance(row, dict):
            continue
        raw_url = str(row.get("raw_url") or "").strip()
        fail_hash = str(row.get("fail_hash") or key or "").strip()
        if not fail_hash:
            if not raw_url:
                continue
            fail_hash = hash_fn(raw_url)
        out[fail_hash] = {
            "fail_hash": fail_hash,
            "kind": str(row.get("kind") or "page"),
            "raw_url": raw_url,
            "parent_source_url": str(row.get("parent_source_url") or ""),
            "last_error": str(row.get("last_error") or ""),
            "http_status": row.get("http_status"),
            "retry_count": int(row.get("retry_count", 0)),
            "attempt_count": int(row.get("attempt_count", row.get("retry_count", 0))),
            "last_attempt_at": str(row.get("last_attempt_at") or row.get("last_failed_at") or ""),
            "first_failed_at": str(row.get("first_failed_at") or row.get("last_failed_at") or ""),
            "last_failed_at": str(row.get("last_failed_at") or ""),
            "reason_code": str(row.get("reason_code") or "REQUEST_ERROR"),
            "target_year": int(row.get("target_year", default_target_year)),
            "max_retries": int(row.get("max_retries", 0) or 0),
            "cooldown_seconds": int(row.get("cooldown_seconds", 0) or 0),
        }
    return out


def save_failed_fetches_ledger(path: Path, ledger: dict[str, dict[str, Any]]) -> None:
    payload = {fail_hash: ledger[fail_hash] for fail_hash in sorted(ledger)}
    _write_json(path, payload)


def clear_failed_fetch(ledger: dict[str, dict[str, Any]], raw_url: str, *, hash_fn: HashFn) -> None:
    ledger.pop(hash_fn(raw_url), None)


def build_failed_fetches_reason_counts(ledger: dict[str, dict[str, Any]]) -> dict[str, int]:
    return dict(Counter(str(item.get("reason_code") or "REQUEST_ERROR") for item in ledger.values()))


def update_failed_fetches_summary(
    summary: dict[str, Any],
    *,
    path: Path | None,
    ledger: dict[str, dict[str, Any]],
    new_in_run: int,
    prefix: str = "",
) -> None:
    summary[f"{prefix}failed_fetches_path"] = str(path) if path is not None else ""
    summary[f"{prefix}failed_fetches_new_in_run"] = int(new_in_run)
    summary[f"{prefix}failed_fetches_total_ledger"] = len(ledger)
    summary[f"{prefix}failed_fetches_reason_counts"] = build_failed_fetches_reason_counts(ledger)


def update_visited_pages_summary(
    summary: dict[str, Any],
    *,
    path: Path | None,
    ledger: dict[str, dict[str, Any]],
    prefix: str = "",
) -> None:
    summary[f"{prefix}visited_pages_path"] = str(path) if path is not None else ""
    summary[f"{prefix}visited_pages_total_ledger"] = len(ledger)


def build_artist_master_entry(
    *,
    identity_key: str,
    artist_name_key: str,
    artist_name_en: str,
    source_url: str,
    fair_slug: str,
    gallery_name_en: str,
    seen_at: str,
) -> dict[str, Any]:
    return {
        "artist_identity_key": identity_key,
        "artist_name_key": str(artist_name_key or "").strip(),
        "artist_name_en": str(artist_name_en or "").strip(),
        "first_source_url": str(source_url or "").strip(),
        "first_fair_slug": str(fair_slug or "").strip(),
        "first_gallery_name_en": str(gallery_name_en or "").strip(),
        "first_seen_at": str(seen_at or "").strip(),
        "updated_at": str(seen_at or "").strip(),
    }


def load_artist_master_global(path: Path) -> dict[str, dict[str, Any]]:
    payload = _read_json(path)
    if not isinstance(payload, dict):
        return {}
    records = payload.get("records")
    if not isinstance(records, list):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for item in records:
        if not isinstance(item, dict):
            continue
        key = str(item.get("artist_identity_key") or "").strip().lower()
        if not key:
            continue
        out[key] = item
    return out


def save_artist_master_global(path: Path, master: dict[str, dict[str, Any]]) -> None:
    payload = {
        "schema_name": "artist_master_global",
        "schema_version": "v1",
        "generated_at": utc_now_iso(),
        "records": sorted(master.values(), key=lambda x: str(x.get("artist_identity_key") or "")),
    }
    _write_json(path, payload)


def update_artist_master_summary(
    summary: dict[str, Any],
    *,
    path: Path | None,
    master: dict[str, dict[str, Any]],
    exists_at_start: bool | None = None,
) -> None:
    summary["artist_master_global_path"] = str(path) if path is not None else ""
    summary["artist_master_global_record_count"] = len(master)
    if exists_at_start is not None:
        summary["artist_master_global_exists_at_start"] = bool(exists_at_start)


def load_known_unresolvable_source_keys(
    path: Path,
    *,
    normalize_url_key: NormalizeUrlKeyFn,
) -> set[str]:
    payload = _read_json(path)
    if not isinstance(payload, dict):
        return set()
    items = payload.get("items")
    if not isinstance(items, list):
        return set()
    out: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        source_url = str(item.get("source_url") or "").strip()
        if not source_url:
            continue
        key = normalize_url_key(source_url)
        if key:
            out.add(key)
    return out


def update_known_unresolvable_summary(
    summary: dict[str, Any],
    *,
    path: Path | None,
    known_source_keys: set[str],
) -> None:
    summary["known_unresolvable_registry_path"] = str(path) if path is not None else ""
    summary["known_unresolvable_registry_count"] = len(known_source_keys)


@dataclass
class LedgerLoadResult:
    path: Path
    exists: bool
    format: str
    entries: dict[str, dict[str, Any]]
    load_error: str | None
    key_hash_mismatch_count: int
    missing_hash_field_count: int


def _normalize_guard_entry_key(entry: dict[str, Any], hash_field: str) -> str | None:
    value = entry.get(hash_field)
    return value if isinstance(value, str) and value else None


def load_guard_ledger(path: Path, *, hash_field: str) -> LedgerLoadResult:
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
            entry_hash = _normalize_guard_entry_key(value, hash_field)
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
            entry_hash = _normalize_guard_entry_key(value, hash_field)
            if not entry_hash:
                missing_hash_field_count += 1
                continue
            entries[f"{entry_hash}:{idx}"] = value
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
        attempt_valid = _safe_int(attempt_count)
        retry_valid = _safe_int(retry_count)
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


def pick_latest_by_mtime(paths: list[Path]) -> Path | None:
    if not paths:
        return None
    return max(paths, key=lambda p: p.stat().st_mtime if p.exists() else 0.0)


def resolve_guard_default_run_summary_path(logs_dir: Path, target_year: int) -> Path:
    primary = get_phase1_run_summary_path(target_year, logs_dir=logs_dir)
    if primary.exists():
        return primary
    candidates = sorted(logs_dir.glob(f"run_summary_*_{target_year}.json"))
    latest = pick_latest_by_mtime(candidates)
    return latest if latest is not None else primary


def resolve_guard_default_visited_pages_path(logs_dir: Path, target_year: int) -> Path:
    return _resolve_guard_default_ledger_path(
        primary=get_phase1_visited_pages_ledger_path("exhibitions", target_year, logs_dir=logs_dir),
        logs_dir=logs_dir,
        glob_pattern=f"visited_pages_*_{target_year}.json",
    )


def resolve_guard_default_failed_fetches_path(logs_dir: Path, target_year: int) -> Path:
    return _resolve_guard_default_ledger_path(
        primary=get_phase1_failed_fetches_ledger_path("exhibitions", target_year, logs_dir=logs_dir),
        logs_dir=logs_dir,
        glob_pattern=f"failed_fetches_*_{target_year}.json",
    )


def _resolve_guard_default_ledger_path(*, primary: Path, logs_dir: Path, glob_pattern: str) -> Path:
    if primary.exists():
        return primary
    candidates = sorted(logs_dir.glob(glob_pattern))
    latest = pick_latest_by_mtime(candidates)
    return latest if latest is not None else primary


def _safe_int(value: Any) -> int | None:
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
