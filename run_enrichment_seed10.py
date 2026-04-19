#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from enrichment_batch_common import build_requests_runtime_report_path
from phase2_art_pulse_config import TARGET_YEAR, get_enrichment_runtime_requests_path
from run_enrichment_exhibitions_preview import (
    RAW_INPUT_PATHS as CANONICAL_RAW_INPUT_PATHS,
    REQUESTS_OUTPUT_PATH as CANONICAL_REQUESTS_OUTPUT_PATH,
    build_requests as build_canonical_requests,
    write_jsonl,
)

ENRICHMENT_REQUESTS_PATH = get_enrichment_runtime_requests_path("exhibitions", TARGET_YEAR)
ENRICHMENT_SUMMARY_PATH = build_requests_runtime_report_path(
    "exhibitions",
    action="seed10_summary",
    target_year=TARGET_YEAR,
)

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    started_at = utc_now_iso()
    print(f"[START] Post-fetch enrichment seed10 at {started_at}")
    if ENRICHMENT_REQUESTS_PATH != CANONICAL_REQUESTS_OUTPUT_PATH:
        raise RuntimeError(
            "canonical_requests_path_mismatch:"
            f"seed10={ENRICHMENT_REQUESTS_PATH} canonical={CANONICAL_REQUESTS_OUTPUT_PATH}"
        )
    request_rows, canonical_summary = build_canonical_requests()
    ENRICHMENT_REQUESTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(ENRICHMENT_REQUESTS_PATH, request_rows)

    completed_at = utc_now_iso()
    raw_counts_by_fair = dict(canonical_summary.get("raw_records_by_fair") or {})
    raw_records_total = int(canonical_summary.get("raw_records_total") or sum(raw_counts_by_fair.values()))
    summary = {
        "started_at": started_at,
        "completed_at": completed_at,
        "target_year": TARGET_YEAR,
        "raw_input_paths": {k: str(v) for k, v in CANONICAL_RAW_INPUT_PATHS.items()},
        "raw_records_by_fair": raw_counts_by_fair,
        "raw_records_total": raw_records_total,
        "enrichment_candidates_total": len(request_rows),
        "counters": dict(canonical_summary.get("counters") or {}),
        "output_requests_path": str(ENRICHMENT_REQUESTS_PATH),
        "canonical_builder": "run_enrichment_exhibitions_preview.build_requests",
    }
    write_json(ENRICHMENT_SUMMARY_PATH, summary)

    print(
        f"[DONE] Enrichment entry complete. raw_total={summary['raw_records_total']} "
        f"candidates={summary['enrichment_candidates_total']}"
    )
    print(f"[DONE] requests={ENRICHMENT_REQUESTS_PATH}")
    print(f"[DONE] summary={ENRICHMENT_SUMMARY_PATH}")
    print("[SYNC] explicit_current_mirror_only; no automatic R2 sync is triggered by this helper")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
