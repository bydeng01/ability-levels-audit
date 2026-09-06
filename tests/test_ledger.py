"""Spend ledger + circuit breaker guarantees (Phase 7)."""
import json
import pytest

from judging.run_study import (Breaker, SpendLedger, BREAKER_WARMUP,
                               WORST_CASE_IN_TOKENS, worst_case_call_usd)


@pytest.fixture(autouse=True)
def _isolate_results_namespace(tmp_path, monkeypatch):
    """Point the runner's module-global RESULTS at a scratch dir for every test here.

    These tests already put their ledger in `tmp_path`, but `SpendLedger._load` checks
    for a live wire log at the module-global `RESULTS / "wire" / "calls.jsonl"` rather
    than at a path derived from the ledger under test. That is correct in production (there is
    exactly one results namespace) but it couples the tests to the real one: once an
    actual paid run has written `results/wire/calls.jsonl`, every `tmp_path` ledger is
    "missing beside a wire log with LIVE requests" and five tests here fail. That is
    exactly what happened after the 2026-08-10 run, and it would have made
    `pytest tests/ -q` fail on any clone of the released repository, contradicting
    README's own reproduce instructions.

    Scope is deliberately this file only, and it changes no production code path; the
    guard itself is still exercised, against a scratch namespace instead of the
    operator's real one. `tests/` is not a frozen input and is not bound by
    `contract_sha256`, so this does not touch the run's provenance.
    """
    import judging.run_study as _rs
    scratch = tmp_path / "results"
    scratch.mkdir(exist_ok=True)
    monkeypatch.setattr(_rs, "RESULTS", scratch)


def test_cap_trips_before_the_next_request(tmp_path):
    led = SpendLedger(tmp_path / "ledger.json", cap_usd=1.0, backend="live")
    led.charge(0.4, "a")
    led.settle(0.4, 0.35)
    led.charge(0.4, "b")
    led.settle(0.4, 0.4)
    with pytest.raises(SystemExit, match="SPEND CAP"):
        led.charge(0.4, "c")  # 0.75 settled + 0.4 projected > 1.0 — refused pre-request
    assert led._this["requests"] == 2


def test_ledger_is_cumulative_across_invocations(tmp_path):
    p = tmp_path / "ledger.json"
    led1 = SpendLedger(p, cap_usd=1.0, backend="live")
    led1.charge(0.3, "a")
    led1.settle(0.3, 0.3)
    led2 = SpendLedger(p, cap_usd=1.0, backend="live")  # resume
    assert led2.settled == pytest.approx(0.3)
    led2.charge(0.3, "b")
    led2.settle(0.3, 0.3)
    with pytest.raises(SystemExit, match="SPEND CAP"):
        led2.charge(0.5, "c")


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), 0.0, -1.0])
def test_nonfinite_or_nonpositive_cap_is_refused(tmp_path, bad):
    with pytest.raises(SystemExit, match="finite positive"):
        SpendLedger(tmp_path / "ledger.json", cap_usd=bad, backend="live")


def test_live_cap_cannot_exceed_study_ceiling_or_rise_on_resume(tmp_path):
    with pytest.raises(SystemExit, match="immutable study ceiling"):
        SpendLedger(tmp_path / "too-high.json", cap_usd=40.01, backend="live")

    p = tmp_path / "ledger.json"
    led = SpendLedger(p, cap_usd=20.0, backend="live")
    led.charge(1.0, "first")
    led.settle(1.0, 0.5)
    with pytest.raises(SystemExit, match="cannot be raised"):
        SpendLedger(p, cap_usd=20.01, backend="live")


def test_crash_leaves_precharge_committed(tmp_path):
    p = tmp_path / "ledger.json"
    led1 = SpendLedger(p, cap_usd=1.0, backend="live")
    led1.charge(0.6, "a")          # crash before settle
    led2 = SpendLedger(p, cap_usd=1.0, backend="live")
    assert led2.committed == pytest.approx(0.6)  # conservative: still counted
    with pytest.raises(SystemExit, match="SPEND CAP"):
        led2.charge(0.5, "b")


def test_mock_rows_never_consume_the_live_allowance(tmp_path):
    """A crashed mock rehearsal's outstanding pre-charge must not eat the live budget.

    The old version settled the mock charge to $0.00 before asserting, so
    `live.settled == 0.0` held whether or not the ledger partitioned rows by backend,
    so changing the partition to `if True:` passed the whole suite
    (AUDIT-2026-08-08-preflight-review-3 N2b, mutation M6). Leaving the mock charge
    unsettled, which is what a crashed rehearsal persists, makes the partition
    load-bearing.
    """
    p = tmp_path / "ledger.json"
    mock = SpendLedger(p, cap_usd=1.0, backend="mock")
    mock.charge(0.9, "rehearsal")                       # deliberately never settled
    assert json.loads(p.read_text())["invocations"][0]["committed_usd"] == 0.9
    live = SpendLedger(p, cap_usd=1.0, backend="live")
    assert live.settled == 0.0 and live.committed == 0.0
    live.charge(0.9, "paid")  # full allowance available


def test_corrupt_ledger_fails_closed(tmp_path):
    p = tmp_path / "ledger.json"
    p.write_text("{not json")
    with pytest.raises(SystemExit, match="SPEND LEDGER CORRUPT"):
        SpendLedger(p, cap_usd=1.0, backend="live")


