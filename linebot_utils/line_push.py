"""
LINE Push Notifier
主動推播 ETF 分析報告，不需要 Flask / ngrok / Webhook。
訂閱者清單優先從 SQLite 讀取（Render 環境），退回 CHANNEL_STOCK_USER_IDS 環境變數（GitHub Actions）。
"""
from __future__ import annotations

import json
import logging
import os
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

from agents.llm_commentary import enrich_analyses_with_llm
from agents.orchestrator import Orchestrator
from config import ETF_CONFIG
from linebot_utils.flex_card import build_etf_carousel, build_etf_flex_card
from project_env import load_project_env

load_project_env()
logger = logging.getLogger(__name__)

# LINE Flex Message Carousel 最大限制：50 KB
# 設定安全閾值為 45 KB，留 buffer
MAX_FLEX_SIZE_BYTES = 45 * 1024


def _get_api() -> MessagingApi:
    token = os.environ.get("CHANNEL_STOCK_ACCESS_TOKEN", "")
    if not token:
        raise RuntimeError("CHANNEL_STOCK_ACCESS_TOKEN 未設定")
    return MessagingApi(ApiClient(Configuration(access_token=token)))


def _get_user_ids() -> list[str]:
    """
    訂閱者清單讀取順序：
    1. SQLite data.db（Render web service 有 DB 時使用）
    2. CHANNEL_STOCK_USER_IDS 環境變數（逗號分隔，GitHub Actions fallback）
    3. CHANNEL_STOCK_USER_ID 環境變數（單人向下相容）
    """
    try:
        from data.db import get_subscribers
        ids = get_subscribers()
        if ids:
            logger.info("[Push] 從 DB 讀取訂閱者 %d 人", len(ids))
            return ids
    except Exception as exc:
        logger.warning("[Push] 無法讀取 DB，改用環境變數：%s", exc)

    ids_env = os.environ.get("CHANNEL_STOCK_USER_IDS", "")
    if ids_env:
        ids = [uid.strip() for uid in ids_env.split(",") if uid.strip()]
        if ids:
            logger.info("[Push] 從 CHANNEL_STOCK_USER_IDS 讀取 %d 人", len(ids))
            return ids

    single = os.environ.get("CHANNEL_STOCK_USER_ID", "").strip()
    if single:
        return [single]

    raise RuntimeError("找不到任何訂閱者（DB 空、CHANNEL_STOCK_USER_IDS、CHANNEL_STOCK_USER_ID 皆未設定）")


def _send(api: MessagingApi, user_ids: list[str], messages: list) -> None:
    """單人用 push_message，多人用 multicast（每批 ≤500）。"""
    if len(user_ids) == 1:
        api.push_message(PushMessageRequest(to=user_ids[0], messages=messages))
    else:
        for i in range(0, len(user_ids), 500):
            api.multicast(MulticastRequest(to=user_ids[i:i + 500], messages=messages))


def _run_and_cache(symbol: str) -> dict:
    """執行分析並存入快取，回傳 analysis dict。"""
    analysis = Orchestrator(symbol).run()
    try:
        from data.db import save_analysis
        save_analysis(symbol, analysis)
        logger.info("[Cache] %s 分析結果已存入 DB", symbol)
    except Exception as exc:
        logger.warning("[Cache] 無法儲存 %s 快取：%s", symbol, exc)
    return analysis


def _save_analyses_post_llm(analyses: list[dict]) -> None:
    """LLM 解讀寫入後再更新快取（含 llm_commentary）。"""
    try:
        from data.db import save_analysis
        for a in analyses:
            save_analysis(a["symbol"], a)
        logger.info("[Cache] 已更新 %d 筆含 LLM 解讀之快取", len(analyses))
    except Exception as exc:
        logger.warning("[Cache] LLM 後無法更新快取：%s", exc)


def _get_flex_size(payload: dict) -> int:
    """計算 Flex Message JSON 資料的大小（bytes）。"""
    return len(json.dumps(payload["contents"], ensure_ascii=False).encode("utf-8"))


