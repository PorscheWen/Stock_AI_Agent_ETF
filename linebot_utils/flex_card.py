"""
Flex Message 卡片產生器 — 左右橫排圖卡版
bubble size: mega，Agent 判斷 2×2 格、訊號左右雙欄排列。
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
    True:  "#2E7D32",
    False: "#C62828",
    None:  "#546E7A",
}


def build_etf_flex_card(analysis: dict[str, Any]) -> dict:
    symbol        = analysis["symbol"]
    etf_info      = analysis["etf_info"]
    price         = analysis["latest_price"]
    date_str      = analysis["latest_date"]
    final_action  = analysis["final_action"]
    total_score   = analysis["total_score"]
    confidence    = analysis["confidence"]
    stop_loss     = analysis.get("stop_loss")
    take_profit   = analysis.get("take_profit")
    recommendation = analysis.get("recommendation", {})
    agent_results = analysis["agent_results"]
    generated_at  = analysis["generated_at"]

    action_meta  = ACTION_LABELS.get(final_action, {"emoji": "➖", "color": "#546E7A"})
    header_color = _ACTION_HEADER_COLOR.get(final_action, "#37474F")

    # ── Header ───────────────────────────────────────────────────────────────
    header = {
        "type": "box",
        "layout": "horizontal",
        "backgroundColor": header_color,
        "paddingAll": "14px",
        "contents": [
            {
                "type": "box",
                "layout": "vertical",
                "flex": 5,
                "contents": [
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "text",
                                "text": etf_info["name"],
                                "color": "#FFFFFF",
                                "size": "md",
                                "weight": "bold",
                                "flex": 0,
                            },
                            {
                                "type": "text",
                                "text": f"  {symbol}",
                                "color": "#FFFFFFaa",
                                "size": "sm",
                                "flex": 0,
                            },
                        ],
                    },
                    {
                        "type": "text",
                        "text": etf_info["description"],
                        "color": "#FFFFFFaa",
                        "size": "xxs",
                        "margin": "xs",
                        "wrap": True,
                    },
                ],
            },
            {
                "type": "box",
                "layout": "vertical",
                "flex": 3,
                "alignItems": "flex-end",
                "contents": [
                    {
                        "type": "text",
                        "text": f"{action_meta['emoji']} {final_action}",
                        "color": "#FFFFFF",
                        "size": "sm",
                        "weight": "bold",
                        "align": "end",
                    },
                    {
                        "type": "text",
                        "text": f"信心 {confidence}%",
                        "color": "#FFFFFFcc",
                        "size": "xs",
                        "align": "end",
                        "margin": "xs",
                    },
                    {
                        "type": "text",
                        "text": etf_info.get("risk_level", "-") + " 風險",
                        "color": "#FFFFFFaa",
                        "size": "xxs",
                        "align": "end",
                        "margin": "xs",
                    },
                ],
            },
        ],
    }

    # ── 價格 + 停損停利（左側現價 / 右側停損+停利同欄） ────────────────────
    price_right = []
    if stop_loss and take_profit:
        price_right = [
            {"type": "separator", "margin": "sm"},
            {
                "type": "box",
                "layout": "vertical",
                "flex": 5,
                "alignItems": "flex-end",
                "contents": [
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {"type": "text", "text": "停利", "size": "xxs", "color": "#888888", "flex": 0},
                            {"type": "text", "text": f"  NT${take_profit:.2f}", "size": "sm",
                             "weight": "bold", "color": "#C62828", "flex": 0},
                        ],
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "margin": "sm",
                        "contents": [
                            {"type": "text", "text": "停損", "size": "xxs", "color": "#888888", "flex": 0},
                            {"type": "text", "text": f"  NT${stop_loss:.2f}", "size": "sm",
                             "weight": "bold", "color": "#2E7D32", "flex": 0},
                        ],
                    },
                ],
            },
        ]

    price_row = {
        "type": "box",
        "layout": "horizontal",
        "margin": "md",
        "contents": [
            {
                "type": "box",
                "layout": "vertical",
                "flex": 5,
                "contents": [
                    {"type": "text", "text": "現價", "size": "xxs", "color": "#888888"},
                    {"type": "text", "text": f"NT${price:.2f}", "size": "xl",
                     "weight": "bold", "color": "#212121", "adjustMode": "shrink-to-fit"},
                    {"type": "text", "text": date_str, "size": "xxs", "color": "#BBBBBB"},
                ],
            },
            *price_right,
        ],
    }

    # ── 分數橫條 ──────────────────────────────────────────────────────────────
    score_row = {
        "type": "box",
        "layout": "horizontal",
        "margin": "md",
        "contents": [
            {
                "type": "text",
                "text": f"綜合分數 {total_score:+.1f}",
                "size": "xxs",
                "color": "#666666",
                "flex": 0,
            },
            {
                "type": "box",
                "layout": "vertical",
                "flex": 1,
                "margin": "sm",
                "justifyContent": "center",
                "contents": [_build_score_bar(total_score)],
            },
        ],
    }

    # ── Agent 判斷 2×2 橫排格 ────────────────────────────────────────────────
    agent_cells = []
    for r in agent_results:
        action_color = next(
            (v["color"] for k, v in ACTION_LABELS.items() if k == r["action"]),
            "#546E7A",
        )
        agent_cells.append({
            "type": "box",
            "layout": "vertical",
            "flex": 1,
            "backgroundColor": "#F8F8F8",
            "cornerRadius": "6px",
            "paddingAll": "8px",
            "contents": [
                {
                    "type": "text",
                    "text": r["agent"].replace(" Agent", ""),
                    "size": "xxs",
                    "color": "#666666",
                    "wrap": True,
                },
                {
                    "type": "text",
                    "text": r["action"],
                    "size": "xs",
                    "weight": "bold",
                    "color": action_color,
                    "margin": "xs",
                },
            ],
        })

    # 兩個一排，共兩排
    agent_grid = {
        "type": "box",
        "layout": "vertical",
        "margin": "md",
        "spacing": "sm",
        "contents": [
            {
                "type": "box",
                "layout": "horizontal",
                "spacing": "sm",
                "contents": agent_cells[:2],
            },
            {
                "type": "box",
                "layout": "horizontal",
                "spacing": "sm",
                "contents": agent_cells[2:4],
            },
        ],
    }

    # ── 訊號左右雙欄（技術 + 量能 | 趨勢 + 風險） ───────────────────────────
    _AGENT_TITLES = ["📊 技術", "📦 量能", "🔭 趨勢", "⚠️ 風險"]
    signal_col_groups = []
    for r, title in zip(agent_results, _AGENT_TITLES):
        rows = []
        for sig in r["signals"][:3]:
            color = _SIGNAL_COLORS.get(sig["bullish"], "#546E7A")
            rows.append({
                "type": "box",
                "layout": "horizontal",
                "paddingTop": "2px",
                "paddingBottom": "2px",
                "contents": [
                    {
                        "type": "text",
                        "text": sig["label"],
                        "size": "xxs",
                        "color": "#777777",
                        "flex": 2,
                        "wrap": True,
                    },
                    {
                        "type": "text",
                        "text": sig["value"].split(" ")[0],  # 只取數值/狀態，不含 emoji
                        "size": "xxs",
                        "color": color,
                        "align": "end",
                        "flex": 3,
                        "wrap": True,
                    },
                ],
            })
        signal_col_groups.append({
            "type": "box",
            "layout": "vertical",
            "flex": 1,
            "backgroundColor": "#FAFAFA",
            "cornerRadius": "6px",
            "paddingAll": "8px",
            "contents": [
                {
                    "type": "text",
                    "text": title,
                    "size": "xs",
                    "weight": "bold",
                    "color": "#444444",
                    "margin": "none",
                },
                {"type": "separator", "margin": "xs"},
                *rows,
            ],
        })

    signal_section = {
        "type": "box",
        "layout": "vertical",
        "margin": "md",
        "spacing": "sm",
        "contents": [
            {
                "type": "box",
                "layout": "horizontal",
                "spacing": "sm",
                "contents": signal_col_groups[:2],
            },
            {
                "type": "box",
                "layout": "horizontal",
                "spacing": "sm",
                "contents": signal_col_groups[2:4],
            },
        ],
    }

    # ── 操作建議（compact 單行） ──────────────────────────────────────────────
    rec_contents = []
    if recommendation:
        summary = recommendation.get("summary", "")
        entry   = recommendation.get("entry", "")
        note    = recommendation.get("note", "")
        if summary:
            rec_contents.append({
                "type": "text", "text": summary,
                "size": "xs", "color": "#333333", "wrap": True,
            })
        if entry:
            rec_contents.append({
                "type": "text", "text": entry,
                "size": "xs", "color": "#555555", "wrap": True, "margin": "xs",
            })
        if note:
            rec_contents.append({
                "type": "text", "text": note,
                "size": "xs", "color": "#C62828", "wrap": True,
                "margin": "sm", "weight": "bold",
            })

    rec_section = {
        "type": "box",
        "layout": "vertical",
        "margin": "md",
        "backgroundColor": "#E8F5E9",
        "paddingAll": "10px",
        "cornerRadius": "8px",
        "contents": [
            _section_title("📋 操作建議"),
            {"type": "separator", "margin": "xs"},
            *rec_contents,
        ],
    } if rec_contents else None

    # ── 精確操作建議（AdviceAgent） ───────────────────────────────────────────
    advice = analysis.get("advice") or {}
    advice_section = None
    if advice:
        conf_color   = advice.get("confidence_color", "#E65100")
        conf_label   = advice.get("confidence_label", "中等信心")
        conf_pct     = advice.get("confidence", 0)
        consensus    = advice.get("consensus", "")
        position_pct = advice.get("position_pct", "—")
        entry_advice = advice.get("entry_advice", "")
        points       = advice.get("points", [])
        risk_warning = advice.get("risk_warning", "")

        # 標題列：「🎯 精確操作建議」+「● 高信心 82%」
        advice_header_row = {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                _section_title("🎯 精確操作建議"),
                {
                    "type": "box",
                    "layout": "horizontal",
                    "flex": 0,
                    "contents": [
                        {
                            "type": "text",
                            "text": "●",
                            "color": conf_color,
                            "size": "xs",
                            "flex": 0,
                        },
                        {
                            "type": "text",
                            "text": f" {conf_label} {conf_pct}%",
                            "color": conf_color,
                            "size": "xs",
                            "weight": "bold",
                            "flex": 0,
                        },
                    ],
                },
            ],
        }

        # 共識 + 建議倉位
        meta_row = {
            "type": "box",
            "layout": "horizontal",
            "margin": "sm",
            "contents": [
                {
                    "type": "text",
                    "text": consensus,
                    "size": "xs",
                    "color": conf_color,
                    "weight": "bold",
                    "flex": 0,
                },
                {
                    "type": "text",
                    "text": f"  建議倉位 {position_pct}",
                    "size": "xs",
                    "color": "#555555",
                    "flex": 0,
                },
            ],
        }

        # 進場建議
        entry_row = {
            "type": "text",
            "text": entry_advice,
            "size": "xs",
            "color": "#333333",
            "wrap": True,
            "margin": "xs",
        }

        # 關鍵重點列表
        point_rows = [
            {
                "type": "text",
                "text": f"• {pt}",
                "size": "xxs",
                "color": "#555555",
                "wrap": True,
                "margin": "xs",
            }
            for pt in points
        ]

        # 風險警示（有則顯示）
        risk_rows = []
        if risk_warning:
            risk_rows = [
                {"type": "separator", "margin": "sm"},
                {
                    "type": "text",
                    "text": risk_warning,
                    "size": "xs",
                    "color": "#C62828",
                    "wrap": True,
                    "weight": "bold",
                    "margin": "sm",
                },
            ]

        advice_section = {
            "type": "box",
            "layout": "vertical",
            "margin": "md",
            "backgroundColor": "#F1F8E9",
            "paddingAll": "10px",
            "cornerRadius": "8px",
            "contents": [
                advice_header_row,
                {"type": "separator", "margin": "xs"},
                meta_row,
                entry_row,
                *point_rows,
                *risk_rows,
            ],
        }

    # ── LLM 盤勢解讀 ─────────────────────────────────────────────────────────
    llm_text = (analysis.get("llm_commentary") or "").strip()
    llm_section = None
    if llm_text:
        llm_section = {
            "type": "box",
            "layout": "vertical",
            "margin": "md",
            "backgroundColor": "#E3F2FD",
            "paddingAll": "10px",
            "cornerRadius": "8px",
            "contents": [
                _section_title("AI 盤勢解讀"),
                {"type": "separator", "margin": "xs"},
                {
                    "type": "text",
                    "text": llm_text,
                    "size": "xs",
                    "color": "#1565C0",
                    "wrap": True,
                },
            ],
        }

    # ── 價格跌幅警示橫幅 ──────────────────────────────────────────────────────
    price_alert_level = analysis.get("price_alert_level", "none")
    price_alerts_data  = analysis.get("price_alerts", [])
    alert_banner = None
    if price_alert_level in ("critical", "warning") and price_alerts_data:
        if price_alert_level == "critical":
            banner_bg   = "#B71C1C"
            banner_text = "  ".join(
                f"{a['label']} {a['value']}" for a in price_alerts_data
                if "critical" in a.get("label", "") or "🚨" in a.get("label", "")
            ) or price_alerts_data[0]["value"]
        else:
            banner_bg   = "#E65100"
            banner_text = "  ".join(
                f"{a['label']} {a['value']}" for a in price_alerts_data
            )
        alert_banner = {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": banner_bg,
            "paddingAll": "10px",
            "cornerRadius": "6px",
            "margin": "md",
            "contents": [
                {
                    "type": "text",
                    "text": banner_text,
                    "color": "#FFFFFF",
                    "size": "xs",
                    "weight": "bold",
                    "wrap": True,
                }
            ],
        }

    # ── Body ─────────────────────────────────────────────────────────────────
    body_contents = []
    if alert_banner:
        body_contents.append(alert_banner)
    body_contents += [
        price_row,
        {"type": "separator", "margin": "md"},
        score_row,
        {"type": "separator", "margin": "md"},
        _section_title("🤖 Agent 判斷"),
        agent_grid,
        {"type": "separator", "margin": "md"},
        _section_title("📈 訊號明細"),
        signal_section,
    ]
    if rec_section:
        body_contents.append(rec_section)
    if advice_section:
        body_contents.append(advice_section)
    if llm_section:
        body_contents.append(llm_section)

    body = {
        "type": "box",
        "layout": "vertical",
        "paddingAll": "14px",
        "contents": body_contents,
    }

    # ── Footer ────────────────────────────────────────────────────────────────
    footer = {
        "type": "box",
        "layout": "vertical",
        "backgroundColor": "#F5F5F5",
        "paddingAll": "10px",
        "contents": [
            {
                "type": "text",
                "text": f"⏱ {generated_at}　⚠️ 僅供參考，非投資建議",
                "size": "xxs",
                "color": "#AAAAAA",
                "align": "center",
                "wrap": True,
            },
        ],
    }

    bubble = {
        "type": "bubble",
        "size": "mega",
        "header": header,
        "body": body,
        "footer": footer,
        "styles": {
            "header": {"separator": False},
            "footer": {"separator": True},
        },
    }

    alert_prefix = ""
    if price_alert_level == "critical":
        alert_prefix = "🚨 急跌警示！"
    elif price_alert_level == "warning":
        alert_prefix = "⚠️ 下跌警示！"

    return {
        "type": "flex",
        "altText": f"{alert_prefix}{etf_info['name']}({symbol}) AI分析：{final_action}，信心度{confidence}%，現價NT${price:.2f}",
        "contents": bubble,
    }


def build_etf_carousel(*analyses: dict) -> dict:
    """將任意數量 ETF 分析結果組合為 Carousel（左右滑動）。"""
    bubbles = [build_etf_flex_card(a)["contents"] for a in analyses]
    names = "、".join(a["symbol"] for a in analyses)
    return {
        "type": "flex",
        "altText": f"ETF AI 多空分析（{names}）",
        "contents": {
            "type": "carousel",
            "contents": bubbles,
        },
    }


def build_dual_etf_carousel(analysis_0050: dict, analysis_00631L: dict) -> dict:
    return build_etf_carousel(analysis_0050, analysis_00631L)


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
    clamped = max(-3.5, min(3.5, score))
    pct = int((clamped + 3.5) / 7.0 * 100)
    color = "#2E7D32" if score >= 0 else "#C62828"
    return {
        "type": "box",
        "layout": "horizontal",
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
            {
                "type": "box",
                "layout": "vertical",
                "flex": 100 - pct,
                "contents": [],
            },
        ],
    }
