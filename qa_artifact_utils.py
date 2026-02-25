#!/usr/bin/env python3
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ARTIFACT_REGISTRY: dict[str, dict[str, Any]] = {
    "retry_run_summary_from_rollup": {
        "artifact_kind": "retry_run_summary_from_rollup",
        "schema_name": "artists_answer_qa_daily_recovery_retry_run_from_rollup_summary",
        "schema_version": "v1",
        "glob_pattern": "artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*.json",
        "required_prefix": "artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_",
        "required_suffix": ".json",
        "exclude_substrings": ["_report.json", "_failed_run_"],
    },
    "retry_run_summary_from_rollup_report": {
        "artifact_kind": "retry_run_summary_from_rollup_report",
        "schema_name": "artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_report",
        "schema_version": "v1",
        "glob_pattern": "artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_*_report.json",
        "required_prefix": "artists_answer_qa_daily_recovery_retry_run_from_rollup_summary_",
        "required_suffix": "_report.json",
        "exclude_substrings": ["_failed_run_", "_report_rollup_"],
    },
    "retry_run_report_rollup": {
        "artifact_kind": "retry_run_report_rollup",
        "schema_name": "artists_answer_qa_daily_recovery_retry_run_report_rollup",
        "schema_version": "v1",
        "glob_pattern": "artists_answer_qa_daily_recovery_retry_run_report_rollup_*.json",
        "required_prefix": "artists_answer_qa_daily_recovery_retry_run_report_rollup_",
        "required_suffix": ".json",
        "exclude_substrings": ["_retry_manifest.json"],
    },
    "retry_run_report_rollup_retry_manifest": {
        "artifact_kind": "retry_run_report_rollup_retry_manifest",
        "schema_name": "artists_answer_qa_daily_recovery_retry_run_report_rollup_retry_manifest",
        "schema_version": "v1",
        "glob_pattern": "artists_answer_qa_daily_recovery_retry_run_report_rollup_*_retry_manifest.json",
        "required_prefix": "artists_answer_qa_daily_recovery_retry_run_report_rollup_",
        "required_suffix": "_retry_manifest.json",
        "exclude_substrings": [],
    },
    "retry_run_daily_chain_summary": {
        "artifact_kind": "retry_run_daily_chain_summary",
        "schema_name": "artists_answer_qa_retry_run_daily_chain_summary",
        "schema_version": "v1",
        "glob_pattern": "artists_answer_qa_retry_run_daily_chain_summary_*.json",
        "required_prefix": "artists_answer_qa_retry_run_daily_chain_summary_",
        "required_suffix": ".json",
        "exclude_substrings": ["_report.json"],
    },
    "retry_run_daily_chain_report": {
        "artifact_kind": "retry_run_daily_chain_report",
        "schema_name": "artists_answer_qa_retry_run_daily_chain_report",
        "schema_version": "v1",
        "glob_pattern": "artists_answer_qa_retry_run_daily_chain_summary_*_report.json",
        "required_prefix": "artists_answer_qa_retry_run_daily_chain_summary_",
        "required_suffix": "_report.json",
        "exclude_substrings": [],
    },
    "retry_run_daily_chain_report_rollup": {
        "artifact_kind": "retry_run_daily_chain_report_rollup",
        "schema_name": "artists_answer_qa_retry_run_daily_chain_report_rollup",
        "schema_version": "v1",
        "glob_pattern": "artists_answer_qa_retry_run_daily_chain_report_rollup_*.json",
        "required_prefix": "artists_answer_qa_retry_run_daily_chain_report_rollup_",
        "required_suffix": ".json",
        "exclude_substrings": ["_retry_manifest.json"],
    },
    "retry_run_daily_chain_report_rollup_retry_manifest": {
        "artifact_kind": "retry_run_daily_chain_report_rollup_retry_manifest",
        "schema_name": "artists_answer_qa_retry_run_daily_chain_report_rollup_retry_manifest",
        "schema_version": "v1",
        "glob_pattern": "artists_answer_qa_retry_run_daily_chain_report_rollup_*_retry_manifest.json",
        "required_prefix": "artists_answer_qa_retry_run_daily_chain_report_rollup_",
        "required_suffix": "_retry_manifest.json",
        "exclude_substrings": [],
    },
    "retry_run_daily_chain_recovery_chain_summary": {
        "artifact_kind": "retry_run_daily_chain_recovery_chain_summary",
        "schema_name": "artists_answer_qa_retry_run_daily_chain_recovery_chain_summary",
        "schema_version": "v1",
        "glob_pattern": "artists_answer_qa_retry_run_daily_chain_recovery_chain_summary_*.json",
        "required_prefix": "artists_answer_qa_retry_run_daily_chain_recovery_chain_summary_",
        "required_suffix": ".json",
        "exclude_substrings": ["_report.json"],
    },
    "retry_run_daily_chain_recovery_chain_report": {
        "artifact_kind": "retry_run_daily_chain_recovery_chain_report",
        "schema_name": "artists_answer_qa_retry_run_daily_chain_recovery_chain_report",
        "schema_version": "v1",
        "glob_pattern": "artists_answer_qa_retry_run_daily_chain_recovery_chain_summary_*_report.json",
        "required_prefix": "artists_answer_qa_retry_run_daily_chain_recovery_chain_summary_",
        "required_suffix": "_report.json",
        "exclude_substrings": [],
    },
    "retry_run_daily_chain_recovery_chain_report_rollup": {
        "artifact_kind": "retry_run_daily_chain_recovery_chain_report_rollup",
        "schema_name": "artists_answer_qa_retry_run_daily_chain_recovery_chain_report_rollup",
        "schema_version": "v1",
        "glob_pattern": "artists_answer_qa_retry_run_daily_chain_recovery_chain_report_rollup_*.json",
        "required_prefix": "artists_answer_qa_retry_run_daily_chain_recovery_chain_report_rollup_",
        "required_suffix": ".json",
        "exclude_substrings": [],
    },
}

