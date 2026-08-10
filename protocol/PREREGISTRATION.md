# Pre-registration — Do Pedagogy-Aware LLM Judges Generalize Across Student Ability Levels?

**Status: FINAL FREEZE CANDIDATE; zero paid judge calls made.** The material is not a
valid live run target until every file is committed and `HEAD` carries a
`prereg-final-*` tag. The runner enforces both conditions before preflight, then binds
the exact request code, runtime, dependencies and frozen inputs in
`contract_sha256`; every later live command aborts on drift. These controls were
added after the independent pre-flight audit in `protocol/AUDIT-2026-08-08.md`
(Amendments A2–A4, all made with zero judge scores in existence). Anything analyzed
beyond §6 is exploratory and will be labelled as such.

Format: 2 pages, one figure. Companion full paper:
the conv-vs-ped-tutor study (source corpus `ab5ea2a99d67cc2b23808c52e841301c5e56d887`),
whose frozen pedagogy-judge instrument this study reuses verbatim.

---

## 1. Research question

When a learner's **stated** profile conflicts with the competence the learner
**demonstrates** in the dialogue, does a pedagogy-aware LLM judge ground its rating
in the behavioural evidence, or does it anchor on the supplied label?

The manipulation is on the **judge**, not the tutor. Dialogues and candidate tutor
responses are held fixed; the only randomised factor is the learner profile shown to
the judge. No new tutoring sessions are generated; zero student or tutor model calls
are made. **"Ability levels" in the title are stated learner profiles supplied to the
judge** (the manipulated factor, randomised within-stimulus); demonstrated competence
varies **observationally** across frozen transcripts (the stratification factor,
independently labelled). No student simulation differs between conditions.

## 2. Design

- **Stimuli**: 55 dialogue contexts (Amendments A2 and A4) drawn from the frozen 2,219 judged tutor turns of
  the source corpus (140 runs; 7 tutor policies × 3 tutor bases), each context ending
  with a student turn, split from the tutor turn the source study's judge rated.
  Each stimulus carries two candidate responses to the same context: a
  high-scaffolding `R_H` (responds to where the student is and leaves the next
  reasoning step to them; never states the answer) and a low-scaffolding `R_L`
  (performs that step for them). One pole is the session's real next tutor turn; the
  counterpart is either another corpus turn on the same problem that genuinely fits
  this context, or an authored reply matched for length and register — decided by
  blind review, never by keyword heuristic (decisions-log 2026-08-08). Provenance is
  recorded per response and the split is reported.
- **Authoring, and how far its cancellation argument actually reaches.** Because the
  real turn serves whichever pole it actually serves, authored counterparts fall on
  `R_H` for some stimuli and `R_L` for others. **The split is heavily uneven and we
  state the true figure rather than a bound: authored text sits on `R_L` 26 times and
  on `R_H` twice** (Amendment A3; the source tutors are pedagogically tuned, so the
  real turn is the high pole in 43 of 55 stimuli). `tests/test_stimuli.py` pins
  those exact counts, so the disclosed number cannot drift from the artifact; the
  previous assertion (≥10 corpus responses per pole) was described here as a
  "lopsidedness bound" but would have passed with almost any imbalance.
  The imbalance is nevertheless **inert for the primary endpoint under additivity**:
  the identical `R_H`/`R_L` texts are judged in all three arms, so a stimulus-level
  artifact δ (authoring fluency, length, register) that shifts a pole's score by the
  same amount in every arm enters every arm's Δ equally and cancels in
  `PAG = Δ(P_nov) − Δ(P_adv)`. Such an artifact can shift the *level* of Δ in the
  four-cell table; under additivity it cannot create or hide a Profile Anchoring Gap,
  which is a within-stimulus difference of differences.
  **What that argument does not cover**, and we say so rather than claiming exact
  cancellation: an artifact that *interacts* with the profile — if, say, the judge
  reacts differently to authored register when told the learner is advanced — does
  not cancel. The §6.3 all-corpus re-estimate (27 stimuli) is the check on that, and
  it is reported whatever it shows.
