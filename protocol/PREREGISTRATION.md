# Pre-registration — Do Pedagogy-Aware LLM Judges Generalize Across Student Ability Levels?

**Status: FROZEN before the first paid judge call.** The freeze is enacted by the
sha256 hashes in `results/frozen_inputs.sha256` and the git tag `prereg-frozen`;
the preflight binds the request contract (`contract_sha256`) to these inputs, and
the paid runner refuses to score if any of them changes. Anything analyzed beyond
§6 is exploratory and will be labelled as such.

Target venue: AAAI-27 Student Abstract (2 pages, one figure). Companion full paper:
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

- **Stimuli**: 60 dialogue contexts drawn from the frozen 2,219 judged tutor turns of
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
- **Authoring, and why it cannot manufacture the primary result.** Because the real
  turn serves whichever pole it actually serves, authored counterparts fall on `R_H`
  for some stimuli and `R_L` for others; the split is reported and a lopsidedness
  bound is asserted in `tests/test_stimuli.py`. It is not perfectly even — the source
  tutors are pedagogically tuned, so a real turn is more often the high pole — and
  that residual imbalance is disclosed. It is nevertheless **inert for the primary
  endpoint by construction**: the identical `R_H`/`R_L` texts are judged in all three
  arms, so any stimulus-level artifact δ (authoring fluency, length, register) enters
  every arm's Δ equally and cancels exactly in
  `PAG = Δ(P_nov) − Δ(P_adv)`. Such an artifact can shift the *level* of Δ in the
  four-cell table; it cannot create or hide a Profile Anchoring Gap, which is a
  within-stimulus difference of differences.
- **Arms** (within-stimulus, the manipulated factor):
  `D` (dialogue + response), `P_nov` (novice profile + dialogue + response),
  `P_adv` (advanced profile + dialogue + response). Profile texts are frozen in
  `profiles/profiles.yaml`, length-matched, and contain no dialogue hints and no
  weighing instructions.
- **Demonstrated competence** (between-stimulus, the stratification factor): 30 weak /
  30 strong per the independent blind labels (§3). Cells (novice profile, weak) and
  (advanced, strong) are **congruent**; (advanced, weak) and (novice, strong) are
  **conflict** cells.
- **Judge**: the source study's frozen pedagogy judge — `claude-opus-4-8`, Anthropic,
  temperature omitted, max_tokens 512, system prompt `PED_SYSTEM` verbatim; user
  message `PED_USER` verbatim with, in profile arms only, a frozen profile block
  prepended. Three reps per (stimulus, arm, response); reps are genuine stochastic
  samples (no seed on the Anthropic path, as in the source study).
- **Size**: 60 × 3 × 2 = 360 units; × 3 reps = 1,080 paid calls.
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
  majority vote; items without ≥2/3 agreement on competence are dropped and the
  count reported.
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
- Selection of the final 60 from the 126-candidate pool follows the deterministic rule
  frozen in `corpus/build_stimuli.py select` (eligibility and ≥2/3 agreement, then
  unanimity, then confidence, then candidate id, under per-problem coverage caps) —
  labels and coverage only; nothing downstream of a judge score exists at selection
  time.

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
design requires. Both freezes precede any judge call. If a stratum has < 30 eligible
members, we take all of it and report the imbalance (no post-label re-sampling).

## 4b. Manipulation check (run before freeze, reported)

Δ is only interpretable if `R_H` and `R_L` genuinely differ in scaffolding level. A
blind, order-randomised check verifies this independently of the judge and of the
profile manipulation: raters see the context and the two responses as "A"/"B" in
random order and say which leaves more of the next reasoning step to the student,
explicitly ignoring tone, length, formatting, and mathematical correctness
(`corpus/manipulation_check.py`; result in `corpus/manip/report.json`). It is a
validity report, not a selection step — no stimulus is dropped on the basis of a
judge score, and no judge call exists at this point. A pair the raters call reversed
is a construction defect and is repaired before freeze; the final agreement rate is
reported in the paper.

## 5. Frozen artifacts

