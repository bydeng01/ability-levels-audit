#!/usr/bin/env python3
"""Exploratory diagnostics of rating-scale censoring (outside registered S6/S7).

Panels show (a) composite ratings and boundary counts, (b) the two pole terms
whose difference is PAG, and (c) the productive-struggle censoring construction.
Panel (c) includes clipped and rounded variants, BCa intervals, and nonzero
cluster counts. A residual test with an attainable p-value floor above 0.05
cannot establish equivalence.

Reads released scores through _data, which checks key quantities against the
analysis output. Run from the repository root: python3 analysis/figures/fig2.py
"""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

import _data
import _style

FRAC_LINEWIDTH = 1.0
ASPECT = 0.4455          # 5.50 x 2.45in, the shipped height

# Panel (b) has the longest title and receives the widest slot.
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
    # Shade the scale bounds to show ceiling and floor pile-ups.
    for b in (_data.SCALE_MIN, _data.SCALE_MAX):
        ax.axvspan(b - 0.12, b + 0.12, color=C["band"], lw=0, zorder=0)
        ax.axvline(b, color=C["band_edge"], lw=0.6, ls=(0, (2.0, 1.6)), zorder=1)

    rows = [(p, a) for p in ("high", "low") for a in ARMS]
    ticks, labels = [], []
    for i, (pole, arm) in enumerate(rows):
        y = len(rows) - i
        col = C["pole_H"] if pole == "high" else C["pole_L"]
        v = np.array([_data.score(s, arm, pole) for s in _data.WEAK])
        # Jitter only the categorical row so boundary ratings remain at 1 or 5.
        # The jitter standard deviation is small relative to the row spacing.
        ax.scatter(v,
                   np.full(len(v), y)
                   + np.random.default_rng(i).normal(0, 0.09, len(v)),
                   s=6.0, color=col, alpha=0.55,
                   linewidths=0, zorder=3)
        ax.scatter([v.mean()], [y], marker="|", s=80, color=C["ink"],
                   zorder=4, linewidths=1.0)
        # The caption supplies the common denominator of 30.
        ax.text(5.28, y, f"{_data.n_at_bound(arm, pole)}", fontsize=PT["small"],
                va="center", color=col)
        head = "R_H" if pole == "high" else "R_L"
        sub = {"D": "D", "P_nov": r"P_{\mathrm{nov}}",
               "P_adv": r"P_{\mathrm{adv}}"}[arm]
        ticks.append(y)
        labels.append(rf"${head}\mid {sub}$")

    ax.set_yticks(ticks, labels, fontsize=PT["small"])
    # Leave room for the boundary-count labels.
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
        # The vertical gap encodes PAG; the annotation reports the high-pole share.
        ax.annotate(f"{share:.0%}", (x, -0.565), ha="center", va="center",
                    fontsize=PT["small"], color=C["muted"])

    ax.axhline(0, color=C["rule"], lw=0.7, zorder=1)
    # The caption defines the grey percentages as |a_H|/(|a_H|+|a_L|).

    # Place the pole key below the two leftmost columns.
    for k, (col, lab) in enumerate(((C["pole_H"], r"$a_H$  high pole"),
                                    (C["pole_L"], r"$a_L$  low pole"))):
        ax.annotate(lab, (-0.62, -0.325 - 0.085 * k), ha="left", va="center",
                    fontsize=PT["small"], color=col)

    ax.set_xticks(xs, [TICK[f] for f in FIELDS], fontsize=PT["small"],
                  rotation=32, ha="right", rotation_mode="anchor")
    ax.set_xlim(-0.72, 4.55)
    # Include the share annotations below the measured pole terms.
    ax.set_ylim(-0.65, 0.06)
    ax.set_yticks([-0.4, -0.2, 0.0])
    ax.set_ylabel("scale points", labelpad=2)
    # Use the manuscript terminology for the two terms of PAG.
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
        # Place the residual label beside its marker to clear the sensitivity label.
        if _lab == "residual":
            ax.annotate(f"{w['mean']:+.3f}", (i, w["mean"]), xytext=(-5, 0),
                        textcoords="offset points", ha="right", va="center",
                        fontsize=PT["small"], color=col)
        else:
            ax.annotate(f"{w['mean']:+.3f}", (i, hi), xytext=(0, 3),
                        textcoords="offset points", ha="center", va="bottom",
                        fontsize=PT["small"], color=col)
        # Report k to expose the attainable p-value floor, 2/2**k.
        # When that floor exceeds alpha, the exact test cannot reject.
        note = f"$k$={w['k_nonzero']}"
        if not w["can_reach_alpha"]:
            note += "\ncannot reject"
        ax.annotate(note, (i, lo), xytext=(0, -3.5), textcoords="offset points",
                    ha="center", va="top", fontsize=PT["small"],
                    color=C["muted"], linespacing=1.45)

    # Also show the variant rounded to the integer scores emitted by the judge.
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
