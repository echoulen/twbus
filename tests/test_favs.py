import json
from pathlib import Path

import pytest

from _favs import read_favs, add_fav, list_favs, FavRecord


def test_read_empty(fake_home):
    assert read_favs() == []


def test_add_writes_and_dedupes(fake_home):
    rec = FavRecord(ref="台北:235:公館:往台北車站", label="235 公館 往台北車站")
    assert add_fav(rec) == "added"
    assert add_fav(rec) == "already"
    favs = read_favs()
    assert len(favs) == 1
    assert favs[0].ref == rec.ref


def test_list_returns_records_in_order(fake_home):
    add_fav(FavRecord(ref="台北:235:公館:往台北車站", label="A"))
    add_fav(FavRecord(ref="新北:802:板橋:往土城", label="B"))
    favs = list_favs()
    assert [f.ref for f in favs] == [
        "台北:235:公館:往台北車站",
        "新北:802:板橋:往土城",
    ]


def test_corrupt_file_is_reset(fake_home):
    (fake_home / ".twbus").mkdir()
    (fake_home / ".twbus" / "favourites.json").write_text("not json")
    # Should not crash; treat as empty.
    assert read_favs() == []
