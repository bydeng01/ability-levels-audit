# Independent pre-flight review — label-vs-evidence paid run

**Status: INCOMPLETE — stopped on request partway through.** This is a *record of where
the review stopped*, not a finished audit. Sections 1–4 report only what I established
and personally re-verified; §5 lists, honestly and in detail, what was never examined.
Do not read a missing finding as a clean bill of health.

**Reviewer:** second independent pre-flight review, 2026-08-08.
**Provider calls made: ZERO. Money spent: $0.00.**
Everything was offline: the test suite, the mock backend, ad-hoc Python over the frozen
artifacts, and scratch copies of the repo outside it. No file in this repository was
created or modified except this one — confirmed by `git status --porcelain` (41 entries,
unchanged from session start) and by `corpus/stimuli.jsonl` / `labeling/labels.jsonl`
still hashing to `2613e05f…16adf8` / `fda2bc3d…2707d4` at the end.

### Filename note

The brief asked for `protocol/AUDIT-<today>.md`. That path — `protocol/AUDIT-2026-08-08.md`
— **already exists**: it is the *first* audit, and it is referenced by `README.md:94` and
`protocol/PREREGISTRATION.md:9`. Writing there would have destroyed it and broken both
references, so this review is at a non-colliding path. Rename if you prefer, but do not
overwrite the first audit.

### Relationship to the first audit

`protocol/AUDIT-2026-08-08.md` returned **NO-GO** on four blocking findings; its §6
"Post-fix addendum" then records that **the same agent** applied the fixes and revised the
verdict to GO, and says so plainly. That addendum is therefore a *self-report*. I treated
every claim in it as unverified. Where I checked its claims they very largely hold (§4);
the exceptions are in §3.

---

## 1. PROVISIONAL VERDICT

**GO-WITH-FIXES** — provisional, and conditional on the audit being finished.

The engineering is genuinely good and most of the repository's own claims are exactly
true: I recomputed the entire frozen-set composition, the whole labelling reliability
chain, the cost arithmetic, the contract hash, the manipulation check and the selection
rule, and they reproduce to the digit (§4). The four fixes the first audit forced are real
— I re-demonstrated the B2 tamper case end-to-end and it is now caught on every path.

But **one blocking item stands (§2.1): the frozen materials do not exist in version
control.** The `prereg-frozen` tag and `HEAD` both still hold the superseded 60-stimulus
set; the entire 56-stimulus re-freeze — stimuli, labels wiring, corrected code, corrected
protocol, regenerated manifest — is uncommitted working-tree state, and seven required
paths are untracked outright. A study whose central claim is a pre-registration freeze
currently has no immutable anchor for the thing it froze. The fix costs $0 and one commit,
and it must happen before the first paid call, because afterwards it is unprovable.

Everything else I found is non-blocking (§3): a set of statements in the pre-registration,
the decisions-log and the abstract that are wrong or overstated and must be corrected
*before* the run, since a pre-registration cannot honestly be amended once data exist. Two
of them are substantive enough to change how the headline may be written (§3.1, §3.2).

The provisional part matters: **seven of my nine investigation lines never reported.**

---

## 2. BLOCKING FINDINGS

### 2.1 — The frozen 56-stimulus materials are not committed; the freeze has no immutable anchor, and a normal commit would ship a broken release

**What is wrong.** Three separate things, one cause.

*(a) Nothing is committed.* `git tag -l` → `prereg-frozen` only, pointing at `1e4c868`.
`git show prereg-frozen:corpus/stimuli.jsonl | wc -l` → **60**. `git show
HEAD:corpus/stimuli.jsonl | wc -l` → **60**. The working tree has **56**.
`git diff --name-status prereg-frozen HEAD` shows only `.gitignore`, `paper/abstract.md`,
`protocol/PREREGISTRATION.md`, `protocol/decisions-log.md` — i.e. *no commit in this
repository contains the materials that are about to be scored.* `git diff --stat` against
HEAD: 32 tracked files changed, +2100/−925, including `corpus/stimuli.jsonl`,
`corpus/selection.json`, `judging/run_study.py`, `judging/profile_judge.py`,
`analysis/analyze.py`, `corpus/build_stimuli.py`, `results/frozen_inputs.sha256`,
`results/input_manifest.jsonl`, `results/plan.json`.

