# twbus

Taiwan public bus realtime skill plugin for [Claude Code](https://github.com/anthropics/claude-code). Wraps the [TDX V3 API](https://tdx.transportdata.tw/) and exposes 5 slash commands covering Taipei / New Taipei / Keelung / Taichung.

## Features

- `/bus-search <kw>` — fuzzy search routes + stops across all four cities
- `/bus-status <ref...>` — next-bus ETA for one or more favourite refs
- `/bus-stop <city>:<stop>` — all buses approaching one stop, sorted by ETA
- `/bus-add <ref>` — save a favourite (4-tuple `city:route:stop:往終點`); lists candidates when ref is partial
- `/bus-list` — list saved favourites

## Install

The plugin layer (skills + slash commands) lives in this repo's `.claude-plugin/`; the underlying CLI ships separately on PyPI.

1. Install the CLI so `twbus` is on PATH:
   ```sh
   curl -fsSL https://raw.githubusercontent.com/echoulen/twbus/main/install.sh | bash
   ```
   裝法：建一個隔離 venv 在 `~/.local/share/twbus/venv`，把 `twbus` symlink 到 `~/.local/bin/`。不依賴 pipx、不污染系統 site-packages。
   解除安裝：
   ```sh
   curl -fsSL https://raw.githubusercontent.com/echoulen/twbus/main/uninstall.sh | bash
   # 也想清掉 ~/.twbus/（憑證 + 快取 + favourites）：加 --purge
   ```
2. Install the Claude Code plugin (from this marketplace):
   ```
   /plugin install <this-marketplace>/twbus
   ```

Then provide TDX credentials. The first run prints onboarding instructions and creates an empty skeleton at `~/.twbus/.env`. Fill it in:

```
TDX_CLIENT_ID=...
TDX_CLIENT_SECRET=...
```

(You can also set the same names as environment variables; env wins over `.env`.)

Sign up for credentials at https://tdx.transportdata.tw/.

## Standalone CLI

Even without Claude Code the CLI is usable:

```sh
twbus search 公館
twbus status 台北:235:公館:往台北車站
twbus stop 台北:公館
twbus add 台北:235:公館:往台北車站
twbus list
```

## Requirements

- Python 3.10+ (stdlib only at runtime)
- TDX free-tier credentials

## Storage

All state under `~/.twbus/`:

| Path | What |
|---|---|
| `.env` | TDX credentials |
| `token.json` | cached OAuth access token (auto-refreshed) |
| `catalog/<city>.json` | static route/stop catalog (7-day TTL) |
| `favourites.json` | saved 4-tuple refs |

To delete everything: `rm -rf ~/.twbus/`.

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest
```

Tests use `unittest.mock.patch('urllib.request.urlopen')` against recorded JSON fixtures in `tests/fixtures/`. No network calls in CI. Live integration tests are opt-in via `pytest -m integration` (requires `TDX_CLIENT_ID` env).

## License

MIT — see `LICENSE`.
