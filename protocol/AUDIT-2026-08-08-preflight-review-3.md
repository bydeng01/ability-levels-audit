# VERDICT: GO-WITH-FIXES

**Independent pre-flight audit, third pass, 2026-08-08. Provider calls made: ZERO. Money spent: $0.00.**

The engineering here is unusually good and almost every quantitative claim in the
repository is exactly true — I recomputed the frozen-set composition, the entire
labelling reliability chain, the v1→v2 confusion table, the cost arithmetic, the
signed-rank implementation, the vendored provenance, and the full construction chain
from the source repository's raw logs, and all of them reproduce to the byte or to the
digit. The spend controls resisted every attack I could construct. What stops the run
today is three things: (1) the tree still has no `prereg-final-*` tag and three
untracked paths, so `--preflight` will abort before it constructs a client — mechanical,
and the runner enforces it; (2) the frozen judge system prompt contains the sentence
*"Base your rating only on the dialogue shown"*, while the manipulated factor is placed
**outside** the dialogue — so the pre-registered reading of a null primary endpoint
(§6.2: "the judge grounds its preference in behavioural evidence") is not licensed by
this design, and nothing in the frozen materials acknowledges it; and (3) the two
profile texts differ not only in stated ability but in a **stated need for step-by-step
help**, which is precisely what the rubric's `assistance_calibration` dimension asks the
judge to score, so a *positive* PAG is equally consistent with correct assistance
calibration as with label anchoring. (2) and (3) make the registered interpretation of
the primary endpoint indefensible in **both** directions. Both are fixable in an hour by
a pre-data amendment (an "A5") that costs nothing now and is impossible to make
credibly once scores exist — which is exactly what a freeze is for. Fix those three,
then run: the $9.72 buys a real measurement, and the rest of the apparatus is sound.

---

## Filename note

The brief asked for `protocol/AUDIT-<today>.md`. That path — `protocol/AUDIT-2026-08-08.md`
— **already exists**: it is the *first* audit, referenced by `README.md:100` and
`protocol/PREREGISTRATION.md:8`. Writing there would have destroyed it and broken both
references. `protocol/AUDIT-2026-08-08-independent-review.md` is also taken (an earlier,
explicitly incomplete second review). This report is therefore at a third, non-colliding
path. Rename if you prefer; do not overwrite either predecessor.

**During the audit itself, no file in this repository was created or modified except
this one** (the remediation in the appendix came afterwards, on a separate instruction).
All experiments ran on `cp -a` copies under a scratch directory. Confirmed at the end of
the audit phase:
`git status --porcelain --untracked-files=all` still lists exactly the three pre-existing
untracked paths plus this file, and `corpus/stimuli.jsonl` / `labeling/labels.jsonl`
still hash to `1d240ebc…8c5376` / `fda2bc3d…2707d4`. I treated
`~/Documents/GitHub/conv-vs-ped-tutor` as read-only (only `git show` and reads of
`logs/`); its worktree is clean.

I treated the two predecessor audits as unverified claims, not as evidence. Where I
checked their assertions they largely hold; the exceptions are B1 and N1–N2 below.

> **Post-audit note (same day).** The repository owner subsequently asked for the fixes
> to be applied, and they were — see **Appendix: remediation applied** at the end. Every
> `file:line` citation in this report refers to the tree **as audited**, at
> `HEAD 9c879b63` before any fix; several have shifted. **The VERDICT above is not
> revised.** It was a judgment about the tree that was audited, and the remediation is a
> self-report by the same agent that wrote the findings — exactly the pattern this
> report criticises in the first audit's §6 addendum. It needs independent
> re-verification, and B1 remains open regardless.

---

## 1. BLOCKING FINDINGS

### B1. The freeze the protocol depends on has still not been enacted

**What is wrong.** `HEAD` is `9c879b63d311841352a32a36066431aef7ebc2ce`; the only tag in
the repository is `prereg-frozen`, which points at `1e4c8686…` (the superseded 60-item
design). No tag at `HEAD` starts with `prereg-final-`. Three paths are untracked
(`corpus/logs/abl-s0-ped_no_gate-r0/calls.jsonl`,
`corpus/logs/conf-gpt-s0-ped-r7/calls.jsonl`,
`protocol/AUDIT-2026-08-08-independent-review.md`), and this report makes a fourth.

**Evidence.** `judging/run_study.py:175-190` (`require_git_freeze`) and
`judging/run_study.py:691` (`mode_preflight` calls it first when `backend == "live"`).
`protocol/PREREGISTRATION.md:3-10` makes the tag part of the freeze.

**How verified.** `git rev-parse HEAD`, `git tag --points-at HEAD` (empty),
`git tag -l` (`prereg-frozen` only), `git rev-list -n1 prereg-frozen`,
`git status --porcelain --untracked-files=all`. Separately confirmed that the frozen
55-stimulus artifact *is* already committed and matches the worktree:
`git show HEAD:corpus/stimuli.jsonl | shasum -a 256` = `1d240ebc…8c5376` = the worktree
file. So this is now purely the tag plus three stray files, not a content gap.

**Concrete failure.** `python3 judging/run_study.py --preflight` exits with
`LIVE RUN REQUIRES THE FROZEN TREE TO BE CLEAN` / `LIVE PREFLIGHT REQUIRES A TAG AT
HEAD` before an `anthropic.Anthropic` client is constructed. No money can be spent from
this checkout. Without the tag there is no immutable identity for the pre-data claim.

**Required before the run.** Decide what to do with the two untracked `corpus/logs/`
directories (see N10 — they are *not* referenced by any frozen stimulus; committing them
as unused donor-pool material or deleting them are both fine, but do it deliberately),
commit the intended tree including the audit reports, re-run the suite from a clean
checkout, then `git tag prereg-final-2026-08-08`.

**Confidence: high.**

---

### B2. The frozen instrument tells the judge to ignore the manipulated factor, and §6.2 registers an inference that cannot survive that

**What is wrong.** The system prompt sent on every one of the 990 calls ends with the
constraint list, whose last bullet is:

> `- Base your rating only on the dialogue shown.`

and whose opening sentence is *"Rate ONLY the final tutor turn, read in the context of
the dialogue shown."* The manipulated factor — the profile block — is prepended to the
**user** message, above `"Here is a tutoring dialogue…"` and outside the triple-quoted
`DIALOGUE:` region. It is, verbatim, information that is not in the dialogue shown, and
the instrument explicitly instructs the judge not to use it.

The pre-registration then commits to this reading of the modal outcome:

