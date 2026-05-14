---
description: "查某站牌目前有哪些公車要來（按 ETA 由近至遠）"
argument-hint: "<city>:<stop> [--limit 10]"
allowed-tools: Bash
---

User 要查的站牌：`$ARGUMENTS`

請執行：

```bash
twbus stop $ARGUMENTS --json
```

`data[]` 每筆 `{route, direction_label, destination, seconds, plate, status}`，已按 ETA 排序。

| 路線 | 方向 | 剩餘 | 車牌 |

- `seconds < 60` → 「即將進站」
- `seconds = null` → 「—」並排在表尾
- `error.kind == "stop_not_found"` → 列 `error.extra.suggestions` 請使用者確認站名
- `error.kind == "bad_ref"` → 提示格式為 `城市:站名`，例如 `台北:公館`
