#!/usr/bin/env python3
"""EXPLORATORY (not registered S6/S7).  What the primary endpoint can resolve.
Rebuilt 2026-08-18; text-load, palette and token pass 2026-08-22.

(a) The 18 weak-stratum source-run means the registered test sees, stacked on
    the sparse rational lattice, with the four exact zeros the test discards
    drawn as such, and the estimate with its BCa interval.
(b) Power of that test against a location shift, with the shift-zero point
    marked as the thing it is and the 80% crossing drawn as the bracket it is.

2026-08-22 pass.  Measured first (``pdftotext -bbox`` on the shipped PDF):
86 word boxes, 373 glyphs, 15.66% text ink over the canvas, 8.0 words/in^2.
Per panel, (a) 43 boxes / 198 glyphs / 20.41% ink and (b) 43 / 175 / 17.41% --
so the strip plot, which carries one measured variable, was the denser panel of
the two.  That is the case for the cuts below.

Text load: six in-panel strings removed, all of them duplicates.

Every numeral in them is already set in body prose within a page of the figure,
and most are in this figure's own caption:

  panel (a)  "18 source-run means; 4 exact zeros (hollow) are dropped"
             -> caption (a) and body L159 ("on 18 source-run means of which
                14 are nonzero").  Both counts are now *countable* off the
                stack, which is the encoding this line was standing in for.
  panel (a)  "+0.0849  BCa [-0.167, +0.353] / half-width 0.260  exact
             signed-rank p = 0.684"
             -> body L159 sets all four verbatim, and Figure 2's caption sets
                half-width 0.260.  The estimate and interval are *drawn*; the
                digits were the table's job.
  panel (b)  "0.080 at zero shift is not the size (0.049)"
             -> caption (b) verbatim, and body L438.
  panel (b)  "BCa upper limit +0.353 / power 0.71"
             -> body L161 and L438 ("power is 0.709 at the interval's upper
                limit of +0.353").  It also *violated the value-label rule*:
                "power 0.71" was anchored at y = 1.04, a quarter of the panel
                above the 0.709 it names.  Deleted instead of moved; the reader
                now reads it off the curve where the rule crosses it.
  panel (b)  "80% between 0.40 and 0.42"
             -> caption (b) verbatim.
  panel (b)  "80% power"
             -> replaced by a 0.8 entry in the y-ticks, which labels the
                reference line at its own value in three glyphs instead of
                eight, and puts the label on the axis where a value belongs.

What was NOT cut, because the drawing is its only source: the counts and the
stack multiplicities in (a), the shape of the power curve, and the position of
every reference mark.  Facts that live only in the caption after this pass are
listed at the end of this note and must not be edited out of it.

Retighten: (a) ran to x = 1.62 with a tick at 1.5 to clear the statistics
line; the largest datum is +7/6.  Now xlim (-1.16, 1.33), ticks to 1.0.  Its
y-extent is set from the drawn content (see ``_rows``) so the band the two text
blocks vacated cannot read as blank paper.  (b) drops from ylim 1.06 to 1.04.
Canvas height 1.95 -> 1.7325in; width is untouched at 5.5in = 1.0 linewidth.

Palette: the shipped build painted the strip plot and the power curve in P_nov
blue and ruled the BCa limit in P_adv vermillion.  Those two hues are the arm
identities (``_style.COLOR``), and neither panel of this figure shows an arm:
(a) is a within-run contrast, (b) is a rejection rate.  Both were generic
accents on hues that already carry a meaning, which is the failure the
2026-08-18 redesign removed from fig2 and which had simply relocated here.
This figure now carries no categorical variable and so no categorical hue: ink,
muted, faint, rule, band.  It is greyscale-identical by construction, and the
one distinction it does draw (retained vs dropped) is carried by marker shape
and by position on the zero rule instead of by colour.

Tokens: two collisions, one inside the figure and one across figures.

  * Hollow meant two things: "exact zero, dropped by the test" in (a) and
    "off the curve, not the test's size" in (b).  The dropped zeros are now
    crosses, so hollow has exactly one meaning in this figure.
  * Grey fill meant "under 80% power" in Figure 2 and "up to the BCa upper
    limit" here, and within this panel the solid and fringed greys meant two
    unrelated things.  The band here is now the same object Figure 2 shades
    (shifts the test has under 80% power against, solid to 0.40 and fringed to
    0.42), so one fill carries one meaning across both figures and the two
    captions can use the same words.  The BCa upper limit keeps its own token:
    a thin solid rule, keyed in the caption.  The 80% reference is dotted and
    lands on a labelled tick.

Terminology, censused against ``neurips_2026.tex``.  "true shift" occurs 0
times in the body and is replaced by "location shift" (3).  Panel (b)'s title
was "effects this design cannot rule out": "rule out" occurs 0 times, and the
body's hedge at L161 is the opposite shape, since it says no bound of the form
|PAG| < c may be asserted at all.  The panel is now titled as a power curve.
"registered test" (4), "source run" (4) / "source-run" (11), "location shift"
(3), "scale points" and "pseudomedian" (6) all carry.  alpha = 0.05 moves to
the caption's scope clause, so the y-axis reads "power".

PRECISION AUDIT (2026-08-22, after the pass above).  Every drawn mark was read
back out of the PDF content stream (the CTM stack interpreted, marker
placements back-projected through the axes transform) instead of being trusted
from this script.  All 18 marks in (a) sit on their exact lattice value to 1.4e-12
scale points (9e-11 pt on paper); the whisker ends land on the BCa limits to
5e-9; the zero rule, the BCa rule, the 80% reference and all ticks are exact to
1e-9.  Three defects were found and are fixed here:

  1. ``diam_pt`` used ``2*sqrt(s/pi)``, reading matplotlib's scatter ``s`` as an
     area, which it is not; see the note on ``DOT_S`` below.  Every printed
     invariant was 12.8% too large.  Benign in the picture, since it only bought
     extra clearance and the tightest pair had 1.08pt of it, but a trap for the
     next edit.
  2. The under-80%-power band ran from the axis limit, -0.008, so 1.8pt of it
     lay over negative shifts the simulation never evaluated.  It now starts
     at 0.
  3. Power at 0.38 (0.7187) exceeds power at 0.40 (0.7112).  Power is monotone
     in a location shift, so that 0.0075 drop (0.48pt on paper, 0.91 Monte
     Carlo standard errors) is noise the figure would otherwise draw as fact.
     It is not redrawn, because an MC ribbon would be a second grey fill and
     would collide with the band token.  The caption instead quotes the
     resolution, "Monte Carlo standard error at most 0.007", which is what a
     reader needs in order not to over-read that segment.  ``main()`` prints
     the realised max.

Caption clauses that are now the sole source of their fact, and must survive
any later edit:
  * "Crosses are the four exact zeros, which the test drops"    -> keys "x"
  * "the point with whiskers below is the estimate and its 95% BCa interval"
      -> keys the errorbar, which the shipped caption never keyed at all
  * "Shading marks shifts the test has under 80% power against: solid to 0.40,
     fringed to 0.42"                                           -> keys the fill
  * "The vertical rule is the interval's upper limit, +0.353"   -> keys the rule
  * "The hollow point at zero shift is off the curve ... 0.080 ... 0.049"
  * "denominators {1,3,6,12,18}; only 14 of the 18 lie on thirds"

Three repairs against the 2026-08-18 build are still in force.

1.  Panel (a)'s statistics line no longer runs into panel (b).  It was one
6.2pt string placed at x = -1.22 in data coordinates, and it overflowed: the
final digit of "half-width 0.260" was overprinted by panel (b)'s rotated y-label
and the tail, "exact signed-rank p = 0.6837", was drawn inside panel (b) across
the power curve, leaving the primary endpoint's p-value unreadable in the
paper's own figure.  That string is now gone entirely (see the text-load note
above).  ``_style.scan_text`` fails the build if anything like it returns.

2.  Panel (a) no longer rules a grid its own data sit off.  The 2026-08-18
build drew vertical lines at thirds.  Per-stimulus PAG is a multiple of 1/3, but
averaging within source run divides by the run's stimulus count, so these means
have denominators {1, 3, 6, 12, 18} and include 7/6, -1/6, -1/12 and -1/18: only
14 of the 18 land on thirds.  The grid is gone.  The stack introduced here
makes the point positively instead of by omission: coincident values pile up and
isolated denominators stand alone.

3.  Panel (b) marks the shift-zero point instead of letting it sit on a curve
labelled "power".  Centring is on the MEAN, so at shift zero the resampled
distribution is asymmetric and the signed-rank null (symmetry about zero) is
false there.  The 0.080 rejection rate is power against a nonzero pseudomedian
rather than the test's size, which ``analysis/simulations.py`` puts at 0.049
under a DGP that does satisfy the null.  The 80% crossing is likewise only
bracketed: power is 0.711 at a 0.40 shift and 0.930 at 0.42, because the
endpoint lives on a lattice and the curve is a step function.
"""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

