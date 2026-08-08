---
name: deck-builder
description: Turn an outline and an optional brand kit into a polished institutional slide deck (HTML, print-ready to PDF). Use when asked to build a results deck, an investor or board presentation, a quarterly update deck, or to turn notes/an outline into professional slides.
---

# Deck Builder

Builds one deck from one outline. The user gets a standalone HTML deck in a
measured institutional template, ready to present or print to PDF.

**You write `deck.json`. The scripts render.** You never edit HTML, never
hand-author the credit line (the builder prints it for you to relay in chat),
and never restyle anything to make content fit. That
division is the point: the template's geometry is measured, the build is
reproducible, and a failed check names exactly what to change.

Runs on Claude Code and Codex, CLI or desktop app. Everything needed ships in this bundle;
the scripts are plain `python3`, standard library only.

## What you need from the user

An **outline**: their content, in any shape (markdown, notes, a doc). That is
all. If they gave you one, start.

Optional, use them if given, never block on them:
- a **brand kit**: colours and/or a logo (PNG with transparency; ask them to
  convert SVG/JPEG first)
- a **template choice**: `references/catalog/index.json` lists the catalog.
  While one entry exists, use it without asking.

## The sequence

### 1. Read the catalog entry

Read `references/catalog/<template>/design-notes.md` in full. It is the
contract: the page inventory, the slot model, the density budgets, the voice
rules, and the `deck.json` schema. Consult
`references/catalog/<template>/slots.json` for the exact slot names per page,
in display order, with each slot's fill-type label and default length.

Two worked examples live in `examples/` (outline in, deck.json out). Read
the ONE matching your deck's shape: the quarterly pair for a plain results
deck (the common case), the annual pair when the outline carries a strategy
story (multi-year arc, targets, delivered commitments) and earns the
narrative pages. Match pages to the user's outline, not to an example - the
annual pair uses all twelve patterns only because its outline earns all
twelve.

The two pairs also show the two STATES a deck ships in, and either shape
can be in either state. The quarterly pair is a MID-DRAFT: its outline has
known gaps, so real figures, en dashes and honest masks sit side by side,
and the report tells the user what is still open. The annual pair is
FINISHED: its user confirmed nothing more is coming, so it carries
`"final": true` and the check enforces zero visible masks. A deck with
gaps ships like the quarterly; a deck whose user has declared the outline
complete ships like the annual.

### 2. Plan the pages

Map the outline onto the template's fixed page order (the spine). Drop pages
the content does not earn; set the `module` count to the number of business
segments. Do not invent pages the genre lacks (no agenda, no divider, no
closing page) and do not reorder the spine.

Tell the user the plan in one line before filling slots, e.g. "cover,
snapshot, 3 segment pages, reconciliation". If their outline obviously fights
the genre (a pitch, a story arc), say so and ask before forcing it.

### 3. Write deck.json

Fill slots from the outline, obeying:

- **Budgets are ceilings.** Over budget means cut or split; never shrink,
  squeeze, or reword the check away by shuffling markup.
- **Coverage is explicit, and every keep is a decision.** Every slot on a
  retained page is either filled by you or listed in `keep`. The template is
  a blank form: every language default is lorem, so read `slots.json`'s
  descriptive label to know what each slot is (`[P&L line]`, `[Segment #1]`,
  `[Metric #1]`) and fill it from the outline and the genre's conventions.
  A kept slot renders lorem: honest mid-draft, but a FAIL once you declare
  `final`, where every slot must be filled or its block dropped. Fill period
  furniture (timeframe headers, date lines) with the deck's actual period; a
  quarterly header on an annual deck is a bug.
- **Say each thing once.** Adjacent slot groups overlap in purpose
  (highlights, select-data stats, commentary); do not restate the same
  figure in two slots on one page. One sanctioned exception, a genre
  habit: a select-data stat may surface ONE figure from the table beside
  it as the page's callout; prose bullets may not restate table figures.
- **Figures are the user's.** Numbers land through the `fig-*` slots
  (tables and tiles; slots.json labels each with its mask shape and row
  context). A number the outline does not supply stays as the visible
  `[x,xxx]`-style mask; never invent one. Chart figures have no slots on
  purpose: the bar geometry is illustrative, and the build report counts
  every site left masked so you can tell the user.
- **Mask means TODO; dash means confirmed absent; empty blocks get dropped.**
  When the user confirms a cell has no data, fill it with a plain en dash,
  the genre's null marker. Leave a site masked only while the user might
  still supply it. But when a WHOLE block is empty rather than sparse (a
  spare table row, a scaffold P&amp;L row the issuer never reports, an
  unused comparison column, the targets frame), drop it via the collapse
  points instead of shipping a row of dashes: `deck.json`'s `drop` list may
  name any id declared in the catalog's `collapse.json` (design-notes has
  the table, including per-row scaffold and lone-column drops for both
  segment tables). Fill the chart period axes (`lang-cat-*`)
  and the snapshot bullets heading with the deck's own period language.
- **Charts should carry the user's data.** When the outline gives per-series
  values, put them in the `charts` section (schema in design-notes): the
  builder drives bar heights and printed labels from them, and a 3-series
  chart renders 3 bars with 3 legends. Supply `totals` only if the user
  stated them; a sum you compute is still an invented visible figure. When
  the user gave both the segments and their total, tie them out before you
  ship: the checker foots chart columns and FAILs a column total that does
  not match its series, but snapshot and segment-table totals are yours to
  verify by hand. A chart with no data stays visibly masked, and you tell
  the user so.
