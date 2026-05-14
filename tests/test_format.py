import json

from twbus.formatting import ok, err, with_warning, eta_status


def test_ok_minimal():
    out = ok([])
    assert json.loads(out) == {"ok": True, "data": [], "warnings": []}


def test_ok_with_warnings():
    out = ok({"x": 1}, warnings=[{"kind": "stale_catalog", "fetched_at": "2026-05-01"}])
    parsed = json.loads(out)
    assert parsed["ok"] is True
    assert parsed["data"] == {"x": 1}
    assert parsed["warnings"][0]["kind"] == "stale_catalog"


def test_err_shape():
    out = err("route_not_found", "找不到路線 999", extra={"suggestions": ["909"]})
    parsed = json.loads(out)
    assert parsed["ok"] is False
    assert parsed["error"]["kind"] == "route_not_found"
    assert parsed["error"]["message"] == "找不到路線 999"
    assert parsed["error"]["extra"]["suggestions"] == ["909"]


def test_with_warning_appends():
    envelope = json.loads(ok([1, 2]))
    envelope = with_warning(envelope, "no_data", "末班過")
    assert envelope["warnings"] == [{"kind": "no_data", "message": "末班過"}]


def test_eta_status_imminent():
    assert eta_status(45) == "即將進站"


def test_eta_status_normal():
    assert eta_status(180) == "3 分鐘"


def test_eta_status_normal_status_zero():
    # StopStatus=0 (正常) + seconds -> seconds-based label.
    assert eta_status(180, 0) == "3 分鐘"
    assert eta_status(45, 0) == "即將進站"


def test_eta_status_running_but_no_eta():
    # StopStatus=0 + None -> route is running, this stop just has no estimate yet.
    assert eta_status(None, 0) == "暫無預估"


def test_eta_status_not_departed():
    assert eta_status(None, 1) == "尚未發車"


def test_eta_status_traffic_control():
    assert eta_status(None, 2) == "交管不停駛"


def test_eta_status_last_bus_passed():
    assert eta_status(None, 3) == "末班已過"


def test_eta_status_not_operating_today():
    assert eta_status(None, 4) == "今日未營運"


def test_eta_status_unknown_status_falls_back():
    # Unknown StopStatus code -> fall back to seconds-based label.
    assert eta_status(180, 99) == "3 分鐘"
    assert eta_status(None, 99) == "暫無預估"


def test_eta_status_unknown():
    # Backward compat: no stop_status provided, seconds None -> 暫無預估.
    assert eta_status(None) == "暫無預估"
