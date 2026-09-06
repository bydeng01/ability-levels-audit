# Manuscript correctness audit — `ability-levels-audit`

Adversarial re-derivation of `NeurIPS_2026_newinml/neurips_2026.tex` against the released artifacts.
Every number below was recomputed from `results/`, `corpus/`, `labeling/` and `profiles/` with an
independent implementation of the registered estimators, not read from `summary.json`,
`diagnostics.json`, the README, the pre-registration or any prior audit.

**Integrity gates.** All 12 entries of `results/frozen_inputs.sha256` were re-hashed at the start and
again at the end of this audit: unchanged, and in agreement with `results/run_meta.json`,
`results/preflight/resolved_config.json` and the sidecar. `contract_sha256` agrees across both
records (`fe0a59d2…`). The promoted-result manifest, the wire hash and the cache hash all verify.
Nothing was modified. No paid call was made.

---

## Findings

### 1. Three reported values do not re-derive from the released artifacts — Blocker

**Claim.** §7 asserts that every reported value re-derives offline from the release, and Appendix D
that the release is self-contained; the drift check's published comparison values are not in the
release and cannot be recomputed from it.

**Location.** `neurips_2026.tex:210` (§7, twice) and `:395` (App. D).

**Evidence.** §7: *"for each stimulus's real tutor turn, the no-profile arm re-issues a
byte-identical rating request whose prompt and published score ship with the corpus, 165 calls in
all. They return a mean of 3.891 against the published 3.879, Pearson r = 0.979, exact agreement on
40 of the 55 stimuli."*

- The re-issued side re-derives exactly. From `results/per_unit.jsonl`, taking each stimulus's
  `real_turn_pole` under arm `D`: n = 55, 165 calls, mean = **3.890909** → `3.891`. ✔
- The published side does not. `analysis/diagnostics.py::_load_companion_scores` reads
  `<companion results>/{ablation,confirmatory,confirmatory_gpt,confirmatory_gemini}/pedagogy_detail.json`
  from a separate repository (`vendor/PROVENANCE.md`: source repo `conv-vs-ped-tutor`, commit
  `ab5ea2a9…`). Nothing under this release contains published pedagogy scores:
  `grep -c productive_struggle corpus/logs/*/calls.jsonl` → `0` (those logs hold only `student`/`tutor`
  roles); `grep -c overall_mean corpus/candidates.jsonl corpus/response_pools.jsonl` → `0`, `0`.
  Keys of the corpus artifacts carry `context`, `response`, `tracker`, `n_words`, and no scores.
- So `3.879`, `r = 0.979` and `40 of the 55` require a second, separately-released artifact. They are
  the only reported values that do. Everything else I re-derived offline from this release alone.

**Severity.** Blocker: "every value reported here re-derives offline" and "the release is
self-contained" are false as stated, in the paragraph whose subject is checkable provenance.

**Fix.** Two edits, length-neutral together.

At `:395`, replace `The release is self-contained.` with:

`The release is self-contained but for the corpus's own published scores, which only the drift check reads.`

At `:210`, replace `On the arm it covers, this removes judge drift as a competing account of the null, and it is the only direct drift check the design affords.` with (this also fixes finding 6, and the clause I cut to pay for the sentence above is `and it is the only direct drift check the design affords`, which Appendix A already states at `:347`):

`On the one arm and pole it covers, 165 of the 990 calls, this removes judge drift as a competing account of the null.`

---

### 2. The premise that the field uses this design is uncited, and no cited audit instantiates it — Serious

**Claim.** The paper's relevance rests on a within-item double difference being current practice and
the field's strongest design; that sentence carries no citation and none of the cited audits uses it.

**Location.** `neurips_2026.tex:69`, echoed at `:222`.