def _is_flex_too_large(payload: dict) -> bool:
    """檢查 Flex Message 是否超過安全大小限制。"""
    size = _get_flex_size(payload)
    logger.debug("[Size] Flex Message 大小：%.2f KB", size / 1024)
    return size > MAX_FLEX_SIZE_BYTES


def push_single(symbol: str) -> None:
    """分析單支 ETF 並推播給所有訂閱者。"""
    logger.info("[Push] 分析 %s ...", symbol)
    analysis = _run_and_cache(symbol)
    enrich_analyses_with_llm([analysis])
    _save_analyses_post_llm([analysis])
    payload = build_etf_flex_card(analysis)

    user_ids = _get_user_ids()
    _send(_get_api(), user_ids, [
        FlexMessage(
            alt_text=payload["altText"],
            contents=FlexContainer.from_dict(payload["contents"]),
        )
    ])
    logger.info("[Push] %s 推播成功（%s，準確率 %d%%，%d 人）",
                symbol, analysis["final_action"], analysis["confidence"], len(user_ids))


def push_dual() -> None:
    """同時分析全部 ETF，以 Carousel 左右滑動卡片推播給所有訂閱者。
    若 Carousel 超過 50 KB 限制，則嘗試精簡版本或分別推播。
    """
    symbols = list(ETF_CONFIG.keys())
    logger.info("[Push] 分析 %s ...", " + ".join(symbols))

    with ThreadPoolExecutor(max_workers=len(symbols)) as ex:
        analyses = list(ex.map(_run_and_cache, symbols))

    enrich_analyses_with_llm(analyses)
    _save_analyses_post_llm(analyses)

    user_ids = _get_user_ids()
    api = _get_api()

    # 策略 1：嘗試正常版 Carousel
    carousel = build_etf_carousel(*analyses, compact=False)
    carousel_size = _get_flex_size(carousel)
    logger.info("[Push] Carousel 大小：%.2f KB（限制：%.0f KB）", 
                carousel_size / 1024, MAX_FLEX_SIZE_BYTES / 1024)

    if carousel_size <= MAX_FLEX_SIZE_BYTES:
        _send(api, user_ids, [
            FlexMessage(
                alt_text=carousel["altText"],
                contents=FlexContainer.from_dict(carousel["contents"]),
            )
        ])
        logger.info("[Push] %d 支 ETF Carousel 推播成功（%d 人）", len(symbols), len(user_ids))
        return

    # 策略 2：嘗試精簡版 Carousel
    logger.warning("[Push] Carousel 過大，嘗試精簡版本...")
    carousel_compact = build_etf_carousel(*analyses, compact=True)
    compact_size = _get_flex_size(carousel_compact)
    logger.info("[Push] 精簡版 Carousel 大小：%.2f KB", compact_size / 1024)

    if compact_size <= MAX_FLEX_SIZE_BYTES:
        _send(api, user_ids, [
            FlexMessage(
                alt_text=carousel_compact["altText"],
                contents=FlexContainer.from_dict(carousel_compact["contents"]),
            )
        ])
        logger.info("[Push] %d 支 ETF 精簡版 Carousel 推播成功（%d 人）", len(symbols), len(user_ids))
        return

    # 策略 3：分別推播
    logger.warning("[Push] 精簡版仍過大，改為分別推播 %d 支 ETF", len(symbols))
    for analysis in analyses:
        payload = build_etf_flex_card(analysis, compact=True)
        _send(api, user_ids, [
            FlexMessage(
                alt_text=payload["altText"],
                contents=FlexContainer.from_dict(payload["contents"]),
            )
        ])
        logger.info("[Push] %s 推播成功（%s，準確率 %d%%）",
                    analysis["symbol"], analysis["final_action"], analysis["confidence"])


def push_text(message: str) -> None:
    """推播純文字訊息給所有訂閱者（用於錯誤通知）。"""
    user_ids = _get_user_ids()
    _send(_get_api(), user_ids, [TextMessage(text=message)])
