#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

PHASE1_ROOT = Path("data/phase1_seed10")
LOG_DIR = PHASE1_ROOT / "logs"
DEFAULT_MANIFEST_PATH = PHASE1_ROOT / "derived" / "phase1_seed10_artifact_manifest.json"
DEFAULT_MANIFEST_R2_KEY = "phase1_seed10/derived/phase1_seed10_artifact_manifest.json"

R2_ALIAS = {
    "R2_ENDPOINT": ["R2_ENDPOINT", "R2_ENDPOINT_URL", "R2_S3_ENDPOINT"],
    "R2_BUCKET": ["R2_BUCKET"],
    "R2_ACCESS_KEY_ID": ["R2_ACCESS_KEY_ID"],
    "R2_SECRET_ACCESS_KEY": ["R2_SECRET_ACCESS_KEY"],
    "R2_REGION": ["R2_REGION"],
}

SCOPE_CHOICES = ("raw", "derived", "enrichment", "logs", "all")
R2_PREFIX_BY_CATEGORY = {
    "raw": "phase1_seed10/source",
    "derived": "phase1_seed10/derived",
    "enrichment": "phase1_seed10/derived/enrichment",
    "logs": "phase1_seed10/logs",
}


@dataclass(frozen=True)
class UploadTarget:
    local_path: Path
    r2_key: str
    size_bytes: int
    category: str


@dataclass(frozen=True)
class RemoteObject:
    key: str
    etag: str
    size_bytes: int


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def utc_timestamp_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


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


def format_bytes(size: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size)
    idx = 0
    while value >= 1024 and idx < len(units) - 1:
        value /= 1024.0
        idx += 1
    if idx == 0:
        return f"{int(value)} {units[idx]}"
    return f"{value:.2f} {units[idx]}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted((p for p in root.rglob("*") if p.is_file()), key=lambda p: p.as_posix())


def build_target(local_path: Path, category: str, rel_path: str) -> UploadTarget:
    r2_prefix = R2_PREFIX_BY_CATEGORY[category]
    r2_key = f"{r2_prefix}/{rel_path}"
    return UploadTarget(
        local_path=local_path,
        r2_key=r2_key,
        size_bytes=local_path.stat().st_size,
        category=category,
    )


def collect_raw_targets(root: Path) -> list[UploadTarget]:
    raw_root = root / "raw"
    return [
        build_target(path, "raw", path.relative_to(raw_root).as_posix())
        for path in iter_files(raw_root)
    ]


def collect_derived_targets(root: Path, manifest_path: Path) -> list[UploadTarget]:
    derived_root = root / "derived"
    targets: list[UploadTarget] = []
    for path in iter_files(derived_root):
        if path.resolve() == manifest_path.resolve():
            continue
        rel = path.relative_to(derived_root).as_posix()
        targets.append(build_target(path, "derived", rel))
    return targets


def collect_enrichment_targets(root: Path) -> list[UploadTarget]:
    enrichment_root = root / "enrichment"
    return [
        build_target(path, "enrichment", path.relative_to(enrichment_root).as_posix())
        for path in iter_files(enrichment_root)
    ]


def collect_log_targets(root: Path) -> list[UploadTarget]:
    logs_root = root / "logs"
    return [
        build_target(path, "logs", path.relative_to(logs_root).as_posix())
        for path in iter_files(logs_root)
    ]


def collect_targets(root: Path, scope: str, manifest_path: Path) -> tuple[list[UploadTarget], list[str]]:
    scope_map = {
        "raw": ["raw"],
        "derived": ["derived"],
        "enrichment": ["enrichment"],
        "logs": ["logs"],
        "all": ["raw", "derived", "enrichment", "logs"],
    }
    categories = scope_map[scope]
    collectors = {
        "raw": lambda: collect_raw_targets(root),
        "derived": lambda: collect_derived_targets(root, manifest_path),
        "enrichment": lambda: collect_enrichment_targets(root),
        "logs": lambda: collect_log_targets(root),
    }

    dedup: dict[str, UploadTarget] = {}
    for category in categories:
        for target in collectors[category]():
            dedup[target.local_path.as_posix()] = target

    targets = sorted(dedup.values(), key=lambda t: t.r2_key)
    return targets, categories


def load_remote_head(client: Any, bucket: str, key: str) -> dict[str, Any] | None:
    try:
        return client.head_object(Bucket=bucket, Key=key)
    except ClientError as exc:
        code = str(exc.response.get("Error", {}).get("Code", ""))
        if code in {"404", "NoSuchKey", "NotFound"}:
            return None
        raise


