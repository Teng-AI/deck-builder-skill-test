#!/usr/bin/env python3
"""Render a deck.json over a catalog template. Deterministic; stdlib only.

    build_deck.py <deck.json> [--catalog DIR] [--out FILE]

The generating model writes deck.json and NOTHING else; this script is the
only writer of HTML. Run check_deck.py first: this builder trusts its input
and fails on structural impossibilities only, while the checker owns
coverage, budgets and contrast.

What it does, in order:

  pages    keep the template's fixed page order (the spine), drop pages the
           plan omits, clone the module pattern N times. Clone i (i >= 2)
           has every data-slot renamed to "m<i>:<name>" so instances fill
           independently.
  tokens   CSS custom properties, injected as a <style id="brand-profile">
           block before </head>; cascade order does the work.
  slots    innerHTML per data-slot site, paired by tag-balance scan (a
           nested slot inside a filled outer is wiped by the outer fill;
           that is by design, the outer fill carries the whole sentence).
           cover-title fills are re-wrapped into the template's hang spans.
  marks    PNGs with alpha, embedded as data URIs into the brand slots;
           paths resolve relative to the deck.json's directory.
  folios   renumbered contiguously in page order (the cover carries none).
  cta      the footer strip on the LAST rendered page, from
           references/cta.json. Absent file renders silence. When present,
           the same line is printed to stdout so it reaches the chat
           surface on every run.

Port of the lane's research/tools/brand.py (institutional-deck-templates),
extended with the page plan and the CTA. The slot fill here uses a balance
scan instead of brand.py's non-greedy regex, so nested same-tag content
cannot truncate a fill.
"""
import base64
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
REFS = HERE.parent / "references"
SECTION = re.compile(r'<section class="slide slide--([\w-]+)( is-active)?">')
OPEN_SLOT = r'<(\w+)([^>]*\bdata-slot="{name}"[^>]*)>'


def element_end(html, open_end, tag):
    """Index just past the close tag matching an element opened at open_end."""
    depth = 1
    for m in re.finditer(rf"<{tag}\b[^>]*>|</{tag}>", html[open_end:]):
        depth += -1 if m.group(0).startswith("</") else 1
        if depth == 0:
            return open_end + m.end()
    sys.exit(f"unbalanced <{tag}> in template (element opened at {open_end})")


def fill_slot(html, name, content):
    """Replace innerHTML of every data-slot site named `name`. Returns
    (html, count). Sites are re-scanned after each replacement because
    offsets move."""
    n = 0
    pos = 0
    pat = re.compile(OPEN_SLOT.format(name=re.escape(name)))
    while True:
        m = pat.search(html, pos)
        if not m:
            return html, n
        end = element_end(html, m.end(), m.group(1))
        close = f"</{m.group(1)}>"
        html = html[:m.end()] + content + html[end - len(close):end] + html[end:]
        pos = m.end() + len(content) + len(close)
        n += 1


def hang_wrap(content):
    lines = re.split(r"<br\s*/?>", content)
    return "".join(f'<span class="hang hang-l{i + 1}">{line}</span>'
                   for i, line in enumerate(lines))


def normalize_pages(pages):
    """[(pattern, instances)] from the deck.json pages list."""
    plan = []
    for p in pages:
        if isinstance(p, str):
            plan.append((p, 1))
        else:
            plan.append((p["pattern"], int(p.get("count", 1))))
    return plan


