"""TDX OAuth2 + HTTP helpers. Stdlib only."""
from __future__ import annotations

import json
import os
import re
import ssl
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import certifi

# Use certifi's Mozilla-curated CA bundle. Some macOS/Linux system bundles
# include CA certs whose basicConstraints aren't marked critical, which
# OpenSSL 3.x rejects ("Basic Constraints of CA cert not marked critical").
_SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


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


TDX_TOKEN_URL = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
HTTP_TIMEOUT = 15  # seconds


def _token_path() -> Path:
    return _state_dir() / "token.json"


def _read_token_cache() -> dict | None:
    p = _token_path()
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return None


def _write_token_cache(access_token: str, expires_in: int) -> None:
    p = _token_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({
        "access_token": access_token,
        "expires_at": time.time() + expires_in - 60,
    }))


def _fetch_token(client_id: str, client_secret: str) -> tuple[str, int]:
    body = urlencode({
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }).encode("utf-8")
    req = Request(
        TDX_TOKEN_URL,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=HTTP_TIMEOUT, context=_SSL_CONTEXT) as resp:
            payload = json.loads(resp.read())
    except HTTPError as e:
        if e.code in (400, 401, 403):
            raise TwbusError("auth_invalid", "TDX 拒絕憑證，請檢查 ~/.twbus/.env") from e
        raise TwbusError("network", f"TDX token endpoint HTTP {e.code}") from e
    except URLError as e:
        raise TwbusError("network", f"連線 TDX 失敗：{e.reason}") from e
    return payload["access_token"], int(payload.get("expires_in", 86400))


def get_token(force_refresh: bool = False) -> str:
    """Return a valid TDX access token, refreshing if needed."""
    if not force_refresh:
        cached = _read_token_cache()
        if cached and cached.get("expires_at", 0) > time.time() + 60:
            return cached["access_token"]
    cid, csec = load_credentials()
    access_token, expires_in = _fetch_token(cid, csec)
    _write_token_cache(access_token, expires_in)
    return access_token


TDX_API_BASE = "https://tdx.transportdata.tw"


def request(path: str, params: dict) -> list | dict:
    """GET <TDX_API_BASE><path>?<params> with Bearer token. Retries once on 401."""
    if "$format" not in params:
        params = {**params, "$format": "JSON"}
    return _request_with_token(path, params, force_refresh_token=False)


def _request_with_token(path: str, params: dict, *, force_refresh_token: bool) -> list | dict:
    token = get_token(force_refresh=force_refresh_token)
    qs = urlencode(params, safe="$,'")  # keep $ and , unescaped per OData convention
    url = f"{TDX_API_BASE}{path}?{qs}"
    req = Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urlopen(req, timeout=HTTP_TIMEOUT, context=_SSL_CONTEXT) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        if e.code == 401:
            if force_refresh_token:
                raise TwbusError("auth_invalid", "TDX 拒絕憑證，請檢查 ~/.twbus/.env") from e
            return _request_with_token(path, params, force_refresh_token=True)
        if e.code == 429:
            raise TwbusError("rate_limit", "TDX rate limit，請稍後再試") from e
        body = _read_error_body(e)
        raise TwbusError(
            "network",
            f"TDX API HTTP {e.code} @ {url}" + (f" — {body}" if body else ""),
        ) from e
    except URLError as e:
        raise TwbusError("network", f"連線 TDX 失敗：{e.reason}") from e


def _read_error_body(e: HTTPError, limit: int = 300) -> str:
    try:
        return e.read().decode("utf-8", errors="replace")[:limit].strip()
    except Exception:
        return ""
