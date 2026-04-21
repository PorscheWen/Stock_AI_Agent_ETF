"""
資料管理 — PostgreSQL（Render，DATABASE_URL）或 SQLite（本機 fallback）
"""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

_DATABASE_URL = os.environ.get("DATABASE_URL", "")
_DB_PATH = os.environ.get("DB_PATH") or str(Path(__file__).parent.parent / "data.db")
_USE_PG = bool(_DATABASE_URL)
_PH = "%s" if _USE_PG else "?"


@contextmanager
def _conn():
    if _USE_PG:
        import psycopg2
        import psycopg2.extras
        con = psycopg2.connect(_DATABASE_URL)
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()
    else:
        con = sqlite3.connect(_DB_PATH, check_same_thread=False)
        con.row_factory = sqlite3.Row
        try:
            yield con
            con.commit()
        finally:
            con.close()


def _exec(con, sql: str, params=()):
    if _USE_PG:
        import psycopg2.extras
        cur = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params)
        return cur
    return con.execute(sql, params)


def init_db() -> None:
    _joined_default = "NOW()" if _USE_PG else "datetime('now','localtime')"
    with _conn() as con:
        _exec(con, f"""
            CREATE TABLE IF NOT EXISTS subscribers (
                user_id   TEXT PRIMARY KEY,
                joined_at TEXT NOT NULL DEFAULT ({_joined_default})
            )
        """)
        _exec(con, """
            CREATE TABLE IF NOT EXISTS analysis_cache (
                symbol     TEXT PRIMARY KEY,
                result     TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)


# ── 訂閱者 ────────────────────────────────────────────────────────────────────

def add_subscriber(user_id: str) -> None:
    with _conn() as con:
        _exec(con,
            f"INSERT INTO subscribers (user_id) VALUES ({_PH}) ON CONFLICT (user_id) DO NOTHING",
            (user_id,),
        )


def remove_subscriber(user_id: str) -> None:
    with _conn() as con:
        _exec(con, f"DELETE FROM subscribers WHERE user_id = {_PH}", (user_id,))


def get_subscribers() -> list[str]:
    with _conn() as con:
        rows = _exec(con, "SELECT user_id FROM subscribers").fetchall()
    return [r["user_id"] for r in rows]


# ── 分析快取 ──────────────────────────────────────────────────────────────────

def save_analysis(symbol: str, analysis: dict[str, Any]) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as con:
        _exec(con,
            f"""
            INSERT INTO analysis_cache (symbol, result, updated_at)
            VALUES ({_PH}, {_PH}, {_PH})
            ON CONFLICT (symbol) DO UPDATE SET
                result     = EXCLUDED.result,
                updated_at = EXCLUDED.updated_at
            """,
            (symbol, json.dumps(analysis, ensure_ascii=False), now),
        )


def get_analysis(symbol: str) -> tuple[dict[str, Any], str] | None:
    with _conn() as con:
        row = _exec(con,
            f"SELECT result, updated_at FROM analysis_cache WHERE symbol = {_PH}",
            (symbol,),
        ).fetchone()
    if row is None:
        return None
    return json.loads(row["result"]), row["updated_at"]


def clear_all_cache() -> None:
    """清除所有 ETF 分析快取（測試用）"""
    with _conn() as con:
        _exec(con, "DELETE FROM analysis_cache")
        con.commit()


# 啟動時自動建表
init_db()
