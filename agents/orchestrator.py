"""
Orchestrator — 協調所有 Agent 並彙整最終買賣判斷
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from agents.technical_agent import TechnicalAgent
from agents.volume_agent import VolumeAgent
from agents.trend_agent import TrendAgent
from agents.risk_agent import RiskAgent
from config import DECISION_THRESHOLDS, ETF_CONFIG
from data import fetch_etf_data


class Orchestrator:
    """
    多 Agent 協調器。
    依序呼叫各 Agent，彙整分數後輸出最終決策。
    """

    def __init__(self, symbol: str):
        if symbol not in ETF_CONFIG:
            raise ValueError(f"不支援的 ETF 代號：{symbol}，支援：{list(ETF_CONFIG.keys())}")
        self.symbol = symbol
        self.etf_info = ETF_CONFIG[symbol]
        self._agents = [
            TechnicalAgent(symbol),
            VolumeAgent(symbol),
            TrendAgent(symbol),
            RiskAgent(symbol),
        ]

    def run(self) -> dict[str, Any]:
        """抓取資料、執行所有 Agent、回傳完整分析結果。"""
        df = fetch_etf_data(self.symbol, period="6mo")

        agent_results = []
        for agent in self._agents:
            try:
                result = agent.analyze(df)
                agent_results.append(result)
            except Exception as exc:
                agent_results.append({
                    "agent": agent.name,
                    "symbol": self.symbol,
                    "score": 0,
                    "action": "觀望",
                    "signals": [{"label": "錯誤", "value": str(exc), "bullish": None}],
                    "details": {},
                })

        # 彙整分數（技術:量能:趨勢:風險 = 1:1:1:0.5 加權）
        weights = [1.0, 1.0, 1.0, 0.5]
        total_score = sum(
            r["score"] * w for r, w in zip(agent_results, weights)
        )

        final_action = self._score_to_final_action(total_score)

        # 信心度（取 |total_score| 轉換為 0~100%）
        confidence = min(abs(total_score) / 8 * 100, 100)
        confidence = round(confidence)

        latest_price = float(df["Close"].iloc[-1])
        latest_date = df.index[-1]
        if hasattr(latest_date, "strftime"):
            latest_date_str = latest_date.strftime("%Y/%m/%d")
        else:
            latest_date_str = str(latest_date)

        return {
            "symbol": self.symbol,
            "etf_info": self.etf_info,
            "latest_price": latest_price,
            "latest_date": latest_date_str,
            "total_score": round(total_score, 1),
            "final_action": final_action,
            "confidence": confidence,
            "agent_results": agent_results,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

    @staticmethod
    def _score_to_final_action(score: float) -> str:
        th = DECISION_THRESHOLDS
        if score >= th["strong_buy"]:
            return "強力買入"
        if score >= th["buy"]:
            return "買入"
        if score <= th["strong_sell"]:
            return "強力賣出"
        if score <= th["sell"]:
            return "賣出"
        return "觀望"
