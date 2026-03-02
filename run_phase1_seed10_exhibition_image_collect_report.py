from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase1 seed10 exhibitions image collect report")
    parser.add_argument("--summary-path", required=True)
    parser.add_argument("--output-json", required=True)
    return parser.parse_args()


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    args = parse_args()
    summary_path = Path(args.summary_path)
    summary = read_json(summary_path)
    failed_cases = list(summary.get("failed_cases") or [])
    reason_counter: Counter[str] = Counter()
    for row in failed_cases:
        reason = str(row.get("reason") or "unknown")
        reason_counter[reason] += 1
    cases = list(summary.get("cases") or [])
    seed_url_type_counter: Counter[str] = Counter()
    listing_resolved_to_detail_count = 0
    gallery_stats: dict[tuple[str, str], dict[str, Any]] = {}
    for row in cases:
        fair_slug = str(row.get("fair_slug") or "")
        gallery_name = str(row.get("gallery_name_en") or "")
        key = (fair_slug, gallery_name)
        bucket = gallery_stats.setdefault(
            key,
            {
                "fair_slug": fair_slug,
                "gallery_name_en": gallery_name,
                "seed_exhibitions": 0,
                "ge_1_exhibitions": 0,
                "ge_target_exhibitions": 0,
                "ge_1_new_exhibitions": 0,
                "ge_target_new_exhibitions": 0,
                "new_saved_images_total": 0,
                "existing_hit_only_cases": 0,
                "seed_url_type_breakdown": Counter(),
                "failed_reason_counts": Counter(),
            },
        )
        bucket["seed_exhibitions"] += 1
        if int(row.get("saved_images") or 0) >= 1:
            bucket["ge_1_exhibitions"] += 1
        if bool(row.get("target_met")):
            bucket["ge_target_exhibitions"] += 1
        if int(row.get("new_saved_images") or 0) >= 1:
            bucket["ge_1_new_exhibitions"] += 1
        if bool(row.get("target_met_new")):
            bucket["ge_target_new_exhibitions"] += 1
        bucket["new_saved_images_total"] += int(row.get("new_saved_images") or 0)
        if bool(row.get("existing_hit_only")):
            bucket["existing_hit_only_cases"] += 1
        seed_type = str(row.get("seed_url_type") or "unknown")
        seed_url_type_counter[seed_type] += 1
        bucket["seed_url_type_breakdown"][seed_type] += 1
        if seed_type == "listing" and int(row.get("listing_resolved_to_detail_count") or 0) > 0:
            listing_resolved_to_detail_count += 1
    for row in failed_cases:
        fair_slug = str(row.get("fair_slug") or "")
        gallery_name = str(row.get("gallery_name_en") or "")
        key = (fair_slug, gallery_name)
        bucket = gallery_stats.setdefault(
            key,
            {
                "fair_slug": fair_slug,
                "gallery_name_en": gallery_name,
                "seed_exhibitions": 0,
                "ge_1_exhibitions": 0,
                "ge_target_exhibitions": 0,
                "ge_1_new_exhibitions": 0,
                "ge_target_new_exhibitions": 0,
                "new_saved_images_total": 0,
                "existing_hit_only_cases": 0,
                "seed_url_type_breakdown": Counter(),
                "failed_reason_counts": Counter(),
            },
        )
        reason = str(row.get("reason") or "unknown")
        bucket["failed_reason_counts"][reason] += 1
    top_saved = sorted(cases, key=lambda row: int(row.get("saved_images") or 0), reverse=True)[:10]
    gallery_breakdown = []
    for _, bucket in sorted(gallery_stats.items(), key=lambda item: (item[0][0], item[0][1])):
        seed_exhibitions = int(bucket["seed_exhibitions"])
        ge_1 = int(bucket["ge_1_exhibitions"])
        ge_target = int(bucket["ge_target_exhibitions"])
        ge_1_new = int(bucket["ge_1_new_exhibitions"])
        ge_target_new = int(bucket["ge_target_new_exhibitions"])
        gallery_breakdown.append(
            {
                "fair_slug": bucket["fair_slug"],
                "gallery_name_en": bucket["gallery_name_en"],
                "seed_exhibitions": seed_exhibitions,
                "ge_1_exhibitions": ge_1,
                "ge_target_exhibitions": ge_target,
                "ge_1_new_exhibitions": ge_1_new,
                "ge_target_new_exhibitions": ge_target_new,
                "success_rate_ge_1": round((ge_1 / seed_exhibitions) if seed_exhibitions else 0.0, 6),
                "success_rate_ge_target": round((ge_target / seed_exhibitions) if seed_exhibitions else 0.0, 6),
                "success_rate_ge_1_new": round((ge_1_new / seed_exhibitions) if seed_exhibitions else 0.0, 6),
                "success_rate_ge_target_new": round((ge_target_new / seed_exhibitions) if seed_exhibitions else 0.0, 6),
                "new_saved_images_total": int(bucket["new_saved_images_total"]),
                "existing_hit_only_cases": int(bucket["existing_hit_only_cases"]),
                "seed_url_type_breakdown": dict(bucket["seed_url_type_breakdown"]),
                "failed_reason_counts": dict(bucket["failed_reason_counts"]),
            }
        )
    report = {
        "artifact": "phase1_seed10_exhibition_image_collect_report",
        "source_summary_path": str(summary_path),
        "target_year": int(summary.get("target_year") or 0),
        "target_images_per_exhibition": int(summary.get("target_images_per_exhibition") or 0),
        "seed_exhibition_count": int(summary.get("seed_exhibition_count") or 0),
        "seed_url_type_breakdown": dict(summary.get("seed_url_type_breakdown") or seed_url_type_counter),
        "listing_resolved_to_detail_count": int(
            summary.get("listing_resolved_to_detail_count") or listing_resolved_to_detail_count
        ),
        "listing_resolved_detail_urls_total": int(summary.get("listing_resolved_detail_urls_total") or 0),
        "exhibitions_with_ge_1_image": int(summary.get("exhibitions_with_ge_1_image") or 0),
        "success_rate_ge_1_image": float(summary.get("success_rate_ge_1_image") or 0.0),
        "exhibitions_with_ge_target_images": int(summary.get("exhibitions_with_ge_target_images") or 0),
        "success_rate_ge_target_images": float(summary.get("success_rate_ge_target_images") or 0.0),
        "exhibitions_with_ge_1_new_image": int(summary.get("exhibitions_with_ge_1_new_image") or 0),
        "success_rate_ge_1_new_image": float(summary.get("success_rate_ge_1_new_image") or 0.0),
        "exhibitions_with_ge_target_new_images": int(summary.get("exhibitions_with_ge_target_new_images") or 0),
        "success_rate_ge_target_new_images": float(summary.get("success_rate_ge_target_new_images") or 0.0),
        "saved_images_total": int(summary.get("saved_images_total") or 0),
        "new_saved_images_total": int(summary.get("new_saved_images_total") or 0),
        "existing_hit_only_case_count": int(summary.get("existing_hit_only_case_count") or 0),
        "failed_case_count": len(failed_cases),
        "top_failed_reasons": [{"reason": key, "count": value} for key, value in reason_counter.most_common(10)],
        "gallery_breakdown": gallery_breakdown,
        "top_saved_cases": [
            {
                "fair_slug": row.get("fair_slug"),
                "gallery_name_en": row.get("gallery_name_en"),
                "source_url": row.get("source_url"),
                "saved_images": int(row.get("saved_images") or 0),
                "target_images": int(row.get("target_images") or 0),
                "target_met": bool(row.get("target_met")),
            }
            for row in top_saved
        ],
        "generated_at": utc_now_iso(),
    }
    write_json(Path(args.output_json), report)
    print(f"[exhibitions-image-report] output={args.output_json}")
    print(
        "[exhibitions-image-report] "
        f"seed={report['seed_exhibition_count']} "
        f"ge1={report['exhibitions_with_ge_1_image']} "
        f"ge_target={report['exhibitions_with_ge_target_images']} "
        f"failed={report['failed_case_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
