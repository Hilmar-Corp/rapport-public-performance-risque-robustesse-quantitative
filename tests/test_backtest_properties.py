from __future__ import annotations

import numpy as np
import pandas as pd
from hypothesis import given, settings
from hypothesis import strategies as st

from hilmarbench.backtest import (
    BacktestConfig,
    run_backtest,
)

finite_return = st.floats(
    min_value=-0.50,
    max_value=0.50,
    allow_nan=False,
    allow_infinity=False,
    width=32,
)

bounded_exposure = st.floats(
    min_value=0.0,
    max_value=1.0,
    allow_nan=False,
    allow_infinity=False,
    width=32,
)

portfolio_paths = st.lists(
    st.tuples(
        finite_return,
        bounded_exposure,
    ),
    min_size=2,
    max_size=50,
)


@settings(
    max_examples=60,
    deadline=None,
)
@given(portfolio_paths)
def test_cash_position_preserves_equity(
    path: list[tuple[float, float]],
) -> None:
    returns = pd.Series([item[0] for item in path])

    cash = pd.Series(
        0.0,
        index=returns.index,
    )

    result = run_backtest(
        returns,
        cash,
        execution_lag_days=0,
        config=BacktestConfig(
            cost_bps=25.0,
        ),
    )

    assert np.allclose(
        result["equity"],
        1.0,
    )


@settings(
    max_examples=60,
    deadline=None,
)
@given(portfolio_paths)
def test_full_exposure_without_costs_matches_asset_returns(
    path: list[tuple[float, float]],
) -> None:
    returns = pd.Series([item[0] for item in path])

    full = pd.Series(
        1.0,
        index=returns.index,
    )

    result = run_backtest(
        returns,
        full,
        execution_lag_days=0,
        config=BacktestConfig(
            cost_bps=0.0,
        ),
    )

    assert np.allclose(
        result["strategy_return"],
        returns,
    )


@settings(
    max_examples=60,
    deadline=None,
)
@given(portfolio_paths)
def test_drawdown_never_exceeds_zero(
    path: list[tuple[float, float]],
) -> None:
    returns = pd.Series([item[0] for item in path])

    exposure = pd.Series([item[1] for item in path])

    result = run_backtest(
        returns,
        exposure,
        execution_lag_days=0,
        config=BacktestConfig(
            cost_bps=25.0,
        ),
    )

    assert (result["drawdown"] <= 1e-12).all()


@settings(
    max_examples=60,
    deadline=None,
)
@given(
    st.lists(
        bounded_exposure,
        min_size=2,
        max_size=50,
    )
)
def test_zero_return_equity_is_nonincreasing_under_costs(
    exposures: list[float],
) -> None:
    returns = pd.Series(
        0.0,
        index=pd.RangeIndex(len(exposures)),
    )

    decisions = pd.Series(
        exposures,
        index=returns.index,
    )

    result = run_backtest(
        returns,
        decisions,
        execution_lag_days=0,
        config=BacktestConfig(
            cost_bps=25.0,
        ),
    )

    assert (result["equity"].diff().dropna() <= 1e-15).all()


@settings(
    max_examples=60,
    deadline=None,
)
@given(portfolio_paths)
def test_transaction_cost_identity(
    path: list[tuple[float, float]],
) -> None:
    returns = pd.Series([item[0] for item in path])

    exposure = pd.Series([item[1] for item in path])

    cost_bps = 17.0

    result = run_backtest(
        returns,
        exposure,
        execution_lag_days=0,
        config=BacktestConfig(
            cost_bps=cost_bps,
        ),
    )

    expected = result["turnover"] * cost_bps / 10_000.0

    assert np.allclose(
        result["transaction_cost"],
        expected,
    )
