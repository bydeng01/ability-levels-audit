"""Prompt purity + arm equivalence + profile matching (Phase 7)."""
import json
import re
from types import SimpleNamespace
from pathlib import Path

import pytest

from analysis import judge_pedagogy as JP
from judging import profile_judge as PJ
import judging.run_study as RS
from judging.run_study import PREFLIGHT_STIMULUS

ROOT = Path(__file__).resolve().parents[1]
STIMULI = ROOT / "corpus/stimuli.jsonl"


def _stimuli():
    if not STIMULI.exists():
        pytest.skip("corpus/stimuli.jsonl not frozen yet")
    return [json.loads(l) for l in open(STIMULI)]


# ---------------------------------------------------------------- profiles
def test_profiles_matched_and_dialogue_free():
    p = PJ.load_profiles()
    nov, adv = p["novice"], p["advanced"]
    assert abs(len(nov.split()) - len(adv.split())) <= 1
    assert abs(nov.count(".") - adv.count(".")) == 0  # same sentence structure
    for text in (nov, adv):
        # no hint at the dialogue's task domain beyond the (shared) course subject
        for tok in ("acid", "liter", "mixture", "solution", "mph", "blend",
                    "alloy", "coffee", "%"):
            assert tok not in text.lower(), f"profile leaks task specifics: {tok!r}"
        # no instruction to the judge about how to weigh the profile ("scored in
        # the Nth percentile" is a fact about the student, not an instruction —
        # so the scan targets judge-directed phrasings, not bare tokens)
        for tok in ("you should", "when rating", "weigh", "rubric", "evaluator",
                    "take this into account", "keep in mind", "adjust your"):
            assert tok not in text.lower(), f"profile instructs the judge: {tok!r}"


# ---------------------------------------------------------------- arm equivalence
def test_arm_equivalence_byte_identical_except_profile_block():
    profiles = PJ.load_profiles()
    for stim in [PREFLIGHT_STIMULUS] + (_stimuli() if STIMULI.exists() else []):
        for pole in ("high", "low"):
            d = PJ.build_user(stim, "D", pole, profiles)
            for arm, name in (("P_nov", "novice"), ("P_adv", "advanced")):
                pu = PJ.build_user(stim, arm, pole, profiles)
                block = PJ.PROFILE_BLOCK_TEMPLATE.format(profile=profiles[name])
                assert pu == block + d, f"{arm}/{pole}: not byte-identical-plus-block"


def test_system_prompt_is_frozen_rubric_verbatim_in_every_arm():
    assert PJ.build_system() == JP.PED_SYSTEM
    # and the released rubric file contains the same rubric text the system uses
    released = (ROOT / "vendor/supplement/judge_pedagogy_rubric.md").read_text()
    probe = "scaffolding (contingent support)"
    assert probe in JP.PED_RUBRIC_TEXT and probe in released


# ---------------------------------------------------------------- purity
def test_prompt_purity_constructive_and_token_scan():
    profiles = PJ.load_profiles()
    for s in _stimuli():
        for arm in PJ.ARMS:
            for pole in PJ.POLES:
                user = PJ.build_user(s, arm, pole, profiles)
                # constructive purity: the prompt is EXACTLY the frozen template over
                # (optional profile block, dialogue) — nothing else can be in it
                expected = JP.PED_USER.format(dialogue=PJ.dialogue_for(s, pole))
                prof = PJ.profile_for_arm(arm, profiles)
                if prof is not None:
                    expected = PJ.PROFILE_BLOCK_TEMPLATE.format(profile=prof) + expected
                assert user == expected
                PJ.assert_prompt_pure(user, arm, profiles)


def test_corpus_text_itself_carries_no_metadata_tokens():
    for s in _stimuli():
        blob = (s["context"] + s["r_high"] + s["r_low"]).lower()
        for tok in PJ.FORBIDDEN_METADATA_TOKENS:
            assert tok.lower() not in blob, (
                f"{s['stimulus_id']}: corpus text contains metadata token {tok!r}")


def test_profile_block_never_in_D_arm():
    profiles = PJ.load_profiles()
    marker = PJ.PROFILE_BLOCK_TEMPLATE.split("\n")[0]
    for s in _stimuli():
        for pole in PJ.POLES:
            assert marker not in PJ.build_user(s, "D", pole, profiles)


# ---------------------------------------------------------------- schedule
def test_schedule_covers_design_exactly_once():
    stimuli = _stimuli()
    sched = PJ.schedule(stimuli)
    keys = [PJ.cache_key(c["stimulus_id"], c["arm"], c["pole"], c["rep"]) for c in sched]
    assert len(keys) == len(stimuli) * 3 * 2 * 3
    assert len(set(keys)) == len(keys)
    # seeded shuffle: deterministic across calls
    assert [c["stimulus_id"] for c in PJ.schedule(stimuli)[:10]] == \
           [c["stimulus_id"] for c in sched[:10]]
    # arm order is genuinely mixed (not blocked by arm)
    first_arms = {c["arm"] for c in sched[:30]}
    assert len(first_arms) == 3


def test_dialogue_reassembly_matches_render_contract():
    """context + 'Tutor: ' + response must round-trip through the frozen renderer."""
    from analysis import judge as J
    for s in _stimuli():
        for pole in PJ.POLES:
            d = PJ.dialogue_for(s, pole)
            turns = re.split(r"\n\n(?=(?:Student|Tutor): )", d)
            labeled = [(b.partition(": ")[0], b.partition(": ")[2]) for b in turns]
            assert J.render_dialogue(labeled) == d
            assert labeled[-1][0] == "Tutor"
            assert labeled[-1][1] == s[f"r_{pole}"].strip()


def test_live_transport_disables_sdk_retries_and_sends_only_frozen_fields(monkeypatch):
    import anthropic
    captured = {"calls": 0}

    class FakeMessages:
        def create(self, **kwargs):
            captured["calls"] += 1
            captured["request"] = kwargs
            return SimpleNamespace(
                id="msg_offline_test", model="claude-opus-4-8",
                stop_reason="end_turn",
                content=[SimpleNamespace(type="text", text='{"overall": 3}')],
                usage=SimpleNamespace(input_tokens=10, output_tokens=5))

    class FakeAnthropic:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.messages = FakeMessages()

    monkeypatch.setenv("ANTHROPIC_API_KEY", "offline-placeholder")
    monkeypatch.setattr(anthropic, "Anthropic", FakeAnthropic)
    caller = RS.LiveCaller(RS.judge_spec()["cfg"])
    result = caller.call("system", "user", seed=123)

    assert captured["client"]["max_retries"] == 0
    assert captured["calls"] == 1
    assert set(captured["request"]) == {"model", "system", "messages", "max_tokens"}
    assert result["response_id"] == "msg_offline_test"
