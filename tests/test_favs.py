import json
from pathlib import Path

import pytest

from twbus.favs import read_favs, add_fav, list_favs, FavRecord


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


def test_remove_existing(fake_home):
    from twbus.favs import remove_fav
    add_fav(FavRecord(ref="台北:235:公館:往台北車站", label="A"))
    add_fav(FavRecord(ref="新北:802:板橋:往土城", label="B"))
    assert remove_fav("台北:235:公館:往台北車站") == "removed"
    assert [f.ref for f in read_favs()] == ["新北:802:板橋:往土城"]


def test_remove_not_found(fake_home):
    from twbus.favs import remove_fav
    add_fav(FavRecord(ref="台北:235:公館:往台北車站", label="A"))
    assert remove_fav("台北:999:nope:往哪") == "not_found"
    assert len(read_favs()) == 1


def test_remove_from_empty(fake_home):
    from twbus.favs import remove_fav
    assert remove_fav("台北:235:公館:往台北車站") == "not_found"


def test_corrupt_file_is_reset(fake_home):
    (fake_home / ".twbus").mkdir()
    (fake_home / ".twbus" / "favourites.json").write_text("not json")
    # Should not crash; treat as empty.
    assert read_favs() == []
