# VERDICT: GO

The materials verify end-to-end and the run should proceed **from the current tree**. I
independently recomputed every quantitative claim in the self-applied Amendment **A6** from
the companion study's own released scores (all reproduce to the digit), and I empirically
re-verified the two self-applied code fixes **B2** (preflight usage guard) and **B3**
(analysis integrity anchored to the committed `plan.json`) by executing the exact attacks
they claim to block — both hold. The freeze is intact (all 12 frozen-input hashes, the three
sidecars, the manifest, and `contract_sha256` all recompute; the deterministic selection
regenerates the frozen 55 byte-for-byte; the frozen competence labels are exactly the
majority vote of the three per-rep files, 0/126 mismatches); the spend ceiling is a genuine
hard cap on billed dollars; the instrument's D-arm payloads are byte-identical to real
companion-study calls; 81 tests pass with zero skips and a clean tree; and no paid artifact
of any kind exists. I found **no blocking defect** in the frozen materials, no spend hole,
and no rival explanation for the primary endpoint that the pre-registration does not already
disclose. The single pre-run action is a **process reconciliation**, not a change to any
frozen file: the operator's asserted state is stale (see NB1) — HEAD is `c297d22`
(`prereg-final-2026-08-10`), **not** the claimed `c5fdf97` (`prereg-final-2026-08-08b`), and
`c297d22` is unpushed. Run on `c297d22`; do **not** revert to `c5fdf97`, which is the
pre-A6 tree.

---

## 0. State the operator asserted vs. what is actually here (read this first)

The operator asserted "HEAD is `c5fdf97`, tagged `prereg-final-2026-08-08b`, worktree clean,
pushed to origin." That is **stale**. Actual state, confirmed directly:

| | operator asserted | actual |
|---|---|---|
| HEAD | `c5fdf97` | **`c297d22`** ("Apply 2026-08-10 pre-flight audit fixes: Amendment A6, …") |
| tag at HEAD | `prereg-final-2026-08-08b` | **`prereg-final-2026-08-10`** |
| origin/master | = HEAD (pushed) | `c5fdf97` — HEAD is **1 commit ahead, unpushed** |
| worktree | clean | clean (confirmed) |

`c297d22` is the A6/B2/B3-remediated commit and is a **valid preflight target**: the real
(non-monkeypatched) `require_git_freeze()` returns clean + `['prereg-final-2026-08-10']` at
HEAD, so preflight passes here today. The whole of this audit was performed against
`c297d22`. The danger is only if the operator acts on the stale belief and checks out
`c5fdf97`/`prereg-final-2026-08-08b` — that tree predates A6 (no censoring disclosure), the
B2 preflight guard, and the B3 analysis anchor, and running it would publish superseded
materials. See NB1.

---

## 1. BLOCKING FINDINGS

**None.** No issue rises to the level of stopping the paid run. Everything the prior
(fourth) pass fixed was re-verified independently and holds; the areas the prior passes
declared "not covered" were probed and produced only test-quality and disclosure items
(Section 2), not defects in what will actually run.

---

## 2. NON-BLOCKING FINDINGS

### NB1. The operator's stated freeze commit is wrong and the real freeze commit is unpushed — DOCUMENTARY, confidence **high**

**What is wrong.** The operator asserts HEAD = `c5fdf97` / `prereg-final-2026-08-08b`,
pushed. In fact HEAD = `c297d22` / `prereg-final-2026-08-10`, one commit ahead of
`origin/master` (`c5fdf97`) and not pushed. `git diff c5fdf97 c297d22` is exactly the A6
remediation (PREREGISTRATION +100 lines / Amendment A6, `run_study.py` preflight guard,
`analyze.py` plan-anchor, abstract "If null" fix, the AUDIT-2026-08-10 report,
regenerated `results/plan.json` + `frozen_inputs.sha256`).

**How I verified it.** `git rev-parse HEAD`, `git tag --points-at HEAD`,
`git rev-parse origin/master`, `git diff --stat c5fdf97 c297d22`, and the real
`_git_freeze_snapshot()` executed against the live tree (returns commit `c297d22`, tag
`prereg-final-2026-08-10`, empty `unexpected_git_status`).

