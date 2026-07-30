from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from hilmarbench.backtest import (
    BacktestConfig,
    apply_execution_lag,
    run_backtest,
    validate_accounting,
)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"cost_bps": -1.0},
        {"initial_equity": 0.0},
        {"initial_equity": -1.0},
        {
            "minimum_position": 1.0,
            "maximum_position": 0.0,
        },
        {
            "minimum_position": 0.0,
            "maximum_position": 1.0,
            "initial_position": 1.5,
        },
    ],
)
def test_invalid_backtest_configuration_is_rejected(
    kwargs: dict[str, float],
) -> None:
    with pytest.raises(ValueError):
        BacktestConfig(**kwargs)


def test_zero_day_lag_preserves_decisions(
    daily_index: pd.DatetimeIndex,
) -> None:
    decision = pd.Series(
        np.linspace(0.0, 1.0, len(daily_index)),
        index=daily_index,
    )

    actual = apply_execution_lag(
        decision,
        lag_days=0,
    )

    expected = decision.rename("position")

    pd.testing.assert_series_equal(
        actual,
        expected,
    )


def test_two_day_execution_lag(
    daily_index: pd.DatetimeIndex,
) -> None:
    decision = pd.Series(
        np.arange(len(daily_index), dtype=float),
        index=daily_index,
    )

    actual = apply_execution_lag(
        decision,
        lag_days=2,
        initial_position=-1.0,
    )

    expected = pd.Series(
        [-1.0, -1.0, 0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0],
        index=daily_index,
        name="position",
    )

    pd.testing.assert_series_equal(
        actual,
        expected,
    )


def test_negative_lag_is_rejected(
    daily_index: pd.DatetimeIndex,
) -> None:
    decision = pd.Series(
        0.5,
        index=daily_index,
    )

    with pytest.raises(
        ValueError,
        match="lag_days",
    ):
        apply_execution_lag(
            decision,
            lag_days=-1,
        )


def test_positions_are_clipped_to_configured_bounds(
    daily_index: pd.DatetimeIndex,
) -> None:
    returns = pd.Series(
        0.0,
        index=daily_index,
    )

    decisions = pd.Series(
        [-2.0, 2.0] * 5,
        index=daily_index,
    )

    result = run_backtest(
        returns,
        decisions,
        execution_lag_days=0,
        config=BacktestConfig(
            cost_bps=0.0,
            minimum_position=0.0,
            maximum_position=1.0,
        ),
    )

    assert result["position"].min() == 0.0
    assert result["position"].max() == 1.0


def test_missing_return_is_rejected(
    daily_index: pd.DatetimeIndex,
) -> None:
    returns = pd.Series(
        [0.0] * 9 + [np.nan],
        index=daily_index,
    )

    decisions = pd.Series(
        0.5,
        index=daily_index,
    )

    with pytest.raises(
        ValueError,
        match="missing",
    ):
        run_backtest(
            returns,
            decisions,
        )


def test_disjoint_series_are_rejected() -> None:
    returns = pd.Series(
        [0.01, 0.02],
        index=pd.date_range(
            "2024-01-01",
            periods=2,
            tz="UTC",
        ),
    )

    decisions = pd.Series(
        [0.5, 0.5],
        index=pd.date_range(
            "2025-01-01",
            periods=2,
            tz="UTC",
        ),
    )

    with pytest.raises(
        ValueError,
        match="aligned",
    ):
        run_backtest(
            returns,
            decisions,
        )


def test_transaction_costs_are_symmetric(
    daily_index: pd.DatetimeIndex,
) -> None:
    returns = pd.Series(
        0.0,
        index=daily_index,
    )

    decisions = pd.Series(
        [0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0],
        index=daily_index,
    )

    result = run_backtest(
        returns,
        decisions,
        execution_lag_days=0,
        config=BacktestConfig(
            cost_bps=25.0,
        ),
    )

    assert np.allclose(
        result["turnover"].iloc[1:],
        1.0,
    )

    assert np.allclose(
        result["transaction_cost"].iloc[1:],
        0.0025,
    )


def test_higher_costs_cannot_improve_final_equity(
    daily_index: pd.DatetimeIndex,
) -> None:
    returns = pd.Series(
        [0.02, -0.01] * 5,
        index=daily_index,
    )

    decisions = pd.Series(
        [0.0, 1.0] * 5,
        index=daily_index,
    )

    low_cost = run_backtest(
        returns,
        decisions,
        execution_lag_days=0,
        config=BacktestConfig(
            cost_bps=5.0,
        ),
    )

    high_cost = run_backtest(
        returns,
        decisions,
        execution_lag_days=0,
        config=BacktestConfig(
            cost_bps=50.0,
        ),
    )

    assert high_cost["equity"].iloc[-1] < low_cost["equity"].iloc[-1]


def test_accounting_validator_detects_tampering(
    daily_index: pd.DatetimeIndex,
) -> None:
    result = run_backtest(
        pd.Series(
            0.01,
            index=daily_index,
        ),
        pd.Series(
            0.5,
            index=daily_index,
        ),
        execution_lag_days=0,
        config=BacktestConfig(
            cost_bps=0.0,
        ),
    )

    corrupted = result.copy()
    corrupted.loc[daily_index[3], "strategy_return"] += 0.01

    with pytest.raises(
        ValueError,
        match="Net return",
    ):
        validate_accounting(corrupted)


def test_drawdown_is_zero_at_each_new_high(
    daily_index: pd.DatetimeIndex,
) -> None:
    result = run_backtest(
        pd.Series(
            [0.10, -0.05, 0.10, -0.20, 0.30, 0.0, 0.01, -0.01, 0.02, 0.03],
            index=daily_index,
        ),
        pd.Series(
            1.0,
            index=daily_index,
        ),
        execution_lag_days=0,
        config=BacktestConfig(
            cost_bps=0.0,
        ),
    )

    running_high = result["equity"].cummax()
    at_high = np.isclose(
        result["equity"],
        running_high,
    )

    assert np.allclose(
        result.loc[at_high, "drawdown"],
        0.0,
    )

    assert (result["drawdown"] <= 1e-15).all()
