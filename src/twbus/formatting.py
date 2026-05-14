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


# TDX StopStatus codes carry the authoritative reason when an ETA is missing —
# without them we'd conflate "route still running, no estimate yet" with "last bus passed".
_STOP_STATUS_LABEL = {
    1: "尚未發車",
    2: "交管不停駛",
    3: "末班已過",
    4: "今日未營運",
}


def eta_status(seconds: int | None, stop_status: int | None = None) -> str:
    if stop_status in _STOP_STATUS_LABEL:
        return _STOP_STATUS_LABEL[stop_status]
    if seconds is None:
        return "暫無預估"
    if seconds < 60:
        return "即將進站"
    minutes = seconds // 60
    return f"{minutes} 分鐘"
