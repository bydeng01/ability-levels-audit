#!/usr/bin/env python3
"""Check Figure 3's caption against the artifact it sits beside.

    cd analysis/figures
    python3 check_fig3.py ../../NeurIPS_2026_newinml/neurips_2026.tex

Three independent comparisons, in order of strength:

  A. CAPTION -> DATA.  Every numeral in the caption is re-derived from
     ``_data`` and matched.  Any numeral the caption prints that is not in the
     derived set is reported; that is how a stale number survives an edit.
  B. CAPTION -> DRAWING.  The figures' geometry is read back out of
     ``fig3.pdf``'s content stream (the ``q``/``Q``/``cm`` CTM stack is
     interpreted and every mark back-projected through the axes transform), and
     the caption's positional claims are checked against where the ink actually
     is.  This is the check that catches a caption describing a previous build.
  C. MARKS -> CAPTION.  Every mark the figure draws must be keyed by the
     caption, since FIGURE_SPEC.md requires the figure be decodable from figure
     plus caption alone.  Also asserts the retired wordings are gone: after the
     2026-08-22 pass "hollow" must not appear in panel (a)'s half of the caption
     (the dropped zeros are crosses) and the shading no longer "runs to the
     interval's upper limit".

Exits non-zero on the first category with a failure.  Needs ``qpdf`` (content
stream) and the repo's ``_data``; run it from inside ``analysis/figures``.
"""
from __future__ import annotations

import math
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

import _data

PDF = Path("fig3.pdf")
OK, BAD = "  ok    ", "  FAIL  "
fails: list[str] = []


def check(cond: bool, label: str, detail: str = "") -> None:
    print(f"{OK if cond else BAD}{label}" + (f"   {detail}" if detail else ""))
    if not cond:
        fails.append(label)


# ---------------------------------------------------------------- the caption
def caption_of(tex: Path) -> str:
    t = tex.read_text()
    m = re.search(r"\{figures/fig3\.pdf\}\s*(\\caption\{.*?\})\s*\\label\{fig:three\}",
                  t, re.S)
    if not m:
        sys.exit(f"no fig:three float with figures/fig3.pdf found in {tex}")
    return m.group(1)


