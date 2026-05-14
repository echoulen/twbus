# skills/twbus/scripts/_cmds.py
"""Subcommand implementations. Filled out in Tasks 10–15."""
from __future__ import annotations

import argparse

from _format import ok as fmt_ok, err as fmt_err
from _tdx import load_credentials


def _require_creds() -> None:
    load_credentials()  # raises TwbusError(auth_missing) when not set


def cmd_search(ns: argparse.Namespace) -> int:
    _require_creds()
    raise NotImplementedError("Task 10")


def cmd_status(ns: argparse.Namespace) -> int:
    _require_creds()
    raise NotImplementedError("Task 12")


def cmd_stop(ns: argparse.Namespace) -> int:
    _require_creds()
    raise NotImplementedError("Task 13")


def cmd_add(ns: argparse.Namespace) -> int:
    _require_creds()
    raise NotImplementedError("Task 14")


def cmd_list(ns: argparse.Namespace) -> int:
    raise NotImplementedError("Task 15")
