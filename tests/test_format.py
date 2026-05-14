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


def test_eta_status_unknown():
    assert eta_status(None) == "未發車或末班已過"
