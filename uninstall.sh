#!/usr/bin/env bash
# uninstall.sh — remove the twbus CLI installed via install.sh.
#
#   curl -fsSL https://raw.githubusercontent.com/echoulen/twbus/main/uninstall.sh | bash
#
# Default: removes the venv + symlink only.
# Pass --purge (or set TWBUS_PURGE=1) to also delete ~/.twbus/ (credentials,
# catalog cache, favourites).
#
# Env overrides (mirror install.sh):
#   TWBUS_INSTALL_DIR  venv location       (default: ~/.local/share/twbus)
#   TWBUS_BIN_DIR      symlink location    (default: ~/.local/bin)
#   TWBUS_PURGE        =1 to also wipe ~/.twbus/

set -euo pipefail

INSTALL_DIR="${TWBUS_INSTALL_DIR:-$HOME/.local/share/twbus}"
BIN_DIR="${TWBUS_BIN_DIR:-$HOME/.local/bin}"
STATE_DIR="$HOME/.twbus"

PURGE="${TWBUS_PURGE:-0}"
for arg in "$@"; do
  case "$arg" in
    --purge) PURGE=1 ;;
    -h|--help)
      sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "unknown arg: $arg" >&2; exit 2 ;;
  esac
done

green()  { printf '\033[32m%s\033[0m\n' "$*"; }
yellow() { printf '\033[33m%s\033[0m\n' "$*"; }

removed_anything=0

if [ -L "$BIN_DIR/twbus" ] || [ -e "$BIN_DIR/twbus" ]; then
  rm -f "$BIN_DIR/twbus"
  green "✓ removed $BIN_DIR/twbus"
  removed_anything=1
fi

if [ -d "$INSTALL_DIR" ]; then
  rm -rf "$INSTALL_DIR"
  green "✓ removed $INSTALL_DIR"
  removed_anything=1
fi

if [ "$PURGE" = "1" ]; then
  if [ -d "$STATE_DIR" ]; then
    rm -rf "$STATE_DIR"
    green "✓ removed $STATE_DIR (credentials + cache + favourites)"
    removed_anything=1
  fi
else
  if [ -d "$STATE_DIR" ]; then
    yellow "$STATE_DIR 保留（含 TDX 憑證、catalog 快取、favourites）。要一起刪：./uninstall.sh --purge"
  fi
fi

if [ "$removed_anything" = "0" ]; then
  yellow "找不到 twbus 安裝痕跡（$INSTALL_DIR / $BIN_DIR/twbus 都不存在）。"
fi
