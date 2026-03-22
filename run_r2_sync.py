#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

R2_ALIAS = {
    "R2_ENDPOINT": ["R2_ENDPOINT", "R2_ENDPOINT_URL", "R2_S3_ENDPOINT"],
    "R2_BUCKET": ["R2_BUCKET"],
    "R2_ACCESS_KEY_ID": ["R2_ACCESS_KEY_ID"],
    "R2_SECRET_ACCESS_KEY": ["R2_SECRET_ACCESS_KEY"],
    "R2_REGION": ["R2_REGION"],
}

DEFAULT_CONFIG = Path("config/r2_sync_targets.json")
DEFAULT_LOG_DIR = Path("data/phase1_seed10/logs")
COMMANDS = {"plan", "apply-upload", "apply-prune"}


@dataclass(frozen=True)
class ScopeTarget:
    local_root: Path
    r2_prefix: str
    include_globs: tuple[str, ...]
    exclude_globs: tuple[str, ...]


@dataclass(frozen=True)
class ScopeConfig:
    name: str
    description: str
    enabled_by_default: bool
    prune_allowed: bool
    targets: tuple[ScopeTarget, ...]


@dataclass(frozen=True)
class LocalObject:
    local_path: Path
    repo_rel_path: str
    rel_path: str
    r2_key: str
    size_bytes: int
    mtime_ns: int


@dataclass(frozen=True)
class RemoteObject:
    key: str
    size_bytes: int
    etag: str


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def utc_timestamp_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def get_env_value(key: str, default: str | None = None) -> str | None:
    for alias in R2_ALIAS.get(key, [key]):
        value = os.getenv(alias)
        if value:
            return value
    return default