*(b) Seven required paths are untracked.* `corpus/logs/abl-s0-ped_no_gate-r0/`,
`corpus/logs/abl-s0-ped_no_tracker-r8/`, `corpus/logs/conf-gpt-s0-ped-r6/`,
`corpus/logs/conf-gpt-s0-ped-r7/`, `corpus/packets/packet_9.json`,
`corpus/reviews/packet_9.jsonl`, `corpus/selection.pre-drift-fix.json` — plus
`tests/test_freeze.py`, the file containing the four tests that prove the B2 fix.

*(c) Therefore the freeze rests on nothing but two plain files.* With no committed
baseline, the only records of "what was frozen" are `corpus/stimuli.sha256` and
`results/frozen_inputs.sha256`, both ordinary files in the same working tree, and
`build_stimuli._write_sha` (`corpus/build_stimuli.py:914-917`) regenerates the first in one
line. Git is the only mechanism that would catch a coordinated edit, and git currently
records a *different* set of materials.

**How I verified it.**

- The git facts above, directly.
- Which stimuli need the untracked logs: `S42`/C018 (`abl-s0-ped_no_gate-r0`,
  `conf-gpt-s0-ped-r7`), `S12`/C002 (`abl-s0-ped_no_tracker-r8`), `S54`/C088
  (`conf-gpt-s0-ped-r6`). 40 run dirs are referenced; 37 are tracked.
- I materialised exactly what a tracked-files-only commit would produce
  (`git ls-files | rsync --files-from=- ./ $S/tracked/` → 181 files, 37 log dirs) and ran
  the repo's own gates in it:

```
$ python3 corpus/build_stimuli.py verify
FileNotFoundError: .../corpus/logs/abl-s0-ped_no_tracker-r8/calls.jsonl

$ python3 -m pytest tests/ -q
FAILED tests/test_reconstruction.py::test_stimuli_rebuild_byte_identical_from_corpus_logs
1 failed, 45 passed
```

  Not 50 passed — 45, because `tests/test_freeze.py`'s four tests are absent entirely.
- Tamper probes in scratch copies, after a full 1,008-call mock run had promoted results
  (all mock; `cost_usd` 0.0 throughout):

| edit | detected? | by what |
|---|---|---|
| `stimuli.jsonl` only, sidecar untouched | **yes** | `FROZEN INPUT MISMATCH`; `CACHE STAMP MISMATCH`; `STIMULI CHANGED SINCE SCORING` |
| `stimuli.jsonl` **+** regenerated sidecar | **yes** | `CACHE STAMP MISMATCH`; `STIMULI CHANGED SINCE SCORING` |
| …**+** patch `run_meta.json`'s one hash field | **no** | analyze.py runs clean; re-cut strata to `{'weak': 29, 'strong': 27}` while `summary.json` still reports the original `contract_sha256` `d61b9d53…` |

  The code-level guards are good and the third row is deliberate falsification, not an
  accident — but git is what makes deliberate falsification detectable, and git is where
  the materials are not.

**The concrete failure this causes.** (i) The pre-registration's central assertion —
"FROZEN before the first paid judge call… enacted by the sha256 hashes… and a git tag"
(`protocol/PREREGISTRATION.md:3-5`) — is presently false: the tag names other materials.
(ii) After the run, no third party can establish that the scored stimuli are the frozen
stimuli; the first audit's own V1 check (`git diff prereg-frozen HEAD`) now returns a
2,100-line diff. (iii) If the operator commits with `git commit -am` or `git add -u`
(both stage only tracked files), the release ships a repo whose advertised reproduction
path crashes and whose test count silently drops from 50 to 46, with 1 failing.

**Remedy.** Before `--preflight`: `git add -A` (verify the seven untracked paths are
staged), commit, and tag a **new** freeze (`prereg-frozen-v2`), keeping the old tag. Then
re-run `pytest tests/ -q` and `build_stimuli.py verify` from a clean clone of that tag, not
from the working tree. The first audit's §6 lists "commit, re-tag" as an operator step;
that step is load-bearing, not housekeeping.

**Confidence: high** (every element demonstrated).

---

## 3. NON-BLOCKING FINDINGS

All of these should be fixed or disclosed **before** the run — not because they threaten
the run's value, but because after judge scores exist, amending the pre-registration is no
longer legitimate.

