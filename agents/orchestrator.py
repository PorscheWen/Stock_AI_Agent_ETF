"""
Orchestrator — 協調所有 Agent 並彙整最終買賣判斷
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any

import pandas as pd

from agents.technical_agent import TechnicalAgent
from agents.volume_agent import VolumeAgent
from agents.trend_agent import TrendAgent
from agents.risk_agent import RiskAgent
from config import AGENT_MAX_SCORES, DECISION_THRESHOLDS, ETF_CONFIG, MAX_WEIGHTED_SCORE
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
        """抓取資料、並行執行所有 Agent、回傳完整分析結果。"""
        df = fetch_etf_data(self.symbol, period="1y")

        # 並行執行各 Agent
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(agent.analyze, df) for agent in self._agents]

        agent_results = []
        for future, agent in zip(futures, self._agents):
            try:
                agent_results.append(future.result())
            except Exception as exc:
                agent_results.append({
                    "agent": agent.name,
                    "symbol": self.symbol,
                    "score": 0,
                    "action": "觀望",
                    "signals": [{"label": "錯誤", "value": str(exc), "bullish": None}],
                    "details": {},
                })

        # 正規化各 Agent 分數至 [-1, +1]，再加權彙整
        weights = [1.0, 1.0, 1.0, 0.5]
        total_score = sum(
            (r["score"] / ms) * w
            for r, ms, w in zip(agent_results, AGENT_MAX_SCORES, weights)
        )
        total_score = max(-MAX_WEIGHTED_SCORE, min(MAX_WEIGHTED_SCORE, total_score))

        final_action = self._score_to_final_action(total_score)

        # 信心度：正規化總分佔最大加權總分的比例
        confidence = round(min(abs(total_score) / MAX_WEIGHTED_SCORE * 100, 100))

        latest_price = float(df["Close"].iloc[-1])
        latest_date = df.index[-1]
        latest_date_str = latest_date.strftime("%Y/%m/%d") if hasattr(latest_date, "strftime") else str(latest_date)

        # ATR 停損/停利建議（1.5 ATR 止損，2 ATR 停利）
        risk_details = next(
            (r["details"] for r in agent_results if "atr_pct" in r.get("details", {})),
            {},
        )
        atr_pct = risk_details.get("atr_pct", 0.0)
        stop_loss = round(latest_price * (1 - 1.5 * atr_pct / 100), 2) if atr_pct else None
        take_profit = round(latest_price * (1 + 2.0 * atr_pct / 100), 2) if atr_pct else None

        recommendation = self._generate_recommendation(
            final_action=final_action,
            confidence=confidence,
            latest_price=latest_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            agent_results=agent_results,
            is_leveraged=self.etf_info.get("type") == "leveraged",
        )

        return {
            "symbol": self.symbol,
            "etf_info": self.etf_info,
            "latest_price": latest_price,
            "latest_date": latest_date_str,
            "total_score": round(total_score, 2),
            "final_action": final_action,
            "confidence": confidence,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "recommendation": recommendation,
            "agent_results": agent_results,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

    @staticmethod
    def _generate_recommendation(
        final_action: str,
        confidence: int,
        latest_price: float,
        stop_loss: float | None,
        take_profit: float | None,
        agent_results: list[dict],
        is_leveraged: bool,
    ) -> dict[str, str]:
        """依綜合訊號產生具體操作建議。"""

        # 計算多空訊號數量
        bullish_count = sum(
            1 for r in agent_results for s in r.get("signals", []) if s.get("bullish") is True
        )
        bearish_count = sum(
            1 for r in agent_results for s in r.get("signals", []) if s.get("bullish") is False
        )

        # ATR 波動水準
        risk_details = next(
            (r["details"] for r in agent_results if "atr_pct" in r.get("details", {})), {}
        )
        atr_pct = risk_details.get("atr_pct", 0.0)
        high_volatility = atr_pct > 2.5

        # 停損停利文字
        if stop_loss and take_profit:
            exit_text = f"停損 NT${stop_loss:.2f}，停利 NT${take_profit:.2f}"
        else:
            exit_text = "依個人風險承受度設定停損"

        # 依操作方向決定建議內容
        if final_action == "強力買入":
            summary = f"技術、量能、趨勢全面看多（{bullish_count} 項多頭訊號），積極做多訊號明確。"
            entry   = f"可於現價 NT${latest_price:.2f} 附近進場，信心度 {confidence}%。"
            position = "建議倉位 50～70%，可一次進場或分兩批布局。"

        elif final_action == "買入":
            summary = f"多項指標偏多（{bullish_count} 多頭 vs {bearish_count} 空頭訊號），可考慮布局。"
            entry   = f"建議於 NT${latest_price:.2f} 附近分批進場，避免一次重押。"
            position = "建議倉位 30～50%，留部分現金等待回測確認。"

        elif final_action == "賣出":
            summary = f"技術面走弱（{bearish_count} 項空頭訊號），建議逢反彈減碼。"
            entry   = "現有持倉建議減至 30% 以下，避免持續虧損擴大。"
            position = "建議倉位降至 0～30%。"

        elif final_action == "強力賣出":
            summary = f"多項指標看空（{bearish_count} 項空頭訊號），趨勢向下明確。"
            entry   = "現有持倉應盡速出場，不宜攤平。"
            position = "建議倉位 0%，等待底部訊號確立再重新評估。"

        else:  # 觀望
            summary = f"訊號分歧（{bullish_count} 多頭 vs {bearish_count} 空頭），方向尚不明確。"
            entry   = "建議場外等待，待突破或成交量放大後再決定方向。"
            position = "建議倉位 0%，保留現金靈活應對。"

        # 槓桿 ETF 附加說明
        note = ""
        if is_leveraged:
            if high_volatility:
                note = "⚠️ 00631L 高波動環境下槓桿耗損加速，嚴禁持有過夜，僅適合當日短線操作。"
            elif final_action in ("強力買入", "買入"):
                note = "💡 00631L 適合趨勢明確的短線動能交易（1～3日），獲利後盡早了結。"
            else:
                note = "⚠️ 00631L 非趨勢市場不宜介入，請以 0050 代替。"

        return {
            "summary": summary,
            "entry": entry,
            "exit": exit_text,
            "position": position,
            "note": note,
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
