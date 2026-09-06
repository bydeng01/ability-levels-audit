#!/usr/bin/env python3
"""Registered figure (PREREGISTRATION.md S7), rebuilt 2026-08-18, revised 2026-08-22.

(a) The registered read, unchanged in form: preference for high scaffolding,
    Delta = S(R_H) - S(R_L), against blind-labeled demonstrated competence, one
    line per arm.  Parallel, closely-spaced lines indicate a behaviour-driven
    judge; wide separation would indicate profile anchoring.
(b) The registered estimand, which panel (a) does not show: PAG against zero,
    with its BCa interval and the range the test cannot resolve.

Panel (b) is there because PAG is a difference between two of the lines in (a),
and the eye cannot read a difference off two overlapping error bars.  What it
reads instead is "the intervals overlap, so nothing is precise", which is the
wrong test.  The estimand's own interval is narrower than any arm's (half-width
0.260 against 0.314-0.428), because clustering the difference within source run
removes the between-run level variation that dominates the arm means.  The
shipped build printed that interval in the title and drew only per-arm bars, so
its strongest encoding (the weak->strong slope) carried the one contrast S5.1
explicitly declines to test, while the registered endpoint was a 0.085 gap
invisible inside 0.66-0.86-wide bars.  Panel (b) draws the endpoint.

Two further corrections against the shipped build:

* The detection band is centred on zero.  It is a statement about |PAG|, so it
  belongs on the PAG axis; anchoring it to the novice line in (a) put a claim
  about a difference onto a level axis.
* The band edge brackets the 80% crossing instead of locating it.  Power is
  0.711 at a 0.40 shift and 0.930 at 0.42; the endpoint lives on a sparse
  rational lattice and the curve is a step function.  The shipped caption called
  +-0.42 "the range where power is below 80%", which is false at its own edge.
  The band is now solid to 0.40 and fringed to 0.42, and both numbers are
  re-derived from fig3's simulation through ``_data`` instead of being
  hand-copied into a docstring constant that had already drifted to
  0.702/0.922.

2026-08-22 revision, against FIGURE_SPEC.md.  Encoding-only: every drawn value
is unchanged and ``_data.selftest`` is untouched by it.

* Text-load reduction.  Three runs cut, each a second copy of something the
  caption states verbatim within an inch of the mark:
    - panel (b)'s "shaded: under 80% power (solid 0.40, fringe 0.42)" -- the
      caption already reads "solid to 0.40, fringed to 0.42", and said it more
      precisely, since the shading reaches 0.42, where power is 0.930;
    - panel (b)'s "+0.085 [-0.167, +0.353]" -- now led with in the caption, and
      three decimals were precision the drawing could not support anyway;
    - panel (a)'s "18 runs, 30 stimuli" / "10 runs, 25 stimuli" -- the caption
      gives both, and in the body's word ("clusters"), which the figure did not
      use.
  Those two annotations were also the only users of COLOR["muted"], which is
  byte-identical to COLOR["D"], so the figure was setting prose in the hue that
  means "no-profile arm" three inches to the left.
* Limits retightened after the cut, and the axes grown into the strip the
  cut x-axis annotation vacated (bottom 0.225 -> 0.155, top 0.865 -> 0.900,
  panel (b) y (-0.80, 0.94) -> (-0.52, 0.64) and x (-0.62, 1.62) -> (-0.52,
  1.52)).  The canvas is unchanged at 5.5 x 2.552in, so nothing moves in the
  .tex.
* The power band is drawn under the weak column only.  ``power_curve()``
  bootstraps ``primary_clusters()``, i.e. the 18 weak clusters; the shipped band
  spanned the full panel and so ran under the strong point, about which it says
  nothing.  Re-simulating on the 10 strong clusters puts that bracket near
  0.50-0.55, which is not drawn here because it is not a registered quantity.
* Arm labels sit within a measured line-height of their own mean, with leaders.
  The shipped build offset by (rank-1)x8pt on top of the true spacing, drawing a
  24.2pt spread for arms 9.2pt apart, a 2.6x exaggeration of the one separation
  panel (a) exists to show is small.  ``_repel`` now pushes only as far as the
  measured string height requires and recentres, and a leader line carries each
  label back to its own marker.
* Panel (a)'s title used a word the body does not have.  "registered read"
  occurs 0 times in neurips_2026.tex and "read" as a noun occurs 0 times.  The
  body's own name for this quantity is "baseline scaffolding preference"
  (materials table), which is also the better hedge, since the panel's most
  salient encoding is the weak->strong slope and that is not the registered
  test.  The y-label then carried the same words as the title, so it is now the
  body's own formula instead: Table 1's $\\Delta = S(R_H) - S(R_L)$.
* "blind-labelled" becomes "blind-labeled".  The body spells it with one l, 4/4.

Reads analysis/out/summary.json and the released per-unit scores.  No paid call;
no frozen input touched.
"""
from __future__ import annotations

import matplotlib.pyplot as plt

import _data
import _style