def list_remote_objects_by_prefix(client: Any, bucket: str, prefix: str) -> list[RemoteObject]:
    paginator = client.get_paginator("list_objects_v2")
    remote: list[RemoteObject] = []
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = str(obj.get("Key", ""))
            if not key:
                continue
            remote.append(
                RemoteObject(
                    key=key,
                    etag=normalize_etag(str(obj.get("ETag", ""))),
                    size_bytes=int(obj.get("Size", 0)),
                )
            )
    return remote


def normalize_etag(raw_etag: str | None) -> str:
    if not raw_etag:
        return ""
    return raw_etag.strip().strip('"')


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_json_dict(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return data
    raise ValueError(f"json_root_not_object:{path}")


def resolve_latest_sync_summary(log_dir: Path, scope: str) -> Path | None:
    pattern = f"phase1_seed10_r2_sync_{scope}_*.json"
    candidates = sorted(log_dir.glob(pattern))
    if not candidates:
        return None
    return candidates[-1]


def validate_required_dry_run_log(
    *,
    log_dir: Path,
    scope: str,
    require_prune: bool,
) -> tuple[bool, dict[str, Any]]:
    guard: dict[str, Any] = {
        "enabled": True,
        "ok": False,
        "reason": "",
        "log_path": "",
        "log_mode": "",
        "log_scope": "",
        "log_prune_enabled": False,
        "log_prune_candidates_count": 0,
    }
    latest = resolve_latest_sync_summary(log_dir=log_dir, scope=scope)
    if latest is None:
        guard["reason"] = f"dry_run_log_not_found_for_scope:{scope}"
        return False, guard

    try:
        payload = load_json_dict(latest)
    except Exception as exc:  # noqa: BLE001
        guard["reason"] = f"dry_run_log_load_failed:{exc}"
        guard["log_path"] = latest.as_posix()
        return False, guard

    guard["log_path"] = latest.as_posix()
    guard["log_mode"] = str(payload.get("mode") or "")
    guard["log_scope"] = str(payload.get("scope") or "")
    guard["log_prune_enabled"] = bool(payload.get("prune_enabled"))
    guard["log_prune_candidates_count"] = int(payload.get("prune_candidates_count") or 0)

    if guard["log_mode"] != "dry-run":
        guard["reason"] = f"latest_log_is_not_dry_run:{guard['log_mode']}"
        return False, guard
    if guard["log_scope"] != scope:
        guard["reason"] = f"latest_log_scope_mismatch:{guard['log_scope']}"
        return False, guard
    status_value = str(payload.get("status") or "")
    if not status_value.startswith("DRY_RUN"):
        guard["reason"] = f"latest_dry_run_status_invalid:{status_value}"
        return False, guard
    if require_prune and not guard["log_prune_enabled"]:
        guard["reason"] = "latest_dry_run_log_missing_prune"
        return False, guard

    guard["ok"] = True
    guard["reason"] = "ok"
    return True, guard


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync phase1_seed10 artifacts to R2 (raw/derived/enrichment/logs)."
    )
    parser.add_argument(
        "--scope",
        choices=SCOPE_CHOICES,
        default="all",
        help="sync scope (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only list targets and write local summary/manifest.",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help=(
            "Delete remote-only objects under managed prefixes. "
            "Use with --dry-run first to inspect planned deletions."
        ),
    )
    parser.add_argument(
        "--require-dry-run-log",
        action="store_true",
        help=(
            "Require latest same-scope dry-run summary in log-dir before apply. "
            "If --prune is set, latest dry-run must also be prune-enabled."
        ),
    )
    parser.add_argument(
        "--max-prune",
        type=int,
        default=-1,
        help=(
            "Maximum allowed prune candidates. "
            "Set -1 to disable limit (default: -1)."
        ),
    )
    parser.add_argument(
        "--target-year",
        type=int,
        default=2025,
        help="target year written into manifest metadata (default: 2025)",
    )
    parser.add_argument(
        "--manifest-path",
        type=Path,
        default=DEFAULT_MANIFEST_PATH,
        help=f"local manifest output path (default: {DEFAULT_MANIFEST_PATH})",
    )
    parser.add_argument(
        "--manifest-r2-key",
        default=DEFAULT_MANIFEST_R2_KEY,
        help=f"R2 key for uploaded manifest (default: {DEFAULT_MANIFEST_R2_KEY})",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=LOG_DIR,
        help=f"sync summary log directory (default: {LOG_DIR})",
    )
    return parser.parse_args()


