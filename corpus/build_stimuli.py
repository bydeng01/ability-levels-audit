#!/usr/bin/env python3
"""Build the frozen stimulus corpus for the label-vs-evidence audit.

Offline. Zero API calls. Reconstructs dialogues from the frozen conv-vs-ped-tutor
corpus exactly as the original pedagogy judge saw them (vendored analysis.metrics /
analysis.judge — imported, never re-implemented), splits each judged tutor turn into
a `context` (ends with the last student turn) and the actual tutor `response`, and
samples a stratified candidate pool.

Sampling priors (NEVER analysis labels — the analysis stratum comes from the Phase 3
blind labelling pass):
  - PedTutor-family runs: the logged state_tracker record (tags.node == "state_tracker"),
    joined on (problem_id, turn_index).
  - ConvTutor-family runs (no tracker): a lexical struggle score over the context's
    student turns.

Subcommands (run in order; later ones consume earlier outputs):
  census      verify the corpus shape against the build prompt's measured numbers
              (2,219 judged turns; tracker join 991 with 844/100/39/8) and write
              corpus/census.json + corpus/response_pools.jsonl (all judged turns,
              classified for R_H/R_L pairing).
  candidates  sample the ~90-context candidate pool -> corpus/candidates.jsonl (+ sha256).
  select      apply the pre-specified deterministic rule to the Phase 3 labels ->
              the 60 selected candidate ids (corpus/selection.json).
  pair        attach R_H / R_L to the selected stimuli from the response pools, with
              authored counterparts taken from the blind review packets
              (corpus/reviews/packet_*.jsonl) -> corpus/pairing_draft.jsonl.
  freeze      assemble corpus/stimuli.jsonl (+ sha256) and copy every referenced run
              dir's calls.jsonl into corpus/logs/<run>/.
  verify      rebuild every stimulus context from corpus/logs and assert byte-identical
              reconstruction (the Phase 7 reconstruction guarantee).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))

from analysis import judge as J          # noqa: E402  vendored, frozen
from analysis import metrics as M        # noqa: E402  vendored, frozen
from protocol.leakage import turn_leaks  # noqa: E402  vendored, frozen

SEED = 20260808
CORPUS = ROOT / "corpus"
# Source-corpus logs ($SRC/logs). Only `census`, `candidates`, `topup` and `freeze`
# need them; `verify` reads the vendored copies under corpus/logs/ and is the one
# reproduction path that works on any clone. Overridable via $SRC_LOGS or --src-logs
# so the default absolute path is not a hard dependency on one machine
# (AUDIT-2026-08-08 N9).
DEFAULT_SRC_LOGS = Path(
    os.environ.get("SRC_LOGS")
    or "/Users/boyuandeng/Documents/GitHub/conv-vs-ped-tutor/logs")

# Frozen construction recipes and pre-data material exclusions. Candidate IDs are
# referenced by three completed blind-label passes, pairing reviews, and the
# manipulation check, so a reconstruction must never reassign them to newly sampled
# turns. C018 was removed after the independent pre-flight audit, before any paid
# judge score existed: its unrepaired algebra error conflicts with its strong label,
# and its two candidate responses also differ in error-contingency, not only in how
# much reasoning they leave to the student (PREREGISTRATION Amendment A4).
TOPUP_RECIPE = CORPUS / "candidates_topup.jsonl"
PRE_DATA_EXCLUSIONS = {
    "C018": "unrepaired current error and response-pair contingency confound",
}

# Expected corpus shape. Judged-turn total and the three sampling-relevant tracker
# cells match the build prompt exactly. The build prompt reported 991 joinable with
# (False,False)=8; the join reproducible from the frozen pipeline (strict JSON parse,
# training+answer-phase-window turns) gives 990 with (False,False)=7 — the one-record
# delta sits entirely in the never-sampled ambiguous cell (decisions-log 2026-08-08).
EXPECTED_JUDGED_TURNS = 2219
EXPECTED_TRACKER_JOIN = {"n": 990, (False, True): 844, (True, True): 100,
                         (True, False): 39, (False, False): 7}

CONFUSION_RE = re.compile(
    r"(i'?m stuck|\bstuck\b|confus|don'?t know|not sure|don'?t understand|"
    r"no idea|i'?m lost|help me|i can'?t\b)", re.I)
# STIMULUS ELIGIBILITY (decisions-log 2026-08-08): a stimulus must present a LIVE
# next reasoning step. The frozen answer-phase window only excludes turns after a
# *marked* `FINAL ANSWER:` commit, so post-resolution wrap-ups survive it whenever
# the student solved the problem without emitting the marker during training. In
# such a context neither pole is a scaffolding move — R_L is a closing remark and
# any R_H must invent new work — so the R_H/R_L contrast measures something other
# than scaffolding. Excluded by `is_eligible` at SELECTION (cmd_select), identically
# for both strata — not at candidate sampling.
CLOSING_RE = re.compile(
    r"\b(thank you|thanks|i'?ll remember|good luck|have a (great|good)|"
    r"appreciate (it|your)|i'?ll (try to )?(remember|apply)|"
    r"for future problems|see you|goodbye|bye)\b", re.I)
ASK_ANSWER_RE = re.compile(
    r"(what'?s the answer|what is the answer|just tell me|give me the answer|"
    r"tell me the answer|can you (just )?solve)", re.I)
# Cross-session transplant safety: a donor response must not reference specifics of
# the donor session's student. (Manual review of every pair backstops this filter.)
CROSSREF_RE = re.compile(
    r"you (said|wrote|mentioned|got|tried|computed|found|had|were|noticed|used)|"
    r"your (equation|last|earlier|previous|answer|work|attempt|setup|calculation|"
    r"idea|number|value|guess)|as you|earlier you|before you|you'?ve (got|written|set)",
    re.I)


# ---------------------------------------------------------------- corpus enumeration
def run_meta(name: str):
    """(tutor_base, policy) for a main-corpus run dir name, else None."""
    if re.fullmatch(r"abl-s0-[a-z_]+-r\d+", name):
        return "sonnet", name[len("abl-s0-"):].rsplit("-r", 1)[0]
    m = re.fullmatch(r"conf-(gemini-|gpt-)?s0-(cold|conv|ped)-r\d+", name)
    if m:
        base = (m.group(1) or "sonnet").rstrip("-")
        return base, m.group(2)
    return None


def corpus_runs(src_logs: Path):
    out = []
    for d in sorted(src_logs.iterdir()):
        if not d.is_dir():
            continue
        meta = run_meta(d.name)
        if meta is not None:
            out.append((d, *meta))
    return out


def family_of(policy: str) -> str:
    return "ped" if policy.startswith("ped") else "conv"


def tracker_map(calls: list[dict]) -> dict:
    """(problem_id, turn_index) -> parsed state_tracker record, for runs that carry one."""
    out = {}
    for c in calls:
        t = c.get("tags") or {}
        if t.get("node") != "state_tracker":
            continue
        try:
            rec = json.loads(((c.get("response") or {}).get("text") or "").strip())
        except Exception:  # noqa: BLE001 - a garbled tracker line is just not joinable
            continue
        if isinstance(rec, dict) and "stuck" in rec:
            out[(t.get("problem_id"), t.get("turn_index"))] = rec
    return out


def context_turns(sm, vt) -> list[tuple[str, str]]:
    """The labeled dialogue turns strictly before the rated tutor turn, plus every
    student turn up to it — i.e. J.dialogue_for_turn minus the rated turn itself.
    census asserts the reassembly is byte-identical to the frozen renderer."""
    turns = []
    for r in sm.indep_items:
        if (r["problem_id"] == vt.problem_id and r["seq"] is not None
                and r["seq"] <= vt.first_seq):
            turns.append((r["seq"], "Student", r["text"]))
    for t in sm.visible_turns:
        if t.problem_id == vt.problem_id and t.first_seq < vt.first_seq:
            turns.append((t.first_seq, "Tutor", t.text))
    turns.sort(key=lambda x: x[0])
    return [(role, txt) for _, role, txt in turns]


def judged_turn_records(src_logs: Path, problems_by_id: dict):
    """One record per judged tutor turn across the 140-run corpus, with the
    byte-identity assertion against the frozen dialogue renderer."""
    records = []
    runs = corpus_runs(src_logs)
    assert len(runs) == 140, f"expected 140 corpus runs, found {len(runs)}"
    for run_dir, base, policy in runs:
        if policy == "cold":
            continue
        sm = M.analyze_session(run_dir, problems_by_id)
        calls = M.load_calls(run_dir)
        M.resolve_problem_ids(calls)
        trk = tracker_map(calls)
        for vt in sm.visible_turns:
            p = problems_by_id.get(vt.problem_id)
            if p is None or p.role != M.TRAINING_PHASE:
                continue
            if not M.tutor_in_window(sm.commit_seq, vt.problem_id, vt.first_seq):
                continue
            ctx = context_turns(sm, vt)
            reassembled = J.render_dialogue(ctx + [("Tutor", vt.text)])
            frozen = J.dialogue_for_turn(sm, vt)
            assert reassembled == frozen, (
                f"context+response reassembly diverged from the frozen renderer "
                f"({run_dir.name} {vt.problem_id} t{vt.turn_index})")
            if not ctx or ctx[-1][0] != "Student":
                continue  # a stimulus context must end with a student turn
            students = [t for r, t in ctx if r == "Student"]
            lk = p.leakage or {}
            records.append({
                "run": run_dir.name, "base": base, "policy": policy,
                "family": family_of(policy),
                "problem_id": vt.problem_id, "turn_index": vt.turn_index,
                "first_seq": vt.first_seq,
                "context": J.render_dialogue(ctx),
                "response": vt.text,
                "n_student_turns": len(students),
                "last_student": students[-1],
                "tracker": trk.get((vt.problem_id, vt.turn_index)),
                "leaks": bool(turn_leaks(vt.text, lk.get("numeric_form", []),
                                         lk.get("solution_form", []))),
                "has_question": "?" in vt.text,
                "n_words": len(vt.text.split()),
            })
    return records


# ---------------------------------------------------------------- priors
def struggle_score(rec: dict) -> float:
    """Lexical struggle prior over the context (sampling prior ONLY, never a label)."""
    ctx_students = [t for r, t in parse_context(rec["context"]) if r == "Student"]
    last = ctx_students[-1] if ctx_students else ""
    prev2 = ctx_students[-2:]
    s = 0.0
    if ASK_ANSWER_RE.search(last):
        s += 2.0
    s += min(2.0, sum(1.0 for t in prev2 if CONFUSION_RE.search(t)))
    if not M.attempts_reasoning(last):
        s += 1.0
    s += 0.5 * (rec["n_student_turns"] - 1)
    return s


def strong_prior(rec: dict) -> bool:
    last = rec["last_student"]
    return bool(M.attempts_reasoning(last)) and not CONFUSION_RE.search(last)


def _fmt_answer(x) -> str:
    f = float(x)
    return str(int(f)) if f.is_integer() else f"{f:g}"


def answer_forms(problem) -> list[str]:
    """Every numeric spelling of the canonical answer that counts as stating it.

    Uses the SAME list `protocol.leakage` checks (`leakage.numeric_form`, e.g.
    ['12', '12.0', '12.00']) plus the plain formatting, so this module and the
    leakage guard cannot disagree about what "the answer" looks like
    (AUDIT-2026-08-08 B1: the earlier single-token form missed '12.0'/'12.00').
    """
    forms = set(str(x) for x in ((problem.leakage or {}).get("numeric_form") or []))
    forms.add(_fmt_answer(problem.canonical_answer))
    return sorted(forms)


def _states_answer_in(text: str, problem) -> bool:
    # The lookbehind excludes a preceding '-' as well as digits/'.', so an
    # unrepaired sign error ("x = -21" against answer 21) is NOT read as stating
    # the answer — it is a live next step (AUDIT-2026-08-08 B1; recovered C061, C068).
    for ans in answer_forms(problem):
        if re.search(r"(?<![\d.\-])" + re.escape(ans) + r"(?!\d)(?!\.\d)", text):
            return True
    # A word-spelled resolution ("the answer is twenty-four") states the answer too.
    # Reusing the frozen matcher's solution_form list keeps this filter from being
    # NARROWER than the leak guard it exists to protect
    # (AUDIT-2026-08-08-preflight-review-3 N9). Verified inert on the frozen pool:
    # 0 of the 126 candidates change eligibility, so the selection is untouched.
    return turn_leaks(text, [], (problem.leakage or {}).get("solution_form") or [])


def states_answer(rec: dict, problems_by_id: dict) -> bool:
    """The student's latest turn already states the canonical answer."""
    return _states_answer_in(rec["last_student"], problems_by_id[rec["problem_id"]])


