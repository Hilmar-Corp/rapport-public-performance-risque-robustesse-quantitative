"""Historical drawdown-threshold and allocation-reaction analysis."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, TypeAlias

import numpy as np
from numpy.typing import NDArray

VectorInput: TypeAlias = Sequence[float | int] | NDArray[Any]


@dataclass(frozen=True)
class DrawdownEpisode:
    """One continuous historical drawdown episode."""

    episode_number: int
    peak_index: int
    start_index: int
    trough_index: int
    end_index: int
    recovery_index: int | None
    recovered_in_sample: bool
    maximum_drawdown: float


@dataclass(frozen=True)
class HistoricalThresholdBreach:
    """First breach of one loss threshold within one drawdown episode."""

    episode_number: int
    target_nav_loss: float
    peak_index: int
    breach_index: int
    observations_to_breach: int
    drawdown_at_breach: float
    allocation_at_peak: float
    allocation_at_breach: float
    allocation_change: float
    reaction_classification: str
    observations_to_fractional_reduction: int | None


def _finite_vector(
    values: VectorInput,
    *,
    name: str,
) -> NDArray[np.float64]:
    array = np.asarray(
        values,
        dtype=np.float64,
    )

    if array.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional.")

    if array.size == 0:
        raise ValueError(f"{name} must not be empty.")

    if not np.isfinite(array).all():
        raise ValueError(f"{name} must contain only finite values.")

    return array


def _validate_equal_lengths(
    arrays: Sequence[NDArray[np.float64]],
) -> None:
    lengths = {int(array.size) for array in arrays}

    if len(lengths) != 1:
        raise ValueError("Input vectors must have equal lengths.")


def _validate_probability(
    value: float,
    *,
    name: str,
) -> float:
    number = float(value)

    if not math.isfinite(number) or not 0.0 < number < 1.0:
        raise ValueError(f"{name} must be strictly between zero and one.")

    return number


def row_aligned_net_returns(
    asset_returns: VectorInput,
    allocations: VectorInput,
    turnover: VectorInput,
    *,
    cost_rate: float,
) -> NDArray[np.float64]:
    """Apply the allocation economically aligned with each return row."""

    returns = _finite_vector(
        asset_returns,
        name="asset_returns",
    )
    controlled_allocations = _finite_vector(
        allocations,
        name="allocations",
    )
    controlled_turnover = _finite_vector(
        turnover,
        name="turnover",
    )

    _validate_equal_lengths(
        (
            returns,
            controlled_allocations,
            controlled_turnover,
        )
    )

    controlled_cost_rate = float(cost_rate)

    if not math.isfinite(controlled_cost_rate) or controlled_cost_rate < 0.0:
        raise ValueError("cost_rate must be finite and non-negative.")

    if np.any(controlled_turnover < 0.0):
        raise ValueError("turnover must be non-negative.")

    return controlled_allocations * returns - controlled_cost_rate * controlled_turnover


def equity_curve(
    periodic_returns: VectorInput,
) -> NDArray[np.float64]:
    """Return compounded equity beginning with the first observation."""

    returns = _finite_vector(
        periodic_returns,
        name="periodic_returns",
    )

    if np.any(returns <= -1.0):
        raise ValueError("periodic_returns must be greater than minus one.")

    return np.cumprod(1.0 + returns)


def drawdown_series(
    periodic_returns: VectorInput,
) -> NDArray[np.float64]:
    """Return the drawdown series from compounded periodic returns."""

    equity = equity_curve(periodic_returns)
    running_peak = np.maximum.accumulate(equity)

    return equity / running_peak - 1.0


def identify_drawdown_episodes(
    periodic_returns: VectorInput,
    *,
    tolerance: float = 1e-12,
) -> tuple[DrawdownEpisode, ...]:
    """Identify continuous below-peak intervals and their troughs."""

    controlled_tolerance = float(tolerance)

    if not math.isfinite(controlled_tolerance) or controlled_tolerance < 0.0:
        raise ValueError("tolerance must be finite and non-negative.")

    drawdowns = drawdown_series(periodic_returns)

    episodes: list[DrawdownEpisode] = []

    index = 0
    episode_number = 0

    while index < drawdowns.size:
        if drawdowns[index] >= -controlled_tolerance:
            index += 1
            continue

        start_index = index
        peak_index = max(
            0,
            start_index - 1,
        )

        while index + 1 < drawdowns.size and drawdowns[index + 1] < -controlled_tolerance:
            index += 1

        end_index = index

        local_drawdowns = drawdowns[peak_index : end_index + 1]

        trough_index = peak_index + int(np.argmin(local_drawdowns))

        recovered = bool(
            end_index + 1 < drawdowns.size and drawdowns[end_index + 1] >= -controlled_tolerance
        )

        recovery_index = end_index + 1 if recovered else None

        episode_number += 1

        episodes.append(
            DrawdownEpisode(
                episode_number=episode_number,
                peak_index=peak_index,
                start_index=start_index,
                trough_index=trough_index,
                end_index=end_index,
                recovery_index=recovery_index,
                recovered_in_sample=recovered,
                maximum_drawdown=float(drawdowns[trough_index]),
            )
        )

        index += 1

    return tuple(episodes)


def historical_threshold_breaches(
    periodic_returns: VectorInput,
    allocations: VectorInput,
    *,
    loss_thresholds: Sequence[float],
    reduction_fraction: float = 0.25,
    tolerance: float = 1e-12,
) -> tuple[
    HistoricalThresholdBreach,
    ...,
]:
    """Find the first historical breach of each threshold per episode."""

    returns = _finite_vector(
        periodic_returns,
        name="periodic_returns",
    )
    controlled_allocations = _finite_vector(
        allocations,
        name="allocations",
    )

    _validate_equal_lengths(
        (
            returns,
            controlled_allocations,
        )
    )

    thresholds = tuple(
        sorted(
            {
                _validate_probability(
                    threshold,
                    name="loss threshold",
                )
                for threshold in loss_thresholds
            }
        )
    )

    if not thresholds:
        raise ValueError("loss_thresholds must not be empty.")

    controlled_reduction_fraction = _validate_probability(
        reduction_fraction,
        name="reduction_fraction",
    )

    controlled_tolerance = float(tolerance)

    if not math.isfinite(controlled_tolerance) or controlled_tolerance < 0.0:
        raise ValueError("tolerance must be finite and non-negative.")

    drawdowns = drawdown_series(returns)
    episodes = identify_drawdown_episodes(
        returns,
        tolerance=controlled_tolerance,
    )

    breaches: list[HistoricalThresholdBreach] = []

    for episode in episodes:
        for threshold in thresholds:
            relative_candidates = np.flatnonzero(
                drawdowns[episode.peak_index : episode.end_index + 1] <= -threshold
            )

            if relative_candidates.size == 0:
                continue

            breach_index = episode.peak_index + int(relative_candidates[0])

            if breach_index <= episode.peak_index:
                continue

            allocation_at_peak = float(controlled_allocations[episode.peak_index])
            allocation_at_breach = float(controlled_allocations[breach_index])
            allocation_change = allocation_at_breach - allocation_at_peak

            if allocation_change < -controlled_tolerance:
                reaction = "ALLOCATION_REDUCED"
            elif allocation_change > controlled_tolerance:
                reaction = "ALLOCATION_INCREASED"
            else:
                reaction = "ALLOCATION_UNCHANGED"

            reduction_delay: int | None = None

            if allocation_at_peak > 0.0:
                reduction_level = allocation_at_peak * (1.0 - controlled_reduction_fraction)

                allocation_path = controlled_allocations[episode.peak_index + 1 : breach_index + 1]

                reduction_candidates = np.flatnonzero(allocation_path <= reduction_level)

                if reduction_candidates.size:
                    reduction_delay = int(reduction_candidates[0]) + 1

            breaches.append(
                HistoricalThresholdBreach(
                    episode_number=(episode.episode_number),
                    target_nav_loss=threshold,
                    peak_index=(episode.peak_index),
                    breach_index=breach_index,
                    observations_to_breach=(breach_index - episode.peak_index),
                    drawdown_at_breach=float(drawdowns[breach_index]),
                    allocation_at_peak=(allocation_at_peak),
                    allocation_at_breach=(allocation_at_breach),
                    allocation_change=(allocation_change),
                    reaction_classification=(reaction),
                    observations_to_fractional_reduction=(reduction_delay),
                )
            )

    return tuple(breaches)
