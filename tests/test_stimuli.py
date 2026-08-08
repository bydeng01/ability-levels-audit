"""Frozen-stimulus integrity: design balance, contrast, and label linkage."""
import json
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))

from analysis import metrics as M           # noqa: E402  vendored, frozen
from protocol.leakage import turn_leaks     # noqa: E402  vendored, frozen

STIMULI = ROOT / "corpus/stimuli.jsonl"


def _stimuli():
    if not STIMULI.exists():
        pytest.skip("corpus/stimuli.jsonl not frozen yet")
    return [json.loads(l) for l in open(STIMULI)]


def test_design_is_sixty_stimuli_thirty_per_stratum():
    s = _stimuli()
    assert len(s) == 60
    assert Counter(x["competence_label"] for x in s) == {"weak": 30, "strong": 30}
    assert len({x["stimulus_id"] for x in s}) == 60


def test_neither_pole_is_wholly_authored():
    """Authoring must not fully replace either pole. The source tutors are
    pedagogically tuned, so a real turn is usually the high-scaffolding one and
    authored counterparts land disproportionately on R_L; that residual imbalance
    is disclosed, is inert for the primary endpoint (identical texts are judged in
    all three arms, so a stimulus-level artifact cancels in Δ(P_nov) − Δ(P_adv)),
    and is checked directly by the all-corpus robustness analysis below. What must
    not happen is a pole with no corpus grounding at all."""
    s = _stimuli()
    for pole in ("r_high_provenance", "r_low_provenance"):
        n_corpus = sum(1 for x in s if x[pole] == "corpus")
        assert n_corpus >= 10, f"{pole}: only {n_corpus} corpus-sourced responses"


def test_all_corpus_subset_can_support_the_robustness_check():
    """PREREGISTRATION §6.3 re-runs the primary endpoint on stimuli with NO authored
    text. That check only means something if the subset is non-trivial in both
    strata."""
    s = _stimuli()
    allc = [x for x in s if x["r_high_provenance"] == "corpus"
            and x["r_low_provenance"] == "corpus"]
    per = Counter(x["competence_label"] for x in allc)
    assert len(allc) >= 20, f"only {len(allc)} authoring-free stimuli"
    assert min(per.get("weak", 0), per.get("strong", 0)) >= 10, per


def test_authored_share_is_recorded_and_reportable():
    s = _stimuli()
    for x in s:
        for pole in ("r_high_provenance", "r_low_provenance"):
            assert x[pole] in ("corpus", "authored")
        # corpus-sourced responses must name their source; authored ones must not
        for pole in ("high", "low"):
            if x[f"r_{pole}_provenance"] == "corpus":
                assert x[f"r_{pole}_source_run"]
            else:
                assert x[f"r_{pole}_source_run"] is None


def test_poles_differ_and_r_high_never_leaks_the_answer():
    problems = M.problem_index(str(ROOT / "vendor/domain/algebra/problems.yaml"))
    for x in _stimuli():
        assert x["r_high"].strip() != x["r_low"].strip()
        lk = problems[x["problem_id"]].leakage or {}
        assert not turn_leaks(x["r_high"], lk.get("numeric_form", []),
                              lk.get("solution_form", [])), \
            f"{x['stimulus_id']}: R_H leaks the answer"


def test_context_ends_with_a_student_turn():
    """Turns are separated by a blank line *followed by a speaker label*; a turn's
    own text may contain blank lines, so a bare "\\n\\n" split is not a turn split."""
    import re
    for x in _stimuli():
        turns = re.split(r"\n\n(?=(?:Student|Tutor): )", x["context"])
        assert turns[-1].startswith("Student: "), x["stimulus_id"]
        assert turns[0].startswith(("Student: ", "Tutor: ")), x["stimulus_id"]


def test_every_stimulus_carries_its_blind_labels():
    labels = {l["candidate_id"]: l
              for l in (json.loads(x) for x in open(ROOT / "labeling/labels.jsonl"))}
    for x in _stimuli():
        lab = labels[x["candidate_id"]]
        assert lab["agreement_ok"]
        assert x["competence_label"] == lab["competence"]
        assert x["evidence_strength"] == lab["evidence_strength"]


def test_coverage_is_spread_across_problems_and_bases():
    s = _stimuli()
    per_problem = Counter(x["problem_id"] for x in s)
    assert max(per_problem.values()) <= 14, per_problem
    assert len({x["base"] for x in s}) >= 2
    per_run_problem = Counter((x["source_run"], x["problem_id"]) for x in s)
    assert max(per_run_problem.values()) <= 2, "a single session dominates a problem"