def split_sections(html):
    """(prefix, [(pattern, chunk)], tail). Each chunk starts at the comment
    or whitespace preceding its <section> so a dropped page takes its
    header comment with it."""
    starts = list(SECTION.finditer(html))
    if not starts:
        sys.exit("no slide sections found in template")
    bounds = []
    for m in starts:
        end = element_end(html, m.end(), "section")
        bounds.append((m.start(), end, m.group(1)))
    prefix_end = bounds[0][0]
    sections, chunk_start = [], prefix_end
    for i, (s, e, pattern) in enumerate(bounds):
        sections.append((pattern, html[chunk_start:e]))
        chunk_start = e
    return html[:prefix_end], sections, html[chunk_start:]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    deck_path = pathlib.Path(args[0])
    deck = json.loads(deck_path.read_text())
    template_id = deck.get("_meta", {}).get("template", "institutional-ir")

    catalog = pathlib.Path(sys.argv[sys.argv.index("--catalog") + 1]) \
        if "--catalog" in sys.argv else REFS / "catalog" / template_id
    tpl_path = catalog / "template.html"
    if not tpl_path.exists():
        sys.exit(f"catalog entry missing: {tpl_path}\n"
                 "run sync-catalog.sh (repo checkout) or re-download the "
                 "skill bundle; the template is part of it")
    html = tpl_path.read_text()

    # --- page plan ----------------------------------------------------------
    prefix, sections, tail = split_sections(html)
    spine = [p for p, _ in sections]
    plan = normalize_pages(deck.get("pages", spine))
    unknown = [p for p, _ in plan if p not in spine]
    if unknown:
        sys.exit(f"unknown patterns in pages: {unknown}; spine is {spine}")
    wanted = dict(plan)
    multi = [p for p, n in plan if n > 1 and p != "module"]
    if multi:
        sys.exit(f"only the module pattern may repeat; got counts on {multi}")

    body_parts = []
    for pattern, chunk in sections:
        if pattern not in wanted:
            continue
        count = wanted[pattern]
        body_parts.append(chunk)
        for i in range(2, count + 1):
            clone = re.sub(r'\bdata-slot="([^"]+)"',
                           lambda m, i=i: f'data-slot="m{i}:{m.group(1)}"',
                           chunk)
            body_parts.append(clone)
    body = "".join(body_parts)

    # exactly the first rendered page is active
    body = body.replace(" is-active", "")
    body = body.replace('<section class="slide slide--',
                        '<section class="slide is-active slide--', 1) \
        if '<section class="slide slide--' in body else body
    html = prefix + body + tail

    # --- tokens -------------------------------------------------------------
    tokens = deck.get("tokens", {})
    if tokens:
        block = "\n".join(f"        {k}: {v};" for k, v in tokens.items())
        style = ('    <style id="brand-profile">\n      /* deck.json token '
                 "overrides; the base ZONE A stays untouched */\n"
                 f"      :root {{\n{block}\n      }}\n    </style>\n")
        html, n = re.subn(r"(?=  </head>)", style, html, count=1)
        if n != 1:
            sys.exit("could not find </head> to carry the token block")

    # --- slots --------------------------------------------------------------
    # slots.json records a markup_prefix for slots whose default leads with
    # an empty element (legend swatches); a plain-text fill gets it back so
    # the swatch survives the fill
    prefixes = {}
    slots_path = catalog / "slots.json"
    if slots_path.exists():
        for page in json.loads(slots_path.read_text())["pages"].values():
            for site in page:
                if "markup_prefix" in site:
                    prefixes[site["slot"]] = site["markup_prefix"]

    filled, missing = [], []
    for slot, content in deck.get("slots", {}).items():
        if slot == "cover-title":
            content = hang_wrap(content)
        base = slot.split(":", 1)[1] if ":" in slot else slot
        if base in prefixes and not content.lstrip().startswith("<"):
            content = prefixes[base] + content
        html, n = fill_slot(html, slot, content)
        (filled if n else missing).append(f"{slot} x{n}" if n else slot)
    if missing:
        sys.exit("deck.json names slots the rendered deck does not carry "
                 f"(dropped page, bad name, or bad m-prefix): {missing}")

    # --- marks --------------------------------------------------------------
    def data_uri(rel):
        p = (deck_path.parent / rel).resolve()
        if not p.exists():
            sys.exit(f"mark asset missing: {p}")
        return ("data:image/png;base64,"
                + base64.b64encode(p.read_bytes()).decode())

    marks = deck.get("marks", {})
    if "cover" in marks and "cover" in wanted:
        img = f'<img src="{data_uri(marks["cover"])}" alt="" />'
        html, n = re.subn(
            r'(<div class="brand-slot brand-slot--cover">)(</div>)',
            rf"\1{img}\2", html)
        if n != 1:
            sys.exit(f"expected exactly one empty cover brand slot, found {n}")
    if "body" in marks:
        img = f'<img src="{data_uri(marks["body"])}" alt="" />'
        html, body_n = re.subn(
            r'(<div class="brand-slot">)(</div>)', rf"\1{img}\2", html)
        if body_n == 0:
            sys.exit("no empty body brand slots found")

    # --- folios -------------------------------------------------------------
    counter = {"n": 0}

    def renumber(m):
        counter["n"] += 1
        return f'{m.group(1)}{counter["n"]}{m.group(3)}'

    html = re.sub(r'(<div class="folio">)(\d+)(</div>)', renumber, html)

    # --- CTA ----------------------------------------------------------------
    cta_line = None
    cta_path = REFS / "cta.json"
    if cta_path.exists():
        cta = json.loads(cta_path.read_text())
        links_html = " · ".join(
            f'<a href="{l["url"]}">{l["text"]}</a>' for l in cta["links"])
        strip = (f'\n        <div class="cta-strip">{cta["lead"]} '
                 f"{links_html}</div>\n      ")
        last = html.rfind("</section>")
        if last == -1:
            sys.exit("no sections in output; cannot place the CTA strip")
        html = html[:last] + strip + html[last:]
        css = ("      .cta-strip { position: absolute; left: 50%;"
               " transform: translateX(-50%);"
               " bottom: calc(1080px - var(--g-foot-base));"
               " font-size: var(--sz-caption); line-height: 1;"
               " color: var(--c-ink-soft); white-space: nowrap; }\n"
               "      .cta-strip a { color: inherit;"
               " text-decoration: none; }\n")
        html, n = re.subn(r"(?=  </head>)",
                          f"    <style id=\"cta\">\n{css}    </style>\n",
                          html, count=1)
        if n != 1:
            sys.exit("could not find </head> to carry the CTA style")
        cta_line = cta["lead"] + " " + " · ".join(
            l["text"] for l in cta["links"])

    # --- write --------------------------------------------------------------
    out = pathlib.Path(sys.argv[sys.argv.index("--out") + 1]) \
        if "--out" in sys.argv else deck_path.with_suffix(".html")
    out.write_text(html)
    pages_out = len(re.findall(r'<section class="slide', html))
    body = html[html.find("<section"):]
    masked = len(re.findall(r"\[x[x,.]*\]", re.sub(r"<[^>]+>", " ", body)))
    print(f"{out}  ({out.stat().st_size // 1024} KB)")
    print(f"  pages: {pages_out} (folios 1..{counter['n']};"
          " the cover carries none)")
    if masked:
        print(f"  figures still masked: {masked} sites (chart figures stay "
              "masked by design; tell the user which pages hold the rest)")
    print(f"  slots filled: {len(filled)}   tokens: {len(tokens)}")
    if cta_line:
        print(f"  CTA: {cta_line}")
    else:
        print("  CTA: none (references/cta.json absent)")


if __name__ == "__main__":
    main()
