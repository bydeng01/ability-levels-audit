"""Spend ledger + circuit breaker guarantees (Phase 7)."""
import json
import pytest

from judging.run_study import (Breaker, SpendLedger, BREAKER_WARMUP,
                               WORST_CASE_IN_TOKENS, worst_case_call_usd)


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
    p = tmp_path / "ledger.json"
    mock = SpendLedger(p, cap_usd=1.0, backend="mock")
    mock.charge(0.9, "rehearsal")
    mock.settle(0.9, 0.0)
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