def problem_already_resolved(rec: dict, problems_by_id: dict) -> bool:
    """The named problem's answer appears ANYWHERE in the context.

    AUDIT-2026-08-08 B1. Scoping the answer check to the latest student turn let
    through contexts in which the tutor stated the answer earlier and the dialogue
    then moved on to a *different* problem (a pasted one, an invented practice one,
    or another topic entirely). Those items keep a `problem_id` that no longer
    describes their live content, which silently disables both this filter and the
    R_H answer-leak guard in `assemble`/`tests/test_stimuli.py`, and they carry no
    live scaffolding step for the named problem. Checked over the whole context.
    """
    return _states_answer_in(rec["context"], problems_by_id[rec["problem_id"]])


def is_eligible(rec: dict, problems_by_id: dict) -> bool:
    """Eligible == the context presents a live next reasoning step ON THE NAMED PROBLEM.

    Three independent disqualifiers:
      1. the latest student turn is a closing sign-off (CLOSING_RE);
      2. the latest student turn already states the canonical answer;
      3. the named problem is already resolved earlier in the context, so the
         dialogue has drifted past it (`problem_already_resolved`).

    (1) previously carried an undisclosed `and "?" not in last` escape hatch that
    exempted any wrap-up phrased as a question; it is removed here — the criterion
    now matches the prose in PREREGISTRATION §3 exactly. It changes no candidate's
    eligibility on the frozen pool.
    """
    last = rec["last_student"]
    closing_signoff = bool(CLOSING_RE.search(last))
    return not (closing_signoff
                or states_answer(rec, problems_by_id)
                or problem_already_resolved(rec, problems_by_id))


