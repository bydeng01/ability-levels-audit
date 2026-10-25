#!/usr/bin/env python3
"""Post-hoc robustness checks added for the camera-ready version.

Every output is exploratory. None of it is registered, and none of it needed a new
judge call. The script reads results through analyze.load(), like diagnostics.py.

  1. Holm adjustment over the 21 registered p-values in analysis/out/summary.json.
  2. The share of the productive-struggle gap carried by stimuli whose low pole is
     floored in every arm, where PAG_s = -a_H,s holds exactly.
  3. The floor-censoring construction under an ordered-probit model of the integer
     ratings instead of hard clipping, with the rating noise fitted to the agreement
     among the three repetitions.
  4. Pole pinning under the companion study's second judge (GPT-5.6 Sol), on the
     real-turn poles it scored with the same rubric and the same dialogue.

Usage:
    python3 analysis/analyze.py              # writes analysis/out/summary.json
    python3 analysis/robustness_checks.py
    SRC_RESULTS=/path/to/conv-vs-ped-tutor/results python3 analysis/robustness_checks.py
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from math import comb
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))

import analyze as A  # noqa: E402  the frozen estimator, imported READ-ONLY
import diagnostics as D  # noqa: E402

FIELD = "productive_struggle"
EPS = 1e-9
SECOND_JUDGE = ("judge_robustness", "gpt-5.6-sol")
SECOND_JUDGE_BASES = ("sonnet", "gpt", "gemini")


def _key(field):
    return "overall_mean" if field == "overall" else f"{field}_mean"


def _weak(stimuli):
    return sorted(s for s, st in stimuli.items() if st["competence_label"] == "weak")


def _stimulus_weights(stimuli, sids):
    """Weight of each stimulus in the unweighted mean of source-run means."""
    runs = defaultdict(list)
    for s in sids:
        runs[stimuli[s]["source_run"]].append(s)
    return {s: 1.0 / (len(runs) * len(v)) for v in runs.values() for s in v}


# ------------------------------------------------------------------ 1. multiplicity
def registered_p_values(summary: dict) -> list:
    """(label, p, registered family) for the 21 tests in summary.json."""
    out = [("primary PAG weak", summary["primary_PAG_weak"]["wilcoxon_p"], "6.2 primary"),
           ("PAG strong", summary["secondary_PAG_strong"]["wilcoxon_p"], "6.3 PAG strong")]
    for k, v in summary["secondary_movement_from_D"].items():
        out.append((f"movement {k}", v["wilcoxon_p"], "6.3 movement from D"))
    for k, v in summary["secondary_pure_profile_effect"].items():
        out.append((f"pure profile {k}", v["wilcoxon_p"], "6.3 pure profile effect"))
    for k in ("PAG_weak_all_corpus", "PAG_strong_all_corpus"):
        out.append((f"authoring {k}", summary["secondary_authoring_robustness"][k]["wilcoxon_p"],
                    "6.3 authoring robustness"))
    for f, cell in summary["secondary_per_field_decomposition"].items():
        for st, v in cell.items():
            out.append((f"field {f} {st}", v["wilcoxon_p"], "6.3 per-field decomposition"))
    out.append(("influence x evidence", summary["secondary_influence_x_evidence"]["p"],
                "6.4 influence x evidence"))
    return out


def holm(p) -> np.ndarray:
    p = np.asarray(p, dtype=float)
    adj, running = np.empty(len(p)), 0.0
    for i, idx in enumerate(np.argsort(p)):
        running = max(running, (len(p) - i) * p[idx])
        adj[idx] = min(1.0, running)
    return adj


def sign_test_p(v) -> float:
    v = np.asarray(v, dtype=float)
    nz = v[np.abs(v) > A.ZERO_TOL]
    k = min(int((nz > 0).sum()), int((nz < 0).sum()))
    return min(1.0, 2 * sum(comb(len(nz), i) for i in range(k + 1)) / 2 ** len(nz))


def multiplicity(summary, units, stimuli) -> dict:
    rows = registered_p_values(summary)
    if len(rows) != 21:
        raise SystemExit(f"expected 21 registered p-values, found {len(rows)}")
    p = [r[1] for r in rows]
    all21 = holm(p)
    within = np.empty(len(rows))
    for fam in {r[2] for r in rows}:
        idx = [i for i, r in enumerate(rows) if r[2] == fam]
        within[idx] = holm([p[i] for i in idx])
    U = D._unit_index(units)
    sids = _weak(stimuli)
    key = _key(FIELD)
    ps_gap = D._cluster_means(stimuli, sids, lambda s: (
        (U[(s, "P_nov", "high")][key] - U[(s, "P_nov", "low")][key])
        - (U[(s, "P_adv", "high")][key] - U[(s, "P_adv", "low")][key])))
    return {
        "tests": [{"test": r[0], "family": r[2], "p": r[1], "holm_all_21": float(a),
                   "holm_within_family": float(w)} for r, a, w in zip(rows, all21, within)],
        "n_rejected_holm_all_21": int((all21 < 0.05).sum()),
        "productive_struggle_weak_sign_test_p": sign_test_p(ps_gap),
    }


# ------------------------------------------------------- 2. floored-stimulus share
def floored_share(units, stimuli, field=FIELD) -> dict:
    """Split the weak-stratum gap into the part carried by stimuli whose low pole reads
    1.000 in all three arms and the rest. On the floored part PAG_s = -a_H,s exactly, so
    the split needs no measurement model. Also checks whether the clip construction
    clips anything on the non-floored stimuli."""
    U = D._unit_index(units)
    key = _key(field)
    sids = _weak(stimuli)
    w = _stimulus_weights(stimuli, sids)
    reps = _reps()

    def gap(s):
        return ((U[(s, "P_nov", "high")][key] - U[(s, "P_nov", "low")][key])
                - (U[(s, "P_adv", "high")][key] - U[(s, "P_adv", "low")][key]))

    def a_high(s):
        return U[(s, "P_adv", "high")][key] - U[(s, "P_nov", "high")][key]

    floored = [s for s in sids if all(abs(U[(s, a, "low")][key] - 1.0) < EPS for a in A.ARMS)]
    free = [s for s in sids if s not in floored]
    total = sum(w[s] * gap(s) for s in sids)
    part = sum(w[s] * gap(s) for s in floored)
    clipped_free = [s for s in free
                    if any(not 1.0 <= r + a_high(s) <= 5.0 for r in reps[(s, "P_nov", "low")][field])]
    return {
        "field": field, "observed_PAG": total,
        "n_floored": len(floored), "n_free": len(free),
        "floored_contribution": part, "floored_share": part / total,
        "max_abs_identity_error_on_floored": max(abs(gap(s) + a_high(s)) for s in floored),
        "free_stimuli_with_any_clipping": clipped_free,
    }


# ------------------------------------------------- 3. ordered-probit construction
TAU = np.array([1.5, 2.5, 3.5, 4.5])  # unit-spaced thresholds; end categories open
GRID = np.linspace(-4.0, 10.0, 2801)
PRIORS = {"normal(3, 1.5)": lambda g: stats.norm.pdf(g, 3, 1.5),
          "normal(3, 3)": lambda g: stats.norm.pdf(g, 3, 3.0),
          "uniform(-1, 7)": lambda g: ((g >= -1) & (g <= 7)).astype(float)}


def _expected_rating(mu, sigma):
    return 1.0 + stats.norm.cdf((np.asarray(mu)[..., None] - TAU) / sigma).sum(-1)


def _category_probs(mu, sigma):
    cdf = stats.norm.cdf((TAU[None, :] - np.asarray(mu)[:, None]) / sigma)
    ones = np.ones((len(mu), 1))
    return np.diff(np.concatenate([0 * ones, cdf, ones], axis=1), axis=1)


def _posterior(ratings, sigma, prior):
    probs = _category_probs(GRID, sigma)
    post = prior * np.prod([probs[:, r - 1] for r in ratings], axis=0)
    return post / post.sum()


def probit_construction(units, stimuli, sigma, prior, deattenuate, field=FIELD) -> float:
    """Share of the observed gap reproduced with zero differential preference when each
    integer rating comes from an ordered-probit model. Each unit's latent location gets
    a posterior from its three P_nov ratings. The latent shift is the observed a_H,s
    (deattenuate=False, as in the clip construction) or the shift that makes the model
    reproduce a_H,s at the high pole (deattenuate=True). It is applied to the low pole."""
    U = D._unit_index(units)
    key = _key(field)
    reps = _reps()
    sids = _weak(stimuli)
    m = _expected_rating(GRID, sigma)
    con = {}
    for s in sids:
        a_h = U[(s, "P_adv", "high")][key] - U[(s, "P_nov", "high")][key]
        post_h = _posterior(reps[(s, "P_nov", "high")][field], sigma, prior)
        post_l = _posterior(reps[(s, "P_nov", "low")][field], sigma, prior)
        shift = a_h
        if deattenuate and abs(a_h) > EPS:
            def resid(d):
                return post_h @ _expected_rating(GRID + d, sigma) - post_h @ m - a_h
            lo, hi = (-6.0, 0.0) if a_h < 0 else (0.0, 6.0)
            for _ in range(60):
                mid = (lo + hi) / 2
                lo, hi = (lo, mid) if resid(lo) * resid(mid) <= 0 else (mid, hi)
            shift = (lo + hi) / 2
        a_l = post_l @ _expected_rating(GRID + shift, sigma) - post_l @ m
        con[s] = a_l - a_h
    obs = D._cluster_means(stimuli, sids, lambda s: (
        (U[(s, "P_nov", "high")][key] - U[(s, "P_nov", "low")][key])
        - (U[(s, "P_adv", "high")][key] - U[(s, "P_adv", "low")][key])))
    return float(D._cluster_means(stimuli, sids, lambda s: con[s]).mean() / obs.mean())


def sigma_profile(stimuli, sigmas, field=FIELD, n_iter=300) -> dict:
    """Profile log-likelihood of the rating noise from the three-rating pattern of every
    weak-stratum unit, with the latent locations given a nonparametric distribution on a
    grid (fitted by EM)."""
    reps = _reps()
    patterns = [reps[(s, a, p)][field] for s in _weak(stimuli) for a in A.ARMS
                for p in ("high", "low")]
    grid = np.linspace(-2.0, 8.0, 401)
    out = {}
    for sg in sigmas:
        probs = _category_probs(grid, sg)
        lik = np.array([np.prod([probs[:, r - 1] for r in rs], axis=0) for rs in patterns])
        g = np.full(len(grid), 1.0 / len(grid))
        for _ in range(n_iter):
            g = (lik * g / (lik * g).sum(1, keepdims=True)).mean(0)
        out[sg] = float(np.log((lik * g).sum(1)).sum())
    best = max(out.values())
    return {sg: ll - best for sg, ll in out.items()}


# ------------------------------------------------------------- 4. second judge
def second_judge_pinning(units, stimuli, src_results: Path, field="overall") -> dict:
    lut = {}
    for base in SECOND_JUDGE_BASES:
        p = src_results.joinpath(*SECOND_JUDGE, base, "pedagogy_detail.json")
        if not p.is_file():
            return {"skipped": True, "reason": f"missing {p}"}
        for run in json.loads(p.read_text())["runs"]:
            for t in run["turns"]:
                lut[(t["run_id"], t["problem_id"], t["turn_index"])] = t
    U = D._unit_index(units)
    out = {"field": field}
    for pole, bound in (("high", 5.0), ("low", 1.0)):
        rows = [(sid, lut[(st["source_run"], st["problem_id"], st["turn_index"])])
                for sid, st in sorted(stimuli.items()) if st["real_turn_pole"] == pole
                and (st["source_run"], st["problem_id"], st["turn_index"]) in lut]
        out[pole] = {
            "n_poles": len(rows), "bound": bound,
            "n_at_bound_second_judge": sum(abs(t[_key(field)] - bound) < EPS for _, t in rows),
            "n_at_bound_this_study_D_arm": sum(
                abs(U[(sid, "D", pole)][_key(field)] - bound) < EPS for sid, _ in rows),
        }
    return out


# ------------------------------------------------------------------------- helpers
_REPS = None


def _reps():
    global _REPS
    if _REPS is None:
        _REPS = defaultdict(dict)
        rows = defaultdict(dict)
        for line in open(ROOT / "results/per_rep_scores.jsonl"):
            r = json.loads(line)
            rows[(r["stimulus_id"], r["arm"], r["pole"])][r["rep"]] = r["scores"]
        for k, by_rep in rows.items():
            for f in A.SUB_FIELDS + ("overall",):
                _REPS[k][f] = [by_rep[i][f] for i in sorted(by_rep)]
    return _REPS


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src-results", default=str(D.DEFAULT_SRC_RESULTS),
                    help="companion study results/ dir (default %(default)s)")
    ap.add_argument("--out", default=str(ROOT / "analysis/out/robustness_checks.json"))
    args = ap.parse_args()

    meta, units, stimuli = A.load(False)
    summary_path = ROOT / "analysis/out/summary.json"
    if not summary_path.is_file():
        raise SystemExit("run analysis/analyze.py first; it writes analysis/out/summary.json")
    summary = json.loads(summary_path.read_text())

    sigmas = (0.10, 0.15, 0.20, 0.25)
    res = {
        "status": "POST-HOC; exploratory; no new judge calls",
        "multiplicity": multiplicity(summary, units, stimuli),
        "floored_share": floored_share(units, stimuli),
        "probit_sigma_profile_loglik": sigma_profile(
            stimuli, (0.05, 0.10, 0.15, 0.20, 0.225, 0.25, 0.275, 0.30, 0.50, 1.00)),
        "probit_share": {
            name: {f"sigma={sg}": {"observed_shift": probit_construction(units, stimuli, sg, pr(GRID), False),
                                    "deattenuated_shift": probit_construction(units, stimuli, sg, pr(GRID), True)}
                   for sg in sigmas + (1.0,)}
            for name, pr in PRIORS.items()},
        "second_judge_pinning": second_judge_pinning(units, stimuli, Path(args.src_results)),
    }
    shares = [v for cell in res["probit_share"].values() for k, sg in cell.items()
              if k != "sigma=1.0" for v in sg.values()]
    res["probit_share_range_sigma_0.10_to_0.25"] = [min(shares), max(shares)]

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2))

    m = res["multiplicity"]
    print(f"Holm over 21 registered tests: {m['n_rejected_holm_all_21']} rejection(s)")
    for t in sorted(m["tests"], key=lambda t: t["p"])[:3]:
        print(f"  {t['test']:58s} p={t['p']:.5f}  Holm(21)={t['holm_all_21']:.3f}  "
              f"Holm(within family)={t['holm_within_family']:.3f}")
    print(f"  productive-struggle gap, sign test p = {m['productive_struggle_weak_sign_test_p']:.4f}")
    f = res["floored_share"]
    print(f"Floored stimuli: {f['n_floored']} carry {f['floored_contribution']:+.4f} of "
          f"{f['observed_PAG']:+.4f} ({f['floored_share']:.1%}); free stimuli clipped: "
          f"{f['free_stimuli_with_any_clipping'] or 'none'}")
    print("Ordered-probit sigma profile (log-lik minus max):",
          {k: round(v, 2) for k, v in res["probit_sigma_profile_loglik"].items()})
    lo, hi = res["probit_share_range_sigma_0.10_to_0.25"]
    print(f"Ordered-probit construction, sigma 0.10-0.25: {lo:.1%} to {hi:.1%}")
    print("  sigma=1.0:", {k: {kk: round(vv, 3) for kk, vv in v["sigma=1.0"].items()}
                          for k, v in res["probit_share"].items()})
    print("Second judge:", json.dumps(res["second_judge_pinning"]))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
