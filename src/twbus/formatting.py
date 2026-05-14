"""JSON envelope helpers used by every --json subcommand."""
import json
from typing import Any


def ok(data: Any, warnings: list[dict] | None = None) -> str:
    return json.dumps(
        {"ok": True, "data": data, "warnings": warnings or []},
        ensure_ascii=False,
    )


def err(kind: str, message: str, extra: dict | None = None) -> str:
    error = {"kind": kind, "message": message}
    if extra:
        error["extra"] = extra
    return json.dumps({"ok": False, "error": error}, ensure_ascii=False)


def with_warning(envelope: dict, kind: str, message: str) -> dict:
    envelope.setdefault("warnings", []).append({"kind": kind, "message": message})
    return envelope


# Specific TDX StopStatus reasons that override anything else we know — these
# are about *this stop* and aren't affected by whether the route is alive.
_SPECIFIC_STATUS_LABEL = {
    2: "交管不停駛",
    3: "末班已過",
    4: "今日未營運",
}


def eta_status(
    seconds: int | None,
    stop_status: int | None = None,
    *,
    route_active: bool = False,
) -> str:
    if stop_status in _SPECIFIC_STATUS_LABEL:
        return _SPECIFIC_STATUS_LABEL[stop_status]
    if seconds is not None:
        if seconds < 60:
            return "即將進站"
        return f"{seconds // 60} 分鐘"
    # seconds is None — disambiguate "route alive elsewhere" vs "no service".
    if route_active:
        return "路線運行中"
    if stop_status == 1:
        return "尚未發車"
    return "暫無預估"
