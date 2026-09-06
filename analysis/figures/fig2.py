#!/usr/bin/env python3
"""EXPLORATORY (not registered S6/S7).  Endpoint identifiability under censoring.
Rebuilt 2026-08-18.

(a) Where the ratings sit on the 1-5 scale, per arm and pole, weak stratum.
(b) Each field's two pole terms on a common axis, with PAG as the gap between
    them, and the share of limb movement the high pole carries.
(c) Productive struggle against a zero-differential-preference censoring null.

Four things changed.  Each fixes a place where the shipped build asserted more
than the manuscript does.

1.  Panel (b) no longer draws a push-pull that is not in the data.  The shipped
build plotted -a_H upward and a_L downward as opposed bars.  Both terms are
negative: the advanced profile scores both poles lower than the novice profile
does, by 0.238 and 0.153 on the composite.  Flipping the sign of one of them
turned two co-directional shifts into a visual opposition, which is the
differential preference S6.2 says the data do not show.  Plotting a_H and a_L on
one axis with PAG as the vertical gap makes PAG = a_L - a_H geometric instead of
a sign convention, and lets the reader see that both terms move the same way.

2.  The title no longer overclaims.  "every PAG is one-limb movement" is
false for the panel's own first column: the high pole carries 60.9% of the limb
movement on the composite against 71.9-95.9% on the four sub-scores, and 280% of
the gap against 105-164%.  The sentence citing this panel quotes "72-96%", a
range computed over the sub-scores alone.  The share is now printed per field, so
no verbal summary can drift from what is drawn and the composite shows up as the
outlier.

3.  Panel (c) prints no p-values.  The residual's exact signed-rank test has
5 nonzero clusters, so its smallest attainable p is 2/2**5 = 0.0625, above alpha:
it could not have rejected under any data, and S6.3 says so ("whose floor exceeds
0.05, so it bounds nothing").  The shipped build set "p=0.625" beside it in green
next to two significant p-values, delivering the inference the text disowns.
The null model's own p = 0.00391 is likewise at its floor at 9
nonzero clusters and states only that every moving cluster agreed in sign.  The
panel now shows estimates, intervals and the nonzero-cluster count; the p-values
live in the text, where their floors are stated beside them.

4.  Panel (c) shows the sensitivity band instead of one number.  The
construction reproduces 85% of the observed gap under a plain clip and 79% if the
shifted ratings are rounded to the integers the judge actually emits, and a full
low-limb clip would manufacture 104.5%, more than the whole observed gap.
Drawing all three keeps "censoring alone can account for this" a bounded claim.

Text-load reduction, 2026-08-22.  Measured against the shipped build, this
figure carried 136 word-boxes at 10.1 per square inch, against 4.4 for the
registered figure: 2.3x the density, concentrated in panel (b), which held ten
numerals, a two-line key and a gloss row over five columns.  Three runs of text
were cut, all of them second copies of something the reader already has within a
page and a half: panel (b)'s five PAG numerals (S6.3 gives four of them with
p-values in the sentence above the figure, and the composite is in S6.1 and
Fig. 2b), the "high-pole share of limb movement" gloss (the caption defines the
grey figures), and the six repetitions of "/30" (the caption says "of 30").
Nothing that is only available from the drawing was removed: the five share
percentages, the k counts, the "cannot reject" note and the three panel-(c)
estimates all stay.  The vacated bands are closed by the limit changes marked
below instead of being left as blank paper.

Two further repairs.  Pole identity moved off the arm hues (see
``_style.COLOR``); the shipped build reused fig1's arm blue and vermillion to
mean pole, so a reader carrying the mapping across figures read this one
backwards.  And the x-axis label no longer carries a backticked configuration
field name.

Every value is loaded through ``_data``, whose ``selftest`` re-derives it against
the released estimator output.  No paid call; no frozen input touched.
"""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

import _data
import _style

FRAC_LINEWIDTH = 1.0
ASPECT = 0.4455          # 5.50 x 2.45in, the shipped height

# Panel widths are set from measured string metrics, not guessed: at 7pt the
# longest title is panel (b)'s at 108pt, so (b) gets the widest slot.  Total
# axes width 300pt over three panels, 28pt gaps for tick labels and y-labels.
FIELDS = _data.FIELDS
ARMS = _data.ARMS
TICK = {"overall": "composite", "scaffolding": "scaffolding",
        "productive_struggle": "prod. struggle",
        "assistance_calibration": "assist. calib.",
        "elicitation": "elicitation"}


