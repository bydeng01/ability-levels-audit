"""The pre-registered estimators produce correct numbers on synthetic data."""
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

# the repo's analysis/ dir is shadowed by the vendored `analysis` package (by
# design), so the study's own analyze.py is loaded by file path
REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "lve_analyze", REPO / "analysis/analyze.py")
AN = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(AN)

# analyze.py now binds itself and the plan to the hashes the run recorded, so a
# fixture ROOT must carry both files for the gate to have anything to check.
BOUND_SOURCES = {"analyze_py_sha256": "analysis/analyze.py",
                 "prereg_md_sha256": "protocol/PREREGISTRATION.md"}


def _refresh_hashes(tmp_path):
    names = ("per_rep_scores.jsonl", "per_unit.jsonl", "completeness.json",
             "run_meta.json")
    hashes = {name: hashlib.sha256((tmp_path / "results" / name).read_bytes()).hexdigest()
              for name in names}
    (tmp_path / "results/run_state.json").write_text(json.dumps(
        {"state": "complete", "result_sha256": hashes}))


def _mk_results(tmp_path, pag_weak=1.5, pag_strong=0.1, noise=0.05, n=30):
    """Synthetic per_unit.jsonl with a known anchoring structure."""
    import shutil
    rng = np.random.default_rng(7)
    (tmp_path / "results").mkdir()
    (tmp_path / "corpus").mkdir()
    bound = {}
    for field, sub in BOUND_SOURCES.items():
        (tmp_path / sub).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / sub, tmp_path / sub)
        bound[field] = hashlib.sha256((REPO / sub).read_bytes()).hexdigest()
    units, stimuli = [], []
    for stratum, pag in (("weak", pag_weak), ("strong", pag_strong)):
        for i in range(n):
            sid = f"{stratum[0].upper()}{i:02d}"
            # Half the stimuli are authoring-free, so the §6.3 all-corpus branch is
            # exercised on real data rather than on an empty array (which is what
            # happened before AUDIT-2026-08-08 N13 and produced "Mean of empty slice").
            all_corpus = (i % 2 == 0)
            stimuli.append({"stimulus_id": sid, "competence_label": stratum,
                            # Two stimuli per source run: tests must exercise the
                            # registered cluster-level inference, not only singleton runs.
                            "source_run": f"{stratum}-run-{i // 2:02d}",
                            "evidence_strength": ["ambiguous", "moderate", "strong"][i % 3],
                            "family": "ped", "base": "sonnet",
                            "r_high_provenance": "corpus",
                            "r_low_provenance": "corpus" if all_corpus else "authored"})
            base_delta = 1.0
            deltas = {"D": base_delta, "P_nov": base_delta + pag / 2,
                      "P_adv": base_delta - pag / 2}
            for arm, d in deltas.items():
                s_low = 2.5 + rng.normal(0, noise)
                s_high = s_low + d + rng.normal(0, noise)
                for pole, val in (("high", s_high), ("low", s_low)):
                    units.append({"stimulus_id": sid, "arm": arm, "pole": pole,
                                  "competence_label": stratum,
                                  "evidence_strength": stimuli[-1]["evidence_strength"],
                                  "overall_mean": val, "n_valid": 3,
                                  # the four rubric sub-scores, for §6.3's per-field
                                  # decomposition; same structure, damped effect
                                  # three fields carry the full planted effect...
                                  "scaffolding_mean": val,
                                  "productive_struggle_mean": val,
                                  "elicitation_mean": val,
                                  # ...and one carries half of it, so the
                                  # decomposition has to distinguish them
                                  "assistance_calibration_mean":
                                      (s_low + d / 2) if pole == "high" else s_low})
    with open(tmp_path / "results/per_unit.jsonl", "w") as f:
        for u in units:
            f.write(json.dumps(u) + "\n")
    with open(tmp_path / "corpus/stimuli.jsonl", "w") as f:
        for s in stimuli:
            f.write(json.dumps(s) + "\n")
    # run_meta must pin the stimuli it was scored against (AUDIT-2026-08-08 B2)
    stim_sha = hashlib.sha256(
        (tmp_path / "corpus/stimuli.jsonl").read_bytes()).hexdigest()
    frozen = {"stimuli_sha256": stim_sha, **bound}
    (tmp_path / "results/run_meta.json").write_text(json.dumps(
        {"backend": "live", "reportable": True, "contract_sha256": "test",
         "live_provenance_ok": True,
         "n_units": len(units), "n_per_rep_rows": len(units) * 3,
         "frozen_inputs": frozen}))
    # The committed anchor the run record is checked against; without it the integrity
    # chain terminates in untracked files again (AUDIT-2026-08-10 B3).
    (tmp_path / "results/plan.json").write_text(json.dumps({"frozen_inputs": frozen}))
    (tmp_path / "results/per_rep_scores.jsonl").write_text("synthetic\n")
    (tmp_path / "results/completeness.json").write_text(json.dumps({"complete": True}))
    (tmp_path / "results/cache").mkdir()
    (tmp_path / "results/wire").mkdir()
    cache = tmp_path / "results/cache/profile_pedagogy_cache.json"
    wire = tmp_path / "results/wire/calls.jsonl"
    cache.write_text("synthetic cache\n")
    wire.write_text("synthetic wire\n")
    meta = json.loads((tmp_path / "results/run_meta.json").read_text())
    meta["cache_sha256"] = hashlib.sha256(cache.read_bytes()).hexdigest()
    meta["wire_sha256"] = hashlib.sha256(wire.read_bytes()).hexdigest()
    (tmp_path / "results/run_meta.json").write_text(json.dumps(meta))
    _refresh_hashes(tmp_path)


