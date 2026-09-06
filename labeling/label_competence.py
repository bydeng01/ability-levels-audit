#!/usr/bin/env python3
"""Blind demonstrated-competence labelling over the frozen candidate contexts.

The tracker labels used at sampling time come from the tutor's own planner (same
model family as the judge) and cannot serve as analysis ground truth. This module
defines the frozen labelling rubric, prepares blind per-rep batches, and aggregates
three independent reps by majority vote.

Blindness: a labelling rep sees only the rubric and the dialogue contexts (rep-
specific shuffled order, rep-specific batch splits). Never the candidate's tutor
response, never the tracker record, never the policy/base/prior-stratum metadata.

Primary labelling path (decisions-log 2026-08-08): three independent blind passes
by fresh Claude (Fable 5) agent contexts driven by the build harness — per-rep
records are written to labeling/reps/rep{1,2,3}.jsonl and are auditable. The
`--backend api` path implements the build prompt's paid alternative (~2x96 short
calls through the vendored model client) and can be run as a robustness check;
it is not the primary source of labels.jsonl.

Subcommands:
  prepare    write labeling/batches/rep{r}_batch{b}.json (blind inputs, 3 reps x 3 batches)
  aggregate  majority-vote labeling/reps/rep{r}.jsonl -> labeling/labels.jsonl (+ sha256)
  api        run one labelling rep through the vendored model client (robustness path)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))

LAB = ROOT / "labeling"
SEED = 47100  # v2 (v1 used 47001; archived) — distinct per-rep shuffles from v1

# =====================================================================
# Labelling rubric v2, frozen before any judge call. v1 (archived verbatim in
# labeling/v1-archive/RUBRIC.v1.md with its complete per-rep labels) set the
# strong bar at "any correct step anywhere in the context", which mislabels
# prompted micro-steps, unrepaired current errors, and solution-parroting as
# strong (decisions-log 2026-08-08). v2 measures the study's construct:
# current-state demonstrated competence as of the latest student turn. One
# revision, disclosed, and never tuned after the v2 labels were produced.
# =====================================================================
LABEL_RUBRIC = """\
You are labelling the DEMONSTRATED, CURRENT-STATE COMPETENCE of a student in a
partial tutoring dialogue about one algebra word problem (mixture /
weighted-average setups).

You see the dialogue exactly as the student saw it, ending with the student's most
recent message. Judge ONLY what the student's own messages demonstrate, and judge
the student's CURRENT state as of their latest message. The question to answer is:
"based on what this dialogue shows, is this student currently able to drive the
next step of the solution themselves?"

For each item output three fields:

