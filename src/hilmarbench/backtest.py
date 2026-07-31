"""Daily exposure backtesting with explicit execution lags and costs."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from hilmarbench.execution import (
    ExecutionCostAssumptions,
    estimate_execution_cost,
)


@dataclass(frozen=True)
class BacktestConfig:
    """Configuration for a daily allocation backtest."""

    cost_bps: float = 25.0
    initial_equity: float = 1.0
    initial_position: float = 0.0
    minimum_position: float = 0.0
    maximum_position: float = 1.0

    def __post_init__(self) -> None:
        if self.cost_bps < 0:
            raise ValueError("cost_bps must be non-negative.")

        if self.initial_equity <= 0:
            raise ValueError("initial_equity must be positive.")

        if self.minimum_position > self.maximum_position:
            raise ValueError("Invalid position bounds.")

        if not self.minimum_position <= self.initial_position <= self.maximum_position:
            raise ValueError("initial_position lies outside the position bounds.")


@dataclass(frozen=True)
class ExecutionModelInputs:
    """Inputs required by the optional execution-aware backtest mode.

    The portfolio notional determines the hypothetical order notional:

        absolute position change x portfolio notional

    The execution model replaces ``BacktestConfig.cost_bps``. The latter must
    therefore be set to zero when this object is supplied.
    """

    assumptions: ExecutionCostAssumptions
    portfolio_notional: float | pd.Series
    daily_volume_notional: float | pd.Series
    daily_volatility: float | pd.Series


def apply_execution_lag(
    decision_exposure: pd.Series,
    *,
    lag_days: int = 1,
    initial_position: float = 0.0,
) -> pd.Series:
    """Transform decisions into applied positions."""

    if lag_days < 0:
        raise ValueError("lag_days must be non-negative.")

    decision = pd.to_numeric(decision_exposure, errors="coerce").astype(float)

    applied = decision.shift(lag_days)
    applied = applied.ffill().fillna(float(initial_position))
    applied.name = "position"

    return applied


def _align_execution_input(
    value: float | pd.Series,
    *,
    index: pd.Index,
    name: str,
    strictly_positive: bool,
) -> pd.Series:
    if isinstance(value, pd.Series):
        series = pd.to_numeric(
            value,
            errors="coerce",
        ).reindex(index)
    else:
        series = pd.Series(
            float(value),
            index=index,
            dtype=float,
        )

    numeric = series.astype(float)

    if numeric.isna().any():
        raise ValueError(f"{name} contains missing or unaligned values.")

    values = numeric.to_numpy(dtype=float)

    if not np.isfinite(values).all():
        raise ValueError(f"{name} must contain only finite values.")

    if strictly_positive:
        if (numeric <= 0.0).any():
            raise ValueError(f"{name} must contain only positive values.")
    elif (numeric < 0.0).any():
        raise ValueError(f"{name} must contain only non-negative values.")

    numeric.name = name
    return numeric


def _apply_execution_model(
    frame: pd.DataFrame,
    *,
    model: ExecutionModelInputs,
) -> None:
    portfolio_notional = _align_execution_input(
        model.portfolio_notional,
        index=frame.index,
        name="portfolio_notional",
        strictly_positive=True,
    )
    daily_volume_notional = _align_execution_input(
        model.daily_volume_notional,
        index=frame.index,
        name="daily_volume_notional",
        strictly_positive=True,
    )
    daily_volatility = _align_execution_input(
        model.daily_volatility,
        index=frame.index,
        name="daily_volatility",
        strictly_positive=False,
    )

    order_notional = (frame["turnover"] * portfolio_notional).rename("order_notional")

    estimates = [
        estimate_execution_cost(
            order_notional=float(order),
            daily_volume_notional=float(volume),
            daily_volatility=float(volatility),
            assumptions=model.assumptions,
        )
        for order, volume, volatility in zip(
            order_notional,
            daily_volume_notional,
            daily_volatility,
            strict=True,
        )
    ]

    frame["portfolio_notional"] = portfolio_notional
    frame["daily_volume_notional"] = daily_volume_notional
    frame["daily_volatility"] = daily_volatility
    frame["order_notional"] = order_notional

    frame["participation_rate"] = [estimate.participation_rate for estimate in estimates]
    frame["fee_bps"] = [estimate.fee_bps for estimate in estimates]
    frame["spread_bps"] = [estimate.spread_bps for estimate in estimates]
    frame["slippage_bps"] = [estimate.slippage_bps for estimate in estimates]
    frame["market_impact_bps"] = [estimate.market_impact_bps for estimate in estimates]
    frame["execution_cost_bps"] = [estimate.total_cost_bps for estimate in estimates]
    frame["execution_cost_notional"] = [estimate.total_cost_notional for estimate in estimates]
    frame["within_participation_limit"] = [
        estimate.within_participation_limit for estimate in estimates
    ]

    frame["transaction_cost"] = frame["execution_cost_notional"] / frame["portfolio_notional"]


def run_backtest(
    asset_return: pd.Series,
    decision_exposure: pd.Series,
    *,
    execution_lag_days: int = 1,
    config: BacktestConfig | None = None,
    execution_model: ExecutionModelInputs | None = None,
) -> pd.DataFrame:
    """Run a daily backtest from returns and decision exposures.

    Without ``execution_model``, transaction costs follow the historical
    fixed-basis-point convention.

    With ``execution_model``, fees, spread, slippage and market impact are
    calculated for each hypothetical order. In that mode, ``cost_bps`` must
    be zero to prevent double counting.
    """

    cfg = config or BacktestConfig()

    if execution_model is not None and cfg.cost_bps != 0.0:
        raise ValueError("cost_bps must be zero when execution_model is supplied.")

    returns = pd.to_numeric(
        asset_return,
        errors="coerce",
    ).rename("asset_return")
    decisions = pd.to_numeric(
        decision_exposure,
        errors="coerce",
    ).rename("decision_exposure")

    frame = pd.concat(
        [returns, decisions],
        axis=1,
        join="inner",
    )

    if frame.empty:
        raise ValueError("No aligned observations.")

    if frame["asset_return"].isna().any():
        raise ValueError("asset_return contains missing values.")

    frame["position"] = apply_execution_lag(
        frame["decision_exposure"],
        lag_days=execution_lag_days,
        initial_position=cfg.initial_position,
    ).clip(
        lower=cfg.minimum_position,
        upper=cfg.maximum_position,
    )

    previous_position = frame["position"].shift(1)
    previous_position.iloc[0] = cfg.initial_position

    frame["turnover"] = (frame["position"] - previous_position).abs()

    if execution_model is None:
        frame["transaction_cost"] = frame["turnover"] * cfg.cost_bps / 10_000.0
    else:
        _apply_execution_model(
            frame,
            model=execution_model,
        )

    frame["gross_strategy_return"] = frame["position"] * frame["asset_return"]
    frame["strategy_return"] = frame["gross_strategy_return"] - frame["transaction_cost"]

    if (frame["strategy_return"] <= -1.0).any():
        raise ValueError("A strategy return is less than or equal to -100%.")

    frame["equity"] = cfg.initial_equity * (1.0 + frame["strategy_return"]).cumprod()

    frame["drawdown"] = frame["equity"] / frame["equity"].cummax() - 1.0

    base_columns = [
        "asset_return",
        "decision_exposure",
        "position",
        "turnover",
        "transaction_cost",
        "gross_strategy_return",
        "strategy_return",
        "equity",
        "drawdown",
    ]

    if execution_model is None:
        return frame[base_columns]

    execution_columns = [
        "portfolio_notional",
        "daily_volume_notional",
        "daily_volatility",
        "order_notional",
        "participation_rate",
        "fee_bps",
        "spread_bps",
        "slippage_bps",
        "market_impact_bps",
        "execution_cost_bps",
        "execution_cost_notional",
        "within_participation_limit",
    ]

    return frame[base_columns[:5] + execution_columns + base_columns[5:]]


def validate_accounting(frame: pd.DataFrame) -> None:
    """Validate the principal accounting identities."""

    expected_gross = frame["position"] * frame["asset_return"]
    expected_net = expected_gross - frame["transaction_cost"]

    if not np.allclose(
        expected_gross,
        frame["gross_strategy_return"],
    ):
        raise ValueError("Gross return accounting is inconsistent.")

    if not np.allclose(
        expected_net,
        frame["strategy_return"],
    ):
        raise ValueError("Net return accounting is inconsistent.")
