from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from hilmarbench.strategies import (
    fixed_exposure,
    momentum_exposure,
    moving_average_exposure,
    prices_from_returns,
    volatility_target_exposure,
)


def test_prices_from_returns_compounds_exactly() -> None:
    returns = pd.Series(
        [0.10, -0.10, 0.05],
        index=pd.RangeIndex(3),
    )

    prices = prices_from_returns(
        returns,
        initial_price=100.0,
    )

    expected = pd.Series(
        [110.0, 99.0, 103.95],
        index=pd.RangeIndex(3),
        name="price",
    )

    pd.testing.assert_series_equal(
        prices,
        expected,
    )


def test_fixed_exposure_is_constant() -> None:
    index = pd.RangeIndex(20)

    exposure = fixed_exposure(
        index,
        exposure=0.37,
    )

    assert len(exposure) == 20
    assert np.allclose(
        exposure,
        0.37,
    )


def test_momentum_warmup_and_direction() -> None:
    price = pd.Series(
        [1.0, 2.0, 1.0, 3.0],
        index=pd.RangeIndex(4),
    )

    exposure = momentum_exposure(
        price,
        lookback=1,
    )

    assert np.isnan(exposure.iloc[0])

    assert exposure.iloc[1:].tolist() == [
        1.0,
        0.0,
        1.0,
    ]


def test_moving_average_warmup_and_direction() -> None:
    price = pd.Series(
        [1.0, 2.0, 3.0, 4.0, 1.0],
        index=pd.RangeIndex(5),
    )

    exposure = moving_average_exposure(
        price,
        fast_window=2,
        slow_window=3,
    )

    assert exposure.iloc[:2].isna().all()

    assert exposure.iloc[2:].tolist() == [
        1.0,
        1.0,
        0.0,
    ]


def test_volatility_target_reduces_exposure_when_volatility_rises() -> None:
    low_volatility = np.tile(
        [0.005, -0.005],
        25,
    )

    high_volatility = np.tile(
        [0.05, -0.05],
        25,
    )

    returns = pd.Series(
        np.concatenate(
            [
                low_volatility,
                high_volatility,
            ]
        )
    )

    exposure = volatility_target_exposure(
        returns,
        window=20,
        target_annualized_volatility=0.30,
    )

    low_regime_exposure = exposure.iloc[40:50].mean()
    high_regime_exposure = exposure.iloc[90:100].mean()

    assert high_regime_exposure < low_regime_exposure


def test_volatility_target_respects_bounds() -> None:
    generator = np.random.default_rng(4)

    returns = pd.Series(
        generator.normal(
            0.0,
            0.03,
            300,
        )
    )

    exposure = volatility_target_exposure(
        returns,
        window=30,
        target_annualized_volatility=0.30,
        minimum_exposure=0.10,
        maximum_exposure=0.80,
    ).dropna()

    assert (exposure >= 0.10).all()

    assert (exposure <= 0.80).all()


@pytest.mark.parametrize(
    ("function_name", "kwargs"),
    [
        (
            "momentum",
            {"lookback": 0},
        ),
        (
            "moving_average",
            {
                "fast_window": 0,
                "slow_window": 10,
            },
        ),
        (
            "moving_average",
            {
                "fast_window": 20,
                "slow_window": 10,
            },
        ),
        (
            "volatility_target",
            {"window": 1},
        ),
        (
            "volatility_target",
            {
                "target_annualized_volatility": 0.0,
            },
        ),
    ],
)
def test_invalid_strategy_parameters_are_rejected(
    function_name: str,
    kwargs: dict[str, float],
) -> None:
    series = pd.Series(
        np.linspace(
            1.0,
            2.0,
            100,
        )
    )

    with pytest.raises(ValueError):
        if function_name == "momentum":
            momentum_exposure(
                series,
                **kwargs,
            )

        elif function_name == "moving_average":
            moving_average_exposure(
                series,
                **kwargs,
            )

        else:
            volatility_target_exposure(
                series.pct_change().fillna(0.0),
                **kwargs,
            )


def test_strategy_functions_do_not_mutate_inputs() -> None:
    returns = pd.Series(
        np.linspace(
            -0.02,
            0.02,
            300,
        )
    )

    original = returns.copy(deep=True)

    volatility_target_exposure(
        returns,
        window=30,
    )

    pd.testing.assert_series_equal(
        returns,
        original,
    )
