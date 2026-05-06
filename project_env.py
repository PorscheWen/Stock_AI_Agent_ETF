"""
專案環境變數載入：可選從 Google Drive 拉取 .env 後再交給 python-dotenv。

觸發條件（擇一，設在「系統／終端」環境變數，勿寫進要下載的 .env 內）：
  GOOGLE_DRIVE_DOTENV_FILE_ID   Google 雲端硬碟檔案 ID
  GOOGLE_DRIVE_DOTENV_URL       完整分享連結（會自動解析 id）

選用：
  GOOGLE_DRIVE_DOTENV_OUTPUT    本機寫入路徑，預設專案根目錄的 .env

雲端檔需至少「知道連結的使用者」可檢視，且需安裝 gdown（見 requirements.txt）。
"""
from __future__ import annotations

import logging
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent
_GDRIVE_FETCHED = False


def _resolve_gdrive_file_id() -> str:
    fid = os.environ.get("GOOGLE_DRIVE_DOTENV_FILE_ID", "").strip()
    if fid:
        return fid
    url = os.environ.get("GOOGLE_DRIVE_DOTENV_URL", "").strip()
    if not url:
        return ""
    m = re.search(r"/d/([a-zA-Z0-9_-]+)", url)
    if m:
        return m.group(1)
    m = re.search(r"[?&]id=([a-zA-Z0-9_-]+)", url)
    if m:
        return m.group(1)
    return ""


def _maybe_download_dotenv_from_gdrive(project_root: Path) -> None:
    """若設定了 Drive 檔案 id／URL，下載為本機 .env（每個行程最多一次）。"""
    global _GDRIVE_FETCHED
    if _GDRIVE_FETCHED:
        return
    file_id = _resolve_gdrive_file_id()
    if not file_id:
        return
    _GDRIVE_FETCHED = True

    try:
        import gdown
    except ImportError:
        print(
            "[project_env] 已設定 GOOGLE_DRIVE_DOTENV_* 但未安裝 gdown，請執行：pip install gdown",
            file=sys.stderr,
        )
        return

    rel = os.environ.get("GOOGLE_DRIVE_DOTENV_OUTPUT", ".env").strip() or ".env"
    dest = project_root / rel
    url = f"https://drive.google.com/uc?id={file_id}"

    try:
        logger.info("從 Google Drive 下載環境檔 → %s", dest)
    except Exception:
        print(f"[project_env] 從 Google Drive 下載環境檔 → {dest}", file=sys.stderr)

    try:
        gdown.download(url, str(dest), quiet=False)
    except Exception as exc:
        try:
            logger.warning("Google Drive 下載失敗：%s", exc)
        except Exception:
            print(f"[project_env] Google Drive 下載失敗：{exc}", file=sys.stderr)
        return

    if not dest.is_file() or dest.stat().st_size == 0:
        try:
            logger.warning("Google Drive 下載後檔案不存在或為空：%s", dest)
        except Exception:
            print(f"[project_env] 下載後檔案不存在或為空：{dest}", file=sys.stderr)


def load_project_env() -> None:
    """
    1. 若設定了 GOOGLE_DRIVE_DOTENV_FILE_ID 或 GOOGLE_DRIVE_DOTENV_URL，先下載 .env
    2. 自專案根目錄載入 .env（與本檔案同層）
    """
    root = _PROJECT_ROOT
    _maybe_download_dotenv_from_gdrive(root)
    load_dotenv(root / ".env")
