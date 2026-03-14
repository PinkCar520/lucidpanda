#!/usr/bin/env python3
"""RSS source health checker for AlphaSignal.

Usage:
  python scripts/diagnostics/check_rss_feeds.py
  python scripts/diagnostics/check_rss_feeds.py --raw
  python scripts/diagnostics/check_rss_feeds.py --timeout 20
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from collections import Counter
from urllib.parse import urlparse

import feedparser
import httpx

# Add project root to import path
sys.path.append(os.getcwd())

from src.alphasignal.providers.data_sources.rsshub import RSSHubSource, TIER1_FEEDS_CONFIG

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


async def _probe_source(
    config: dict,
    source_filter: RSSHubSource,
    client: httpx.AsyncClient,
    ssl_client: httpx.AsyncClient,
    timeout_s: float,
    raw_mode: bool,
) -> dict:
    name = config["name"]
    url = config["url"]
    category = config["category"]

    host = urlparse(url).hostname or ""
    active_client = ssl_client if "reuters" in host else client

    started_at = time.perf_counter()
    status = {
        "name": name,
        "category": category,
        "url": url,
        "status": "unknown",
        "http_status": 0,
        "entries": 0,
        "passed": 0,
        "filtered": 0,
        "elapsed_ms": 0,
        "reason": "",
    }

    try:
        resp = await active_client.get(url, timeout=timeout_s)
        status["http_status"] = resp.status_code
        if resp.status_code != 200:
            status["status"] = "failed"
            status["reason"] = f"HTTP {resp.status_code}"
            return status

        feed = feedparser.parse(resp.content)
        entries = getattr(feed, "entries", []) or []
        status["entries"] = len(entries)

        if not entries:
            status["status"] = "ok_empty"
            status["reason"] = "feed 无条目"
            return status

        if raw_mode:
            status["passed"] = len(entries)
            status["status"] = "ok_new"
            return status

        passed = 0
        filtered = 0
        for entry in entries:
            title = getattr(entry, "title", "").strip()
            summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
            full_text = f"{title} {summary}".lower()

            if source_filter._is_noise(full_text):
                filtered += 1
                continue
            if not source_filter._passes_category_filter(category, full_text):
                filtered += 1
                continue
            passed += 1

        status["passed"] = passed
        status["filtered"] = filtered
        status["status"] = "ok_new" if passed > 0 else "ok_empty"
        if passed == 0:
            status["reason"] = "过滤后无可用条目"
        return status
    except Exception as exc:
        status["status"] = "failed"
        status["reason"] = str(exc)
        return status
    finally:
        status["elapsed_ms"] = int((time.perf_counter() - started_at) * 1000)


async def _run(args: argparse.Namespace) -> int:
    filter_source = RSSHubSource(db=None)

    async with httpx.AsyncClient(headers=_DEFAULT_HEADERS, verify=True) as client, httpx.AsyncClient(
        headers=_DEFAULT_HEADERS, verify=False
    ) as ssl_client:
        tasks = [
            _probe_source(
                cfg,
                filter_source,
                client,
                ssl_client,
                timeout_s=args.timeout,
                raw_mode=args.raw,
            )
            for cfg in TIER1_FEEDS_CONFIG
        ]
        results = await asyncio.gather(*tasks)

    counters = Counter(r["status"] for r in results)

    print("\n=== RSS Source Health Report ===")
    print(
        f"total={len(results)} | ok_new={counters.get('ok_new', 0)} | "
        f"ok_empty={counters.get('ok_empty', 0)} | failed={counters.get('failed', 0)}"
    )
    print("mode=raw" if args.raw else "mode=filtered")

    for r in results:
        if r["status"] == "failed":
            print(
                f"❌ [{r['category']}] {r['name']} | {r['reason']} | "
                f"http={r['http_status']} | elapsed={r['elapsed_ms']}ms"
            )
        else:
            reason_suffix = f" | reason={r['reason']}" if r["reason"] else ""
            print(
                f"✅ [{r['category']}] {r['name']} | {r['status']} | "
                f"entries={r['entries']} | passed={r['passed']} | "
                f"filtered={r['filtered']} | elapsed={r['elapsed_ms']}ms{reason_suffix}"
            )

    return 0 if counters.get("failed", 0) == 0 else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check health of configured RSS sources.")
    parser.add_argument("--timeout", type=float, default=15.0, help="HTTP timeout in seconds (default: 15)")
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Do not apply AlphaSignal content filters (only check HTTP + feed entries).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_run(parse_args())))
