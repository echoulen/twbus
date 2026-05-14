# tests/test_status.py
import json
import time
from unittest.mock import patch

import pytest

from twbus.cmds import cmd_status
from twbus.catalog import _build_catalog


@pytest.fixture
def prime(fake_home, load_fixture, monkeypatch):
    monkeypatch.setenv("TDX_CLIENT_ID", "id")
    monkeypatch.setenv("TDX_CLIENT_SECRET", "sec")
    cat_dir = fake_home / ".twbus" / "catalog"
    cat_dir.mkdir(parents=True)
    cat = _build_catalog(load_fixture("stop_of_route_taipei.json"))
    (cat_dir / "Taipei.json").write_text(json.dumps(cat, ensure_ascii=False))


class _NS:
    def __init__(self, **kw):
        self.__dict__.update({"ref": [], "json": True, "refresh": False})
        self.__dict__.update(kw)


def _api_router(eta_payload, near_payload):
    def _r(path, params):
        if "EstimatedTimeOfArrival" in path:
            return eta_payload
        if "RealTimeNearStop" in path:
            return near_payload
        raise AssertionError(f"unexpected call: {path}")
    return _r


def test_status_single_ref(prime, capsys, load_fixture):
    eta = load_fixture("eta_taipei_235.json")
    near = load_fixture("realtime_near_stop_taipei.json")
    with patch("twbus.cmds.tdx_request", side_effect=_api_router(eta, near)):
        cmd_status(_NS(ref=["台北:235:公館:往台北車站"]))
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True
    entry = out["data"][0]
    assert entry["ref"] == "台北:235:公館:往台北車站"
    assert entry["etas"][0]["seconds"] == 180
    assert entry["etas"][0]["plate"] == "KKA-1234"
    assert entry["etas"][0]["status"] == "3 分鐘"


def test_status_unknown_ref_per_entry(prime, capsys, load_fixture):
    eta = load_fixture("eta_taipei_235.json")
    near = load_fixture("realtime_near_stop_taipei.json")
    with patch("twbus.cmds.tdx_request", side_effect=_api_router(eta, near)):
        cmd_status(_NS(ref=["台北:999:公館:往不知道"]))
    out = json.loads(capsys.readouterr().out)
    # Even though the only ref failed normalize, envelope is ok:true with fetchError on that entry.
    assert out["ok"] is True
    fe = out["data"][0]["fetchError"]
    assert fe["kind"] == "route_not_found"
    # The fix: extra must include suggestions
    assert "extra" in fe
    assert "suggestions" in fe["extra"]


def test_status_uses_stop_status(prime, capsys):
    """When EstimateTime is None but StopStatus distinguishes the reason,
    the per-entry status text should reflect StopStatus, not the legacy
    conflated 'unknown' label."""
    eta_rows = [{
        "RouteName": {"Zh_tw": "235"},
        "StopName": {"Zh_tw": "公館"},
        "Direction": 0,
        "EstimateTime": None,
        "PlateNumb": None,
        "StopStatus": 1,  # 尚未發車
    }]
    def _r(path, params):
        if "EstimatedTimeOfArrival" in path:
            return eta_rows
        return []
    with patch("twbus.cmds.tdx_request", side_effect=_r):
        cmd_status(_NS(ref=["台北:235:公館:往台北車站"]))
    out = json.loads(capsys.readouterr().out)
    entry = out["data"][0]
    assert entry["etas"][0]["status"] == "尚未發車"
    assert entry["etas"][0]["seconds"] is None


def test_status_long_route_partially_active(prime, capsys):
    """Long-route 6021 case: our stop has StopStatus=1 (尚未發車), but
    another stop on the same route+direction has an active ETA — the route
    is running, so the label should be '路線運行中', not '尚未發車'."""
    eta_rows = [
        {  # our target stop — no estimate yet
            "RouteName": {"Zh_tw": "235"},
            "StopName": {"Zh_tw": "公館"},
            "Direction": 0,
            "EstimateTime": None,
            "PlateNumb": None,
            "StopStatus": 1,
        },
        {  # a different stop on the same route+direction — bus is en route
            "RouteName": {"Zh_tw": "235"},
            "StopName": {"Zh_tw": "別站"},
            "Direction": 0,
            "EstimateTime": 240,
            "PlateNumb": "KKA-9999",
            "StopStatus": 0,
        },
    ]
    def _r(path, params):
        if "EstimatedTimeOfArrival" in path:
            return eta_rows
        return []
    with patch("twbus.cmds.tdx_request", side_effect=_r):
        cmd_status(_NS(ref=["台北:235:公館:往台北車站"]))
    out = json.loads(capsys.readouterr().out)
    assert out["data"][0]["etas"][0]["status"] == "路線運行中"


