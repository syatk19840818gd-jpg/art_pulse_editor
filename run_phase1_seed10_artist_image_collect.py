#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests

SOURCE_CLI = "run_phase1_seed10_artist_image_collect.py"
TARGET_YEAR_DEFAULT = 2025
TARGET_IMAGES_PER_ARTIST_DEFAULT = 5
SUCCESS_THRESHOLD_DEFAULT = 0.70
REQUEST_TIMEOUT_SECONDS = 15
USER_AGENT = "art-pulse-editor/phase1-seed10-artist-image-collect"

RAW_DIR = Path("data/phase1_seed10/raw")
LOG_DIR = Path("data/phase1_seed10/logs")
IMAGE_ROOT_DIR = Path("data/phase1_seed10/derived/images/artists_text")

SCHEMA_NAME = "phase1_seed10_artist_image_collect_summary"
SCHEMA_VERSION = "v1"
ARTIFACT_KIND = "phase1_seed10_artist_image_collect_summary"

REJECT_TOKENS = (
    "logo",
    "icon",
    "avatar",
    "portrait",
    "hero",
    "banner",
    "favicon",
    "sprite",
    "placeholder",
    "loading",
    "spacer",
    "profile",
)

POSITIVE_TOKENS = (
    "artwork",
    "artworks",
    "work",
    "works",
    "painting",
    "sculpture",
    "installation",
    "exhibition",
    "artist",
)

DISALLOWED_EXTENSIONS = {".svg", ".gif", ".ico"}
CONTENT_TYPE_TO_EXTENSION = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/avif": ".avif",
}

IMG_TAG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
ATTR_RE = re.compile(r"""([A-Za-z_:][-A-Za-z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+))""")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def utc_timestamp_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect artists images for Phase1 seed10 and summarize observed success rate.")
    parser.add_argument("--target-year", type=int, default=TARGET_YEAR_DEFAULT, help=f"default: {TARGET_YEAR_DEFAULT}")
    parser.add_argument(
        "--target-images-per-artist",
        type=int,
        default=TARGET_IMAGES_PER_ARTIST_DEFAULT,
        help=f"default: {TARGET_IMAGES_PER_ARTIST_DEFAULT}",
    )
    parser.add_argument("--output-json", default="", help="optional summary output path")
    return parser.parse_args()


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows


def build_artist_id(row: dict[str, Any]) -> str:
    text_hash = str(row.get("text_hash") or "").strip()
    if text_hash:
        return text_hash
    source_url = str(row.get("source_url") or "").strip()
    return hashlib.sha256(source_url.encode("utf-8")).hexdigest()


def load_artist_targets(target_year: int) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    for raw_path in sorted(RAW_DIR.glob(f"artists_*_{target_year}.jsonl")):
        rows = read_jsonl_rows(raw_path)
        fair_slug = str(raw_path.name.replace(f"artists_", "").replace(f"_{target_year}.jsonl", ""))
        for row in rows:
            source_url = str(row.get("source_url") or "").strip()
            if not source_url:
                continue
            artist_id = build_artist_id(row)
            targets.append(
                {
                    "artist_id": artist_id,
                    "fair_slug": str(row.get("fair_slug") or fair_slug),
                    "gallery_name_en": str(row.get("gallery_name_en") or ""),
                    "headline_ja": str(row.get("headline_ja") or ""),
                    "source_url": source_url,
                }
            )
    return targets