def main() -> None:
    _style.apply()
    C, PT = _style.COLOR, _style.PT
    fig = plt.figure(figsize=_style.figsize_for(FRAC_LINEWIDTH, aspect=ASPECT))
    gs = fig.add_gridspec(1, 3, width_ratios=[0.95, 1.12, 0.93], wspace=0.28,
                          left=0.088, right=0.988, top=0.850, bottom=0.250)

    # ------------------------------------------------- (a) where the ratings sit
    ax = fig.add_subplot(gs[0])
    # Shade the bounds so the pile-up reads as a region instead of a count to be
    # trusted.  The ceiling strip carries far more mass than the floor strip, and
    # that asymmetry is what S6.4 turns on, yet panels (b) and (c) both argue
    # from the floor.  The caption has to name that tension.
    for b in (_data.SCALE_MIN, _data.SCALE_MAX):
        ax.axvspan(b - 0.12, b + 0.12, color=C["band"], lw=0, zorder=0)
        ax.axvline(b, color=C["band_edge"], lw=0.6, ls=(0, (2.0, 1.6)), zorder=1)

    rows = [(p, a) for p in ("high", "low") for a in ARMS]
    ticks, labels = [], []
    for i, (pole, arm) in enumerate(rows):
        y = len(rows) - i
        col = C["pole_H"] if pole == "high" else C["pole_L"]
        v = np.array([_data.score(s, arm, pole) for s in _data.WEAK])
        # Jitter the ROW, never the rating.  This panel exists to show units
        # resting exactly on a bound, which is what the caption counts and what
        # S6.3 argues from; noise on the measured axis smears that stack off
        # the bound and draws marks outside the 1-5 scale.  Sigma is
        # set from the row spacing (1.0), so +-3 sigma stays inside half a gap
        # and adjacent rows never merge.  fig3.py stacks instead; here the six
        # rows are fixed and evenly spaced, so jitter carries the density.
        ax.scatter(v,
                   np.full(len(v), y)
                   + np.random.default_rng(i).normal(0, 0.09, len(v)),
                   s=6.0, color=col, alpha=0.55,
                   linewidths=0, zorder=3)
        ax.scatter([v.mean()], [y], marker="|", s=80, color=C["ink"],
                   zorder=4, linewidths=1.0)
        # Bare count instead of "n/30".  The denominator is the same on all rows
        # and the caption already carries it ("units resting exactly on that
        # pole's bound, of 30"), so printing it six times spends six text runs
        # on one fact the reader is told once.
        ax.text(5.28, y, f"{_data.n_at_bound(arm, pole)}", fontsize=PT["small"],
                va="center", color=col)
        head = "R_H" if pole == "high" else "R_L"
        sub = {"D": "D", "P_nov": r"P_{\mathrm{nov}}",
               "P_adv": r"P_{\mathrm{adv}}"}[arm]
        ticks.append(y)
        labels.append(rf"${head}\mid {sub}$")

    ax.set_yticks(ticks, labels, fontsize=PT["small"])
    # Right margin sized for the bare count instead of "n/30".  The old 6.18
    # held five glyphs, two now suffice, and the reclaimed width goes to the
    # 1-5 scale.
    ax.set_xlim(0.60, 5.86)
    ax.set_ylim(0.4, 6.6)
    ax.set_xticks([1, 2, 3, 4, 5])
    ax.set_xlabel("per-unit composite rating", labelpad=2)
    ax.set_title("a   the ceiling binds hardest", fontsize=PT["annot"],
                 loc="left", pad=4)
    _style.tidy(ax)
    ax.tick_params(axis="y", length=0)

    # ------------------------------------------------------------- (b) the limbs
    ax = fig.add_subplot(gs[1])
    xs = np.arange(len(FIELDS))
    for x, f in zip(xs, FIELDS):
        _pag, aH, aL = _data.limbs(f)
        mH, mL = aH.mean(), aL.mean()
        share = abs(mH) / (abs(mH) + abs(mL))
        ax.plot([x, x], [mH, mL], color=C["ink"], lw=2.8, alpha=0.28,
                solid_capstyle="butt", zorder=2)
        ax.plot([x], [mH], "o", ms=3.8, color=C["pole_H"], zorder=4)
        ax.plot([x], [mL], "o", ms=3.8, color=C["pole_L"], zorder=4)
        # No PAG numeral.  S6.3's own sentence, three lines above this figure,
        # already gives four of the five with their p-values, and the composite
        # is in S6.1 and Fig. 2b.  The panel's claim is that PAG is the gap, so
        # the gap is the encoding and the magnitude stays in prose.  Printing it
        # here also forced the label 3.5pt above m_L (a mark whose value has the
        # opposite sign) on an axis reading "scale points".
        ax.annotate(f"{share:.0%}", (x, -0.565), ha="center", va="center",
                    fontsize=PT["small"], color=C["muted"])

    ax.axhline(0, color=C["rule"], lw=0.7, zorder=1)
    # The grey figures are left unlabelled here on purpose: the caption defines
    # them ("Grey figures give |a_H|/(|a_H|+|a_L|)"), so an in-panel gloss is a
    # second copy.  The percentages themselves stay, because a ratio of two
    # lengths is the one quantity in this panel the eye cannot estimate.

    # A direct key instead of a legend.  A three-entry legend needs the top
    # quarter of a 112pt panel; the key only has to name the two ends, and it
    # sits in the empty wedge below the two leftmost columns.
    for k, (col, lab) in enumerate(((C["pole_H"], r"$a_H$  high pole"),
                                    (C["pole_L"], r"$a_L$  low pole"))):
        ax.annotate(lab, (-0.62, -0.325 - 0.085 * k), ha="left", va="center",
                    fontsize=PT["small"], color=col)

    ax.set_xticks(xs, [TICK[f] for f in FIELDS], fontsize=PT["small"],
                  rotation=32, ha="right", rotation_mode="anchor")
    ax.set_xlim(-0.72, 4.55)
    # Both bands the cuts vacated are closed: the top held the PAG numerals
    # (highest datum is now a_L on productive struggle at -0.017) and the floor
    # held the share gloss (lowest drawn thing is now the share row at -0.565).
    ax.set_ylim(-0.65, 0.06)
    ax.set_yticks([-0.4, -0.2, 0.0])
    ax.set_ylabel("scale points", labelpad=2)
    # "terms" instead of "limbs".  The body uses `pole` 55 times and `limb`
    # zero, and in the trials register the paper already cites, limb is a
    # synonym for arm, the one word this figure must not overload.  a_H and a_L
    # are the two terms of eq. (1), which is what S7 calls them.  Measured
    # 110.0pt against this panel's 112pt budget at 7pt.
    ax.set_title("b   both terms fall, the high pole further",
                 fontsize=PT["annot"], loc="left", pad=4)
    _style.tidy(ax)

    # --------------------------------------------------------- (c) censoring null
    ax = fig.add_subplot(gs[2])
    cn = _data.censoring_null("productive_struggle")
    ceiling = cn["full_clip_ceiling"]
    ax.plot((-0.55, 2.55), (ceiling, ceiling), color=C["faint"], lw=0.6,
            ls=(0, (2.0, 1.6)), zorder=1)
    ax.annotate("full-clip ceiling", (2.50, ceiling), xytext=(0, 2),
                textcoords="offset points", ha="right", va="bottom",
                fontsize=PT["small"], color=C["muted"])

    marks = (("observed", cn["observed"], C["P_adv"]),
             ("censoring\nnull", cn["clip"], C["muted"]),
             ("residual", cn["residual"], C["pole_H"]))
    for i, (_lab, w, col) in enumerate(marks):
        lo, hi = w["ci95_bca"]
        ax.errorbar([i], [w["mean"]], yerr=[[w["mean"] - lo], [hi - w["mean"]]],
                    fmt="o", ms=3.8, color=col, capsize=2.0, capthick=0.7,
                    elinewidth=0.8, zorder=4)
        # The residual's value goes beside its marker instead of above its
        # interval.  Above, it sits at the same height as the sensitivity label
        # one column to its left and the two collide in a 93pt panel.
        if _lab == "residual":
            ax.annotate(f"{w['mean']:+.3f}", (i, w["mean"]), xytext=(-5, 0),
                        textcoords="offset points", ha="right", va="center",
                        fontsize=PT["small"], color=col)
        else:
            ax.annotate(f"{w['mean']:+.3f}", (i, hi), xytext=(0, 3),
                        textcoords="offset points", ha="center", va="bottom",
                        fontsize=PT["small"], color=col)
        # k instead of p.  Where the attainable floor 2/2**k exceeds alpha the test
        # could not have rejected under any data, so a p-value there is not a
        # result and must not be set beside two that are.
        note = f"$k$={w['k_nonzero']}"
        if not w["can_reach_alpha"]:
            note += "\ncannot reject"
        ax.annotate(note, (i, lo), xytext=(0, -3.5), textcoords="offset points",
                    ha="center", va="top", fontsize=PT["small"],
                    color=C["muted"], linespacing=1.45)

    # The rounded variant: the same construction restricted to the integers the
    # judge actually emits.  Reporting both points is the honest reading.
    ax.plot([1], [cn["round_then_clip"]["mean"]], "o", ms=3.8, mfc="white",
            mec=C["muted"], mew=0.8, zorder=5)
    ax.annotate(f"{cn['share_round']:.0%}-{cn['share_clip']:.0%}",
                (1.20, 0.5 * (cn["clip"]["mean"] + cn["round_then_clip"]["mean"])),
                ha="left", va="center", fontsize=PT["small"], color=C["muted"])

    ax.axhline(0, color=C["rule"], lw=0.7, zorder=1)
    ax.set_xticks(range(3), [m[0] for m in marks], fontsize=PT["small"])
    ax.set_xlim(-0.55, 2.55)
    ax.set_ylim(-0.20, 0.78)
    ax.set_yticks([0.0, 0.2, 0.4, 0.6])
    ax.set_ylabel("PAG (scale points)", labelpad=2)
    ax.set_title("c   censoring reproduces it", fontsize=PT["annot"],
                 loc="left", pad=4)
    _style.tidy(ax)

    written = _style.save(fig, _data.OUT, "fig2")
    plt.close(fig)

    problems = _style.verify_pdf(_data.OUT / "fig2.pdf",
                                 _style.TEXTWIDTH_IN * FRAC_LINEWIDTH)
    for msg in problems:
        print(f"  !! {msg}")
    print("wrote " + ", ".join(str(p) for p in written)
          + ("" if problems else "   [submission checks clean]"))


if __name__ == "__main__":
    main()
