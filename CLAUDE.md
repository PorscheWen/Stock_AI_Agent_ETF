# Stock_AI_agent_ETF

台灣 ETF 多 Agent AI 買賣判斷系統，支援 **0050**（元大台灣50）與 **00631L**（元大台灣50正2）。盤前自動分析並推播 LINE，採用 Push 模式（無需 Flask / ngrok）。

## 技術棧
- Python 3.12
- 進入點：`main.py`
- LINE Push 工具：`linebot_utils/`
- 設定：`config.py`

## Agent 架構
```
Orchestrator（並行呼叫 4 個 Agent）
├── 技術指標 Agent   MA/RSI/MACD/布林通道
├── 量能分析 Agent   OBV/量比/量價配合
├── 趨勢動能 Agent   52週位置/動能/突破偵測
└── 風險評估 Agent   ATR/最大回撤/槓桿警示
```

## GitHub Actions 排程
- Workflow：ETF 早盤前分析推播
- 執行時間：週一～週五 **台灣時間 08:00**（UTC `0 0 * * 1-5`）
- Python：3.12
- 支援手動觸發：`workflow_dispatch`

## 必要 Secrets
| Secret | 說明 |
|---|---|
| `LINE_CHANNEL_SECRET` | LINE Bot Channel Secret |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Bot Token |
| `LINE_USER_ID` | 推播目標用戶 ID |

## 注意事項
- 使用 LINE Push API，不需要 Webhook/Flask/ngrok
- 00631L 為槓桿 ETF，風險評估 Agent 會自動加入槓桿警示
- Render 部署設定保留在 `render.yaml`（備用，目前以 GitHub Actions 為主）