> `protocol/PREREGISTRATION.md:261-262` — "A null (CI tight around 0) is a publishable
> finding: the judge grounds its preference in behavioural evidence."

That inference is not available. "The judge grounded its rating in the behavioural
evidence" and "the judge complied with an explicit instruction to disregard everything
outside the dialogue" predict the same observation, and this design contains no
registered way to separate them.

**Evidence.**
- `vendor/analysis/judge_pedagogy.py:104` — the constraint bullet.
- `vendor/analysis/judge_pedagogy.py:61-62` — "read in the context of the dialogue shown".
- `vendor/analysis/judge_pedagogy.py:107-112` — `PED_SYSTEM` composition (both texts are in it).
- `judging/profile_judge.py:51-54, 79-84` — the profile block is prepended to `PED_USER`, outside the dialogue.
- `protocol/PREREGISTRATION.md:261-262` — the registered null interpretation.
- `protocol/PREREGISTRATION.md:158-160` — §4.1(b) **cites this very clause** ("the frozen rubric says 'read in the context of the dialogue shown'") to justify cutting the profile-only arm. The clause was read, reasoned from for a different decision, and not applied to the main manipulation.

**How verified.** I assembled a real payload rather than reading templates: built
`PJ.build_user(stimulus, "P_adv", "high", profiles)` and `PJ.build_system()` for the
frozen stimuli and printed the exact bytes that would be sent. The profile block sits
above the dialogue delimiter; the constraint is in the system prompt. `grep -rn "only on
the dialogue\|dialogue shown\|Base your rating" README.md paper/ protocol/*.md` returns
no discussion of the conflict anywhere in the frozen materials (only §4.1's unrelated
use of the phrase, and the earlier incomplete review).

**Concrete failure.** The likely outcome of this experiment is a small PAG. Under the
current registration that gets written up as "the judge tracks behavioural evidence over
stated labels — an encouraging validity result" (`paper/abstract.md:115-117`). A
competent reviewer will point out that the instrument told it to, and the claim
collapses. $9.72 is not the loss; the loss is a headline finding that cannot be
defended, in a pre-registration that by its own rules cannot be amended after the data
exists.

**The fix is cheap and already half-built.** §6.3 registers the *pure profile effect*,
`S_s(R | P_adv) − S_s(R | P_nov)` per pole — a direct measurement of whether the judge
attends to the profile at all. Record a pre-data amendment that (a) discloses the
instruction conflict, and (b) makes the null reading of §6.2 **conditional** on the
§6.3 pure-profile effect being non-null; if both are null, the registered conclusion is
"the judge did not use the profile", not "the judge grounded in evidence". That is
honest, costs nothing, and must be written before the tag.

**Confidence: high** that the conflict exists and is undisclosed. **Medium** on how much
it will actually suppress the effect — that is empirical, which is exactly why it has to
be registered as a caveat rather than resolved after the fact.

---

### B3. The profile texts confound stated ability with a stated need for assistance — the construct one of the four rubric dimensions directly scores

**What is wrong.** The two frozen profiles are not minimal contrasts on ability. Each
carries a sentence about how much help the student wants:

- `profiles/profiles.yaml:17-18` — novice: *"…say they usually **need step-by-step help** to make progress."*
- `profiles/profiles.yaml:24-25` — advanced: *"…say they usually **work through problems independently without help**."*

The rubric asks the judge to score:

> `vendor/analysis/judge_pedagogy.py:73-77` — "assistance_calibration (right amount of
> help): Does the turn give the right amount of assistance … 1 = badly over-assists
> (does it for them) OR badly under-assists…"

An evaluator that raises `Δ` (preference for high scaffolding) when told the learner
needs step-by-step help, and lowers it when told the learner works without help, is
doing the rubric's job correctly. That behaviour produces a **positive PAG** — the
study's headline "failure mode".

**Evidence.**
- `profiles/profiles.yaml:14-26` (full texts, and the header at `:4` claiming they differ "ONLY in stated ability").
- `protocol/PREREGISTRATION.md:69-70` — "Profile texts … contain no dialogue hints and **no weighing instructions**."
- `tests/test_instrument.py:36-40` — the test backing that claim scans for judge-directed phrasings (`"you should"`, `"when rating"`, `"weigh"`, `"take this into account"`, …). It cannot catch a first-person statement of a support need, and does not claim to.
- The only place this is written down is `paper/abstract.md:123-124`, which is **not** a frozen input (`judging/run_study.py:584-600` lists the twelve manifest entries; `paper/abstract.md` is not among them) and can be edited at any time.

**How verified.** Read the assembled profile block in a real payload; read the four
rubric dimensions in `PED_SYSTEM` as sent; checked `frozen_inputs()` membership;
confirmed the purity test's token list by reading it and by noting that all 70 tests
pass with the current profile texts in place.

**Concrete failure.** If PAG_weak > 0, `paper/abstract.md:111-113` writes it up as
"pedagogy-aware judging inherits a demographic-prior failure mode: the same struggling
learner is judged to need less scaffolding purely because of a label." The word "purely"
is false for these stimuli — the label is bundled with an explicit statement of need.
Combined with B2, both signs of the primary endpoint currently have an unregistered
alternative explanation.

**Fix.** Either (preferred, zero cost) amend §2 pre-data: state the bundling explicitly,
withdraw "differing ONLY in stated ability" from `profiles/profiles.yaml:4`, and reframe
the endpoint as "profile influence" rather than "anchoring on an ability label"; or
(costlier, requires a re-freeze) drop the third sentence from both profiles, which keeps
them length-matched and removes the confound outright. Do not proceed on the current
wording with the disclosure living only in a mutable draft.

**Confidence: high.**

---

## 2. NON-BLOCKING FINDINGS

### N1. The promoted numbers are not tamper-evident — the hash manifest is stored in the file it is meant to protect, and nothing re-derives the scores from the wire evidence

**What is wrong.** `promote()` hashes the four final files and stores the manifest in
`results/run_state.json`; `analyze.py` then validates the four files against the manifest
*in that same unsigned file*. Nothing checks that `per_unit.jsonl` is derivable from the
per-rep cache. `README.md:92-95` advertises this chain as an integrity guarantee.

**Evidence.** `judging/run_study.py:550-559` (`promote`); `analysis/analyze.py:122-134`
(`_validate_promoted_hashes` reads `state["result_sha256"]` and compares against the same
`results/` files); `analysis/analyze.py:137-148` (`_validate_live_provenance_files`
compares cache/wire file hashes to `run_meta.json` — untouched by this attack).

