import json

import pytest

from twbus.cmds import cmd_list
from twbus.favs import FavRecord, add_fav


class _NS:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_list_empty(fake_home, capsys):
    cmd_list(_NS())
    assert capsys.readouterr().out.strip() == "no favourites"


def test_list_two_entries(fake_home, capsys):
    add_fav(FavRecord(ref="台北:235:公館:往台北車站", label="235 公館 往台北車站"))
    add_fav(FavRecord(ref="新北:802:板橋:往土城", label="802 板橋 往土城"))
    cmd_list(_NS())
    lines = capsys.readouterr().out.splitlines()
    assert lines == [
        "台北:235:公館:往台北車站\t235 公館 往台北車站",
        "新北:802:板橋:往土城\t802 板橋 往土城",
    ]
