# Decisions log — label-vs-evidence

Chronological record of every design decision and deviation. Newest entries at the bottom.
Companion source repo (`$SRC`): `conv-vs-ped-tutor` @ `ab5ea2a99d67cc2b23808c52e841301c5e56d887` (clean tree).

---

## 2026-08-08 — Build start, environment, vendoring

- **Build agent**: Claude (Fable 5) via Claude Code, working autonomously from the frozen build
  prompt. Python 3.12.8 (miniforge base env; all `requirements.txt` deps already installed —
  no venv created, `requirements.txt` records the floor versions for reproduction).
- **Vendored transitive dependencies beyond the build prompt's table.** `analysis/metrics.py`
  hard-imports `protocol.leakage`, `protocol.session`, `agents.extraction`,
  `domain.algebra.checker`; `protocol/session.py` imports `agents.cold_baseline` (constants
  only, no further deps). All copied verbatim, read-only, recorded in `vendor/PROVENANCE.md`.
  `configs/models.yaml` also vendored (not in the table, but it defines the `judge` role the
  build prompt names). `agents/base.py`, `ped_tutor.py`, `conv_tutor.py`, `full_session.py`,
  and langgraph are NOT vendored — nothing we run needs the tutor graph.
- **Vendor layout mirrors the source package layout under `vendor/`**, so
  `agents.config.REPO_ROOT` (parent of `agents/`) resolves to `vendor/` and the vendored
  modules' relative-path behavior (`configs/models.yaml`, `domain/algebra/problems.yaml`)
  works unchanged. New code adds `vendor/` to `sys.path`.
- **The 140-run corpus identified** as `abl-s0-*` (50 runs: 5 ablation policies × 10 reps,
  sonnet tutor base) + `conf[-gemini|-gpt]-s0-{cold,conv,ped}` (90 runs: 3 conditions × 3
  tutor bases × 10 reps). `cold` has no tutor turns; the 7 judged tutor policies are
  conv, ped (× 3 bases) and conv_no_final_answer, conv_socratic, ped_no_cascade,
  ped_no_gate, ped_no_tracker (sonnet base). Calibration/smoke/judge/preflight run dirs in
  `$SRC/logs` are not part of the corpus.
- **Cost basis re-verified from `$SRC/logs/pedjudge-20260704-210950-761`**: 3,120 calls,
  mean 1,639.6 input / 52.0 output tokens — matches the build prompt.
