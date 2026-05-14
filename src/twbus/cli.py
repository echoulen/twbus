"""twbus CLI dispatcher. Stdlib only."""
from __future__ import annotations

import argparse
import sys

from twbus.tdx import TwbusError
from twbus.formatting import err as fmt_err


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--json", action="store_true", help="machine-readable JSON envelope")
    p.add_argument("--refresh", action="store_true", help="force-refresh catalog cache")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="twbus", description="Taiwan bus realtime via TDX V3")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_search = sub.add_parser("search", help="fuzzy search routes and stops")
    p_search.add_argument("keyword")
    p_search.add_argument("--city", choices=["Taipei", "NewTaipei", "Keelung", "Taichung"])
    p_search.add_argument("--kind", choices=["route", "stop", "all"], default="all")
    _add_common(p_search)

    p_status = sub.add_parser("status", help="next-bus ETA for one or more favourite refs")
    p_status.add_argument("ref", nargs="+")
    _add_common(p_status)

    p_stop = sub.add_parser("stop", help="all buses approaching one stop")
    p_stop.add_argument("ref", help="<city>:<stop>")
    p_stop.add_argument("--limit", type=int, default=10)
    _add_common(p_stop)

    p_add = sub.add_parser("add", help="add a favourite")
    p_add.add_argument("ref")

    sub.add_parser("list", help="list favourites")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    ns = parser.parse_args(argv)
    try:
        if ns.cmd == "search":
            from twbus.cmds import cmd_search
            return cmd_search(ns)
        if ns.cmd == "status":
            from twbus.cmds import cmd_status
            return cmd_status(ns)
        if ns.cmd == "stop":
            from twbus.cmds import cmd_stop
            return cmd_stop(ns)
        if ns.cmd == "add":
            from twbus.cmds import cmd_add
            return cmd_add(ns)
        if ns.cmd == "list":
            from twbus.cmds import cmd_list
            return cmd_list(ns)
    except TwbusError as e:
        if getattr(ns, "json", False):
            print(fmt_err(e.kind, e.message, e.extra or None))
        else:
            print(f"[{e.kind}] {e.message}", file=sys.stderr)
        return 0  # spec §6.1: exit code stays 0; slash command branches on JSON.
    return 1


if __name__ == "__main__":
    sys.exit(main())