# Included as \includegraphics[width=\linewidth]{figures/fig1.pdf}.
# Changing one of these two without the other reintroduces the scale bug.
FRAC_LINEWIDTH = 1.0
ASPECT = 0.464          # 5.50 x 2.55in: 0.61in shorter than the shipped build

ARMS = ("D", "P_nov", "P_adv")
LABEL = {"P_nov": "stated novice", "P_adv": "stated advanced",
         "D": "no profile ($D$)"}
X = {"weak": 0.0, "strong": 1.0}
NUDGE = {"P_nov": -0.045, "P_adv": +0.045, "D": 0.0}

XLO_A = -0.28
YLIM_A = (2.05, 3.62)   # caption discloses the truncation; data floor is 2.125
YLIM_B = (-0.52, 0.64)
XLIM_B = (-0.52, 1.52)
BAND_HALF_W = 0.32      # the band is a property of the weak column alone

LABEL_GAP_PT = 7.0      # marker to the start of its label
EDGE_PAD_PT = 1.0       # slack between the longest label and the axes edge


def cell(arm, stratum):
    return _data.SUMMARY["four_cell_table"][f"delta({arm},{stratum})"]


def _size_pt(fig, renderer, s, fontsize):
    """Rendered (width, height) of a string, in points.

    Measured rather than counted: "no profile ($D$)" is three characters longer than
    "stated novice" and narrower on the page, because the parens and the italic
    D are narrow and mathtext is not set in the text font.  Sizing panel (a)'s
    right margin off character counts is what let the shipped fig2 clip a title
    mid-word at the canvas edge.
    """
    t = fig.text(0.0, 0.0, s, fontsize=fontsize)
    bb = t.get_window_extent(renderer=renderer)
    t.remove()
    return bb.width * 72.0 / fig.dpi, bb.height * 72.0 / fig.dpi


def _repel(values_pt, min_gap):
    """Smallest order-preserving push that opens ``min_gap`` between neighbours.

    Recentred on the input centroid, so the label block stays where the data is
    and no label travels further than the type demands.  The leader lines keep
    the residual displacement readable.
    """
    order = sorted(range(len(values_pt)), key=lambda i: values_pt[i])
    out = [0.0] * len(values_pt)
    prev = None
    for i in order:
        v = values_pt[i] if prev is None else max(values_pt[i], prev + min_gap)
        out[i] = v
        prev = v
    shift = (sum(values_pt) - sum(out)) / len(out)
    return [v + shift for v in out]


