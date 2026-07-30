"""Daily exposure backtesting with explicit execution lags and costs."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


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


def run_backtest(
    asset_return: pd.Series,
    decision_exposure: pd.Series,
    *,
    execution_lag_days: int = 1,
    config: BacktestConfig | None = None,
) -> pd.DataFrame:
    """Run a daily backtest from returns and decision exposures."""

    cfg = config or BacktestConfig()

    returns = pd.to_numeric(asset_return, errors="coerce").rename("asset_return")
    decisions = pd.to_numeric(decision_exposure, errors="coerce").rename("decision_exposure")

    frame = pd.concat([returns, decisions], axis=1, join="inner")

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
    frame["transaction_cost"] = frame["turnover"] * cfg.cost_bps / 10_000.0

    frame["gross_strategy_return"] = frame["position"] * frame["asset_return"]
    frame["strategy_return"] = frame["gross_strategy_return"] - frame["transaction_cost"]

    if (frame["strategy_return"] <= -1.0).any():
        raise ValueError("A strategy return is less than or equal to -100%.")

    frame["equity"] = cfg.initial_equity * (1.0 + frame["strategy_return"]).cumprod()

    frame["drawdown"] = frame["equity"] / frame["equity"].cummax() - 1.0

    return frame[
        [
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
    ]


def validate_accounting(frame: pd.DataFrame) -> None:
    """Validate the principal accounting identities."""

    expected_gross = frame["position"] * frame["asset_return"]
    expected_net = expected_gross - frame["transaction_cost"]

    if not np.allclose(expected_gross, frame["gross_strategy_return"]):
        raise ValueError("Gross return accounting is inconsistent.")

    if not np.allclose(expected_net, frame["strategy_return"]):
        raise ValueError("Net return accounting is inconsistent.")