### 3.1 — The frozen system prompt instructs the judge to ignore the manipulation, and this is nowhere disclosed

`vendor/analysis/judge_pedagogy.py`'s `PED_SYSTEM` ends its constraint list with:
**"Base your rating only on the dialogue shown."** The profile block is prepended to the
*user* message, outside the `DIALOGUE: """…"""` delimiters — I printed a real assembled
`P_adv` payload to confirm the layout. So the manipulated factor is a block of text that
the frozen instrument explicitly tells the model to disregard.

`grep -rn "only on the dialogue\|dialogue shown\|Base your rating" README.md paper/
protocol/ judging/ analysis/ tests/ labeling/` returns exactly one hit —
`protocol/PREREGISTRATION.md:157`, where the *same phrase* is cited as a reason to cut the
profile-only arm. The author noticed the phrase for the arm they dropped and not for the
arms they kept.

**Why it matters.** §6.2 pre-registers "A null (CI tight around 0) is a publishable
finding: the judge grounds its preference in behavioural evidence." With this instruction
in the system prompt, a null is at least as consistent with "the judge did what the prompt
told it to do and ignored the metadata." That is a different claim, and a reviewer will
make it. This cannot be fixed without changing the instrument and forfeiting
commensurability with the companion study — so it must be *disclosed and framed* in §6.2
and the abstract's limitations, before the data exist. **Confidence: high.**

### 3.2 — The profiles manipulate stated *support need*, not only stated ability

`profiles/profiles.yaml`: the novice text says the learner *"usually need[s] step-by-step
help to make progress"*; the advanced text says they *"usually work through problems
independently without help."* The rated construct is scaffolding. So a judge that prefers
high-scaffolding replies less under the advanced profile may be responding *correctly* to
a stated instructional need rather than anchoring on an ability label — and PAG cannot
distinguish the two.

`paper/abstract.md:119-123` discloses this honestly. `protocol/PREREGISTRATION.md:67-71`
does not, and asserts the profiles "contain no dialogue hints and **no weighing
instructions**". "Usually needs step-by-step help" is close to a weighing instruction about
the very dimension being scored. The pre-registration should carry the abstract's caveat.
**Confidence: high.**

### 3.3 — The short strong stratum received no label-quality filtering, so measurement error in the stratification variable is strongly differential

This is a side-effect of Amendment A2 that nobody has noticed. The selection rule orders by
`(-unanimous, -Σconfidence, candidate_id)` and takes greedily
(`corpus/build_stimuli.py:516-520`). Recomputed by me over the 126-item pool:

| stratum | eligible | selected | mean labeller confidence-sum (0–6) | unanimous |
|---|---|---|---|---|
| weak | 75 | 30 | **5.97** (29 of 30 at the maximum) | 30/30 |
| weak — *rejected* | | 45 | 3.73 | |
| strong | 26 | **all 26** | **3.58** | 25/26 |

The weak stratum creamed the top of a 75-item pool. The strong stratum had exactly 26
eligible for 26 slots, so **no confidence filtering was applied to it at all** — and its
label quality (3.58) is statistically indistinguishable from the pile the rule *discarded*
from the weak stratum (3.73). All 5 frozen items carrying a `low` confidence vote are
strong; **zero** weak items do. The single non-unanimous item in the frozen 56 (`S06`/C021)
is strong.

**Consequence.** The stratification variable is measured with materially more error on one
side. That attenuates every weak-vs-strong comparison: the four-cell table's strong column,
`PAG_strong`, and the weak→strong gradient that *is* the paper's only figure. The primary
endpoint `PAG_weak` is unaffected — it lives entirely in the high-quality stratum, which is
the main reason this is not blocking. Disclose as a limitation; do not re-tune the rule.
**Confidence: high** on the numbers and the mechanism; **medium** on the magnitude of the
attenuation, which I did not model.

### 3.4 — "The corrected rule rejects exactly those eight and nothing else" is false: 13 candidates lost eligibility, and 2 gained it

Cited at `protocol/PREREGISTRATION.md:348`, `protocol/decisions-log.md:313-314`, and
`protocol/AUDIT-2026-08-08.md:773`. I reconstructed the pre-fix `is_eligible` exactly as
B1 describes it (single-token `answer_forms`, lookbehind without `-`, the `and "?" not in
last` hatch) and diffed it against the shipped rule over all 126 candidates:

