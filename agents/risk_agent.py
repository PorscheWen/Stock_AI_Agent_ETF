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

            if atr_pct > 2.5:
                # 高波動下槓桿耗損加速，不建議持有
                signals.append({
                    "label": "⚠️ 震盪耗損",
                    "value": "高波動市況槓桿耗損加速，不建議持有過夜",
                    "bullish": False,
                })
                score -= 1
            else:
                # 低波動趨勢市場，槓桿 ETF 適合短線動能交易
                signals.append({
                    "label": "💡 適用情境",
                    "value": "低波動趨勢市場，適合短線動能交易",
                    "bullish": None,
                })

        # --- 價格跌幅警示（1日 / 5日）---
        price_alerts = self._price_drop_alerts(close)
        for alert in price_alerts:
            signals.append(alert)
            score -= alert.get("_score_penalty", 0)

        action = self._score_to_action(score)

        # 取最高警示等級（critical > warning > none）
        alert_level = "none"
        for a in price_alerts:
            if a.get("_alert_level") == "critical":
                alert_level = "critical"
                break
            if a.get("_alert_level") == "warning":
                alert_level = "warning"

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
                "price_alerts": price_alerts,
                "price_alert_level": alert_level,
            },
        }

    @staticmethod
    def _price_drop_alerts(close: pd.Series) -> list[dict]:
        """計算 1日 / 5日 跌幅，達到 5% 或 10% 時產生警示。"""
        alerts = []

        def _check(pct: float, period_label: str) -> None:
            if pct >= 10:
                alerts.append({
                    "label": f"🚨 {period_label}急跌",
                    "value": f"跌幅 {pct:.1f}% — 緊急警示，注意停損！",
                    "bullish": False,
                    "_alert_level": "critical",
                    "_score_penalty": 2,
                })
            elif pct >= 5:
                alerts.append({
                    "label": f"⚠️ {period_label}下跌",
                    "value": f"跌幅 {pct:.1f}% — 警示，建議觀察支撐",
                    "bullish": False,
                    "_alert_level": "warning",
                    "_score_penalty": 1,
                })

        # 1日跌幅
        if len(close) >= 2:
            daily_chg = (close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] * 100
            if daily_chg < 0:
                _check(abs(daily_chg), "單日")

        # 5日跌幅（約一週）
        if len(close) >= 6:
            week_chg = (close.iloc[-1] - close.iloc[-6]) / close.iloc[-6] * 100
            if week_chg < 0:
                _check(abs(week_chg), "5日")

        return alerts

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
