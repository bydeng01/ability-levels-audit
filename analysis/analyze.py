#!/usr/bin/env python3
"""Pre-registered analysis (PREREGISTRATION.md §6). Written and frozen BEFORE any
judge score existed; everything beyond §6 is exploratory and must be labelled so.

Inputs:  results/per_unit.jsonl (promoted, complete), corpus/stimuli.jsonl.
Outputs: analysis/out/summary.json, analysis/out/per_stimulus_deltas.csv, and a
         printed report. Refuses non-live (mock) runs unless --allow-mock.
"""
from __future__ import annotations

import argparse
import hashlib
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
# The four rubric principle sub-scores, for the §6.3 per-field decomposition.
SUB_FIELDS = ("scaffolding", "productive_struggle", "assistance_calibration",
              "elicitation")


def bca_ci(vals: np.ndarray, alpha: float = 0.05):
    vals = np.asarray(vals, dtype=float)
    if len(vals) < 2 or np.allclose(vals, vals[0]):
        return [float(vals.mean()), float(vals.mean())]
    res = stats.bootstrap((vals,), np.mean, n_resamples=N_RESAMPLES, method="BCa",
                          confidence_level=1 - alpha,
                          random_state=np.random.default_rng(BOOT_SEED))
    return [float(res.confidence_interval.low), float(res.confidence_interval.high)]


# A per-unit score is the mean of 3 integer ratings, so an exactly-zero difference
# of differences is common — but in binary floating point it lands on +/-4.44e-16
# rather than 0.0, with a sign set by rounding order alone. `vals != 0` therefore
# failed to drop true zeros and fed them to the signed-rank test as its
# smallest-magnitude (rank 1..k) differences (AUDIT-2026-08-08 B3: on
# real-shaped data this moved the primary p by .06 and the rank-biserial by .03).
# ZERO_TOL is far above that residue and far below the smallest genuine
# difference the design can produce (1/3 of a scale point).
ZERO_TOL = 1e-9


def wilcoxon_report(vals: np.ndarray) -> dict:
    """Tie-valid exact two-sided signed-rank + rank-biserial effect size.

    Zeros are dropped as registered. Average ranks handle tied absolute differences;
    dynamic programming enumerates the exact conditional sign distribution. This
    avoids SciPy's version-dependent `method="auto"` and is defined even when fewer
    than five differences are nonzero.
    """
    vals = np.asarray(vals, dtype=float)
    nz = vals[np.abs(vals) > ZERO_TOL]
    out = {"n": int(len(vals)), "n_nonzero": int(len(nz)),
           "n_zero_dropped": int(len(vals) - len(nz)),
           "mean": float(vals.mean()), "median": float(np.median(vals)),
           "ci95_bca": bca_ci(vals)}
    if len(nz) == 0:
        out.update({"wilcoxon_stat": 0.0, "wilcoxon_p": 1.0,
                    "rank_biserial": 0.0,
                    "note": "all differences are zero"})
        return out
    # The design's rational thirds can acquire last-bit differences through
    # subtraction order. Canonicalising well below the 1/3 score resolution keeps
    # mathematically tied magnitudes tied in the exact distribution.
    ranks = stats.rankdata(np.round(np.abs(nz), 12), method="average")
    doubled = np.rint(2 * ranks).astype(int)
    if not np.allclose(doubled, 2 * ranks):
        raise RuntimeError("signed-rank ties did not produce half-integer ranks")
    total = int(doubled.sum())
    observed_plus = int(doubled[nz > 0].sum())
    observed_tail = min(observed_plus, total - observed_plus)
    counts = {0: 1}
    for rank in doubled:
        updated = dict(counts)
        for subtotal, nways in counts.items():
            updated[subtotal + int(rank)] = updated.get(subtotal + int(rank), 0) + nways
        counts = updated
    lower_ways = sum(nways for subtotal, nways in counts.items()
                     if subtotal <= observed_tail)
    exact_p = min(1.0, 2 * lower_ways / (2 ** len(nz)))
    w_plus = float(ranks[nz > 0].sum())
    w_minus = float(ranks[nz < 0].sum())
    out.update({"wilcoxon_stat": min(w_plus, w_minus),
                "wilcoxon_p": exact_p,
                "wilcoxon_method": "exact conditional sign enumeration; average ranks",
                "rank_biserial": (w_plus - w_minus) / (w_plus + w_minus)})
    return out