def build_manifest_payload(
    *,
    args: argparse.Namespace,
    categories: list[str],
    synced_files: list[dict[str, Any]],
    failed_count: int,
) -> dict[str, Any]:
    sorted_files = sorted(synced_files, key=lambda x: x["path"])
    return {
        "artifact_kind": "phase1_seed10_artifact_manifest",
        "schema_name": "phase1_seed10_artifact_manifest",
        "schema_version": "v1",
        "generated_at": utc_now_iso(),
        "generated_by": "run_phase1_seed10_r2_sync.py",
        "target_year": args.target_year,
        "scope": args.scope,
        "categories": categories,
        "source_root": PHASE1_ROOT.as_posix(),
        "records_count": len(sorted_files),
        "failed_count": failed_count,
        "files": sorted_files,
    }


def main() -> int:
    args = parse_args()
    started_at = utc_now_iso()
    guard_blocked = False
    dry_run_guard: dict[str, Any] = {
        "enabled": bool(args.require_dry_run_log),
        "ok": not bool(args.require_dry_run_log) or bool(args.dry_run),
        "reason": "disabled" if not args.require_dry_run_log else ("skip_for_dry_run_mode" if args.dry_run else ""),
        "log_path": "",
        "log_mode": "",
        "log_scope": "",
        "log_prune_enabled": False,
        "log_prune_candidates_count": 0,
    }

    if args.require_dry_run_log and not args.dry_run:
        ok, dry_run_guard = validate_required_dry_run_log(
            log_dir=args.log_dir,
            scope=args.scope,
            require_prune=bool(args.prune),
        )
        if not ok:
            print(f"[GUARD-FAIL] require_dry_run_log: {dry_run_guard['reason']}")
            if dry_run_guard.get("log_path"):
                print(f"[GUARD-FAIL] checked_log={dry_run_guard['log_path']}")
            return 2

    targets, categories = collect_targets(PHASE1_ROOT, args.scope, args.manifest_path)
    total_bytes = sum(t.size_bytes for t in targets)
    target_counts_by_category = dict(Counter(t.category for t in targets))

    uploaded: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    synced_files: list[dict[str, Any]] = []
    pruned: list[dict[str, Any]] = []
    prune_failed: list[dict[str, Any]] = []
    prune_candidates: list[dict[str, Any]] = []

    print(f"[START] phase1_seed10 R2 sync at {started_at}")
    print(
        f"[INFO] scope={args.scope} categories={','.join(categories)} "
        f"targets={len(targets)} total_size={total_bytes} ({format_bytes(total_bytes)}) "
        f"mode={'dry-run' if args.dry_run else 'apply'}"
    )
    print(f"[INFO] target_counts_by_category={target_counts_by_category}")

    client = None
    bucket = ""
    if (not args.dry_run) or args.prune:
        client, bucket = build_r2_client()

    for target in targets:
        try:
            local_sha256 = sha256_file(target.local_path)

            if args.dry_run:
                synced_files.append(
                    {
                        "path": target.r2_key,
                        "etag": "",
                        "sha256": local_sha256,
                        "bytes": target.size_bytes,
                        "category": target.category,
                        "local_path": target.local_path.as_posix(),
                    }
                )
                print(
                    f"[DRY-RUN] [{target.category}] {target.local_path.as_posix()} -> "
                    f"{target.r2_key} ({target.size_bytes} bytes)"
                )
                continue

            assert client is not None
            remote = load_remote_head(client=client, bucket=bucket, key=target.r2_key)
            remote_sha = ""
            remote_size = -1
            remote_etag = ""
            if remote is not None:
                remote_size = int(remote.get("ContentLength", -1))
                remote_etag = normalize_etag(remote.get("ETag"))
                remote_sha = str((remote.get("Metadata") or {}).get("sha256", ""))

            if remote is not None and remote_size == target.size_bytes and remote_sha == local_sha256:
                skipped.append(
                    {
                        "category": target.category,
                        "local_path": target.local_path.as_posix(),
                        "r2_key": target.r2_key,
                        "size_bytes": target.size_bytes,
                        "sha256": local_sha256,
                        "reason": "EXISTS_SAME_SIZE_AND_SHA256",
                    }
                )
                synced_files.append(
                    {
                        "path": target.r2_key,
                        "etag": remote_etag,
                        "sha256": local_sha256,
                        "bytes": target.size_bytes,
                        "category": target.category,
                        "local_path": target.local_path.as_posix(),
                    }
                )
                print(
                    f"[SKIP] [{target.category}] {target.r2_key} "
                    f"reason=EXISTS_SAME_SIZE_AND_SHA256 size={target.size_bytes}"
                )
                continue

            with target.local_path.open("rb") as body:
                put_resp = client.put_object(
                    Bucket=bucket,
                    Key=target.r2_key,
                    Body=body,
                    Metadata={"sha256": local_sha256},
                )
            etag = normalize_etag(str(put_resp.get("ETag", "")))

            uploaded.append(
                {
                    "category": target.category,
                    "local_path": target.local_path.as_posix(),
                    "r2_key": target.r2_key,
                    "size_bytes": target.size_bytes,
                    "sha256": local_sha256,
                    "etag": etag,
                }
            )
            synced_files.append(
                {
                    "path": target.r2_key,
                    "etag": etag,
                    "sha256": local_sha256,
                    "bytes": target.size_bytes,
                    "category": target.category,
                    "local_path": target.local_path.as_posix(),
                }
            )
            print(
                f"[UPLOAD] [{target.category}] {target.r2_key} "
                f"size={target.size_bytes} sha256={local_sha256[:12]}..."
            )
        except Exception as exc:  # noqa: BLE001
            failed.append(
                {
                    "category": target.category,
                    "local_path": target.local_path.as_posix(),
                    "r2_key": target.r2_key,
                    "size_bytes": target.size_bytes,
                    "error": str(exc),
                }
            )
            print(f"[FAIL] [{target.category}] {target.r2_key} error={exc}")

    manifest_payload = build_manifest_payload(
        args=args,
        categories=categories,
        synced_files=synced_files,
        failed_count=len(failed),
    )
    write_json(args.manifest_path, manifest_payload)
    manifest_local_sha = sha256_file(args.manifest_path)

    manifest_upload = {
        "attempted": False,
        "uploaded": False,
        "r2_key": args.manifest_r2_key,
        "etag": "",
        "sha256": manifest_local_sha,
        "size_bytes": args.manifest_path.stat().st_size,
        "reason": "dry_run",
    }

    if not args.dry_run:
        manifest_upload["attempted"] = True
        if failed:
            manifest_upload["reason"] = "skipped_due_to_failed_uploads"
        else:
            assert client is not None
            with args.manifest_path.open("rb") as handle:
                put_manifest = client.put_object(
                    Bucket=bucket,
                    Key=args.manifest_r2_key,
                    Body=handle,
                    Metadata={"sha256": manifest_local_sha},
                )
            manifest_upload["uploaded"] = True
            manifest_upload["reason"] = "uploaded"
            manifest_upload["etag"] = normalize_etag(str(put_manifest.get("ETag", "")))
            print(
                f"[UPLOAD] [manifest] {args.manifest_r2_key} "
                f"size={manifest_upload['size_bytes']} sha256={manifest_local_sha[:12]}..."
            )

    prune_result = {
        "enabled": bool(args.prune),
        "attempted": False,
        "executed": False,
        "reason": "prune_disabled",
        "managed_prefixes": [],
        "remote_objects_scanned_count": 0,
        "candidate_count": 0,
        "deleted_count": 0,
        "failed_count": 0,
    }
    if args.prune:
        managed_prefixes = sorted({R2_PREFIX_BY_CATEGORY[c] for c in categories})
        prune_result["managed_prefixes"] = managed_prefixes
        desired_keys = {target.r2_key for target in targets}
        if "derived" in categories:
            desired_keys.add(args.manifest_r2_key)

        assert client is not None
        remote_by_key: dict[str, RemoteObject] = {}
        for prefix in managed_prefixes:
            for remote_obj in list_remote_objects_by_prefix(client=client, bucket=bucket, prefix=prefix):
                remote_by_key[remote_obj.key] = remote_obj
        prune_result["remote_objects_scanned_count"] = len(remote_by_key)

        for key in sorted(remote_by_key.keys()):
            if key in desired_keys:
                continue
            robj = remote_by_key[key]
            prune_candidates.append(
                {
                    "r2_key": robj.key,
                    "etag": robj.etag,
                    "size_bytes": robj.size_bytes,
                    "reason": "REMOTE_ONLY_NOT_IN_LOCAL_MANIFEST",
                }
            )
        prune_result["candidate_count"] = len(prune_candidates)
        max_prune_limit = args.max_prune if args.max_prune >= 0 else None

        if max_prune_limit is not None and len(prune_candidates) > max_prune_limit:
            prune_result["attempted"] = True
            prune_result["executed"] = False
            prune_result["reason"] = "max_prune_exceeded"
            prune_result["max_prune"] = max_prune_limit
            prune_result["candidate_count"] = len(prune_candidates)
            guard_blocked = not args.dry_run
            print(
                f"[PRUNE-BLOCK] candidate_count={len(prune_candidates)} "
                f"exceeds max_prune={max_prune_limit}"
            )
        elif args.dry_run:
            prune_result["attempted"] = True
            prune_result["executed"] = False
            prune_result["reason"] = "dry_run_no_delete"
            for candidate in prune_candidates:
                print(
                    f"[PRUNE-DRY-RUN] {candidate['r2_key']} "
                    f"size={candidate['size_bytes']} reason={candidate['reason']}"
                )
        elif failed:
            prune_result["attempted"] = True
            prune_result["executed"] = False
            prune_result["reason"] = "skipped_due_to_upload_failures"
        else:
            prune_result["attempted"] = True
            prune_result["executed"] = True
            for idx in range(0, len(prune_candidates), 1000):
                batch = prune_candidates[idx : idx + 1000]
                try:
                    resp = client.delete_objects(
                        Bucket=bucket,
                        Delete={"Objects": [{"Key": c["r2_key"]} for c in batch], "Quiet": False},
                    )
                    for deleted in resp.get("Deleted", []):
                        key = str(deleted.get("Key", ""))
                        if not key:
                            continue
                        pruned.append({"r2_key": key})
                        print(f"[PRUNE] deleted {key}")
                    for err in resp.get("Errors", []):
                        key = str(err.get("Key", ""))
                        code = str(err.get("Code", ""))
                        msg = str(err.get("Message", ""))
                        prune_failed.append({"r2_key": key, "error": f"{code}:{msg}"})
                        print(f"[PRUNE-FAIL] {key} error={code}:{msg}")
                except Exception as exc:  # noqa: BLE001
                    for candidate in batch:
                        prune_failed.append({"r2_key": candidate["r2_key"], "error": str(exc)})
                        print(f"[PRUNE-FAIL] {candidate['r2_key']} error={exc}")
            prune_result["deleted_count"] = len(pruned)
            prune_result["failed_count"] = len(prune_failed)
            prune_result["reason"] = "ok" if not prune_failed else "partial_fail"

    completed_at = utc_now_iso()
    if args.dry_run:
        status = "DRY_RUN_OK"
    elif guard_blocked and not failed and not prune_failed:
        status = "GUARD_BLOCKED"
    else:
        has_failures = bool(failed or prune_failed or guard_blocked)
        status = "PARTIAL_FAIL" if has_failures else "OK"
    summary = {
        "artifact_kind": "phase1_seed10_r2_sync_summary",
        "schema_name": "phase1_seed10_r2_sync_summary",
        "schema_version": "v1",
        "generated_at": completed_at,
        "generated_by": "run_phase1_seed10_r2_sync.py",
        "started_at": started_at,
        "completed_at": completed_at,
        "status": status,
        "mode": "dry-run" if args.dry_run else "apply",
        "scope": args.scope,
        "target_year": args.target_year,
        "categories": categories,
        "source_root": PHASE1_ROOT.as_posix(),
        "targets_total": len(targets),
        "target_counts_by_category": target_counts_by_category,
        "targets_total_size_bytes": total_bytes,
        "targets_total_size_human": format_bytes(total_bytes),
        "uploaded_count": len(uploaded),
        "skipped_count": len(skipped),
        "failed_count": len(failed),
        "prune_enabled": bool(args.prune),
        "require_dry_run_log": bool(args.require_dry_run_log),
        "dry_run_guard": dry_run_guard,
        "max_prune": args.max_prune,
        "guard_blocked": guard_blocked,
        "prune_result": prune_result,
        "prune_candidates_count": len(prune_candidates),
        "pruned_count": len(pruned),
        "prune_failed_count": len(prune_failed),
        "manifest_local_path": args.manifest_path.as_posix(),
        "manifest_upload": manifest_upload,
        "uploaded": uploaded,
        "skipped": skipped,
        "failed": failed,
        "prune_candidates": prune_candidates,
        "pruned": pruned,
        "prune_failed": prune_failed,
    }

    summary_path = args.log_dir / f"phase1_seed10_r2_sync_{args.scope}_{utc_timestamp_compact()}.json"
    write_json(summary_path, summary)

    print(
        f"[DONE] status={status} uploaded={len(uploaded)} skipped={len(skipped)} "
        f"failed={len(failed)} pruned={len(pruned)} prune_failed={len(prune_failed)}"
    )
    print(f"[DONE] manifest_local={args.manifest_path.as_posix()}")
    print(f"[DONE] summary={summary_path.as_posix()}")

    return 0 if (args.dry_run or (not failed and not prune_failed and not guard_blocked)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
