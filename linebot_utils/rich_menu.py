"""
LINE Rich Menu 建立工具
呼叫一次 /setup_rich_menu 完成設定，之後所有用戶自動顯示選單。

佈局（3×2）：
  [ 0050   ]  [ 00631L ]  [ 009816  ]
  [ 00981A ]  [ 全部比較]  [ 操作說明 ]
"""
from __future__ import annotations

import io
import logging
import os

import requests
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessageAction,
    MessagingApi,
    RichMenuArea,
    RichMenuBounds,
    RichMenuRequest,
    RichMenuSize,
)

logger = logging.getLogger(__name__)

_W, _H = 2500, 843
_COLS, _ROWS = 3, 2

_BUTTONS = [
    ("0050",    "元大台灣50",  "#1565C0", "0050"),
    ("00631L",  "台灣50正2",  "#6A1B9A", "00631L"),
    ("009816",  "凱基TOP50",  "#00695C", "009816"),
    ("00981A",  "統一成長",   "#4527A0", "00981A"),
    ("全部比較", "4支ETF總覽", "#37474F", "分析"),
    ("操作說明", "指令 & 訂閱", "#BF360C", "說明"),
]


def _get_font(size: int):
    from PIL import ImageFont
    for path in [
        "C:/Windows/Fonts/msjhbd.ttc",        # Windows 微軟正黑粗體
        "C:/Windows/Fonts/msjh.ttc",           # Windows 微軟正黑
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKtc-Bold.otf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def build_rich_menu_image() -> bytes:
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (_W, _H), "#EEEEEE")
    draw = ImageDraw.Draw(img)

    cell_w = _W // _COLS
    cell_h = _H // _ROWS
    pad = 10

    font_main = _get_font(90)
    font_sub  = _get_font(46)

    for i, (label, sub, color, _) in enumerate(_BUTTONS):
        row, col = divmod(i, _COLS)
        x0 = col * cell_w + pad
        y0 = row * cell_h + pad
        x1 = (col + 1) * cell_w - pad
        y1 = (row + 1) * cell_h - pad
        cx = (x0 + x1) // 2
        cy = (y0 + y1) // 2

        # 背景
        draw.rounded_rectangle([x0, y0, x1, y1], radius=24, fill=color)

        # 主標籤
        draw.text((cx, cy - 28), label, fill="#FFFFFF", font=font_main, anchor="mm")
        # 副標籤
        draw.text((cx, cy + 62), sub,   fill="#FFFFFFBB", font=font_sub,  anchor="mm")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def setup_rich_menu() -> str:
    """建立 Rich Menu、上傳圖片、設為預設，回傳 rich_menu_id。"""
    token = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
    config = Configuration(access_token=token)

    cell_w = _W // _COLS
    cell_h = _H // _ROWS

    areas = []
    for i, (label, _, _, msg) in enumerate(_BUTTONS):
        row, col = divmod(i, _COLS)
        areas.append(RichMenuArea(
            bounds=RichMenuBounds(
                x=col * cell_w,
                y=row * cell_h,
                width=cell_w,
                height=cell_h,
            ),
            action=MessageAction(label=label, text=msg),
        ))

    with ApiClient(config) as api_client:
        api = MessagingApi(api_client)

        rich_menu_id = api.create_rich_menu(
            RichMenuRequest(
                size=RichMenuSize(width=_W, height=_H),
                selected=True,
                name="ETF AI 分析選單",
                chat_bar_text="📊 ETF 查詢",
                areas=areas,
            )
        ).rich_menu_id

    # 圖片上傳使用 requests（SDK blob API 相容性較差）
    image_bytes = build_rich_menu_image()
    resp = requests.post(
        f"https://api-data.line.me/v2/bot/richmenu/{rich_menu_id}/content",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "image/png",
        },
        data=image_bytes,
        timeout=30,
    )
    resp.raise_for_status()

    # 設為預設選單
    with ApiClient(config) as api_client:
        api = MessagingApi(api_client)
        api.set_default_rich_menu(rich_menu_id)

    logger.info("[RichMenu] 設定完成：%s", rich_menu_id)
    return rich_menu_id


def delete_all_rich_menus() -> int:
    """刪除帳號下所有 Rich Menu（重設用）。"""
    token = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
    config = Configuration(access_token=token)
    with ApiClient(config) as api_client:
        api = MessagingApi(api_client)
        menus = api.get_rich_menu_list().richmenus or []
        for m in menus:
            api.delete_rich_menu(m.rich_menu_id)
    logger.info("[RichMenu] 已刪除 %d 個選單", len(menus))
    return len(menus)