def parse_context(context: str) -> list[tuple[str, str]]:
    """Invert J.render_dialogue. Blocks are separated by blank lines and each block
    starts with 'Student: ' or 'Tutor: '; turn text may itself contain newlines."""
    turns: list[tuple[str, str]] = []
    for block in re.split(r"\n\n(?=(?:Student|Tutor): )", context):
        role, _, text = block.partition(": ")
        turns.append((role, text))
    return turns


# ---------------------------------------------------------------- census
def cmd_census(args):
    problems = M.problem_index(str(ROOT / "vendor/domain/algebra/problems.yaml"))
    recs = judged_turn_records(Path(args.src_logs), problems)
    n = len(recs)
    print(f"judged tutor turns: {n} (expected {EXPECTED_JUDGED_TURNS})")

    joined = [r for r in recs if r["tracker"] is not None]
    dist = Counter((bool(r["tracker"]["stuck"]), bool(r["tracker"]["progressed"]))
                   for r in joined)
    print(f"tracker-joinable turns: {len(joined)} (expected {EXPECTED_TRACKER_JOIN['n']})")
    for k in [(False, True), (True, True), (True, False), (False, False)]:
        print(f"  stuck={k[0]!s:5} progressed={k[1]!s:5}: {dist.get(k, 0):4d} "
              f"(expected {EXPECTED_TRACKER_JOIN[k]})")

    by_policy = Counter(r["policy"] for r in recs)
    leak_by_policy = Counter(r["policy"] for r in recs if r["leaks"])
    print("\nper-policy judged turns (leaks):")
    for pol in sorted(by_policy):
        print(f"  {pol:24s} {by_policy[pol]:4d}  ({leak_by_policy.get(pol, 0)} leak)")

    ok = (n == EXPECTED_JUDGED_TURNS and len(joined) == EXPECTED_TRACKER_JOIN["n"]
          and all(dist.get(k, 0) == EXPECTED_TRACKER_JOIN[k]
                  for k in [(False, True), (True, True), (True, False), (False, False)]))
    print(f"\ncensus check: {'PASS' if ok else 'MISMATCH — investigate before proceeding'}")

    census = {
        "judged_turns": n, "tracker_joined": len(joined),
        "tracker_distribution": {f"stuck={k[0]},progressed={k[1]}": dist.get(k, 0)
                                 for k in dist},
        "per_policy": dict(by_policy),
        "leaks_per_policy": dict(leak_by_policy),
        "reassembly_assertion": "byte-identical to analysis.judge.dialogue_for_turn "
                                "for every judged turn",
        "check_pass": ok,
    }
    (CORPUS / "census.json").write_text(json.dumps(census, indent=2))
    with open(CORPUS / "response_pools.jsonl", "w") as f:
        for r in recs:
            f.write(json.dumps(r) + "\n")
    print(f"wrote corpus/census.json and corpus/response_pools.jsonl ({n} rows)")
    return 0 if ok else 1


