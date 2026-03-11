from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from phase2_art_pulse_config import (
    TARGET_YEAR,
    get_enrichment_current_output_path,
    get_enrichment_current_summary_path,
    get_enrichment_history_dir,
    get_enrichment_scaffold_dirs,
)


def _ensure_dir(path: Path) -> bool:
    existed = path.exists()
    path.mkdir(parents=True, exist_ok=True)
    (path / ".gitkeep").touch(exist_ok=True)
    return not existed


def main() -> int:
    created_dirs = 0
    for scaffold_dir in get_enrichment_scaffold_dirs():
        if _ensure_dir(scaffold_dir):
            created_dirs += 1

    summary = {
        "task": "A2_STORAGE_LAYOUT_SCAFFOLD_01",
        "created_dirs": created_dirs,
        "scaffold_dirs": [str(p) for p in get_enrichment_scaffold_dirs()],
        "current_contract": {
            "artists_output": str(get_enrichment_current_output_path("artists", TARGET_YEAR)),
            "artists_summary": str(get_enrichment_current_summary_path("artists", TARGET_YEAR)),
            "exhibitions_output": str(get_enrichment_current_output_path("exhibitions", TARGET_YEAR)),
            "exhibitions_summary": str(get_enrichment_current_summary_path("exhibitions", TARGET_YEAR)),
        },
        "history_contract": {
            "artists": str(get_enrichment_history_dir("artists")),
            "exhibitions": str(get_enrichment_history_dir("exhibitions")),
        },
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
