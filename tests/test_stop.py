import json
from unittest.mock import patch

import pytest

from twbus.cmds import cmd_stop
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
        self.__dict__.update({"ref": "", "limit": 10, "json": True, "refresh": False})
        self.__dict__.update(kw)


def test_stop_lists_routes_sorted_by_eta(prime, capsys):
    eta_payload = [
        {"RouteName": {"Zh_tw": "235"}, "StopName": {"Zh_tw": "公館"}, "Direction": 0,
         "EstimateTime": 600, "PlateNumb": None},
        {"RouteName": {"Zh_tw": "236"}, "StopName": {"Zh_tw": "公館"}, "Direction": 0,
         "EstimateTime": 120, "PlateNumb": "KKA-9"},
        {"RouteName": {"Zh_tw": "235"}, "StopName": {"Zh_tw": "公館"}, "Direction": 1,
         "EstimateTime": None, "PlateNumb": None},
    ]
    with patch("twbus.cmds.tdx_request", return_value=eta_payload):
        cmd_stop(_NS(ref="台北:公館", limit=10))
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True
    rows = out["data"]
    assert rows[0]["route"] == "236"
    assert rows[0]["seconds"] == 120
    # Unknown ETA goes last.
    assert rows[-1]["seconds"] is None


def test_stop_bad_ref(prime, capsys):
    cmd_stop(_NS(ref="garbage"))
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is False
    assert out["error"]["kind"] == "bad_ref"


def test_stop_unknown_stop_in_city(prime, capsys):
    cmd_stop(_NS(ref="台北:不存在"))
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is False
    assert out["error"]["kind"] == "stop_not_found"


def test_stop_respects_limit(prime, capsys):
    eta_payload = [
        {"RouteName": {"Zh_tw": str(i)}, "StopName": {"Zh_tw": "公館"}, "Direction": 0,
         "EstimateTime": i * 10, "PlateNumb": None}
        for i in range(20)
    ]
    with patch("twbus.cmds.tdx_request", return_value=eta_payload):
        cmd_stop(_NS(ref="台北:公館", limit=3))
    out = json.loads(capsys.readouterr().out)
    assert len(out["data"]) == 3
