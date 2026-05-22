"""
操作建議 Agent — 彙整所有 Agent 結果，依準確度輸出精確操作建議與顏色標示。

準確度顏色規則：
  ≥ 60%  → 綠色（高準確度）
  < 10%  → 紅色（低準確度）
  其他   → 橘色（中等準確度）
"""
from __future__ import annotations

from typing import Any


# 準確度閾值
_CONFIDENCE_HIGH = 60
_CONFIDENCE_LOW  = 10

# 顏色
_COLOR_HIGH   = "#2E7D32"   # 深綠
_COLOR_LOW    = "#C62828"   # 深紅
_COLOR_MEDIUM = "#E65100"   # 橘

_BULLISH_ACTIONS = {"強力買入", "買入"}
_BEARISH_ACTIONS = {"強力賣出", "賣出"}


def confidence_color(confidence: int) -> str:
    """依準確度回傳 hex 顏色：≥60% 綠、<10% 紅、其他橘。"""
    if confidence >= _CONFIDENCE_HIGH:
        return _COLOR_HIGH
    if confidence < _CONFIDENCE_LOW:
        return _COLOR_LOW
    return _COLOR_MEDIUM


def confidence_label(confidence: int) -> str:
    """依準確度回傳文字標籤。"""
    if confidence >= _CONFIDENCE_HIGH:
        return "高準確度"
    if confidence < _CONFIDENCE_LOW:
        return "低準確度"
    return "中等準確度"