**The concrete failure it could cause.** If the operator "restores" the state they believe
they are in (`git checkout prereg-final-2026-08-08b`) and runs preflight there, the paid run
executes against pre-A6 materials: the primary endpoint's asymmetric-censoring limitation
is undisclosed, `mode_preflight` carries the unguarded cost computation (the B2 defect), and
`analyze.py`'s integrity chain terminates in an untracked file (the B3 defect). Running in
place (the default) uses `c297d22` and is correct.

**Required action (no frozen-file change).** Confirm HEAD is `c297d22`/`prereg-final-2026-08-10`
before preflight; push it to origin so the "pushed" precondition is true and the released
tree carries A6; do not check out `c5fdf97`. **DOCUMENTARY** — nothing in the freeze changes.

### NB2. The cache/wire fraud-resistance checks and the B2 guard are almost entirely undefended by tests — DOCUMENTARY, confidence **high**

**What is wrong.** `validate_live_cache_provenance` (`judging/run_study.py:449-512`) is the
function that certifies every released rating is a genuine, hashed, provider-identified API
response. Of its nine internal checks, **only one** (response-id mismatch, `:499-500`) has a
negative test. I mutated the wire-hash check `if digest != _wire_digest(row)` → `if False`
(`:472-473`) on a copy and the suite stayed green (81 passed). The prior pass's N8 named this
and gave two examples; I reproduced both and find the gap is broader (8 of 9 checks). The B2
preflight usage guard (`:722-726`) likewise has **no** test — removing it survives the suite.
`corpus/manipulation_check.py` and `labeling/label_competence.py` have ~0% code coverage
(only their frozen JSON outputs are asserted).

**How I verified it, and why it does not block.** The *shipped* code is correct — I read
`validate_live_cache_provenance` line by line and it enforces wire-hash integrity,
response-hash, re-parse, no-matching-row, duplicate-response-id, prompt-hash, and served/
frozen-model checks correctly — and `run_study.py` is a hash-bound frozen input, so it cannot
be edited after preflight without tripping the contract. So for *this* run the checks will
run and are correct; the gap is that a *future* regression removing one would ship green.
Crucially, the uncovered generators are not trusted blind: I independently re-derived the
frozen competence labels as the majority vote of `labeling/reps/rep{1,2,3}.jsonl` (**0/126**
competence mismatches; evidence = per-rep median, **0** mismatches; 115/126 unanimous), and
re-verified the manipulation-check output (55/55, A/B position randomised B34/A21) — so the
frozen artifacts those uncovered modules produced are provably correct regardless of coverage.

**Correction to a prior "not covered" claim.** The assertion that `corpus/build_stimuli.py`
has ~0% coverage is inaccurate: `tests/test_reconstruction.py` replays
topup→select→assemble→freeze→verify and compares byte-for-byte, so `is_eligible` and
`_states_answer_in` mutations are caught. Only the `cmd_packets` ranking helpers
(`_similarity`/`_rank_candidates`) are off that path (they fed human review pre-freeze).
**DOCUMENTARY** — recommend adding negative tests before any future edit to these files.

### NB3. `analyze.py`'s integrity chain reaches git, but is not self-enforcing — DOCUMENTARY, confidence **high**

**What is wrong.** The B3 fix (`analysis/analyze.py:156-167`) anchors the analysis-code /
prereg digests to `results/plan.json`, which is committed under the freeze tag, closing the
hole where the chain terminated in the untracked `run_meta.json`. I confirmed the fix works:
on a scratch copy I edited the primary estimand in `analyze.py`, re-stamped
`run_meta.json`/`run_state.json`, left `plan.json` untouched, and `analyze.py` **refused**
("FROZEN INPUTS DISAGREE WITH THE COMMITTED PLAN"). But `analyze.py` does not itself check
git-cleanliness at analysis time, so completing the fabrication only requires *also* editing
the tracked `plan.json` (I confirmed this makes the fabricated `PAG_weak=+99` print with exit
0). The guarantee is therefore "fabrication now requires editing a tracked, tag-covered file
and is git-detectable," not "self-enforcing."