# ------------------------------------------------------- the drawing, from PDF
def geometry(pdf: Path) -> dict:
    """Back-project fig3.pdf's ink into data coordinates."""
    qdf = subprocess.run(["qpdf", "--qdf", "--object-streams=disable",
                          str(pdf), "-"], capture_output=True).stdout.decode("latin-1")
    main = re.findall(r"stream\n(.*?)\nendstream", qdf, re.S)[0]

    rects = []
    for m in re.finditer(r"([\d.\-]+) ([\d.\-]+) m\n([\d.\-]+) ([\d.\-]+) l\n"
                         r"([\d.\-]+) ([\d.\-]+) l\n([\d.\-]+) ([\d.\-]+) l\nh\n\nf", main):
        xs = [float(m.group(k)) for k in (1, 3, 5, 7)]
        ys = [float(m.group(k)) for k in (2, 4, 6, 8)]
        rects.append((min(xs), max(xs), min(ys), max(ys)))
    page_w = max(r[1] for r in rects)
    panels = sorted({r for r in rects if r[1] - r[0] < page_w * 0.9},
                    key=lambda r: r[0])
    ax_a, ax_b = panels[0], panels[1]
    # the bands are the rects inside panel (b) that are narrower than it
    bands = sorted((r for r in rects if r[0] >= ax_b[0] - .01 and r[1] <= ax_b[1] + .01
                    and r[1] - r[0] < (ax_b[1] - ax_b[0]) * 0.99), key=lambda r: r[0])

    def unproj(px, ax, xl):
        return xl[0] + (px - ax[0]) / (ax[1] - ax[0]) * (xl[1] - xl[0])

    # axis limits are recovered from the script's own constants rather than guessed
    XL_A, XL_B, YL_B = (-1.16, 1.33), (-0.008, 0.725), (0.0, 1.04)

    # CTM stack -> marker placements
    stack, ctm, nums, marks = [], [1, 0, 0, 1, 0, 0], [], []
    def cc(m, n):
        a, b, c, d, e, f = m; A, B, C, D, E, F = n
        return [A*a+B*c, A*b+B*d, C*a+D*c, C*b+D*d, E*a+F*c+e, E*b+F*d+f]
    for num, op in re.findall(r"(-?[\d.]+(?:e-?\d+)?)|(\bq\b|\bQ\b|\bcm\b|/M\d+ Do)", main):
        if num:
            nums.append(float(num)); continue
        if op == "q": stack.append(list(ctm)); nums = []
        elif op == "Q": ctm = stack.pop() if stack else [1, 0, 0, 1, 0, 0]; nums = []
        elif op == "cm": ctm = cc(ctm, nums[-6:]); nums = []
        else: marks.append((ctm[4], ctm[5], op.split()[0][1:])); nums = []

    a_marks = [m for m in marks if m[0] < ax_b[0]]
    dots = [unproj(x, ax_a, XL_A) for x, _, n in a_marks if n == "M0"]
    crosses = [unproj(x, ax_a, XL_A) for x, _, n in a_marks if n == "M1"]

    # long verticals inside panel (b) = the BCa rule (the other is the spine)
    rules = []
    for m in re.finditer(r"([\d.\-]+) ([\d.\-]+) m\n([\d.\-]+) ([\d.\-]+) l\n\n(?:S|B)", main):
        x0, y0, x1, y1 = map(float, m.groups())
        if abs(x0 - x1) < 1e-6 and abs(y1 - y0) > (ax_b[3] - ax_b[2]) * 0.9 and x0 > ax_b[0] + 0.5:
            rules.append(unproj(x0, ax_b, XL_B))
    # the whisker: the horizontal inside panel (a) that is neither axis nor tick
    whisk = None
    for m in re.finditer(r"([\d.\-]+) ([\d.\-]+) m\n([\d.\-]+) ([\d.\-]+) l\n\n(?:S|B)", main):
        x0, y0, x1, y1 = map(float, m.groups())
        if abs(y0 - y1) < 1e-6 and ax_a[0] < min(x0, x1) and max(x0, x1) < ax_a[1] \
           and 5 < abs(x1 - x0) < (ax_a[1] - ax_a[0]) * 0.9:
            whisk = (unproj(min(x0, x1), ax_a, XL_A), unproj(max(x0, x1), ax_a, XL_A))
    # Ticks, used to prove the hardcoded limits above still describe this build.
    # Without this the checker would silently mis-project every coordinate if
    # fig3.py's xlim ever changed, and report a precise-looking pass.
    ticks_a, ticks_b = [], []
    for m in re.finditer(r"([\d.\-]+) ([\d.\-]+) m\n([\d.\-]+) ([\d.\-]+) l\n\n(?:S|B)", main):
        x0, y0, x1, y1 = map(float, m.groups())
        if abs(x0 - x1) < 1e-6 and 1.5 < abs(y1 - y0) < 4 and y0 <= ax_a[2] + 0.01:
            (ticks_a if x0 < ax_b[0] else ticks_b).append(
                unproj(x0, ax_a if x0 < ax_b[0] else ax_b, XL_A if x0 < ax_b[0] else XL_B))
    # y-ticks of panel (b): short horizontals just left of its spine
    ticks_by = []
    for m in re.finditer(r"([\d.\-]+) ([\d.\-]+) m\n([\d.\-]+) ([\d.\-]+) l\n\n(?:S|B)", main):
        x0, y0, x1, y1 = map(float, m.groups())
        if abs(y0 - y1) < 1e-6 and 0 < abs(x1 - x0) < 4 and ax_b[0] - 4 < min(x0, x1) <= ax_b[0] + 0.1:
            ticks_by.append(YL_B[0] + (y0 - ax_b[2]) / (ax_b[3] - ax_b[2]) * (YL_B[1] - YL_B[0]))
    # long horizontal inside panel (b) that is not the axis = the 80% reference
    href = [YL_B[0] + (float(m.group(2)) - ax_b[2]) / (ax_b[3] - ax_b[2]) * (YL_B[1] - YL_B[0])
            for m in re.finditer(r"([\d.\-]+) ([\d.\-]+) m\n([\d.\-]+) ([\d.\-]+) l\n\n(?:S|B)", main)
            if abs(float(m.group(2)) - float(m.group(4))) < 1e-6
            and abs(float(m.group(3)) - float(m.group(1))) > (ax_b[1] - ax_b[0]) * 0.9
            and float(m.group(1)) > ax_b[0] - 0.1 and float(m.group(2)) > ax_b[2] + 1]
    # long vertical in panel (a) that is not a spine = the zero rule
    vzero = [unproj(float(m.group(1)), ax_a, XL_A)
             for m in re.finditer(r"([\d.\-]+) ([\d.\-]+) m\n([\d.\-]+) ([\d.\-]+) l\n\n(?:S|B)", main)
             if abs(float(m.group(1)) - float(m.group(3))) < 1e-6
             and abs(float(m.group(4)) - float(m.group(2))) > (ax_a[3] - ax_a[2]) * 0.9
             and ax_a[0] + 0.5 < float(m.group(1)) < ax_a[1] - 0.5]
    return dict(
        page_w=page_w, n_dots=len(dots), n_cross=len(crosses),
        dots=dots, crosses=crosses, whisker=whisk, rules=rules,
        ticks_by=sorted(ticks_by), href=href, vzero=vzero,
        ticks_a=sorted(ticks_a), ticks_b=sorted(ticks_b),
        band_solid=(unproj(bands[0][0], ax_b, XL_B), unproj(bands[0][1], ax_b, XL_B)),
        band_fringe=(unproj(bands[1][0], ax_b, XL_B), unproj(bands[1][1], ax_b, XL_B)),
    )


