# Stock_AI_agent_ETF

台灣 ETF **多 Agent 規則式指標**買賣判斷：`config.ETF_CONFIG` 內 **0050、00631L、009816、00981A** 四檔；歷史資料來自 **Yahoo Finance**，現價優先 **證交所 MIS**（見 `data/fetcher.py`）。

## 架構特點

- **純推播模式**：不接受用戶 Webhook 互動或 Rich Menu 指令
- **GitHub Actions 自動化**：盤前自動分析並推播至 LINE
- **多 Agent 協作**：4 個規則型 Agent 並行分析；**選用** Anthropic Claude 產生「AI 盤勢解讀」段落（`ANTHROPIC_API_KEY` 或 `CHANNEL_STOCK_Claude_Token`）

## 技術棧

- Python 3.12
- 進入點：`main.py`（推播與可選本機排程）
- LINE Push：`linebot_utils/line_push.py`
- 設定：`config.py`
- 資料：`data/__init__.py`（Yahoo + 現價彙整）、`data/fetcher.py`（MIS）

## Agent 架構

```
Orchestrator（並行呼叫 4 個 Agent）
├── 技術指標 Agent   MA/RSI/MACD/布林通道
├── 量能分析 Agent   OBV/量比/量價配合
├── 趨勢動能 Agent   52週位置/動能/突破偵測
└── 風險評估 Agent   ATR/最大回撤/槓桿警示
```

## GitHub Actions 排程

- Workflow：`.github/workflows/morning_push.yml`
- 執行時間：週一～週五 **台灣時間 14:30**（UTC `30 6 * * 1-5`）**收盤後執行**
- Python：3.12
- 支援手動觸發：`workflow_dispatch`

## 必要 Secrets

| Secret | 說明 |
|--------|------|
| `CHANNEL_STOCK_SECRET` | LINE Bot Channel Secret |
| `CHANNEL_STOCK_ACCESS_TOKEN` | LINE Channel access token |
| `CHANNEL_STOCK_USER_ID` | 推播目標用戶 ID |
| `ANTHROPIC_API_KEY` | 選填；AI 盤勢解讀 |

## 執行方式

```bash
# 本地推播（全部 ETF）
python main.py

# 只推播特定 ETF
python main.py --etf 0050
python main.py --etf 00631L
```

## 已棄用功能

- Flask Webhook 處理（`app.py` 僅保留健康檢查）
- Rich Menu 互動（`linebot_utils/rich_menu.py` 已停用）
- 用戶指令處理（`linebot_utils/handler.py` 已停用）
- Render 排程（改用 GitHub Actions）

## 注意事項

- 使用 LINE Push API，無需 Webhook／Flask／ngrok 即可推播
- 00631L 為槓桿 ETF，風險評估 Agent 會加入槓桿相關警示
- 系統僅供推播，不接受一般終端用戶互動
