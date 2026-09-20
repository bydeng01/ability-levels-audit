#!/usr/bin/env python3
"""Shared data loading and calculations for the figures.

Loads released per-unit and per-rep scores, summary.json, and diagnostics.json.
selftest() checks key figure quantities against the analysis output. Figure
calculations run offline; simulation seeds are fixed below.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "analysis"))
import analyze as A  # noqa: E402

OUT = ROOT / "analysis" / "figures"
ARMS = ("D", "P_nov", "P_adv")
POLES = ("high", "low")
FIELDS = ("overall", "scaffolding", "productive_struggle",
          "assistance_calibration", "elicitation")

# Display labels for the configuration fields.
SHORT = {"overall": "composite", "scaffolding": "scaffolding",
         "productive_struggle": "productive\nstruggle",
         "assistance_calibration": "assistance\ncalibration",
         "elicitation": "elicitation"}

SCALE_MIN, SCALE_MAX = 1.0, 5.0
EPS = 1e-9


# --------------------------------------------------------------------------
# raw records
# --------------------------------------------------------------------------
def _jsonl(path: Path):
    with open(path) as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


STIM = {d["stimulus_id"]: d for d in _jsonl(ROOT / "corpus/stimuli.jsonl")}
UNIT = {(u["stimulus_id"], u["arm"], u["pole"]): u
        for u in _jsonl(ROOT / "results/per_unit.jsonl")}
REP: dict[tuple, dict] = defaultdict(dict)
for _r in _jsonl(ROOT / "results/per_rep_scores.jsonl"):
    REP[(_r["stimulus_id"], _r["arm"], _r["pole"])][_r["rep"]] = _r["scores"]

WEAK = sorted(s for s, d in STIM.items() if d["competence_label"] == "weak")
STRONG = sorted(s for s, d in STIM.items() if d["competence_label"] == "strong")

SUMMARY = json.loads((ROOT / "analysis/out/summary.json").read_text())
DIAG = json.loads((ROOT / "analysis/out/diagnostics.json").read_text())


def score(sid: str, arm: str, pole: str, field: str = "overall") -> float:
    u = UNIT[(sid, arm, pole)]
    return u["overall_mean"] if field == "overall" else u[f"{field}_mean"]


# --------------------------------------------------------------------------
# clustering
# --------------------------------------------------------------------------
def cluster_means(sids, fn) -> np.ndarray:
    """Average within source tutoring run, the registered inference unit.

    Stimuli from one run are not independent, so every estimand is averaged
    within run first and all tests and intervals run on those means.
    """
    g = defaultdict(list)
    for s in sids:
        g[STIM[s]["source_run"]].append(float(fn(s)))
    return np.array([float(np.mean(g[k])) for k in sorted(g)])


def limbs(field: str, sids=None):
    """PAG and its two pole terms, as source-run means.

        PAG_s = D_s(P_nov) - D_s(P_adv) = a_L,s - a_H,s
        a_j,s = S_s(R_j | P_adv) - S_s(R_j | P_nov)

    Both a_j are signed shifts under the advanced profile, and on this data
    both are negative: the advanced profile scores both poles lower.  The PAG is
    the gap between them and not an opposition between them, which is why the
    figure plots them on a common axis instead of as up-and-down bars.
    """
    sids = WEAK if sids is None else sids
    aH = cluster_means(sids, lambda s: score(s, "P_adv", "high", field)
                       - score(s, "P_nov", "high", field))
    aL = cluster_means(sids, lambda s: score(s, "P_adv", "low", field)
                       - score(s, "P_nov", "low", field))
    return aL - aH, aH, aL


def n_at_bound(arm: str, pole: str, field: str = "overall", sids=None) -> int:
    """Units resting exactly on the bound this pole runs into."""
    sids = WEAK if sids is None else sids
    bound = SCALE_MAX if pole == "high" else SCALE_MIN
    return sum(1 for s in sids if abs(score(s, arm, pole, field) - bound) < EPS)


def n_pinned_all_arms(pole: str, field: str = "overall", sids=None) -> int:
    sids = WEAK if sids is None else sids
    bound = SCALE_MAX if pole == "high" else SCALE_MIN
    return sum(1 for s in sids
               if all(abs(score(s, a, pole, field) - bound) < EPS for a in ARMS))


# --------------------------------------------------------------------------
# inference, with the honesty flags the figures need
# --------------------------------------------------------------------------
def report(v: np.ndarray) -> dict:
    """``analyze.wilcoxon_report`` plus what the p-value is *able* to say.

    A two-sided exact signed-rank test on k nonzero clusters cannot return a
    p below 2/2**k.  Where that floor exceeds alpha the test could not have
    rejected under any data, so its p-value carries no evidence and the figures
    must not print it as though it did: fig2's residual (k=5, floor 0.0625) was
    shipped with "p=0.625" set beside two significant p-values.
    """
    w = dict(A.wilcoxon_report(v))
    k = int(np.sum(np.abs(np.asarray(v, dtype=float)) > A.ZERO_TOL))
    w["k_nonzero"] = k
    w["floor"] = 2.0 / (2 ** k) if k else 1.0
    w["can_reach_alpha"] = w["floor"] <= 0.05
    w["at_floor"] = abs(w["wilcoxon_p"] - w["floor"]) < 1e-12
    return w


def censoring_null(field: str = "productive_struggle", sids=None) -> dict:
    """Impose zero differential preference by hand and see what censoring alone
    manufactures.

    For each stimulus take its own observed high-pole shift a_H,s, apply the
    identical shift to each of its three integer low-pole ratings under P_nov,
    clip to the rating scale, and re-average.  ``round_then_clip`` additionally
    rounds to the integers the judge actually emits.  ``full_clip_ceiling`` is
    what the construction yields if the low limb clips completely (a_L == 0),
    where the identity collapses to PAG == -a_H.

    Mirrors ``diagnostics.censoring_null_model``; ``selftest`` asserts equality.
    """
    sids = WEAK if sids is None else sids
    obs, aH, _ = limbs(field, sids)

    def _sim(round_first: bool):
        low = {}
        for s in sids:
            shift = score(s, "P_adv", "high", field) - score(s, "P_nov", "high", field)
            base = [REP[(s, "P_nov", "low")][r][field] for r in range(3)]
            moved = [b + shift for b in base]
            if round_first:
                moved = [float(np.round(m)) for m in moved]
            low[s] = float(np.mean([min(SCALE_MAX, max(SCALE_MIN, m)) for m in moved]))
        return cluster_means(
            sids,
            lambda s: (score(s, "P_nov", "high", field) - score(s, "P_nov", "low", field))
            - (score(s, "P_adv", "high", field) - low[s]))

    clip, rtc = _sim(False), _sim(True)
    return {
        "observed": report(obs),
        "clip": report(clip),
        "round_then_clip": report(rtc),
        "residual": report(obs - clip),
        "share_clip": float(clip.mean() / obs.mean()),
        "share_round": float(rtc.mean() / obs.mean()),
        "full_clip_ceiling": float(-aH.mean()),
        "share_ceiling": float(-aH.mean() / obs.mean()),
    }


# --------------------------------------------------------------------------
# power
# --------------------------------------------------------------------------
POWER_SEED, POWER_NSIM = 4242, 6000
POWER_SHIFTS = (0.0, 0.10, 0.15, 0.20, 0.26, 0.30, 0.3534, 0.38, 0.40,
                0.42, 0.45, 0.50, 0.55, 0.60, 0.70)


def primary_clusters() -> np.ndarray:
    return cluster_means(
        WEAK,
        lambda s: (score(s, "P_nov", "high") - score(s, "P_nov", "low"))
        - (score(s, "P_adv", "high") - score(s, "P_adv", "low")))


def _p_signrank(v: np.ndarray) -> float:
    from scipy import stats
    nz = v[np.abs(v) > A.ZERO_TOL]
    if len(nz) == 0:
        return 1.0
    r = stats.rankdata(np.round(np.abs(nz), 12), method="average")
    d = np.rint(2 * r).astype(int)
    tot, obs = int(d.sum()), int(d[nz > 0].sum())
    tail = min(obs, tot - obs)
    cnt = {0: 1}
    for rk in d:
        up = dict(cnt)
        for st, nw in cnt.items():
            up[st + int(rk)] = up.get(st + int(rk), 0) + nw
        cnt = up
    return min(1.0, 2 * sum(n for st, n in cnt.items() if st <= tail) / (2 ** len(nz)))


def power_curve(clusters: np.ndarray | None = None):
    """Power of the registered test against a location shift, by nonparametric
    bootstrap of the observed centred cluster distribution.

    Centring is on the MEAN, so at shift zero the resampled distribution is
    asymmetric and the signed-rank null (symmetry about zero) is false there.
    The rejection rate at zero is therefore power against a nonzero pseudomedian
    and not the test's size; ``analysis/simulations.py`` puts the size at 0.049
    under a DGP that does satisfy the null.  The figure marks that point
    separately instead of letting it sit on the curve.
    """
    clusters = primary_clusters() if clusters is None else clusters
    rng = np.random.default_rng(POWER_SEED)
    centred = clusters - clusters.mean()
    shifts = np.array(POWER_SHIFTS)
    pw = np.array([
        sum(_p_signrank(rng.choice(centred, size=len(centred), replace=True) + sh) < 0.05
            for _ in range(POWER_NSIM)) / POWER_NSIM
        for sh in shifts])
    return shifts, pw


def power_crossing(shifts, pw, target: float = 0.80):
    """The bracket around the ``target``-power shift.

    The curve is a step function, because the endpoint lives on a sparse
    rational lattice, so there is no smooth crossing to quote.  The shipped fig1 drew a
    single +-0.42 band and its caption called that "the range where power is
    below 80%", which is false at the band's own edge: power there is 0.93.
    Returning the bracket forces the figure to draw what the simulation supports.
    """
    below = shifts[pw < target]
    above = shifts[pw >= target]
    lo = float(below.max()) if len(below) else float(shifts.min())
    hi = float(above[above > lo].min()) if len(above[above > lo]) else float(shifts.max())
    return lo, hi


# --------------------------------------------------------------------------
def selftest() -> None:
    """Re-derive every figure headline against the released estimator output."""
    def close(a, b, tol=1e-9, what=""):
        if abs(float(a) - float(b)) > tol:
            raise AssertionError(f"{what}: {a!r} != {b!r}")

    prim = report(primary_clusters())
    ref = SUMMARY["primary_PAG_weak"]
    close(prim["mean"], ref["mean"], what="PAG_weak mean")
    close(prim["ci95_bca"][0], ref["ci95_bca"][0], 1e-9, "PAG_weak BCa lo")
    close(prim["ci95_bca"][1], ref["ci95_bca"][1], 1e-9, "PAG_weak BCa hi")
    close(prim["wilcoxon_p"], ref["wilcoxon_p"], 1e-12, "PAG_weak p")
    assert prim["k_nonzero"] == ref["n_nonzero"], "nonzero cluster count"

    # the four-cell table fig1 draws
    for arm in ARMS:
        for stratum, sids in (("weak", WEAK), ("strong", STRONG)):
            got = cluster_means(sids, lambda s, a=arm: score(s, a, "high") - score(s, a, "low"))
            close(got.mean(), SUMMARY["four_cell_table"][f"delta({arm},{stratum})"]["mean"],
                  1e-9, f"delta({arm},{stratum})")

    # the per-field limbs fig2b draws
    pf = DIAG["POSTHOC_per_field_decomposition"]
    for f in FIELDS:
        pag, aH, aL = limbs(f)
        close(pag.mean(), pf[f]["weak"]["PAG"]["mean"], 1e-9, f"PAG {f}")
        close(aH.mean(), pf[f]["weak"]["a_high"]["mean"], 1e-9, f"a_H {f}")
        close(aL.mean(), pf[f]["weak"]["a_low"]["mean"], 1e-9, f"a_L {f}")
        assert n_pinned_all_arms("low", f) == \
            pf[f]["weak"]["n_stimuli_low_pole_floored_all_arms"], f"floored {f}"

    # the null model fig2c draws
    cn = censoring_null()
    ref = DIAG["POSTHOC_censoring_null_model"]
    close(cn["observed"]["mean"], ref["observed_PAG"]["mean"], 1e-9, "observed PAG")
    close(cn["clip"]["mean"], ref["clip"]["null_model_PAG"]["mean"], 1e-9, "clip null")
    close(cn["round_then_clip"]["mean"],
          ref["round_then_clip"]["null_model_PAG"]["mean"], 1e-9, "round-then-clip null")
    close(cn["residual"]["mean"], ref["clip"]["residual"]["mean"], 1e-9, "residual")
    close(cn["full_clip_ceiling"], ref["full_clip_ceiling"]["neg_a_high"], 1e-9, "ceiling")
    assert not cn["residual"]["can_reach_alpha"], "residual floor must exceed alpha"

    print(f"_data.selftest: OK  ({len(UNIT)} units, {len(STIM)} stimuli, "
          f"{len(WEAK)} weak / {len(STRONG)} strong)")


if __name__ == "__main__":
    selftest()