**How verified — demonstrated end to end, not reasoned about.** In a scratch copy I ran
the full mock pipeline (`--manifest-only`, `--preflight --judge-backend mock`,
`--judge-backend mock` → 330 units / 990 rows promoted). Then I rewrote every
`(P_adv, high)` row's `overall_mean` to `1.0` in `results/per_unit.jsonl` and refreshed
that one entry in `run_state.json`'s manifest. `python3 analysis/analyze.py --allow-mock`
accepted it and reported

```
PRIMARY PAG_weak: mean +1.940 CI [1.495, 2.588] Wilcoxon p=1.52587890625e-05 r_rb=1.0
```

against the honest `mean +0.179 … p=0.737`. Every provenance gate passed. I then ran
`--offline-cache-only` on the tampered tree: it **silently rewrote** `per_unit.jsonl`
from the cache back to the correct values and re-promoted, reporting no discrepancy
(verified by diffing against the pristine copy). `tests/test_analyze.py:258-264`
(`test_analysis_refuses_post_promotion_file_edit`) catches only the case where the
manifest is *not* refreshed.

**Concrete failure.** A post-hoc edit of the promoted scores is neither prevented nor
detected by anything in the shipped pipeline. It is recoverable by an independent party
who happens to re-run the reconstruction *and* diff, but the tool that exists to do that
repairs the evidence instead of reporting it.

**Fix.** Two lines of work: (a) make `--offline-cache-only` compare against the existing
finals and abort on any difference rather than `os.replace` over them; (b) have
`analyze.py` rebuild `per_unit` from the released cache (or at minimum assert
`per_unit.overall_mean` equals `aggregate_reps` of the cached reps) before computing
statistics. Neither changes any registered quantity.

**Confidence: high (demonstrated).**

---

### N2. The analysis code is bound for live *scoring* but not for *analysis*, and `summary.json` inherits a contract hash that no longer describes it

**What is wrong.** `analysis/analyze.py` is in `frozen_inputs()`, so a live scoring
invocation aborts if it changed since preflight. After the run, nothing re-checks it.
`summary.json` copies `contract_sha256` out of `run_meta.json`, so a tampered analysis
emits output stamped with the legitimate contract.

**Evidence.** `judging/run_study.py:596` (`analyze_py_sha256` recorded);
`judging/run_study.py:764-770` (`load_resolved` compares `frozen_inputs`, live path only);
`analysis/analyze.py:353-354` (`"contract_sha256": meta["contract_sha256"]`).

**How verified.** After the mock run I patched one statement in the copy's `analyze.py`
so `out["primary_PAG_weak"]` was computed from the **strong** stratum, and re-ran. It
printed `PRIMARY PAG_weak: mean -0.682 … p=0.3125` — the strong-stratum number under the
primary label — with no gate firing and no hash complaint.

**Concrete failure.** The freeze does not cover the step where a result is turned into a
claim. `README.md:87-88` groups "analysis code, and the analysis plan" with the
hash-bound artifacts, which reads as stronger than what is enforced. Git and the recorded
`analyze_py_sha256` make this *auditable* by a third party, but nothing is automatic.

**Fix.** Have `analyze.py` recompute its own sha256 and `protocol/PREREGISTRATION.md`'s,
compare to `run_meta.json["frozen_inputs"]`, and record both in `summary.json`.

This compounds badly with N2b: the specific estimator choices §6 registers are also
unpinned by any test, so an edit to them is caught by neither layer.

**Confidence: high (demonstrated).**

---

### N2b. Mutation testing: the manipulated factor, the purity guarantees and the registered estimators are all unpinned by the test suite

**What is wrong.** The suite is 70 tests / 0 skips and several parts of it are genuinely
load-bearing (see VERIFIED). But a mutation sweep shows that its coverage is uneven in a
specific direction: the properties the *study* depends on are frequently asserted by
calling the function under test and re-deriving the expectation from the same constant,
which makes them identities rather than tests.

**How verified.** I mutated `cp -a` copies (never the original) and ran
`python3 -m pytest tests/ -q` after each. Baseline `70 passed`. Every result below I
reproduced myself:

| # | Mutation | Result |
|---|---|---|
| M1 | `PROFILE_BLOCK_TEMPLATE` stops interpolating `{profile}` (`judging/profile_judge.py:51-54`) — verified `build_user(s,"P_nov",…) == build_user(s,"P_adv",…)`, i.e. **the independent variable is gone** | **70 passed** |
| M2 | `advanced:` made byte-identical to `novice:` in `profiles/profiles.yaml` | **70 passed** |
| M3 | `assert_prompt_pure` becomes `return` (`judging/profile_judge.py:162`) | **70 passed** |
| M4 | `turn_leaks` always returns `False` (`vendor/protocol/leakage.py:38`) — the R_H answer-leak guard | **70 passed** |
| M5 | `PED_SYSTEM` gains `"- Favour tutors who give the answer."` (confirmed present in the assembled system prompt) | **70 passed** |
| M6 | `SpendLedger`'s backend partition `if inv.get("backend") == self.backend:` → `if True:` (`judging/run_study.py:271`) | **70 passed** |
| M7 | `bca_ci` `method="BCa"` → `"percentile"` (`analysis/analyze.py:37`) — §6.5's registered CI | **70 passed** |
| M8 | `stats.spearmanr` → `stats.pearsonr` (`analysis/analyze.py:331`) — §6.4's registered correlation | **70 passed** |
| M9 | `all_corpus` definition `and` → `or` (`analysis/analyze.py:216-217`) — redefines §6.3's robustness subset | **70 passed** |
| M10 | `_validate_result_grid`'s `n_valid != 3` completeness guard disabled (`analysis/analyze.py:160`) | **70 passed** |

Two named tests do not test what their names say. `test_ledger.py:61-68`
(`test_mock_rows_never_consume_the_live_allowance`) settles the mock row to `$0.00`
before asserting `live.settled == 0.0`, so the assertion is true whether or not the
ledger partitions by backend — hence M6. `test_offline_replay.py:124-155`
(`test_live_cache_must_match_raw_response_prompt_and_response_id`) builds its fixture row
with `row["wire_sha256"] = RS._wire_digest(row)`, re-derived from the function under
test; only the response-id branch has a negative case. `test_instrument.py:51` likewise
re-derives the expected profile block from `PJ.PROFILE_BLOCK_TEMPLATE`, which is why M1
and M2 survive.