```
eligible OLD: 112    NEW: 101
lost (13): C001 C019 C030 C035 C038 C052 C062 C073 C078 C103 C106 C110 C124   (7 weak, 6 strong)
gained (2): C061 C068                                                          (the lookbehind fix — claim holds)
of the 13 lost, 8 were selected: C001 C030 C052 C073 C078 C103 C106 C110
the other 5 were eligible-but-unselected: C019 C035 C038 C062 C124
```

80/32 − 13 + 2 = 75/26 ✓. So the sentence is also internally inconsistent with its own next
clause (114 − 8 ≠ 101). The two sub-claims around it *do* hold: removing the `"?"` hatch
changes no candidate's eligibility (`lost^gained = ∅` for that variant alone), and the
lookbehind fix recovers exactly C061 and C068. Only "eight and nothing else" is wrong —
and it is the sentence that certifies the fix was surgical. **Confidence: high.**

### 3.5 — PREREGISTRATION §6.5 names a Wilcoxon branch the data cannot reach

§6.5 states `method="auto"` "selects the **exact** distribution at these sample sizes
(n ≤ 50 without ties)". The frozen design guarantees ties: a per-unit score is a mean of
three integers, so every `PAG_s` is a multiple of 1/3 and `|d|` collides constantly. On
PAG-shaped data:

```
n=30  nonzero=30  distinct|d|=23 (7 ties)   auto=0.69586216  exact=0.71513297  asymptotic=0.69586216
n=26  nonzero=26  distinct|d|=18 (8 ties)   auto=0.27445426  exact=0.29137629  asymptotic=0.27445426
                                            -> auto == ASYMPTOTIC, not exact
```

(My first check missed this because I used tie-free continuous draws — with those, auto
does equal exact at n = 30, 26, 28, 16, 12. The frozen design does not produce those.) The
parenthetical "without ties" makes the sentence technically self-qualifying, but the
pre-registration names a null distribution that will not run. Correct §6.5 to describe the
asymptotic branch. `analyze.py` needs no change. **Confidence: high.**

### 3.6 — The candidate pool is not regenerable, so one pre-registration sentence is false as written

`cmd_topup` filters by `is_eligible` (`corpus/build_stimuli.py:454`), and `is_eligible`
changed under B1. Four of the 30 top-up candidates — **C103, C106, C110, C124** — are
ineligible under the shipped rule, so re-running `topup` today draws a different set and
`candidates.jsonl` / `candidates.sha256` cannot be reproduced.
`protocol/PREREGISTRATION.md:129-130` says the top-up was "drawn deterministically from the
eligible unsampled turns"; under the shipped filter, 4 of 30 were not.
`protocol/decisions-log.md:201`'s "987 unsampled judged turns" is likewise unreachable now.

**This does not touch the frozen 56.** I confirmed 25 of the 126 candidates are ineligible
under the shipped rule and **none of them is in the frozen 56** — every one of the 56
passes all three disqualifiers. So the run is safe; the reproducibility claim and the §3
wording are not. (Reported to me as *blocking* by one investigation line; I downgrade it —
the frozen set is clean and I verified that directly.) **Confidence: high.**

### 3.7 — "A relabelled mock cache cannot be promoted" is not true; the fix relocated the self-declaration rather than grounding it

`judging/run_study.py:670-671` now derives `reportable` from the cache stamp. But the stamp
is itself an editable JSON string in the same file. In a scratch copy I renamed
`mock_cache.json` → `profile_pedagogy_cache.json`, set `stamp.backend` to `"live"`, set the
preflight's `backend` to `"live"`, and ran:

```
$ python3 judging/run_study.py --judge-backend live --offline-cache-only
PROMOTED 336 units / 1008 per-rep rows to results/ (REPORTABLE)
run_meta: {'backend': 'live', 'cache_backend': 'live', 'reportable': True}
$ python3 analysis/analyze.py          # no --allow-mock needed
```

In fairness the fix *does* close the accident case an honest mock cache creates, which was
the point. But `protocol/decisions-log.md:342` and `AUDIT-2026-08-08.md:844` overstate it.
Grounding `reportable` in evidence (nonzero `cost_usd` in the wire log, real usage tokens,
a matching preflight timestamp) would cost little. **Confidence: high.**

### 3.8 — The spend ledger fails *open* on any row whose `backend` is not exactly `"live"`

