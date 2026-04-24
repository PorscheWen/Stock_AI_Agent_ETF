"""
【已棄用】LINE Webhook 事件處理器

⚠️ 注意：本專案已改為 GitHub Actions 自動推播模式
不再接受用戶 Webhook 指令或互動，所有處理函數已停用

原功能包括：
- Follow/Unfollow 事件處理
- 訊息事件處理
- ETF 查詢與刷新
- 訂閱管理
"""
from __future__ import annotations

import logging
from linebot.v3.webhooks import (
    FollowEvent,
    MessageEvent,
    UnfollowEvent,
)

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# 所有處理函數已停用，保留空實作避免 import 錯誤
# ══════════════════════════════════════════════════════════════════════════════


def handle_follow_event(event: FollowEvent) -> None:
    """已棄用 - Webhook 處理已停用"""
    raise NotImplementedError("Webhook 處理已停用，本專案已改為 GitHub Actions 推播模式")


def handle_unfollow_event(event: UnfollowEvent) -> None:
    """已棄用 - Webhook 處理已停用"""
    raise NotImplementedError("Webhook 處理已停用，本專案已改為 GitHub Actions 推播模式")


def handle_message_event(event: MessageEvent) -> None:
    """已棄用 - Webhook 處理已停用"""
    raise NotImplementedError("Webhook 處理已停用，本專案已改為 GitHub Actions 推播模式")
