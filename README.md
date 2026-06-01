# Stock_AI_Agent_ETF

台灣 ETF **多 Agent 規則式指標**買賣判斷系統：以歷史 K 線與技術／量能／趨勢／風險訊號加權彙整，每日盤前透過 GitHub Actions 自動分析並 **LINE Push** 推播，無需 Webhook、ngrok。

## 支援 ETF（`config.ETF_CONFIG`）

| 代號 | 說明 |
|------|------|
| **0050** | 元大台灣50 |
| **00631L** | 元大台灣50正2（槓桿，風險 Agent 另有警示） |
| **009816** | 凱基台灣TOP50 |
| **00981A** | 統一台灣成長主動 ETF |

`python main.py` 會分析 **全部** 上述標的，並以 **Carousel** 一則 Flex 推播（4 張卡片可左右滑動）。`--etf` 可指定單一代號。

## 資料來源

| 用途 | 來源 |
|------|------|
| 歷史 OHLCV（指標計算） | Yahoo Finance（`yfinance`） |
| 卡片顯示之現價、停損停利參考 | 優先 [證交所 MIS](https://mis.twse.com.tw/) 即時行情，失敗則回退 Yahoo |

上櫃標的可在 `config.py` 為該 ETF 設定 `mis_market: "otc"` 或 `mis_ex_ch`（見檔內註解）。

## 架構

```
┌─────────────────────────────────────────────────────────┐
│                   Orchestrator                          │
│   協調並行呼叫 4 個 Agent → 彙整總分 → 最終判斷            │
└──┬─────────────┬──────────────┬────────────────┬────────┘
   ▼             ▼              ▼                ▼
📊 技術指標    📦 量能分析    🔭 趨勢動能    🛡 風險評估
MA/RSI/MACD   OBV/量比       動能/突破       ATR/回撤
布林通道       量價配合       52週位置       槓桿警示
```

## 功能

| 功能 | 說明 |
|------|------|
| 技術指標 Agent | MA 黃金/死亡交叉、RSI、MACD、布林通道 |
| 量能分析 Agent | OBV、成交量比、量價配合 |
| 趨勢動能 Agent | 52週位置、5/20日報酬、突破偵測 |
| 風險評估 Agent | ATR 波動率、最大回撤、槓桿 ETF 耗損警示 |
| LINE Push 推播 | 多檔 ETF Flex Carousel（左右滑動）；單檔為單張 Flex |
| AI 盤勢解讀 | 選用 **Anthropic Claude**：依四 Agent 結果產生繁中簡評（見 `agents/llm_commentary.py`） |

## GitHub Actions 自動排程

每週一至週五台灣時間 **14:30**（收盤後）自動執行，無需本機常駐。

支援手動觸發：GitHub repo → Actions → ETF 收盤後推播 → Run workflow

### 必要 Secrets（GitHub repo → Settings → Secrets and variables → Actions）

| Secret | 說明 |
|--------|------|
| `CHANNEL_STOCK_SECRET` | LINE Bot Channel Secret |
| `CHANNEL_STOCK_ACCESS_TOKEN` | LINE Bot Token |
| `CHANNEL_STOCK_USER_ID` | 推播目標用戶 ID |
| `ANTHROPIC_API_KEY` | Claude AI API Key（用於 Agent 分析）|

## 快速啟動（本機執行）

```bash
# 1. 安裝套件
pip install -r requirements.txt

# 2. 設定環境變數
cp .env.example .env
# 填入 CHANNEL_STOCK_SECRET、CHANNEL_STOCK_ACCESS_TOKEN、CHANNEL_STOCK_USER_ID

# 3. 立即推播全部 ETF（Carousel 左右滑動）
python main.py

# 4. 只推播單支 ETF
python main.py --etf 0050
python main.py --etf 00631L

# 5. 啟動本機排程（台灣時間週一~週五 14:30）
python main.py --schedule
```

## 檔案結構

```
├── .github/workflows/          # GitHub Actions 排程
├── main.py                     # 進入點（Push 模式）
├── config.py                   # ETF 設定與指標參數
├── data/
│   └── __init__.py             # yfinance 資料抓取
├── agents/
│   ├── base_agent.py           # 抽象基底類別
│   ├── technical_agent.py      # 技術指標 Agent
│   ├── volume_agent.py         # 量能分析 Agent
│   ├── trend_agent.py          # 趨勢動能 Agent
│   ├── risk_agent.py           # 風險評估 Agent
│   └── orchestrator.py         # 多 Agent 協調器
└── linebot_utils/
    ├── flex_card.py            # Flex Message 卡片產生器
    ├── line_push.py            # LINE 推播工具
    ├── handler.py              # ❌ 已棄用（Webhook 事件處理）
    └── rich_menu.py            # ❌ 已棄用（Rich Menu 建立）
```

## 已棄用功能

本專案已改為**純推播模式**（GitHub Actions），以下功能已停用：

| 檔案 | 說明 | 狀態 |
|------|------|------|
| `app.py` | Flask Webhook 處理 | ⚠️ 僅保留健康檢查端點 |
| `linebot_utils/handler.py` | Webhook 事件處理器 | ❌ 已停用 |
| `linebot_utils/rich_menu.py` | Rich Menu 建立工具 | ❌ 已停用 |
| `check_webhook.py` | Webhook 檢查腳本 | ❌ 已停用 |
| `test_webhook.py` | Webhook 測試腳本 | ❌ 已停用 |
| `reset_rich_menu.py` | Rich Menu 重置腳本 | ❌ 已停用 |

**備註**：系統不再接受用戶 Webhook 互動或 Rich Menu 指令，僅透過 GitHub Actions 自動推播。

> ⚠️ 本專案資訊僅供參考，不構成任何投資建議。