- **Arms** (within-stimulus, the manipulated factor):
  `D` (dialogue + response), `P_nov` (novice profile + dialogue + response),
  `P_adv` (advanced profile + dialogue + response). Profile texts are frozen in
  `profiles/profiles.yaml`, length-matched, and contain no dialogue hints and no
  instruction to the judge about how to weigh them. They are **not** a minimal
  contrast on ability: each also states a help-seeking preference ("usually need
  step-by-step help" against "usually work through problems independently without
  help"), which is the construct the rubric's `assistance_calibration` dimension
  scores directly. The endpoint is therefore profile *influence*, not anchoring on an
  ability label alone — see **Amendment A5**, recorded before any judge call.
- **Demonstrated competence** (between-stimulus, the stratification factor): 30 weak /
  25 strong per the independent blind labels (§3; the strong stratum is short of 30
  under §4's take-all clause and one invalid pair was excluded before data collection
  — Amendments A2 and A4). Cells (novice profile, weak) and
  (advanced, strong) are **congruent**; (advanced, weak) and (novice, strong) are
  **conflict** cells.
- **Judge**: the source study's frozen pedagogy judge — `claude-opus-4-8`, Anthropic,
  temperature omitted, max_tokens 512, system prompt `PED_SYSTEM` verbatim; user
  message `PED_USER` verbatim with, in profile arms only, a frozen profile block
  prepended. Three reps per (stimulus, arm, response); reps are genuine stochastic
  samples (no seed on the Anthropic path, as in the source study).
- **Size**: 55 × 3 × 2 = 330 units; × 3 reps = 990 paid calls (Amendment A4).
- **Score**: `overall` (1–5) parsed by the frozen `parse_pedagogy_scores`; per-unit
  score = mean of the 3 reps (`aggregate_reps`, unchanged). Sub-scores are reported
  descriptively in the supplement.

## 3. Independent competence labels

The tutor's own state-tracker records were used ONLY as a sampling prior (they come
from the tutor's planner and share a model family with the judge; using them as
ground truth would be circular). The analysis stratum comes from a separate blind
labelling pass:

- Input per item: the dialogue **context only** — never the candidate responses, the
  tracker record, or any policy/base metadata.
- Frozen rubric (`labeling/RUBRIC.md`, **v2**): CURRENT-STATE demonstrated competence
  (weak/strong) as of the latest student turn, ordinal **evidence strength**
  (ambiguous / moderate / strong), and confidence. **One disclosed instrument
  revision preceded the final labels** (decisions-log 2026-08-08): the v1 rubric's
  strong bar ("any correct step anywhere in the context") mislabelled prompted
  micro-steps, unrepaired current errors, and solution-parroting as strong; v2 adds
  explicit boundary rules for those cases. v1 is archived in full (rubric + all
  per-rep labels, `labeling/v1-archive/`) and the v1→v2 confusion table is reported.
  The revision happened with zero judge scores in existence; no further revision is
  permitted after the v2 labels.
- 3 independent blind reps (fresh contexts, rep-specific shuffles and batch splits),
  majority vote. **Correction (Amendment A3):** earlier drafts reported "0 items
  dropped for <2/3 agreement" as a reliability result. With three reps and a binary
  label, the majority is 2 or 3 by pigeonhole, so that gate can never fire and the
  count is a tautology, not a finding. The reliability evidence is the **unanimity
  rate** (115/126) and the **pairwise inter-rep agreement** (94.4 / 94.4 / 93.7 % over
  the 126-candidate pool; 94.8 / 94.8 / 95.8 % over the earlier 96-item pool). The
  `agreement_ok` field is retained in the released `labels.jsonl` for compatibility
  and is annotated as structurally-always-true in `labeling/label_competence.py`.
- **Labeller identity (disclosed)**: three fresh Claude (Fable 5) agent contexts run
  through the build harness, each seeing only the rubric and the shuffled contexts.
  This removes the tutor-pipeline circularity but is family-correlated with the judge
  (as the build prompt's paid alternative — an API labelling pass — would also have
  been); `labeling/label_competence.py api` implements that alternative as a
  robustness path. Limitation stated in the abstract's notes.
- **Stimulus eligibility.** A context qualifies only if it presents a *live next
  reasoning step*: its latest student turn must not be a closing sign-off and must not
  already state the canonical answer (`is_eligible`). Post-resolution wrap-ups survive
  the source study's answer-phase window whenever the student solved a training
  problem without emitting a `FINAL ANSWER:` marker, and in such a context no
  scaffolding contrast exists — R_L is a closing remark and any R_H must invent new
  work. The criterion was added before any judge call and applies identically to both
  strata (decisions-log 2026-08-08). Applying it left 63 weak but only 26 strong of
  the original 96-candidate pool, so the pool was topped up with 30 further
  strong-prior candidates drawn deterministically from the eligible unsampled turns
  and labelled under the **unchanged** v2 rubric and the same 3-rep blind protocol.
  **Corrected implementation (Amendment A2).** The first implementation of
  `is_eligible` scoped its answer check to the *latest student turn* only, and
  exempted any wrap-up containing a question mark (an escape hatch that was never
  disclosed here). It therefore admitted contexts in which the tutor had stated the
  named problem's answer earlier and the dialogue had moved on to a *different*
  problem — a pasted one, an invented practice one, or another topic entirely. Those
  items keep a `problem_id` that no longer describes their live content, which
  silently disables both this filter and the R_H answer-leak guard. The criterion now
  has three disqualifiers — closing sign-off, answer in the latest student turn, and
  the named problem already resolved anywhere in the context — matched against every
  numeric spelling of the answer that `protocol.leakage` checks, with a lookbehind
  that no longer reads an unrepaired sign error (`x = -21`) as stating the answer.
