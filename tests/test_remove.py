import json

import pytest

from twbus.cmds import cmd_remove
from twbus.favs import add_fav, read_favs, FavRecord


class _NS:
    def __init__(self, **kw):
        self.__dict__.update({"ref": ""})
        self.__dict__.update(kw)


@pytest.fixture
def primed_favs(fake_home):
    add_fav(FavRecord(ref="台北:235:公館:往台北車站", label="235 公館 往台北車站"))
    add_fav(FavRecord(ref="新北:802:板橋:往土城", label="802 板橋 往土城"))
    return fake_home


def test_remove_existing(primed_favs, capsys):
    cmd_remove(_NS(ref="台北:235:公館:往台北車站"))
    out = capsys.readouterr().out
    assert out.startswith("removed 台北:235:公館:往台北車站\t")
    assert [f.ref for f in read_favs()] == ["新北:802:板橋:往土城"]


def test_remove_not_in_favourites(primed_favs, capsys):
    cmd_remove(_NS(ref="台北:999:somewhere:往哪"))
    out = capsys.readouterr().out
    assert out.startswith("not in favourites: 台北:999:somewhere:往哪")
    assert len(read_favs()) == 2


def test_remove_when_empty(fake_home, capsys):
    cmd_remove(_NS(ref="台北:235:公館:往台北車站"))
    out = capsys.readouterr().out
    assert out.startswith("not in favourites:")
