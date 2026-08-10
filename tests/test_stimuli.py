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

# The frozen design, pinned exactly (AUDIT-2026-08-08 B1/N2). Every number the paper
# reports about the composition of the frozen set is asserted here, so a disclosed
# figure cannot drift away from the artifact without a test failing. The strong
# stratum is 25, not 30: eligibility left 26 and the pre-data audit excluded C018
# for a rubric conflict and response-pair contingency confound (Amendment A4).
N_STIMULI = 55
PER_STRATUM = {"weak": 30, "strong": 25}
PROVENANCE = {"r_high": {"corpus": 53, "authored": 2},
              "r_low": {"corpus": 29, "authored": 26}}
ALL_CORPUS = {"weak": 12, "strong": 15}


def _stimuli():
    if not STIMULI.exists():
        pytest.skip("corpus/stimuli.jsonl not frozen yet")
    return [json.loads(l) for l in open(STIMULI)]


def test_design_matches_the_frozen_strata():
    s = _stimuli()
    assert len(s) == N_STIMULI
    assert Counter(x["competence_label"] for x in s) == PER_STRATUM
    assert len({x["stimulus_id"] for x in s}) == N_STIMULI
    assert "C018" not in {x["candidate_id"] for x in s}


def test_authoring_split_is_exactly_as_disclosed():
    """The authoring/pole split is a disclosed FACT about the frozen set, so pin it.

    The previous assertion (`n_corpus >= 10` per pole) was advertised in
    PREREGISTRATION §2 as "a lopsidedness bound" but would have passed with nearly
    every response authored on one pole — it bounded only "a pole with no corpus grounding
    at all" (AUDIT-2026-08-08 N2). The imbalance is real and heavy: authored text sits
    on R_L 26 times against 2 on R_H, because the source tutors are pedagogically
    tuned so the real turn is usually the high pole. An additive artifact is inert
    for the primary endpoint by construction — the identical R_H/R_L texts are judged
    in all three arms, so a stimulus-level artifact enters every arm's Δ equally and cancels in
    Δ(P_nov) − Δ(P_adv) under additivity — and it is checked directly by the
    all-corpus robustness analysis. What must not happen is the number drifting away
    from what the paper says it is.
    """
    s = _stimuli()
    for pole, expected in PROVENANCE.items():
        got = Counter(x[f"{pole}_provenance"] for x in s)
        assert dict(got) == expected, f"{pole}: {dict(got)} != disclosed {expected}"


def test_all_corpus_subset_can_support_the_robustness_check():
    """PREREGISTRATION §6.3 re-runs the primary endpoint on stimuli with NO authored
    text. That check only means something if the subset is non-trivial in both
    strata."""
    s = _stimuli()
    allc = [x for x in s if x["r_high_provenance"] == "corpus"
            and x["r_low_provenance"] == "corpus"]
    per = Counter(x["competence_label"] for x in allc)
    assert dict(per) == ALL_CORPUS, f"{dict(per)} != disclosed {ALL_CORPUS}"
    assert min(per.values()) >= 10, per


def test_no_response_text_serves_two_stimuli():
    """Two stimuli sharing a donor turn are not independent observations, but the
    §6.5 bootstrap resamples stimuli as if they were (AUDIT-2026-08-08 N6)."""
    seen = {}
    for x in _stimuli():
        for pole in ("r_high", "r_low"):
            txt = x[pole].strip()
            assert txt not in seen, (
                f"{x['stimulus_id']}:{pole} duplicates {seen.get(txt)}")
            seen[txt] = f"{x['stimulus_id']}:{pole}"


def test_no_context_has_already_resolved_its_named_problem():
    """Every stimulus's `problem_id` must still describe its live content.

    AUDIT-2026-08-08 B1: eight stimuli had drifted onto a *different* problem after
    the named one was solved earlier in the dialogue. Because every guard keys on
    `problem_id`, that silently disabled both the eligibility filter and the R_H
    answer-leak check below — one of those items' R_H stated its live problem's
    answer while `turn_leaks`, pointed at the named problem, reported nothing.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "bs_elig", ROOT / "corpus/build_stimuli.py")
    BS = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(BS)
    problems = M.problem_index(str(ROOT / "vendor/domain/algebra/problems.yaml"))
    for x in _stimuli():
        assert not BS._states_answer_in(x["context"], problems[x["problem_id"]]), (
            f"{x['stimulus_id']}: the context already resolves {x['problem_id']}, so "
            "the dialogue has moved past the problem its metadata names")


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


def test_answer_guards_actually_fire_on_text_that_states_the_answer():
    """Positive controls for the two guards the frozen set relies on.

    `test_poles_differ_and_r_high_never_leaks_the_answer` and
    `test_no_context_has_already_resolved_its_named_problem` both assert only that the
    guard returns False on the frozen text, so stubbing `turn_leaks` to return False
    passed the whole suite (AUDIT-2026-08-08-preflight-review-3 N2b, mutation M4).
    These pin the other direction, including the word-spelled forms the eligibility
    filter used to miss (N9).
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "bs_guards", ROOT / "corpus/build_stimuli.py")
    BS = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(BS)
    problems = M.problem_index(str(ROOT / "vendor/domain/algebra/problems.yaml"))
    for pid in sorted({x["problem_id"] for x in _stimuli()}):
        problem = problems[pid]
        lk = problem.leakage or {}
        numeric, solution = lk.get("numeric_form", []), lk.get("solution_form", [])
        assert numeric and solution, pid
        assert turn_leaks(f"So x = {numeric[0]} liters.", numeric, solution), pid
        assert turn_leaks(f"In short, {solution[0]}.", numeric, solution), pid
        assert BS._states_answer_in(f"So x = {numeric[0]} liters.", problem), pid
        assert BS._states_answer_in(f"In short, {solution[0]}.", problem), pid
        # the deliberate carve-out: an unrepaired sign error is a live next step
        assert not BS._states_answer_in(f"I got x = -{numeric[0]}.", problem), pid


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


def test_manipulation_check_covers_exactly_the_final_pairs():
    key = json.loads((ROOT / "corpus/manip/_key.json").read_text())
    report = json.loads((ROOT / "corpus/manip/report.json").read_text())
    expected = {x["candidate_id"] for x in _stimuli()}
    assert {row["candidate_id"] for row in key.values()} == expected
    assert {row["candidate_id"] for row in report["per_item"].values()} == expected
    assert report["n_pairs"] == N_STIMULI
    assert report["n_correct"] == N_STIMULI
    assert report["n_reversed"] == report["n_tied"] == 0


def test_coverage_is_spread_across_problems_and_bases():
    s = _stimuli()
    per_problem = Counter(x["problem_id"] for x in s)
    assert max(per_problem.values()) <= 14, per_problem
    assert len({x["base"] for x in s}) >= 2
    per_run_problem = Counter((x["source_run"], x["problem_id"]) for x in s)
    assert max(per_run_problem.values()) <= 2, "a single session dominates a problem"
