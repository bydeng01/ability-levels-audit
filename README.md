# Difference-in-Differences on a Censored Rating Scale Can Manufacture an Effect

[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://img.shields.io/github/actions/workflow/status/bydeng01/ability-levels-audit/ci.yml?branch=master&label=CI)](https://github.com/bydeng01/ability-levels-audit/actions/workflows/ci.yml)
[![arXiv](https://img.shields.io/badge/arXiv-2608.27309-b31b1b.svg)](https://arxiv.org/abs/2608.27309)
[![Docker](https://img.shields.io/badge/Docker-supported-2496ED.svg?logo=docker&logoColor=white)](Dockerfile)

Code and released data for *Difference-in-Differences on a Censored Rating Scale
Can Manufacture an Effect: Evidence from a Pre-Registered LLM-Judge Audit*
([paper](https://arxiv.org/abs/2608.27309)).

The study varies the learner profile shown to a pedagogy-aware LLM judge while
holding each dialogue and candidate tutor response fixed. The pre-registered
primary weak-stratum Profile Anchoring Gap was +0.085 (95% BCa interval [−0.167, +0.353]; exact
signed-rank p = 0.684). This does not establish equivalence across profiles.
An exploratory censoring construction reproduces much of the largest sub-score
gap, illustrating how a bounded rating scale can turn a common score shift into
an apparent change in scaffolding preference.

The release includes the frozen study materials, 990 accepted judge ratings,
request records, registered analysis, exploratory diagnostics, and figure scripts.
The [protocol index](protocol/README.md) separates the pre-registration and dated
audit records from the current reproduction instructions below.

## Reproduce the released analysis

Use Python 3.12.8 and the pinned dependencies. From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt

python3 analysis/analyze.py
python3 analysis/diagnostics.py
python3 analysis/simulations.py
python3 analysis/figures/fig1.py
python3 analysis/figures/fig2.py
python3 analysis/figures/fig3.py
```

After dependency installation, these commands run offline without an API key.
Analysis outputs go to `analysis/out/`; figures go to `analysis/figures/`.
`analyze.py` implements the frozen registered analysis. `diagnostics.py` adds
registered diagnostics and separately labelled post-hoc analyses; `simulations.py`
and Figures 2–3 are exploratory.

The instrument test-retest comparison in `diagnostics.py` also needs the companion
study's per-turn results. Set `SRC_RESULTS=/path/to/conv-vs-ped-tutor/results` to
supply them. That comparison is skipped when those files are unavailable.
Figure PDF checks use Poppler's `pdfinfo`, `pdffonts`, and `pdftotext`; missing
tools are reported by the scripts. See [figure maintenance](analysis/figures/FIGURE_SPEC.md).

Verify the released materials and run the offline tests:

```bash
python3 corpus/build_stimuli.py verify
python3 -m pytest tests/ -q
```

The reconstruction check uses the source logs included in `corpus/logs/`.
The tests include a 990-call mock run and cache replay checks.

Alternatively, build the frozen Python 3.12.8 container:

```bash
docker build -t ability-levels-audit .
docker run --rm ability-levels-audit
docker run --rm ability-levels-audit python analysis/analyze.py
```

[CI](.github/workflows/ci.yml) runs the offline tests, reconstruction, analysis,
diagnostics, simulations, figure generation, and manifest checks. It also builds
the container and runs the tests and registered analysis inside it.

## Design and data

The study selected 55 contexts from 2,219 judged tutor turns in the companion
`conv-vs-ped-tutor` corpus: 30 weak and 25 strong by blind-labelled demonstrated
competence. Three independent annotation passes in fresh Claude agent contexts
supplied the competence labels; the tutor's state tracker was used only as a
sampling prior. The eligibility corrections and pre-run exclusion that reduced
the strong stratum are recorded in pre-registration Amendments A2 and A4.

Each context has a high-scaffolding response `R_H` and a low-scaffolding response
`R_L`, drawn from the corpus or authored with provenance recorded. The frozen
Opus-4.8 pedagogy judge rated both responses under three arms: no profile `D`,
novice profile `P_nov`, and advanced profile `P_adv`. Prompts differ only in the
profile block. Three repetitions per unit gave 55 × 3 × 2 × 3 = 990 accepted ratings.

The primary endpoint is the weak stratum's Profile Anchoring Gap:
`PAG = Δ(P_nov) − Δ(P_adv)`, where `Δ = S(R_H) − S(R_L)`.
Stimulus contrasts are averaged within source run before inference: 18 runs
contribute to the weak stratum and 10 to the strong stratum, with 23 distinct
runs overall. Demonstrated competence is observational; the randomised factor
is the profile shown to the judge. The corpus and judge instrument are reused
from the companion study at commit `ab5ea2a99d67cc2b23808c52e841301c5e56d887`.

## Repository layout

```text
vendor/       companion-study code, configuration, rubric, and provenance hashes
corpus/       frozen stimuli, construction records, and source logs
labeling/     rubric, blind batches, per-rep labels, and the v1 archive
profiles/     frozen novice and advanced profile texts
judging/      judge instrument and paid-run controller
analysis/     registered estimator, diagnostics, simulations, and figures
results/      released ratings, request records, cache, manifests, and run metadata
protocol/     pre-registration, decisions log, and historical audit index
paper/        archived pre-run abstract draft
tests/        offline tests
```

## Frozen records

The study inputs and analysis are bound by
[`results/frozen_inputs.sha256`](results/frozen_inputs.sha256) and the run contract.
`analysis/analyze.py` verifies the analysis and protocol hashes, result hashes,
cache and wire records, and the complete 55 × 3 × 2 result grid before analysis.
The [vendored provenance record](vendor/PROVENANCE.md) identifies the source copies.

The [pre-registration](protocol/PREREGISTRATION.md), frozen code, original labels,
and audit reports retain their historical wording. Later decisions and corrections
are in the [decisions log](protocol/decisions-log.md); the
[protocol index](protocol/README.md) explains the dated reports. The
[pre-run abstract](paper/abstract.md) contains unfilled result templates and is
retained as a historical draft, not the current paper.

<details>
<summary>Original paid-run workflow and corpus-building commands</summary>

The following records the original operator workflow. Reproducing the released
analysis uses the offline commands above. A new paid run needs its own reviewed
study checkout and frozen inputs; the released results directory already contains
the completed study.

Live calls require `ANTHROPIC_API_KEY`, a clean worktree, and a `prereg-final-*`
tag at `HEAD`. The judge is configured in `vendor/configs/models.yaml`. The
persisted spend ledger defaults to a $40 lifetime cap, which cannot be raised on
resume. The cache supports resumption; result promotion requires three valid
repetitions for every unit.

After committing and tagging the study inputs, the original sequence was:

```bash
python3 judging/run_study.py --preflight  # two synthetic provider calls
python3 judging/run_study.py --pilot 12  # paid pilot; cached for the full run
python3 judging/run_study.py             # complete and promote the run
```

Every live command after preflight requires `HEAD` to match the preflight commit.
Do not commit between preflight and completion. The same check limits live
`--offline-cache-only` replay to the original run checkout; it does not work at a
later release commit. `--judge-backend mock` exercises the pipeline with synthetic,
unreportable scores. `--manifest-only` makes no provider calls but rewrites the
plan and manifests in `results/`, so use a separate checkout for that check.

Rebuilding the full corpus census requires the companion study's source logs:

```bash
SRC_LOGS=/path/to/conv-vs-ped-tutor/logs \
  python3 corpus/build_stimuli.py census
```

The public `verify` command instead uses the included source-log subset to
reconstruct the released stimuli.

</details>

## Citation

If you use the code or released results, cite the paper. Citation metadata is also
available in [CITATION.cff](CITATION.cff).

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
