---
name: twbus
description: "查台北/新北/基隆/台中即時公車到站時間、模糊搜路線/站牌、管理 favourites。Use when user asks for Taiwan bus ETA, looks up a route or stop, or manages saved bus routes."
---

# twbus

Taiwan public bus realtime data via TDX v2 Bus API.

## When to use
- 使用者問「公車多久到」「235 在哪」「公館站有什麼車」
- 模糊搜路線或站牌名稱
- 管理常用通勤 favourite（站牌+路線+方向）

## Setup
首次使用前：
1. 安裝 CLI（讓 `twbus` 指令上 PATH）：
   ```sh
   curl -fsSL https://raw.githubusercontent.com/echoulen/twbus/main/install.sh | bash
   ```
2. 至 https://tdx.transportdata.tw/ 註冊並建立應用程式（記得在 app 後台勾選「公共運輸 → 公車」資料集）
3. 填入 `~/.twbus/.env`：
   ```
   TDX_CLIENT_ID=...
   TDX_CLIENT_SECRET=...
   ```
（或設環境變數 `TDX_CLIENT_ID` / `TDX_CLIENT_SECRET`，env var 優先）

## Subcommands cheat sheet

| Slash | 用途 | Ref 格式 |
|---|---|---|
| `/bus-search <kw>` | 跨城市模糊搜路線+站牌 | 自由關鍵字 |
| `/bus-status [ref...]` | 查下一班 ETA；無 ref 時查全部最愛 | `<city>:<route>:<stop>:往<終點>` |
| `/bus-stop <city>:<stop>` | 站牌中心：這站有哪些車要來 | `<city>:<stop>` |
| `/bus-add <ref>` | 加 favourite；ref 不全則列候選 | 同 status，或 partial |
| `/bus-remove <ref>` | 從 favourites 移除（需完整 ref） | 同 status |
| `/bus-list` | 列 favourites | — |

## CLI 用法（從自然語言對應到 `twbus` 指令）

`twbus search` 只吃**一個 keyword**：

```sh
# ✅ OK
twbus search 6021 --city 基隆 --json
twbus search 公館 --json

# ❌ 錯：多 keyword，會被當第二個位置參數
twbus search 基隆 6021 --json
twbus search 6021 公館 --json
```

當使用者用自然語言問（例如「基隆 6021」、「找台北的 235」），先**自己拆**成 `keyword` + `--city`，再呼叫 CLI。

## City codes
`--city` 同時接中文與英文：`台北 / 新北 / 基隆 / 台中` 或 `Taipei / NewTaipei / Keelung / Taichung`，輸出 JSON 內仍以中文 `city` 欄位呈現。

## Gotchas
- 第一次跑某城市的 search/status/stop 會抓 catalog（StopOfRoute）並寫入 `~/.twbus/catalog/<city>.json`，7 天 TTL；之後純走 local
- ETA API 即時、不快取
- `route_not_found` / `stop_not_on_route` 且 catalog > 1 天舊 → CLI 自動 refresh 一次再試（新路線/改站時不用使用者手動 refresh）
- `--refresh` flag 強制重抓 catalog
- 同一條路線兩個方向各算一個 favourite

## Output channels
- `/bus-search`, `/bus-status`, `/bus-stop` 用 `--json` envelope（`ok / data / warnings / error`）
- `/bus-add`, `/bus-list` 用純文字 prefix（仿 twparking）

使用者用自然語言問公車時，應**主動**跑對應的 `twbus ... --json`，把結果整理回中文表格給他，不要等使用者下 slash command。