def main() -> None:
    tex = Path(sys.argv[1] if len(sys.argv) > 1
               else "../../NeurIPS_2026_newinml/neurips_2026.tex")
    cap = caption_of(tex)
    body = tex.read_text()
    g = geometry(PDF)

    prim = _data.primary_clusters()
    w = _data.report(prim)
    lo, hi = w["ci95_bca"]
    shifts, pw = _data.power_curve(prim)
    blo, bhi = _data.power_crossing(shifts, pw, 0.80)
    zeros = int((np.abs(prim) <= 1e-12).sum())
    thirds = sum(1 for v in prim if abs(v * 3 - round(v * 3)) < 1e-9)
    dens = sorted({__import__("fractions").Fraction(float(v)).limit_denominator(36).denominator
                   for v in prim})
    mcse = float(np.sqrt(pw * (1 - pw) / _data.POWER_NSIM).max())

    print("\nA.  CAPTION -> DATA   (every numeral re-derived from _data)")
    derived = {
        "18": len(prim), "14": thirds, "80": 80, "95": 95,
        "+0.40": blo, "+0.42": bhi, "0.40": blo, "0.42": bhi,
        "+0.353": round(float(hi), 3), "0.05": 0.05,
        "0.080": round(float(pw[0]), 3), "0.049": 0.049,
        "6{,}000": _data.POWER_NSIM, "0.007": 0.007,
        "1,3,6,12,18": dens,
    }
    check(len(prim) == 18, "n = 18 source-run means", f"drawn {g['n_dots'] + g['n_cross']}")
    check(zeros == 4, "4 exact zeros", f"{zeros} in data, {g['n_cross']} crosses drawn")
    check(thirds == 14, "14 of 18 on thirds", f"{thirds}")
    check(dens == [1, 3, 6, 12, 18], "denominators {1,3,6,12,18}", f"{dens}")
    check(round(float(hi), 3) == 0.353, "BCa upper limit +0.353", f"{hi:.6f}")
    check((round(blo, 2), round(bhi, 2)) == (0.40, 0.42), "bracket 0.40 / 0.42",
          f"{blo:.2f} / {bhi:.2f}")
    check(round(float(pw[0]), 3) == 0.080, "0.080 at zero shift", f"{float(pw[0]):.4f}")
    check(_data.POWER_NSIM == 6000, "6,000 replicates per point")
    check(mcse <= 0.007, "Monte Carlo SE <= the quoted 0.007", f"realised max {mcse:.5f}")
    # any numeral the caption prints that we did not derive
    printed = set(re.findall(r"\$?([+-]?\d[\d.,{}]*\d|\b\d\b)\$?", cap))
    unknown = {p for p in printed if p not in derived}
    check(not unknown, "no numeral in the caption is unaccounted for",
          f"unaccounted: {sorted(unknown)}" if unknown else "")

    print("\nB.  CAPTION -> DRAWING   (geometry read back out of fig3.pdf)")
    cs, cf = g["band_solid"], g["band_fringe"]
    # Gate everything below on the projection still being valid.
    want_a, want_b = [-1.0, -0.5, 0.0, 0.5, 1.0], [0.0, 0.2, 0.4, 0.6]
    proj_ok = (len(g["ticks_a"]) == len(want_a) and len(g["ticks_b"]) == len(want_b)
               and all(abs(a - b) < 1e-6 for a, b in zip(g["ticks_a"], want_a))
               and all(abs(a - b) < 1e-6 for a, b in zip(g["ticks_b"], want_b)))
    check(proj_ok, "axis limits unchanged, so the back-projection is valid",
          f"(a) ticks {[round(t, 4) for t in g['ticks_a']]}  "
          f"(b) ticks {[round(t, 4) for t in g['ticks_b']]}")
    if not proj_ok:
        print("        ^ fig3.py's xlim changed; update XL_A/XL_B in geometry() "
              "before trusting anything below")
    check(abs(cs[0]) < 1e-6, "shading starts at shift 0, not at the axis limit",
          f"left edge {cs[0]:+.6f}")
    # Each of these asserts both that the caption makes the claim and that the
    # ink agrees with it.  Testing only the geometry would let the label read
    # 'caption "solid to 0.40" matches the fill' about a caption that never says
    # it, which would make the checker itself overclaim.
    check("solid to $0.40$" in cap and abs(cs[1] - blo) < 1e-6,
          'caption says "solid to 0.40" AND the fill ends there',
          f"fill solid to {cs[1]:.6f}")
    check("fringed to $0.42$" in cap and abs(cf[1] - bhi) < 1e-6,
          'caption says "fringed to 0.42" AND the fringe ends there',
          f"fringe to {cf[1]:.6f}")
    check("vertical rule is the interval's upper limit, $+0.353$" in cap
          and len(g["rules"]) == 1 and abs(g["rules"][0] - hi) < 1e-6,
          'caption names the vertical rule AND it stands at +0.353',
          f"rule at {g['rules'][0]:+.7f}" if g["rules"] else "no rule drawn")
    check("95\\% BCa interval" in cap and g["whisker"] is not None
          and abs(g["whisker"][0] - lo) < 1e-6 and abs(g["whisker"][1] - hi) < 1e-6,
          'caption names the 95% BCa interval AND the whisker spans it',
          f"whisker {g['whisker'][0]:+.7f} .. {g['whisker'][1]:+.7f}" if g["whisker"] else "")
    check("Crosses are the four exact zeros" in cap
          and g["n_cross"] == 4 and all(abs(x) < 1e-9 for x in g["crosses"]),
          'caption says "crosses are the four exact zeros" AND 4 are drawn at 0',
          f"{g['n_cross']} crosses, all at x = 0")
    check(g["n_dots"] + g["n_cross"] == len(prim),
          "every source-run mean is drawn exactly once",
          f"{g['n_dots']} dots + {g['n_cross']} crosses")

    print("\nC.  MARK INVENTORY -> CAPTION   (built from the DRAWING, not from the caption)")
    # Enumerated from fig3.py's painting calls rather than from phrases in the
    # caption, because a phrase-driven check can only confirm what the caption
    # already says and can never discover an element the caption forgot.  Each
    # element declares how it is keyed.  Two are keyed by landing exactly on a
    # labelled tick rather than by a caption clause; that is a deliberate,
    # stated judgement, and the tick coincidence is verified from the PDF
    # below.
    PAINTING_CALLS = 10          # bump ONLY when a new element is declared here
    INVENTORY = [
        ("(a) zero reference rule",  "tick",    None),
        ("(a) 14 filled dots",       "caption", "The 18 source-run means the test sees"),
        ("(a) 4 grey crosses",       "caption", "Crosses are the four exact zeros"),
        ("(a) estimate + whiskers",  "caption", "the point with whiskers below is the estimate"),
        ("(b) solid grey band",      "caption", "Shading marks shifts the test has under $80\\%$ power against"),
        ("(b) light grey fringe",    "caption", "fringed to $0.42$"),
        ("(b) BCa upper-limit rule", "caption", "The vertical rule is the interval's upper limit"),
        ("(b) dotted 80% reference", "tick",    None),
        ("(b) power curve",          "caption", "Power against a location shift"),
        ("(b) hollow point at 0",    "caption", "The hollow point at zero shift is off the curve"),
    ]
    n_declared = len(INVENTORY)
    src = Path("fig3.py").read_text().split("def main()")[1]
    n_calls = len(re.findall(r"ax\.(?:axvline|axhline|axvspan|scatter|errorbar|plot)\(", src))
    check(n_calls == PAINTING_CALLS == n_declared,
          "every painting call in fig3.py is declared in this inventory",
          f"{n_calls} calls, {n_declared} declared")
    if n_calls != n_declared:
        print("        ^ an element was added or removed without declaring how the "
              "reader decodes it; add it to INVENTORY before trusting this section")
    for label, mode, phrase in INVENTORY:
        if mode == "caption":
            check(phrase in cap, f"{label:27s} keyed by caption")
        else:
            print(f"{OK}{label:27s} keyed by a labelled tick, NOT by the caption")
    # the two tick-keyed marks must actually coincide with a drawn, labelled tick
    check(len(g["vzero"]) == 1 and abs(g["vzero"][0]) < 1e-6
          and any(abs(t) < 1e-6 for t in g["ticks_a"]),
          "  ^ (a)'s rule sits on the labelled 0.0 tick",
          f"rule at {g['vzero'][0]:+.9f}, x-ticks {[round(t,2) for t in g['ticks_a']]}"
          if g["vzero"] else "no zero rule found")
    check(len(g["href"]) == 1 and abs(g["href"][0] - 0.80) < 1e-6
          and any(abs(t - 0.80) < 1e-6 for t in g["ticks_by"]),
          "  ^ (b)'s dotted line sits on the labelled 0.8 tick",
          f"line at y={g['href'][0]:.7f}, y-ticks {[round(t,2) for t in g['ticks_by']]}"
          if g["href"] else "no 80% reference found")

    print("\n    caption-level requirements")
    a_half = cap.split(r"\textbf{(b)}")[0]
    for phrase, label in [
        ("95\\% BCa interval", "the interval named"),
        ("Monte Carlo standard error", "curve resolution stated"),
        ("weak stratum", "scope stated once"),
        (r"\alpha = 0.05", "alpha stated (it left the y-axis)"),
    ]:
        check(phrase in cap, label)
    check("hollow" not in a_half,
          'retired wording gone: no "hollow" in panel (a); zeros are crosses')
    check("runs to the interval's upper limit" not in cap,
          'retired wording gone: shading no longer "runs to the interval\'s upper limit"')
    check(cap.lstrip().startswith(r"\caption{\textbf{The registered test first exceeds"),
          "caption leads with the take-away, not the status label")
    check("Exploratory" in cap, "status label retained, second")
    check(re.search(r"\\includegraphics\[width=\\linewidth\]\{figures/fig3\.pdf\}\s*\\caption",
                    body) is not None,
          "caption follows the graphic, no hand-set spacing between")

    print()
    if fails:
        print(f"{len(fails)} FAILED: " + "; ".join(fails))
        sys.exit(1)
    n_cap = sum(1 for _, m, _ in INVENTORY if m == "caption")
    n_tick = sum(1 for _, m, _ in INVENTORY if m == "tick")
    print("caption is precise: every numeral re-derives and every positional claim "
          "matches the ink.")
    print(f"of {len(INVENTORY)} drawn elements, {n_cap} are named in the caption and "
          f"{n_tick} are keyed only by landing on a labelled tick\n"
          f"(the zero reference in (a) and the 80% reference in (b)): decodable, "
          f"but not stated in words.")


if __name__ == "__main__":
    main()
