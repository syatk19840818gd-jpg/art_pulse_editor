#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_SEARCH_DIR = Path("data/phase1_seed10/derived/answer")
DEFAULT_GLOB = "artists_answer_qa_smoke_summary_*_cases.jsonl"
SOURCE_CLI = "run_artists_answer_qa_retry_manifest.py"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _resolve_latest_cases_jsonl(search_dir: Path, pattern: str) -> tuple[Path | None, str | None]:
    candidates = [p for p in search_dir.glob(pattern) if p.is_file()]
    if not candidates:
        return None, f"latest_cases_jsonl_not_found:{search_dir}/{pattern}"
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    return latest.resolve(), None


def _load_cases_jsonl(path: Path) -> tuple[list[dict[str, Any]] | None, str | None]:
    if not path.exists():
        return None, f"cases_jsonl_not_found:{path}"

    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                raw = line.strip()
                if not raw:
                    continue
                obj = json.loads(raw)
                if not isinstance(obj, dict):
                    return None, f"cases_jsonl_line_not_object:{line_no}"
                rows.append(obj)
    except json.JSONDecodeError as exc:
        return None, f"cases_jsonl_json_decode_error:{exc}"
    except OSError as exc:
        return None, f"cases_jsonl_os_error:{exc}"

    return rows, None


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        if lowered in {"false", "0", "no", "off"}:
            return False
    return None


def _as_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return str(value)


def _build_retry_manifest(cases: list[dict[str, Any]], input_path: Path) -> dict[str, Any]:
    retry_cases: list[dict[str, Any]] = []
    failed_case_ids: list[str] = []

    for row in cases:
        exit_code = _as_int(row.get("exit_code"))
        if exit_code is not None and exit_code == 0:
            continue

        case_id = _as_optional_str(row.get("case_id")) or ""
        question = _as_optional_str(row.get("question")) or ""
        query = _as_optional_str(row.get("query"))
        context_path = _as_optional_str(row.get("context_path"))

        fail_on_regression = _as_bool(row.get("fail_on_regression_effective"))
        if fail_on_regression is None:
            fail_on_regression = _as_bool(row.get("fail_on_regression"))
        if fail_on_regression is None:
            fail_on_regression = False

        retry_cases.append(
            {
                "case_id": case_id,
                "question": question,
                "query": query,
                "context_path": context_path,
                "fail_on_regression": fail_on_regression,
            }
        )
        failed_case_ids.append(case_id)

    return {
        "generated_at": utc_now_iso(),
        "source_cli": SOURCE_CLI,
        "input_cases_jsonl_path": str(input_path),
        "total_cases": len(cases),
        "failed_cases": len(retry_cases),
        "retry_case_count": len(retry_cases),
        "failed_case_ids": failed_case_ids,
        "cases": retry_cases,
        "notes": [] if retry_cases else ["no_failed_cases_found"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build artists QA retry manifest from batch cases JSONL."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--cases-jsonl", default="", help="path to batch cases JSONL")
    group.add_argument("--latest", action="store_true", help="resolve latest cases JSONL")
    parser.add_argument(
        "--search-dir",
        default=str(DEFAULT_SEARCH_DIR),
        help=f"search directory for --latest (default: {DEFAULT_SEARCH_DIR})",
    )
    parser.add_argument(
        "--glob",
        default=DEFAULT_GLOB,
        help=f"glob for --latest (default: {DEFAULT_GLOB})",
    )
    parser.add_argument("--output-manifest", default="", help="optional output manifest path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.cases_jsonl:
        input_path = Path(args.cases_jsonl).resolve()
    else:
        latest_path, latest_error = _resolve_latest_cases_jsonl(Path(args.search_dir), args.glob)
        if latest_error:
            print(f"[ERROR] {latest_error}")
            return 1
        assert latest_path is not None
        input_path = latest_path

    cases, load_error = _load_cases_jsonl(input_path)
    if load_error:
        print(f"[ERROR] {load_error}")
        return 1
    assert cases is not None

    manifest = _build_retry_manifest(cases, input_path)
    output_path = (
        Path(args.output_manifest).resolve()
        if args.output_manifest
        else input_path.with_name(f"{input_path.stem}_retry_manifest.json")
    )
    write_json(output_path, manifest)

    print(
        "[DONE] retry_manifest_generated "
        f"total_cases={manifest['total_cases']} failed_cases={manifest['failed_cases']}"
    )
    print(f"[DONE] retry_manifest={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
