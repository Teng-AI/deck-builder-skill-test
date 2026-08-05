#!/usr/bin/env python3
"""Validate a deck.json before build_deck.py renders it. Stdlib only.

    check_deck.py <deck.json> [--catalog DIR]

Every finding names the page, the slot, and the number that failed; exit is
non-zero if anything FAILED. Checks, in order:

  schema    known top-level keys; pages drawn from the template spine in
            spine order; repeat counts on module only.
  slots     every filled slot exists on a RETAINED page (m-prefixed names
            resolve against the module instance count).
  coverage  every slot site on a retained page is user-filled or listed in
            "keep". A nested slot (worded figure inside a language span)
            counts as covered when its outer slot is filled. Template
            defaults describe a fictional issuer; one leaking into a user
            deck is a defect, so coverage is a FAIL, not a warning.
            EXCEPTION: fig-* slots (masked digit figures) are optional by
            design; unfilled means visibly masked, never invented.
  length    filled text vs the template default's length (the default IS
            house-density content): over 1.30x FAILS as overflow risk,
            over 1.10x WARNS. Short spans get absolute slack instead of a
            ratio. This is a proxy: real render verification needs a
            browser and runs separately when one is available.
  tokens    only the free-to-set brand tokens; a fill and its paired ink
            travel together or the pair FAILS unset.
  contrast  WCAG ratio on every touched fill/ink pair, resolved against
            deck values first and template defaults second; under 4.5:1
            FAILS with the measured ratio and a direction hint.
  marks     files exist and are PNG; a missing alpha channel WARNS (the
            mark will sit on its own background rectangle).

What this checker does NOT do, said plainly because a silent gap reads as
coverage: it does not render, so text that wraps differently from the
default can still overflow; budgets.json's count ceilings are enforced by
the template's fixed structure rather than re-counted here; and font checks
do not exist because v1 fixes the faces.
"""
import html as htmllib
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
REFS = HERE.parent / "references"

PAIRS = [
    ("--c-header", "--c-ink-reverse"),
    ("--c-panel", "--c-ink"),
    ("--c-accent", "--c-ground"),
    ("--c-forward", "--c-ground"),
    ("--c-emphasis", "--c-ink"),
    ("--c-s1", "--c-s1-ink"), ("--c-s2", "--c-s2-ink"),
    ("--c-s3", "--c-s3-ink"), ("--c-s4", "--c-s4-ink"),
    ("--c-cover-field", "--c-cover-ink"),
]

# blank-form labels whose template defaults carry the fictional issuer's
# STORY; keeping one of these is a leak until a person decides otherwise
NARRATIVE_LABELS = (
    "[Claim", "[Proof point", "[Achievement", "[Summary claim",
    "[Completed strategic", "[Announced strategic", "[Page headline",
    "[Presentation Title", "[Highlight", "[Commentary point", "[Headline",
    "[Executive quote", "&ldquo;[Executive", "[Name", "[Business line",
    "[Segment", "[Driver", "[Outcome", "[Catalyst", "[Growth channel",
    "[Forward", "[Key metric", "[Chart title", "[Definition of the target",
    "[Targets")
FREE_TOKENS = {t for pair in PAIRS for t in pair} - \
    {"--c-ink", "--c-ink-reverse", "--c-ground"}
FREE_TOKENS |= {"--brand-h", "--brand-max-w"}
TAG = re.compile(r"<[^>]+>")


def parse_root_vars(html):
    """Template default custom properties, var() references resolved.

    Comments are stripped first: the template's documentation prose
    mentions token names mid-sentence, and a greedy scan once rebound
    --c-ink to half a sentence about TYPE-08."""
    html = re.sub(r"/\*.*?\*/", "", html, flags=re.S)
    raw = dict(re.findall(r"(--[\w-]+)\s*:\s*([^;\n{}]+);", html))
    def resolve(v, depth=0):
        v = v.strip()
        m = re.match(r"var\((--[\w-]+)\)", v)
        if m and depth < 8 and m.group(1) in raw:
            return resolve(raw[m.group(1)], depth + 1)
        return v
    return {k: resolve(v) for k, v in raw.items()}


