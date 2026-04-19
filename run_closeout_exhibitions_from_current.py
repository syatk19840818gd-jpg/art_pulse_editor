#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Retired runner. Use run_block_closeout.py for official closeout flow."
        )
    )
    parser.add_argument(
        "--targets-file",
        default="",
        help="gallery scope CSV to pass to run_block_closeout.py",
    )
    parser.add_argument(
        "--xlsx-path",
        default="",
        help="optional xlsx path to pass to run_block_closeout.py",
    )
    parser.add_argument(
        "--target-year",
        default="",
        help="optional target year to pass to run_block_closeout.py",
    )
    parser.add_argument(
        "--run-id",
        default="",
        help="optional run_id to pass to run_block_closeout.py",
    )
    parser.add_argument(
        "--approval-token",
        default="",
        help="optional approval token for live run_block_closeout.py execution",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="include --apply in the suggested run_block_closeout.py command",
    )
    return parser.parse_args(argv)


def build_mainline_command(args: argparse.Namespace) -> str:
    parts: list[str] = ["python", "run_block_closeout.py", "--targets-file"]
    targets_file = str(args.targets_file or "").strip() or "<path/to/targets.csv>"
    parts.append(targets_file)

    xlsx_path = str(args.xlsx_path or "").strip()
    if xlsx_path:
        parts.extend(["--xlsx-path", xlsx_path])

    target_year = str(args.target_year or "").strip()
    if target_year:
        parts.extend(["--target-year", target_year])

    run_id = str(args.run_id or "").strip()
    if run_id:
        parts.extend(["--run-id", run_id])

    if args.apply:
        parts.append("--apply")
        approval_token = str(args.approval_token or "").strip()
        if approval_token:
            parts.extend(["--approval-token", approval_token])
        else:
            parts.extend(["--approval-token", "<user-approved-note>"])

    return " ".join(parts)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    message_lines = [
        "retired_runner: run_closeout_exhibitions_from_current.py",
        "This exhibition-only closeout runner is retired to prevent old closeout flow usage.",
        "Use the official mainline runner instead:",
        build_mainline_command(args),
    ]
    if args.apply:
        message_lines.append(
            "Note: live execution requires explicit approval token on run_block_closeout.py."
        )
    else:
        message_lines.append("Note: verify-first dry-run remains available on run_block_closeout.py by default.")

    print("\n".join(message_lines), file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
