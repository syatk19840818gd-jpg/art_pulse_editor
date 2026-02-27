#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from qa_artifact_utils import build_artifact_header, resolve_latest_artifact

DEFAULT_SEARCH_DIR = Path("data/phase1_seed10/logs")
BREAKDOWN_DOC_PATH = Path("docs/RAG_EXTRACTION_BREAKDOWN_JA.md")
SOURCE_CLI = "run_phase1_seed10_artist_image_collect_report.py"
INPUT_ARTIFACT_KIND = "phase1_seed10_artist_image_collect_summary"
OUTPUT_ARTIFACT_KIND = "phase1_seed10_artist_image_collect_report"
SEED_PER_FAIR = 5
CSV_PATHS = {
    "frieze_london": Path("data/gallery_lists/gallery_list_frieze_london.csv"),
    "liste": Path("data/gallery_lists/gallery_list_liste.csv"),
}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"json_not_object:{path}")
    return obj


def normalize_domain(url: str) -> str:
    host = (urlparse(url).hostname or "").strip().lower()
    if host.startswith("www."):
        host = host[4:]
    return host or "unknown"


def normalize_reason(reason: str) -> str:
    text = (reason or "").strip()
    if not text:
        return "unknown"
    if ":" in text:
        return text.split(":", 1)[0].strip() or "unknown"
    return text


def parse_gallery_name(raw_name: str) -> str:
    text = (raw_name or "").strip()
    match = re.match(r"^(.*?)（(.*?)）$", text)
    if match:
        return match.group(1).strip()
    return text


def load_seed_gallery_pairs(limit_per_fair: int = SEED_PER_FAIR) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for fair_slug, csv_path in CSV_PATHS.items():
        if not csv_path.exists():
            continue
        count = 0
        with csv_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            for row in reader:
                if len(row) < 2:
                    continue
                gallery_raw = (row[0] or "").strip()
                list_url = (row[1] or "").strip()
                if not gallery_raw or not list_url:
                    continue
                pairs.append((fair_slug, parse_gallery_name(gallery_raw)))
                count += 1
                if count >= limit_per_fair:
                    break
    return pairs


def merge_gallery_breakdown_with_seed_targets(report: dict[str, Any]) -> list[dict[str, Any]]:
    existing_rows = report.get("gallery_breakdown")
    row_map: dict[tuple[str, str], dict[str, Any]] = {}
    if isinstance(existing_rows, list):
        for row in existing_rows:
            if not isinstance(row, dict):
                continue
            fair_slug = str(row.get("fair_slug") or "").strip()
            gallery_name_en = str(row.get("gallery_name_en") or "").strip()
            if not fair_slug or not gallery_name_en:
                continue
            row_map[(fair_slug, gallery_name_en)] = dict(row)

    seed_pairs = load_seed_gallery_pairs()
    merged_rows: list[dict[str, Any]] = []
    for fair_slug, gallery_name_en in seed_pairs:
        row = row_map.get((fair_slug, gallery_name_en))
        if row is None:
            row = {
                "fair_slug": fair_slug,
                "gallery_name_en": gallery_name_en,
                "artist_count": 0,
                "artists_with_ge_1_image": 0,
                "artists_with_ge_target_images": 0,
                "images_saved_total": 0,
                "success_rate_ge_target": 0.0,
                "success_rate_ge_target_pct": 0.0,
            }
        merged_rows.append(row)

    used_keys = set(seed_pairs)
    for key, row in row_map.items():
        if key in used_keys:
            continue
        merged_rows.append(row)
    return merged_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read seed10 artist image collect summary and write a lightweight report."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--summary-path", default="", help="summary path")
    group.add_argument("--latest", action="store_true", help="resolve latest summary")
    parser.add_argument(
        "--search-dir",
        default=str(DEFAULT_SEARCH_DIR),
        help=f"search directory for --latest (default: {DEFAULT_SEARCH_DIR})",
    )
    parser.add_argument("--glob", default="", help="optional glob override for --latest")
    parser.add_argument("--output-json", default="", help="optional output report path")
    parser.add_argument("--top-n", type=int, default=5, help="max items for top lists (default: 5)")
    parser.add_argument(
        "--skip-breakdown-doc",
        action="store_true",
        help="skip auto append to docs/RAG_EXTRACTION_BREAKDOWN_JA.md",
    )
    return parser.parse_args()


