from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

PROJECT_ROOT = Path(__file__).resolve().parent
SKIPPED_GALLERIES_REGISTRY_PATH = Path("data/gallery_lists/skipped_galleries_registry.csv")
OFFICIAL_GALLERY_LIST_FRIEZE_LONDON_PATH = (
    PROJECT_ROOT / "data" / "gallery_lists" / "gallery_list_frieze_london.csv"
).resolve()
OFFICIAL_GALLERY_LIST_LISTE_PATH = (
    PROJECT_ROOT / "data" / "gallery_lists" / "gallery_list_liste.csv"
).resolve()
OFFICIAL_SKIPPED_GALLERIES_REGISTRY_PATH = (PROJECT_ROOT / SKIPPED_GALLERIES_REGISTRY_PATH).resolve()
OFFICIAL_RAG_GALLERY_BREAKDOWN_XLSX_PATH = (
    PROJECT_ROOT / "data" / "gallery_lists" / "rag_gellery_breakdown_master.xlsx"
).resolve()
OFFICIAL_MUTATION_PROTECTED_PATHS = frozenset(
    {
        OFFICIAL_GALLERY_LIST_FRIEZE_LONDON_PATH,
        OFFICIAL_GALLERY_LIST_LISTE_PATH,
        OFFICIAL_SKIPPED_GALLERIES_REGISTRY_PATH,
        OFFICIAL_RAG_GALLERY_BREAKDOWN_XLSX_PATH,
    }
)
REGISTRY_FIELDS = (
    "fair_slug",
    "gallery_name_en",
    "skip_reason",
    "detected_at",
    "run_id",
    "source_scope_file",
    "evidence",
)
KNOWN_FAIR_SLUGS = {"frieze_london", "liste"}


def resolve_repo_path(path: Path) -> Path:
    if path.is_absolute():
        return path.resolve()
    return (PROJECT_ROOT / path).resolve()


def is_official_mutation_protected_path(path: Path) -> bool:
    return resolve_repo_path(path) in OFFICIAL_MUTATION_PROTECTED_PATHS


def require_official_apply(
    path: Path,
    *,
    official_apply: bool,
    operation: str,
) -> None:
    resolved_path = resolve_repo_path(path)
    if resolved_path in OFFICIAL_MUTATION_PROTECTED_PATHS and not official_apply:
        raise RuntimeError(
            f"official_apply_required_for_{operation}: {resolved_path}"
        )


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def normalize_fair_slug(value: str) -> str:
    token = str(value or "").strip().lower().replace("-", "_")
    if token in KNOWN_FAIR_SLUGS:
        return token
    return token


def normalize_gallery_name(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value or "").strip())
    text = re.sub(r"\s+", " ", text)
    text = "".join(ch for ch in unicodedata.normalize("NFD", text) if unicodedata.category(ch) != "Mn")
    return text.casefold()


