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


def eta_status(seconds: int | None) -> str:
    if seconds is None:
        return "未發車或末班已過"
    if seconds < 60:
        return "即將進站"
    minutes = seconds // 60
    return f"{minutes} 分鐘"
