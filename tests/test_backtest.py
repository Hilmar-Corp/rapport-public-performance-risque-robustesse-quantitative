import numpy as np
import pandas as pd

from hilmarbench.backtest import (
    BacktestConfig,
    run_backtest,
    validate_accounting,
)


def test_accounting_without_costs() -> None:
    index = pd.date_range(
        "2025-01-01",
        periods=3,
        freq="D",
        tz="UTC",
    )

    returns = pd.Series(
        [0.10, -0.05, 0.02],
        index=index,
    )

    decisions = pd.Series(
        [0.0, 0.5, 1.0],
        index=index,
    )

    result = run_backtest(
        returns,
        decisions,
        execution_lag_days=0,
        config=BacktestConfig(cost_bps=0.0),
    )

    assert np.allclose(
        result["strategy_return"],
        [0.0, -0.025, 0.02],
    )

    assert np.allclose(
        result["equity"],
        [1.0, 0.975, 0.9945],
    )

    validate_accounting(result)


def test_initial_allocation_is_charged() -> None:
    index = pd.date_range(
        "2025-01-01",
        periods=2,
        freq="D",
        tz="UTC",
    )

    result = run_backtest(
        pd.Series([0.0, 0.0], index=index),
        pd.Series([1.0, 1.0], index=index),
        execution_lag_days=0,
        config=BacktestConfig(
            cost_bps=25.0,
            initial_position=0.0,
        ),
    )

    assert np.isclose(result["turnover"].iloc[0], 1.0)
    assert np.isclose(result["transaction_cost"].iloc[0], 0.0025)
    assert np.isclose(result["equity"].iloc[-1], 0.9975)