def extract_gallery_name_en_from_list_cell(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKC", text)
    if " (" in normalized:
        return normalized.split(" (", 1)[0].strip()
    if "（" in normalized:
        return normalized.split("（", 1)[0].strip()
    return normalized.strip()


@dataclass(frozen=True)
class SkipGalleryEntry:
    fair_slug: str
    gallery_name_en: str
    skip_reason: str
    detected_at: str
    run_id: str
    source_scope_file: str
    evidence: str

    @property
    def scope_key(self) -> tuple[str, str]:
        return normalize_fair_slug(self.fair_slug), normalize_gallery_name(self.gallery_name_en)

    def to_row(self) -> dict[str, str]:
        return {
            "fair_slug": normalize_fair_slug(self.fair_slug),
            "gallery_name_en": str(self.gallery_name_en or "").strip(),
            "skip_reason": str(self.skip_reason or "").strip(),
            "detected_at": str(self.detected_at or "").strip(),
            "run_id": str(self.run_id or "").strip(),
            "source_scope_file": str(self.source_scope_file or "").strip(),
            "evidence": str(self.evidence or "").strip(),
        }


def _looks_like_header(row: list[str]) -> bool:
    if not row:
        return False
    normalized = {str(cell or "").strip().lower() for cell in row}
    return "gallery_name_en" in normalized or "fair_slug" in normalized


def _entry_from_dict_row(row: dict[str, Any]) -> SkipGalleryEntry | None:
    gallery_name = str(row.get("gallery_name_en") or row.get("gallery_name") or "").strip()
    if not gallery_name:
        return None
    return SkipGalleryEntry(
        fair_slug=normalize_fair_slug(str(row.get("fair_slug") or row.get("fair") or "").strip()),
        gallery_name_en=gallery_name,
        skip_reason=str(row.get("skip_reason") or "").strip(),
        detected_at=str(row.get("detected_at") or "").strip(),
        run_id=str(row.get("run_id") or "").strip(),
        source_scope_file=str(row.get("source_scope_file") or "").strip(),
        evidence=str(row.get("evidence") or row.get("note") or "").strip(),
    )


def _entry_from_legacy_row(row: list[str]) -> SkipGalleryEntry | None:
    if not row:
        return None
    gallery_name = str(row[0] or "").strip()
    if not gallery_name:
        return None
    skip_reason = str(row[3] or "").strip() if len(row) >= 4 else ""
    return SkipGalleryEntry(
        fair_slug="",
        gallery_name_en=gallery_name,
        skip_reason=skip_reason,
        detected_at="",
        run_id="",
        source_scope_file="",
        evidence="legacy_registry_row",
    )


def load_skip_registry_entries(path: Path = SKIPPED_GALLERIES_REGISTRY_PATH) -> list[SkipGalleryEntry]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    lines = text.splitlines()
    first_row = next(csv.reader([lines[0]]), [])
    entries: list[SkipGalleryEntry] = []
    if _looks_like_header(first_row):
        reader = csv.DictReader(lines)
        for row in reader:
            entry = _entry_from_dict_row(row)
            if entry is not None:
                entries.append(entry)
        return entries
    reader = csv.reader(lines)
    for row in reader:
        entry = _entry_from_legacy_row(row)
        if entry is not None:
            entries.append(entry)
    return entries


def build_skip_lookup(entries: Iterable[SkipGalleryEntry]) -> dict[str, dict[Any, SkipGalleryEntry]]:
    by_scope: dict[tuple[str, str], SkipGalleryEntry] = {}
    by_gallery: dict[str, SkipGalleryEntry] = {}
    for entry in entries:
        fair_slug, gallery_key = entry.scope_key
        if not gallery_key:
            continue
        if fair_slug:
            by_scope[(fair_slug, gallery_key)] = entry
        else:
            by_gallery[gallery_key] = entry
    return {"by_scope": by_scope, "by_gallery": by_gallery}


def find_skip_entry(
    lookup: dict[str, dict[Any, SkipGalleryEntry]],
    *,
    fair_slug: str,
    gallery_name_en: str,
) -> SkipGalleryEntry | None:
    gallery_key = normalize_gallery_name(gallery_name_en)
    if not gallery_key:
        return None
    fair_key = normalize_fair_slug(fair_slug)
    by_scope = lookup.get("by_scope", {})
    by_gallery = lookup.get("by_gallery", {})
    if fair_key and (fair_key, gallery_key) in by_scope:
        return by_scope[(fair_key, gallery_key)]
    return by_gallery.get(gallery_key)


def is_skipped(
    lookup: dict[str, dict[Any, SkipGalleryEntry]],
    *,
    fair_slug: str,
    gallery_name_en: str,
) -> bool:
    return find_skip_entry(lookup, fair_slug=fair_slug, gallery_name_en=gallery_name_en) is not None


def upsert_skip_registry_entries(
    path: Path,
    new_entries: Iterable[SkipGalleryEntry],
    *,
    official_apply: bool = False,
) -> dict[str, Any]:
    resolved_path = resolve_repo_path(path)
    require_official_apply(
        resolved_path,
        official_apply=official_apply,
        operation="skip_registry_upsert",
    )
    existing_entries = load_skip_registry_entries(resolved_path)
    registry: dict[tuple[str, str], SkipGalleryEntry] = {entry.scope_key: entry for entry in existing_entries}
    added = 0
    updated = 0
    unchanged = 0
    for entry in new_entries:
        fair_slug, gallery_key = entry.scope_key
        if not gallery_key:
            continue
        key = (fair_slug, gallery_key)
        current = registry.get(key)
        if current is None:
            registry[key] = entry
            added += 1
            continue
        merged = SkipGalleryEntry(
            fair_slug=entry.fair_slug or current.fair_slug,
            gallery_name_en=entry.gallery_name_en or current.gallery_name_en,
            skip_reason=entry.skip_reason or current.skip_reason,
            detected_at=entry.detected_at or current.detected_at,
            run_id=entry.run_id or current.run_id,
            source_scope_file=entry.source_scope_file or current.source_scope_file,
            evidence=entry.evidence or current.evidence,
        )
        if merged == current:
            unchanged += 1
            continue
        registry[key] = merged
        updated += 1

    final_entries = sorted(
        registry.values(),
        key=lambda item: (
            normalize_fair_slug(item.fair_slug),
            normalize_gallery_name(item.gallery_name_en),
        ),
    )
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    with resolved_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(REGISTRY_FIELDS))
        writer.writeheader()
        for entry in final_entries:
            writer.writerow(entry.to_row())

    return {
        "registry_path": str(resolved_path),
        "added": added,
        "updated": updated,
        "unchanged": unchanged,
        "total": len(final_entries),
    }


