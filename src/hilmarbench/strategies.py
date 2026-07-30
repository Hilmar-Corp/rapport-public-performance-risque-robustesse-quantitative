"""Transparent benchmark allocation rules."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def prices_from_returns(
    asset_return: pd.Series,
    *,
    initial_price: float = 1.0,
) -> pd.Series:
    """Construct a normalized price index."""

    returns = pd.to_numeric(asset_return, errors="coerce").fillna(0.0)
    price = initial_price * (1.0 + returns).cumprod()
    price.name = "price"

    return price


def fixed_exposure(
    index: pd.Index,
    *,
    exposure: float,
) -> pd.Series:
    """Generate a constant allocation."""

    return pd.Series(
        float(exposure),
        index=index,
        dtype=float,
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

    price_series = pd.to_numeric(price, errors="coerce")
    trailing_return = price_series / price_series.shift(lookback) - 1.0

    exposure = pd.Series(
        np.where(trailing_return > 0.0, 1.0, 0.0),
        index=price_series.index,
        dtype=float,
        name=f"momentum_{lookback}",
    )

    exposure[trailing_return.isna()] = np.nan
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

    price_series = pd.to_numeric(price, errors="coerce")

    fast = price_series.rolling(
        fast_window,
        min_periods=fast_window,
    ).mean()

    slow = price_series.rolling(
        slow_window,
        min_periods=slow_window,
    ).mean()

    exposure = pd.Series(
        np.where(fast > slow, 1.0, 0.0),
        index=price_series.index,
        dtype=float,
        name=f"ma_{fast_window}_{slow_window}",
    )

    exposure[slow.isna()] = np.nan
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

    if target_annualized_volatility <= 0:
        raise ValueError("target_annualized_volatility must be positive.")

    returns = pd.to_numeric(asset_return, errors="coerce")

    realized_volatility = returns.rolling(window, min_periods=window).std(ddof=1) * math.sqrt(
        periods_per_year
    )

    exposure = target_annualized_volatility / realized_volatility
    exposure = exposure.replace([np.inf, -np.inf], np.nan)

    exposure = exposure.clip(
        lower=minimum_exposure,
        upper=maximum_exposure,
    )

    exposure.name = f"vol_target_{window}"
    return exposure