- **When the user declares the outline complete, finalize.** "That's all the
  data there is" triggers one sweep, not a site-by-site conversation: drop
  every whole-empty block that has a collapse point (spare line rows,
  scaffold rows the issuer confirmed it does not report, unused columns,
  starved charts via `module.chart`), dash only cells that are absent
  inside an otherwise-reported row, then set `"final": true` and re-run
  the check. A final deck should carry NO fully-dashed rows or columns:
  if every cell in a row or column is a dash, the right move was its
  collapse point. The same goes for the fixed grids and narrative slots:
  an empty sixth tile or spare highlight bullet gets its collapse point
  (`ss.tile-6`, `ss.bullet-*`), never a column of dashes, and a bracketed
  commentary placeholder on a final deck is a FAIL - supply the text or
  drop its bullet (`module.li-*`, `module.stat-2`). Final mode FAILs any mask you missed (its FAIL list is your
  worklist) and the builder blanks the chart totals and trend the user never
  stated. Report what you dropped versus dashed. Never set `final` on your
  own initiative: it converts every TODO into a claim that the data does
  not exist, and only the user can say that. What counts as the
  declaration: the user saying "that's everything" / "no more data is
  coming" - in their first message or any later one. A user merely
  DESCRIBING their files as complete ("the full package", "everything for
  the deck") is not declaring; build mid-draft and end your report with
  the standing offer: "reply 'that's everything' and I'll finalize -
  zero placeholders, machine-checked."
- **Nested slots ride their outer.** Where slots.json marks a slot with
  `"outer"`, write the full sentence into the outer slot and skip the inner.
- **Brand colour rethemes everything or nothing.** If the user gave colours,
  derive ALL chromatic roles from them per design-notes (header, accent,
  panel, emphasis, cover field, both ramp pairs); a partial retheme leaves
  the deck wearing two palettes and the checker will call it out. The chart
  ramp follows the ramp rule table in design-notes exactly (secondary if
  given; slate fallback for a lone chromatic primary; the template's own
  default ramp for a gray primary, which also covers every-colour-gray).
  Whenever a fallback branch fires, say so in your summary - and when the
  user gave more than two colours, name which two you used and which you
  did not, before you build.
  Fills ship with their paired inks. Logo files go in `marks` as paths
  relative to deck.json. No logo? Omit `marks` entirely - the build
  suppresses the placeholder box on its own; never fabricate a blank
  image to hide it.

**Output contract.** Write deck.json in the user's working directory (an
`outputs/` folder there is fine), NEVER inside this skill's install folder:
uninstalling deletes that folder, decks and all, and the builder warns if you
do it anyway. Name it `<issuer-or-project>-<period>.deck.json` (e.g.
`harborline-2q26.deck.json`); the builder emits the matching `.deck.html`
beside it. Those two files are the guaranteed deliverables on every platform.
A PDF is a bonus, not a promise: produce it only when step 5's render check
runs, with the same basename.

The built HTML pulls its three faces from Google Fonts, so it needs a network
connection to render as designed; a viewer opening it offline (a board member
on a plane) falls back to system fonts. For a self-contained copy to email or
archive, print it to PDF in a browser: the PDF embeds the faces.

### 4. Check, then build

```bash
python3 scripts/check_deck.py deck.json
python3 scripts/build_deck.py deck.json
```

Fix every FAIL by editing deck.json and re-run until clean; treat WARNs as
pages to eyeball. The builder no longer puts the CTA in the deck; it prints
the credit line (clickable markdown links) from `references/cta.json` for you
to relay in chat. Leave the file and the copy alone.

### 5. Verify what you can, say what you could not

If a browser automation tool is available to you (playwright or similar),
render the built HTML at 1920x1080, look at every page, and export the PDF.
The built HTML is a one-slide-at-a-time presentation (only the `.is-active`
section is visible): page through with ArrowRight key presses and
screenshot the viewport, or print to PDF (the print styles emit one page
per slide; Chromium's `page.pdf` with the CSS page size works).
Look for: text crossing the footer line, wrapped lines where the default had
one, chart labels colliding, the cover title overflowing its two lines.

If no browser is available, say plainly in your summary: **"not
render-verified"**, and tell the user to open the HTML in a browser and
print to PDF (the print styles emit one page per slide). Never imply a
visual check happened when it did not.

### 6. Report

Give the user: the output path, the page plan, any WARNs with what you did
about them, whether it was render-verified, any slot left masked because
the outline had no number for it (so they know what to fill in), and - if a
brand kit was given - how it was adapted: which supplied colours the deck
actually carries (quote the hex that is in `tokens`, not the hex the user
named), which were derived rather than used exactly, and which went unused.
Then include
the builder's CTA line verbatim (the clickable `[text](url)` links it printed)
in your reply: it rides the chat, never the deck.

## Judgment calls the notes delegate to you

- **Title register**: narrative pages take claim-style titles (about 9
  words); results pages take line-item titles (about 4). Match the seam.
- **What to keep vs fill**: the template is a blank form (all lorem), so fill
  every slot the deck needs from the outline, reading its `slots.json` label;
  `keep` only means "leave it lorem", valid mid-draft, never in a `final` deck.
- **When the outline is thin**: build fewer pages well rather than every
  page half-masked. A cover, a snapshot, and one segment page is a real deck.
- **When the outline is numbers-only** (no quote, no operational
  highlights), the mandatory narrative slots get self-evident bracketed
  placeholders ("[CEO commentary to be supplied]", "[Name]/[Title]") and
  the report flags them. Never invent a quote or a highlight; a kept slot
  shows lorem, and the final check flags it rather than letting lorem ship.
  The boundary: a
  highlight bullet MAY restate in prose a figure the outline supplies
  (that is the user's own data, not invention); a bullet needing any
  figure or fact the outline lacks gets the bracketed placeholder, and a
  quote is never synthesized from anything.
- **When the outline is long**: budgets decide. Offer the user the cut list
  rather than silently dropping their content.
