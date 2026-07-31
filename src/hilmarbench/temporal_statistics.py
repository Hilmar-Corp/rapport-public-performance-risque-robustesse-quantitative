"""Temporal-dependence diagnostics for return series."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, TypeAlias

import numpy as np
from numpy.typing import NDArray
from scipy.stats import chi2

VectorInput: TypeAlias = Sequence[float | int] | NDArray[Any]


@dataclass(frozen=True)
class HACSharpeResult:
    """Conventional and HAC-adjusted annualized Sharpe estimates."""

    observations: int
    annualization: int
    lag_count: int
    mean_periodic_return: float
    conventional_periodic_volatility: float
    long_run_periodic_volatility: float
    conventional_annualized_sharpe: float
    hac_adjusted_annualized_sharpe: float
    volatility_inflation_factor: float


@dataclass(frozen=True)
class LjungBoxResult:
    """Ljung-Box portmanteau test result."""

    observations: int
    lag_count: int
    statistic: float
    p_value: float
    autocorrelations: tuple[float, ...]


@dataclass(frozen=True)
class BlockBootstrapSharpeInterval:
    """Moving-block bootstrap interval for an annualized Sharpe ratio."""

    observations: int
    annualization: int
    block_size: int
    repetitions: int
    seed: int
    confidence_level: float
    observed_annualized_sharpe: float
    interval_lower: float
    interval_upper: float
    bootstrap_median: float
    bootstrap_positive_share: float


def _finite_vector(
    values: VectorInput,
    *,
    minimum_observations: int = 3,
) -> NDArray[np.float64]:
    vector = np.asarray(
        values,
        dtype=np.float64,
    )

    if vector.ndim != 1:
        raise ValueError("Return series must be one-dimensional.")

    if vector.size < minimum_observations:
        raise ValueError("Return series contains too few observations.")

    if not np.isfinite(vector).all():
        raise ValueError("Return series must contain only finite values.")

    return vector


def _validate_annualization(
    annualization: int,
) -> None:
    if type(annualization) is bool or annualization <= 0:
        raise ValueError("annualization must be a positive integer.")


def _validate_lag_count(
    lag_count: int,
    observations: int,
) -> None:
    if type(lag_count) is bool or lag_count < 0 or lag_count >= observations:
        raise ValueError("lag_count must be between zero and the sample size minus one.")


def annualized_sharpe(
    returns: VectorInput,
    *,
    annualization: int = 365,
) -> float:
    """Calculate the conventional annualized arithmetic Sharpe ratio."""

    values = _finite_vector(returns)
    _validate_annualization(annualization)

    volatility = float(
        np.std(
            values,
            ddof=1,
        )
    )

    if volatility <= 0.0:
        raise ValueError("Return series must have positive variance.")

    return float(np.mean(values) / volatility * math.sqrt(annualization))


def sample_autocorrelation(
    returns: VectorInput,
    lag: int,
) -> float:
    """Calculate the sample autocorrelation at a controlled lag."""

    values = _finite_vector(returns)

    _validate_lag_count(
        lag,
        len(values),
    )

    if lag == 0:
        return 1.0

    centered = values - np.mean(values)

    denominator = float(
        np.dot(
            centered,
            centered,
        )
    )

    if denominator <= 0.0:
        raise ValueError("Return series must have positive variance.")

    numerator = float(
        np.dot(
            centered[lag:],
            centered[:-lag],
        )
    )

    return numerator / denominator


def newey_west_long_run_variance(
    returns: VectorInput,
    *,
    lag_count: int,
) -> float:
    """Estimate long-run variance using the Bartlett Newey-West kernel."""

    values = _finite_vector(returns)
    observations = len(values)

    _validate_lag_count(
        lag_count,
        observations,
    )

    centered = values - np.mean(values)

    gamma_zero = float(
        np.dot(
            centered,
            centered,
        )
        / observations
    )

    if gamma_zero <= 0.0:
        raise ValueError("Return series must have positive variance.")

    long_run_variance = gamma_zero

    for lag in range(
        1,
        lag_count + 1,
    ):
        autocovariance = float(
            np.dot(
                centered[lag:],
                centered[:-lag],
            )
            / observations
        )

        bartlett_weight = 1.0 - lag / (lag_count + 1.0)

        long_run_variance += 2.0 * bartlett_weight * autocovariance

    if not math.isfinite(long_run_variance) or long_run_variance <= 0.0:
        raise ValueError("Newey-West long-run variance must be positive.")

    return float(long_run_variance)


def hac_adjusted_sharpe(
    returns: VectorInput,
    *,
    lag_count: int,
    annualization: int = 365,
) -> HACSharpeResult:
    """Calculate conventional and Newey-West-adjusted Sharpe ratios."""

    values = _finite_vector(returns)
    _validate_annualization(annualization)

    conventional_volatility = float(
        np.std(
            values,
            ddof=1,
        )
    )

    if conventional_volatility <= 0.0:
        raise ValueError("Return series must have positive variance.")

    long_run_variance = newey_west_long_run_variance(
        values,
        lag_count=lag_count,
    )

    long_run_volatility = math.sqrt(long_run_variance)
    mean_return = float(np.mean(values))
    annualization_factor = math.sqrt(annualization)

    conventional_sharpe = mean_return / conventional_volatility * annualization_factor

    adjusted_sharpe = mean_return / long_run_volatility * annualization_factor

    return HACSharpeResult(
        observations=len(values),
        annualization=annualization,
        lag_count=lag_count,
        mean_periodic_return=mean_return,
        conventional_periodic_volatility=(conventional_volatility),
        long_run_periodic_volatility=(long_run_volatility),
        conventional_annualized_sharpe=float(conventional_sharpe),
        hac_adjusted_annualized_sharpe=float(adjusted_sharpe),
        volatility_inflation_factor=float(long_run_volatility / conventional_volatility),
    )


def ljung_box_test(
    returns: VectorInput,
    *,
    lag_count: int,
) -> LjungBoxResult:
    """Test the joint null of zero autocorrelation through lag_count."""

    values = _finite_vector(returns)
    observations = len(values)

    _validate_lag_count(
        lag_count,
        observations,
    )

    if lag_count == 0:
        raise ValueError("Ljung-Box lag_count must be positive.")

    autocorrelations = tuple(
        sample_autocorrelation(
            values,
            lag,
        )
        for lag in range(
            1,
            lag_count + 1,
        )
    )

    statistic = float(
        observations
        * (observations + 2)
        * sum(
            autocorrelation**2 / (observations - lag)
            for lag, autocorrelation in enumerate(
                autocorrelations,
                start=1,
            )
        )
    )

    p_value = float(
        chi2.sf(
            statistic,
            lag_count,
        )
    )

    return LjungBoxResult(
        observations=observations,
        lag_count=lag_count,
        statistic=statistic,
        p_value=p_value,
        autocorrelations=autocorrelations,
    )


def _circular_moving_block_indices(
    observations: int,
    block_size: int,
    rng: np.random.Generator,
) -> NDArray[np.int64]:
    block_count = math.ceil(observations / block_size)

    starts = rng.integers(
        0,
        observations,
        size=block_count,
        dtype=np.int64,
    )

    offsets = np.arange(
        block_size,
        dtype=np.int64,
    )

    blocks = [(start + offsets) % observations for start in starts]

    return np.concatenate(blocks)[:observations]


def moving_block_sharpe_interval(
    returns: VectorInput,
    *,
    annualization: int = 365,
    block_size: int = 21,
    repetitions: int = 2_000,
    confidence_level: float = 0.95,
    seed: int = 20260731,
) -> BlockBootstrapSharpeInterval:
    """Estimate a percentile Sharpe interval by circular block bootstrap."""

    values = _finite_vector(
        returns,
        minimum_observations=10,
    )
    observations = len(values)

    _validate_annualization(annualization)

    if type(block_size) is bool or block_size <= 0 or block_size > observations:
        raise ValueError("block_size must be between one and the sample size.")

    if type(repetitions) is bool or repetitions < 99:
        raise ValueError("repetitions must be at least 99.")

    if not math.isfinite(confidence_level) or not 0.0 < confidence_level < 1.0:
        raise ValueError("confidence_level must be strictly between zero and one.")

    observed_sharpe = annualized_sharpe(
        values,
        annualization=annualization,
    )

    rng = np.random.default_rng(seed)

    bootstrap_sharpes = np.empty(
        repetitions,
        dtype=np.float64,
    )

    for repetition in range(repetitions):
        indices = _circular_moving_block_indices(
            observations,
            block_size,
            rng,
        )

        sample = values[indices]

        sample_volatility = float(
            np.std(
                sample,
                ddof=1,
            )
        )

        if sample_volatility <= 0.0:
            bootstrap_sharpes[repetition] = np.nan
            continue

        bootstrap_sharpes[repetition] = float(
            np.mean(sample) / sample_volatility * math.sqrt(annualization)
        )

    finite_bootstrap = bootstrap_sharpes[np.isfinite(bootstrap_sharpes)]

    if finite_bootstrap.size < (repetitions * 0.95):
        raise RuntimeError("Too few finite bootstrap Sharpe estimates.")

    tail_probability = (1.0 - confidence_level) / 2.0

    interval = np.quantile(
        finite_bootstrap,
        [
            tail_probability,
            1.0 - tail_probability,
        ],
        method="linear",
    )

    return BlockBootstrapSharpeInterval(
        observations=observations,
        annualization=annualization,
        block_size=block_size,
        repetitions=repetitions,
        seed=seed,
        confidence_level=confidence_level,
        observed_annualized_sharpe=(observed_sharpe),
        interval_lower=float(interval[0]),
        interval_upper=float(interval[1]),
        bootstrap_median=float(np.median(finite_bootstrap)),
        bootstrap_positive_share=float(np.mean(finite_bootstrap > 0.0)),
    )
