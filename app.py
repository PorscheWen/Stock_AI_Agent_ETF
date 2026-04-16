"""
主程式 — Flask + LINE Webhook
參考 What_To_Eat 模式：先回 200，再背景執行分析，避免 LINE webhook 逾時。
"""
from __future__ import annotations

import logging
import os
import threading

from dotenv import load_dotenv
from flask import Flask, abort, request

from linebot.v3 import WebhookParser
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, TextMessageContent

from linebot_utils.handler import handle_message_event

load_dotenv()

# ── 設定 ───────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

_parser = WebhookParser(os.environ["LINE_CHANNEL_SECRET"])


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

    # 先驗章，無效直接 400
    try:
        events = _parser.parse(body, signature)
    except InvalidSignatureError:
        logger.warning("Invalid signature received")
        abort(400)

    # 參考 What_To_Eat：立即回 200，背景處理每個事件（避免 LINE webhook 逾時）
    for event in events:
        if isinstance(event, MessageEvent) and isinstance(event.message, TextMessageContent):
            t = threading.Thread(target=_safe_handle, args=(event,), daemon=True)
            t.start()

    return "OK", 200


# ── 事件處理 ──────────────────────────────────────────────────────────────────

def _safe_handle(event: MessageEvent) -> None:
    """背景執行事件處理，例外不影響主程序。"""
    try:
        handle_message_event(event)
    except Exception as exc:
        logger.exception("處理事件時發生錯誤：%s", exc)


# ── 本機開發 ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
