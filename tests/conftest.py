"""Pytest config: every test gets an isolated $HOME so ~/.twbus/ never collides."""
import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    """Redirect HOME so ~/.twbus/ writes go to tmp_path."""
    monkeypatch.setenv("HOME", str(tmp_path))
    # Some stdlib uses USERPROFILE on win; HOME is enough on macOS/Linux.
    return tmp_path


@pytest.fixture
def load_fixture():
    """Return parsed JSON from tests/fixtures/<name>."""
    def _load(name):
        return json.loads((FIXTURES / name).read_text())
    return _load


@pytest.fixture(autouse=True)
def _clear_tdx_env(monkeypatch):
    """Tests opt in to creds explicitly; never leak host env."""
    monkeypatch.delenv("TDX_CLIENT_ID", raising=False)
    monkeypatch.delenv("TDX_CLIENT_SECRET", raising=False)
