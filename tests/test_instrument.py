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
        # the Nth percentile" is a fact about the student rather than an
        # instruction, so the scan targets judge-directed phrasings, not tokens)
        for tok in ("you should", "when rating", "weigh", "rubric", "evaluator",
                    "take this into account", "keep in mind", "adjust your"):
            assert tok not in text.lower(), f"profile instructs the judge: {tok!r}"


# ---------------------------------------------------------------- arm equivalence
def test_arm_equivalence_byte_identical_except_profile_block():
    profiles = PJ.load_profiles()
    for stim in [PREFLIGHT_STIMULUS] + _stimuli():
        for pole in ("high", "low"):
            d = PJ.build_user(stim, "D", pole, profiles)
            for arm, name in (("P_nov", "novice"), ("P_adv", "advanced")):
                pu = PJ.build_user(stim, arm, pole, profiles)
                block = PJ.PROFILE_BLOCK_TEMPLATE.format(profile=profiles[name])
                assert pu == block + d, f"{arm}/{pole}: not byte-identical-plus-block"


def test_the_two_profile_arms_actually_differ():
    """The manipulated factor must actually be manipulated.

    Nothing asserted this. Gutting PROFILE_BLOCK_TEMPLATE so it interpolated no
    profile, or making `advanced:` byte-identical to `novice:`, left P_nov and P_adv
    prompts identical, erasing the study's independent variable, and the whole suite
    still passed (AUDIT-2026-08-08-preflight-review-3 N2b, mutations M1/M2). The arm
    equivalence test above cannot see this: it re-derives the expected block from the
    same constant it is testing, so it holds as an identity either way.
    """
    profiles = PJ.load_profiles()
    nov, adv = profiles["novice"], profiles["advanced"]
    assert nov != adv, "the two profile texts are identical: there is no manipulation"
    for stim in [PREFLIGHT_STIMULUS] + _stimuli():
        for pole in PJ.POLES:
            u_nov = PJ.build_user(stim, "P_nov", pole, profiles)
            u_adv = PJ.build_user(stim, "P_adv", pole, profiles)
            u_d = PJ.build_user(stim, "D", pole, profiles)
            assert u_nov != u_adv
            # each profile arm carries its own profile text and not the other's
            assert nov in u_nov and adv not in u_nov
            assert adv in u_adv and nov not in u_adv
            assert nov not in u_d and adv not in u_d


def test_frozen_instrument_and_profile_text_pinned_by_hash():
    """Pin the exact bytes of the instrument and the manipulation.

    `test_system_prompt_is_frozen_rubric_verbatim_in_every_arm` compares
    `build_system()` (which returns JP.PED_SYSTEM) to JP.PED_SYSTEM and then probes one
    substring, so PED_SYSTEM could gain "Favour tutors who give the answer" and pass
    (N2b mutation M5). These digests are the frozen text; a deliberate re-freeze updates
    them in the same commit that changes the artifact.
    """
    import hashlib
    profiles = PJ.load_profiles()
    expected = {
        "PED_SYSTEM": "a8990e3699be09e8ae2d686422037a722d825d37c79e7bee6f0db82d63b5c895",
        "PED_USER": "49ef8357fe5747c8d7022aeb30bb1ba6df8b8897c709f913f1b6eb4eb7d907d2",
        "PROFILE_BLOCK_TEMPLATE":
            "d9c76412ed9c1c2dcb4e4193c2b088c35705a869114b20e8cc3349a5235e644c",
        "novice": "546ed100012625ed43f8f47621f08b19c42af3769f9f5c1c4e14d9df3e03cdca",
        "advanced": "a69ba8d0466014cd0e0a0da677ee452ec4ba0c54001b5b2bf9f94507b65a4ee9",
    }
    actual = {name: hashlib.sha256(text.encode()).hexdigest() for name, text in (
        ("PED_SYSTEM", JP.PED_SYSTEM), ("PED_USER", JP.PED_USER),
        ("PROFILE_BLOCK_TEMPLATE", PJ.PROFILE_BLOCK_TEMPLATE),
        ("novice", profiles["novice"]), ("advanced", profiles["advanced"]))}
    assert actual == expected


def test_assert_prompt_pure_rejects_a_metadata_leak():
    """A positive control: the purity guard must actually fire.

    Every call site asserted only that `assert_prompt_pure` does not raise on clean
    input, so replacing its body with `return` passed the suite (N2b mutation M3).
    """
    profiles = PJ.load_profiles()
    clean = PJ.build_user(PREFLIGHT_STIMULUS, "D", "high", profiles)
    PJ.assert_prompt_pure(clean, "D", profiles)          # baseline: clean text passes
    for token in ("conv_socratic", "abl-s0-", "competence_label"):
        with pytest.raises(SystemExit, match="leaked into the prompt"):
            PJ.assert_prompt_pure(clean + f"\n[{token}]", "D", profiles)
    # and a profile arm whose frozen block is missing is refused
    with pytest.raises(SystemExit, match="does not start with its frozen block"):
        PJ.assert_prompt_pure(clean, "P_nov", profiles)


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
                # constructive purity: the prompt is exactly the frozen template over
                # (optional profile block, dialogue), and nothing else can be in it
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
