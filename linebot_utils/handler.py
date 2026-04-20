"""
LINE Webhook 事件處理器
"""
from __future__ import annotations

import logging
import os

from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    FlexContainer,
    FlexMessage,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import (
    FollowEvent,
    MessageEvent,
    TextMessageContent,
    UnfollowEvent,
)

from agents.orchestrator import Orchestrator
from data.db import add_subscriber, get_analysis, remove_subscriber
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
    "🔍 查詢指令：\n"
    "  • 「0050」→ 顯示上次分析結果\n"
    "  • 「刷新 0050」→ 重新分析（較慢）\n"
    "  • 「00631L」「009816」「00981A」同上\n"
    "  • 「分析」→ 全部 4 支上次結果\n\n"
    "📩 推播訂閱：\n"
    "  • 「訂閱」→ 加入每日早盤推播\n"
    "  • 「取消訂閱」→ 停止推播\n\n"
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


def _parse_refresh(text: str) -> str | None:
    """判斷是否為「刷新 <ETF>」指令，回傳 ETF symbol 或 None。"""
    lower = text.strip().lower()
    for prefix in ("刷新 ", "刷新", "refresh ", "重新分析 ", "重新分析"):
        if lower.startswith(prefix):
            rest = text[len(prefix):].strip()
            target = _parse_target(rest)
            if target and target != "all":
                return target
    return None


# ── 公開進入點 ────────────────────────────────────────────────────────────────

def handle_follow_event(event: FollowEvent) -> None:
    user_id = event.source.user_id
    add_subscriber(user_id)
    logger.info("[Subscribe] follow — %s", user_id)
    api = _messaging_api()
    _reply_text(api, event.reply_token,
                "👋 歡迎加入 ETF AI 分析機器人！\n\n" + SUBSCRIBE_TEXT)


def handle_unfollow_event(event: UnfollowEvent) -> None:
    user_id = event.source.user_id
    remove_subscriber(user_id)
    logger.info("[Unsubscribe] unfollow — %s", user_id)


def handle_message_event(event: MessageEvent) -> None:
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

    # 刷新（強制重新分析）
    refresh_symbol = _parse_refresh(text)
    if refresh_symbol:
        try:
            _reply_text(api, reply_token, f"⏳ 正在重新分析 {refresh_symbol}，請稍候...")
            _push_fresh(api, event.source.user_id, refresh_symbol)
        except Exception as exc:
            logger.exception("刷新分析失敗：%s", exc)
        return

    # ETF 查詢（優先顯示快取）
    target = _parse_target(text)
    if target is None:
        _reply_text(api, reply_token, HELP_TEXT)
        return

    try:
        if target == "all":
            _reply_all_cached(api, reply_token)
        else:
            _reply_single_cached(api, reply_token, target)
    except Exception as exc:
        logger.exception("查詢失敗：%s", exc)
        _reply_text(api, reply_token, f"⚠️ 查詢失敗，請稍後再試。\n錯誤：{exc}")


# ── 快取查詢 ──────────────────────────────────────────────────────────────────

def _reply_single_cached(api: MessagingApi, reply_token: str, symbol: str) -> None:
    """優先回傳快取結果；無快取才即時分析。"""
    cached = get_analysis(symbol)
    if cached:
        analysis, updated_at = cached
        flex_payload = build_etf_flex_card(analysis)
        messages = [
            TextMessage(text=f"📂 {symbol} 上次分析：{updated_at}\n輸入「刷新 {symbol}」取得最新結果"),
            FlexMessage(
                alt_text=flex_payload["altText"],
                contents=FlexContainer.from_dict(flex_payload["contents"]),
            ),
        ]
        api.reply_message(ReplyMessageRequest(reply_token=reply_token, messages=messages))
        logger.info("[Cache Hit] %s (%s)", symbol, updated_at)
    else:
        # 無快取 → 即時分析
        _reply_text(api, reply_token, f"⏳ 尚無 {symbol} 快取，正在分析中...")
        _push_fresh(api, None, symbol, reply_token=reply_token)


def _reply_all_cached(api: MessagingApi, reply_token: str) -> None:
    """全部 ETF 快取結果 Carousel；任一無快取則即時分析該支。"""
    symbols = list(ETF_CONFIG.keys())
    analyses = []
    missing = []
    for s in symbols:
        cached = get_analysis(s)
        if cached:
            analyses.append((s, cached[0], cached[1]))
        else:
            missing.append(s)

    if missing:
        _reply_text(api, reply_token,
                    f"⏳ {', '.join(missing)} 尚無快取，正在分析，完成後將推播...")
        for s in missing:
            from agents.orchestrator import Orchestrator
            from data.db import save_analysis
            result = Orchestrator(s).run()
            save_analysis(s, result)
            analyses.append((s, result, result["generated_at"]))

    analyses.sort(key=lambda x: symbols.index(x[0]))
    latest_time = max(a[2] for a in analyses)
    carousel = build_etf_carousel(*[a[1] for a in analyses])

    messages = [
        TextMessage(text=f"📂 全部 ETF 上次分析：{latest_time}"),
        FlexMessage(
            alt_text=carousel["altText"],
            contents=FlexContainer.from_dict(carousel["contents"]),
        ),
    ]
    api.reply_message(ReplyMessageRequest(reply_token=reply_token, messages=messages))


# ── 強制重新分析（刷新） ──────────────────────────────────────────────────────

def _push_fresh(
    api: MessagingApi,
    user_id: str | None,
    symbol: str,
    reply_token: str | None = None,
) -> None:
    """重新執行分析、存快取，再回覆或推播給用戶。"""
    from agents.orchestrator import Orchestrator
    from data.db import save_analysis
    from linebot.v3.messaging import PushMessageRequest

    analysis = Orchestrator(symbol).run()
    save_analysis(symbol, analysis)
    flex_payload = build_etf_flex_card(analysis)
    messages = [
        FlexMessage(
            alt_text=flex_payload["altText"],
            contents=FlexContainer.from_dict(flex_payload["contents"]),
        )
    ]

    if reply_token:
        api.reply_message(ReplyMessageRequest(reply_token=reply_token, messages=messages))
    elif user_id:
        api.push_message(PushMessageRequest(to=user_id, messages=messages))

    logger.info("[Fresh] %s 重新分析完成（%s）", symbol, analysis["final_action"])


# ── 回覆工具 ──────────────────────────────────────────────────────────────────

def _reply_text(api: MessagingApi, reply_token: str, text: str) -> None:
    api.reply_message(ReplyMessageRequest(
        reply_token=reply_token,
        messages=[TextMessage(text=text)],
    ))
