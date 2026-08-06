# design-notes: the generator contract for institutional-ir

*Derived 2026-08-05 (M4) from `template.json`, `BRAND.md`, `budgets.json` and the
fiction bible's voice rules. This file is what a generating model reads before writing
a `deck.json`. It is part of the catalog-entry bundle (brainstorm Q10, amended 08-04);
the bank-maker emits one of these per bank. When this file and the template's own
comments disagree, the template is ahead; fix this file.*

## What this template is

Bulge-bracket investor-relations reporting: banded tables, hairline rules, zero
ornament. Built for a deck read at desk distance under a skeptical line-by-line read,
not projected to a room that wants energy. There is **no agenda page, no section
divider and no closing page** anywhere in the measured genre (174 anchor pages), and
adding one contradicts the source. Wrong for pitches, warmth, or momentum.

## The twelve pages, in deck order

The slides sit in DECK ORDER for the annual deck. Drop the five narrative patterns
(chart-split through stat-board) and what is left IS the quarterly deck; nothing else
changes.

| # | Pattern (`slide--<id>`) | Job | Register |
|---|---|---|---|
| 1 | `cover` | Title + date on the colour field | -- |
| 2 | `chart-split` | Narrative workhorse: left argues, right proves | narrative |
| 3 | `panel-row` | Three chart panels with claims | narrative |
| 4 | `checklist` | Strategy scorecard: claim band + delivered actions | narrative |
| 5 | `hero-chart` | One full-width chart with annotation boxes | narrative |
| 6 | `stat-board` | Three display stats + closing frame | narrative |
| 7 | `snapshot` | Results snapshot: quote, six KPI tiles, bullets | results |
| 8 | `module` | Segment P&L table + commentary + chart. **One per business segment**; the anchor runs 9-10 of these | results |
| 9 | `split` | Second segment shape: table + bullet column | results |
| 10 | `prose` | Full-page prose (basis of presentation) | back matter |
| 11 | `recon` | Non-GAAP reconciliation + footnotes | back matter |
| 12 | `notes-continued` | Footnote continuation | back matter |

**Page-plan rules (v1 composition scope, decided 2026-08-05):**

- Any page may be dropped. Only `module` may repeat (it is the workhorse; each
  instance covers one business segment).
- Four patterns appear exactly once in every anchor deck: cover, snapshot, the
  segment split, and recon. Dropping one of those is a decision, not a default.
- **The split page is an alternate segment SHAPE, not an extra segment.** When
  module instances already cover every business segment, dropping split is the
  right call, not a deviation; module count = segments and split both holding
  literally would double-report a segment.
- A `notes-continued` page exists because the previous page filled. Do not retain it
  half-empty; move the break instead.
- Folios renumber contiguously after subsetting (the builder does this; the cover
  carries no folio).
- **Title register is a real seam.** A narrative title makes a claim (median 9
  words); a results title names a line item (median 4). Do not write claim-style
  titles on results pages.

## The slot model

Every fillable site is a `data-slot`. The generator fills slots through `deck.json`;
it never edits HTML. The machine-derived map of every slot (page, DOM order,
fill-type label from the blank form) lives in `slots.json`, generated at sync time.
Families:

