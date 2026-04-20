"""
主程式進入點（Push 模式，不需要 Flask / ngrok）
執行方式：
  python main.py              # 立即推播雙 ETF（0050 + 00631L）
  python main.py --etf 0050   # 只推播 0050
  python main.py --etf 00631L # 只推播 00631L
  python main.py --schedule   # 啟動排程，台灣時間 08:00 週一～週五自動推播
"""
from __future__ import annotations

import argparse
import io
import logging
import sys

import pytz
from apscheduler.schedulers.blocking import BlockingScheduler

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

TZ_TAIPEI = pytz.timezone("Asia/Taipei")


def _run_push(etf: str | None = None) -> None:
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
    from config import ETF_CONFIG
    parser.add_argument("--etf", choices=list(ETF_CONFIG.keys()),
                        help="指定單支 ETF；不填則推播全部")
    parser.add_argument("--schedule", action="store_true",
                        help="啟動排程（台灣時間週一~週五 08:00 自動推播）")
    args = parser.parse_args()

    if args.schedule:
        scheduler = BlockingScheduler(timezone=TZ_TAIPEI)

        # 週一～週五台灣時間 08:00 推播
        scheduler.add_job(
            _run_push,
            trigger="cron",
            day_of_week="mon-fri",
            hour=8,
            minute=0,
            kwargs={"etf": args.etf},
            id="etf_morning_push",
            name="ETF 早盤前分析推播",
            misfire_grace_time=300,  # 最多容忍遲發 5 分鐘
        )

        logger.info("⏰ 排程模式啟動 — 台灣時間週一至週五 08:00 自動推播")

        # 啟動時立即推播一次
        _run_push(args.etf)

        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("排程已停止")
    else:
        _run_push(args.etf)


if __name__ == "__main__":
    main()
