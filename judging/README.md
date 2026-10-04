# Original paid-run workflow and corpus-building commands

Run these commands from the repository root. For offline reproduction of the
released results, use the [repository README](../README.md#reproduce-the-released-analysis).
A new paid run needs its own reviewed study checkout and frozen inputs; the
released results directory already contains the completed study.

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
