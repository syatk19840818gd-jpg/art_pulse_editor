from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AUTO_SYNC_ROOT = Path("data/r2_auto_sync")
AUTO_SYNC_LOG_DIR = AUTO_SYNC_ROOT / "logs"
AUTO_SYNC_STATE_PATH = AUTO_SYNC_ROOT / "auto_sync_state.json"
AUTO_SYNC_LOCK_PATH = AUTO_SYNC_ROOT / "auto_sync.lock"

DELETE_STABILITY_REQUIRED_RUNS = 2


@dataclass(frozen=True)
class TargetConfig:
    name: str
    script: str
    scope: str
    log_dir: Path
    summary_pattern: str
    max_prune: int
    prune_extra_args: tuple[str, ...] = ()


TARGET_CONFIGS: dict[str, TargetConfig] = {
    "phase1_derived": TargetConfig(
        name="phase1_derived",
        script="run_phase1_seed10_r2_sync.py",
        scope="derived",
        log_dir=Path("data/phase1_seed10/logs"),
        summary_pattern="phase1_seed10_r2_sync_derived_*.json",
        max_prune=600,
    ),
    "phase1_all": TargetConfig(
        name="phase1_all",
        script="run_phase1_seed10_r2_sync.py",
        scope="all",
        log_dir=Path("data/phase1_seed10/logs"),
        summary_pattern="phase1_seed10_r2_sync_all_*.json",
        max_prune=600,
    ),
    "tarutani_all": TargetConfig(
        name="tarutani_all",
        script="run_tarutani_r2_sync.py",
        scope="all",
        log_dir=Path("data/Tarutani_data/logs"),
        summary_pattern="tarutani_r2_sync_all_*.json",
        max_prune=100,
        prune_extra_args=("--prune-prefix", "tarutani/source"),
    ),
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def read_json_dict(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _ensure_state_root() -> None:
    AUTO_SYNC_ROOT.mkdir(parents=True, exist_ok=True)
    AUTO_SYNC_LOG_DIR.mkdir(parents=True, exist_ok=True)


def _load_state() -> dict[str, Any]:
    _ensure_state_root()
    state = read_json_dict(AUTO_SYNC_STATE_PATH)
    targets = state.get("targets")
    if not isinstance(targets, dict):
        targets = {}
    state["targets"] = targets
    return state


def _save_state(state: dict[str, Any]) -> None:
    state["updated_at"] = utc_now_iso()
    write_json(AUTO_SYNC_STATE_PATH, state)


def _get_target_state(state: dict[str, Any], target: str) -> dict[str, Any]:
    targets = state.setdefault("targets", {})
    raw = targets.get(target)
    if not isinstance(raw, dict):
        raw = {}
    prune = raw.get("prune")
    if not isinstance(prune, dict):
        prune = {}
    raw["prune"] = prune
    targets[target] = raw
    return raw


def _acquire_lock() -> int | None:
    _ensure_state_root()
    try:
        fd = os.open(str(AUTO_SYNC_LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return None
    os.write(fd, f"{os.getpid()} {utc_now_iso()}".encode("utf-8", "ignore"))
    return fd


def _release_lock(fd: int | None) -> None:
    if fd is None:
        return
    try:
        os.close(fd)
    except OSError:
        pass
    try:
        AUTO_SYNC_LOCK_PATH.unlink(missing_ok=True)
    except OSError:
        pass


def _resolve_latest_summary(log_dir: Path, pattern: str) -> Path | None:
    candidates = sorted(log_dir.glob(pattern))
    if not candidates:
        return None
    return candidates[-1]


def _run_subprocess(cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    stdout_lines = [line for line in (proc.stdout or "").splitlines() if line.strip()]
    stderr_lines = [line for line in (proc.stderr or "").splitlines() if line.strip()]
    return {
        "command": cmd,
        "exit_code": int(proc.returncode),
        "stdout_tail": stdout_lines[-20:],
        "stderr_tail": stderr_lines[-20:],
    }


def _fingerprint_prune_candidates(candidates: list[dict[str, Any]]) -> str:
    if not candidates:
        return ""
    parts: list[str] = []
    for row in candidates:
        key = str(row.get("r2_key") or "")
        size = int(row.get("size_bytes") or 0)
        parts.append(f"{key}|{size}")
    payload = "\n".join(sorted(parts))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _build_sync_command(
    *,
    config: TargetConfig,
    py_exec: str,
    dry_run: bool,
    with_prune: bool,
    require_dry_run_log: bool,
) -> list[str]:
    cmd: list[str] = [py_exec, config.script, "--scope", config.scope]
    if dry_run:
        cmd.append("--dry-run")
    if with_prune:
        cmd.extend(["--prune", *config.prune_extra_args])
    if require_dry_run_log:
        cmd.append("--require-dry-run-log")
    if not dry_run:
        cmd.extend(["--max-prune", str(config.max_prune)])
    return cmd


def _env_auto_sync_enabled() -> bool:
    raw = str(os.getenv("R2_AUTO_SYNC_ENABLED", "1")).strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _lock_wait_seconds() -> int:
    raw = str(os.getenv("R2_AUTO_SYNC_LOCK_WAIT_SECONDS", "30")).strip()
    try:
        value = int(raw)
    except ValueError:
        return 30
    return max(0, min(value, 300))


def auto_sync_after_job(
    *,
    target: str,
    trigger: str,
    strict: bool = False,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "unknown",
        "target": target,
        "trigger": trigger,
        "started_at": utc_now_iso(),
        "finished_at": "",
        "steps": [],
        "dry_run_summary_path": "",
        "apply_summary_path": "",
        "delete_policy": "",
        "prune_candidates_count": 0,
        "prune_stable_hits": 0,
        "prune_ready": False,
    }
    if target not in TARGET_CONFIGS:
        result["status"] = f"invalid_target:{target}"
        result["finished_at"] = utc_now_iso()
        return result
    if not _env_auto_sync_enabled():
        result["status"] = "disabled_by_env"
        result["finished_at"] = utc_now_iso()
        return result

    lock_fd = _acquire_lock()
    if lock_fd is None:
        deadline = time.time() + _lock_wait_seconds()
        while time.time() < deadline:
            time.sleep(1.0)
            lock_fd = _acquire_lock()
            if lock_fd is not None:
                break
    if lock_fd is None:
        result["status"] = "skipped_lock_busy"
        result["finished_at"] = utc_now_iso()
        return result

    config = TARGET_CONFIGS[target]
    py_exec = sys.executable
    state = _load_state()
    target_state = _get_target_state(state, target)

    try:
        dry_cmd = _build_sync_command(
            config=config,
            py_exec=py_exec,
            dry_run=True,
            with_prune=True,
            require_dry_run_log=False,
        )
        dry_step = _run_subprocess(dry_cmd)
        dry_step["name"] = "dry_run_prune"
        result["steps"].append(dry_step)
        if dry_step["exit_code"] != 0:
            result["status"] = "dry_run_failed"
            return result

        dry_summary_path = _resolve_latest_summary(config.log_dir, config.summary_pattern)
        result["dry_run_summary_path"] = dry_summary_path.as_posix() if dry_summary_path else ""
        dry_summary = read_json_dict(dry_summary_path) if dry_summary_path else {}
        prune_candidates = dry_summary.get("prune_candidates")
        if not isinstance(prune_candidates, list):
            prune_candidates = []
        prune_candidates_count = int(dry_summary.get("prune_candidates_count") or len(prune_candidates))
        result["prune_candidates_count"] = prune_candidates_count

        prune_fp = _fingerprint_prune_candidates(prune_candidates)
        prev_prune = target_state.get("prune", {})
        prev_fp = str(prev_prune.get("fingerprint") or "")
        prev_hits = int(prev_prune.get("stable_hits") or 0)

        if prune_candidates_count <= 0:
            stable_hits = 0
            prune_ready = True
            delete_policy = "no_prune_candidates"
        elif prune_fp and prune_fp == prev_fp:
            stable_hits = prev_hits + 1
            prune_ready = stable_hits >= DELETE_STABILITY_REQUIRED_RUNS
            delete_policy = "prune_deferred_until_stable" if not prune_ready else "prune_allowed_stable"
        else:
            stable_hits = 1
            prune_ready = False
            delete_policy = "prune_deferred_first_seen"

        result["prune_stable_hits"] = stable_hits
        result["prune_ready"] = prune_ready
        result["delete_policy"] = delete_policy

        apply_with_prune = prune_ready
        apply_cmd = _build_sync_command(
            config=config,
            py_exec=py_exec,
            dry_run=False,
            with_prune=apply_with_prune,
            require_dry_run_log=True,
        )
        apply_step = _run_subprocess(apply_cmd)
        apply_step["name"] = "apply_guarded_with_prune" if apply_with_prune else "apply_guarded_without_prune"
        result["steps"].append(apply_step)
        if apply_step["exit_code"] != 0:
            result["status"] = "apply_failed"
        else:
            result["status"] = "ok"

        apply_summary_path = _resolve_latest_summary(config.log_dir, config.summary_pattern)
        result["apply_summary_path"] = apply_summary_path.as_posix() if apply_summary_path else ""

        target_state["last_trigger"] = trigger
        target_state["last_run_at"] = utc_now_iso()
        target_state["last_status"] = result["status"]
        target_state["last_delete_policy"] = delete_policy
        target_state["last_prune_candidates_count"] = prune_candidates_count
        target_state["last_dry_run_summary_path"] = result["dry_run_summary_path"]
        target_state["last_apply_summary_path"] = result["apply_summary_path"]
        target_state["prune"] = {
            "fingerprint": prune_fp,
            "stable_hits": stable_hits,
            "candidate_count": prune_candidates_count,
            "last_seen_at": utc_now_iso(),
        }
        _save_state(state)
    except Exception as exc:  # noqa: BLE001
        result["status"] = f"error:{exc}"
        if strict:
            raise
    finally:
        result["finished_at"] = utc_now_iso()
        _release_lock(lock_fd)
        _persist_result_log(result)
    return result


def _persist_result_log(result: dict[str, Any]) -> None:
    _ensure_state_root()
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_target = str(result.get("target") or "unknown").replace("/", "_")
    path = AUTO_SYNC_LOG_DIR / f"r2_auto_sync_{safe_target}_{ts}.json"
    write_json(path, result)
    result["result_log_path"] = path.as_posix()


def format_auto_sync_brief(result: dict[str, Any]) -> str:
    status = str(result.get("status") or "unknown")
    target = str(result.get("target") or "")
    policy = str(result.get("delete_policy") or "")
    cands = int(result.get("prune_candidates_count") or 0)
    hits = int(result.get("prune_stable_hits") or 0)
    return (
        "[AUTO-SYNC] "
        f"target={target} status={status} "
        f"prune_candidates={cands} stable_hits={hits} policy={policy}"
    )