**Why it does not block.** This matches the prior pass's stated intent (terminate the chain
in git) and is a reasonable stopping point; detection just relies on a reviewer running
`git status`/`git diff prereg-final-2026-08-10` against the analysis tree. **DOCUMENTARY.**
Optional hardening: have `analyze.py` call `require_git_freeze()` for reportable runs.

### NB4. Two money-path robustness gaps remain open (as the prior pass recorded) — DOCUMENTARY, confidence **high**

`AUDIT-2026-08-10` deliberately did not apply its own N1/N2. Both re-confirmed and both
genuinely non-blocking for this run: (N1) there is no exception handling around
`caller.call(...)` (`judging/run_study.py:664`) with `max_retries=0` (`:357`), so a single
transient 429/500/timeout aborts a ~27-minute run and leaves one `$0.05376` reservation
committed (`charge` at `:295` with no compensating `settle`) — recoverable by re-running
(the cache preserves all scored reps), bounded by operator patience, not a spend hole; (N2)
`SpendLedger._load` cross-checks the wire log only in the *missing*-ledger branch
(`:225-234`), so a ledger that exists and honestly reports `settled_usd_total: 0.0` is
accepted — an operator-error/tamper concern that is irrelevant to the first run (no ledger,
wire, or cache exists yet, confirmed) and cannot defeat the in-run cap. **DOCUMENTARY.**

### NB5. Label borderlines and a between-stratum construct confound — DOCUMENTARY, confidence **medium**

A full independent read of all 55 stimuli against `labeling/RUBRIC.md` found **no clear-cut
mislabel**, one defensible lean (S38, strong→weak: near-twin of the weak-labelled S17 on the
same problem, split on the parroting-vs-applying boundary; unanimous but only *medium*
confidence), and four borderlines (S18, S42, S01/C036, S26). I read the two highest-stakes
myself: **S18** is in the primary (weak) stratum, but its *latest* student turn ends in an
explicit impasse ("I'm not sure how to do that") after strong prior work, so the unanimous
3/3 high-confidence "weak" is consistent with the v2 rubric's current-state framing, and its
R_H/R_L (withhold vs. perform "x=18") is a clean scaffolding contrast; **S38** and its
strong-stratum siblings feed only secondaries. More broadly, `competence_label` partly tracks
conversation structure (self-initiated setup vs. tutor-prompted micro-steps), which is
correlated with tutor family / turn-index / base — but this is substantially disclosed
(A5.3 strong-stratum-is-all-prior, A5.4 family-differential eligibility, A5.5 23 single-turn
contexts, A3.6 family≈stratum collinearity), and the **primary is within-stimulus and
unaffected**. Re-cutting a frozen label on one adjudicator's read is precisely what the freeze
forbids. **DOCUMENTARY** — the strong stratum (secondaries) carries the most label
uncertainty, which the prereg already flags; a sentence sharpening the "label encodes who
initiated the step" framing would be honest but is not required.

### NB6. Minor documentary imprecisions — DOCUMENTARY, confidence **high**

- The operator's "stimuli.jsonl and labels.jsonl have not changed across any remediation" is
  precise for **labels** (blob `f802c2e1`, unchanged since the initial freeze `1e4c868`) but
  loose for **stimuli**: the blob changed once (`e20580c2`→`84afc1ed`) at the A4 56→55
  refreeze (`9c879b6`) and has been byte-stable across all three `prereg-final-*` tags. The
  change is fully disclosed (A2/A4); the current `sha256 1d240ebc…` is the A5/A6 value.
- `README.md:73` still shows `git tag prereg-final-2026-08-08` in the operator sequence; that
  tag already exists on an old commit and HEAD already carries `prereg-final-2026-08-10`
  (which the runner accepts), so the example is stale but harmless.
- `results/plan.json`'s `est_cost_usd 9.72` and `run_study.py:623`'s `est_in = 1640 + 95*2/3`
  still use the pre-A6 95-token profile-block figure; the directly-measured value with the
  corrected 124-token block is ~$9.81 (A6.7 rounds it to "~$10.0"). Immaterial against the
  $40 cap; disclosed.
