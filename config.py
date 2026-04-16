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

# 決策閾值
DECISION_THRESHOLDS = {
    "strong_buy": 4,
    "buy": 2,
    "sell": -2,
    "strong_sell": -4,
}

ACTION_LABELS = {
    "強力買入": {"emoji": "🚀", "color": "#00897B"},
    "買入": {"emoji": "📈", "color": "#2E7D32"},
    "觀望": {"emoji": "⏸", "color": "#F57F17"},
    "賣出": {"emoji": "📉", "color": "#C62828"},
    "強力賣出": {"emoji": "🔴", "color": "#B71C1C"},
}
