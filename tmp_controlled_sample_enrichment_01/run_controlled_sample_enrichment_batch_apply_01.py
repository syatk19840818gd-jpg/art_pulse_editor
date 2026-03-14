from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import run_enrichment_artists_seed10_apply as artists_apply
import run_enrichment_exhibitions_seed10_apply as exhibitions_apply
from phase2_art_pulse_config import (
    get_enrichment_current_output_path,
    get_enrichment_current_summary_path,
    get_enrichment_history_dir,
)

ROOT = Path("tmp_controlled_sample_enrichment_01")
INPUT_ROOT = ROOT / "inputs"
ARTIFACT_ROOT = ROOT / "artifacts"
REPORT_PATH = ROOT / "controlled_sample_report.json"

TARGET_YEAR = 2025
ARTIST_SAMPLE_HASH = "72951a84d055b363d94691d66262fafb2c3d0ec2ede75e137fc4606852757888"
EXHIBITION_SAMPLE_HASH = "09645512426b5e7dd4efae8404d2ee6d0bb5c3b4542a0775b22399bde0f2bc89"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_signature(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}
    stat = path.stat()
    return {
        "exists": True,
        "size": stat.st_size,
        "sha256": sha256_file(path),
    }


def dir_signature(path: Path) -> dict[str, Any]:
    entries: list[str] = []
    if path.exists():
        for child in sorted(path.glob("*")):
            if child.is_file():
                stat = child.stat()
                entries.append(f"{child.name}|{stat.st_size}|{stat.st_mtime_ns}")
    joined = "\n".join(entries)
    return {
        "exists": path.exists(),
        "file_count": len(entries),
        "digest": hashlib.sha256(joined.encode("utf-8")).hexdigest(),
    }


def snapshot_real_state() -> dict[str, Any]:
    current_paths = {
        "artists_output": get_enrichment_current_output_path("artists", TARGET_YEAR),
        "artists_summary": get_enrichment_current_summary_path("artists", TARGET_YEAR),
        "exhibitions_output": get_enrichment_current_output_path("exhibitions", TARGET_YEAR),
        "exhibitions_summary": get_enrichment_current_summary_path("exhibitions", TARGET_YEAR),
    }
    history_dirs = {
        "artists_history_dir": get_enrichment_history_dir("artists"),
        "exhibitions_history_dir": get_enrichment_history_dir("exhibitions"),
    }
    return {
        "current": {key: file_signature(path) for key, path in current_paths.items()},
        "history": {key: dir_signature(path) for key, path in history_dirs.items()},
    }


