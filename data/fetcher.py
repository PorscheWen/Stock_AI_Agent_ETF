"""
台股即時行情 — 證交所 MIS（getStockInfo.jsp）
歷史 K 線仍由 data/__init__.py 的 yfinance 負責。
"""
from __future__ import annotations

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

MIS_STOCK_INFO_URL = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp"
_DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _mis_ex_ch(symbol: str) -> str:
    """組出 MIS 的 ex_ch；可在 config.ETF_CONFIG[symbol] 設定 mis_ex_ch 或 mis_market。"""
    try:
        from config import ETF_CONFIG

        info: dict[str, Any] = ETF_CONFIG.get(symbol) or {}
        custom = info.get("mis_ex_ch")
        if custom:
            return str(custom)
        market = str(info.get("mis_market", "tse"))
    except Exception:
        market = "tse"
    return f"{market}_{symbol}.tw"


def _parse_mis_row_price(row: dict[str, Any]) -> float:
    """z=最新價；無成交時 z 可能為 '-'，改試 y=昨收。"""
    z = row.get("z")
    if z is not None and str(z).strip() not in ("", "-"):
        try:
            return float(str(z).replace(",", ""))
        except ValueError:
            pass
    y = row.get("y")
    if y is not None and str(y).strip() not in ("", "-"):
        try:
            return float(str(y).replace(",", ""))
        except ValueError:
            pass
    return 0.0


def get_quote_mis(symbol: str, *, timeout: float = 15.0) -> float:
    """
    自證交所 MIS 取得價格（delay=0 為盤中即時）。
    失敗或無法解析時回傳 0.0，供上層改走其他資料源。
    """
    ex_ch = _mis_ex_ch(symbol)
    try:
        r = requests.get(
            MIS_STOCK_INFO_URL,
            params={"ex_ch": ex_ch, "json": "1", "delay": "0"},
            headers={"User-Agent": _DEFAULT_UA},
            timeout=timeout,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as exc:
        logger.warning("MIS 請求失敗 %s (%s): %s", symbol, ex_ch, exc)
        return 0.0

    if data.get("rtcode") != "0000" or data.get("rtmessage") != "OK":
        logger.warning(
            "MIS 回傳異常 %s: rtcode=%s rtmessage=%s",
            symbol,
            data.get("rtcode"),
            data.get("rtmessage"),
        )

    rows: list[dict[str, Any]] = data.get("msgArray") or []
    if not rows:
        logger.warning("MIS 無 msgArray %s (%s)", symbol, ex_ch)
        return 0.0

    price = _parse_mis_row_price(rows[0])
    if price <= 0:
        logger.warning("MIS 無法解析價格 %s (%s)", symbol, ex_ch)
    return price