`SpendLedger._load` (`judging/run_study.py:158-166`) sums only rows where
`inv.get("backend") == self.backend`, while `_corrupt`'s consistency check validates the
*grand* total. So a row can carry real dollars, satisfy every integrity check, and
contribute nothing to the cap:

```
honest live row $39            -> prior spend seen by cap = $39.00
backend=null row $39           -> $0.00
backend key ABSENT, $39        -> $0.00
backend='Live' (case typo)     -> $0.00
backend='live ' (trailing sp)  -> $0.00      (file total $39.00 in every case)
```

This matters because it is exactly the recovery path the code's own error message
prescribes: *"reconstruct the true figure from results/wire/calls.jsonl and rewrite the
ledger deliberately."* A hand-written row missing an exact `"backend": "live"` silently
resets the allowance to zero. One-line fix: reject unknown/missing backends. **Confidence:
high.** (Practical exposure is small — see §4 on the real cost — but this is a fail-closed
component with a fail-open seam.)

### 3.9 — `analyze.py` is "recorded, not binding", but the record goes stale and `summary.json` does not self-identify

`frozen_inputs()` writes `analyze_py_sha256` into `run_meta.json` at *promotion* time —
before any analysis runs. `analyze.py` never checks its own hash, and `summary.json`
records only `backend`, `reportable`, `contract_sha256`, `n_stimuli`, `n_per_stratum`. I
edited `analysis/analyze.py` post-run in a scratch copy; it ran clean, and `run_meta.json`
still attested the pre-edit hash `906ad92f…`. So `protocol/PREREGISTRATION.md:228-231`'s
claim that `run_meta.json` "attests which analysis code… produced the numbers" is not
right: it attests which analysis code existed when scoring was promoted. Have `analyze.py`
stamp its own live hash (and the scipy/numpy versions) into `summary.json`. **Confidence:
high.**

### 3.10 — Smaller items, verified

- **"7 tutor policies × 3 tutor bases"** (`paper/abstract.md:36`,
  `protocol/PREREGISTRATION.md:36`) implies 21 cells. Per `protocol/decisions-log.md:24-28`
  only `conv` and `ped` span 3 bases; the 5 ablations are sonnet-only. 11 cells, not 21.
- **Stale 60-design text**: `judging/profile_judge.py:18` ("60 stimuli … 1,080 calls"),
  `judging/run_study.py:12` ("the full 1,080-call pass"), `tests/test_offline_replay.py:3`
  ("1,080-call scoring"). Cosmetic, but they are the first thing a reader of the runner
  sees.
- **Loose test bounds the addendum claims were tightened.** `AUDIT-2026-08-08.md:848` says
  "N13 (test bounds tightened)". `tests/test_stimuli.py:155-156` still asserts
  `max per problem <= 14` (actual 11) and `>= 2` bases (actual 3). The authoring-split
  bound genuinely was tightened; these two were not.
- **`test_every_stimulus_carries_its_blind_labels` still asserts `lab["agreement_ok"]`**
  (`tests/test_stimuli.py:147`) — the quantity B4 established is a pigeonhole tautology.
  Harmless (the other two assertions are real), but it reads as a check.
- **The manipulation check records no rationales.** Rating rows carry only
  `item_id` / `leaves_more_to_student` / `confidence`. `protocol/decisions-log.md:400-403`
  quotes what "the rater notes" about C002; no such note exists in any released artifact.
- **Surface cues remain perfectly diagnostic** — on the frozen 56: "exactly one pole has
  `?` → pick it" fires 36/56 and is right **36/36**; `\boxed` fires 18/18 right. §4b and
  the abstract now disclose this accurately (I reproduced 37/1 and 0/18 exactly), so it is
  disclosure-complete, not a defect — recorded here only because it bounds what the
  56/56 result can support.
- **C018/S42's label is in tension with the rubric.** Its last student turn writes
  `9 = 3.6 + 0.2x - 0.2x` → *"Which simplifies to 9 = 3.6"*, then silently reinstates the
  term. `labeling/RUBRIC.md`'s boundary rule: "A currently incorrect step (sign error,
  **dropped term**, wrong expansion) that the student has not repaired is weak." It is
  labelled `strong`, unanimously but at the pool's near-lowest confidence
  (`medium/low/medium`), and it is one of the four post-audit backfills, in the short
  strong stratum. The first audit's B4 remedy — "independently re-check the frozen set's
  labels against the rubric; this is legitimate now and impossible later" — was **not**
  carried out; the addendum instead reasons that the mislabelled items left with B1.
  A charitable reading is possible (the student is self-directed and reaches the right
  expression), which is why I rate this **medium** confidence and non-blocking — but the
  re-check itself is free now and worth doing.

