import json
import time
from unittest.mock import patch

import pytest

from twbus.catalog import load_catalog, CITY_CODES


def test_city_codes_mapping():
    assert CITY_CODES == {"台北": "Taipei", "新北": "NewTaipei", "基隆": "Keelung", "台中": "Taichung"}


def test_load_catalog_fetches_when_cache_missing(fake_home, monkeypatch, load_fixture):
    monkeypatch.setenv("TDX_CLIENT_ID", "id")
    monkeypatch.setenv("TDX_CLIENT_SECRET", "sec")
    (fake_home / ".twbus").mkdir()
    (fake_home / ".twbus" / "token.json").write_text(json.dumps({
        "access_token": "tok",
        "expires_at": time.time() + 1000,
    }))
    sor = load_fixture("stop_of_route_taipei.json")
    with patch("twbus.catalog.tdx_request", return_value=sor) as mock_req:
        cat = load_catalog("Taipei")
    mock_req.assert_called_once()
    # Catalog file written.
    cache = json.loads((fake_home / ".twbus" / "catalog" / "Taipei.json").read_text())
    assert "fetched_at" in cache
    assert any(r["route_name"] == "235" for r in cache["routes"])
    # Stops index has 公館 -> {235, 236}.
    routes_at_gongguan = sorted(cache["stops_index"]["公館"][0]["routes"])
    assert routes_at_gongguan == ["235", "236"]
    # Returned dict shape.
    assert cat["fetched_at"] == cache["fetched_at"]


def test_load_catalog_uses_cache_when_fresh(fake_home, monkeypatch):
    monkeypatch.setenv("TDX_CLIENT_ID", "id")
    monkeypatch.setenv("TDX_CLIENT_SECRET", "sec")
    cat_dir = fake_home / ".twbus" / "catalog"
    cat_dir.mkdir(parents=True)
    (cat_dir / "Taipei.json").write_text(json.dumps({
        "fetched_at": time.time(),  # fresh
        "routes": [{"route_name": "X"}],
        "stops_index": {}
    }))
    with patch("twbus.catalog.tdx_request") as mock_req:
        cat = load_catalog("Taipei")
    mock_req.assert_not_called()
    assert cat["routes"][0]["route_name"] == "X"


def test_load_catalog_refreshes_when_expired(fake_home, monkeypatch, load_fixture):
    monkeypatch.setenv("TDX_CLIENT_ID", "id")
    monkeypatch.setenv("TDX_CLIENT_SECRET", "sec")
    (fake_home / ".twbus").mkdir()
    (fake_home / ".twbus" / "token.json").write_text(json.dumps({
        "access_token": "tok",
        "expires_at": time.time() + 1000,
    }))
    cat_dir = fake_home / ".twbus" / "catalog"
    cat_dir.mkdir(parents=True)
    (cat_dir / "Taipei.json").write_text(json.dumps({
        "fetched_at": time.time() - (8 * 86400),  # 8 days ago, > 7 day TTL
        "routes": [],
        "stops_index": {}
    }))
    with patch("twbus.catalog.tdx_request", return_value=load_fixture("stop_of_route_taipei.json")) as mock_req:
        cat = load_catalog("Taipei")
    mock_req.assert_called_once()
    assert any(r["route_name"] == "235" for r in cat["routes"])


def test_load_catalog_force_refresh(fake_home, monkeypatch, load_fixture):
    monkeypatch.setenv("TDX_CLIENT_ID", "id")
    monkeypatch.setenv("TDX_CLIENT_SECRET", "sec")
    cat_dir = fake_home / ".twbus" / "catalog"
    cat_dir.mkdir(parents=True)
    (cat_dir / "Taipei.json").write_text(json.dumps({
        "fetched_at": time.time(),
        "routes": [],
        "stops_index": {}
    }))
    with patch("twbus.catalog.tdx_request", return_value=load_fixture("stop_of_route_taipei.json")) as mock_req:
        load_catalog("Taipei", force=True)
    mock_req.assert_called_once()


def test_load_catalog_falls_back_to_stale(fake_home, monkeypatch):
    from twbus.tdx import TwbusError
    monkeypatch.setenv("TDX_CLIENT_ID", "id")
    monkeypatch.setenv("TDX_CLIENT_SECRET", "sec")
    cat_dir = fake_home / ".twbus" / "catalog"
    cat_dir.mkdir(parents=True)
    (cat_dir / "Taipei.json").write_text(json.dumps({
        "fetched_at": time.time() - (10 * 86400),
        "routes": [{"route_name": "stale"}],
        "stops_index": {}
    }))
    with patch("twbus.catalog.tdx_request", side_effect=TwbusError("network", "down")):
        cat = load_catalog("Taipei")
    assert cat["routes"][0]["route_name"] == "stale"
    assert cat.get("_stale") is True