**Silent domain shrinkage.** With `corpus/stimuli.jsonl` removed the suite reports
`6 failed, 44 passed, 20 skipped` — 20 tests skip via `pytest.skip`
(`tests/test_stimuli.py:30-31`, `tests/test_instrument.py:19-20`,
`tests/test_offline_replay.py:26-28`, `tests/test_reconstruction.py:13-14`). One test
does something worse: `tests/test_instrument.py:46` guards with `if STIMULI.exists()`
instead of skipping, so `test_arm_equivalence_byte_identical_except_profile_block`
silently degrades from 55 real stimuli to the single synthetic `PREFLIGHT_STIMULUS` and
still reports `1 passed`.

**Scope — what the freeze still catches, in fairness.** M1, M2, M3, M5 and M6 all touch
files inside `frozen_inputs()`, and M1/M2/M5 additionally change values hashed into
`contract_sha256` (`judging/profile_judge.py:129-145` hashes `profiles`,
`profile_block_template`, `system`, `user_template`). A live invocation after preflight
would abort on any of them, and `vendor/` is additionally `chmod 444` on disk (M4 and M5
required `chmod u+w` before they would apply — a real, if informal, barrier). So these
are *test-suite* gaps, not unguarded live paths. **M7–M10 are the exception and the
serious ones**: they live in `analysis/analyze.py`, which N2 shows is not re-checked at
analysis time. An edit swapping the registered BCa interval for a percentile one, or
Spearman for Pearson, or redefining the §6.3 subset, would be caught by neither the tests
nor any runtime gate, and `summary.json` would still carry the legitimate contract hash.

**Concrete failure.** The green suite is not evidence that the manipulated factor is
present, that prompts are pure, that R_H does not leak, or that §6's registered
estimators are the ones being computed. It is evidence about the plumbing.

**Fix.** Cheap and targeted: (a) one test asserting
`build_user(s,"P_nov",…) != build_user(s,"P_adv",…)` and that each arm's prompt contains
its own profile's distinguishing string; (b) pin `PED_SYSTEM`/`PED_USER` and the two
profile texts by sha256 in a test, not by a probe substring; (c) negative tests for
`assert_prompt_pure` and `turn_leaks` (feed each a string that must trip it); (d) assert
`summary.json`'s `four_cell_table` CI method, the correlation name, and the all-corpus
subset size against §6; (e) change `tests/test_instrument.py:46` to use the same skip
guard as its neighbours.

**Confidence: high (all ten mutations reproduced on my own copies).**

---

### N3. The strong stratum is 100% strong-sampling-prior — every candidate where the blind label overturned the prior toward "strong" was removed before the freeze

**What is wrong.** §3 opens by insisting that the tutor's own state-tracker was used
"ONLY as a sampling prior … using them as ground truth would be circular", and that the
analysis stratum comes from an independent blind pass. In the frozen set, the two
coincide exactly on the strong side.

**Evidence and how verified** (recomputed from the artifacts, not read from a document):

Prior × blind label over the 126-candidate pool, and after `is_eligible`:

```
POOL (126)      {(weak,weak):45, (strong,weak):39, (weak,strong): 9, (strong,strong):33}
ELIGIBLE (101)  {(weak,weak):38, (strong,weak):37, (weak,strong): 1, (strong,strong):25}
FINAL (55)      {(weak,weak):23, (strong,weak): 7, (weak,strong): 0, (strong,strong):25}
```

The nine `(weak-prior, strong-label)` candidates — the only cases in the whole pool where
the blind pass overturned the prior toward "strong" — are
`C006 C018 C024 C029 C037 C041 C052 C073 C078`. Eligibility removes eight of them (89%
drop rate, against 24% / 16% / 5% for the other three cells); the survivor is `C018`,
which is precisely the item removed by the Amendment A4 pre-data material exclusion.
Computed with `BS.is_eligible` over `corpus/candidates.jsonl` + `labeling/labels.jsonl`,
and with `sampling_prior_stratum` read directly from `corpus/stimuli.jsonl`. For all 56
ped-family candidates the prior *is* the tracker record (`tracker` non-null); for all 70
conv-family candidates it is the lexical struggle score.

**Concrete failure.** Nothing here is fraudulent — each step was independently motivated
and pre-data — but the released materials contain zero counterexamples to "strong label =
strong prior". §3's independence claim is therefore untestable inside the frozen set, and
the strong stratum inherits whatever bias the tracker (same model family as the judge)
carries. This bears on the four-cell table, PAG_strong and §6.4 — not on the primary
endpoint, which is within-stimulus. A reviewer who computes this crosstab will raise it.

**Fix.** Disclose the crosstab in §3 and in the limitations. It costs one table.

**Confidence: high.**

---

### N4. The eligibility filter drops 34% of conv-family candidates and 2% of ped-family — an undisclosed differential on a factor already known to be collinear with the stratum

**What is wrong.** `is_eligible`'s only operative disqualifier removes contexts whose
named problem is already resolved somewhere in the dialogue — which is close to a
definition of what ConvTutor policies do.

**Evidence / how verified.** Recomputed over all 126 candidates with
`corpus/build_stimuli.py:285-303`:

```
family:  conv 24/70 = 34%      ped  1/56 = 2%
policy:  conv_no_final_answer 7/16 = 44%   conv 17/52 = 33%
         ped 1/43 = 2%   ped_no_cascade 0/13   conv_socratic 0/2
```

Attribution of the 25 drops: `resolved_in_ctx` alone 13, `closing + resolved_in_ctx` 7,
`answer_in_last + resolved_in_ctx` 5. Disqualifiers 1 and 2 never fire on their own, so
the filter is operationally single-criterion; the docstring's claim at
`corpus/build_stimuli.py:294-297` that removing the old `and "?" not in last` escape
hatch "changes no candidate's eligibility" is true but vacuous.

**Concrete failure.** §A3.6 already discloses that tutor family is nearly collinear with
the competence stratum (ped 23 weak / 8 strong; conv 7 weak / 17 strong). What is not
disclosed is that a filter added late, after the labels existed, is what produced a good
part of that shape. Add it to the same disclosure.

**Confidence: high.**

---

### N5. 23 of the 55 "dialogue contexts" contain no tutor turn at all, and they are concentrated in the strong stratum

**What is wrong.** 23 stimuli (42%) have a context consisting of a single student
message — `turn_index == 0`, no `Tutor:` block anywhere. The split across the
stratification factor is 16 of 25 strong (64%) against 7 of 30 weak (23%).

