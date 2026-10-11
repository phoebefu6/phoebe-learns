# Product
<!-- impeccable:product-schema 1 -->

## Platform
web

## Users
Primary: Phoebe Fu, a data and AI leader who subscribes to five learning platforms (Coursera Plus,
365 Data Science, DataCamp, Udemy, DeepLearning.AI) and finishes far fewer courses than she starts.
She opens the homepage to see where she stands, pick the next course, and drop a new course link in.
Secondary: employers and LinkedIn followers who land on the public page and see a serious,
continuous learner as a side effect. Confirmed 2026-10-10: "me first, visitors second".

## Product Purpose
A public learning knowledge base that turns finishing courses into a game. Every course is an entry
with tidied notes, cited evidence for and against each key point, readings and a course bundle.
The homepage must pull her back daily and make the next course to take obvious.
Success: she finishes courses because the board makes progress visible and the next move clear.

## Positioning
Every tile on the board is backed by real research (36 tiered references per researched course),
not a checkbox. The game state is computed from the entries: XP from course hours, bosses from
unfinished courses, conquest from finished ones.

## Operating Context
Entries are written by the learning-buddy skill in Claude Code. The page cannot call Claude: the
paste-a-link box and the card buttons copy exact commands she pastes into Claude Code
(`learning buddy add to-do <url>`, `learning buddy start <id>`, `mark <id> done`).
Static GitHub Pages site, built by a stdlib Python build.py; every page embeds its data inline.

## Capabilities and Constraints
- Domains are the 18 hub bucket ids; status is to-do, in-progress, done.
- Hours are often unknown (64 imported 365 Data Science to-dos); the game uses a 1.5 h estimate
  marked "est." and a missing field must never make a course look finished.
- Today: 66 entries, 0 done, 2 in progress, 10 domains. The empty-progress state is the common
  state for now and must look like a starting line, not a broken board.

## Brand Commitments
- Palette and fonts are locked (design.md, Plum and peach): white paper only, plum #9333EA, ink
  #2A1B3D, tints #FAF5FF / #F3E8FF, hairline #EAE8F0, muted #6B6480, peach #FDBA74 at most twice
  per view; Poppins and Inter. Changing any of these needs Phoebe's explicit yes.
- Never a dark surface. No em or en dashes. No cross-mark bullets. Hyphens only.
- Freshness comes from composition, layout and hand-drawn illustration of the real mechanism.
- Playful game styling is welcome. It must not feel quiet or flat (the 2026-10-10 version scored
  2/10), and it must not be so busy she cannot see what to take next.

## Evidence on Hand
entries/*/entry.json (66), two fully researched entries, the network page, the quest-map data.
No real completions yet; do not fabricate progress.

## Product Principles
1. The next course to take is always one glance away.
2. Progress is earned and visible; nothing is faked or estimated without saying so.
3. Every game element maps to a real fact in the entries.
4. Adding a course is one paste.
