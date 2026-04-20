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
from linebot.v3.webhooks import (
    FollowEvent,
    MessageEvent,
    TextMessageContent,
    UnfollowEvent,
)

from agents.orchestrator import Orchestrator
from data.db import add_subscriber, remove_subscriber
from linebot_utils.flex_card import build_etf_flex_card, build_etf_carousel
from config import ETF_CONFIG

logger = logging.getLogger(__name__)

_KEYWORD_MAP: dict[str, list[str]] = {
    "0050":   ["0050", "台灣50", "台50"],
    "00631L": ["00631l", "00631L", "正2", "槓桿", "leveraged"],
    "009816": ["009816", "凱基", "top50", "TOP50"],
    "00981A": ["00981a", "00981A", "統一成長", "主動", "成長"],
    "all":    ["all", "全部", "比較", "分析", "both", "所有"],
}

HELP_TEXT = (
    "📋 ETF AI 分析機器人\n\n"
    "🔍 支援指令：\n"
    "  • 「0050」 → 元大台灣50\n"
    "  • 「00631L」 → 元大台灣50正2（槓桿）\n"
    "  • 「009816」 → 凱基台灣TOP50\n"
    "  • 「00981A」 → 統一台灣成長主動\n"
    "  • 「分析」 → 全部 4 支 ETF 比較\n\n"
    "📩 盤前推播：\n"
    "  • 「訂閱」 → 加入每日早盤推播\n"
    "  • 「取消訂閱」 → 停止推播\n\n"
    "⚠️ 本資訊僅供參考，不構成投資建議。"
)

SUBSCRIBE_TEXT = (
    "✅ 訂閱成功！\n"
    "每個交易日早上 8:00 將自動推播 ETF AI 分析報告。\n\n"
    "輸入「取消訂閱」可隨時退訂。"
)

UNSUBSCRIBE_TEXT = "🔕 已取消訂閱，不再接收每日推播。"


def _messaging_api() -> MessagingApi:
    config = Configuration(access_token=os.environ["LINE_CHANNEL_ACCESS_TOKEN"])
    return MessagingApi(ApiClient(config))


def _parse_target(text: str) -> str | None:
    lower = text.strip().lower()
    for key, keywords in _KEYWORD_MAP.items():
        if any(kw.lower() in lower for kw in keywords):
            return key
    return None


# ── 公開進入點（by app.py 分派） ────────────────────────────────────────────────

def handle_follow_event(event: FollowEvent) -> None:
    """加好友時自動訂閱並歡迎。"""
    user_id = event.source.user_id
    add_subscriber(user_id)
    logger.info("[Subscribe] follow — %s", user_id)

    api = _messaging_api()
    _reply_text(api, event.reply_token,
                "👋 歡迎加入 ETF AI 分析機器人！\n\n" + SUBSCRIBE_TEXT)


def handle_unfollow_event(event: UnfollowEvent) -> None:
    """封鎖/刪除好友時自動退訂。"""
    user_id = event.source.user_id
    remove_subscriber(user_id)
    logger.info("[Unsubscribe] unfollow — %s", user_id)


def handle_message_event(event: MessageEvent) -> None:
    """處理文字訊息。"""
    if not isinstance(event.message, TextMessageContent):
        return

    text = event.message.text.strip()
    reply_token = event.reply_token
    user_id = event.source.user_id
    api = _messaging_api()

    # 訂閱 / 取消訂閱
    if text in ("訂閱", "subscribe"):
        add_subscriber(user_id)
        logger.info("[Subscribe] message — %s", user_id)
        _reply_text(api, reply_token, SUBSCRIBE_TEXT)
        return

    if text in ("取消訂閱", "退訂", "unsubscribe"):
        remove_subscriber(user_id)
        logger.info("[Unsubscribe] message — %s", user_id)
        _reply_text(api, reply_token, UNSUBSCRIBE_TEXT)
        return

    # ETF 分析
    target = _parse_target(text)
    if target is None:
        _reply_text(api, reply_token, HELP_TEXT)
        return

    try:
        if target == "all":
            _reply_all(api, reply_token)
        else:
            _reply_single(api, reply_token, target)
    except Exception as exc:
        logger.exception("分析失敗：%s", exc)
        _reply_text(api, reply_token, f"⚠️ 分析時發生錯誤，請稍後再試。\n錯誤：{exc}")


# ── 內部回覆函式 ──────────────────────────────────────────────────────────────

def _reply_single(api: MessagingApi, reply_token: str, symbol: str) -> None:
    analysis = Orchestrator(symbol).run()
    flex_payload = build_etf_flex_card(analysis)
    api.reply_message(ReplyMessageRequest(
        reply_token=reply_token,
        messages=[FlexMessage(
            alt_text=flex_payload["altText"],
            contents=flex_payload["contents"],
        )],
    ))


def _reply_all(api: MessagingApi, reply_token: str) -> None:
    from concurrent.futures import ThreadPoolExecutor
    symbols = list(ETF_CONFIG.keys())
    with ThreadPoolExecutor(max_workers=len(symbols)) as ex:
        analyses = list(ex.map(lambda s: Orchestrator(s).run(), symbols))
    carousel = build_etf_carousel(*analyses)
    api.reply_message(ReplyMessageRequest(
        reply_token=reply_token,
        messages=[FlexMessage(
            alt_text=carousel["altText"],
            contents=carousel["contents"],
        )],
    ))


def _reply_text(api: MessagingApi, reply_token: str, text: str) -> None:
    api.reply_message(ReplyMessageRequest(
        reply_token=reply_token,
        messages=[TextMessage(text=text)],
    ))