def main() -> None:
    _style.apply()
    S = _data.SUMMARY
    pag = {"weak": S["primary_PAG_weak"], "strong": S["secondary_PAG_strong"]}

    # PAG is the vertical gap between the two profile arms in (a).  Assert the
    # identity instead of trusting that the two panels agree.
    for stratum in ("weak", "strong"):
        gap = cell("P_nov", stratum)["mean"] - cell("P_adv", stratum)["mean"]
        assert abs(gap - pag[stratum]["mean"]) < 1e-9, f"PAG != nov - adv, {stratum}"

    shifts, pw = _data.power_curve()
    band_lo, band_hi = _data.power_crossing(shifts, pw, 0.80)

    fig = plt.figure(figsize=_style.figsize_for(FRAC_LINEWIDTH, aspect=ASPECT))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 0.50], wspace=0.36,
                          left=0.077, right=0.988, top=0.900, bottom=0.155)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    # ---------------------------------------------------------------- (a) arms
    ax = fig.add_subplot(gs[0])
    ends = []
    for arm in ARMS:
        xs, ys, lo, hi = [], [], [], []
        for stratum in ("weak", "strong"):
            c = cell(arm, stratum)
            xs.append(X[stratum] + NUDGE[arm])
            ys.append(c["mean"])
            lo.append(c["mean"] - c["ci95_bca"][0])
            hi.append(c["ci95_bca"][1] - c["mean"])
        style = dict(color=_style.COLOR[arm], lw=1.1, marker="o", ms=3.0, zorder=4)
        if arm == "D":
            style.update(ls=(0, (3.2, 1.8)), lw=0.85, ms=2.4, zorder=3)
        ax.errorbar(xs, ys, yerr=[lo, hi], capsize=1.8, capthick=0.7,
                    elinewidth=0.7, **style)
        ends.append((xs[-1], ys[-1], arm))

    ax.set_ylim(*YLIM_A)

    # Right margin solved from the measured width of the widest label instead
    # of hand-tuned.  The label block has to clear the axes edge, and the
    # points-to-data conversion depends on the limit being solved for.
    sizes = {arm: _size_pt(fig, renderer, LABEL[arm], _style.PT["small"])
             for arm in ARMS}
    w_pt = max(w for w, _ in sizes.values())
    h_pt = max(h for _, h in sizes.values())
    pos = ax.get_position()
    ax_w_pt = pos.width * fig.get_figwidth() * 72.0
    ax_h_pt = pos.height * fig.get_figheight() * 72.0

    label_x = X["strong"] + max(NUDGE.values())
    x_hi = XLO_A + (label_x - XLO_A) * ax_w_pt / (
        ax_w_pt - LABEL_GAP_PT - w_pt - EDGE_PAD_PT)
    ax.set_xlim(XLO_A, x_hi)

    # The three arms are 0.106 of a scale point apart at the strong end (9.2pt
    # against a measured line height of 7.2pt), so the labels do not fit at
    # their own y.  Push by the minimum the type demands, then let a leader line
    # carry each label back to its marker, so the reader can see how far each
    # label was moved.  The shipped build's exaggeration was undisclosed.
    per_unit = ax_h_pt / (YLIM_A[1] - YLIM_A[0])
    placed = _repel([y * per_unit for _, y, _ in ends], h_pt + 0.9)
    text_x = label_x + LABEL_GAP_PT * (x_hi - XLO_A) / ax_w_pt
    # The leader runs from the arm's own marker, so the true mean is where the
    # line starts and the displacement is on show.  It is drawn at 0.45pt and
    # 0.6 alpha, lighter than the 0.7pt error bars and the 1.1pt series, so it
    # reads as annotation and not as a fourth line.  Alpha does that work
    # instead of a fourth grey, since grey already means the no-profile arm.
    for (mx, my, arm), y_pt in zip(ends, placed):
        ax.annotate(LABEL[arm], xy=(mx, my), xytext=(text_x, y_pt / per_unit),
                    xycoords="data", textcoords="data", ha="left", va="center",
                    fontsize=_style.PT["small"], color=_style.COLOR[arm],
                    arrowprops=dict(arrowstyle="-", lw=0.45, shrinkA=2.5,
                                    shrinkB=1.5, alpha=0.6,
                                    color=_style.COLOR[arm]))

    ax.set_xticks([0, 1], ["weak", "strong"])
    ax.set_yticks([2.2, 2.6, 3.0, 3.4])
    ax.set_yticks([2.1, 2.3, 2.4, 2.5, 2.7, 2.8, 2.9, 3.1, 3.2, 3.3, 3.5, 3.6],
                  minor=True)
    ax.set_xlabel("demonstrated competence (blind-labeled)", labelpad=4)
    ax.set_ylabel(r"$\Delta = S(R_H) - S(R_L)$", labelpad=3)
    ax.set_title("a   baseline scaffolding preference",
                 fontsize=_style.PT["title"], loc="left", pad=5)
    _style.tidy(ax)

    # ------------------------------------------------------------- (b) estimand
    ax = fig.add_subplot(gs[1])
    # The band is the power of the registered test on the 18 WEAK clusters
    # (``power_curve`` bootstraps ``primary_clusters``).  It is drawn under the
    # weak column and nowhere else: run under the strong point it would assert a
    # resolution the simulation never computed for that stratum.
    span = (X["weak"] - BAND_HALF_W, X["weak"] + BAND_HALF_W)
    ax.fill_between(span, -band_hi, band_hi,
                    color=_style.COLOR["band_fringe"], lw=0, zorder=0)
    ax.fill_between(span, -band_lo, band_lo,
                    color=_style.COLOR["band"], lw=0, zorder=0)
    # Rule the fringe edge: at this size the two greys read as one band, and the
    # two-tone is there to show that the crossing is only bracketed.
    for edge in (-band_hi, band_hi):
        ax.plot(span, (edge, edge), color=_style.COLOR["band_edge"],
                lw=0.5, ls=(0, (2.0, 1.6)), zorder=1)
    ax.axhline(0, color=_style.COLOR["ink"], lw=0.7, zorder=2)

    # Primary and secondary differ by marker fill instead of hue, since grey
    # already means "no profile arm" in panel (a) and one hue must not carry two
    # meanings inside one figure.  The x ticks name the strata and the caption
    # keys the fill.
    for stratum, fill in (("weak", _style.COLOR["ink"]), ("strong", "white")):
        p = pag[stratum]
        lo, hi = p["ci95_bca"]
        ax.errorbar([X[stratum]], [p["mean"]],
                    yerr=[[p["mean"] - lo], [hi - p["mean"]]],
                    fmt="o", ms=3.6, mfc=fill, mec=_style.COLOR["ink"], mew=0.8,
                    color=_style.COLOR["ink"], capsize=1.8, capthick=0.7,
                    elinewidth=0.8, zorder=5)

    ax.set_xticks([0, 1], ["weak", "strong"])
    ax.set_xlim(*XLIM_B)
    ax.set_ylim(*YLIM_B)
    ax.set_yticks([-0.5, 0.0, 0.5])
    ax.set_ylabel(r"PAG  $=\Delta(P_{\mathrm{nov}})-\Delta(P_{\mathrm{adv}})$",
                  labelpad=2)
    ax.set_title("b   the registered estimand", fontsize=_style.PT["title"],
                 loc="left", pad=5)
    _style.tidy(ax)

    written = _style.save(fig, _data.OUT, "fig1")
    plt.close(fig)

    problems = _style.verify_pdf(_data.OUT / "fig1.pdf",
                                 _style.TEXTWIDTH_IN * FRAC_LINEWIDTH)
    for msg in problems:
        print(f"  !! {msg}")
    print("wrote " + ", ".join(str(p_) for p_ in written)
          + ("" if problems else "   [submission checks clean]"))


if __name__ == "__main__":
    main()