# ---------------------------------------------------------------- candidate sampling
def _rr_take(groups: dict, want: int, cap_per_run_problem: int = 2):
    """Round-robin over group keys, respecting a per-(run, problem) cap. Deterministic."""
    taken, used = [], Counter()
    keys = sorted(groups)
    idx = {k: 0 for k in keys}
    while len(taken) < want and any(idx[k] < len(groups[k]) for k in keys):
        for k in keys:
            if len(taken) >= want:
                break
            while idx[k] < len(groups[k]):
                r = groups[k][idx[k]]
                idx[k] += 1
                cap_key = (r["run"], r["problem_id"])
                if used[cap_key] < cap_per_run_problem:
                    used[cap_key] += 1
                    taken.append(r)
                    break
    return taken


def cmd_candidates(args):
    rng = random.Random(SEED)
    pools = [json.loads(l) for l in open(CORPUS / "response_pools.jsonl")]

    # ---- weak-prior candidates -------------------------------------------------
    ped_stuck = [r for r in pools if r["tracker"] and r["tracker"]["stuck"]]
    # visible textual struggle preferred, later turns before turn-0 openers
    # (labels come from the context alone, so the text should carry the evidence)
    ped_stuck.sort(key=lambda r: (r["turn_index"] == 0, -struggle_score(r),
                                  r["run"], r["turn_index"]))
    g = defaultdict(list)
    for r in ped_stuck:
        g[(r["base"], r["problem_id"])].append(r)
    weak_ped = _rr_take(g, want=34)

    conv = [r for r in pools if r["family"] == "conv"]
    conv_struggle = sorted(conv, key=lambda r: (-struggle_score(r), r["run"],
                                                r["turn_index"]))
    conv_struggle = [r for r in conv_struggle if struggle_score(r) >= 1.5]
    g = defaultdict(list)
    for r in conv_struggle:
        g[(r["base"], r["problem_id"])].append(r)
    weak_conv = _rr_take(g, want=20)

    # ---- strong-prior candidates -----------------------------------------------
    ped_ok = [r for r in pools
              if r["tracker"] and not r["tracker"]["stuck"] and r["tracker"]["progressed"]
              and strong_prior(r)]
    ped_ok.sort(key=lambda r: (r["run"], r["turn_index"]))
    g = defaultdict(list)
    for r in ped_ok:
        g[(r["base"], r["problem_id"])].append(r)
    strong_ped = _rr_take(g, want=22)

    conv_ok = [r for r in conv if strong_prior(r)]
    conv_ok.sort(key=lambda r: (r["run"], r["turn_index"]))
    g = defaultdict(list)
    for r in conv_ok:
        g[(r["base"], r["problem_id"])].append(r)
    strong_conv = _rr_take(g, want=20)

    seen, cands = set(), []
    for prior, rows in (("weak", weak_ped), ("weak", weak_conv),
                        ("strong", strong_ped), ("strong", strong_conv)):
        for r in rows:
            key = (r["run"], r["problem_id"], r["turn_index"])
            if key in seen:
                continue
            seen.add(key)
            cands.append({**r, "prior_stratum": prior,
                          "struggle_score": struggle_score(r)})
    rng.shuffle(cands)
    for i, c in enumerate(cands, 1):
        c["candidate_id"] = f"C{i:03d}"

    with open(CORPUS / "candidates.jsonl", "w") as f:
        for c in cands:
            f.write(json.dumps(c) + "\n")
    _write_sha(CORPUS / "candidates.jsonl")
    byf = Counter((c["prior_stratum"], c["family"]) for c in cands)
    print(f"candidate pool: {len(cands)} contexts "
          f"({sum(v for (s, _), v in byf.items() if s == 'weak')} weak-prior / "
          f"{sum(v for (s, _), v in byf.items() if s == 'strong')} strong-prior)")
    for k in sorted(byf):
        print(f"  {k}: {byf[k]}")
    print("wrote corpus/candidates.jsonl (+ .sha256)")


def cmd_topup(args):
    """Replay the frozen 30-item top-up recipe without reassigning candidate IDs.

    `candidates_topup.jsonl` is the pre-label sampling result. Recomputing that sample
    after eligibility code changed assigned C103/C106/C110/C124 to different source
    turns while the completed labels still joined by candidate ID. The recipe is now
    an immutable construction input: every source-derived field is checked against
    `response_pools.jsonl`, then its exact rows are appended to the 96-item pool.
    """
    pools = [json.loads(l) for l in open(CORPUS / "response_pools.jsonl")]
    existing = [json.loads(l) for l in open(CORPUS / "candidates.jsonl")]
    seen = {(c["run"], c["problem_id"], c["turn_index"]) for c in existing}
    if not TOPUP_RECIPE.exists():
        raise SystemExit(
            "missing frozen corpus/candidates_topup.jsonl; refusing to regenerate "
            "candidate identities after labels exist")
    new = [json.loads(l) for l in open(TOPUP_RECIPE) if l.strip()]
    if len(new) != args.n:
        raise SystemExit(
            f"frozen top-up has {len(new)} rows, but -n requested {args.n}; "
            "the labelled recipe cannot be resized")
    existing_ids = {c["candidate_id"] for c in existing}
    overlap = sorted(existing_ids & {c["candidate_id"] for c in new})
    if overlap:
        raise SystemExit(
            f"top-up IDs already exist ({overlap[:3]}); start from "
            "corpus/candidates.pre-topup.jsonl")

    pool_by_key = {(r["run"], r["problem_id"], r["turn_index"]): r for r in pools}
    for row in new:
        key = (row["run"], row["problem_id"], row["turn_index"])
        if key in seen:
            raise SystemExit(f"frozen top-up is not disjoint from the base pool: {key}")
        source = pool_by_key.get(key)
        if source is None:
            raise SystemExit(f"frozen top-up source turn is missing: {key}")
        expected = {**source, "prior_stratum": "strong",
                    "struggle_score": struggle_score(source),
                    "candidate_id": row["candidate_id"]}
        if row != expected:
            raise SystemExit(
                f"frozen top-up row {row['candidate_id']} no longer matches its "
                f"source turn {key}")

    with open(CORPUS / "candidates.jsonl", "a") as f:
        for c in new:
            f.write(json.dumps(c) + "\n")
    _write_sha(CORPUS / "candidates.jsonl")
    print(f"top-up: replayed {len(new)} frozen candidates "
          f"({new[0]['candidate_id']}..{new[-1]['candidate_id']}); "
          f"pool now {len(existing) + len(new)}")


