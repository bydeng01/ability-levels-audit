#!/usr/bin/env python3
"""Post-hoc simulations for the appendix. Not registered, and not a frozen input; every
value is a deterministic function of the promoted scores and of SEED.

This file exists because three numbers the manuscript reports had no producer in the
repository, which contradicts the provenance claim that every reported value re-derives
offline from the released artifacts. It commits them:

  1. BCa interval coverage at n = 18, for the primary endpoint and for the pure low-pole
     endpoint (Appendix "Power and coverage simulations").
  2. Stability of the one near-zero BCa lower limit across bootstrap seeds (Appendix
     "Release, specification status, and multiplicity").
  3. The size of the registered exact signed-rank test under a null it actually
     satisfies.

(3) is the substantive one. analysis/figures/fig3.py resamples the cluster distribution
centred on its MEAN. That distribution has mean zero but is asymmetric, so the
signed-rank null (symmetry about zero) is false under it by construction, and the
rejection rate it returns at shift zero is not the test's size. Under a DGP that does
satisfy the null (random sign flips of the observed magnitudes) the same exact test is
correctly sized. Reading fig3's shift-zero rate as "a mildly anti-conservative test" is
therefore a misdiagnosis: what it measures is the gap between the mean and the
pseudomedian. The power curve itself is unaffected; it remains a valid power curve
against a shift in the mean.

Run:  python analysis/simulations.py
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))
import analyze as A  # noqa: E402  the frozen estimator, imported READ-ONLY

SEED = 20260818
ALPHA = 0.05


def _bca(vals: np.ndarray, seed: int) -> list:
    """A.bca_ci with the bootstrap seed exposed. Asserted against the frozen version at
    A.BOOT_SEED below, so a drift in either implementation fails loudly."""
    vals = np.asarray(vals, dtype=float)
    if len(vals) < 2 or np.allclose(vals, vals[0]):
        return [float(vals.mean()), float(vals.mean())]
    res = stats.bootstrap((vals,), np.mean, n_resamples=A.N_RESAMPLES, method="BCa",
                          confidence_level=1 - ALPHA,
                          random_state=np.random.default_rng(seed))
    return [float(res.confidence_interval.low), float(res.confidence_interval.high)]


def _p_exact_signrank(v: np.ndarray) -> float:
    """The registered test's p-value only, without the BCa interval A.wilcoxon_report
    also computes: 10,000 resamples per replicate would make the size study
    unaffordable. Asserted against A.wilcoxon_report on the observed vectors below."""
    nz = np.asarray(v, dtype=float)
    nz = nz[np.abs(nz) > A.ZERO_TOL]
    if len(nz) == 0:
        return 1.0
    doubled = np.rint(2 * stats.rankdata(np.round(np.abs(nz), 12),
                                         method="average")).astype(int)
    total, plus = int(doubled.sum()), int(doubled[nz > 0].sum())
    tail = min(plus, total - plus)
    counts = {0: 1}
    for rank in doubled:
        nxt = dict(counts)
        for state, n in counts.items():
            nxt[state + int(rank)] = nxt.get(state + int(rank), 0) + n
        counts = nxt
    return min(1.0, 2 * sum(n for s, n in counts.items() if s <= tail) / (2 ** len(nz)))


def _hodges_lehmann(v: np.ndarray) -> float:
    w = [(v[i] + v[j]) / 2.0 for i in range(len(v)) for j in range(i, len(v))]
    return float(np.median(w))


def _cluster_means(stimuli, sids, value_of) -> np.ndarray:
    grouped = defaultdict(list)
    for sid in sids:
        grouped[stimuli[sid]["source_run"]].append(float(value_of(sid)))
    return np.array([np.mean(grouped[r]) for r in sorted(grouped)], dtype=float)


def endpoints(units, stimuli) -> dict:
    """The three weak-stratum cluster vectors the appendix simulations are about."""
    U = {(u["stimulus_id"], u["arm"], u["pole"]): u for u in units}
    weak = [s for s, st in stimuli.items() if st["competence_label"] == "weak"]

    def S(sid, arm, pole):
        return U[(sid, arm, pole)]["overall_mean"]

    return {
        "primary_PAG_weak": _cluster_means(
            stimuli, weak,
            lambda s: (S(s, "P_nov", "high") - S(s, "P_nov", "low"))
                    - (S(s, "P_adv", "high") - S(s, "P_adv", "low"))),
        "pure_low_pole_weak": _cluster_means(
            stimuli, weak, lambda s: S(s, "P_adv", "low") - S(s, "P_nov", "low")),
        # the row whose BCa lower limit prints as 0.000
        "movement_P_nov_minus_D_weak": _cluster_means(
            stimuli, weak,
            lambda s: (S(s, "P_nov", "high") - S(s, "P_nov", "low"))
                    - (S(s, "D", "high") - S(s, "D", "low"))),
    }


def coverage(vals: np.ndarray, reps: int, seed: int) -> dict:
    """Nonparametric coverage of the registered BCa interval at the realised n. The
    population is the empirical distribution of the observed cluster means, so the true
    parameter is their mean; draw samples of the same size from it and count coverage."""
    rng = np.random.default_rng(seed)
    truth, n, hits = float(vals.mean()), len(vals), 0
    for _ in range(reps):
        lo, hi = _bca(rng.choice(vals, size=n, replace=True), A.BOOT_SEED)
        hits += int(lo <= truth <= hi)
    p = hits / reps
    return {"n": n, "replicates": reps, "true_parameter": truth,
            "coverage": p, "mc_standard_error": float(np.sqrt(p * (1 - p) / reps)),
            "nominal": 1 - ALPHA}


def seed_sweep(vals: np.ndarray, n_seeds: int) -> dict:
    """How much of the near-zero BCa lower limit is the resample draw rather than the
    data. Seeds are 0..n_seeds-1 so the sweep is reproducible without a stored list."""
    limits = [_bca(vals, seed)[0] for seed in range(n_seeds)]
    return {"n_seeds": n_seeds, "seeds": "range(0, %d)" % n_seeds,
            "frozen_estimator_seed": A.BOOT_SEED,
            "frozen_estimator_lower_limit": _bca(vals, A.BOOT_SEED)[0],
            "lower_limits_exactly_zero": int(sum(abs(x) < 1e-12 for x in limits)),
            "lower_limits_excluding_zero": int(sum(x > 0 for x in limits)),
            "max_abs_lower_limit": float(np.max(np.abs(limits)))}


def signrank_size(vals: np.ndarray, reps: int, seed: int) -> dict:
    """Size of the registered exact test under three DGPs. Only the sign-flip DGPs
    satisfy the test's null (symmetry about zero); the mean-centred bootstrap is the one
    fig3.py uses, reported here so the two can be compared directly."""
    rng = np.random.default_rng(seed)
    n = len(vals)
    hl = _hodges_lehmann(vals)
    dgps = {
        "mean_centred_bootstrap_fig3": lambda: rng.choice(vals - vals.mean(), size=n,
                                                          replace=True),
        "hodges_lehmann_centred_bootstrap": lambda: rng.choice(vals - hl, size=n,
                                                               replace=True),
        "sign_flip_about_hodges_lehmann": lambda: np.abs(vals - hl) * rng.choice(
            [-1.0, 1.0], size=n),
        "sign_flip_about_zero": lambda: np.abs(vals) * rng.choice([-1.0, 1.0], size=n),
    }
    out = {"replicates": reps, "alpha": ALPHA, "mean": float(vals.mean()),
           "hodges_lehmann": hl,
           "note": "only the sign_flip rows satisfy the signed-rank null; those are the "
                   "test's size. The fig3 row is power against a nonzero pseudomedian."}
    for name, draw in dgps.items():
        out[name] = sum(_p_exact_signrank(draw()) < ALPHA for _ in range(reps)) / reps
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--allow-mock", action="store_true")
    ap.add_argument("--coverage-reps", type=int, default=600)
    ap.add_argument("--size-reps", type=int, default=20000)
    ap.add_argument("--n-seeds", type=int, default=40)
    ap.add_argument("--out", default=str(ROOT / "analysis/out/simulations.json"))
    args = ap.parse_args()

    meta, units, stimuli = A.load(args.allow_mock)
    ep = endpoints(units, stimuli)

    # Guards: the two local reimplementations must agree with the frozen estimator.
    for name, v in ep.items():
        assert _bca(v, A.BOOT_SEED) == A.bca_ci(v), f"_bca drifted from A.bca_ci on {name}"
        assert abs(_p_exact_signrank(v) - A.wilcoxon_report(v)["wilcoxon_p"]) < 1e-12, \
            f"_p_exact_signrank drifted from A.wilcoxon_report on {name}"

    res = {
        "provenance": {
            "contract_sha256": meta.get("contract_sha256"),
            "seed": SEED,
            "emitted_by": "analysis/simulations.py (NOT a frozen input; post-hoc; "
                          "deterministic given seed)",
        },
        "coverage": {name: coverage(ep[name], args.coverage_reps, SEED + i)
                     for i, name in enumerate(("primary_PAG_weak", "pure_low_pole_weak"))},
        "near_zero_bca_limit": seed_sweep(ep["movement_P_nov_minus_D_weak"], args.n_seeds),
        "signrank_size_primary": signrank_size(ep["primary_PAG_weak"], args.size_reps, SEED),
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(res, indent=2))

    print("POST-HOC — BCa coverage at the realised n (nominal 0.95)")
    for name, c in res["coverage"].items():
        print(f"  {name:28} n={c['n']}  coverage={c['coverage']:.3f} "
              f"(MC s.e. {c['mc_standard_error']:.3f}, {c['replicates']} replicates)")

    z = res["near_zero_bca_limit"]
    print(f"\nPOST-HOC — the near-zero BCa lower limit across {z['n_seeds']} bootstrap seeds")
    print(f"  frozen estimator (seed {z['frozen_estimator_seed']}): "
          f"{z['frozen_estimator_lower_limit']!r}")
    print(f"  exactly zero in {z['lower_limits_exactly_zero']}/{z['n_seeds']} seeds; "
          f"strictly positive (excludes zero) in {z['lower_limits_excluding_zero']}; "
          f"max |limit| {z['max_abs_lower_limit']:.3g}")

    s = res["signrank_size_primary"]
    print(f"\nPOST-HOC — exact signed-rank rejection rate at alpha={s['alpha']}, "
          f"{s['replicates']} replicates")
    print(f"  primary cluster vector: mean {s['mean']:+.4f}, "
          f"Hodges-Lehmann {s['hodges_lehmann']:+.4f}")
    for name in ("mean_centred_bootstrap_fig3", "hodges_lehmann_centred_bootstrap",
                 "sign_flip_about_hodges_lehmann", "sign_flip_about_zero"):
        satisfies = "null TRUE  -> this is the size" if name.startswith("sign_flip") \
            else "null FALSE -> not a size"
        print(f"  {name:34} {s[name]:.4f}   ({satisfies})")

    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
