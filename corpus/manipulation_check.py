#!/usr/bin/env python3
"""Blind manipulation check on the R_H / R_L contrast (pre-freeze).

The study's Δ = S(R_H) − S(R_L) is only meaningful if the two poles really do
differ in scaffolding level. This check verifies that independently of the judge
and of the profile manipulation: a blind rater sees the dialogue context and the
two responses in a RANDOMISED, unlabelled order and says which one leaves more of
the next reasoning step to the student.

It is a validity report, not a selection step — no stimulus is dropped on the
basis of a judge score, and no judge call exists yet. A pair the raters call
REVERSED is a construction defect and is repaired before freeze.

  prepare  -> corpus/manip/batch{n}.json   (blind, order-randomised)
  score    -> corpus/manip/report.json     (agreement + any reversed/tied pairs)
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus"
MANIP = CORPUS / "manip"
SEED = 5150

BRIEF = """\
For each item you see a tutoring DIALOGUE CONTEXT ending with the student's latest
message, and two alternative tutor replies, "A" and "B", in arbitrary order.

Answer one question per item: which reply leaves MORE of the next reasoning step
for the student to do themselves, rather than performing that step for them?

- A reply that hints, points at what to consider, or asks the student to produce
  the next expression/step LEAVES MORE to the student.
- A reply that states the next result, works the algebra, or gives the answer
  PERFORMS the step.

Judge only these two replies against each other. Ignore tone, length, formatting,
and politeness; ignore whether the mathematics is correct.

Output JSON Lines, one object per item, no commentary:
{"item_id": "M##", "leaves_more_to_student": "A"|"B"|"tie", "confidence": "low"|"medium"|"high"}
"""


def cmd_prepare(args):
    pairs = {r["candidate_id"]: r
             for r in (json.loads(l) for l in open(CORPUS / "pairing_draft.jsonl"))}
    cands = {c["candidate_id"]: c
             for c in (json.loads(l) for l in open(CORPUS / "candidates.jsonl"))}
    rng = random.Random(SEED)
    MANIP.mkdir(exist_ok=True)

    items, key = [], {}
    for i, (cid, p) in enumerate(sorted(pairs.items()), 1):
        item_id = f"M{i:02d}"
        swap = rng.random() < 0.5          # randomise which pole is shown as "A"
        a, b = (p["r_low"], p["r_high"]) if swap else (p["r_high"], p["r_low"])
        key[item_id] = {"candidate_id": cid, "high_is": "B" if swap else "A"}
        items.append({"item_id": item_id, "context": cands[cid]["context"],
                      "A": a["text"], "B": b["text"]})
    rng.shuffle(items)

    per = 30
    n = 0
    for b in range(0, len(items), per):
        n += 1
        (MANIP / f"batch{n}.json").write_text(
            json.dumps({"instructions": BRIEF, "items": items[b:b + per]}, indent=1))
    (MANIP / "_key.json").write_text(json.dumps(key, indent=1))
    print(f"wrote {n} blind batches over {len(items)} pairs "
          f"(A/B order randomised, seed {SEED})")


def cmd_score(args):
    key = json.loads((MANIP / "_key.json").read_text())
    got = {}
    for p in sorted(MANIP.glob("resp*.jsonl")):
        for line in p.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                got[r["item_id"]] = r
    missing = sorted(set(key) - set(got))
    assert not missing, f"no manipulation-check response for: {missing}"

    correct, reversed_, tied = [], [], []
    for item_id, k in key.items():
        pick = got[item_id]["leaves_more_to_student"]
        cid = k["candidate_id"]
        if pick == "tie":
            tied.append(cid)
        elif pick == k["high_is"]:
            correct.append(cid)
        else:
            reversed_.append(cid)

    n = len(key)
    report = {
        "n_pairs": n,
        "n_correct": len(correct), "n_reversed": len(reversed_), "n_tied": len(tied),
        "agreement_rate": round(len(correct) / n, 4),
        "reversed_stimuli": sorted(reversed_), "tied_stimuli": sorted(tied),
        "note": "blind, order-randomised; validates that R_H leaves more of the next "
                "reasoning step to the student than R_L. Not a selection step.",
    }
    (MANIP / "report.json").write_text(json.dumps(report, indent=2))
    print(f"manipulation check: {len(correct)}/{n} correct "
          f"({report['agreement_rate']:.1%}), {len(reversed_)} reversed, "
          f"{len(tied)} tied")
    if reversed_:
        print(f"  REVERSED (repair before freeze): {sorted(reversed_)}")
    if tied:
        print(f"  TIED (inspect): {sorted(tied)}")
    print("wrote corpus/manip/report.json")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cmd", choices=["prepare", "score"])
    args = ap.parse_args()
    return {"prepare": cmd_prepare, "score": cmd_score}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
