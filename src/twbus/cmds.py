"""Subcommand implementations."""
from __future__ import annotations

import difflib
import time
from collections import defaultdict
from datetime import datetime

from twbus.formatting import ok as fmt_ok, err as fmt_err, eta_status
from twbus.tdx import request as tdx_request, load_credentials, TwbusError
from twbus.catalog import load_catalog, normalize_ref, CITY_CODES, CITY_CODES_INVERSE
from twbus.favs import add_fav, FavRecord, list_favs


SEARCH_LIMIT = 30


def _require_creds() -> None:
    load_credentials()  # raises TwbusError(auth_missing) when not set


def cmd_search(ns):
    _require_creds()
    cities = [ns.city] if ns.city else list(CITY_CODES.values())
    hits: list[dict] = []
    stale_cats: list[dict] = []
    for code in cities:
        cat = load_catalog(code, force=ns.refresh)
        if cat.get("_stale"):
            stale_cats.append(cat)
        _search_in_catalog(cat, code, ns.keyword.strip(), ns.kind, hits)
    total = len(hits)
    truncated = total > SEARCH_LIMIT
    if truncated:
        hits = hits[:SEARCH_LIMIT]
    warnings = []
    if truncated:
        warnings.append({"kind": "truncated", "message": f"共 {total} 筆，僅列前 {SEARCH_LIMIT}", "total": total})
    for cat in stale_cats:
        days = int((time.time() - cat["fetched_at"]) / 86400)
        warnings.append({
            "kind": "stale_catalog",
            "message": f"資料 {days} 天前",
            "fetched_at": datetime.fromtimestamp(cat["fetched_at"]).isoformat(),
        })
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
            fe = {"kind": e.kind, "message": e.message}
            if e.extra:
                fe["extra"] = e.extra
            entries.append({"ref": ref, "fetchError": fe})
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
                fe = {"kind": e.kind, "message": e.message}
                if e.extra:
                    fe["extra"] = e.extra
                entry["fetchError"] = fe
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

    warnings = []
    all_entries_with_etas = [e for e in entries if "etas" in e]
    if all_entries_with_etas and all(not e["etas"] for e in all_entries_with_etas):
        warnings.append({"kind": "no_data", "message": "可能末班過或路線停駛"})

    print(fmt_ok(entries, warnings=warnings))
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
            f"/api/basic/v2/Bus/EstimatedTimeOfArrival/City/{city_code}",
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
        f"/api/basic/v2/Bus/RealTimeNearStop/City/{city_code}",
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
    parts = ns.ref.split(":")
    if len(parts) != 2 or parts[0] not in CITY_CODES:
        print(fmt_err("bad_ref", f"ref 格式應為 <city>:<stop>，得到 {ns.ref!r}"))
        return 0
    city_zh, stop_name = parts
    city_code = CITY_CODES[city_zh]
    cat = load_catalog(city_code, force=ns.refresh)
    warnings = []
    if cat.get("_stale"):
        days = int((time.time() - cat["fetched_at"]) / 86400)
        warnings.append({
            "kind": "stale_catalog",
            "message": f"資料 {days} 天前",
            "fetched_at": datetime.fromtimestamp(cat["fetched_at"]).isoformat(),
        })
    if stop_name not in cat["stops_index"]:
        suggestions = difflib.get_close_matches(stop_name, list(cat["stops_index"].keys()), n=3, cutoff=0.5)
        print(fmt_err("stop_not_found", f"{city_zh} 找不到站牌 {stop_name}", {"suggestions": suggestions}))
        return 0
    rows = tdx_request(
        f"/api/basic/v2/Bus/EstimatedTimeOfArrival/City/{city_code}",
        {"$filter": f"StopName/Zh_tw eq '{_odata_quote(stop_name)}'", "$top": 200},
    )
    # Map (route, direction) -> destination via catalog for display labels.
    dest_map: dict[tuple[str, int], str] = {}
    for r in cat["routes"]:
        for sub in r["sub_routes"]:
            dest_map[(r["route_name"], sub["direction"])] = sub["destination"]

    data = []
    for row in rows:
        rn = row.get("RouteName", {}).get("Zh_tw")
        d = row.get("Direction")
        secs = row.get("EstimateTime")
        plate = row.get("PlateNumb")
        data.append({
            "route": rn,
            "direction": d,
            "direction_label": f"往{dest_map.get((rn, d), '?')}",
            "destination": dest_map.get((rn, d), ""),
            "seconds": secs,
            "plate": plate,
            "status": eta_status(secs),
        })
    # Sort: None (unknown ETA) goes last; otherwise ascending.
    data.sort(key=lambda x: (x["seconds"] is None, x["seconds"] if x["seconds"] is not None else 0))
    data = data[:ns.limit]
    if not data:
        warnings.append({"kind": "no_data", "message": "可能末班過或路線停駛"})
    print(fmt_ok(data, warnings=warnings))
    return 0


