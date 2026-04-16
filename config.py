"""
ETF 設定檔 — 定義 0050 與 00631L 的基本資訊
"""

ETF_CONFIG = {
    "0050": {
        "name": "元大台灣50",
        "full_name": "元大台灣50 ETF",
        "description": "追蹤台灣前50大上市公司",
        "type": "standard",
        "leverage": 1,
        "risk_level": "中",
        "risk_color": "#F39C12",
        "header_color": "#1565C0",
        "yahoo_symbol": "0050.TW",
    },
    "00631L": {
        "name": "元大台灣50正2",
        "full_name": "元大台灣50正2 ETF",
        "description": "2倍槓桿追蹤台灣50指數（高風險）",
        "type": "leveraged",
        "leverage": 2,
        "risk_level": "高",
        "risk_color": "#C0392B",
        "header_color": "#6A1B9A",
        "yahoo_symbol": "00631L.TW",
    },
    "009816": {
        "name": "凱基台灣TOP50",
        "full_name": "凱基台灣TOP50 ETF",
        "description": "追蹤台灣市值前50大上市公司",
        "type": "standard",
        "leverage": 1,
        "risk_level": "中",
        "risk_color": "#F39C12",
        "header_color": "#00695C",
        "yahoo_symbol": "009816.TW",
    },
    "00981A": {
        "name": "統一台灣成長",
        "full_name": "統一台灣成長主動 ETF",
        "description": "主動式選股，聚焦台灣成長型企業",
        "type": "active",
        "leverage": 1,
        "risk_level": "中高",
        "risk_color": "#E65100",
        "header_color": "#4527A0",
        "yahoo_symbol": "00981A.TW",
    },
}

# 技術指標參數
INDICATOR_PARAMS = {
    "ma_short": 5,
    "ma_mid": 20,
    "ma_long": 60,
    "rsi_period": 14,
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    "bb_period": 20,
    "bb_std": 2,
    "atr_period": 14,
    "volume_ma": 20,
}

# 決策閾值（對應正規化後加權總分，範圍約 -3.5 ~ +3.5）
DECISION_THRESHOLDS = {
    "strong_buy": 2.5,
    "buy": 1.2,
    "sell": -1.2,
    "strong_sell": -2.5,
}

# 各 Agent 正規化基準（理論最大正分）
AGENT_MAX_SCORES = [7.0, 5.0, 7.0, 3.0]  # tech, vol, trend, risk

# 加權正規化後的最大總分（用於信心度計算）
MAX_WEIGHTED_SCORE = 3.5

ACTION_LABELS = {
    "強力買入": {"emoji": "🚀", "color": "#00897B"},
    "買入": {"emoji": "📈", "color": "#2E7D32"},
    "觀望": {"emoji": "⏸", "color": "#F57F17"},
    "賣出": {"emoji": "📉", "color": "#C62828"},
    "強力賣出": {"emoji": "🔴", "color": "#B71C1C"},
}
