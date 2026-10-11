# Design

The homepage is a printed board game seen from above. Product truth lives in `PRODUCT.md`;
the brand rules come from Phoebe's design constitution (Plum and peach). The design contract
sits verbatim in the `<!-- @contract -->` block at the top of `templates/index.html`.
This page records the system the board is built from. Never fork the palette here.

## Tokens (locked, from `templates/base.html`)

| Token | Value | Use |
|-------|-------|-----|
| paper | `#FFFFFF` | every surface, board field, tooltip and card |
| plum | `#9333EA` | done squares, ringed numerals, roll arrow, primary buttons, 4px top rule |
| ink | `#2A1B3D` | text, square outlines, the heavy board border |
| tint / tint2 | `#FAF5FF` / `#F3E8FF` | the track lane; the "plum tint" district fill |
| hairline | `#EAE8F0` | inner frame of chance cards, page dividers |
| muted | `#6B6480` | kickers, captions, unearned stamp outline |
| peach | `#FDBA74` | the pawn, plus the latest earned stamp. Never more than two per view |

Poppins 500/600 for headlines and numbers, Inter 400/500 for body. Corners 0-2px.
No shadows, gradients, glow or glass. Never a dark surface: solid plum appears only on
elements 48px or smaller (squares, chips, buttons, rules). Hyphens only; body text ASCII.

## Board grammar

- **Track.** `build.py board_state()` orders every entry into one loop, grouped by district.
  The page never reorders it. Square numbers are track positions, 1-based.
- **Loop (600px and wider).** Clockwise from the top-left corner: top row, right side,
  bottom row, left side. Columns across come from the track length and a target aspect
  (`C = round((n + 4) / (2 + 2 / aspect))`, aspect 1.06 at 980px and up, 0.62 below);
  the sides take the rest. For 66 squares at 1280 this is 18 across and 15 down each side.
  If the board face does not fit inside the loop, the loop drops a column and grows taller.
- **Square pitch** at most 56px with a 48px tile, so a filled square never paints plum
  over more than 48px.
- **Serpentine (under 600px).** The board face sits above the track. Each district starts
  its own rows of four that snake left and right, joined by a hand-drawn rail; the district
  name and its strip run down a left lane.
- **Board face.** Title, level at poster scale, XP score track of ten printed cells, the
  pawn's square, the START tile with the paste box, and three chance cards. It reflows by
  its own width through container queries (face, 640px and 440px).
- **START tile.** A printed corner tile; its START cell is where the pawn stands when
  nothing is in progress (`pawn_index` -1).
- **Ink layer.** One inline SVG over the board: the doubled wobbly border, district strips
  and the roll arrow are stroked through a light `feTurbulence` + `feDisplacementMap`
  filter. District names sit in a separate group outside the filter.

## District patterns

Ten printed fills, in plum on white: solid plum, plum tint, diagonal hatch, cross-hatch,
dots, horizontal rules, vertical rules, checker, wave, chevron. A district takes
`PATTERNS[district.pattern % 10]`; if an earlier district already wears that fill it steps to
the next free one, so the ten districts on the board never share a fill. With more than ten
districts patterns would repeat; the printed names still tell them apart. Districts are never
told apart by a new hue.

## Square states

| State | Square |
|-------|--------|
| to do | white, 1.5px ink outline, track number centred (Poppins 15px) |
| in progress | white with the lower-right half plum, track number top-left |
| done | solid plum with a white check, track number top-left in white |
| next roll 1, 2, 3 | a ringed numeral (plum ring, ink figure) centred, track number top-left |
| pawn | the peach pawn stands in the square's lower-right corner |

The course name is never printed on a square: hover or focus shows a light printed-card
tooltip, and click opens the entry page.

## Motion

- On first load the pawn hops from START to its square, one small arc per square, about
  1.2 s in all; the level and XP count up once. Nothing loops.
- Hover or focus raises a square 2px and thickens its ink outline. No shadow.
- Chance cards sit fanned (small rotations, stepped down) and straighten and lift on hover.
- Under `prefers-reduced-motion` the pawn and numbers show their final state at once.
  A 1.6 s safety net settles everything for print and headless capture.