def assert_stimuli_unchanged(meta: dict) -> None:
    """The stimuli analysed must be the stimuli scored.

    AUDIT-2026-08-08 B2. The stratum (`competence_label`) and the §6.3 provenance
    subset are read from `corpus/stimuli.jsonl` at ANALYSIS time, after the scores
    exist. Without this check, editing that file post-run silently re-cuts the
    strata while `summary.json` still reports the run's original contract hash.
    """
    recorded = (meta.get("frozen_inputs") or {}).get("stimuli_sha256")
    actual = hashlib.sha256((ROOT / "corpus/stimuli.jsonl").read_bytes()).hexdigest()
    if recorded is None:
        raise SystemExit("results/run_meta.json records no stimuli hash; refusing to "
                         "analyse an unverifiable set.")
    if recorded != actual:
        raise SystemExit(
            f"STIMULI CHANGED SINCE SCORING: run_meta.json was written against "
            f"{recorded}, corpus/stimuli.jsonl now hashes to {actual}. The strata "
            "and provenance subset would not be the ones that were scored. Refusing "
            "to analyse.")


def _validate_analysis_code_unchanged(meta: dict) -> None:
    """This script and the plan it implements must be the ones the run was frozen under.

    `frozen_inputs` binds `analyze.py` and `PREREGISTRATION.md` for every LIVE command,
    but nothing rechecked them at ANALYSIS time — so the estimator could be edited after
    the scores existed and `summary.json` would still carry the run's legitimate
    `contract_sha256` (AUDIT-2026-08-08-preflight-review-3 N2).

    That check trusted `run_meta.json`, which is untracked and hand-writable, so
    re-stamping it (and `run_state.json`, which certifies it) restored a fabricated
    result to a clean bill of health. `results/plan.json` records the same
    `frozen_inputs` and IS committed under the freeze tag, so anchoring to it terminates
    the chain in git rather than in a file the analyst can edit
    (AUDIT-2026-08-10-endpoint-sensitivity B3).
    """
    frozen = meta.get("frozen_inputs") or {}
    for field, path in (("analyze_py_sha256", ROOT / "analysis/analyze.py"),
                        ("prereg_md_sha256", ROOT / "protocol/PREREGISTRATION.md")):
        recorded = frozen.get(field)
        if recorded is None:
            raise SystemExit(
                f"results/run_meta.json records no {field}; refusing to analyse a run "
                "whose analysis code and plan are not bound.")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if recorded != actual:
            raise SystemExit(
                f"ANALYSIS CODE OR PLAN CHANGED SINCE SCORING: {path.relative_to(ROOT)} "
                f"was {recorded} at scoring time and is {actual} now. The registered "
                "analysis is not the one about to run. Refusing to analyse.")
    # Everything above trusts run_meta.json, which is untracked and hand-writable — so
    # re-stamping it (and run_state.json, which certifies it) restored a fabricated
    # result to a clean bill of health. results/plan.json records the same frozen_inputs
    # and IS committed under the freeze tag, so this is where the chain reaches git
    # (AUDIT-2026-08-10-endpoint-sensitivity B3).
    plan_path = ROOT / "results/plan.json"
    if not plan_path.exists():
        raise SystemExit(
            "results/plan.json is missing. It is the committed record of the frozen "
            "inputs and the only anchor the analyst cannot rewrite. Refusing to analyse.")
    if json.loads(plan_path.read_text()).get("frozen_inputs") != frozen:
        raise SystemExit(
            "FROZEN INPUTS DISAGREE WITH THE COMMITTED PLAN: results/run_meta.json "
            "records a different frozen-input set than results/plan.json, which is "
            "committed under the freeze tag. Either the run was scored against "
            "materials the released plan does not describe, or the run record was "
            "edited afterwards. Refusing to analyse.")