def test_recovers_planted_anchoring_gap(tmp_path, monkeypatch):
    monkeypatch.setattr(AN, "ROOT", tmp_path)
    monkeypatch.setattr(AN, "N_RESAMPLES", 2000)
    _mk_results(tmp_path, pag_weak=1.5, pag_strong=0.1)
    _, units, stimuli = AN.load(allow_mock=False)
    rows = AN.build_deltas(units, stimuli)
    res = AN.analyze(rows)
    assert res["n_per_stratum"] == {"weak": 30, "strong": 30}
    assert res["n_source_runs_per_stratum"] == {"weak": 15, "strong": 15}
    p = res["primary_PAG_weak"]
    assert p["mean"] == pytest.approx(1.5, abs=0.1)
    assert p["wilcoxon_p"] < 1e-4
    assert p["ci95_bca"][0] > 1.0
    s = res["secondary_PAG_strong"]
    assert s["mean"] == pytest.approx(0.1, abs=0.1)
    # planted structure: movement from D is symmetric +/- pag/2 in the weak stratum
    mv = res["secondary_movement_from_D"]["delta(P_nov)-delta(D), weak"]
    assert mv["mean"] == pytest.approx(0.75, abs=0.1)


def test_null_structure_reports_null(tmp_path, monkeypatch):
    monkeypatch.setattr(AN, "ROOT", tmp_path)
    monkeypatch.setattr(AN, "N_RESAMPLES", 2000)
    _mk_results(tmp_path, pag_weak=0.0, pag_strong=0.0, noise=0.15)
    _, units, stimuli = AN.load(allow_mock=False)
    res = AN.analyze(AN.build_deltas(units, stimuli))
    p = res["primary_PAG_weak"]
    assert abs(p["mean"]) < 0.15
    assert p["ci95_bca"][0] < 0 < p["ci95_bca"][1]