def build_r2_client() -> tuple[Any, str]:
    load_dotenv()

    endpoint = get_env_value("R2_ENDPOINT")
    bucket = get_env_value("R2_BUCKET")
    access_key = get_env_value("R2_ACCESS_KEY_ID")
    secret_key = get_env_value("R2_SECRET_ACCESS_KEY")
    region = get_env_value("R2_REGION", "auto")

    missing = [
        key
        for key, value in {
            "R2_ENDPOINT": endpoint,
            "R2_BUCKET": bucket,
            "R2_ACCESS_KEY_ID": access_key,
            "R2_SECRET_ACCESS_KEY": secret_key,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(f"Missing R2 env vars: {', '.join(missing)}")

    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
    )
    return client, str(bucket)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_etag(raw: str | None) -> str:
    if not raw:
        return ""
    return raw.strip().strip('"')


def hash_dict(payload: dict[str, Any]) -> str:
    return sha256_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def to_posix(path: Path) -> str:
    return path.as_posix().replace("\\", "/")


def glob_any(path_value: str, patterns: tuple[str, ...]) -> bool:
    if not patterns:
        return False
    for pattern in patterns:
        if fnmatch.fnmatchcase(path_value, pattern):
            return True
        # Keep root-level files matched when include pattern is "**/*".
        if pattern.startswith("**/") and fnmatch.fnmatchcase(path_value, pattern[3:]):
            return True
    return False


def should_include_scope_path(
    *,
    rel_path: str,
    repo_rel_path: str,
    include_globs: tuple[str, ...],
    exclude_globs: tuple[str, ...],
    global_excludes: tuple[str, ...],
) -> bool:
    if include_globs and not glob_any(rel_path, include_globs):
        return False
    if glob_any(rel_path, exclude_globs):
        return False
    if glob_any(repo_rel_path, global_excludes) or glob_any(rel_path, global_excludes):
        return False
    return True


def load_scope_config(config_path: Path) -> tuple[dict[str, ScopeConfig], tuple[str, ...], dict[str, Any]]:
    raw = read_json(config_path)
    if not isinstance(raw, dict):
        raise RuntimeError(f"Invalid config root: {config_path.as_posix()}")

    global_excludes_raw = raw.get("global_exclude_globs", [])
    if not isinstance(global_excludes_raw, list):
        raise RuntimeError("global_exclude_globs must be list[str]")
    global_excludes = tuple(str(x) for x in global_excludes_raw)

    scopes_raw = raw.get("scopes", {})
    if not isinstance(scopes_raw, dict):
        raise RuntimeError("scopes must be object")

    scopes: dict[str, ScopeConfig] = {}
    for scope_name, scope_obj in scopes_raw.items():
        if not isinstance(scope_obj, dict):
            raise RuntimeError(f"scope must be object: {scope_name}")
        targets_raw = scope_obj.get("targets", [])
        if not isinstance(targets_raw, list) or not targets_raw:
            raise RuntimeError(f"scope targets missing: {scope_name}")

        targets: list[ScopeTarget] = []
        for row in targets_raw:
            if not isinstance(row, dict):
                raise RuntimeError(f"scope target must be object: {scope_name}")
            local_root = Path(str(row.get("local_root", "")))
            r2_prefix = str(row.get("r2_prefix", "")).strip().strip("/")
            include_globs = tuple(str(x) for x in row.get("include_globs", ["**/*"]))
            exclude_globs = tuple(str(x) for x in row.get("exclude_globs", []))
            if not local_root.as_posix():
                raise RuntimeError(f"local_root missing in scope={scope_name}")
            if not r2_prefix:
                raise RuntimeError(f"r2_prefix missing in scope={scope_name}")
            targets.append(
                ScopeTarget(
                    local_root=local_root,
                    r2_prefix=r2_prefix,
                    include_globs=include_globs,
                    exclude_globs=exclude_globs,
                )
            )

        scopes[scope_name] = ScopeConfig(
            name=scope_name,
            description=str(scope_obj.get("description", "")).strip(),
            enabled_by_default=bool(scope_obj.get("enabled_by_default", True)),
            prune_allowed=bool(scope_obj.get("prune_allowed", True)),
            targets=tuple(targets),
        )

    return scopes, global_excludes, raw


def collect_local_objects(
    *,
    scope: ScopeConfig,
    global_excludes: tuple[str, ...],
) -> tuple[list[LocalObject], dict[str, Any]]:
    objects: list[LocalObject] = []
    dedup_r2_keys: dict[str, str] = {}
    roots_missing: list[str] = []

    for target in scope.targets:
        root = target.local_root
        if not root.exists():
            roots_missing.append(to_posix(root))
            continue
        if not root.is_dir():
            raise RuntimeError(f"local_root_not_dir:{to_posix(root)}")

        for path in sorted(root.rglob("*"), key=lambda p: p.as_posix()):
            if not path.is_file():
                continue

            repo_rel = to_posix(path)
            rel = path.relative_to(root).as_posix()

            if not should_include_scope_path(
                rel_path=rel,
                repo_rel_path=repo_rel,
                include_globs=target.include_globs,
                exclude_globs=target.exclude_globs,
                global_excludes=global_excludes,
            ):
                continue

            r2_key = f"{target.r2_prefix}/{rel}".replace("//", "/")
            if r2_key in dedup_r2_keys:
                prev_path = dedup_r2_keys[r2_key]
                raise RuntimeError(f"r2_key_collision:{r2_key} prev={prev_path} now={repo_rel}")
            dedup_r2_keys[r2_key] = repo_rel

            stat = path.stat()
            objects.append(
                LocalObject(
                    local_path=path,
                    repo_rel_path=repo_rel,
                    rel_path=rel,
                    r2_key=r2_key,
                    size_bytes=int(stat.st_size),
                    mtime_ns=int(stat.st_mtime_ns),
                )
            )

    objects.sort(key=lambda row: row.r2_key)
    stats = {
        "roots_missing": roots_missing,
        "local_count": len(objects),
        "local_total_size_bytes": sum(obj.size_bytes for obj in objects),
    }
    return objects, stats


def list_remote_objects(
    *,
    client: Any,
    bucket: str,
    scope: ScopeConfig,
    global_excludes: tuple[str, ...],
) -> dict[str, RemoteObject]:
    remote: dict[str, RemoteObject] = {}
    paginator = client.get_paginator("list_objects_v2")

    for target in scope.targets:
        clean_prefix = target.r2_prefix.rstrip("/")
        if not clean_prefix:
            continue
        for page in paginator.paginate(Bucket=bucket, Prefix=f"{clean_prefix}/"):
            for obj in page.get("Contents", []):
                key = str(obj.get("Key", ""))
                if not key:
                    continue
                rel = key[len(clean_prefix) + 1 :] if key.startswith(f"{clean_prefix}/") else ""
                if not rel:
                    continue
                repo_rel = f"{to_posix(target.local_root)}/{rel}"
                if not should_include_scope_path(
                    rel_path=rel,
                    repo_rel_path=repo_rel,
                    include_globs=target.include_globs,
                    exclude_globs=target.exclude_globs,
                    global_excludes=global_excludes,
                ):
                    continue
                remote[key] = RemoteObject(
                    key=key,
                    size_bytes=int(obj.get("Size", 0)),
                    etag=normalize_etag(str(obj.get("ETag", ""))),
                )
    return remote


def build_plan(
    *,
    local_objects: list[LocalObject],
    remote_objects: dict[str, RemoteObject],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    local_by_key = {row.r2_key: row for row in local_objects}

    unchanged: list[dict[str, Any]] = []
    would_upload: list[dict[str, Any]] = []
    would_prune: list[dict[str, Any]] = []

    for key, local_obj in sorted(local_by_key.items()):
        remote_obj = remote_objects.get(key)
        if remote_obj is None:
            would_upload.append(
                {
                    "r2_key": key,
                    "reason": "REMOTE_MISSING",
                    "size_bytes": local_obj.size_bytes,
                    "local_path": local_obj.repo_rel_path,
                }
            )
            continue
        if remote_obj.size_bytes != local_obj.size_bytes:
            would_upload.append(
                {
                    "r2_key": key,
                    "reason": "SIZE_MISMATCH",
                    "size_bytes": local_obj.size_bytes,
                    "remote_size_bytes": remote_obj.size_bytes,
                    "local_path": local_obj.repo_rel_path,
                }
            )
            continue
        unchanged.append(
            {
                "r2_key": key,
                "size_bytes": local_obj.size_bytes,
                "local_path": local_obj.repo_rel_path,
            }
        )

    for key, remote_obj in sorted(remote_objects.items()):
        if key in local_by_key:
            continue
        would_prune.append(
            {
                "r2_key": key,
                "reason": "REMOTE_ONLY_NOT_IN_LOCAL_SCOPE",
                "size_bytes": remote_obj.size_bytes,
                "etag": remote_obj.etag,
            }
        )

    return unchanged, would_upload, would_prune


def fingerprint_scope(scope: ScopeConfig, global_excludes: tuple[str, ...]) -> str:
    payload = {
        "scope": scope.name,
        "enabled_by_default": scope.enabled_by_default,
        "prune_allowed": scope.prune_allowed,
        "targets": [
            {
                "local_root": to_posix(target.local_root),
                "r2_prefix": target.r2_prefix,
                "include_globs": list(target.include_globs),
                "exclude_globs": list(target.exclude_globs),
            }
            for target in scope.targets
        ],
        "global_excludes": list(global_excludes),
    }
    return hash_dict(payload)


def fingerprint_input(scope_name: str, local_objects: list[LocalObject]) -> str:
    lines = [
        f"{scope_name}|{row.r2_key}|{row.size_bytes}|{row.mtime_ns}"
        for row in local_objects
    ]
    return sha256_text("\n".join(lines))


def fingerprint_code(config_path: Path) -> str:
    payload = {
        "run_r2_sync.py": sha256_file(Path(__file__)),
        "config": sha256_file(config_path),
    }
    return hash_dict(payload)


def fingerprint_prune_candidates(candidates: list[dict[str, Any]]) -> str:
    lines = [f"{row.get('r2_key', '')}|{int(row.get('size_bytes', 0))}" for row in candidates]
    return sha256_text("\n".join(sorted(lines)))


def resolve_latest_plan_log(log_dir: Path, scope_name: str, exclude_path: Path | None = None) -> Path | None:
    pattern = f"r2_sync_plan_{scope_name}_*.json"
    candidates = sorted(log_dir.glob(pattern))
    if exclude_path is not None:
        candidates = [path for path in candidates if path.resolve() != exclude_path.resolve()]
    if not candidates:
        return None
    return candidates[-1]


def validate_apply_flag(args: argparse.Namespace) -> None:
    if not getattr(args, "apply", False):
        raise RuntimeError("apply_requires_flag: use --apply to execute write/delete operations")
    if not str(getattr(args, "run_id", "")).strip():
        raise RuntimeError("apply_requires_run_id: use --run-id <ID>")


def append_operation_log(path: Path, payload: dict[str, Any]) -> None:
    write_json(path, payload)


def run_plan(
    *,
    scope: ScopeConfig,
    global_excludes: tuple[str, ...],
    config_path: Path,
    log_dir: Path,
    run_id: str,
    command: str,
) -> tuple[dict[str, Any], list[LocalObject], list[dict[str, Any]], list[dict[str, Any]], str]:
    client, bucket = build_r2_client()
    local_objects, local_stats = collect_local_objects(scope=scope, global_excludes=global_excludes)
    remote_objects = list_remote_objects(
        client=client,
        bucket=bucket,
        scope=scope,
        global_excludes=global_excludes,
    )
    unchanged, would_upload, would_prune = build_plan(
        local_objects=local_objects,
        remote_objects=remote_objects,
    )

    scope_hash = fingerprint_scope(scope, global_excludes)
    input_fingerprint = fingerprint_input(scope.name, local_objects)
    code_fingerprint = fingerprint_code(config_path)
    prune_candidates_fingerprint = fingerprint_prune_candidates(would_prune)

    payload = {
        "artifact_kind": "r2_sync_plan",
        "schema_version": "v1",
        "generated_at": utc_now_iso(),
        "command": command,
        "scope": scope.name,
        "description": scope.description,
        "enabled_by_default": scope.enabled_by_default,
        "prune_allowed": scope.prune_allowed,
        "run_id": run_id,
        "bucket_env_key": "R2_BUCKET",
        "bucket": bucket,
        "local_stats": local_stats,
        "remote_scanned_count": len(remote_objects),
        "unchanged_count": len(unchanged),
        "would_upload_count": len(would_upload),
        "would_prune_count": len(would_prune),
        "scope_hash": scope_hash,
        "input_fingerprint": input_fingerprint,
        "code_fingerprint": code_fingerprint,
        "prune_candidates_fingerprint": prune_candidates_fingerprint,
        "targets": [
            {
                "local_root": to_posix(target.local_root),
                "r2_prefix": target.r2_prefix,
                "include_globs": list(target.include_globs),
                "exclude_globs": list(target.exclude_globs),
            }
            for target in scope.targets
        ],
        "would_upload": would_upload,
        "would_prune": would_prune,
    }

    log_dir.mkdir(parents=True, exist_ok=True)
    plan_path = log_dir / f"r2_sync_plan_{scope.name}_{run_id}.json"
    write_json(plan_path, payload)
    payload["plan_log_path"] = plan_path.as_posix()
    return payload, local_objects, would_upload, would_prune, prune_candidates_fingerprint


def apply_upload(
    *,
    client: Any,
    bucket: str,
    local_by_key: dict[str, LocalObject],
    would_upload: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    uploaded: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []

    for row in would_upload:
        key = str(row.get("r2_key", ""))
        local_obj = local_by_key.get(key)
        if not key or local_obj is None:
            failed.append(
                {
                    "r2_key": key,
                    "local_path": str(row.get("local_path", "")),
                    "error": "local_object_not_found",
                }
            )
            continue

        try:
            local_sha256 = sha256_file(local_obj.local_path)
            with local_obj.local_path.open("rb") as handle:
                client.put_object(
                    Bucket=bucket,
                    Key=key,
                    Body=handle,
                    Metadata={"sha256": local_sha256},
                )
            uploaded.append(
                {
                    "r2_key": key,
                    "local_path": local_obj.repo_rel_path,
                    "size_bytes": local_obj.size_bytes,
                    "sha256": local_sha256,
                }
            )
        except Exception as exc:  # noqa: BLE001
            failed.append(
                {
                    "r2_key": key,
                    "local_path": local_obj.repo_rel_path,
                    "error": str(exc),
                }
            )

    return uploaded, failed


def apply_prune(
    *,
    client: Any,
    bucket: str,
    would_prune: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    deleted: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []

    for idx in range(0, len(would_prune), 1000):
        batch = would_prune[idx : idx + 1000]
        objects = [{"Key": str(row["r2_key"])} for row in batch]
        try:
            resp = client.delete_objects(
                Bucket=bucket,
                Delete={"Objects": objects, "Quiet": False},
            )
            failed_keys: set[str] = set()
            for err in resp.get("Errors", []):
                key = str(err.get("Key", ""))
                code = str(err.get("Code", ""))
                msg = str(err.get("Message", ""))
                failed.append({"r2_key": key, "error": f"{code}:{msg}"})
                if key:
                    failed_keys.add(key)
            for item in resp.get("Deleted", []):
                key = str(item.get("Key", ""))
                if key and key not in failed_keys:
                    deleted.append({"r2_key": key})
        except Exception as exc:  # noqa: BLE001
            for row in batch:
                failed.append({"r2_key": str(row.get("r2_key", "")), "error": str(exc)})

    return deleted, failed


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] not in COMMANDS:
        argv = ["plan", *argv]

    parser = argparse.ArgumentParser(
        description=(
            "Unified R2 sync CLI. Default command is plan (dry-run). "
            "Write/delete operations require explicit safety flags."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common(common_parser: argparse.ArgumentParser) -> None:
        common_parser.add_argument(
            "--scope",
            action="append",
            default=[],
            help=(
                "Scope name defined in config/r2_sync_targets.json. "
                "Repeatable. For plan, omitted means enabled_by_default scopes."
            ),
        )
        common_parser.add_argument(
            "--config",
            type=Path,
            default=DEFAULT_CONFIG,
            help=f"Scope config path (default: {DEFAULT_CONFIG.as_posix()})",
        )
        common_parser.add_argument(
            "--log-dir",
            type=Path,
            default=DEFAULT_LOG_DIR,
            help=f"Plan/apply log directory (default: {DEFAULT_LOG_DIR.as_posix()})",
        )
        common_parser.add_argument("--run-id", default="", help="Run identifier. Required for apply commands.")

    p_plan = subparsers.add_parser("plan", help="Build sync plan only (default command).")
    add_common(p_plan)

    p_upload = subparsers.add_parser("apply-upload", help="Apply uploads only (no prune).")
    add_common(p_upload)
    p_upload.add_argument("--apply", action="store_true", help="Required confirmation flag for write operation.")

    p_prune = subparsers.add_parser("apply-prune", help="Apply R2 prune only (delete remote-only objects).")
    add_common(p_prune)
    p_prune.add_argument("--apply", action="store_true", help="Required confirmation flag for delete operation.")
    p_prune.add_argument(
        "--confirm-prune",
        action="store_true",
        help="Second confirmation flag required for delete operation.",
    )
    p_prune.add_argument(
        "--max-prune",
        type=int,
        required=True,
        help="Maximum allowed prune candidates. Command aborts when exceeded.",
    )

    return parser.parse_args(argv)


def main() -> int:
    args = parse_args()
    command = str(args.command)
    run_id = str(args.run_id or "").strip() or f"{command}_{utc_timestamp_compact()}"

    scopes, global_excludes, _raw_config = load_scope_config(args.config)
    requested_scopes = list(dict.fromkeys([str(s).strip() for s in (args.scope or []) if str(s).strip()]))
    if not requested_scopes:
        if command == "plan":
            requested_scopes = [
                scope_name for scope_name, scope_cfg in scopes.items() if scope_cfg.enabled_by_default
            ]
            if not requested_scopes:
                raise RuntimeError("no_enabled_by_default_scopes_defined")
        else:
            raise RuntimeError(f"{command}_requires_scope_explicit: use --scope <name>")

    unknown_scopes = [scope_name for scope_name in requested_scopes if scope_name not in scopes]
    if unknown_scopes:
        scope_csv = ", ".join(sorted(scopes.keys()))
        raise RuntimeError(f"unknown_scope:{','.join(unknown_scopes)} available=[{scope_csv}]")

    if command == "plan":
        for scope_name in requested_scopes:
            scope = scopes[scope_name]
            scope_run_id = run_id if len(requested_scopes) == 1 else f"{run_id}_{scope_name}"
            plan_payload, _local_objects, would_upload, would_prune, _prune_fp = run_plan(
                scope=scope,
                global_excludes=global_excludes,
                config_path=args.config,
                log_dir=args.log_dir,
                run_id=scope_run_id,
                command=command,
            )
            print(
                "[PLAN] "
                f"scope={scope.name} run_id={scope_run_id} "
                f"would_upload={len(would_upload)} would_prune={len(would_prune)} "
                f"log={plan_payload['plan_log_path']}"
            )
        return 0

    if len(requested_scopes) != 1:
        raise RuntimeError(f"{command}_requires_single_scope")
    scope = scopes[requested_scopes[0]]

    plan_payload, local_objects, would_upload, would_prune, prune_fp = run_plan(
        scope=scope,
        global_excludes=global_excludes,
        config_path=args.config,
        log_dir=args.log_dir,
        run_id=run_id,
        command=command,
    )

    print(
        "[PLAN] "
        f"scope={scope.name} run_id={run_id} "
        f"would_upload={len(would_upload)} would_prune={len(would_prune)} "
        f"log={plan_payload['plan_log_path']}"
    )

    validate_apply_flag(args)

    client, bucket = build_r2_client()
    local_by_key = {row.r2_key: row for row in local_objects}

    if command == "apply-upload":
        uploaded, failed = apply_upload(
            client=client,
            bucket=bucket,
            local_by_key=local_by_key,
            would_upload=would_upload,
        )
        payload = {
            "artifact_kind": "r2_sync_apply_upload",
            "schema_version": "v1",
            "generated_at": utc_now_iso(),
            "scope": scope.name,
            "run_id": run_id,
            "bucket": bucket,
            "plan_log_path": plan_payload["plan_log_path"],
            "would_upload_count": len(would_upload),
            "uploaded_count": len(uploaded),
            "failed_count": len(failed),
            "uploaded": uploaded,
            "failed": failed,
        }
        log_path = args.log_dir / f"r2_sync_apply_upload_{scope.name}_{run_id}.json"
        append_operation_log(log_path, payload)
        print(
            "[APPLY-UPLOAD] "
            f"scope={scope.name} run_id={run_id} uploaded={len(uploaded)} failed={len(failed)} "
            f"log={log_path.as_posix()}"
        )
        return 0 if not failed else 2

    if command == "apply-prune":
        if not scope.prune_allowed:
            raise RuntimeError(
                f"prune_forbidden_for_scope:{scope.name}. "
                "This scope is GitHub source-of-truth; prune is disabled. "
                "Use apply-upload only when explicitly needed."
            )
        if not bool(args.confirm_prune):
            raise RuntimeError("apply-prune requires --confirm-prune")
        if int(args.max_prune) < 0:
            raise RuntimeError("--max-prune must be >= 0")
        if len(would_prune) > int(args.max_prune):
            raise RuntimeError(
                f"max_prune_exceeded: candidates={len(would_prune)} max_prune={int(args.max_prune)}"
            )

        current_plan_path = Path(str(plan_payload["plan_log_path"]))
        previous_plan_path = resolve_latest_plan_log(
            log_dir=args.log_dir,
            scope_name=scope.name,
            exclude_path=current_plan_path,
        )
        stability = {
            "required_runs": 2,
            "ok": False,
            "reason": "",
            "previous_plan_log": previous_plan_path.as_posix() if previous_plan_path else "",
            "previous_prune_candidates_fingerprint": "",
            "current_prune_candidates_fingerprint": prune_fp,
            "current_prune_candidates_count": len(would_prune),
        }

        if len(would_prune) == 0:
            stability["ok"] = True
            stability["reason"] = "no_prune_candidates"
        elif previous_plan_path is None:
            stability["ok"] = False
            stability["reason"] = "previous_plan_log_not_found"
        else:
            previous_payload = read_json(previous_plan_path)
            prev_scope = str(previous_payload.get("scope", ""))
            prev_fp = str(previous_payload.get("prune_candidates_fingerprint", ""))
            stability["previous_prune_candidates_fingerprint"] = prev_fp
            if prev_scope != scope.name:
                stability["ok"] = False
                stability["reason"] = f"previous_scope_mismatch:{prev_scope}"
            elif prev_fp != prune_fp:
                stability["ok"] = False
                stability["reason"] = "prune_candidates_not_stable_two_runs"
            else:
                stability["ok"] = True
                stability["reason"] = "ok"

        if not stability["ok"]:
            payload = {
                "artifact_kind": "r2_sync_apply_prune_blocked",
                "schema_version": "v1",
                "generated_at": utc_now_iso(),
                "scope": scope.name,
                "run_id": run_id,
                "plan_log_path": plan_payload["plan_log_path"],
                "stability": stability,
                "would_prune_count": len(would_prune),
            }
            log_path = args.log_dir / f"r2_sync_apply_prune_{scope.name}_{run_id}.json"
            append_operation_log(log_path, payload)
            raise RuntimeError(f"prune_blocked:{stability['reason']} log={log_path.as_posix()}")

        deleted, failed = apply_prune(
            client=client,
            bucket=bucket,
            would_prune=would_prune,
        )
        payload = {
            "artifact_kind": "r2_sync_apply_prune",
            "schema_version": "v1",
            "generated_at": utc_now_iso(),
            "scope": scope.name,
            "run_id": run_id,
            "bucket": bucket,
            "plan_log_path": plan_payload["plan_log_path"],
            "stability": stability,
            "would_prune_count": len(would_prune),
            "deleted_count": len(deleted),
            "failed_count": len(failed),
            "deleted": deleted,
            "failed": failed,
        }
        log_path = args.log_dir / f"r2_sync_apply_prune_{scope.name}_{run_id}.json"
        append_operation_log(log_path, payload)
        print(
            "[APPLY-PRUNE] "
            f"scope={scope.name} run_id={run_id} deleted={len(deleted)} failed={len(failed)} "
            f"log={log_path.as_posix()}"
        )
        return 0 if not failed else 2

    raise RuntimeError(f"unsupported_command:{command}")


if __name__ == "__main__":
    raise SystemExit(main())