- **Git**: repo initialized. Per the build prompt ("Do not commit or push without being
  asked" + the build order's explicit "freeze …, tag it"), commits are made ONLY at the
  named freeze milestones, each with a tag; no pushes.

## 2026-08-08 — Freeze-order refinement (candidate pool → labels → stimulus freeze)

The build prompt freezes `stimuli.jsonl` (60 items, 30 weak / 30 strong **per the Phase 3
labels**) before Phase 3 runs. Those two requirements conflict: a pre-frozen 60 cannot be
guaranteed 30/30 under labels that do not yet exist. Resolution (recorded here as a
deviation in build order, not in design):

1. Freeze a **candidate pool** (`corpus/candidates.jsonl`, ~90 contexts, hashed) built with
   the sampling priors (tracker for PedTutor-family, lexical struggle score for
   ConvTutor-family — priors only, never analysis labels).
2. Run the blind labelling pass over ALL candidates (contexts only).
3. Apply a **pre-specified deterministic selection rule** (written down in
   `protocol/PREREGISTRATION.md` terms before labels are seen; implemented in
   `corpus/build_stimuli.py select`) to pick 30 weak + 30 strong.
4. Pair R_H / R_L for the selected 60, then freeze `stimuli.jsonl` + `labels.jsonl`
   together, tagged, **before any judge call**. The "freeze before scoring" non-negotiable
   is fully honored; nothing downstream of judge scores touches stimulus selection.

If a stratum has fewer than 30 labelled members, the rule is: take all of that stratum,
top up nothing, run with the imbalance, and report it (no re-sampling after labels).

## 2026-08-08 — Census result (Phase 2 gate)

`build_stimuli.py census` over the 140-run corpus: **2,219 judged tutor turns (exact
match)**; per-turn context+response reassembly asserted byte-identical to the frozen
`analysis.judge.dialogue_for_turn` for all 2,219. Tracker join: **990** records vs the
build prompt's 991 — cells (False,True)=844, (True,True)=100, (True,False)=39 match the
prompt exactly; (False,False) is 7 vs the prompt's 8. Investigated: not a parse-tolerance
issue (no tracker line is recoverable by tolerant-JSON extraction that strict parsing
misses); an unwindowed join gives 1092, so the prompt's variant is some third measurement.
The delta is one record in the ambiguous never-sampled cell; the weak-stratum constraint
(139 stuck=True) and the strong cell match exactly, so sampling is unaffected. Census
expectation pinned to the reproducible measurement (990/7). Also noted: `ped_no_cascade`
logs tutor prose under the `state_tracker` node tag on some turns — correctly non-joinable.
The build prompt's per-policy leak figures (ped 14/223, conv 52/135) are single-base
(sonnet) counts; the 3-base totals measured here (ped 45/668, conv 199/511, and
conv_socratic 4/223 exactly) are consistent with them.

## 2026-08-08 — Labelling rubric v2 (one disclosed instrument revision, pre-judging)

The v1 blind pass (3 reps × 96 candidates, zero <2/3-agreement dropouts, 84/96
unanimous) produced 20 weak / 76 strong — far from the 30/30 the design needs, and
inspection shows a construct mismatch rather than corpus reality: v1's strong bar
("a correct equation setup OR a correct algebraic/arithmetic step" anywhere in
context) marks as strong (a) students who compute one micro-step at the tutor's
direct prompting and then say they cannot form the equation (e.g. C002), (b)
students whose CURRENT attempt contains an unrepaired algebra error (C005), and in
at least one case (c) pure post-walkthrough parroting (C006). The study's construct
— the source plan's "the same visibly struggling learner", the state the judge's
rated response replies to — is CURRENT-STATE competence as of the latest student
turn.

Decision: ONE rubric revision (v2: current-state framing with explicit boundary
rules for prompted micro-steps, unrepaired errors, and parroting), full blind
relabel from scratch (3 fresh reps × 96, same blindness, same aggregation), v1
fully archived in labeling/v1-archive/ and released alongside v2. Zero judge calls
exist; the binding freeze ("freeze before scoring") is untouched. The v1→v2
confusion table will be reported. Whatever v2 yields is final: if a stratum still
has <30 members, take all of it and report the imbalance — no further instrument
iteration, no post-label re-sampling.

## 2026-08-08 — Paid-run credential situation

No `ANTHROPIC_API_KEY` exists in this environment (not in the shell env, no `.env`
anywhere, no dotfile reference, no `ant` CLI profile) — the source study's keys were
evidently exported per terminal session and never persisted. The build therefore
completes everything up to and including the offline gates (mock end-to-end, manifest,
frozen artifacts, tags), and the live sequence (`--preflight` → `--pilot 12` → paid
run) is left as a documented one-command-each sequence for the operator to run with
the key exported. The runner fails fast and clearly without the key (LiveCaller
raises before any state is touched).

## 2026-08-08 — v2 labels complete; v1→v2 relationship is strictly monotone

v2 blind pass complete (3 reps × 96, fresh contexts, rep-specific shuffles).
Result: **65 weak / 31 strong**, 0 dropped for <2/3 agreement, 89/96 unanimous.
Inter-rep pairwise agreement 94.8% / 94.8% / 95.8% — the v2 instrument is reliable,
so the v1-vs-v2 difference is a construct difference, not annotation noise.

v1→v2 confusion (`labeling/v1_v2_confusion.json`), n=96:

| | v2 weak | v2 strong |
|---|---|---|
| **v1 weak** | 20 | **0** |
| **v1 strong** | 45 | 31 |

The revision is **strictly monotone**: it moved 45 items strong→weak and *zero*
items weak→strong. That is precisely and only the tightening the v2 boundary rules
specify (prompted micro-steps, unrepaired current errors, parroting no longer count
as strong); the rubric change did not re-shuffle the construct in an unconstrained
way. Cohen's κ(v1,v2) = 0.22 and evidence-strength agreement 64.6% reflect that
deliberate shift. Both tables are released. **No further instrument iteration.**

Operational note: 5 of the 9 v2 batch agents hit a provider credit limit at the very
end of their run; each had already written its complete output file, and the 5
genuinely missing labels (rep2 ×4, rep3 ×1) were filled by fresh blind agents on the
same v2 rubric with the same blindness protocol (`labeling/batches/rep{2,3}_fill.json`).
Every merged rep file was validated for schema, duplicates, and full 96-item coverage.

## 2026-08-08 — Pairing v2: review packets replace heuristic mining (pre-freeze)

Selection produced 30 weak / 30 strong (problem cap 7; 65 and 31 eligible). The
first pairing pass resolved all 120 poles from corpus turns with zero authoring —
which looked ideal until the pairs were actually read. Three failure modes, all
present in the first three pairs inspected:

* **Incoherent graft.** C006's R_H was transplanted from a session that shared the
  `problem_id` but whose tutor was discussing a *"working together" rate problem*
  (hourly rates, 2.4 hours) — grafted onto a mixture-problem context. Same
  `problem_id` does not imply the donor tutor was talking about the same thing.
* **No real contrast.** C001's two poles were both long expository turns.
* **Phrasing, not scaffolding.** C002's poles said the same pedagogical thing, one
  as a question and one as an instruction. `has_question`/`leaks` separates surface
  form, not who does the next reasoning step.

The heuristic is retired. Pairing v2 keeps the build prompt's order of preference
(a real corpus turn wherever one genuinely fits; author the counterpart otherwise)
but resolves it by **review** instead of regex:

1. `build_stimuli.py packets` emits, per stimulus, the problem statement, the full
   context, the real next turn, and up to 4 ranked same-problem candidates per pole.
   Candidates are drawn from the build prompt's policy pools (ped*/conv_socratic for
   elicit, conv-family for perform), exclude the stimulus's own run, exclude any turn
   containing a cross-reference to its donor's student, and are ranked by content-word
   similarity between the donor's and this stimulus's latest student turn.
