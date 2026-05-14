# skills/twbus/scripts/_cmds.py
"""Subcommand implementations. Filled out across Tasks 10–15."""
from __future__ import annotations

import argparse
import difflib

from _format import ok as fmt_ok, err as fmt_err
from _tdx import load_credentials
from _catalog import load_catalog, CITY_CODES, CITY_CODES_INVERSE


SEARCH_LIMIT = 30


def _require_creds() -> None:
    load_credentials()  # raises TwbusError(auth_missing) when not set


def cmd_search(ns):
    _require_creds()
    cities = [ns.city] if ns.city else list(CITY_CODES.values())
    hits: list[dict] = []
    for code in cities:
        cat = load_catalog(code, force=ns.refresh)
        _search_in_catalog(cat, code, ns.keyword.strip(), ns.kind, hits)
    total = len(hits)
    truncated = total > SEARCH_LIMIT
    if truncated:
        hits = hits[:SEARCH_LIMIT]
    warnings = []
    if truncated:
        warnings.append({"kind": "truncated", "message": f"共 {total} 筆，僅列前 {SEARCH_LIMIT}", "total": total})
    print(fmt_ok(hits, warnings=warnings))
    return 0


def _search_in_catalog(cat: dict, city_code: str, kw: str, kind: str, hits: list) -> None:
    city_zh = CITY_CODES_INVERSE[city_code]
    if kind in ("route", "all"):
        names = [r["route_name"] for r in cat["routes"]]
        for r in cat["routes"]:
            if _matches(r["route_name"], kw, names):
                hits.append({
                    "kind": "route",
                    "city": city_zh,
                    "id": r["route_id"],
                    "name": r["route_name"],
                    "extra": {"sub_routes": [
                        {"direction": s["direction"], "destination": s["destination"]}
                        for s in r["sub_routes"]
                    ]},
                })
    if kind in ("stop", "all"):
        stop_names = list(cat["stops_index"].keys())
        for name, entries in cat["stops_index"].items():
            if _matches(name, kw, stop_names):
                for entry in entries:
                    hits.append({
                        "kind": "stop",
                        "city": city_zh,
                        "id": entry["stop_id"],
                        "name": name,
                        "extra": {"routes_passing": list(entry["routes"])},
                    })


def _matches(candidate: str, kw: str, pool: list[str]) -> bool:
    if not kw:
        return False
    if kw in candidate:
        return True
    # difflib fallback for typos when kw is at least 2 chars.
    return len(kw) >= 2 and candidate in difflib.get_close_matches(kw, pool, n=10, cutoff=0.6)


# Stubs for later tasks
def cmd_status(ns):
    _require_creds()
    raise NotImplementedError("Task 12")


def cmd_stop(ns):
    _require_creds()
    raise NotImplementedError("Task 13")


def cmd_add(ns):
    _require_creds()
    raise NotImplementedError("Task 14")


def cmd_list(ns):
    raise NotImplementedError("Task 15")
