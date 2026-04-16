"""
Flex Message 卡片產生器
兩支 ETF（0050 / 00631L）使用相同的卡片模板。
"""
from __future__ import annotations

from typing import Any

from config import ACTION_LABELS, ETF_CONFIG


# ── 顏色常數 ────────────────────────────────────────────────────────────────
_ACTION_HEADER_COLOR = {
    "強力買入": "#00695C",
    "買入":     "#2E7D32",
    "觀望":     "#E65100",
    "賣出":     "#B71C1C",
    "強力賣出": "#880E4F",
}

_SIGNAL_COLORS = {
    True:  "#2E7D32",   # 看多 — 綠
    False: "#C62828",   # 看空 — 紅
    None:  "#546E7A",   # 中性 — 灰藍
}


def build_etf_flex_card(analysis: dict[str, Any]) -> dict:
    """
    依照 Orchestrator 回傳的 analysis dict，
    產生 LINE Flex Message Bubble 物件（Python dict）。
    """
    symbol       = analysis["symbol"]
    etf_info     = analysis["etf_info"]
    price        = analysis["latest_price"]
    date_str     = analysis["latest_date"]
    final_action = analysis["final_action"]
    total_score  = analysis["total_score"]
    confidence   = analysis["confidence"]
    agent_results = analysis["agent_results"]
    generated_at  = analysis["generated_at"]

    action_meta   = ACTION_LABELS.get(final_action, {"emoji": "➖", "color": "#546E7A"})
    header_color  = _ACTION_HEADER_COLOR.get(final_action, "#37474F")

    # ── Header ───────────────────────────────────────────────────────────────
    header = {
        "type": "box",
        "layout": "vertical",
        "backgroundColor": header_color,
        "paddingAll": "16px",
        "contents": [
            {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "text",
                        "text": f"{etf_info['name']} ({symbol})",
                        "color": "#FFFFFF",
                        "size": "lg",
                        "weight": "bold",
                        "flex": 4,
                    },
                    {
                        "type": "text",
                        "text": etf_info.get("risk_level", "-") + " 風險",
                        "color": "#FFFFFFcc",
                        "size": "sm",
                        "align": "end",
                        "flex": 2,
                    },
                ],
            },
            {
                "type": "text",
                "text": etf_info["description"],
                "color": "#FFFFFFaa",
                "size": "xs",
                "margin": "sm",
            },
        ],
    }

    # ── 價格區塊 ──────────────────────────────────────────────────────────────
    price_box = {
        "type": "box",
        "layout": "horizontal",
        "margin": "md",
        "contents": [
            {
                "type": "box",
                "layout": "vertical",
                "flex": 3,
                "contents": [
                    {"type": "text", "text": "最新收盤價", "size": "xs", "color": "#888888"},
                    {"type": "text", "text": f"NT$ {price:.2f}", "size": "xl", "weight": "bold", "color": "#212121"},
                    {"type": "text", "text": f"資料日期：{date_str}", "size": "xxs", "color": "#AAAAAA"},
                ],
            },
            {
                "type": "separator",
                "margin": "md",
            },
            {
                "type": "box",
                "layout": "vertical",
                "flex": 3,
                "paddingStart": "12px",
                "contents": [
                    {"type": "text", "text": "AI 綜合判斷", "size": "xs", "color": "#888888"},
                    {
                        "type": "text",
                        "text": f"{action_meta['emoji']} {final_action}",
                        "size": "lg",
                        "weight": "bold",
                        "color": action_meta["color"],
                    },
                    {"type": "text", "text": f"信心度 {confidence}%", "size": "xs", "color": "#888888"},
                ],
            },
        ],
    }

    # ── 分數條 ────────────────────────────────────────────────────────────────
    score_label = f"綜合分數：{total_score:+.1f}"
    score_bar = _build_score_bar(total_score)

    # ── Agent 彙整 ────────────────────────────────────────────────────────────
    agent_summary_rows = []
    for r in agent_results:
        action_color = next(
            (v["color"] for k, v in ACTION_LABELS.items() if k == r["action"]),
            "#546E7A",
        )
        agent_summary_rows.append({
            "type": "box",
            "layout": "horizontal",
            "paddingTop": "4px",
            "paddingBottom": "4px",
            "contents": [
                {
                    "type": "text",
                    "text": r["agent"],
                    "size": "sm",
                    "color": "#333333",
                    "flex": 5,
                },
                {
                    "type": "text",
                    "text": r["action"],
                    "size": "sm",
                    "color": action_color,
                    "weight": "bold",
                    "align": "end",
                    "flex": 2,
                },
            ],
        })

    agent_section = {
        "type": "box",
        "layout": "vertical",
        "margin": "lg",
        "contents": [
            _section_title("🤖 Agent 判斷摘要"),
            {"type": "separator", "margin": "sm"},
            *agent_summary_rows,
        ],
    }

    # ── 各 Agent 訊號明細（只顯示前三個 Agent 的訊號，避免卡片過長）──────────
    signal_sections = []
    for r in agent_results[:3]:   # 顯示技術、量能、趨勢三個 agent
        rows = []
        for sig in r["signals"][:4]:  # 每個 agent 最多顯示 4 個訊號
            color = _SIGNAL_COLORS.get(sig["bullish"], "#546E7A")
            rows.append({
                "type": "box",
                "layout": "horizontal",
                "paddingTop": "3px",
                "paddingBottom": "3px",
                "contents": [
                    {
                        "type": "text",
                        "text": sig["label"],
                        "size": "xs",
                        "color": "#555555",
                        "flex": 3,
                    },
                    {
                        "type": "text",
                        "text": sig["value"],
                        "size": "xs",
                        "color": color,
                        "align": "end",
                        "flex": 4,
                        "wrap": True,
                    },
                ],
            })
        if rows:
            signal_sections.append({
                "type": "box",
                "layout": "vertical",
                "margin": "md",
                "contents": [
                    _section_title(r["agent"]),
                    {"type": "separator", "margin": "sm"},
                    *rows,
                ],
            })

    # ── 風險 Agent 訊號（獨立顯示）──────────────────────────────────────────
    risk_result = next((r for r in agent_results if "風險" in r["agent"]), None)
    risk_section_contents = []
    if risk_result:
        for sig in risk_result["signals"]:
            color = _SIGNAL_COLORS.get(sig["bullish"], "#546E7A")
            risk_section_contents.append({
                "type": "box",
                "layout": "horizontal",
                "paddingTop": "3px",
                "paddingBottom": "3px",
                "contents": [
                    {"type": "text", "text": sig["label"], "size": "xs", "color": "#555555", "flex": 3},
                    {"type": "text", "text": sig["value"], "size": "xs", "color": color,
                     "align": "end", "flex": 4, "wrap": True},
                ],
            })

    risk_section = {
        "type": "box",
        "layout": "vertical",
        "margin": "md",
        "backgroundColor": "#FFF8E1",
        "paddingAll": "10px",
        "cornerRadius": "8px",
        "contents": [
            _section_title("⚠️ 風險評估"),
            {"type": "separator", "margin": "sm"},
            *risk_section_contents,
        ],
    }

    # ── Body ─────────────────────────────────────────────────────────────────
    body = {
        "type": "box",
        "layout": "vertical",
        "paddingAll": "16px",
        "contents": [
            price_box,
            {"type": "separator", "margin": "lg"},
            {
                "type": "box",
                "layout": "vertical",
                "margin": "lg",
                "contents": [
                    {"type": "text", "text": score_label, "size": "xs", "color": "#555555"},
                    score_bar,
                ],
            },
            agent_section,
            *signal_sections,
            risk_section,
        ],
    }

    # ── Footer ────────────────────────────────────────────────────────────────
    footer = {
        "type": "box",
        "layout": "vertical",
        "backgroundColor": "#F5F5F5",
        "paddingAll": "12px",
        "contents": [
            {
                "type": "text",
                "text": f"⏱ 更新時間：{generated_at}",
                "size": "xxs",
                "color": "#AAAAAA",
                "align": "center",
            },
            {
                "type": "text",
                "text": "⚠️ 本資訊僅供參考，不構成投資建議",
                "size": "xxs",
                "color": "#BBBBBB",
                "align": "center",
                "margin": "sm",
            },
        ],
    }

    bubble = {
        "type": "bubble",
        "size": "kilo",
        "header": header,
        "body": body,
        "footer": footer,
        "styles": {
            "header": {"separator": False},
            "footer": {"separator": True},
        },
    }

    return {
        "type": "flex",
        "altText": f"{etf_info['name']}({symbol}) AI分析：{final_action}，信心度{confidence}%，現價NT${price:.2f}",
        "contents": bubble,
    }