---

## 4. VERIFIED — claims I checked and found to hold

**V1. All nine frozen hashes match their artifacts.** `shasum -a 256` over
`corpus/stimuli.jsonl`, `labeling/labels.jsonl`, `profiles/profiles.yaml`,
`vendor/configs/models.yaml`, `vendor/analysis/judge_pedagogy.py`,
`judging/profile_judge.py`, `vendor/supplement/judge_pedagogy_rubric.md`,
`analysis/analyze.py`, `protocol/PREREGISTRATION.md` — all nine identical to
`results/frozen_inputs.sha256` and to `plan.json`'s `frozen_inputs`. Both sidecars match
too.

**V2. The B2 fix is real and complete on every path.** With 1,008 mock ratings promoted, an
artifact-only edit is refused by `FROZEN INPUT MISMATCH` (manifest), `CACHE STAMP MISMATCH`
(scoring and offline replay) and `STIMULI CHANGED SINCE SCORING` (analysis). A coordinated
artifact+sidecar edit is still refused by the latter two, because `contract_sha256` now
hashes the file (`judging/profile_judge.py:107`). `tests/test_freeze.py`'s four tests
genuinely mutate and assert refusal — they are not vacuous.

**V3. Composition reproduces to the digit.** Recomputed from `corpus/stimuli.jsonl`:
56 stimuli, 30 weak / 26 strong; evidence moderate 38 / strong 18 / ambiguous 0; families
32 ped / 24 conv; bases gpt 23 / gemini 19 / sonnet 14; problems 7–11; R_H 54 corpus /
2 authored, R_L 30 / 26; 28 all-corpus (12 weak, 16 strong); real turn high 44 / low 12;
family × stratum ped 23 weak / 9 strong, conv 7 weak / 17 strong; `?` in 37/56 R_H vs 1/56
R_L with all 36 exactly-one-pole pairs favouring R_H; `\boxed` 0 vs 18; **zero** duplicate
response texts. Every one matches `decisions-log.md:406-413`, PREREG §2/§4b/§7b and the
abstract.

**V4. The B1 fix holds on the frozen set.** Using the shipped helpers and, independently,
the vendored `protocol.leakage` against `vendor/domain/algebra/problems.yaml`:
`problem_already_resolved` fires on **0/56**; `states_answer` on the latest student turn
**0/56**; `CLOSING_RE` **0/56**; `turn_leaks(r_high, …)` **0/56**; every context ends with a
student turn. (I also checked whether any R_H leaks a *different* problem's answer — 28 hit,
but that is an artifact of these problems sharing numerals like 12/20/30/40, not a real
leak.)

**V5. Reconstruction is genuine.** `python3 corpus/build_stimuli.py verify` →
`56 contexts and 84 corpus-sourced responses rebuilt byte-identical from corpus/logs;
sha256 matches` (54 corpus R_H + 30 corpus R_L = 84 ✓). `cmd_verify` raises rather than
skipping when a judged turn is absent, so it cannot pass by omission — which is precisely
why it crashes on the tracked-only tree (§2.1).

**V6. The instrument is what the protocol says.** I assembled all **336** real payloads:
0 mismatches against `results/input_manifest.jsonl` on both `user_sha256` and `user_chars`;
336 distinct hashes; **0** arm byte-identity violations (every `P_nov`/`P_adv` prompt equals
`PROFILE_BLOCK_TEMPLATE.format(...) + ` its `D` prompt exactly); `assert_prompt_pure` passes
on all 336; `PJ.contract_sha256(...)` = `d61b9d53…47aea`, identical to `plan.json`;
`PJ.schedule()` returns 1,008 calls and is deterministic across runs.