def remove_skipped_from_gallery_list_csv(
    *,
    path: Path,
    fair_slug: str,
    lookup: dict[str, dict[Any, SkipGalleryEntry]],
    apply: bool = True,
    official_apply: bool = False,
) -> dict[str, Any]:
    mode = "apply" if apply else "dry_run"
    resolved_path = resolve_repo_path(path)
    if not resolved_path.exists():
        return {
            "mode": mode,
            "status": "blocked_missing_gallery_list",
            "gallery_list_path": str(resolved_path),
            "fair_slug": normalize_fair_slug(fair_slug),
            "removed_count": 0,
            "removed_galleries": [],
            "rows_before": 0,
            "rows_after": 0,
            "changed": False,
            "would_write": False,
            "missing": True,
        }
    rows: list[list[str]] = []
    with resolved_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    kept_rows: list[list[str]] = []
    removed_galleries: list[str] = []
    for row in rows:
        if not row:
            kept_rows.append(row)
            continue
        gallery_name_en = extract_gallery_name_en_from_list_cell(row[0] if len(row) >= 1 else "")
        if not gallery_name_en:
            kept_rows.append(row)
            continue
        if is_skipped(lookup, fair_slug=fair_slug, gallery_name_en=gallery_name_en):
            removed_galleries.append(gallery_name_en)
            continue
        kept_rows.append(row)
    changed = len(kept_rows) != len(rows)
    if changed and apply:
        require_official_apply(
            resolved_path,
            official_apply=official_apply,
            operation="gallery_list_cleanup",
        )
        with resolved_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerows(kept_rows)
    return {
        "mode": mode,
        "status": "applied" if apply else "planned",
        "gallery_list_path": str(resolved_path),
        "fair_slug": normalize_fair_slug(fair_slug),
        "removed_count": len(removed_galleries),
        "removed_galleries": removed_galleries,
        "rows_before": len(rows),
        "rows_after": len(kept_rows),
        "changed": changed,
        "would_write": bool(changed),
        "missing": False,
    }


def is_all_rag_zero_target_row(row: dict[str, Any]) -> bool:
    counts = extract_target_row_counts(row)
    artist_count = counts["artist_count"]
    artist_image_rows = counts["artist_image_rows"]
    artist_image_count = counts["artist_image_count"]
    exhibition_count = counts["exhibition_count"]
    exhibition_image_count = counts["exhibition_image_count"]
    return (
        artist_count == 0
        and artist_image_rows == 0
        and artist_image_count == 0
        and exhibition_count == 0
        and exhibition_image_count == 0
    )


def extract_target_row_counts(row: dict[str, Any]) -> dict[str, int]:
    def _int_or_zero(*keys: str) -> int:
        for key in keys:
            value = row.get(key)
            if value is None:
                continue
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
        return 0

    return {
        "artist_count": _int_or_zero("artist_count", "artist_text_count"),
        "artist_image_rows": _int_or_zero("artist_image_rows", "artist_image_keys_count"),
        "artist_image_count": _int_or_zero("artist_image_count"),
        "exhibition_count": _int_or_zero("exhibition_count", "exhibition_text_count"),
        "exhibition_image_rows": _int_or_zero(
            "exhibition_image_rows",
            "exhibition_image_keys_count",
            "exhibition_image_count",
        ),
        "exhibition_image_count": _int_or_zero(
            "exhibition_image_count",
            "exhibition_image_rows",
            "exhibition_image_keys_count",
        ),
    }