import _data
import _style

FRAC_LINEWIDTH = 1.0     # tex: \includegraphics[width=\linewidth]{figures/fig3.pdf}
ASPECT = 0.3150          # 5.50 x 1.7325in

# Panel (a) geometry.  The stack step and the collision radius are multiples of
# the marker DIAMETER, and everything below is derived from ``DOT_S``, so there
# is no hand-set data-coordinate offset anywhere in this panel.  ``_rows``
# divides the step into the measured axes height and solves for the
# interval-to-cloud gap, so the drawn content spans the panel exactly and the
# geometry survives a change of ASPECT.
#
# ``DOT_S`` is matplotlib's scatter ``s``.  Its docs call it "size in points**2",
# which invites ``diameter = 2*sqrt(s/pi)``; that is wrong by a factor of
# 2/sqrt(pi) = 1.1284.  matplotlib scales the unit marker path (radius 0.5) by
# ``sqrt(s)``, so the drawn diameter is exactly ``sqrt(s)`` and the drawn area is
# ``pi*s/4``.  Verified against the PDF content stream: s = 18 emits a circle of
# radius 2.121320 = sqrt(18)/2.  The area reading was used here until 2026-08-22
# and made every printed invariant 12.8% too large.  Harmless in the picture,
# since it only bought extra clearance, but it would have produced silent
# overlap for anyone who trusted STACK_GAP = 1.0 to mean "just touching".
DOT_S = 18.0             # scatter s for a retained mean; drawn diameter sqrt(s)
CROSS_S = 22.0           # scatter s for a dropped exact zero
STACK_GAP = 1.49         # stack step, in marker diameters (~half a diameter clear)
TOUCH_GAP = 1.19         # min centre-to-centre x-gap, in diameters, to share a row
PAD_STEPS = 1.05         # stack steps of pad above and below the drawn content
ROW_GAP_BOUNDS = (2.5, 6.5)   # sane range for the solved interval-to-cloud gap

