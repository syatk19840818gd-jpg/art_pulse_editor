from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from phase1_exhibitions_text_utils import (
    canonicalize_exhibition_url,
    extract_year_tokens,
    has_explicit_non_target_year,
    merge_sources,
    normalize_sources,
)

RAG_CATEGORY = "exhibitions_text"
JOIN_BY_SOURCE_URL = "JOIN_BY_SOURCE_URL"
JOIN_BY_SOURCES_FALLBACK = "JOIN_BY_SOURCES_FALLBACK"
TEXT_ONLY = "TEXT_ONLY"
AMBIGUOUS_JOIN = "AMBIGUOUS_JOIN"
DUPLICATE_JOIN_COLLISION = "DUPLICATE_JOIN_COLLISION"
IMAGE_TEXT_MISMATCH = "IMAGE_TEXT_MISMATCH"

DEFAULT_IMAGE_JSONL = [
    Path("data/phase1_seed10/derived/exhibitions_images_frieze_london_2025.jsonl"),
    Path("data/phase1_seed10/derived/exhibitions_images_liste_2025.jsonl"),
]
SUSPICIOUS_ROUTE_TOKENS = (
    "viewing-room",
    "/about",
    "/artists",
    "/artist",
    "/past",
    "/upcoming",
    "/art-fairs",
)
HARD_BAD_ROUTE_TOKENS = (
    "viewing-room",
    "/about",
    "/artists",
    "/artist",
)
SOFT_SUSPICIOUS_ROUTE_TOKENS = (
    "/past",
    "/upcoming",
    "/art-fairs",
)
PROVENANCE_WEAK_REASON_TOKENS = (
    "metadata_fallback",
    "fallback",
    "listing",
    "root",
)
ALLOWED_SELECTED_REASONS = {
    "",
    "detail_page_candidate_rank",
    "detail_page_candidate",
    "year_signal_present",
    "year_signal_in_url_path",
    "two_digit_year_signal",
    "no_explicit_year_signal",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utc_timestamp_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip().lstrip("\ufeff")
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows


def write_jsonl_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def normalize_text_for_hash(text: str) -> str:
    return " ".join(str(text or "").lower().split()).strip()


def normalize_url_for_hash(url: str) -> str:
    parsed = urlparse(str(url or "").strip())
    path = parsed.path or "/"
    normalized = f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{path}"
    return normalized.rstrip("/")


def compute_text_hash(text: str, source_url: str, rag_category: str = RAG_CATEGORY) -> str:
    normalized_text = normalize_text_for_hash(text)
    if normalized_text:
        payload = f"{rag_category}\n{normalized_text}"
    else:
        payload = f"{rag_category}\n{normalize_url_for_hash(source_url)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def parse_int(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        return int(text)
    return None


def classify_route(source_url: str) -> str:
    quality = classify_route_quality(source_url)
    if quality in {"hard_bad", "soft_suspicious"}:
        return "suspicious"
    return quality


def classify_route_quality(source_url: str) -> str:
    lowered = str(source_url or "").lower()
    if not lowered:
        return "missing"
    for token in HARD_BAD_ROUTE_TOKENS:
        if token in lowered:
            return "hard_bad"
    for token in SOFT_SUSPICIOUS_ROUTE_TOKENS:
        if token in lowered:
            return "soft_suspicious"
    return "detail_candidate"


def parse_date_year(value: Any) -> int | None:
    text = str(value or "").strip()
    if len(text) < 4:
        return None
    head = text[:4]
    if head.isdigit():
        return int(head)
    return None


def is_explicit_non_target_year_range(*, start_date: str, end_date: str, target_year: int) -> bool:
    start_year = parse_date_year(start_date)
    end_year = parse_date_year(end_date)
    if start_year is None or end_year is None:
        return False
    lower = min(start_year, end_year)
    upper = max(start_year, end_year)
    return not (int(target_year) >= lower and int(target_year) <= upper)


def evaluate_quality_gate(summary: dict[str, Any]) -> dict[str, Any]:
    source_missing = int(summary.get("source_url_missing_count") or 0)
    route_hard = int(summary.get("route_hard_bad_count") or 0)
    route_soft = int(summary.get("route_soft_suspicious_count") or 0)
    year_hard = int(summary.get("year_hard_mismatch_count") or 0)
    year_soft = int(summary.get("year_soft_suspicious_count") or 0)
    provenance_suspicious = int(summary.get("provenance_suspicious_count") or 0)
    date_non_target = int(summary.get("date_non_target_year_count") or 0)
    date_missing = int(summary.get("date_missing_count") or 0)
    pdf_unmerged = int(summary.get("pdf_unmerged_with_url_count") or 0)
    ambiguous = int(summary.get("ambiguous_join_count") or 0)
    duplicate = int(summary.get("duplicate_join_group_count") or 0)
    mismatch = int(summary.get("image_text_mismatch_count") or 0)

    route_signal = "PASS"
    if route_hard > 0:
        route_signal = "REJECT"
    elif route_soft > 0:
        route_signal = "WARN"

    year_signal = "PASS"
    if year_hard > 0:
        year_signal = "HOLD"
    elif year_soft > 0:
        year_signal = "WARN"

    provenance_signal = "HOLD" if provenance_suspicious > 0 else "PASS"
    date_signal = "PASS"
    if date_non_target > 0:
        date_signal = "HOLD"
    elif date_missing > 0:
        date_signal = "WARN"
    source_signal = "REJECT" if source_missing > 0 else "PASS"
    pdf_signal = "WARN" if pdf_unmerged > 0 else "PASS"

    blocker_labels: list[str] = []
    review_required_count = 0

    if source_missing > 0:
        blocker_labels.append("SOURCE_URL_MISSING")
    if route_hard > 0:
        blocker_labels.append("KNOWN_BAD_ROUTE_RECURRED")
    if year_hard > 0 or date_non_target > 0:
        blocker_labels.append("SUSPICIOUS_YEAR")
    if provenance_suspicious > 0:
        blocker_labels.append("SUSPICIOUS_PROVENANCE")
    if mismatch > 0:
        blocker_labels.append("IMAGE_TEXT_MISMATCH")
    if ambiguous > 0:
        blocker_labels.append("AMBIGUOUS_JOIN")
    if duplicate > 0:
        blocker_labels.append("DUPLICATE_JOIN_COLLISION")

    review_required_count += route_soft
    review_required_count += year_soft
    review_required_count += date_missing
    review_required_count += pdf_unmerged

    if source_signal == "REJECT" or route_signal == "REJECT":
        gate_verdict = "REJECT"
    elif len(blocker_labels) > 0:
        gate_verdict = "HOLD"
    elif review_required_count > 0:
        gate_verdict = "WARN"
    else:
        gate_verdict = "PASS"

    gate_passed = gate_verdict in {"PASS", "WARN"}
    return {
        "gate_verdict": gate_verdict,
        "gate_passed": gate_passed,
        "blocker_labels": sorted(set(blocker_labels)),
        "review_required_count": int(review_required_count),
        "route_quality_signal": route_signal,
        "year_quality_signal": year_signal,
        "provenance_quality_signal": provenance_signal,
        "date_quality_signal": date_signal,
        "source_url_presence_signal": source_signal,
        "pdf_handling_signal": pdf_signal,
    }


def classify_provenance(row: dict[str, Any], source_url: str) -> bool:
    selected_reason = str(row.get("selected_reason") or "").strip().lower()
    if selected_reason not in ALLOWED_SELECTED_REASONS:
        return True
    if any(token in selected_reason for token in PROVENANCE_WEAK_REASON_TOKENS):
        return True
    seed_source_url = canonicalize_exhibition_url(str(row.get("seed_source_url") or ""))
    parent_source_url = canonicalize_exhibition_url(str(row.get("parent_source_url") or ""))
    if parent_source_url and classify_route(parent_source_url) == "suspicious":
        return True
    if seed_source_url:
        seed_host = urlparse(seed_source_url).netloc.lower()
        source_host = urlparse(source_url).netloc.lower()
        if seed_host and source_host and seed_host != source_host:
            return True
    return False


def resolve_candidate_year(row: dict[str, Any], source_url: str, text: str) -> int | None:
    explicit = parse_int(row.get("candidate_year"))
    if explicit:
        return explicit
    target_from_row = parse_int(row.get("target_year"))
    if target_from_row:
        return target_from_row
    years = extract_year_tokens(f"{source_url}\n{text}")
    if len(years) == 1:
        return next(iter(years))
    return None


def normalize_gallery_name(row: dict[str, Any]) -> str:
    return str(row.get("gallery_name") or row.get("gallery_name_en") or "").strip()


def canonical_record_source_url(row: dict[str, Any]) -> str:
    raw = str(row.get("source_url") or "").strip()
    if not raw:
        return ""
    return canonicalize_exhibition_url(raw)


def load_image_index(paths: list[Path]) -> dict[str, list[dict[str, Any]]]:
    by_source_url: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for path in paths:
        for row in read_jsonl_rows(path):
            source_url = canonicalize_exhibition_url(str(row.get("source_url") or ""))
            if not source_url:
                continue
            by_source_url[source_url].append(
                {
                    "source_url": source_url,
                    "fair_slug": str(row.get("fair_slug") or "").strip(),
                    "target_year": parse_int(row.get("target_year")),
                    "gallery_name_en": str(row.get("gallery_name_en") or "").strip(),
                    "r2_key": str(row.get("r2_key") or "").strip(),
                    "local_path": str(row.get("local_path") or "").strip(),
                    "image_url": str(row.get("image_url") or "").strip(),
                }
            )
    return by_source_url


def _candidate_matches_scope(candidate: dict[str, Any], record: dict[str, Any]) -> bool:
    fair_record = str(record.get("fair_slug") or "").strip()
    fair_candidate = str(candidate.get("fair_slug") or "").strip()
    if fair_record and fair_candidate and fair_record != fair_candidate:
        return False
    year_record = parse_int(record.get("target_year"))
    year_candidate = parse_int(candidate.get("target_year"))
    if year_record and year_candidate and year_record != year_candidate:
        return False
    gallery_record = normalize_gallery_name(record).casefold()
    gallery_candidate = str(candidate.get("gallery_name_en") or "").strip().casefold()
    if gallery_record and gallery_candidate and gallery_record != gallery_candidate:
        return False
    return True


def _dedupe_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[str, dict[str, Any]] = {}
    for row in candidates:
        key = "|".join(
            [
                str(row.get("source_url") or ""),
                str(row.get("r2_key") or ""),
                str(row.get("local_path") or ""),
                str(row.get("image_url") or ""),
            ]
        )
        unique[key] = row
    return list(unique.values())


def _has_collision(candidates: list[dict[str, Any]]) -> bool:
    r2_groups: dict[str, set[str]] = defaultdict(set)
    path_groups: dict[str, set[str]] = defaultdict(set)
    for row in candidates:
        source = str(row.get("source_url") or "")
        r2_key = str(row.get("r2_key") or "")
        local_path = str(row.get("local_path") or "")
        if r2_key:
            r2_groups[r2_key].add(source or local_path)
        if local_path:
            path_groups[local_path].add(source or r2_key)
    if any(len(v) > 1 for v in r2_groups.values()):
        return True
    if any(len(v) > 1 for v in path_groups.values()):
        return True
    return False


def evaluate_joinability(
    *,
    record: dict[str, Any],
    sources_for_hash: list[str],
    image_index: dict[str, list[dict[str, Any]]],
) -> tuple[str, str, str, int]:
    source_url = str(record.get("source_url") or "")
    ordered_sources: list[str] = []
    for src in [source_url, *sources_for_hash]:
        canon = canonicalize_exhibition_url(src)
        if canon and canon not in ordered_sources:
            ordered_sources.append(canon)

    primary_candidates = list(image_index.get(source_url, []))
    all_candidates: list[dict[str, Any]] = []
    for src in ordered_sources:
        all_candidates.extend(image_index.get(src, []))

    if not all_candidates:
        return TEXT_ONLY, "no_image_candidate", "", 0

    valid = [row for row in all_candidates if _candidate_matches_scope(row, record)]
    mismatched = [row for row in all_candidates if row not in valid]
    valid = _dedupe_candidates(valid)

    if valid and mismatched:
        return IMAGE_TEXT_MISMATCH, "mixed_scope_candidates", "", len(valid)

    if not valid and mismatched:
        return IMAGE_TEXT_MISMATCH, "scope_mismatch", "", 0

    if _has_collision(valid):
        return DUPLICATE_JOIN_COLLISION, "duplicate_image_key_collision", "", len(valid)

    if len(valid) > 1:
        source_count = len({str(row.get("source_url") or "") for row in valid})
        if source_count > 1:
            return AMBIGUOUS_JOIN, "multiple_source_candidates", "", len(valid)
        return AMBIGUOUS_JOIN, "multiple_image_candidates", "", len(valid)

    if valid:
        chosen = valid[0]
        chosen_source = str(chosen.get("source_url") or "")
        if chosen_source == source_url:
            return JOIN_BY_SOURCE_URL, "source_url_exact", chosen_source, 1
        return JOIN_BY_SOURCES_FALLBACK, "sources_fallback", chosen_source, 1

    return TEXT_ONLY, "no_valid_image_after_scope_check", "", 0


def load_text_sources(path: Path) -> dict[str, list[str]]:
    payload = read_json(path, default={})
    if not isinstance(payload, dict):
        return {}
    mapping = payload.get("text_hash_to_sources", payload)
    if not isinstance(mapping, dict):
        return {}
    out: dict[str, list[str]] = {}
    for key, value in mapping.items():
        if not isinstance(key, str) or not key.strip():
            continue
        out[key.strip()] = normalize_sources(value, fallback_source_url="")
    return out


def save_text_sources(path: Path, mapping: dict[str, list[str]], *, target_year: int) -> None:
    normalized = {k: normalize_sources(v, fallback_source_url="") for k, v in sorted(mapping.items())}
    payload = {
        "artifact": "text_sources",
        "version": 1,
        "target_year": int(target_year),
        "updated_at": utc_now_iso(),
        "text_hash_to_sources": normalized,
    }
    write_json(path, payload)


def main() -> int:
    parser = argparse.ArgumentParser(description="Exhibitions Text standard lane minimal (proposal-only)")
    parser.add_argument("--input-jsonl", action="append", required=True, help="input exhibitions text jsonl (repeatable)")
    parser.add_argument("--image-jsonl", action="append", default=[], help="image jsonl for join checks (repeatable)")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--text-sources-json", default="")
    parser.add_argument("--target-year", type=int, default=2025)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--proposal-bundle-id", default="")
    parser.add_argument("--max-records", type=int, default=0)
    args = parser.parse_args()

    run_id = args.run_id.strip() or utc_timestamp_compact()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    text_sources_path = Path(args.text_sources_json).resolve() if args.text_sources_json else (output_dir / "text_sources.json")

    input_paths = [Path(p) for p in args.input_jsonl]
    image_paths = [Path(p) for p in args.image_jsonl] if args.image_jsonl else DEFAULT_IMAGE_JSONL
    image_index = load_image_index(image_paths)
    text_sources = load_text_sources(text_sources_path)

    input_rows: list[dict[str, Any]] = []
    for path in input_paths:
        input_rows.extend(read_jsonl_rows(path))
    if args.max_records > 0:
        input_rows = input_rows[: args.max_records]

    metrics = Counter()
    status_counts = Counter()
    text_hash_seen_counts: dict[str, int] = defaultdict(int)
    proposal_records_by_hash: dict[str, dict[str, Any]] = {}
    extracted_at = utc_now_iso()

    for row in input_rows:
        source_url = canonical_record_source_url(row)
        if not source_url:
            metrics["source_url_missing_count"] += 1
            continue

        start_date = str(row.get("exhibition_start_date") or "").strip()
        end_date = str(row.get("exhibition_end_date") or "").strip()
        if is_explicit_non_target_year_range(
            start_date=start_date,
            end_date=end_date,
            target_year=int(args.target_year),
        ):
            metrics["input_filter_rejected_non_target_year_count"] += 1
            continue

        text = str(row.get("text") or "").strip()
        text_hash = str(row.get("text_hash") or "").strip()
        if not text_hash:
            text_hash = compute_text_hash(text=text, source_url=source_url)
        text_hash_seen_counts[text_hash] += 1

        row_sources = normalize_sources(row.get("sources"), fallback_source_url=source_url)
        existing_sources = text_sources.get(text_hash, [])
        merged_sources = normalize_sources(existing_sources, fallback_source_url="")
        for src in row_sources:
            merged_sources = merge_sources(merged_sources, src)
        text_sources[text_hash] = merged_sources

        if text_hash in proposal_records_by_hash:
            proposal_records_by_hash[text_hash]["sources"] = merged_sources
            continue

        candidate_year = resolve_candidate_year(row, source_url, text)
        route_quality_label = classify_route_quality(source_url)
        if route_quality_label == "hard_bad":
            metrics["route_hard_bad_count"] += 1
            metrics["route_suspicious_count"] += 1
        elif route_quality_label == "soft_suspicious":
            metrics["route_soft_suspicious_count"] += 1
            metrics["route_suspicious_count"] += 1

        explicit_non_target = has_explicit_non_target_year(
            f"{source_url}\n{text}",
            int(args.target_year),
        )
        if explicit_non_target:
            metrics["non_target_year_count"] += 1
        elif candidate_year is not None and candidate_year == int(args.target_year):
            metrics["target_year_match_count"] += 1
        elif candidate_year is not None and candidate_year != int(args.target_year):
            metrics["non_target_year_count"] += 1

        year_quality_label = "pass"
        if candidate_year is not None and candidate_year != int(args.target_year):
            year_quality_label = "hard_mismatch"
        elif explicit_non_target and candidate_year is None:
            year_quality_label = "hard_mismatch"
        elif explicit_non_target or candidate_year is None:
            year_quality_label = "soft_suspicious"

        year_suspicious = year_quality_label != "pass"
        if year_suspicious:
            metrics["year_suspicious_count"] += 1
        if year_quality_label == "hard_mismatch":
            metrics["year_hard_mismatch_count"] += 1
        elif year_quality_label == "soft_suspicious":
            metrics["year_soft_suspicious_count"] += 1

        route_class = classify_route(source_url)

        provenance_suspicious = classify_provenance(row, source_url)
        if provenance_suspicious:
            metrics["provenance_suspicious_count"] += 1

        join_status, join_basis, primary_match_source, matched_count = evaluate_joinability(
            record={
                "source_url": source_url,
                "fair_slug": str(row.get("fair_slug") or "").strip(),
                "target_year": parse_int(row.get("target_year")) or int(args.target_year),
                "gallery_name": normalize_gallery_name(row),
            },
            sources_for_hash=merged_sources,
            image_index=image_index,
        )
        status_counts[join_status] += 1

        if join_status == JOIN_BY_SOURCE_URL:
            metrics["joinable_to_image_by_source_url_count"] += 1
        elif join_status == JOIN_BY_SOURCES_FALLBACK:
            metrics["joinable_to_image_by_sources_fallback_count"] += 1
        elif join_status == TEXT_ONLY:
            metrics["text_only_count"] += 1
        elif join_status == AMBIGUOUS_JOIN:
            metrics["ambiguous_join_count"] += 1
        elif join_status == DUPLICATE_JOIN_COLLISION:
            metrics["duplicate_join_group_count"] += 1
        elif join_status == IMAGE_TEXT_MISMATCH:
            metrics["image_text_mismatch_count"] += 1

        if start_date or end_date:
            metrics["date_parse_success_count"] += 1
        else:
            metrics["date_missing_count"] += 1

        start_year = parse_date_year(start_date)
        end_year = parse_date_year(end_date)
        target_year = int(args.target_year)
        date_non_target_year = False
        if start_year is not None and end_year is not None:
            low_year = min(start_year, end_year)
            high_year = max(start_year, end_year)
            date_non_target_year = not (low_year <= target_year <= high_year)
        elif start_year is not None:
            date_non_target_year = start_year != target_year
        elif end_year is not None:
            date_non_target_year = end_year != target_year
        if date_non_target_year:
            metrics["date_non_target_year_count"] += 1

        pdf_merged = bool(row.get("pdf_text_merged") or row.get("pdf_merged"))
        pdf_url = str(row.get("pdf_url") or "").strip()
        if pdf_merged:
            metrics["pdf_merge_count"] += 1
        if pdf_url and not pdf_merged:
            metrics["pdf_unmerged_with_url_count"] += 1

        extract_status = "saved"
        if join_status in {AMBIGUOUS_JOIN, DUPLICATE_JOIN_COLLISION, IMAGE_TEXT_MISMATCH}:
            extract_status = "review_required"
        elif join_status == TEXT_ONLY:
            extract_status = "saved_text_only"

        proposal_records_by_hash[text_hash] = {
            "source_url": source_url,
            "sources": merged_sources,
            "text": text,
            "text_hash": text_hash,
            "gallery_name": normalize_gallery_name(row),
            "gallery_name_en": str(row.get("gallery_name_en") or "").strip(),
            "fair_slug": str(row.get("fair_slug") or "").strip(),
            "target_year": parse_int(row.get("target_year")) or int(args.target_year),
            "candidate_year": candidate_year,
            "exhibition_start_date": start_date,
            "exhibition_end_date": end_date,
            "date_source": str(row.get("date_source") or "").strip(),
            "date_confidence": str(row.get("date_confidence") or "").strip(),
            "extract_status": extract_status,
            "join_status": join_status,
            "join_basis": join_basis,
            "primary_image_match_source_url": primary_match_source,
            "matched_image_count": int(matched_count),
            "pdf_url": pdf_url,
            "pdf_merged": bool(pdf_merged),
            "seed_source_url": str(row.get("seed_source_url") or "").strip(),
            "seed_url_type": str(row.get("seed_url_type") or "").strip(),
            "selected_reason": str(row.get("selected_reason") or "").strip(),
            "evidence_text": str(row.get("evidence_text") or "").strip(),
            "parent_source_url": str(row.get("parent_source_url") or "").strip(),
            "route_class": route_class,
            "route_quality_label": route_quality_label,
            "year_suspicious": bool(year_suspicious),
            "year_quality_label": year_quality_label,
            "date_non_target_year": bool(date_non_target_year),
            "provenance_suspicious": bool(provenance_suspicious),
            "extracted_at": str(row.get("extracted_at") or extracted_at),
            "proposal_run_id": run_id,
            "rag_category": RAG_CATEGORY,
            "target_year_signal_reason": str(row.get("target_year_signal_reason") or "").strip(),
        }

    duplicate_groups = sum(1 for _, count in text_hash_seen_counts.items() if count > 1)
    metrics["text_hash_duplicate_groups"] = duplicate_groups
    records = list(proposal_records_by_hash.values())
    metrics["records_total"] = len(records)

    bundle_id = args.proposal_bundle_id.strip() or f"exhibitions_text_proposal_bundle_{run_id}"
    records_path = output_dir / f"exhibitions_text_proposal_records_{run_id}.jsonl"
    summary_path = output_dir / f"exhibitions_text_proposal_summary_{run_id}.json"
    manifest_path = output_dir / f"exhibitions_text_proposal_manifest_{run_id}.json"
    sources_snapshot_path = output_dir / f"text_sources_{run_id}.json"

    write_jsonl_rows(records_path, records)
    save_text_sources(text_sources_path, text_sources, target_year=args.target_year)
    save_text_sources(sources_snapshot_path, text_sources, target_year=args.target_year)

    summary = {
        "artifact": "exhibitions_text_proposal_summary",
        "task": "TASK230",
        "run_id": run_id,
        "proposal_bundle_id": bundle_id,
        "target_year": int(args.target_year),
        "created_at": utc_now_iso(),
        "records_total": int(metrics["records_total"]),
        "source_url_missing_count": int(metrics["source_url_missing_count"]),
        "input_filter_rejected_non_target_year_count": int(
            metrics["input_filter_rejected_non_target_year_count"]
        ),
        "text_hash_duplicate_groups": int(metrics["text_hash_duplicate_groups"]),
        "target_year_match_count": int(metrics["target_year_match_count"]),
        "non_target_year_count": int(metrics["non_target_year_count"]),
        "date_parse_success_count": int(metrics["date_parse_success_count"]),
        "joinable_to_image_by_source_url_count": int(metrics["joinable_to_image_by_source_url_count"]),
        "joinable_to_image_by_sources_fallback_count": int(metrics["joinable_to_image_by_sources_fallback_count"]),
        "text_only_count": int(metrics["text_only_count"]),
        "ambiguous_join_count": int(metrics["ambiguous_join_count"]),
        "duplicate_join_group_count": int(metrics["duplicate_join_group_count"]),
        "image_text_mismatch_count": int(metrics["image_text_mismatch_count"]),
        "provenance_suspicious_count": int(metrics["provenance_suspicious_count"]),
        "route_suspicious_count": int(metrics["route_suspicious_count"]),
        "route_hard_bad_count": int(metrics["route_hard_bad_count"]),
        "route_soft_suspicious_count": int(metrics["route_soft_suspicious_count"]),
        "year_suspicious_count": int(metrics["year_suspicious_count"]),
        "year_hard_mismatch_count": int(metrics["year_hard_mismatch_count"]),
        "year_soft_suspicious_count": int(metrics["year_soft_suspicious_count"]),
        "date_missing_count": int(metrics["date_missing_count"]),
        "date_non_target_year_count": int(metrics["date_non_target_year_count"]),
        "pdf_merge_count": int(metrics["pdf_merge_count"]),
        "pdf_unmerged_with_url_count": int(metrics["pdf_unmerged_with_url_count"]),
        "join_status_counts": dict(status_counts),
        "input_row_count": len(input_rows),
        "proposal_record_count": len(records),
        "current_formal_touched": False,
        "adoption_executed": False,
        "rollback_executed": False,
    }
    quality_gate = evaluate_quality_gate(summary)
    summary["gate_verdict"] = quality_gate["gate_verdict"]
    summary["gate_passed"] = bool(quality_gate["gate_passed"])
    summary["blocker_labels"] = quality_gate["blocker_labels"]
    summary["review_required_count"] = int(quality_gate["review_required_count"])
    summary["route_quality_signal"] = quality_gate["route_quality_signal"]
    summary["year_quality_signal"] = quality_gate["year_quality_signal"]
    summary["provenance_quality_signal"] = quality_gate["provenance_quality_signal"]
    summary["date_quality_signal"] = quality_gate["date_quality_signal"]
    summary["source_url_presence_signal"] = quality_gate["source_url_presence_signal"]
    summary["pdf_handling_signal"] = quality_gate["pdf_handling_signal"]
    write_json(summary_path, summary)

    manifest = {
        "artifact": "exhibitions_text_proposal_manifest",
        "task": "TASK230",
        "run_id": run_id,
        "proposal_bundle_id": bundle_id,
        "created_at": utc_now_iso(),
        "inputs": {
            "input_jsonl": [str(p) for p in input_paths],
            "image_jsonl": [str(p) for p in image_paths],
            "text_sources_json": str(text_sources_path),
        },
        "outputs": {
            "proposal_records_jsonl": str(records_path),
            "proposal_summary_json": str(summary_path),
            "proposal_manifest_json": str(manifest_path),
            "text_sources_json": str(text_sources_path),
            "text_sources_snapshot_json": str(sources_snapshot_path),
        },
        "policies": {
            "formal_is_authoritative": True,
            "proposal_direct_adoption_forbidden": True,
            "text_only_allowed": True,
            "image_text_mismatch_forbidden_for_auto_adopt": True,
            "ambiguous_join_auto_resolution": False,
            "duplicate_join_auto_resolution": False,
            "enrichment_in_scope": False,
            "anti_mixing_enforced": True,
        },
        "quality_gate": {
            "gate_verdict": summary["gate_verdict"],
            "gate_passed": summary["gate_passed"],
            "blocker_labels": summary["blocker_labels"],
            "review_required_count": summary["review_required_count"],
            "route_quality_signal": summary["route_quality_signal"],
            "year_quality_signal": summary["year_quality_signal"],
            "provenance_quality_signal": summary["provenance_quality_signal"],
            "date_quality_signal": summary["date_quality_signal"],
            "source_url_presence_signal": summary["source_url_presence_signal"],
            "pdf_handling_signal": summary["pdf_handling_signal"],
        },
    }
    write_json(manifest_path, manifest)

    print(
        "[exhibitions-text-minimal] "
        f"run_id={run_id} records={summary['records_total']} "
        f"join_source={summary['joinable_to_image_by_source_url_count']} "
        f"join_fallback={summary['joinable_to_image_by_sources_fallback_count']} "
        f"text_only={summary['text_only_count']} "
        f"ambiguous={summary['ambiguous_join_count']} "
        f"duplicate={summary['duplicate_join_group_count']} "
        f"mismatch={summary['image_text_mismatch_count']} "
        f"gate={summary['gate_verdict']}"
    )
    print(f"[exhibitions-text-minimal] summary={summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
