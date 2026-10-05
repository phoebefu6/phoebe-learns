#!/usr/bin/env python3
"""Check every url and doi in data.json with curl.

Usage: python3 scripts/check_links.py data.json

Pass: HTTP 200-299. A 403 from udemy.com, coursera.org, datacamp.com or a doi.org link prints
"verify by WebFetch" and does not fail (those hosts block curl).
Anything else fails. Exit 1 on any failure.
Python 3.11 stdlib only; needs curl on PATH.
"""
from __future__ import annotations

import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

SOFT_403_HOSTS = ("udemy.com", "coursera.org", "datacamp.com", "doi.org")


def collect(data: dict) -> list[tuple[str, str]]:
    """Return (url, where) pairs, deduped by url, in first-seen order."""
    seen: dict[str, str] = {}

    def add(url: str, where: str) -> None:
        if url and url not in seen:
            seen[url] = where

    for e in data.get("entries", []):
        eid = e.get("id", "?")
        add(e.get("url", ""), f"{eid} url")
        for group in ("linked_references", "support_readings"):
            for r in e.get(group, []):
                rid = r.get("id", "?")
                add(r.get("url", ""), f"{eid} {rid} url")
                if r.get("doi"):
                    add(f"https://doi.org/{r['doi']}", f"{eid} {rid} doi")
        for i, c in enumerate(e.get("linked_courses", [])):
            add(c.get("url", ""), f"{eid} course {i + 1}")
    return list(seen.items())


def probe(url: str) -> str:
    cmd = ["curl", "-sIL", "-A", "Mozilla/5.0", "--max-time", "15",
           "-o", "/dev/null", "-w", "%{http_code}", url]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        code = out.stdout.strip() or "000"
    except (subprocess.TimeoutExpired, OSError):
        code = "000"
    return code


def verdict(url: str, code: str) -> tuple[str, bool]:
    try:
        n = int(code)
    except ValueError:
        n = 0
    if 200 <= n < 300:
        return "pass", True
    host = urlparse(url).netloc.lower()
    if n == 403 and any(host == h or host.endswith("." + h) for h in SOFT_403_HOSTS):
        return "verify by WebFetch", True
    if n == 403 and url.startswith("https://doi.org/"):
        # publisher landing pages (ACM, Wiley, PNAS, OUP, MIT Press) bot-block curl after the doi redirect
        return "verify by WebFetch", True
    return "FAIL", False


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    with open(argv[1], encoding="utf-8") as fh:
        data = json.load(fh)
    items = collect(data)
    if not items:
        print("no urls or dois to check: pass")
        return 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        codes = list(pool.map(probe, [u for u, _ in items]))
    failures = 0
    width = min(max(len(u) for u, _ in items), 70)
    print(f"{'status':<6} {'result':<20} {'url':<{width}} where")
    for (url, where), code in zip(items, codes):
        label, ok = verdict(url, code)
        if not ok:
            failures += 1
        shown = url if len(url) <= width else url[: width - 3] + "..."
        print(f"{code:<6} {label:<20} {shown:<{width}} {where}")
    print(f"checked {len(items)} unique urls, {failures} failures")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