- `analysis/figures/fig1.py` renders whatever `summary.json` it is given without reading
  `reportable`, so it would draw a mock-backed figure; `analysis/out/` is gitignored.

---

## 3. VERIFIED — specific claims I checked, and how

**Re-verified myself (not inherited from prior passes):**

- **Amendment A6, every number, recomputed from the companion study's own
  `results/{ablation,confirmatory,confirmatory_gpt,confirmatory_gemini}/pedagogy_detail.json`**
  joined to the 82 corpus-sourced poles (0 lookup misses): corpus `R_H` mean **4.5535**,
  25/53 pinned at 5.0; `R_L` **1.7816**, 17/29 at 1.0; weak `R_H` **4.567**, **16/30** at
  [5,5,5]; weak `R_L` **2.333** (12 corpus, 18 authored/unmeasured); 27 all-corpus D-arm Δ
  **2.889** (sd 1.09, max 4.0); 55 real turns high **4.488** (18/43 at 5.0) / low **1.694**
  (8/12 at 1.0); the headroom algebra `a_H∈[−3.57,+0.43]`, `a_L∈[−1.33,+2.67]`,
  PAG span ≈ **[−1.77, +6.23]**; A6.5 base×pole (`R_L` gpt 26/gemini 2/sonnet 1 + 26 authored;
  `R_H` gemini 23/sonnet 19/gpt 11) and char lengths (254 vs 374); A6.6 all-corpus clusters
  **8 weak / 7 strong** → floors 0.0078 / 0.0156 vs primary 7.63e-06. All reproduce exactly.
- **B2 (preflight usage guard)** empirically, both directions: driving `mode_preflight` with a
  usage-less reply on a copy → clean `SystemExit` ("missing usage accounting"); with the guard
  removed → the exact `TypeError: … 'NoneType' and 'float'` the fix claims to prevent.
- **B3 (analysis anchor)** empirically: the fabrication the prior pass demonstrated is now
  refused via `plan.json`; residual characterised in NB3.
- **Freeze integrity:** all 12 entries in `results/frozen_inputs.sha256`, the three sidecars
  (`stimuli`/`labels`/`candidates`), `contract_sha256` (`fe0a59d2…`), and the full
  `input_manifest.jsonl`/`plan.json` all recompute; `--manifest-only` from a clean
  `git archive HEAD` regenerates the three tracked `results/` files **byte-identically**
  (330 units, 990 calls, $9.72). Env matches `requirements.txt` (py 3.12.8, anthropic 0.96.0,
  scipy 1.17.1, numpy 1.26.4).
- **Reproducibility:** the deterministic `build_stimuli.py select` re-run over the frozen
  labels reproduces `selection.json` byte-identically, and selected−{C018} == the frozen 55
  candidate ids, every frozen `competence_label` == its blind label; `build_stimuli.py verify`
  rebuilds 55 contexts + 82 corpus responses byte-identically; the census turn set = the 2,219
  keys in the companion `pedagogy_detail.json` files.
- **Labels:** frozen `labels.jsonl` == majority vote of `reps/rep{1,2,3}.jsonl` (0/126
  competence, 0 evidence mismatches); unanimity 115/126.
- **Instrument fidelity (real payloads, not templates):** vendored `JP.PED_SYSTEM` is
  byte-identical to `request.system` on all 3,120 companion judge calls; the D-arm real-pole
  user message byte-matches the surviving companion wire log on 13/55 (the log covers only a
  few ablation runs) and equals the companion renderer output on 55/55; system+user max
  payload 6,746 B < the 7,680 B reservation guard.
- **Composition:** 23 source runs (18 weak / 10 strong, 5 both) → primary n = **18**; evidence
  moderate 37/strong 18; family ped 31/conv 24 (weak 23/7, strong 8/17); 23 turn-0 contexts
  (16 strong/7 weak); `?` 37/1, `\boxed{}` 0/18; profiles 59/59 words, 374/380 chars; no R_H
  leaks its answer, no context resolves its named problem, no duplicate response text (all 0).
