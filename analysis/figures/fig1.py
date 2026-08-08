#!/usr/bin/env python3
"""The abstract's one figure (PREREGISTRATION.md §7).

x: demonstrated competence (weak -> strong, independently labelled);
y: preference for high scaffolding, Delta = S(R_H) - S(R_L);
two lines: stated-novice and stated-advanced profile arms, BCa CIs;
gray dashed reference: the no-profile D arm.
Parallel, closely-spaced lines = behaviour-driven judge; wide separation =
profile anchoring.

Reads analysis/out/summary.json (written by analyze.py). Emits fig1.pdf/.png.
Palette: Okabe-Ito blue/vermillion (validated CVD-safe pair) + neutral gray.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "analysis" / "figures"

COL = {"P_nov": "#0072B2", "P_adv": "#D55E00", "D": "#6b6b6b"}
LABEL = {"P_nov": "stated novice", "P_adv": "stated advanced", "D": "no profile (D)"}
X = {"weak": 0.0, "strong": 1.0}
NUDGE = {"P_nov": -0.03, "P_adv": +0.03, "D": 0.0}


def cell(summary, arm, stratum):
    return summary["four_cell_table"][f"delta({arm},{stratum})"]


def main():
    summary = json.loads((ROOT / "analysis/out/summary.json").read_text())

    fig, ax = plt.subplots(figsize=(3.35, 2.7), dpi=300)
    for arm in ("D", "P_nov", "P_adv"):
        xs, ys, lo, hi = [], [], [], []
        for stratum in ("weak", "strong"):
            c = cell(summary, arm, stratum)
            xs.append(X[stratum] + NUDGE[arm])
            ys.append(c["mean"])
            lo.append(c["mean"] - c["ci95_bca"][0])
            hi.append(c["ci95_bca"][1] - c["mean"])
        style = dict(color=COL[arm], lw=1.6, marker="o", ms=4, zorder=3)
        if arm == "D":
            style.update(ls="--", lw=1.2, ms=3, zorder=2, alpha=0.85)
        ax.errorbar(xs, ys, yerr=[lo, hi], capsize=2.5, elinewidth=0.9, **style)
        ax.annotate(LABEL[arm], (xs[-1], ys[-1]), xytext=(6, 0),
                    textcoords="offset points", va="center", fontsize=7,
                    color=COL[arm])

    pag = summary["primary_PAG_weak"]
    ax.set_title(
        f"PAG$_{{weak}}$ = {pag['mean']:+.2f}  "
        f"[{pag['ci95_bca'][0]:+.2f}, {pag['ci95_bca'][1]:+.2f}]",
        fontsize=8, loc="left", pad=4)
    ax.axhline(0, color="#c9c9c9", lw=0.7, zorder=1)
    ax.set_xticks([0, 1], ["weak", "strong"], fontsize=8)
    ax.set_xlabel("demonstrated competence (blind-labelled)", fontsize=8)
    ax.set_ylabel(r"preference for high scaffolding  $\Delta$", fontsize=8)
    ax.set_xlim(-0.25, 1.55)
    ax.tick_params(labelsize=7)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#9a9a9a")
    ax.grid(axis="y", color="#ececec", lw=0.5, zorder=0)
    fig.tight_layout(pad=0.4)
    fig.savefig(OUT / "fig1.pdf")
    fig.savefig(OUT / "fig1.png")
    print(f"wrote {OUT}/fig1.pdf and fig1.png")


if __name__ == "__main__":
    main()