**V7. The cost arithmetic is sound and conservative.** `plan.json`'s `est_cost_usd 9.9` =
1,008 × (1,703.33 × $5/Mtok + 52 × $25/Mtok) — reproduced exactly; `worst_case_cost_usd
33.06` = 1,008 × 0.0328 ✓. My independent estimate from real payload sizes (system 3,096
chars + user mean 1,902; 4,998 total) gives **$7.6–8.5** at 3.5–4.0 chars/token, i.e. the
plan over-estimates. `WORST_CASE_IN_TOKENS = 4000` is a genuine bound: the largest
assembled prompt is 6,746 chars ≈ 1,690–1,930 tokens.

**V8. Every labelling number reproduces.** From `labeling/labels.jsonl` and
`labeling/reps/rep{1,2,3}.jsonl`: 126 items, **84 weak / 42 strong**; **115/126** unanimous;
pairwise inter-rep **94.4 / 94.4 / 93.7 %**; majority vote reproduces `labels.jsonl` with
**0** mismatches; the 96-item sub-pool gives 65 weak / 31 strong, 89/96 unanimous and
**94.8 / 94.8 / 95.8 %** — so both the corrected figure and the superseded one are right,
each for its own pool, and A3's re-scoping is correct. Top-up yield 19 weak / 11 strong ✓.
All 8 `ambiguous` items are weak ✓.

**V9. The selection rule reproduces exactly.** I re-implemented it independently (no
writes) and it returns `corpus/selection.json`'s picks **exactly** for both strata; the
selected set equals the frozen 56's `candidate_id` set; eligibility is 75 weak / 26 strong
as recorded. `selection.pre-drift-fix.json` → `selection.json` removes exactly 8 (C001,
C030, C052, C073, C078, C103, C106, C110) and adds exactly 4 (C018, C021, C043, C088), as
documented. The sort key is totally ordered (`candidate_id` is unique), so no iteration
order can affect it. The strong stratum's cap relaxes 7→12, which the documents do not
mention, but it is **inert**: max per-problem strong count is 6.

**V10. The manipulation check reproduces exactly.** 56 key items, 56 ratings across
`resp1`/`resp2`, no duplicates, no extras, no missing — **56 correct, 0 reversed, 0 tied**,
matching `report.json`. Confidence high 50 / medium 5 / low 1, the low one being M01 = C002
✓. The strengthened brief genuinely names question marks, `\boxed{}`/LaTeX and length as
features that must not decide, and offers "tie"; batch items carry only
`context`/`A`/`B`/`item_id` — no candidate id, no labels, no key.

**V11. §6.5's precision claim is arithmetically exact.** Deriving it myself: four per-unit
means each of 3 reps, `Var(PAG_s) = 4σ²/3`, `SD = 1.1547σ`, `SE(mean, n=30) = 0.2108σ` —
the pre-registered **0.21σ**; half-widths 0.207 (σ=0.5) and 0.331 (σ=0.8), the
pre-registered **0.2–0.35**. One caveat: this assumes the true `PAG_s` is constant across
stimuli, so it is a *floor* on the realised half-width, not an expectation. §6.5 commits to
reporting the realised figure, which covers it.

**V12. The analysis implements §6, and the offline pipeline runs end to end.**
`pytest tests/ -q` → **50 passed**, no skips. A full mock sequence (preflight → 1,008 calls
→ completeness gate → transactional promotion) then `analyze.py --allow-mock` produced a
`summary.json` containing every pre-registered §6.1–§6.4 object, including the per-field
decomposition (N4, previously unimplemented). `analysis/figures/fig1.py` renders
`fig1.pdf`/`fig1.png` matching §7's description (weak→strong x-axis, novice/advanced lines
with CIs, D-arm reference, PAG annotation) — the "stated advanced" label clips the right
edge, cosmetically.

**V13. The Anthropic path really does ignore the seed, and the breaker is tight.**
`vendor/agents/model_client.py:111` — `_complete_anthropic(self, role, spec, system,
messages)` takes no `seed`; temperature is sent only `if temp is not None` and
`models.yaml` sets it null. So the 3 reps are genuine stochastic samples, as §2 claims.
The circuit breaker trips after **12** responses in a 100 %-failure run — ≤ $0.39 at
worst-case pricing.

**V14. `$SRC` exists and is intact.** `/Users/boyuandeng/Documents/GitHub/conv-vs-ped-tutor`
is present with 221 log dirs. I did not write to it.

---

## 5. NOT COVERED — where this review stops

This is the important section. The review was stopped partway; **seven of nine parallel
investigation lines never reported**, and I had not begun to reconcile the two that did.

