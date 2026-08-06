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


def section_span(html, pattern, occurrence=0):
    """(start, end) of the Nth rendered section of a pattern, else None."""
    n = -1
    for m in re.finditer(r'<section class="slide[^"]*slide--([\w-]+)">', html):
        if m.group(1) == pattern:
            n += 1
            if n == occurrence:
                return m.start(), element_end(html, m.end(), "section")
    return None


def split_instance(did):
    """'m2:module.row-5' -> ('m2:', 1, 'module.row-5'); bare ids -> instance 0."""
    m = re.match(r"(?:m(\d+):)?(.+)$", did)
    inst = int(m.group(1)) - 1 if m.group(1) else 0
    pref = f"m{inst + 1}:" if inst else ""
    return pref, inst, m.group(2)


def fmt_num(v):
    return f"{v:,.10g}"


def remove_slot_element(html, name):
    m = re.search(rf'<(\w+)[^>]*\bdata-slot="{re.escape(name)}"[^>]*>', html)
    if not m:
        return html
    return html[:m.start()] + html[element_end(html, m.end(), m.group(1)):]


def cells_of(row_html):
    return re.findall(r"<t[dh]\b.*?</t[dh]>", row_html, re.S)


def drop_row_cells(table_html, idxs):
    """Remove the given cell indexes from every row of a table fragment."""
    def per_row(m):
        row = m.group(0)
        cells = cells_of(row)
        if len(cells) <= max(idxs):
            return row
        head = row[: row.find(cells[0])]
        tail = row[row.rfind(cells[-1]) + len(cells[-1]):]
        return head + "".join(c for i, c in enumerate(cells) if i not in idxs) + tail
    return re.sub(r"<tr\b.*?</tr>", per_row, table_html, flags=re.S)


def apply_drops(html, drops, blocks):
    # the two recon column groups compose; asof indexes assume avg cells are
    # still present, so it must run first
    drops = sorted(drops, key=lambda d: 0 if "asof" in d else 1)
    for did in drops:
        pref, inst, base = split_instance(did)
        blk = blocks.get(base)
        if blk is None:
            sys.exit(f"drop id not declared in collapse.json: {did}")
        fam = blk["family"]
        page = blk.get("page") or blk.get("table_page") or base.split(".")[0]
        if base.startswith("recon"):
            page = "recon"
        span = section_span(html, page, inst)
        if span is None:
            sys.exit(f"drop {did}: page '{page}' (instance {inst + 1}) is not "
                     "in the rendered deck")
        s, e = span
        sec = html[s:e]
        if fam == "table-row":
            m = re.search(rf'data-slot="{re.escape(pref + blk["anchor_slot"])}"', sec)
            if not m:
                sys.exit(f"drop {did}: anchor slot not found")
            rs = sec.rfind("<tr", 0, m.start())
            re_ = sec.find("</tr>", m.start()) + len("</tr>")
            sec = sec[:rs] + sec[re_:]
        elif fam == "table-cols":
            t = sec.find('<table class="data">')
            te = element_end(sec, t + len('<table class="data">'), "table")
            idxs = set(blk["col_indexes"])
            sec = sec[:t] + drop_row_cells(sec[t:te], idxs) + sec[te:]
        elif fam == "element":
            m = re.search(rf'<div class="{re.escape(blk["container_class"])}[" ]', sec)
            if not m:
                sys.exit(f"drop {did}: container .{blk['container_class']} not found")
            sec = sec[:m.start()] + sec[element_end(sec, sec.find(">", m.start()) + 1, "div"):]
        elif fam == "recon-asof":
            cg = sec.find("<colgroup>")
            cge = sec.find("</colgroup>")
            cols = re.findall(r"<col[^>]*/>", sec[cg:cge])
            sec = sec[:cg] + "<colgroup>" + "".join(cols[:8]) + sec[cge:]
            sec = remove_slot_element(sec, "lang-th-rec-2")
            sec = remove_slot_element(sec, "lang-th-rec-3")
            sec = re.sub(r'(colspan=")6("[^>]*data-slot="lang-rec-basis-2")',
                         r"\g<1>2\g<2>", sec, count=1)
            tb = sec.find("<tbody>")
            tbe = sec.find("</tbody>")
            sec = sec[:tb] + drop_row_cells(sec[tb:tbe], {8, 9, 10, 11}) \
                + sec[tbe:]
        elif fam == "recon-avg":
            cg = sec.find("<colgroup>")
            cge = sec.find("</colgroup>")
            cols = re.findall(r"<col[^>]*/>", sec[cg:cge])
            sec = sec[:cg] + "<colgroup>" + "".join([cols[0]] + cols[6:]) \
                + sec[cge:]
            for slot in ("lang-rec-basis-1", "lang-rec-ended-1",
                         "lang-rec-ended-2"):
                sec = remove_slot_element(sec, slot)
            sec = sec.replace('<th class="gap" rowspan="3"></th>', "", 1)
            th = sec.find("<thead>")
            the = sec.find("</thead>")
            head = sec[th:the]
            rows = list(re.finditer(r"<tr\b.*?</tr>", head, re.S))
            if len(rows) == 3:  # the date row is empty once th-4/5 slots left
                head = head[:rows[2].start()] + head[rows[2].end():]
            head = remove_slot_element(head, "lang-th-rec-4")
            head = remove_slot_element(head, "lang-th-rec-5")
            sec = sec[:th] + head + sec[the:]
            tb = sec.find("<tbody>")
            tbe = sec.find("</tbody>")
            sec = sec[:tb] + drop_row_cells(sec[tb:tbe], {1, 2, 3, 4, 5}) \
                + sec[tbe:]
        else:
            sys.exit(f"drop {did}: unknown family {fam}")
        html = html[:s] + sec + html[e:]
    return html