`corpus/stimuli.jsonl` (+ .sha256), `labeling/labels.jsonl` (+ .sha256),
`profiles/profiles.yaml`, the vendored judge instrument
(`vendor/analysis/judge_pedagogy.py`, `vendor/configs/models.yaml`,
`vendor/supplement/judge_pedagogy_rubric.md`), `judging/profile_judge.py` (prompt
assembly, schedule seed 90210), and this document. Hashes: `results/frozen_inputs.sha256`;
binding: `contract_sha256` in `results/preflight/resolved_config.json`.

## 6. Analysis plan

Unit of analysis: the stimulus. Per (stimulus s, arm a): the scaffolding preference

    Δ_s(a) = S_s(R_H | a) − S_s(R_L | a)

with S the per-unit mean `overall`.

**6.1 Headline object — the four-cell table** of mean Δ by (profile, demonstrated
competence): Δ(nov, weak), Δ(adv, weak), Δ(nov, strong), Δ(adv, strong), each with a
bootstrap CI (§6.5).

**6.2 Primary endpoint — the Profile Anchoring Gap in the weak stratum:**

    PAG_s = Δ_s(P_nov) − Δ_s(P_adv);   PAG_weak = mean over weak-stratum stimuli

Sign convention (matches the source plan): positive = the advanced label suppresses
the judge's scaffolding preference for the same visibly struggling learner.
Primary test: two-sided Wilcoxon signed-rank on the weak-stratum per-stimulus PAG_s
against 0, with a BCa bootstrap CI on mean PAG_weak and the rank-biserial correlation
as effect size. A null (CI tight around 0) is a publishable finding: the judge grounds
its preference in behavioural evidence. We report effect sizes with CIs, not
null-vs-significant dichotomies.

**6.3 Secondary (labelled as such):**
- PAG_strong (same estimator, strong stratum).
- Movement from the no-profile control: Δ_s(P_x) − Δ_s(D) per profile and stratum —
  in conflict cells this is the plan's anchoring score S(R | P_conflict, D) − S(R | D).
- **Pure profile effect on absolute scores** (the plan's "crucial comparison"):
  S_s(R | P_adv) − S_s(R | P_nov) per response pole, same transcript and response,
  only the metadata differing.
- **Authoring robustness (pre-registered).** Re-estimate the primary endpoint on the
  subset of stimuli whose *both* poles are real corpus turns (28 stimuli: 12 weak,
  16 strong) — no authored text anywhere. Authoring is disproportionately on `R_L`
  (27 of 32 authored responses), and although that is inert for PAG by construction
  (§2), this subset removes the question entirely. Reported alongside the primary,
  whatever it shows.
- Per-field decomposition of the primary over the four rubric sub-scores.

**6.4 Profile influence × evidence strength (secondary):** influence_s = |PAG_s|;
Spearman correlation of influence_s with the ordinal evidence-strength label across
all 60 stimuli (direction: negative = influence shrinks as evidence strengthens).
Framing per the source plan: a rational evaluator may legitimately lean on the
profile when evidence is ambiguous (it is a prior); the failure mode is profile
influence that persists undiminished under strong evidence. We do NOT pre-register
"evidence should always beat the label."

**6.5 Statistics:** paired throughout; stimulus as the unit; BCa bootstrap (10,000
resamples, seed 13) resampling stimuli within stratum; exact Wilcoxon where n ≤ 25
per SciPy defaults, otherwise the normal approximation. No multiplicity correction on
the single primary endpoint; secondaries are descriptive with CIs.

**6.6 Exclusions:** none at analysis time — the completeness gate guarantees
n_valid = 3 for every unit before promotion, and stimulus selection closed at §3.
If the paid run cannot reach completeness under the $40 cap, the study stops and the
incompleteness is reported; no partial-data analysis is promoted.

## 7. One figure

x-axis: demonstrated competence (weak → strong); y-axis: preference for high
scaffolding (Δ); two lines (stated novice, stated advanced) with CIs; the D-arm
control shown as a reference. Parallel, closely-spaced lines = behaviour-driven
judge; wide separation = profile anchoring.

## 8. Budget

Cost basis measured from the source pedagogy-judge log (3,120 calls: 1,639.6 in /
52.0 out mean tokens): ~$10.70 for the 1,080-call main run at $5/$25 per Mtok, plus
preflight + pilot. Hard lifetime cap: **$40**, enforced per request by the spend
ledger. The ~814-token system prompt is below claude-opus-4-8's 1024-token
prompt-cache minimum, so no caching discount is assumed.
