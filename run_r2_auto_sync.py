#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from r2_auto_sync import TARGET_CONFIGS, auto_sync_after_job, format_auto_sync_brief


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run guarded automatic R2 sync for one target.")
    parser.add_argument("--target", choices=sorted(TARGET_CONFIGS.keys()), required=True)
    parser.add_argument("--trigger", default="manual")
    parser.add_argument("--output-json", default="")
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    result = auto_sync_after_job(target=args.target, trigger=args.trigger, strict=args.strict)
    print(format_auto_sync_brief(result))

    if args.output_json:
        out = Path(args.output_json)
        write_json(out, result)
        print(f"[AUTO-SYNC] summary={out.as_posix()}")

    status = str(result.get("status") or "")
    return 0 if status == "ok" or status.startswith("disabled") or status.startswith("skipped") else 1


if __name__ == "__main__":
    raise SystemExit(main())