def _validate_promoted_hashes(state: dict) -> None:
    recorded = state.get("result_sha256")
    if not isinstance(recorded, dict):
        raise SystemExit("results/run_state.json has no promoted-result hash manifest")
    expected_names = {"per_rep_scores.jsonl", "per_unit.jsonl",
                      "completeness.json", "run_meta.json"}
    if set(recorded) != expected_names:
        raise SystemExit("promoted-result hash manifest has the wrong file set")
    for name, expected in recorded.items():
        path = ROOT / "results" / name
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
        if actual != expected:
            raise SystemExit(f"PROMOTED RESULT CHANGED: {name}")


def _validate_live_provenance_files(meta: dict) -> None:
    paths = {
        "cache_sha256": ROOT / "results/cache/profile_pedagogy_cache.json",
        "wire_sha256": ROOT / "results/wire/calls.jsonl",
    }
    for field, path in paths.items():
        expected = meta.get(field)
        if not isinstance(expected, str) or len(expected) != 64:
            raise SystemExit(f"reportable run_meta has no valid {field}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
        if actual != expected:
            raise SystemExit(f"LIVE PROVENANCE CHANGED: {path.relative_to(ROOT)}")


def _validate_result_grid(meta: dict, units: list[dict], stimuli: dict) -> None:
    expected = {(sid, arm, pole) for sid in stimuli
                for arm in ARMS for pole in ("high", "low")}
    seen = set()
    for i, unit in enumerate(units, 1):
        key = (unit.get("stimulus_id"), unit.get("arm"), unit.get("pole"))
        if key in seen:
            raise SystemExit(f"DUPLICATE promoted unit at row {i}: {key}")
        seen.add(key)
        if unit.get("n_valid") != 3:
            raise SystemExit(f"INCOMPLETE promoted unit at row {i}: {key}")
        if not isinstance(unit.get("overall_mean"), (int, float)):
            raise SystemExit(f"INVALID promoted score at row {i}: {key}")
    missing, extra = sorted(expected - seen), sorted(seen - expected)
    if missing or extra:
        raise SystemExit(
            f"PROMOTED RESULT GRID MISMATCH: missing={missing[:3]} extra={extra[:3]}")
    if meta.get("n_units") != len(expected):
        raise SystemExit(
            f"run_meta n_units={meta.get('n_units')} but frozen schedule has {len(expected)}")
    if meta.get("n_per_rep_rows") != len(expected) * 3:
        raise SystemExit("run_meta n_per_rep_rows does not match three reps per unit")


def load(allow_mock: bool):
    meta = json.loads((ROOT / "results/run_meta.json").read_text())
    state = json.loads((ROOT / "results/run_state.json").read_text())
    if state.get("state") != "complete":
        raise SystemExit("results are not a complete promoted set")
    if not meta.get("reportable") and not allow_mock:
        raise SystemExit(f"results backend is {meta.get('backend')!r} — NOT reportable. "
                         "Pass --allow-mock only for pipeline rehearsal output.")
    if meta.get("reportable") and not meta.get("live_provenance_ok"):
        raise SystemExit("live results lack validated cache/wire provenance")
    _validate_promoted_hashes(state)
    if meta.get("reportable"):
        _validate_live_provenance_files(meta)
    assert_stimuli_unchanged(meta)
    _validate_analysis_code_unchanged(meta)
    units = [json.loads(l) for l in open(ROOT / "results/per_unit.jsonl")]
    stimulus_rows = [json.loads(l) for l in open(ROOT / "corpus/stimuli.jsonl")]
    stimuli = {s["stimulus_id"]: s for s in stimulus_rows}
    if len(stimuli) != len(stimulus_rows):
        raise SystemExit("duplicate stimulus_id in corpus/stimuli.jsonl")
    _validate_result_grid(meta, units, stimuli)
    return meta, units, stimuli


def build_deltas(units, stimuli):
    """Per stimulus: S(pole|arm), Delta_s(arm) = S(high|arm) - S(low|arm)."""
    S = defaultdict(dict)
    SUB = defaultdict(dict)
    for u in units:
        key = (u["arm"], u["pole"])
        if key in S[u["stimulus_id"]]:
            raise SystemExit(f"duplicate result key for {u['stimulus_id']}: {key}")
        S[u["stimulus_id"]][key] = u["overall_mean"]
        SUB[u["stimulus_id"]][key] = {
            f: u.get(f"{f}_mean") for f in SUB_FIELDS}
    rows = []
    for sid, sc in sorted(S.items()):
        st = stimuli[sid]
        row = {"stimulus_id": sid, "competence": st["competence_label"],
               "source_run": st["source_run"],
               "evidence_strength": st["evidence_strength"],
               "family": st["family"], "base": st["base"],
               "all_corpus": (st.get("r_high_provenance") == "corpus"
                              and st.get("r_low_provenance") == "corpus")}
        for arm in ARMS:
            row[f"S_high_{arm}"] = sc[(arm, "high")]
            row[f"S_low_{arm}"] = sc[(arm, "low")]
            row[f"delta_{arm}"] = sc[(arm, "high")] - sc[(arm, "low")]
        row["pag"] = row["delta_P_nov"] - row["delta_P_adv"]
        # §6.3 per-field decomposition: the same PAG built from each rubric
        # sub-score instead of `overall`. None when any of the four cells the
        # field needs failed to parse in every rep of a unit.
        sub = SUB[sid]
        for f in SUB_FIELDS:
            vals = {(a, p): sub[(a, p)].get(f) for a in ("P_nov", "P_adv")
                    for p in ("high", "low")}
            if any(v is None for v in vals.values()):
                row[f"pag_{f}"] = None
            else:
                row[f"pag_{f}"] = ((vals[("P_nov", "high")] - vals[("P_nov", "low")])
                                   - (vals[("P_adv", "high")] - vals[("P_adv", "low")]))
        rows.append(row)
    return rows


def cluster_means(rows, field: str) -> np.ndarray:
    """Mean a stimulus-level estimand within each independent source run."""
    grouped = defaultdict(list)
    for row in rows:
        value = row[field]
        if value is not None:
            grouped[row["source_run"]].append(float(value))
    return np.array([np.mean(grouped[run]) for run in sorted(grouped)], dtype=float)


def analyze(rows) -> dict:
    by_strat = {s: [r for r in rows if r["competence"] == s]
                for s in ("weak", "strong")}
    out = {"n_stimuli": len(rows),
           "n_per_stratum": {k: len(v) for k, v in by_strat.items()},
           "n_source_runs_per_stratum": {
               k: len({r["source_run"] for r in v}) for k, v in by_strat.items()},
           "inference_unit": "source_run mean"}

    # 6.1 four-cell table (+ D-arm reference per stratum)
    four = {}
    for strat, rs in by_strat.items():
        for arm in ARMS:
            vals = cluster_means(rs, f"delta_{arm}")
            four[f"delta({arm},{strat})"] = {
                "mean": float(vals.mean()), "ci95_bca": bca_ci(vals),
                "n_source_runs": len(vals), "n_stimuli": len(rs)}
    out["four_cell_table"] = four

    # 6.2 primary: PAG_weak
    out["primary_PAG_weak"] = wilcoxon_report(
        cluster_means(by_strat["weak"], "pag"))

    # 6.3 secondaries
    out["secondary_PAG_strong"] = wilcoxon_report(
        cluster_means(by_strat["strong"], "pag"))
    move = {}
    for strat, rs in by_strat.items():
        for arm in ("P_nov", "P_adv"):
            field = f"movement_{arm}"
            for r in rs:
                r[field] = r[f"delta_{arm}"] - r["delta_D"]
            move[f"delta({arm})-delta(D), {strat}"] = wilcoxon_report(
                cluster_means(rs, field))
    out["secondary_movement_from_D"] = move
    pure = {}
    for strat, rs in by_strat.items():
        for pole in ("high", "low"):
            field = f"pure_{pole}"
            for r in rs:
                r[field] = r[f"S_{pole}_P_adv"] - r[f"S_{pole}_P_nov"]
            pure[f"S(R_{pole}|P_adv)-S(R_{pole}|P_nov), {strat}"] = wilcoxon_report(
                cluster_means(rs, field))
    out["secondary_pure_profile_effect"] = pure

    # 6.3b authoring robustness: the primary endpoint on stimuli with NO authored text
    allc = [r for r in rows if r["all_corpus"]]
    out["secondary_authoring_robustness"] = {
        "n_all_corpus": len(allc),
        "n_per_stratum": dict(Counter(r["competence"] for r in allc)),
        "PAG_weak_all_corpus": wilcoxon_report(
            cluster_means([r for r in allc if r["competence"] == "weak"], "pag")),
        "PAG_strong_all_corpus": wilcoxon_report(
            cluster_means([r for r in allc if r["competence"] == "strong"], "pag")),
        "rationale": "identical R_H/R_L texts are judged in all three arms, so an "
                     "additive stimulus-level authoring artifact cancels in "
                     "PAG = delta(P_nov) - delta(P_adv); this subset removes "
                     "authoring entirely and checks profile-by-register interaction",
    }

    # 6.3c per-field decomposition of the primary over the four rubric sub-scores
    per_field = {}
    for f in SUB_FIELDS:
        cell = {}
        for strat, rs in by_strat.items():
            vals = cluster_means(rs, f"pag_{f}")
            cell[strat] = (wilcoxon_report(vals) if len(vals)
                           else {"n": 0, "note": "no unit had this field parsed"})
            cell[strat]["n_stimuli_dropped_unparsed"] = sum(
                r[f"pag_{f}"] is None for r in rs)
        per_field[f] = cell
    out["secondary_per_field_decomposition"] = per_field

    # 6.4 profile influence x evidence strength
    by_run = defaultdict(list)
    for r in rows:
        by_run[r["source_run"]].append(r)
    infl = np.array([np.mean([abs(r["pag"]) for r in by_run[run]])
                     for run in sorted(by_run)])
    ev = np.array([np.mean([EV_ORD[r["evidence_strength"]] for r in by_run[run]])
                   for run in sorted(by_run)])
    if len(set(ev)) > 1:
        rho, p = stats.spearmanr(ev, infl)
        stim_ev = np.array([EV_ORD[r["evidence_strength"]] for r in rows])
        stim_infl = np.array([abs(r["pag"]) for r in rows])
        out["secondary_influence_x_evidence"] = {
            "spearman_rho": float(rho), "p": float(p), "n_source_runs": len(by_run),
            "by_level": {lv: {"n_stimuli": int((stim_ev == EV_ORD[lv]).sum()),
                              "mean_abs_pag": float(
                                  stim_infl[stim_ev == EV_ORD[lv]].mean())
                              if (stim_ev == EV_ORD[lv]).any() else None}
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

    print(f"n = {res['n_stimuli']} stimuli {res['n_per_stratum']}; independent "
          f"source runs {res['n_source_runs_per_stratum']}")
    print("\nfour-cell table (Δ = S(R_H) − S(R_L)):")
    for k, v in res["four_cell_table"].items():
        print(f"  {k:24s} {v['mean']:+.3f}  CI {v['ci95_bca'][0]:+.3f}..{v['ci95_bca'][1]:+.3f}")
    p = res["primary_PAG_weak"]
    print(f"\nPRIMARY PAG_weak: mean {p['mean']:+.3f} CI {p['ci95_bca']} "
          f"Wilcoxon p={p['wilcoxon_p']} r_rb={p['rank_biserial']}")
    s = res["secondary_PAG_strong"]
    print(f"secondary PAG_strong: mean {s['mean']:+.3f} CI {s['ci95_bca']} "
          f"p={s['wilcoxon_p']}")
    print("\nper-field decomposition of PAG (weak stratum):")
    for f, cell in res["secondary_per_field_decomposition"].items():
        w = cell["weak"]
        if w.get("n"):
            print(f"  {f:24s} mean {w['mean']:+.3f}  CI {w['ci95_bca'][0]:+.3f}.."
                  f"{w['ci95_bca'][1]:+.3f}  p={w['wilcoxon_p']}")
        else:
            print(f"  {f:24s} {w.get('note')}")
    if "secondary_influence_x_evidence" in res:
        e = res["secondary_influence_x_evidence"]
        print(f"influence×evidence: Spearman rho={e['spearman_rho']:+.3f} p={e['p']:.4f}")
    print("\nwrote analysis/out/summary.json + per_stimulus_deltas.csv")


if __name__ == "__main__":
    main()
