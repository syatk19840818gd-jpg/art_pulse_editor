#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

SOURCE_ROOT = Path("data/Tarutani_data")
LOG_DIR = SOURCE_ROOT / "logs"

R2_ALIAS = {
    "R2_ENDPOINT": ["R2_ENDPOINT", "R2_ENDPOINT_URL", "R2_S3_ENDPOINT"],
    "R2_BUCKET": ["R2_BUCKET"],
    "R2_ACCESS_KEY_ID": ["R2_ACCESS_KEY_ID"],
    "R2_SECRET_ACCESS_KEY": ["R2_SECRET_ACCESS_KEY"],
    "R2_REGION": ["R2_REGION"],
}

SCOPE_CHOICES = ("source", "derived", "logs", "all")
R2_PREFIX_BY_CATEGORY = {
    "source": "tarutani/source",
    "derived": "tarutani/derived",
    "logs": "tarutani/logs",
    "vectors": "tarutani/vectors",  # future-ready receiver for vector artifacts
}


@dataclass(frozen=True)
class UploadTarget:
    local_path: Path
    r2_key: str
    size_bytes: int
    category: str


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


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
        missing_csv = ", ".join(missing)
        raise RuntimeError(f"Missing R2 env vars: {missing_csv}")

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


def build_target(local_path: Path, category: str, relative_from_base: str) -> UploadTarget:
    r2_prefix = R2_PREFIX_BY_CATEGORY[category]
    r2_key = f"{r2_prefix}/{relative_from_base}"
    return UploadTarget(
        local_path=local_path,
        r2_key=r2_key,
        size_bytes=local_path.stat().st_size,
        category=category,
    )


def should_ignore_sync_path(path: Path) -> bool:
    # Ignore Windows ADS artifacts that may appear as pseudo-files in some environments.
    name = path.name
    return "Zone.Identifier" in name


def collect_source_targets(root: Path) -> list[UploadTarget]:
    targets: list[UploadTarget] = []
    for file_path in sorted(root.glob("*/Text/*"), key=lambda p: p.as_posix()):
        if not file_path.is_file():
            continue
        if should_ignore_sync_path(file_path):
            continue
        rel = file_path.relative_to(root).as_posix()
        targets.append(build_target(local_path=file_path, category="source", relative_from_base=rel))
    return targets


def collect_derived_targets(root: Path) -> list[UploadTarget]:
    targets: list[UploadTarget] = []

    fixed_files = [
        root / "tarutani_text.jsonl",
        root / "tarutani_text_import_summary.json",
    ]
    for path in fixed_files:
        if path.is_file():
            if should_ignore_sync_path(path):
                continue
            rel = path.relative_to(root).as_posix()
            targets.append(build_target(local_path=path, category="derived", relative_from_base=rel))

    enrichment_root = root / "enrichment"
    if enrichment_root.exists():
        for file_path in sorted(enrichment_root.rglob("*"), key=lambda p: p.as_posix()):
            if not file_path.is_file():
                continue
            if should_ignore_sync_path(file_path):
                continue
            rel = file_path.relative_to(root).as_posix()
            targets.append(
                build_target(local_path=file_path, category="derived", relative_from_base=rel)
            )

    # De-duplicate by local path (fixed list + enrichment traversal safety)
    dedup: dict[str, UploadTarget] = {}
    for target in targets:
        dedup[target.local_path.as_posix()] = target
    return sorted(dedup.values(), key=lambda t: t.r2_key)


def collect_log_targets(root: Path) -> list[UploadTarget]:
    targets: list[UploadTarget] = []
    logs_root = root / "logs"
    if not logs_root.exists():
        return targets

    for file_path in sorted(logs_root.rglob("*.json"), key=lambda p: p.as_posix()):
        if not file_path.is_file():
            continue
        if should_ignore_sync_path(file_path):
            continue
        rel = file_path.relative_to(logs_root).as_posix()
        targets.append(build_target(local_path=file_path, category="logs", relative_from_base=rel))
    return targets


def collect_vector_targets(root: Path) -> list[UploadTarget]:
    targets: list[UploadTarget] = []
    vector_root = root / "vector"
    if not vector_root.exists():
        return targets

    for file_path in sorted(vector_root.rglob("*"), key=lambda p: p.as_posix()):
        if not file_path.is_file():
            continue
        if should_ignore_sync_path(file_path):
            continue
        rel = file_path.relative_to(vector_root).as_posix()
        targets.append(build_target(local_path=file_path, category="vectors", relative_from_base=rel))
    return targets


def collect_targets(root: Path, scope: str) -> tuple[list[UploadTarget], list[str]]:
    scope_map = {
        "source": ["source"],
        "derived": ["derived"],
        "logs": ["logs"],
        "all": ["source", "derived", "logs", "vectors"],
    }
    categories = scope_map[scope]

    collectors = {
        "source": collect_source_targets,
        "derived": collect_derived_targets,
        "logs": collect_log_targets,
        "vectors": collect_vector_targets,
    }

    dedup: dict[str, UploadTarget] = {}
    for category in categories:
        for target in collectors[category](root):
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