def test_float_ghost_zeros_are_dropped_from_the_signed_rank_test():
    """A PAG that is exactly zero in exact arithmetic must not enter the Wilcoxon.

    AUDIT-2026-08-08 B3: per-unit scores are means of 3 integers, so a true zero
    difference-of-differences lands on +/-4.44e-16, and `vals != 0` let it through as
    the smallest-magnitude (rank 1) difference, with a sign set by rounding order
    alone. Reproduce the exact arithmetic the pipeline produces instead of writing
    the residue in by hand.
    """
    def unit_mean(a, b, c):
        return (a + b + c) / 3

    # three reps per (arm, pole); nov and adv have identical score patterns, so the
    # true PAG is exactly 0, though not in binary floating point
    nov_high, nov_low = unit_mean(4, 3, 3), unit_mean(3, 3, 2)
    adv_high, adv_low = unit_mean(4, 3, 3), unit_mean(3, 3, 2)
    ghost = (nov_high - nov_low) - (adv_high - adv_low)
    assert ghost == 0.0 or abs(ghost) < 1e-12  # exact-zero PAG, however it rounds

    vals = np.array([ghost] * 6 + [0.5, -0.25, 0.75, 1.0, -0.5, 0.25])
    rep = AN.wilcoxon_report(vals)
    assert rep["n"] == 12
    assert rep["n_nonzero"] == 6, "true zeros leaked into the signed-rank test"
    assert rep["n_zero_dropped"] == 6

    # and the residue must not be able to sneak in with either sign
    for signed in (+4.440892098500626e-16, -4.440892098500626e-16):
        r = AN.wilcoxon_report(np.array([signed] * 4 + [0.5, -0.25, 0.75, 1.0, -0.5]))
        assert r["n_nonzero"] == 5, signed


def test_exact_signed_rank_is_tie_valid_and_defined_for_sparse_nonzeros():
    tied = np.array([-1/3] + [2/3] * 9 + [-2/3] * 20)
    report = AN.wilcoxon_report(tied)
    assert report["wilcoxon_p"] == pytest.approx(0.04277394525706768)
    assert report["wilcoxon_method"].startswith("exact conditional")

    sparse = AN.wilcoxon_report(np.array([1/3] * 4 + [0.0] * 26))
    assert sparse["n_nonzero"] == 4
    assert sparse["wilcoxon_p"] == pytest.approx(0.125)
    assert sparse["rank_biserial"] == 1.0

    all_zero = AN.wilcoxon_report(np.zeros(30))
    assert all_zero["wilcoxon_p"] == 1.0
    assert all_zero["rank_biserial"] == 0.0


def test_per_field_decomposition_is_produced_for_every_rubric_subscore():
    """PREREGISTRATION §6.3's last bullet was pre-registered but not implemented
    (AUDIT-2026-08-08 N4)."""
    assert AN.SUB_FIELDS == ("scaffolding", "productive_struggle",
                             "assistance_calibration", "elicitation")


def test_per_field_decomposition_runs_on_full_results(tmp_path, monkeypatch):
    monkeypatch.setattr(AN, "ROOT", tmp_path)
    monkeypatch.setattr(AN, "N_RESAMPLES", 500)
    _mk_results(tmp_path, pag_weak=1.5, pag_strong=0.1)
    _, units, stimuli = AN.load(allow_mock=False)
    res = AN.analyze(AN.build_deltas(units, stimuli))
    pf = res["secondary_per_field_decomposition"]
    assert set(pf) == set(AN.SUB_FIELDS)
    for f in AN.SUB_FIELDS:
        for stratum in ("weak", "strong"):
            assert pf[f][stratum]["n"] == 15, (f, stratum)
            assert pf[f][stratum]["n_stimuli_dropped_unparsed"] == 0
    # the fixture plants the PAG in scaffolding/productive_struggle/elicitation at
    # full size and in assistance_calibration at half size
    assert pf["scaffolding"]["weak"]["mean"] == pytest.approx(1.5, abs=0.1)
    assert pf["assistance_calibration"]["weak"]["mean"] == pytest.approx(0.75, abs=0.1)


def test_per_field_decomposition_tolerates_an_unparsed_subscore(tmp_path, monkeypatch):
    monkeypatch.setattr(AN, "ROOT", tmp_path)
    monkeypatch.setattr(AN, "N_RESAMPLES", 500)
    _mk_results(tmp_path, pag_weak=1.5, pag_strong=0.1)
    units = [json.loads(l) for l in open(tmp_path / "results/per_unit.jsonl")]
    for u in units:                       # one stimulus never had `elicitation` parsed
        if u["stimulus_id"] == "W00":
            u["elicitation_mean"] = None
    with open(tmp_path / "results/per_unit.jsonl", "w") as f:
        for u in units:
            f.write(json.dumps(u) + "\n")
    _refresh_hashes(tmp_path)
    _, units, stimuli = AN.load(allow_mock=False)
    pf = AN.analyze(AN.build_deltas(units, stimuli))["secondary_per_field_decomposition"]
    assert pf["elicitation"]["weak"]["n"] == 15
    assert pf["elicitation"]["weak"]["n_stimuli_dropped_unparsed"] == 1
    assert pf["scaffolding"]["weak"]["n"] == 15


