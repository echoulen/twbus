"""StopOfRoute catalog cache + ref normalization."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from _tdx import request as tdx_request, TwbusError


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
            f"/api/basic/v3/Bus/StopOfRoute/City/{city_code}",
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
