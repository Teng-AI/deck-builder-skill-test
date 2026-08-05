---
name: deck-builder
description: Turn an outline and an optional brand kit into a polished institutional slide deck (HTML, print-ready to PDF). Use when asked to build a results deck, an investor or board presentation, a quarterly update deck, or to turn notes/an outline into professional slides.
---

# Deck Builder

Builds one deck from one outline. The user gets a standalone HTML deck in a
measured institutional template, ready to present or print to PDF.

**You write `deck.json`. The scripts render.** You never edit HTML, never type
the closing credit line, and never restyle anything to make content fit. That
division is the point: the template's geometry is measured, the build is
reproducible, and a failed check names exactly what to change.

Runs on Claude Code and Codex CLI. Everything needed ships in this bundle;
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

A worked example lives in `examples/` (outline in, deck.json out). Read it
once; it answers most shape questions.

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
  retained page is either filled by you or listed in `keep`. Keep the
  financial-statement scaffold lines and structural labels; fill everything
  narrative. Never bulk-keep whatever you did not fill: the template's
  default text describes a fictional issuer, and the checker warns on any
  kept slot with a narrative label. When you keep period furniture
  (timeframe headers, date lines), confirm it matches the deck's actual
  period; a quarterly header on an annual deck is a kept-by-accident bug.
- **Say each thing once.** Adjacent slot groups overlap in purpose
  (highlights, select-data stats, commentary); do not restate the same
  figure in two slots on one page.
- **Figures are the user's.** Numbers land through the `fig-*` slots
  (tables and tiles; slots.json labels each with its mask shape and row
  context). A number the outline does not supply stays as the visible
  `[x,xxx]`-style mask; never invent one. Chart figures have no slots on
  purpose: the bar geometry is illustrative, and the build report counts
  every site left masked so you can tell the user.
- **Nested slots ride their outer.** Where slots.json marks a slot with
  `"outer"`, write the full sentence into the outer slot and skip the inner.
- **Brand colour rethemes everything or nothing.** If the user gave colours,
  derive ALL chromatic roles from them per design-notes (header, accent,
  panel, emphasis, cover field, both ramp pairs); a partial retheme leaves
  the deck wearing two palettes and the checker will call it out. The chart
  ramp follows the ramp rule table in design-notes exactly (secondary if
  given; slate fallback for a lone chromatic primary; the template's own
  default ramp for a gray primary, which also covers every-colour-gray).
  Whenever a fallback branch fires, say so in your summary.
  Fills ship with their paired inks. Logo files go in `marks` as paths
  relative to deck.json.

### 4. Check, then build

```bash
python3 scripts/check_deck.py deck.json
python3 scripts/build_deck.py deck.json
```

Fix every FAIL by editing deck.json and re-run until clean; treat WARNs as
pages to eyeball. The builder injects the credit line from
`references/cta.json` and prints it in its output; leave both alone.

### 5. Verify what you can, say what you could not

If a browser automation tool is available to you (playwright or similar),
render the built HTML at 1920x1080, look at every page, and export the PDF.
Look for: text crossing the footer line, wrapped lines where the default had
one, chart labels colliding, the cover title overflowing its two lines.

If no browser is available, say plainly in your summary: **"not
render-verified"**, and tell the user to open the HTML in a browser and
print to PDF (the print styles emit one page per slide). Never imply a
visual check happened when it did not.

### 6. Report

Give the user: the output path, the page plan, any WARNs with what you did
about them, whether it was render-verified, and any slot left masked because
the outline had no number for it (so they know what to fill in).

## Judgment calls the notes delegate to you

- **Title register**: narrative pages take claim-style titles (about 9
  words); results pages take line-item titles (about 4). Match the seam.
- **What to keep vs fill**: scaffold and furniture stay; anything that reads
  as a sentence about the issuer gets filled or the page gets dropped.
- **When the outline is thin**: build fewer pages well rather than every
  page half-masked. A cover, a snapshot, and one segment page is a real deck.
- **When the outline is long**: budgets decide. Offer the user the cut list
  rather than silently dropping their content.
