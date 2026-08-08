#!/usr/bin/env python3
"""The profile-anchoring judge instrument.

Builds on the vendored, frozen pedagogy judge (analysis/judge_pedagogy.py) so the
scores are commensurable with the companion study:
  - system prompt: JP.PED_SYSTEM, VERBATIM, identical in every arm;
  - user message: JP.PED_USER.format(dialogue=...) — with, in the profile arms
    ONLY, a profile block prepended. The three arms' user messages are
    byte-identical except for that block (asserted in tests/test_instrument.py);
  - parsing/aggregation: JP.parse_pedagogy_scores / JP.aggregate_reps, unchanged.

Arms:
  D      dialogue + response                       (no-profile control)
  P_nov  novice profile + dialogue + response
  P_adv  advanced profile + dialogue + response

Units are (stimulus_id, arm, pole) with pole in {high, low} (the R_H / R_L
candidate response). Design: 60 stimuli x 3 arms x 2 poles x 3 reps = 1,080 calls.
Cache key: (stimulus_id, arm, pole, rep). Call order is a seeded shuffle of the
full schedule (arm order randomised, per the pre-registration).

The prompt NEVER contains: the condition/arm label, the competence label, the
source policy name, the tutor base, node names, run ids, or the canonical answer
— nothing beyond profile block (when the arm calls for it) + dialogue + rubric.
"""
from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))

from analysis import judge_pedagogy as JP  # noqa: E402  vendored, frozen

SCHEDULE_SEED = 90210
ARMS = ("D", "P_nov", "P_adv")
POLES = ("high", "low")
REPS = 3

# The ONLY text this study adds to the frozen instrument. A neutral provenance
# framing; no instruction about how to weigh it.
PROFILE_BLOCK_TEMPLATE = (
    "Background information about the student, from the course records:\n"
    '"""\n{profile}\n"""\n\n'
)


def load_profiles() -> dict:
    p = yaml.safe_load((ROOT / "profiles/profiles.yaml").read_text())
    assert set(p) == {"novice", "advanced"}
    return p


def load_stimuli() -> list[dict]:
    return [json.loads(l) for l in open(ROOT / "corpus/stimuli.jsonl")]


def dialogue_for(stimulus: dict, pole: str) -> str:
    """context + the rated response, exactly as analysis.judge.render_dialogue
    would render them (each turn's text stripped, blocks joined by blank lines)."""
    response = stimulus[f"r_{pole}"]
    return stimulus["context"] + "\n\nTutor: " + response.strip()


def profile_for_arm(arm: str, profiles: dict):
    return {"D": None, "P_nov": profiles["novice"], "P_adv": profiles["advanced"]}[arm]


def build_user(stimulus: dict, arm: str, pole: str, profiles: dict) -> str:
    user = JP.PED_USER.format(dialogue=dialogue_for(stimulus, pole))
    profile = profile_for_arm(arm, profiles)
    if profile is not None:
        user = PROFILE_BLOCK_TEMPLATE.format(profile=profile) + user
    return user


def build_system() -> str:
    return JP.PED_SYSTEM


def cache_key(stimulus_id: str, arm: str, pole: str, rep: int) -> str:
    return f"{stimulus_id}|{arm}|{pole}|{rep}"


def schedule(stimuli: list[dict]) -> list[dict]:
    """The full call schedule, seeded-shuffled so arm order is randomised."""
    calls = [{"stimulus_id": s["stimulus_id"], "arm": arm, "pole": pole, "rep": rep}
             for s in stimuli for arm in ARMS for pole in POLES for rep in range(REPS)]
    random.Random(SCHEDULE_SEED).shuffle(calls)
    return calls


def contract_sha256(judge_spec: dict) -> str:
    """Hash of everything that shapes a request: model + params + every frozen text.
    The preflight freezes this; the paid run refuses to start if it changed."""
    profiles = load_profiles()
    stimuli_sha = (ROOT / "corpus/stimuli.sha256").read_text().split()[0]
    blob = json.dumps({
        "model": judge_spec["model"],
        "provider": judge_spec.get("provider"),
        "temperature": judge_spec.get("temperature"),
        "max_tokens": judge_spec.get("max_tokens"),
        "system": JP.PED_SYSTEM,
        "user_template": JP.PED_USER,
        "profile_block_template": PROFILE_BLOCK_TEMPLATE,
        "profiles": profiles,
        "stimuli_sha256": stimuli_sha,
        "arms": ARMS, "poles": POLES, "reps": REPS,
        "schedule_seed": SCHEDULE_SEED,
    }, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()


# Unambiguous run-metadata tokens that must NEVER appear in an assembled prompt.
# (Competence labels and canonical answers cannot be checked as bare substrings —
# dialogue text can legitimately contain "strong" or the answer value — so the
# load-bearing guarantee is the constructive-equality test in tests/test_instrument.py;
# this list catches metadata strings that have no legitimate in-dialogue reading.)
FORBIDDEN_METADATA_TOKENS = (
    "conv_socratic", "conv_no_final_answer", "ped_no_cascade", "ped_no_gate",
    "ped_no_tracker", "state_tracker", "hint_cascade", "deferral_gate", "decomposer",
    "abl-s0-", "conf-s0-", "conf-gemini", "conf-gpt", "P_nov", "P_adv",
    "prior_stratum", "competence_label", "evidence_strength", "canonical_answer",
    "sonnet", "gemini", "gpt-5", "claude", "replicate_id", "stimulus_id",
)


def assert_prompt_pure(user: str, arm: str, profiles: dict) -> None:
    """The non-profile portion must contain no metadata token; the profile block
    (the manipulated factor) is exempt by construction."""
    body = user
    profile = profile_for_arm(arm, profiles)
    if profile is not None:
        block = PROFILE_BLOCK_TEMPLATE.format(profile=profile)
        assert user.startswith(block), "profile arm does not start with its block"
        body = user[len(block):]
    low = body.lower()
    for tok in FORBIDDEN_METADATA_TOKENS:
        assert tok.lower() not in low, f"metadata token {tok!r} leaked into the prompt"
