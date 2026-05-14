import io
import json
import time
from unittest.mock import patch

import pytest

from _tdx import get_token, TwbusError


def _fake_urlopen(payload: dict, status: int = 200):
    """Return a context manager that mimics urllib.request.urlopen."""
    class _Resp:
        def __init__(self):
            self.status = status
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def read(self):
            return json.dumps(payload).encode("utf-8")
    return _Resp()


def test_get_token_fetches_and_caches(fake_home, monkeypatch, load_fixture):
    monkeypatch.setenv("TDX_CLIENT_ID", "id")
    monkeypatch.setenv("TDX_CLIENT_SECRET", "sec")
    fixture = load_fixture("token_resp.json")
    with patch("_tdx.urlopen", return_value=_fake_urlopen(fixture)) as mock_open:
        tok = get_token()
    assert tok == "fake-access-token-1"
    cached = json.loads((fake_home / ".twbus" / "token.json").read_text())
    assert cached["access_token"] == "fake-access-token-1"
    assert cached["expires_at"] > time.time() + 86000  # ~86400s - 60s slack
    mock_open.assert_called_once()


def test_get_token_returns_cached_when_fresh(fake_home, monkeypatch):
    monkeypatch.setenv("TDX_CLIENT_ID", "id")
    monkeypatch.setenv("TDX_CLIENT_SECRET", "sec")
    (fake_home / ".twbus").mkdir()
    (fake_home / ".twbus" / "token.json").write_text(json.dumps({
        "access_token": "cached-tok",
        "expires_at": time.time() + 1000,
    }))
    with patch("_tdx.urlopen") as mock_open:
        tok = get_token()
    assert tok == "cached-tok"
    mock_open.assert_not_called()


def test_get_token_refreshes_when_expiring(fake_home, monkeypatch, load_fixture):
    monkeypatch.setenv("TDX_CLIENT_ID", "id")
    monkeypatch.setenv("TDX_CLIENT_SECRET", "sec")
    (fake_home / ".twbus").mkdir()
    (fake_home / ".twbus" / "token.json").write_text(json.dumps({
        "access_token": "old-tok",
        "expires_at": time.time() + 30,  # within 60s slack -> refresh
    }))
    with patch("_tdx.urlopen", return_value=_fake_urlopen(load_fixture("token_resp.json"))) as mock_open:
        tok = get_token()
    assert tok == "fake-access-token-1"
    mock_open.assert_called_once()


def test_get_token_force_refresh(fake_home, monkeypatch, load_fixture):
    monkeypatch.setenv("TDX_CLIENT_ID", "id")
    monkeypatch.setenv("TDX_CLIENT_SECRET", "sec")
    (fake_home / ".twbus").mkdir()
    (fake_home / ".twbus" / "token.json").write_text(json.dumps({
        "access_token": "old-tok",
        "expires_at": time.time() + 1000,
    }))
    with patch("_tdx.urlopen", return_value=_fake_urlopen(load_fixture("token_resp.json"))) as mock_open:
        tok = get_token(force_refresh=True)
    assert tok == "fake-access-token-1"
    mock_open.assert_called_once()


def test_get_token_propagates_auth_missing(fake_home):
    # No env, no .env file -> auth_missing.
    with pytest.raises(TwbusError) as exc:
        get_token()
    assert exc.value.kind == "auth_missing"
