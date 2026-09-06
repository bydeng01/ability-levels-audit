# Post-run interpretation audit — what the 990 paid calls will and will not support

**Status: POST-RUN. Not a pre-flight document and not a revision of any pre-flight report.**
The paid run is complete, promoted and `reportable: true`; nothing here is a defect in the run,
the freeze, or the instrument. The pre-flight verdict in
`protocol/AUDIT-2026-08-10-post-a6-reverification.md` (GO) stands unamended. This document is
solely about which claims the resulting numbers license, and it exists because the first
interpretation written after the run (including a proposed headline) was wrong in two places.

Method: five independent adversarial lenses (statistical inference; censoring and measurement;
confounding and construct validity; pre-registration compliance; rival explanations) were each
tasked with refuting seven interpretive claims, every objection was then re-tested by a separate
verifier empowered to refute it, and 25 objections survived. Every load-bearing survivor below was
then re-verified a third time by the auditor directly against `results/per_unit.jsonl`,
`results/per_rep_scores.jsonl` and `results/wire/calls.jsonl`. Figures marked **[V]** were
personally recomputed; figures marked **[W]** are adopted from the adversarial pass and are
flagged as not independently re-derived.

---

## 1. The result, as it stands

**[V]** Primary `PAG_weak` = **+0.0849**, BCa 95% CI **[−0.16667, +0.35340]**, exact signed-rank
**p = 0.6837**, rank-biserial +0.1333, 18 clusters (14 nonzero). `PAG_strong` = +0.106, p = 0.9141.
Four-cell Δ: (D,weak) +2.582, (P_nov,weak) +2.719, (P_adv,weak) +2.634; (D,strong) +3.147,
(P_nov,strong) +3.194, (P_adv,strong) +3.089. Pure profile effect (weak): `R_H` −0.238 (p = 0.0625,
10/18 nonzero, 8 neg / 2 pos), `R_L` −0.153 (p = 0.0078, 8/18 nonzero, all negative).
Spend $10.01; 990/990 calls parsed, non-degraded, served `claude-opus-4-8`.

---

## 2. Verdicts on the seven post-run claims

| # | Claim as first written | Verdict |
|---|---|---|
| C1 | A6.3's uninformative branch is *decisively excluded* because a fall is uncensored | **Amend** — conclusion survives, stated reason is false |
| C2 | Censoring biases the primary *conservatively* (true PAG ≤ observed) | **FAILS** — direction is reversed |
| C3 | `productive_struggle` is real anchoring and deserves co-headline status | **FAILS** — reproduced by a zero-anchoring censoring model |
| C4 | The authoring-robustness re-estimate is uninformative | **Survives** |
| C5 | The A5.1 conditioner is satisfied (but thin) | **Amend** — "satisfied" overstates a floor-valued p |
| C6 | The shape is a uniform severity shift *rather than* differential preference | **Amend** — the contrast is an untested equivalence claim |
| C7 | CI/p disagreement is caused by BCa-on-all vs signed-rank-on-nonzero | **Amend** — right symptom, wrong mechanism |
| — | Proposed headline sentence | **FAILS on four independent counts** |

---

## 3. The three errors, with the evidence that kills them

### 3.1 C3 — the `productive_struggle` finding is manufactured by floor censoring (most important)

**[V]** `PAG_ps` (weak) = **+0.3781** (p = 0.0020) decomposes as `a_L` − `a_H` with
**`a_H` = −0.3951** (p = 0.0010) and **`a_L` = −0.0170** (p = 0.2500): 96% of the statistic is
one-sided movement on the high pole, and the low pole contributes essentially nothing.

**[V]** On **17 of 30** weak stimuli the `productive_struggle` low pole is pinned at exactly 1.000
in all three arms. On exactly those stimuli `PAG_ps ≡ −a_H` identically (verified to 1e-12):
where the low pole cannot move, the difference-of-differences degenerates into a one-pole severity
effect. Splitting on that:

| subset | stimuli | clusters | `PAG_ps` | p |
|---|---|---|---|---|
| low pole floored in all arms | 17 | 14 | **+0.4722** | 0.0039 |
| identifiable (low pole free) | 13 | 8 | **+0.1493** | 0.6250 |

**[W]** A generative model containing zero differential preference (add each stimulus's own
`a_H` to its three integer `R_L|P_nov` reps and clip at 1.0) reproduces `PAG_ps` = +0.3210
(p = 0.0039), leaving a residual of +0.0571 (p = 0.6250).

**[V]** The "anchoring on `productive_struggle` but not on `overall`" contrast was never coherent:
the judge emits `productive_struggle` and `assistance_calibration` as the same integer in
815/990 reps, `overall == assistance_calibration` in 849/990, pairwise sub-score r = 0.891–0.976,
and `overall` is a near-linear weighted mean of the four sub-scores (**R² = 0.9656**) whose
`productive_struggle` weight is ≈ **−0.067**. `overall` barely loads on the field in question, so
the divergence is a property of the rubric's aggregation rather than a result.

