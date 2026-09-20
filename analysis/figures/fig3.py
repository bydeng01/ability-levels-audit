#!/usr/bin/env python3
"""Exploratory resolution analysis of the primary endpoint.

Panel (a) stacks the 18 weak-stratum source-run means at their measured values;
crosses mark the four exact zeros dropped by the signed-rank test. The separate
point and whiskers show the mean and its 95% BCa interval.

Panel (b) shows rejection rates under location shifts of the mean-centred
empirical distribution. This distribution is asymmetric, so the hollow point
at zero shift is not the test's size under its symmetry null. Shading brackets
the 80% power crossing; the vertical rule marks the BCa upper limit. The caption
should state the Monte Carlo uncertainty and explain these reference marks.

Reads released scores through _data. Run from the repository root:
    python3 analysis/figures/fig3.py
"""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

import _data
import _style

FRAC_LINEWIDTH = 1.0     # tex: \includegraphics[width=\linewidth]{figures/fig3.pdf}
ASPECT = 0.3150          # 5.50 x 1.7325in

# Stack spacing scales with marker diameter and the measured axes size.
# For a circular scatter marker, s scales the unit path: diameter = sqrt(s)
# points and area = pi*s/4. _rows solves the interval-to-cloud gap.
DOT_S = 18.0             # scatter s for a retained mean; drawn diameter sqrt(s)
CROSS_S = 22.0           # scatter s for a dropped exact zero
STACK_GAP = 1.49         # stack step, in marker diameters (~half a diameter clear)
TOUCH_GAP = 1.19         # min centre-to-centre x-gap, in diameters, to share a row
PAD_STEPS = 1.05         # stack steps of pad above and below the drawn content
ROW_GAP_BOUNDS = (2.5, 6.5)   # sane range for the solved interval-to-cloud gap

GRID_LEFT, GRID_RIGHT, GRID_WSPACE = 0.050, 0.988, 0.24
GRID_TOP, GRID_BOTTOM = 0.845, 0.315


def _text_width_pt(fig, s: str, fontsize: float) -> float:
    """Rendered text width in points, used to check panel fit."""
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
    # The x limits include all source-run means and the BCa interval.
    ax.set_xlim(*XLIM_A)
    ax.set_xticks([-1.0, -0.5, 0.0, 0.5, 1.0])
    ax.set_xlabel(r"PAG$_{\mathrm{weak}}$ per source run (scale points)",
                  labelpad=2)
    ax.set_title(title_a, fontsize=PT["annot"], loc="left", pad=4)
    _style.tidy(ax)
    ax.spines["left"].set_visible(False)

    # ------------------------------------------------------------------ (b) power
    ax = fig.add_subplot(gs[1])
    # Shade from zero to the last simulated shift below 80% power, with a
    # fringe over the crossing bracket. Negative shifts were not simulated.
    ax.axvspan(0.0, band_lo, color=C["band"], lw=0, zorder=0)
    ax.axvspan(band_lo, band_hi, color=C["band_fringe"], lw=0, zorder=0)
    # Use a neutral rule for the BCa upper limit.
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

    # Print counts and geometry for caption verification.
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
    # Check the realised Monte Carlo uncertainty against the caption bound.
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
