"""
技術指標 Agent
計算 MA 黃金/死亡交叉、RSI、MACD、布林通道，彙整多空訊號。
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from agents.base_agent import BaseAgent
from config import INDICATOR_PARAMS


class TechnicalAgent(BaseAgent):
    """技術面分析 Agent"""

    def __init__(self, symbol: str):
        super().__init__("📊 技術指標 Agent", symbol)

    # ------------------------------------------------------------------
    # 公開介面
    # ------------------------------------------------------------------

    def analyze(self, df: pd.DataFrame) -> dict[str, Any]:
        df = df.copy()
        df = self._add_indicators(df)
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) >= 2 else latest

        signals = []
        score = 0

        # --- MA 訊號 ---
        ma_s = INDICATOR_PARAMS["ma_short"]
        ma_m = INDICATOR_PARAMS["ma_mid"]
        ma_l = INDICATOR_PARAMS["ma_long"]
        ma5, ma20, ma60 = latest[f"MA{ma_s}"], latest[f"MA{ma_m}"], latest[f"MA{ma_l}"]
        close = latest["Close"]

        if ma5 > ma20:
            signals.append({"label": f"MA{ma_s}/MA{ma_m}", "value": "黃金交叉 ✅", "bullish": True})
            score += 1
        else:
            signals.append({"label": f"MA{ma_s}/MA{ma_m}", "value": "死亡交叉 ❌", "bullish": False})
            score -= 1

        if close > ma60:
            signals.append({"label": f"站上 MA{ma_l}", "value": "長線多頭 ✅", "bullish": True})
            score += 1
        else:
            signals.append({"label": f"跌破 MA{ma_l}", "value": "長線空頭 ❌", "bullish": False})
            score -= 1

        # --- RSI 訊號 ---
        rsi = latest["RSI"]
        if rsi < 30:
            signals.append({"label": "RSI", "value": f"{rsi:.1f} 超賣 ✅", "bullish": True})
            score += 2
        elif rsi > 70:
            signals.append({"label": "RSI", "value": f"{rsi:.1f} 超買 ❌", "bullish": False})
            score -= 2
        else:
            signals.append({"label": "RSI", "value": f"{rsi:.1f} 中性 ➖", "bullish": None})

        # --- MACD 訊號 ---
        macd, signal_line, hist = latest["MACD"], latest["MACD_signal"], latest["MACD_hist"]
        prev_hist = prev["MACD_hist"]
        if macd > signal_line:
            signals.append({"label": "MACD", "value": "多頭排列 ✅", "bullish": True})
            score += 1
        else:
            signals.append({"label": "MACD", "value": "空頭排列 ❌", "bullish": False})
            score -= 1

        if hist > 0 and hist > prev_hist:
            signals.append({"label": "MACD 柱狀", "value": "動能增強 ✅", "bullish": True})
            score += 1
        elif hist < 0 and hist < prev_hist:
            signals.append({"label": "MACD 柱狀", "value": "動能衰退 ❌", "bullish": False})
            score -= 1

        # --- 布林通道訊號 ---
        bb_upper, bb_lower, bb_mid = latest["BB_upper"], latest["BB_lower"], latest["BB_mid"]
        bb_range = bb_upper - bb_lower
        bb_pct = ((close - bb_lower) / bb_range * 100) if bb_range > 0 else 50

        if bb_pct < 20:
            signals.append({"label": "布林下軌", "value": f"接近下軌 {bb_pct:.0f}% ✅", "bullish": True})
            score += 1
        elif bb_pct > 80:
            signals.append({"label": "布林上軌", "value": f"接近上軌 {bb_pct:.0f}% ❌", "bullish": False})
            score -= 1
        else:
            signals.append({"label": "布林通道", "value": f"中間位置 {bb_pct:.0f}%", "bullish": None})

        action = self._score_to_action(score)

        return {
            "agent": self.name,
            "symbol": self.symbol,
            "score": score,
            "action": action,
            "signals": signals,
            "details": {
                "close": self._safe_float(close),
                f"ma{ma_s}": self._safe_float(ma5),
                f"ma{ma_m}": self._safe_float(ma20),
                f"ma{ma_l}": self._safe_float(ma60),
                "rsi": self._safe_float(rsi),
                "macd": self._safe_float(macd),
                "macd_signal": self._safe_float(signal_line),
                "bb_pct": self._safe_float(bb_pct),
            },
        }

    # ------------------------------------------------------------------
    # 私有方法
    # ------------------------------------------------------------------

    def _add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        p = INDICATOR_PARAMS
        # Moving Averages
        df[f"MA{p['ma_short']}"] = df["Close"].rolling(p["ma_short"]).mean()
        df[f"MA{p['ma_mid']}"] = df["Close"].rolling(p["ma_mid"]).mean()
        df[f"MA{p['ma_long']}"] = df["Close"].rolling(p["ma_long"]).mean()

        # RSI
        df["RSI"] = self._rsi(df["Close"], p["rsi_period"])

        # MACD
        ema_fast = df["Close"].ewm(span=p["macd_fast"], adjust=False).mean()
        ema_slow = df["Close"].ewm(span=p["macd_slow"], adjust=False).mean()
        df["MACD"] = ema_fast - ema_slow
        df["MACD_signal"] = df["MACD"].ewm(span=p["macd_signal"], adjust=False).mean()
        df["MACD_hist"] = df["MACD"] - df["MACD_signal"]

        # Bollinger Bands
        df["BB_mid"] = df["Close"].rolling(p["bb_period"]).mean()
        rolling_std = df["Close"].rolling(p["bb_period"]).std()
        df["BB_upper"] = df["BB_mid"] + p["bb_std"] * rolling_std
        df["BB_lower"] = df["BB_mid"] - p["bb_std"] * rolling_std

        return df

    @staticmethod
    def _rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        delta = prices.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    @staticmethod
    def _score_to_action(score: int) -> str:
        if score >= 5:
            return "強力買入"
        if score >= 2:
            return "買入"
        if score <= -5:
            return "強力賣出"
        if score <= -2:
            return "賣出"
        return "觀望"