# ---------------------------------------------------------------- selection (post-labels)
def cmd_select(args):
    """Deterministic selection of up to 30 weak + 30 strong labelled candidates.

    Rule (pre-specified before any label existed; see decisions-log 2026-08-08):
    eligible = candidates whose 3 blind reps reached >= 2/3 agreement on competence
    AND whose context presents a live next reasoning step (`is_eligible`; added
    2026-08-08 before any judge call, applied identically to both strata).
    Within each labelled stratum, order by (unanimity desc, mean confidence desc,
    candidate_id asc) and take greedily under coverage caps: <= 7 per problem,
    <= 2 per (run, problem) [already enforced at candidate stage], relaxing the
    problem cap to 9 then 12 only if 30 cannot otherwise be reached. If a stratum
    has < 30 eligible members, take all and report the imbalance. The explicit
    pre-data material exclusions above are applied before this unchanged ordering.
    """
    cands = {c["candidate_id"]: c
             for c in (json.loads(l) for l in open(CORPUS / "candidates.jsonl"))}
    labels = [json.loads(l) for l in open(ROOT / "labeling/labels.jsonl")]
    problems = M.problem_index(str(ROOT / "vendor/domain/algebra/problems.yaml"))
    by_stratum = defaultdict(list)
    n_ineligible = Counter()
    for lab in labels:
        if lab["candidate_id"] in PRE_DATA_EXCLUSIONS:
            continue
        if not lab["agreement_ok"]:
            continue
        if not is_eligible(cands[lab["candidate_id"]], problems):
            n_ineligible[lab["competence"]] += 1
            continue
        by_stratum[lab["competence"]].append(lab)
    print(f"dropped for no live next step: {dict(n_ineligible)}")

    conf_ord = {"low": 0, "medium": 1, "high": 2}
    selected = {}
    for stratum in ("weak", "strong"):
        rows = sorted(by_stratum.get(stratum, []),
                      key=lambda l: (-int(l["unanimous"]),
                                     -sum(conf_ord[c] for c in l["confidences"]),
                                     l["candidate_id"]))
        for cap in (7, 9, 12):
            picked, per_problem = [], Counter()
            for lab in rows:
                if len(picked) >= 30:
                    break
                pid = cands[lab["candidate_id"]]["problem_id"]
                if per_problem[pid] >= cap:
                    continue
                per_problem[pid] += 1
                picked.append(lab["candidate_id"])
            if len(picked) >= 30 or cap == 12:
                break
        selected[stratum] = picked
        print(f"{stratum}: {len(picked)} selected "
              f"({len(by_stratum.get(stratum, []))} eligible; problem cap used: {cap})")

    out = {"rule": cmd_select.__doc__.strip(), "selected": selected,
           "n_eligible": {k: len(v) for k, v in by_stratum.items()},
           "pre_data_exclusions": PRE_DATA_EXCLUSIONS,
           "n_dropped_no_agreement": sum(1 for l in labels if not l["agreement_ok"]),
           "n_dropped_no_live_step": dict(n_ineligible)}
    (CORPUS / "selection.json").write_text(json.dumps(out, indent=2))
    print("wrote corpus/selection.json")


# ---------------------------------------------------------------- pairing
# Pairing v2 (decisions-log 2026-08-08). v1 mined a counterpart response with a
# lexical heuristic (has_question / leaks) plus same-problem_id + length matching.
# Manual review showed that is not sufficient: same problem_id does not imply the
# donor tutor was discussing the same thing (one graft imported a "working
# together" rate discussion into a mixture context), and question-vs-no-question
# separates phrasing rather than scaffolding LEVEL.
#
# v2 keeps the build prompt's order of preference — a real corpus turn wherever
# one genuinely fits, an authored counterpart otherwise — but resolves it by
# REVIEW rather than by regex: for each stimulus we emit a packet (context, the
# real next turn, and ranked same-problem candidates from each pole's pool), a
# blind reviewer picks a fitting corpus candidate or authors the counterpart, and
# every decision is validated and spot-checked before freeze.

# Policy pools follow the build prompt: ped* and conv_socratic are the natural
# high-scaffolding sources; plain conv is the low-scaffolding source.
ELICIT_POLICIES = {"ped", "ped_no_gate", "ped_no_cascade", "ped_no_tracker",
                   "conv_socratic", "conv_no_final_answer"}
PERFORM_POLICIES = {"conv", "conv_no_final_answer", "ped", "ped_no_gate",
                    "ped_no_cascade", "ped_no_tracker"}
_WORD_RE = re.compile(r"[a-z0-9]+")
_STOP = set("the a an and or of to in is are was were be been for on with that this "
            "it as at by from i you we so but if then not no yes do does did can "
            "could would should have has had my your our their there here what".split())