_TIMESTAMP_RE = re.compile(r"(20\d{6}T\d{6}Z)")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def utc_timestamp_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def get_artifact_spec(artifact_kind: str) -> dict[str, Any]:
    if artifact_kind not in ARTIFACT_REGISTRY:
        raise KeyError(f"unknown_artifact_kind:{artifact_kind}")
    return ARTIFACT_REGISTRY[artifact_kind]


def build_artifact_header(artifact_kind: str, generated_by: str) -> dict[str, Any]:
    spec = get_artifact_spec(artifact_kind)
    return {
        "artifact_kind": spec.get("artifact_kind", artifact_kind),
        "schema_name": spec.get("schema_name", artifact_kind),
        "schema_version": spec.get("schema_version", "v1"),
        "generated_at": utc_now_iso(),
        "generated_by": generated_by,
    }


def _extract_filename_timestamp(path: Path) -> float:
    matches = _TIMESTAMP_RE.findall(path.name)
    if not matches:
        return 0.0
    last = matches[-1]
    try:
        return datetime.strptime(last, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        return 0.0


def is_artifact_candidate(path: Path, artifact_kind: str) -> bool:
    spec = get_artifact_spec(artifact_kind)
    name = path.name

    required_prefix = str(spec.get("required_prefix") or "")
    required_suffix = str(spec.get("required_suffix") or "")

    if required_prefix and not name.startswith(required_prefix):
        return False
    if required_suffix and not name.endswith(required_suffix):
        return False

    exclude_substrings = spec.get("exclude_substrings") or []
    for token in exclude_substrings:
        if token and token in name:
            return False

    return True


def list_candidate_artifacts(
    search_dir: Path,
    artifact_kind: str,
    *,
    glob_pattern: str | None = None,
    latest_n: int | None = None,
) -> list[Path]:
    spec = get_artifact_spec(artifact_kind)
    pattern = glob_pattern or str(spec.get("glob_pattern") or "*")

    candidates: list[Path] = []
    for path in search_dir.glob(pattern):
        if not path.is_file():
            continue
        if not is_artifact_candidate(path, artifact_kind):
            continue
        candidates.append(path.resolve())

    candidates = sorted(
        candidates,
        key=lambda p: (_extract_filename_timestamp(p), p.stat().st_mtime, p.name),
        reverse=True,
    )
    if latest_n is not None and latest_n > 0:
        return candidates[:latest_n]
    return candidates


def resolve_latest_artifact(
    search_dir: Path,
    artifact_kind: str,
    *,
    glob_pattern: str | None = None,
) -> tuple[Path | None, str | None]:
    spec = get_artifact_spec(artifact_kind)
    pattern = glob_pattern or str(spec.get("glob_pattern") or "*")
    candidates = list_candidate_artifacts(search_dir, artifact_kind, glob_pattern=pattern, latest_n=1)
    if not candidates:
        return None, f"latest_artifact_not_found:{artifact_kind}:{search_dir}/{pattern}"
    return candidates[0], None
