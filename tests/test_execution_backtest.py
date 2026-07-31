from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from hilmarbench.backtest import (
    BacktestConfig,
    ExecutionModelInputs,
    run_backtest,
    validate_accounting,
)
from hilmarbench.execution import ExecutionCostAssumptions


def assumptions() -> ExecutionCostAssumptions:
    return ExecutionCostAssumptions(
        fee_bps=2.0,
        half_spread_bps=3.0,
        slippage_bps=5.0,
        impact_coefficient_bps=8.0,
        impact_exponent=0.5,
        reference_participation_rate=0.01,
        reference_volatility=0.04,
        maximum_participation_rate=0.10,
    )


def test_legacy_fixed_cost_mode_is_unchanged() -> None:
    index = pd.date_range(
        "2026-01-01",
        periods=2,
        freq="D",
        tz="UTC",
    )

    result = run_backtest(
        pd.Series([0.0, 0.0], index=index),
        pd.Series([1.0, 1.0], index=index),
        execution_lag_days=0,
        config=BacktestConfig(cost_bps=25.0),
    )

    assert list(result.columns) == [
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
    assert result["transaction_cost"].iloc[0] == pytest.approx(0.0025)


def test_execution_model_decomposes_initial_order_cost() -> None:
    index = pd.date_range(
        "2026-01-01",
        periods=2,
        freq="D",
        tz="UTC",
    )

    result = run_backtest(
        pd.Series([0.0, 0.0], index=index),
        pd.Series([1.0, 1.0], index=index),
        execution_lag_days=0,
        config=BacktestConfig(cost_bps=0.0),
        execution_model=ExecutionModelInputs(
            assumptions=assumptions(),
            portfolio_notional=1_000_000.0,
            daily_volume_notional=100_000_000.0,
            daily_volatility=0.04,
        ),
    )

    first = result.iloc[0]

    assert first["order_notional"] == pytest.approx(1_000_000.0)
    assert first["participation_rate"] == pytest.approx(0.01)
    assert first["fee_bps"] == pytest.approx(2.0)
    assert first["spread_bps"] == pytest.approx(3.0)
    assert first["slippage_bps"] == pytest.approx(5.0)
    assert first["market_impact_bps"] == pytest.approx(8.0)
    assert first["execution_cost_bps"] == pytest.approx(18.0)
    assert first["execution_cost_notional"] == pytest.approx(1_800.0)
    assert first["transaction_cost"] == pytest.approx(0.0018)
    assert result["equity"].iloc[-1] == pytest.approx(0.9982)

    validate_accounting(result)


def test_zero_turnover_has_zero_advanced_execution_cost() -> None:
    index = pd.RangeIndex(3)

    result = run_backtest(
        pd.Series([0.0, 0.0, 0.0], index=index),
        pd.Series([0.0, 0.0, 0.0], index=index),
        execution_lag_days=0,
        config=BacktestConfig(cost_bps=0.0),
        execution_model=ExecutionModelInputs(
            assumptions=assumptions(),
            portfolio_notional=1_000_000.0,
            daily_volume_notional=100_000_000.0,
            daily_volatility=0.04,
        ),
    )

    assert np.allclose(result["order_notional"], 0.0)
    assert np.allclose(result["execution_cost_bps"], 0.0)
    assert np.allclose(result["transaction_cost"], 0.0)


def test_execution_model_rejects_fixed_cost_double_counting() -> None:
    with pytest.raises(
        ValueError,
        match="cost_bps must be zero",
    ):
        run_backtest(
            pd.Series([0.0]),
            pd.Series([1.0]),
            execution_lag_days=0,
            config=BacktestConfig(cost_bps=25.0),
            execution_model=ExecutionModelInputs(
                assumptions=assumptions(),
                portfolio_notional=1_000_000.0,
                daily_volume_notional=100_000_000.0,
                daily_volatility=0.04,
            ),
        )


def test_larger_portfolio_has_higher_impact_and_lower_equity() -> None:
    index = pd.RangeIndex(2)
    returns = pd.Series([0.0, 0.0], index=index)
    decisions = pd.Series([1.0, 1.0], index=index)

    small = run_backtest(
        returns,
        decisions,
        execution_lag_days=0,
        config=BacktestConfig(cost_bps=0.0),
        execution_model=ExecutionModelInputs(
            assumptions=assumptions(),
            portfolio_notional=1_000_000.0,
            daily_volume_notional=100_000_000.0,
            daily_volatility=0.04,
        ),
    )

    large = run_backtest(
        returns,
        decisions,
        execution_lag_days=0,
        config=BacktestConfig(cost_bps=0.0),
        execution_model=ExecutionModelInputs(
            assumptions=assumptions(),
            portfolio_notional=4_000_000.0,
            daily_volume_notional=100_000_000.0,
            daily_volatility=0.04,
        ),
    )

    assert large["market_impact_bps"].iloc[0] > small["market_impact_bps"].iloc[0]
    assert large["equity"].iloc[-1] < small["equity"].iloc[-1]


def test_series_inputs_are_aligned_by_index() -> None:
    index = pd.date_range(
        "2026-01-01",
        periods=2,
        freq="D",
        tz="UTC",
    )

    result = run_backtest(
        pd.Series([0.0, 0.0], index=index),
        pd.Series([1.0, 1.0], index=index),
        execution_lag_days=0,
        config=BacktestConfig(cost_bps=0.0),
        execution_model=ExecutionModelInputs(
            assumptions=assumptions(),
            portfolio_notional=pd.Series(
                [1_000_000.0, 2_000_000.0],
                index=index,
            ),
            daily_volume_notional=pd.Series(
                [100_000_000.0, 200_000_000.0],
                index=index,
            ),
            daily_volatility=pd.Series(
                [0.04, 0.08],
                index=index,
            ),
        ),
    )

    assert result["portfolio_notional"].tolist() == [
        1_000_000.0,
        2_000_000.0,
    ]
    assert result["daily_volatility"].tolist() == [
        0.04,
        0.08,
    ]


def test_unaligned_execution_series_is_rejected() -> None:
    index = pd.RangeIndex(2)

    with pytest.raises(
        ValueError,
        match="missing or unaligned",
    ):
        run_backtest(
            pd.Series([0.0, 0.0], index=index),
            pd.Series([1.0, 1.0], index=index),
            execution_lag_days=0,
            config=BacktestConfig(cost_bps=0.0),
            execution_model=ExecutionModelInputs(
                assumptions=assumptions(),
                portfolio_notional=pd.Series(
                    [1_000_000.0],
                    index=pd.RangeIndex(1),
                ),
                daily_volume_notional=100_000_000.0,
                daily_volatility=0.04,
            ),
        )


@pytest.mark.parametrize(
    (
        "portfolio_notional",
        "daily_volume_notional",
        "daily_volatility",
        "message",
    ),
    [
        (
            0.0,
            100_000_000.0,
            0.04,
            "portfolio_notional",
        ),
        (
            1_000_000.0,
            0.0,
            0.04,
            "daily_volume_notional",
        ),
        (
            1_000_000.0,
            100_000_000.0,
            -0.01,
            "daily_volatility",
        ),
        (
            1_000_000.0,
            100_000_000.0,
            float("inf"),
            "daily_volatility",
        ),
    ],
)
def test_invalid_execution_series_values_are_rejected(
    portfolio_notional: float,
    daily_volume_notional: float,
    daily_volatility: float,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        run_backtest(
            pd.Series([0.0]),
            pd.Series([1.0]),
            execution_lag_days=0,
            config=BacktestConfig(cost_bps=0.0),
            execution_model=ExecutionModelInputs(
                assumptions=assumptions(),
                portfolio_notional=portfolio_notional,
                daily_volume_notional=daily_volume_notional,
                daily_volatility=daily_volatility,
            ),
        )


def test_participation_limit_is_exposed_in_backtest() -> None:
    result = run_backtest(
        pd.Series([0.0]),
        pd.Series([1.0]),
        execution_lag_days=0,
        config=BacktestConfig(cost_bps=0.0),
        execution_model=ExecutionModelInputs(
            assumptions=assumptions(),
            portfolio_notional=20_000_000.0,
            daily_volume_notional=100_000_000.0,
            daily_volatility=0.04,
        ),
    )

    assert result["participation_rate"].iloc[0] == pytest.approx(0.20)
    assert not bool(result["within_participation_limit"].iloc[0])
