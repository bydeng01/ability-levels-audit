# Do Pedagogy-Aware LLM Judges Generalize Across Student Ability Levels?

*AAAI-27 Student Abstract draft. Two pages, one figure. Numbers marked
`[[key]]` are filled from `analysis/out/summary.json` after the paid run; no
number below is real until that fill happens.*

## Abstract

LLM judges are increasingly used to score tutoring systems on pedagogical
quality. We audit whether such a judge grounds its ratings in the competence a
learner *demonstrates* in the dialogue, or anchors on a *stated* learner profile
supplied alongside it. Holding a frozen corpus of tutoring dialogues and
candidate tutor responses fixed and randomising only the profile shown to the
judge, we measure the Profile Anchoring Gap — the change in the judge's
preference for high-scaffolding responses when the same visibly struggling
learner is described as a novice versus as advanced. **[[one-sentence headline:
PAG_weak effect size with CI, or the null]]** Our results bear directly on the
validity of learner-adaptive LLM evaluation.

## 1. Terms — what varies and what does not

In this study's title, "ability levels" are **stated learner profiles supplied
to the judge**: short, length-matched background paragraphs (novice vs.
advanced) prepended to the judge's prompt. This is the manipulated factor, and
it is randomised **within-stimulus** — every dialogue is judged under both
labels and under no label. Demonstrated competence — what the learner's own
messages show — varies **observationally** across the frozen transcripts and is
the stratification factor, labelled by an independent blind pass (weak vs.
strong, with an ordinal evidence-strength covariate). **No student simulation
differs between conditions**; no new tutoring sessions were generated; the
manipulation touches only the evaluator.

## 2. Setup

**Corpus.** 60 dialogue contexts drawn from the 2,219 judged tutor turns of a
frozen tutoring-policy study (7 tutor policies × 3 tutor bases; algebra mixture
problems; a calibrated-weak Llama-3.1-8B student). Each context ends with a
student turn and carries two candidate tutor replies to that same context: a
high-scaffolding `R_H` and a low-scaffolding `R_L`
([[n_corpus_pairs]] drawn from real corpus turns, [[n_authored]] authored,
length-matched).

**Labels.** Demonstrated competence (30 weak / 30 strong — [[actual split]])
comes from three independent blind annotation passes over the contexts alone
(majority vote; rubric and per-rep records released), not from the tutor's own
state tracker, which shares a model family with the judge and is used only as a
sampling prior.

**Judge.** The source study's frozen pedagogy judge (Claude Opus 4.8, rubric
verbatim: contingent scaffolding, productive struggle, assistance calibration,
elicitation, overall). Three arms per (context, response): no profile (D),
novice profile (P_nov), advanced profile (P_adv) — user prompts byte-identical
except for the profile block (asserted in tests). 60 × 3 × 2 × 3 reps = 1,080
calls. Everything — stimuli, labels, profiles, prompts, analysis plan — was
frozen and hash-bound before the first paid call.

## 3. Results

**[[Four-cell table: Δ(nov,weak), Δ(adv,weak), Δ(nov,strong), Δ(adv,strong)
with CIs — from summary.json four_cell_table]]**

The pre-registered primary endpoint is the weak stratum's Profile Anchoring Gap,
PAG = Δ(P_nov) − Δ(P_adv), positive when the advanced label suppresses the
judge's scaffolding preference for the same visibly struggling learner.
**[[PAG_weak mean, BCa CI, Wilcoxon p, rank-biserial]]**. Movement from the
no-profile control ([[Δ(P)−Δ(D) numbers]]) locates the anchoring causally; the
pure profile effect on absolute scores ([[S(R|P_adv)−S(R|P_nov)]]) shows
whether the label moves ratings even with the response held fixed.

**Evidence gradient.** Profile influence [[shrinks/does not shrink]] as the
blind-labelled behavioural evidence strengthens (Spearman ρ = [[rho]],
p = [[p]]). A rational evaluator may lean on a prior when evidence is ambiguous;
the failure mode is influence that persists undiminished under strong evidence
— which we [[do/do not]] observe.

**Figure 1.** [[fig1.pdf — two lines (stated novice / stated advanced) over
demonstrated competence, D-arm reference; parallel lines = behaviour-driven,
separation = anchoring.]]

## 4. Discussion

[[If PAG_weak > 0: pedagogy-aware judging inherits a demographic-prior failure
mode: the same struggling learner is judged to need less scaffolding purely
because of a label. Implications for learner-conditioned reward models and
adaptive-tutor evaluation.]]
[[If null: the judge tracks behavioural evidence over stated labels in this
setting — an encouraging validity result for pedagogy rubrics under learner
metadata, bounded by the single domain and judge family.]]

**Limitations.** One judge family (the blind competence labels are also
Claude-family, disclosed; the tutor-pipeline circularity is removed but
family-correlation with the judge remains); one algebra domain; profiles are
synthetic course-record texts; scaffolding preference is rubric-scored rather
than forced-choice (a forced-choice robustness check is a labelled exploratory
follow-up).

**Relation to companion work.** The corpus, judge, and rubric come from a
companion study of tutoring policies [cite]; its headline findings are not
restated here. This abstract's contribution is the **profile manipulation** on
the judge and the anchoring analysis.
