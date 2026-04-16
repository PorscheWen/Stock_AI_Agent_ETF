# Stock_AI_Agent_ETF

台灣 ETF 多 Agent AI 買賣判斷 LINE Bot，支援 **0050**（元大台灣50）與 **00631L**（元大台灣50正2）。

## 架構

```
┌─────────────────────────────────────────────────────────┐
│                      LINE Bot                           │
│   使用者輸入 "0050" / "00631L" / "分析"                  │
└────────────────────────┬────────────────────────────────┘
                         ▼
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
| LINE Bot Flex 卡片 | 兩支 ETF 使用同款卡片模板，可左右滑動比較 |

## 快速啟動

```bash
# 1. 安裝套件
pip install -r requirements.txt

# 2. 複製環境變數設定
cp .env.example .env
# 填入 LINE_CHANNEL_SECRET 與 LINE_CHANNEL_ACCESS_TOKEN

# 3. 啟動服務
python app.py
```

### LINE Bot 指令

| 輸入 | 回應 |
|------|------|
| `0050` / `台灣50` | 0050 分析卡片 |
| `00631L` / `正2` / `槓桿` | 00631L 分析卡片 |
| `分析` / `全部` / `比較` | 兩支 ETF 左右滑動 Carousel |

## 檔案結構

```
├── app.py                  # Flask + LINE Webhook 主程式
├── config.py               # ETF 設定與指標參數
├── data/
│   └── __init__.py         # yfinance 資料抓取
├── agents/
│   ├── base_agent.py       # 抽象基底類別
│   ├── technical_agent.py  # 技術指標 Agent
│   ├── volume_agent.py     # 量能分析 Agent
│   ├── trend_agent.py      # 趨勢動能 Agent
│   ├── risk_agent.py       # 風險評估 Agent
│   └── orchestrator.py     # 多 Agent 協調器
└── linebot_utils/
    ├── flex_card.py        # Flex Message 卡片產生器
    └── handler.py          # Webhook 事件處理
```

> ⚠️ 本專案資訊僅供參考，不構成任何投資建議。