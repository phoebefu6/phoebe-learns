# phoebe-learns

Phoebe Fu's personal learning knowledge base, published at
https://phoebefu6.github.io/phoebe-learns/

## The problem

Courses get finished and the notes vanish into a folder. Six months later the
same question comes back and the work is done twice. This repo keeps one record
per thing learned, researched once, and shows the records three ways: a
Notion-looking learning DB, one page per entry, and a knowledge network that
links entries through the courses they bundle and the references behind them.

## What it is

A static site. Entries are JSON + Markdown in the repo; `python3 build.py`
renders everything into plain HTML with no server, no framework and no build
dependency beyond Python 3.11's standard library. GitHub Pages serves the
`main` branch root.

```
build.py                 renders the site (validates first)
domains.json             the 18 learning domains, generated from the learn-with-phoebe hub
domains-extra.json       6 learning-only domains from the Notion course library (edit by hand)
templates/               base.html, index.html, entry.html, network.html
entries/<id>/            one folder per entry: entry.json, notes.md, research.md, source/ (optional)
scripts/validate.py      schema rules, usable standalone
scripts/check_links.py   curls every url and doi in data.json
scripts/import_365_tracker.py   one-off import of the 365 Data Science finish tracker
scripts/sync_notion.py   Notion All Courses -> entries/ (see "Notion sync")
scripts/add_course.py    adds one course link to Notion (run by the workflow)
scripts/notion_lib.py    Notion API calls and the Notion -> site field mapping
scripts/daily_pick.py    ticks Today's pick on one course in Notion each morning
.github/workflows/notion.yml    daily sync, issue-form adds, rebuild and commit
assets/                  d3 v7 (ISC licence) kept for provenance; network.html inlines it
index.html network.html entries/<id>/index.html data.json   generated, committed
```

## How an entry is shaped

Folder name = entry id = `yyyy-mm-dd-slug`. Inside:

- `entry.json` - the record. Topic, domain (an id from `domains.json`), platform,
  source type, url, tags, status, dates, three main ideas, key points (each with
  three supporting references, three other angles and one unresolved
  disagreement), five support readings, a five-course bundle, and
  `research_status` (`full` or `none`).
- `notes.md` - Phoebe's own notes. Always present.
- `research.md` - the research write-up. Required when `research_status` is `full`.
- `source/` - optional original material, pointed to by `source_file`.

`scripts/validate.py` enforces every rule, including: id matches the folder,
domain exists, dates are ISO, `end_date` is set when status is `done`,
exact counts when research is `full`, every reference id a key point cites
exists, every reference has a url or doi, and no em dash, en dash or cross
mark anywhere in the JSON.

```
python3 scripts/validate.py entries/2026-10-05-evaluating-ai-agents
python3 scripts/validate.py --all
```

## Build

```
python3 build.py
```

It validates every entry (and aborts with a list of `path: rule` lines if any
fail), refreshes `domains.json` from the learn-with-phoebe hub when that file
is readable (otherwise it keeps the committed copy and prints a warning), then
writes `index.html`, `network.html`, one `entries/<id>/index.html` per entry
and `data.json`. The pages embed their data inline, so they open straight from
`file://` as well as from GitHub Pages.

```
python3 scripts/check_links.py data.json
```

Curls every url and doi. 2xx passes; a 403 from udemy.com or coursera.org is
reported as "verify by WebFetch" and does not fail; anything else fails.

## How status works

Three states, always shown as colour plus a glyph so colour is never the only
signal:

| status | chip | glyph |
|---|---|---|
| `to-do` | 1px plum outline | outline square |
| `in-progress` | soft tint fill | half-filled square |
| `done` | solid plum fill, white text | filled square |

The homepage's hero number is the current level (see "How XP works"). The board
view has exactly three columns, one per status; the table view groups by domain.

## How XP works

The homepage is a game dashboard: level, quest map, boss board and trophy shelf.
Every number on it comes from one place, `course_xp()` and `game_state()` in
`build.py`, exported to `data.json` as `game` (site totals) and `entries[].game`
(per course). The page only displays them.

