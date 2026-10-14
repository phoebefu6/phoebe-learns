#!/usr/bin/env python3
"""Build the phoebe-learns static site.

    python3 build.py

Walks entries/, validates every entry.json (scripts/validate.py), renders
index.html, network.html, entries/<id>/index.html and data.json, and
refreshes domains.json from the learn-with-phoebe hub when it is readable.
Python 3.11 stdlib only. No network access.
"""
from __future__ import annotations

import datetime as _dt
import html
import itertools
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO / "scripts"))
from validate import validate_entry  # noqa: E402

ENTRIES_DIR = REPO / "entries"
TEMPLATES = REPO / "templates"
DOMAINS_FILE = REPO / "domains.json"
EXTRA_DOMAINS_FILE = REPO / "domains-extra.json"
HUB_COURSES = Path.home() / "Documents/Claude_Work/github_repo/learn-with-phoebe/courses.json"
SITE_URL = "https://phoebefu6.github.io/phoebe-learns/"
TODAY = _dt.date.today().isoformat()
STATUS_LABEL = {"to-do": "To do", "in-progress": "In progress", "done": "Done"}
STATUS_GLYPH = {"to-do": "glyph", "in-progress": "glyph half", "done": "glyph full"}
ROLE_CLASS = {"support": "tint", "opposes": "outline-plum", "extends": "outline-muted",
              "reframes": "outline-muted", "deepen": "outline-muted", "widen": "outline-muted", "practitioner": "outline-muted"}
TIER_CLASS = {"PRIMARY": "solid", "SECONDARY": "tint", "UNVERIFIED": "outline-muted",
              "CONTRADICTED": "outline-muted", "SUPERSEDED": "outline-muted"}


# ---------------------------------------------------------------- domains ----
def refresh_domains() -> list[dict]:
    """Hub domains (refreshed from the hub when readable) plus domains-extra.json."""
    domains = _hub_domains()
    try:
        extra = json.loads(EXTRA_DOMAINS_FILE.read_text(encoding="utf-8"))["domains"]
    except (OSError, ValueError, KeyError) as exc:
        print(f"warning: domains-extra.json unreadable ({exc}); building with hub domains only")
        extra = []
    known = {d["id"] for d in domains}
    return domains + [d for d in extra if d["id"] not in known]


def _hub_domains() -> list[dict]:
    """Regenerate domains.json from the hub; fall back to the committed copy."""
    try:
        hub = json.loads(HUB_COURSES.read_text(encoding="utf-8"))
        buckets = [{"id": b["id"], "name": b["name"]} for b in hub["buckets"]]
        if not buckets:
            raise ValueError("no buckets")
        out = {"_generated": f"from learn-with-phoebe/courses.json buckets on {TODAY}; do not edit by hand",
               "domains": buckets}
        DOMAINS_FILE.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return buckets
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"warning: hub courses.json unreadable ({exc}); using committed domains.json")
    try:
        return json.loads(DOMAINS_FILE.read_text(encoding="utf-8"))["domains"]
    except (OSError, ValueError, KeyError) as exc:
        sys.exit(f"error: domains.json unreadable too ({exc}); cannot build")


# --------------------------------------------------------------- markdown ----
_CODE_RE = re.compile(r"`([^`]+)`")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")


def _inline(text: str) -> str:
    """Escape, then apply code spans, bold and links (code spans are left alone)."""
    parts = _CODE_RE.split(html.escape(text, quote=False))
    out = []
    for i, part in enumerate(parts):
        if i % 2:
            out.append(f"<code>{part}</code>")
        else:
            part = _BOLD_RE.sub(r"<strong>\1</strong>", part)
            part = _LINK_RE.sub(r'<a href="\2">\1</a>', part)
            out.append(part)
    return "".join(out)