GRID_LEFT, GRID_RIGHT, GRID_WSPACE = 0.050, 0.988, 0.24
GRID_TOP, GRID_BOTTOM = 0.845, 0.315


def _text_width_pt(fig, s: str, fontsize: float) -> float:
    """Rendered width of ``s`` in points.

    The build contract requires titles and labels to be sized from measured
    string widths, not character counts.  Both are printed at build time and
    the build stops if either exceeds its panel: the two titles here run 86.1pt
    and 91.1pt in a 165.8pt panel, and the ratio of width to character count
    differs between them (2.69 vs 2.76 pt/char), so a character budget set from
    one would not be the budget for the other.
    """
    t = fig.text(0.0, 0.0, s, fontsize=fontsize)
    fig.canvas.draw()
    w = t.get_window_extent(fig.canvas.get_renderer()).width * 72.0 / fig.dpi
    t.remove()
    return w


def _rows(prim: np.ndarray, axes_h_pt: float, axes_w_pt: float, x_span: float):
    """Stack rows for panel (a), sized so the content fills the panel exactly.

    Returns ``(y_of_each_point, y_interval, step, tallest)`` in data units on a
    (0, 1) axis.

    Each point keeps its true x and is dropped into the lowest row where it
    would not touch a dot already in that row.  Equal values therefore stack --
    the four zeros, the three at -1/3, the two at +1/3 and at +1 -- and so do
    the near-coincident ones: -1/12 and -1/18 are 0.0278 scale points apart,
    which at this panel width is 1.9pt, well under a marker diameter, and the
    shipped build drew them overlapping.  Nothing is displaced horizontally, so
    every mark still sits at its own value; the count is read up the column.

    Jitter is not used at all.  The shipped build drew ``normal(0, 0.055)``
    here, which is at least the correct axis to disturb -- never the measured
    one -- but it destroys the multiplicities that are this panel's whole point,
    and it puts an RNG seed in a figure that has no need of one.

    The step is fixed in POINTS first, as a multiple of the marker diameter, and
    the interval-to-cloud gap is then SOLVED so that pad + cloud + gap fills the
    measured axes height.  After the text cuts there is no slack band left to
    read as blank paper, and the panel re-solves itself if ASPECT ever changes.
    """
    diam_pt = np.sqrt(DOT_S)          # matplotlib scales the unit marker by sqrt(s)
    touch_x = TOUCH_GAP * diam_pt / axes_w_pt * x_span     # in data units

    # The dropped zeros are packed first, so they occupy rows 0..3 at x = 0 and
    # read as one contiguous column of four.  Packing purely left-to-right let a
    # neighbouring value (-1/18, 0.056 away) take a row in the middle of them,
    # and a column with a hole in it cannot be counted off.
    zero_first = np.lexsort((prim, ~(np.abs(prim) <= 1e-12)))
    rows_x: list[list[float]] = []
    offsets = np.zeros(len(prim), dtype=float)
    for i in zero_first:
        v = float(prim[i])
        # Compared against every x already in the row rather than just the
        # last one: the zeros are placed out of x order, so "last" need not be
        # "nearest".
        for r, xs in enumerate(rows_x):
            if all(abs(v - u) >= touch_x for u in xs):
                xs.append(v)
                offsets[i] = r
                break
        else:
            rows_x.append([v])
            offsets[i] = len(rows_x) - 1
    tallest = float(offsets.max())

    step_pt = STACK_GAP * diam_pt
    total_steps = axes_h_pt / step_pt
    row_gap = total_steps - tallest - 2.0 * PAD_STEPS
    if not ROW_GAP_BOUNDS[0] <= row_gap <= ROW_GAP_BOUNDS[1]:
        raise SystemExit(
            f"panel (a) does not compose: solved interval-to-cloud gap "
            f"{row_gap:.2f} steps is outside {ROW_GAP_BOUNDS}. "
            f"axes {axes_h_pt:.1f}pt, {diam_pt:.2f}pt markers, "
            f"step {step_pt:.2f}pt, cloud {tallest:.0f} rows. Adjust ASPECT.")

    step = 1.0 / total_steps
    y_int = PAD_STEPS * step
    y_base = y_int + row_gap * step
    print(f"  panel (a): {diam_pt:.2f}pt markers, step {step_pt:.2f}pt, "
          f"cloud {int(tallest) + 1} rows, solved gap {row_gap:.2f} steps, "
          f"touch radius {touch_x:.4f} scale points")
    return offsets * step + y_base, y_int, step, tallest


