#!/usr/bin/env python3
"""Tick "Today's pick" on one course in Notion All Courses, and untick yesterday's.

    NOTION_TOKEN=... python3 scripts/daily_pick.py [--date 2026-10-14] [--dry-run]

Run each morning by .github/workflows/notion.yml. The Learning Dashboard page in
Notion shows the ticked course. How the pick is made:

- Candidates are courses In progress or Not started (never Done, never a
  "(duplicate?)" row).
- In progress courses get 3 tickets each, Not started courses 1 ticket, plus one
  extra ticket per star above one. Finishing what is started comes first.
- The draw is seeded by the date, so a re-run on the same day gives the same
  course, and yesterday's pick is excluded so it changes every day.
Python 3.11 stdlib only.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import notion_lib  # noqa: E402

WEIGHT = {"In progress": 3, "Not started": 1}


def choose(rows: list[dict], day: str) -> dict | None:
    yesterday = {r["id"] for r in rows if r.get("pick")}
    pool = [r for r in rows
            if r.get("status") in WEIGHT and r.get("title") and "(duplicate?)" not in r["title"]
            and r["id"] not in yesterday]
    if not pool:
        return None
    pool.sort(key=lambda r: r["id"])
    weights = [WEIGHT[r["status"]] + max(0, int(r.get("rating") or 1) - 1) for r in pool]
    seed = int(hashlib.sha256(day.encode()).hexdigest()[:12], 16)
    return random.Random(seed).choices(pool, weights=weights, k=1)[0]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--date", default=_dt.datetime.now(_dt.timezone(_dt.timedelta(hours=8))).date().isoformat(),
                    help="the day to pick for (default: today in Singapore)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    try:
        rows = notion_lib.fetch_all_rows()
        pick = choose(rows, args.date)
        if pick is None:
            print("nothing left to pick: every course is done")
            return 0
        print(f"{args.date}: {pick['title']} ({pick['status']})")
        if args.dry_run:
            return 0
        for r in rows:
            if r.get("pick") and r["id"] != pick["id"]:
                notion_lib.set_pick(r["id"], False)
        notion_lib.set_pick(pick["id"], True)
    except notion_lib.NotionError as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
