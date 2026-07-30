"""Generic statistical validation utilities for strategy return series."""

from __future__ import annotations

import itertools
import math
from collections.abc import Iterable

import numpy as np
from arch.bootstrap import SPA
from scipy.stats import kurtosis, norm, rankdata, skew


def _clean_returns(values: Iterable[float]) -> np.ndarray:
    array = np.asarray(list(values), dtype=float)
    array = array[np.isfinite(array)]

    if array.size < 3:
        raise ValueError("At least three finite observations are required")

    if array.std(ddof=1) <= 0:
        raise ValueError("Return series must have positive variance")

    return array


def probabilistic_sharpe_ratio(
    returns: Iterable[float],
    benchmark_sharpe_annualized: float = 0.0,
    annualization: int = 365,
) -> dict[str, float | int]:
    """Estimate the probability that Sharpe exceeds a benchmark Sharpe."""

    values = _clean_returns(returns)

    if annualization <= 0:
        raise ValueError("annualization must be positive")

    observations = int(values.size)
    periodic_sharpe = float(values.mean() / values.std(ddof=1))
    annualized_sharpe = periodic_sharpe * math.sqrt(annualization)
    benchmark_periodic = benchmark_sharpe_annualized / math.sqrt(annualization)

    sample_skew = float(skew(values, bias=False))
    sample_kurtosis = float(kurtosis(values, fisher=False, bias=False))

    variance_term = (
        1.0 - sample_skew * periodic_sharpe + ((sample_kurtosis - 1.0) / 4.0) * periodic_sharpe**2
    )

    if variance_term <= 0:
        raise ValueError("Invalid PSR variance term")

    statistic = (
        (periodic_sharpe - benchmark_periodic)
        * math.sqrt(observations - 1)
        / math.sqrt(variance_term)
    )

    return {
        "probability": float(norm.cdf(statistic)),
        "test_statistic": float(statistic),
        "observations": observations,
        "sharpe_annualized": float(annualized_sharpe),
        "benchmark_sharpe_annualized": float(benchmark_sharpe_annualized),
        "skewness": sample_skew,
        "pearson_kurtosis": sample_kurtosis,
        "annualization": int(annualization),
    }


def deflated_sharpe_ratio(
    returns: Iterable[float],
    trial_sharpes_annualized: Iterable[float],
    annualization: int = 365,
) -> dict[str, float | int]:
    """Calculate DSR using the dispersion of observed trial Sharpes."""

    trials = np.asarray(
        list(trial_sharpes_annualized),
        dtype=float,
    )
    trials = trials[np.isfinite(trials)]

    if trials.size < 2:
        raise ValueError("At least two trial Sharpe estimates are required")

    trial_standard_deviation = float(trials.std(ddof=1))

    if trial_standard_deviation <= 0:
        raise ValueError("Trial Sharpe dispersion must be positive")

    trial_count = int(trials.size)
    euler_gamma = 0.5772156649015329

    first_quantile = norm.ppf(1.0 - 1.0 / trial_count)
    second_quantile = norm.ppf(1.0 - 1.0 / (trial_count * math.e))

    expected_maximum_sharpe = trial_standard_deviation * (
        (1.0 - euler_gamma) * first_quantile + euler_gamma * second_quantile
    )

    result = probabilistic_sharpe_ratio(
        returns=returns,
        benchmark_sharpe_annualized=float(expected_maximum_sharpe),
        annualization=annualization,
    )

    result.update(
        {
            "trial_count": trial_count,
            "trial_sharpe_standard_deviation": (trial_standard_deviation),
            "expected_maximum_sharpe": float(expected_maximum_sharpe),
        }
    )

    return result


