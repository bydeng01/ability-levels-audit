# label-vs-evidence: profile anchoring in pedagogy-aware LLM judges

[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://img.shields.io/github/actions/workflow/status/bydeng01/ability-levels-audit/ci.yml?branch=master&label=CI)](https://github.com/bydeng01/ability-levels-audit/actions/workflows/ci.yml)
[![arXiv](https://img.shields.io/badge/arXiv-2608.27309-b31b1b.svg)](https://arxiv.org/abs/2608.27309)
[![Docker](https://img.shields.io/badge/Docker-supported-2496ED.svg?logo=docker&logoColor=white)](Dockerfile)

**Title:** *Do Pedagogy-Aware LLM Judges Generalize Across Student Ability
Levels?*

This study asks what a pedagogy-aware LLM judge does when a learner's *stated*
profile conflicts with the competence the learner *demonstrates* in the dialogue:
ground the rating in the behavioural evidence, or anchor on the label. The
manipulation is applied to the judge and not to the tutor. Dialogues and candidate
tutor responses are held fixed, and only the learner profile shown to the judge is
randomised. The study reuses the
frozen corpus and the frozen pedagogy-judge instrument of the companion
`conv-vs-ped-tutor` study (vendored read-only at commit
`ab5ea2a99d67cc2b23808c52e841301c5e56d887`); it generates no new tutoring sessions
and makes zero student or tutor model calls.

Full design + analysis plan: [protocol/PREREGISTRATION.md](protocol/PREREGISTRATION.md).
Every decision and deviation: [protocol/decisions-log.md](protocol/decisions-log.md).

## Design

55 dialogue contexts (each ending with a student turn) are drawn from the source
corpus's 2,219 judged tutor turns, stratified **30 weak / 25 strong** by independently
blind-labelled demonstrated competence (with an ordinal evidence-strength covariate;
the tutor's own state-tracker is a sampling prior only). The strong stratum is short of
30 because the corrected eligibility rule left only 26 eligible strong candidates in
the whole pool and a pre-data audit excluded one whose current error made its two
response poles an invalid scaffolding contrast; the remaining 25 are taken entire
(Amendments A2 and A4). Each context carries a high-scaffolding `R_H` and a
low-scaffolding `R_L` candidate response (real corpus
turns where possible, authored otherwise; provenance recorded). The frozen Opus-4.8
pedagogy judge rates each (context, response) under three arms — no profile `D`,
novice profile `P_nov`, advanced profile `P_adv` — whose prompts are byte-identical
except for the profile block. 55 × 3 × 2 × 3 reps = **990 paid calls (~$9.72)**.
Primary endpoint: the weak stratum's Profile Anchoring Gap
`PAG = Δ(P_nov) − Δ(P_adv)` where `Δ = S(R_H) − S(R_L)`.

## Layout

```
vendor/            read-only verbatim copies from $SRC (PROVENANCE.md has hashes)
corpus/            build_stimuli.py; frozen stimuli.jsonl (+.sha256); corpus/logs/
labeling/          blind labelling (RUBRIC.md, label_competence.py, labels.jsonl)
profiles/          frozen novice/advanced profile texts
judging/           profile_judge.py (instrument) + run_study.py (paid runner)
analysis/          analyze.py (pre-registered §6); diagnostics.py and
                   simulations.py (post-hoc, not frozen); figures/
results/           runner namespace: manifest, preflight, cache, wire, finals
protocol/          PREREGISTRATION.md + decisions-log.md + AUDIT-2026-08-08.md
tests/             prompt purity, arm equivalence, reconstruction, parser,
                   ledger/breaker, mock end-to-end + offline replay
paper/             abstract draft (placeholders until the paid run)
```

## Reproduce (offline, no key)

```bash
python3 -m pytest tests/ -q                  # incl. the 990-call mock end-to-end
SRC_LOGS=/path/to/conv-vs-ped-tutor/logs \
  python3 corpus/build_stimuli.py census     # corpus census (needs the source logs)
python3 corpus/build_stimuli.py verify       # byte-identical stimulus reconstruction
python3 judging/run_study.py --manifest-only # plan + hashes, zero provider calls
```

Or in the frozen container (Python 3.12.8 and the exact pins), which runs that suite
by default:

```bash
docker build -t ability-levels-audit .
docker run --rm ability-levels-audit
```

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs the whole offline path on
every push: the test suite, the reconstruction check, `analysis/analyze.py`,
`diagnostics.py`, `simulations.py`, the three figure scripts, and `--manifest-only`,
then asserts that `results/input_manifest.jsonl` and `results/frozen_inputs.sha256`
come back byte-identical. No key, no provider calls.

## The paid run (operator sequence)

Requires `ANTHROPIC_API_KEY` exported (Anthropic; judge = `claude-opus-4-8` per the
vendored `configs/models.yaml`). Lifetime spend is capped by a per-attempt persisted
ledger (default `--cap 40`, which cannot be raised on resume); the cache makes every
step resumable; nothing is promoted unless every unit has 3 valid reps. Live
preflight also requires a clean worktree and a `prereg-final-*` tag at `HEAD`.

```bash
# After reviewing and committing every frozen artifact:
git tag prereg-final-2026-08-08
python3 judging/run_study.py --preflight     # 2 synthetic calls; freezes the contract
python3 judging/run_study.py --pilot 12      # small paid pilot; no promotion
python3 judging/run_study.py                 # full run; transactional promotion
python3 analysis/analyze.py                  # pre-registered analysis -> summary.json
python3 analysis/figures/fig1.py             # registered figure
python3 analysis/figures/fig2.py             # exploratory
python3 analysis/figures/fig3.py             # exploratory
```

`--offline-cache-only` re-derives the promoted numbers from the released per-rep
cache and aborts on any miss; `--judge-backend mock` exercises the full pipeline with
synthetic scores (never reportable).

**Do not create any commit between `--preflight` and the end of the run.** Every live
command after preflight requires `HEAD` to equal the commit preflight froze, so a commit
in between blocks the paid run. The same check means live `--offline-cache-only` replays
in the operator's own tree, not in a clone whose history includes the commit that
published the cache (AUDIT-2026-08-10 N5).

## Freeze discipline

Stimuli, labels, profile texts, judge prompt, executed request code, exact dependency
versions, analysis code, and the analysis plan are hash-bound
(`results/frozen_inputs.sha256`, `contract_sha256`) and committed under the required
git tag **before the first paid judge call**. Preflight and every later live command
abort on drift. Accepted live cache entries must match an fsynced wire record carrying
the provider response id, full response, parsed scores, and record hash. Promotion
hashes all four final result files; `analysis/analyze.py` verifies those hashes and the
cache/wire hashes plus the complete unique 55 × 3 × 2 result grid before computing
anything. Inference is over
the 23 independent source runs, with stimulus-level contrasts averaged within source
run first. A null result is a reportable outcome, and nothing is tuned toward an
effect.

An independent pre-flight audit of all of this is at
[protocol/AUDIT-2026-08-08.md](protocol/AUDIT-2026-08-08.md); the fixes it required
(including the re-freeze to 55 stimuli and the integrity gates) are recorded as
Amendments A2–A4.

## Citation

If you use this repository or its released results, cite the paper. GitHub reads
[CITATION.cff](CITATION.cff); the BibTeX arXiv serves is

```bibtex
@misc{fan2026differenceindifferencescensoredratingscale,
      title={Difference-in-Differences on a Censored Rating Scale Can Manufacture an Effect: Evidence from a Pre-Registered LLM-Judge Audit},
      author={Shuyi Fan and Boyuan Deng and Mengyu Xu and Xinhong Xie and Chenyang Li and Hongyang Zhang},
      year={2026},
      eprint={2608.27309},
      archivePrefix={arXiv},
      primaryClass={cs.CL},
      url={https://arxiv.org/abs/2608.27309},
}
```

## License

MIT — see [LICENSE](LICENSE).


