"""
主程式進入點（Push 模式，不需要 Flask / ngrok）
執行方式：
  python main.py              # 立即推播雙 ETF（0050 + 00631L）
  python main.py --etf 0050   # 只推播 0050
  python main.py --etf 00631L # 只推播 00631L
  python main.py --schedule   # 啟動每日 08:30 排程，自動雙 ETF 推播
"""
from __future__ import annotations

import argparse
import io
import logging
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _run_push(etf: str | None) -> None:
    from linebot_utils.line_push import push_dual, push_single, push_text
    try:
        if etf:
            push_single(etf)
        else:
            push_dual()
    except Exception as exc:
        logger.exception("推播失敗：%s", exc)
        try:
            push_text(f"⚠️ ETF AI 分析推播失敗\n錯誤：{exc}")
        except Exception:
            pass


def main() -> None:
    parser = argparse.ArgumentParser(description="ETF AI Agent — LINE Push 模式")
    parser.add_argument("--etf", choices=["0050", "00631L"],
                        help="指定單支 ETF；不填則推播兩支")
    parser.add_argument("--schedule", action="store_true",
                        help="啟動每日 08:30 排程")
    args = parser.parse_args()

    if args.schedule:
        import schedule
        import time

        logger.info("⏰ 排程模式啟動，每日 08:30 自動推播")
        # 啟動時先執行一次
        _run_push(args.etf)

        schedule.every().day.at("08:30").do(_run_push, etf=args.etf)
        while True:
            schedule.run_pending()
            time.sleep(30)
    else:
        _run_push(args.etf)


if __name__ == "__main__":
    main()
