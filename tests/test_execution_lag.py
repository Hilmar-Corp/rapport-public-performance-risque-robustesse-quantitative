import pandas as pd

from hilmarbench.backtest import apply_execution_lag


def test_one_day_execution_lag() -> None:
    index = pd.date_range(
        "2025-01-01",
        periods=4,
        freq="D",
        tz="UTC",
    )

    decision = pd.Series(
        [0.2, 0.4, 0.8, 0.1],
        index=index,
    )

    actual = apply_execution_lag(
        decision,
        lag_days=1,
        initial_position=0.0,
    )

    expected = pd.Series(
        [0.0, 0.2, 0.4, 0.8],
        index=index,
        name="position",
    )

    pd.testing.assert_series_equal(actual, expected)
