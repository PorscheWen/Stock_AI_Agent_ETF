"""
以 Anthropic Claude 根據規則型 Agent 輸出，產生繁體中文盤勢解讀（補充說明，非改寫分數）。
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

_SYSTEM = (
    "你是台股 ETF 市場解讀助理。僅根據使用者提供的 JSON 數據做簡短說明，使用繁體中文。"
    "語氣中立；不得改寫成明確的買賣指令或保證報酬。"
    "可提醒波動、槓桿 ETF 耗損等風險。輸出必須為單一 JSON 物件，不要 markdown，不要其他說明文字。"
)


def _api_key() -> str:
    return (
        os.environ.get("ANTHROPIC_API_KEY", "").strip()
        or os.environ.get("CHANNEL_STOCK_Claude_Token", "").strip()
    )


def _model() -> str:
    return os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022").strip()


def _compact_analysis(a: dict[str, Any]) -> dict[str, Any]:
    agents = []
    for r in a.get("agent_results", []):
        agents.append({
            "name": r.get("agent"),
            "score": r.get("score"),
            "action": r.get("action"),
            "signals": [
                {"label": s.get("label"), "value": s.get("value"), "bullish": s.get("bullish")}
                for s in r.get("signals", [])[:8]
            ],
        })
    rec = a.get("recommendation") or {}
    return {
        "symbol": a["symbol"],
        "name": (a.get("etf_info") or {}).get("name"),
        "type": (a.get("etf_info") or {}).get("type"),
        "final_action": a["final_action"],
        "confidence": a["confidence"],
        "total_score": a["total_score"],
        "latest_price": a["latest_price"],
        "latest_date": a.get("latest_date"),
        "stop_loss": a.get("stop_loss"),
        "take_profit": a.get("take_profit"),
        "recommendation_summary": rec.get("summary"),
        "recommendation_note": rec.get("note"),
        "agents": agents,
    }


def _parse_json_object(text: str) -> dict[str, Any]:
    raw = text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, count=1)
        raw = re.sub(r"\s*```\s*$", "", raw, count=1)
    return json.loads(raw)


def enrich_analyses_with_llm(analyses: list[dict[str, Any]]) -> None:
    """
    就地為每個 analysis 加上 llm_commentary（str）。
    未設定 API key 或呼叫失敗時為空字串，不影響推播。
    """
    if not analyses:
        return

    for a in analyses:
        a.setdefault("llm_commentary", "")

    key = _api_key()
    if not key:
        logger.info("[LLM] 未設定 ANTHROPIC_API_KEY 或 CHANNEL_STOCK_Claude_Token，略過盤勢解讀")
        return

    try:
        import anthropic
    except ImportError:
        logger.warning("[LLM] 未安裝 anthropic，請執行 pip install anthropic")
        return

    symbols = [a["symbol"] for a in analyses]
    payload = [_compact_analysis(a) for a in analyses]
    user = (
        "以下為程式依技術／量能／趨勢／風險規則計算後的結果（JSON）。"
        "請針對每一檔 ETF 各寫一段繁體中文解讀（約 2～4 句），整合多空氛圍與須注意之處。\n\n"
        f"{json.dumps(payload, ensure_ascii=False)}\n\n"
        f"請只輸出一個 JSON 物件，且必須僅包含這些鍵：{json.dumps(symbols, ensure_ascii=False)}。"
        "每個鍵的值為字串（該檔解讀）。"
    )

    try:
        client = anthropic.Anthropic(api_key=key)
        msg = client.messages.create(
            model=_model(),
            max_tokens=1200,
            system=_SYSTEM,
            messages=[{"role": "user", "content": user}],
        )
        block = msg.content[0]
        text = block.text if hasattr(block, "text") else str(block)
        data = _parse_json_object(text)
        if not isinstance(data, dict):
            raise ValueError("LLM 回傳非物件")
        for a in analyses:
            raw_txt = data.get(a["symbol"], "")
            if not isinstance(raw_txt, str):
                raw_txt = str(raw_txt)
            a["llm_commentary"] = raw_txt.strip()[:2000]
        logger.info("[LLM] 盤勢解讀已寫入 %d 檔", len(analyses))
    except Exception as exc:
        logger.warning("[LLM] 解讀失敗（略過）：%s", exc)
        for a in analyses:
            a["llm_commentary"] = ""