def build_dual_etf_carousel(analysis_0050: dict, analysis_00631L: dict) -> dict:
    """
    將兩支 ETF 的卡片組合為 Carousel（左右滑動）。
    """
    card_0050   = build_etf_flex_card(analysis_0050)["contents"]
    card_00631L = build_etf_flex_card(analysis_00631L)["contents"]

    return {
        "type": "flex",
        "altText": "ETF AI 多空分析（0050 & 00631L）",
        "contents": {
            "type": "carousel",
            "contents": [card_0050, card_00631L],
        },
    }


# ── 工具函式 ──────────────────────────────────────────────────────────────────

def _section_title(text: str) -> dict:
    return {
        "type": "text",
        "text": text,
        "size": "sm",
        "weight": "bold",
        "color": "#333333",
    }


def _build_score_bar(score: float) -> dict:
    """
    用一列方塊視覺化總分（-8 ~ +8 映射到 0~100%）。
    正分綠色，負分紅色。
    """
    clamped = max(-8.0, min(8.0, score))
    pct = int((clamped + 8) / 16 * 100)
    color = "#2E7D32" if score >= 0 else "#C62828"

    return {
        "type": "box",
        "layout": "vertical",
        "margin": "xs",
        "contents": [
            {
                "type": "box",
                "layout": "vertical",
                "height": "8px",
                "backgroundColor": "#EEEEEE",
                "cornerRadius": "4px",
                "contents": [
                    {
                        "type": "box",
                        "layout": "vertical",
                        "backgroundColor": color,
                        "height": "8px",
                        "cornerRadius": "4px",
                        "flex": pct,
                        "contents": [],
                    },
                ],
            }
        ],
    }
