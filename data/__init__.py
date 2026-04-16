"""
資料抓取模組 — 從 Yahoo Finance 取得台灣 ETF 歷史資料
"""
from __future__ import annotations

import time
from datetime import datetime
from functools import lru_cache
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf


def fetch_etf_data(symbol: str, period: str = "1y") -> pd.DataFrame:
    """
    從 Yahoo Finance 取得 ETF OHLCV 資料。
    Taiwan 股票使用 .TW 後綴（若尚未加入）。
    """
    ticker_symbol = symbol if symbol.endswith(".TW") else f"{symbol}.TW"
    try:
        df = yf.download(ticker_symbol, period=period, progress=False, auto_adjust=True)
        if df.empty:
            raise ValueError(f"無法取得 {symbol} 的資料，回傳空 DataFrame")
        # 攤平多層欄位（yfinance 有時會回傳 MultiIndex）
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        # 移除重複欄位（MultiIndex 展平後可能出現）
        df = df.loc[:, ~df.columns.duplicated()]
        df.dropna(subset=["Close", "Volume"], inplace=True)
        return df
    except Exception as exc:
        raise RuntimeError(f"取得 {symbol} 資料失敗：{exc}") from exc


def get_current_price(symbol: str) -> float:
    """取得最新成交價"""
    ticker_symbol = symbol if symbol.endswith(".TW") else f"{symbol}.TW"
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.fast_info
        price = getattr(info, "last_price", None)
        if price is None or np.isnan(price):
            # fallback: 使用 history
            hist = ticker.history(period="2d")
            if not hist.empty:
                price = float(hist["Close"].iloc[-1])
        return float(price)
    except Exception:
        return 0.0


def get_etf_summary(symbol: str) -> dict:
    """取得 ETF 基本摘要資訊"""
    ticker_symbol = symbol if symbol.endswith(".TW") else f"{symbol}.TW"
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        return {
            "market_cap": info.get("marketCap"),
            "total_assets": info.get("totalAssets"),
            "nav": info.get("navPrice"),
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
        }
    except Exception:
        return {}
