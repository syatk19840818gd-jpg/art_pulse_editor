#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run guarded R2 sync in fixed order: dry-run(prune) -> "
            "apply(prune+require-dry-run-log+max-prune)."
        )
    )
    parser.add_argument("--dry-run-only", action="store_true", help="run only dry-run steps")
    parser.add_argument("--phase1-scope", default="all", choices=("raw", "derived", "enrichment", "logs", "all"))
    parser.add_argument("--tarutani-scope", default="all", choices=("source", "derived", "logs", "all"))
    parser.add_argument("--phase1-max-prune", type=int, default=600)
    parser.add_argument("--tarutani-max-prune", type=int, default=100)
    parser.add_argument(
        "--no-tarutani-legacy-source-prune",
        action="store_true",
        help="do not include --prune-prefix tarutani/source in tarutani steps",
    )
    parser.add_argument(
        "--output-json",
        default="",
        help="optional output summary path",
    )
    return parser.parse_args()


def run_step(name: str, cmd: list[str]) -> dict[str, Any]:
    print(f"[RUN] {name}: {' '.join(cmd)}")
    proc = subprocess.run(cmd, check=False)
    step = {
        "name": name,
        "command": cmd,
        "exit_code": int(proc.returncode),
        "ok": proc.returncode == 0,
    }
    print(f"[DONE] {name}: exit={proc.returncode}")
    return step


def build_tarutani_prune_prefix(args: argparse.Namespace) -> list[str]:
    if args.no_tarutani_legacy_source_prune:
        return []
    return ["--prune-prefix", "tarutani/source"]


def main() -> int:
    args = parse_args()
    started_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    py = sys.executable
    tarutani_prune_prefix = build_tarutani_prune_prefix(args)
    steps: list[dict[str, Any]] = []

    steps.append(
        run_step(
            "phase1_dry_run_prune",
            [py, "run_phase1_seed10_r2_sync.py", "--scope", args.phase1_scope, "--dry-run", "--prune"],
        )
    )
    steps.append(
        run_step(
            "tarutani_dry_run_prune",
            [py, "run_tarutani_r2_sync.py", "--scope", args.tarutani_scope, "--dry-run", "--prune", *tarutani_prune_prefix],
        )
    )

    if not args.dry_run_only:
        steps.append(
            run_step(
                "phase1_apply_prune_guarded",
                [
                    py,
                    "run_phase1_seed10_r2_sync.py",
                    "--scope",
                    args.phase1_scope,
                    "--prune",
                    "--require-dry-run-log",
                    "--max-prune",
                    str(args.phase1_max_prune),
                ],
            )
        )
        steps.append(
            run_step(
                "tarutani_apply_prune_guarded",
                [
                    py,
                    "run_tarutani_r2_sync.py",
                    "--scope",
                    args.tarutani_scope,
                    "--prune",
                    *tarutani_prune_prefix,
                    "--require-dry-run-log",
                    "--max-prune",
                    str(args.tarutani_max_prune),
                ],
            )
        )

    all_ok = all(bool(step["ok"]) for step in steps)
    completed_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    status = "OK" if all_ok else "PARTIAL_FAIL"

    output_path = (
        Path(args.output_json)
        if args.output_json
        else Path("data/phase1_seed10/logs") / f"r2_sync_runbook_summary_{utc_compact()}.json"
    )
    summary = {
        "artifact_kind": "r2_sync_runbook_summary",
        "schema_name": "r2_sync_runbook_summary",
        "schema_version": "v1",
        "generated_by": "run_r2_sync_runbook.py",
        "started_at": started_at,
        "completed_at": completed_at,
        "status": status,
        "dry_run_only": bool(args.dry_run_only),
        "phase1_scope": args.phase1_scope,
        "tarutani_scope": args.tarutani_scope,
        "phase1_max_prune": args.phase1_max_prune,
        "tarutani_max_prune": args.tarutani_max_prune,
        "tarutani_legacy_source_prune_enabled": not bool(args.no_tarutani_legacy_source_prune),
        "steps": steps,
    }
    write_json(output_path, summary)
    print(f"[DONE] status={status}")
    print(f"[DONE] summary={output_path.as_posix()}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

