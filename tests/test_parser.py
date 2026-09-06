"""The frozen pedagogy parser round-trips well-formed and malformed replies (Phase 7)."""
import json

from analysis import judge_pedagogy as JP


def _well_formed(vals=(4, 3, 4, 5, 4)):
    return json.dumps(dict(zip(JP.FIELDS, vals)))


def test_parses_clean_json():
    s = JP.parse_pedagogy_scores(_well_formed())
    assert s == {"scaffolding": 4, "productive_struggle": 3,
                 "assistance_calibration": 4, "elicitation": 5, "overall": 4}


def test_parses_json_with_surrounding_prose():
    text = "Here are my ratings:\n" + _well_formed((2, 2, 3, 2, 2)) + "\nHope that helps."
    assert JP.parse_pedagogy_scores(text)["overall"] == 2


def test_parses_single_quotes_and_equals_fallback():
    text = ("{'scaffolding'= 3, 'productive_struggle'= 2, "
            "'assistance_calibration'= 3, 'elicitation'= 1, 'overall'= 2,}")
    s = JP.parse_pedagogy_scores(text)
    assert s is not None and s["overall"] == 2 and s["elicitation"] == 1


def test_missing_overall_is_unusable():
    text = json.dumps({k: 4 for k in JP.FIELDS if k != "overall"})
    assert JP.parse_pedagogy_scores(text) is None


def test_out_of_range_overall_is_unusable():
    assert JP.parse_pedagogy_scores(_well_formed((4, 4, 4, 4, 9))) is None


def test_empty_and_prose_only_are_unusable():
    assert JP.parse_pedagogy_scores("") is None
    assert JP.parse_pedagogy_scores("I would rate this turn quite highly.") is None


def test_numeric_strings_and_floats_coerce():
    text = json.dumps({"scaffolding": "4", "productive_struggle": 3.0,
                       "assistance_calibration": "5", "elicitation": 2, "overall": "3"})
    s = JP.parse_pedagogy_scores(text)
    assert s == {"scaffolding": 4, "productive_struggle": 3,
                 "assistance_calibration": 5, "elicitation": 2, "overall": 3}


def test_aggregate_reps_drops_unusable_and_counts_valid():
    reps = [JP.parse_pedagogy_scores(_well_formed((4, 4, 4, 4, 4))),
            None,
            JP.parse_pedagogy_scores(_well_formed((2, 2, 2, 2, 2)))]
    agg = JP.aggregate_reps(reps)
    assert agg["n_reps"] == 3 and agg["n_valid"] == 2
    assert agg["overall_mean"] == 3.0
    assert agg["overall_var"] == 2.0  # sample variance of [4, 2]
