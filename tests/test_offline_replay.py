"""Mock end-to-end + offline-cache-only replay guarantees (Phase 7).

Runs the ENTIRE pipeline (preflight -> derived full scoring -> completeness ->
transactional promotion -> offline reconstruction) with the deterministic mock
backend inside a temp results dir, so the repo's real results/ namespace stays
clean for the paid run. The same reconstruction path serves the released live
cache after the paid run.
"""
import json
import hashlib
from pathlib import Path

import pytest

import judging.run_study as RS

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def tmp_results(tmp_path, monkeypatch):
    monkeypatch.setattr(RS, "RESULTS", tmp_path)
    return tmp_path


def _needs_stimuli():
    if not (ROOT / "corpus/stimuli.jsonl").exists():
        pytest.skip("corpus/stimuli.jsonl not frozen yet")


def test_mock_end_to_end_then_offline_replay(tmp_results):
    _needs_stimuli()
    spec = RS.judge_spec()

    # paid mode refuses to run without a preflight
    with pytest.raises(SystemExit, match="preflight"):
        RS.mode_score(spec, "mock", cap=40.0, pilot_n=None, cache_only=False)

    RS.mode_preflight(spec, "mock", cap=40.0)
    resolved = json.loads((tmp_results / "preflight/resolved_config.json").read_text())
    assert resolved["parser_ok"] and resolved["backend"] == "mock"

    RS.mode_score(spec, "mock", cap=40.0, pilot_n=None, cache_only=False)
    state = json.loads((tmp_results / "run_state.json").read_text())
    assert state["state"] == "complete"
    per_unit = (tmp_results / "per_unit.jsonl").read_bytes()
    rows = [json.loads(l) for l in per_unit.splitlines()]
    # derived from the frozen set, not hard-coded, so a re-freeze does not silently
    # turn this into a weaker assertion
    import judging.profile_judge as PJ
    n_units = len(PJ.load_stimuli()) * len(PJ.ARMS) * len(PJ.POLES)
    assert len(rows) == n_units and all(r["n_valid"] == 3 for r in rows)
    meta = json.loads((tmp_results / "run_meta.json").read_text())
    assert meta["reportable"] is False  # mock is NEVER reportable

    # offline reconstruction from the cache reproduces the promoted numbers exactly
    RS.mode_score(spec, "mock", cap=40.0, pilot_n=None, cache_only=True)
    assert (tmp_results / "per_unit.jsonl").read_bytes() == per_unit

    # a seeded cache miss must abort reconstruction, not fabricate
    cache_path = tmp_results / "cache/mock_cache.json"
    blob = json.loads(cache_path.read_text())
    victim = sorted(blob["entries"])[7]
    del blob["entries"][victim]
    cache_path.write_text(json.dumps(blob))
    with pytest.raises(SystemExit, match="TRIPWIRE"):
        RS.mode_score(spec, "mock", cap=40.0, pilot_n=None, cache_only=True)


def test_completeness_gate_blocks_promotion(tmp_results):
    _needs_stimuli()
    spec = RS.judge_spec()
    RS.mode_preflight(spec, "mock", cap=40.0)
    RS.mode_score(spec, "mock", cap=40.0, pilot_n=None, cache_only=False)

    # drop one rep from the cache and re-finalize: the gate must refuse
    cache_path = tmp_results / "cache/mock_cache.json"
    blob = json.loads(cache_path.read_text())
    victim = sorted(blob["entries"])[0]
    del blob["entries"][victim]
    cache_path.write_text(json.dumps(blob))

    import judging.profile_judge as PJ
    stimuli = PJ.load_stimuli()
    cache = RS.RepCache(cache_path, blob["stamp"])
    with pytest.raises(SystemExit, match="COMPLETENESS GATE"):
        RS.finalize(spec, "mock", cache, PJ.schedule(stimuli),
                    {s["stimulus_id"]: s for s in stimuli}, note="unit test")
    state = json.loads((tmp_results / "run_state.json").read_text())
    assert state["state"] == "incomplete"


def test_contract_mismatch_refuses_stale_cache(tmp_results):
    _needs_stimuli()
    spec = RS.judge_spec()
    cache_path = tmp_results / "cache/mock_cache.json"
    cache_path.parent.mkdir(parents=True)
    cache_path.write_text(json.dumps({"stamp": {"contract_sha256": "stale", "backend": "mock"},
                                      "entries": {}}))
    with pytest.raises(SystemExit, match="CACHE STAMP MISMATCH"):
        RS.RepCache(cache_path, {"contract_sha256": "current", "backend": "mock"})


def test_fabricated_live_cache_without_wire_provenance_is_refused(tmp_results):
    import judging.profile_judge as PJ
    spec = RS.judge_spec()
    contract = PJ.contract_sha256(spec["spec"])
    entries = {}
    scores = {k: 5 for k in ("scaffolding", "productive_struggle",
                              "assistance_calibration", "elicitation", "overall")}
    for call in PJ.schedule(PJ.load_stimuli()):
        key = PJ.cache_key(call["stimulus_id"], call["arm"], call["pole"], call["rep"])
        entries[key] = {"scores": scores, "served_model": "claude-opus-4-8"}
    path = tmp_results / "cache/profile_pedagogy_cache.json"
    path.parent.mkdir()
    path.write_text(json.dumps({
        "stamp": {"contract_sha256": contract, "backend": "live"},
        "entries": entries}))

    with pytest.raises(SystemExit, match="cache exists without a wire log"):
        RS.mode_score(spec, "live", cap=40.0, pilot_n=None, cache_only=False)


def test_live_cache_must_match_raw_response_prompt_and_response_id(tmp_results):
    key = "S01|D|high|0"
    user_sha = hashlib.sha256(b"frozen prompt").hexdigest()
    text = json.dumps({k: 5 for k in (
        "scaffolding", "productive_struggle", "assistance_calibration",
        "elicitation", "overall")})
    scores = json.loads(text)
    row = {
        "key": key, "attempt": 1, "backend": "live",
        "response_id": "msg_offline_provenance", "served_model": "claude-opus-4-8",
        "stop_reason": "end_turn", "in_tokens": 10, "out_tokens": 5,
        "cost_usd": 0.000175, "degraded": None, "parsed_ok": True,
        "scores": scores, "response_text": text,
        "response_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "user_sha256": user_sha, "latency_s": 0.1, "utc": "offline-test"}
    row["wire_sha256"] = RS._wire_digest(row)
    wire = tmp_results / "wire"
    wire.mkdir()
    (wire / "calls.jsonl").write_text(json.dumps(row) + "\n")
    cache_path = tmp_results / "cache/profile_pedagogy_cache.json"
    cache_path.parent.mkdir()
    stamp = {"contract_sha256": "test", "backend": "live"}
    cache_path.write_text(json.dumps({"stamp": stamp, "entries": {key: {
        "scores": scores, "served_model": "claude-opus-4-8",
        "response_id": "msg_offline_provenance", "wire_sha256": row["wire_sha256"]}}}))
    cache = RS.RepCache(cache_path, stamp)
    assert RS.validate_live_cache_provenance(
        cache, {key: user_sha}, "claude-opus-4-8")

    cache.entries[key]["response_id"] = "msg_forged"
    with pytest.raises(SystemExit, match="response-id mismatch"):
        RS.validate_live_cache_provenance(cache, {key: user_sha}, "claude-opus-4-8")
