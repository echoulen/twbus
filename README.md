<p align="left">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/logo-readme-dark.svg">
    <img src="docs/logo-readme.svg" alt="twbus" width="440">
  </picture>
</p>

CLI 查台北 / 新北 / 基隆 / 台中四個城市的即時公車到站時間（TDX v2 Bus API）。

## Install (CLI)

```sh
curl -fsSL https://raw.githubusercontent.com/echoulen/twbus/main/install.sh | bash
```

需要 Python 3.10+。裝完直接 `twbus --help`。

首次跑會在 `~/.twbus/.env` 建空骨架；至 https://tdx.transportdata.tw/ 註冊應用程式（記得勾「公共運輸 → 公車」資料集）拿到 client_id / client_secret 填進去即可。

## Install (Claude Code plugin)

本 repo 同時是一個 Claude Code marketplace：

```
/plugin marketplace add echoulen/twbus
/plugin install twbus@twbus
```

裝完即可用 slash commands：

- `/bus-search <關鍵字> [--city Taipei|NewTaipei|Keelung|Taichung]`
- `/bus-status <city>:<route>:<stop>:往<終點> [...]`
- `/bus-stop <city>:<stop>`
- `/bus-add <city>:<route>:<stop>:往<終點>`
- `/bus-list`

底層 slash command 會呼叫 `twbus` CLI（前一步裝的）。

## License

MIT