def md_to_html(text: str) -> str:
    """Small Markdown subset: h1-h3, paragraphs, - bullets, 1. lists, pipe tables,
    links, bold, code spans, fenced code, blockquotes."""
    lines = text.splitlines()
    out: list[str] = []
    para: list[str] = []
    i = 0

    def flush() -> None:
        if para:
            out.append(f"<p>{_inline(' '.join(para))}</p>")
            para.clear()

    while i < len(lines):
        s = lines[i].strip()
        if not s:
            flush(); i += 1; continue
        m = re.match(r"^(#{1,3})\s+(.*)$", s)
        if m:
            flush(); n = len(m.group(1))
            out.append(f"<h{n}>{_inline(m.group(2))}</h{n}>"); i += 1; continue
        if s.startswith("```"):
            flush(); i += 1; block = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block.append(lines[i]); i += 1
            out.append(f"<pre><code>{html.escape(chr(10).join(block), quote=False)}</code></pre>"); i += 1; continue
        if s.startswith(">"):
            flush(); block = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                block.append(lines[i].strip()[1:].strip()); i += 1
            out.append(f"<blockquote><p>{_inline(' '.join(block))}</p></blockquote>"); continue
        if re.match(r"^[-*]\s+", s):
            flush(); items = []
            while i < len(lines) and re.match(r"^[-*]\s+", lines[i].strip()):
                items.append(re.sub(r"^[-*]\s+", "", lines[i].strip())); i += 1
            out.append("<ul>" + "".join(f"<li>{_inline(x)}</li>" for x in items) + "</ul>"); continue
        if re.match(r"^\d+[.)]\s+", s):
            flush(); items = []
            while i < len(lines) and re.match(r"^\d+[.)]\s+", lines[i].strip()):
                items.append(re.sub(r"^\d+[.)]\s+", "", lines[i].strip())); i += 1
            out.append("<ol>" + "".join(f"<li>{_inline(x)}</li>" for x in items) + "</ol>"); continue
        if s.startswith("|"):
            flush(); rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.match(r"^:?-{2,}:?$", c) for c in cells):
                    rows.append(cells)
                i += 1
            if rows:
                head = "".join(f"<th>{_inline(c)}</th>" for c in rows[0])
                body = "".join("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>" for r in rows[1:])
                out.append(f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>")
            continue
        para.append(s); i += 1
    flush()
    return "\n".join(out)


# -------------------------------------------------------------- templating ----
_PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")


def render(template: str, mapping: dict) -> str:
    return _PLACEHOLDER.sub(lambda m: str(mapping.get(m.group(1), "")), template)


def split_page(template: str) -> dict:
    """Page templates carry three blocks: <!-- @css -->, <!-- @content -->, <!-- @script -->,
    plus an optional <!-- @contract --> block emitted as the first thing inside <body>."""
    blocks: dict[str, str] = {}
    current = None
    for line in template.splitlines(keepends=True):
        m = re.match(r"^<!-- @(contract|css|content|script) -->\s*$", line)
        if m:
            current = m.group(1); blocks[current] = ""
        elif current:
            blocks[current] += line
    return blocks


def page(base: str, tpl: dict, root: str, mapping: dict) -> str:
    """Fill a page template then drop it into base.html."""
    m = dict(mapping, root=root)
    inner = {
        "page_css": render(tpl.get("css", ""), m),
        "content": render(tpl.get("content", ""), m),
        "page_script": render(tpl.get("script", ""), m),
        "body_contract": tpl.get("contract", "").strip(),
    }
    return render(base, dict(m, **inner))


def inline_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def esc(s) -> str:
    return html.escape(str(s if s is not None else ""), quote=True)


# ----------------------------------------------------------------- entries ----
def load_entries(domain_ids: set[str]) -> list[dict]:
    entries, errors = [], []
    for folder in sorted(p for p in ENTRIES_DIR.iterdir() if p.is_dir()):
        errs = validate_entry(folder, domain_ids)
        if errs:
            errors.extend(errs); continue
        e = json.loads((folder / "entry.json").read_text(encoding="utf-8"))
        e["_notes"] = (folder / "notes.md").read_text(encoding="utf-8")
        rp = folder / "research.md"
        e["_research"] = rp.read_text(encoding="utf-8") if rp.exists() else ""
        entries.append(e)
    if errors:
        print("build aborted: entry validation failed")
        for line in errors:
            print("  " + line)
        sys.exit(1)
    entries.sort(key=lambda e: (e["updated"], e["id"]), reverse=True)
    return entries


def _norm_url(u: str) -> str:
    u = (u or "").strip().lower().rstrip("/")
    return re.sub(r"^https?://(www\.)?", "", u)


def build_graph(entries: list[dict], names: dict) -> tuple[list[dict], list[dict]]:
    nodes: dict[str, dict] = {}
    links: dict[tuple, dict] = {}

    def link(a: str, b: str, kind: str, **extra) -> None:
        links.setdefault((a, b), dict(source=a, target=b, type=kind, **extra))

    for e in entries:
        nid = f"e:{e['id']}"
        nodes[nid] = {"id": nid, "type": "entry", "label": e["topic"], "domain": e["domain"],
                      "domain_name": names.get(e["domain"], e["domain"]), "platform": e["platform"],
                      "status": e["status"], "tags": e["tags"], "url": e["url"],
                      "entries": [{"id": e["id"], "topic": e["topic"]}], "degree": 0}
        for c in e["linked_courses"]:
            cid = f"c:{_norm_url(c['url'])}"
            n = nodes.setdefault(cid, {"id": cid, "type": "course", "label": c["title"], "platform": c["platform"],
                                       "url": c["url"], "entries": [], "degree": 0})
            n["entries"].append({"id": e["id"], "topic": e["topic"]})
            link(nid, cid, "course")
        for r in e["linked_references"] + e["support_readings"]:
            key = (r.get("doi") or "").strip().lower() or _norm_url(r.get("url", ""))
            rid = f"r:{key}"
            n = nodes.setdefault(rid, {"id": rid, "type": "reference", "label": r["title"], "year": r.get("year"),
                                       "cited_by": r.get("cited_by"), "url": r.get("url") or f"https://doi.org/{r.get('doi')}",
                                       "entries": [], "degree": 0})
            if not any(x["id"] == e["id"] for x in n["entries"]):
                n["entries"].append({"id": e["id"], "topic": e["topic"]})
            link(nid, rid, "reference")
    for a, b in itertools.combinations(entries, 2):
        shared = len(set(a["tags"]) & set(b["tags"]))
        if shared >= 2:
            link(f"e:{a['id']}", f"e:{b['id']}", "tags", shared=shared)
    for l in links.values():
        nodes[l["source"]]["degree"] += 1
        nodes[l["target"]]["degree"] += 1
    return list(nodes.values()), list(links.values())


# --------------------------------------------------------------------- game ----
# One XP rule, documented in README.md ("How XP works"). The homepage reads the
# derived numbers from data.json["game"] and each entry's "game" block; it never
# recomputes them.
EST_HOURS = 1.5
# XP counts from this day. Courses finished earlier stay filled on the board and keep their
# badges, but earn no XP: Phoebe chose to start the game as a Beginner on this date.
SEASON_START = "2026-10-14"
LEVEL_THRESHOLDS = [0, 300, 800, 1500, 2500, 4000, 6000, 9000]
RANKS = ["Beginner", "Apprentice", "Analyst", "Practitioner", "Steward", "Architect", "Strategist", "Chief"]
MILESTONES = [1, 5, 10, 25, 50, 100]


def course_xp(e: dict) -> dict:
    """XP, boss HP and reward for one entry.

    done        -> round(hours * 100)
    in-progress -> round(hours * 100 * progress_pct / 100)
    to-do       -> 0
    Missing hours -> 1.5 h estimate, flagged hours_estimated so the UI prints "est.".
    """
    has_hours = isinstance(e.get("hours"), (int, float)) and not isinstance(e.get("hours"), bool) and e["hours"] > 0
    hours = float(e["hours"]) if has_hours else EST_HOURS
    status = e["status"]
    if status == "done":
        pct = 100
    elif status == "in-progress":
        pct = int(e.get("progress_pct") or 0)
    else:
        pct = 0
    full = round(hours * 100)
    pre_season = status == "done" and (e.get("end_date") or "0000-00-00") < SEASON_START
    if status == "done":
        xp = 0 if pre_season else full
    elif status == "in-progress":
        xp = round(hours * 100 * pct / 100)
    else:
        xp = 0
    hp = 0.0 if status == "done" else hours * (1 - pct / 100)
    return {"hours": hours, "hours_estimated": not has_hours, "progress_pct": pct,
            "xp": xp, "xp_full": full, "reward_xp": 0 if status == "done" else full - xp,
            "hp_hours": round(hp, 2), "pre_season": pre_season}


def level_for(xp: int) -> dict:
    idx = max(i for i, t in enumerate(LEVEL_THRESHOLDS) if xp >= t)
    nxt = idx + 1 if idx + 1 < len(LEVEL_THRESHOLDS) else None
    lo = LEVEL_THRESHOLDS[idx]
    out = {"level": idx + 1, "rank": RANKS[idx], "floor": lo,
           "next_level": None, "next_rank": None, "next_threshold": None, "xp_to_next": 0, "bar_pct": 100}
    if nxt is not None:
        hi = LEVEL_THRESHOLDS[nxt]
        out.update(next_level=nxt + 1, next_rank=RANKS[nxt], next_threshold=hi, xp_to_next=hi - xp,
                   bar_pct=round((xp - lo) / (hi - lo) * 100, 1))
    return out


def _iso_week(d: str) -> tuple[int, int]:
    y, w, _ = _dt.date.fromisoformat(d).isocalendar()
    return (y, w)


def _week_before(wk: tuple[int, int]) -> tuple[int, int]:
    y, w, _ = (_dt.date.fromisocalendar(wk[0], wk[1], 1) - _dt.timedelta(days=7)).isocalendar()
    return (y, w)


def weekly_streak(entries: list[dict], today: str = TODAY) -> dict:
    """Consecutive ISO weeks, ending at the current week, with at least one done end_date."""
    weeks = {_iso_week(e["end_date"]) for e in entries if e["status"] == "done" and e.get("end_date")}
    cur = _iso_week(today)
    current, wk = 0, cur
    while wk in weeks:
        current += 1
        wk = _week_before(wk)
    best = 0
    for w in weeks:
        if _week_before(w) in weeks:
            continue  # not the start of a run
        run, nx = 0, w
        while nx in weeks:
            run += 1
            y, n, _ = (_dt.date.fromisocalendar(nx[0], nx[1], 1) + _dt.timedelta(days=7)).isocalendar()
            nx = (y, n)
        best = max(best, run)
    recent, wk = [], cur
    for _ in range(10):
        recent.append({"week": f"{wk[0]}-W{wk[1]:02d}", "done": wk in weeks})
        wk = _week_before(wk)
    return {"current": current, "best": best, "this_week": f"{cur[0]}-W{cur[1]:02d}", "recent": recent[::-1]}


def badges(entries: list[dict], domains: list[dict]) -> list[dict]:
    done = sorted((e for e in entries if e["status"] == "done"), key=lambda e: (e["end_date"] or "9999-99-99", e["id"]))
    out = []
    for d in domains:
        if not any(e["domain"] == d["id"] for e in entries):
            continue
        first = next((e for e in done if e["domain"] == d["id"]), None)
        out.append({"id": f"first-{d['id']}", "kind": "domain", "name": f"First in {d['name']}",
                    "rule": f"Finish {'an' if d['name'][:1].lower() in 'aeiou' else 'a'} {d['name']} course.",
                    "earned": first is not None, "earned_on": first["end_date"] if first else None,
                    "by": first["id"] if first else None, "latest": False})
    for n in MILESTONES:
        hit = done[n - 1] if len(done) >= n else None
        out.append({"id": f"done-{n}", "kind": "milestone",
                    "name": "First course done" if n == 1 else f"{n} courses done",
                    "rule": "Finish any course." if n == 1 else f"Finish {n} courses.",
                    "earned": hit is not None, "earned_on": hit["end_date"] if hit else None,
                    "by": hit["id"] if hit else None, "latest": False})
    earned = [b for b in out if b["earned"]]
    if earned:
        # Latest by date; on a tie the milestone (computed last) wins, it is the bigger news.
        max(enumerate(earned), key=lambda ib: (ib[1]["earned_on"] or "", ib[0]))[1]["latest"] = True
    return out


TRACK_RANK = {"done": 0, "in-progress": 1, "to-do": 2}


def board_state(entries: list[dict], domains: list[dict]) -> dict:
    """The homepage board: one loop track of every entry, plus where the pawn stands.

    Track order: districts (domains) in domains.json order, unknown domains last;
    inside a district, done squares lead (ground already covered), then in-progress,
    then to-do, each by topic. The pawn stands on the first in-progress square
    (index into track) or on START (-1) when nothing is in progress. next_ids are the
    next three not-done squares after the pawn, wrapping round the loop.
    Each district carries "pattern": its index in domains.json, so a district keeps
    its printed strip pattern as courses are added.
    """
    order = {d["id"]: i for i, d in enumerate(domains)}
    names = {d["id"]: d["name"] for d in domains}
    ordered = sorted(entries, key=lambda e: (order.get(e["domain"], len(order)), e["domain"],
                                             TRACK_RANK[e["status"]], e["topic"].lower(), e["id"]))
    track = [e["id"] for e in ordered]
    districts: list[dict] = []
    for i, e in enumerate(ordered):
        if not districts or districts[-1]["id"] != e["domain"]:
            districts.append({"id": e["domain"], "name": names.get(e["domain"], e["domain"]),
                              "pattern": order.get(e["domain"], len(order)), "start": i, "count": 0})
        districts[-1]["count"] += 1
    status = {e["id"]: e["status"] for e in entries}
    pawn = next((i for i, eid in enumerate(track) if status[eid] == "in-progress"), -1)
    nxt: list[str] = []
    n = len(track)
    for k in range(1, n + 1):
        j = (pawn + k) % n if n else 0
        if j == pawn or not n:
            break
        if status[track[j]] != "done":
            nxt.append(track[j])
        if len(nxt) == 3:
            break

    # Validate here, once: the page trusts these numbers.
    problems = []
    if sorted(track) != sorted(e["id"] for e in entries) or len(set(track)) != len(track):
        problems.append("track must hold every entry exactly once")
    if sum(d["count"] for d in districts) != n or len({d["id"] for d in districts}) != len(districts):
        problems.append("each district must be one contiguous run covering the track")
    if pawn != -1 and status[track[pawn]] != "in-progress":
        problems.append("pawn must stand on an in-progress square")
    if pawn == -1 and any(s == "in-progress" for s in status.values()):
        problems.append("pawn on START while a course is in progress")
    if len(set(nxt)) != len(nxt) or any(status[x] == "done" for x in nxt) or (pawn != -1 and track[pawn] in nxt):
        problems.append("next_ids must be distinct, not done, and not the pawn's square")
    if len(nxt) != min(3, sum(1 for s in status.values() if s != "done") - (1 if pawn != -1 else 0)):
        problems.append("next_ids must hold three squares when three not-done squares exist")
    if problems:
        sys.exit("build aborted: board_state invalid: " + "; ".join(problems))
    return {"track": track, "districts": districts, "pawn_index": pawn, "next_ids": nxt}


def game_state(entries: list[dict], domains: list[dict]) -> dict:
    total_xp = sum(course_xp(e)["xp"] for e in entries)
    lvl = level_for(total_xp)
    return {"xp": total_xp, **lvl, "board": board_state(entries, domains),
            "levels": [{"level": i + 1, "rank": r, "threshold": t} for i, (r, t) in enumerate(zip(RANKS, LEVEL_THRESHOLDS))],
            "rule": {"xp_per_hour": 100, "est_hours": EST_HOURS, "season_start": SEASON_START},
            "done": sum(1 for e in entries if e["status"] == "done"),
            "in_progress": sum(1 for e in entries if e["status"] == "in-progress"),
            "to_do": sum(1 for e in entries if e["status"] == "to-do"),
            "streak": weekly_streak(entries), "badges": badges(entries, domains)}


# ---------------------------------------------------------------- renderers ----
def status_chip(status: str) -> str:
    return f'<span class="status {status}"><span class="{STATUS_GLYPH[status]}"></span>{STATUS_LABEL[status]}</span>'


def rating_html(e: dict) -> str:
    """Stars from the Notion Rating column. 1 star is the unrated default, so it is not shown."""
    r = e.get("rating") or 1
    if r < 2:
        return ""
    return (f'<span class="kicker">&middot;</span><span class="kicker rating" aria-label="Rated {r} of 5">'
            f'{"&#9733;" * r}{"&#9734;" * (5 - r)}</span>')


def chip(text: str, cls: str) -> str:
    return f'<span class="chip {cls}">{esc(text)}</span>'


def sentence(word: str) -> str:
    return word[:1].upper() + word[1:].lower() if word else ""


def ref_link(r: dict) -> str:
    url = r.get("url") or (f"https://doi.org/{r['doi']}" if r.get("doi") else "")
    title = esc(r.get("title") or "(untitled)")
    return f'<a href="{esc(url)}" target="_blank" rel="noopener">{title}</a>' if url else title


def cited(r: dict) -> str:
    n = r.get("cited_by")
    if n is None or n == "":
        return "-"
    return f"{int(n):,} as of {esc(r.get('retrieved') or TODAY)}"


def date_line(e: dict) -> str:
    s, t = e.get("start_date"), e.get("end_date")
    if s and t:
        return f"{s} to {t}"
    if s:
        return f"started {s}"
    if t:
        return f"finished {t}"
    if e.get("status") == "done":
        return "finished, date not recorded"
    return "not started"


def render_research(e: dict) -> str:
    refs = {r["id"]: r for r in e["linked_references"]}
    out = ['<section class="block" id="research"><p class="kicker">Research</p>']
    if e["_research"].strip():
        out.append(f'<div class="prose">{md_to_html(e["_research"])}</div>')
    for kp in e["key_points"]:
        rows = []
        for rid in list(kp["supporting"]) + list(kp["other_angles"]):
            r = refs[rid]
            tier = r["tier"]
            rows.append(
                "<tr>"
                f'<td class="num">{esc(rid)}</td>'
                f'<td>{chip(sentence(r["role"]), ROLE_CLASS.get(r["role"], "outline-muted"))}</td>'
                f"<td>{ref_link(r)}</td>"
                f'<td class="num">{esc(r.get("year") or "-")}</td>'
                f'<td>{esc(r.get("venue") or "-")}</td>'
                f'<td class="num">{cited(r)}</td>'
                f'<td>{chip(sentence(tier), TIER_CLASS.get(tier, "outline-muted"))}</td>'
                f'<td>{esc(r.get("why") or "")}</td>'
                "</tr>")
        out.append(
            f'<div class="kp"><h3>{esc(kp["claim"])}</h3><div class="tablewrap"><table>'
            "<thead><tr><th>#</th><th>Role</th><th>Title</th><th>Year</th><th>Venue</th>"
            "<th>Cited by</th><th>Tier</th><th>Why</th></tr></thead>"
            f'<tbody>{"".join(rows)}</tbody></table></div>'
            f'<p class="disagree">Where they disagree: {esc(kp["disagreement"])}</p></div>')
    out.append("</section>")

    out.append('<section class="block" id="readings"><p class="kicker">Five readings</p><ol class="readings">')
    for i, r in enumerate(e["support_readings"], 1):
        by = ", ".join(x for x in [esc(r.get("authors") or ""), esc(r.get("year") or "")] if x)
        out.append(
            f'<li><span class="n">{i}</span><div><div class="t">{ref_link(r)} '
            f'{chip(sentence(r["role"]), "outline-muted")}</div>'
            f'<div class="by">{by}</div><p class="why">{esc(r.get("why") or "")}</p></div></li>')
    out.append("</ol></section>")

    out.append('<section class="block" id="courses"><p class="kicker">Course bundle</p><ul class="courses">')
    for c in e["linked_courses"]:
        taught = ""
        if c.get("taught_by_phoebe"):
            taught = (f'<a class="chip outline-plum" href="https://phoebefu6.github.io/{esc(c["taught_by_phoebe"])}/" '
                      'target="_blank" rel="noopener">also taught by Phoebe</a>')
        facts = " &middot; ".join(x for x in [esc(c.get("level") or ""), esc(c.get("hours") or ""),
                                              f"fit: {esc(c.get('fit') or '')}"] if x)
        out.append(
            f'<li><div class="top">{chip(c["platform"], "")}<span class="t"><a href="{esc(c["url"])}" '
            f'target="_blank" rel="noopener">{esc(c["title"])}</a></span>{taught}</div>'
            f'<p class="facts">{facts}</p><p class="why">{esc(c.get("why") or "")}</p></li>')
    out.append("</ul></section>")

    out.append('<section class="block" id="references"><p class="kicker">References</p><ol class="refs">')
    seen = set()
    for r in e["linked_references"]:
        if r["id"] in seen:
            continue
        seen.add(r["id"])
        by = " ".join(x for x in [esc(r.get("authors") or ""), f"({esc(r['year'])})" if r.get("year") else "",
                                  esc(r.get("venue") or "")] if x)
        by_html = f' <span class="by">{by}</span>' if by else ""
        out.append(f'<li><span class="rid">{esc(r["id"])}</span><div>{ref_link(r)}{by_html}</div></li>')
    out.append("</ol></section>")
    return "\n".join(out)


def render_entry(e: dict, names: dict, base: str, tpl: dict, data_json: str) -> str:
    ideas = e["main_ideas"]
    ideas_block = ""
    if ideas:
        label = "Three ideas" if len(ideas) == 3 else "Main ideas"
        ideas_block = (f'<section class="block" id="ideas"><p class="kicker">{label}</p><ol class="ideas">'
                       + "".join(f"<li><span>{esc(x)}</span></li>" for x in ideas) + "</ol></section>")
    if e["research_status"] == "full":
        research_block = render_research(e)
    else:
        research_block = ('<section class="block" id="research"><p class="kicker">Research</p>'
                          '<div class="panel-tint"><strong>Research not run yet.</strong> '
                          "When it runs, this page gains three main ideas, key points with three supporting and "
                          "three other-angle references each, five readings and a five-course bundle.</div></section>")
    source_link = (f'<a href="{esc(e["url"])}" target="_blank" rel="noopener">Source</a>' if e["url"] else "")
    mapping = {
        "title": f"{e['topic']} - Phoebe learns",
        "description": f"Learning entry: {e['topic']}",
        "domain_name": esc(names.get(e["domain"], e["domain"])),
        "platform": esc(e["platform"]),
        "status_chip": status_chip(e["status"]),
        "rating": rating_html(e),
        "topic": esc(e["topic"]),
        "dates": esc(date_line(e)),
        "source_link": source_link,
        "tag_chips": "".join(chip(t, "tag") for t in e["tags"]),
        "ideas_block": ideas_block,
        "notes_html": md_to_html(e["_notes"]),
        "research_block": research_block,
        "active_db": "", "active_net": "",
        "generated": TODAY,
        "data_json": data_json,
    }
    return page(base, tpl, "../../", mapping)


# -------------------------------------------------------------------- main ----
def main() -> int:
    domains = refresh_domains()
    names = {d["id"]: d["name"] for d in domains}
    entries = load_entries(set(names))
    nodes, links = build_graph(entries, names)

    public = []
    for e in entries:
        pe = {k: v for k, v in e.items() if not k.startswith("_")}
        pe["domain_name"] = names.get(e["domain"], e["domain"])
        pe["game"] = course_xp(e)
        public.append(pe)
    game = game_state(entries, domains)
    data = {"generated": TODAY, "site": SITE_URL, "domains": domains, "entries": public,
            "game": game, "nodes": nodes, "links": links}
    (REPO / "data.json").write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    data_json = inline_json(data)

    base = (TEMPLATES / "base.html").read_text(encoding="utf-8")
    tpl_index = split_page((TEMPLATES / "index.html").read_text(encoding="utf-8"))
    tpl_entry = split_page((TEMPLATES / "entry.html").read_text(encoding="utf-8"))
    tpl_net = split_page((TEMPLATES / "network.html").read_text(encoding="utf-8"))
    d3_src = (REPO / "assets/d3.min.js").read_text(encoding="utf-8")
    pages = 0

    done = sum(1 for e in entries if e["status"] == "done")
    (REPO / "index.html").write_text(page(base, tpl_index, "", {
        "title": "Phoebe learns - learning DB",
        "description": "Phoebe Fu's learning knowledge base: every course or notes file, tidied, researched and mapped.",
        "done_count": done, "total": len(entries), "in_progress_count": game["in_progress"],
        "level": game["level"], "rank": game["rank"], "xp": f"{game['xp']:,}",
        "xp_raw": game["xp"], "bar_pct": game["bar_pct"],
        "next_line": (f"{game['xp_to_next']:,} XP to {game['next_rank']}" if game["next_rank"]
                      else "Top rank reached"),
        "next_threshold": f"{game['next_threshold']:,}" if game["next_threshold"] else "",
        "next_level": game["next_level"] or "",
        "floor": f"{game['floor']:,}",
        "scale_right": (f"Level {game['next_level']} at {game['next_threshold']:,} XP" if game["next_rank"] else "Top rank"),
        "max_class": "" if game["next_rank"] else "lv-max",
        "active_db": "active", "active_net": "", "generated": TODAY, "data_json": data_json,
    }), encoding="utf-8"); pages += 1

    (REPO / "network.html").write_text(page(base, tpl_net, "", {
        "title": "Phoebe learns - knowledge network",
        "description": "Knowledge network of Phoebe Fu's learning entries, the courses they bundle and the references behind them.",
        "d3": d3_src,
        "active_db": "", "active_net": "active", "generated": TODAY, "data_json": data_json,
    }), encoding="utf-8"); pages += 1

    # Entry pages get only their own record inline (the DB page carries the full export).
    for e in entries:
        own = {"generated": TODAY, "site": SITE_URL, "domains": domains,
               "entries": [p for p in public if p["id"] == e["id"]]}
        out = ENTRIES_DIR / e["id"] / "index.html"
        out.write_text(render_entry(e, names, base, tpl_entry, inline_json(own)), encoding="utf-8"); pages += 1

    print(f"{len(entries)} entries, {pages} pages written, {len(nodes)} nodes, {len(links)} links")
    return 0


if __name__ == "__main__":
    sys.exit(main())
