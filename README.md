# Stock_AI_Agent_ETF

台灣 ETF **多 Agent 規則式指標**買賣判斷系統：以歷史 K 線與技術／量能／趨勢／風險訊號加權彙整，每日盤前透過 GitHub Actions 自動分析並 **LINE Push** 推播，無需 Webhook、ngrok。

## 支援 ETF（`config.ETF_CONFIG`）

| 代號 | 說明 |
|------|------|
| **0050** | 元大台灣50 |
| **00631L** | 元大台灣50正2（槓桿，風險 Agent 另有警示） |
| **009816** | 凱基台灣TOP50 |
| **00981A** | 統一台灣成長主動 ETF |

`python main.py` 會分析 **全部** 上述標的，並以 **Carousel** 一則 Flex 推播（可左右滑動）。`--etf` 可指定單一代號。

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
| LINE Push 推播 | 多檔 ETF Flex Carousel；單檔為單張 Flex |
| AI 盤勢解讀 | 選用 **Anthropic Claude**：依四 Agent 結果產生繁中簡評（見 `agents/llm_commentary.py`） |

## GitHub Actions 自動排程

每週一至週五台灣時間 **08:00**（盤前）自動執行，無需本機常駐。

支援手動觸發：GitHub repo → **Actions** → **ETF 早盤推播** → **Run workflow**

### 必要 Secrets（GitHub repo → Settings → Secrets and variables → Actions）

| Secret | 說明 |
|--------|------|
| `CHANNEL_STOCK_SECRET` | LINE Bot Channel Secret |
| `CHANNEL_STOCK_ACCESS_TOKEN` | LINE Channel access token |
| `CHANNEL_STOCK_USER_ID` | 推播目標用戶 ID（單人） |
| `ANTHROPIC_API_KEY` | 選填；啟用 Flex 卡片內 **AI 盤勢解讀**（未設定則略過） |

若部署環境會讀取 SQLite 訂閱表或多使用者變數，請一併設定該環境所需變數（本機可參考 `linebot_utils/line_push.py` 的讀取順序）。本機亦可使用 `CHANNEL_STOCK_Claude_Token` 作為 Anthropic key（與 `ANTHROPIC_API_KEY` 擇一）。

**本機執行與 GitHub Secret：**  
Repository 裡設定的 Secret **只會在 Actions 跑 workflow 時**注入成環境變數，**不會**自動出現在你電腦上。要在本機跑 `python main.py`，請在專案根目錄建立 `.env`，變數名稱與 Secret **一致**（例如 `CHANNEL_STOCK_ACCESS_TOKEN`），程式會從與 `main.py` 同層的 `.env` 載入，與目前工作目錄無關。

**從 Google Drive 取得 `.env`（選用）：**  
1. 將內含 `CHANNEL_STOCK_*` 等變數的文字檔上傳至雲端硬碟，分享權限至少為「**知道連結的使用者**」（僅限你信任的連結）。  
2. 在執行程式**之前**於終端機設定（勿寫進雲端上的那份 `.env`，以免雞生蛋）：`GOOGLE_DRIVE_DOTENV_FILE_ID`（檔案 ID），或 `GOOGLE_DRIVE_DOTENV_URL`（完整分享網址）。  
3. `pip install -r requirements.txt`（含 `gdown`）後執行 `python main.py`；會先下載為專案根目錄的 `.env` 再載入。  
4. 僅限可匿名／連結下載的檔案；設為「僅限本人」且未搭配 OAuth 時，`gdown` 可能無法下載。雲端上的敏感檔仍須自行控管權限。

## 快速啟動（本機執行）

```bash
# 1. 安裝套件
pip install -r requirements.txt

# 2. 設定環境變數
cp .env.example .env
# 填入 CHANNEL_STOCK_SECRET、CHANNEL_STOCK_ACCESS_TOKEN、CHANNEL_STOCK_USER_ID（及選填 CHANNEL_STOCK_USER_IDS）

# 3. 立即推播（全部 ETF）
python main.py

# 4. 只推播單支 ETF
python main.py --etf 0050
python main.py --etf 00631L

# 5. 啟動本機排程（台灣時間週一~週五 08:00）
python main.py --schedule
```

## 檔案結構

```
├── .github/workflows/          # GitHub Actions 排程（morning_push.yml）
├── main.py                     # 進入點（Push 模式、可選本機排程）
├── app.py                      # Flask：僅 / 與 /health（部署健康檢查）
├── config.py                   # ETF 設定、MIS 選用欄位、指標與閾值
├── data/
│   ├── __init__.py             # fetch_etf_data / get_current_price / get_etf_summary
│   ├── fetcher.py              # 證交所 MIS 即時報價
│   └── db.py                   # 訂閱者與分析快取（SQLite 等，依部署）
├── agents/
│   ├── base_agent.py           # 抽象基底類別
│   ├── technical_agent.py      # 技術指標 Agent
│   ├── volume_agent.py         # 量能分析 Agent
│   ├── trend_agent.py          # 趨勢動能 Agent
│   ├── risk_agent.py           # 風險評估 Agent
│   ├── llm_commentary.py     # Anthropic 盤勢解讀（選用）
│   └── orchestrator.py       # 多 Agent 協調器
└── linebot_utils/
    ├── flex_card.py          # Flex Message／Carousel
    ├── line_push.py          # LINE Push／Multicast
    ├── handler.py            # ❌ 已棄用（Webhook）
    └── rich_menu.py          # ❌ 已棄用（Rich Menu）
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

**備註**：系統不再接受用戶 Webhook 互動或 Rich Menu 指令，僅透過排程或本機執行推播。

> ⚠️ 本專案資訊僅供參考，不構成任何投資建議。
