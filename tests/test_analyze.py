"""The pre-registered estimators produce correct numbers on synthetic data."""
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

# the repo's analysis/ dir is shadowed by the vendored `analysis` package (by
# design), so the study's own analyze.py is loaded by file path
_spec = importlib.util.spec_from_file_location(
    "lve_analyze", Path(__file__).resolve().parents[1] / "analysis/analyze.py")
AN = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(AN)


def _mk_results(tmp_path, pag_weak=1.5, pag_strong=0.1, noise=0.05, n=30):
    """Synthetic per_unit.jsonl with a known anchoring structure."""
    rng = np.random.default_rng(7)
    (tmp_path / "results").mkdir()
    (tmp_path / "corpus").mkdir()
    units, stimuli = [], []
    for stratum, pag in (("weak", pag_weak), ("strong", pag_strong)):
        for i in range(n):
            sid = f"{stratum[0].upper()}{i:02d}"
            stimuli.append({"stimulus_id": sid, "competence_label": stratum,
                            "evidence_strength": ["ambiguous", "moderate", "strong"][i % 3],
                            "family": "ped", "base": "sonnet"})
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
                                  "overall_mean": val, "n_valid": 3})
    with open(tmp_path / "results/per_unit.jsonl", "w") as f:
        for u in units:
            f.write(json.dumps(u) + "\n")
    with open(tmp_path / "corpus/stimuli.jsonl", "w") as f:
        for s in stimuli:
            f.write(json.dumps(s) + "\n")
    (tmp_path / "results/run_meta.json").write_text(json.dumps(
        {"backend": "live", "reportable": True, "contract_sha256": "test"}))
    (tmp_path / "results/run_state.json").write_text(json.dumps({"state": "complete"}))


def test_recovers_planted_anchoring_gap(tmp_path, monkeypatch):
    monkeypatch.setattr(AN, "ROOT", tmp_path)
    monkeypatch.setattr(AN, "N_RESAMPLES", 2000)
    _mk_results(tmp_path, pag_weak=1.5, pag_strong=0.1)
    _, units, stimuli = AN.load(allow_mock=False)
    rows = AN.build_deltas(units, stimuli)
    res = AN.analyze(rows)
    assert res["n_per_stratum"] == {"weak": 30, "strong": 30}
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


def test_mock_results_are_refused_without_flag(tmp_path, monkeypatch):
    monkeypatch.setattr(AN, "ROOT", tmp_path)
    _mk_results(tmp_path)
    meta = json.loads((tmp_path / "results/run_meta.json").read_text())
    meta.update(backend="mock", reportable=False)
    (tmp_path / "results/run_meta.json").write_text(json.dumps(meta))
    with pytest.raises(SystemExit, match="NOT reportable"):
        AN.load(allow_mock=False)
    AN.load(allow_mock=True)  # rehearsal path stays available