- "competence": "weak" or "strong"
    strong = the student is currently driving the solution: their most recent
             substantive work is correct (a correct equation setup, a correct
             algebraic step, or correct arithmetic they chose to do themselves),
             and nothing in their latest message signals they cannot continue.
             Independent correct work earlier in the dialogue counts only if the
             student has not since hit an impasse.
    weak   = the student currently depends on the tutor to move forward: they are
             stuck or say so, ask for the answer or for help, their most recent
             attempt contains an error they have not repaired, they only echo or
             agree with work the tutor produced, or their correct contributions
             are micro-steps performed exactly when and where the tutor directed
             (fill-in-the-blank compliance rather than self-directed solving).

    Boundary rules (apply them exactly):
      * One correct arithmetic evaluation done at the tutor's direct prompting
        (e.g. tutor asks "what is 0.20 times 48?" and the student answers) does
        NOT by itself make the student strong.
      * An early correct fragment does NOT make the student strong if the student
        then signals impasse (e.g. "but I'm stuck", "I'm not sure how to put this
        into an equation").
      * Parroting a solution the tutor revealed — restating its equation or
        answer, agreeing, thanking — is weak, however fluent it sounds.
      * A currently incorrect step (sign error, dropped term, wrong expansion)
        that the student has not repaired is weak, even if earlier steps were
        right.
      * A fully correct, self-directed setup or solve with no current impasse is
        strong even if the student sounds tentative while doing it.

- "evidence_strength": "ambiguous", "moderate", or "strong"
    How compelling is the behavioural evidence for your competence call?
    ambiguous = little to go on (e.g. a single short message, a bare "I'm not
                sure", no real attempt either way)
    moderate  = one clear signal (e.g. one incorrect setup, or one correct
                independent step)
    strong    = repeated or decisive signals (e.g. repeated failure of the same
                prerequisite even after help, or a fully correct independent
                setup carried through several steps)

- "confidence": "low", "medium", or "high" — your confidence in the competence call.

Judge each item independently. Do not try to balance the two labels across items —
the true mix is unknown to you and may be very uneven.
"""

COMP_VALS = ("weak", "strong")
EV_VALS = ("ambiguous", "moderate", "strong")
CONF_VALS = ("low", "medium", "high")
N_REPS = 3
N_BATCHES = 3


def _candidates() -> list[dict]:
    return [json.loads(l) for l in open(ROOT / "corpus/candidates.jsonl")]


def cmd_prepare(args):
    cands = _candidates()
    (LAB / "batches").mkdir(exist_ok=True)
    (LAB / "reps").mkdir(exist_ok=True)
    # The rubric is frozen (decisions-log 2026-08-08: "No further instrument
    # iteration"). Re-running prepare must never silently rewrite it
    # (AUDIT-2026-08-08 N-series): emit it only if absent, and refuse if the file on
    # disk differs from the module's text.
    rubric_path = LAB / "RUBRIC.md"
    if not rubric_path.exists():
        rubric_path.write_text(LABEL_RUBRIC)
    elif rubric_path.read_text() != LABEL_RUBRIC:
        raise SystemExit(
            f"FROZEN RUBRIC MISMATCH: {rubric_path} differs from LABEL_RUBRIC in "
            "label_competence.py. The labelling instrument is frozen; refusing to "
            "overwrite it. Reconcile deliberately if a revision is genuinely intended.")
    for rep in range(1, N_REPS + 1):
        order = list(cands)
        random.Random(SEED + rep).shuffle(order)
        per = (len(order) + N_BATCHES - 1) // N_BATCHES
        for b in range(N_BATCHES):
            chunk = order[b * per:(b + 1) * per]
            items = [{"candidate_id": c["candidate_id"], "context": c["context"]}
                     for c in chunk]
            (LAB / "batches" / f"rep{rep}_batch{b + 1}.json").write_text(
                json.dumps({"rubric": LABEL_RUBRIC, "items": items}, indent=1))
    print(f"prepared {N_REPS}x{N_BATCHES} blind batches over {len(cands)} candidates "
          f"(rep-specific order and splits); rubric frozen at labeling/RUBRIC.md")


def _validate_row(row: dict, known_ids: set[str]) -> dict:
    assert row["candidate_id"] in known_ids, f"unknown id {row['candidate_id']}"
    assert row["competence"] in COMP_VALS, row
    assert row["evidence_strength"] in EV_VALS, row
    assert row["confidence"] in CONF_VALS, row
    return {k: row[k] for k in ("candidate_id", "competence", "evidence_strength",
                                "confidence")}


def cmd_aggregate(args):
    cands = _candidates()
    known = {c["candidate_id"] for c in cands}
    reps: list[dict[str, dict]] = []
    for rep in range(1, N_REPS + 1):
        path = LAB / "reps" / f"rep{rep}.jsonl"
        rows = [_validate_row(json.loads(l), known) for l in open(path) if l.strip()]
        by_id = {r["candidate_id"]: r for r in rows}
        assert len(by_id) == len(known), (
            f"rep{rep}: {len(by_id)} unique labels for {len(known)} candidates")
        reps.append(by_id)

    ev_ord = {v: i for i, v in enumerate(EV_VALS)}
    out, n_dropped = [], 0
    for c in sorted(cands, key=lambda c: c["candidate_id"]):
        cid = c["candidate_id"]
        votes = [reps[i][cid] for i in range(N_REPS)]
        comp_counts = Counter(v["competence"] for v in votes)
        top, n_top = comp_counts.most_common(1)[0]
        # Note (AUDIT-2026-08-08 B4): with N_REPS == 3 and a binary competence label,
        # n_top is 2 or 3 by pigeonhole, so `agreement_ok` is structurally always True
        # and `n_dropped` is structurally always 0. The field is retained because the
        # released labels.jsonl carries it, but it is not a reliability statistic and
        # must not be reported as one ("0 items dropped for <2/3 agreement" is a
        # tautology rather than a finding). The reliability evidence is the unanimity rate and
        # the pairwise inter-rep agreement printed below. A gate that can actually fail
        # would need either an "unclear" option in COMP_VALS or an even rep count.
        agreement_ok = n_top >= 2
        if not agreement_ok:
            n_dropped += 1
        # evidence strength: median of the three ordinal votes
        ev_sorted = sorted(votes, key=lambda v: ev_ord[v["evidence_strength"]])
        out.append({
            "candidate_id": cid,
            "competence": top if agreement_ok else None,
            "agreement_ok": agreement_ok,
            "unanimous": n_top == N_REPS,
            "evidence_strength": ev_sorted[1]["evidence_strength"],
            "confidences": [v["confidence"] for v in votes],
            "per_rep": votes,
        })
    with open(LAB / "labels.jsonl", "w") as f:
        for r in out:
            f.write(json.dumps(r) + "\n")
    sha = hashlib.sha256((LAB / "labels.jsonl").read_bytes()).hexdigest()
    (LAB / "labels.sha256").write_text(f"{sha}  labels.jsonl\n")

    kept = [r for r in out if r["agreement_ok"]]
    comp = Counter(r["competence"] for r in kept)
    ev = Counter(r["evidence_strength"] for r in kept)
    unan = sum(1 for r in kept if r["unanimous"])
    print(f"labels: {len(out)} candidates, {n_dropped} dropped "
          f"(<2/3 agreement — NOTE: structurally always 0, see cmd_aggregate; "
          f"not a reliability statistic)")
    print(f"  competence: {dict(comp)}  (unanimous: {unan}/{len(kept)})")
    print(f"  evidence_strength: {dict(ev)}")
    # Real reliability evidence: pairwise agreement between the independent reps.
    for i in range(N_REPS):
        for j in range(i + 1, N_REPS):
            same = sum(1 for c in cands
                       if reps[i][c["candidate_id"]]["competence"]
                       == reps[j][c["candidate_id"]]["competence"])
            print(f"  inter-rep competence agreement rep{i + 1}/rep{j + 1}: "
                  f"{same}/{len(cands)} ({same / len(cands):.1%})")
    prior = {c["candidate_id"]: c["prior_stratum"] for c in cands}
    match = sum(1 for r in kept if r["competence"] == prior[r["candidate_id"]])
    print(f"  agreement with sampling prior: {match}/{len(kept)} "
          f"(prior was a sampling aid only; disagreement is expected and fine)")
    print("wrote labeling/labels.jsonl (+ .sha256)")


def cmd_api(args):
    """Robustness path: one labelling rep through the vendored model client."""
    from agents.config import load_models_config, resolve_backend
    from agents.model_client import ModelClient

    cfg = load_models_config(str(ROOT / "vendor/configs/models.yaml"))
    client = ModelClient(models_cfg=cfg, backend=resolve_backend(cfg, args.backend))
    cands = _candidates()
    order = list(cands)
    random.Random(SEED + args.rep).shuffle(order)
    out_path = LAB / "reps" / f"api_rep{args.rep}.jsonl"
    with open(out_path, "w") as f:
        for c in order:
            user = (LABEL_RUBRIC + "\nDIALOGUE:\n\"\"\"\n" + c["context"] + "\n\"\"\"\n\n"
                    'Reply with ONLY the JSON object: {"competence": "...", '
                    '"evidence_strength": "...", "confidence": "..."}')
            comp = client.complete(role="judge", system="You are a careful annotator.",
                                   messages=[{"role": "user", "content": user}],
                                   seed=SEED + args.rep,
                                   tags={"component": "competence_labeller"})
            import re
            m = re.search(r"\{.*\}", comp.text, re.DOTALL)
            row = json.loads(m.group(0)) if m else {}
            row["candidate_id"] = c["candidate_id"]
            f.write(json.dumps(row) + "\n")
    print(f"wrote {out_path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cmd", choices=["prepare", "aggregate", "api"])
    ap.add_argument("--rep", type=int, default=1)
    ap.add_argument("--backend", default=None)
    args = ap.parse_args()
    return {"prepare": cmd_prepare, "aggregate": cmd_aggregate,
            "api": cmd_api}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
