#!/usr/bin/env python3
"""The paid runner for the label-vs-evidence judge study.

Control surface modeled on $SRC/analysis/run_cross_judge_audit.py (reimplemented,
not vendored). All output lives under results/ (enforced). Modes:

  --manifest-only       OFFLINE. input_manifest.jsonl + plan.json + frozen_inputs.sha256.
  --preflight           TWO synthetic, non-study calls (one D-arm, one profile-arm)
                        through the real instrument. Resolves and freezes the transport
                        contract -> results/preflight/resolved_config.json. Refuses to
                        freeze on any contract violation.
  (default: paid)       the full pass derived from the frozen stimulus count. Requires
                        a completed preflight whose contract and frozen-file hashes
                        still match. Promotes only when EVERY unit has n_valid == 3.
  --pilot N             run only the first N schedule calls (shared cache, real spend,
                        no promotion). Writes results/pilot_report.json.
  --offline-cache-only  reconstruct finals from the released per-rep cache. ANY cache
                        miss aborts, and any disagreement with the already-promoted
                        finals aborts without overwriting them. No provider call, no
                        synthetic score.
  --judge-backend mock  full pipeline, deterministic synthetic scores, no key. Uses a
                        separate cache namespace. NEVER reportable.

Guardrails:
  - CUMULATIVE dollar spend ledger (results/spend_ledger.json), persisted around every
    provider request: a conservative worst-case pre-charge before the request, settled
    to actual usage-derived cost after. Hard cap via --cap (default $40), lifetime
    across invocations; a crash leaves the pre-charge committed (conservative).
    The Anthropic SDK's hidden retries are disabled. Every physical attempt is made
    by this runner only after a separate worst-case reservation; an exception leaves
    that reservation committed.
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
import math
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT))

from analysis import judge_pedagogy as JP          # noqa: E402  vendored, frozen
from agents.config import load_models_config       # noqa: E402  vendored
from judging import profile_judge as PJ            # noqa: E402

RESULTS = ROOT / "results"
CAP_DEFAULT_USD = 40.0
HARD_LIVE_CAP_USD = 40.0
# claude-opus-4-8 first-party pricing (USD per token).
PRICE_IN = 5.00 / 1e6
PRICE_OUT = 25.00 / 1e6
# Conservative pre-charge: the request text is checked against a byte-based upper
# bound (a tokenizer cannot emit more ordinary text tokens than UTF-8 bytes), with
# room for the provider's message envelope, plus the full max_tokens output.
WORST_CASE_IN_TOKENS = 8192
REQUEST_ENVELOPE_TOKEN_ALLOWANCE = 512
MAX_ATTEMPTS_PER_REP = 4
BREAKER_WARMUP = 12
BREAKER_MIN_ACCEPT = 0.5
CACHE_FLUSH_EVERY = 20

FINAL_NAMES = ("per_rep_scores.jsonl", "per_unit.jsonl", "completeness.json",
               "run_meta.json")
FREEZE_TAG_PREFIX = "prereg-final-"
RUNTIME_RESULT_PATHS = (
    "results/preflight/",
    "results/cache/profile_pedagogy_cache.json",
    "results/wire/calls.jsonl",
    "results/spend_ledger.json",
    "results/pilot_report.json",
    "results/run_state.json",
    "results/per_rep_scores.jsonl",
    "results/per_unit.jsonl",
    "results/completeness.json",
    "results/run_meta.json",
)

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
    if spec.get("provider", cfg.get("provider")) != "anthropic":
        raise SystemExit(f"judge provider must be anthropic: {spec}")
    if spec.get("model") != "claude-opus-4-8":
        raise SystemExit(f"judge model drifted from claude-opus-4-8: {spec}")
    if spec.get("temperature") is not None:
        raise SystemExit("judge temperature must be omitted")
    return {"cfg": cfg, "spec": spec}


def worst_case_call_usd(spec: dict, system: str | None = None,
                        user: str | None = None) -> float:
    if (system is None) != (user is None):
        raise ValueError("system and user must be supplied together")
    if system is not None:
        text_bytes = len(system.encode()) + len(user.encode())
        if text_bytes + REQUEST_ENVELOPE_TOKEN_ALLOWANCE > WORST_CASE_IN_TOKENS:
            raise SystemExit(
                f"REQUEST EXCEEDS SPEND RESERVATION: {text_bytes} UTF-8 bytes plus "
                f"{REQUEST_ENVELOPE_TOKEN_ALLOWANCE} envelope tokens exceeds the "
                f"{WORST_CASE_IN_TOKENS}-token input reservation")
    return WORST_CASE_IN_TOKENS * PRICE_IN + spec.get("max_tokens", 512) * PRICE_OUT


def _git_freeze_snapshot(allow_runtime_results: bool = False) -> dict:
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
            capture_output=True, text=True).stdout.strip()
        tags = subprocess.run(
            ["git", "tag", "--points-at", "HEAD"], cwd=ROOT, check=True,
            capture_output=True, text=True).stdout.splitlines()
    except (OSError, subprocess.CalledProcessError) as e:
        raise SystemExit(f"cannot verify the Git freeze: {e}")
    dirty = []
    for line in status.splitlines():
        path = line[3:]
        allowed = allow_runtime_results and any(
            path == prefix or (prefix.endswith("/") and path.startswith(prefix))
            for prefix in RUNTIME_RESULT_PATHS)
        if not allowed:
            dirty.append(line)
    return {"git_commit": commit, "git_tags_at_head": sorted(tags),
            "unexpected_git_status": dirty}


def require_git_freeze(allow_runtime_results: bool = False) -> dict:
    """Require the tagged source tree; later calls may add only named run outputs."""
    snapshot = _git_freeze_snapshot(allow_runtime_results)
    if snapshot["unexpected_git_status"]:
        raise SystemExit(
            "LIVE RUN REQUIRES THE FROZEN TREE TO BE CLEAN. Commit every intended "
            "material, code, protocol, test, and reconstruction input first. Only "
            "named runtime result files may appear after preflight.\n" +
            "\n".join(snapshot["unexpected_git_status"]))
    freeze_tags = [t for t in snapshot["git_tags_at_head"]
                   if t.startswith(FREEZE_TAG_PREFIX)]
    if not freeze_tags:
        raise SystemExit(
            f"LIVE PREFLIGHT REQUIRES A TAG AT HEAD named {FREEZE_TAG_PREFIX}<label>")
    return {"git_commit": snapshot["git_commit"],
            "git_freeze_tags": freeze_tags}


# ---------------------------------------------------------------- spend ledger
class SpendLedger:
    """Cumulative dollar ledger, persisted on every state change, fail-closed."""

    def __init__(self, path: Path, cap_usd: float, backend: str):
        self.path = path
        self.cap = float(cap_usd)
        self.backend = backend
        if not math.isfinite(self.cap) or self.cap <= 0:
            raise SystemExit("SPEND CAP must be a finite positive number")
        if backend == "live" and self.cap > HARD_LIVE_CAP_USD:
            raise SystemExit(
                f"SPEND CAP ${self.cap:g} exceeds the immutable study ceiling "
                f"${HARD_LIVE_CAP_USD:g}")
        self.settled = 0.0      # billed dollars, current backend regime
        self.committed = 0.0    # outstanding pre-charges (crash leaves them counted)
        self.invocations = []
        self._stored_caps = {}
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
        stored_caps = blob.get("caps_usd_by_backend", {})
        if not isinstance(stored_caps, dict):
            self._corrupt("has invalid caps_usd_by_backend")
        stored_cap = stored_caps.get(self.backend)
        if stored_cap is None and any(
                isinstance(inv, dict) and inv.get("backend") == self.backend
                for inv in blob["invocations"]):
            self._corrupt(f"has {self.backend} spend but no immutable stored cap")
        if stored_cap is not None:
            if not isinstance(stored_cap, (int, float)) or not math.isfinite(stored_cap):
                self._corrupt(f"has an invalid stored {self.backend} cap")
            if self.cap > stored_cap + 1e-12:
                raise SystemExit(
                    f"SPEND CAP cannot be raised for {self.backend}: ledger ceiling is "
                    f"${stored_cap:g}, requested ${self.cap:g}")
        self._stored_caps = dict(stored_caps)
        total = blob.get("settled_usd_total")
        if not isinstance(total, (int, float)) or not math.isfinite(total) or total < 0:
            self._corrupt("has an invalid settled_usd_total")
        s = c = all_settled = 0.0
        for inv in blob["invocations"]:
            if not isinstance(inv, dict):
                self._corrupt("contains a non-object invocation")
            settled = inv.get("settled_usd")
            committed = inv.get("committed_usd", 0.0)
            if (not isinstance(settled, (int, float)) or not math.isfinite(settled)
                    or settled < 0):
                self._corrupt("holds a non-numeric settled_usd")
            if (not isinstance(committed, (int, float)) or not math.isfinite(committed)
                    or committed < -1e-9):
                self._corrupt("holds an invalid committed_usd")
            all_settled += settled
            if inv.get("backend") == self.backend:
                s += settled
                c += max(0.0, committed)
        if abs(all_settled - total) > 1e-6:
            self._corrupt("is internally inconsistent (totals != sum of invocations)")
        self.settled, self.committed = s, c
        self.invocations = blob["invocations"]

    def _persist(self):
        allrows = [*self.invocations, self._this]
        caps = {**self._stored_caps, self.backend: self.cap}
        self._stored_caps = caps
        write_json(self.path, {
            "cap_usd_current_backend": self.cap,
            "caps_usd_by_backend": caps,
            "settled_usd_total": round(sum(i["settled_usd"] for i in allrows), 6),
            "note": "CUMULATIVE across invocations; rows labeled by backend (mock "
                    "rehearsals never consume the live allowance). committed_usd is "
                    "a crash-conservative outstanding pre-charge.",
            "invocations": allrows,
        })

    def charge(self, worst_case_usd: float, where: str):
        if (not isinstance(worst_case_usd, (int, float))
                or not math.isfinite(worst_case_usd) or worst_case_usd <= 0):
            raise SystemExit("SPEND RESERVATION must be a finite positive number")
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
        if (not isinstance(actual_usd, (int, float)) or not math.isfinite(actual_usd)
                or actual_usd < 0 or actual_usd > worst_case_usd + 1e-12):
            raise SystemExit("SPEND SETTLEMENT is invalid or exceeds its reservation")
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
        import anthropic
        self.spec = cfg["roles"]["judge"]
        # The runner, ledger, and wire log own retries. SDK retries would create
        # unreserved physical requests inside one logical call.
        self.client = anthropic.Anthropic(
            api_key=os.environ["ANTHROPIC_API_KEY"], max_retries=0)

    def call(self, system: str, user: str, seed: int) -> dict:
        del seed  # Anthropic path intentionally has no seed.
        response = self.client.messages.create(
            model=self.spec["model"], system=system,
            messages=[{"role": "user", "content": user}],
            max_tokens=self.spec.get("max_tokens", 512))
        text = "".join(
            b.text for b in response.content if getattr(b, "type", None) == "text")
        return {"text": text,
                "response_id": getattr(response, "id", None),
                "served_model": getattr(response, "model", None),
                "stop_reason": getattr(response, "stop_reason", None),
                "in_tokens": getattr(response.usage, "input_tokens", None),
                "out_tokens": getattr(response.usage, "output_tokens", None)}


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
def _wire_digest(rec: dict) -> str:
    unsigned = {k: v for k, v in rec.items() if k != "wire_sha256"}
    payload = json.dumps(unsigned, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def wire_write(rec: dict) -> str:
    p = RESULTS / "wire" / "calls.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    digest = _wire_digest(rec)
    row = {**rec, "wire_sha256": digest}
    with open(p, "a") as f:
        f.write(json.dumps(row) + "\n")
        f.flush()
        os.fsync(f.fileno())
    return digest


def validate_live_cache_provenance(cache: RepCache, expected_user_sha256=None,
                                   frozen_model=None) -> bool:
    """Require every live cache entry to match a hashed, provider-identified wire row."""
    if (cache.stamp or {}).get("backend") != "live":
        return False
    if expected_user_sha256 is not None:
        extras = sorted(set(cache.entries) - set(expected_user_sha256))
        if extras:
            raise SystemExit(f"LIVE CACHE PROVENANCE: unexpected key {extras[0]}")
    if not cache.entries:
        return True
    p = RESULTS / "wire" / "calls.jsonl"
    if not p.exists():
        raise SystemExit("LIVE CACHE PROVENANCE: cache exists without a wire log")
    by_digest = {}
    for lineno, line in enumerate(p.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception as e:  # noqa: BLE001
            raise SystemExit(f"LIVE CACHE PROVENANCE: invalid wire row {lineno}: {e}")
        digest = row.get("wire_sha256")
        if digest != _wire_digest(row):
            raise SystemExit(f"LIVE CACHE PROVENANCE: wire hash mismatch at row {lineno}")
        if row.get("backend") == "live" and row.get("parsed_ok"):
            if not row.get("response_id"):
                raise SystemExit(
                    f"LIVE CACHE PROVENANCE: live wire row {lineno} has no response id")
            response_text = row.get("response_text")
            if not isinstance(response_text, str):
                raise SystemExit(
                    f"LIVE CACHE PROVENANCE: live wire row {lineno} has no raw response")
            if row.get("response_sha256") != hashlib.sha256(
                    response_text.encode()).hexdigest():
                raise SystemExit(
                    f"LIVE CACHE PROVENANCE: response hash mismatch at row {lineno}")
            if JP.parse_pedagogy_scores(response_text) != row.get("scores"):
                raise SystemExit(
                    f"LIVE CACHE PROVENANCE: parsed scores mismatch at row {lineno}")
            by_digest[digest] = row
    response_ids = set()
    for key, entry in cache.entries.items():
        digest = entry.get("wire_sha256")
        row = by_digest.get(digest)
        if row is None:
            raise SystemExit(
                f"LIVE CACHE PROVENANCE: {key} has no matching accepted wire row")
        if row.get("key") != key or row.get("scores") != entry.get("scores"):
            raise SystemExit(f"LIVE CACHE PROVENANCE: wire/cache mismatch for {key}")
        if row.get("response_id") != entry.get("response_id"):
            raise SystemExit(f"LIVE CACHE PROVENANCE: response-id mismatch for {key}")
        if row["response_id"] in response_ids:
            raise SystemExit(
                f"LIVE CACHE PROVENANCE: duplicate provider response id for {key}")
        response_ids.add(row["response_id"])
        if (expected_user_sha256 is not None
                and row.get("user_sha256") != expected_user_sha256[key]):
            raise SystemExit(f"LIVE CACHE PROVENANCE: prompt hash mismatch for {key}")
        if row.get("served_model") != entry.get("served_model"):
            raise SystemExit(f"LIVE CACHE PROVENANCE: served-model mismatch for {key}")
        if frozen_model is not None and row.get("served_model") != frozen_model:
            raise SystemExit(f"LIVE CACHE PROVENANCE: frozen-model mismatch for {key}")
    return True


def expected_user_hashes(sched: list[dict], by_id: dict, profiles: dict) -> dict:
    out = {}
    for call in sched:
        key = PJ.cache_key(call["stimulus_id"], call["arm"], call["pole"], call["rep"])
        user = PJ.build_user(by_id[call["stimulus_id"]], call["arm"],
                             call["pole"], profiles)
        PJ.assert_prompt_pure(user, call["arm"], profiles)
        out[key] = hashlib.sha256(user.encode()).hexdigest()
    return out


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
    result_sha256 = {n: sha_file(RESULTS / n) for n in FINAL_NAMES}
    mark_state("complete", {**payload, "result_sha256": result_sha256})
    shutil.rmtree(staging, ignore_errors=True)


# ---------------------------------------------------------------- frozen inputs
def sha_artifact(artifact: Path, sidecar: Path) -> str:
    """sha256 of the ARTIFACT, cross-checked against its recorded sidecar.

    AUDIT-2026-08-08 B2: this used to return the sidecar's *text* without ever
    hashing the file, so editing `stimuli.jsonl` or `labels.jsonl` while leaving
    the sidecar alone left `contract_sha256`, the cache stamp and the recorded
    provenance completely unchanged — the two artifacts that matter most were the
    only two outside the freeze the runner claims to enforce. Now the artifact is
    hashed, and a sidecar that disagrees is a hard stop rather than the value used.
    """
    actual = sha_file(artifact)
    recorded = sidecar.read_text().split()[0] if sidecar.exists() else None
    if recorded != actual:
        raise SystemExit(
            f"FROZEN INPUT MISMATCH: {artifact.relative_to(ROOT)} hashes to {actual} "
            f"but {sidecar.relative_to(ROOT)} records {recorded}. A frozen artifact "
            "and its recorded hash disagree — refusing to run. Re-freeze deliberately "
            "if the change is intended.")
    return actual


def frozen_inputs() -> dict:
    return {
        "stimuli_sha256": sha_artifact(ROOT / "corpus/stimuli.jsonl",
                                       ROOT / "corpus/stimuli.sha256"),
        "labels_sha256": sha_artifact(ROOT / "labeling/labels.jsonl",
                                      ROOT / "labeling/labels.sha256"),
        "profiles_yaml_sha256": sha_file(ROOT / "profiles/profiles.yaml"),
        "models_yaml_sha256": sha_file(ROOT / "vendor/configs/models.yaml"),
        "judge_pedagogy_py_sha256": sha_file(ROOT / "vendor/analysis/judge_pedagogy.py"),
        "profile_judge_py_sha256": sha_file(ROOT / "judging/profile_judge.py"),
        "run_study_py_sha256": sha_file(ROOT / "judging/run_study.py"),
        "rubric_md_sha256": sha_file(ROOT / "vendor/supplement/judge_pedagogy_rubric.md"),
        "analyze_py_sha256": sha_file(ROOT / "analysis/analyze.py"),
        "prereg_md_sha256": sha_file(ROOT / "protocol/PREREGISTRATION.md"),
        "requirements_txt_sha256": sha_file(ROOT / "requirements.txt"),
        "topup_recipe_sha256": sha_file(ROOT / "corpus/candidates_topup.jsonl"),
    }


# ---------------------------------------------------------------- modes
def mode_manifest(spec: dict):
    stimuli = PJ.load_stimuli()
    profiles = PJ.load_profiles()
    system = PJ.build_system()
    units = [(s["stimulus_id"], arm, pole)
             for s in stimuli for arm in PJ.ARMS for pole in PJ.POLES]
    with open(RESULTS / "input_manifest.jsonl", "w") as f:
        for s in stimuli:
            for arm in PJ.ARMS:
                for pole in PJ.POLES:
                    user = PJ.build_user(s, arm, pole, profiles)
                    PJ.assert_prompt_pure(user, arm, profiles)
                    worst_case_call_usd(spec["spec"], system, user)
                    f.write(json.dumps({
                        "stimulus_id": s["stimulus_id"], "arm": arm, "pole": pole,
                        "user_sha256": hashlib.sha256(user.encode()).hexdigest(),
                        "user_chars": len(user)}) + "\n")
    est_in = 1640 + 95 * 2 / 3          # measured pedjudge basis + profile block share
    n_calls = len(units) * PJ.REPS
    plan = {
        # Derived from the artifact: a hard-coded stimulus count already went stale
        # during pre-flight remediation.
        "design": (f"{len(stimuli)} stimuli x {len(PJ.ARMS)} arms x "
                   f"{len(PJ.POLES)} poles x {PJ.REPS} reps"),
        "n_stimuli": len(stimuli), "n_units": len(units), "reps": PJ.REPS,
        "n_calls_planned": n_calls,
        "judge_model": spec["spec"]["model"],
        "est_cost_usd": round(n_calls * (est_in * PRICE_IN + 52 * PRICE_OUT), 2),
        "no_retry_reservation_usd": round(
            n_calls * worst_case_call_usd(spec["spec"]), 2),
        "retry_inclusive_request_ceiling_usd": round(
            n_calls * MAX_ATTEMPTS_PER_REP * worst_case_call_usd(spec["spec"]), 2),
        "hard_live_cap_usd": HARD_LIVE_CAP_USD,
        "contract_sha256": PJ.contract_sha256(spec["spec"]),
        "frozen_inputs": frozen_inputs(),
        "note": "no cache_control breakpoint is ever sent, so no prompt-cache discount "
                "applies and none is assumed (the ~1000-token system prompt is at "
                "claude-opus-4-8's 1024-token cache minimum, not below it as earlier "
                "drafts said; nothing turns on it)",
    }
    write_json(RESULTS / "plan.json", plan)
    with open(RESULTS / "frozen_inputs.sha256", "w") as f:
        for k, v in sorted(frozen_inputs().items()):
            f.write(f"{v}  {k}\n")
    print(f"manifest: {len(units)} units, {n_calls} valid calls planned, "
          f"est ${plan['est_cost_usd']}, no-retry reservation "
          f"${plan['no_retry_reservation_usd']}, hard cap ${HARD_LIVE_CAP_USD:g}")


def _attempt_rep(key, system, user, seed, caller, backend, ledger, breaker, spec,
                 frozen_model):
    wc = worst_case_call_usd(spec, system, user)
    for attempt in range(1, MAX_ATTEMPTS_PER_REP + 1):
        ledger.charge(wc, where=key)
        t0 = time.time()
        if backend == "mock":
            res = caller.call_key(key, attempt)
        else:
            res = caller.call(system, user, seed=seed)
        deg = degraded_reason(res)
        # A reply with no usage accounting is degraded, not free: settling it at the
        # reservation is the conservative reading of a request we know was billed.
        # Computing cost first raised TypeError on `None` tokens and killed the run
        # before the wire row was written, so the "missing usage" refusal below was
        # unreachable (AUDIT-2026-08-08-preflight-review-3 N7).
        if res["in_tokens"] is None or res["out_tokens"] is None:
            cost = wc
        else:
            cost = res["in_tokens"] * PRICE_IN + res["out_tokens"] * PRICE_OUT
        ledger.settle(wc, cost if backend == "live" else 0.0)
        scores = None if deg else JP.parse_pedagogy_scores(res["text"])
        ok = scores is not None
        wire_sha = wire_write({"key": key, "attempt": attempt, "backend": backend,
                    "response_id": res.get("response_id"),
                    "served_model": res["served_model"], "stop_reason": res["stop_reason"],
                    "in_tokens": res["in_tokens"], "out_tokens": res["out_tokens"],
                    "cost_usd": round(cost, 6) if backend == "live" else 0.0,
                    "degraded": deg, "parsed_ok": ok, "scores": scores,
                    "response_text": res["text"],
                    "response_sha256": hashlib.sha256(res["text"].encode()).hexdigest(),
                    "user_sha256": hashlib.sha256(user.encode()).hexdigest(),
                    "latency_s": round(time.time() - t0, 2), "utc": now_utc()})
        if frozen_model is not None and res["served_model"] != frozen_model:
            raise SystemExit(
                f"SERVED-MODEL DRIFT: preflight froze {frozen_model!r} but this call "
                f"was served by {res['served_model']!r}. Aborting before another call.")
        breaker.record(ok, where=key)
        if ok:
            return {"scores": scores, "served_model": res["served_model"],
                    "response_id": res.get("response_id"),
                    "wire_sha256": wire_sha,
                    "usage": {"in": res["in_tokens"], "out": res["out_tokens"]},
                    "attempts": attempt, "utc": now_utc()}
    return None


def mode_preflight(spec: dict, backend: str, cap: float):
    git_freeze = require_git_freeze() if backend == "live" else {}
    profiles = PJ.load_profiles()
    system = PJ.build_system()
    ledger = SpendLedger(RESULTS / "spend_ledger.json", cap, backend)
    caller = (MockCaller(spec["spec"]) if backend == "mock" else LiveCaller(spec["cfg"]))
    records, served = [], set()
    for arm in ("D", "P_nov"):
        user = PJ.build_user(PREFLIGHT_STIMULUS, arm, "high", profiles)
        PJ.assert_prompt_pure(user, arm, profiles)
        wc = worst_case_call_usd(spec["spec"], system, user)
        ledger.charge(wc, where=f"preflight:{arm}")
        if backend == "mock":
            res = caller.call_key(f"PREFLIGHT|{arm}", attempt=2)
        else:
            res = caller.call(system, user, seed=0)
        # Same guard as _attempt_rep: a reply with no usage accounting is degraded, not
        # free. A5.7 recorded this fix but applied it only to the scoring path, so the
        # "missing usage accounting" refusal below stayed unreachable HERE — the very
        # first paid command (AUDIT-2026-08-10-endpoint-sensitivity B2).
        if res["in_tokens"] is None or res["out_tokens"] is None:
            cost = wc
        else:
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
        **git_freeze,
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
    current_frozen = frozen_inputs()
    if resolved.get("frozen_inputs") != current_frozen:
        changed = sorted(k for k in set(current_frozen) | set(resolved.get("frozen_inputs", {}))
                         if current_frozen.get(k) != resolved.get("frozen_inputs", {}).get(k))
        raise SystemExit(
            f"PREFLIGHT FROZEN-INPUT MISMATCH: {changed}. Re-run --preflight only "
            "after a deliberate pre-data re-freeze.")
    if resolved.get("backend") != backend:
        raise SystemExit(f"preflight was run with backend={resolved.get('backend')!r}, "
                         f"this run is {backend!r}; re-run --preflight for this backend.")
    if backend == "live":
        freeze = require_git_freeze(allow_runtime_results=True)
        if freeze["git_commit"] != resolved.get("git_commit"):
            raise SystemExit("GIT FREEZE MISMATCH: HEAD moved after live preflight")
        if not set(resolved.get("git_freeze_tags", [])) <= set(
                freeze["git_freeze_tags"]):
            raise SystemExit("GIT FREEZE MISMATCH: preflight freeze tag is not at HEAD")
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
    expected_prompts = expected_user_hashes(sched, by_id, profiles)
    if backend == "live":
        validate_live_cache_provenance(cache, expected_prompts)

    if cache_only:
        # Reconstruction must be held to the same contract as scoring: a released
        # cache replayed under an untested/changed contract is not a reproduction
        # (AUDIT-2026-08-08 N7).
        #
        # CAVEAT, not yet resolved: results/preflight/ is NOT tracked, and the git_commit
        # equality check below means committing it to publish it moves HEAD and breaks
        # this path on every clone. So `--offline-cache-only --judge-backend live` works
        # in the operator's own tree before any further commit, and NOT in a released
        # repository (AUDIT-2026-08-10-endpoint-sensitivity N5). Consequence for the
        # operator: do not create any commit between --preflight and the end of the run.
        resolved = load_resolved(spec, backend)
        if backend == "live":
            validate_live_cache_provenance(
                cache, expected_prompts, resolved["served_model_frozen"])
        missing = [c for c in sched
                   if PJ.cache_key(c["stimulus_id"], c["arm"], c["pole"], c["rep"])
                   not in cache.entries]
        if missing:
            raise SystemExit(
                f"OFFLINE RECONSTRUCTION TRIPWIRE: {len(missing)}/{len(sched)} per-rep "
                f"ratings are not in the released cache (first: {missing[0]}). "
                "Refusing to fabricate or fetch; reconstruction must be exact.")
        finalize(spec, backend, cache, sched, by_id,
                 note="offline reconstruction from the released per-rep cache",
                 frozen_model=resolved["served_model_frozen"],
                 compare_existing=True)
        return

    resolved = load_resolved(spec, backend)
    frozen_model = resolved["served_model_frozen"]
    ledger = SpendLedger(RESULTS / "spend_ledger.json", cap, backend)
    breaker = Breaker()
    caller = (MockCaller(spec["spec"]) if backend == "mock" else LiveCaller(spec["cfg"]))

    todo = sched if pilot_n is None else sched[:pilot_n]
    if pilot_n is not None and not 1 <= pilot_n <= len(sched):
        raise SystemExit(f"--pilot must be between 1 and {len(sched)}")
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

    if backend == "live":
        validate_live_cache_provenance(cache, expected_prompts, frozen_model)

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
             extra={"spend": ledger.summary()}, frozen_model=frozen_model)


def finalize(spec, backend, cache, sched, by_id, note, extra=None,
             frozen_model=None, compare_existing=False):
    """Completeness gate + transactional promotion of the final outputs.

    `compare_existing` makes reconstruction REPORT a discrepancy instead of
    repairing one. Replaying the released cache used to os.replace its output over
    whatever was promoted, so a post-hoc edit of the promoted scores was silently
    reverted and never reported — the one tool that could have detected the edit
    destroyed the evidence of it (AUDIT-2026-08-08-preflight-review-3 N1).
    """
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
    # `reportable` must follow the provenance of the RATINGS, not just the flag this
    # invocation was launched with (AUDIT-2026-08-08 N7). The cache stamp records the
    # backend the ratings were produced under, so a mock cache cannot be promoted as
    # reportable by relabelling the run.
    cache_backend = (cache.stamp or {}).get("backend")
    expected_prompts = expected_user_hashes(sched, by_id, PJ.load_profiles())
    live_provenance_ok = (
        validate_live_cache_provenance(cache, expected_prompts, frozen_model)
        if backend == "live" else False)
    reportable = backend == "live" and cache_backend == "live" and live_provenance_ok
    write_json(staging / "run_meta.json", {
        "note": note, "backend": backend,
        "cache_backend": cache_backend,
        "reportable": reportable,
        "live_provenance_ok": live_provenance_ok,
        "judge_model": spec["spec"]["model"],
        "contract_sha256": PJ.contract_sha256(spec["spec"]),
        "frozen_inputs": frozen_inputs(),
        "n_units": len(units), "n_per_rep_rows": len(per_rep_rows),
        "cache_sha256": sha_file(cache.path) if cache.path.exists() else None,
        "wire_sha256": (sha_file(RESULTS / "wire/calls.jsonl")
                         if (RESULTS / "wire/calls.jsonl").exists() else None),
        "utc": now_utc(), **(extra or {})})
    if compare_existing:
        # run_meta.json carries this invocation's timestamp, so only the three data
        # files are comparable; they are a pure function of the cache.
        for name in ("per_rep_scores.jsonl", "per_unit.jsonl", "completeness.json"):
            current = RESULTS / name
            if current.exists() and current.read_bytes() != (staging / name).read_bytes():
                raise SystemExit(
                    f"OFFLINE RECONSTRUCTION MISMATCH: results/{name} differs from what "
                    "the released per-rep cache rebuilds. The promoted results are not "
                    "the ones the cache and wire log support. Nothing was overwritten — "
                    f"the rebuild is in {staging} for comparison.")
    promote(staging, {"complete": True, "backend": backend, "note": note})
    print(f"PROMOTED {len(per_unit_rows)} units / {len(per_rep_rows)} per-rep rows "
          f"to results/ ({'REPORTABLE' if reportable else 'NOT reportable: backend=' + str(backend) + ', ratings=' + str(cache_backend)})")


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

    if RESULTS != ROOT / "results":
        raise SystemExit("runner output namespace must be ROOT/results")
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