def cmd_add(ns):
    _require_creds()
    ref = ns.ref
    parts = ref.split(":")
    if len(parts) >= 1 and parts[0] not in CITY_CODES:
        print(f"bad ref: {ref}")
        return 0

    if len(parts) == 4:
        return _add_full(ref)
    if len(parts) == 3:
        return _add_pick_direction(ref, parts)
    if len(parts) == 2:
        return _add_pick_route(ref, parts)
    print(f"bad ref: {ref}")
    return 0


def _add_full(ref: str) -> int:
    try:
        norm = normalize_ref(ref)
    except TwbusError as e:
        return _print_add_error(ref, e)
    label = f"{norm['route_name']} {norm['stop_name']} 往{norm['destination']}"
    result = add_fav(FavRecord(ref=ref, label=label))
    if result == "added":
        print(f"added {ref}\t{label}")
    else:
        print(f"already in favourites: {ref}")
    return 0


def _add_pick_direction(ref: str, parts: list[str]) -> int:
    city_zh, route_name, stop_name = parts
    city_code = CITY_CODES[city_zh]
    cat = load_catalog(city_code)
    route = next((r for r in cat["routes"] if r["route_name"] == route_name), None)
    if route is None:
        suggestions = difflib.get_close_matches(route_name, [r["route_name"] for r in cat["routes"]], n=3, cutoff=0.5)
        print(f"route not found: {route_name}")
        for s in suggestions:
            print(f"  {s}")
        return 0
    valid_dirs = [s for s in route["sub_routes"] if any(st["stop_name"] == stop_name for st in s["stops"])]
    if not valid_dirs:
        print(f"stop not on route: {stop_name}")
        return 0
    print(f"ambiguous direction for {ref}, please pick one:")
    for s in valid_dirs:
        print(f"  往{s['destination']}")
    return 0


def _add_pick_route(ref: str, parts: list[str]) -> int:
    city_zh, stop_name = parts
    city_code = CITY_CODES[city_zh]
    cat = load_catalog(city_code)
    if stop_name not in cat["stops_index"]:
        suggestions = difflib.get_close_matches(stop_name, list(cat["stops_index"].keys()), n=3, cutoff=0.5)
        print(f"stop not found: {stop_name}")
        for s in suggestions:
            print(f"  {s}")
        return 0
    routes = sorted({rn for entry in cat["stops_index"][stop_name] for rn in entry["routes"]})
    print(f"multiple routes at {ref}, please pick one:")
    for r in routes:
        print(f"  {r}")
    return 0


def _print_add_error(ref: str, e: TwbusError) -> int:
    if e.kind == "route_not_found":
        print(f"route not found: {ref.split(':')[1]}")
        for s in e.extra.get("suggestions", []):
            print(f"  {s}")
    elif e.kind == "stop_not_on_route":
        print(f"stop not on route: {ref.split(':')[2]}")
        for s in e.extra.get("stops", []):
            print(f"  {s}")
    elif e.kind == "ambiguous_direction":
        print(f"ambiguous direction for {ref}, please pick one:")
        for s in e.extra.get("candidates", []):
            print(f"  {s}")
    elif e.kind == "bad_ref":
        print(f"bad ref: {ref}")
    else:
        print(f"error [{e.kind}]: {e.message}")
    return 0


def cmd_list(ns):
    favs = list_favs()
    if not favs:
        print("no favourites")
        return 0
    for f in favs:
        print(f"{f.ref}\t{f.label}")
    return 0
