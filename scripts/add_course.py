#!/usr/bin/env python3
"""Add one course to the Notion All Courses database from a link.

    NOTION_TOKEN=... python3 scripts/add_course.py --issue-body-env ISSUE_BODY --reply reply.md
    NOTION_TOKEN=... python3 scripts/add_course.py --url https://... [--domain "AI & LLMs"] [--title "..."]

Run by .github/workflows/notion.yml when Phoebe opens an "Add a course" issue.
It skips links already in Notion, reads the page title (or uses the one typed
in the form), picks the platform from the link and the domain from the form or
from title keywords, and creates the row as Not started with one star.
The reply file holds the Markdown comment the workflow posts on the issue.
Python 3.11 stdlib only.
"""
from __future__ import annotations

import argparse
import html
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import notion_lib  # noqa: E402

NO_ANSWER = {"", "_no response_", "guess for me", "none"}


def parse_issue_body(body: str) -> dict:
    """Issue forms render as '### Label' headings, each followed by the answer."""
    out, label = {}, None
    for line in body.splitlines():
        m = re.match(r"^###\s+(.*)$", line)
        if m:
            label = m.group(1).strip().lower()
            out[label] = ""
        elif label is not None and line.strip():
            out[label] = (out[label] + " " + line.strip()).strip()
    return {
        "url": out.get("course link", ""),
        "domain": out.get("domain", ""),
        "title": out.get("course title (optional)", ""),
    }


def fetch_title(url: str) -> str:
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 phoebe-learns",
            "Accept-Language": "en,zh;q=0.8"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            page = resp.read(600_000).decode("utf-8", "replace")
    except Exception:  # noqa: BLE001 - any failure falls back to the link itself
        page = ""
    for pat in (r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)',
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:title',
                r"<title[^>]*>(.*?)</title>"):
        m = re.search(pat, page, re.I | re.S)
        if m:
            t = html.unescape(re.sub(r"\s+", " ", m.group(1))).strip()
            t = re.split(r"\s+[|]\s+", t)[0]
            t = re.sub(r"\s+[-]\s+(Coursera|Udemy|DataCamp|LinkedIn.*|DeepLearning\.AI|365 Data Science)$", "", t)
            if t and t.lower() not in {"just a moment...", "access denied", "attention required!"}:
                return t
    # Fallback: the last meaningful path segment, title-cased.
    parts = [p for p in urllib.parse.urlparse(url).path.split("/") if p and not p.isdigit()]
    skip = {"learn", "courses", "course", "specializations", "paths", "skill-tracks", "tracks", "preview",
            "home", "module", "lecture", "overview", "welcome", "introduction-to-the-course"}
    for p in reversed(parts):
        if p.lower() not in skip:
            return urllib.parse.unquote(p).replace("-", " ").replace("_", " ").strip().title()
    return url


def add(url: str, domain: str, title: str) -> str:
    url = url.strip()
    if not re.match(r"^https?://[^\s/]+\.[^\s/]+", url):
        return f"That does not look like a course link: `{url}`. Nothing was added."
    existing = notion_lib.find_by_url(url)
    if existing:
        return (f"**{existing['title']}** is already in Notion "
                f"([open](https://www.notion.so/{existing['id']})). Nothing was added.")
    title = title.strip() if title.strip().lower() not in NO_ANSWER else fetch_title(url)
    domain = domain.strip()
    if domain.lower() in NO_ANSWER or domain not in notion_lib.DOMAIN_IDS:
        domain = notion_lib.guess_domain(title, url)
    platform = notion_lib.platform_for_url(url)
    created = notion_lib.create_course(title, url, platform, domain)
    lines = [f"Added **{title}** to Notion ([open](https://www.notion.so/{created['id']})).",
             "", f"- Platform: {platform}", "- Status: Not started, rated 1 star"]
    if domain:
        lines.append(f"- Domain: {domain}")
        lines.append("")
        lines.append("It appears on https://phoebefu6.github.io/phoebe-learns/ within a few minutes.")
    else:
        lines.append("- Domain: not set. Pick one in Notion and it appears on the site at the next daily sync.")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--issue-body-env", help="name of the env var holding the issue body")
    ap.add_argument("--url", default="")
    ap.add_argument("--domain", default="")
    ap.add_argument("--title", default="")
    ap.add_argument("--reply", type=Path, help="write the issue comment here")
    args = ap.parse_args(argv)
    fields = (parse_issue_body(os.environ.get(args.issue_body_env, "")) if args.issue_body_env
              else {"url": args.url, "domain": args.domain, "title": args.title})
    try:
        reply = add(fields["url"], fields["domain"], fields["title"])
        code = 0
    except notion_lib.NotionError as exc:
        reply, code = f"Could not add the course: {exc}", 1
    print(reply)
    if args.reply:
        args.reply.write_text(reply + "\n", encoding="utf-8")
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