**[V]** Multiplicity does not rescue it either: the zero-robust exact sign test on the 18 PS
cluster means (10+ / 1−) gives p = **0.01172**, which fails Bonferroni ×8. No correction was
pre-registered in any case (§6.5: secondaries are descriptive with CIs).

**Consequence:** delete the `productive_struggle` clause from the headline; report the field with
`a_H` and `a_L` printed beside it, the floored/free split, and the null-model reproduction.

### 3.2 C2 — censoring is not conservative; the correction runs the other way

**[V]** The premise behind C1 and C2 ("the ceiling blocks rises, not falls") is empirically
false. Among weak `R_H` **pinned at 5.0 under P_nov, 1 of 16** fell under P_adv; among **unpinned,
8 of 14** did (Fisher exact **p = 0.0043**). A latent value sitting above the cap only shows an
observed drop once the latent drop exceeds the headroom, so the ceiling masks falls too.

Therefore `a_H` is the more attenuated term rather than `a_L`. Since `PAG = a_L − a_H`, de-censoring
makes `a_H` more negative and pushes `PAG` upward. **[W]** Estimated attenuation
k_H = 0.600 vs k_L = 0.783; latent `PAG` ≈ +0.2014 with a 95% profile region [0.00, +0.40]; every
de-censoring route tried (rescale, imputation, parametric) moved the estimate up. The original
claim required k_L < 0.455.

The surviving residue is weaker but still supports the primary's reading: **[W]** even the latent
`PAG` is not distinguishable from zero (deviance p = 0.067). But it must not be presented as a
conservative bound. **[W]** Disclose also that the primary is a mixture: `PAG` = −0.205 where the
D arm pins `R_H` at 5.0 versus +0.352 where it does not.

### 3.3 C1 — the conclusion survives, by a different route

A6.3's uninformative branch is still inapplicable, but not because a fall is uncensored. It is
inapplicable by its own text: A6.3 conditions on a joint null of `PAG_weak` and the §6.3 pure
profile effect, and **[V]** the pure effect is non-null (`a_L` p = 0.0078). Strike "decisively
excluded" and "contradicted by data". **[W]** On the 14 weak stimuli where a rise is expressible,
8 fell and 2 rose (sign p = 0.109), which is suggestive but not decisive.

---

## 4. A falsified registered statement (the most publishable finding here)

Amendment **A6.3** asserts: *"Censoring cannot manufacture an effect, so a non-null `PAG_weak`
remains interpretable as profile influence."* That is false as written for a
difference-of-differences endpoint, and this study's own data demonstrate it: when one pole is
floored, `PAG` collapses to `−a_H` (§3.1, verified identically on 17/30 weak stimuli), so
asymmetric censoring biases the statistic away from zero in the registered anchoring direction.