def test_mock_results_are_refused_without_flag(tmp_path, monkeypatch):
    monkeypatch.setattr(AN, "ROOT", tmp_path)
    _mk_results(tmp_path)
    meta = json.loads((tmp_path / "results/run_meta.json").read_text())
    meta.update(backend="mock", reportable=False)
    (tmp_path / "results/run_meta.json").write_text(json.dumps(meta))
    _refresh_hashes(tmp_path)
    with pytest.raises(SystemExit, match="NOT reportable"):
        AN.load(allow_mock=False)
    AN.load(allow_mock=True)  # rehearsal path stays available


def test_analysis_refuses_missing_and_duplicate_promoted_units(tmp_path, monkeypatch):
    monkeypatch.setattr(AN, "ROOT", tmp_path)
    _mk_results(tmp_path)
    path = tmp_path / "results/per_unit.jsonl"
    rows = path.read_text().splitlines()

    path.write_text("\n".join(rows[:-1]) + "\n")
    meta = json.loads((tmp_path / "results/run_meta.json").read_text())
    meta["n_units"] -= 1
    (tmp_path / "results/run_meta.json").write_text(json.dumps(meta))
    _refresh_hashes(tmp_path)
    with pytest.raises(SystemExit, match="GRID MISMATCH"):
        AN.load(False)

    again = tmp_path / "again"
    again.mkdir()
    _mk_results(again)
    monkeypatch.setattr(AN, "ROOT", again)
    path = again / "results/per_unit.jsonl"
    rows = path.read_text().splitlines()
    path.write_text("\n".join(rows + [rows[0]]) + "\n")
    _refresh_hashes(again)
    with pytest.raises(SystemExit, match="DUPLICATE"):
        AN.load(False)


def test_analysis_refuses_post_promotion_file_edit(tmp_path, monkeypatch):
    monkeypatch.setattr(AN, "ROOT", tmp_path)
    _mk_results(tmp_path)
    with open(tmp_path / "results/per_unit.jsonl", "a") as f:
        f.write("{}\n")
    with pytest.raises(SystemExit, match="PROMOTED RESULT CHANGED"):
        AN.load(False)


def test_analysis_refuses_post_promotion_provenance_edit(tmp_path, monkeypatch):
    monkeypatch.setattr(AN, "ROOT", tmp_path)
    _mk_results(tmp_path)
    with open(tmp_path / "results/wire/calls.jsonl", "a") as f:
        f.write("tamper\n")
    with pytest.raises(SystemExit, match="LIVE PROVENANCE CHANGED"):
        AN.load(False)


def test_analysis_refuses_edited_analysis_code_or_plan(tmp_path, monkeypatch):
    """The estimator and the plan must be the ones the run was frozen under.

    `frozen_inputs` binds both for every live command, but nothing rechecked them at
    analysis time, so repointing the primary endpoint at the other stratum after the
    scores existed produced a summary.json still stamped with the run's legitimate
    contract hash (AUDIT-2026-08-08-preflight-review-3 N2).
    """
    monkeypatch.setattr(AN, "ROOT", tmp_path)
    _mk_results(tmp_path)
    AN.load(False)                                  # baseline: bound and unmodified

    for sub in BOUND_SOURCES.values():
        target = tmp_path / sub
        original = target.read_bytes()
        target.write_bytes(original + b"\n# post-hoc change\n")
        with pytest.raises(SystemExit, match="ANALYSIS CODE OR PLAN CHANGED"):
            AN.load(False)
        target.write_bytes(original)

    meta = json.loads((tmp_path / "results/run_meta.json").read_text())
    del meta["frozen_inputs"]["analyze_py_sha256"]
    (tmp_path / "results/run_meta.json").write_text(json.dumps(meta))
    _refresh_hashes(tmp_path)
    with pytest.raises(SystemExit, match="records no analyze_py_sha256"):
        AN.load(False)


