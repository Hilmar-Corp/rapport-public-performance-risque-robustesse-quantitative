import numpy as np
import pandas as pd

from hilmarbench.strategies import (
    momentum_exposure,
    prices_from_returns,
    volatility_target_exposure,
)


def make_returns() -> pd.Series:
    generator = np.random.default_rng(42)

    index = pd.date_range(
        "2022-01-01",
        periods=600,
        freq="D",
        tz="UTC",
    )

    return pd.Series(
        generator.normal(
            loc=0.0005,
            scale=0.025,
            size=len(index),
        ),
        index=index,
    )


def test_future_data_does_not_change_past_volatility_target() -> None:
    original = make_returns()
    modified = original.copy()

    cutoff = 450
    modified.iloc[cutoff:] = modified.iloc[cutoff:] * -8.0

    original_signal = volatility_target_exposure(
        original,
        window=30,
    )

    modified_signal = volatility_target_exposure(
        modified,
        window=30,
    )

    pd.testing.assert_series_equal(
        original_signal.iloc[:cutoff],
        modified_signal.iloc[:cutoff],
    )


def test_future_data_does_not_change_past_momentum() -> None:
    original = make_returns()
    modified = original.copy()

    cutoff = 450
    modified.iloc[cutoff:] = 0.30

    original_signal = momentum_exposure(
        prices_from_returns(original),
        lookback=90,
    )

    modified_signal = momentum_exposure(
        prices_from_returns(modified),
        lookback=90,
    )

    pd.testing.assert_series_equal(
        original_signal.iloc[:cutoff],
        modified_signal.iloc[:cutoff],
    )
