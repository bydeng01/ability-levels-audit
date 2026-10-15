# Protocol and review evidence

[PREREGISTRATION.md](PREREGISTRATION.md) is the unchanged pre-run protocol bound
by `results/frozen_inputs.sha256`. The [decisions log](decisions-log.md) records
design amendments, exclusions and post-run corrections. For the current paper
and offline commands, start with the [repository README](../README.md).

## Record conventions

The reviews below are edited public excerpts. They retain scientific findings,
supporting checks, reviewer attribution and coverage limits. Operator handoffs,
credential status, manuscript revision instructions and literature-positioning
notes have been removed. The original records are preserved at repository commit
`9ba8d6039f84ac57e02623ffe83aa34778d7d400` and in a local recovery archive excluded
from Git and Docker builds.

Dates, finding IDs, first-person verification statements and file/line citations
refer to the original review. They do not certify the current checkout or paper.
Some citations name superseded files, including the pre-run abstract template,
which is no longer part of the public file tree. The reviews' scientific findings
remain at their original paths because the frozen protocol and code cite them.

Earlier reviews contain conclusions corrected by later ones. In particular, the
post-run review corrects A6's claim that censoring cannot manufacture a difference
in differences. Self-reported fixes remain distinguished from separate checks;
the `[V]` and `[W]` markers retain their original verification scope. No reviewer
identity or independence is inferred from missing metadata. The disclosed
Claude-family labelling process and its unverified process claims are retained.

| Record | Evidence retained |
|---|---|
| [First pre-flight review, August 8](AUDIT-2026-08-08.md) | Reconstruction, material exclusions, inference, provenance and remediation checks. |
| [Second pre-flight review, August 8](AUDIT-2026-08-08-independent-review.md) | Findings on the intermediate 56-stimulus version and explicit coverage gaps. |
| [Third pre-flight review, August 8](AUDIT-2026-08-08-preflight-review-3.md) | Instrument and interpretation findings, mutation checks, and self-reported remediation. |
| [Endpoint sensitivity, August 10](AUDIT-2026-08-10-endpoint-sensitivity.md) | Censoring, endpoint interpretation, usage accounting and integrity checks. |
| [Post-A6 verification, August 10](AUDIT-2026-08-10-post-a6-reverification.md) | Pre-run checks of Amendment A6 and its code fixes at `c297d22`. |
| [Post-run interpretation, August 10](AUDIT-2026-08-10-post-run-interpretation.md) | Interpretation limits, including values adopted from other reviews without direct recomputation. |
| [Released-artifact checks, August 18](AUDIT-2026-08-18-manuscript-correctness.md) | Numerical and mathematical checks, discrepancies and unavailable companion data. |

Candidate pools, selection snapshots, blind batches, review decisions, earlier
labels and raw request/response logs remain in `corpus/`, `labeling/` and
`results/`. They document how the released materials and scores were obtained.
Current offline reproduction uses these artifacts and does not require the local
recovery archive. Paid-run requirements are documented in the
[original run workflow](../judging/README.md).
