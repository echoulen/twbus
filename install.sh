#!/usr/bin/env bash
# install.sh — install twbus CLI from the GitHub repo.
#
#   curl -fsSL https://raw.githubusercontent.com/echoulen/twbus/main/install.sh | bash
#
# Creates an isolated venv at ~/.local/share/twbus/venv and symlinks the
# `twbus` binary into ~/.local/bin/. No pipx required; avoids PEP 668
# breakage on Homebrew/Debian Python.
#
# Env overrides:
#   TWBUS_REPO         git URL to install from
#                      (default: https://github.com/echoulen/twbus.git)
#   TWBUS_REF          branch/tag/sha to pin               (default: main)
#   TWBUS_INSTALL_DIR  where the venv lives    (default: ~/.local/share/twbus)
#   TWBUS_BIN_DIR      where the `twbus` symlink goes  (default: ~/.local/bin)
#   PYTHON             python3 binary                   (default: python3)

set -euo pipefail

REPO_URL="${TWBUS_REPO:-https://github.com/echoulen/twbus.git}"
REF="${TWBUS_REF:-main}"
PY="${PYTHON:-python3}"
INSTALL_DIR="${TWBUS_INSTALL_DIR:-$HOME/.local/share/twbus}"
BIN_DIR="${TWBUS_BIN_DIR:-$HOME/.local/bin}"

red()    { printf '\033[31m%s\033[0m\n' "$*" >&2; }
green()  { printf '\033[32m%s\033[0m\n' "$*"; }
yellow() { printf '\033[33m%s\033[0m\n' "$*"; }

# 1. Python 3.10+ check
if ! command -v "$PY" >/dev/null 2>&1; then
  red "python3 not found. Install Python 3.10+ first."
  exit 1
fi
ver=$("$PY" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')
maj=${ver%.*}; min=${ver#*.}
if [ "$maj" -lt 3 ] || { [ "$maj" -eq 3 ] && [ "$min" -lt 10 ]; }; then
  red "Python 3.10+ required (found $ver)."
  exit 1
fi

# 2. Build an isolated venv (idempotent: nuke any previous one first)
VENV="$INSTALL_DIR/venv"
yellow "Setting up venv at $VENV ..."
mkdir -p "$INSTALL_DIR"
rm -rf "$VENV"
"$PY" -m venv "$VENV"
"$VENV/bin/pip" install --quiet --upgrade pip

# 3. Install twbus into the venv (from git)
yellow "Installing twbus from $REPO_URL@$REF ..."
"$VENV/bin/pip" install --quiet "git+${REPO_URL}@${REF}"

# 4. Symlink CLI onto $BIN_DIR
mkdir -p "$BIN_DIR"
ln -sf "$VENV/bin/twbus" "$BIN_DIR/twbus"
green "✓ twbus installed: $BIN_DIR/twbus -> $VENV/bin/twbus"

# 5. PATH hint
case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *)
    yellow "$BIN_DIR 不在你的 PATH 上。把這行加到 ~/.zshrc 或 ~/.bashrc："
    echo "  export PATH=\"$BIN_DIR:\$PATH\""
    ;;
esac

cat <<'EOF'

下一步：
  1. twbus search 公館               # 第一次會在 ~/.twbus/.env 建立空骨架
  2. 至 https://tdx.transportdata.tw/ 註冊應用程式取得 client_id / client_secret
  3. 填入 ~/.twbus/.env：
       TDX_CLIENT_ID=...
       TDX_CLIENT_SECRET=...
  4. 再跑一次 twbus search 公館 確認

更新： curl -fsSL https://raw.githubusercontent.com/echoulen/twbus/main/install.sh | bash
解除： curl -fsSL https://raw.githubusercontent.com/echoulen/twbus/main/uninstall.sh | bash
       （加 `--purge` 也會刪 ~/.twbus/ 內的憑證與快取）
EOF
