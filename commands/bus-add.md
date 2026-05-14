---
description: "把 ref（city:route:stop:往終點）加入 favourites；ref 不完整則列候選"
argument-hint: "<ref>"
allowed-tools: Bash
---

User 要加的 ref：`$ARGUMENTS`

請執行：

```bash
python3 "$CLAUDE_PLUGIN_ROOT/skills/twbus/scripts/twbus.py" add $ARGUMENTS
```

輸出是純文字、用 prefix 判斷：

- `added <ref>\t<label>` → 顯示「已加入 <ref> <label>」
- `already in favourites: <ref>` → 顯示「已在 favourites 中」
- `ambiguous direction for <ref>, please pick one:` 後接候選方向（縮排兩格）→ **不是錯誤**，列方向給使用者選、請他用完整 ref 再試一次
- `multiple routes at <ref>, please pick one:` 後接候選路線 → 同上
- `route not found: <route>` 後接 fuzzy 建議 → 拼字提示
- `stop not on route: <stop>` 後接同方向所有站名 → 確認站名
- `stop not found: <stop>` 後接 fuzzy 建議 → 拼字提示
- `bad ref: <ref>` → 提示格式 `<city>:<route>:<stop>:往<終點>`，例 `台北:235:公館:往台北車站`
