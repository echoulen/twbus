import json
from unittest.mock import patch

import pytest

from twbus.cmds import cmd_add
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
        self.__dict__.update({"ref": ""})
        self.__dict__.update(kw)


def test_add_full_ref(prime, capsys, fake_home):
    cmd_add(_NS(ref="台北:235:公館:往台北車站"))
    captured = capsys.readouterr().out
    assert captured.startswith("added 台北:235:公館:往台北車站\t")
    favs = json.loads((fake_home / ".twbus" / "favourites.json").read_text())
    assert favs[0]["ref"] == "台北:235:公館:往台北車站"


def test_add_already(prime, capsys):
    cmd_add(_NS(ref="台北:235:公館:往台北車站"))
    capsys.readouterr()
    cmd_add(_NS(ref="台北:235:公館:往台北車站"))
    assert capsys.readouterr().out.startswith("already in favourites: 台北:235:公館:往台北車站")


def test_add_partial_missing_direction(prime, capsys):
    """ref = 台北:235:公館  -> ambiguous direction with candidates."""
    cmd_add(_NS(ref="台北:235:公館"))
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "ambiguous direction for 台北:235:公館, please pick one:"
    candidates = {line.strip() for line in out[1:]}
    assert candidates == {"往台北車站", "往青年公園"}


def test_add_partial_missing_route(prime, capsys):
    """ref = 台北:公館  -> list routes passing through 公館."""
    cmd_add(_NS(ref="台北:公館"))
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "multiple routes at 台北:公館, please pick one:"
    routes = {line.strip() for line in out[1:]}
    assert routes == {"235", "236"}


def test_add_route_not_found(prime, capsys):
    cmd_add(_NS(ref="台北:999:公館:往台北車站"))
    out = capsys.readouterr().out
    assert out.startswith("route not found: 999")


def test_add_stop_not_on_route(prime, capsys):
    cmd_add(_NS(ref="台北:236:台北車站:往台大"))
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "stop not on route: 台北車站"


def test_add_stop_not_found_in_partial(prime, capsys):
    cmd_add(_NS(ref="台北:不存在"))
    out = capsys.readouterr().out
    assert out.startswith("stop not found: 不存在")