def reality_check_and_spa(
    return_differentials: np.ndarray,
    block_size: int = 21,
    repetitions: int = 2_000,
    seed: int = 20260730,
) -> dict[str, object]:
    """Run White Reality Check and Hansen SPA on return differentials.

    Positive values indicate that a candidate outperformed the benchmark.
    """

    matrix = np.asarray(return_differentials, dtype=float)

    if matrix.ndim != 2:
        raise ValueError("return_differentials must be two-dimensional")

    matrix = matrix[np.isfinite(matrix).all(axis=1)]

    if matrix.shape[0] < 10 or matrix.shape[1] < 1:
        raise ValueError("Insufficient observations or candidates")

    if block_size <= 0 or repetitions <= 0:
        raise ValueError("block_size and repetitions must be positive")

    benchmark_losses = np.zeros(matrix.shape[0])
    candidate_losses = -matrix

    reality_check = SPA(
        benchmark=benchmark_losses,
        models=candidate_losses,
        block_size=block_size,
        reps=repetitions,
        bootstrap="moving block",
        studentize=False,
        seed=seed,
    )
    reality_check.compute()

    hansen_spa = SPA(
        benchmark=benchmark_losses,
        models=candidate_losses,
        block_size=block_size,
        reps=repetitions,
        bootstrap="moving block",
        studentize=True,
        seed=seed,
    )
    hansen_spa.compute()

    rc_pvalues = {str(name): float(value) for name, value in reality_check.pvalues.items()}
    spa_pvalues = {str(name): float(value) for name, value in hansen_spa.pvalues.items()}

    return {
        "observations": int(matrix.shape[0]),
        "candidate_count": int(matrix.shape[1]),
        "block_size": int(block_size),
        "repetitions": int(repetitions),
        "seed": int(seed),
        "white_reality_check_pvalue": rc_pvalues["upper"],
        "hansen_spa_pvalue": spa_pvalues["consistent"],
        "reality_check_pvalues": rc_pvalues,
        "spa_pvalues": spa_pvalues,
    }


def purge_training_indices(
    train: np.ndarray,
    test: np.ndarray,
    n_observations: int,
    purge: int,
) -> np.ndarray:
    """Remove training observations around contiguous test segments."""

    if purge < 0:
        raise ValueError("purge must be non-negative")

    train = np.sort(np.asarray(train, dtype=int))
    test = np.sort(np.asarray(test, dtype=int))

    if purge == 0 or train.size == 0 or test.size == 0:
        return train

    split_points = np.flatnonzero(np.diff(test) > 1) + 1
    test_segments = np.split(test, split_points)

    keep = np.ones(train.size, dtype=bool)

    for segment in test_segments:
        lower = max(0, int(segment[0]) - purge)
        upper = min(
            n_observations - 1,
            int(segment[-1]) + purge,
        )
        keep &= ~((train >= lower) & (train <= upper))

    return train[keep]


