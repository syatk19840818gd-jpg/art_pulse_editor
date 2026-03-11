#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from run_enrichment_exhibitions_preview import utc_now_compact, utc_now_iso

from phase2_art_pulse_config import (
    TARGET_YEAR,
    get_enrichment_current_output_path,
    get_enrichment_current_summary_path,
    get_enrichment_history_output_path,
    get_enrichment_history_summary_path,
)

LEGACY_DERIVED_DIR = Path("data/phase1_seed10/derived")
LEGACY_LOGS_DIR = Path("data/phase1_seed10/logs")
DRYRUN_OUTPUT_DIR = Path("data/phase1_seed10/logs")
CATEGORIES = ("artists", "exhibitions")
STAMP_RE = re.compile(r"_(\d{8}T\d{6}Z)\.(jsonl|json)$")


def _extract_stamp(path: Path) -> str:
    match = STAMP_RE.search(path.name)
    return match.group(1) if match else ""


def _read_summary(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _count_jsonl_lines(path: Path) -> int | None:
    try:
        count = 0
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    count += 1
        return count
    except Exception:
        return None


def _evaluate_success(category: str, pair: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if pair["pair_status"] != "paired_ok":
        reasons.append("pair_incomplete")
        return False, reasons
    summary = pair.get("summary_data")
    if not isinstance(summary, dict):
        reasons.append("summary_parse_failed")
        return False, reasons

    total_targeted = int(summary.get("total_targeted") or 0)
    total_applied = int(summary.get("total_applied") or 0)
    output_rows = pair.get("output_row_count")

    if total_targeted <= 0:
        reasons.append("total_targeted_non_positive")
    if total_applied <= 0:
        reasons.append("idempotent_or_no_updates")
    if output_rows is None:
        reasons.append("output_row_count_unreadable")
    elif output_rows != total_targeted:
        reasons.append("output_summary_count_mismatch")

    if category == "artists":
        counters = summary.get("counters") if isinstance(summary.get("counters"), dict) else {}
        if int(counters.get("skipped_target_row_not_found") or 0) > 0:
            reasons.append("target_row_not_found_present")
    elif category == "exhibitions":
        if int(summary.get("error_count") or 0) > 0:
            reasons.append("error_count_positive")

    return len(reasons) == 0, reasons


def _collect_pairs(category: str, target_year: int) -> list[dict[str, Any]]:
    output_glob = f"{category}_enrichment_apply_output_{target_year}_*.jsonl"
    summary_glob = f"{category}_enrichment_apply_summary_{target_year}_*.json"

    outputs = { _extract_stamp(p): p for p in sorted(LEGACY_DERIVED_DIR.glob(output_glob)) if _extract_stamp(p) }
    summaries = { _extract_stamp(p): p for p in sorted(LEGACY_LOGS_DIR.glob(summary_glob)) if _extract_stamp(p) }
    stamps = sorted(set(outputs.keys()) | set(summaries.keys()))

    pairs: list[dict[str, Any]] = []
    for stamp in stamps:
        output_path = outputs.get(stamp)
        summary_path = summaries.get(stamp)
        pair_status = "paired_ok"
        if output_path and not summary_path:
            pair_status = "missing_summary"
        elif summary_path and not output_path:
            pair_status = "missing_output"

        summary_data = _read_summary(summary_path) if summary_path else None
        output_row_count = _count_jsonl_lines(output_path) if output_path else None
        success, success_reasons = _evaluate_success(
            category,
            {
                "pair_status": pair_status,
                "summary_data": summary_data,
                "output_row_count": output_row_count,
            },
        )
        pairs.append(
            {
                "category": category,
                "year": target_year,
                "stamp": stamp,
                "output_path": str(output_path) if output_path else "",
                "summary_path": str(summary_path) if summary_path else "",
                "pair_status": pair_status,
                "output_row_count": output_row_count,
                "summary_data": summary_data,
                "is_success_candidate": success,
                "success_reasons": success_reasons,
            }
        )
    return pairs


def _build_actions_for_category(category: str, target_year: int, pairs: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    success_pairs = [p for p in pairs if p["is_success_candidate"]]
    current_pair = max(success_pairs, key=lambda p: p["stamp"]) if success_pairs else None
    current_stamp = str(current_pair["stamp"]) if current_pair else ""

    actions: list[dict[str, Any]] = []
    for pair in pairs:
        stamp = str(pair["stamp"])
        pair_status = str(pair["pair_status"])
        is_broken = pair_status != "paired_ok"
        if not is_broken and pair.get("summary_data") is None:
            is_broken = True

        for kind in ("output", "summary"):
            source_path = str(pair.get(f"{kind}_path") or "")
            if not source_path:
                continue

            if is_broken:
                actions.append(
                    {
                        "category": category,
                        "year": target_year,
                        "stamp": stamp,
                        "source_legacy_path": source_path,
                        "target_new_path": "",
                        "action": "skip_broken",
                        "reason": ";".join(pair.get("success_reasons") or ["pair_incomplete_or_unreadable"]),
                        "pair_status": pair_status,
                    }
                )
                continue

            history_target = (
                get_enrichment_history_output_path(category, stamp, target_year)
                if kind == "output"
                else get_enrichment_history_summary_path(category, stamp, target_year)
            )
            actions.append(
                {
                    "category": category,
                    "year": target_year,
                    "stamp": stamp,
                    "source_legacy_path": source_path,
                    "target_new_path": str(history_target),
                    "action": "history_copy",
                    "reason": "retain_legacy_timestamp_as_history",
                    "pair_status": pair_status,
                }
            )

            if stamp == current_stamp:
                current_target = (
                    get_enrichment_current_output_path(category, target_year)
                    if kind == "output"
                    else get_enrichment_current_summary_path(category, target_year)
                )
                actions.append(
                    {
                        "category": category,
                        "year": target_year,
                        "stamp": stamp,
                        "source_legacy_path": source_path,
                        "target_new_path": str(current_target),
                        "action": "seed_current_copy",
                        "reason": "latest_success_pair_selected_for_initial_current",
                        "pair_status": pair_status,
                    }
                )

    current_candidate = {
        "category": category,
        "year": target_year,
        "stamp": current_stamp,
        "output_path": str(current_pair["output_path"]) if current_pair else "",
        "summary_path": str(current_pair["summary_path"]) if current_pair else "",
        "selection_rule": "latest_success_pair",
    }
    return actions, current_candidate


def main() -> int:
    target_year = TARGET_YEAR
    started_at = utc_now_iso()
    stamp = utc_now_compact()

    all_pairs: list[dict[str, Any]] = []
    all_actions: list[dict[str, Any]] = []
    current_candidates: list[dict[str, Any]] = []

    for category in CATEGORIES:
        pairs = _collect_pairs(category, target_year)
        actions, current_candidate = _build_actions_for_category(category, target_year, pairs)
        all_pairs.extend(pairs)
        all_actions.extend(actions)
        current_candidates.append(current_candidate)

    action_counts = dict(Counter(str(a.get("action") or "") for a in all_actions))
    pair_counts = dict(Counter(str(p.get("pair_status") or "") for p in all_pairs))

    plan = {
        "task": "A4_MIGRATION_PLAN_AND_DRYRUN_01",
        "mode": "dry_run_only",
        "started_at": started_at,
        "completed_at": utc_now_iso(),
        "target_year": target_year,
        "legacy_roots": {
            "derived": str(LEGACY_DERIVED_DIR),
            "logs": str(LEGACY_LOGS_DIR),
        },
        "new_contract_roots": {
            "current": "data/current/enrichment/",
            "history_artists": "data/history/enrichment/artists/",
            "history_exhibitions": "data/history/enrichment/exhibitions/",
        },
        "selection_rules": {
            "current": "latest success pair (output+summary paired, summary parse ok, total_targeted>0, total_applied>0, output rows match total_targeted; artists also require skipped_target_row_not_found=0; exhibitions require error_count=0)",
            "history": "all paired legacy timestamp artifacts are history_copy candidates; broken/incomplete pairs are skip_broken in dry-run classification",
        },
        "execution_runbook_for_next_task": [
            "copy selected pair files to history targets first",
            "verify history copies and checksums",
            "copy selected current seed pair to current fixed paths",
            "verify current files are readable and pair-consistent",
            "keep all legacy files untouched until post-check completion",
        ],
        "rollback_note": "if migration execution fails in next task, remove only newly copied files under data/current and data/history; keep legacy files as source of truth",
        "pair_counts": pair_counts,
        "action_counts": action_counts,
        "pairs": all_pairs,
        "current_candidates": current_candidates,
        "actions": all_actions,
    }

    DRYRUN_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = DRYRUN_OUTPUT_DIR / f"enrichment_migration_dryrun_{target_year}_{stamp}.json"
    latest_path = DRYRUN_OUTPUT_DIR / f"enrichment_migration_dryrun_{target_year}_latest.json"
    output_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    latest_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"[DONE] dryrun_output={output_path}")
    print(f"[DONE] dryrun_latest={latest_path}")
    print(f"[DONE] action_counts={action_counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
