---
description: "跨台北/新北/基隆/台中模糊搜尋公車路線或站牌"
argument-hint: "<關鍵字> [--city Taipei|NewTaipei|Keelung|Taichung] [--kind route|stop|all]"
allowed-tools: Bash
---

User 給的搜尋輸入：`$ARGUMENTS`

請執行：

```bash
twbus search $ARGUMENTS --json
```

若 bash 回 `command not found: twbus` → CLI 未安裝。告知使用者跑 `curl -fsSL https://raw.githubusercontent.com/echoulen/twbus/main/install.sh | bash`，裝完後重試此 slash command，**不要繼續解析輸出**。

JSON envelope 是 `{ok, data, warnings}`：
- `ok: false` + `error.kind == "auth_missing"` → 把 `error.message` 原樣轉達給使用者，**不要**自己幫忙設環境變數
- `ok: true` + `data: []` → 顯示「沒找到符合的路線或站牌」
- `ok: true` + 有資料 → 整理成中文表格，每行 `城市 / 種類 / 名稱 / ID / 附註`：
  - `kind: route` 的附註列出方向（`往 XX / 往 YY`）
  - `kind: stop` 的附註列出該站經過的路線（最多列 5 條，多的補「等 N 條」）
- `warnings` 含 `kind: truncated` → 表尾加註「共 N 筆，僅列前 30」
- 不要再去 `cat`/`grep` 任何檔案；CLI 給的就是全部資訊