def is_exhibition_text_only_target_row(row: dict[str, Any]) -> bool:
    counts = extract_target_row_counts(row)
    artist_side_empty = (
        counts["artist_count"] == 0
        and counts["artist_image_rows"] == 0
        and counts["artist_image_count"] == 0
    )
    if not artist_side_empty:
        return False

    exhibition_text_count = counts["exhibition_count"]
    exhibition_image_count = counts["exhibition_image_count"]
    return exhibition_text_count > 0 and exhibition_image_count == 0


def is_exhibition_image_only_target_row(row: dict[str, Any]) -> bool:
    counts = extract_target_row_counts(row)
    artist_side_empty = (
        counts["artist_count"] == 0
        and counts["artist_image_rows"] == 0
        and counts["artist_image_count"] == 0
    )
    if not artist_side_empty:
        return False

    exhibition_text_count = counts["exhibition_count"]
    exhibition_image_count = counts["exhibition_image_count"]
    return exhibition_text_count == 0 and exhibition_image_count > 0

def _build_skip_entries_for_predicate(
    *,
    target_gallery_rows: Iterable[dict[str, Any]],
    predicate: Callable[[dict[str, Any]], bool],
    skip_reason: str,
    run_id: str,
    source_scope_file: str,
    detected_at: str | None = None,
    evidence: str = "",
) -> list[SkipGalleryEntry]:
    detected = str(detected_at or "").strip() or utc_now_iso()
    out: list[SkipGalleryEntry] = []
    for row in target_gallery_rows:
        fair_slug = normalize_fair_slug(str(row.get("fair_slug") or ""))
        gallery_name_en = str(row.get("gallery_name_en") or "").strip()
        if not fair_slug or not gallery_name_en:
            continue
        if not predicate(row):
            continue
        out.append(
            SkipGalleryEntry(
                fair_slug=fair_slug,
                gallery_name_en=gallery_name_en,
                skip_reason=str(skip_reason or "").strip(),
                detected_at=detected,
                run_id=str(run_id or "").strip(),
                source_scope_file=str(source_scope_file or "").strip(),
                evidence=str(evidence or "").strip(),
            )
        )
    return out


def build_all_rag_zero_skip_entries(
    *,
    target_gallery_rows: Iterable[dict[str, Any]],
    skip_reason: str,
    run_id: str,
    source_scope_file: str,
    detected_at: str | None = None,
    evidence: str = "",
) -> list[SkipGalleryEntry]:
    return _build_skip_entries_for_predicate(
        target_gallery_rows=target_gallery_rows,
        predicate=is_all_rag_zero_target_row,
        skip_reason=skip_reason,
        run_id=run_id,
        source_scope_file=source_scope_file,
        detected_at=detected_at,
        evidence=evidence,
    )


def build_exhibition_text_only_skip_entries(
    *,
    target_gallery_rows: Iterable[dict[str, Any]],
    skip_reason: str,
    run_id: str,
    source_scope_file: str,
    detected_at: str | None = None,
    evidence: str = "",
) -> list[SkipGalleryEntry]:
    return _build_skip_entries_for_predicate(
        target_gallery_rows=target_gallery_rows,
        predicate=is_exhibition_text_only_target_row,
        skip_reason=skip_reason,
        run_id=run_id,
        source_scope_file=source_scope_file,
        detected_at=detected_at,
        evidence=evidence,
    )


def build_exhibition_image_only_skip_entries(
    *,
    target_gallery_rows: Iterable[dict[str, Any]],
    skip_reason: str,
    run_id: str,
    source_scope_file: str,
    detected_at: str | None = None,
    evidence: str = "",
) -> list[SkipGalleryEntry]:
    return _build_skip_entries_for_predicate(
        target_gallery_rows=target_gallery_rows,
        predicate=is_exhibition_image_only_target_row,
        skip_reason=skip_reason,
        run_id=run_id,
        source_scope_file=source_scope_file,
        detected_at=detected_at,
        evidence=evidence,
    )

