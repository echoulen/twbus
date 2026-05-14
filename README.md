<p align="left">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/logo-readme-dark.svg">
    <img src="docs/logo-readme.svg" alt="twbus" width="440">
  </picture>
</p>

Taiwan public bus realtime skill plugin for [Claude Code](https://github.com/anthropics/claude-code). Wraps the [TDX v2 Bus API](https://tdx.transportdata.tw/) and exposes 5 slash commands covering Taipei / New Taipei / Keelung / Taichung.

## Features

- `/bus-search <kw>` — fuzzy search routes + stops across all four cities
- `/bus-status <ref...>` — next-bus ETA for one or more favourite refs
- `/bus-stop <city>:<stop>` — all buses approaching one stop, sorted by ETA
- `/bus-add <ref>` — save a favourite (4-tuple `city:route:stop:往終點`); lists candidates when ref is partial
- `/bus-list` — list saved favourites

## Install

The repo ships two layers — the Claude Code plugin (`.claude-plugin/`, `skills/`, `commands/`) and the underlying `twbus` CLI (Python `src/twbus/`). Install both:

1. Install the CLI so `twbus` is on PATH:
   ```sh
   curl -fsSL https://raw.githubusercontent.com/echoulen/twbus/main/install.sh | bash
   ```
   Builds an isolated venv at `~/.local/share/twbus/venv` and symlinks `twbus` into `~/.local/bin/`. No pipx required; doesn't touch system site-packages.

   Uninstall:
   ```sh
   curl -fsSL https://raw.githubusercontent.com/echoulen/twbus/main/uninstall.sh | bash
   # add --purge to also wipe ~/.twbus/ (credentials + cache + favourites)
   ```
2. Install the Claude Code plugin — inside Claude Code, run:
   ```
   /plugin marketplace add echoulen/twbus
   /plugin install twbus@twbus
   ```
3. Provide TDX credentials. Sign up at https://tdx.transportdata.tw/ and add the 公共運輸 → 公車 dataset to your app. Then either fill `~/.twbus/.env` (the first `twbus` invocation creates an empty skeleton):
   ```
   TDX_CLIENT_ID=...
   TDX_CLIENT_SECRET=...
   ```
   or export `TDX_CLIENT_ID` / `TDX_CLIENT_SECRET` as environment variables (env wins over `.env`).

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

- Python 3.10+
- TDX free-tier credentials (https://tdx.transportdata.tw/)

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
