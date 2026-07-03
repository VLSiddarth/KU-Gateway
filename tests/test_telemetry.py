from ku_gateway.telemetry import Telemetry

def test_update():
    tel = Telemetry()
    tel.update({"original_tokens": 100, "tokens_saved": 40, "cost_saved": 0.08, "conflicts_detected": 1})
    assert tel.total_tokens == 100