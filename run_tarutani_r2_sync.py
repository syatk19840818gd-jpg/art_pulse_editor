#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
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


@dataclass(frozen=True)
class UploadTarget:
    local_path: Path
    r2_key: str
    size_bytes: int


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


def collect_targets(root: Path) -> list[UploadTarget]:
    targets: list[UploadTarget] = []
    for file_path in sorted(root.glob("*/Text/*"), key=lambda p: p.as_posix()):
        if not file_path.is_file():
            continue
        rel = file_path.as_posix()
        targets.append(
            UploadTarget(
                local_path=file_path,
                r2_key=rel,  # SSOT 5-5: data/Tarutani_data/{Series_Name}/Text/{Text_File}
                size_bytes=file_path.stat().st_size,
            )
        )
    return targets


def load_remote_head(client: Any, bucket: str, key: str) -> dict[str, Any] | None:
    try:
        return client.head_object(Bucket=bucket, Key=key)
    except ClientError as exc:
        code = str(exc.response.get("Error", {}).get("Code", ""))
        if code in {"404", "NoSuchKey", "NotFound"}:
            return None
        raise


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync Tarutani source files to R2 (R2 canonical operation)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print/upload targets and write a dry-run log JSON.",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=LOG_DIR,
        help=f"Directory for sync result JSON logs (default: {LOG_DIR}).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started_at = utc_now_iso()
    targets = collect_targets(SOURCE_ROOT)
    total_bytes = sum(t.size_bytes for t in targets)

    uploaded: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []

    print(f"[START] Tarutani R2 sync at {started_at}")
    print(
        f"[INFO] targets={len(targets)} total_size={total_bytes} ({format_bytes(total_bytes)}) "
        f"mode={'dry-run' if args.dry_run else 'apply'}"
    )

    if args.dry_run:
        for target in targets:
            print(
                f"[DRY-RUN] {target.local_path.as_posix()} -> {target.r2_key} "
                f"({target.size_bytes} bytes)"
            )
    else:
        client, bucket = build_r2_client()
        for target in targets:
            try:
                remote = load_remote_head(client=client, bucket=bucket, key=target.r2_key)
                if remote is not None:
                    remote_size = int(remote.get("ContentLength", -1))
                    if remote_size == target.size_bytes:
                        skipped.append(
                            {
                                "local_path": target.local_path.as_posix(),
                                "r2_key": target.r2_key,
                                "size_bytes": target.size_bytes,
                                "reason": "EXISTS_SAME_SIZE",
                            }
                        )
                        print(
                            f"[SKIP] {target.r2_key} reason=EXISTS_SAME_SIZE "
                            f"size={target.size_bytes}"
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
                        "local_path": target.local_path.as_posix(),
                        "r2_key": target.r2_key,
                        "size_bytes": target.size_bytes,
                        "sha256": local_sha256,
                    }
                )
                print(
                    f"[UPLOAD] {target.r2_key} size={target.size_bytes} "
                    f"sha256={local_sha256[:12]}..."
                )
            except Exception as exc:  # noqa: BLE001
                failed.append(
                    {
                        "local_path": target.local_path.as_posix(),
                        "r2_key": target.r2_key,
                        "size_bytes": target.size_bytes,
                        "error": str(exc),
                    }
                )
                print(f"[FAIL] {target.r2_key} error={exc}")

    completed_at = utc_now_iso()
    status = "DRY_RUN_OK" if args.dry_run else ("PARTIAL_FAIL" if failed else "OK")
    summary = {
        "started_at": started_at,
        "completed_at": completed_at,
        "status": status,
        "mode": "dry-run" if args.dry_run else "apply",
        "source_root": str(SOURCE_ROOT),
        "targets_total": len(targets),
        "targets_total_size_bytes": total_bytes,
        "targets_total_size_human": format_bytes(total_bytes),
        "uploaded_count": len(uploaded),
        "skipped_count": len(skipped),
        "failed_count": len(failed),
        "uploaded": uploaded,
        "skipped": skipped,
        "failed": failed,
        "target_files": [
            {
                "local_path": t.local_path.as_posix(),
                "r2_key": t.r2_key,
                "size_bytes": t.size_bytes,
            }
            for t in targets
        ],
    }

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = args.log_dir / f"tarutani_r2_sync_{timestamp}.json"
    write_json(log_path, summary)

    print(
        f"[DONE] status={status} uploaded={len(uploaded)} skipped={len(skipped)} "
        f"failed={len(failed)}"
    )
    print(f"[DONE] log={log_path.as_posix()}")
    return 0 if (args.dry_run or not failed) else 1


if __name__ == "__main__":
    raise SystemExit(main())