def rewrite_stacked(html, span, data, spec, ipref):
    s, e = span
    sec = html[s:e]
    p = sec.find('<div class="plot">')
    pe = element_end(sec, p + len('<div class="plot">'), "div")
    plot = sec[p:pe]
    series = data["series"]
    n = len(series)
    totals = data.get("totals")
    col_totals = [sum(sr[c] for sr in series) for c in range(spec["cats"])]
    scale = spec["scale_px"] / max(col_totals)
    order = []
    for x in (int(x) for x in re.findall(r"seg seg--(\d)", plot)):
        if x not in order:
            order.append(x)
    order = [x for x in order if x <= n]
    out, pos, c = [], 0, 0
    while True:
        i = plot.find('<div class="cat">', pos)
        if i < 0:
            out.append(plot[pos:])
            break
        ce = element_end(plot, i + len('<div class="cat">'), "div")
        cat = plot[i:ce]
        if totals is not None:
            t = totals[c]
            cat = re.sub(r'(<div class="total num">)[^<]*(</div>)',
                         lambda m: m.group(1) + t + m.group(2), cat, count=1)
        b = cat.find('<div class="bar">')
        be = element_end(cat, b + len('<div class="bar">'), "div")
        segs = []
        for k in order:
            v = series[k - 1][c]
            if v <= 0:
                continue
            h = max(2, round(v * scale))
            # a segment too thin to hold its label goes unlabelled; the
            # value still lives in the table, and proportions never distort
            label = fmt_num(v) if spec["seg_labels"] and h >= 22 else ""
            segs.append(f'<div class="seg seg--{k}" '
                        f'style="height: {h}px">{label}</div>')
        cat = cat[:b] + '<div class="bar">' + "".join(segs) + "</div>" + cat[be:]
        out.append(plot[pos:i])
        out.append(cat)
        pos, c = ce, c + 1
    sec = sec[:p] + "".join(out) + sec[pe:]
    if spec.get("legend_prefix"):
        for k in range(n + 1, spec["max_series"] + 1):
            sec = remove_slot_element(sec, f'{ipref}{spec["legend_prefix"]}{k}')
    return html[:s] + sec + html[e:]


