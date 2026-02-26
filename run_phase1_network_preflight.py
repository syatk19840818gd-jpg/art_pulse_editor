#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

SOURCE_CLI = "run_phase1_network_preflight.py"
SEARCH_CSVS = [
    Path("data/gallery_lists/gallery_list_frieze_london.csv"),
    Path("data/gallery_lists/gallery_list_liste.csv"),
]
LOG_DIR = Path("data/phase1_seed10/logs")
DEFAULT_TIMEOUT = 8
DEFAULT_SAMPLE_SIZE = 20
SCHEMA_NAME = "phase1_network_preflight_summary"
SCHEMA_VERSION = "v1"
ARTIFACT_KIND = "phase1_network_preflight_summary"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def utc_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Preflight network/DNS check before Phase1 runs")
    p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    p.add_argument("--sample-size", type=int, default=DEFAULT_SAMPLE_SIZE)
    p.add_argument("--output-json", default="")
    return p.parse_args()


def read_seed_hosts(sample_size: int) -> list[str]:
    hosts: list[str] = []
    seen: set[str] = set()
    for csv_path in SEARCH_CSVS:
        if not csv_path.exists():
            continue
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 2:
                    continue
                for col in (1, 2):
                    if col >= len(row):
                        continue
                    url = (row[col] or "").strip()
                    if not url:
                        continue
                    host = (urlparse(url).hostname or "").lower()
                    if host.startswith("www."):
                        host = host[4:]
                    if not host or host in seen:
                        continue
                    seen.add(host)
                    hosts.append(host)
                    if len(hosts) >= sample_size:
                        return hosts
    return hosts


def probe_dns(host: str) -> dict[str, Any]:
    try:
        ip = socket.gethostbyname(host)
        return {"host": host, "dns_ok": True, "ip": ip, "error": ""}
    except OSError as exc:
        return {"host": host, "dns_ok": False, "ip": "", "error": str(exc)}


def probe_http(url: str, timeout: int) -> dict[str, Any]:
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent": "art-pulse-editor/network-preflight"})
        return {"url": url, "http_ok": 200 <= r.status_code < 500, "status_code": r.status_code, "error": ""}
    except requests.RequestException as exc:
        return {"url": url, "http_ok": False, "status_code": None, "error": str(exc)}


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()

    hosts = read_seed_hosts(args.sample_size)
    if "example.com" not in hosts:
        hosts.insert(0, "example.com")

    dns_results = [probe_dns(h) for h in hosts]
    dns_ok_count = sum(1 for x in dns_results if x["dns_ok"])
    dns_total = len(dns_results)
    dns_ok_rate = (dns_ok_count / dns_total) if dns_total else 0.0

    http_results = [probe_http("https://example.com", args.timeout)]
    http_ok = bool(http_results[0]["http_ok"])

    notes: list[str] = []
    if dns_total == 0:
        notes.append("seed_hosts_not_found")
    if not http_ok:
        notes.append("http_probe_failed:example.com")
    if dns_ok_rate < 0.8:
        notes.append(f"dns_ok_rate_below_threshold:{dns_ok_rate:.3f}")

    passed = http_ok and dns_ok_rate >= 0.8

    output_path = Path(args.output_json) if args.output_json else LOG_DIR / f"phase1_network_preflight_summary_{utc_compact()}.json"
    summary = {
        "artifact_kind": ARTIFACT_KIND,
        "schema_name": SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "generated_by": SOURCE_CLI,
        "dns_total": dns_total,
        "dns_ok_count": dns_ok_count,
        "dns_ok_rate": dns_ok_rate,
        "http_probe_url": "https://example.com",
        "http_probe_ok": http_ok,
        "seed_hosts": hosts,
        "dns_results": dns_results,
        "http_results": http_results,
        "notes": notes,
        "passed": passed,
        "wrapper_exit_code": 0 if passed else 1,
    }
    write_json(output_path, summary)

    print(f"[network-preflight] output={output_path}")
    print(f"[network-preflight] dns_ok_rate={dns_ok_rate:.3f} ({dns_ok_count}/{dns_total}) http_ok={http_ok}")
    if not passed:
        print("[network-preflight] FAILED: ネットワーク復旧後に再実行してください。")
        print("[network-preflight] 手順: DNS確認 -> curl確認 -> preflight再実行 -> 本体実行")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