- Selection of the final 55 from the 126-candidate pool follows the deterministic rule
  frozen in `corpus/build_stimuli.py select` (eligibility and ≥2/3 agreement, then
  unanimity, then confidence, then candidate id, under per-problem coverage caps),
  followed by the single pre-data material exclusion in Amendment A4. Candidate C018
  is excluded because its latest student turn contains an unrepaired arithmetic error
  and its nominal `R_H` endorses that error; the pair therefore changes correctness,
  not only scaffolding. No paid judge score existed when this exclusion was made.

## 4. Deliberate deviations from the source plan

Recorded as decisions, not omissions (build prompt; decisions-log 2026-08-08):

1. **The profile-only arm (`P + R`, no dialogue) is cut.** (a) The 2-page budget —
   Judge 1 vs Judge 3 carries the whole result; (b) rating a tutor turn with no
   dialogue requires a different user template (the frozen rubric says "read in the
   context of the dialogue shown"), breaking the byte-identical-except-profile-block
   invariant and the commensurability argument; (c) that profiles alone move
   learner-conditioned scores is already established (EduPanel) — it is not this
   study's question. If wanted, it is a separately-frozen template variant (~720
   calls, ~$4–5), never folded into the main arms.
2. **Evidence strength is an annotated covariate, not a third manipulated factor.**
   The Phase 3 pass rates it per stimulus; §6.4 tests whether profile influence
   shrinks as evidence strengthens. No extra stimuli or calls.
3. **Rubric scoring is the instrument, not forced-choice pairwise preference.**
   Independent scoring reuses the frozen pedagogy rubric verbatim (commensurable with
   the companion study). A forced-choice variant may be run later as a clearly
   labelled exploratory robustness check, never as the primary.

Additional recorded deviation from the build prompt's ordering: the stimulus freeze
happens **after** the label freeze (candidate pool → labels → deterministic selection
→ stimulus freeze), because a pre-label freeze cannot guarantee the 30/30 split the
design targets. Both freezes precede any judge call. If a stratum has < 30 eligible
members, we take all of it and report the imbalance (no post-label re-sampling).
**This clause was invoked: see Amendments A2 and A4** — the strong stratum has 26
otherwise eligible members; after the pre-data exclusion of C018, all 25 valid pairs
are retained. The final design is 30 weak / 25 strong.

## 4b. Manipulation check (run before freeze, reported)

Δ is only interpretable if `R_H` and `R_L` genuinely differ in scaffolding level. A
blind, order-randomised check verifies this independently of the judge and of the
profile manipulation: raters see the context and the two responses as "A"/"B" in
random order and say which leaves more of the next reasoning step to the student,
explicitly ignoring tone, length, formatting, and mathematical correctness
(`corpus/manipulation_check.py`; result in `corpus/manip/report.json`). It is a
validity report, not a selection step — no stimulus is dropped on the basis of a
judge score, and no judge call exists at this point. A pair the raters call reversed
is a construction defect and is repaired before freeze; the final rate is reported in
the paper.

**How much this check can carry (Amendment A3).** Two limits, stated rather than
glossed. (i) Each pair is rated **once**, so the reported figure is agreement with the
construction key — did the rater recover the pole the pairing review assigned — and is
**not** an inter-rater reliability statistic; `report.json` now names the field
`key_agreement_rate` and records `n_raters_per_pair`. (ii) The poles carry surface
cues that correlate almost perfectly with the contrast in this material: a question
mark appears in 37 of 55 `R_H` against 1 of 55 `R_L` (in all 36 pairs where exactly
one pole has one, it is `R_H`), and `\boxed{}` in 0 `R_H` against 18 `R_L`. This is
partly structural — the corpus candidate pools are still filtered by `has_question` /
`leaks` in `build_stimuli.py packets` — so a rater matching on punctuation alone would
score near-perfectly without reading for scaffolding. The brief therefore now names
question marks, formatting and length explicitly as features that must not decide the
answer, and offers "tie" as the honest response when both replies leave the same work
undone. The check is reported as a **construction check** on the pairing review, not
as independent evidence that Δ measures scaffolding.

## 5. Frozen artifacts

The frozen-input manifest covers the actual files, not their sidecars:
`corpus/stimuli.jsonl`, `corpus/candidates_topup.jsonl`, `labeling/labels.jsonl`,
`profiles/profiles.yaml`, `vendor/analysis/judge_pedagogy.py`,
`vendor/configs/models.yaml`, `vendor/supplement/judge_pedagogy_rubric.md`,
`judging/profile_judge.py`, `judging/run_study.py`, `analysis/analyze.py`,
`requirements.txt`, and this document. Their hashes are in
`results/frozen_inputs.sha256`.

The live contract binds every manifest entry, the model and request parameters,
system and user templates, profile blocks, arms, poles, reps, schedule seed, executed
request modules, Python version, and installed Anthropic SDK version. A live preflight
also binds the clean tagged git commit. The runner checks the complete contract on
every later invocation. No live cache entry is accepted unless an fsynced wire row
with the same key, scores, served model and provider response id exists and its
canonical row hash matches. Transactional promotion records sha256 hashes for every
final result file and records whole-cache and whole-wire hashes; analysis recomputes
all of them and verifies the exact unique result grid before reading outcomes. These
are aborting gates, not provenance annotations
(Amendment A4).

