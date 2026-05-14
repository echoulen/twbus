---
description: "從 favourites 移除一筆 ref（需完整 city:route:stop:往終點）"
argument-hint: "<ref>"
allowed-tools: Bash
---

User 要移除的 ref：`$ARGUMENTS`

請執行：

```bash
twbus remove $ARGUMENTS
```

若 bash 回 `command not found: twbus` → CLI 未安裝。告知使用者跑 `curl -fsSL https://raw.githubusercontent.com/echoulen/twbus/main/install.sh | bash`，裝完後重試此 slash command，**不要繼續解析輸出**。

輸出是純文字、用 prefix 判斷：

- `removed <ref>\t<label>` → 顯示「已移除 <ref> <label>」
- `not in favourites: <ref>` → 顯示「該 ref 不在 favourites 中；可先 `/bus-list` 查看」

`remove` 只接**完整 ref**（exact match）。若使用者給的不完整或拼錯，先建議他跑 `/bus-list` 取得正確字串再來。