| Family | What it holds | Notes |
|---|---|---|
| `cover-*`, `quote-name/role` | Cover strings, quote attribution | cover-title lines are re-wrapped into hang spans by the builder; write plain `line<br />line` |
| `segment-1`, `segment-2` (+ `-lc` lowercase) | Business segment names | One value fills every occurrence across pages; consistency is automatic |
| `lang-*` | All narrative language | Sub-families: `lang-blank-*` bullets and footnotes, `lang-th-*` table heads, `lang-line-*` P&L lines, `lang-legend-*`, `lang-cat-*` chart categories, `lang-units-*` unit captions, `lang-tile-*` KPI tiles, `lang-band-*` claim band |
| `lang-scaf-*` | Financial-statement scaffold lines (Net revenues, Provision for credit losses, ...) | Genre boilerplate. Keep unless the user's statement genuinely differs |
| `target-*`, `rank-*`, `period-*`, `streak-*` | Worded figures (targets, ranks, streaks) | These are figures in word form; they take the user's real values |
| `fig-*` | Digit figures in tables and tiles (skill's synced copy only; the sync step slots them, the lane template keeps raw masks) | OPTIONAL: unfilled stays visibly masked, never invented. slots.json labels carry the mask shape plus row context. Chart-zone figures are deliberately not slotted; bar geometry is synthetic, so real labels over fixed bars would misrepresent |

**Coverage rule: a retained page must have every slot either user-filled or
explicitly kept.** The template's neutral defaults describe a fictional issuer; a
default leaking into a user deck is a defect the checks fail on, not a fallback.

**Chart period axes are slotted** (`lang-cat-cs-1..5`, `lang-cat-hc-1..5`,
`lang-cat-pr-1..6` in panel order, `lang-cat-mod-1..3`; added 2026-08-05 after a
fiscal-year deck rendered calendar-year axes). Fill them with the deck's own
period labels. The snapshot bullets heading is `lang-ss-high-head` ("Quarterly
Highlights" by default); an annual deck renames it.

## Page micro-structures the generator must respect

Found in calibration run 3; each of these is invisible to the checks and shows
up only in the render.

- **The checklist claim band is segment-bracketed.** Cells 1-3 sit under a
  `segment-1` bracket, cells 4-6 under `segment-2`. Fill each cell with a fact
  that belongs to that segment; a group-level fact under a segment bracket reads
  as mis-attribution. Cells 1-2 carry `#[x]` badge figures (fig, maskable; the
  anchor's habit is ranks but any short figure of the segment's fits); cells
  3-6 carry worded badges (`lang-band-v1..4`) that pair with their captions.
- **The recon table is two column groups**: "Average for the" (columns 1-2,
  with `lang-rec-ended-1/2` + `lang-th-rec-4/5` as their heads) and "As of"
  (columns 3-5, heads `lang-th-rec-1..3`). Average-balance figures belong in
  the average columns; period-end balances in the as-of columns.
- **Recon rows 1 and 6 are currency rows** (baked `$` signs). Only dollar
  amounts sit there; a ratio result belongs in the reconciliation prose note,
  not in the table.

## Placeholders in a shipped deck: mask vs dash

A visible mask (`[x,xxx]`) means "awaiting data", a TODO. That is right while
drafting and wrong in a deck being shipped, where the genre's marker for
"confirmed not available or not applicable" is the en dash. The rule:

- A figure the user may still supply stays MASKED, and the build report counts
  it so the user can fill it.
- A cell the user has confirmed has no data (a comparison period the outline
  does not cover, a spare row's figures) is FILLED with an en dash (a plain
  `–`), which renders as the genre's null marker.
- Chart bar labels stay masked ONLY when no chart data is supplied. The right
  fix is the `charts` section below: user values drive the geometry and the
  labels, and the synthetic-bars problem disappears.
- **A legend slot with no series to name** (a masked chart on a page whose
  issuer has fewer series than the template shows) is FILLED with the en dash,
  same as a confirmed-absent figure: keeping it leaks fiction, and with no
  `charts` data there is no exemption to invoke. Supplying `charts` with the
  real series count is always the better fix when the data exists.

## Data-driven charts (v1.1)

`charts.json` in this catalog entry declares every chart: id, page, kind
(stacked or pair), category count, max series, whether segments carry printed
labels, and the measured px scale. deck.json may supply, per chart id:

```json
"charts": {
  "module":    {"series": [[2310, 2180, 2050], [1480, 1300, 1160]],
                "totals": ["5,440", "5,080", "4,760"]},
  "m2:module": {"series": [[...]]},
  "pr-1":      {"values": [4810, 5440], "totals": ["4,810", "5,440"], "trend": "+13%"}
}
```

- `series` (stacked): one list per series in seg order, each with one
  non-negative number per category. Fewer series than the template maximum is
  the SUPPORTED way to handle a 3-segment issuer: surplus bars and their
  legend slots disappear, and coverage exempts those legends.
- Heights are computed geometry (allowed); every printed label is the user's
  own number. `totals` are strings printed verbatim and OPTIONAL: a column sum
  the user did not supply stays masked, because a computed visible figure is
  still a computed visible figure.
- `pair` charts (the three panel-row panels) take `values` [prior, current]
  plus optional `totals` (two label strings) and `trend`.
- A supplied chart makes its bars honest. An unsupplied chart stays masked.
  There is no third state.

## Collapse points (v1.1)

`collapse.json` declares the only blocks a deck may remove; deck.json lists
them in `drop` (module ids take `m<N>:` prefixes):

| id | what goes | use when |
|---|---|---|
| `module.row-1..5` | one table line row | the segment has fewer revenue lines than rows |
| `module.cols-34` | comparison columns 3-4 | the outline covers one comparison period |
| `cs.targets` | the chart-split targets frame | no targets are being (re)announced there |
| `hc.boxes` | the hero growth-channel boxes | nothing earns the row |
| `recon.avg-cols` | the "Average for the" column group | the reconciliation has no average balances |
| `recon.asof-cols-23` | the second and third "As of" date columns | the deck has one balance date; composes with `avg-cols` |

Slots inside a dropped block need no fill or keep; the checker exempts them
and warns if a fill targets one. An id not in collapse.json FAILS. This is
subtraction from a measured page; there is no free-form removal or resizing,
and preferring a drop over a row of dashes is the right call whenever the
whole block is empty rather than sparse.

## Density budgets

`budgets.json` carries three numbers per ceiling; **`budget` is the only one a
generator may consume**: `budget = min(house, capacity - 1)`. Capacity is what the
geometry holds; house is what a real deck sets; the model cannot see the rendered
page, so it gets one item of headroom below geometry and never more than the genre
sets. Where the grid fixes a count (three panels, six tiles, six band cells), the
budget equals it: there is no such thing as two and a half columns.

**A count is "of the item as written on that slide."** The split page holds 13 of
the two-line bullets it actually sets and roughly twice as many one-line ones. When
no budget row covers a span, match the default span's length within about ±10%; the
tight buckets are band cells (~20-30 chars), checklist h3s (~25-45), panel-row boxes
(~20-30), stat-board boxes (~65-75).

Over budget means cut or split into another page. **Never shrink type, never tighten
leading, never widen a box.** The geometry is measured; content adapts to it.

**Where the grid fixes the slot count and no collapse point covers it, the grid
wins over the budget number.** Coverage requires the fixed structure filled;
a budget below the fixed count describes the anchor's typical density, not a
cap you can meet by leaving narrative slots empty. This applies wherever the
two disagree: the six checklist groups, the three stat-board frame boxes, the
seven recon note slots. Budgets bind hardest on variable-count zones and on
length.

## Voice and claim shapes

- Claim shapes are preserved: a superlative span stays a superlative, a
  delivered-action span stays past-tense verb-first, chart heads stay noun phrases
  with the unit in parentheses.
- Spelling follows the user's content. (The template's neutral defaults use British
  spellings; that is the fiction issuer's voice, not a rule for user decks.)
- "Record" and similar superlatives: use only where the user's content asserts them.
- Titles obey the register seam above.

## The brand kit (v1: logo + colours only; fonts are fixed)

**Retheme every chromatic role or none.** Two brand colours dropped onto header and
accent leave the quote panel, the emphasis rows, the cover field and the chart ramp
in the template's blue: the deck wears two palettes at once (found in calibration,
2026-08-05). When the user supplies brand colour, derive the full set:

| Role | Derivation from the brand kit |
|---|---|
| `--c-header` | primary, dark |
| `--c-accent` | primary or a near-adjacent of it (it sets 16.7px type on white) |
| `--c-panel` | mid tint of primary, still >= 4.5:1 under `--c-ink` |
| `--c-emphasis` | pale tint of primary (the subtotal band) |
| `--c-cover-field` + `--c-cover-ink` | pale tint of primary + a near-black of it |
| `--c-s1`/`--c-s2` | primary pair, dark to light; dark takes reversed ink, light takes dark ink |
| `--c-s3`/`--c-s4` | SECONDARY-hue pair, same lightness logic, chosen by the ramp rule below |
| `--c-forward` | The target/outlook role (it never marks a reported number, and that job must survive): a DARK variant of the secondary; the slate dark `#3f4a54` when the slate fallback is in play; template teal untouched for gray brands. Found escaping the retheme in calibration run 2 |

**The ramp rule** (decided 2026-08-05, Teng). The invariant: the ramp must end up
with two visually separable pairs, at most one of them neutral. Hue = which
business line, so never invent a hue the brand does not own. A colour counts as
gray when its RGB channel spread is under about 10%; the boundary is deliberately
harmless, since both nearby branches are neutral-safe.

| User supplied | Ramp pairs |
|---|---|
| Nothing | Template palette untouched, everywhere. No derivation at all |
| Primary + secondary, at least one chromatic | Both, dark-to-light per pair |
| Primary + secondary, both gray | Collapses to the gray-primary row: two gray pairs are not separable |
| Primary only, chromatic | Primary pair + the neutral slate fallback: `--c-s3: #3f4a54`/`--c-s3-ink: #ffffff`, `--c-s4: #aab4bd`/`--c-s4-ink: #101418` (pre-cleared 9.0:1 and 8.8:1) |
| Primary only, gray | Gray carries every non-chart role (monochrome is genre-correct); the ramp AND `--c-forward` keep **this template's own defaults** untouched. A neutral brand does not fight a chromatic chart surface |
| Three or more colours | First two in the order given, or ask which two; extras unused in v1 |

Phrase matters: the gray branch keeps "the template's default ramp", not "blue and
teal". Each catalog entry ships its own default ramp, so the rule ports to every
future bank template with zero edits. **Whenever a fallback branch fires, say so
in the run summary.** The contrast checks re-run on every touched pair regardless
of branch.

**Palette.** Free-to-set tokens carry the brand; each ships PAIRED with its ink, and
the pair changes together or not at all:

| Token | Role | Constraint |
|---|---|---|
| `--c-header` | dark fill under reversed type (table heads, tile heads) | >= 4.5:1 vs `--c-ink-reverse` |
| `--c-panel` | the quote field | >= 4.5:1 vs `--c-ink` |
| `--c-accent` | page rule, module rules, bracket label | >= 4.5:1 vs `--c-ground` (it sets 16.7px type) |
| `--c-emphasis` | subtotal and total rows | >= 4.5:1 vs `--c-ink` |
| `--c-s1..s4` + `--c-sN-ink` | the chart ramp | each fill >= 4.5:1 vs its own ink |
| `--c-cover-field` + `--c-cover-ink` | the cover colour field | pair travels together |

The ramp is **two pairs, not one slope**: hue says which business line, lightness
says which sub-line. Ask for the brand's secondary hue rather than deriving one.
Leave `--c-ground`, `--c-ink`, `--c-ink-reverse` alone: a dark ground is a different
piece of work, not a brand application.

**Mark.** PNG with alpha, dropped into the dimensioned brand slots as a data URI.
Height-normalised: 37.8px body pages, 57.6px cover; width ceilings 260/392px are
stops, not sizes. The cover slot sits on `--c-cover-field` (pale by default), so a
white-only mark dies there: supply a dark variant for the cover, or re-set the
field+ink pair and re-check contrast.

**Type.** Fixed in v1 (`--f-title` Oswald, `--f-body` IBM Plex Sans, `--f-voice`
Spectral). Two of three roles are gated by measurement; swaps are a v2 question, not
a knob.

## What the generator never does

- Edit HTML. The deck is expressed entirely as `deck.json`; the builder renders it.
- Write the CTA. The builder injects it from `cta.json`; a presence check enforces it.
- Shrink, squeeze, or restyle to fit. Budgets decide; content yields.
- Add agenda, divider, or closing pages. The genre has none.
- Compute nothing visible: masked `[x,xxx]` figures the user did not supply stay
  masked, visibly, rather than being invented.

## The deck.json contract (v1)

```json
{
  "_meta": {"template": "institutional-ir", "title": "..."},
  "pages": ["cover", "snapshot", {"pattern": "module", "count": 3}, "split", "recon"],
  "tokens": {"--c-header": "#123456", "--c-accent": "..."},
  "marks": {"cover": "path/logo-dark.png", "body": "path/logo.png"},
  "slots": {"cover-title": "...", "segment-1": "...", "m2:segment-1": "..."},
  "keep": ["lang-scaf-netrevenue-1"]
}
```

- `pages`: ordered subset of the twelve patterns; `module` may carry a count. The
  builder clones module instances and prefixes every slot inside instance N with
  `m<N>:` (instance 1 keeps bare names).
- `slots`: fills by slot name; cloned-instance slots use the prefix.
- `keep`: slots deliberately left at their template default (scaffold lines,
  structural labels). Everything else on a retained page must appear in `slots`,
  except `fig-*` sites: an unfilled figure stays visibly masked by design.
- `tokens`/`marks`: the brand kit. Only the free-to-set tokens above.

`check_deck.py` validates this file against `slots.json` + `budgets.json` before
`build_deck.py` renders; both fail loudly with the page, slot and overage named.