def clear_enrichment_fields(row: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(row)
    for key in list(out.keys()):
        if key.startswith("enrich_"):
            out.pop(key, None)
    out["headline_ja"] = ""
    out["summary_ja"] = ""
    return out


def load_sample_source(
    *,
    requests_path: Path,
    raw_path: Path,
    target_hash: str,
    request_id_prefix: str,
) -> dict[str, Any]:
    request_rows = read_jsonl(requests_path)
    raw_rows = read_jsonl(raw_path)
    request_row = next(row for row in request_rows if str(row.get("text_hash") or "") == target_hash)
    raw_row = next(row for row in raw_rows if str(row.get("text_hash") or "") == target_hash)
    sample_request = copy.deepcopy(request_row)
    sample_request["request_id"] = f"{request_id_prefix}_{target_hash[:12]}"
    sample_raw = clear_enrichment_fields(raw_row)
    return {
        "request_row": sample_request,
        "raw_row": sample_raw,
    }


def build_trial_paths(category: str, *, stamp: str, target_year: int, guard_key: str) -> dict[str, Path]:
    base = ARTIFACT_ROOT / category
    runtime = base / "_runtime_guards"
    current = base / "current_blocked"
    return {
        "history_output_path": base / f"{category}_sample_apply_output_{target_year}_{stamp}.jsonl",
        "history_summary_path": base / f"{category}_sample_apply_summary_{target_year}_{stamp}.json",
        "history_manifest_path": base / f"{category}_sample_apply_manifest_{target_year}_{stamp}.json",
        "batch_input_path": base / f"{category}_sample_batch_input_{target_year}_{stamp}.jsonl",
        "current_output_path": current / f"{category}_sample_current_output_{target_year}.jsonl",
        "current_summary_path": current / f"{category}_sample_current_summary_{target_year}.json",
        "guard_state_path": runtime / f"{category}_sample_guard_{target_year}_{guard_key}.json",
        "lock_path": runtime / f"{category}_sample_guard_{target_year}_{guard_key}.lock",
    }


def collect_trial_artifacts(category: str) -> dict[str, Any]:
    base = ARTIFACT_ROOT / category
    summaries = sorted(base.glob(f"{category}_sample_apply_summary_{TARGET_YEAR}_*.json"))
    manifests = sorted(base.glob(f"{category}_sample_apply_manifest_{TARGET_YEAR}_*.json"))
    outputs = sorted(base.glob(f"{category}_sample_apply_output_{TARGET_YEAR}_*.jsonl"))
    guards = sorted((base / "_runtime_guards").glob(f"{category}_sample_guard_{TARGET_YEAR}_*.json"))
    locks = sorted((base / "_runtime_guards").glob(f"{category}_sample_guard_{TARGET_YEAR}_*.lock"))

    summary_path = summaries[-1] if summaries else None
    manifest_path = manifests[-1] if manifests else None
    output_path = outputs[-1] if outputs else None
    guard_path = guards[-1] if guards else None
    lock_path = locks[-1] if locks else None

    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path else {}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path else {}
    output_text = output_path.read_text(encoding="utf-8") if output_path else ""

    return {
        "summary_path": str(summary_path) if summary_path else "",
        "manifest_path": str(manifest_path) if manifest_path else "",
        "output_path": str(output_path) if output_path else "",
        "guard_state_path": str(guard_path) if guard_path else "",
        "lock_path": str(lock_path) if lock_path else "",
        "summary": summary,
        "manifest": manifest,
        "contains_direct_apply_marker": "openai_direct_apply" in output_text,
    }


def run_trial(
    *,
    category: str,
    module: Any,
    request_attr: str,
    raw_attr: str,
    request_path: Path,
    raw_paths: dict[str, Path],
) -> dict[str, Any]:
    original_request_path = getattr(module, request_attr)
    original_raw_paths = getattr(module, raw_attr)
    original_build_paths = module.build_bulk_artifact_paths
    original_validate_promote = module.validate_bulk_promote_summary
    original_promote = module.promote_history_file_to_current
    original_argv = sys.argv[:]

    setattr(module, request_attr, request_path)
    setattr(module, raw_attr, raw_paths)
    module.build_bulk_artifact_paths = lambda cat, stamp, target_year, guard_key: build_trial_paths(  # type: ignore[assignment]
        cat,
        stamp=stamp,
        target_year=target_year,
        guard_key=guard_key,
    )
    module.validate_bulk_promote_summary = lambda summary: (False, "trial_promote_forced_block")  # type: ignore[assignment]

    def _unexpected_promote(history_path: Path, current_path: Path) -> None:
        raise RuntimeError(f"trial_promote_unexpected:{history_path}->{current_path}")

    module.promote_history_file_to_current = _unexpected_promote  # type: ignore[assignment]

    try:
        sys.argv = [f"{category}_controlled_sample"]
        exit_code = int(module.main())
        return {"status": "ok", "exit_code": exit_code, **collect_trial_artifacts(category)}
    except Exception as exc:
        return {"status": "error", "error_type": type(exc).__name__, "error": str(exc), **collect_trial_artifacts(category)}
    finally:
        sys.argv = original_argv
        setattr(module, request_attr, original_request_path)
        setattr(module, raw_attr, original_raw_paths)
        module.build_bulk_artifact_paths = original_build_paths  # type: ignore[assignment]
        module.validate_bulk_promote_summary = original_validate_promote  # type: ignore[assignment]
        module.promote_history_file_to_current = original_promote  # type: ignore[assignment]


def main() -> int:
    if REPORT_PATH.exists():
        raise RuntimeError(f"controlled_sample_already_exists:{REPORT_PATH}")

    ROOT.mkdir(parents=True, exist_ok=True)
    before = snapshot_real_state()

    artist_source = load_sample_source(
        requests_path=Path("data/phase1_seed10/derived/artists_enrichment_requests_2025.jsonl"),
        raw_path=Path("data/phase1_seed10/raw/artists_frieze_london_2025.jsonl"),
        target_hash=ARTIST_SAMPLE_HASH,
        request_id_prefix="trial_artists",
    )
    exhibition_source = load_sample_source(
        requests_path=Path("data/phase1_seed10/derived/exhibitions_enrichment_requests_2025.jsonl"),
        raw_path=Path("data/phase1_seed10/raw/exhibitions_frieze_london_2025.jsonl"),
        target_hash=EXHIBITION_SAMPLE_HASH,
        request_id_prefix="trial_exhibitions",
    )

    artist_request_path = INPUT_ROOT / "artists" / "artists_enrichment_requests_2025.jsonl"
    artist_raw_path = INPUT_ROOT / "artists" / "artists_frieze_london_2025.jsonl"
    exhibition_request_path = INPUT_ROOT / "exhibitions" / "exhibitions_enrichment_requests_2025.jsonl"
    exhibition_raw_path = INPUT_ROOT / "exhibitions" / "exhibitions_frieze_london_2025.jsonl"

    write_jsonl(artist_request_path, [artist_source["request_row"]])
    write_jsonl(artist_raw_path, [artist_source["raw_row"]])
    write_jsonl(exhibition_request_path, [exhibition_source["request_row"]])
    write_jsonl(exhibition_raw_path, [exhibition_source["raw_row"]])

    artists_result = run_trial(
        category="artists",
        module=artists_apply,
        request_attr="REQUESTS_PATH",
        raw_attr="RAW_INPUT_PATHS",
        request_path=artist_request_path,
        raw_paths={"frieze_london": artist_raw_path},
    )
    exhibitions_result = run_trial(
        category="exhibitions",
        module=exhibitions_apply,
        request_attr="REQUESTS_OUTPUT_PATH",
        raw_attr="RAW_INPUT_PATHS",
        request_path=exhibition_request_path,
        raw_paths={"frieze_london": exhibition_raw_path},
    )

    after = snapshot_real_state()
    report = {
        "task": "EMERGENCY_CONTROLLED_SAMPLE_ENRICHMENT_BATCH_APPLY_01",
        "target_year": TARGET_YEAR,
        "selection": {
            "artists": {
                "reason": "short frieze_london artist row with matched request, valid source_url, empty enrichment fields in isolated copy",
                "request_id": artist_source["request_row"]["request_id"],
                "fair_slug": artist_source["request_row"]["fair_slug"],
                "text_hash": artist_source["request_row"]["text_hash"],
                "source_url": artist_source["raw_row"].get("source_url"),
                "text_len": len(str(artist_source["raw_row"].get("text") or "")),
            },
            "exhibitions": {
                "reason": "stable frieze_london exhibition row with matched request, valid source_url, empty enrichment fields in isolated copy",
                "request_id": exhibition_source["request_row"]["request_id"],
                "fair_slug": exhibition_source["request_row"]["fair_slug"],
                "text_hash": exhibition_source["request_row"]["text_hash"],
                "source_url": exhibition_source["raw_row"].get("source_url"),
                "text_len": len(str(exhibition_source["raw_row"].get("text") or "")),
            },
        },
        "before_real_state": before,
        "after_real_state": after,
        "real_state_unchanged": before == after,
        "artists_result": artists_result,
        "exhibitions_result": exhibitions_result,
    }
    write_json(REPORT_PATH, report)

    print(json.dumps(report, ensure_ascii=False))
    if artists_result.get("status") != "ok" or exhibitions_result.get("status") != "ok":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
