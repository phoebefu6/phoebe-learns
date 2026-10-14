#!/usr/bin/env python3
"""Sync the Notion "All Courses" database into entries/.

    NOTION_TOKEN=... python3 scripts/sync_notion.py           # read live from Notion
    python3 scripts/sync_notion.py --from-json export.json    # read a saved export instead
    python3 scripts/sync_notion.py --dry-run                  # report only, write nothing

Notion is the source of truth for courses. One direction only: Notion -> site.

- Only course details go public: title, domain, platform, status, rating, tags,
  link and end date. Page bodies (Phoebe's Notion notes) are never read.
- A Notion row matches an existing entry by notion_id, then by link, then by
  title. A match updates status, end_date, rating, domain, platform and
  notion_id. Topic, tags, notes and research written on the site are kept.
- A row with no match becomes a new entry with research_status "none" and a
  stub notes.md.
- Skipped: rows with no title, titles marked "(duplicate?)", and rows with no
  Domain yet. Each skip is printed.
- An entry whose notion_id is gone from Notion is removed if it only holds
  synced data. If it has research, it is kept and a warning is printed.
- Entries with no notion_id (written by learning-buddy, or imported) are never
  touched.

Python 3.11 stdlib only.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import shutil
import sys
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import notion_lib  # noqa: E402

ENTRIES_DIR = REPO / "entries"
TODAY = _dt.date.today().isoformat()
RECENT = (_dt.date.today() - _dt.timedelta(days=7)).isoformat()
STUB_MARK = "Synced from Notion (All Courses)"
REPLACEMENTS = {"—": "-", "–": "-", "✗": "x", "✕": "x", "×": "x", "❌": "x"}


def clean(s: str) -> str:
    for bad, good in REPLACEMENTS.items():
        s = s.replace(bad, good)
    return re.sub(r"\s+", " ", s).strip()


def norm_url(u: str) -> str:
    u = (u or "").strip().lower()
    u = re.sub(r"^https?://(www\.)?", "", u)
    u = re.split(r"[?#]", u)[0]
    return u.rstrip("/")


def norm_title(t: str) -> str:
    t = unicodedata.normalize("NFKC", t or "").casefold()
    return re.sub(r"[\W_]+", "", t)


def slugify(title: str, fallback: str) -> str:
    s = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii").lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    s = "-".join(s.split("-")[:8])
    return s if len(s) >= 3 else f"course-{fallback[:8]}"


def load_entries() -> list[tuple[Path, dict]]:
    out = []
    for folder in sorted(p for p in ENTRIES_DIR.iterdir() if p.is_dir()):
        ej = folder / "entry.json"
        if ej.exists():
            out.append((folder, json.loads(ej.read_text(encoding="utf-8"))))
    return out


def synced_fields(row: dict) -> dict:
    status = notion_lib.STATUS_FROM_NOTION.get(row.get("status") or "", "to-do")
    end = row.get("end_date")
    f = {
        "status": status,
        "end_date": end,
        "rating": int(row.get("rating") or 1),
        "domain": notion_lib.DOMAIN_IDS[row["domain"]],
        "platform": notion_lib.PLATFORM_TO_SITE.get(row.get("platform") or "", row.get("platform") or "Other"),
        "notion_id": row["id"],
    }
    if status == "done" and not end:
        f["end_date_unknown"] = True
    return f


def is_stub_only(folder: Path, e: dict) -> bool:
    if e.get("research_status") != "none":
        return False
    notes = folder / "notes.md"
    return not notes.exists() or STUB_MARK in notes.read_text(encoding="utf-8")


def sync(rows: list[dict], dry_run: bool) -> dict:
    entries = load_entries()
    by_nid = {e.get("notion_id"): (f, e) for f, e in entries if e.get("notion_id")}
    by_url = {norm_url(e["url"]): (f, e) for f, e in entries if e.get("url")}
    by_title = {norm_title(e["topic"]): (f, e) for f, e in entries}
    taken = {f.name for f, _ in entries}
    stats = {"created": 0, "updated": 0, "unchanged": 0, "removed": 0, "skipped": 0}
    seen_nids = set()

    for row in rows:
        title = clean(row.get("title") or "")
        if not title:
            stats["skipped"] += 1
            print(f"skip   {row['id']}: no title")
            continue
        if "(duplicate?)" in title:
            stats["skipped"] += 1
            print(f"skip   {title}: marked as a possible duplicate")
            continue
        if row.get("domain") not in notion_lib.DOMAIN_IDS:
            stats["skipped"] += 1
            print(f"skip   {title}: no Domain in Notion yet")
            continue
        seen_nids.add(row["id"])
        fields = synced_fields(row)

        hit = (by_nid.get(row["id"]) or (by_url.get(norm_url(row.get("url"))) if row.get("url") else None)
               or by_title.get(norm_title(title)))
        if hit:
            folder, e = hit
            before = json.dumps(e, sort_keys=True)
            if fields.get("end_date_unknown") and e.get("status") != "done":
                # Marked Done in Notion without an End Date since the last sync: it finished
                # between then and now, so record today rather than "unknown".
                fields["end_date"] = TODAY
                fields.pop("end_date_unknown")
            e.update(fields)
            if not fields.get("end_date_unknown"):
                e.pop("end_date_unknown", None)
            if json.dumps(e, sort_keys=True) == before:
                stats["unchanged"] += 1
                continue
            e["updated"] = TODAY
            stats["updated"] += 1
            print(f"update {folder.name}")
            if not dry_run:
                (folder / "entry.json").write_text(json.dumps(e, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            continue

        added = row.get("added") or TODAY
        if fields.get("end_date_unknown") and added >= RECENT:
            # Added and finished within the last week: today is the honest finish date.
            fields["end_date"] = TODAY
            fields.pop("end_date_unknown")
        base = f"{added}-{slugify(title, row['id'])}"
        eid, n = base, 2
        while eid in taken:
            eid, n = f"{base}-{n}", n + 1
        taken.add(eid)
        url = row.get("url") or ""
        e = {
            "id": eid, "topic": title, "domain": fields["domain"], "platform": fields["platform"],
            "source_type": "course", "url": url if url.startswith("http") else "",
            "tags": sorted({clean(t).lower() for t in row.get("tags") or [] if clean(t)}),
            "status": fields["status"], "start_date": None, "end_date": fields["end_date"],
            "supporting_doc": "notes.md", "main_ideas": [], "key_points": [], "linked_references": [],
            "support_readings": [], "linked_courses": [], "research_status": "none",
            "created": added, "updated": TODAY,
            "rating": fields["rating"], "notion_id": row["id"],
        }
        if fields.get("end_date_unknown"):
            e["end_date_unknown"] = True
        stats["created"] += 1
        print(f"create {eid}")
        if not dry_run:
            folder = ENTRIES_DIR / eid
            folder.mkdir()
            (folder / "entry.json").write_text(json.dumps(e, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            (folder / "notes.md").write_text(
                f"# {title}\n\n{STUB_MARK} on {TODAY}. Course notes stay in Notion.\n", encoding="utf-8")

    for nid, (folder, e) in by_nid.items():
        if nid in seen_nids:
            continue
        if is_stub_only(folder, e):
            stats["removed"] += 1
            print(f"remove {folder.name}: gone from Notion (or now skipped there)")
            if not dry_run:
                shutil.rmtree(folder)
        else:
            print(f"warn   {folder.name}: gone from Notion but holds research; kept")
    return stats


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--from-json", type=Path, help="read rows from a saved export instead of the API")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    try:
        rows = (json.loads(args.from_json.read_text(encoding="utf-8")) if args.from_json
                else notion_lib.fetch_all_rows())
    except notion_lib.NotionError as exc:
        print(f"error: {exc}")
        return 1
    if not rows:
        # An empty answer almost always means the integration lost access. Never wipe the site on it.
        print("error: Notion returned no courses; nothing changed")
        return 1
    stats = sync(rows, args.dry_run)
    print(f"{len(rows)} Notion rows: " + ", ".join(f"{v} {k}" for k, v in stats.items())
          + (" (dry run)" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
