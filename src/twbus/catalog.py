"""StopOfRoute catalog cache + ref normalization."""
from __future__ import annotations

import difflib
import json
import os
import time
from pathlib import Path

from twbus.tdx import request as tdx_request, TwbusError


CITY_CODES = {
    "台北": "Taipei",
    "新北": "NewTaipei",
    "基隆": "Keelung",
    "台中": "Taichung",
}
CITY_CODES_INVERSE = {v: k for k, v in CITY_CODES.items()}

CATALOG_TTL_SECONDS = 7 * 86400


def _catalog_path(city_code: str) -> Path:
    return Path(os.path.expanduser(f"~/.twbus/catalog/{city_code}.json"))


def _build_catalog(sor_payload: list[dict]) -> dict:
    """Reshape TDX StopOfRoute into our internal catalog format.

    Routes are grouped by RouteName; sub-routes are flattened by Direction.
    A stops_index keyed by StopName/Zh_tw lets /bus-stop and search work.
    """
    routes_by_name: dict[str, dict] = {}
    stops_index: dict[str, dict] = {}
    for entry in sor_payload:
        rname = entry["RouteName"]["Zh_tw"]
        rec = routes_by_name.setdefault(rname, {
            "route_name": rname,
            "route_id": entry["RouteID"],
            "sub_routes": [],
        })
        rec["sub_routes"].append({
            "direction": entry["Direction"],
            "destination": entry.get("DestinationStopNameZh", ""),
            "departure": entry.get("DepartureStopNameZh", ""),
            "stops": [
                {"stop_id": s["StopID"], "stop_name": s["StopName"]["Zh_tw"], "seq": s["StopSequence"]}
                for s in entry.get("Stops", [])
            ],
        })
        for s in entry.get("Stops", []):
            name = s["StopName"]["Zh_tw"]
            sid = s["StopID"]
            slot = stops_index.setdefault(name, [])
            existing = next((x for x in slot if x["stop_id"] == sid), None)
            if existing is None:
                slot.append({"stop_id": sid, "routes": [rname]})
            elif rname not in existing["routes"]:
                existing["routes"].append(rname)
    return {
        "fetched_at": time.time(),
        "routes": list(routes_by_name.values()),
        "stops_index": stops_index,
    }


def load_catalog(city_code: str, *, force: bool = False) -> dict:
    """Return the catalog for a city, fetching/refreshing as needed."""
    p = _catalog_path(city_code)
    cached: dict | None = None
    if p.exists():
        try:
            cached = json.loads(p.read_text())
        except (OSError, ValueError):
            cached = None
    fresh_enough = (
        cached is not None
        and not force
        and (time.time() - cached.get("fetched_at", 0)) < CATALOG_TTL_SECONDS
    )
    if fresh_enough:
        return cached

    try:
        payload = tdx_request(
            f"/api/basic/v2/Bus/StopOfRoute/City/{city_code}",
            {"$format": "JSON"},
        )
    except TwbusError:
        if cached is not None:
            cached["_stale"] = True
            return cached
        raise

    built = _build_catalog(payload)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(built, ensure_ascii=False))
    return built


def normalize_ref(ref: str) -> dict:
    """Parse '<city>:<route>:<stop>:往<dest>' into a struct ready for ETA queries."""
    segments = ref.split(":")
    if len(segments) != 4:
        raise TwbusError("bad_ref", f"ref 格式錯誤，應為 <city>:<route>:<stop>:往<終點>，得到 {ref!r}")
    city_zh, route_name, stop_name, dir_str = segments
    if city_zh not in CITY_CODES:
        raise TwbusError("bad_ref", f"未知城市 {city_zh!r}，請用 台北/新北/基隆/台中")
    if not dir_str.startswith("往") or len(dir_str) < 2:
        raise TwbusError("bad_ref", f"方向欄位 {dir_str!r} 必須以「往」開頭")
    dest_hint = dir_str[1:]
    city_code = CITY_CODES[city_zh]
    return _resolve(city_code, route_name, stop_name, dest_hint, allow_refresh=True)


def _resolve(city_code: str, route_name: str, stop_name: str, dest_hint: str, *, allow_refresh: bool) -> dict:
    cat = load_catalog(city_code)
    route = next((r for r in cat["routes"] if r["route_name"] == route_name), None)
    if route is None:
        # Try auto-refresh if cache is more than 1 day old.
        if allow_refresh and (time.time() - cat.get("fetched_at", 0)) > 86400:
            cat = load_catalog(city_code, force=True)
            return _resolve(city_code, route_name, stop_name, dest_hint, allow_refresh=False)
        suggestions = difflib.get_close_matches(
            route_name, [r["route_name"] for r in cat["routes"]], n=3, cutoff=0.0
        )
        raise TwbusError(
            "route_not_found",
            f"找不到路線 {route_name}",
            {"suggestions": suggestions, "city": CITY_CODES_INVERSE[city_code]},
        )

    # Match direction by destination string.
    candidates = [s for s in route["sub_routes"] if dest_hint in s["destination"] or s["destination"] in dest_hint]
    if len(candidates) != 1:
        raise TwbusError(
            "ambiguous_direction",
            f"無法判斷方向「往{dest_hint}」",
            {"candidates": [f"往{s['destination']}" for s in route["sub_routes"]]},
        )
    sub = candidates[0]
    stop = next((s for s in sub["stops"] if s["stop_name"] == stop_name), None)
    if stop is None:
        if allow_refresh and (time.time() - cat.get("fetched_at", 0)) > 86400:
            cat = load_catalog(city_code, force=True)
            return _resolve(city_code, route_name, stop_name, dest_hint, allow_refresh=False)
        raise TwbusError(
            "stop_not_on_route",
            f"{route_name} 在「往{dest_hint}」方向沒有 {stop_name} 這站",
            {"stops": [s["stop_name"] for s in sub["stops"]]},
        )
    return {
        "city_code": city_code,
        "route_name": route_name,
        "route_id": route["route_id"],
        "direction": sub["direction"],
        "destination": sub["destination"],
        "stop_id": stop["stop_id"],
        "stop_name": stop["stop_name"],
    }