2. Six blind reviewers (fresh contexts; they see no competence labels, no profiles,
   no policy names) decide which pole the real turn serves and either select a
   fitting candidate or author the counterpart matched for length and register.
3. `build_stimuli.py assemble` validates every decision (R_H must not leak the
   answer, poles must differ, transplants must carry no cross-reference) and reports
   the provenance split.

**Design property worth stating explicitly: authoring must not be confounded with
the R_H/R_L contrast.** Because the real turn serves whichever pole it actually
serves, roughly half the stimuli get a corpus R_H + authored R_L and half the
reverse. If authoring were always on one pole, any authoring artifact (fluency,
register, length) would be perfectly confounded with the scaffolding manipulation
and would masquerade as a profile-independent effect. `assemble` reports the
per-pole authored counts and `tests/test_stimuli.py` asserts neither pole is
overwhelmingly authored.

## 2026-08-08 — Stimulus eligibility: contexts must present a live next step

Reading the first completed pairing reviews surfaced a **corpus-eligibility** defect
(not a review defect). Three items in one packet — C006, C024, C029 — are
post-resolution wrap-ups: the student has finished the problem and is thanking the
tutor. The reviewer, correctly following the brief, had to *invent a new mini-problem*
to manufacture an R_H ("imagine adding water instead...", "picture a version where you
combine 10% and 70%..."). In such a context there is no next reasoning step, so the
R_H/R_L difference is "opens new work" vs "closes warmly" — not a scaffolding
contrast. Left in, those items would contaminate Δ and the four-cell table with a
different construct, and they would do so unevenly (5 of 30 strong vs 2 of 30 weak).

Why they got through: the frozen answer-phase window (`tutor_in_window`) only excludes
turns after a *marked* `FINAL ANSWER:` commit. Students who solved a training problem
without emitting the marker leave their wrap-up turns inside the window.

**Criterion added (`is_eligible`, applied identically to both strata, before any judge
call):** a stimulus context is eligible only if its latest student turn is not a
closing sign-off and does not already state the canonical answer.

Applying it to the 96-candidate pool leaves 63 weak but only 26 strong — below the
pre-specified 30. Rather than invoke the "take all and report the imbalance" clause
for a shortfall *I* created by adding a filter late, the pool was topped up:
`build_stimuli.py topup -n 30` appended 30 strong-prior candidates (C097–C126),
drawn deterministically from the 987 unsampled judged turns that pass the eligibility
filter and a tightened strong prior, spread 5 per problem across 10 runs and all three
tutor bases, disjoint from the existing pool. They were labelled by the **unchanged v2
rubric** under the same 3-rep blind protocol.

This is stimulus construction, not analysis: zero judge calls exist, the labelling
instrument is untouched, the selection rule is unchanged and deterministic, and the
30/30 target predates everything. Disclosed here and in the pre-registration; the
pre-top-up pool is preserved at `corpus/candidates.pre-topup.jsonl`.

## 2026-08-08 — Re-selection after eligibility + top-up

126-candidate pool labelled (unchanged v2 rubric): **84 weak / 42 strong**, 0 dropped
for <2/3 agreement, 115/126 unanimous. The top-up's yield was 19 weak / 11 strong —
lower than the ~52% strong the prior predicted, which is itself evidence the v2 rubric
is strict rather than prior-driven.

Eligibility dropped 4 weak and 10 strong, leaving 80 weak / 32 strong eligible; the
deterministic rule then selected the pre-specified **30 / 30** at problem cap 7.

Effect on the pairing work already done: 47 of the 60 previously-reviewed stimuli
remain selected and their decisions are reused verbatim; 13 were de-selected (the 7
post-resolution items plus 6 displaced on the frozen ordering) and 13 newly-selected
top-up stimuli were sent for fresh blind review. De-selected decisions stay on disk as
a record but are excluded by `assemble`.

Pairing outcome over the first 60 reviewed: real turn served the high pole 43 times
and the low pole 17, giving 24 authored R_L against 12 authored R_H. The residual
imbalance is disclosed and bounded by a test; it is provably inert for the primary
endpoint, because identical R_H/R_L texts are judged in all three arms, so any
stimulus-level authoring artifact cancels exactly in Δ(P_nov) − Δ(P_adv).

## 2026-08-08 — Manipulation check, stimulus freeze, dry runs

**Manipulation check (new, added pre-freeze; PREREGISTRATION §4b).** Δ is only
interpretable if the two poles really differ in scaffolding level, so before freezing
we verified that independently of the judge: blind raters saw each context with its
two responses as "A"/"B" in randomised order and said which leaves more of the next
reasoning step to the student, explicitly ignoring tone, length, formatting, and
mathematical correctness. Result: **60/60 correct, 0 reversed, 0 tied**
(`corpus/manip/report.json`). No stimulus was dropped on this basis; it is a validity
report, and no judge call existed.

**Freeze.** `corpus/stimuli.jsonl` frozen (60 stimuli, 30/30) + sha256; 37 referenced
run dirs copied into `corpus/logs/`. `verify` rebuilds all 60 contexts and all 88
corpus-sourced responses byte-identically from those copies.

Provenance of the frozen set: R_H is 55 corpus / 5 authored; R_L is 33 corpus /
27 authored; 28 stimuli (12 weak, 16 strong) use no authored text at all and back the
pre-registered authoring-robustness analysis.

**Test-suite note.** `test_context_ends_with_a_student_turn` initially failed on 39 of
60 stimuli. The data was correct and the *test* was wrong: turns are separated by a
blank line followed by a speaker label, and a student turn may itself contain blank
lines, so a bare `"\n\n"` split is not a turn split. The pipeline always used the
structured turn list (which is why `verify` passed); only the test used the naive
split. Fixed to split on the same boundary the renderer uses. All 40 tests now pass,
including the full 1,080-call mock end-to-end and the offline-replay tripwire, which
now exercise the real frozen stimuli rather than skipping.

**Dry run.** `--manifest-only`: 360 units, 1,080 calls, est **$10.60**, worst case
$35.42 under the $40 cap. Contract hash
`41ec4f6696d773202a94729b575061ed6164b929d49fc551a20df9b69b584eb8`.
