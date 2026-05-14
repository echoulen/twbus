import os
import stat
from pathlib import Path

import pytest

from _tdx import load_credentials, TwbusError


def test_env_var_wins(fake_home, monkeypatch):
    monkeypatch.setenv("TDX_CLIENT_ID", "env-id")
    monkeypatch.setenv("TDX_CLIENT_SECRET", "env-secret")
    # Even with a .env file, env vars should win.
    (fake_home / ".twbus").mkdir()
    (fake_home / ".twbus" / ".env").write_text(
        "TDX_CLIENT_ID=file-id\nTDX_CLIENT_SECRET=file-secret\n"
    )
    creds = load_credentials()
    assert creds == ("env-id", "env-secret")


def test_dotenv_used_when_no_env_var(fake_home):
    (fake_home / ".twbus").mkdir()
    (fake_home / ".twbus" / ".env").write_text(
        "# this is a comment\nTDX_CLIENT_ID=file-id\n\nTDX_CLIENT_SECRET=file-secret\n"
    )
    creds = load_credentials()
    assert creds == ("file-id", "file-secret")


def test_missing_creates_skeleton(fake_home):
    with pytest.raises(TwbusError) as excinfo:
        load_credentials()
    assert excinfo.value.kind == "auth_missing"
    env_path = fake_home / ".twbus" / ".env"
    assert env_path.exists()
    # Skeleton lines for the user to fill in.
    contents = env_path.read_text()
    assert "TDX_CLIENT_ID=" in contents
    assert "TDX_CLIENT_SECRET=" in contents
    # chmod 600
    mode = stat.S_IMODE(env_path.stat().st_mode)
    assert mode == 0o600


def test_empty_values_treated_as_missing(fake_home):
    (fake_home / ".twbus").mkdir()
    (fake_home / ".twbus" / ".env").write_text("TDX_CLIENT_ID=\nTDX_CLIENT_SECRET=\n")
    with pytest.raises(TwbusError) as excinfo:
        load_credentials()
    assert excinfo.value.kind == "auth_missing"


def test_parser_ignores_quotes_and_export_prefix(fake_home):
    (fake_home / ".twbus").mkdir()
    (fake_home / ".twbus" / ".env").write_text(
        'export TDX_CLIENT_ID="id-with-quotes"\nTDX_CLIENT_SECRET=\'sec\'\n'
    )
    creds = load_credentials()
    assert creds == ("id-with-quotes", "sec")
