"""Performance and risk metrics."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd


def compute_performance_metrics(
    strategy_return: pd.Series,
    *,
    equity: pd.Series | None = None,
    drawdown: pd.Series | None = None,
    position: pd.Series | None = None,
    turnover: pd.Series | None = None,
    transaction_cost: pd.Series | None = None,
    periods_per_year: float = 365.0,
) -> dict[str, Any]:
    """Calculate standard performance statistics."""

    returns = pd.to_numeric(strategy_return, errors="coerce").dropna()

    if returns.empty:
        raise ValueError("strategy_return is empty.")

    if (returns <= -1.0).any():
        raise ValueError("strategy_return contains an observation <= -100%.")

    if equity is None:
        equity_series = (1.0 + returns).cumprod()
    else:
        equity_series = pd.to_numeric(equity, errors="coerce").dropna()

    if drawdown is None:
        drawdown_series = equity_series / equity_series.cummax() - 1.0
    else:
        drawdown_series = pd.to_numeric(drawdown, errors="coerce").dropna()

    observations = len(returns)
    elapsed_years = observations / periods_per_year

    final_equity = float(equity_series.iloc[-1])
    total_return = final_equity - 1.0
    cagr = final_equity ** (1.0 / elapsed_years) - 1.0

    daily_volatility = float(returns.std(ddof=1))
    annualized_volatility = daily_volatility * math.sqrt(periods_per_year)

    sharpe = (
        float(returns.mean() / daily_volatility * math.sqrt(periods_per_year))
        if daily_volatility > 0
        else float("nan")
    )

    downside = np.minimum(returns.to_numpy(dtype=float), 0.0)
    downside_deviation = float(np.sqrt(np.mean(np.square(downside))))

    sortino = (
        float(returns.mean() / downside_deviation * math.sqrt(periods_per_year))
        if downside_deviation > 0
        else float("nan")
    )

    maximum_drawdown = float(drawdown_series.min())

    calmar = float(cagr / abs(maximum_drawdown)) if maximum_drawdown < 0 else float("nan")

    result: dict[str, Any] = {
        "date_start": str(returns.index.min()),
        "date_end": str(returns.index.max()),
        "observations": observations,
        "total_return": total_return,
        "final_equity": final_equity,
        "cagr": cagr,
        "annualized_volatility": annualized_volatility,
        "sharpe": sharpe,
        "sortino": sortino,
        "maximum_drawdown": maximum_drawdown,
        "calmar": calmar,
        "hit_rate": float((returns > 0).mean()),
        "mean_daily_return": float(returns.mean()),
        "worst_daily_return": float(returns.min()),
        "best_daily_return": float(returns.max()),
    }

    if position is not None:
        clean_position = pd.to_numeric(position, errors="coerce").dropna()

        result["mean_position"] = float(clean_position.mean())
        result["minimum_position"] = float(clean_position.min())
        result["maximum_position"] = float(clean_position.max())

    if turnover is not None:
        result["turnover"] = float(pd.to_numeric(turnover, errors="coerce").fillna(0.0).sum())

    if transaction_cost is not None:
        result["transaction_cost_sum"] = float(
            pd.to_numeric(transaction_cost, errors="coerce").fillna(0.0).sum()
        )

    return result
