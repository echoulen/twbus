import json
import time
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError

import pytest

from twbus.tdx import request, TwbusError


def _resp(payload, status=200):
    class _R:
        def __init__(self):
            self.status = status
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def read(self):
            return json.dumps(payload).encode("utf-8")
    return _R()


@pytest.fixture
def primed_token(fake_home, monkeypatch):
    monkeypatch.setenv("TDX_CLIENT_ID", "id")
    monkeypatch.setenv("TDX_CLIENT_SECRET", "sec")
    (fake_home / ".twbus").mkdir()
    (fake_home / ".twbus" / "token.json").write_text(json.dumps({
        "access_token": "tok-1",
        "expires_at": time.time() + 1000,
    }))


def test_request_uses_bearer_and_returns_json(primed_token):
    with patch("twbus.tdx.urlopen", return_value=_resp([{"a": 1}])) as mock_open:
        data = request("/api/basic/v3/Bus/StopOfRoute/City/Taipei", {"$top": 30})
    assert data == [{"a": 1}]
    sent: MagicMock = mock_open.call_args.args[0]
    auth = sent.get_header("Authorization")
    assert auth == "Bearer tok-1"
    # URL has the query string ($ kept literal per OData convention, not percent-encoded).
    assert "$top=30" in sent.full_url


def test_request_retries_once_on_401(primed_token, load_fixture):
    # First call 401; refresh issues new token; second call 200.
    err = HTTPError("u", 401, "unauth", {}, None)
    new_tok_resp = _resp(load_fixture("token_resp.json"))
    success_resp = _resp([{"ok": True}])

    def side_effect(*a, **kw):
        if not hasattr(side_effect, "n"):
            side_effect.n = 0
        side_effect.n += 1
        if side_effect.n == 1:
            raise err
        if side_effect.n == 2:
            return new_tok_resp     # token refresh
        return success_resp          # retried API call

    with patch("twbus.tdx.urlopen", side_effect=side_effect):
        data = request("/api/basic/v3/Bus/X/City/Taipei", {})
    assert data == [{"ok": True}]
    assert side_effect.n == 3


def test_request_raises_auth_invalid_after_double_401(primed_token):
    err = HTTPError("u", 401, "unauth", {}, None)

    def side_effect(*a, **kw):
        if not hasattr(side_effect, "n"):
            side_effect.n = 0
        side_effect.n += 1
        if side_effect.n == 2:
            return _resp({"access_token": "new", "expires_in": 86400})
        raise err

    with patch("twbus.tdx.urlopen", side_effect=side_effect):
        with pytest.raises(TwbusError) as exc:
            request("/x", {})
    assert exc.value.kind == "auth_invalid"


def test_request_429_raises_rate_limit(primed_token):
    err = HTTPError("u", 429, "too many", {}, None)
    with patch("twbus.tdx.urlopen", side_effect=err):
        with pytest.raises(TwbusError) as exc:
            request("/x", {})
    assert exc.value.kind == "rate_limit"


def test_request_network_error(primed_token):
    from urllib.error import URLError
    with patch("twbus.tdx.urlopen", side_effect=URLError("timed out")):
        with pytest.raises(TwbusError) as exc:
            request("/x", {})
    assert exc.value.kind == "network"