**Evidence / how verified.** Split each `context` on the same boundary the renderer uses
(`\n\n(?=(?:Student|Tutor): )`) and counted; cross-checked with
`"Tutor: " not in context`. Both give the same 23 ids
(`S03 S06 S07 S08 S10 S11 S16 S19 S21 S22 S26 S27 S31 S32 S35 S36 S41 S42 S43 S45 S49 S51 S55`)
and the same 16/7 split. `turn_index` distribution: `{0: 23, 1: 18, 2: 7, 3: 7}`.

**Concrete failure.** Two things. (a) The amount of behavioural evidence available to
ground a rating is systematically smaller in the strong stratum, and the profile block is
95 tokens regardless — so the weak-vs-strong comparison in the four-cell table, PAG_strong
and §6.4 is confounded with how much dialogue there is. (b) `PREREGISTRATION.md:34-36`
and `paper/abstract.md:35-36` describe the material as "55 dialogue contexts"; for 42% of
them the "dialogue" is one student message plus the rated reply. Disclose both. The
primary endpoint is unaffected (within-stimulus).

**Confidence: high** on the counts; **medium** on how much the evidence-quantity
asymmetry actually matters.

---

### N6. The circuit breaker is a cumulative-rate breaker, so it is nearly blind to a late-onset systematic failure

**What is wrong.** `Breaker` counts every response ever seen in the invocation and fires
only when the *lifetime* accept rate drops below 50%.

**Evidence.** `judging/run_study.py:327-342`; `BREAKER_WARMUP = 12`,
`BREAKER_MIN_ACCEPT = 0.5` at `:73-74`.

**How verified.** By reading, plus the observed mock run: 990 reps required 1,027
physical attempts (37 seeded first-attempt failures), and the breaker never approached
its threshold. After N accepted responses it takes N consecutive failures to fire.

**Concrete failure.** If the judge starts refusing at call 500, roughly 500 further
failed responses are needed before the breaker trips. The actual backstop is the ledger,
and the default cap ($40) is 4.1× the $9.72 point estimate — so the realistic worst case
is a wasted ~$10–25 followed by a completeness-gate refusal, not a runaway. Consider a
windowed rate (e.g. last 30 responses) and/or `--cap 15` for the main run, which still
leaves 50% headroom over the estimate.

**Confidence: high.**

---

### N7. The "missing usage accounting" degraded branch is unreachable — it raises `TypeError` first

**What is wrong.** The module docstring promises that responses with missing usage are
"REFUSED, never parsed into a score; the rep is retried on a fresh request". The cost
line runs before `degraded_reason` is consulted.

**Evidence.** `judging/run_study.py:661` computes
`cost = res["in_tokens"] * PRICE_IN + res["out_tokens"] * PRICE_OUT`;
`degraded_reason` is called at `:663`; the branch it would return is at `:396-397`.
Docstring claim at `judging/run_study.py:33-35`.

**How verified.** Executed `degraded_reason({... "in_tokens": None, "out_tokens": None})`
→ `"missing usage accounting"`, then executed the cost expression on the same dict →
`TypeError: unsupported operand type(s) for *: 'NoneType' and 'float'`.

**Concrete failure.** A response with absent usage crashes the run *after* the request was
charged and *before* `wire_write`, so the paid call leaves no wire row. The reservation
stays committed (conservative) and the cache keeps everything else, so it is recoverable —
but the advertised refuse-and-retry never happens. Move the cost computation below the
degraded check and treat missing usage as the worst case.

**Confidence: high.**

---

### N8. Internal numeric drift inside the frozen pre-registration

**What is wrong.** Amendment A3 states figures for the superseded 56-stimulus set in the
present tense, and they contradict §2/§4b/A4's figures for the frozen 55:

- `PREREGISTRATION.md:391` — "ped 23 weak / **9** strong"; A4 at `:424-425` and the
  artifact both give ped 8 strong (I recomputed: `{(ped,weak):23, (ped,strong):8,
  (conv,weak):7, (conv,strong):17}`). As written, §A3 implies 32 ped items against A4's 31.
- `PREREGISTRATION.md:392-393` — "37/**56** R_H … 18/**56** R_L"; §4b at `:199-201` gives
  37 of 55 and 18 of 55. I recomputed: `?` in 37 R_H / 1 R_L; `\boxed{}` in 0 R_H / 18 R_L
  — the numerators are right, the denominators are stale.
- `PREREGISTRATION.md:34-35` and `paper/abstract.md:35` describe the corpus as
  "7 tutor policies × 3 tutor bases"; the actual layout (decisions-log:24-29) is 5 ablation
  policies × 10 reps on sonnet only, plus 3 conditions × 3 bases × 10 reps = 140 runs.
  Only `conv` and `ped` exist on three bases.
- `corpus/selection.json` still reports `n_dropped_no_agreement: 0`, the statistic
  Amendment A3.3 retired as a tautology (it is annotated as structurally-always-true in
  `labeling/label_competence.py:178-186`, but the selection record still carries it).

**How verified.** Recomputed every figure from `corpus/stimuli.jsonl` and
`corpus/selection.json`.

**Concrete failure.** None to the result; but the pre-registration is the document a
reviewer reads, and it currently states two different values for the same quantity.
Fix before the tag, since editing it afterwards is exactly what the freeze forbids.

**Confidence: high.**

---

### N9. `is_eligible` checks only the numeric answer forms, not `protocol.leakage`'s `solution_form` phrases (latent)

**Evidence.** `corpus/build_stimuli.py:243-253` (`answer_forms` returns
`numeric_form ∪ {formatted answer}`); `:256-263` (`_states_answer_in` iterates only those).
`vendor/protocol/leakage.py:44-49` also matches `solution_form` phrases.

**How verified.** For `train-1` (`canonical_answer = 24.0`,
`solution_form = ['add twenty four', 'add twenty-four', 'answer is twenty four',
'answer is twenty-four']`): `"So the answer is twenty-four liters."` →
`_states_answer_in = False` but `turn_leaks = True`. I then checked whether it bites:
**no frozen context and no frozen `R_H` contains a `solution_form` phrase for its named
problem** (0 of 55 on both). `tests/test_stimuli.py:126-129` does pass `solution_form` to
`turn_leaks`, so the R_H guard is complete; only the eligibility filter is narrower.
`PREREGISTRATION.md:141-143` claims only "every numeric spelling", which is accurate.

**Concrete failure.** None on this set. Latent for any future re-freeze.

**Confidence: high.**

---

### N10. Housekeeping that will bite the operator