## 6. Analysis plan

The stimulus-level contrast is defined first. Per (stimulus s, arm a), the
scaffolding preference is

    Δ_s(a) = S_s(R_H | a) − S_s(R_L | a)

with S the per-unit mean `overall`. Multiple selected stimuli can come from the same
generated tutoring session and are not independent. The **independent inferential
unit is therefore the source run**: every registered stimulus-level estimand is first
averaged within `source_run`, and tests and confidence intervals use those source-run
means. The final set contains 23 source runs: 18 represented in the weak stratum and
10 represented in the strong stratum (some runs contribute to both strata).

**6.1 Headline object — the four-cell table** of mean Δ by (profile, demonstrated
competence): Δ(nov, weak), Δ(adv, weak), Δ(nov, strong), Δ(adv, strong). Each is the
unweighted mean of source-run means in that cell, with a source-run bootstrap CI
(§6.5).

**6.2 Primary endpoint — the Profile Anchoring Gap in the weak stratum:**

    PAG_s = Δ_s(P_nov) − Δ_s(P_adv)
    PAG_run = mean of PAG_s within source run and stratum
    PAG_weak = mean over the 18 weak-stratum source-run means

Sign convention (matches the source plan): positive = the advanced label suppresses
the judge's scaffolding preference for the same visibly struggling learner.
Primary test: two-sided exact conditional Wilcoxon signed-rank on the 18
weak-stratum source-run means against 0, with a source-run BCa bootstrap CI on mean
PAG_weak and the rank-biserial correlation as effect size. A null (CI tight around 0)
is a publishable finding, but **only conditionally** — see **Amendment A5**. The frozen
system prompt instructs the judge to "Base your rating only on the dialogue shown", and
the profile block sits outside that dialogue, so "grounded in behavioural evidence" and
"obeyed an instruction to ignore the profile" predict the same null. The registered
reading is therefore: a null PAG_weak supports evidence-grounding **only if** the §6.3
pure profile effect is non-null, i.e. only if the judge demonstrably used the profile at
all. If both are null, the registered conclusion is **not** that the profile did not reach
the rating: **Amendment A6** shows the two poles already sit at 4.55 and 1.78 on a 1-5
scale, so a profile effect in one direction is largely unobservable, and a joint null is
registered as **uninformative** between "the profile did not reach the rating" and "the
profile effect fell in the direction this scale cannot express". Either way it is a
statement about this instrument rather than about evidence-grounding.
We report effect sizes with CIs, not null-vs-significant dichotomies.

**6.3 Secondary (labelled as such):**
- PAG_strong (same estimator, strong stratum).
- Movement from the no-profile control: Δ_s(P_x) − Δ_s(D) per profile and stratum —
  in conflict cells this is the plan's anchoring score S(R | P_conflict, D) − S(R | D).