def append_breakdown_doc(report: dict[str, Any], report_path: Path) -> str:
    summary_path = str(report.get("summary_path") or "")
    if not summary_path:
        return "skipped:no_summary_path"

    marker = f"- `{summary_path}`"
    existing = BREAKDOWN_DOC_PATH.read_text(encoding="utf-8") if BREAKDOWN_DOC_PATH.exists() else ""
    if marker in existing:
        return "skipped:already_recorded"

    lines: list[str] = []
    lines.append("\n---")
    lines.append(f"## RUN {str(report.get('generated_at') or '')} artists画像収集")
    lines.append("")
    lines.append("参照元:")
    lines.append(f"- `{summary_path}`")
    lines.append(f"- `{report_path}`")
    lines.append("")
    lines.append("### サマリー")
    lines.append(f"- 対象人数: {report.get('seed_artist_count')}")
    lines.append(f"- 5枚達成人数: {report.get('artists_with_ge_target_images')}")
    lines.append(
        f"- 達成率(>= {report.get('target_images_per_artist')}枚): "
        f"{report.get('success_rate_ge_target_pct')}%"
    )
    lines.append(f"- 閾値通過(70%): {report.get('threshold_passed')}")
    lines.append("")
    lines.append("### fair/gallery内訳")
    lines.append("| fair | gallery | 対象人数 | 成功人数(>=1枚) | 取得件数(画像枚数) | 成功率(>=5枚) |")
    lines.append("|---|---|---:|---:|---:|---:|")
    gallery_rows = report.get("gallery_breakdown", [])
    if isinstance(gallery_rows, list) and gallery_rows:
        for row in gallery_rows:
            if not isinstance(row, dict):
                continue
            lines.append(
                f"| {row.get('fair_slug')} | {row.get('gallery_name_en')} | "
                f"{row.get('artist_count')} | {row.get('artists_with_ge_1_image')} | "
                f"{row.get('images_saved_total')} | {row.get('success_rate_ge_target_pct')}% |"
            )
    else:
        lines.append("| - | - | 0 | 0 | 0 | 0.0% |")

    top_reasons = report.get("top_failed_reasons", [])
    top_domains = report.get("top_failed_domains", [])
    lines.append("")
    lines.append("### 失敗理由上位")
    if isinstance(top_reasons, list) and top_reasons:
        for item in top_reasons:
            if isinstance(item, dict):
                lines.append(f"- {item.get('reason')}: {item.get('count')}件")
    else:
        lines.append("- なし")

    lines.append("")
    lines.append("### 失敗ドメイン上位")
    if isinstance(top_domains, list) and top_domains:
        for item in top_domains:
            if isinstance(item, dict):
                lines.append(f"- {item.get('domain')}: {item.get('count')}件")
    else:
        lines.append("- なし")

    BREAKDOWN_DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    with BREAKDOWN_DOC_PATH.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    return "appended"


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")

    args = parse_args()
    top_n = max(1, int(args.top_n))

    report: dict[str, Any] = {
        **build_artifact_header(OUTPUT_ARTIFACT_KIND, generated_by=SOURCE_CLI),
        "source_cli": SOURCE_CLI,
        "source_summary_path_requested": args.summary_path if args.summary_path else "--latest",
        "latest_resolved": bool(args.latest),
        "summary_path": None,
        "seed_artist_count": None,
        "artists_with_ge_target_images": None,
        "success_rate_ge_target": None,
        "success_rate_ge_target_pct": None,
        "threshold_passed": None,
        "target_images_per_artist": None,
        "success_threshold": None,
        "fair_breakdown": [],
        "gallery_breakdown": [],
        "top_failed_reasons": [],
        "top_failed_domains": [],
        "notes": [],
        "warnings": [],
        "report_exit_code": 1,
        "exit_reason": "summary_not_found_or_invalid",
    }

    if args.summary_path:
        summary_path = Path(args.summary_path).resolve()
    else:
        latest_path, latest_error = resolve_latest_artifact(
            Path(args.search_dir).resolve(),
            INPUT_ARTIFACT_KIND,
            glob_pattern=args.glob or None,
        )
        if latest_error:
            report["notes"].append(latest_error)
            print(f"[ERROR] {latest_error}")
            output_path = (
                Path(args.output_json).resolve()
                if args.output_json
                else (Path(args.search_dir).resolve() / "phase1_seed10_artist_image_collect_report_latest_error.json")
            )
            write_json(output_path, report)
            print(f"[DONE] report={output_path}")
            return 1
        assert latest_path is not None
        summary_path = latest_path

    report["summary_path"] = str(summary_path)
    output_path = (
        Path(args.output_json).resolve()
        if args.output_json
        else summary_path.with_name(f"{summary_path.stem}_report.json")
    )

    if not summary_path.exists():
        error = f"artist_image_collect_summary_not_found:{summary_path}"
        report["notes"].append(error)
        print(f"[ERROR] {error}")
        write_json(output_path, report)
        print(f"[DONE] report={output_path}")
        return 1

    try:
        summary = load_json(summary_path)
    except Exception as exc:  # noqa: BLE001
        error = f"artist_image_collect_summary_load_failed:{exc}"
        report["notes"].append(error)
        print(f"[ERROR] {error}")
        write_json(output_path, report)
        print(f"[DONE] report={output_path}")
        return 1

    for key in (
        "seed_artist_count",
        "artists_with_ge_target_images",
        "success_rate_ge_target",
        "success_rate_ge_target_pct",
        "threshold_passed",
        "target_images_per_artist",
        "success_threshold",
        "fair_breakdown",
        "gallery_breakdown",
    ):
        report[key] = summary.get(key)
    report["gallery_breakdown"] = merge_gallery_breakdown_with_seed_targets(report)

    notes = summary.get("notes", [])
    if isinstance(notes, list):
        report["notes"] = [str(note) for note in notes]
    elif notes is not None:
        report["notes"] = [str(notes)]

    failed_cases = summary.get("failed_cases")
    if not isinstance(failed_cases, list):
        report["warnings"].append("failed_cases_missing_or_invalid")
        failed_cases = []

    reason_counter: Counter[str] = Counter()
    domain_counter: Counter[str] = Counter()

    for raw_case in failed_cases:
        if not isinstance(raw_case, dict):
            continue
        reason = normalize_reason(str(raw_case.get("reason") or "unknown"))
        source_url = str(raw_case.get("source_url") or "")
        reason_counter[reason] += 1
        domain_counter[normalize_domain(source_url)] += 1

    report["top_failed_reasons"] = [
        {"reason": reason, "count": count}
        for reason, count in reason_counter.most_common(top_n)
    ]
    report["top_failed_domains"] = [
        {"domain": domain, "count": count}
        for domain, count in domain_counter.most_common(top_n)
    ]

    report["report_exit_code"] = 0
    report["exit_reason"] = "report_generated"
    write_json(output_path, report)
    if not args.skip_breakdown_doc:
        result = append_breakdown_doc(report, output_path)
        print(f"[REPORT] breakdown_doc={BREAKDOWN_DOC_PATH} status={result}")

    print(
        "[REPORT] "
        f"seed_artist_count={report.get('seed_artist_count')} "
        f"artists_with_ge_target_images={report.get('artists_with_ge_target_images')} "
        f"success_rate_ge_target={report.get('success_rate_ge_target')} "
        f"({report.get('success_rate_ge_target_pct')}%) "
        f"threshold_passed={report.get('threshold_passed')}"
    )
    if report["top_failed_reasons"]:
        print("[REPORT] top_failed_reasons:")
        for item in report["top_failed_reasons"]:
            print(f"  - {item.get('reason')} count={item.get('count')}")
    else:
        print("[REPORT] top_failed_reasons: none")

    if report["top_failed_domains"]:
        print("[REPORT] top_failed_domains:")
        for item in report["top_failed_domains"]:
            print(f"  - {item.get('domain')} count={item.get('count')}")
    else:
        print("[REPORT] top_failed_domains: none")

    gallery_breakdown = report.get("gallery_breakdown")
    if isinstance(gallery_breakdown, list) and gallery_breakdown:
        print("[REPORT] gallery_breakdown:")
        for row in gallery_breakdown:
            if not isinstance(row, dict):
                continue
            print(
                "  - "
                f"{row.get('fair_slug')}/{row.get('gallery_name_en')}: "
                f"artists={row.get('artist_count')} "
                f"ge1={row.get('artists_with_ge_1_image')} "
                f"ge_target={row.get('artists_with_ge_target_images')} "
                f"images={row.get('images_saved_total')} "
                f"rate={row.get('success_rate_ge_target')} "
                f"({row.get('success_rate_ge_target_pct')}%)"
            )
    else:
        print("[REPORT] gallery_breakdown: none")

    print(f"[DONE] report={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
