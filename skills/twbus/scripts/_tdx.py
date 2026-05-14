"""TDX OAuth2 + HTTP helpers. Stdlib only."""
from __future__ import annotations

import os
import re
from pathlib import Path


class TwbusError(Exception):
    """Structured error carrying a kind + user-facing message + extra dict."""

    def __init__(self, kind: str, message: str, extra: dict | None = None):
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.extra = extra or {}


_DOTENV_LINE = re.compile(r"^\s*(?:export\s+)?([A-Z_][A-Z0-9_]*)\s*=\s*(.*?)\s*$")


def _parse_dotenv(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = _DOTENV_LINE.match(line)
        if not m:
            continue
        key, value = m.group(1), m.group(2)
        # Strip matching surrounding quotes; no shell expansion.
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        out[key] = value
    return out


def _state_dir() -> Path:
    return Path(os.path.expanduser("~/.twbus"))


def _env_path() -> Path:
    return _state_dir() / ".env"


def _onboarding_message() -> str:
    return (
        "TDX 憑證未設定。請至 https://tdx.transportdata.tw/ 註冊 "
        "並建立應用程式取得 client_id / client_secret，然後填入 ~/.twbus/.env："
        "\n  TDX_CLIENT_ID=...\n  TDX_CLIENT_SECRET=..."
    )


def load_credentials() -> tuple[str, str]:
    """Return (client_id, client_secret). Env vars beat ~/.twbus/.env.

    Raises TwbusError(kind='auth_missing') if neither path yields both values.
    Creates ~/.twbus/.env (chmod 600) as a skeleton when missing.
    """
    cid = os.environ.get("TDX_CLIENT_ID", "").strip()
    csec = os.environ.get("TDX_CLIENT_SECRET", "").strip()
    if cid and csec:
        return cid, csec

    env_path = _env_path()
    if env_path.exists():
        parsed = _parse_dotenv(env_path.read_text())
        cid = cid or parsed.get("TDX_CLIENT_ID", "").strip()
        csec = csec or parsed.get("TDX_CLIENT_SECRET", "").strip()
        if cid and csec:
            return cid, csec

    # Create skeleton .env so the user has somewhere to fill in.
    state = _state_dir()
    state.mkdir(parents=True, exist_ok=True)
    if not env_path.exists():
        env_path.write_text(
            "# TDX credentials — get them at https://tdx.transportdata.tw/\n"
            "TDX_CLIENT_ID=\nTDX_CLIENT_SECRET=\n"
        )
        env_path.chmod(0o600)
    raise TwbusError("auth_missing", _onboarding_message())
