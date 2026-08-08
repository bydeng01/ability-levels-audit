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

**Corpus.** 55 dialogue contexts drawn from the 2,219 judged tutor turns of a
frozen tutoring-policy study (7 tutor policies × 3 tutor bases; algebra mixture
problems; a calibrated-weak Llama-3.1-8B student), spanning all six training
problems (31 ped / 24 conv). Each context ends with a student turn, presents a
live next reasoning step **on the problem its metadata names**, and carries two
candidate tutor replies to that same context: a high-scaffolding `R_H` and a
low-scaffolding `R_L`. One pole is the session's real next tutor turn; the
counterpart is another corpus turn that fits, or an authored reply matched for
length and register (R_H: 53 corpus / 2 authored; R_L: 29 / 26).
**27 stimuli use no authored text at all** and support a pre-registered
authoring-robustness re-estimate of the primary endpoint.

**Manipulation check.** Blind, order-randomised raters — briefed to disregard
question marks, formatting and length, which correlate with the poles in this
material — recovered the intended pole in **55/55** pairs (0 reversed, 0 tied).
One pair was flagged as reversed on an earlier pass and repaired before freeze.
This is agreement with the construction key at one rater per pair, so it checks
the pairing review rather than establishing independently that Δ measures
scaffolding.

**Labels.** Demonstrated competence (30 weak / 25 strong) comes from three
independent blind annotation passes over the contexts alone (126-candidate pool;
majority vote; 115/126 unanimous; pairwise rep agreement 94.4 / 94.4 / 93.7%),
not from the tutor's own state tracker, which shares a model
family with the judge and is used only as a sampling prior. The labelling rubric
was revised once before any judge call, to measure *current-state* competence;
the revision was strictly monotone (45 items strong→weak, **0** weak→strong) and
both label sets are released.

**Judge.** The source study's frozen pedagogy judge (Claude Opus 4.8, rubric
verbatim: contingent scaffolding, productive struggle, assistance calibration,
elicitation, overall). Three arms per (context, response): no profile (D),
novice profile (P_nov), advanced profile (P_adv) — user prompts byte-identical
except for the profile block (asserted in tests). 55 × 3 × 2 × 3 reps = 990
calls. Stimuli, labels, profiles, prompts, executed request code, runtime and
analysis plan are hash-bound; live execution additionally requires a clean tagged
commit. The audit corrections were completed before any provider call or judge
score (Amendments A2–A4).

## 3. Results

**[[Four-cell table: Δ(nov,weak), Δ(adv,weak), Δ(nov,strong), Δ(adv,strong)
with CIs — from summary.json four_cell_table]]**

The pre-registered primary endpoint is the weak stratum's Profile Anchoring Gap,
PAG = Δ(P_nov) − Δ(P_adv), positive when the advanced label suppresses the
judge's scaffolding preference for the same visibly struggling learner. Stimulus
contrasts are averaged within source tutoring run; inference uses 18 independent
weak-stratum run means, not 30 correlated turns.
**[[PAG_weak mean, BCa CI, Wilcoxon p, rank-biserial]]**. Movement from the
no-profile control ([[Δ(P)−Δ(D) numbers]]) locates the anchoring causally; the
pure profile effect on absolute scores ([[S(R|P_adv)−S(R|P_nov)]]) shows
whether the label moves ratings even with the response held fixed.

**Evidence gradient.** Profile influence [[shrinks/does not shrink]] as the
blind-labelled behavioural evidence strengthens (Spearman ρ = [[rho]],
p = [[p]]). A rational evaluator may lean on a prior when evidence is ambiguous;
the failure mode is influence that persists undiminished under strong evidence
— which we [[do/do not]] observe. This contrast spans two evidence levels
(moderate, strong); the frozen set contains no ambiguous-evidence items, so the
end of the scale where profile use is most defensible is not tested here.

**Authoring robustness.** Authored text sits on `R_L` 26 times and on `R_H` twice,
because the source tutors are pedagogically tuned and the real turn is the high
pole in 43 of 55 stimuli. Under additivity this cannot manufacture the result —
identical `R_H`/`R_L` texts are judged in all three arms, so a stimulus-level
artifact cancels in a difference-of-differences — but an artifact that *interacts*
with the profile would not. Re-estimated on the 27 stimuli containing no authored
text, the primary endpoint is [[PAG_weak all-corpus mean, CI]].

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
synthetic course-record texts, and the novice text states that the learner
"usually needs step-by-step help", so part of any profile effect may be a
*rational* response to a stated support need rather than anchoring on an ability
label. The strong stratum is 25 rather than 30: the eligibility rule left 26
otherwise eligible strong candidates, and one invalid pair was excluded before the
final freeze because it confounded scaffolding with an unrepaired arithmetic error.
The tutor family is nearly collinear with the competence stratum (ped 23 weak /
8 strong; conv 7 weak / 17 strong), so every weak-vs-strong comparison is
confounded with tutor policy; the within-stimulus primary endpoint is not. The
evidence-strength moderation spans only moderate and strong, so the ambiguous end
— where profile use is most defensible — is untested. Nearly half of `R_L`
responses are authored. The `R_H`/`R_L` contrast carries surface cues (a question
mark in 37/55 `R_H` against 1/55 `R_L`; `\boxed{}` in 0 against 18), so Δ is not a
pure scaffolding contrast. Scaffolding preference is rubric-scored rather than
forced-choice (a forced-choice robustness check is a labelled exploratory
follow-up).

**Relation to companion work.** The corpus, judge, and rubric come from a
companion study of tutoring policies [cite]; its headline findings are not
restated here. This abstract's contribution is the **profile manipulation** on
the judge and the anchoring analysis.