The primary endpoint is null, so nothing in the headline result is corrupted. But the registered
protection is narrower than it claims: only the weaker reading ("the profile influenced the
rating") is protected, and the per-field secondaries are not protected at all. Correcting this in
print is a genuine methodological contribution and should be stated plainly.

---

## 5. Required disclosures

1. **Report the interval, never a bound.** BCa 95% = [−0.16667, **+0.35340**], half-width 0.2600.
   "|PAG| < 0.35" is **[V]** false against the study's own upper limit. No equivalence margin,
   SESOI or power statement is pre-registered, so no bound may be asserted. §6.5 registers the
   half-width as a reported output and **[V]** `summary.json` contains no `half_width` key.
2. **Resolution.** **[W]** 80% power is first attained near +0.41–0.45; power at +0.35 is ≈0.70;
   nominal-95% BCa coverage at n=18 is ≈0.93 (0.894 on the pure-low endpoint). State the null as a
   failure to detect at this resolution, not as absence of effect.
3. **Censoring direction is not conservative** (§3.2), with the saturated/interior mixture.
4. **A6.4 sub-score floor table**, registered but never emitted by the digest-bound estimator.
   **[V]** Low pole at exactly 1.000, per 55 units, D / P_nov / P_adv:

   | field | D | P_nov | P_adv | weak stimuli pinned in all 3 arms |
   |---|---|---|---|---|
   | overall | 18 | 25 | 30 | 4/30 |
   | scaffolding | 1 | 2 | 8 | 0/30 |
   | productive_struggle | 41 | 41 | 42 | **17/30** |
   | assistance_calibration | 31 | 33 | 37 | 10/30 |
   | elicitation | 46 | 46 | 48 | 22/30 |

5. **Per-field decomposition** with `a_H`/`a_L` beside every PAG. **[V]** `assistance_calibration`
   has the larger `a_H` (−0.4645, p = 0.0090) but the smaller PAG (+0.3086), the difference
   being low-pole retention, which is direct evidence that the field ranking is censoring geometry.
6. **Rubric near-collinearity** (§3.1): 815/990, 849/990, R² = 0.9656. The top of the per-field
   table is not statistically separable.
7. **Multiplicity.** **[V]** `summary.json` reports 20 p-values + 26 BCa intervals = **46**
   inferential statements (the adversarial pass counted 47; my count is 46). Drop "survives
   Bonferroni ×8": the family size is unjustified and the zero-robust sign test fails it.
8. **A5.1 / A5.2 gates.** **[V]** `a_L`'s p = 0.0078125 is exactly 2/2⁸, the *attainable minimum*
   at 8 nonzero clusters; the whole result is "8 of 8 clusters agreed in sign", magnitude
   discarded. **[V]** The A5.2 evidence gradient is null (Spearman ρ = −0.179, p = 0.4149), so the
   ability-anchoring reading is unsupported in either direction.
9. **CI/p disagreement rows.** State the cause correctly: the CI estimates a magnitude-weighted
   mean while the p tests rank/sign location; **[W]** restricting the CI to the nonzero
   set does not remove the disagreement. **[V]** Print the
   `2.2308762216603812e-17` lower limit on `delta(P_nov)-delta(D), weak` as 0.000; **[W]** its
   zero-exclusion is seed-dependent (16/40 seeds).
10. **Quantisation.** **[W]** 86.1% of units are rep-deterministic on `overall`; per-stimulus PAG
    takes 8 values, all multiples of 1/3; five optimally placed single-rep flips zero the primary.
    Drop the "genuine indifference vs movement-blocked" partition: interior zeros are threshold
    non-crossings, not evidence of indifference.
11. **Label the unregistered contrasts as exploratory.** **[V]** Per-pole D-contrasts (weak),
    absent from `summary.json`: P_nov−D high +0.009 (p = 0.842); P_adv−D high −0.228 (p = 0.047);
    P_nov−D low −0.128 (p = 0.094); P_adv−D low −0.281 (p = 0.001953 is itself exactly 2/2¹⁰, its
    own floor at 10/10 clusters; say so).
12. **"Learner profile", not "ability label"**, throughout: the profiles bundle stated ability with
    a stated help-seeking preference (§2, A5.2), so the endpoint is profile *influence*.
13. **Provenance split.** Distinguish numbers emitted by the digest-bound estimator
    (`analyze_py_sha256` 458932b5…, `prereg_md_sha256` 2e3a8697…, both **[V]** matching) from
    post-hoc diagnostics. Commit a separate script emitting the A6.4 table and the test-retest, and
    publish its output beside `summary.json`.

---

## 6. Two positive robustness facts that survived every attack

- **[V] Not a prompt-length artifact.** Input tokens are constant across the 3 reps of all 330
  units, and differ by exactly one token between P_adv and P_nov across all 110
  (stimulus, pole) pairs (min = max = −1; P_nov − D = +122 exactly). The pure profile effect cannot
  be explained by prompt length.
- **[V] Instrument test–retest.** The 165 D-arm real-pole calls are byte-identical repeats of
  July-2026 companion calls: now 3.891 vs 3.879, Pearson **r = 0.979**, mean |diff| 0.133,
  **[W]** 40/55 exactly equal, sub-score r 0.982–0.997. No model drift.

---

## 7. Defensible headline

> On weak-evidence stimuli, a frozen pedagogy LLM judge's holistic preference for high-scaffolding
> responses (Δ = +2.58 with no profile) is not detectably shifted by a stated learner profile
> (`PAG_weak` = +0.085, 95% BCa [−0.167, +0.353], half-width 0.260, exact signed-rank p = 0.68). It
> is a failure to detect anchoring at a resolution that cannot exclude a +0.35 gap (≈13% of the
> measured Δ), not a demonstration of its absence. The advanced profile does lower absolute severity
> relative to the novice profile on the low pole (−0.153, p = 0.0078, the exact-test floor at 8 of
> 18 clusters) and, non-significantly, on the high pole (−0.238, p = 0.0625). The largest per-field
> gap (`productive_struggle`, +0.378) is reproduced by a zero-anchoring floor-censoring model and is
> not identified as anchoring. The pre-registered authoring-interaction check was underpowered
> (4 nonzero clusters, p = 0.75) and is reported as uninformative.

---

## 8. Not covered

- **No re-analysis of the frozen estimator itself.** `analyze.py` was verified (pre-flight, and
  again post-run by independent reimplementation reproducing the real primary to 10 significant
  figures) to compute the registered §6 estimands; nothing here proposes changing it, and it must
  not be edited; it is digest-bound to the run.
- **The censoring corrections in §3.2 are model-based**, not registered, and are reported as
  sensitivity analyses only. No censoring-corrected number should be promoted to a headline.
- **`[W]`-marked figures** (coverage simulations, power curves, attenuation coefficients, the
  null-model reproduction, the seed-dependence count) were produced by the adversarial pass and
  re-tested by its verifiers, but not re-derived a third time by the auditor. The claims they
  support are directional and would need independent recomputation before print.
- **No new labelling, stimulus or instrument review** was performed; §5 of the pre-flight report
  stands.
- **Operational note:** this file is untracked, so `run_study.py`'s clean-tree gate will refuse
  `--offline-cache-only` until it is committed, and committing moves `HEAD`, which breaks that
  path's `git_commit` equality check anyway (the known N5 limitation). Run any cache replay before
  committing this, or accept that replay is only possible from the run's own commit.
