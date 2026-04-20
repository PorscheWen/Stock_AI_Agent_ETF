"""
主程式 — Flask + LINE Webhook
參考 What_To_Eat 模式：先回 200，再背景執行，避免 LINE webhook 逾時。
支援 follow/unfollow 事件自動訂閱，及 /push 端點供 Render cron job 觸發。
"""
from __future__ import annotations

import logging
import os
import threading

from dotenv import load_dotenv
from flask import Flask, abort, jsonify, request

from linebot.v3 import WebhookParser
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import (
    FollowEvent,
    MessageEvent,
    TextMessageContent,
    UnfollowEvent,
)

from linebot_utils.handler import (
    handle_follow_event,
    handle_message_event,
    handle_unfollow_event,
)

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

_parser: WebhookParser | None = None


def _get_parser() -> WebhookParser:
    global _parser
    if _parser is None:
        secret = os.environ.get("LINE_CHANNEL_SECRET", "")
        if not secret:
            raise RuntimeError("LINE_CHANNEL_SECRET 環境變數未設定")
        _parser = WebhookParser(secret)
    return _parser


# ── 路由 ───────────────────────────────────────────────────────────────────────

@app.get("/")
def index():
    return "Stock AI Agent ETF Bot is running! 📈", 200


@app.get("/health")
def health():
    return {"status": "ok"}, 200


@app.post("/webhook")
def webhook():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    try:
        events = _get_parser().parse(body, signature)
    except InvalidSignatureError:
        logger.warning("Invalid signature received")
        abort(400)

    for event in events:
        if isinstance(event, FollowEvent):
            threading.Thread(target=_safe_run, args=(handle_follow_event, event), daemon=True).start()
        elif isinstance(event, UnfollowEvent):
            threading.Thread(target=_safe_run, args=(handle_unfollow_event, event), daemon=True).start()
        elif isinstance(event, MessageEvent) and isinstance(event.message, TextMessageContent):
            threading.Thread(target=_safe_run, args=(handle_message_event, event), daemon=True).start()

    return "OK", 200


@app.post("/push")
def push_trigger():
    """
    Render cron job 觸發端點。
    需帶 Authorization: Bearer <PUSH_SECRET> header。
    """
    secret = os.environ.get("PUSH_SECRET", "")
    if secret:
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {secret}":
            abort(401)

    def _do_push():
        from linebot_utils.line_push import push_dual, push_text
        try:
            push_dual()
        except Exception as exc:
            logger.exception("排程推播失敗：%s", exc)
            try:
                push_text(f"⚠️ ETF AI 推播失敗\n錯誤：{exc}")
            except Exception:
                pass

    threading.Thread(target=_do_push, daemon=True).start()
    return jsonify({"status": "push triggered"}), 202


# ── 工具函式 ──────────────────────────────────────────────────────────────────

def _safe_run(fn, event) -> None:
    try:
        fn(event)
    except Exception as exc:
        logger.exception("處理事件時發生錯誤：%s", exc)


# ── 本機開發 ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
