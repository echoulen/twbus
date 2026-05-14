# tests/test_status.py
import json
import time
from unittest.mock import patch

import pytest

from _cmds import cmd_status
from _catalog import _build_catalog


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
    with patch("_cmds.tdx_request", side_effect=_api_router(eta, near)):
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
    with patch("_cmds.tdx_request", side_effect=_api_router(eta, near)):
        cmd_status(_NS(ref=["台北:999:公館:往不知道"]))
    out = json.loads(capsys.readouterr().out)
    # Even though the only ref failed normalize, envelope is ok:true with fetchError on that entry.
    assert out["ok"] is True
    assert out["data"][0]["fetchError"]["kind"] == "route_not_found"


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
    with patch("_cmds.tdx_request", side_effect=_router):
        cmd_status(_NS(ref=["台北:235:公館:往台北車站", "新北:235:公館:往台北車站"]))
    eta_calls = [c for c in calls if "EstimatedTimeOfArrival" in c[0]]
    assert {c[0].rsplit("/", 1)[-1] for c in eta_calls} == {"Taipei", "NewTaipei"}