def test_status_eta_filter_drops_stopname(prime, capsys, load_fixture):
    """The ETA OData filter must query by (route, direction) only — without
    the StopName clause — so we get every stop's row back and can detect
    route-level activity."""
    eta = load_fixture("eta_taipei_235.json")
    near = load_fixture("realtime_near_stop_taipei.json")
    captured: list[dict] = []
    def _r(path, params):
        if "EstimatedTimeOfArrival" in path:
            captured.append(params)
            return eta
        return near
    with patch("twbus.cmds.tdx_request", side_effect=_r):
        cmd_status(_NS(ref=["台北:235:公館:往台北車站"]))
    assert captured, "EstimatedTimeOfArrival was never called"
    flt = captured[0]["$filter"]
    assert "StopName" not in flt
    assert "RouteName" in flt and "Direction" in flt


def test_status_running_route_no_local_eta(prime, capsys):
    """StopStatus=0 + EstimateTime=None means the route is running but this
    stop has no estimate yet (long-route edge case). Must not say '末班已過'."""
    eta_rows = [{
        "RouteName": {"Zh_tw": "235"},
        "StopName": {"Zh_tw": "公館"},
        "Direction": 0,
        "EstimateTime": None,
        "PlateNumb": None,
        "StopStatus": 0,
    }]
    def _r(path, params):
        if "EstimatedTimeOfArrival" in path:
            return eta_rows
        return []
    with patch("twbus.cmds.tdx_request", side_effect=_r):
        cmd_status(_NS(ref=["台北:235:公館:往台北車站"]))
    out = json.loads(capsys.readouterr().out)
    assert out["data"][0]["etas"][0]["status"] == "暫無預估"


def test_status_no_data_warning(prime, capsys):
    """ETA API returns empty -> envelope carries no_data warning."""
    def _r(path, params):
        if "EstimatedTimeOfArrival" in path:
            return []
        return []
    with patch("twbus.cmds.tdx_request", side_effect=_r):
        cmd_status(_NS(ref=["台北:235:公館:往台北車站"]))
    out = json.loads(capsys.readouterr().out)
    assert any(w["kind"] == "no_data" for w in out.get("warnings", []))


def test_status_no_ref_uses_favs(prime, capsys, load_fixture, fake_home):
    """`twbus status` with no refs should pull refs from ~/.twbus/favourites.json."""
    favs = [{"ref": "台北:235:公館:往台北車站", "label": "235 公館 往台北車站"}]
    (fake_home / ".twbus" / "favourites.json").write_text(json.dumps(favs, ensure_ascii=False))
    eta = load_fixture("eta_taipei_235.json")
    near = load_fixture("realtime_near_stop_taipei.json")
    with patch("twbus.cmds.tdx_request", side_effect=_api_router(eta, near)):
        cmd_status(_NS(ref=[]))
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True
    assert len(out["data"]) == 1
    assert out["data"][0]["ref"] == "台北:235:公館:往台北車站"


def test_status_no_ref_no_favs(prime, capsys, fake_home):
    """`twbus status` with no refs and no favs file — surface a clear warning."""
    cmd_status(_NS(ref=[]))
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True
    assert out["data"] == []
    assert any(w["kind"] == "no_favourites" for w in out.get("warnings", []))


def test_status_batches_per_city(prime, capsys, load_fixture, fake_home, monkeypatch):
    """Two refs same city -> one ETA call. Two refs different cities -> two calls."""
    monkeypatch.setenv("TDX_CLIENT_ID", "id")
    monkeypatch.setenv("TDX_CLIENT_SECRET", "sec")
    cat = _build_catalog(load_fixture("stop_of_route_taipei.json"))
    (fake_home / ".twbus" / "catalog" / "NewTaipei.json").write_text(json.dumps(cat, ensure_ascii=False))
    eta = load_fixture("eta_taipei_235.json")
    near = load_fixture("realtime_near_stop_taipei.json")
    calls = []
    def _router(path, params):
        calls.append((path, params))
        if "EstimatedTimeOfArrival" in path:
            return eta
        return near
    with patch("twbus.cmds.tdx_request", side_effect=_router):
        cmd_status(_NS(ref=["台北:235:公館:往台北車站", "新北:235:公館:往台北車站"]))
    eta_calls = [c for c in calls if "EstimatedTimeOfArrival" in c[0]]
    assert {c[0].rsplit("/", 1)[-1] for c in eta_calls} == {"Taipei", "NewTaipei"}
