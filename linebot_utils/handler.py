"""
LINE Webhook 事件處理器
"""
from __future__ import annotations

import logging
import os

from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    ReplyMessageRequest,
    FlexMessage,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

from agents.orchestrator import Orchestrator
from linebot_utils.flex_card import build_etf_flex_card, build_dual_etf_carousel
from config import ETF_CONFIG

logger = logging.getLogger(__name__)

# ETF 關鍵字對應對照表
_KEYWORD_MAP: dict[str, list[str]] = {
    "0050":   ["0050", "台灣50", "台50"],
    "00631L": ["00631l", "00631L", "正2", "槓桿", "leveraged"],
    "both":   ["both", "全部", "兩個", "比較", "分析", "all"],
}

HELP_TEXT = (
    "📋 ETF AI 分析機器人\n\n"
    "🔍 支援指令：\n"
    "  • 傳送 「0050」 → 元大台灣50 分析\n"
    "  • 傳送 「00631L」 → 元大台灣50正2 分析\n"
    "  • 傳送 「分析」 → 同時顯示兩支 ETF\n\n"
    "⚠️ 本資訊僅供參考，不構成投資建議。"
)


def _messaging_api() -> MessagingApi:
    config = Configuration(access_token=os.environ["LINE_CHANNEL_ACCESS_TOKEN"])
    return MessagingApi(ApiClient(config))


def _parse_target(text: str) -> str | None:
    """根據使用者輸入判斷要分析哪支（哪些）ETF"""
    lower = text.strip().lower()
    for key, keywords in _KEYWORD_MAP.items():
        if any(kw.lower() in lower for kw in keywords):
            return key
    return None


def handle_message_event(event: MessageEvent) -> None:
    """處理使用者傳入的文字訊息，回傳對應 Flex 卡片。"""
    if not isinstance(event.message, TextMessageContent):
        return

    text = event.message.text
    reply_token = event.reply_token
    api = _messaging_api()

    target = _parse_target(text)
    if target is None:
        _reply_text(api, reply_token, HELP_TEXT)
        return

    try:
        if target == "both":
            _reply_dual(api, reply_token)
        else:
            _reply_single(api, reply_token, target)
    except Exception as exc:
        logger.exception("分析失敗：%s", exc)
        _reply_text(api, reply_token, f"⚠️ 分析時發生錯誤，請稍後再試。\n錯誤：{exc}")


# ── 內部回覆函式 ──────────────────────────────────────────────────────────────

def _reply_single(api: MessagingApi, reply_token: str, symbol: str) -> None:
    orchestrator = Orchestrator(symbol)
    analysis = orchestrator.run()
    flex_payload = build_etf_flex_card(analysis)

    api.reply_message(
        ReplyMessageRequest(
            reply_token=reply_token,
            messages=[
                FlexMessage(
                    alt_text=flex_payload["altText"],
                    contents=flex_payload["contents"],
                )
            ],
        )
    )


def _reply_dual(api: MessagingApi, reply_token: str) -> None:
    analysis_0050   = Orchestrator("0050").run()
    analysis_00631L = Orchestrator("00631L").run()
    carousel = build_dual_etf_carousel(analysis_0050, analysis_00631L)

    api.reply_message(
        ReplyMessageRequest(
            reply_token=reply_token,
            messages=[
                FlexMessage(
                    alt_text=carousel["altText"],
                    contents=carousel["contents"],
                )
            ],
        )
    )


def _reply_text(api: MessagingApi, reply_token: str, text: str) -> None:
    api.reply_message(
        ReplyMessageRequest(
            reply_token=reply_token,
            messages=[TextMessage(text=text)],
        )
    )
