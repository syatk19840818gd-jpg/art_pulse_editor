#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SOURCE_CLI = "run_script_sprawl_guard.py"
DEFAULT_ALLOWLIST_PATH = Path("config/run_script_sprawl_allowlist.json")
HEAVY_TOKENS = ("report", "rollup", "manifest", "retry", "recovery", "chain")
HEAVY_TOKEN_THRESHOLD = 3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Guard against additional run_*.py script-name sprawl."
    )
    parser.add_argument(
        "--allowlist",
        default=str(DEFAULT_ALLOWLIST_PATH),
        help=f"allowlist JSON path (default: {DEFAULT_ALLOWLIST_PATH})",
    )
    parser.add_argument("--output-json", default="", help="optional summary output path")
    return parser.parse_args()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_allowlist(path: Path) -> set[str]:
    if not path.exists():
        return set()
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        return set()
    raw = obj.get("allowed_heavy_scripts")
    if not isinstance(raw, list):
        return set()
    return {str(item).strip() for item in raw if str(item).strip()}


def heavy_token_count(filename: str) -> int:
    lowered = filename.lower()
    return sum(1 for token in HEAVY_TOKENS if token in lowered)


def main() -> int:
    args = parse_args()
    allowlist_path = Path(args.allowlist)
    allowlist = load_allowlist(allowlist_path)

    run_scripts = sorted(Path(".").glob("run_*.py"), key=lambda p: p.name)
    heavy_scripts = [
        p.name for p in run_scripts if heavy_token_count(p.name) >= HEAVY_TOKEN_THRESHOLD
    ]
    unknown_heavy_scripts = [name for name in heavy_scripts if name not in allowlist]

    summary = {
        "source_cli": SOURCE_CLI,
        "allowlist_path": str(allowlist_path.resolve()),
        "run_script_count": len(run_scripts),
        "heavy_script_threshold": HEAVY_TOKEN_THRESHOLD,
        "heavy_script_count": len(heavy_scripts),
        "heavy_scripts": heavy_scripts,
        "unknown_heavy_script_count": len(unknown_heavy_scripts),
        "unknown_heavy_scripts": unknown_heavy_scripts,
        "guard_passed": len(unknown_heavy_scripts) == 0,
    }

    output_path = (
        Path(args.output_json).resolve()
        if args.output_json
        else Path("data/phase1_seed10/logs/run_script_sprawl_guard_summary.json").resolve()
    )
    write_json(output_path, summary)

    print(
        "[SPRAWL_GUARD] "
        f"run_scripts={summary['run_script_count']} "
        f"heavy={summary['heavy_script_count']} "
        f"unknown_heavy={summary['unknown_heavy_script_count']}"
    )
    print(f"[SPRAWL_GUARD] summary={output_path}")
    return 0 if summary["guard_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
