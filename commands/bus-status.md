---
description: "查 favourite ref（city:route:stop:往終點）的下一班公車 ETA"
argument-hint: "<ref> [<ref> ...]"
allowed-tools: Bash
---

User 要查的 ref：`$ARGUMENTS`

請執行：

```bash
twbus status $ARGUMENTS --json
```

每筆 `data[]` 帶 `ref / normalized / etas / fetchError?`：

| 路線 | 站牌 | 方向 | 剩餘 | 車牌 | 狀態 |

- `etas[0].seconds < 60` 顯示 ⚡「即將進站」
- `etas[0].seconds = null` 顯示「未發車或末班已過」
- `etas[1]` 存在則註明「下下班 X 分鐘」
- `fetchError.kind == "route_not_found"` → 把 `error.extra.suggestions` 列為候選、請使用者確認拼字
- `fetchError.kind == "ambiguous_direction"` → 列 `candidates` 請使用者選方向
- `fetchError.kind == "stop_not_on_route"` → 列 `extra.stops` 請使用者確認站名
- `fetchError.kind == "auth_missing"` → 把 `error.message` 原樣轉達
