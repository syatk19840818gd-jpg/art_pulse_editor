#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
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
PROFILE_JSON = Path("config/phase1_network_preflight_profile.json")
LOG_DIR = Path("data/phase1_seed10/logs")
DEFAULT_TIMEOUT = 8
DEFAULT_SAMPLE_SIZE = 20
DEFAULT_DNS_THRESHOLD = 0.8
DEFAULT_HTTP_QUORUM_RATE = 0.67
DEFAULT_PROBE_URLS = [
    "https://www.google.com/generate_204",
    "https://api.github.com",
    "https://www.cloudflare.com/cdn-cgi/trace",
]
DEFAULT_USER_AGENT = "art-pulse-editor/network-preflight"
SCHEMA_NAME = "phase1_network_preflight_summary"
SCHEMA_VERSION = "v1"
ARTIFACT_KIND = "phase1_network_preflight_summary"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def utc_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preflight network/DNS check before Phase1 runs")
    parser.add_argument("--timeout", type=int, default=None)
    parser.add_argument("--sample-size", type=int, default=None)
    parser.add_argument("--profile-json", default=str(PROFILE_JSON))
    parser.add_argument("--probe-url", action="append", default=[])
    parser.add_argument("--dns-threshold", type=float, default=None)
    parser.add_argument("--http-required-successes", type=int, default=None)
    parser.add_argument("--output-json", default="")
    return parser.parse_args()


