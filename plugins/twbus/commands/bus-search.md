---
description: "跨台北/新北/基隆/台中模糊搜尋公車路線或站牌"
argument-hint: "<關鍵字> [--city 台北|新北|基隆|台中] [--kind route|stop|all]"
allowed-tools: Bash
---

User 給的搜尋輸入：`$ARGUMENTS`

**重要**：`twbus search` 只吃**一個** keyword 位置參數。若 `$ARGUMENTS` 含多個詞（例如「基隆 6021」），先自行拆解：

1. 若有任何詞屬於 `台北/新北/基隆/台中`（或英文 `Taipei/NewTaipei/Keelung/Taichung`）→ 抽出來放到 `--city`
2. 剩下的詞合併成單一 keyword（用最具識別性的那個，例如路線號或站名片段）
3. 不要把多個詞當成多個位置參數丟進去

範例對應：

| 使用者輸入 | 正確指令 |
|---|---|
| `基隆 6021` | `twbus search 6021 --city 基隆 --json` |
| `台北 235 公館` | `twbus search 235 --city 台北 --json`（或 `公館`，看意圖） |
| `碧嵐大地` | `twbus search 碧嵐大地 --json` |

請執行（替換成你拆好的參數）：

```bash
twbus search <keyword> [--city <city>] [--kind route|stop|all] --json
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
