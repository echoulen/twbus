---
description: "列出已加入的 favourites（city:route:stop:往終點）"
allowed-tools: Bash
---

請執行：

```bash
twbus list
```

輸出每行是 tab 分隔的 `<ref>\t<label>`：

- 第一行為 `no favourites` → 告知使用者尚無 favourite，建議用 `/bus-add` 加入
- 否則整理為中文清單，每筆 `<ref>  →  <label>`
