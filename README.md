# Difference-in-Differences on a Censored Rating Scale Can Manufacture an Effect

[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://img.shields.io/github/actions/workflow/status/bydeng01/ability-levels-audit/ci.yml?branch=master&label=CI)](https://github.com/bydeng01/ability-levels-audit/actions/workflows/ci.yml)
[![arXiv](https://img.shields.io/badge/arXiv-2608.27309-b31b1b.svg)](https://arxiv.org/abs/2608.27309)
[![Docker](https://img.shields.io/badge/Docker-supported-2496ED.svg?logo=docker&logoColor=white)](Dockerfile)

Code and released data for *Difference-in-Differences on a Censored Rating Scale
Can Manufacture an Effect: Evidence from a Pre-Registered LLM-Judge Audit*
([paper](https://arxiv.org/abs/2608.27309)). Accepted to the NewInML Workshop at
NeurIPS 2026.

This repository contains the frozen study materials, 990 accepted judge ratings,
request records, and code to reproduce the analyses and figures. See the
[paper](https://arxiv.org/abs/2608.27309) for the study design and results.

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

[CI](.github/workflows/ci.yml) checks offline reproduction and the Docker build.

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

The [protocol index](protocol/README.md) links the pre-registration, historical
reviews, and archived pre-run abstract. Amendments and corrections are recorded
in the [decisions log](protocol/decisions-log.md).

See the [original run workflow](judging/README.md) for paid-run requirements and
corpus-building commands.

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
