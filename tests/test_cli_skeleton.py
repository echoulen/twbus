import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TWBUS = ROOT / "skills" / "twbus" / "scripts" / "twbus.py"


def run_cli(*args, env=None):
    return subprocess.run(
        [sys.executable, str(TWBUS), *args],
        capture_output=True, text=True, env=env,
    )


def test_no_args_shows_help():
    r = run_cli()
    assert r.returncode == 2  # argparse usage error
    assert "usage" in r.stderr.lower()


def test_help_lists_subcommands():
    r = run_cli("--help")
    assert r.returncode == 0
    for sub in ("search", "status", "stop", "add", "list"):
        assert sub in r.stdout


def test_unknown_subcommand():
    r = run_cli("nonsense")
    assert r.returncode == 2


def test_auth_missing_returns_json_envelope_when_json_flag(tmp_path):
    env = {"HOME": str(tmp_path), "PATH": "/usr/bin:/bin"}
    r = run_cli("search", "公館", "--json", env=env)
    assert r.returncode == 0
    parsed = json.loads(r.stdout)
    assert parsed["ok"] is False
    assert parsed["error"]["kind"] == "auth_missing"
