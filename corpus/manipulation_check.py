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
  prune    -> remove ratings for pairs excluded pre-data, preserving all other raw votes
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

Three surface features in particular must NOT decide your answer — in this material
they correlate with the poles, so relying on them would tell us nothing (see
AUDIT-2026-08-08 N1):

- **Question marks.** A reply can hand the next step to the student without asking a
  question (an imperative "now find the total volume" does), and a reply can ask a
  question while still having performed the step ("...so x = 25. Make sense?").
- **LaTeX, \\boxed{}, display math, bullet lists** and any other formatting.
- **Which reply is longer.**

Ask only: after reading this reply, is there still a reasoning step the student has
to produce themselves, or has the reply already produced it? If both replies leave
the same amount of work to the student, answer "tie" — do not guess from surface form.

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
    got, source = {}, {}
    # AUDIT-2026-08-08 N1: this loop used to be silent last-file-wins. A duplicate
    # item_id in a later resp*.jsonl would quietly replace an earlier rating — a
    # re-rating is a selection step and must never happen invisibly. Extras and
    # malformed picks were also ignored.
    for p in sorted(MANIP.glob("resp*.jsonl")):
        for line in p.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            iid = r["item_id"]
            if iid in got:
                raise SystemExit(
                    f"DUPLICATE RATING for {iid}: {source[iid]} and {p.name}. A "
                    "re-rating is a silent selection step; resolve it deliberately.")
            if r.get("leaves_more_to_student") not in ("A", "B", "tie"):
                raise SystemExit(
                    f"{p.name}: {iid} has an invalid verdict "
                    f"{r.get('leaves_more_to_student')!r}")
            got[iid], source[iid] = r, p.name
    missing = sorted(set(key) - set(got))
    assert not missing, f"no manipulation-check response for: {missing}"
    extra = sorted(set(got) - set(key))
    assert not extra, f"ratings for items that are not in the key: {extra}"

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
        "n_ratings_consumed": len(got),
        "n_correct": len(correct), "n_reversed": len(reversed_), "n_tied": len(tied),
        # NOT inter-rater reliability: each pair is rated ONCE, so this is agreement
        # with the construction key, i.e. "did the rater recover the pole the pairing
        # review assigned" (AUDIT-2026-08-08 N1). Report it as such.
        "key_agreement_rate": round(len(correct) / n, 4),
        "n_raters_per_pair": 1,
        "reversed_stimuli": sorted(reversed_), "tied_stimuli": sorted(tied),
        "response_files": sorted(set(source.values())),
        "per_item": {iid: {"candidate_id": key[iid]["candidate_id"],
                           "high_is": key[iid]["high_is"],
                           "pick": got[iid]["leaves_more_to_student"],
                           "confidence": got[iid].get("confidence"),
                           "source": source[iid]}
                     for iid in sorted(key)},
        "note": "blind, order-randomised, one rating per pair; checks that R_H leaves "
                "more of the next reasoning step to the student than R_L. Not a "
                "selection step, and not an inter-rater reliability statistic. The "
                "brief explicitly forbids deciding on question marks, formatting or "
                "length, which correlate with the poles in this material.",
    }
    (MANIP / "report.json").write_text(json.dumps(report, indent=2))
    print(f"manipulation check: {len(correct)}/{n} correct "
          f"({report['key_agreement_rate']:.1%} key agreement, 1 rater/pair), "
          f"{len(reversed_)} reversed, "
          f"{len(tied)} tied")
    if reversed_:
        print(f"  REVERSED (repair before freeze): {sorted(reversed_)}")
    if tied:
        print(f"  TIED (inspect): {sorted(tied)}")
    print("wrote corpus/manip/report.json")
    return 0


def cmd_prune(args):
    """Remove only candidates absent from the current pre-data pairing draft.

    This preserves the original blinded A/B assignment, item id, batch placement, and
    raw verdict for every retained pair. It is used when a material is excluded before
    scoring; it never creates or changes a rating.
    """
    selected = {json.loads(line)["candidate_id"]
                for line in (CORPUS / "pairing_draft.jsonl").read_text().splitlines()
                if line.strip()}
    key_path = MANIP / "_key.json"
    key = json.loads(key_path.read_text())
    dropped_ids = {iid for iid, row in key.items()
                   if row["candidate_id"] not in selected}
    dropped_candidates = sorted(key[iid]["candidate_id"] for iid in dropped_ids)
    kept_key = {iid: row for iid, row in key.items() if iid not in dropped_ids}
    key_path.write_text(json.dumps(kept_key, indent=1))

    for path in sorted(MANIP.glob("batch*.json")):
        blob = json.loads(path.read_text())
        blob["items"] = [row for row in blob["items"]
                         if row["item_id"] not in dropped_ids]
        path.write_text(json.dumps(blob, indent=1))
    for path in sorted(MANIP.glob("resp*.jsonl")):
        rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        rows = [row for row in rows if row["item_id"] not in dropped_ids]
        path.write_text("".join(json.dumps(row) + "\n" for row in rows))

    remaining = {row["candidate_id"] for row in kept_key.values()}
    if remaining != selected:
        raise SystemExit(
            f"manipulation assignments do not cover current pairs: "
            f"missing={sorted(selected - remaining)} extra={sorted(remaining - selected)}")
    print(f"pruned {dropped_candidates}; preserved {len(kept_key)} blinded ratings")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cmd", choices=["prepare", "prune", "score"])
    args = ap.parse_args()
    return {"prepare": cmd_prepare, "prune": cmd_prune,
            "score": cmd_score}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