def main() -> None:
    _style.apply()
    C, PT = _style.COLOR, _style.PT

    prim = _data.primary_clusters()
    w = _data.report(prim)
    lo, hi = w["ci95_bca"]
    zeros = np.abs(prim) <= 1e-12

    shifts, pw = _data.power_curve(prim)
    band_lo, band_hi = _data.power_crossing(shifts, pw, 0.80)

    fig = plt.figure(figsize=_style.figsize_for(FRAC_LINEWIDTH, aspect=ASPECT))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 1.0], wspace=GRID_WSPACE,
                          left=GRID_LEFT, right=GRID_RIGHT,
                          top=GRID_TOP, bottom=GRID_BOTTOM)

    canvas_w_pt = _style.TEXTWIDTH_IN * FRAC_LINEWIDTH * 72.0
    panel_w_pt = (GRID_RIGHT - GRID_LEFT) / (2.0 + GRID_WSPACE) * canvas_w_pt
    axes_h_pt = (GRID_TOP - GRID_BOTTOM) * ASPECT * canvas_w_pt

    title_a = "a   what the registered test sees"
    title_b = "b   power against a location shift"
    for s in (title_a, title_b):
        got = _text_width_pt(fig, s, PT["annot"])
        print(f"  title {s!r}: {got:.1f}pt measured in a {panel_w_pt:.1f}pt panel")
        if got > panel_w_pt:
            raise SystemExit(f"panel title overruns its panel: {s!r}")

    # ------------------------------------------------------------ (a) what it sees
    ax = fig.add_subplot(gs[0])
    XLIM_A = (-1.16, 1.33)
    ys, y_int, step, tallest = _rows(prim, axes_h_pt, panel_w_pt,
                                     XLIM_A[1] - XLIM_A[0])

    ax.axvline(0, color=C["rule"], lw=0.7, zorder=1)
    ax.scatter(prim[~zeros], ys[~zeros], s=DOT_S, color=C["ink"],
               alpha=0.85, linewidths=0, zorder=3)
    # The four exact zeros are dropped by the signed-rank test.  They are
    # crosses rather than hollow dots, because hollow is spent in panel (b) on a
    # different meaning and one marker token must not carry two.  They sit on
    # the zero rule, so shape and position both identify them without colour.
    ax.scatter(prim[zeros], ys[zeros], s=CROSS_S, marker="x",
               color=C["faint"], linewidths=0.9, zorder=3)
    ax.errorbar([w["mean"]], [y_int], xerr=[[w["mean"] - lo], [hi - w["mean"]]],
                fmt="o", ms=4.0, color=C["ink"], capsize=2.0, capthick=0.7,
                elinewidth=0.9, zorder=4)

    ax.set_ylim(0.0, 1.0)
    ax.set_yticks([])
    # Retightened after the cut: the data run -1 to +7/6, and nothing needs the
    # width the deleted statistics line did.  The interval's own reach, to
    # +0.353, is well inside.
    ax.set_xlim(*XLIM_A)
    ax.set_xticks([-1.0, -0.5, 0.0, 0.5, 1.0])
    ax.set_xlabel(r"PAG$_{\mathrm{weak}}$ per source run (scale points)",
                  labelpad=2)
    ax.set_title(title_a, fontsize=PT["annot"], loc="left", pad=4)
    _style.tidy(ax)
    ax.spines["left"].set_visible(False)

    # ------------------------------------------------------------------ (b) power
    ax = fig.add_subplot(gs[1])
    # The same object Figure 2 shades, drawn the same way: shifts the test has
    # under 80% power against, solid to the last simulated shift below 80% and
    # fringed over the bracket containing the crossing.  The fill means the same
    # thing in both figures.
    # Starts at 0, not at the axis limit.  Running the fill out to the spine
    # (xlim -0.008) closed a 1.8pt sliver but shaded 0.008 scale points of
    # negative shift, which the simulation never evaluated, so the band would
    # have claimed coverage it does not have.  The sliver is where the hollow
    # zero-shift marker sits, so the band now begins exactly at that marker.
    ax.axvspan(0.0, band_lo, color=C["band"], lw=0, zorder=0)
    ax.axvspan(band_lo, band_hi, color=C["band_fringe"], lw=0, zorder=0)
    # Its own token rather than P_adv vermillion, since that hue means
    # "advanced-profile arm" everywhere else in the paper and this panel has no
    # arm in it.
    ax.axvline(hi, color=C["muted"], lw=0.8, zorder=2)
    # Dotted, and landing on a labelled tick, so it needs no string of its own.
    ax.axhline(0.80, color=C["rule"], lw=0.6, ls=(0, (1.0, 2.0)), zorder=1)

    ax.plot(shifts[1:], pw[1:], "-o", color=C["ink"], lw=1.1, ms=2.8, zorder=3)
    # Shift zero, off the curve and hollow: at the mean-centred null the
    # signed-rank symmetry assumption is false, so this is power against a
    # nonzero pseudomedian rather than the test's size.  Hollow appears exactly
    # once in this figure, here.
    ax.plot([0], [pw[0]], "o", ms=3.6, mfc="white", mec=C["ink"], mew=0.9,
            zorder=4)

    ax.set_xlim(-0.008, 0.725)
    ax.set_ylim(0.0, 1.04)
    ax.set_xticks([0.0, 0.2, 0.4, 0.6])
    ax.set_yticks([0.0, 0.5, 0.8, 1.0])
    ax.set_xlabel(r"location shift in PAG$_{\mathrm{weak}}$ (scale points)",
                  labelpad=2)
    ax.set_ylabel("power", labelpad=2)
    ax.set_title(title_b, fontsize=PT["annot"], loc="left", pad=4)
    _style.tidy(ax)

    written = _style.save(fig, _data.OUT, "fig3")
    plt.close(fig)

    problems = _style.verify_pdf(_data.OUT / "fig3.pdf",
                                 _style.TEXTWIDTH_IN * FRAC_LINEWIDTH)
    for msg in problems:
        print(f"  !! {msg}")
    print("wrote " + ", ".join(str(p) for p in written)
          + ("" if problems else "   [submission checks clean]"))

    # Everything the panels now assert without a string of their own.
    cols = {}
    for v in np.round(prim.astype(float), 12):
        cols[v] = cols.get(v, 0) + 1
    print(f"(a) n={len(prim)}  {int(zeros.sum())} exact zeros  "
          f"{len(cols)} lattice columns, tallest {max(cols.values())}  "
          f"on thirds {sum(1 for v in prim if abs(v * 3 - round(v * 3)) < 1e-9)}"
          f"  x[{prim.min():+.4f}, {prim.max():+.4f}]  "
          f"est {w['mean']:+.4f} BCa [{lo:+.4f}, {hi:+.4f}] p={w['wilcoxon_p']:.4f}")
    print("(b) power:", " ".join(f"{s:.3g}:{v:.3f}" for s, v in zip(shifts, pw)))
    print(f"(b) band solid to {band_lo:.2f}, fringe to {band_hi:.2f}; "
          f"rule at BCa upper limit {hi:+.4f}, power there "
          f"{float(pw[np.argmin(np.abs(shifts - hi))]):.3f}")
    # The curve's own resolution.  The caption quotes a bound on this; if the
    # realised value ever exceeds it, the caption is the thing that needs
    # fixing.
    se = np.sqrt(pw * (1.0 - pw) / _data.POWER_NSIM)
    drops = [(shifts[i], pw[i], shifts[i + 1], pw[i + 1])
             for i in range(len(shifts) - 1) if pw[i + 1] < pw[i]]
    print(f"(b) max Monte Carlo SE {se.max():.5f} at shift {shifts[se.argmax()]:.4f} "
          f"(caption bound 0.007){'  ** CAPTION BOUND EXCEEDED **' if se.max() > 0.007 else ''}")
    for a, pa, b, pb in drops:
        z = (pa - pb) / float(np.hypot(se[list(shifts).index(a)],
                                       se[list(shifts).index(b)]))
        print(f"(b) non-monotone {a:.4f}->{b:.4f}: {pa:.4f}->{pb:.4f}, "
              f"{z:.2f} MC SE -- noise, power is monotone in a location shift")


if __name__ == "__main__":
    main()