**Evidence.** At `:69`, *"The strongest audits difference twice: a within-item contrast between two
candidate responses is differenced again across the manipulated attribute…"* carries no `\citep`. The
citation on the preceding clause is `\citep{wang2024large,howell2025prestige}`. Checked against the
cited works: `wang2024large` swaps candidate order (a within-item contrast, not a double
difference); `howell2025prestige` randomises author identity across manuscripts in a between-item
regression whose headline is a rejection decision; `panickssery2024llm` contrasts self- versus
other-generated text; `chen2024humans` perturbs items; and the manuscript's only named exemplar,
`maltbie2026intersectional` (`:71`), is a between-conversation persona factorial
(race × age × gender × confidence) rather than a within-item two-pole difference in differences. The design
the paper analyses and warns the field about is not documented as being in use.

**Severity.** Serious: an unsupported empirical claim about the field, load-bearing for the paper's
scope.

**Fix.** At `:69`, replace `The strongest audits difference twice:` with:

`A stronger design differences twice:`

At `:222`, replace `and the within-item difference in differences is their strongest form;` with:

`and a within-item difference in differences is the natural way to strengthen them;`

---

### 3. The "worse as the stimuli improve" claim is stated in a work cited only for a weaker point, and the closest prior work is uncited — Serious

**Claim.** The escalation observation the abstract sells as distinctive appears almost verbatim in
Rohrer & Arslan (2021), which the paper cites only for "a scale can manufacture an interaction is
known"; and a 2025/26 paper covering exactly this statistical object is uncited.

**Location.** `neurips_2026.tex:92` (the citation), `:141` (the claim), `:63` and `:71` (the abstract
and introduction versions), `:77` (contribution 1).

**Evidence.**

- Rohrer & Arslan (2021), *AMPPS* 4(2), Box 1, verbatim: *"The stronger the main effect of the
  moderator on the outcome is, the more exacerbated the problems caused by ceiling or floor effects
  are because this will push individuals with certain moderator values closer to the boundaries of
  the scale."* Box 1 also gives the spurious interaction itself (*"a regular regression analysis
  would indicate an interaction between the predictor and group membership"*) and both remedies the
  manuscript names at `:217`. The manuscript's `:141`, *"the difficulty deepens as the stimuli
  improve: a common shift is censored unequally precisely because the two poles sit near opposite
  bounds"*, is the same point.
- Wang & Li, *"Tobit modeling for dependent-sample t-tests and moderated regression with ceiling or
  floor data"*, **Behavior Research Methods** (doi `10.3758/s13428-025-02904-y`), uncited: a
  dependent-sample design, a moderation (interaction) estimand, a ceiling/floor-censored
  outcome. Abstract: conventional analysis yields *"biased estimates, inflated Type I error rates,
  and poor confidence interval coverage, even with as little as 10% ceiling data"*; the paper reports
  moderated-regression Type I error of 69.8–80.3% and relative bias in the interaction coefficient of
  92.7–101.2%. That is the manufactured interaction, quantified, in the manuscript's own setting.

