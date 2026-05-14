<p align="left">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/logo-readme-dark.svg">
    <img src="docs/logo-readme.svg" alt="twbus" width="440">
  </picture>
</p>

Taiwan public bus realtime skill plugin for [Claude Code](https://github.com/anthropics/claude-code). Wraps the [TDX v2 Bus API](https://tdx.transportdata.tw/) and exposes 5 slash commands covering Taipei / New Taipei / Keelung / Taichung.

## Install

1. Install the CLI:
   ```sh
   curl -fsSL https://raw.githubusercontent.com/echoulen/twbus/main/install.sh | bash
   ```

2. Install the plugin (inside Claude Code):
   ```
   /plugin marketplace add echoulen/twbus
   /plugin install twbus@twbus
   ```

## License

MIT — see `LICENSE`.
