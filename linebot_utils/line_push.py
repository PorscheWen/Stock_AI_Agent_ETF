"""
LINE Push Notifier
主動推播 ETF 分析報告，不需要 Flask / ngrok / Webhook。
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


def _get_user_id() -> str:
    uid = os.environ.get("LINE_USER_ID", "")
    if not uid:
        raise RuntimeError("LINE_USER_ID 未設定")
    return uid


def push_single(symbol: str) -> None:
    """分析單支 ETF 並推播。"""
    logger.info("[Push] 分析 %s ...", symbol)
    analysis = Orchestrator(symbol).run()
    payload = build_etf_flex_card(analysis)

    api = _get_api()
    api.push_message(
        PushMessageRequest(
            to=_get_user_id(),
            messages=[
                FlexMessage(
                    alt_text=payload["altText"],
                    contents=FlexContainer.from_dict(payload["contents"]),
                )
            ],
        )
    )
    logger.info("[Push] %s 推播成功（%s，信心 %d%%）",
                symbol, analysis["final_action"], analysis["confidence"])


def push_dual() -> None:
    """同時分析全部 ETF，以 Carousel 推播。"""
    symbols = list(ETF_CONFIG.keys())
    logger.info("[Push] 分析 %s ...", " + ".join(symbols))

    with ThreadPoolExecutor(max_workers=len(symbols)) as ex:
        analyses = list(ex.map(lambda s: Orchestrator(s).run(), symbols))

    carousel = build_etf_carousel(*analyses)

    api = _get_api()
    api.push_message(
        PushMessageRequest(
            to=_get_user_id(),
            messages=[
                FlexMessage(
                    alt_text=carousel["altText"],
                    contents=FlexContainer.from_dict(carousel["contents"]),
                )
            ],
        )
    )
    logger.info("[Push] %d 支 ETF Carousel 推播成功", len(symbols))


def push_text(message: str) -> None:
    """推播純文字訊息（用於錯誤通知）。"""
    api = _get_api()
    api.push_message(
        PushMessageRequest(
            to=_get_user_id(),
            messages=[TextMessage(text=message)],
        )
    )