**Severity.** Serious: contribution 1 as worded ("an identifiability analysis of within-item
difference-in-differences endpoints on bounded rating scales") does not survive Wang & Li; the
judge-audit instantiation, the live counterexample and the three-number check do.

**Fix.** At `:92`, replace `that a scale can manufacture an interaction is known \citep{rohrer2021precise}.` with:

`that a bound can manufacture an interaction, and that it worsens as the moderator's main effect grows, is known \citep{rohrer2021precise}, and censored-outcome corrections exist for the dependent-sample moderation case \citep{wangli2026tobit}.`

Buy the length by cutting, from the same paragraph, `Recent work on judge scale design tunes granularity for human agreement \citep{li2026grading} but does not treat the bounds as an identification problem.`

At `:77`, replace `an identifiability analysis of within-item difference-in-differences endpoints on bounded rating scales, carrying known limited-dependent-variable results \citep{puhani2012treatment} into the judge-audit setting` with:

`we carry known censored-outcome results \citep{puhani2012treatment,rohrer2021precise} into the judge-audit setting`

---

### 4. The introduction reports only the larger of the two construction shares — Serious

**Claim.** The abstract and §4.3 both give the reproduced share as a range; the introduction gives
only the upper end, which is the one the producing code says not to quote alone.

**Location.** `neurips_2026.tex:75`.

**Evidence.** Recomputed from `results/per_rep_scores.jsonl`: applying each stimulus's observed
high-pole shift to its three integer low-pole ratings under the novice profile and clipping to
[1,5] reproduces **+0.320988** = **84.90%** of the observed **+0.378086**; rounding the shifted
ratings to the integers the judge emits reproduces **+0.297840** = **78.78%**. The abstract (`:63`)
says "79 to 85\%" and §4.3 (`:192`) gives both. `:75` says only "85\% of the magnitude".
`analysis/diagnostics.py` (the producer) states: *"The judge emits integers, so `round_then_clip` is
at least as defensible and gives a smaller share. Quote the range, not the larger endpoint."*

**Severity.** Serious: a missing hedge on the paper's headline counterexample, inconsistent with its
own abstract two paragraphs earlier.

**Fix.** Replace `reproduces $+0.321$, 85\% of the magnitude,` with:

`reproduces 79 to 85\% of the magnitude,`

---

### 5. Table 3 claims to cover every reported quantity; the per-pole split that carries §4.3 has no row and no status label — Serious

**Claim.** The per-pole decomposition of each per-field gap is post-hoc, is not emitted by the frozen
estimator, and appears in no row of the specification-status table, while the sentence that
introduces it opens with "The registered per-field decomposition".

**Location.** `neurips_2026.tex:188` (the numbers), `:402` (the caption's completeness claim),
`:410`–`:429` (the table).

**Evidence.** `analysis/analyze.py:358-369` emits, per field × stratum, only
`mean / ci95_bca / wilcoxon_p / rank_biserial / n_nonzero`; dumping the keys of
`analysis/out/summary.json` for `secondary_per_field_decomposition.productive_struggle.weak`
confirms there is no `a_high`, no `a_low`, no share and no floored/free split. Those quantities
($a_H = -0.395$, $a_L = -0.017$, $a_H = -0.465$ with $p = 0.00903$, the 72–96% and 104–164% shares,
the +0.472 / +0.149 split, and every per-pole term in Figure 2b) come from
`analysis/diagnostics.py`, which is not in `frozen_inputs` (I re-hashed all 12: `diagnostics.py`
has no entry). Table 3's rows are: *Per-field decomposition* (filed registered-by-digest, correct
for the gap but not for its split); *Unregistered per-pole contrasts* (Location §4.2 / App. C; those are
the contrasts against the no-profile arm, a different quantity); *Identifiability diagnostic*
(Location §5; the three-number check, of which the per-pole split is not one). Figure 2's caption
does open "**Exploratory.**"; the prose numbers at `:188` carry no such label.

**Severity.** Serious: an unlabelled post-hoc quantity carrying the central §4.3 argument, in the
one table a reader consults for specification status.

**Fix.** Insert after `:427`:

`Per-pole split of each gap & Shows the gaps are high-pole movement & \S\ref{sec:manufactured}, Fig.~\ref{fig:two} \\`

Buy the row by deleting, from the Table 3 caption at `:402`, `Registered quantities were fixed before any score existed;` which the group headings already say. And at `:188` replace `The registered per-field decomposition reports one nominally significant gap:` with:

`The registered per-field gaps include one nominally significant one; their per-pole split below is exploratory:`

---

### 6. The drift check's stated coverage limit omits that it covers one pole per stimulus — Serious

**Claim.** The check is hedged to "the arm it covers"; it also covers only the real-turn pole, so it
speaks to 165 of 990 calls and to 55 of the 110 no-profile units.

**Location.** `neurips_2026.tex:210`.

**Evidence.** `analysis/diagnostics.py::test_retest` joins on `stimuli[sid]["real_turn_pole"]` only.
From `corpus/stimuli.jsonl` the real turn is the high pole in 43 of 55 pairs and the low pole in 12,
so exactly one of each stimulus's two poles is covered. The no-profile arm holds 55 × 2 × 3 = 330
calls; the check re-issues 165. Mean absolute difference is 0.133 with a maximum of 1.0, and exact
agreement is 40 of 55; the check bounds mean drift on that one cell, not agreement everywhere.

**Severity.** Serious: a check said to remove a competing account without its own coverage limits
fully stated.

**Fix.** Given in finding 1.

---

### 7. "105–164%" excludes its own minimum — Minor

**Claim.** The lower endpoint of the stated range is 104%, not 105%.

**Location.** `neurips_2026.tex:188`.

**Evidence.** $|a_H| / |\mathrm{PAG}|$ recomputed per field over source-run means: scaffolding
$0.212963/0.129630 = 164.29\%$; productive struggle $0.395062/0.378086 = \mathbf{104.49\%}$;
assistance calibration $0.464506/0.308642 = 150.50\%$; elicitation $0.172840/0.134259 = 128.74\%$.
Minimum 104.49% → 104%. (The companion range is right: pole-movement shares are 71.9, 95.9, 74.9,
81.8% → "72–96%".)

**Severity.** Minor: rounding, in the direction that overstates the smallest share.

**Fix.** Replace `$105$--$164\%$` with `$104$--$164\%$`.

---

### 8. §5 attributes both bounds on the attenuation share to non-expansiveness — Minor

**Claim.** Non-expansiveness gives $\kappa_j \ge 0$; the upper bound $\kappa_j \le 1$ needs the clip's
monotonicity, which is not invoked.

**Location.** `neurips_2026.tex:134`.

**Evidence.** $\kappa_j = 1 - a_j/\delta$ with $a_j = \mathbb{E}\,c(Y^{*}_j+\delta) - \mathbb{E}\,c(Y^{*}_j)$.
$\kappa_j \ge 0 \iff a_j/\delta \le 1$, which is $|a_j| \le |\delta|$: non-expansiveness.
$\kappa_j \le 1 \iff a_j/\delta \ge 0$, i.e. $a_j$ shares the sign of $\delta$; that is monotonicity,
and a non-expansive map need not be monotone. Both hold for $c(y)=\min(\max(y,\ell),u)$, so the
conclusion stands; the stated reason covers half of it. Everything else in §5 re-derives:
$\PAG = (\kappa_H-\kappa_L)\delta$; the collapse to $\PAG \equiv -a_H$ at $\kappa_L=1,\kappa_H=0$;
$\PAG = \PAG^{*} + \kappa_H\delta_H - \kappa_L\delta_L$ with $\PAG^{*} = \delta_L-\delta_H$; and the
headroom identity (positive headroom $d+4$, negative $4-d$, difference $2d$ with $d$ the pole
separation).

**Severity.** Minor.

**Fix.** Replace `Because $c$ is non-expansive,` with `Because $c$ is monotone and non-expansive,`,
and pay for it by deleting `whatsoever` from `expresses no differential preference whatsoever`
earlier in the same paragraph.

---

### 9. Table 3 calls the floor-censoring construction a "null simulation" — Minor

**Claim.** The object is deterministic and is named a construction everywhere else; the table's name
also collides with the genuine Monte-Carlo row four lines below.

**Location.** `neurips_2026.tex:425`, against `:63`, `:75`, `:147`, `:192`, `:197`, `:217`, `:429`.

**Evidence.** The manuscript calls it "a construction containing zero differential preference"
(`:63`, `:75`), "a null model" (`:147`), "A post-hoc construction" (`:192`), "a
zero-differential-preference floor-censoring construction" (`:197`) and "…model" (`:217`); Table 3
says "Floor-censoring null simulation" (`:425`), and `:429` uses "simulations" for the 6,000 / 20,000
/ 600-replicate Monte Carlo. The producing code states the object *"is NOT a data-generating
process"*.

**Severity.** Minor.

**Fix.** Replace `Floor-censoring null simulation` with `Floor-censoring construction`.

---

### 10. Table 2's tutor-type row counts stimuli, not source runs — Minor

**Location.** `neurips_2026.tex:368`.

**Evidence.** The row reads `Source-run tutor type (pedagogy-tuned / conversational) & 31 / 24`.
From `corpus/stimuli.jsonl`, 31 + 24 = 55 stimuli; by source run the split is 13 / 10 = 23, and
the row two above states 23 runs. The dependent row at `:370` (`ped. 29/31, conv. 14/24`) also uses
stimulus denominators, and the prose at `:217` says "23 of 30 weak *contexts*".

**Severity.** Minor.

**Fix.** Replace `Source-run tutor type (pedagogy-tuned / conversational)` with
`Stimuli by source-run tutor type (ped.-tuned / conversational)`.

---

### 11. "cluster" carries every exact-test floor argument but is never bound to "source run" — Minor

**Location.** first undefined use at `neurips_2026.tex:183`; definition paragraph at `:126`.

**Evidence.** §3 defines the inference unit as "source tutoring run" / "source run" and §4.1 says
"source-run means"; "cluster" then appears twelve times (`:183`, `:188`, `:190`, `:192`, `:213`,
`:217`, `:386`, `:388`, `:439`, `:447`, `:454`) carrying every "n nonzero clusters" floor statement,
without ever being identified with the source run.

**Severity.** Minor.

**Fix.** At `:126` replace `and all tests and intervals use those source-run means;` with
`and all tests and intervals use those source-run means, the study's clusters;`, paying for it by
deleting `in full` from `its $p$-value enumerated in full`.

---

### 12. Figure 1's caption defines the shaded band as the sub-80%-power range; power at ±0.42 is 0.93 — Minor

**Location.** `neurips_2026.tex:447`, against `:157`.

**Evidence.** Re-running the registered power simulation (bootstrap of the observed centred cluster
distribution, 6,000 replicates, the figure's own seed): power is 0.0800 at shift 0, 0.7093 at
+0.3534, 0.7187 at +0.38, **0.7112 at +0.40** and **0.9297 at +0.42**. The main text says power
"first exceeds $0.80$ between $+0.40$ and $+0.42$", so ±0.42 is the upper bracket of the crossing,
not the range where power is below 80%.

**Severity.** Minor.

**Fix.** Replace `within $\pm 0.42$ of the stated-novice line: the $|\PAG|$ range where the registered test's power is below $80\%$` with:

`within $\pm 0.42$ of the stated-novice line, the bracket inside which the registered test's power first reaches $80\%$`

---

### 13. Bibliographic details — Minor

**Location.** `references.bib`.

- `gelman2016statistical` is a mangled record (`journal={The best writing on mathematics (Pitici M, ed)}, volume={102}, pages={305--318}, year={2016}`). The primary publication is Gelman & Loken, *American Scientist* **102**(6), 460–465, **2014**. The content attributed at `:95` is correct.
- `tack2022ai` is cited as an arXiv preprint; it was published at **EDM 2022** (15th Int. Conf. on Educational Data Mining, short papers).
- `maltbie2026intersectional` gives the author as "Benjamin Maltbie"; arXiv:2604.11609 lists **Ben Maltbie**. Everything the manuscript attributes to it at `:71` (1–10 rubric, factorial interactions, most ratings within two points of the floor) checks out.
- `vanlehn2011relative` is in the bib and never cited.

---

## Known items

**Item 1: the client-library version is not single-sourced. CONFIRMED.**
`judging/run_study.py:756` records `anthropic.__version__` into `resolved_config.json`
(`"anthropic_sdk_version": "0.96.0"`), while `judging/profile_judge.py::contract_sha256` hashes
`importlib.metadata.version("anthropic")` into the digest. Two independent lookups; they can
disagree (editable install, shadowed module, vendored copy). Appendix A at `:347`, *"the provider's
client library version, 0.96.0, is hashed into the contract digest"*, attributes the recorded
string to the digest, which is not where the digest's copy came from.
Suggested fix at `:347`: replace `and the provider's client library version, 0.96.0, is hashed into the contract digest with the request values and the code that assembles them` with
`and the client library version the digest records, 0.96.0, is hashed with the request values and the code that assembles them, though the run record reads it by a second path`.

**Item 2: the judge is named one way in the main text and another in Appendix A. REFUTED.**
`grep -in "opus|claude" neurips_2026.tex` returns exactly two mentions: `:110` *"an instance of
Claude Opus 4.8"* and `:347` *"The provider returned one identifier, Claude Opus 4.8, on all 990
calls"*. Identical prose form. The artifacts use the API identifier `claude-opus-4-8`
(`run_meta.json:judge_model`; `served_model` on all 990 wire rows; `vendor/configs/models.yaml`
judge role), which is the same object in its API spelling. No inconsistency remains in this file.

---

## Verification record

### Re-derives exactly

Design and units: 55 stimuli (30 weak / 25 strong), 23 source runs (18 / 10, 5 shared), 6 problems,
330 units, 990 rep rows, 990 wire rows, 990 unique keys, all `parsed_ok`, all `attempt = 1`, all
`stop_reason = end_turn`, all `served_model = claude-opus-4-8`, 55 × 3 × 2 × 3 = 990.

Preference table (all six cells and all six intervals): weak $D$ +2.5818 [2.2716, 2.9167],
$\Pnov$ +2.7191 [2.3796, 3.0370], $\Padv$ +2.6343 [2.1250, 2.9815]; strong $D$ +3.1467 [2.7633,
3.5091], $\Pnov$ +3.1944 [2.9222, 3.5500], $\Padv$ +3.0889 [2.7000, 3.4667].

Primary: +0.084877, pseudomedian 0.000, BCa [−0.16667, +0.35340], half-width 0.26003,
exact signed-rank $p$ = 0.683716, rank-biserial +0.13333, 18 clusters, 14 nonzero, 4 exact zeros.
Strong companion +0.105556, [−0.19444, +0.57222], $p$ = 0.914062.
Movement contrasts +0.137346 ($p$ = 0.163086) and +0.052469 ($p$ = 0.742188).

Per-pole shifts: pure low weak −0.152778 (pseudomedian −0.08333, BCa [−0.32407, −0.07407],
$p$ = 0.0078125 = $2/2^8$ at 8 nonzero clusters); pure high weak −0.237654 ([−0.46914, −0.01852],
$p$ = 0.0625). Identity $a_L - a_H$ = +0.084877 = the primary. Per-pole contrasts against the
no-profile arm: +0.009259 ($p$ = 0.841797), −0.128086 ($p$ = 0.09375), −0.228395 ($p$ = 0.046875),
−0.280864 ($p$ = 0.00195312 = $2/2^{10}$, 10 of 10 concordant).

Per-field decomposition (weak): productive struggle +0.378086 ($p$ = 0.00195312), assistance
calibration +0.308642 ($p$ = 0.101685), elicitation +0.134259 ($p$ = 0.226562), scaffolding
+0.129630 ($p$ = 0.501953). $a_H$ / $a_L$ for productive struggle −0.395062 / −0.016975;
$a_H$ for assistance calibration −0.464506 ($p$ = 0.0090332). $a_L - a_H$ closes on all four gaps to
machine precision. High-pole test $p$ = 0.000976562 = $2/2^{11}$ at 11 nonzero clusters; low-pole
term 3 nonzero clusters, floor 0.25.

Censoring and pinning: composite high pole at exactly 5.000 in 18 / 16 / 17 of 30 by arm, low pole at
exactly 1.000 in 4 / 9 / 11; these are Figure 2a's six counts, exact. Low pole pinned in all three
arms, by field: composite 4, scaffolding 0, productive struggle 17, assistance calibration 10,
elicitation 22; those are Figure 2b's five grey counts, exact. On the 17 productive-struggle pinned stimuli
$\PAG_s \equiv -a_{H,s}$ holds identically. Split +0.472222 ($p$ = 0.00390625 = $2/2^9$, 9 nonzero)
against +0.149306 (5 nonzero, floor 0.0625).

Floor-censoring construction: +0.320988 = 84.90% ($p$ = 0.00390625, Figure 2c's 0.004); rounded
+0.297840 = 78.78%; residual +0.057099 ($p$ = 0.625, 5 nonzero, floor 0.0625).

Not-conservative section: 16 pinned at 5.000 under the novice profile of which 1 fell; 14 unpinned of
which 8 fell; Fisher exact two-sided $p$ = 0.00429785. Oversaturation mixture −0.204545 on 18
stimuli ($p$ = 0.21875) and +0.351852 on 12 ($p$ = 0.105469). $|a_H| = 0.238 > |a_L| = 0.153$.

§5 numbers: weak-stratum stimulus-level pole means under the novice profile 4.5778 and 1.9556,
separation 2.6222, headroom +6.6222 against −1.3778, difference 5.2444 = twice the separation.

Resolution and multiplicity: 21 $p$-values + 26 intervals = 47 in `summary.json`; 284 of 330 units
returned the same integer in all three reps; the closest pair of rubric fields agrees in 815 of 990
ratings (productive struggle vs assistance calibration; no other pair of the four exceeds it); eight
distinct per-stimulus weak-stratum $\PAG$ values, all multiples of 1/3; the exact clustered mean is
55/648, five single-integer rating changes take it strictly past zero (cumulative 1/54 × 5 = 5/54)
and the minimum landing exactly on zero is six (1/54 × 4 + 1/162 + 1/216); four rows where a BCa
interval excludes zero although the rank test does not reject; the near-zero limit is
$2.2309\times10^{-17}$ at the registered seed, and over seeds 0–39 it never exceeds 0.00463 in
magnitude and is zero to floating-point precision in exactly 13. Six reported tests sit at their
attainable floor and four have a floor above 0.05; both counts verified by enumerating every
$p$-value printed in the manuscript and in the figures (the sixth floor case is the construction's
$p = 0.004$ in Figure 2c; the fourth "cannot reject" case is the residual, also figure-reported).

Simulations: power 0.0800 at shift 0, 0.7093 at the interval's upper limit, first above 0.80 between
+0.40 and +0.42; size 0.04865 under sign flips; BCa coverage 0.9417 and 0.8817 at n = 18 with Monte
Carlo standard errors 0.00957 and 0.01319.

Materials and labels: 23 single-message contexts (weak 7/30, strong 16/25); real turn is the high
pole 43/55, by tutor type 29/31 and 14/24; authored poles 26 low and 2 high; 27 all-corpus pairs
with 24/27 low and 4/27 high poles from one tutor model; 26 of 29 corpus-drawn low poles from that
model; question marks in 37/55 high and 1/55 low; `\boxed` final answers in 18 low and 0 high; low
responses longer (61.0 vs 47.0 mean words); weak contexts 23/30 pedagogy-tuned, strong 17/25
conversational; construction check 55/55 at one rater per pair, blind and order-randomised;
126-candidate pool, 115 unanimous, pairwise agreement 119/126, 119/126, 118/126 = 94.4 / 94.4 /
93.7%; prior overturned toward weak 7 times and toward strong 0; the rubric revision moved 45
candidates strong→weak and 0 weak→strong; census 2,219 judged turns.

Appendix A: the three verbatim blocks un-wrap (strip the two-space continuation indent, rejoin with a
single space) byte-for-byte identical to the frozen system prompt (3,096 chars), the assembled
profile-arm user message (458 chars) and both profile texts (374 and 380 chars, 59 words each). No
line of any real prompt begins with the continuation indent. Square brackets appear only as the three
slot markers. Independently, reconstructing every user message from the stimuli and the frozen
templates reproduces the logged prompt hash on **990 of 990** calls. Request facts: `max_tokens` 512,
temperature omitted, input tokens identical across the three reps of all 330 units, exactly one token
lower under the advanced profile than the novice on all 110 (stimulus, pole) pairs, exactly 122
higher under the novice than under the no-profile arm on all 110. The served-model abort gate exists
(`run_study.py:688-691`).

Appendix D's rebuild claim: running the repository's own verifier on the device returned
`verify PASS: 55 contexts and 82 corpus-sourced responses rebuilt byte-identical from corpus/logs;
sha256 matches`.

Figures: `fig1.pdf` is 324.72 pt wide and included at `0.82\linewidth` (= 324.72 pt); `fig2.pdf` and
`fig3.pdf` are 396.00 pt and included at `\linewidth`. The content streams of the three PDFs shipped
with the paper are byte-identical to the current output in `analysis/figures/` (only the PDF
creation timestamp differs), so the plotted values are the ones the scripts produce from the released
data. Every label extracted from the three figures matches the text.

Pre-registration quotation at `:144` matches `protocol/PREREGISTRATION.md:552-553` verbatim
(truncated at "profile influence", the remainder being "and §6.2's positive reading is unaffected").
Table 3's registered-by-digest rows are all emitted by `analyze.py`, whose hash is in
`frozen_inputs`; the "separate script" rows map to sections `diagnostics.py` marks
`REGISTERED A6.4(a)`, `A6.4(b)` and `§6.5`; neither `diagnostics.py` nor `simulations.py` is a frozen
input.

### Re-derives only to rounding

`+0.106` for the strong-stratum companion (exact +0.105556; the four-cell table's three-decimal
display gives 3.194 − 3.089 = 0.105); `2.981` for the weak advanced-arm upper interval limit (exact
2.98148); `+2.6` for a baseline of 2.5818. None of these is an error.

### Does not re-derive

`105\%` at `:188`: the recomputed minimum is 104.49% (finding 7). That is the only numeric literal
in the manuscript I could not reproduce.

---

## Coverage

**Checked.** Every numeric claim in the abstract, all eight sections, both tables, all three figure
captions and all five appendices, re-derived from `results/per_unit.jsonl`,
`results/per_rep_scores.jsonl`, `results/wire/calls.jsonl`, `corpus/stimuli.jsonl`,
`labeling/labels.jsonl`, `profiles/profiles.yaml`, `corpus/census.json`, `corpus/manip/report.json`,
`labeling/v1_v2_confusion.json` and the frozen prompt sources, with independent implementations of
the exact signed-rank enumeration, the Hodges–Lehmann pseudomedian, the rank-biserial correlation,
the BCa bootstrap (registered seed and resample count), the power/size/coverage simulations and the
floor-censoring construction. Appendix A un-wrapped and compared byte-for-byte, plus a 990-call
prompt-hash reconstruction. All of §5's algebra re-derived by hand. All 12 frozen-input hashes
re-verified at open and at close. All 26 labels and 74 cross-references resolved and each checked
against its citing sentence. Every citation checked against the cited work.

**Could not check.** (i) The published side of the drift check (`3.879`, `r = 0.979`, `40 of 55`),
because the companion study's per-turn scores are not in this release (finding 1); I verified only
that our side is 3.890909 and that the comparison is impossible offline from what ships here.
(ii) Whether the D-arm request is byte-identical to the companion's logged request, for the same
reason; I verified instead that the D-arm user message is exactly the frozen template with no profile
block, which makes byte-identity constructive rather than observed. (iii) Appendix B's "one pair was
flagged as reversed on an earlier pass and repaired before the freeze": the released manipulation
report describes the final pass only (55/55, 0 reversed). (iv) Whether the six acid-mixture problems
are all in fact acid-mixture (I confirmed six distinct problem identifiers, not their content).

**Most likely to be wrong.** Finding 2. It rests on a reading of five cited audits' designs rather
than on this repository, and an author who has a specific within-item double-difference audit in mind
can refute it with one citation, which is also the cheapest fix. Finding 5 is next: the boundary
between "the registered per-field gap" and "its post-hoc per-pole split" is one a reader could argue
Table 3's caption already covers by saying status is per quantity, though the table then owes the
split a row. Finding 3's novelty exposure is a judgement about how much of contribution 1 survives
Wang & Li, not a factual error in the manuscript.

**Deliberately not reported.** The abstract's bare "is null" (the interval follows immediately, and
§1, §4.1 and §8 all state the failure-to-detect reading); Type 3 fonts in two figures and four
unreferenced labels (formatting, out of scope); the §5 pole means being stimulus-level rather than
clustered (the sentence says so); "still draw the low pole from a single tutor model" at `:104`
(24 of 27, given three lines below in Table 2). I also checked and cleared two claims that look
wrong and are not: "six reported here return the smallest $p$-value their nonzero-cluster count
admits" (six is right once figure-reported tests are counted, which is the same convention that makes
the companion "four" right), and "survives no correction at a family larger than four" (the sign test
on 10 positive of 11 nonzero clusters gives $p = 0.01172$; $0.05/4 = 0.0125$ passes and
$0.05/5 = 0.01$ fails).
