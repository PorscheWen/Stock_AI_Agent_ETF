"""
風險評估 Agent
計算波動率、最大回撤，並針對槓桿 ETF（00631L）給予額外風險警示。
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from agents.base_agent import BaseAgent
from config import ETF_CONFIG, INDICATOR_PARAMS


class RiskAgent(BaseAgent):
    """風險評估 Agent"""

    def __init__(self, symbol: str):
        super().__init__("🛡 風險評估 Agent", symbol)
        self._is_leveraged = ETF_CONFIG.get(symbol, {}).get("type") == "leveraged"

    def analyze(self, df: pd.DataFrame) -> dict[str, Any]:
        df = df.copy()
        close = df["Close"]

        signals = []
        score = 0  # 正分=風險低（利多），負分=風險高（利空）

        # --- ATR 波動率 ---
        atr = self._atr(df, INDICATOR_PARAMS["atr_period"]).iloc[-1]
        atr_pct = (atr / close.iloc[-1] * 100) if close.iloc[-1] > 0 else 0

        if atr_pct > 3:
            signals.append({"label": "波動率(ATR)", "value": f"{atr_pct:.1f}% 高波動 ⚠️", "bullish": False})
            score -= 1
        elif atr_pct < 1.5:
            signals.append({"label": "波動率(ATR)", "value": f"{atr_pct:.1f}% 低波動 ✅", "bullish": True})
            score += 1
        else:
            signals.append({"label": "波動率(ATR)", "value": f"{atr_pct:.1f}% 正常", "bullish": None})

        # --- 最近20日最大回撤 ---
        recent = close.tail(20)
        rolling_max = recent.cummax()
        drawdown = ((recent - rolling_max) / rolling_max * 100).min()

        if drawdown < -10:
            signals.append({"label": "最大回撤", "value": f"{drawdown:.1f}% 深度修正 ⚠️", "bullish": False})
            score -= 2
        elif drawdown < -5:
            signals.append({"label": "最大回撤", "value": f"{drawdown:.1f}% 中度修正", "bullish": None})
            score -= 1
        else:
            signals.append({"label": "最大回撤", "value": f"{drawdown:.1f}% 回撤可控 ✅", "bullish": True})
            score += 1

        # --- 年化波動率 ---
        daily_ret = close.pct_change().dropna()
        annual_vol = daily_ret.std() * np.sqrt(252) * 100

        if annual_vol > 40:
            signals.append({"label": "年化波動", "value": f"{annual_vol:.1f}% 極高 ⚠️", "bullish": False})
            score -= 1
        elif annual_vol > 25:
            signals.append({"label": "年化波動", "value": f"{annual_vol:.1f}% 偏高", "bullish": None})
        else:
            signals.append({"label": "年化波動", "value": f"{annual_vol:.1f}% 正常 ✅", "bullish": True})
            score += 1

        # --- 槓桿 ETF 特殊警示 ---
        if self._is_leveraged:
            signals.append({
                "label": "⚠️ 槓桿警示",
                "value": "2倍槓桿，長期持有有耗損風險",
                "bullish": False,
            })
            score -= 1

            # 高波動環境下槓桿 ETF 加倍警示
            if atr_pct > 2.5:
                signals.append({
                    "label": "⚠️ 震盪耗損",
                    "value": "高波動市況槓桿耗損加速",
                    "bullish": False,
                })
                score -= 1

        action = self._score_to_action(score)

        return {
            "agent": self.name,
            "symbol": self.symbol,
            "score": score,
            "action": action,
            "signals": signals,
            "details": {
                "atr_pct": self._safe_float(atr_pct),
                "max_drawdown_pct": self._safe_float(drawdown),
                "annual_volatility_pct": self._safe_float(annual_vol),
                "is_leveraged": self._is_leveraged,
            },
        }

    @staticmethod
    def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        high, low, close = df["High"], df["Low"], df["Close"]
        prev_close = close.shift(1)
        tr = pd.concat(
            [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
            axis=1,
        ).max(axis=1)
        return tr.rolling(period).mean()

    @staticmethod
    def _score_to_action(score: int) -> str:
        if score >= 3:
            return "風險偏低"
        if score <= -3:
            return "風險偏高"
        return "風險中等"
