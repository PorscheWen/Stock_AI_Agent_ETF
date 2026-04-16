"""
Agent 基底類別
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import pandas as pd


class BaseAgent(ABC):
    """所有分析 Agent 的抽象基底類別。"""

    def __init__(self, name: str, symbol: str):
        self.name = name          # Agent 顯示名稱
        self.symbol = symbol      # ETF 代號，如 "0050"

    @abstractmethod
    def analyze(self, df: pd.DataFrame) -> dict[str, Any]:
        """
        分析資料並回傳標準化結果字典。

        Returns
        -------
        dict 包含以下鍵值：
          - agent (str)         : Agent 名稱
          - symbol (str)        : ETF 代號
          - score (int)         : 正分看多，負分看空
          - action (str)        : "買入" | "觀望" | "賣出"
          - signals (list[dict]): 各指標訊號列表
          - details (dict)      : 額外指標數值
        """

    def _safe_float(self, value: Any) -> float:
        """安全轉換為 float，避免 NaN 導致 JSON 序列化失敗。"""
        try:
            v = float(value)
            return round(v, 4) if v == v else 0.0  # NaN check
        except (TypeError, ValueError):
            return 0.0
