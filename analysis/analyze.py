#!/usr/bin/env python3
"""Pre-registered analysis (PREREGISTRATION.md §6). Written and frozen BEFORE any
judge score existed; everything beyond §6 is exploratory and must be labelled so.

Inputs:  results/per_unit.jsonl (promoted, complete), corpus/stimuli.jsonl.
Outputs: analysis/out/summary.json, analysis/out/per_stimulus_deltas.csv, and a
         printed report. Refuses non-live (mock) runs unless --allow-mock.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))

BOOT_SEED = 13
N_RESAMPLES = 10_000
EV_ORD = {"ambiguous": 0, "moderate": 1, "strong": 2}
ARMS = ("D", "P_nov", "P_adv")


def bca_ci(vals: np.ndarray, alpha: float = 0.05):
    vals = np.asarray(vals, dtype=float)
    if len(vals) < 2 or np.allclose(vals, vals[0]):
        return [float(vals.mean()), float(vals.mean())]
    res = stats.bootstrap((vals,), np.mean, n_resamples=N_RESAMPLES, method="BCa",
                          confidence_level=1 - alpha,
                          random_state=np.random.default_rng(BOOT_SEED))
    return [float(res.confidence_interval.low), float(res.confidence_interval.high)]


def wilcoxon_report(vals: np.ndarray) -> dict:
    """Two-sided signed-rank vs 0 + matched-pairs rank-biserial effect size."""
    vals = np.asarray(vals, dtype=float)
    nz = vals[vals != 0]
    out = {"n": int(len(vals)), "n_nonzero": int(len(nz)),
           "mean": float(vals.mean()), "median": float(np.median(vals)),
           "ci95_bca": bca_ci(vals)}
    if len(nz) < 5:
        out.update({"wilcoxon_p": None, "rank_biserial": None,
                    "note": "fewer than 5 nonzero differences"})
        return out
    w = stats.wilcoxon(nz, alternative="two-sided", mode="auto")
    ranks = stats.rankdata(np.abs(nz))
    w_plus = float(ranks[nz > 0].sum())
    w_minus = float(ranks[nz < 0].sum())
    out.update({"wilcoxon_stat": float(w.statistic), "wilcoxon_p": float(w.pvalue),
                "rank_biserial": (w_plus - w_minus) / (w_plus + w_minus)})
    return out


def load(allow_mock: bool):
    meta = json.loads((ROOT / "results/run_meta.json").read_text())
    state = json.loads((ROOT / "results/run_state.json").read_text())
    assert state["state"] == "complete", "results are not a complete promoted set"
    if not meta.get("reportable") and not allow_mock:
        raise SystemExit(f"results backend is {meta.get('backend')!r} — NOT reportable. "
                         "Pass --allow-mock only for pipeline rehearsal output.")
    units = [json.loads(l) for l in open(ROOT / "results/per_unit.jsonl")]
    stimuli = {s["stimulus_id"]: s for s in
               (json.loads(l) for l in open(ROOT / "corpus/stimuli.jsonl"))}
    return meta, units, stimuli


def build_deltas(units, stimuli):
    """Per stimulus: S(pole|arm), Delta_s(arm) = S(high|arm) - S(low|arm)."""
    S = defaultdict(dict)
    for u in units:
        S[u["stimulus_id"]][(u["arm"], u["pole"])] = u["overall_mean"]
    rows = []
    for sid, sc in sorted(S.items()):
        st = stimuli[sid]
        row = {"stimulus_id": sid, "competence": st["competence_label"],
               "evidence_strength": st["evidence_strength"],
               "family": st["family"], "base": st["base"],
               "all_corpus": (st.get("r_high_provenance") == "corpus"
                              and st.get("r_low_provenance") == "corpus")}
        for arm in ARMS:
            row[f"S_high_{arm}"] = sc[(arm, "high")]
            row[f"S_low_{arm}"] = sc[(arm, "low")]
            row[f"delta_{arm}"] = sc[(arm, "high")] - sc[(arm, "low")]
        row["pag"] = row["delta_P_nov"] - row["delta_P_adv"]
        rows.append(row)
    return rows


def analyze(rows) -> dict:
    by_strat = {s: [r for r in rows if r["competence"] == s]
                for s in ("weak", "strong")}
    out = {"n_stimuli": len(rows),
           "n_per_stratum": {k: len(v) for k, v in by_strat.items()}}

    # 6.1 four-cell table (+ D-arm reference per stratum)
    four = {}
    for strat, rs in by_strat.items():
        for arm in ARMS:
            vals = np.array([r[f"delta_{arm}"] for r in rs])
            four[f"delta({arm},{strat})"] = {
                "mean": float(vals.mean()), "ci95_bca": bca_ci(vals), "n": len(rs)}
    out["four_cell_table"] = four

    # 6.2 primary: PAG_weak
    out["primary_PAG_weak"] = wilcoxon_report(
        np.array([r["pag"] for r in by_strat["weak"]]))

    # 6.3 secondaries
    out["secondary_PAG_strong"] = wilcoxon_report(
        np.array([r["pag"] for r in by_strat["strong"]]))
    move = {}
    for strat, rs in by_strat.items():
        for arm in ("P_nov", "P_adv"):
            vals = np.array([r[f"delta_{arm}"] - r["delta_D"] for r in rs])
            move[f"delta({arm})-delta(D), {strat}"] = wilcoxon_report(vals)
    out["secondary_movement_from_D"] = move
    pure = {}
    for strat, rs in by_strat.items():
        for pole in ("high", "low"):
            vals = np.array([r[f"S_{pole}_P_adv"] - r[f"S_{pole}_P_nov"] for r in rs])
            pure[f"S(R_{pole}|P_adv)-S(R_{pole}|P_nov), {strat}"] = wilcoxon_report(vals)
    out["secondary_pure_profile_effect"] = pure

    # 6.3b authoring robustness: the primary endpoint on stimuli with NO authored text
    allc = [r for r in rows if r["all_corpus"]]
    out["secondary_authoring_robustness"] = {
        "n_all_corpus": len(allc),
        "n_per_stratum": dict(Counter(r["competence"] for r in allc)),
        "PAG_weak_all_corpus": wilcoxon_report(
            np.array([r["pag"] for r in allc if r["competence"] == "weak"])),
        "PAG_strong_all_corpus": wilcoxon_report(
            np.array([r["pag"] for r in allc if r["competence"] == "strong"])),
        "rationale": "identical R_H/R_L texts are judged in all three arms, so a "
                     "stimulus-level authoring artifact cancels exactly in "
                     "PAG = delta(P_nov) - delta(P_adv); this subset removes "
                     "authoring entirely and should reproduce the primary result",
    }

    # 6.4 profile influence x evidence strength
    infl = np.array([abs(r["pag"]) for r in rows])
    ev = np.array([EV_ORD[r["evidence_strength"]] for r in rows])
    if len(set(ev)) > 1:
        rho, p = stats.spearmanr(ev, infl)
        out["secondary_influence_x_evidence"] = {
            "spearman_rho": float(rho), "p": float(p), "n": len(rows),
            "by_level": {lv: {"n": int((ev == EV_ORD[lv]).sum()),
                              "mean_abs_pag": float(infl[ev == EV_ORD[lv]].mean())
                              if (ev == EV_ORD[lv]).any() else None}
                         for lv in EV_ORD},
            "framing": "negative rho = profile influence shrinks as evidence "
                       "strengthens; the failure mode is influence persisting "
                       "undiminished under strong evidence"}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--allow-mock", action="store_true")
    args = ap.parse_args()
    meta, units, stimuli = load(args.allow_mock)
    rows = build_deltas(units, stimuli)
    res = {"backend": meta["backend"], "reportable": meta.get("reportable"),
           "contract_sha256": meta["contract_sha256"], **analyze(rows)}

    outdir = ROOT / "analysis/out"
    outdir.mkdir(exist_ok=True)
    (outdir / "summary.json").write_text(json.dumps(res, indent=2))
    cols = list(rows[0].keys())
    with open(outdir / "per_stimulus_deltas.csv", "w") as f:
        f.write(",".join(cols) + "\n")
        for r in rows:
            f.write(",".join(str(r[c]) for c in cols) + "\n")

    print(f"n = {res['n_stimuli']} stimuli {res['n_per_stratum']}")
    print("\nfour-cell table (Δ = S(R_H) − S(R_L)):")
    for k, v in res["four_cell_table"].items():
        print(f"  {k:24s} {v['mean']:+.3f}  CI {v['ci95_bca'][0]:+.3f}..{v['ci95_bca'][1]:+.3f}")
    p = res["primary_PAG_weak"]
    print(f"\nPRIMARY PAG_weak: mean {p['mean']:+.3f} CI {p['ci95_bca']} "
          f"Wilcoxon p={p['wilcoxon_p']} r_rb={p['rank_biserial']}")
    s = res["secondary_PAG_strong"]
    print(f"secondary PAG_strong: mean {s['mean']:+.3f} CI {s['ci95_bca']} "
          f"p={s['wilcoxon_p']}")
    if "secondary_influence_x_evidence" in res:
        e = res["secondary_influence_x_evidence"]
        print(f"influence×evidence: Spearman rho={e['spearman_rho']:+.3f} p={e['p']:.4f}")
    print("\nwrote analysis/out/summary.json + per_stimulus_deltas.csv")


if __name__ == "__main__":
    main()