def rewrite_pair(html, span, data, spec):
    s, e = span
    sec = html[s:e]
    plots = list(re.finditer(r'<div class="plot plot--pair">', sec))
    m = plots[spec["plot_index"]]
    pe = element_end(sec, m.end(), "div")
    plot = sec[m.start():pe]
    vals = data["values"]
    totals = data.get("totals")
    scale = spec["scale_px"] / max(vals)
    parts, pos, ci = [], 0, 0
    for cm in re.finditer(r'<div class="cat( cat--prior)?">', plot):
        if cm.start() < pos:
            continue
        ce = element_end(plot, cm.end(), "div")
        cat = plot[cm.start():ce]
        h = max(2, round(vals[ci] * scale)) if vals[ci] > 0 else 0
        cat = re.sub(r'(style="height: )\d+(px")', rf"\g<1>{h}\g<2>", cat,
                     count=1)
        if totals is not None:
            t = totals[ci]
            cat = re.sub(r'(<div class="total num">)[^<]*(</div>)',
                         lambda mm: mm.group(1) + t + mm.group(2), cat, count=1)
        parts.append(plot[pos:cm.start()])
        parts.append(cat)
        pos, ci = ce, ci + 1
    parts.append(plot[pos:])
    sec = sec[:m.start()] + "".join(parts) + sec[pe:]
    if "trend" in data:
        trends = list(re.finditer(r'(<div class="trend">).*?(</div>)', sec,
                                  re.S))
        t = trends[spec["plot_index"]]
        sec = sec[:t.start()] + t.group(1) + data["trend"] + t.group(2) \
            + sec[t.end():]
    return html[:s] + sec + html[e:]


def apply_charts(html, charts, spec_map):
    for cid, data in charts.items():
        ipref, inst, base = split_instance(cid)
        spec = spec_map.get(base)
        if spec is None:
            sys.exit(f"chart id not declared in charts.json: {cid}")
        span = section_span(html, spec["page"], inst)
        if span is None:
            sys.exit(f"chart {cid}: page '{spec['page']}' (instance "
                     f"{inst + 1}) is not in the rendered deck")
        if spec["kind"] == "pair":
            html = rewrite_pair(html, span, data, spec)
        else:
            html = rewrite_stacked(html, span, data, spec, ipref)
    return html


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

    # A brand slot left empty shows the template's dashed BRAND SLOT box, a
    # drafting aid; a shipped deck renders empty slots as clean whitespace.
    hide = ('    <style id="brand-slot-final">.brand-slot:not(:has(img, svg))'
            "::after { content: none; }</style>\n")
    html, n = re.subn(r"(?=  </head>)", hide, html, count=1)
    if n != 1:
        sys.exit("could not find </head> to carry the brand-slot style")

    # --- v1.1: collapse points, then data-driven charts ---------------------
    drops = deck.get("drop", [])
    charts = deck.get("charts", {})
    if drops:
        cpath = catalog / "collapse.json"
        if not cpath.exists():
            sys.exit("deck.json drops blocks but this catalog entry has no "
                     "collapse.json (v1 catalog?)")
        html = apply_drops(html, drops, json.loads(cpath.read_text())["blocks"])
    if charts:
        cpath = catalog / "charts.json"
        if not cpath.exists():
            sys.exit("deck.json carries charts but this catalog entry has no "
                     "charts.json (v1 catalog?)")
        html = apply_charts(html, charts,
                            json.loads(cpath.read_text())["charts"])

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
    skill_root = HERE.parent
    if skill_root in out.resolve().parents:
        print(f"WARN: output written inside the skill install ({skill_root}); "
              "uninstalling the skill deletes this deck. Write deck.json in "
              "the working directory instead.", file=sys.stderr)
    pages_out = len(re.findall(r'<section class="slide', html))
    body = html[html.find("<section"):]
    masked = len(re.findall(r"\[x[x,.]*\]", re.sub(r"<[^>]+>", " ", body)))
    print(f"{out}  ({out.stat().st_size // 1024} KB)")
    print(f"  pages: {pages_out} (folios 1..{counter['n']};"
          " the cover carries none)")
    if masked:
        print(f"  figures still masked: {masked} sites (chart figures stay "
              "masked by design; tell the user which pages hold the rest)")
    if not marks:
        print("  brand slots: empty (no mark supplied; the placeholder box "
              "is suppressed in the build)")
    if drops:
        print(f"  collapse points dropped: {len(drops)} "
              f"({', '.join(drops)})")
    if charts:
        print(f"  data-driven charts: {len(charts)} "
              f"({', '.join(charts)}); their geometry now carries the "
              "deck's own values")
    print(f"  slots filled: {len(filled)}   tokens: {len(tokens)}")
    if cta_line:
        print(f"  CTA: {cta_line}")
    else:
        print("  CTA: none (references/cta.json absent)")


if __name__ == "__main__":
    main()
