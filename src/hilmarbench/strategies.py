"""Transparent benchmark allocation rules."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _as_float_series(
    values: pd.Series,
    *,
    fill_value: float | None = None,
) -> pd.Series:
    """Return a numeric float64 series while preserving the original index."""

    numeric = pd.to_numeric(
        values,
        errors="coerce",
    ).astype("float64")

    if fill_value is not None:
        numeric = numeric.fillna(fill_value)

    return numeric


def prices_from_returns(
    asset_return: pd.Series,
    *,
    initial_price: float = 1.0,
) -> pd.Series:
    """Construct a normalized price index."""

    if not math.isfinite(initial_price):
        raise ValueError("initial_price must be finite.")

    if initial_price <= 0.0:
        raise ValueError("initial_price must be positive.")

    returns = _as_float_series(
        asset_return,
        fill_value=0.0,
    )

    gross_return = 1.0 + returns
    price = initial_price * gross_return.cumprod()

    price.name = "price"
    return price


def fixed_exposure(
    index: pd.Index,
    *,
    exposure: float,
) -> pd.Series:
    """Generate a constant allocation."""

    if not math.isfinite(exposure):
        raise ValueError("exposure must be finite.")

    return pd.Series(
        float(exposure),
        index=index,
        dtype="float64",
        name=f"fixed_{exposure:g}",
    )


def momentum_exposure(
    price: pd.Series,
    *,
    lookback: int = 90,
) -> pd.Series:
    """Long-only time-series momentum."""

    if lookback <= 0:
        raise ValueError("lookback must be positive.")

    price_series = _as_float_series(price)
    lagged_price = price_series.shift(lookback)
    trailing_return = price_series / lagged_price - 1.0

    exposure = trailing_return.gt(0.0).astype("float64")
    exposure = exposure.mask(trailing_return.isna())
    exposure.name = f"momentum_{lookback}"

    return exposure


def moving_average_exposure(
    price: pd.Series,
    *,
    fast_window: int = 50,
    slow_window: int = 200,
) -> pd.Series:
    """Long-only moving-average crossover."""

    if fast_window <= 0 or slow_window <= 0:
        raise ValueError("Moving-average windows must be positive.")

    if fast_window >= slow_window:
        raise ValueError("fast_window must be lower than slow_window.")

    price_series = _as_float_series(price)

    fast = price_series.rolling(
        fast_window,
        min_periods=fast_window,
    ).mean()

    slow = price_series.rolling(
        slow_window,
        min_periods=slow_window,
    ).mean()

    exposure = fast.gt(slow).astype("float64")
    exposure = exposure.mask(slow.isna())
    exposure.name = f"ma_{fast_window}_{slow_window}"

    return exposure


def volatility_target_exposure(
    asset_return: pd.Series,
    *,
    window: int = 30,
    target_annualized_volatility: float = 0.30,
    periods_per_year: float = 365.0,
    minimum_exposure: float = 0.0,
    maximum_exposure: float = 1.0,
) -> pd.Series:
    """Allocate inversely to trailing realized volatility."""

    if window <= 1:
        raise ValueError("window must exceed one observation.")

    if not math.isfinite(target_annualized_volatility):
        raise ValueError("target_annualized_volatility must be finite.")

    if target_annualized_volatility <= 0.0:
        raise ValueError("target_annualized_volatility must be positive.")

    if not math.isfinite(periods_per_year):
        raise ValueError("periods_per_year must be finite.")

    if periods_per_year <= 0.0:
        raise ValueError("periods_per_year must be positive.")

    if not math.isfinite(minimum_exposure):
        raise ValueError("minimum_exposure must be finite.")

    if not math.isfinite(maximum_exposure):
        raise ValueError("maximum_exposure must be finite.")

    if minimum_exposure > maximum_exposure:
        raise ValueError("minimum_exposure must not exceed maximum_exposure.")

    returns = _as_float_series(asset_return)

    rolling_std = returns.rolling(
        window,
        min_periods=window,
    ).std(ddof=1)

    realized_volatility = rolling_std * math.sqrt(periods_per_year)

    exposure = target_annualized_volatility / realized_volatility

    exposure = exposure.replace(
        [np.inf, -np.inf],
        np.nan,
    )

    exposure = exposure.clip(
        lower=minimum_exposure,
        upper=maximum_exposure,
    )

    exposure.name = f"vol_target_{window}"
    return exposure
