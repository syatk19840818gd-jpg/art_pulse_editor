#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from qa_artifact_utils import build_artifact_header, resolve_latest_artifact

DEFAULT_SEARCH_DIR = Path("data/phase1_seed10/logs")
SOURCE_CLI = "run_phase1_seed10_artist_image_collect_retry_manifest.py"
INPUT_ARTIFACT_KIND = "phase1_seed10_artist_image_collect_report_rollup"
OUTPUT_ARTIFACT_KIND = "phase1_seed10_artist_image_collect_retry_manifest"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"json_not_object:{path}")
    return obj


def _as_string(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if text:
            try:
                return int(text)
            except ValueError:
                return None
    return None


def normalize_reason(raw_reason: str) -> str:
    text = _as_string(raw_reason)
    if not text:
        return "unknown"
    if ":" in text:
        head = text.split(":", 1)[0].strip()
        return head or "unknown"
    return text


def normalize_domain(url: str) -> str:
    host = (urlparse(_as_string(url)).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host or "unknown"


def parse_csv_list(raw: str) -> list[str]:
    values: list[str] = []
    for chunk in _as_string(raw).split(","):
        text = chunk.strip()
        if text:
            values.append(text)
    return values


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build retry manifest from artist image collect report rollup. "
            "Select retry cases by reason/domain filters with bounded case count."
        )
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--rollup-json", default="", help="path to rollup JSON")
    group.add_argument("--latest", action="store_true", help="resolve latest rollup JSON")

    parser.add_argument(
        "--search-dir",
        default=str(DEFAULT_SEARCH_DIR),
        help=f"search directory for --latest (default: {DEFAULT_SEARCH_DIR})",
    )
    parser.add_argument("--glob", default="", help="optional glob override for --latest")
    parser.add_argument("--output-manifest", default="", help="optional output manifest path")
    parser.add_argument(
        "--max-cases",
        type=int,
        default=50,
        help="max selected retry cases (default: 50)",
    )
    parser.add_argument(
        "--min-failed-count",
        type=int,
        default=1,
        help="minimum count threshold when auto-building filters (default: 1)",
    )
    parser.add_argument(
        "--failed-reasons",
        default="",
        help="optional comma-separated normalized reasons to include",
    )
    parser.add_argument(
        "--failed-domains",
        default="",
        help="optional comma-separated domains to include",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    requested_rollup_path = _as_string(args.rollup_json)
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
        rollup_path = latest_path
        latest_resolved = True

    if not rollup_path.exists():
        print(f"[ERROR] artist_image_collect_report_rollup_not_found:{rollup_path}")
        return 1

    try:
        rollup_obj = load_json(rollup_path)
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] artist_image_collect_report_rollup_load_failed:{rollup_path}:{exc}")
        return 1

    max_cases = max(0, int(args.max_cases))
    min_failed_count = max(1, int(args.min_failed_count))

    notes: list[str] = []
    warnings: list[str] = []

    summary_paths: list[str] = []
    seen_summary_paths: set[str] = set()
    raw_trend = rollup_obj.get("success_rate_trend")
    if isinstance(raw_trend, list):
        for item in raw_trend:
            if not isinstance(item, dict):
                continue
            summary_path = _as_string(item.get("summary_path"))
            if summary_path and summary_path not in seen_summary_paths:
                seen_summary_paths.add(summary_path)
                summary_paths.append(summary_path)

    if not summary_paths:
        raw_source_paths = rollup_obj.get("source_report_paths")
        if isinstance(raw_source_paths, list):
            for report_path_raw in raw_source_paths:
                report_path = Path(_as_string(report_path_raw)).resolve()
                if not report_path.exists() or not report_path.is_file():
                    warnings.append(f"source_report_not_found:{report_path}")
                    continue
                try:
                    report_obj = load_json(report_path)
                except Exception as exc:  # noqa: BLE001
                    warnings.append(f"source_report_load_failed:{report_path}:{exc}")
                    continue
                summary_path = _as_string(report_obj.get("summary_path"))
                if summary_path and summary_path not in seen_summary_paths:
                    seen_summary_paths.add(summary_path)
                    summary_paths.append(summary_path)

    if not summary_paths:
        notes.append("no_summary_paths_in_rollup")

    failed_candidates: list[dict[str, Any]] = []
    reason_counter: Counter[str] = Counter()
    domain_counter: Counter[str] = Counter()

    for summary_path_raw in reversed(summary_paths):
        summary_path = Path(summary_path_raw).resolve()
        if not summary_path.exists():
            warnings.append(f"source_summary_not_found:{summary_path}")
            continue

        try:
            summary_obj = load_json(summary_path)
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"source_summary_load_failed:{summary_path}:{exc}")
            continue

        raw_failed_cases = summary_obj.get("failed_cases")
        if not isinstance(raw_failed_cases, list):
            warnings.append(f"source_summary_failed_cases_missing_or_invalid:{summary_path}")
            continue

        for failed_case in raw_failed_cases:
            if not isinstance(failed_case, dict):
                continue

            artist_id = _as_string(failed_case.get("artist_id"))
            source_url = _as_string(failed_case.get("source_url"))
            reason_raw = _as_string(failed_case.get("reason"))
            reason = normalize_reason(reason_raw)
            domain = normalize_domain(source_url)
            saved_images = _as_int(failed_case.get("saved_images"))
            target_images = _as_int(failed_case.get("target_images"))

            reason_counter[reason] += 1
            domain_counter[domain] += 1

            failed_candidates.append(
                {
                    "artist_id": artist_id,
                    "source_url": source_url,
                    "reason": reason,
                    "reason_raw": reason_raw,
                    "domain": domain,
                    "saved_images": saved_images,
                    "target_images": target_images,
                    "source_summary_path": str(summary_path),
                }
            )

    requested_reason_filters = parse_csv_list(args.failed_reasons)
    requested_domain_filters = parse_csv_list(args.failed_domains)

    if requested_reason_filters:
        effective_reason_filters = requested_reason_filters
    else:
        effective_reason_filters = [
            reason
            for reason, count in reason_counter.most_common()
            if count >= min_failed_count
        ]

    if requested_domain_filters:
        effective_domain_filters = requested_domain_filters
    else:
        effective_domain_filters = [
            domain
            for domain, count in domain_counter.most_common()
            if count >= min_failed_count
        ]

    if not effective_reason_filters and reason_counter:
        effective_reason_filters = [reason for reason, _ in reason_counter.most_common()]
    if not effective_domain_filters and domain_counter:
        effective_domain_filters = [domain for domain, _ in domain_counter.most_common()]

    reason_filter_set = set(effective_reason_filters)
    domain_filter_set = set(effective_domain_filters)

    selected_candidates: list[dict[str, Any]] = []
    seen_case_keys: set[str] = set()

    for candidate in failed_candidates:
        reason = _as_string(candidate.get("reason"))
        domain = _as_string(candidate.get("domain"))

        if reason_filter_set and reason not in reason_filter_set:
            continue
        if domain_filter_set and domain not in domain_filter_set:
            continue

        artist_id = _as_string(candidate.get("artist_id"))
        source_url = _as_string(candidate.get("source_url"))
        case_key = artist_id or source_url
        if not case_key:
            case_key = json.dumps(candidate, ensure_ascii=False)
        if case_key in seen_case_keys:
            continue
        seen_case_keys.add(case_key)
        selected_candidates.append(candidate)

    selected_candidates.sort(
        key=lambda c: (
            reason_counter[_as_string(c.get("reason"))],
            domain_counter[_as_string(c.get("domain"))],
            _as_string(c.get("artist_id")),
            _as_string(c.get("source_url")),
        ),
        reverse=True,
    )

    if max_cases > 0:
        selected_candidates = selected_candidates[:max_cases]

    cases: list[dict[str, Any]] = []
    for idx, candidate in enumerate(selected_candidates, start=1):
        cases.append(
            {
                "case_id": f"retry_case_{idx:03d}",
                "artist_id": candidate.get("artist_id"),
                "source_url": candidate.get("source_url"),
                "reason": candidate.get("reason"),
                "domain": candidate.get("domain"),
                "saved_images": candidate.get("saved_images"),
                "target_images": candidate.get("target_images"),
                "source_summary_path": candidate.get("source_summary_path"),
            }
        )

    if not cases:
        notes.append("no_retry_cases_selected")

    output_manifest_path = (
        Path(args.output_manifest).resolve()
        if args.output_manifest
        else rollup_path.with_name(f"{rollup_path.stem}_retry_manifest.json")
    )

    manifest: dict[str, Any] = {
        **build_artifact_header(OUTPUT_ARTIFACT_KIND, generated_by=SOURCE_CLI),
        "source_cli": SOURCE_CLI,
        "source_rollup_path_requested": requested_rollup_path or None,
        "source_rollup_path": str(rollup_path),
        "source_rollup_latest_resolved": latest_resolved,
        "retry_manifest_path": str(output_manifest_path),
        "max_cases": max_cases,
        "min_failed_count": min_failed_count,
        "failed_reason_filter_requested": requested_reason_filters,
        "failed_domain_filter_requested": requested_domain_filters,
        "failed_reason_filter": effective_reason_filters,
        "failed_domain_filter": effective_domain_filters,
        "source_summary_paths": summary_paths,
        "candidate_failed_case_count": len(failed_candidates),
        "selected_case_count": len(cases),
        "reason_counts": [
            {"reason": reason, "count": count}
            for reason, count in reason_counter.most_common(50)
        ],
        "domain_counts": [
            {"domain": domain, "count": count}
            for domain, count in domain_counter.most_common(50)
        ],
        "cases": cases,
        "notes": notes,
        "warnings": warnings,
    }
    write_json(output_manifest_path, manifest)

    print(
        "[DONE] artist_image_collect_retry_manifest_generated "
        f"candidates={manifest['candidate_failed_case_count']} "
        f"selected={manifest['selected_case_count']}"
    )
    print(
        "[DONE] "
        f"failed_reason_filter={manifest['failed_reason_filter']} "
        f"failed_domain_filter={manifest['failed_domain_filter']}"
    )
    print(f"[DONE] retry_manifest={output_manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