def cscv_pbo(
    return_matrix: np.ndarray,
    n_blocks: int = 8,
    purge: int = 30,
) -> dict[str, float | int | str]:
    """Estimate CSCV Probability of Backtest Overfitting."""

    matrix = np.nan_to_num(
        np.asarray(return_matrix, dtype=float),
        nan=0.0,
    )

    if matrix.ndim != 2:
        raise ValueError("return_matrix must be two-dimensional")

    observations, candidate_count = matrix.shape

    if candidate_count < 2:
        raise ValueError("At least two candidates are required")

    if n_blocks < 2 or n_blocks % 2:
        raise ValueError("n_blocks must be an even integer")

    if n_blocks > observations:
        raise ValueError("n_blocks cannot exceed observations")

    edges = np.linspace(
        0,
        observations,
        n_blocks + 1,
        dtype=int,
    )
    chunks = [np.arange(edges[index], edges[index + 1]) for index in range(n_blocks)]

    logits: list[float] = []
    train_sizes: list[int] = []

    for selected in itertools.combinations(
        range(n_blocks),
        n_blocks // 2,
    ):
        selected_blocks = set(selected)

        raw_train = np.concatenate(
            [chunks[index] for index in range(n_blocks) if index in selected_blocks]
        )
        test = np.concatenate(
            [chunks[index] for index in range(n_blocks) if index not in selected_blocks]
        )

        train = purge_training_indices(
            raw_train,
            test,
            observations,
            purge,
        )

        if len(train) < 10 or len(test) < 10:
            continue

        winner = int(matrix[train].mean(axis=0).argmax())

        oos_means = matrix[test].mean(axis=0)
        percentile_ranks = rankdata(oos_means, method="average") / candidate_count
        winner_rank = float(percentile_ranks[winner])
        winner_rank = float(np.clip(winner_rank, 1e-9, 1 - 1e-9))

        logits.append(math.log(winner_rank / (1 - winner_rank)))
        train_sizes.append(len(train))

    if not logits:
        raise RuntimeError("No valid CSCV combinations remained")

    logit_array = np.asarray(logits)

    return {
        "pbo": float((logit_array < 0).mean()),
        "combinations": len(logit_array),
        "combinations_total": math.comb(n_blocks, n_blocks // 2),
        "blocks": int(n_blocks),
        "candidate_count": int(candidate_count),
        "purge_observations": int(purge),
        "purge_applied_to": "training_set_only",
        "minimum_train_observations": int(min(train_sizes)),
        "maximum_train_observations": int(max(train_sizes)),
    }


def equity_to_returns(
    equity_values: Iterable[float],
) -> np.ndarray:
    """Reconstruct daily simple returns from an equity curve."""

    equity = np.asarray(
        list(equity_values),
        dtype=float,
    )

    if equity.size == 0:
        raise ValueError("Equity curve cannot be empty")

    if not np.isfinite(equity).all():
        raise ValueError("Equity curve must be finite")

    if np.any(equity <= 0):
        raise ValueError("Equity values must be positive")

    returns = np.empty_like(equity)
    returns[0] = equity[0] - 1.0
    returns[1:] = equity[1:] / equity[:-1] - 1.0

    return returns


def _moving_block_indices(
    observations: int,
    block_size: int,
    rng: np.random.Generator,
) -> np.ndarray:
    block_count = math.ceil(observations / block_size)

    starts = rng.integers(
        0,
        observations - block_size + 1,
        size=block_count,
    )

    return np.concatenate([np.arange(start, start + block_size) for start in starts])[:observations]


def compounded_outperformance(
    strategy_returns: Iterable[float],
    benchmark_returns: Iterable[float],
    annualization: int = 365,
    block_size: int = 21,
    repetitions: int = 5_000,
    seed: int = 20260730,
) -> dict[str, float | int | bool]:
    """Compare compounded growth using block-bootstrap log returns."""

    strategy = np.asarray(
        list(strategy_returns),
        dtype=float,
    )
    benchmark = np.asarray(
        list(benchmark_returns),
        dtype=float,
    )

    if strategy.shape != benchmark.shape:
        raise ValueError("Strategy and benchmark must be aligned")

    if strategy.size < block_size:
        raise ValueError("Series must contain at least one block")

    if annualization <= 0:
        raise ValueError("annualization must be positive")

    if block_size <= 0 or repetitions <= 0:
        raise ValueError("block_size and repetitions must be positive")

    if not (np.isfinite(strategy).all() and np.isfinite(benchmark).all()):
        raise ValueError("Return series must be finite")

    if np.any(strategy <= -1) or np.any(benchmark <= -1):
        raise ValueError("Returns must be greater than -100%")

    log_difference = np.log1p(strategy) - np.log1p(benchmark)
    observed_mean = float(log_difference.mean())

    rng = np.random.default_rng(seed)
    bootstrap_means = np.empty(repetitions)

    for index in range(repetitions):
        sample = _moving_block_indices(
            len(log_difference),
            block_size,
            rng,
        )
        bootstrap_means[index] = log_difference[sample].mean()

    ci_lower, ci_upper = np.quantile(
        bootstrap_means,
        [0.025, 0.975],
    )

    centered = log_difference - observed_mean
    null_rng = np.random.default_rng(seed + 10_000)
    null_means = np.empty(repetitions)

    for index in range(repetitions):
        sample = _moving_block_indices(
            len(centered),
            block_size,
            null_rng,
        )
        null_means[index] = centered[sample].mean()

    exceedances = int(np.count_nonzero(null_means >= observed_mean))
    p_value = (exceedances + 1) / (repetitions + 1)

    years = len(strategy) / annualization

    strategy_growth = float(np.prod(1.0 + strategy))
    benchmark_growth = float(np.prod(1.0 + benchmark))

    strategy_cagr = strategy_growth ** (1.0 / years) - 1.0
    benchmark_cagr = benchmark_growth ** (1.0 / years) - 1.0

    return {
        "observations": len(strategy),
        "strategy_cagr": float(strategy_cagr),
        "benchmark_cagr": float(benchmark_cagr),
        "cagr_difference": float(strategy_cagr - benchmark_cagr),
        "annualized_log_outperformance": float(observed_mean * annualization),
        "ci95_lower_annualized_log": float(ci_lower * annualization),
        "ci95_upper_annualized_log": float(ci_upper * annualization),
        "one_sided_p_value": float(p_value),
        "significant_at_5pct": bool(p_value < 0.05 and ci_lower > 0),
        "block_size": int(block_size),
        "repetitions": int(repetitions),
        "seed": int(seed),
    }
