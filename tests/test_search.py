import json
import time
from unittest.mock import patch

import pytest

from _cmds import cmd_search
from _catalog import _build_catalog


@pytest.fixture
def prime_taipei(fake_home, load_fixture, monkeypatch):
    monkeypatch.setenv("TDX_CLIENT_ID", "id")
    monkeypatch.setenv("TDX_CLIENT_SECRET", "sec")
    cat_dir = fake_home / ".twbus" / "catalog"
    cat_dir.mkdir(parents=True)
    cat = _build_catalog(load_fixture("stop_of_route_taipei.json"))
    (cat_dir / "Taipei.json").write_text(json.dumps(cat, ensure_ascii=False))


class _NS:
    def __init__(self, **kw):
        self.__dict__.update({"keyword": "", "city": None, "kind": "all", "json": True, "refresh": False})
        self.__dict__.update(kw)


def test_search_exact_stop_name(prime_taipei, capsys):
    cmd_search(_NS(keyword="公館", city="Taipei", kind="all"))
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True
    stops = [r for r in out["data"] if r["kind"] == "stop"]
    assert any(s["name"] == "公館" for s in stops)
    gongguan = next(s for s in stops if s["name"] == "公館")
    assert set(gongguan["extra"]["routes_passing"]) == {"235", "236"}


def test_search_exact_route_name(prime_taipei, capsys):
    cmd_search(_NS(keyword="235", city="Taipei", kind="all"))
    out = json.loads(capsys.readouterr().out)
    routes = [r for r in out["data"] if r["kind"] == "route"]
    assert any(r["name"] == "235" for r in routes)
    r235 = next(r for r in routes if r["name"] == "235")
    assert {sr["direction"] for sr in r235["extra"]["sub_routes"]} == {0, 1}


def test_search_kind_filter(prime_taipei, capsys):
    cmd_search(_NS(keyword="235", city="Taipei", kind="route"))
    out = json.loads(capsys.readouterr().out)
    assert all(r["kind"] == "route" for r in out["data"])


def test_search_no_hits(prime_taipei, capsys):
    cmd_search(_NS(keyword="zzz", city="Taipei", kind="all"))
    out = json.loads(capsys.readouterr().out)
    assert out["data"] == []


def test_search_cross_city_loads_all(prime_taipei, monkeypatch, capsys, load_fixture):
    """When --city omitted, all four city catalogs are loaded."""
    monkeypatch.setenv("TDX_CLIENT_ID", "id")
    monkeypatch.setenv("TDX_CLIENT_SECRET", "sec")
    # Provide a tdx_request that returns the same fixture regardless of city.
    with patch("_catalog.tdx_request", return_value=load_fixture("stop_of_route_taipei.json")) as mock_req:
        cmd_search(_NS(keyword="公館", city=None, kind="all"))
        # 4 cities, but Taipei is already cached -> 3 calls.
        assert mock_req.call_count == 3
    out = json.loads(capsys.readouterr().out)
    assert any(r["city"] for r in out["data"])


def test_search_truncates_at_30(prime_taipei, monkeypatch, capsys):
    # Inject a synthetic catalog with > 30 stops named identically.
    from _catalog import _catalog_path
    big_stops_index = {f"站{i}": [{"stop_id": str(i), "routes": ["X"]}] for i in range(50)}
    cat = {"fetched_at": time.time(), "routes": [], "stops_index": big_stops_index}
    _catalog_path("Taipei").write_text(json.dumps(cat, ensure_ascii=False))
    cmd_search(_NS(keyword="站", city="Taipei", kind="all"))
    out = json.loads(capsys.readouterr().out)
    assert len(out["data"]) == 30
    assert any(w["kind"] == "truncated" for w in out["warnings"])
