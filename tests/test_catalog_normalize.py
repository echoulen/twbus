import json
import time
from unittest.mock import patch

import pytest

from twbus.catalog import normalize_ref
from twbus.tdx import TwbusError


@pytest.fixture
def with_taipei_catalog(fake_home, load_fixture, monkeypatch):
    monkeypatch.setenv("TDX_CLIENT_ID", "id")
    monkeypatch.setenv("TDX_CLIENT_SECRET", "sec")
    cat_dir = fake_home / ".twbus" / "catalog"
    cat_dir.mkdir(parents=True)
    from twbus.catalog import _build_catalog
    cat = _build_catalog(load_fixture("stop_of_route_taipei.json"))
    (cat_dir / "Taipei.json").write_text(json.dumps(cat, ensure_ascii=False))


def test_normalize_full_ref(with_taipei_catalog):
    out = normalize_ref("台北:235:公館:往台北車站")
    assert out["city_code"] == "Taipei"
    assert out["route_name"] == "235"
    assert out["direction"] == 0
    assert out["stop_name"] == "公館"
    assert out["stop_id"] == "101"
    assert out["destination"] == "台北車站"


def test_normalize_direction_match_other_way(with_taipei_catalog):
    out = normalize_ref("台北:235:公館:往青年公園")
    assert out["direction"] == 1


def test_normalize_route_not_found(with_taipei_catalog):
    with pytest.raises(TwbusError) as exc:
        normalize_ref("台北:999:公館:往台北車站")
    assert exc.value.kind == "route_not_found"
    assert "235" in exc.value.extra["suggestions"] or "236" in exc.value.extra["suggestions"]


def test_normalize_ambiguous_direction(with_taipei_catalog):
    with pytest.raises(TwbusError) as exc:
        normalize_ref("台北:235:公館:往不存在的地方")
    assert exc.value.kind == "ambiguous_direction"
    assert set(exc.value.extra["candidates"]) == {"往台北車站", "往青年公園"}


def test_normalize_stop_not_on_route(with_taipei_catalog):
    with pytest.raises(TwbusError) as exc:
        normalize_ref("台北:236:台北車站:往台大")
    assert exc.value.kind == "stop_not_on_route"
    # 236 stops on this direction are 景美 + 公館.
    assert set(exc.value.extra["stops"]) == {"景美", "公館"}


def test_normalize_bad_ref_format(with_taipei_catalog):
    with pytest.raises(TwbusError) as exc:
        normalize_ref("台北:235:公館")  # only 3 segments
    assert exc.value.kind == "bad_ref"


def test_normalize_unknown_city(with_taipei_catalog):
    with pytest.raises(TwbusError) as exc:
        normalize_ref("高雄:235:公館:往A")
    assert exc.value.kind == "bad_ref"


def test_normalize_direction_missing_往_prefix(with_taipei_catalog):
    with pytest.raises(TwbusError) as exc:
        normalize_ref("台北:235:公館:台北車站")  # missing 往
    assert exc.value.kind == "bad_ref"
