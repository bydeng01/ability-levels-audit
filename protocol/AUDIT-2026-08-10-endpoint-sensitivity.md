# VERDICT: GO-WITH-FIXES

The materials are in genuinely good shape. Every hash in `results/frozen_inputs.sha256`
recomputes; all 20 vendored files are byte-identical to source commit `ab5ea2a9`; every
composition number in Amendments A4 and A5 reproduces exactly from `corpus/stimuli.jsonl`;
the committed manifest regenerates byte-for-byte from a clean `git archive HEAD`; 79 tests
pass with zero skips and a clean worktree; no paid artifact of any kind exists. I found no
error in the frozen materials and no way to make the runner spend money it should not.

What I found instead is a **sensitivity problem in the primary endpoint that is measurable
today, for free, and is disclosed nowhere**. The companion study already rated 82 of the
110 frozen pole texts with this exact instrument and model, and its published scores show
the two poles sitting at opposite ends of the response scale: corpus `R_H` averages 4.55/5
with 47% pinned at exactly 5.0, corpus `R_L` averages 1.78/5 with 59% pinned at exactly
1.0. In the weak stratum the endpoint therefore has ~6.2 scale points of room to move in
the pre-registered "anchoring" direction and ~1.8 in the opposite direction — a 3.5:1
asymmetry that §6.2's conditional null reading (the safeguard A5 added) does not account
for. That is a limitation, not an error, and stating it costs one paragraph. It is also
pre-run-or-never: after the first judge score, adding it reads as post-hoc excuse-making,
which is exactly what the freeze exists to prevent.

Two code defects share that property. `mode_preflight` still carries the unguarded cost
computation that Amendment A5.7 claims was fixed — a self-reported remediation that only
landed on one of its two call sites — and `analyze.py`'s integrity chain terminates in an
untracked file while the committed anchor that would close it sits unread in
`results/plan.json`. Both are on frozen inputs (`run_study.py`, `analyze.py`), so both are
also pre-run-or-never: editing either after a judge score exists trips the run's own
gates. Fix these three, regenerate the manifest, re-tag, then go. The run is otherwise
sound and the $40 cap is real.

---

## 1. BLOCKING FINDINGS

### B1. The primary endpoint is asymmetrically censored by the judge's own score distribution, and §6.2's registered null reading does not survive it — MATERIAL, confidence **high**

**What is wrong.** `PREREGISTRATION.md:256-275` registers `PAG_weak` as the primary
endpoint and, via Amendment A5.1, registers a conditional reading of a null: a null
supports evidence-grounding *only if* §6.3's pure profile effect is non-null. Both
readings assume the instrument can express a profile effect in either direction. It
cannot, and the asymmetry is measurable in advance.

**Evidence, computed from the companion study's own released scores.** The source repo
holds complete per-turn pedagogy-judge output for all 2,219 corpus turns
(`conv-vs-ped-tutor/results/{ablation,confirmatory,confirmatory_gpt,confirmatory_gemini}/pedagogy_detail.json`),
produced by `claude-opus-4-8`, temperature omitted, `max_tokens` 512, 3 reps — the same
instrument this study reuses. Joining those to the 82 corpus-sourced poles of the frozen
55 by `(source_run, problem_id, turn_index)` gives 0 lookup misses and:

| | n | mean `overall` | pinned at extreme |
|---|---|---|---|
| corpus `R_H` (all) | 53 | **4.553** | 25/53 = 47% at exactly 5.0 |
| corpus `R_L` (all) | 29 | **1.782** | 17/29 = 59% at exactly 1.0 |
| corpus `R_H`, **weak stratum** | 30 | 4.567 | **16/30 = 53% at exactly 5.0** |
| corpus `R_L`, weak stratum | 12 | 2.333 | 5/12 at exactly 1.0 |

The 27 all-corpus pairs give a directly measured D-arm `Δ` of **2.889** (sd 1.09, max
4.00) — i.e. the design's contrast already consumes ~72% of the usable 4-point range
before any profile is shown.

**The consequence, algebraically.** Write `a_H = S_H(adv) − S_H(nov)` and
`a_L = S_L(adv) − S_L(nov)`. Then `PAG = a_L − a_H`. In the weak stratum the ceiling and
floor bound each term:

- `a_H ∈ [−3.57, +0.43]` — the advanced label can lower the judge's rating of the
  withholding response by up to 3.6 points, but can raise it by at most 0.43 on average,
  and **for 16 of the 30 weak stimuli by exactly zero**, because those `R_H` texts already
  scored 5/5/5.
- `a_L ∈ [−1.33, +2.67]` (corpus subset).