- **Two untracked `corpus/logs/` directories** (`abl-s0-ped_no_gate-r0`,
  `conf-gpt-s0-ped-r7`) will block `require_git_freeze` until resolved. Verified they are
  **not** referenced by any frozen stimulus: `corpus/stimuli.jsonl` names 38 run dirs (as
  `source_run` or as a donor), all 38 are tracked, all 38 are present. They are donor-pool
  leftovers from the pre-drift-fix selection. `conf-gemini-s0-conv-r3` is tracked but
  unreferenced for the same reason — `cmd_freeze` (`corpus/build_stimuli.py:890-893`) only
  ever adds directories, never prunes.
- **`analysis/out/` is not gitignored**, so running `analyze.py` dirties the tree; any
  later live command then fails `require_git_freeze` (`analysis/out/` is not in
  `RUNTIME_RESULT_PATHS`, `judging/run_study.py:80-91`). Harmless in the documented
  ordering, annoying if the operator re-runs anything.
- **Deleting *both* the ledger and the wire log resets the live allowance.** Verified:
  with a live wire log present the ledger refuses to start fresh
  (`judging/run_study.py:224-231`); with both removed it starts at zero. Self-defeating
  (the orphaned cache then fails `validate_live_cache_provenance`), but worth knowing.
- **Docstring drift:** `corpus/build_stimuli.py:26` cites
  `corpus/authored_responses.yaml`, which does not exist (authoring comes from
  `corpus/reviews/packet_*.jsonl`). `:94` says post-resolution items are "Excluded at
  sampling for both strata"; `is_eligible` is only called from `cmd_select`.
  `protocol/decisions-log.md:218` still reports the superseded "80 weak / 32 strong …
  selected 30/30" without an in-place superseded marker.
- **Preflight exercises only two of the three arms** (`D`, `P_nov` —
  `judging/run_study.py:697`). The `P_adv` block is never sent before the paid run. It is
  byte-checked by `tests/test_instrument.py:44-52`, so this is cosmetic.

**Confidence: high.**

---

## 3. VERIFIED

Everything below I recomputed or executed myself. "The tests pass" is not on this list
except where I say what a test would have to catch.

**Composition of the frozen set — every disclosed figure reproduces exactly.** From
`corpus/stimuli.jsonl`: 55 stimuli; 30 weak / 25 strong; evidence `moderate` 37 /
`strong` 18 / `ambiguous` 0; family ped 31 / conv 24, crossed with stratum
`{(ped,weak):23, (ped,strong):8, (conv,weak):7, (conv,strong):17}`; base gpt 22 /
gemini 19 / sonnet 14; provenance `R_H` 53 corpus / 2 authored, `R_L` 29 corpus / 26
authored; 27 all-corpus pairs (12 weak / 15 strong); per-problem 6–11 across all six
training problems, and ≤7 per (problem, stratum) — consistent with the frozen cap of 7,
so the selection rule's caps were honoured. `?` in 37 `R_H` against 1 `R_L`, and in all
36 pairs where exactly one pole has one it is `R_H`; `\boxed{}` in 0 `R_H` against 18
`R_L`. sha256 = `1d240ebc…8c5376`, matching both `corpus/stimuli.sha256` and
`results/plan.json`.

**Inference units.** 23 distinct `source_run` values; 18 represented in the weak stratum,
10 in the strong, 5 in both (18 + 10 − 5 = 23). Matches §6 exactly. Confirmed
independently by running the analysis end to end on mock scores:
`n = 55 stimuli {'weak': 30, 'strong': 25}; independent source runs {'weak': 18,
'strong': 10}`.

**Labelling reliability — recomputed from `labeling/reps/*.jsonl`, not read from a
document.** Majority vote reproduces `labels.jsonl` for all 126 candidates with zero
mismatches, and `per_rep` matches the rep files exactly. Unanimity 115/126. Pairwise
inter-rep agreement over the 126 pool: 119/126, 119/126, 118/126 = **94.4 / 94.4 /
93.7%**; over the earlier 96-item pool: 91/96, 91/96, 92/96 = **94.8 / 94.8 / 95.8%**.
Pool composition 84 weak / 42 strong (126) and 65 / 31 (96); top-up yield 19 weak / 11
strong. All match the prereg, the decisions log and the abstract. `agreement_ok` is True
for all 126 — confirming A3.3's point that the gate is a pigeonhole tautology.

**v1→v2 confusion.** Recomputed from `labeling/v1-archive/labels.jsonl` against
`labeling/labels.jsonl` over the 96 common ids: `{(strong,strong): 31, (strong,weak): 45,
(weak,weak): 20, (weak,strong): 0}`. Strictly monotone, exactly as claimed; matches
`labeling/v1_v2_confusion.json`.

**Reproducibility from raw source logs — the full chain, byte for byte.** Running
`corpus/build_stimuli.py census` in a scratch copy against
`~/Documents/GitHub/conv-vs-ped-tutor/logs` gives **2,219 judged tutor turns**, tracker
join **990** with cells 844 / 100 / 39 / 7, and per-policy counts summing to 2,219 — all
matching `corpus/census.json`, and the regenerated `corpus/response_pools.jsonl` and
`corpus/census.json` are **byte-identical** to the frozen ones. Replaying `topup -n 30`
from `candidates.pre-topup.jsonl` reproduces `corpus/candidates.jsonl` byte-identically.
`build_stimuli.py verify` reports `verify PASS: 55 contexts and 82 corpus-sourced
responses rebuilt byte-identical from corpus/logs; sha256 matches`. This closes the
question of whether the frozen inputs are re-derivable: they are, from the source
repository's raw logs, with no manual step.

**Vendored provenance.** All 20 files listed in `vendor/PROVENANCE.md` hash to the value
recorded there **and** are byte-identical to
`~/Documents/GitHub/conv-vs-ped-tutor` at commit
`ab5ea2a99d67cc2b23808c52e841301c5e56d887` (`git show <commit>:<path>` per file). Source
worktree clean. No file was written to that repository.

**Frozen-input manifest.** All twelve entries in `results/frozen_inputs.sha256` match the
current files, and the key set matches `frozen_inputs()` exactly. `results/plan.json`'s
recorded hashes agree.

