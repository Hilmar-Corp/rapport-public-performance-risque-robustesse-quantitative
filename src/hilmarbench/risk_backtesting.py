"""Generic and deterministic VaR and Expected Shortfall backtesting."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal, TypeAlias

import numpy as np
from numpy.typing import NDArray
from scipy.stats import binomtest, chi2

VectorInput: TypeAlias = Sequence[float | int | bool] | NDArray[Any]


@dataclass(frozen=True)
class LikelihoodRatioTest:
    """Likelihood-ratio test result."""

    statistic: float
    p_value: float
    degrees_of_freedom: int
    observations: int


@dataclass(frozen=True)
class IndependenceTest:
    """Christoffersen independence-test result and transition counts."""

    statistic: float
    p_value: float
    degrees_of_freedom: int
    observations: int
    n00: int
    n01: int
    n10: int
    n11: int


@dataclass(frozen=True)
class ExceptionClusterSummary:
    """Descriptive clustering statistics for VaR exceptions."""

    exception_count: int
    cluster_count: int
    maximum_cluster_length: int
    mean_cluster_length: float
    minimum_gap_between_exceptions: int | None
    median_gap_between_exceptions: float | None
    maximum_gap_between_exceptions: int | None


@dataclass(frozen=True)
class ExpectedShortfallTest:
    """One-sided ES calibration test for risk underestimation."""

    statistic: float
    mean_tail_loss_to_es_ratio: float
    p_value_underestimation: float
    observations: int
    exceedances: int
    block_length: int
    bootstrap_repetitions: int


@dataclass(frozen=True)
class TrafficLightDecision:
    """Internal risk-model validation decision."""

    colour: Literal["GREEN", "AMBER", "RED"]
    reason_codes: tuple[str, ...]
    minimum_p_value: float
    expected_exception_count: float


def _exception_array(values: VectorInput) -> NDArray[np.bool_]:
    raw = np.asarray(values)

    if raw.ndim != 1:
        raise ValueError("exceptions must be one-dimensional")

    if raw.size == 0:
        raise ValueError("exceptions must not be empty")

    if raw.dtype == np.bool_:
        return raw.astype(np.bool_, copy=True)

    numeric = np.asarray(values, dtype=float)

    if not np.all(np.isfinite(numeric)):
        raise ValueError("exceptions must contain finite values")

    if not np.all((numeric == 0.0) | (numeric == 1.0)):
        raise ValueError("exceptions must contain only zero or one")

    return numeric.astype(np.bool_)


def _finite_vector(
    values: VectorInput,
    *,
    name: str,
) -> NDArray[np.float64]:
    vector = np.asarray(values, dtype=float)

    if vector.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional")

    if vector.size == 0:
        raise ValueError(f"{name} must not be empty")

    if not np.all(np.isfinite(vector)):
        raise ValueError(f"{name} must contain finite values")

    return vector.astype(np.float64, copy=False)


def _bernoulli_log_likelihood(
    successes: int,
    total: int,
    probability: float,
) -> float:
    if total < 0 or successes < 0 or successes > total:
        raise ValueError("invalid Bernoulli counts")

    if not 0.0 <= probability <= 1.0:
        raise ValueError("probability must be between zero and one")

    failures = total - successes

    if successes > 0 and probability == 0.0:
        return -math.inf

    if failures > 0 and probability == 1.0:
        return -math.inf

    success_term = successes * math.log(probability) if successes > 0 else 0.0
    failure_term = failures * math.log1p(-probability) if failures > 0 else 0.0

    return success_term + failure_term


def kupiec_unconditional_coverage(
    exceptions: VectorInput,
    expected_exception_probability: float,
) -> LikelihoodRatioTest:
    """Test whether the exception frequency equals the stated probability."""

    flags = _exception_array(exceptions)

    if not 0.0 < expected_exception_probability < 1.0:
        raise ValueError("expected_exception_probability must be strictly between zero and one")

    observations = int(flags.size)
    exception_count = int(flags.sum())
    empirical_probability = exception_count / observations

    null_log_likelihood = _bernoulli_log_likelihood(
        exception_count,
        observations,
        expected_exception_probability,
    )
    fitted_log_likelihood = _bernoulli_log_likelihood(
        exception_count,
        observations,
        empirical_probability,
    )

    statistic = max(
        0.0,
        2.0 * (fitted_log_likelihood - null_log_likelihood),
    )

    return LikelihoodRatioTest(
        statistic=float(statistic),
        p_value=float(chi2.sf(statistic, df=1)),
        degrees_of_freedom=1,
        observations=observations,
    )


def exact_binomial_coverage_p_value(
    exceptions: VectorInput,
    expected_exception_probability: float,
) -> float:
    """Return the exact two-sided binomial coverage p-value."""

    flags = _exception_array(exceptions)

    if not 0.0 < expected_exception_probability < 1.0:
        raise ValueError("expected_exception_probability must be strictly between zero and one")

    result = binomtest(
        int(flags.sum()),
        int(flags.size),
        expected_exception_probability,
        alternative="two-sided",
    )

    return float(result.pvalue)


def christoffersen_independence(
    exceptions: VectorInput,
) -> IndependenceTest:
    """Test first-order independence of consecutive exceptions."""

    flags = _exception_array(exceptions)

    if flags.size < 2:
        raise ValueError("at least two observations are required")

    previous = flags[:-1]
    current = flags[1:]

    n00 = int(np.sum((~previous) & (~current)))
    n01 = int(np.sum((~previous) & current))
    n10 = int(np.sum(previous & (~current)))
    n11 = int(np.sum(previous & current))

    total_transitions = n00 + n01 + n10 + n11
    total_exceptions = n01 + n11
    unconditional_probability = total_exceptions / total_transitions

    zero_origin_total = n00 + n01
    one_origin_total = n10 + n11

    zero_origin_probability = n01 / zero_origin_total if zero_origin_total else 0.0
    one_origin_probability = n11 / one_origin_total if one_origin_total else 0.0

    null_log_likelihood = _bernoulli_log_likelihood(
        total_exceptions,
        total_transitions,
        unconditional_probability,
    )

    alternative_log_likelihood = 0.0

    if zero_origin_total:
        alternative_log_likelihood += _bernoulli_log_likelihood(
            n01,
            zero_origin_total,
            zero_origin_probability,
        )

    if one_origin_total:
        alternative_log_likelihood += _bernoulli_log_likelihood(
            n11,
            one_origin_total,
            one_origin_probability,
        )

    statistic = max(
        0.0,
        2.0 * (alternative_log_likelihood - null_log_likelihood),
    )

    return IndependenceTest(
        statistic=float(statistic),
        p_value=float(chi2.sf(statistic, df=1)),
        degrees_of_freedom=1,
        observations=int(flags.size),
        n00=n00,
        n01=n01,
        n10=n10,
        n11=n11,
    )


def christoffersen_conditional_coverage(
    exceptions: VectorInput,
    expected_exception_probability: float,
) -> LikelihoodRatioTest:
    """Combine unconditional coverage and exception independence."""

    unconditional = kupiec_unconditional_coverage(
        exceptions,
        expected_exception_probability,
    )
    independence = christoffersen_independence(
        exceptions,
    )

    statistic = unconditional.statistic + independence.statistic

    return LikelihoodRatioTest(
        statistic=float(statistic),
        p_value=float(chi2.sf(statistic, df=2)),
        degrees_of_freedom=2,
        observations=unconditional.observations,
    )


def exception_cluster_summary(
    exceptions: VectorInput,
) -> ExceptionClusterSummary:
    """Describe contiguous exception clusters and inter-exception gaps."""

    flags = _exception_array(exceptions)
    exception_indices = np.flatnonzero(flags)

    cluster_lengths: list[int] = []
    current_length = 0

    for flag in flags:
        if flag:
            current_length += 1
        elif current_length:
            cluster_lengths.append(current_length)
            current_length = 0

    if current_length:
        cluster_lengths.append(current_length)

    if exception_indices.size >= 2:
        gaps = np.diff(exception_indices) - 1
        minimum_gap = int(np.min(gaps))
        median_gap = float(np.median(gaps))
        maximum_gap = int(np.max(gaps))
    else:
        minimum_gap = None
        median_gap = None
        maximum_gap = None

    return ExceptionClusterSummary(
        exception_count=int(exception_indices.size),
        cluster_count=len(cluster_lengths),
        maximum_cluster_length=(max(cluster_lengths) if cluster_lengths else 0),
        mean_cluster_length=(float(np.mean(cluster_lengths)) if cluster_lengths else 0.0),
        minimum_gap_between_exceptions=minimum_gap,
        median_gap_between_exceptions=median_gap,
        maximum_gap_between_exceptions=maximum_gap,
    )


def expected_shortfall_calibration_test(
    realized_losses: VectorInput,
    var_forecasts: VectorInput,
    expected_shortfall_forecasts: VectorInput,
    expected_exception_probability: float,
    *,
    block_length: int = 21,
    bootstrap_repetitions: int = 2_000,
    seed: int = 0,
) -> ExpectedShortfallTest:
    """Test whether realized tail losses systematically exceed ES forecasts.

    The statistic is the mean normalized tail loss minus one. Positive
    values indicate risk underestimation. A deterministic circular
    moving-block bootstrap provides the one-sided p-value.
    """

    losses = _finite_vector(
        realized_losses,
        name="realized_losses",
    )
    var_values = _finite_vector(
        var_forecasts,
        name="var_forecasts",
    )
    es_values = _finite_vector(
        expected_shortfall_forecasts,
        name="expected_shortfall_forecasts",
    )

    if not (losses.size == var_values.size == es_values.size):
        raise ValueError("losses, VaR forecasts and ES forecasts must have equal lengths")

    if not 0.0 < expected_exception_probability < 1.0:
        raise ValueError("expected_exception_probability must be strictly between zero and one")

    if np.any(var_values < 0.0):
        raise ValueError("VaR forecasts must be non-negative")

    if np.any(es_values <= 0.0):
        raise ValueError("ES forecasts must be strictly positive")

    if np.any(es_values < var_values):
        raise ValueError("ES forecasts must be greater than or equal to VaR")

    if block_length < 1 or block_length > losses.size:
        raise ValueError("block_length must be between one and the sample size")

    if bootstrap_repetitions < 99:
        raise ValueError("bootstrap_repetitions must be at least 99")

    exceedances = losses > var_values

    normalized_tail_losses = (
        losses * exceedances.astype(float) / (expected_exception_probability * es_values)
    )

    mean_ratio = float(np.mean(normalized_tail_losses))
    statistic = mean_ratio - 1.0

    centered = normalized_tail_losses - mean_ratio

    rng = np.random.default_rng(seed)
    bootstrap_statistics = np.empty(
        bootstrap_repetitions,
        dtype=float,
    )

    blocks_required = math.ceil(losses.size / block_length)
    offsets = np.arange(
        block_length,
        dtype=int,
    )

    for repetition in range(bootstrap_repetitions):
        starts = rng.integers(
            0,
            losses.size,
            size=blocks_required,
        )
        indices = (starts[:, None] + offsets[None, :]) % losses.size

        sample = centered[indices.reshape(-1)[: losses.size]]
        bootstrap_statistics[repetition] = float(np.mean(sample))

    p_value = (1.0 + float(np.sum(bootstrap_statistics >= statistic))) / (
        bootstrap_repetitions + 1.0
    )

    return ExpectedShortfallTest(
        statistic=float(statistic),
        mean_tail_loss_to_es_ratio=mean_ratio,
        p_value_underestimation=float(p_value),
        observations=int(losses.size),
        exceedances=int(exceedances.sum()),
        block_length=block_length,
        bootstrap_repetitions=bootstrap_repetitions,
    )


def validation_traffic_light(
    *,
    p_values: VectorInput,
    expected_exception_count: float,
    low_power_threshold: float = 5.0,
) -> TrafficLightDecision:
    """Map formal test results into a conservative internal decision."""

    values = _finite_vector(
        p_values,
        name="p_values",
    )

    if np.any((values < 0.0) | (values > 1.0)):
        raise ValueError("p_values must be between zero and one")

    if expected_exception_count < 0.0:
        raise ValueError("expected_exception_count must be non-negative")

    minimum_p_value = float(np.min(values))
    reasons: list[str] = []

    if minimum_p_value < 0.01:
        colour: Literal[
            "GREEN",
            "AMBER",
            "RED",
        ] = "RED"
        reasons.append("FORMAL_REJECTION_AT_1_PERCENT")
    elif minimum_p_value < 0.05:
        colour = "AMBER"
        reasons.append("FORMAL_REJECTION_AT_5_PERCENT")
    else:
        colour = "GREEN"
        reasons.append("NO_FORMAL_REJECTION_AT_5_PERCENT")

    if expected_exception_count < low_power_threshold:
        reasons.append("LOW_EXPECTED_EXCEPTION_COUNT")

        if colour == "GREEN":
            colour = "AMBER"

    return TrafficLightDecision(
        colour=colour,
        reason_codes=tuple(reasons),
        minimum_p_value=minimum_p_value,
        expected_exception_count=float(expected_exception_count),
    )
