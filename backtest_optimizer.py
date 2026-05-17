"""
Backtest existing ETF agent rules against defensive variants.

The script reuses the production Agents but avoids LINE/current-price calls.
Signals are generated after each close and applied to the next trading day.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from agents.risk_agent import RiskAgent
from agents.technical_agent import TechnicalAgent
from agents.trend_agent import TrendAgent
from agents.volume_agent import VolumeAgent
from config import AGENT_MAX_SCORES, ETF_CONFIG, MAX_WEIGHTED_SCORE
from data import fetch_etf_data


@dataclass(frozen=True)
class StrategyProfile:
    name: str
    buy_threshold: float
    strong_buy_threshold: float
    weights: tuple[float, float, float, float]
    require_ma60: bool = False
    require_ma120: bool = False
    crash_guard: bool = False
    max_atr_pct: float | None = None
    stop_loss_pct: float | None = None
    take_profit_pct: float | None = None


PROFILES = [
    StrategyProfile(
        name="current_rules",
        buy_threshold=1.2,
        strong_buy_threshold=2.5,
        weights=(1.0, 1.0, 1.0, 0.5),
    ),
    StrategyProfile(
        name="defensive_ma60",
        buy_threshold=1.4,
        strong_buy_threshold=2.5,
        weights=(1.0, 0.8, 1.0, 1.0),
        require_ma60=True,
        crash_guard=True,
    ),
    StrategyProfile(
        name="defensive_ma120",
        buy_threshold=1.4,
        strong_buy_threshold=2.6,
        weights=(1.0, 0.8, 1.0, 1.2),
        require_ma60=True,
        require_ma120=True,
        crash_guard=True,
        max_atr_pct=3.0,
    ),
    StrategyProfile(
        name="defensive_stop",
        buy_threshold=1.4,
        strong_buy_threshold=2.6,
        weights=(1.0, 0.8, 1.0, 1.2),
        require_ma60=True,
        crash_guard=True,
        max_atr_pct=3.0,
        stop_loss_pct=7.0,
        take_profit_pct=18.0,
    ),
]


def _agent_score(df: pd.DataFrame, symbol: str, profile: StrategyProfile) -> dict[str, Any]:
    agents = [
        TechnicalAgent(symbol),
        VolumeAgent(symbol),
        TrendAgent(symbol),
        RiskAgent(symbol),
    ]
    results = [agent.analyze(df) for agent in agents]
    total_score = sum(
        (result["score"] / max_score) * weight
        for result, max_score, weight in zip(results, AGENT_MAX_SCORES, profile.weights)
    )
    total_score = max(-MAX_WEIGHTED_SCORE, min(MAX_WEIGHTED_SCORE, total_score))
    risk_details = next(
        (r["details"] for r in results if "atr_pct" in r.get("details", {})),
        {},
    )
    return {
        "score": float(total_score),
        "atr_pct": float(risk_details.get("atr_pct", 0.0)),
    }


def _crash_guard_triggered(history: pd.DataFrame, atr_pct: float, profile: StrategyProfile) -> bool:
    close = history["Close"]
    latest = float(close.iloc[-1])
    ret_20d = latest / float(close.iloc[-21]) - 1 if len(close) >= 21 else 0.0
    ret_5d = latest / float(close.iloc[-6]) - 1 if len(close) >= 6 else 0.0
    high_20d = float(close.tail(20).max())
    drawdown_20d = latest / high_20d - 1 if high_20d > 0 else 0.0

    if profile.max_atr_pct is not None and atr_pct > profile.max_atr_pct:
        return True
    if not profile.crash_guard:
        return False

    return ret_20d <= -0.05 or ret_5d <= -0.035 or drawdown_20d <= -0.08


def _desired_position(history: pd.DataFrame, symbol: str, profile: StrategyProfile) -> tuple[float, float]:
    score_info = _agent_score(history, symbol, profile)
    close = history["Close"]
    latest = float(close.iloc[-1])

    if profile.require_ma60:
        ma60 = float(close.rolling(60).mean().iloc[-1])
        if latest < ma60:
            return 0.0, score_info["score"]

    if profile.require_ma120:
        ma120 = float(close.rolling(120).mean().iloc[-1])
        if latest < ma120:
            return 0.0, score_info["score"]

    if _crash_guard_triggered(history, score_info["atr_pct"], profile):
        return 0.0, score_info["score"]

    if score_info["score"] >= profile.strong_buy_threshold:
        return 1.0, score_info["score"]
    if score_info["score"] >= profile.buy_threshold:
        return 0.7, score_info["score"]
    return 0.0, score_info["score"]


def _apply_exit_rules(
    position: float,
    entry_price: float | None,
    latest_close: float,
    profile: StrategyProfile,
) -> float:
    if position <= 0 or entry_price is None or entry_price <= 0:
        return position

    trade_ret = latest_close / entry_price - 1
    if profile.stop_loss_pct is not None and trade_ret <= -(profile.stop_loss_pct / 100):
        return 0.0
    if profile.take_profit_pct is not None and trade_ret >= profile.take_profit_pct / 100:
        return 0.0
    return position


def backtest_symbol(
    symbol: str,
    profile: StrategyProfile,
    *,
    period: str,
    warmup_days: int,
    trading_cost: float,
) -> dict[str, Any]:
    df = fetch_etf_data(symbol, period=period)
    df = df.dropna(subset=["Open", "High", "Low", "Close", "Volume"]).copy()
    if len(df) <= warmup_days + 30:
        raise ValueError(f"{symbol} usable data too short: {len(df)} rows")

    positions: list[float] = []
    scores: list[float] = []
    dates = df.index[warmup_days:-1]
    position = 0.0
    entry_price: float | None = None

    for idx in range(warmup_days, len(df) - 1):
        history = df.iloc[: idx + 1]
        latest_close = float(history["Close"].iloc[-1])
        desired_position, score = _desired_position(history, symbol, profile)
        desired_position = _apply_exit_rules(desired_position, entry_price, latest_close, profile)

        if desired_position > 0 and position <= 0:
            entry_price = latest_close
        elif desired_position <= 0:
            entry_price = None

        positions.append(desired_position)
        scores.append(score)
        position = desired_position

    result = pd.DataFrame(index=dates)
    result["position"] = positions
    result["score"] = scores
    result["asset_return"] = df["Close"].pct_change().shift(-1).reindex(dates).fillna(0.0)
    result["turnover"] = result["position"].diff().abs().fillna(result["position"].abs())
    result["strategy_return"] = result["position"] * result["asset_return"] - result["turnover"] * trading_cost

    return _metrics(symbol, profile.name, result)


def _max_drawdown(equity: pd.Series) -> float:
    peak = equity.cummax()
    drawdown = equity / peak - 1
    return float(drawdown.min())


def _metrics(symbol: str, profile_name: str, result: pd.DataFrame) -> dict[str, Any]:
    equity = (1 + result["strategy_return"]).cumprod()
    buy_hold = (1 + result["asset_return"]).cumprod()
    years = max(len(result) / 252, 0.01)
    downside_days = result["asset_return"] < 0
    crash_days = result["asset_return"] <= -0.025

    def annualized_return(series: pd.Series) -> float:
        return float(series.iloc[-1] ** (1 / years) - 1)

    strategy_vol = float(result["strategy_return"].std() * np.sqrt(252))
    strategy_sharpe = (
        float(result["strategy_return"].mean() / result["strategy_return"].std() * np.sqrt(252))
        if result["strategy_return"].std() > 0
        else 0.0
    )
    downside_capture = (
        float(result.loc[downside_days, "strategy_return"].sum() / result.loc[downside_days, "asset_return"].sum())
        if downside_days.any() and result.loc[downside_days, "asset_return"].sum() != 0
        else 0.0
    )

    return {
        "symbol": symbol,
        "profile": profile_name,
        "days": int(len(result)),
        "total_return_pct": round((float(equity.iloc[-1]) - 1) * 100, 2),
        "buy_hold_return_pct": round((float(buy_hold.iloc[-1]) - 1) * 100, 2),
        "annual_return_pct": round(annualized_return(equity) * 100, 2),
        "max_drawdown_pct": round(_max_drawdown(equity) * 100, 2),
        "buy_hold_max_drawdown_pct": round(_max_drawdown(buy_hold) * 100, 2),
        "volatility_pct": round(strategy_vol * 100, 2),
        "sharpe": round(strategy_sharpe, 2),
        "exposure_pct": round(float(result["position"].mean()) * 100, 2),
        "trades": int((result["turnover"] > 0).sum()),
        "downside_capture_pct": round(downside_capture * 100, 2),
        "crash_days": int(crash_days.sum()),
        "crash_day_return_pct": round(float(result.loc[crash_days, "strategy_return"].sum()) * 100, 2),
        "buy_hold_crash_day_return_pct": round(float(result.loc[crash_days, "asset_return"].sum()) * 100, 2),
    }


def run_backtests(
    symbols: list[str],
    profiles: list[StrategyProfile],
    *,
    period: str,
    warmup_days: int,
    trading_cost: float,
) -> dict[str, Any]:
    rows = []
    failures = []

    for symbol in symbols:
        for profile in profiles:
            try:
                rows.append(
                    backtest_symbol(
                        symbol,
                        profile,
                        period=period,
                        warmup_days=warmup_days,
                        trading_cost=trading_cost,
                    )
                )
            except Exception as exc:
                failures.append({"symbol": symbol, "profile": profile.name, "error": str(exc)})

    by_symbol: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_symbol.setdefault(row["symbol"], []).append(row)

    best_defensive = {}
    for symbol, symbol_rows in by_symbol.items():
        defensive_rows = [r for r in symbol_rows if r["profile"] != "current_rules"]
        best_defensive[symbol] = max(defensive_rows, key=lambda r: r["max_drawdown_pct"]) if defensive_rows else None

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "period": period,
        "warmup_days": warmup_days,
        "trading_cost": trading_cost,
        "profiles": [asdict(profile) for profile in profiles],
        "results": rows,
        "best_defensive_by_symbol": best_defensive,
        "failures": failures,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest ETF agent rules and defensive variants.")
    parser.add_argument("--symbols", nargs="+", default=list(ETF_CONFIG.keys()), help="ETF symbols to test.")
    parser.add_argument("--period", default="5y", help="Yahoo Finance period, for example 2y, 5y, max.")
    parser.add_argument("--warmup-days", type=int, default=130, help="Rows used before first signal.")
    parser.add_argument("--trading-cost", type=float, default=0.001, help="Cost per 100% turnover.")
    parser.add_argument("--output", default="backtest_results.json", help="JSON output path.")
    args = parser.parse_args()

    summary = run_backtests(
        args.symbols,
        PROFILES,
        period=args.period,
        warmup_days=args.warmup_days,
        trading_cost=args.trading_cost,
    )

    output_path = Path(args.output)
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Saved {output_path}")
    for row in summary["results"]:
        print(
            f"{row['symbol']:>6} {row['profile']:<16} "
            f"return={row['total_return_pct']:>7.2f}% "
            f"mdd={row['max_drawdown_pct']:>7.2f}% "
            f"bh_mdd={row['buy_hold_max_drawdown_pct']:>7.2f}% "
            f"exposure={row['exposure_pct']:>6.2f}% "
            f"trades={row['trades']:>3}"
        )

    if summary["failures"]:
        print("Failures:")
        for failure in summary["failures"]:
            print(f"- {failure['symbol']} {failure['profile']}: {failure['error']}")


if __name__ == "__main__":
    main()
