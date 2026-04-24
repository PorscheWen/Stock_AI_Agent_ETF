"""
【已棄用】LINE Rich Menu 建立工具

⚠️ 注意：本專案已改為 GitHub Actions 自動推播模式，不再使用 Rich Menu
此檔案保留僅供參考，所有功能已停用

原功能說明：
呼叫一次 /setup_rich_menu 完成設定，之後所有用戶自動顯示選單。

佈局（3×2）：
  [ 0050   ]  [ 00631L ]  [ 009816  ]
  [ 00981A ]  [ 全部比較]  [ 操作說明 ]
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# 所有功能已停用，保留空實作避免 import 錯誤
# ══════════════════════════════════════════════════════════════════════════════


def build_rich_menu_image() -> bytes:
    """已棄用 - Rich Menu 功能已停用"""
    raise NotImplementedError("Rich Menu 功能已停用，本專案已改為 GitHub Actions 推播模式")


def setup_rich_menu() -> str:
    """已棄用 - Rich Menu 功能已停用"""
    raise NotImplementedError("Rich Menu 功能已停用，本專案已改為 GitHub Actions 推播模式")


def delete_all_rich_menus() -> int:
    """已棄用 - Rich Menu 功能已停用"""
    raise NotImplementedError("Rich Menu 功能已停用，本專案已改為 GitHub Actions 推播模式")
