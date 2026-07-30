from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from hilmarbench.metrics import compute_performance_metrics


def test_flat_returns_produce_flat_equity() -> None:
    index = pd.date_range(
        "2024-01-01",
        periods=366,
        freq="D",
        tz="UTC",
    )

    metrics = compute_performance_metrics(
        pd.Series(
            0.0,
            index=index,
        )
    )

    assert metrics["final_equity"] == 1.0
    assert metrics["total_return"] == 0.0
    assert metrics["cagr"] == 0.0
    assert metrics["annualized_volatility"] == 0.0
    assert math.isnan(metrics["sharpe"])
    assert metrics["maximum_drawdown"] == 0.0


def test_one_year_compounding_is_exact() -> None:
    index = pd.date_range(
        "2024-01-01",
        periods=366,
        freq="D",
        tz="UTC",
    )

    returns = pd.Series(
        0.0,
        index=index,
    )

    returns.iloc[0] = 0.10

    metrics = compute_performance_metrics(returns)

    assert metrics["final_equity"] == pytest.approx(1.10)

    assert metrics["total_return"] == pytest.approx(0.10)

    expected_cagr = 1.10 ** (365.0 / 366.0) - 1.0

    assert metrics["cagr"] == pytest.approx(expected_cagr)


def test_known_maximum_drawdown() -> None:
    index = pd.date_range(
        "2025-01-01",
        periods=3,
        freq="D",
        tz="UTC",
    )

    metrics = compute_performance_metrics(
        pd.Series(
            [0.10, -0.20, 0.05],
            index=index,
        )
    )

    assert metrics["maximum_drawdown"] == pytest.approx(-0.20)


def test_hit_rate_counts_only_positive_returns() -> None:
    metrics = compute_performance_metrics(
        pd.Series(
            [0.01, 0.0, -0.01],
            index=pd.RangeIndex(3),
        )
    )

    assert metrics["hit_rate"] == pytest.approx(1.0 / 3.0)


def test_optional_portfolio_statistics() -> None:
    index = pd.date_range(
        "2025-01-01",
        periods=4,
        freq="D",
        tz="UTC",
    )

    metrics = compute_performance_metrics(
        pd.Series(
            [0.0, 0.01, -0.01, 0.02],
            index=index,
        ),
        position=pd.Series(
            [0.0, 0.5, 1.0, 0.5],
            index=index,
        ),
        turnover=pd.Series(
            [0.0, 0.5, 0.5, 0.5],
            index=index,
        ),
        transaction_cost=pd.Series(
            [0.0, 0.001, 0.001, 0.001],
            index=index,
        ),
    )

    assert metrics["mean_position"] == pytest.approx(0.5)

    assert metrics["minimum_position"] == 0.0
    assert metrics["maximum_position"] == 1.0

    assert metrics["turnover"] == pytest.approx(1.5)

    assert metrics["transaction_cost_sum"] == pytest.approx(0.003)


def test_empty_return_series_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="empty",
    ):
        compute_performance_metrics(pd.Series(dtype=float))


def test_total_loss_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="100%",
    ):
        compute_performance_metrics(pd.Series([0.01, -1.0]))


def test_input_series_is_not_mutated() -> None:
    returns = pd.Series(
        [0.01, -0.02, 0.03],
        index=pd.RangeIndex(3),
    )

    original = returns.copy(deep=True)

    compute_performance_metrics(returns)

    pd.testing.assert_series_equal(
        returns,
        original,
    )


def test_non_datetime_index_uses_observation_count() -> None:
    returns = pd.Series(
        np.full(
            365,
            0.001,
        ),
        index=pd.RangeIndex(365),
    )

    metrics = compute_performance_metrics(returns)

    expected_final = 1.001**365

    assert metrics["final_equity"] == pytest.approx(expected_final)

    assert metrics["cagr"] == pytest.approx(expected_final - 1.0)
