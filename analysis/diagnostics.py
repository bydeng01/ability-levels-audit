#!/usr/bin/env python3
"""Registered diagnostics that the frozen estimator does not emit, plus the
post-hoc disclosures the post-run audit requires.

Why this is a separate file from analyze.py
-------------------------------------------
`analysis/analyze.py` is a frozen input: its sha256 is bound into `contract_sha256`,
recorded in `results/plan.json` under the freeze tag, and rechecked at analysis time.
Editing it after a judge score exists trips the run's own gates and invalidates the
provenance chain. But Amendment A6.4 registers two outputs it never computes:

  (a) "Per arm and pole, the fraction of units at `overall == 5.000` and at `== 1.000`,
      and the same for the four sub-scores."
  (b) The 165 D-arm real-pole calls are byte-identical repeats of published
      companion-study calls, so "their agreement with the released 3-rep means is
      reported as a test-retest check on the frozen instrument".

and PREREGISTRATION §6.5 registers the realised BCa half-width, which `summary.json`
has no key for. This script emits those without touching the frozen estimator.

It is deliberately not a frozen input and not part of `contract_sha256`: it computes no
registered estimand, and every number it prints is a deterministic function of the
already-promoted results. Re-running it can never change a reported estimate.

Integrity: it calls `analyze.load()`, so it inherits that function's gates unchanged:
promoted-set completeness, the exact 55x3x2 grid, the stimuli-unchanged check, the
analysis-code/prereg digest check, and the committed-`plan.json` anchor. Diagnostics
therefore cannot be produced from a tampered, incomplete or mock run (without
`--allow-mock`), and they provably describe the same promoted set `analyze.py` read.

Sections are labelled by provenance. "REGISTERED" outputs are named in the
pre-registration (A6.4, §6.5). "POST-HOC" outputs are disclosures required by
`protocol/AUDIT-2026-08-10-post-run-interpretation.md`; they are descriptive functions
of the frozen promoted scores, they are not registered, and they must be labelled as
exploratory wherever they appear in the paper.

Usage:
    python3 analysis/diagnostics.py                    # after a promoted live run
    python3 analysis/diagnostics.py --allow-mock       # pipeline rehearsal only
    python3 analysis/diagnostics.py --out results/diagnostics.json
    SRC_RESULTS=/path/to/conv-vs-ped-tutor/results python3 analysis/diagnostics.py

The test-retest section needs the companion study's released per-turn scores. It is
skipped (not failed) when they are not reachable, so the registered ceiling/floor table
is still produced on a clone without the source repository.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))

import analyze as A  # noqa: E402  the frozen estimator, imported READ-ONLY

SUB_FIELDS = A.SUB_FIELDS
FIELDS = ("overall",) + SUB_FIELDS
ARMS = A.ARMS
POLES = ("high", "low")

# The companion study's released per-turn pedagogy scores (same judge, same instrument,
# temperature omitted, max_tokens 512, 3 reps). Overridable for a clone.
DEFAULT_SRC_RESULTS = Path(
    os.environ.get("SRC_RESULTS")
    or (os.environ.get("SRC_LOGS") and str(Path(os.environ["SRC_LOGS"]).parent / "results"))
    or "../conv-vs-ped-tutor/results")
SRC_SPLITS = ("ablation", "confirmatory", "confirmatory_gpt", "confirmatory_gemini")

EPS = 1e-9
ALPHA = 0.05


def _at(x, target) -> bool:
    return x is not None and abs(x - target) < EPS


def _hodges_lehmann(v: np.ndarray) -> float:
    """The pseudomedian (median of Walsh averages): the location parameter the exact
    signed-rank test actually locates. The frozen estimator reports a mean next to that
    test's p-value; the two are different estimands and on this data they differ, so
    every mean this script emits carries its Hodges-Lehmann partner."""
    v = np.asarray(v, dtype=float)
    if len(v) == 0:
        return float("nan")
    walsh = [(v[i] + v[j]) / 2.0 for i in range(len(v)) for j in range(i, len(v))]
    return float(np.median(walsh))


def _report(v: np.ndarray) -> dict:
    """A.wilcoxon_report plus the estimand the test targets and the two small-k failure
    modes of the exact conditional test."""
    rep = A.wilcoxon_report(v)
    rep["hodges_lehmann"] = _hodges_lehmann(v)
    k = rep["n_nonzero"]
    rep["attainable_floor"] = 2.0 / (2 ** k) if k else None
    rep["at_exact_test_floor"] = bool(
        k and abs(rep["wilcoxon_p"] - 2.0 / (2 ** k)) < 1e-12)
    rep["can_reach_alpha"] = bool(k and 2.0 / (2 ** k) <= ALPHA)
    return rep


def _unit_index(units) -> dict:
    return {(u["stimulus_id"], u["arm"], u["pole"]): u for u in units}


def _cluster_means(stimuli, sids, value_of) -> np.ndarray:
    """Mean a stimulus-level quantity within source run — the §6 inference unit."""
    grouped = defaultdict(list)
    for sid in sids:
        v = value_of(sid)
        if v is not None:
            grouped[stimuli[sid]["source_run"]].append(float(v))
    return np.array([np.mean(grouped[r]) for r in sorted(grouped)], dtype=float)


# ------------------------------------------------------------------ REGISTERED: A6.4(a)
def ceiling_floor_table(units) -> dict:
    """A6.4: fraction of units at exactly 5.000 and exactly 1.000, per arm x pole,
    for `overall` and each of the four rubric sub-scores.

    This is the diagnostic that makes A6's censoring argument checkable after the run,
    and it is what identifies a per-field endpoint whose low pole cannot move.
    """
    out = {}
    for field in FIELDS:
        key = f"{field}_mean" if field != "overall" else "overall_mean"
        per_cell = {}
        for arm in ARMS:
            for pole in POLES:
                vals = [u[key] for u in units if u["arm"] == arm and u["pole"] == pole]
                vals = [v for v in vals if v is not None]
                n = len(vals)
                per_cell[f"{arm}|{pole}"] = {
                    "n": n,
                    "mean": float(np.mean(vals)) if n else None,
                    "n_at_5": sum(1 for v in vals if _at(v, 5.0)),
                    "n_at_1": sum(1 for v in vals if _at(v, 1.0)),
                    "frac_at_5": (sum(1 for v in vals if _at(v, 5.0)) / n) if n else None,
                    "frac_at_1": (sum(1 for v in vals if _at(v, 1.0)) / n) if n else None,
                }
        out[field] = per_cell
    return out


def pinned_in_every_arm(units, stimuli) -> dict:
    """Stimuli whose pole is pinned at the same extreme in all three arms.

    Where a pole is pinned in every arm it contributes exactly zero to that pole's
    profile contrast, so the difference-of-differences degenerates to the other pole's
    one-sided effect. Reported per stratum because the primary endpoint is weak-only.
    """
    U = _unit_index(units)
    out = {}
    for field in FIELDS:
        key = f"{field}_mean" if field != "overall" else "overall_mean"
        cell = {}
        for stratum in ("weak", "strong"):
            sids = [s for s, st in stimuli.items() if st["competence_label"] == stratum]
            for pole, extreme in (("high", 5.0), ("low", 1.0)):
                pinned = [s for s in sids
                          if all(_at(U[(s, a, pole)][key], extreme) for a in ARMS)]
                cell[f"{pole}@{extreme:g}"] = {"n_pinned": len(pinned),
                                               "n_stimuli": len(sids),
                                               "stimulus_ids": sorted(pinned)}
            out.setdefault(field, {})[stratum] = cell.copy()
            cell.clear()
    return out


# ------------------------------------------------------------------ REGISTERED: A6.4(b)
def _load_companion_scores(src_results: Path):
    lut = {}
    for split in SRC_SPLITS:
        p = src_results / split / "pedagogy_detail.json"
        if not p.is_file():
            return None, f"missing {p}"
        blob = json.loads(p.read_text())
        for run in blob.get("runs", []):
            for turn in run.get("turns", []):
                lut[(run["run_id"], turn["problem_id"], turn["turn_index"])] = turn
    return lut, None


def test_retest(units, stimuli, src_results: Path) -> dict:
    """A6.4: the D-arm call on each stimulus's REAL pole is a byte-identical repeat of a
    call the companion study already made and published. Agreement with its released
    3-rep mean is a test-retest check on the frozen instrument and direct evidence on
    whether the judge still behaves as it did when the corpus was rated.
    """
    lut, err = _load_companion_scores(src_results)
    if lut is None:
        return {"skipped": True, "reason": err,
                "note": "set $SRC_RESULTS to the companion study's results/ directory"}
    U = _unit_index(units)
    rows, misses = [], []
    for sid, st in sorted(stimuli.items()):
        pole = st["real_turn_pole"]
        prior = lut.get((st["source_run"], st["problem_id"], st["turn_index"]))
        if prior is None:
            misses.append(sid)
            continue
        now = U[(sid, "D", pole)]
        rows.append({"stimulus_id": sid, "pole": pole,
                     "now": now["overall_mean"], "prior": prior["overall_mean"],
                     "now_sub": {f: now[f"{f}_mean"] for f in SUB_FIELDS},
                     "prior_sub": {f: prior.get(f"{f}_mean") for f in SUB_FIELDS}})
    if not rows:
        return {"skipped": True, "reason": "no stimulus joined the companion scores"}
    now = np.array([r["now"] for r in rows], dtype=float)
    prior = np.array([r["prior"] for r in rows], dtype=float)
    sub_r = {}
    for f in SUB_FIELDS:
        a = np.array([r["now_sub"][f] for r in rows], dtype=float)
        b = np.array([r["prior_sub"][f] for r in rows
                      if r["prior_sub"][f] is not None], dtype=float)
        if len(a) == len(b) and len(a) > 1 and a.std() > 0 and b.std() > 0:
            sub_r[f] = float(np.corrcoef(a, b)[0, 1])
    return {
        "skipped": False,
        "n_stimuli": len(rows), "n_calls": len(rows) * 3, "lookup_misses": misses,
        "mean_now": float(now.mean()), "mean_prior": float(prior.mean()),
        "pearson_r": float(np.corrcoef(now, prior)[0, 1]),
        "mean_abs_diff": float(np.abs(now - prior).mean()),
        "max_abs_diff": float(np.abs(now - prior).max()),
        "n_exactly_equal": int(np.sum(np.abs(now - prior) < EPS)),
        "sub_score_pearson_r": sub_r,
        "interpretation": "high agreement = the frozen instrument still behaves as it "
                          "did when the companion corpus was rated; this is the only "
                          "direct check on judge drift available to this study",
    }


# ------------------------------------------------------------------ REGISTERED: §6.5
def interval_half_widths(summary: dict) -> dict:
    """§6.5 registers the realised BCa interval AND its half-width as reported outputs.
    `summary.json` records the interval but has no half-width key. Also flags intervals
    whose limit is numerically zero but prints as nonzero, and rows where the CI and the
    signed-rank p disagree (the CI estimates a magnitude-weighted MEAN, the p tests
    RANK/SIGN location, so the two can legitimately diverge)."""
    out, disagreements, near_zero = {}, [], []

    def walk(node, path):
        if isinstance(node, dict):
            ci = node.get("ci95_bca")
            if isinstance(ci, list) and len(ci) == 2:
                lo, hi = float(ci[0]), float(ci[1])
                out[path] = {"ci95_bca": [lo, hi],
                             "half_width": (hi - lo) / 2.0,
                             "excludes_zero": (lo > 0) or (hi < 0)}
                p = node.get("wilcoxon_p")
                if p is not None and ((lo > 0) or (hi < 0)) and p > 0.05:
                    disagreements.append({"path": path, "ci95_bca": [lo, hi],
                                          "wilcoxon_p": p})
                for limit in (lo, hi):
                    if limit != 0.0 and abs(limit) < 1e-9:
                        near_zero.append({"path": path, "limit": limit})
            for k, v in node.items():
                walk(v, f"{path}.{k}" if path else k)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")

    walk(summary, "")
    return {"intervals": out,
            "ci_p_disagreements": disagreements,
            "numerically_zero_limits": near_zero,
            "note": "a limit like 2.2e-17 is numerically zero and must be printed as "
                    "0.000; its zero-exclusion is bootstrap-seed dependent"}


# ------------------------------------------------------------------ POST-HOC
def per_field_decomposition(units, stimuli) -> dict:
    """POST-HOC (not registered). For every field, split the per-field PAG into its two
    limbs and report the identifiable subset.

        PAG = a_L - a_H,  a_X = S_X(P_adv) - S_X(P_nov)

    Where a pole is pinned at its extreme in every arm, that limb is identically zero
    and PAG degenerates into the other pole's one-sided severity effect. Reporting PAG
    without a_H and a_L invites reading a censored one-pole effect as anchoring.
    """
    U = _unit_index(units)
    out = {}
    for field in FIELDS:
        key = f"{field}_mean" if field != "overall" else "overall_mean"

        def val(sid, arm, pole, key=key):
            return U[(sid, arm, pole)][key]

        cell = {}
        for stratum in ("weak", "strong"):
            sids = [s for s, st in stimuli.items() if st["competence_label"] == stratum]
            def a_of(pole, sids=sids, val=val):
                return _cluster_means(stimuli, sids,
                                      lambda s: val(s, "P_adv", pole) - val(s, "P_nov", pole))
            def pag_of(sids, val=val):
                return _cluster_means(
                    stimuli, sids,
                    lambda s: (val(s, "P_nov", "high") - val(s, "P_nov", "low"))
                            - (val(s, "P_adv", "high") - val(s, "P_adv", "low")))
            aH, aL, pag = a_of("high"), a_of("low"), pag_of(sids)
            floored = [s for s in sids if all(_at(val(s, a, "low"), 1.0) for a in ARMS)]
            free = [s for s in sids if s not in floored]
            entry = {
                "PAG": _report(pag),
                "a_high": _report(aH),
                "a_low": _report(aL),
                # Two different quantities, routinely confused. The first is the high
                # limb's share of total absolute pole movement and is bounded by 1; the
                # second is its share of the gap, which exceeds 1 whenever a_L and a_H
                # share a sign, because a_L then offsets part of the high-pole term.
                "abs_a_high_share_of_limbs": (
                    float(abs(aH.mean()) / (abs(aH.mean()) + abs(aL.mean())))
                    if (abs(aH.mean()) + abs(aL.mean())) > 0 else None),
                "neg_a_high_share_of_PAG": (
                    float(-aH.mean() / pag.mean()) if abs(pag.mean()) > EPS else None),
                "n_stimuli_low_pole_floored_all_arms": len(floored),
                "n_stimuli": len(sids),
                "n_source_runs_in_both_subsets": len(
                    {stimuli[s]["source_run"] for s in floored}
                    & {stimuli[s]["source_run"] for s in free}),
            }
            if floored:
                entry["PAG_floored_subset"] = _report(pag_of(floored))
            if free:
                entry["PAG_identifiable_subset"] = _report(pag_of(free))
            cell[stratum] = entry
        out[field] = cell
    return out


def censoring_null_model(units, stimuli, reps_path: Path, field="productive_struggle") -> dict:
    """POST-HOC. The floor-censoring construction reported in the manuscript, moved here
    from analysis/figures/fig2.py so that it has a producer outside a plotting script and
    so that the exact-test-floor census below can see its p-values.

    Construction: take each stimulus's OBSERVED high-pole shift a_H, apply that identical
    shift to each of its three integer low-pole ratings under P_nov, clip to [1,5], and
    re-average. It is not a data-generating process: it keeps the observed high limb in
    both arms and counterfactuals only the low limb, so it imposes the common-shift
    hypothesis by construction and then measures what censoring alone reproduces under it.
    Report it as 'reproduced under this construction', never as an attribution or a bound.

    Two things the manuscript's single number hides, both emitted here:
      * `residual` is algebraically a_L(observed) - a_L(simulated). It is the clip model's
        low-pole prediction error, not a function of any latent contrast, so it bounds
        nothing.
      * The clip is applied to a continuous shifted value. The judge emits integers, so
        `round_then_clip` is at least as defensible and gives a smaller share. Quote the
        range rather than the larger endpoint.
    """
    if not reps_path.is_file():
        return {"skipped": True, "reason": f"missing {reps_path}"}
    U = _unit_index(units)
    rep_of = defaultdict(dict)
    for line in open(reps_path):
        r = json.loads(line)
        rep_of[(r["stimulus_id"], r["arm"], r["pole"])][r["rep"]] = r["scores"]
    key = f"{field}_mean" if field != "overall" else "overall_mean"
    sids = [s for s, st in stimuli.items() if st["competence_label"] == "weak"]

    def val(sid, arm, pole):
        return U[(sid, arm, pole)][key]

    def sim_low(sid, integerise):
        shift = val(sid, "P_adv", "high") - val(sid, "P_nov", "high")
        base = [rep_of[(sid, "P_nov", "low")][r][field] for r in sorted(rep_of[(sid, "P_nov", "low")])]
        moved = [b + shift for b in base]
        if integerise:
            moved = [round(m) for m in moved]
        return float(np.mean([min(5.0, max(1.0, m)) for m in moved]))

    def pag_with(low_of):
        return _cluster_means(
            stimuli, sids,
            lambda s: (val(s, "P_nov", "high") - val(s, "P_nov", "low"))
                    - (val(s, "P_adv", "high") - low_of(s)))

    obs = pag_with(lambda s: val(s, "P_adv", "low"))
    out = {"field": field, "stratum": "weak", "observed_PAG": _report(obs)}
    for name, integerise in (("clip", False), ("round_then_clip", True)):
        sim = pag_with(lambda s, i=integerise: sim_low(s, i))
        out[name] = {
            "null_model_PAG": _report(sim),
            "residual": _report(obs - sim),
            "share_of_observed_reproduced": (
                float(sim.mean() / obs.mean()) if abs(obs.mean()) > EPS else None),
        }
    aH = _cluster_means(stimuli, sids,
                        lambda s: val(s, "P_adv", "high") - val(s, "P_nov", "high"))
    out["full_clip_ceiling"] = {
        "neg_a_high": float(-aH.mean()),
        "share_of_observed": (float(-aH.mean() / obs.mean())
                              if abs(obs.mean()) > EPS else None),
        "note": "what a floor-censoring model manufactures if the low limb clips "
                "completely (a_L == 0); the reported share sits below this, so "
                "censoring alone can account for the whole observed gap and more",
    }
    return out


def rubric_collinearity(reps_path: Path) -> dict:
    """POST-HOC. How separable are the five rubric fields as the judge actually emits
    them? If the sub-scores are near-collinear, 'anchoring on field X but not on
    overall' is not a coherent claim about the instrument."""
    if not reps_path.is_file():
        return {"skipped": True, "reason": f"missing {reps_path}"}
    scores = [json.loads(l)["scores"] for l in open(reps_path) if l.strip()]
    scores = [s for s in scores if s and all(s.get(f) is not None for f in FIELDS)]
    if len(scores) < 3:
        return {"skipped": True, "reason": "too few fully-parsed reps"}
    cols = {f: np.array([s[f] for s in scores], dtype=float) for f in FIELDS}
    pair_r, exact = {}, {}
    names = list(FIELDS)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if cols[a].std() > 0 and cols[b].std() > 0:
                pair_r[f"{a} x {b}"] = float(np.corrcoef(cols[a], cols[b])[0, 1])
            exact[f"{a} == {b}"] = int(np.sum(cols[a] == cols[b]))
    X = np.column_stack([cols[f] for f in SUB_FIELDS] + [np.ones(len(scores))])
    y = cols["overall"]
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    pred = X @ beta
    ss_res = float(((y - pred) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    return {
        "n_reps": len(scores),
        "pairwise_pearson_r": pair_r,
        "n_reps_fields_identical": exact,
        "overall_on_subscores": {
            "r_squared": (1 - ss_res / ss_tot) if ss_tot > 0 else None,
            "weights": {f: float(w) for f, w in zip(SUB_FIELDS, beta[:-1])},
            "intercept": float(beta[-1]),
        },
        "note": "near-collinear sub-scores mean the per-field ranking is not "
                "statistically separable at the top",
    }


def per_pole_movement_from_D(units, stimuli) -> dict:
    """POST-HOC and UNREGISTERED (§6.3 registers movement in Delta, not per pole).
    Must be labelled exploratory wherever reported."""
    U = _unit_index(units)
    out = {}
    for stratum in ("weak", "strong"):
        sids = [s for s, st in stimuli.items() if st["competence_label"] == stratum]
        for arm in ("P_nov", "P_adv"):
            for pole in POLES:
                v = _cluster_means(
                    stimuli, sids,
                    lambda s, a=arm, p=pole: U[(s, a, p)]["overall_mean"]
                                           - U[(s, "D", p)]["overall_mean"])
                rep = A.wilcoxon_report(v)
                k = rep["n_nonzero"]
                rep["at_exact_test_floor"] = bool(
                    k > 0 and abs(rep["wilcoxon_p"] - 2.0 / (2 ** k)) < 1e-12)
                out[f"S(R_{pole}|{arm}) - S(R_{pole}|D), {stratum}"] = rep
    return out


def exact_test_floors(*sections: dict) -> dict:
    """POST-HOC. Two small-k failure modes of the exact conditional test, swept over EVERY
    test this repository reports: the frozen estimator's summary and the post-hoc
    sections alike. Sweeping only the summary is what let the second list below go
    unreported: the tests that carry the manufactured-effect argument are all post-hoc.

    at_their_exact_floor: p == 2/2**k, the smallest value the test could have returned.
        Carries only 'all k nonzero clusters agreed in sign'; magnitude is discarded, so
        it cannot be read as strength of evidence.
    cannot_reach_alpha: 2/2**k > ALPHA, i.e. k <= 4 at 5%, and in fact k <= 5, since
        2/2**5 = 0.0625.
        Such a test cannot reject under any configuration of the data. A
        non-significant result from one is no evidence of a null at all, and it
        must never be described as 'not distinguishable from
        zero' or contrasted with a significant result as though the comparison were
        informative.
    """
    at_floor, unreachable = {}, {}

    def walk(node, path):
        if isinstance(node, dict):
            p, k = node.get("wilcoxon_p"), node.get("n_nonzero")
            if p is not None and k:
                floor = 2.0 / (2 ** k)
                rec = {"wilcoxon_p": p, "n_nonzero": k, "attainable_floor": floor,
                       "n_clusters": node.get("n")}
                if abs(p - floor) < 1e-12:
                    at_floor[path] = rec
                if floor > ALPHA:
                    unreachable[path] = rec
            for kk, v in node.items():
                walk(v, f"{path}.{kk}" if path else kk)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")

    for section in sections:
        walk(section, "")
    return {"alpha": ALPHA,
            "tests_at_their_exact_floor": at_floor,
            "tests_that_cannot_reach_alpha": unreachable,
            "note": "p == 2/2**k means every nonzero cluster agreed in sign and nothing "
                    "more; sign, Pratt and permutation tests return the identical value"}


# ------------------------------------------------------------------ report
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--allow-mock", action="store_true",
                    help="permit a non-reportable (mock) promoted set; never publishable")
    ap.add_argument("--src-results", default=str(DEFAULT_SRC_RESULTS),
                    help="companion study results/ dir for the test-retest (default %(default)s)")
    ap.add_argument("--out", default=str(ROOT / "analysis/out/diagnostics.json"),
                    help="JSON output path (default %(default)s)")
    args = ap.parse_args()

    # Same gates as the registered analysis: completeness, exact grid, stimuli-unchanged,
    # analysis-code/prereg digests, and the committed plan.json anchor.
    meta, units, stimuli = A.load(args.allow_mock)

    summary_path = ROOT / "analysis/out/summary.json"
    summary = json.loads(summary_path.read_text()) if summary_path.is_file() else {}

    res = {
        "provenance": {
            "backend": meta.get("backend"),
            "reportable": meta.get("reportable"),
            "contract_sha256": meta.get("contract_sha256"),
            "frozen_inputs": meta.get("frozen_inputs"),
            "summary_json_present": bool(summary),
            "emitted_by": "analysis/diagnostics.py (NOT a frozen input; computes no "
                          "registered estimand; every value is a deterministic function "
                          "of the promoted results)",
        },
        "REGISTERED_A6_4a_ceiling_floor": ceiling_floor_table(units),
        "REGISTERED_A6_4a_pinned_in_every_arm": pinned_in_every_arm(units, stimuli),
        "REGISTERED_A6_4b_test_retest": test_retest(units, stimuli, Path(args.src_results)),
        "REGISTERED_6_5_interval_half_widths": interval_half_widths(summary),
        "POSTHOC_per_field_decomposition": per_field_decomposition(units, stimuli),
        "POSTHOC_censoring_null_model": censoring_null_model(
            units, stimuli, ROOT / "results/per_rep_scores.jsonl"),
        "POSTHOC_rubric_collinearity": rubric_collinearity(ROOT / "results/per_rep_scores.jsonl"),
        "POSTHOC_per_pole_movement_from_D": per_pole_movement_from_D(units, stimuli),
    }
    # Swept last, over everything above as well as the frozen estimator's summary.
    res["POSTHOC_exact_test_floors"] = exact_test_floors(summary, res)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(res, indent=2))

    # ---- printed report ----
    print(f"diagnostics for backend={meta.get('backend')!r} "
          f"reportable={meta.get('reportable')!r}\n")

    print("REGISTERED (A6.4) — units at the scale extremes, per arm x pole")
    print(f"  {'field':24} {'arm|pole':14} {'mean':>6}  {'@5.000':>8} {'@1.000':>8}")
    for field, cells in res["REGISTERED_A6_4a_ceiling_floor"].items():
        for cell, v in cells.items():
            print(f"  {field:24} {cell:14} {v['mean']:6.3f}  "
                  f"{v['n_at_5']:3}/{v['n']:<4} {v['n_at_1']:3}/{v['n']:<4}")
    print()

    print("REGISTERED (A6.4) — poles pinned at the same extreme in ALL THREE arms (weak stratum)")
    for field, strata in res["REGISTERED_A6_4a_pinned_in_every_arm"].items():
        w = strata["weak"]
        print(f"  {field:24} low@1: {w['low@1']['n_pinned']:2}/{w['low@1']['n_stimuli']}"
              f"   high@5: {w['high@5']['n_pinned']:2}/{w['high@5']['n_stimuli']}")
    print()

    tr = res["REGISTERED_A6_4b_test_retest"]
    print("REGISTERED (A6.4) — test-retest of the frozen instrument")
    if tr.get("skipped"):
        print(f"  SKIPPED: {tr.get('reason')}")
    else:
        print(f"  {tr['n_stimuli']} stimuli / {tr['n_calls']} D-arm calls repeating published ones")
        print(f"  now {tr['mean_now']:.3f} vs prior {tr['mean_prior']:.3f} | "
              f"r={tr['pearson_r']:.3f} | mean|diff|={tr['mean_abs_diff']:.3f} | "
              f"exactly equal {tr['n_exactly_equal']}/{tr['n_stimuli']}")
        if tr.get("sub_score_pearson_r"):
            print("  sub-score r: " + ", ".join(
                f"{f}={r:.3f}" for f, r in tr["sub_score_pearson_r"].items()))
    print()

    hw = res["REGISTERED_6_5_interval_half_widths"]
    prim = hw["intervals"].get("primary_PAG_weak")
    if prim:
        print("REGISTERED (§6.5) — realised interval and half-width, primary endpoint")
        print(f"  PAG_weak BCa [{prim['ci95_bca'][0]:+.5f}, {prim['ci95_bca'][1]:+.5f}]  "
              f"half-width {prim['half_width']:.4f}")
    if hw["ci_p_disagreements"]:
        print(f"  rows where the BCa excludes zero but p>0.05 "
              f"({len(hw['ci_p_disagreements'])}): the CI estimates a magnitude-weighted "
              f"MEAN, the p tests RANK/SIGN location")
        for d in hw["ci_p_disagreements"]:
            print(f"    {d['path']}  CI [{d['ci95_bca'][0]:+.4f},{d['ci95_bca'][1]:+.4f}] "
                  f"p={d['wilcoxon_p']:.4f}")
    for z in hw["numerically_zero_limits"]:
        print(f"  numerically-zero limit to print as 0.000: {z['path']} -> {z['limit']!r}")
    print()

    print("POST-HOC (exploratory) — per-field PAG split into its two limbs, weak stratum")
    print(f"  {'field':24} {'PAG':>8} {'  (H-L)':>9} {'p':>8}   {'a_high':>8} {'a_low':>8}  "
          f"{'|aH|/limbs':>10} {'-aH/PAG':>8} {'lowPinned':>9}")
    for field, cell in res["POSTHOC_per_field_decomposition"].items():
        w = cell["weak"]
        share, gap = w["abs_a_high_share_of_limbs"], w["neg_a_high_share_of_PAG"]
        nan = float("nan")
        print(f"  {field:24} {w['PAG']['mean']:+8.4f} {w['PAG']['hodges_lehmann']:+9.4f} "
              f"{w['PAG']['wilcoxon_p']:8.4f}   "
              f"{w['a_high']['mean']:+8.4f} {w['a_low']['mean']:+8.4f}  "
              f"{(share if share is not None else nan):10.3f} "
              f"{(gap if gap is not None else nan):8.3f} "
              f"{w['n_stimuli_low_pole_floored_all_arms']:4}/{w['n_stimuli']:<4}")
    print("  |aH|/limbs is the high limb's share of TOTAL ABSOLUTE POLE MOVEMENT (<=1);")
    print("  -aH/PAG is its share of the GAP (>1 when a_L and a_H share a sign). Do not")
    print("  describe the first as a share of the gap. (H-L) is what the test locates.")
    for field, cell in res["POSTHOC_per_field_decomposition"].items():
        w = cell["weak"]
        if "PAG_floored_subset" in w and "PAG_identifiable_subset" in w:
            fl, fr = w["PAG_floored_subset"], w["PAG_identifiable_subset"]
            mark = "" if fr["can_reach_alpha"] else "  <- free-arm test CANNOT reach alpha"
            print(f"    {field:22} floored subset {fl['mean']:+.4f} (p={fl['wilcoxon_p']:.4f}, "
                  f"{fl['n']} clusters) | identifiable {fr['mean']:+.4f} "
                  f"(p={fr['wilcoxon_p']:.4f}, {fr['n']} clusters); "
                  f"{w['n_source_runs_in_both_subsets']} source runs in both{mark}")
    print()

    nm = res["POSTHOC_censoring_null_model"]
    if not nm.get("skipped"):
        print(f"POST-HOC (exploratory) — floor-censoring null model, {nm['field']}, weak stratum")
        o = nm["observed_PAG"]
        print(f"  observed PAG {o['mean']:+.4f} (H-L {o['hodges_lehmann']:+.4f}, "
              f"p={o['wilcoxon_p']:.5g})")
        for variant in ("clip", "round_then_clip"):
            v = nm[variant]
            s, r = v["null_model_PAG"], v["residual"]
            flag = "" if r["can_reach_alpha"] else "  <- residual test CANNOT reach alpha"
            print(f"  {variant:16} null {s['mean']:+.4f} (p={s['wilcoxon_p']:.5g}) "
                  f"= {100 * v['share_of_observed_reproduced']:.1f}% of observed; "
                  f"residual {r['mean']:+.4f} (p={r['wilcoxon_p']:.5g}, k={r['n_nonzero']}, "
                  f"floor {r['attainable_floor']:.4g}){flag}")
        fc = nm["full_clip_ceiling"]
        print(f"  full-clip ceiling -a_H {fc['neg_a_high']:+.4f} "
              f"= {100 * fc['share_of_observed']:.1f}% of observed")
        print("  the residual is a_L(observed) - a_L(simulated): the clip model's low-pole")
        print("  prediction error. It bounds nothing. Report 'reproduced under this")
        print("  construction', and quote the share as a range across the two variants.")
    print()

    col = res["POSTHOC_rubric_collinearity"]
    if not col.get("skipped"):
        print("POST-HOC (exploratory) — how separable are the rubric fields as emitted")
        print(f"  overall ~ 4 sub-scores: R^2={col['overall_on_subscores']['r_squared']:.4f} "
              f"weights " + " ".join(f"{f[:4]}={w:+.3f}" for f, w in
                                     col["overall_on_subscores"]["weights"].items()))
        top = sorted(col["n_reps_fields_identical"].items(), key=lambda kv: -kv[1])[:3]
        for k, v in top:
            print(f"  identical in {v}/{col['n_reps']} reps: {k}")
        print()

    ft = res["POSTHOC_exact_test_floors"]
    floors = ft["tests_at_their_exact_floor"]
    if floors:
        print("POST-HOC — tests sitting at the exact-test floor (p == 2/2^k):")
        for path, v in floors.items():
            print(f"  {path}  p={v['wilcoxon_p']:.6g} = 2/2^{v['n_nonzero']} "
                  f"({v['n_nonzero']} of {v['n_clusters']} clusters nonzero, all same sign)")
        print()
    unreachable = ft["tests_that_cannot_reach_alpha"]
    if unreachable:
        print(f"POST-HOC — tests that CANNOT REJECT at alpha={ft['alpha']} under any data "
              f"(2/2^k > alpha):")
        for path, v in unreachable.items():
            print(f"  {path}  k={v['n_nonzero']} of {v['n_clusters']} clusters nonzero, "
                  f"floor 2/2^{v['n_nonzero']}={v['attainable_floor']:.4g} > {ft['alpha']}, "
                  f"reported p={v['wilcoxon_p']:.6g}")
        print("  A non-significant result from one of these is no evidence of a null. Do")
        print("  not write 'not distinguishable from zero', and do not contrast one with a")
        print("  significant result as though the difference in significance meant anything.")
        print()

    print("POST-HOC (UNREGISTERED — label exploratory) — per-pole movement from D, weak")
    for k, v in res["POSTHOC_per_pole_movement_from_D"].items():
        if k.endswith("weak"):
            flag = "  <- at its exact floor" if v.get("at_exact_test_floor") else ""
            print(f"  {k:44} {v['mean']:+.3f}  p={v['wilcoxon_p']:.6f}  "
                  f"nz={v['n_nonzero']}/{v['n']}{flag}")

    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
