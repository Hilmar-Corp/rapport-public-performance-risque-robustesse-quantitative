from __future__ import annotations

import math

import numpy as np
import pytest

from hilmarbench.temporal_statistics import (
    annualized_sharpe,
    hac_adjusted_sharpe,
    ljung_box_test,
    moving_block_sharpe_interval,
    newey_west_long_run_variance,
    sample_autocorrelation,
)


def test_zero_lag_newey_west_matches_population_variance() -> None:
    returns = np.array(
        [0.01, -0.02, 0.03, 0.00, 0.02],
        dtype=float,
    )

    result = newey_west_long_run_variance(
        returns,
        lag_count=0,
    )

    assert result == pytest.approx(
        np.var(
            returns,
            ddof=0,
        )
    )


def test_positive_serial_dependence_reduces_hac_sharpe() -> None:
    rng = np.random.default_rng(42)

    returns = np.empty(
        2_000,
        dtype=float,
    )
    returns[0] = 0.001

    for index in range(
        1,
        len(returns),
    ):
        returns[index] = (
            0.0005
            + 0.80 * (returns[index - 1] - 0.0005)
            + rng.normal(
                0.0,
                0.005,
            )
        )

    result = hac_adjusted_sharpe(
        returns,
        lag_count=21,
    )

    assert result.observations == 2_000
    assert result.lag_count == 21
    assert result.volatility_inflation_factor > 1.0

    assert abs(result.hac_adjusted_annualized_sharpe) < abs(result.conventional_annualized_sharpe)


def test_sample_autocorrelation_contract() -> None:
    values = np.array(
        [1.0, -1.0] * 100,
    )

    assert (
        sample_autocorrelation(
            values,
            0,
        )
        == 1.0
    )

    assert (
        sample_autocorrelation(
            values,
            1,
        )
        < -0.95
    )


def test_ljung_box_detects_serial_dependence() -> None:
    values = np.array(
        [1.0, -1.0] * 250,
    )

    result = ljung_box_test(
        values,
        lag_count=10,
    )

    assert result.observations == 500
    assert result.lag_count == 10
    assert result.statistic > 100.0
    assert result.p_value < 1e-10
    assert len(result.autocorrelations) == 10


def test_moving_block_interval_is_deterministic() -> None:
    rng = np.random.default_rng(7)

    returns = rng.normal(
        0.001,
        0.01,
        500,
    )

    first = moving_block_sharpe_interval(
        returns,
        block_size=21,
        repetitions=200,
        seed=99,
    )

    second = moving_block_sharpe_interval(
        returns,
        block_size=21,
        repetitions=200,
        seed=99,
    )

    assert first == second
    assert first.interval_lower < first.interval_upper

    assert first.interval_lower <= first.bootstrap_median <= first.interval_upper

    assert 0.0 <= first.bootstrap_positive_share <= 1.0


def test_annualized_sharpe_matches_manual_result() -> None:
    returns = np.array(
        [0.01, -0.005, 0.02, 0.0],
    )

    expected = float(
        np.mean(returns)
        / np.std(
            returns,
            ddof=1,
        )
        * math.sqrt(365)
    )

    assert annualized_sharpe(returns) == pytest.approx(expected)


@pytest.mark.parametrize(
    "values, message",
    [
        ([], "too few"),
        ([0.01, 0.02], "too few"),
        (
            [[0.01, 0.02], [0.03, 0.04]],
            "one-dimensional",
        ),
        ([0.01, np.nan, 0.02], "finite"),
        ([0.01, 0.01, 0.01], "positive variance"),
    ],
)
def test_invalid_return_series_are_rejected(
    values: object,
    message: str,
) -> None:
    with pytest.raises(
        ValueError,
        match=message,
    ):
        annualized_sharpe(
            values,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "annualization",
    [0, -1, True],
)
def test_invalid_annualization_is_rejected(
    annualization: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="positive integer",
    ):
        annualized_sharpe(
            [0.01, -0.01, 0.02],
            annualization=annualization,
        )


@pytest.mark.parametrize(
    "lag_count",
    [-1, 3, True],
)
def test_invalid_newey_west_lag_is_rejected(
    lag_count: int,
) -> None:
    with pytest.raises(
        ValueError,
        match="sample size minus one",
    ):
        newey_west_long_run_variance(
            [0.01, -0.01, 0.02],
            lag_count=lag_count,
        )


def test_ljung_box_requires_positive_lag() -> None:
    with pytest.raises(
        ValueError,
        match="must be positive",
    ):
        ljung_box_test(
            [0.01, -0.01, 0.02],
            lag_count=0,
        )


def test_bootstrap_rejects_zero_block_size() -> None:
    with pytest.raises(
        ValueError,
        match="block_size",
    ):
        moving_block_sharpe_interval(
            np.linspace(-0.01, 0.02, 10),
            block_size=0,
        )


def test_bootstrap_rejects_oversized_block() -> None:
    with pytest.raises(
        ValueError,
        match="block_size",
    ):
        moving_block_sharpe_interval(
            np.linspace(-0.01, 0.02, 10),
            block_size=11,
        )


def test_bootstrap_rejects_too_few_repetitions() -> None:
    with pytest.raises(
        ValueError,
        match="at least 99",
    ):
        moving_block_sharpe_interval(
            np.linspace(-0.01, 0.02, 10),
            block_size=5,
            repetitions=10,
        )


@pytest.mark.parametrize(
    "confidence_level",
    [0.0, 1.0],
)
def test_bootstrap_rejects_invalid_confidence(
    confidence_level: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="strictly between",
    ):
        moving_block_sharpe_interval(
            np.linspace(-0.01, 0.02, 10),
            block_size=5,
            confidence_level=confidence_level,
        )
