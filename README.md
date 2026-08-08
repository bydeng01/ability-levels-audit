# label-vs-evidence — profile anchoring in pedagogy-aware LLM judges

**Working title:** *Do Pedagogy-Aware LLM Judges Generalize Across Student Ability
Levels?* — AAAI-27 Student Abstract.

When a learner's *stated* profile conflicts with the competence the learner
*demonstrates* in the dialogue, does a pedagogy-aware LLM judge ground its rating in
the behavioural evidence, or anchor on the label? The manipulation is on the
**judge**, not the tutor: dialogues and candidate tutor responses are held fixed and
only the learner profile shown to the judge is randomised. The study reuses the
frozen corpus and the frozen pedagogy-judge instrument of the companion
`conv-vs-ped-tutor` study (vendored read-only at commit
`ab5ea2a99d67cc2b23808c52e841301c5e56d887`); it generates no new tutoring sessions
and makes zero student or tutor model calls.

Full design + analysis plan: [protocol/PREREGISTRATION.md](protocol/PREREGISTRATION.md).
Every decision and deviation: [protocol/decisions-log.md](protocol/decisions-log.md).

## Design in one paragraph

60 dialogue contexts (each ending with a student turn) are drawn from the source
corpus's 2,219 judged tutor turns, stratified 30/30 by **independently blind-labelled
demonstrated competence** (weak/strong, with an ordinal evidence-strength covariate;
the tutor's own state-tracker is a sampling prior only). Each context carries a
high-scaffolding `R_H` and a low-scaffolding `R_L` candidate response (real corpus
turns where possible, authored otherwise; provenance recorded). The frozen Opus-4.8
pedagogy judge rates each (context, response) under three arms — no profile `D`,
novice profile `P_nov`, advanced profile `P_adv` — whose prompts are byte-identical
except for the profile block. 60 × 3 × 2 × 3 reps = **1,080 paid calls (~$10.70)**.
Primary endpoint: the weak stratum's Profile Anchoring Gap
`PAG = Δ(P_nov) − Δ(P_adv)` where `Δ = S(R_H) − S(R_L)`.

## Layout

```
vendor/            read-only verbatim copies from $SRC (PROVENANCE.md has hashes)
corpus/            build_stimuli.py; frozen stimuli.jsonl (+.sha256); corpus/logs/
labeling/          blind labelling (RUBRIC.md, label_competence.py, labels.jsonl)
profiles/          frozen novice/advanced profile texts
judging/           profile_judge.py (instrument) + run_study.py (paid runner)
analysis/          analyze.py (pre-registered §6) + figures/fig1.py
results/           runner namespace: manifest, preflight, cache, wire, finals
protocol/          PREREGISTRATION.md + decisions-log.md
tests/             prompt purity, arm equivalence, reconstruction, parser,
                   ledger/breaker, mock end-to-end + offline replay
paper/             abstract draft (placeholders until the paid run)
```

## Reproduce (offline, no key)

```bash
python3 -m pytest tests/ -q                  # incl. the 1,080-call mock end-to-end
python3 corpus/build_stimuli.py census       # corpus census vs expected numbers
python3 corpus/build_stimuli.py verify       # byte-identical stimulus reconstruction
python3 judging/run_study.py --manifest-only # plan + hashes, zero provider calls
```

## The paid run (operator sequence)

Requires `ANTHROPIC_API_KEY` exported (Anthropic; judge = `claude-opus-4-8` per the
vendored `configs/models.yaml`). Lifetime spend is capped by a per-request persisted
ledger (default `--cap 40`); the cache makes every step resumable; nothing is
promoted unless every unit has 3 valid reps.

```bash
python3 judging/run_study.py --preflight     # 2 synthetic calls; freezes the contract
python3 judging/run_study.py --pilot 12      # small paid pilot; no promotion
python3 judging/run_study.py                 # full run; transactional promotion
python3 analysis/analyze.py                  # pre-registered analysis -> summary.json
python3 analysis/figures/fig1.py             # the abstract's figure
```

`--offline-cache-only` re-derives the promoted numbers from the released per-rep
cache and aborts on any miss; `--judge-backend mock` exercises the full pipeline with
synthetic scores (never reportable).

## Freeze discipline

Stimuli, labels, profile texts, judge prompt, and the analysis plan are frozen and
hash-bound (`results/frozen_inputs.sha256`, git tags) **before the first paid judge
call**; the preflight binds a `contract_sha256` over all of them and the paid runner
refuses to score if anything changed. A null result is a publishable finding; nothing
is tuned toward an effect.