def load_profile(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def read_seed_hosts(sample_size: int) -> list[str]:
    hosts: list[str] = []
    seen: set[str] = set()
    for csv_path in SEARCH_CSVS:
        if not csv_path.exists():
            continue
        with csv_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
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


def append_probe_hosts(hosts: list[str], probe_urls: list[str]) -> list[str]:
    seen = set(hosts)
    merged = list(hosts)
    for probe_url in probe_urls:
        host = (urlparse(probe_url).hostname or "").lower()
        if host.startswith("www."):
            host = host[4:]
        if not host or host in seen:
            continue
        seen.add(host)
        merged.append(host)
    return merged


def probe_dns(host: str) -> dict[str, Any]:
    try:
        ip = socket.gethostbyname(host)
        return {"host": host, "dns_ok": True, "ip": ip, "error": ""}
    except OSError as exc:
        return {"host": host, "dns_ok": False, "ip": "", "error": str(exc)}


def classify_http_error(error_text: str) -> str:
    lowered = error_text.lower()
    if "certificateverifyfailed" in lowered or "sslcertverificationerror" in lowered:
        return "tls_cert_verify_failed"
    if "nameresolutionerror" in lowered or "failed to resolve" in lowered or "getaddrinfo failed" in lowered:
        return "dns_resolution_failed"
    if "proxyerror" in lowered:
        return "proxy_error"
    if "connecttimeout" in lowered or "read timed out" in lowered or "timed out" in lowered:
        return "timeout"
    if "connection refused" in lowered:
        return "connection_refused"
    return "request_exception"


def probe_http(url: str, timeout: int, user_agent: str) -> dict[str, Any]:
    try:
        response = requests.get(url, timeout=timeout, headers={"User-Agent": user_agent})
        http_ok = 200 <= response.status_code < 500
        return {
            "url": url,
            "http_ok": http_ok,
            "status_code": response.status_code,
            "error": "",
            "failure_kind": "" if http_ok else f"http_status_{response.status_code}",
        }
    except requests.RequestException as exc:
        error_text = str(exc)
        return {
            "url": url,
            "http_ok": False,
            "status_code": None,
            "error": error_text,
            "failure_kind": classify_http_error(error_text),
        }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_default_output_path() -> Path:
    stamp = utc_compact()
    base = LOG_DIR / f"phase1_network_preflight_summary_{stamp}.json"
    if not base.exists():
        return base
    idx = 1
    while True:
        candidate = LOG_DIR / f"phase1_network_preflight_summary_{stamp}_{idx:02d}.json"
        if not candidate.exists():
            return candidate
        idx += 1


def dedup_strings(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def main() -> int:
    args = parse_args()
    profile_path = Path(args.profile_json)
    profile = load_profile(profile_path)

    timeout = int(args.timeout if args.timeout is not None else profile.get("timeout", DEFAULT_TIMEOUT))
    sample_size = int(
        args.sample_size if args.sample_size is not None else profile.get("sample_size", DEFAULT_SAMPLE_SIZE)
    )
    dns_threshold = float(
        args.dns_threshold
        if args.dns_threshold is not None
        else profile.get("dns_threshold", DEFAULT_DNS_THRESHOLD)
    )
    user_agent = str(profile.get("user_agent", DEFAULT_USER_AGENT))

    probe_urls = [u.strip() for u in args.probe_url if (u or "").strip()]
    if not probe_urls:
        probe_urls = [str(u).strip() for u in profile.get("probe_urls", DEFAULT_PROBE_URLS) if str(u).strip()]

    configured_http_required = args.http_required_successes
    if configured_http_required is None:
        configured_http_required = profile.get("http_required_successes")
    if configured_http_required is None:
        quorum_rate = float(profile.get("http_quorum_rate", DEFAULT_HTTP_QUORUM_RATE))
        configured_http_required = max(1, math.ceil(len(probe_urls) * quorum_rate))
    http_required_successes = int(max(1, configured_http_required))
    if probe_urls:
        http_required_successes = min(http_required_successes, len(probe_urls))

    hosts = append_probe_hosts(read_seed_hosts(sample_size), probe_urls)

    dns_results = [probe_dns(host) for host in hosts]
    dns_ok_count = sum(1 for item in dns_results if item["dns_ok"])
    dns_total = len(dns_results)
    dns_ok_rate = (dns_ok_count / dns_total) if dns_total else 0.0

    http_results = [probe_http(url, timeout, user_agent) for url in probe_urls]
    http_total = len(http_results)
    http_ok_count = sum(1 for item in http_results if item["http_ok"])
    http_ok_rate = (http_ok_count / http_total) if http_total else 0.0
    http_ok = http_total > 0 and http_ok_count >= http_required_successes

    notes: list[str] = []
    if dns_total == 0:
        notes.append("seed_hosts_not_found")
    if http_total == 0:
        notes.append("http_probe_urls_not_found")
    if not http_ok:
        notes.append(f"http_probe_quorum_failed:{http_ok_count}/{http_total}")
    if dns_ok_rate < dns_threshold:
        notes.append(f"dns_ok_rate_below_threshold:{dns_ok_rate:.3f}")

    failure_kinds = sorted(
        {
            item.get("failure_kind", "")
            for item in http_results
            if not item.get("http_ok") and item.get("failure_kind")
        }
    )
    if failure_kinds:
        notes.append("http_failure_kinds:" + ",".join(failure_kinds))

    failed_probe_hosts: list[str] = []
    for item in http_results:
        if item.get("http_ok"):
            continue
        host = (urlparse(str(item.get("url", ""))).hostname or "").lower()
        if host:
            failed_probe_hosts.append(f"http_probe_failed:{host}")
    notes.extend(dedup_strings(failed_probe_hosts))

    passed = http_ok and dns_ok_rate >= dns_threshold

    output_path = Path(args.output_json) if args.output_json else build_default_output_path()
    summary = {
        "artifact_kind": ARTIFACT_KIND,
        "schema_name": SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "generated_by": SOURCE_CLI,
        "profile_path": str(profile_path),
        "timeout": timeout,
        "sample_size": sample_size,
        "dns_total": dns_total,
        "dns_ok_count": dns_ok_count,
        "dns_ok_rate": dns_ok_rate,
        "dns_threshold": dns_threshold,
        "http_probe_url": probe_urls[0] if probe_urls else "",
        "http_probe_urls": probe_urls,
        "http_probe_ok": http_ok,
        "http_total": http_total,
        "http_ok_count": http_ok_count,
        "http_ok_rate": http_ok_rate,
        "http_required_successes": http_required_successes,
        "seed_hosts": hosts,
        "dns_results": dns_results,
        "http_results": http_results,
        "notes": notes,
        "passed": passed,
        "wrapper_exit_code": 0 if passed else 1,
    }
    write_json(output_path, summary)

    print(f"[network-preflight] output={output_path}")
    print(
        f"[network-preflight] dns_ok_rate={dns_ok_rate:.3f} ({dns_ok_count}/{dns_total}) "
        f"http_ok={http_ok} ({http_ok_count}/{http_total}, required={http_required_successes})"
    )
    if not passed:
        print("[network-preflight] FAILED: rerun after restoring network trust/connectivity.")
        print("[network-preflight] steps: DNS check -> HTTPS check -> preflight rerun -> main run")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