def test_analysis_refuses_a_restamped_run_record(tmp_path, monkeypatch):
    """Re-stamping the untracked chain must not launder an edited estimator.

    The N2 gate above trusts run_meta.json, and run_meta.json is certified only by
    run_state.json, which are both untracked and hand-writable. Editing analyze.py and
    then rewriting both records by hand passed every check and reported the fabricated
    number. results/plan.json is committed under the freeze tag and carries the same
    frozen_inputs, so the chain now terminates in git
    (AUDIT-2026-08-10-endpoint-sensitivity B3).
    """
    monkeypatch.setattr(AN, "ROOT", tmp_path)
    _mk_results(tmp_path)
    AN.load(False)                                  # baseline: anchored and unmodified

    target = tmp_path / "analysis/analyze.py"
    target.write_bytes(target.read_bytes() + b"\n# post-hoc estimator change\n")
    # ...and cover the tracks the N2 gate would otherwise catch.
    meta = json.loads((tmp_path / "results/run_meta.json").read_text())
    meta["frozen_inputs"]["analyze_py_sha256"] = hashlib.sha256(
        target.read_bytes()).hexdigest()
    (tmp_path / "results/run_meta.json").write_text(json.dumps(meta))
    _refresh_hashes(tmp_path)

    with pytest.raises(SystemExit, match="DISAGREE WITH THE COMMITTED PLAN"):
        AN.load(False)


def test_analysis_refuses_when_the_committed_plan_is_absent(tmp_path, monkeypatch):
    """A missing anchor fails closed rather than falling back to the untracked chain."""
    monkeypatch.setattr(AN, "ROOT", tmp_path)
    _mk_results(tmp_path)
    (tmp_path / "results/plan.json").unlink()
    with pytest.raises(SystemExit, match="results/plan.json is missing"):
        AN.load(False)


def test_analysis_refuses_an_incomplete_promoted_unit(tmp_path, monkeypatch):
    """The n_valid == 3 gate had no test; disabling it passed the suite (N2b, M10)."""
    monkeypatch.setattr(AN, "ROOT", tmp_path)
    _mk_results(tmp_path)
    path = tmp_path / "results/per_unit.jsonl"
    rows = [json.loads(l) for l in path.read_text().splitlines()]
    rows[0]["n_valid"] = 2
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    _refresh_hashes(tmp_path)
    with pytest.raises(SystemExit, match="INCOMPLETE promoted unit"):
        AN.load(False)


def test_all_corpus_subset_requires_both_poles_from_the_corpus():
    """§6.3's robustness subset is "no authored text anywhere", on both poles.

    The definition was never exercised through analyze.py (test_stimuli.py recomputes
    the subset inside the test), so flipping the `and` to an `or`, which would silently
    widen the pre-registered subset from 27 stimuli to 55, passed (N2b, M9).
    """
    combos = {"CC": ("corpus", "corpus"), "CA": ("corpus", "authored"),
              "AC": ("authored", "corpus"), "AA": ("authored", "authored")}
    stimuli, units = {}, []
    for sid, (high, low) in combos.items():
        stimuli[sid] = {"stimulus_id": sid, "competence_label": "weak",
                        "source_run": f"run-{sid}", "evidence_strength": "moderate",
                        "family": "ped", "base": "sonnet",
                        "r_high_provenance": high, "r_low_provenance": low}
        for arm in AN.ARMS:
            for pole, val in (("high", 4.0), ("low", 3.0)):
                units.append({"stimulus_id": sid, "arm": arm, "pole": pole,
                              "overall_mean": val, "n_valid": 3})
    rows = AN.build_deltas(units, stimuli)
    assert {r["stimulus_id"] for r in rows if r["all_corpus"]} == {"CC"}
