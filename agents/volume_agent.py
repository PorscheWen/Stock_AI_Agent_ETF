"""
成交量 Agent
分析量能趨勢、OBV 累積量，判斷主力進出。
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from agents.base_agent import BaseAgent
from config import INDICATOR_PARAMS


class VolumeAgent(BaseAgent):
    """成交量分析 Agent"""

    def __init__(self, symbol: str):
        super().__init__("📦 量能分析 Agent", symbol)

    def analyze(self, df: pd.DataFrame) -> dict[str, Any]:
        df = df.copy()
        vol_ma = INDICATOR_PARAMS["volume_ma"]

        df["Vol_MA"] = df["Volume"].rolling(vol_ma).mean()
        df["OBV"] = self._obv(df)
        df["OBV_MA"] = df["OBV"].rolling(vol_ma).mean()

        latest = df.iloc[-1]
        recent_5 = df.tail(5)

        signals = []
        score = 0

        # 量能 vs 均量
        vol_ratio = latest["Volume"] / latest["Vol_MA"] if latest["Vol_MA"] > 0 else 1.0
        if vol_ratio >= 1.5:
            signals.append({"label": "放量", "value": f"量能 {vol_ratio:.1f}x 均量 ✅", "bullish": True})
            score += 1
        elif vol_ratio <= 0.5:
            signals.append({"label": "縮量", "value": f"量能 {vol_ratio:.1f}x 均量", "bullish": None})
        else:
            signals.append({"label": "量能", "value": f"{vol_ratio:.1f}x 均量 正常", "bullish": None})

        # 量價配合: 價漲量增（需放量 1.2x 以上才算確認）/ 價跌量縮 為多頭
        price_change = df["Close"].pct_change().iloc[-1]
        if price_change > 0 and vol_ratio >= 1.2:
            signals.append({"label": "量價", "value": "價漲量增 多頭確認 ✅", "bullish": True})
            score += 2
        elif price_change < 0 and vol_ratio >= 1.5:
            signals.append({"label": "量價", "value": "價跌量增 空頭賣壓 ❌", "bullish": False})
            score -= 2
        elif price_change < 0 and vol_ratio < 0.8:
            signals.append({"label": "量價", "value": "價跌縮量 賣壓輕 ➖", "bullish": None})
        else:
            signals.append({"label": "量價", "value": "量價配合正常 ➖", "bullish": None})

        # OBV 趨勢
        obv_trend = latest["OBV"] - df["OBV"].iloc[-vol_ma] if len(df) >= vol_ma else 0
        if obv_trend > 0:
            signals.append({"label": "OBV", "value": "持續上升 主力買進 ✅", "bullish": True})
            score += 1
        elif obv_trend < 0:
            signals.append({"label": "OBV", "value": "持續下降 主力出貨 ❌", "bullish": False})
            score -= 1

        # 5日均量趨勢
        recent_avg_vol = recent_5["Volume"].mean()
        prev_avg_vol = df.iloc[-10:-5]["Volume"].mean() if len(df) >= 10 else recent_avg_vol
        if prev_avg_vol > 0:
            vol_trend_ratio = recent_avg_vol / prev_avg_vol
            if vol_trend_ratio >= 1.2:
                signals.append({"label": "量能趨勢", "value": f"近期量增 {vol_trend_ratio:.1f}x ✅", "bullish": True})
                score += 1
            elif vol_trend_ratio <= 0.8:
                signals.append({"label": "量能趨勢", "value": f"近期量縮 {vol_trend_ratio:.1f}x ❌", "bullish": False})
                score -= 1

        action = self._score_to_action(score)

        return {
            "agent": self.name,
            "symbol": self.symbol,
            "score": score,
            "action": action,
            "signals": signals,
            "details": {
                "volume": self._safe_float(latest["Volume"]),
                "vol_ma": self._safe_float(latest["Vol_MA"]),
                "vol_ratio": self._safe_float(vol_ratio),
                "obv": self._safe_float(latest["OBV"]),
            },
        }

    @staticmethod
    def _obv(df: pd.DataFrame) -> pd.Series:
        direction = np.sign(df["Close"].diff().fillna(0))
        return (direction * df["Volume"]).cumsum()

    @staticmethod
    def _score_to_action(score: int) -> str:
        if score >= 4:
            return "強力買入"
        if score >= 2:
            return "買入"
        if score <= -4:
            return "強力賣出"
        if score <= -2:
            return "賣出"
        return "觀望"
