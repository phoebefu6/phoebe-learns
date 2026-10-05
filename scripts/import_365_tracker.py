#!/usr/bin/env python3
"""Import the 365 Data Science finish tracker into entries/ as to-do stubs.

Reads ~/Documents/Claude_Work/Learning/365-finish-tracker.md, creates one
entries/<date>-<slug>/ folder per unticked course row, and never touches
the tracker itself. Idempotent: folders that already exist are skipped.

Usage: python3 scripts/import_365_tracker.py [path-to-tracker.md]
Python 3.11 stdlib only.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ENTRIES_DIR = REPO / "entries"
DEFAULT_TRACKER = Path.home() / "Documents/Claude_Work/Learning/365-finish-tracker.md"
TODAY = "2026-10-05"

# First match wins on the text before any "/".
TRACK_TO_DOMAIN = [
    ("Data Science", "ds"),
    ("Data Analytics", "data"),
    ("Programming", "prog"),
    ("AI & LLMs", "ai"),
    ("AI Literacy", "ai"),
    ("RAG", "ai"),
    ("AI + Data Analysis", "aiap"),
    ("Applied AI", "aiap"),
    ("Leadership", "lead"),
    ("AI + Management", "lead"),
    ("Data & AI Governance", "gov"),
    ("Visual Thinking", "viz"),
    ("Data Engineering & Infra", "deng"),
    ("Communications", "comm"),
]
STOPWORDS = {
    "a", "an", "and", "the", "to", "of", "in", "with", "for", "on", "at", "by",
    "from", "intro", "introduction", "introducing", "course", "complete", "using",
    "your", "vs", "how", "like", "or", "building", "build", "think", "starting",
    "prep", "everyone", "work", "hero", "working", "files", "understanding",
    "bernard", "marr", "ken", "jee", "101", "102", "r", "s",
}
# merge known two-word names into one tag and keep platform words whole
PHRASES = {
    "power bi": "power-bi", "power query": "power-query", "data science": "data-science",
    "machine learning": "machine-learning", "deep learning": "deep-learning",
    "data engineering": "data-engineering", "data analysis": "data-analysis",
    "data visualization": "data-visualization", "data architecture": "data-architecture",
    "data warehousing": "data-warehousing", "data literacy": "data-literacy",
    "data strategy": "data-strategy", "ai strategy": "ai-strategy", "ai agents": "ai-agents",
    "agentic ai": "agentic-ai", "generative ai": "generative-ai", "vector databases": "vector-databases",
    "hugging face": "hugging-face", "google cloud": "google-cloud", "amazon redshift": "redshift",
    "microsoft azure": "azure", "aws cloud": "aws", "cloud computing": "cloud",
    "pivot tables": "pivot-tables", "text files": "text-files", "dates and times": "datetime",
    "data preprocessing": "preprocessing", "data cleaning": "data-cleaning",
    "business reports": "reporting", "coding interview": "interview-prep",
    "data science interviews": "interview-prep", "career in data science": "career",
}
PLACEHOLDER_MARK = "paste your 13"


def slugify(title: str) -> str:
    s = title.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def tags_for(title: str) -> list[str]:
    """Phrase tags first (power-bi, data-science), then single words, 4 max, no stopwords."""
    t = title.lower()
    out: list[str] = []
    for phrase, tag in PHRASES.items():
        if phrase in t and tag not in out:
            out.append(tag)
            t = t.replace(phrase, " ")
    for w in re.findall(r"[a-z0-9]+", t):
        if w in STOPWORDS or w in out or len(w) < 3:
            continue
        out.append(w)
    return out[:4]


def map_domain(track: str, warnings: list[str], title: str) -> str:
    head = track.split("/")[0].strip()
    for key, dom in TRACK_TO_DOMAIN:
        if head == key or head.startswith(key):
            return dom
    warnings.append(f"unmapped track '{track}' for '{title}' -> ds")
    return "ds"


def clean_title(raw: str) -> str:
    t = raw.replace("*(confirm in account)*", "")
    t = re.sub(r"\s+", " ", t).strip()
    return t


def parse_rows(md: str):
    """Yield (wave_heading, title, track) for every unticked course row."""
    wave = ""
    for line in md.splitlines():
        if line.startswith("## "):
            wave = line[3:].strip()
            continue
        if not line.startswith("| [ ] |"):
            continue
        if PLACEHOLDER_MARK in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        title = clean_title(cells[1])
        if not title:
            continue
        yield wave, title, cells[2]


def main(argv: list[str]) -> int:
    tracker = Path(argv[1]) if len(argv) > 1 else DEFAULT_TRACKER
    if not tracker.exists():
        print(f"tracker not found: {tracker}")
        return 1
    md = tracker.read_text(encoding="utf-8")
    warnings: list[str] = []
    created = skipped = 0
    for wave, title, track in parse_rows(md):
        eid = f"{TODAY}-{slugify(title)}"
        folder = ENTRIES_DIR / eid
        if folder.exists():
            skipped += 1
            continue
        domain = map_domain(track, warnings, title)
        entry = {
            "id": eid,
            "topic": title,
            "domain": domain,
            "platform": "365 Data Science",
            "source_type": "course",
            "url": "",
            "tags": tags_for(title),
            "status": "to-do",
            "start_date": None,
            "end_date": None,
            "supporting_doc": "notes.md",
            "main_ideas": [],
            "key_points": [],
            "linked_references": [],
            "support_readings": [],
            "linked_courses": [],
            "research_status": "none",
            "created": TODAY,
            "updated": TODAY,
        }
        folder.mkdir(parents=True)
        (folder / "entry.json").write_text(json.dumps(entry, indent=2, ensure_ascii=False) + "\n",
                                           encoding="utf-8")
        notes = (f"# {title}\n\n"
                 f"Imported from the 365 Data Science finish tracker on {TODAY}. Wave: {wave}.\n\n"
                 f"Notes not written yet.\n")
        (folder / "notes.md").write_text(notes, encoding="utf-8")
        created += 1
    print(f"created {created} entries, skipped {skipped} existing")
    for w in warnings:
        print(f"warning: {w}")
    if not warnings:
        print("no mapping warnings")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
