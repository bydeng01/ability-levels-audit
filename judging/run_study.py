#!/usr/bin/env python3
"""The paid runner for the label-vs-evidence judge study.

Control surface modeled on $SRC/analysis/run_cross_judge_audit.py (reimplemented,
not vendored). All output lives under results/ (enforced). Modes:

  --manifest-only       OFFLINE. input_manifest.jsonl + plan.json + frozen_inputs.sha256.
  --preflight           TWO synthetic, non-study calls (one D-arm, one profile-arm)
                        through the real instrument. Resolves and freezes the transport
                        contract -> results/preflight/resolved_config.json. Refuses to
                        freeze on any contract violation.
  (default: paid)       the full 1,080-call pass. Requires a completed preflight whose
                        contract_sha256 still matches the frozen inputs. Promotes final
                        outputs only when EVERY unit has n_valid == 3 (transactional).
  --pilot N             run only the first N schedule calls (shared cache, real spend,
                        no promotion). Writes results/pilot_report.json.
  --offline-cache-only  reconstruct finals from the released per-rep cache. ANY cache
                        miss aborts. No provider call, no synthetic score.
  --judge-backend mock  full pipeline, deterministic synthetic scores, no key. Uses a
                        separate cache namespace. NEVER reportable.

Guardrails:
  - CUMULATIVE dollar spend ledger (results/spend_ledger.json), persisted around every
    provider request: a conservative worst-case pre-charge before the request, settled
    to actual usage-derived cost after. Hard cap via --cap (default $40), lifetime
    across invocations; a crash leaves the pre-charge committed (conservative).
    Dollar accounting is per BILLED request: transport retries that fail bill nothing
    and settle to $0; a billed-but-degraded response still settles at its real cost.
  - Quality circuit breaker: after a warmup of responses, abort if the usable-rating
    rate falls below the floor (systematic failure, not noise).
  - Per-call served-model check against the model identity FROZEN at preflight; abort
    on drift.
  - Degraded/truncated responses (no text, stop_reason != end_turn, missing usage) are
    REFUSED, never parsed into a score; the rep is retried on a fresh request.
  - Transactional promotion: finals are built in a staging dir and os.replace'd into
    results/ only after the completeness gate passes; run_state.json flips LAST.
  - Run lock: one scoring invocation per repo at a time.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT))

from analysis import judge_pedagogy as JP          # noqa: E402  vendored, frozen
from agents.config import load_models_config       # noqa: E402  vendored
from agents.model_client import ModelClient        # noqa: E402  vendored
from judging import profile_judge as PJ            # noqa: E402

RESULTS = ROOT / "results"
CAP_DEFAULT_USD = 40.0
# claude-opus-4-8 first-party pricing (USD per token).
PRICE_IN = 5.00 / 1e6
PRICE_OUT = 25.00 / 1e6
# Conservative pre-charge: generous input bound + the full max_tokens output.
WORST_CASE_IN_TOKENS = 4000
MAX_ATTEMPTS_PER_REP = 4
BREAKER_WARMUP = 12
BREAKER_MIN_ACCEPT = 0.5
CACHE_FLUSH_EVERY = 20

FINAL_NAMES = ("per_rep_scores.jsonl", "per_unit.jsonl", "completeness.json",
               "run_meta.json")

# Synthetic preflight dialogue — deliberately NOT study material (no mixture/percent
# problem, none of the frozen problem set's numbers as an answer).
PREFLIGHT_STIMULUS = {
    "stimulus_id": "PREFLIGHT", "context":
        "Student: I keep mixing up how to double a recipe that needs 3/4 cup of "
        "flour. Is it 6/4?\n\n"
        "Tutor: You're on the right track with the idea of doubling the numerator. "
        "What is 6/4 as a mixed number?\n\n"
        "Student: Um, 6/4 is... one and a half cups? I think I divided right but "
        "I'm not sure.",
    "r_high": "You did divide right. Can you explain how you got from 6/4 to one "
              "and a half, step by step?",
    "r_low": "Yes: 6/4 = 1.5, so use one and a half cups of flour. That's the answer.",
}


def now_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write_json(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(f"tmp.{os.getpid()}.{p.name}")
    tmp.write_text(json.dumps(obj, indent=2))
    os.replace(tmp, p)


def judge_spec() -> dict:
    cfg = load_models_config(str(ROOT / "vendor/configs/models.yaml"))
    spec = cfg["roles"]["judge"]
    assert spec.get("provider", cfg.get("provider")) == "anthropic", spec
    assert spec["model"] == "claude-opus-4-8", spec
    assert spec.get("temperature") is None, "judge temperature must be omitted"
    return {"cfg": cfg, "spec": spec}


def worst_case_call_usd(spec: dict) -> float:
    return WORST_CASE_IN_TOKENS * PRICE_IN + spec.get("max_tokens", 512) * PRICE_OUT


# ---------------------------------------------------------------- spend ledger
class SpendLedger:
    """Cumulative dollar ledger, persisted on every state change, fail-closed."""

    def __init__(self, path: Path, cap_usd: float, backend: str):
        self.path = path
        self.cap = float(cap_usd)
        self.backend = backend
        self.settled = 0.0      # billed dollars, current backend regime
        self.committed = 0.0    # outstanding pre-charges (crash leaves them counted)
        self.invocations = []
        self._this = {"pid": os.getpid(), "utc": now_utc(), "backend": backend,
                      "settled_usd": 0.0, "committed_usd": 0.0, "requests": 0}
        self._load()

    def _corrupt(self, why: str):
        raise SystemExit(
            f"SPEND LEDGER CORRUPT: {self.path} {why}. An untrusted ledger must not "
            "be read as zero prior spend. Refusing to run. Recover the true figure "
            "from results/wire/calls.jsonl (sum cost_usd) and rewrite the ledger "
            "deliberately, over-stating if unsure.")

    def _load(self):
        if not self.path.exists():
            wire = RESULTS / "wire" / "calls.jsonl"
            if self.backend == "live" and wire.exists() and any(
                    json.loads(l).get("backend") == "live"
                    for l in wire.read_text().splitlines() if l.strip()):
                raise SystemExit(
                    "SPEND LEDGER MISSING beside a wire log with LIVE requests. "
                    "Refusing to run with a fresh allowance; reconstruct the ledger "
                    "from the wire log's cost_usd column first.")
            return
        try:
            blob = json.loads(self.path.read_text())
        except Exception as e:  # noqa: BLE001
            self._corrupt(f"is unreadable ({e})")
        if not isinstance(blob, dict) or not isinstance(blob.get("invocations"), list):
            self._corrupt("has the wrong shape")
        s = c = 0.0
        for inv in blob["invocations"]:
            if not isinstance(inv.get("settled_usd"), (int, float)) or inv["settled_usd"] < 0:
                self._corrupt("holds a non-numeric settled_usd")
            if inv.get("backend") == self.backend:
                s += inv["settled_usd"]
                c += max(0.0, inv.get("committed_usd", 0.0))
        if abs(sum(i["settled_usd"] for i in blob["invocations"])
               - blob.get("settled_usd_total", -1)) > 1e-6:
            self._corrupt("is internally inconsistent (totals != sum of invocations)")
        self.settled, self.committed = s, c
        self.invocations = blob["invocations"]

    def _persist(self):
        allrows = [*self.invocations, self._this]
        write_json(self.path, {
            "cap_usd_current_backend": self.cap,
            "settled_usd_total": round(sum(i["settled_usd"] for i in allrows), 6),
            "note": "CUMULATIVE across invocations; rows labeled by backend (mock "
                    "rehearsals never consume the live allowance). committed_usd is "
                    "a crash-conservative outstanding pre-charge.",
            "invocations": allrows,
        })

    def charge(self, worst_case_usd: float, where: str):
        projected = (self.settled + self.committed + self._this["settled_usd"]
                     + self._this["committed_usd"] + worst_case_usd)
        if projected > self.cap:
            raise SystemExit(
                f"SPEND CAP: issuing another request could bring lifetime {self.backend} "
                f"spend to ${projected:.2f} > cap ${self.cap:.2f} ({where}). Stopping "
                "BEFORE the request. The per-rep cache keeps everything already scored; "
                "re-running with a deliberately raised --cap pays only for what is "
                "missing.")
        self._this["committed_usd"] += worst_case_usd
        self._this["requests"] += 1
        self._persist()

    def settle(self, worst_case_usd: float, actual_usd: float):
        self._this["committed_usd"] -= worst_case_usd
        self._this["settled_usd"] += actual_usd
        self._persist()

    def summary(self) -> dict:
        return {"cap_usd": self.cap, "backend": self.backend,
                "prior_settled_usd": round(self.settled, 4),
                "this_run_settled_usd": round(self._this["settled_usd"], 4),
                "lifetime_settled_usd": round(self.settled + self._this["settled_usd"], 4),
                "outstanding_committed_usd": round(self.committed + self._this["committed_usd"], 4),
                "requests_this_run": self._this["requests"]}


class Breaker:
    def __init__(self):
        self.responses = 0
        self.accepted = 0

    def record(self, ok: bool, where: str):
        self.responses += 1
        self.accepted += ok
        if self.responses >= BREAKER_WARMUP:
            rate = self.accepted / self.responses
            if rate < BREAKER_MIN_ACCEPT:
                raise SystemExit(
                    f"CIRCUIT BREAKER: {self.accepted}/{self.responses} responses "
                    f"({rate:.0%}) usable, below {BREAKER_MIN_ACCEPT:.0%} ({where}). "
                    "Systematic failure — inspect results/wire/calls.jsonl before "
                    "spending more.")


# ---------------------------------------------------------------- backends
class LiveCaller:
    def __init__(self, cfg: dict):
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise SystemExit("live mode needs ANTHROPIC_API_KEY in the environment")
        self.client = ModelClient(models_cfg=cfg, backend="live", logger=None)

    def call(self, system: str, user: str, seed: int) -> dict:
        comp = self.client.complete(role="judge", system=system,
                                    messages=[{"role": "user", "content": user}],
                                    seed=seed)
        raw = comp.raw_response or {}
        return {"text": comp.text,
                "served_model": raw.get("model"),
                "stop_reason": raw.get("stop_reason"),
                "in_tokens": comp.input_tokens, "out_tokens": comp.output_tokens}


class MockCaller:
    """Deterministic pedagogy-shaped scores; malformed on the first attempt for a
    small slice of keys so the retry path is exercised end-to-end."""

    def __init__(self, spec: dict):
        self.model = spec["model"]

    def call_key(self, key: str, attempt: int) -> dict:
        h = hashlib.sha256(f"{key}|scores".encode()).digest()
        if h[9] % 25 == 0 and attempt == 1:
            text = "I think the scaffolding here is decent but let me hedge."  # unparseable
        else:
            vals = [1 + h[i] % 5 for i in range(5)]
            text = json.dumps(dict(zip(JP.FIELDS, vals)))
        return {"text": text, "served_model": self.model, "stop_reason": "end_turn",
                "in_tokens": 1700, "out_tokens": 52}


def degraded_reason(res: dict) -> str | None:
    if not (res.get("text") or "").strip():
        return "empty response text"
    if res.get("stop_reason") != "end_turn":
        return f"stop_reason={res.get('stop_reason')!r} (truncated/degraded)"
    if not res.get("in_tokens") or res.get("out_tokens") is None:
        return "missing usage accounting"
    return None


# ---------------------------------------------------------------- cache
class RepCache:
    def __init__(self, path: Path, stamp: dict):
        self.path = path
        self.stamp = stamp
        self.entries: dict = {}
        self._dirty = 0
        if path.exists():
            blob = json.loads(path.read_text())
            if blob.get("stamp") != stamp:
                raise SystemExit(
                    f"CACHE STAMP MISMATCH: {path} was written under a different "
                    "frozen contract. Refusing to mix ratings across contracts. "
                    "Move the old cache aside deliberately if it is superseded.")
            self.entries = blob["entries"]

    def flush(self):
        write_json(self.path, {"stamp": self.stamp, "entries": self.entries})
        self._dirty = 0

    def put(self, key: str, rec: dict):
        self.entries[key] = rec
        self._dirty += 1
        if self._dirty >= CACHE_FLUSH_EVERY:
            self.flush()


# ---------------------------------------------------------------- wire log
def wire_write(rec: dict):
    p = RESULTS / "wire" / "calls.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a") as f:
        f.write(json.dumps(rec) + "\n")


# ---------------------------------------------------------------- run lock / promotion
@contextlib.contextmanager
def run_lock():
    import fcntl
    RESULTS.mkdir(exist_ok=True)
    handle = open(RESULTS / "tmp.lock.run", "w")
    try:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise SystemExit("another run_study invocation holds the run lock; "
                             "concurrent runs would duplicate paid calls.")
        handle.write(f"{os.getpid()} {now_utc()}\n")
        handle.flush()
        yield
    finally:
        with contextlib.suppress(Exception):
            fcntl.flock(handle, fcntl.LOCK_UN)
        handle.close()


def mark_state(state: str, payload: dict):
    write_json(RESULTS / "run_state.json", {"state": state, "timestamp_utc": now_utc(),
                                            **payload})


def promote(staging: Path, payload: dict):
    import shutil
    missing = [n for n in FINAL_NAMES if not (staging / n).is_file()]
    if missing:
        raise SystemExit(f"refusing to promote an incomplete set: missing {missing}")
    for n in FINAL_NAMES:
        os.replace(staging / n, RESULTS / n)
    mark_state("complete", payload)
    shutil.rmtree(staging, ignore_errors=True)


# ---------------------------------------------------------------- frozen inputs
def frozen_inputs() -> dict:
    return {
        "stimuli_sha256": (ROOT / "corpus/stimuli.sha256").read_text().split()[0],
        "labels_sha256": (ROOT / "labeling/labels.sha256").read_text().split()[0],
        "profiles_yaml_sha256": sha_file(ROOT / "profiles/profiles.yaml"),
        "models_yaml_sha256": sha_file(ROOT / "vendor/configs/models.yaml"),
        "judge_pedagogy_py_sha256": sha_file(ROOT / "vendor/analysis/judge_pedagogy.py"),
        "profile_judge_py_sha256": sha_file(ROOT / "judging/profile_judge.py"),
        "rubric_md_sha256": sha_file(ROOT / "vendor/supplement/judge_pedagogy_rubric.md"),
    }


# ---------------------------------------------------------------- modes
def mode_manifest(spec: dict):
    stimuli = PJ.load_stimuli()
    profiles = PJ.load_profiles()
    units = [(s["stimulus_id"], arm, pole)
             for s in stimuli for arm in PJ.ARMS for pole in PJ.POLES]
    with open(RESULTS / "input_manifest.jsonl", "w") as f:
        for s in stimuli:
            for arm in PJ.ARMS:
                for pole in PJ.POLES:
                    user = PJ.build_user(s, arm, pole, profiles)
                    PJ.assert_prompt_pure(user, arm, profiles)
                    f.write(json.dumps({
                        "stimulus_id": s["stimulus_id"], "arm": arm, "pole": pole,
                        "user_sha256": hashlib.sha256(user.encode()).hexdigest(),
                        "user_chars": len(user)}) + "\n")
    est_in = 1640 + 95 * 2 / 3          # measured pedjudge basis + profile block share
    n_calls = len(units) * PJ.REPS
    plan = {
        "design": "60 stimuli x 3 arms x 2 poles x 3 reps",
        "n_stimuli": len(stimuli), "n_units": len(units), "reps": PJ.REPS,
        "n_calls_planned": n_calls,
        "judge_model": spec["spec"]["model"],
        "est_cost_usd": round(n_calls * (est_in * PRICE_IN + 52 * PRICE_OUT), 2),
        "worst_case_cost_usd": round(n_calls * worst_case_call_usd(spec["spec"]), 2),
        "contract_sha256": PJ.contract_sha256(spec["spec"]),
        "frozen_inputs": frozen_inputs(),
        "note": "the ~814-token system prompt is below claude-opus-4-8's 1024-token "
                "prompt-cache minimum, so no cache discount is assumed",
    }
    write_json(RESULTS / "plan.json", plan)
    with open(RESULTS / "frozen_inputs.sha256", "w") as f:
        for k, v in sorted(frozen_inputs().items()):
            f.write(f"{v}  {k}\n")
    print(f"manifest: {len(units)} units, {n_calls} calls planned, "
          f"est ${plan['est_cost_usd']}, worst-case ${plan['worst_case_cost_usd']}")


def _attempt_rep(key, system, user, seed, caller, backend, ledger, breaker, spec,
                 frozen_model):
    wc = worst_case_call_usd(spec)
    for attempt in range(1, MAX_ATTEMPTS_PER_REP + 1):
        ledger.charge(wc, where=key)
        t0 = time.time()
        if backend == "mock":
            res = caller.call_key(key, attempt)
        else:
            res = caller.call(system, user, seed=seed)
        cost = res["in_tokens"] * PRICE_IN + res["out_tokens"] * PRICE_OUT
        ledger.settle(wc, cost if backend == "live" else 0.0)
        deg = degraded_reason(res)
        scores = None if deg else JP.parse_pedagogy_scores(res["text"])
        ok = scores is not None
        wire_write({"key": key, "attempt": attempt, "backend": backend,
                    "served_model": res["served_model"], "stop_reason": res["stop_reason"],
                    "in_tokens": res["in_tokens"], "out_tokens": res["out_tokens"],
                    "cost_usd": round(cost, 6) if backend == "live" else 0.0,
                    "degraded": deg, "parsed_ok": ok,
                    "response_text": res["text"][:2000],
                    "user_sha256": hashlib.sha256(user.encode()).hexdigest(),
                    "latency_s": round(time.time() - t0, 2), "utc": now_utc()})
        if frozen_model is not None and res["served_model"] != frozen_model:
            raise SystemExit(
                f"SERVED-MODEL DRIFT: preflight froze {frozen_model!r} but this call "
                f"was served by {res['served_model']!r}. Aborting before another call.")
        breaker.record(ok, where=key)
        if ok:
            return {"scores": scores, "served_model": res["served_model"],
                    "usage": {"in": res["in_tokens"], "out": res["out_tokens"]},
                    "attempts": attempt, "utc": now_utc()}
    return None


def mode_preflight(spec: dict, backend: str, cap: float):
    profiles = PJ.load_profiles()
    system = PJ.build_system()
    ledger = SpendLedger(RESULTS / "spend_ledger.json", cap, backend)
    caller = (MockCaller(spec["spec"]) if backend == "mock" else LiveCaller(spec["cfg"]))
    records, served = [], set()
    for arm in ("D", "P_nov"):
        user = PJ.build_user(PREFLIGHT_STIMULUS, arm, "high", profiles)
        PJ.assert_prompt_pure(user, arm, profiles)
        wc = worst_case_call_usd(spec["spec"])
        ledger.charge(wc, where=f"preflight:{arm}")
        if backend == "mock":
            res = caller.call_key(f"PREFLIGHT|{arm}", attempt=2)
        else:
            res = caller.call(system, user, seed=0)
        cost = res["in_tokens"] * PRICE_IN + res["out_tokens"] * PRICE_OUT
        ledger.settle(wc, cost if backend == "live" else 0.0)
        parsed = JP.parse_pedagogy_scores(res["text"])
        rec = {"arm": arm, "parsed_ok": parsed is not None,
               "degraded": degraded_reason(res), **{k: res[k] for k in
               ("served_model", "stop_reason", "in_tokens", "out_tokens")}}
        records.append(rec)
        served.add(res["served_model"])

    violations = []
    if not all(r["parsed_ok"] for r in records):
        violations.append("the frozen pedagogy parser did not parse a preflight reply")
    if any(r["degraded"] for r in records):
        violations.append(f"degraded preflight response: "
                          f"{[r['degraded'] for r in records if r['degraded']]}")
    if len(served) != 1 or None in served:
        violations.append(f"inconsistent/absent served model: {sorted(map(str, served))}")
    if violations:
        raise SystemExit("preflight FAILED — refusing to freeze this contract:\n  - "
                         + "\n  - ".join(violations))

    import anthropic
    resolved = {
        "timestamp_utc": now_utc(), "backend": backend,
        "requested_model": spec["spec"]["model"],
        "served_model_frozen": next(iter(served)),
        "temperature": "omitted from request (spec temperature: null)",
        "max_tokens": spec["spec"].get("max_tokens"),
        "seed_supported": False,
        "seed_note": "the Anthropic path sends no seed; the 3 reps are genuine "
                     "stochastic samples (matches the source study)",
        "anthropic_sdk_version": anthropic.__version__,
        "parser_ok": True,
        "finish_reasons": sorted({str(r["stop_reason"]) for r in records}),
        "usage_logged": True,
        "contract_sha256": PJ.contract_sha256(spec["spec"]),
        "frozen_inputs": frozen_inputs(),
        "spend": ledger.summary(),
        "calls": records,
    }
    write_json(RESULTS / "preflight" / "resolved_config.json", resolved)
    print(f"preflight PASS: served model {resolved['served_model_frozen']!r}, "
          f"parser ok, spend {ledger.summary()['this_run_settled_usd']}$")


def load_resolved(spec: dict, backend: str) -> dict:
    p = RESULTS / "preflight" / "resolved_config.json"
    if not p.exists():
        raise SystemExit("no completed preflight (results/preflight/resolved_config.json); "
                         "run --preflight first.")
    resolved = json.loads(p.read_text())
    current = PJ.contract_sha256(spec["spec"])
    if resolved.get("contract_sha256") != current:
        raise SystemExit(
            "PREFLIGHT CONTRACT MISMATCH: a frozen input (stimuli, profiles, prompt "
            "templates, judge config, schedule) changed after the preflight. Re-run "
            "--preflight deliberately; do not score under an untested contract.")
    if resolved.get("backend") != backend:
        raise SystemExit(f"preflight was run with backend={resolved.get('backend')!r}, "
                         f"this run is {backend!r}; re-run --preflight for this backend.")
    return resolved


def mode_score(spec: dict, backend: str, cap: float, pilot_n: int | None,
               cache_only: bool):
    stimuli = PJ.load_stimuli()
    profiles = PJ.load_profiles()
    system = PJ.build_system()
    sched = PJ.schedule(stimuli)
    stamp = {"contract_sha256": PJ.contract_sha256(spec["spec"]), "backend": backend}
    cache_name = "profile_pedagogy_cache.json" if backend == "live" else "mock_cache.json"
    cache = RepCache(RESULTS / "cache" / cache_name, stamp)
    by_id = {s["stimulus_id"]: s for s in stimuli}

    if cache_only:
        missing = [c for c in sched
                   if PJ.cache_key(c["stimulus_id"], c["arm"], c["pole"], c["rep"])
                   not in cache.entries]
        if missing:
            raise SystemExit(
                f"OFFLINE RECONSTRUCTION TRIPWIRE: {len(missing)}/{len(sched)} per-rep "
                f"ratings are not in the released cache (first: {missing[0]}). "
                "Refusing to fabricate or fetch; reconstruction must be exact.")
        finalize(spec, backend, cache, sched, by_id,
                 note="offline reconstruction from the released per-rep cache")
        return

    resolved = load_resolved(spec, backend)
    frozen_model = resolved["served_model_frozen"]
    ledger = SpendLedger(RESULTS / "spend_ledger.json", cap, backend)
    breaker = Breaker()
    caller = (MockCaller(spec["spec"]) if backend == "mock" else LiveCaller(spec["cfg"]))

    todo = sched if pilot_n is None else sched[:pilot_n]
    if pilot_n is None:
        mark_state("scoring", {"complete": False, "backend": backend,
                               "note": "scoring in progress; any previously promoted "
                                       "finals are stale and must not be reported."})
    n_hit = n_new = 0
    try:
        for i, c in enumerate(todo):
            key = PJ.cache_key(c["stimulus_id"], c["arm"], c["pole"], c["rep"])
            if key in cache.entries:
                n_hit += 1
                continue
            s = by_id[c["stimulus_id"]]
            user = PJ.build_user(s, c["arm"], c["pole"], profiles)
            PJ.assert_prompt_pure(user, c["arm"], profiles)
            rec = _attempt_rep(key, system, user, seed=PJ.SCHEDULE_SEED + c["rep"],
                               caller=caller, backend=backend, ledger=ledger,
                               breaker=breaker, spec=spec["spec"],
                               frozen_model=frozen_model)
            if rec is not None:
                cache.put(key, rec)
                n_new += 1
            if (i + 1) % 100 == 0:
                print(f"  {i + 1}/{len(todo)} calls done "
                      f"(cache hits {n_hit}, new {n_new}, "
                      f"spend ${ledger.summary()['this_run_settled_usd']})")
    finally:
        cache.flush()

    print(f"scored: {n_hit} cache hits, {n_new} new ratings; "
          f"spend {json.dumps(ledger.summary())}")
    if pilot_n is not None:
        write_json(RESULTS / "pilot_report.json", {
            "pilot_calls": len(todo), "cache_hits": n_hit, "new_ratings": n_new,
            "breaker": {"responses": breaker.responses, "accepted": breaker.accepted},
            "spend": ledger.summary(), "utc": now_utc()})
        print("pilot only — nothing promoted. See results/pilot_report.json")
        return
    finalize(spec, backend, cache, sched, by_id, note="scored run",
             extra={"spend": ledger.summary()})


def finalize(spec, backend, cache, sched, by_id, note, extra=None):
    """Completeness gate + transactional promotion of the final outputs."""
    units: dict[tuple, list] = {}
    for c in sched:
        units.setdefault((c["stimulus_id"], c["arm"], c["pole"]), []).append(
            PJ.cache_key(c["stimulus_id"], c["arm"], c["pole"], c["rep"]))

    per_rep_rows, per_unit_rows, incomplete = [], [], []
    for (sid, arm, pole), keys in sorted(units.items()):
        reps = []
        for key in sorted(keys, key=lambda k: int(k.rsplit("|", 1)[1])):
            e = cache.entries.get(key)
            reps.append(e["scores"] if e else None)
            if e:
                per_rep_rows.append({"stimulus_id": sid, "arm": arm, "pole": pole,
                                     "rep": int(key.rsplit("|", 1)[1]), **e})
        agg = JP.aggregate_reps(reps)
        if agg["n_valid"] != PJ.REPS:
            incomplete.append([sid, arm, pole, agg["n_valid"]])
        s = by_id[sid]
        per_unit_rows.append({
            "stimulus_id": sid, "arm": arm, "pole": pole,
            "competence_label": s["competence_label"],
            "evidence_strength": s["evidence_strength"], **agg})

    completeness = {"reps": PJ.REPS, "n_units": len(units),
                    "complete": not incomplete,
                    "units_missing_valid_reps": incomplete[:50],
                    "n_units_incomplete": len(incomplete)}
    if incomplete:
        mark_state("incomplete", {"complete": False, "backend": backend,
                                  "completeness": completeness})
        raise SystemExit(
            f"COMPLETENESS GATE: {len(incomplete)} unit(s) lack {PJ.REPS} valid reps. "
            "Nothing promoted; the cache keeps every valid rating, so re-running pays "
            "only for what is missing.")

    staging = RESULTS / f"tmp.staging.{os.getpid()}"
    staging.mkdir(parents=True, exist_ok=True)
    with open(staging / "per_rep_scores.jsonl", "w") as f:
        for r in per_rep_rows:
            f.write(json.dumps(r) + "\n")
    with open(staging / "per_unit.jsonl", "w") as f:
        for r in per_unit_rows:
            f.write(json.dumps(r) + "\n")
    write_json(staging / "completeness.json", completeness)
    write_json(staging / "run_meta.json", {
        "note": note, "backend": backend,
        "reportable": backend == "live",
        "judge_model": spec["spec"]["model"],
        "contract_sha256": PJ.contract_sha256(spec["spec"]),
        "frozen_inputs": frozen_inputs(),
        "n_units": len(units), "n_per_rep_rows": len(per_rep_rows),
        "utc": now_utc(), **(extra or {})})
    promote(staging, {"complete": True, "backend": backend, "note": note})
    print(f"PROMOTED {len(per_unit_rows)} units / {len(per_rep_rows)} per-rep rows "
          f"to results/ ({'REPORTABLE' if backend == 'live' else 'NOT reportable: ' + backend})")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest-only", action="store_true")
    ap.add_argument("--preflight", action="store_true")
    ap.add_argument("--offline-cache-only", action="store_true")
    ap.add_argument("--judge-backend", choices=["live", "mock"], default="live")
    ap.add_argument("--pilot", type=int, default=None, metavar="N")
    ap.add_argument("--cap", type=float, default=CAP_DEFAULT_USD,
                    help="lifetime spend cap in USD (default %(default)s)")
    args = ap.parse_args()

    assert RESULTS == ROOT / "results"
    RESULTS.mkdir(exist_ok=True)
    spec = judge_spec()

    if args.manifest_only:
        return mode_manifest(spec)
    with run_lock():
        if args.preflight:
            return mode_preflight(spec, args.judge_backend, args.cap)
        return mode_score(spec, args.judge_backend, args.cap, args.pilot,
                          args.offline_cache_only)


if __name__ == "__main__":
    raise SystemExit(main())