So observable `PAG_weak` spans roughly **[−1.77, +6.23]**: about **6.2 scale points of
headroom in the pre-registered positive ("advanced label suppresses the scaffolding
preference") direction against ~1.8 in the negative direction.**

**The concrete failure this causes.** Censoring cannot manufacture an effect, so a
significant positive `PAG_weak` remains interpretable. The failure is on the null branch,
which §6.2 explicitly calls publishable. Suppose the truth is the pedagogically
*standard* response — an advanced label makes withholding more appropriate, so the judge
rates `R_H` higher and `R_L` lower under `P_adv`. Both movements are the censored ones.
The study would observe `PAG_weak ≈ 0` **and** a near-null §6.3 pure profile effect on
both poles, and the registered conclusion would be "the profile did not reach the rating"
— which would be false. A5's conditional safeguard fails in precisely the scenario it was
added to catch.

**How I verified it.** Joined `corpus/stimuli.jsonl` to the four `pedagogy_detail.json`
files in Python (0 misses over 82 corpus poles); separately confirmed the instrument is
identical by exact byte match of 13 assembled D-arm user messages against the surviving
`logs/pedjudge-20260704-210950-761/calls.jsonl` wire log, and confirmed the source
study's `request.system` is byte-identical to the vendored `JP.PED_SYSTEM`. I also ran a
4,000-draw null simulation resampling the empirical 3-rep triples: rep noise alone leaves
a mean of 14.9 of 18 weak-stratum run means non-zero, so the endpoint is not degenerate —
it is *directionally* insensitive, which is the finding.

**Required fix (prose only; no stimulus, label, profile or estimand changes).** Add to
`PREREGISTRATION.md` §7b as Amendment A6, and to the abstract's limitations: the
measured D-arm position of both poles; the resulting one-sided censoring of `a_H` (and
`a_L` at the floor); the statement that `PAG_weak` is materially more able to express the
positive direction than the negative; and an explicit third reading of a null —
"the profile effect fell in a direction this scale cannot express" — alongside the two
§6.2 already registers. Recommend also pre-registering the ceiling/floor diagnostic that
makes this checkable after the run: report, per arm and pole, the fraction of units at
`overall == 5.0` and `== 1.0`.

**Why MATERIAL.** `PREREGISTRATION.md` is itself a frozen input (`prereg_md_sha256` in
`results/frozen_inputs.sha256`, rechecked by `run_study.py:774-780` and
`analysis/analyze.py:122-143`). Any edit to it changes the manifest and forces a
regenerated `results/frozen_inputs.sha256`, a new commit, and a new `prereg-final-*` tag.
Under this repo's design there is no such thing as a documentary edit to the
pre-registration.

---

### B2. Amendment A5.7's "a reply with no usage accounting is refused and retried" is false for `mode_preflight` — the exact defect it claims to have fixed is still on the first paid command — MATERIAL, confidence **high**

**What is wrong.** `judging/run_study.py:716`:

```python
cost = res["in_tokens"] * PRICE_IN + res["out_tokens"] * PRICE_OUT
```

is unguarded, and runs **before** `degraded_reason(res)` is consulted at `:720`. The
scoring path was fixed — `_attempt_rep` at `:669-672` guards `None` tokens and settles at
the full reservation, with a comment citing `AUDIT-2026-08-08-preflight-review-3 N7`. The
preflight path was not. `PREREGISTRATION.md:511-512` (A5.7) states the fix without
qualification.

**The concrete failure.** A preflight reply whose `usage` lacks `input_tokens` or
`output_tokens` raises `TypeError: unsupported operand type(s) for *: 'NoneType' and
'float'` after `ledger.charge()` has already committed `$0.05376`. `mode_preflight` never
calls `wire_write`, so there is no wire row either: the money is committed, the contract
is not frozen, and the ledger's own recovery instructions (`:218-222`, "recover the true
figure from `results/wire/calls.jsonl`") point at a file with nothing in it. The refusal
branch at `:720` and `:393-400` is unreachable in preflight, exactly as it was in
`_attempt_rep` before A5.7.

**How I verified it.** Read `mode_preflight` (`:700-759`) against `_attempt_rep`
(`:653-697`) and confirmed the asymmetry; two independent lines of inquiry reproduced the
`TypeError` by driving `mode_preflight` with a usage-less fake caller on a scratch copy.
Probability is low (Anthropic returns `usage` on success), severity is low in dollars, but
it is a one-line fix on the very first paid command and A5.7 asserts it is already done.

**Required fix.** Apply the `:669-672` guard at `:716`, and correct A5.7's wording to name
the paths it covers. Optionally have `mode_preflight` write wire rows so preflight spend
is reconstructible.

---

### B3. `analyze.py`'s integrity chain terminates in an untracked, hand-writable file while the committed anchor that would close it goes unread — MATERIAL, confidence **high**

**What is wrong.** `analysis/analyze.py:122-143` verifies its own sha256 and
`PREREGISTRATION.md`'s against `results/run_meta.json`; `:146-158` verifies
`run_meta.json` against `results/run_state.json`. **Nothing verifies `run_state.json`.**
All five `results/*.json*` runtime files are untracked (`git ls-files results/` returns
only `frozen_inputs.sha256`, `input_manifest.jsonl`, `plan.json`) and none is gitignored,
so the chain's root is a plain editable file. Meanwhile the correct
`analyze_py_sha256` = `06d87e24…1bd4` is recorded in **two committed, tag-covered files**
— `results/plan.json` and `results/frozen_inputs.sha256` — and `analyze.py` reads neither
(the only Python reference to `frozen_inputs.sha256` is the writer at
`run_study.py:645`).

**The concrete failure.** Editing the primary estimand at `analyze.py:247` and
re-stamping two hashes by hand (`run_meta.frozen_inputs.analyze_py_sha256` and
`run_state.result_sha256["run_meta.json"]`) makes `analyze.py` report a fabricated
`PAG_weak` with exit code 0, `per_unit.jsonl` untouched and `summary.json` carrying the
run's legitimate `contract_sha256`. This was demonstrated end to end on a scratch copy.
It extends `AUDIT-2026-08-08-preflight-review-3` N1/N2 — that pass closed the
`run_meta.json` link and recorded the residual as "deliberately not applied", judging the
proper fix to be a test-fixture redesign. It is not: comparing `frozen_inputs()` against
the committed `results/plan.json` is a few lines and closes the chain against a
git-anchored root.

**Why this blocks rather than waits.** `analyze.py` is a frozen input. Editing it after a
judge score exists trips `_validate_analysis_code_unchanged` and invalidates the run's own
provenance. Pre-run or never.

**Required fix.** In `analyze.py`'s validation block, additionally load
`results/plan.json` (tracked, tag-covered) and require
`plan["frozen_inputs"] == run_meta["frozen_inputs"]`, and require the current
`analyze.py`/`PREREGISTRATION.md` digests to match *that* record, not only `run_meta`'s.

---

## 2. NON-BLOCKING FINDINGS

**N1. The paid path has no exception handling around the provider call, so any transient
error terminates a ~27-minute run** — confidence **high**, DOCUMENTARY (operability).
`grep -n "try:\|except" judging/run_study.py` returns eleven hits, none of them around
`caller.call(...)` at `:662` or `client.messages.create(...)` at `:361`; the only `try` in
`mode_score` (`:845`) has a bare `finally: cache.flush()`. With `max_retries=0` (`:357`)
and no pacing between the ~990 sequential requests, a single 429/500/529/read-timeout
aborts the run. The cache preserves everything scored, so no data is lost and the operator
just re-runs — but each abort leaves `$0.05376` permanently committed (`charge` at `:308`
without a matching `settle`), and the source study's own judge log shows 3,120 calls over
86 minutes at 1.66 s/call, so expect **~27 minutes** of continuous exposure for 990 calls.
Budget impact is bounded by operator patience (744 aborts to exhaust the cap), so this is
robustness, not a spend hole. Recommend: catch provider exceptions, release the
reservation when the request demonstrably never reached the provider, and add bounded
backoff. If the operator prefers not to touch frozen code, plan on babysitting and
re-running.

**N2. A zeroed spend ledger is accepted; only a deleted one is caught** — confidence
**high**, DOCUMENTARY. `SpendLedger._load` (`:224-279`) cross-checks
`results/wire/calls.jsonl` only inside the `if not self.path.exists()` branch (`:225-234`).
A ledger file that exists, parses, and honestly reports `settled_usd_total: 0.0` with an
empty `invocations` list is accepted without the wire log ever being read — beside a wire
log full of live rows. Verified by execution on a scratch copy: $39 burned, ledger
rewritten to zero, another $39 spent. Deletion *is* caught. The ledger carries no MAC and
is never reconciled against `sum(cost_usd)`, even though `_corrupt`'s own message
(`:218-222`) names that as the recovery source. This is an integrity-of-the-record gap,
not an attack surface — the threat model here is operator error. Fix: cross-check against
the wire log whenever the ledger exists and take `max(ledger, wire)` as prior spend.

**N3. §8's token arithmetic is wrong in both figures, and the prompt-cache claim's premise
is wrong** — confidence **high**, DOCUMENTARY (but see B1's note: any prereg edit is
material). `PREREGISTRATION.md:530-531` and `run_study.py:641` state a "~814-token system
prompt … below claude-opus-4-8's 1024-token prompt-cache minimum"; §8 also uses a
"95-token profile block". Calibrating against real Anthropic-reported `input_tokens` from
two source judge logs with different system prompts (3,096 chars → intercept 1047.5
tokens; 2,039 chars → 723.3; identical user-side slope 0.37619 tok/char, residual sd 34):
`PED_SYSTEM` is **~1,000 Anthropic tokens**, not 814 — at or above the 1024 minimum, not
below it. Cross-checked by measuring the Anthropic/tiktoken ratio on 300 real requests
(1.508 ± 0.027) and scaling: system 663 → ~1,000 tokens; profile block 82 → **~124**
tokens, not 95. The prompt-cache threshold itself (1024 tokens for `claude-opus-4-8`) is
correct as stated. No cost or safety consequence: `messages.create` never sets
`cache_control` (`:361-364`), so no discount exists to assume either way, and the errors
run in opposite directions. Independently recomputed run cost from the same calibration:
**~$10.01** against the registered $9.72 — 3% high, immaterial against a $40 cap. Fix:
correct both numbers and restate the caching sentence as "no `cache_control` breakpoint is
sent, so no caching discount applies."

**N4. §8's "four attempts for every main-schedule unit … is intentionally impossible"
conflates the reservation ceiling with settled spend** — confidence **high**, DOCUMENTARY.
`charge` (`:295-310`) checks `settled + outstanding_committed + new_reservation > cap`, and
every reservation is settled to actual usage immediately after the call (`:673`), so
outstanding committed is ~0 during the check. The cap therefore binds on *settled* spend:
3,960 requests at the doc's own $0.009815/call basis is **$38.87 — under $40**. The
$212.89 figure is `n × attempts × reservation`, which never accumulates. The conclusion
(it will not happen) is right; the stated reason is wrong. The actual protection is the
circuit breaker, and per N9 below it is weaker than it reads.

**N5. The released-clone reproduction path the README advertises cannot work, and a code
comment asserts the opposite** — confidence **high**, DOCUMENTARY. `run_study.py:811`
states "results/preflight/ is tracked, so a released repo carries what this needs". It is
not tracked and not gitignored (`git check-ignore` returns nothing for it). To publish it
you must commit it; committing moves `HEAD`; and `load_resolved` (`:786-787`) requires
`freeze["git_commit"] == resolved["git_commit"]` for every live command, including
`--offline-cache-only`, which defaults to `--judge-backend live` and whose resolved config
records `backend: "live"`. So `README.md:81-83`'s "`--offline-cache-only` re-derives the
promoted numbers from the released per-rep cache" fails with `GIT FREEZE MISMATCH` on any
clone. `.gitignore:16-19` shows a prior audit fixed half of this (un-ignoring the cache
for exactly this reason, citing N8) without the other half. **Operator consequence to note
now: do not create any commit between `--preflight` and the end of the paid run.**

**N6. The tutor *base* is near-perfectly confounded with the R_H/R_L pole, and this is
disclosed nowhere** — confidence **high**, DOCUMENTARY. Over the 82 corpus-sourced poles:
`R_H` is gemini 23 / sonnet 19 / gpt 11, while `R_L` is **gpt 26 / gemini 2 / sonnet 1**.
So 90% of corpus-sourced low-scaffolding text was written by the GPT-based tutor and the
remaining 26 `R_L` are authored — meaning essentially *every* `R_L` is either GPT-written
or agent-authored, while `R_H` is overwhelmingly gemini/sonnet. This is the same class of
artifact as the authoring imbalance the pre-registration devotes two paragraphs to (§2,
A3.4), with the same cancellation argument and the same additivity caveat, and it is the
mechanical source of the `\boxed{}` cue (0 `R_H` / 18 `R_L`) already disclosed in A5.6.
Grep confirms `PREREGISTRATION.md` mentions tutor base only at `:100` (labellers see none)
and `:504` (corpus structure); the abstract mentions it only in describing the corpus.
Also unreported: corpus `R_L` averages 374 chars against corpus `R_H` at 254. Recommend
one disclosure sentence alongside the existing authoring paragraph.

**N7. §6.3's authoring-robustness re-estimate runs on 8 and 7 clusters, not the
27 / 12 / 15 the text quotes** — confidence **high**, DOCUMENTARY.
`PREREGISTRATION.md:284-290` describes the all-corpus subset by stimulus count. Under the
source-run inference unit that A4.3 made binding, those 12 weak stimuli sit in **8** source
runs and the 15 strong in **7**. Minimum attainable two-sided exact signed-rank p is
therefore **0.0078** and **0.0156**, against 7.6e-06 for the 18-cluster primary. A reader
comparing "the primary, re-estimated on the all-corpus subset" against the primary is
comparing 8 clusters to 18. Recomputed directly from `stimuli.jsonl`. Recommend stating
the run counts wherever the stimulus counts appear.

**N8. Five of `validate_live_cache_provenance`'s checks have no negative test, and
mutations to them survive the suite** — confidence **high**, DOCUMENTARY.
`tests/test_offline_replay.py:124-155` is named
`test_live_cache_must_match_raw_response_prompt_and_response_id` but drives exactly one
negative case: the `response_id` mismatch at `:153-155`. The raw-response hash, the
re-parse check, the prompt-hash check, the duplicate-response-id check and the
served-model checks are exercised only in the passing direction, and `:139` computes the
expected digest by calling `RS._wire_digest` — the signature scheme asserted against
itself. Targeted mutations confirm: replacing the "no matching accepted wire row"
`SystemExit` (`:494-496`) with `continue` leaves 79/79 passing while a wholly fabricated
990-entry cache validates; dropping the wire-hash check (`:472-473`) leaves 79/79 passing
while a post-hoc score rewrite validates. `run_lock` (`:527-544`) and the cache-hit resume
branch (`:848-850`) have zero coverage. This does not affect the run — the checks are
present and correct in the shipped code — but the suite does not defend them, so the
study's fraud-resistance story rests on code no test would notice being removed.

**N9. The circuit breaker is cumulative, so a late-onset systematic failure wastes ~500
calls before it fires** — confidence **high**, DOCUMENTARY. `Breaker.record` (`:334-344`)
compares lifetime `accepted/responses` against `BREAKER_MIN_ACCEPT = 0.5`. If the judge
starts failing after `k` good responses, the breaker cannot fire until `k` further
failures accumulate; the worst case sits near `k ≈ 500`, i.e. ~500 wasted responses
(≈$5 at measured usage) before abort. `AUDIT-2026-08-08-preflight-review-3` N6 recorded
this and deliberately declined to change an abort threshold mid-flight; that judgment
still looks right, and the arithmetic above is the bound it costs.

**N10. Parser edge cases in the frozen instrument** — confidence **high**, DOCUMENTARY,
inherited-upstream. Executing `JP.parse_pedagogy_scores` directly:
`{"overall": 10}` → `overall: 1` (the JSON path correctly rejects 10, then the per-field
regex `([1-5])` at `judge_pedagogy.py:145` matches the leading `1`); `{"overall": 50}` →
`5`; `{"overall": true}` → `1`; two JSON objects in one reply → the first wins. `7`, `0`,
`-3`, prose, and empty all correctly return `None` and are retried. Separately,
`aggregate_reps([full, full, only_overall])` returns `n_valid: 3` while the four sub-score
means are computed over **2** reps with no flag — so §6.3's per-field decomposition can
silently mix 2- and 3-rep means. All of this is in vendored, hash-pinned code that must not
be edited for commensurability. Recommend disclosing the sub-score caveat in §6.3 and
having the operator grep the wire log post-run for any `scores` dict with a `None`
sub-field.

**N11. `bca_ci` has an unmarked zero-width fallback** — confidence **high** (code),
**low** (likelihood), DOCUMENTARY. `analyze.py:35-36` returns `[mean, mean]` when
`len(vals) < 2 or np.allclose(vals, vals[0])`, indistinguishable in `summary.json` from a
computed BCa interval — and `figures/fig1.py:46-47` would render zero-height error bars.
§6.5 promises to report the realised interval and half-width, so a `[0.000, 0.000]` would
badly overstate precision. I initially expected this to be likely under a true null and
**measured that it is not**: resampling the empirical 3-rep triples 4,000 times under the
null gives P(all 18 weak run-means identical) ≈ 0.0000, with a mean of 14.9 non-zero run
means. Report as a latent code smell, not an expected event; a one-line `"degenerate":
true` marker would close it.

**N12. The abstract's "If null" branch states the unconditional reading that §6.2 and A5.1
forbid** — confidence **high**, DOCUMENTARY. `paper/abstract.md:115-117` reads "the judge
tracks behavioural evidence over stated labels in this setting", with no mention of the
§6.3 conditionality that Amendment A5.1 exists to impose. The abstract is a draft with
placeholders, but it is committed and is the text that becomes the paper. Same section
should also carry A5.1, A5.3 and A5.5, none of which currently appear in its limitations.

**N13. Free external validation the study is not using — worth pre-registering now**
— confidence **high**, opportunity rather than defect. Because the D-arm user message for
each stimulus's real pole is byte-identical to a call the companion study already made,
**165 of the 990 planned calls (55 stimuli × 1 real pole × 3 reps) are exact repeats of
published measurements**, and the prior 3-rep mean is known for all 55. That gives, at zero
cost: (a) a test–retest reliability estimate for the frozen instrument, (b) a direct check
that `claude-opus-4-8` still behaves as it did in July 2026 — the single biggest unverifiable
risk in this run — and (c) the ceiling/floor diagnostic B1 needs. Recommend adding it to
§6.3 as a labelled secondary before the freeze, and having the operator compare the
12-call pilot's D-arm rows against the known values before committing to the full run.

**N14. Minor corrections to the operator's stated preconditions** — confidence **high**.
"`corpus/stimuli.jsonl` … has not changed across any remediation" is not accurate:
`git log --follow` shows it changed at `9c879b6` ("Fix preflight blockers and refreeze
study inputs"), which is A4's 56→55 re-freeze. It is unchanged across the *most recent*
remediation (`ff41ecc`), which is what A5 actually claims, and the change is fully
disclosed. `labeling/labels.jsonl` genuinely has not changed since the initial freeze at
`1e4c868`. Everything else the operator asserted checks out (see §3).

---

## 3. VERIFIED — what I checked and how

**Freeze state and provenance**
- `HEAD` = `c5fdf9737fc3d6b0121f05eb316001d62290933f`, tagged `prereg-final-2026-08-08b`,
  `git status --porcelain` empty, `origin/master` at the same commit. Confirmed directly.
- **Zero paid artifacts exist.** `results/` contains only the three tracked files; no
  `preflight/`, `cache/`, `wire/`, `spend_ledger.json`, `run_state.json` or finals.
- All 12 entries in `results/frozen_inputs.sha256` recomputed with `shasum -a 256` and
  match; `corpus/stimuli.sha256`, `labeling/labels.sha256` and `corpus/candidates.sha256`
  match their artifacts.
- All **20** vendored files byte-identical to `conv-vs-ped-tutor@ab5ea2a9` via
  `git show <commit>:<path> | sha256`, and to `vendor/PROVENANCE.md`. Nothing in `vendor/`
  is unlisted.
- `results/plan.json`, `results/frozen_inputs.sha256` and `results/input_manifest.jsonl`
  **regenerate byte-identically** from a clean `git archive HEAD` tree via
  `--manifest-only` in the operator's environment (Python 3.12.8, anthropic 0.96.0,
  scipy 1.17.1, numpy 1.26.4 — matching `requirements.txt` exactly).
- `PJ.contract_sha256` recomputes to `8ad74807…d414`, the value in `plan.json`.

**Composition — every A4/A5 number recomputed from `corpus/stimuli.jsonl`**
55 stimuli; 30 weak / 25 strong; evidence moderate 37 / strong 18 / ambiguous 0;
families ped 31 / conv 24 (weak ped 23 / conv 7; strong ped 8 / conv 17); bases gpt 22 /
gemini 19 / sonnet 14; `R_H` 53 corpus / 2 authored; `R_L` 29 / 26; 27 all-corpus pairs
(12 weak / 15 strong); real turn on the high pole 43 times; **23 source runs, 18 weak /
10 strong, 5 spanning both**; prior×label over the frozen 55 = {(weak,weak) 23,
(strong,weak) 7, (weak,strong) **0**, (strong,strong) 25} — A5.3 confirmed; question mark
37/55 `R_H` vs 1/55 `R_L`; `\boxed{}` 0 vs 18; 23 contexts with `turn_index == 0`,
16 strong / 7 weak — A5.5 confirmed; zero duplicate response texts, zero duplicate
contexts. `labeling/labels.jsonl` joins to all 55 with **zero** label or
evidence-strength disagreements.

**The instrument**
- The source study's logged `request.system` is **byte-identical** to the vendored
  `JP.PED_SYSTEM` (3,096 chars), across all 3,120 logged calls; `temperature: null` on all
  3,120, `max_tokens: 512`, `model: claude-opus-4-8`, `provider: anthropic` — matching
  §2 and `vendor/configs/models.yaml`.
- Assembled D-arm user messages for the real pole **exactly match** the source study's
  judge calls on the 13 stimuli whose run appears in the surviving wire log (byte
  equality on the full user message). A parallel line of inquiry rebuilt the remaining 42
  via `analysis.judge.dialogue_for_turn` and reported 55/55 — I verified the method and
  13 instances myself and adopt the rest as consistent-but-not-personally-checked.
- All 330 assembled payloads: profile arms are exactly `PROFILE_BLOCK + D-arm message`,
  byte for byte; `assert_prompt_pure` passes on all 330; `D` never carries a profile
  block. Max request is 6,746 bytes (S15/P_adv/high) against the guard's effective 7,680,
  and max estimated input is ~2,421 tokens against the 8,192-token reservation.
- Profiles are word-matched exactly (59/59) and differ by 6 characters.

**Spending controls**
- `claude-opus-4-8` bills **$5.00 / $25.00 per MTok** — confirmed against the current
  model catalog, so the hard-coded `PRICE_IN`/`PRICE_OUT` at `run_study.py:67-68` are
  correct and the cap is not silently under-counting. (A parallel line of inquiry
  suspected Opus-tier rates might be ~3× higher; that suspicion is wrong.)
- Reservation arithmetic checks out exactly: 8192×$5/M + 512×$25/M = **$0.05376**;
  ×990 = $53.2224; ×992 = $53.32992; ×3960 = $212.8896.
- Cap validation is sound: `inf`, `nan`, `0`, `-1`, `40.01` all rejected; a stored cap
  cannot be raised on resume; `HARD_LIVE_CAP_USD` binds independently of the ledger file.
- `max_retries=0` on the SDK client and one `caller.call` per `ledger.charge` — verified
  by reading `_attempt_rep`; the vendored `_with_backoff` is not on the judging path.
- Reservation is persisted **before** the request; a crash leaves it committed
  (conservative). Cap is checked against reserved, not settled.
- Pilot and full run share the live cache namespace and the same ledger; mock rows are
  partitioned by backend.
- Independent worst-case recomputation: at the doc's basis, every reply filling
  `max_tokens` costs **$21.10** for 990 calls — comfortably inside the cap.

**Reproducibility and analysis**
- `python3 corpus/build_stimuli.py verify` passes: 55 contexts and 82 corpus-sourced
  responses rebuilt byte-identically from `corpus/logs/`. A from-scratch replay
  (`census → candidates → topup → select → assemble → freeze → verify`) against the real
  source logs reproduces `census.json`, `response_pools.jsonl`, `candidates.jsonl`,
  `selection.json`, `pairing_draft.jsonl` and `stimuli.jsonl` byte-identically — no
  circularity; the irreducible inputs are the source logs, `vendor/`, the frozen top-up
  recipe, the labels, and the human/agent decision records.
- Census reproduces exactly: 2,219 judged tutor turns; tracker join 990 with cells
  844 / 100 / 39 / 7 — matching `decisions-log.md:59-68`. The census turn set is
  **identical** to the set of `(run_id, problem_id, turn_index)` keys in the companion
  study's own `pedagogy_detail.json` files (0 in either direction).
- 41 copied `corpus/logs/*/calls.jsonl` are byte-identical to the source repo; all 38 runs
  referenced by the frozen 55 are present.
- The exact conditional signed-rank implementation agrees with an independent brute-force
  reference and with `scipy.stats.wilcoxon(method="exact")` across 15 hand-built cases,
  400 fuzz cases and 200 cross-checks — 0 mismatches on both p and rank-biserial. n=18
  all-positive gives 2/2^18 = 7.62939453125e-06 exactly. Sign convention matches §6.2.
- Source-run averaging is applied to every registered estimand (verified by instrumenting
  `bca_ci`: vector sizes 18/10 in the registered pattern, primary vector bit-identical to
  an independently computed one); BCa resamples within stratum; `summary.json` is
  byte-reproducible across runs.
- `analyze.py` has no CLI/env/config knob that can change a reported number (`--allow-mock`
  is a gate, not an estimator switch); `BOOT_SEED=13`, `N_RESAMPLES=10_000`,
  `ZERO_TOL=1e-9` are module constants.
- `python3 -m pytest tests/ -q -rs` → **79 passed, 0 skipped, 0 xfailed**, 4.24s, and
  `git status --porcelain` empty before and after.

**Prior findings and remediation claims I re-verified myself**
- **A5.7's `is_eligible` inertness** — re-verified by restoring the exact pre-A5.7
  `_states_answer_in` (regex loop only, no `solution_form` clause) and re-running
  eligibility over all 126 candidates: 101 eligible both ways, **0 changed**. Claim holds.
- **A5's headline hashes** — `corpus/stimuli.jsonl` = `1d240ebc…8c5376` and
  `labeling/labels.jsonl` = `fda2bc3d…2707d4`. Both confirmed.
- **A5.7's `--offline-cache-only` fix (N1)** — `finalize(compare_existing=True)` at
  `run_study.py:961-971` compares the three data files and aborts with
  `OFFLINE RECONSTRUCTION MISMATCH` without overwriting;
  `tests/test_offline_replay.py:157-182` is a genuine regression test that asserts the
  tampered file survives. Holds.
- **A5.7's `analyze.py` self-digest fix (N2)** — present at `:122-143` and functional; the
  residual is B3.
- **A4.2's C018 exclusion** — `C018` absent from the frozen set, asserted by
  `tests/test_stimuli.py:41`.
- **A4.4's git-freeze gates** — `require_git_freeze` demands a clean tree and a
  `prereg-final-*` tag at preflight, and every later live mode rechecks contract,
  frozen inputs, commit and tag via `load_resolved`.
- **B4/A3.3's tautology correction** — `agreement_ok` is `True` for all 126 and is
  annotated as structurally-always-true; unanimity is 115/126.
- Reliability statistics recomputed independently: unanimity 115/126; pairwise inter-rep
  agreement 94.4 / 94.4 / 93.7% over 126 and 94.8 / 94.8 / 95.8% over 96; 84 weak / 42
  strong; v1→v2 confusion {20, 0, 45, 31} with κ = 0.223. All match.
- The blind labelling batches contain only `{candidate_id, context}` — no policy, run id,
  base, tracker, prior or stratum — across all 383 items; rep orders are genuinely
  different (Spearman +0.020 / −0.072 / +0.021); the merge to `labels.jsonl` recomputes
  with 0 mismatches. The pairing packets contain no labels, profiles or policy names, and
  all 55 frozen pairings trace to a recorded review decision with matching text and
  provenance.
- The manipulation check's 55/55 recomputes from `_key.json` and the response files with
  0 duplicates and 0 unrated items; A/B assignment is not recoverable from position.

**Taken on trust (not verifiable offline)**
That the three labelling reps and the nine pairing reviewers were genuinely independent
fresh contexts — no artifact carries a rep, reviewer, session or model identifier, so this
rests entirely on the decisions-log narrative. That `claude-opus-4-8` is still served and
still behaves as the companion study measured (N13 is the cheap way to check this after
the pilot).

---

## 4. NOT COVERED

- **No provider call of any kind was made.** The served model string, real parse-failure
  rate, real token accounting, real latency, and provider billing semantics remain
  unobserved. Every "live" behaviour reported above was produced by driving the real code
  path with a fake caller or by unambiguous code reading.
- **I did not re-label the 126 candidates.** I read ~15 stimuli in full against
  `labeling/RUBRIC.md`. A parallel line of inquiry independently re-labelled 17 contexts
  and agreed on 14; its one disagreement inside the frozen set is **C036 / S01** (strong
  stratum, unanimous 3/3 in the released labels) on the grounds that every student turn
  answers exactly the question the tutor posed and the final turn carries an unrepaired
  conceptual error ("since the 70% solution is pure acid"). I report this as a **lead, not
  a finding**: it is a single Claude-family rater on a genuine rubric boundary, it sits in
  the strong stratum (so it touches PAG_strong and §6.4, not the primary), and re-cutting a
  frozen label on one rater's read is exactly what the freeze forbids. The related
  observation that the weak/strong boundary partly tracks how explicitly the *tutor*
  pre-wrote the step is worth a limitation sentence but is not established here.
- **`vendor/analysis/metrics.py` beyond a turn-indexing spot check.** Turn grouping,
  responder selection and `first_seq` were cross-checked against raw `calls.jsonl` for all
  23 source runs with 0 discrepancies, but `tutor_in_window`, the visible-turn logic and
  the rest of its 650 lines are inherited trust.
- **The mutation sweep was targeted, not exhaustive** (~87 mutations). Unswept areas
  include most of `corpus/build_stimuli.py`, `corpus/manipulation_check.py` and
  `labeling/label_competence.py` (0% test coverage each — their frozen JSON outputs are
  cross-checked, their code is not), and the real `_git_freeze_snapshot`, which
  `tests/test_freeze.py:102` monkeypatches away.
- **`analysis/figures/fig1.py` was read, not executed** on real data — it needs a
  `summary.json` from a real run. It is a pure renderer of `summary.json` and cannot
  disagree numerically, but it does not read `reportable`, so it will happily render a
  mock-backed summary, and `analysis/out/` is gitignored so its input leaves no repo trace.
- **No power simulation on real profile-arm variance.** B1's censoring analysis uses the
  companion study's D-arm-equivalent scores; how much a profile actually moves those
  scores is unmeasured by construction and is what the run will establish.
- **Nothing outside the repo pair**: no billing dashboard, API-key limits, organization
  budget, or provider-side spend controls were inspected.
- **The three predecessor audit reports were used for orientation and for their NOT
  COVERED sections, not systematically re-verified line by line.** Where their claims
  intersected my own checks they held, except as recorded in B2, B3, N5 and N8. I did not
  re-derive their pre-remediation evidence.