- **Statistics:** the exact signed-rank gives 7.62939453125e-06 for all-positive n=18, rb=+1
  / −1 / 0 with correct sign convention and p=1 on the all-zero sample; a full mock run →
  `analyze.py --allow-mock` emits exactly the registered §6 structure (four-cell, primary,
  all §6.3 secondaries incl. per-field over 4 sub-scores, §6.4).
- **Spend controls:** per-call reservation $0.05376 (8192×$5/M + 512×$25/M); ×990=$53.22;
  the cap is checked (worst-case reserved) *before* each request, so lifetime **billed** spend
  can never exceed $40; cost basis 1,639.6 in / 52.0 out (3,120 calls) → $9.72 reproduces;
  the real git-freeze gate passes on HEAD; zero paid artifacts exist (results/ = 3 tracked
  files only; tree fully clean before and after all my offline runs).

**The inference (each outcome).** A **positive** `PAG_weak` has exactly the rival readings the
prereg discloses — correct assistance-calibration for a stated support need (A5.2), not only
label anchoring — and censoring cannot manufacture it (deterministic function of the latent
score, so a true-zero profile effect yields observed PAG=0). A **null** is registered as
conditional on §6.3's pure profile effect (A5.1) and, jointly null, as *uninformative* between
"the profile never reached the rating" and "the effect fell in the censored direction" (A6.3).
The within-stimulus double-difference isolates the profile-content×pole interaction, so
between-stimulus confounds (authoring, tutor base, family, turn count) cancel under additivity
and the disclosed exception (an artifact that *interacts* with the profile) is checked by the
§6.3 all-corpus re-estimate (authoring) and disclosed as uncontrolled for base (A6.5). I could
construct **no undisclosed rival** for any outcome of the primary.

**Prior findings / remediation I re-verified:** A6.1–A6.7 (recomputed, above), B2, B3, N8 (two
mutations reproduced), N14 (the stimuli-vs-labels change history), the C018 pre-data exclusion,
the git-freeze gates, the selection determinism, the label/rep aggregation. **Taken on trust
(as the prior passes also did):** that the three label reps and nine pairing reviewers were
genuinely independent fresh contexts (no artifact carries a rep/reviewer identity); that
`claude-opus-4-8` still behaves as measured in July 2026 (the registered 165-call test-retest /
pilot D-arm check is the cheap post-hoc verification); the correctness of the vendored
`metrics.py`/`leakage.py`/`session.py` beyond byte-identity to source (they are the frozen,
commensurability-locked instrument and out of scope to re-implement).

---

## 4. NOT COVERED

- **No provider call of any kind was made.** The served-model string, real parse-failure rate,
  real token accounting, latency, and provider billing semantics remain unobserved; every
  "live" behaviour reported here came from driving the real code path with a fake caller or
  from code reading.
- **I did not re-label the 126 candidates.** I read the rubric and ~10 stimuli in full
  myself and adopted a full 55-stimulus read as *leads*; the label defensibility in NB5 is an
  adjudication on a frozen set, not a re-derivation of the annotation.
- **Vendored library internals** (`vendor/analysis/metrics.py` turn selection /
  `tutor_in_window`, `leakage.py`, `session.py`) were checked only for byte-identity to
  `conv-vs-ped-tutor@ab5ea2a9`, not audited for correctness — they are the frozen shared
  instrument.
- **`analysis/figures/fig1.py`** was exercised on mock data only (it rendered without error);
  it is a pure renderer and cannot change a reported number.
- **No power/variance simulation on real profile-arm scores** — how far a profile actually
  moves the rating is unmeasured by construction and is what the run establishes.
- **Nothing outside the two repos** — no billing dashboard, API-key limits, or org budget were
  inspected; the $40 cap is the only spend control I could verify, and only offline.
- **The predecessor audit reports** were used for orientation and for their "not covered"
  sections; I re-verified their claims only where they intersected my own checks (A6, B2, B3,
  N8, N14, the freeze/selection/label chains), and did not re-derive their pre-remediation
  evidence line by line.
