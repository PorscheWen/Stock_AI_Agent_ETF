"""
趨勢動能 Agent
分析中長期價格趨勢、動能指標（ROC）、52週相對位置。
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from agents.base_agent import BaseAgent


class TrendAgent(BaseAgent):
    """趨勢動能分析 Agent"""

    def __init__(self, symbol: str):
        super().__init__("🔭 趨勢動能 Agent", symbol)

    def analyze(self, df: pd.DataFrame) -> dict[str, Any]:
        df = df.copy()
        close = df["Close"]
        latest_price = close.iloc[-1]

        signals = []
        score = 0

        # --- 52週高低點位置 ---
        high_52w = close.rolling(252, min_periods=60).max().iloc[-1]
        low_52w = close.rolling(252, min_periods=60).min().iloc[-1]
        range_52 = high_52w - low_52w
        pos_52w = ((latest_price - low_52w) / range_52 * 100) if range_52 > 0 else 50.0

        if pos_52w >= 80:
            signals.append({"label": "52週位置", "value": f"接近高點 {pos_52w:.0f}% ❌", "bullish": False})
            score -= 1
        elif pos_52w <= 30:
            signals.append({"label": "52週位置", "value": f"接近低點 {pos_52w:.0f}% ✅", "bullish": True})
            score += 1
        else:
            signals.append({"label": "52週位置", "value": f"中間區間 {pos_52w:.0f}%", "bullish": None})

        # --- 短期動能（5日報酬率）---
        if len(close) >= 6:
            ret_5d = (close.iloc[-1] / close.iloc[-6] - 1) * 100
            if ret_5d > 2:
                signals.append({"label": "5日動能", "value": f"+{ret_5d:.1f}% 強勢 ✅", "bullish": True})
                score += 1
            elif ret_5d < -2:
                signals.append({"label": "5日動能", "value": f"{ret_5d:.1f}% 弱勢 ❌", "bullish": False})
                score -= 1
            else:
                signals.append({"label": "5日動能", "value": f"{ret_5d:.1f}% 持平 ➖", "bullish": None})

        # --- 中期動能（20日報酬率）---
        if len(close) >= 21:
            ret_20d = (close.iloc[-1] / close.iloc[-21] - 1) * 100
            if ret_20d > 5:
                signals.append({"label": "月報酬", "value": f"+{ret_20d:.1f}% 多頭 ✅", "bullish": True})
                score += 2
            elif ret_20d < -5:
                signals.append({"label": "月報酬", "value": f"{ret_20d:.1f}% 空頭 ❌", "bullish": False})
                score -= 2
            else:
                signals.append({"label": "月報酬", "value": f"{ret_20d:.1f}% 中性 ➖", "bullish": None})

        # --- 趨勢斜率（線性回歸近20日）---
        if len(close) >= 20:
            y = close.iloc[-20:].values
            slope = float(np.polyfit(range(len(y)), y, 1)[0])
            if slope > 0:
                signals.append({"label": "20日趨勢", "value": "上升趨勢 ✅", "bullish": True})
                score += 1
            elif slope < 0:
                signals.append({"label": "20日趨勢", "value": "下降趨勢 ❌", "bullish": False})
                score -= 1

        # --- 價格高低突破 ---
        if len(close) >= 20:
            high_20 = close.rolling(20).max().iloc[-2]  # 前一根的20日高點
            low_20 = close.rolling(20).min().iloc[-2]
            if latest_price > high_20:
                signals.append({"label": "20日突破", "value": "向上突破 🚀 ✅", "bullish": True})
                score += 2
            elif latest_price < low_20:
                signals.append({"label": "20日跌破", "value": "向下跌破 ❌", "bullish": False})
                score -= 2

        action = self._score_to_action(score)

        return {
            "agent": self.name,
            "symbol": self.symbol,
            "score": score,
            "action": action,
            "signals": signals,
            "details": {
                "price": self._safe_float(latest_price),
                "high_52w": self._safe_float(high_52w),
                "low_52w": self._safe_float(low_52w),
                "pos_52w_pct": self._safe_float(pos_52w),
            },
        }

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