- **Pure profile effect on absolute scores** (the plan's "crucial comparison"):
  S_s(R | P_adv) − S_s(R | P_nov) per response pole, same transcript and response,
  only the metadata differing.
- **Authoring robustness (pre-registered).** Re-estimate the primary endpoint on the
  subset of stimuli whose *both* poles are real corpus turns (27 stimuli: 12 weak,
  15 strong — but **8 and 7 source runs**, which is what the test actually sees, so its
  floor on p is 0.0078 / 0.0156 against the primary's 7.6e-06; Amendment A6.6). Note this
  subset removes authored text but **not** the base × pole confound (A6.5). Authoring is
  heavily on `R_L`
  (26 of 28 authored responses; Amendment A3), and although an additive artifact is
  inert for PAG by construction (§2), this subset removes the question entirely.
  Reported alongside the primary,
  whatever it shows.
- Per-field decomposition of the primary over the four rubric sub-scores.

**6.4 Profile influence × evidence strength (secondary):** within each source run,
average `|PAG_s|` and the ordinal evidence-strength value; compute their Spearman
correlation across all 23 source runs (direction: negative = influence shrinks as
evidence strengthens).
Framing per the source plan: a rational evaluator may legitimately lean on the
profile when evidence is ambiguous (it is a prior); the failure mode is profile
influence that persists undiminished under strong evidence. We do NOT pre-register
"evidence should always beat the label."

> **Scope limit, recorded at freeze (see Amendment A1).** The frozen 55 span only
> two evidence levels — `moderate` (37) and `strong` (18); the pool's 8 `ambiguous`
> items were all excluded as a side-effect of the confidence-ordered selection rule.
> §6.4 is therefore a two-level contrast, and it cannot speak to the ambiguous end,
> which is precisely where leaning on a profile would be most defensible. The
> selection rule was **not** re-tuned to recover them: it was frozen before any label
> existed, the gain would be ~4 items per stratum, and re-cutting a frozen rule after
> seeing the covariate is the behaviour the freeze exists to prevent. Reported as a
> limitation.

**6.5 Statistics:** paired throughout; source run as the independent unit; BCa
bootstrap (10,000 resamples, seed 13) resampling source-run means within stratum. The
two-sided signed-rank p-value is computed by dynamic programming over the exact
conditional sign distribution, using average ranks for tied absolute differences.
Mathematically equal thirds are rounded to 12 decimal places for tie assignment.
Zero differences are dropped using a 1e-9 tolerance; an all-zero sample returns
p = 1 and rank-biserial 0. Exact dependency versions and Python 3.12.8 are frozen in
the contract, but the p-value no longer depends on SciPy's changing `method="auto"`
rules. No multiplicity correction on the single primary endpoint; secondaries are
descriptive with CIs.

**Precision, stated in advance.** We do not claim the earlier independence-based
half-width calculation: it treated 30 weak stimuli as independent even though they
come from 18 source runs, and no defensible intraclass correlation is available before
the run. The realised source-run BCa interval and its half-width will be reported. A
null result will be described only at the resolution supported by that interval, not
as evidence of no effect.

**6.6 Exclusions:** none at analysis time — the completeness gate guarantees
n_valid = 3 for every unit before promotion, and stimulus selection closed at §3.
The sole material exclusion, C018, was made and recorded before the final stimulus
freeze and before any paid judge score existed (Amendment A4); it is not an
outcome-dependent analysis exclusion.
If the paid run cannot reach completeness under the $40 cap, the study stops and the
incompleteness is reported; no partial-data analysis is promoted.

## 7. One figure

x-axis: demonstrated competence (weak → strong); y-axis: preference for high
scaffolding (Δ); two lines (stated novice, stated advanced) with CIs; the D-arm
control shown as a reference. Parallel, closely-spaced lines = behaviour-driven
judge; wide separation = profile anchoring.

## 7b. Amendments after the `prereg-frozen` tag

Recorded here rather than silently edited. No judge call had been made at the time of
either entry, and neither is data-dependent.

**A1 (2026-08-08) — evidence-strength coverage of the frozen set.** Composition audit
of the frozen 60 found `moderate` 37 / `strong` 23 / `ambiguous` 0. §6.4's three-level
framing was written before the materials existed; the text above now states the actual
two-level scope. The design was not changed to chase the missing level. (After A2 the
frozen 56 span `moderate` 38 / `strong` 18 / `ambiguous` 0; the conclusion is
unchanged.)

**A2 (2026-08-08) — the frozen set is 56 stimuli, 30 weak / 26 strong.** An
independent pre-flight audit (`protocol/AUDIT-2026-08-08.md`, finding B1) found that
eight of the frozen 60 had drifted past the problem their `problem_id` names: the
named problem was solved earlier in the context and the live content belonged to a
different problem — in one case a work-rate problem, outside the labelling rubric's
stated mixture/weighted-average domain. Because every guard keys on `problem_id`, this
disabled the eligibility filter and the R_H answer-leak check on those items (one
item's R_H stated its live problem's answer while `turn_leaks`, pointed at the named
problem, reported nothing), and the contamination was uneven across the stratification
factor — 6 strong against 2 weak.

`is_eligible` was corrected (§3) and the frozen deterministic selection rule re-run
**unchanged**. It rejects exactly those eight and nothing else, and leaves 75 weak but
only 26 eligible strong candidates in the whole pool. Per §4's standing contingency —
"If a stratum has < 30 eligible members, we take all of it and report the imbalance
(no post-label re-sampling)" — the strong stratum is taken entire at 26 rather than
topped up a second time. Two weak backfills and one strong (C021) needed new pairing
decisions; they were produced by fresh blind reviewers under the unchanged packet
brief, seeing no labels, no profiles and no policy names. **No judge call existed at
the time of this amendment**, the labelling instrument is untouched, and the selection
rule was not re-tuned. The superseded selection is preserved at
`corpus/selection.pre-drift-fix.json`. Design: 56 × 3 × 2 × 3 = **1,008 calls, ~$9.90**.

**A3 (2026-08-08) — corrections to reported statistics and to the analysis code.**
From the same audit, none data-dependent (no judge score existed):

1. *Primary test.* `wilcoxon_report` dropped zero differences with `vals != 0`. A
   per-unit score is a mean of three integers, so an exactly-zero PAG lands on
   ±4.44e-16 and survived that filter, entering the signed-rank test as its
   smallest-magnitude difference with a sign set by floating-point rounding order.
   On real-shaped data this moved the primary p by .06 and the pre-registered
   rank-biserial effect size by .03. Zeros are now dropped with a 1e-9 tolerance,
   verified against exact rational arithmetic.
2. *Per-field decomposition* (§6.3, last bullet) was pre-registered but not
   implemented; it is now implemented, before any data exists.
3. *Agreement gate.* See §3: "0 items below 2/3 agreement" was a tautology and is
   replaced by unanimity and pairwise inter-rep agreement.
4. *Authoring split.* The true figure (26 authored `R_L` against 2 authored `R_H`) is
   stated in §2 and pinned by test, replacing a "lopsidedness bound" that was not one.
5. *Freeze enforcement.* `contract_sha256` and `frozen_inputs()` hashed the sidecar
   *text files* rather than `stimuli.jsonl` / `labels.jsonl` themselves, so either
   artifact could be edited after scoring with no tripwire; `analyze.py` re-read the
   strata from `stimuli.jsonl` at analysis time with no check at all. Both now hash
   the artifacts and refuse on mismatch.
6. *Disclosures added* to §6.3 (the cancellation argument holds under additivity, not
   exactly) and to the limitations: the tutor family is nearly collinear with the
   competence stratum (ped 23 weak / 9 strong; conv 7 weak / 17 strong), and the
   R_H/R_L contrast carries surface cues (a question mark in 37/56 R_H against 1/56
   R_L; `\boxed{}` in 0/56 R_H against 18/56 R_L) — **[figures in this item describe the
   56-stimulus set A3 was written against and are superseded by A4 and A5: the frozen 55
   are ped 23 weak / 8 strong, and the denominators are 55, not 56]** — that the
   manipulation check cannot
   fully control — so §4b's 56/56 result is reported as a construction check, not as
   independent evidence that Δ measures scaffolding.

**A4 (2026-08-08) — remediation of the remaining pre-flight blockers.** A second
adversarial pass was completed before any provider call or judge score. It produced
the following frozen corrections.

1. The 30-row top-up is now a checked-in replay recipe. A clean reconstruction
   (`topup → select → assemble → freeze → verify`) reproduces the candidates,
   selection, pairing and stimuli byte for byte; it no longer depends on the source
   repository's current unsampled-turn ordering.
2. C018 is excluded before the final freeze. Its latest student turn makes an
   unrepaired arithmetic error and its nominal high-scaffolding response endorses
   that error, so the pair confounds correctness with scaffolding. The final set is
   55 stimuli (30 weak / 25 strong), 330 units and 990 valid paid calls. The blind
   construction check is correspondingly 55/55.
3. The independent inference unit is the source run, not the stimulus. All registered
   estimands are averaged within source run before testing or bootstrapping. The
   signed-rank implementation now uses exact conditional sign enumeration with valid
   handling of ties, sparse nonzero samples and all-zero samples.
4. Live preflight requires a clean `prereg-final-*` tagged commit. The request
   contract binds all frozen inputs, the exact executable request path, Python and SDK
   versions. The SDK is instantiated with `max_retries=0`; each charged outer attempt
   issues exactly one provider request. Invalid, non-finite or above-$40 caps are
   rejected, and a persisted cap cannot be raised on resume.
5. Accepted live cache rows are cryptographically joined to fsynced wire records that
   contain the provider response id and full raw response. Promotion hashes every
   final result file, and analysis rejects any hash mismatch, duplicate, missing or
   extra result unit before computing statistics.

The final composition is `moderate` 37 / `strong` 18; tutor family ped 31 / conv 24
(weak: ped 23 / conv 7; strong: ped 8 / conv 17); and 27 all-corpus pairs (12 weak /
15 strong). Authored-response and punctuation counts stated above are unchanged.

**A5 (2026-08-08) — construct-validity disclosures and composition facts found by a
third pre-flight audit** (`protocol/AUDIT-2026-08-08-preflight-review-3.md`). A third
adversarial pass was completed **before any provider call and with zero judge scores in
existence**. It changed no stimulus, no label, no profile text and no registered
estimand: `corpus/stimuli.jsonl` and `labeling/labels.jsonl` still hash to
`1d240ebc…8c5376` and `fda2bc3d…2707d4`. What follows is disclosure, recorded here
rather than left to be noticed after the data exists.

1. **The instrument instructs the judge to ignore the manipulated factor.** The frozen
   `PED_SYSTEM` ends with "Base your rating only on the dialogue shown", and opens with
   "read in the context of the dialogue shown"; the profile block is prepended to the
   user message, outside the triple-quoted `DIALOGUE:` region. The instrument was reused
   verbatim for commensurability with the companion study and is **not** changed here.
   The consequence is registered in §6.2: a null primary endpoint is evidence of
   evidence-grounding only if §6.3's pure profile effect is non-null. §4.1(b) already
   cited this clause for a different purpose; that it also bears on the main
   manipulation was not previously stated.

2. **The profiles bundle stated ability with a stated assistance need** (§2). "Usually
   need step-by-step help" versus "usually work through problems independently without
   help" is precisely what `assistance_calibration` scores, so a positive PAG is
   consistent with a *correctly* calibrated evaluator as well as with label anchoring.
   Deliberately not fixed by editing the profile texts: they were frozen before any
   judge call, and re-cutting the manipulation after an audit is the behaviour the
   freeze exists to prevent. The endpoint is reported as profile influence, and the
   ability-anchoring reading is offered only where the pure profile effect and the
   evidence gradient support it.

3. **The strong stratum is entirely strong-sampling-prior.** Prior × blind label over
   the 126-candidate pool is {(weak,weak) 45, (strong,weak) 39, (weak,strong) 9,
   (strong,strong) 33}; after eligibility it is {38, 37, 1, 25}; over the frozen 55 it
   is {23, 7, 0, 25}. The nine candidates whose blind label overturned the prior toward
   "strong" are the only counterexamples in the pool, and eight fail `is_eligible` while
   the ninth is C018, removed by A4's pre-data exclusion. §3's insistence that the
   tracker is a sampling prior and not ground truth remains true of the *procedure*, but
   the released materials contain no case where the blind pass overturned the prior
   toward "strong", so that independence is not testable inside the frozen set and the
   strong stratum inherits any bias the prior carries. This affects §6.1, PAG_strong and
   §6.4; the primary endpoint is within-stimulus and is unaffected.

4. **The eligibility filter is strongly family-differential.** It drops 24 of 70
   conv-family candidates (34%) against 1 of 56 ped-family (2%); by policy,
   `conv_no_final_answer` 44%, `conv` 33%, `ped` 2%. Its only operative disqualifier is
   "the named problem is already resolved somewhere in the context", which is close to a
   description of what the conv policies do. A3.6's disclosure that tutor family is
   nearly collinear with the competence stratum stands; this records that a filter added
   after the labels existed is part of what produced that shape.

5. **23 of the 55 contexts contain no tutor turn at all** — a single student message,
   `turn_index == 0` — and they are concentrated in the strong stratum (16 of 25 strong,
   7 of 30 weak). The amount of behavioural evidence available to ground a rating is
   therefore systematically smaller in the strong stratum while the profile block is a
   constant 95 tokens, which confounds every weak-versus-strong comparison. "55 dialogue
   contexts" in §2 should be read as "55 rating contexts, 23 of them a single student
   turn". The within-stimulus primary endpoint is unaffected.

6. **Corrected figures.** A3.6's "ped 23 weak / 9 strong" and its `/56` denominators
   describe the superseded 56-stimulus set; the frozen 55 are ped 23 weak / 8 strong,
   with a question mark in 37 of 55 `R_H` against 1 of 55 `R_L` and `\boxed{}` in 0
   against 18. §4b and A4 already carry the correct values; A3 is annotated in place
   rather than rewritten. §2's "7 tutor policies × 3 tutor bases" is loose: the corpus is
   140 runs — 5 ablation policies × 10 replicates on the sonnet base, plus 3 conditions ×
   3 bases × 10 replicates — and only `conv` and `ped` exist on all three bases.

7. **Integrity fixes to the executed code**, none of which touch a registered estimand:
   `--offline-cache-only` now aborts on any disagreement with the promoted finals
   instead of silently overwriting them; `analysis/analyze.py` verifies its own digest
   and this document's against the ones the run recorded before computing anything; a
   reply carrying no usage accounting is refused and retried rather than raising inside
   the cost computation; and `is_eligible` now also matches `protocol.leakage`'s
   word-spelled `solution_form` answers (verified inert — 0 of the 126 candidates change
   eligibility, and the byte-identical reconstruction of the frozen 55 still passes).

**A6 (2026-08-10) — the response scale is asymmetrically censored against one direction of
the primary endpoint, and a base × pole confound** (`protocol/AUDIT-2026-08-10-endpoint-sensitivity.md`).
A fourth adversarial pass was completed **before any provider call and with zero judge
scores in existence**. It changed no stimulus, no label, no profile text and no registered
estimand: `corpus/stimuli.jsonl` and `labeling/labels.jsonl` still hash to `1d240ebc…8c5376`
and `fda2bc3d…2707d4`. What follows is disclosure.

1. **Where the poles already sit on the scale.** The companion study released per-turn
   pedagogy scores for all 2,219 corpus turns
   (`results/{ablation,confirmatory,confirmatory_gpt,confirmatory_gemini}/pedagogy_detail.json`),
   produced by the same `claude-opus-4-8` judge, the same frozen instrument, temperature
   omitted, `max_tokens` 512, 3 reps. Joining them to the 82 corpus-sourced poles of the
   frozen 55 (0 lookup misses) gives: `R_H` mean **4.553 / 5** with **25 of 53 at exactly
   5.000**; `R_L` mean **1.782** with **17 of 29 at exactly 1.000**. Over the 27 all-corpus
   pairs the implied no-profile `Δ` is **2.889** (sd 1.09, max 4.00) — the contrast already
   consumes about three quarters of the usable range. For the 55 real turns, whose D-arm
   prompt is byte-identical to a call the companion study actually made, the figures are
   4.488 (18 of 43 at 5.000) on the high pole and 1.694 (8 of 12 at 1.000) on the low.

2. **What that does to `PAG`.** Writing `a_H = S_H(P_adv) − S_H(P_nov)` and
   `a_L = S_L(P_adv) − S_L(P_nov)`, the primary endpoint is `PAG = a_L − a_H`. In the weak
   stratum the observed positions bound the two terms unequally: **6.23 scale points of
   headroom in the positive (registered "anchoring") direction against 1.77 in the
   negative** — `a_H` can fall by 3.57 on average but rise by at most 0.43, and for
   **16 of the 30 weak stimuli it cannot rise at all**, their `R_H` having already scored
   5/5/5. (Prior scores exist for all 30 weak `R_H` but only the 12 corpus-sourced weak
   `R_L`; the 18 authored ones are unmeasured, so the floor term is the weaker half of
   this estimate.)

3. **The registered consequence.** Censoring cannot manufacture an effect, so a non-null
   `PAG_weak` remains interpretable as profile influence and §6.2's positive reading is
   unaffected. The null branch is what changes. §6.2 registers two readings of a null and
   discriminates between them with §6.3's pure profile effect; **there is a third, and it
   is hereby registered**: the profile effect fell in the direction this scale cannot
   express. It is not idle — it is what the *pedagogically standard* response produces
   (an advanced label makes withholding more appropriate, raising `R_H` and lowering
   `R_L`, both of which are the censored movements), and in that world §6.3's pure profile
   effect is censored on both poles too, so the A5.1 safeguard would also read null. **A
   joint null of `PAG_weak` and §6.3 is therefore reported as uninformative between "the
   profile did not reach the rating" and "the profile effect was not expressible", and
   the earlier reading is not asserted over the later one.**

4. **Diagnostic registered now, reported whatever it shows.** Per arm and pole, the
   fraction of units at `overall == 5.000` and at `== 1.000`, and the same for the four
   sub-scores. Also registered as a secondary: the 55 × 3 = **165 D-arm calls on the real
   pole are byte-identical repeats of published companion-study calls**, so their
   agreement with the released 3-rep means is reported as a test–retest check on the
   frozen instrument and as evidence on whether the judge still behaves as measured.

5. **Tutor base is confounded with the pole.** Among the 82 corpus-sourced responses,
   `r_high` is gemini 23 / sonnet 19 / gpt 11 while `r_low` is **gpt 26 / gemini 2 /
   sonnet 1**. With the 26 authored `R_L`, essentially every low pole is either GPT-written
   or authored while the high pole is mostly gemini/sonnet, so `Δ` contrasts text from
   different model families as well as different scaffolding — the mechanical source of the
   `\boxed{}` cue already disclosed in A5.6. This is the same class of artifact as the
   authoring imbalance in §2, with the same additivity argument and the same limit:
   inert for `PAG` under additivity, not inert for an artifact that interacts with the
   profile. The §6.3 all-corpus re-estimate does **not** control it (it removes authoring,
   not base). Corpus `r_low` also averages 374 characters against `r_high` at 254.

6. **Cluster counts for the §6.3 authoring-robustness re-estimate.** Under A4.3's
   source-run inference unit, the 27 all-corpus stimuli sit in **8 weak and 7 strong source
   runs**, not 12 and 15. Minimum attainable two-sided exact p is therefore 0.0078 and
   0.0156, against 7.6e-06 for the 18-cluster primary; the two are not comparable at face
   value and will not be reported as though they were.

7. **Corrections to §8's token arithmetic** (below, corrected in place): the system prompt
   is ~1,000 Anthropic tokens, not ~814, and the profile block ~124, not 95 — calibrated
   against Anthropic-reported `input_tokens` on 3,120 logged companion-study calls carrying
   this byte-identical system prompt. The cost consequence is negligible and conservative
   (measured point estimate ~$10.0 against the registered $9.72).

## 8. Budget

Cost basis measured from the source pedagogy-judge log (3,120 calls: 1,639.6 input /
52.0 output mean tokens), plus two thirds of the 95-token profile block: **~$9.72**
for 990 accepted calls at $5/$25 per Mtok. Before each physical request, the ledger
reserves $0.05376: an 8,192-token input ceiling plus the full 512-token output
allowance. The runner also verifies that the request's UTF-8 byte length plus a
512-token message-envelope allowance fits that input ceiling. The deliberately loose
reservation totals $53.22 for 990 attempts ($53.33 including preflight), so the
**$40 hard lifetime cap** would stop the study if actual usage approached the bound;
at the measured usage it leaves ample room. Four attempts for every main-schedule
unit would reserve $212.89 in aggregate, but each reservation is settled to actual usage
immediately, so the cap meters **settled** spend: at the measured basis 3,960 requests
cost ~$38.9 and would *not* by themselves trip the $40 ceiling. What actually prevents
that regime is the quality circuit breaker, which aborts once the usable-rating rate
falls below 50%; the cap is the backstop, not the mechanism (Amendment A6.7 / audit
2026-08-10 N4). Pilot calls
populate the main cache rather than adding a second set, and all modes share the same
persisted ledger. The cap must be finite and positive, cannot exceed $40, and cannot
be raised on resume. No `cache_control` breakpoint is ever sent, so no prompt-caching
discount applies and none is assumed. (The system prompt measures ~1,000 Anthropic
tokens and the profile block ~124 — calibrated against Anthropic-reported `input_tokens`
on 3,120 companion-study calls carrying this byte-identical system prompt; earlier drafts
said 814 and 95, and inferred from the 814 figure that the prompt sat below
claude-opus-4-8's 1,024-token cache minimum. It does not, but nothing turns on it.)