Two optional fields on `entry.json` feed it:

| field | type | meaning |
|---|---|---|
| `hours` | number > 0 | course length in hours |
| `progress_pct` | integer 0-100 | how far through an `in-progress` course; absent means 0 |

XP per course:

- `done`: `round(hours * 100)`, but only when `end_date` is on or after `SEASON_START`
  (2026-10-14, set in `build.py`). Courses finished earlier, or with no recorded date, stay
  filled on the board and keep their badges but earn 0 XP: the game starts as a Beginner.
- `in-progress`: `round(hours * 100 * progress_pct / 100)`
- `to-do`: 0
- No `hours`: use a 1.5 h estimate and set `hours_estimated: true`; the page prints
  "est." beside every number built on it. A missing field never makes a course look
  finished or trivial: boss HP uses the same 1.5 h estimate.

Boss HP is hours left, `hours * (1 - progress_pct / 100)`; the reward is the XP still
to earn. Levels start at 0, 300, 800, 1500, 2500, 4000, 6000 and 9000 XP: Beginner,
Apprentice, Analyst, Practitioner, Steward, Architect, Strategist, Chief.

The weekly streak counts consecutive ISO weeks, ending at the current week, that hold
at least one `end_date` of a `done` entry; the best streak is the longest such run.
Badges: "First in <domain>" for the first finish in each domain that has entries, and
milestones at 1, 5, 10, 25, 50 and 100 courses done. The most recently earned badge
carries the peach accent.

The homepage's add box opens the "Add a course" issue form with the link filled in
(see "Notion sync"). The boss cards still build commands for the `learning-buddy` skill
(`learning buddy start <id>`, `mark <id> done`) and copy them to the clipboard.

## Notion sync

Phoebe's Notion database **All Courses** (in the private page Course Library) is the
source of truth for courses. The site follows it, one direction only.

- `scripts/sync_notion.py` reads every row and writes `entries/`. Only course details
  go public: title, domain, platform, status, rating, tags, link and end date. Notion
  page bodies (her notes) are never read. Matching, skips and removals are described
  at the top of the script.
- Rows with no Domain, or titled "(duplicate?)", are skipped until fixed in Notion.
- Done courses with no End Date carry `end_date_unknown: true`; they count as done
  but add nothing to the weekly streak.
- `rating` (1-5) comes from the Notion Rating column; 1 star is the default and is not shown.
- Paste a link in the homepage box, press **Add to Notion**, then **Submit** on the form.
  `.github/workflows/notion.yml` adds the row to Notion (as Not started, one star),
  syncs, rebuilds and commits. It only acts on issues opened by `phoebefu6` with the
  `add-course` label. It also runs daily at 01:17 UTC and from the Actions tab.

One-time setup, done by Phoebe (the key never leaves her hands):

1. https://www.notion.so/profile/integrations: **New integration**, type Internal,
   workspace = hers, capabilities: read content, update content, insert content.
   Copy the Internal Integration Secret.
2. In Notion, open **All Courses** > `...` menu > **Connections** > add the integration.
3. GitHub repo **Settings > Secrets and variables > Actions > New repository secret**:
   name `NOTION_TOKEN`, value = the secret.
4. **Actions** tab > **Notion sync** > **Run workflow** to check it works.

## First real entry

`entries/2026-10-05-evaluating-ai-agents/` is the first entry written by the `learning-buddy`
skill: 6 key points, 36 references with API citation counts and source-checker tiers, 5
readings and a 5-course bundle, one per platform. The 64 `to-do` entries under 365 Data
Science were imported from a finish tracker and carry `research_status: none` until taken.

## Companion skill

Entries are written by the `learning-buddy` skill. This repo only stores and
renders them; it does no research itself.

## Licence

MIT, copyright 2026 Phoebe Fu. d3 is ISC, see `assets/D3-LICENSE.txt`.
