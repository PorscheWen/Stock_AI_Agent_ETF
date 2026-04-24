"""
簡化版 Flask App（僅提供健康檢查）
本專案已改為 Push 模式，透過 GitHub Actions 自動推播
不再接受用戶 Webhook 指令或 Rich Menu 互動
"""
from __future__ import annotations

import logging
from dotenv import load_dotenv
from flask import Flask, jsonify

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.get("/")
def index():
    return "Stock AI Agent ETF Bot (Push Mode Only) 📈", 200


@app.get("/health")
def health():
    return {"status": "ok", "mode": "push_only"}, 200


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
