#!/usr/bin/env python3
"""Validate phoebe-learns entries.

Usage:
  python3 scripts/validate.py entries/<id>
  python3 scripts/validate.py --all

Prints one "path: rule" line per failure and exits 1 if anything failed.
build.py imports validate_entry() and runs it before rendering.
Python 3.11 stdlib only.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ENTRIES_DIR = REPO / "entries"
DOMAINS_FILE = REPO / "domains.json"

ID_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9-]+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PLATFORMS = {"Coursera Plus", "365 Data Science", "DataCamp", "Udemy",
             "DeepLearning.AI", "Notion export", "Other"}
SOURCE_TYPES = {"course", "notes"}
STATUSES = {"to-do", "in-progress", "done"}
RESEARCH_STATUSES = {"full", "none"}
REF_ROLES = {"support", "opposes", "extends", "reframes"}
READING_ROLES = {"deepen", "widen", "practitioner"}
TIERS = {"PRIMARY", "SECONDARY", "UNVERIFIED", "CONTRADICTED", "SUPERSEDED"}
FITS = {"prereq", "deepen", "widen"}
BANNED_CHARS = {
    "\u2014": "em dash U+2014",
    "\u2013": "en dash U+2013",
    "\u2717": "cross mark U+2717",
    "\u2715": "cross mark U+2715",
    "\u00d7": "cross mark U+00D7",
    "\u274c": "cross mark U+274C",
}
REQUIRED_KEYS = ["id", "topic", "domain", "platform", "source_type", "url", "tags",
                 "status", "start_date", "end_date", "supporting_doc", "main_ideas",
                 "key_points", "linked_references", "support_readings",
                 "linked_courses", "research_status", "created", "updated"]


def load_domain_ids(domains_file: Path = DOMAINS_FILE) -> set[str]:
    try:
        data = json.loads(domains_file.read_text(encoding="utf-8"))
        return {d["id"] for d in data.get("domains", [])}
    except (OSError, ValueError, KeyError, TypeError):
        return set()


def _walk_strings(obj, path=""):
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _walk_strings(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk_strings(v, f"{path}[{i}]")


def _is_date_or_null(v) -> bool:
    return v is None or (isinstance(v, str) and bool(DATE_RE.match(v)))


def _check_reference(ref, where, roles, errs):
    if not isinstance(ref, dict):
        errs.append(f"{where}: must be an object")
        return
    for k in ("id", "title", "role", "tier"):
        if not isinstance(ref.get(k), str) or not ref.get(k):
            errs.append(f"{where}.{k}: required non-empty string")
    if ref.get("role") not in roles:
        errs.append(f"{where}.role: must be one of {sorted(roles)}")
    if ref.get("tier") not in TIERS:
        errs.append(f"{where}.tier: must be one of {sorted(TIERS)}")
    if not (ref.get("url") or ref.get("doi")):
        errs.append(f"{where}: url or doi must be non-empty")
    if "year" in ref and ref["year"] is not None and not isinstance(ref["year"], int):
        errs.append(f"{where}.year: must be an integer or null")
    if "cited_by" in ref and ref["cited_by"] is not None and not isinstance(ref["cited_by"], int):
        errs.append(f"{where}.cited_by: must be an integer or null")


def validate_entry(folder: Path, domain_ids: set[str] | None = None) -> list[str]:
    """Return a list of 'path: rule' failure lines (empty when valid)."""
    folder = Path(folder)
    if domain_ids is None:
        domain_ids = load_domain_ids()
    errs: list[str] = []
    ej = folder / "entry.json"
    rel = str(ej.relative_to(REPO)) if ej.is_relative_to(REPO) else str(ej)

    if not ej.exists():
        return [f"{rel}: entry.json missing"]
    try:
        e = json.loads(ej.read_text(encoding="utf-8"))
    except ValueError as exc:
        return [f"{rel}: invalid JSON ({exc})"]
    if not isinstance(e, dict):
        return [f"{rel}: top level must be an object"]

    for k in REQUIRED_KEYS:
        if k not in e:
            errs.append(f"{rel}: missing key '{k}'")
    if errs:
        return errs

    # Banned characters anywhere in any string.
    for path, s in _walk_strings(e):
        for ch, name in BANNED_CHARS.items():
            if ch in s:
                errs.append(f"{rel}: {path} contains {name}")

    # Identity.
    if not isinstance(e["id"], str) or not ID_RE.match(e["id"]):
        errs.append(f"{rel}: id must match ^\\d{{4}}-\\d{{2}}-\\d{{2}}-[a-z0-9-]+$")
    if e["id"] != folder.name:
        errs.append(f"{rel}: id '{e['id']}' != folder name '{folder.name}'")
    if not isinstance(e["topic"], str) or not e["topic"].strip():
        errs.append(f"{rel}: topic must be a non-empty string")
    if e["domain"] not in domain_ids:
        errs.append(f"{rel}: domain '{e['domain']}' not in domains.json")
    if e["platform"] not in PLATFORMS:
        errs.append(f"{rel}: platform must be one of {sorted(PLATFORMS)}")
    if e["source_type"] not in SOURCE_TYPES:
        errs.append(f"{rel}: source_type must be course or notes")
    if not isinstance(e["url"], str):
        errs.append(f"{rel}: url must be a string (may be empty for notes)")
    if e["source_type"] == "course" and e["url"] and not e["url"].startswith("http"):
        errs.append(f"{rel}: url must start with http")

    # Tags.
    if not isinstance(e["tags"], list) or not all(isinstance(t, str) for t in e["tags"]):
        errs.append(f"{rel}: tags must be a list of strings")
    else:
        for t in e["tags"]:
            if t != t.lower():
                errs.append(f"{rel}: tag '{t}' must be lowercase")

    # Status and dates.
    if e["status"] not in STATUSES:
        errs.append(f"{rel}: status must be one of {sorted(STATUSES)}")
    if not _is_date_or_null(e["start_date"]):
        errs.append(f"{rel}: start_date must be ISO yyyy-mm-dd or null")
    if not _is_date_or_null(e["end_date"]):
        errs.append(f"{rel}: end_date must be ISO yyyy-mm-dd or null")
    if e["status"] == "done" and not e["end_date"]:
        errs.append(f"{rel}: end_date required when status == done")
    for k in ("created", "updated"):
        if not (isinstance(e[k], str) and DATE_RE.match(e[k])):
            errs.append(f"{rel}: {k} must be ISO yyyy-mm-dd")

    # Supporting docs.
    if not isinstance(e["supporting_doc"], str) or not e["supporting_doc"]:
        errs.append(f"{rel}: supporting_doc must be a non-empty string")
    if not (folder / "notes.md").exists():
        errs.append(f"{rel}: notes.md must exist")
    if "source_file" in e:
        sf = e["source_file"]
        if not (isinstance(sf, str) and sf.startswith("source/")):
            errs.append(f"{rel}: source_file must look like source/<file>")
        elif not (folder / sf).exists():
            errs.append(f"{rel}: source_file '{sf}' does not exist")

    # Research status drives the counts.
    rs = e["research_status"]
    if rs not in RESEARCH_STATUSES:
        errs.append(f"{rel}: research_status must be full or none")
    full = rs == "full"
    if full and not (folder / "research.md").exists():
        errs.append(f"{rel}: research.md must exist when research_status == full")

    mi = e["main_ideas"]
    if not isinstance(mi, list) or not all(isinstance(x, str) and x.strip() for x in mi):
        errs.append(f"{rel}: main_ideas must be a list of non-empty strings")
    elif full and len(mi) != 3:
        errs.append(f"{rel}: main_ideas must have exactly 3 items when research_status == full")
    elif not full and len(mi) > 3:
        errs.append(f"{rel}: main_ideas must have 0-3 items")

    # References.
    refs = e["linked_references"]
    ref_ids: set[str] = set()
    if not isinstance(refs, list):
        errs.append(f"{rel}: linked_references must be a list")
        refs = []
    for i, r in enumerate(refs):
        _check_reference(r, f"{rel}: linked_references[{i}]", REF_ROLES, errs)
        if isinstance(r, dict) and isinstance(r.get("id"), str):
            if r["id"] in ref_ids:
                errs.append(f"{rel}: linked_references[{i}].id '{r['id']}' duplicated")
            ref_ids.add(r["id"])

    kps = e["key_points"]
    if not isinstance(kps, list):
        errs.append(f"{rel}: key_points must be a list")
        kps = []
    for i, kp in enumerate(kps):
        where = f"{rel}: key_points[{i}]"
        if not isinstance(kp, dict):
            errs.append(f"{where}: must be an object")
            continue
        for k in ("id", "claim", "disagreement"):
            if not isinstance(kp.get(k), str) or not kp.get(k).strip():
                errs.append(f"{where}.{k}: required non-empty string")
        for k in ("supporting", "other_angles"):
            lst = kp.get(k)
            if not isinstance(lst, list) or not all(isinstance(x, str) for x in lst):
                errs.append(f"{where}.{k}: must be a list of reference ids")
                continue
            if full and len(lst) != 3:
                errs.append(f"{where}.{k}: must list exactly 3 reference ids when research_status == full")
            for rid in lst:
                if rid not in ref_ids:
                    errs.append(f"{where}.{k}: reference id '{rid}' not in linked_references")

    sr = e["support_readings"]
    if not isinstance(sr, list):
        errs.append(f"{rel}: support_readings must be a list")
        sr = []
    if full and len(sr) != 5:
        errs.append(f"{rel}: support_readings must have exactly 5 items when research_status == full")
    for i, r in enumerate(sr):
        _check_reference(r, f"{rel}: support_readings[{i}]", READING_ROLES, errs)

    lc = e["linked_courses"]
    if not isinstance(lc, list):
        errs.append(f"{rel}: linked_courses must be a list")
        lc = []
    if full and len(lc) != 5:
        errs.append(f"{rel}: linked_courses must have exactly 5 items when research_status == full")
    for i, c in enumerate(lc):
        where = f"{rel}: linked_courses[{i}]"
        if not isinstance(c, dict):
            errs.append(f"{where}: must be an object")
            continue
        for k in ("title", "url"):
            if not isinstance(c.get(k), str) or not c.get(k):
                errs.append(f"{where}.{k}: required non-empty string")
        if c.get("platform") not in PLATFORMS:
            errs.append(f"{where}.platform: must be one of {sorted(PLATFORMS)}")
        if c.get("fit") not in FITS:
            errs.append(f"{where}.fit: must be one of {sorted(FITS)}")
        tb = c.get("taught_by_phoebe")
        if tb is not None and not (isinstance(tb, str) and re.match(r"^learn-[a-z0-9-]+-with-phoebe$", tb)):
            errs.append(f"{where}.taught_by_phoebe: must be a learn-*-with-phoebe slug or null")

    return errs


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return 2
    domain_ids = load_domain_ids()
    if not domain_ids:
        print("domains.json: unreadable or empty; run build.py once to generate it")
        return 1
    if argv[1] == "--all":
        folders = sorted(p for p in ENTRIES_DIR.iterdir() if p.is_dir())
    else:
        folders = [Path(a).resolve() for a in argv[1:]]
    failures = 0
    for f in folders:
        errs = validate_entry(f, domain_ids)
        for line in errs:
            print(line)
        failures += len(errs)
    print(f"validated {len(folders)} entries, {failures} failures")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
