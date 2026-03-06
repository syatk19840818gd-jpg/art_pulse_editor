#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from tools.required_images_union import (
        DEFAULT_ARTIST_META,
        DEFAULT_EXHIBITIONS_META,
        DEFAULT_IMAGES_ROOT,
        build_required_images_union,
        compute_missing_required,
        count_images_under_root,
    )
except ModuleNotFoundError:
    from required_images_union import (  # type: ignore
        DEFAULT_ARTIST_META,
        DEFAULT_EXHIBITIONS_META,
        DEFAULT_IMAGES_ROOT,
        build_required_images_union,
        compute_missing_required,
        count_images_under_root,
    )

PHASE1_ROOT = Path("data/phase1_seed10")
REPORT_PATH = PHASE1_ROOT / "logs/formal_gate_postflight_report.md"

TARGET_PATHS = [
    PHASE1_ROOT / "raw/artists_frieze_london_2025.jsonl",
    PHASE1_ROOT / "raw/artists_liste_2025.jsonl",
    PHASE1_ROOT / "raw/exhibitions_frieze_london_2025.jsonl",
    PHASE1_ROOT / "raw/exhibitions_liste_2025.jsonl",
    PHASE1_ROOT / "derived/artist_works_images_frieze_london.jsonl",
    PHASE1_ROOT / "derived/artist_works_images_liste.jsonl",
]
OPTIONAL_PATHS = [
    PHASE1_ROOT / "derived/exhibitions_images_frieze_london_2025.jsonl",
    PHASE1_ROOT / "derived/exhibitions_images_liste_2025.jsonl",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _read_jsonl_count(path: Path) -> int:
    count = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                count += 1
    return count


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_postflight_gate(
    *,
    context: str = "default",
    report_path: Path = REPORT_PATH,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    hold_reasons: list[str] = []
    sha_rows: list[dict[str, str]] = []

    all_paths: list[Path] = []
    for p in TARGET_PATHS:
        all_paths.append(p)
    for p in OPTIONAL_PATHS:
        if p.exists():
            all_paths.append(p)

    for p in all_paths:
        if not p.exists():
            hold_reasons.append(f"missing_file:{p}")
            checks.append({"check": f"{p.name}_exists", "status": "HOLD", "detail": str(p)})
            continue
        c = _read_jsonl_count(p)
        status = "PASS" if c > 0 else "HOLD"
        checks.append({"check": f"{p.name}_row_count", "status": status, "detail": c})
        if status == "HOLD":
            hold_reasons.append(f"zero_rows:{p}")
        sha_rows.append({"path": str(p), "sha256": _sha256(p)})

    try:
        union = build_required_images_union(
            exhibitions_meta_paths=DEFAULT_EXHIBITIONS_META,
            artist_meta_paths=DEFAULT_ARTIST_META,
            images_root=DEFAULT_IMAGES_ROOT,
            require_exhibitions=True,
        )
        missing = compute_missing_required(union["union_required"], images_root=DEFAULT_IMAGES_ROOT)
        missing_count = len(missing)
        derived_count = count_images_under_root(DEFAULT_IMAGES_ROOT)
        union_count = union["union_required_count"]

        checks.append(
            {
                "check": "missing_required_count",
                "status": "PASS" if missing_count == 0 else "HOLD",
                "detail": missing_count,
            }
        )
        if missing_count > 0:
            hold_reasons.append(f"missing_required_images:{missing_count}")
        checks.append(
            {
                "check": "union_required_equals_derived_images_count",
                "status": "PASS" if union_count == derived_count else "HOLD",
                "detail": f"union={union_count},derived={derived_count}",
            }
        )
        if union_count != derived_count:
            hold_reasons.append(f"union_count_mismatch:union={union_count},derived={derived_count}")
    except Exception as exc:
        checks.append({"check": "union_required_generation", "status": "HOLD", "detail": repr(exc)})
        hold_reasons.append(f"union_required_generation_failed:{exc}")
        union = None
        missing = []
        missing_count = 0
        union_count = 0
        derived_count = count_images_under_root(DEFAULT_IMAGES_ROOT)

    status = "PASS" if not hold_reasons else "HOLD"
    payload = {
        "task": "TASK_F6_GUARD_01",
        "context": context,
        "executed_at": _now_iso(),
        "status": status,
        "checks": checks,
        "hold_reasons": hold_reasons,
        "sha256_rows": sha_rows,
        "union_counts": {
            "exhibitions_required_count": union["exhibitions_required_count"] if union else None,
            "artist_required_count": union["artist_required_count"] if union else None,
            "union_required_count": union_count,
            "derived_images_count": derived_count,
            "missing_required_count": missing_count,
        },
        "missing_required_examples": missing[:10] if missing else [],
    }

    lines: list[str] = []
    lines.append("# formal postflight gate")
    lines.append("")
    lines.append(f"- context: {context}")
    lines.append(f"- status: {status}")
    lines.append(f"- union_required_count: {union_count}")
    lines.append(f"- derived_images_count: {derived_count}")
    lines.append(f"- missing_required_count: {missing_count}")
    lines.append("")
    lines.append("## Hold reasons")
    if hold_reasons:
        for r in hold_reasons:
            lines.append(f"- {r}")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Checks")
    for c in checks:
        lines.append(f"- {c['check']}: {c['status']} ({c['detail']})")
    lines.append("")
    lines.append("## sha256")
    for r in sha_rows:
        lines.append(f"- {r['path']}: {r['sha256']}")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


def _cli() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", default="manual")
    parser.add_argument("--report-path", default=str(REPORT_PATH))
    args = parser.parse_args()

    result = run_postflight_gate(context=args.context, report_path=Path(args.report_path))
    print(json.dumps({"status": result["status"], "hold_reasons": result["hold_reasons"]}, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(_cli())