class AdviceAgent:
    """
    操作建議 Agent。

    呼叫 ``AdviceAgent.generate(analysis)`` 傳入 ``Orchestrator.run()`` 的完整結果字典，
    回傳 advice 字典並同時就地寫入 ``analysis["advice"]``。
    """

    @staticmethod
    def generate(analysis: dict[str, Any]) -> dict[str, Any]:
        """
        Parameters
        ----------
        analysis : dict
            Orchestrator.run() 回傳的完整 analysis 字典。

        Returns
        -------
        dict
            精確操作建議字典，同時寫入 analysis["advice"]。
        """
        agent_results = analysis.get("agent_results", [])
        final_action  = analysis.get("final_action", "觀望")
        conf          = int(analysis.get("confidence", 0))
        latest_price  = analysis.get("latest_price", 0.0)
        stop_loss     = analysis.get("stop_loss")
        take_profit   = analysis.get("take_profit")
        is_leveraged  = (analysis.get("etf_info") or {}).get("type") == "leveraged"

        # ── 1. Agent 共識分析 ──────────────────────────────────────────────────
        bullish_agents = [r for r in agent_results if r.get("action") in _BULLISH_ACTIONS]
        bearish_agents = [r for r in agent_results if r.get("action") in _BEARISH_ACTIONS]
        neutral_agents = [r for r in agent_results if r.get("action") == "觀望"]

        n = len(agent_results) or 1
        bull_ratio = len(bullish_agents) / n
        bear_ratio = len(bearish_agents) / n

        if bull_ratio >= 0.75:
            consensus = "多頭共識"
        elif bear_ratio >= 0.75:
            consensus = "空頭共識"
        elif bull_ratio > bear_ratio and bull_ratio >= 0.5:
            consensus = "偏多分歧"
        elif bear_ratio > bull_ratio and bear_ratio >= 0.5:
            consensus = "偏空分歧"
        else:
            consensus = "訊號分歧"

        consensus_detail = (
            f"{len(bullish_agents)} 多頭 / "
            f"{len(neutral_agents)} 觀望 / "
            f"{len(bearish_agents)} 空頭"
        )

        # ── 2. 訊號強度統計 ────────────────────────────────────────────────────
        all_signals  = [s for r in agent_results for s in r.get("signals", [])]
        bull_signals = sum(1 for s in all_signals if s.get("bullish") is True)
        bear_signals = sum(1 for s in all_signals if s.get("bullish") is False)
        total_sigs   = len(all_signals) or 1

        # ── 3. 操作重點列表 ────────────────────────────────────────────────────
        points: list[str] = [
            f"Agent 共識：{consensus}（{consensus_detail}）",
            f"訊號分佈：{bull_signals} 多頭 / {bear_signals} 空頭（共 {total_sigs} 訊號）",
        ]

        if stop_loss and take_profit and latest_price:
            denom = abs(latest_price - stop_loss) or 0.001
            rr = round((take_profit - latest_price) / denom, 1)
            points.append(
                f"風報比 {rr}：1（停利 NT${take_profit:.2f}  停損 NT${stop_loss:.2f}）"
            )

        # ── 4. 倉位與進場建議 ──────────────────────────────────────────────────
        if final_action == "強力買入" and conf >= _CONFIDENCE_HIGH:
            position_pct = "50–70%"
            entry_advice = (
                f"訊號明確，可於現價 NT${latest_price:.2f} 附近積極進場，"
                "建議分兩批建立倉位。"
            )
        elif final_action in _BULLISH_ACTIONS and conf >= _CONFIDENCE_HIGH:
            position_pct = "30–50%"
            entry_advice = (
                f"現價 NT${latest_price:.2f} 附近分批進場，"
                "保留部分現金等待更佳買點。"
            )
        elif final_action in _BULLISH_ACTIONS and conf >= _CONFIDENCE_LOW:
            position_pct = "10–30%"
            entry_advice = (
                f"準確度中等（{conf}%），小倉位試水溫，"
                "等方向明確確認後再逐步加碼。"
            )
        elif final_action in _BEARISH_ACTIONS:
            position_pct = "0–20%"
            entry_advice = "空頭訊號明確，建議減碼至低倉位，切勿攤平。"
        elif conf < _CONFIDENCE_LOW:
            position_pct = "0%"
            entry_advice = (
                f"準確度過低（{conf}%），訊號不足以支撐進場判斷，"
                "建議場外等待更清晰訊號。"
            )
        else:
            position_pct = "0%"
            entry_advice = "訊號分歧，建議場外等待突破量能確認後再決定方向。"

        # ── 5. 風險警示 ────────────────────────────────────────────────────────
        risk_details = next(
            (r["details"] for r in agent_results if "atr_pct" in r.get("details", {})),
            {},
        )
        atr_pct = risk_details.get("atr_pct", 0.0)
        risk_warning = ""

        if is_leveraged:
            if atr_pct > 2.5 and final_action in _BULLISH_ACTIONS:
                risk_warning = "⚠️ 高波動 + 槓桿 ETF：波動耗損加速，嚴禁持有過夜，僅限當日短線。"
            elif final_action in _BULLISH_ACTIONS:
                risk_warning = "💡 槓桿 ETF：趨勢明確時適合 1–3 日短線動能操作，獲利後及時了結。"
            else:
                risk_warning = "⚠️ 槓桿 ETF 非多頭趨勢不宜介入，請考慮以 0050 替代。"
        elif conf < _CONFIDENCE_LOW:
            risk_warning = "⚠️ 準確度不足，市場方向不明，保守應對為宜。"
        elif consensus == "訊號分歧":
            risk_warning = "⚠️ 多空訊號分歧，追高追低風險較高，建議等待共識成形。"
        elif final_action in _BEARISH_ACTIONS and conf >= _CONFIDENCE_HIGH:
            risk_warning = "⚠️ 空頭訊號高準確度，現有多頭部位宜盡速減碼或出場。"

        # ── 組合 advice 字典 ───────────────────────────────────────────────────
        advice: dict[str, Any] = {
            "action":           final_action,
            "confidence":       conf,
            "confidence_color": confidence_color(conf),
            "confidence_label": confidence_label(conf),
            "consensus":        consensus,
            "consensus_detail": consensus_detail,
            "position_pct":     position_pct,
            "entry_advice":     entry_advice,
            "points":           points,
            "risk_warning":     risk_warning,
        }

        analysis["advice"] = advice
        return advice
