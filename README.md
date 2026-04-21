# Stock_AI_Agent_ETF

台灣 ETF 多 Agent AI 買賣判斷系統，支援 **0050**（元大台灣50）與 **00631L**（元大台灣50正2）。每日盤前透過 GitHub Actions 自動分析並推播 LINE，採用 Push 模式，無需 Flask 或 ngrok。

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
| LINE Push 推播 | 雙 ETF Flex Message 卡片，可左右滑動比較 |

## GitHub Actions 自動排程

每週一至週五台灣時間 **08:00**（盤前）自動執行，無需本機常駐。

支援手動觸發：GitHub repo → Actions → ETF 早盤前分析推播 → Run workflow

### 必要 Secrets（GitHub repo → Settings → Secrets and variables → Actions）

| Secret | 說明 |
|--------|------|
| `CHANNEL_STOCK_SECRET` | LINE Bot Channel Secret |
| `CHANNEL_STOCK_ACCESS_TOKEN` | LINE Bot Token |
| `CHANNEL_STOCK_USER_ID` | 推播目標用戶 ID |

## 快速啟動（本機執行）

```bash
# 1. 安裝套件
pip install -r requirements.txt

# 2. 設定環境變數
cp .env.example .env
# 填入 CHANNEL_STOCK_SECRET、CHANNEL_STOCK_ACCESS_TOKEN、CHANNEL_STOCK_USER_ID

# 3. 立即推播雙 ETF
python main.py

# 4. 只推播單支 ETF
python main.py --etf 0050
python main.py --etf 00631L

# 5. 啟動本機排程（台灣時間週一~週五 08:00）
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
    └── handler.py              # 推播邏輯
```

> ⚠️ 本專案資訊僅供參考，不構成任何投資建議。
