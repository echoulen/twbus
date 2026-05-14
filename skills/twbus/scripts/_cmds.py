# skills/twbus/scripts/_cmds.py
"""Subcommand implementations. Filled out across Tasks 10–15."""
from __future__ import annotations

import argparse
import difflib
from collections import defaultdict

from _format import ok as fmt_ok, err as fmt_err, eta_status
from _tdx import request as tdx_request, load_credentials, TwbusError
from _catalog import load_catalog, normalize_ref, CITY_CODES, CITY_CODES_INVERSE


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


# ── status ──────────────────────────────────────────────────────────────────

def _odata_quote(s: str) -> str:
    return s.replace("'", "''")


def cmd_status(ns):
    _require_creds()
    entries = []
    by_city: dict[str, list[dict]] = defaultdict(list)
    for ref in ns.ref:
        try:
            norm = normalize_ref(ref)
        except TwbusError as e:
            entries.append({"ref": ref, "fetchError": {"kind": e.kind, "message": e.message}})
            continue
        entry = {"ref": ref, "normalized": norm, "etas": []}
        entries.append(entry)
        by_city[norm["city_code"]].append(entry)

    for city_code, city_entries in by_city.items():
        try:
            eta_rows = _fetch_etas(city_code, city_entries)
            plate_map = _fetch_plates(city_code, city_entries)
        except TwbusError as e:
            for entry in city_entries:
                entry["fetchError"] = {"kind": e.kind, "message": e.message}
            continue
        for entry in city_entries:
            norm = entry["normalized"]
            matched = [
                row for row in eta_rows
                if row.get("RouteName", {}).get("Zh_tw") == norm["route_name"]
                and row.get("StopName", {}).get("Zh_tw") == norm["stop_name"]
                and row.get("Direction") == norm["direction"]
            ]
            matched.sort(key=lambda r: (r.get("EstimateTime") is None, r.get("EstimateTime") or 0))
            etas = []
            for row in matched[:3]:
                secs = row.get("EstimateTime")
                plate = row.get("PlateNumb") or plate_map.get((norm["route_name"], norm["direction"]))
                etas.append({"plate": plate, "seconds": secs, "status": eta_status(secs)})
            entry["etas"] = etas

    print(fmt_ok(entries))
    return 0


def _fetch_etas(city_code: str, city_entries: list[dict]) -> list[dict]:
    clauses: set[str] = set()
    for entry in city_entries:
        n = entry["normalized"]
        clauses.add(
            f"(RouteName/Zh_tw eq '{_odata_quote(n['route_name'])}' "
            f"and StopName/Zh_tw eq '{_odata_quote(n['stop_name'])}' "
            f"and Direction eq {n['direction']})"
        )
    chunks = list(_chunks(sorted(clauses), 20))
    out: list[dict] = []
    for chunk in chunks:
        out.extend(tdx_request(
            f"/api/basic/v3/Bus/EstimatedTimeOfArrival/City/{city_code}",
            {"$filter": " or ".join(chunk), "$top": 200},
        ))
    return out


def _fetch_plates(city_code: str, city_entries: list[dict]) -> dict[tuple[str, int], str]:
    """Return {(route_name, direction): plate} from RealTimeNearStop, when bus is near."""
    keys = {(e["normalized"]["route_name"], e["normalized"]["direction"]) for e in city_entries}
    if not keys:
        return {}
    clauses = [
        f"(RouteName/Zh_tw eq '{_odata_quote(rn)}' and Direction eq {d})"
        for rn, d in keys
    ]
    rows = tdx_request(
        f"/api/basic/v3/Bus/RealTimeNearStop/City/{city_code}",
        {"$filter": " or ".join(clauses), "$top": 200},
    )
    out: dict[tuple[str, int], str] = {}
    for row in rows:
        rn = row.get("RouteName", {}).get("Zh_tw")
        d = row.get("Direction")
        plate = row.get("PlateNumb")
        if rn and plate:
            out[(rn, d)] = plate
    return out


def _chunks(items, n: int):
    for i in range(0, len(items), n):
        yield items[i:i + n]


def cmd_stop(ns):
    _require_creds()
    raise NotImplementedError("Task 13")


def cmd_add(ns):
    _require_creds()
    raise NotImplementedError("Task 14")


def cmd_list(ns):
    raise NotImplementedError("Task 15")
