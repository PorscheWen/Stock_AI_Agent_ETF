"""
SQLite 資料管理（仿 What_To_Eat db.js 模式）
- subscribers：訂閱者清單
- analysis_cache：各 ETF 最新分析結果快取
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

_DB_PATH = os.environ.get("DB_PATH") or str(Path(__file__).parent.parent / "data.db")


def _conn() -> sqlite3.Connection:
    con = sqlite3.connect(_DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def init_db() -> None:
    with _conn() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS subscribers (
                user_id   TEXT PRIMARY KEY,
                joined_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS analysis_cache (
                symbol     TEXT PRIMARY KEY,
                result     TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)


# ── 訂閱者 ────────────────────────────────────────────────────────────────────

def add_subscriber(user_id: str) -> None:
    with _conn() as con:
        con.execute(
            "INSERT OR IGNORE INTO subscribers (user_id) VALUES (?)",
            (user_id,),
        )


def remove_subscriber(user_id: str) -> None:
    with _conn() as con:
        con.execute("DELETE FROM subscribers WHERE user_id = ?", (user_id,))


def get_subscribers() -> list[str]:
    with _conn() as con:
        rows = con.execute("SELECT user_id FROM subscribers").fetchall()
    return [r["user_id"] for r in rows]


# ── 分析快取 ──────────────────────────────────────────────────────────────────

def save_analysis(symbol: str, analysis: dict[str, Any]) -> None:
    """儲存（或覆寫）某支 ETF 的分析結果。"""
    with _conn() as con:
        con.execute(
            """
            INSERT INTO analysis_cache (symbol, result, updated_at)
            VALUES (?, ?, datetime('now','localtime'))
            ON CONFLICT(symbol) DO UPDATE SET
                result     = excluded.result,
                updated_at = excluded.updated_at
            """,
            (symbol, json.dumps(analysis, ensure_ascii=False)),
        )


def get_analysis(symbol: str) -> tuple[dict[str, Any], str] | None:
    """
    取得某支 ETF 的快取分析結果。
    回傳 (analysis_dict, updated_at_str)，若無快取則回傳 None。
    """
    with _conn() as con:
        row = con.execute(
            "SELECT result, updated_at FROM analysis_cache WHERE symbol = ?",
            (symbol,),
        ).fetchone()
    if row is None:
        return None
    return json.loads(row["result"]), row["updated_at"]


# 啟動時自動建表
init_db()