def _content_words(text: str) -> set:
    return {w for w in _WORD_RE.findall((text or "").lower())
            if w not in _STOP and len(w) > 1}


def _similarity(a: str, b: str) -> float:
    """Jaccard over content words — how alike are the two students' latest turns."""
    wa, wb = _content_words(a), _content_words(b)
    return len(wa & wb) / len(wa | wb) if (wa or wb) else 0.0


def _rank_candidates(pool, rec, pole, k=4):
    """Ranked same-problem donor turns whose donor student-state resembles this one."""
    scored = []
    for c in pool:
        if c["problem_id"] != rec["problem_id"]:
            continue
        if c["run"] == rec["run"]:            # never reuse this dialogue's own session
            continue
        if CROSSREF_RE.search(c["response"]):  # would name the donor's student
            continue
        if not (12 <= c["n_words"] <= 140):
            continue
        pols = ELICIT_POLICIES if pole == "high" else PERFORM_POLICIES
        if c["policy"] not in pols:
            continue
        sim = _similarity(rec["last_student"], c["last_student"])
        turn_pen = 0.05 * abs(c["turn_index"] - rec["turn_index"])
        scored.append((sim - turn_pen, c))
    scored.sort(key=lambda x: (-x[0], x[1]["run"], x[1]["turn_index"]))
    return [c for _, c in scored[:k]]


def cmd_packets(args):
    """Emit corpus/packets/packet_{n}.json — the blind pairing-review inputs."""
    pools = [json.loads(l) for l in open(CORPUS / "response_pools.jsonl")]
    cands = {c["candidate_id"]: c
             for c in (json.loads(l) for l in open(CORPUS / "candidates.jsonl"))}
    sel = json.loads((CORPUS / "selection.json").read_text())
    chosen = [cands[cid] for s in ("weak", "strong") for cid in sel["selected"][s]]

    # Re-selection reuses decisions already made for stimuli that stayed selected;
    # only newly-selected stimuli need a fresh packet.
    done = set()
    for p in sorted((CORPUS / "reviews").glob("packet_*.jsonl")):
        done |= {json.loads(l)["candidate_id"] for l in p.read_text().splitlines()
                 if l.strip()}
    chosen = [c for c in chosen if c["candidate_id"] not in done]
    if not chosen:
        print("every selected stimulus already has a pairing decision")
        return

    problems = M.problem_index(str(ROOT / "vendor/domain/algebra/problems.yaml"))
    elicit_pool = [r for r in pools if r["has_question"] and not r["leaks"]]
    perform_pool = [r for r in pools if r["leaks"] or not r["has_question"]]

    (CORPUS / "packets").mkdir(exist_ok=True)
    items = []
    for rec in chosen:
        hi = _rank_candidates(elicit_pool, rec, "high")
        lo = _rank_candidates(perform_pool, rec, "low")
        items.append({
            "candidate_id": rec["candidate_id"],
            "problem_statement": problems[rec["problem_id"]].prompt.strip(),
            "context": rec["context"],
            "real_next_turn": rec["response"],
            "elicit_candidates": [{"ref": f"E{i+1}", "text": c["response"]}
                                  for i, c in enumerate(hi)],
            "perform_candidates": [{"ref": f"P{i+1}", "text": c["response"]}
                                   for i, c in enumerate(lo)],
            "_src": {"real": [rec["run"], rec["turn_index"]],
                     **{f"E{i+1}": [c["run"], c["turn_index"]] for i, c in enumerate(hi)},
                     **{f"P{i+1}": [c["run"], c["turn_index"]] for i, c in enumerate(lo)}},
        })

    per = 10
    existing = len(list((CORPUS / "packets").glob("packet_*.json")))
    n = 0
    for b in range(0, len(items), per):
        chunk = items[b:b + per]
        n += 1
        public = [{k: v for k, v in it.items() if k != "_src"} for it in chunk]
        (CORPUS / "packets" / f"packet_{existing + n}.json").write_text(
            json.dumps({"instructions": PAIRING_BRIEF, "items": public}, indent=1))
    srcs_path = CORPUS / "packets" / "_sources.json"
    srcs = json.loads(srcs_path.read_text()) if srcs_path.exists() else {}
    srcs.update({it["candidate_id"]: it["_src"] for it in items})
    srcs_path.write_text(json.dumps(srcs, indent=1))
    print(f"wrote {n} packets over {len(items)} stimuli "
          f"(median elicit candidates {sorted(len(i['elicit_candidates']) for i in items)[len(items)//2]}, "
          f"perform {sorted(len(i['perform_candidates']) for i in items)[len(items)//2]})")


PAIRING_BRIEF = """\
You are constructing paired tutor responses for a study of tutoring quality.

For each item you get: the algebra problem the dialogue is about, the DIALOGUE
CONTEXT (ending with the student's latest message), the tutor turn that actually
came next in that session, and pools of candidate tutor turns taken from other
sessions on the SAME problem.

Your job per item is to produce TWO alternative replies to this same context:

  R_HIGH (high scaffolding): responds to where this student actually is and
          prompts the student to take the next reasoning step themselves. It may
          give a hint, a partial structure, or a focused question, but it must
          LEAVE the next step for the student and must NOT state the final answer.

  R_LOW  (low scaffolding): performs the step for the student — states the result,
          works the algebra out, or gives the final answer — without asking the
          student to produce anything.

Both must be plausible replies to THIS context and to THIS problem.

Procedure per item:
 1. Decide which pole the real_next_turn serves: "high" or "low". Judge by what it
    does (elicits vs performs), not by whether it contains a question mark.
 2. For the OTHER pole, first look at the candidate list for that pole
    (elicit_candidates for high, perform_candidates for low). If one of them is a
    coherent reply to THIS context — it addresses what this student just said and
    does not refer to anything that did not happen here — choose it by its ref.
 3. If none fits, AUTHOR the counterpart yourself. Match the real turn's length
    (within roughly +/-40%), register, and formatting conventions (the corpus mixes
    plain prose with occasional markdown/LaTeX). Do not mention any tutoring
    strategy, policy, or system by name. Do not address the student by name.
 4. Never let the two poles be paraphrases of each other; the difference must be
    WHO does the next reasoning step.

Output one JSON object per item, in order, as JSON Lines:
{"candidate_id": "Cxxx", "real_turn_pole": "high"|"low",
 "counterpart_source": "corpus"|"authored",
 "counterpart_ref": "E2"|"P1"|null,
 "counterpart_text": "<full text if authored, else null>",
 "note": "<= 15 words on why>"}
"""