def luminance(hexval):
    m = re.fullmatch(r"#([0-9a-fA-F]{6})", hexval.strip())
    if not m:
        return None
    def chan(s):
        c = int(s, 16) / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    h = m.group(1)
    r, g, b = (chan(h[i:i + 2]) for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    if la is None or lb is None:
        return None
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def achromatic(hexval):
    """Gray-ish: RGB channel spread under ~10%. None if not a parseable hex.

    The threshold is deliberately forgiving: a borderline colour lands in a
    neutral-safe branch either way (the ramp rule in design-notes)."""
    m = re.fullmatch(r"#([0-9a-fA-F]{6})", str(hexval).strip())
    if not m:
        return None
    ch = [int(m.group(1)[i:i + 2], 16) for i in (0, 2, 4)]
    return (max(ch) - min(ch)) / 255 <= 0.10


def strip_tags(html):
    # unescape so &amp; counts as one character, the way it renders
    return htmllib.unescape(re.sub(r"\s+", " ", TAG.sub(" ", html)).strip())


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    deck_path = pathlib.Path(args[0])
    deck = json.loads(deck_path.read_text())
    template_id = deck.get("_meta", {}).get("template", "institutional-ir")
    catalog = pathlib.Path(sys.argv[sys.argv.index("--catalog") + 1]) \
        if "--catalog" in sys.argv else REFS / "catalog" / template_id

    slots_map = json.loads((catalog / "slots.json").read_text())["pages"]
    tpl_vars = parse_root_vars((catalog / "template.html").read_text())
    spine = list(slots_map)

    fails, warns = [], []
    def fail(msg): fails.append(msg)
    def warn(msg): warns.append(msg)

    # --- schema -------------------------------------------------------------
    for key in deck:
        if key not in {"_meta", "pages", "tokens", "marks", "slots", "keep"}:
            fail(f"schema: unknown top-level key {key!r}")

    plan = []
    for p in deck.get("pages", spine):
        pattern = p if isinstance(p, str) else p.get("pattern")
        count = 1 if isinstance(p, str) else int(p.get("count", 1))
        if pattern not in spine:
            fail(f"pages: {pattern!r} is not in the spine {spine}")
            continue
        if count > 1 and pattern != "module":
            fail(f"pages: only module may repeat; {pattern} has count {count}")
        plan.append((pattern, count))
    order = [p for p, _ in plan]
    in_spine_order = [p for p in spine if p in order]
    if order != in_spine_order:
        fail(f"pages: order must follow the template spine; got {order}, "
             f"spine order would be {in_spine_order}")
    if len(set(order)) != len(order):
        fail(f"pages: duplicate patterns in {order} (repeat module via "
             "count, not by listing it twice)")
    retained = dict(plan)
    module_count = retained.get("module", 0)

    # --- slot existence -----------------------------------------------------
    site_slots = {s["slot"] for page in spine for s in slots_map[page]}
    filled = set(deck.get("slots", {}))
    kept = set(deck.get("keep", []))
    for slot in filled | kept:
        m = re.match(r"m(\d+):(.+)", slot)
        base, inst = (m.group(2), int(m.group(1))) if m else (slot, 1)
        if base not in site_slots:
            fail(f"slots: {slot!r} does not exist in the template")
            continue
        pages_of = [p for p in spine
                    if any(s["slot"] == base for s in slots_map[p])]
        if m and "module" not in pages_of:
            fail(f"slots: {slot!r} uses an m-prefix but {base!r} has no "
                 "site on the module page")
        if m and inst > max(module_count, 1):
            fail(f"slots: {slot!r} names module instance {inst} but the "
                 f"plan has {module_count}")
        if m and inst == 1:
            fail(f"slots: {slot!r} — instance 1 keeps bare names; drop the "
                 "m1: prefix")
        if not any(p in retained for p in pages_of):
            fail(f"slots: {slot!r} lives only on dropped pages {pages_of}")

    # --- coverage -----------------------------------------------------------
    def covered(name, site):
        if site["slot"].startswith("fig-"):
            return True
        if name in filled or name in kept:
            return True
        if "outer" in site:
            outer = site["outer"]
            pref = name.split(":", 1)[0] + ":" if ":" in name else ""
            return (pref + outer) in filled
        return False

    for pattern in retained:
        instances = range(1, retained[pattern] + 1) \
            if pattern == "module" else [1]
        for i in instances:
            pref = f"m{i}:" if i > 1 else ""
            for site in slots_map[pattern]:
                name = pref + site["slot"]
                if not covered(name, site):
                    fail(f"coverage: {pattern} (instance {i}) slot {name!r} "
                         f"[{site['label']}] is neither filled nor kept; "
                         "the template default is fictional-issuer text")

    # keep-leak: a kept slot whose blank-form label is narrative still
    # renders the fictional issuer's text (calibration run 2 shipped one).
    # Legitimate keeps are furniture; narrative keeps draw one aggregate
    # warning so a deliberate choice survives and a bulk-keep gets caught.
    label_of = {}
    for page in spine:
        for s in slots_map[page]:
            label_of.setdefault(s["slot"], s["label"])
    leaky = []
    for name in sorted(kept):
        base = name.split(":", 1)[1] if ":" in name else name
        lab = label_of.get(base, "")
        if lab.startswith(NARRATIVE_LABELS):
            leaky.append(f"{name} [{lab[:30]}]")
    if leaky:
        shown = ", ".join(leaky[:8])
        more = f" (+{len(leaky) - 8} more)" if len(leaky) > 8 else ""
        warn(f"keep-leak: {len(leaky)} kept slot(s) have narrative labels "
             f"and will render the template's fictional-issuer text: "
             f"{shown}{more}; fill them or drop the page")

    # --- length -------------------------------------------------------------
    default_len = {}
    for page in spine:
        for s in slots_map[page]:
            default_len[s["slot"]] = max(default_len.get(s["slot"], 0),
                                         s["default_len"])
    for slot, content in deck.get("slots", {}).items():
        base = slot.split(":", 1)[1] if ":" in slot else slot
        d = default_len.get(base, 0)
        L = len(strip_tags(content))
        # Proxies for "wraps like the house content it replaces". Strings
        # up to the tightest measured bucket (~34 chars, band cells and
        # checklist h3s) cannot overflow anything and only ever WARN;
        # longer ones fail on ratio or absolute growth, whichever is
        # kinder to short defaults.
        if L > 34 and L > max(d * 1.30, d + 10):
            fail(f"length: {slot!r} is {L} chars against a {d}-char "
                 "default; cut or split, never shrink type")
        elif L > max(d * 1.10, d + 4):
            warn(f"length: {slot!r} is {L} chars against a {d}-char "
                 "default; likely fine, eyeball that page")

    # --- tokens + contrast --------------------------------------------------
    tokens = deck.get("tokens", {})
    for t in tokens:
        if t not in FREE_TOKENS:
            fail(f"tokens: {t!r} is not free to set (free set: "
                 f"{sorted(FREE_TOKENS)})")
        elif t not in tpl_vars:
            # a token the template never declares injects fine and changes
            # nothing; this exact silent no-op shipped once (--c-accent-2,
            # a name invented from metadata while the CSS says --c-forward)
            fail(f"tokens: {t!r} is not declared in the template's :root; "
                 "the override would be a silent no-op")

    # retheme is all-or-none: a brand colour on some chromatic roles with
    # template blue left on the rest is two palettes at once. ONE sanctioned
    # exception (the ramp rule, design-notes): a gray brand keeps the
    # template's own default ramp, because a neutral does not fight a
    # chromatic ramp and two gray pairs would not separate.
    chromatic = ["--c-header", "--c-panel", "--c-accent", "--c-forward",
                 "--c-emphasis", "--c-s1", "--c-s2", "--c-s3", "--c-s4",
                 "--c-cover-field"]
    # a gray brand keeps the template's chart colours: the ramp AND the
    # teal target role (both stay chromatic so their jobs survive)
    template_chart = {"--c-s1", "--c-s2", "--c-s3", "--c-s4", "--c-forward"}
    touched = [t for t in chromatic if t in tokens]
    untouched = [t for t in chromatic if t not in tokens]
    gray_brand = touched and \
        all(achromatic(tokens[t]) for t in touched) and \
        set(untouched) <= template_chart
    if touched and untouched and not gray_brand:
        warn(f"partial retheme: tokens recolour {', '.join(touched)} but "
             f"{', '.join(untouched)} still carry the template palette; "
             "retheme every chromatic role or none (design-notes, brand kit)")
    if "--c-s1" in tokens and "--c-s3" in tokens \
            and achromatic(tokens["--c-s1"]) and achromatic(tokens["--c-s3"]):
        fail("ramp: both pairs are gray, so the two business lines cannot "
             "be told apart; use the gray-primary branch of the ramp rule "
             "(template default ramp) instead")
    for fill_t, ink_t in PAIRS:
        if (fill_t in tokens) != (ink_t in tokens) \
                and ink_t in FREE_TOKENS:
            fail(f"tokens: {fill_t} and {ink_t} are a pair and travel "
                 "together; one without the other ships illegible type")
    resolved = dict(tpl_vars)
    resolved.update(tokens)
    for fill_t, ink_t in PAIRS:
        if fill_t not in tokens and ink_t not in tokens:
            continue
        ratio = contrast(resolved.get(fill_t, ""), resolved.get(ink_t, ""))
        if ratio is None:
            warn(f"contrast: could not resolve {fill_t}/{ink_t} to hex; "
                 "check manually")
        elif ratio < 4.5:
            fail(f"contrast: {fill_t} on {ink_t} measures {ratio:.2f}:1, "
                 "needs 4.5:1; move the fill darker or the ink lighter")

    # --- marks --------------------------------------------------------------
    for role, rel in deck.get("marks", {}).items():
        p = (deck_path.parent / rel).resolve()
        if not p.exists():
            fail(f"marks: {role} asset missing at {p}")
            continue
        head = p.read_bytes()[:26]
        if head[:8] != b"\x89PNG\r\n\x1a\n":
            fail(f"marks: {role} at {p} is not a PNG (magic bytes); "
                 "convert first, SVG/JPEG are not accepted in v1")
        elif head[25] not in (4, 6):
            warn(f"marks: {role} PNG has no alpha channel; it will sit on "
                 "its own background rectangle")

    # --- report -------------------------------------------------------------
    for w in warns:
        print(f"WARN  {w}")
    for f in fails:
        print(f"FAIL  {f}")
    print(f"\n{len(fails)} failed, {len(warns)} warnings"
          f" ({deck_path.name} against {template_id})")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