def list_remote_objects_by_prefixes(
    client: Any, bucket: str, prefixes: list[str]
) -> dict[str, dict[str, Any]]:
    remote_by_key: dict[str, dict[str, Any]] = {}
    for raw_prefix in prefixes:
        prefix = raw_prefix.rstrip("/")
        if not prefix:
            continue

        continuation: str | None = None
        while True:
            kwargs: dict[str, Any] = {"Bucket": bucket, "Prefix": f"{prefix}/"}
            if continuation:
                kwargs["ContinuationToken"] = continuation

            resp = client.list_objects_v2(**kwargs)
            for obj in resp.get("Contents", []):
                key = str(obj.get("Key", ""))
                if not key:
                    continue
                remote_by_key[key] = {
                    "size_bytes": int(obj.get("Size", 0)),
                    "last_modified": (
                        obj.get("LastModified").isoformat()
                        if obj.get("LastModified") is not None
                        else None
                    ),
                }

            if not resp.get("IsTruncated"):
                break
            continuation = resp.get("NextContinuationToken")
    return remote_by_key


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync Tarutani files to R2 (source/derived/logs/all)."
    )
    parser.add_argument(
        "--scope",
        choices=SCOPE_CHOICES,
        default="source",
        help="sync target scope (default: source)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print target list and write a dry-run summary JSON.",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help=(
            "Delete remote objects under managed prefixes that are not present "
            "in local targets. Use with --dry-run first."
        ),
    )
    parser.add_argument(
        "--prune-prefix",
        action="append",
        default=[],
        help=(
            "Additional remote prefix to include in prune scope "
            "(repeatable, e.g. --prune-prefix data/Tarutani_data)."
        ),
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=LOG_DIR,
        help=f"Directory for sync result JSON logs (default: {LOG_DIR}).",
    )
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")

    args = parse_args()
    started_at = utc_now_iso()
    targets, categories = collect_targets(SOURCE_ROOT, args.scope)
    total_bytes = sum(t.size_bytes for t in targets)

    uploaded: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    pruned: list[dict[str, Any]] = []
    prune_failed: list[dict[str, Any]] = []
    prune_candidates: list[dict[str, Any]] = []

    target_counts_by_category = dict(Counter(t.category for t in targets))

    print(f"[START] Tarutani R2 sync at {started_at}")
    print(
        f"[INFO] scope={args.scope} categories={','.join(categories)} "
        f"targets={len(targets)} total_size={total_bytes} ({format_bytes(total_bytes)}) "
        f"mode={'dry-run' if args.dry_run else 'apply'}"
    )
    print(f"[INFO] target_counts_by_category={target_counts_by_category}")
    print(
        f"[INFO] prune_enabled={bool(args.prune)} "
        f"extra_prune_prefixes={[p.rstrip('/') for p in (args.prune_prefix or []) if p]}"
    )

    client: Any | None = None
    bucket: str | None = None
    if (not args.dry_run) or args.prune:
        client, bucket = build_r2_client()

    if args.dry_run:
        for target in targets:
            print(
                f"[DRY-RUN] [{target.category}] {target.local_path.as_posix()} -> {target.r2_key} "
                f"({target.size_bytes} bytes)"
            )
    else:
        assert client is not None and bucket is not None
        for target in targets:
            try:
                remote = load_remote_head(client=client, bucket=bucket, key=target.r2_key)
                if remote is not None:
                    remote_size = int(remote.get("ContentLength", -1))
                    if remote_size == target.size_bytes:
                        skipped.append(
                            {
                                "category": target.category,
                                "local_path": target.local_path.as_posix(),
                                "r2_key": target.r2_key,
                                "size_bytes": target.size_bytes,
                                "reason": "EXISTS_SAME_SIZE",
                            }
                        )
                        print(
                            f"[SKIP] [{target.category}] {target.r2_key} "
                            f"reason=EXISTS_SAME_SIZE size={target.size_bytes}"
                        )
                        continue

                local_sha256 = sha256_file(target.local_path)
                with target.local_path.open("rb") as body:
                    client.put_object(
                        Bucket=bucket,
                        Key=target.r2_key,
                        Body=body,
                        Metadata={"sha256": local_sha256},
                    )
                uploaded.append(
                    {
                        "category": target.category,
                        "local_path": target.local_path.as_posix(),
                        "r2_key": target.r2_key,
                        "size_bytes": target.size_bytes,
                        "sha256": local_sha256,
                    }
                )
                print(
                    f"[UPLOAD] [{target.category}] {target.r2_key} size={target.size_bytes} "
                    f"sha256={local_sha256[:12]}..."
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

    prune_result = {
        "enabled": bool(args.prune),
        "attempted": False,
        "executed": False,
        "reason": "prune_disabled",
    }
    if args.prune:
        assert client is not None and bucket is not None
        managed_prefixes = [R2_PREFIX_BY_CATEGORY[category] for category in categories]
        managed_prefixes.extend([p.rstrip("/") for p in (args.prune_prefix or []) if p])
        managed_prefixes = sorted(set([p for p in managed_prefixes if p]))
        prune_result["managed_prefixes"] = managed_prefixes

        remote_by_key = list_remote_objects_by_prefixes(
            client=client, bucket=bucket, prefixes=managed_prefixes
        )
        prune_result["remote_objects_scanned_count"] = len(remote_by_key)

        desired_keys = {target.r2_key for target in targets}
        for key, meta in sorted(remote_by_key.items()):
            if key in desired_keys:
                continue
            prune_candidates.append(
                {
                    "r2_key": key,
                    "size_bytes": int(meta.get("size_bytes", 0)),
                    "last_modified": meta.get("last_modified"),
                }
            )
        prune_result["candidate_count"] = len(prune_candidates)

        if args.dry_run:
            prune_result["attempted"] = True
            prune_result["executed"] = False
            prune_result["reason"] = "dry_run_no_delete"
            for candidate in prune_candidates:
                print(
                    f"[DRY-RUN-DELETE] {candidate['r2_key']} "
                    f"size={candidate['size_bytes']}"
                )
        elif failed:
            prune_result["attempted"] = True
            prune_result["executed"] = False
            prune_result["reason"] = "skipped_due_to_upload_failures"
            print("[PRUNE-SKIP] upload failures detected; prune was skipped for safety.")
        else:
            prune_result["attempted"] = True
            prune_result["executed"] = True
            for idx in range(0, len(prune_candidates), 1000):
                batch = prune_candidates[idx : idx + 1000]
                objects = [{"Key": candidate["r2_key"]} for candidate in batch]
                try:
                    resp = client.delete_objects(
                        Bucket=bucket,
                        Delete={"Objects": objects, "Quiet": True},
                    )
                    error_entries = resp.get("Errors", [])
                    failed_keys: set[str] = set()
                    for err in error_entries:
                        key = err.get("Key")
                        code = err.get("Code", "Unknown")
                        msg = err.get("Message", "")
                        prune_failed.append({"r2_key": key, "error": f"{code}:{msg}"})
                        if key:
                            failed_keys.add(str(key))
                        print(f"[DELETE-FAIL] {key} error={code}:{msg}")
                    for candidate in batch:
                        key = str(candidate["r2_key"])
                        if key in failed_keys:
                            continue
                        pruned.append({"r2_key": key})
                        print(f"[DELETE] {key}")
                except Exception as exc:  # noqa: BLE001
                    for candidate in batch:
                        prune_failed.append({"r2_key": candidate["r2_key"], "error": str(exc)})
                        print(f"[DELETE-FAIL] {candidate['r2_key']} error={exc}")
            prune_result["deleted_count"] = len(pruned)
            prune_result["failed_count"] = len(prune_failed)
            prune_result["reason"] = "ok" if not prune_failed else "partial_fail"

    completed_at = utc_now_iso()
    if args.dry_run:
        status = "DRY_RUN_OK"
    else:
        status = "PARTIAL_FAIL" if (failed or prune_failed) else "OK"
    summary = {
        "started_at": started_at,
        "completed_at": completed_at,
        "status": status,
        "mode": "dry-run" if args.dry_run else "apply",
        "scope": args.scope,
        "categories": categories,
        "source_root": str(SOURCE_ROOT),
        "targets_total": len(targets),
        "target_counts_by_category": target_counts_by_category,
        "targets_total_size_bytes": total_bytes,
        "targets_total_size_human": format_bytes(total_bytes),
        "uploaded_count": len(uploaded),
        "skipped_count": len(skipped),
        "failed_count": len(failed),
        "prune_enabled": bool(args.prune),
        "prune_result": prune_result,
        "prune_candidates_count": len(prune_candidates),
        "pruned_count": len(pruned),
        "prune_failed_count": len(prune_failed),
        "uploaded": uploaded,
        "skipped": skipped,
        "failed": failed,
        "prune_candidates": prune_candidates,
        "pruned": pruned,
        "prune_failed": prune_failed,
        "target_files": [
            {
                "category": t.category,
                "local_path": t.local_path.as_posix(),
                "r2_key": t.r2_key,
                "size_bytes": t.size_bytes,
            }
            for t in targets
        ],
    }

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = args.log_dir / f"tarutani_r2_sync_{args.scope}_{timestamp}.json"
    write_json(log_path, summary)

    print(
        f"[DONE] scope={args.scope} status={status} uploaded={len(uploaded)} "
        f"skipped={len(skipped)} failed={len(failed)} "
        f"pruned={len(pruned)} prune_failed={len(prune_failed)}"
    )
    print(f"[DONE] log={log_path.as_posix()}")
    return 0 if (args.dry_run or (not failed and not prune_failed)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