def test_inconsistent_totals_fail_closed(tmp_path):
    p = tmp_path / "ledger.json"
    p.write_text(json.dumps({
        "settled_usd_total": 99.0,
        "caps_usd_by_backend": {"live": 1.0},
        "invocations": [{"backend": "live", "settled_usd": 0.1, "committed_usd": 0.0}]}))
    with pytest.raises(SystemExit, match="internally inconsistent"):
        SpendLedger(p, cap_usd=1.0, backend="live")


@pytest.mark.parametrize("field", ["settled_usd", "committed_usd"])
def test_nonfinite_persisted_amounts_fail_closed(tmp_path, field):
    p = tmp_path / "ledger.json"
    row = {"backend": "live", "settled_usd": 0.0, "committed_usd": 0.0}
    row[field] = float("nan")
    p.write_text(json.dumps({
        "settled_usd_total": 0.0, "caps_usd_by_backend": {"live": 1.0},
        "invocations": [row]}))
    with pytest.raises(SystemExit, match="SPEND LEDGER CORRUPT"):
        SpendLedger(p, cap_usd=1.0, backend="live")


def test_invalid_settlement_fails_closed(tmp_path):
    led = SpendLedger(tmp_path / "ledger.json", cap_usd=1.0, backend="live")
    led.charge(0.4, "a")
    with pytest.raises(SystemExit, match="SPEND SETTLEMENT"):
        led.settle(0.4, float("nan"))
    with pytest.raises(SystemExit, match="SPEND SETTLEMENT"):
        led.settle(0.4, 0.41)


def test_request_text_must_fit_the_precharged_input_bound():
    spec = {"max_tokens": 512}
    assert worst_case_call_usd(spec, "system", "user") > 0
    with pytest.raises(SystemExit, match="REQUEST EXCEEDS SPEND RESERVATION"):
        worst_case_call_usd(spec, "", "x" * WORST_CASE_IN_TOKENS)


def test_missing_ledger_beside_live_wire_evidence_refuses(tmp_path, monkeypatch):
    import judging.run_study as RS
    monkeypatch.setattr(RS, "RESULTS", tmp_path)
    wire = tmp_path / "wire"
    wire.mkdir()
    (wire / "calls.jsonl").write_text(json.dumps({"backend": "live", "cost_usd": 0.1}) + "\n")
    with pytest.raises(SystemExit, match="SPEND LEDGER MISSING"):
        SpendLedger(tmp_path / "spend_ledger.json", cap_usd=1.0, backend="live")


def test_breaker_trips_on_low_accept_rate():
    br = Breaker()
    with pytest.raises(SystemExit, match="CIRCUIT BREAKER"):
        for i in range(BREAKER_WARMUP):
            br.record(i % 3 == 0, "unit")  # ~33% accept < 50% floor


def test_breaker_tolerates_healthy_rate():
    br = Breaker()
    for i in range(BREAKER_WARMUP * 3):
        br.record(i % 10 != 0, "unit")  # 90% accept


def test_reply_without_usage_is_refused_and_retried_not_crashed(tmp_path, monkeypatch):
    """A degraded reply with no usage accounting must be refused, then retried.

    `degraded_reason` has a "missing usage accounting" branch that could never run: the
    cost line above it multiplied `None` by a float and raised TypeError, killing the
    run after the request had been billed and before the wire row was written, so the
    refuse-and-retry the module docstring promises never happened
    (AUDIT-2026-08-08-preflight-review-3 N7).
    """
    import judging.run_study as RS
    from analysis import judge_pedagogy as JP

    monkeypatch.setattr(RS, "RESULTS", tmp_path)
    good = json.dumps({k: 3 for k in JP.FIELDS})

    class Caller:
        calls = 0

        def call(self, system, user, seed):
            Caller.calls += 1
            usage = ({"in_tokens": None, "out_tokens": None} if Caller.calls == 1
                     else {"in_tokens": 1700, "out_tokens": 52})
            return {"text": good, "response_id": f"msg_{Caller.calls}",
                    "served_model": "m", "stop_reason": "end_turn", **usage}

    spec = {"max_tokens": 512}
    ledger = SpendLedger(tmp_path / "ledger.json", cap_usd=1.0, backend="live")
    rec = RS._attempt_rep("S01|D|high|0", "sys", "user", seed=0, caller=Caller(),
                          backend="live", ledger=ledger, breaker=Breaker(), spec=spec,
                          frozen_model="m")

    assert Caller.calls == 2, "the usage-less reply was accepted instead of retried"
    assert rec is not None and rec["response_id"] == "msg_2"
    rows = [json.loads(l)
            for l in (tmp_path / "wire/calls.jsonl").read_text().splitlines()]
    assert len(rows) == 2, "the refused attempt left no wire record"
    assert rows[0]["degraded"] == "missing usage accounting"
    assert rows[0]["parsed_ok"] is False and rows[0]["scores"] is None
    # billed but unaccounted: settled at the full reservation, never as free
    assert rows[0]["cost_usd"] == pytest.approx(worst_case_call_usd(spec))
    assert ledger.summary()["this_run_settled_usd"] > worst_case_call_usd(spec)