**Cost arithmetic — recomputed independently.** At $5/$25 per Mtok with the measured
1,639.6-token basis plus two-thirds of a 95-token profile block (est_in = 1,703.33) and
52 output tokens: 990 × ($8.517e-3 + $1.30e-3) = **$9.7185 → $9.72** ✓. Worst-case
reservation 8,192 × $5e-6 + 512 × $25e-6 = **$0.05376**/call → 990 × = **$53.22** ✓,
$53.33 including the two preflight calls ✓, 4 attempts → **$212.89** ✓. The reservation
guard has real headroom: the largest of the 330 assembled prompts is 3,650 user bytes +
3,096 system bytes, so `bytes + 512 envelope = 7,258 < 8,192`; **0 of 330** prompts come
within 692 bytes of tripping it.

**The instrument sends what the protocol says it sends — verified on assembled payloads,
not templates.** `PJ.build_system()` is `JP.PED_SYSTEM` verbatim (3,096 chars).
`PJ.build_user()` is `JP.PED_USER.format(dialogue=context + "\n\nTutor: " +
response.strip())`, with the profile block prepended in profile arms only; the three arms
are byte-identical modulo that block. I printed a full `P_adv` payload and read it. No
metadata token leaks (`assert_prompt_pure` runs before every send and in the manifest
path). Profiles are 59 words / 4 sentences each. `LiveCaller` sends exactly
`{model, system, messages, max_tokens}` with `max_retries=0` — asserted constructively at
`tests/test_instrument.py:148-151`, which would fail if the kwarg were dropped.

**The signed-rank implementation is correct, and more correct than SciPy under ties.** On
500 random continuous samples (n = 4–18) `wilcoxon_report` agrees with
`scipy.stats.wilcoxon(method="exact")` to 1e-9 in **500/500** cases. Under ties they
disagree in 238/300 trials — because SciPy's exact branch does not handle ties. I
brute-forced the exact conditional distribution over all 2^n sign flips with average
ranks for a tied sample: brute force **0.53125**, `wilcoxon_report` **0.53125**, SciPy
exact 0.4375, SciPy normal-approx 0.317. The implementation matches
`PREREGISTRATION.md:301-304` exactly. Zero handling verified: `(1/3+1/3+1/3) − 1.0`
residues are dropped by the 1e-9 tolerance.

**The analysis implements §6.** Ran `analysis/analyze.py --allow-mock` on a full mock run:
it produces the six-cell Δ table (the registered four cells plus the D-arm reference),
`primary_PAG_weak` over the 18 weak-stratum source-run means, `secondary_PAG_strong`,
movement from D, the pure profile effect per pole, the all-corpus re-estimate, the
per-field decomposition over all four rubric sub-scores, and the Spearman
influence × evidence correlation over 23 runs. `cluster_means`
(`analysis/analyze.py:239-246`) averages within `source_run` before any test or
bootstrap, as registered.

**Freeze gates that actually hold (each attacked, each refused).**
`assert_stimuli_unchanged` blocked a post-scoring stratum flip
(`STIMULI CHANGED SINCE SCORING: … refusing to analyse`). `sha_artifact` refuses when the
artifact and its sidecar disagree. `contract_sha256` moves when a stimulus, a profile, or
`run_study.py`/`profile_judge.py`/`judge_pedagogy.py` changes. `RepCache` refuses a stamp
mismatch. `--offline-cache-only` aborts on any cache miss. The completeness gate refuses
to promote when any unit lacks 3 valid reps. `run_meta.reportable` follows the *cache*
backend, so a mock cache cannot be relabelled reportable.

**Spend controls — every attack I could construct was refused.** Rejected: `--cap 1e9`,
`--cap 40.01`, `inf`, `nan`, `-5`, `0` on the live backend; raising the cap on resume
(`ledger ceiling is $10, requested $39.9`); a hand-edited ledger whose
`settled_usd_total` disagrees with its rows; a missing ledger beside a wire log
containing live rows. Mock rows never consume the live allowance. `charge()` fires
*before* the request and `settle()` refuses an actual cost above its reservation. The run
lock is `flock`-based and non-blocking. The only reset path is destroying the ledger *and*
the wire log together (N10).

**Live cache/wire provenance.** Every accepted live cache row must match an fsynced wire
row by canonical row hash, key, scores, prompt hash, served model and provider response
id, with duplicate response ids rejected and the parsed scores re-derived from the stored
raw text (`judging/run_study.py:447-510`). `tests/test_offline_replay.py:104-155` exercises
both the fabricated-cache and forged-response-id cases.

**Material quality — read, not assumed.** I read the full text of six stimuli across both
strata and the final student turn of all 55. Every context ends on a live next reasoning
step; none is a post-resolution wrap-up; none states its problem's answer (`turn_leaks`
over all 55 contexts with both numeric and solution forms: 0 hits, and 0 for `R_H`). The
`R_H`/`R_L` pairs I read are genuine scaffolding contrasts, not phrasing variants. I
specifically probed the C018 exclusion criterion for consistency by pulling the four weak
stimuli whose last student turn contains a conspicuous unrepaired error (S23, S28, S37,
S48): in all four, **both** poles correct the same error and differ only in who performs
the next step — so correctness is held constant and the C018 exclusion looks principled
rather than selective.

**Manipulation check.** `corpus/manip/report.json`: 55 pairs, 55 correct, 0 reversed, 0
tied, `key_agreement_rate` 1.0, `n_raters_per_pair` 1. The A/B order is 34 B / 21 A, so a
constant-"B" rater would score 62%, not 100% — the result is not explained by position
bias. The item set matches the frozen candidate ids exactly (M11/C018 pruned).

**Test suite.** `python3 -m pytest tests/ -q` → **70 passed**, 0 skipped, 0 xfailed
(70 collected). The skip guards in `tests/test_stimuli.py:30-31`,
`tests/test_instrument.py:19-20` and `tests/test_offline_replay.py:26-28` are inert
because the frozen artifact exists. The mock end-to-end really does run all 990 calls: I
reproduced it outside pytest (330 units, 990 rows promoted, 1,027 physical attempts
including 37 seeded retries). **See N2b for what that green does and does not
establish** — `tests/test_reconstruction.py` and `tests/test_parser.py` are the strongest
things here, and the instrument/estimator assertions are the weakest.

**No API key exists in this environment** (`ANTHROPIC_API_KEY` unset, no `.env`), and
`LiveCaller.__init__` (`judging/run_study.py:348-349`) raises before constructing a
client — so nothing I ran could have spent money even by accident.

---

## 4. NOT COVERED

Stated plainly; a missing finding below is not a clean bill of health.

- **The blind pairing reviews.** I did not read `corpus/reviews/packet_*.jsonl` against
  `corpus/packets/packet_*.json` to check that each reviewer's decision is consistent with
  the brief they were given, that reviewers saw no labels/policies, or that the six
  reviewers were genuinely independent contexts. I verified the *outputs* (pairs, poles,
  provenance, no duplicate response text) but not the *process*.
