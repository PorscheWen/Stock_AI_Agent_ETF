"""
SQLite 訂閱者管理（仿 What_To_Eat db.js 模式）
資料庫路徑優先讀 DB_PATH 環境變數，預設同專案根目錄的 data.db。
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

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


# 啟動時自動建表
init_db()