def cmd_assemble(args):
    """Validate the review decisions and assemble corpus/pairing_draft.jsonl."""
    cands = {c["candidate_id"]: c
             for c in (json.loads(l) for l in open(CORPUS / "candidates.jsonl"))}
    srcs = json.loads((CORPUS / "packets" / "_sources.json").read_text())
    packets = {}
    for p in sorted((CORPUS / "packets").glob("packet_*.json")):
        for it in json.loads(p.read_text())["items"]:
            packets[it["candidate_id"]] = it

    sel = json.loads((CORPUS / "selection.json").read_text())["selected"]
    selected = {cid for s in ("weak", "strong") for cid in sel[s]}

    decisions = {}
    for p in sorted((CORPUS / "reviews").glob("packet_*.jsonl")):
        for line in p.read_text().splitlines():
            if line.strip():
                d = json.loads(line)
                decisions[d["candidate_id"]] = d
    missing = sorted(selected - set(decisions))
    assert not missing, f"no pairing decision for: {missing}"
    # Re-selection can leave decisions for stimuli that are no longer selected
    # (e.g. dropped by the eligibility filter); they are kept on disk as a record
    # but must not enter the frozen set.
    dropped = sorted(set(decisions) - selected)
    decisions = {k: v for k, v in decisions.items() if k in selected}
    if dropped:
        print(f"  ignoring {len(dropped)} decision(s) for de-selected stimuli: {dropped}")

    problems = M.problem_index(str(ROOT / "vendor/domain/algebra/problems.yaml"))
    rows, problems_found = [], []
    for cid, d in sorted(decisions.items()):
        rec, pk = cands[cid], packets[cid]
        real = {"text": rec["response"], "provenance": "corpus",
                "source_run": rec["run"], "source_turn_index": rec["turn_index"]}
        if d["counterpart_source"] == "corpus":
            ref = d["counterpart_ref"]
            pool = (pk["elicit_candidates"] if ref.startswith("E")
                    else pk["perform_candidates"])
            match = [c for c in pool if c["ref"] == ref]
            assert match, f"{cid}: unknown candidate ref {ref}"
            run, ti = srcs[cid][ref]
            other = {"text": match[0]["text"], "provenance": "corpus",
                     "source_run": run, "source_turn_index": ti}
        else:
            text = (d.get("counterpart_text") or "").strip()
            assert text, f"{cid}: authored counterpart is empty"
            other = {"text": text, "provenance": "authored",
                     "source_run": None, "source_turn_index": None}

        if d["real_turn_pole"] == "high":
            rh, rl = real, other
        else:
            rh, rl = other, real

        lk = (problems[rec["problem_id"]].leakage or {})
        if turn_leaks(rh["text"], lk.get("numeric_form", []), lk.get("solution_form", [])):
            problems_found.append(f"{cid}: R_H leaks the answer")
        if rh["text"].strip() == rl["text"].strip():
            problems_found.append(f"{cid}: poles identical")
        for pole, r in (("R_H", rh), ("R_L", rl)):
            if r["provenance"] == "corpus" and r["source_run"] != rec["run"] \
                    and CROSSREF_RE.search(r["text"]):
                problems_found.append(f"{cid}: {pole} transplant carries a cross-reference")
        rows.append({"candidate_id": cid, "r_high": rh, "r_low": rl,
                     "real_turn_pole": d["real_turn_pole"],
                     "review_note": d.get("note", "")})

    # No donor turn may serve two stimuli. AUDIT-2026-08-08 N6: the same corpus turn
    # was transplanted into more than one stimulus, so those stimuli shared half their
    # text and were not independent observations — but the bootstrap in §6.5 resamples
    # stimuli as if they were. Checked on the text, so it catches a repeat reached via
    # different refs as well.
    seen: dict[str, tuple[str, str]] = {}
    for r in rows:
        for pole in ("r_high", "r_low"):
            txt = r[pole]["text"].strip()
            if txt in seen:
                other_cid, other_pole = seen[txt]
                problems_found.append(
                    f"{r['candidate_id']}:{pole} duplicates {other_cid}:{other_pole} "
                    f"(same donor text in two stimuli)")
            else:
                seen[txt] = (r["candidate_id"], pole)

    with open(CORPUS / "pairing_draft.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    prov = Counter((r["r_high"]["provenance"], r["r_low"]["provenance"]) for r in rows)
    poles = Counter(r["real_turn_pole"] for r in rows)
    authored_pole = Counter(p for r in rows for p, v in
                            (("R_H", r["r_high"]), ("R_L", r["r_low"]))
                            if v["provenance"] == "authored")
    print(f"assembled {len(rows)} pairs")
    print(f"  provenance (R_H, R_L): {dict(prov)}")
    print(f"  real turn served pole: {dict(poles)}")
    print(f"  authored responses by pole: {dict(authored_pole)}  "
          f"(balance matters: authoring must not be confounded with the contrast)")
    if problems_found:
        print(f"  VALIDATION PROBLEMS ({len(problems_found)}):")
        for p in problems_found:
            print("   ", p)
    else:
        print("  validation: all checks pass")
    return 1 if problems_found else 0


# ---------------------------------------------------------------- freeze + verify
def cmd_freeze(args):
    rng = random.Random(SEED + 1)
    cands = {c["candidate_id"]: c
             for c in (json.loads(l) for l in open(CORPUS / "candidates.jsonl"))}
    labels = {l["candidate_id"]: l
              for l in (json.loads(ln) for ln in open(ROOT / "labeling/labels.jsonl"))}
    pairs = {r["candidate_id"]: r
             for r in (json.loads(l) for l in open(CORPUS / "pairing_draft.jsonl"))}
    sel = json.loads((CORPUS / "selection.json").read_text())
    chosen_ids = [cid for s in ("weak", "strong") for cid in sel["selected"][s]]

    for cid in chosen_ids:
        p = pairs[cid]
        assert p["r_high"]["text"] and p["r_low"]["text"], f"{cid}: unresolved pole"

    order = list(chosen_ids)
    rng.shuffle(order)
    stimuli = []
    for i, cid in enumerate(order, 1):
        rec, p, lab = cands[cid], pairs[cid], labels[cid]
        stimuli.append({
            "stimulus_id": f"S{i:02d}",
            "candidate_id": cid,
            "source_run": rec["run"], "base": rec["base"], "policy": rec["policy"],
            "family": rec["family"],
            "problem_id": rec["problem_id"], "turn_index": rec["turn_index"],
            "first_seq": rec["first_seq"],
            "context": rec["context"],
            "r_high": p["r_high"]["text"], "r_low": p["r_low"]["text"],
            "r_high_provenance": p["r_high"]["provenance"],
            "r_low_provenance": p["r_low"]["provenance"],
            "r_high_source_run": p["r_high"]["source_run"],
            "r_high_source_turn_index": p["r_high"]["source_turn_index"],
            "r_low_source_run": p["r_low"]["source_run"],
            "r_low_source_turn_index": p["r_low"]["source_turn_index"],
            "competence_label": lab["competence"],
            "evidence_strength": lab["evidence_strength"],
            "sampling_prior_stratum": rec["prior_stratum"],
            "real_turn_pole": p["real_turn_pole"],
            "pairing_note": p.get("review_note", ""),
        })
    with open(CORPUS / "stimuli.jsonl", "w") as f:
        for s in stimuli:
            f.write(json.dumps(s) + "\n")
    _write_sha(CORPUS / "stimuli.jsonl")

    # copy only the referenced run dirs' calls.jsonl (reconstruction inputs)
    src_logs = Path(args.src_logs)
    referenced = sorted({s["source_run"] for s in stimuli}
                        | {s["r_high_source_run"] for s in stimuli if s["r_high_source_run"]}
                        | {s["r_low_source_run"] for s in stimuli if s["r_low_source_run"]})
    for run in referenced:
        dst = CORPUS / "logs" / run
        dst.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_logs / run / "calls.jsonl", dst / "calls.jsonl")
    print(f"froze corpus/stimuli.jsonl ({len(stimuli)} stimuli, sha256 written); "
          f"copied {len(referenced)} run dirs into corpus/logs/")