- **The blind labelling process.** I verified aggregation, reliability and reproduction
  arithmetically, and read a sample of contexts against the v2 rubric and found the labels
  defensible — but I did not independently re-label the 126 candidates, and I cannot audit
  the claim that the three reps were genuinely independent fresh contexts. That claim rests
  on the build harness, which is not in this repository.
- **`vendor/analysis/metrics.py` (650 lines) and `vendor/agents/model_client.py`.** I
  confirmed both are byte-identical to the named source commit and that the live path does
  **not** go through `model_client.py` (`LiveCaller` calls the SDK directly), but I did not
  audit `metrics.py`'s turn extraction, `tutor_in_window`, or the visible-turn logic that
  the corpus census depends on. Everything upstream of `response_pools.jsonl` is inherited
  trust.
- **Whether `claude-opus-4-8` exists, is still served, and behaves as the source study
  measured.** Unverifiable without a provider call. Preflight is the right place to find
  out and costs ~$0.02.
- **An exhaustive mutation sweep of the test suite.** N2b reports ten mutations I
  reproduced myself, chosen to target the study's load-bearing properties. That is a
  targeted probe, not full coverage: I did not mechanically mutate every constant and
  branch. Areas I know remain unswept — the `validate_live_cache_provenance` branch set
  beyond the two with negative tests, `degraded_reason`'s individual checks, the
  served-model-drift abort, `promote()`'s missing-file guard, and the real
  `_git_freeze_snapshot` (which `tests/test_freeze.py:101-117` monkeypatches away, so only
  the four lines of `require_git_freeze` that consume its dict are exercised).
  `tests/test_stimuli.py:166` (`max(per_problem.values()) <= 14` against an actual max of
  11) is the loosest assertion I found; I did not hunt for others exhaustively.
- **Statistical power.** I noted that the primary test runs on 18 cluster means and that
  §6.5 deliberately declines a pre-run precision claim. I did not simulate the design to
  estimate what effect size the study can actually detect, which is the analysis a reviewer
  would want. Related and unassessed: whether floor effects on `R_L` (18 of 55 contain
  `\boxed{}` and fully solve the problem, so they should score near the bottom on
  `productive_struggle` in every arm) compress the achievable PAG.
- **`analysis/figures/fig1.py`.** Read for correctness against `summary.json`'s schema;
  never executed (it needs a `summary.json` from a real run).
- **The two predecessor audit documents.** I used them only for orientation. I did not
  systematically re-verify their remediation claims one by one; where their claims
  intersected my own checks, they held, except as recorded in B1 and N1–N2.
- **Anything about the companion `conv-vs-ped-tutor` study** beyond confirming that the 20
  vendored files match its commit `ab5ea2a9` and that its logs reproduce the census.

---

## Appendix: remediation applied

Applied by the same agent that wrote the findings above, at the owner's request, on
2026-08-08. **This is a self-report and needs independent re-verification.** Zero
provider calls; `corpus/stimuli.jsonl` and `labeling/labels.jsonl` are byte-identical to
the audited tree (`1d240ebc…8c5376`, `fda2bc3d…2707d4`), the design is unchanged (330
units / 990 calls / $9.72), `build_stimuli.py verify` still passes, and the suite is
70 → **79 passed**.

### Fixed

| Finding | Change |
|---|---|
| B2, B3, N3, N4, N5, N8 | **Amendment A5** in `PREREGISTRATION.md` §7b, plus a conditional null reading in §6.2, a non-minimal-contrast disclosure in §2, an in-place supersession marker on A3.6's stale 56-set figures, and a corrected header comment in `profiles/profiles.yaml`. **No profile text, stimulus, label or registered estimand was edited.** |
| N1 | `--offline-cache-only` now compares its rebuild against the promoted finals and aborts without overwriting on any difference. Re-ran the demonstrated attack: it now reports `OFFLINE RECONSTRUCTION MISMATCH` and the tampered file is left in place as evidence. |
| N2 | `analyze.py` verifies its own sha256 and `PREREGISTRATION.md`'s against `run_meta.json["frozen_inputs"]` before computing. Re-ran the demonstrated attack: repointing the primary endpoint at the other stratum now aborts. |
| N7 | Cost is computed after `degraded_reason`; a reply with no usage accounting is settled at its full reservation, wire-logged, refused and retried instead of raising `TypeError`. |
| N9 | `_states_answer_in` also matches `protocol.leakage`'s `solution_form` phrases. Verified inert: 0 of 126 candidates change eligibility, and the byte-identical reconstruction still passes. |
| N2b | Nine new tests plus one de-vacuumed. All eleven mutations in N2b's table are now caught, each by its intended test, and reverting each of the three code fixes above kills its own regression test. `tests/test_instrument.py:46` now uses the same skip guard as its neighbours instead of silently shrinking to one synthetic stimulus. |
| N10 | `analysis/out/` gitignored; the `authored_responses.yaml` and "excluded at sampling" docstring drifts corrected. |

### Deliberately not applied

- **B1 (git tag + the untracked paths).** Operator action; not mine to commit or tag.
- **B3's design option** — deleting the help-seeking sentence from both profiles. That
  changes the manipulation. A5 discloses it instead; the choice between disclosure and
  redesign belongs to the author.
- **N6 (windowed circuit breaker).** Changing an abort threshold could abort a paid run
  mid-flight, which is a worse failure than the one it fixes, and the $40 cap is the
  real backstop. Still open.
- **N1's deeper half — having `analyze.py` re-derive the promoted scores from the
  released cache.** Only the reconstruction path was hardened. **Residual, verified
  still open:** `analyze.py` run directly on a tree whose `per_unit.jsonl` and
  `run_state.json` manifest have both been edited still reports the fabricated result
  (`PRIMARY PAG_weak … p=1.5e-05`). Closing it properly requires `tests/test_analyze.py`'s
  fixture to emit realistic 3-integer reps and a real cache, which also fixes the
  fixture-divergence problem N2b names — a test-fixture redesign, not a fix. A
  self-consistency check on `per_unit` alone was considered and rejected as the kind of
  gate that looks stronger than it is.
- **Unit tests pinning §6.5's BCa and §6.4's Spearman** (N2b mutations M7/M8). A
  behavioural test for either is flaky, and the realistic attack — a post-run edit — is
  now caught by the N2 gate. The pre-run case is caught by the contract hash. Recorded
  rather than papered over.
