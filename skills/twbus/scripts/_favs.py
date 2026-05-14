"""Favourites file I/O: list of {ref, label} dicts under ~/.twbus/favourites.json."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class FavRecord:
    ref: str
    label: str


def _path() -> Path:
    return Path(os.path.expanduser("~/.twbus/favourites.json"))


def read_favs() -> list[FavRecord]:
    p = _path()
    if not p.exists():
        return []
    try:
        raw = json.loads(p.read_text())
    except (OSError, ValueError):
        return []
    if not isinstance(raw, list):
        return []
    out: list[FavRecord] = []
    for item in raw:
        if isinstance(item, dict) and "ref" in item:
            out.append(FavRecord(ref=item["ref"], label=item.get("label", "")))
    return out


def list_favs() -> list[FavRecord]:
    return read_favs()


def add_fav(rec: FavRecord) -> str:
    """Return 'added' or 'already'."""
    favs = read_favs()
    if any(f.ref == rec.ref for f in favs):
        return "already"
    favs.append(rec)
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps([asdict(f) for f in favs], ensure_ascii=False, indent=2))
    return "added"