def cmd_verify(args):
    problems = M.problem_index(str(ROOT / "vendor/domain/algebra/problems.yaml"))
    stimuli = [json.loads(l) for l in open(CORPUS / "stimuli.jsonl")]
    sms = {}

    def sm_for(run):
        if run not in sms:
            sms[run] = M.analyze_session(CORPUS / "logs" / run, problems)
        return sms[run]

    def vt_for(run, pid, ti):
        sm = sm_for(run)
        for vt in sm.visible_turns:
            if vt.problem_id == pid and vt.turn_index == ti:
                return sm, vt
        raise AssertionError(f"{run} {pid} t{ti}: judged turn not found")

    n_ctx = n_resp = 0
    for s in stimuli:
        sm, vt = vt_for(s["source_run"], s["problem_id"], s["turn_index"])
        rebuilt = J.render_dialogue(context_turns(sm, vt))
        assert rebuilt == s["context"], f"{s['stimulus_id']}: context mismatch"
        n_ctx += 1
        for pole in ("r_high", "r_low"):
            if s[f"{pole}_provenance"] != "corpus":
                continue
            _, dvt = vt_for(s[f"{pole}_source_run"], s["problem_id"],
                            s[f"{pole}_source_turn_index"])
            assert dvt.text == s[pole], f"{s['stimulus_id']}: {pole} text mismatch"
            n_resp += 1
    sha = (CORPUS / "stimuli.sha256").read_text().split()[0]
    actual = hashlib.sha256((CORPUS / "stimuli.jsonl").read_bytes()).hexdigest()
    assert sha == actual, "stimuli.sha256 does not match stimuli.jsonl"
    print(f"verify PASS: {n_ctx} contexts and {n_resp} corpus-sourced responses "
          f"rebuilt byte-identical from corpus/logs; sha256 matches")


def _write_sha(path: Path):
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    path.with_suffix(".sha256").write_text(f"{sha}  {path.name}\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cmd", choices=["census", "candidates", "topup", "select",
                                    "packets", "assemble", "freeze", "verify"])
    ap.add_argument("--src-logs", default=str(DEFAULT_SRC_LOGS),
                    help="frozen source corpus logs dir (read-only)")
    ap.add_argument("-n", type=int, default=30, help="topup: how many to append")
    args = ap.parse_args()
    return {"census": cmd_census, "candidates": cmd_candidates, "topup": cmd_topup,
            "select": cmd_select, "packets": cmd_packets, "assemble": cmd_assemble,
            "freeze": cmd_freeze, "verify": cmd_verify}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