def normalize_domain(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host or "unknown"


def parse_srcset_best(srcset: str) -> str:
    best_url = ""
    best_width = -1
    for chunk in srcset.split(","):
        item = chunk.strip()
        if not item:
            continue
        parts = item.split()
        candidate = parts[0].strip()
        width = 0
        if len(parts) > 1 and parts[1].endswith("w"):
            try:
                width = int(parts[1][:-1])
            except ValueError:
                width = 0
        if width >= best_width:
            best_url = candidate
            best_width = width
    return best_url


def parse_img_attrs(tag_html: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for match in ATTR_RE.finditer(tag_html):
        key = (match.group(1) or "").strip().lower()
        value = match.group(2) or match.group(3) or match.group(4) or ""
        if key:
            attrs[key] = value.strip()
    return attrs


def should_reject_image_candidate(candidate_url: str, attrs: dict[str, str], parent_name: str) -> tuple[bool, int]:
    url_lower = candidate_url.lower()
    parsed = urlparse(candidate_url)
    ext = Path(parsed.path).suffix.lower()
    if ext in DISALLOWED_EXTENSIONS:
        return True, -10

    alt_text = str(attrs.get("alt") or "").lower()
    class_text = str(attrs.get("class") or "").lower()
    combined = f"{url_lower} {alt_text} {class_text} {parent_name}".strip()

    if any(token in combined for token in REJECT_TOKENS):
        return True, -10

    width_raw = str(attrs.get("width") or "").strip()
    height_raw = str(attrs.get("height") or "").strip()
    try:
        width = int(width_raw) if width_raw else 0
    except ValueError:
        width = 0
    try:
        height = int(height_raw) if height_raw else 0
    except ValueError:
        height = 0
    if width and height and width <= 240 and height <= 240:
        return True, -10

    score = 0
    if parent_name in {"figure", "picture"}:
        score += 1
    if any(token in combined for token in POSITIVE_TOKENS):
        score += 2
    if alt_text and len(alt_text) >= 12:
        score += 1
    return False, score


def extract_image_candidates(page_url: str, html: str) -> list[dict[str, Any]]:
    best_by_url: dict[str, dict[str, Any]] = {}

    for match in IMG_TAG_RE.finditer(html):
        tag_html = match.group(0)
        attrs = parse_img_attrs(tag_html)
        candidate_values: list[str] = []
        for attr_name in ("src", "data-src", "data-original", "data-lazy-src"):
            value = str(attrs.get(attr_name) or "").strip()
            if value:
                candidate_values.append(value)
        srcset = str(attrs.get("srcset") or "").strip()
        if srcset:
            best_srcset = parse_srcset_best(srcset)
            if best_srcset:
                candidate_values.append(best_srcset)

        parent_name = ""
        context_start = max(0, match.start() - 80)
        context = html[context_start : match.start()].lower()
        if "<figure" in context:
            parent_name = "figure"
        elif "<picture" in context:
            parent_name = "picture"
        for raw_value in candidate_values:
            absolute_url = urljoin(page_url, raw_value)
            parsed = urlparse(absolute_url)
            if parsed.scheme not in {"http", "https"}:
                continue
            reject, score = should_reject_image_candidate(absolute_url, attrs, parent_name)
            if reject:
                continue
            existing = best_by_url.get(absolute_url)
            if existing is None or score > int(existing.get("score", -999)):
                best_by_url[absolute_url] = {"url": absolute_url, "score": score}

    candidates = sorted(best_by_url.values(), key=lambda x: (int(x.get("score", 0)), str(x.get("url", ""))), reverse=True)
    return candidates


def detect_extension(image_url: str, content_type: str) -> str:
    parsed = urlparse(image_url)
    ext = Path(parsed.path).suffix.lower()
    if ext and ext not in DISALLOWED_EXTENSIONS and len(ext) <= 8:
        return ext
    normalized_type = content_type.split(";")[0].strip().lower()
    return CONTENT_TYPE_TO_EXTENSION.get(normalized_type, ".jpg")


def fetch_html(session: requests.Session, url: str) -> tuple[bool, str, str]:
    try:
        response = session.get(url, timeout=REQUEST_TIMEOUT_SECONDS, allow_redirects=True)
        response.raise_for_status()
    except requests.RequestException as exc:
        return False, "", f"html_fetch_failed:{exc}"
    content_type = str(response.headers.get("content-type") or "").lower()
    if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
        return False, "", f"html_content_type_unsupported:{content_type or 'unknown'}"
    response.encoding = response.encoding or "utf-8"
    return True, response.text, ""


def fetch_image(session: requests.Session, image_url: str) -> tuple[bool, bytes, str, str]:
    try:
        response = session.get(image_url, timeout=REQUEST_TIMEOUT_SECONDS, allow_redirects=True)
        response.raise_for_status()
    except requests.RequestException as exc:
        return False, b"", "", f"image_fetch_failed:{exc}"
    content_type = str(response.headers.get("content-type") or "").lower()
    if not content_type.startswith("image/"):
        return False, b"", "", f"image_content_type_unsupported:{content_type or 'unknown'}"
    payload = response.content
    if not payload:
        return False, b"", "", "image_empty_payload"
    return True, payload, detect_extension(image_url, content_type), ""


def main() -> int:
    args = parse_args()
    start_time = utc_now_iso()
    target_year = int(args.target_year)
    target_images_per_artist = max(1, int(args.target_images_per_artist))
    success_threshold = SUCCESS_THRESHOLD_DEFAULT
    run_ts = utc_timestamp_compact()

    summary_path = (
        Path(args.output_json).resolve()
        if args.output_json
        else (LOG_DIR / f"phase1_seed10_artist_image_collect_summary_{run_ts}.json").resolve()
    )

    summary: dict[str, Any] = {
        "artifact_kind": ARTIFACT_KIND,
        "schema_name": SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "generated_at": start_time,
        "generated_by": SOURCE_CLI,
        "source_cli": SOURCE_CLI,
        "target_year": target_year,
        "target_images_per_artist": target_images_per_artist,
        "success_threshold": success_threshold,
        "seed_artist_count": 0,
        "processed_artist_count": 0,
        "artists_with_ge_1_image": 0,
        "artists_with_ge_target_images": 0,
        "success_rate_ge_target": 0.0,
        "threshold_passed": False,
        "total_images_saved": 0,
        "per_artist_counts": [],
        "failed_cases": [],
        "domain_stats": {},
        "notes": [],
        "wrapper_exit_code": 0,
    }

    try:
        targets = load_artist_targets(target_year)
        summary["seed_artist_count"] = len(targets)
        if not targets:
            summary["notes"].append(f"no_artist_raw_records_found:artists_*_{target_year}.jsonl")
            write_json(summary_path, summary)
            print(f"[DONE] no targets. summary={summary_path}")
            return 0

        artists_image_root = (IMAGE_ROOT_DIR / str(target_year)).resolve()
        artists_image_root.mkdir(parents=True, exist_ok=True)

        domain_stats: dict[str, dict[str, int]] = defaultdict(
            lambda: {
                "target_artist_count": 0,
                "success_ge1_count": 0,
                "success_ge_target_count": 0,
                "images_saved_total": 0,
            }
        )

        session = requests.Session()
        session.headers.update({"User-Agent": USER_AGENT})

        for target in targets:
            artist_id = str(target["artist_id"])
            source_url = str(target["source_url"])
            fair_slug = str(target["fair_slug"])
            gallery_name_en = str(target["gallery_name_en"])
            domain = normalize_domain(source_url)
            domain_stats[domain]["target_artist_count"] += 1

            artist_dir = artists_image_root / artist_id
            artist_dir.mkdir(parents=True, exist_ok=True)
            existing_images = sorted(
                [
                    p
                    for p in artist_dir.glob("image_*")
                    if p.is_file() and p.suffix.lower() not in DISALLOWED_EXTENSIONS and p.stat().st_size > 0
                ]
            )
            saved_count = len(existing_images)
            case_notes: list[str] = []
            case_reason = ""

            if saved_count < target_images_per_artist:
                ok_html, html, html_error = fetch_html(session, source_url)
                if not ok_html:
                    case_reason = html_error
                else:
                    candidates = extract_image_candidates(source_url, html)
                    if not candidates:
                        case_reason = "no_image_candidates_found"
                    else:
                        next_index = saved_count + 1
                        for candidate in candidates:
                            if saved_count >= target_images_per_artist:
                                break
                            image_url = str(candidate.get("url") or "").strip()
                            if not image_url:
                                continue
                            ok_image, payload, ext, image_error = fetch_image(session, image_url)
                            if not ok_image:
                                case_notes.append(image_error)
                                continue
                            file_path = artist_dir / f"image_{next_index:02d}{ext}"
                            file_path.write_bytes(payload)
                            saved_count += 1
                            next_index += 1
                        if saved_count < target_images_per_artist and not case_reason:
                            case_reason = "insufficient_image_candidates_after_download"

            success_ge1 = saved_count >= 1
            success_ge_target = saved_count >= target_images_per_artist
            if success_ge1:
                domain_stats[domain]["success_ge1_count"] += 1
            if success_ge_target:
                domain_stats[domain]["success_ge_target_count"] += 1
            domain_stats[domain]["images_saved_total"] += saved_count

            summary["processed_artist_count"] += 1
            summary["artists_with_ge_1_image"] += int(success_ge1)
            summary["artists_with_ge_target_images"] += int(success_ge_target)
            summary["total_images_saved"] += saved_count

            summary["per_artist_counts"].append(
                {
                    "artist_id": artist_id,
                    "source_url": source_url,
                    "fair_slug": fair_slug,
                    "gallery_name_en": gallery_name_en,
                    "saved_images": saved_count,
                    "target_images": target_images_per_artist,
                    "target_met": success_ge_target,
                }
            )

            if not success_ge_target:
                fail_reason = case_reason or "target_not_met"
                summary["failed_cases"].append(
                    {
                        "artist_id": artist_id,
                        "source_url": source_url,
                        "saved_images": saved_count,
                        "target_images": target_images_per_artist,
                        "reason": fail_reason,
                        "notes": case_notes[:5],
                    }
                )

        processed = int(summary["processed_artist_count"])
        success_target = int(summary["artists_with_ge_target_images"])
        rate = (success_target / processed) if processed > 0 else 0.0
        summary["success_rate_ge_target"] = round(rate, 6)
        summary["threshold_passed"] = bool(rate >= success_threshold)
        summary["domain_stats"] = dict(domain_stats)
        if not summary["threshold_passed"]:
            summary["notes"].append(
                f"threshold_not_met:{summary['artists_with_ge_target_images']}/{summary['processed_artist_count']}<{success_threshold:.2f}"
            )
        summary["notes"].append("count_mode=effective_images_after_run")
        summary["generated_at"] = utc_now_iso()

        write_json(summary_path, summary)
        print(
            "[DONE] "
            f"processed={summary['processed_artist_count']} "
            f"ge_target={summary['artists_with_ge_target_images']} "
            f"success_rate={summary['success_rate_ge_target']:.4f} "
            f"threshold_passed={summary['threshold_passed']}"
        )
        print(f"[DONE] summary={summary_path}")
        return 0
    except Exception as exc:  # noqa: BLE001
        summary["wrapper_exit_code"] = 1
        summary["notes"].append(f"fatal_error:{exc}")
        summary["generated_at"] = utc_now_iso()
        write_json(summary_path, summary)
        print(f"[ERROR] {exc}")
        print(f"[DONE] summary={summary_path}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
