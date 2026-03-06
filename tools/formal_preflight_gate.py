#!/usr/bin/env python3
from __future__ import annotations

import argparse
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
REPORT_PATH = PHASE1_ROOT / "logs/formal_gate_preflight_report.md"
DEFAULT_MIN_RATIO = 0.80
DEFAULT_MAX_MISSING_KEY_RATIO = 0.05

TARGET_SPECS = [
    {
        "name": "raw_artists_frieze",
        "path": PHASE1_ROOT / "raw/artists_frieze_london_2025.jsonl",
        "required_keys": ["fair_slug", "gallery_name_en", "source_url", "text"],
        "optional": False,
    },
    {
        "name": "raw_artists_liste",
        "path": PHASE1_ROOT / "raw/artists_liste_2025.jsonl",
        "required_keys": ["fair_slug", "gallery_name_en", "source_url", "text"],
        "optional": False,
    },
    {
        "name": "raw_exhibitions_frieze",
        "path": PHASE1_ROOT / "raw/exhibitions_frieze_london_2025.jsonl",
        "required_keys": ["fair_slug", "gallery_name_en", "source_url", "text"],
        "optional": False,
    },
    {
        "name": "raw_exhibitions_liste",
        "path": PHASE1_ROOT / "raw/exhibitions_liste_2025.jsonl",
        "required_keys": ["fair_slug", "gallery_name_en", "source_url", "text"],
        "optional": False,
    },
    {
        "name": "derived_artist_images_frieze",
        "path": PHASE1_ROOT / "derived/artist_works_images_frieze_london.jsonl",
        "required_keys": ["fair_slug", "gallery_name_en", "source_url"],
        "optional": False,
    },
    {
        "name": "derived_artist_images_liste",
        "path": PHASE1_ROOT / "derived/artist_works_images_liste.jsonl",
        "required_keys": ["fair_slug", "gallery_name_en", "source_url"],
        "optional": False,
    },
    {
        "name": "derived_exhibitions_images_frieze",
        "path": PHASE1_ROOT / "derived/exhibitions_images_frieze_london_2025.jsonl",
        "required_keys": ["fair_slug", "gallery_name_en", "source_url", "local_path"],
        "optional": True,
    },
    {
        "name": "derived_exhibitions_images_liste",
        "path": PHASE1_ROOT / "derived/exhibitions_images_liste_2025.jsonl",
        "required_keys": ["fair_slug", "gallery_name_en", "source_url", "local_path"],
        "optional": True,
    },
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _is_missing_value(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, str):
        return not v.strip()
    if isinstance(v, list):
        return len(v) == 0
    return False


def _latest_backup_root() -> Path | None:
    trash_root = PHASE1_ROOT / "_trash"
    if not trash_root.exists():
        return None
    candidates = [
        d
        for d in trash_root.iterdir()
        if d.is_dir() and d.name.startswith("ADOPT_") and (d / "formal_backup").exists()
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: p.name)[-1]


def run_preflight_gate(
    *,
    context: str = "default",
    min_ratio: float = DEFAULT_MIN_RATIO,
    max_missing_key_ratio: float = DEFAULT_MAX_MISSING_KEY_RATIO,
    report_path: Path = REPORT_PATH,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    hold_reasons: list[str] = []

    backup_root = _latest_backup_root()
    backup_formal_root = backup_root / "formal_backup" if backup_root else None

    for spec in TARGET_SPECS:
        path: Path = spec["path"]
        name = spec["name"]
        optional = bool(spec["optional"])
        req_keys = list(spec["required_keys"])

        if not path.exists():
            if optional:
                checks.append({"check": f"{name}_exists", "status": "SKIP", "detail": "optional_missing"})
                continue
            hold_reasons.append(f"required_file_missing:{path}")
            checks.append({"check": f"{name}_exists", "status": "HOLD", "detail": str(path)})
            continue

        rows = _read_jsonl(path)
        row_count = len(rows)
        checks.append({"check": f"{name}_row_count", "status": "PASS" if row_count > 0 else "HOLD", "detail": row_count})
        if row_count == 0:
            hold_reasons.append(f"zero_rows:{path}")

        # missing key ratio
        for key in req_keys:
            miss = 0
            for row in rows:
                if _is_missing_value(row.get(key)):
                    miss += 1
            ratio = (miss / row_count) if row_count else 1.0
            status = "PASS" if ratio <= max_missing_key_ratio else "HOLD"
            checks.append(
                {
                    "check": f"{name}_missing_ratio_{key}",
                    "status": status,
                    "detail": round(ratio, 6),
                }
            )
            if status == "HOLD":
                hold_reasons.append(f"high_missing_ratio:{path}:{key}:{ratio:.6f}")

        # ratio vs backup
        if backup_formal_root:
            rel = path.relative_to(PHASE1_ROOT)
            backup_path = backup_formal_root / rel
            if backup_path.exists():
                backup_rows = _read_jsonl(backup_path)
                backup_count = len(backup_rows)
                if backup_count > 0:
                    ratio = row_count / backup_count
                    status = "PASS" if ratio >= min_ratio else "HOLD"
                    checks.append(
                        {
                            "check": f"{name}_ratio_vs_backup",
                            "status": status,
                            "detail": round(ratio, 6),
                        }
                    )
                    if status == "HOLD":
                        hold_reasons.append(f"sudden_drop_vs_backup:{path}:{ratio:.6f}")
                else:
                    checks.append({"check": f"{name}_ratio_vs_backup", "status": "SKIP", "detail": "backup_zero_rows"})
            else:
                checks.append({"check": f"{name}_ratio_vs_backup", "status": "SKIP", "detail": "backup_not_found"})
        else:
            checks.append({"check": f"{name}_ratio_vs_backup", "status": "SKIP", "detail": "no_backup_root"})

    # D/E: union required + missing + count consistency
    try:
        union = build_required_images_union(
            exhibitions_meta_paths=DEFAULT_EXHIBITIONS_META,
            artist_meta_paths=DEFAULT_ARTIST_META,
            images_root=DEFAULT_IMAGES_ROOT,
            require_exhibitions=True,
        )
        missing = compute_missing_required(union["union_required"], images_root=DEFAULT_IMAGES_ROOT)
        derived_count = count_images_under_root(DEFAULT_IMAGES_ROOT)
        union_count = union["union_required_count"]
        missing_count = len(missing)
        checks.append(
            {
                "check": "union_required_missing_count",
                "status": "PASS" if missing_count == 0 else "HOLD",
                "detail": missing_count,
            }
        )
        if missing_count > 0:
            hold_reasons.append(f"missing_required_images:{missing_count}")
        checks.append(
            {
                "check": "union_required_vs_derived_images_count",
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
        union_count = 0
        derived_count = count_images_under_root(DEFAULT_IMAGES_ROOT)
        missing_count = 0

    status = "PASS" if not hold_reasons else "HOLD"
    payload = {
        "task": "TASK_F6_GUARD_01",
        "context": context,
        "executed_at": _now_iso(),
        "status": status,
        "thresholds": {
            "min_ratio_vs_backup": min_ratio,
            "max_missing_key_ratio": max_missing_key_ratio,
        },
        "checks": checks,
        "hold_reasons": hold_reasons,
        "union_counts": {
            "exhibitions_required_count": union["exhibitions_required_count"] if union else None,
            "artist_required_count": union["artist_required_count"] if union else None,
            "union_required_count": union_count,
            "derived_images_count": derived_count,
            "missing_required_count": missing_count,
        },
        "missing_required_examples": missing[:10] if missing else [],
        "backup_root": str(backup_root) if backup_root else "",
    }

    lines: list[str] = []
    lines.append("# formal preflight gate")
    lines.append("")
    lines.append(f"- context: {context}")
    lines.append(f"- status: {status}")
    lines.append(f"- min_ratio_vs_backup: {min_ratio}")
    lines.append(f"- max_missing_key_ratio: {max_missing_key_ratio}")
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
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


def _cli() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", default="manual")
    parser.add_argument("--min-ratio", type=float, default=DEFAULT_MIN_RATIO)
    parser.add_argument("--max-missing-key-ratio", type=float, default=DEFAULT_MAX_MISSING_KEY_RATIO)
    parser.add_argument("--report-path", default=str(REPORT_PATH))
    args = parser.parse_args()

    result = run_preflight_gate(
        context=args.context,
        min_ratio=args.min_ratio,
        max_missing_key_ratio=args.max_missing_key_ratio,
        report_path=Path(args.report_path),
    )
    print(json.dumps({"status": result["status"], "hold_reasons": result["hold_reasons"]}, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(_cli())
