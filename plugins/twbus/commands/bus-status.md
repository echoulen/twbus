---
description: "查 favourite ref（city:route:stop:往終點）的下一班公車 ETA；不帶參數則查所有最愛"
argument-hint: "[<ref> ...]"
allowed-tools: Bash
---

User 要查的 ref：`$ARGUMENTS`（空字串代表「查全部最愛」）

請執行：

```bash
twbus status $ARGUMENTS --json
```

若 bash 回 `command not found: twbus` → CLI 未安裝。告知使用者跑 `curl -fsSL https://raw.githubusercontent.com/echoulen/twbus/main/install.sh | bash`，裝完後重試此 slash command，**不要繼續解析輸出**。

每筆 `data[]` 帶 `ref / normalized / etas / fetchError?`：

| 路線 | 站牌 | 方向 | 剩餘 | 車牌 | 狀態 |

`etas[].status` 由 CLI 決定，直接照搬即可。常見值：
- `即將進站` / `N 分鐘` — 正常 ETA（`seconds < 60` 可加 ⚡ 圖示）
- `路線運行中` — 路線上有車跑，但本站尚未推估到
- `尚未發車` — 整條路線今日這個方向尚未派車
- `暫無預估` — TDX 沒回估算且狀態未明
- `末班已過` / `今日未營運` / `交管不停駛` — 對應 StopStatus

其他規則：
- `etas[1]` 存在則註明「下下班 X 分鐘」
- `warnings[].kind == "no_favourites"` → 提示使用者用 `/bus-add` 加最愛
- `fetchError.kind == "route_not_found"` → 把 `error.extra.suggestions` 列為候選、請使用者確認拼字
- `fetchError.kind == "ambiguous_direction"` → 列 `candidates` 請使用者選方向
- `fetchError.kind == "stop_not_on_route"` → 列 `extra.stops` 請使用者確認站名
- `fetchError.kind == "auth_missing"` → 把 `error.message` 原樣轉達
