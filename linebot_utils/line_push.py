"""
LINE Push Notifier
主動推播 ETF 分析報告，不需要 Flask / ngrok / Webhook。
訂閱者清單優先從 SQLite 讀取（Render 環境），退回 LINE_USER_IDS 環境變數（GitHub Actions）。
"""
from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    FlexContainer,
    FlexMessage,
    MessagingApi,
    MulticastRequest,
    PushMessageRequest,
    TextMessage,
)

from concurrent.futures import ThreadPoolExecutor

from agents.orchestrator import Orchestrator
from config import ETF_CONFIG
from linebot_utils.flex_card import build_etf_carousel, build_etf_flex_card

load_dotenv()
logger = logging.getLogger(__name__)


def _get_api() -> MessagingApi:
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
    if not token:
        raise RuntimeError("LINE_CHANNEL_ACCESS_TOKEN 未設定")
    return MessagingApi(ApiClient(Configuration(access_token=token)))


def _get_user_ids() -> list[str]:
    """
    訂閱者清單讀取順序：
    1. SQLite data.db（Render web service 有 DB 時使用）
    2. LINE_USER_IDS 環境變數（逗號分隔，GitHub Actions fallback）
    3. LINE_USER_ID 環境變數（單人向下相容）
    """
    try:
        from data.db import get_subscribers
        ids = get_subscribers()
        if ids:
            logger.info("[Push] 從 DB 讀取訂閱者 %d 人", len(ids))
            return ids
    except Exception as exc:
        logger.warning("[Push] 無法讀取 DB，改用環境變數：%s", exc)

    ids_env = os.environ.get("LINE_USER_IDS", "")
    if ids_env:
        ids = [uid.strip() for uid in ids_env.split(",") if uid.strip()]
        if ids:
            logger.info("[Push] 從 LINE_USER_IDS 讀取 %d 人", len(ids))
            return ids

    single = os.environ.get("LINE_USER_ID", "").strip()
    if single:
        return [single]

    raise RuntimeError("找不到任何訂閱者（DB 空、LINE_USER_IDS、LINE_USER_ID 皆未設定）")


def _send(api: MessagingApi, user_ids: list[str], messages: list) -> None:
    """單人用 push_message，多人用 multicast（每批 ≤500）。"""
    if len(user_ids) == 1:
        api.push_message(PushMessageRequest(to=user_ids[0], messages=messages))
    else:
        for i in range(0, len(user_ids), 500):
            api.multicast(MulticastRequest(to=user_ids[i:i + 500], messages=messages))


def push_single(symbol: str) -> None:
    """分析單支 ETF 並推播給所有訂閱者。"""
    logger.info("[Push] 分析 %s ...", symbol)
    analysis = Orchestrator(symbol).run()
    payload = build_etf_flex_card(analysis)

    user_ids = _get_user_ids()
    _send(_get_api(), user_ids, [
        FlexMessage(
            alt_text=payload["altText"],
            contents=FlexContainer.from_dict(payload["contents"]),
        )
    ])
    logger.info("[Push] %s 推播成功（%s，信心 %d%%，%d 人）",
                symbol, analysis["final_action"], analysis["confidence"], len(user_ids))


def push_dual() -> None:
    """同時分析全部 ETF，以 Carousel 推播給所有訂閱者。"""
    symbols = list(ETF_CONFIG.keys())
    logger.info("[Push] 分析 %s ...", " + ".join(symbols))

    with ThreadPoolExecutor(max_workers=len(symbols)) as ex:
        analyses = list(ex.map(lambda s: Orchestrator(s).run(), symbols))

    carousel = build_etf_carousel(*analyses)

    user_ids = _get_user_ids()
    _send(_get_api(), user_ids, [
        FlexMessage(
            alt_text=carousel["altText"],
            contents=FlexContainer.from_dict(carousel["contents"]),
        )
    ])
    logger.info("[Push] %d 支 ETF Carousel 推播成功（%d 人）", len(symbols), len(user_ids))


def push_text(message: str) -> None:
    """推播純文字訊息給所有訂閱者（用於錯誤通知）。"""
    user_ids = _get_user_ids()
    _send(_get_api(), user_ids, [TextMessage(text=message)])