**Lines that never reported at all** (started, killed mid-flight; their transcripts are
under `…/subagents/workflows/wf_1eb8870f-9f3/`):

- **Test quality** — the systematic "what would have to break for this test to fail"
  pass, including mutation-testing every load-bearing test and checking `test_freeze.py`
  against the pre-fix code. I read `test_stimuli.py` and `test_freeze.py` myself and
  spot-checked `test_analyze.py`; **I did not review `test_instrument.py`,
  `test_parser.py`, `test_ledger.py`, `test_offline_replay.py`, `test_reconstruction.py`
  or `conftest.py` at all.**
- **Instrument** — the byte-level commensurability check against the companion study
  (rebuilding each session with `M.analyze_session` and comparing `J.dialogue_for_turn` to
  `PJ.dialogue_for`). **This is the study's central validity claim and I did not verify
  it.** The first audit's V3 reports 60/60 byte-identical on the *old* set; nobody has
  re-checked it on the 56.
- **Data quality** — I read 9 stimuli in full (the four backfills, C002, and the four
  shortest contexts) out of 56. The other 47 were examined only through aggregate
  statistics. There may be more items like C018.
- **Spend/safety** — I probed the ledger, breaker, cap arithmetic and the
  reportable/mock boundary myself, but did **not** examine the run lock under contention,
  crash-mid-promotion semantics, `os.replace` ordering, the served-model-drift abort, or
  `_with_backoff`'s unaccounted-billing exposure beyond reading the code.
- **Labelling blindness** — I recomputed every published *number* (V8) but did **not**
  inspect `labeling/batches/*.json` for what the labelling agents actually saw, nor verify
  the rep-specific shuffles differ, nor audit the five "fill" labels.
- **Manipulation check & selection** — the parts I did myself are in V9/V10; the
  independent re-derivation of the packet/review blindness was not done.
- **Freeze & document consistency** — I checked the git state and many individual numbers,
  but the systematic claim-by-claim table across README / PREREGISTRATION / decisions-log /
  abstract was not completed.

**Two lines did report and I have only partially reconciled them.** I personally re-verified
four of their claims (the untracked-logs consequence, the SciPy tie behaviour, the top-up
irreproducibility, the label join key) and they held. **Their remaining ~13 findings are
unverified leads, not findings, and are deliberately not carried into §2/§3 above.** The
adversarial refutation phase I had queued behind them never ran for either line.

**Structural gaps that no amount of further offline work would close:**

- **The live path was never exercised** (by constraint). Real parse-failure rate, real
  token counts, the served-model string Anthropic returns for `claude-opus-4-8`, and
  whether that model is still served at all are **unverified**. My cost figures are
  estimates from character counts.
- **No power simulation on real judge variance.** `corpus/logs/` holds tutor and student
  calls only — no pedagogy-judge reps — so the per-rep SD of `overall` is unmeasured and
  V11's half-widths are analytic, not empirical.
- **`vendor/` internals were treated as frozen upstream.** I read `judge_pedagogy.py`,
  `leakage.py` and `model_client.py` closely; I did not audit `metrics.py`,
  `protocol/session.py`, `agents/extraction.py` or `domain/algebra/checker.py` for
  correctness, and I did **not** verify the vendored files against `vendor/PROVENANCE.md`.
- **No corroboration for process claims.** No labelling or pairing transcripts exist in the
  repo, so "three fresh blind agents", "fresh blind reviewers", and the ordering claims
  ("pre-specified before any label existed") rest entirely on the decisions-log narrative —
  and, per §2.1, git cannot corroborate them either.
- **This is a methods and engineering review, not a statistical review.** I checked that
  the code computes what §6 describes and re-derived §6.5's precision claim; I did not
  assess whether the estimators are the right ones for the question.

---

## 6. WHERE TO RESUME

1. Finish the seven unreported lines above — **the instrument/commensurability check
   first**, since it is the study's central validity claim and is entirely unverified on
   the current 56.
2. Reconcile and adversarially verify the ~13 outstanding leads from the two lines that did
   report.
3. Then, before `--preflight`: commit and re-tag (§2.1), and make the §3 corrections to
   `PREREGISTRATION.md`, `decisions-log.md` and `paper/abstract.md` — all of which are
   legitimate now and illegitimate once a judge score exists.
