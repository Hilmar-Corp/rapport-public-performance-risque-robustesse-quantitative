from __future__ import annotations

import math

import numpy as np
import pytest

from hilmarbench.historical_reverse_stress import (
    drawdown_series,
    equity_curve,
    historical_threshold_breaches,
    identify_drawdown_episodes,
    row_aligned_net_returns,
)


def test_row_aligned_net_returns_reconciles_costed_returns() -> None:
    result = row_aligned_net_returns(
        [0.10, -0.20, 0.05],
        [0.50, 0.25, -0.10],
        [0.00, 0.25, 0.35],
        cost_rate=0.0025,
    )

    expected = np.array(
        [
            0.050000,
            -0.050625,
            -0.005875,
        ]
    )

    assert result == pytest.approx(expected)


def test_equity_and_drawdown_series() -> None:
    returns = [
        0.10,
        -0.10,
        -0.10,
        0.25,
    ]

    equity = equity_curve(returns)
    drawdowns = drawdown_series(returns)

    assert equity == pytest.approx(
        [
            1.10,
            0.99,
            0.891,
            1.11375,
        ]
    )

    assert drawdowns == pytest.approx(
        [
            0.0,
            -0.10,
            -0.19,
            0.0,
        ]
    )


def test_identify_drawdown_episodes() -> None:
    episodes = identify_drawdown_episodes(
        [
            0.10,
            -0.10,
            -0.10,
            0.25,
            -0.05,
        ]
    )

    assert len(episodes) == 2

    first = episodes[0]

    assert first.episode_number == 1
    assert first.peak_index == 0
    assert first.start_index == 1
    assert first.trough_index == 2
    assert first.end_index == 2
    assert first.recovery_index == 3
    assert first.recovered_in_sample
    assert first.maximum_drawdown == pytest.approx(-0.19)

    second = episodes[1]

    assert second.episode_number == 2
    assert second.peak_index == 3
    assert second.start_index == 4
    assert second.trough_index == 4
    assert second.end_index == 4
    assert second.recovery_index is None
    assert not second.recovered_in_sample


def test_threshold_breaches_are_nested_and_use_first_breach() -> None:
    breaches = historical_threshold_breaches(
        [
            0.10,
            -0.06,
            -0.06,
            -0.06,
            0.30,
        ],
        [
            0.80,
            0.80,
            0.60,
            0.40,
            0.40,
        ],
        loss_thresholds=[
            0.05,
            0.10,
            0.15,
        ],
    )

    assert [breach.target_nav_loss for breach in breaches] == pytest.approx(
        [
            0.05,
            0.10,
            0.15,
        ]
    )

    assert [breach.observations_to_breach for breach in breaches] == [
        1,
        2,
        3,
    ]


def test_threshold_breach_records_allocation_reaction() -> None:
    breaches = historical_threshold_breaches(
        [
            0.10,
            -0.06,
            -0.06,
            -0.06,
            0.30,
        ],
        [
            0.80,
            0.80,
            0.60,
            0.40,
            0.40,
        ],
        loss_thresholds=[
            0.10,
            0.15,
        ],
        reduction_fraction=0.25,
    )

    ten_percent = breaches[0]
    fifteen_percent = breaches[1]

    assert ten_percent.reaction_classification == "ALLOCATION_REDUCED"
    assert ten_percent.allocation_at_peak == 0.80
    assert ten_percent.allocation_at_breach == 0.60
    assert ten_percent.allocation_change == pytest.approx(-0.20)
    assert ten_percent.observations_to_fractional_reduction == 2

    assert fifteen_percent.reaction_classification == "ALLOCATION_REDUCED"
    assert fifteen_percent.allocation_at_breach == 0.40
    assert fifteen_percent.observations_to_fractional_reduction == 2


def test_unchanged_and_increased_reactions() -> None:
    unchanged = historical_threshold_breaches(
        [0.10, -0.10],
        [0.50, 0.50],
        loss_thresholds=[0.05],
    )

    increased = historical_threshold_breaches(
        [0.10, -0.10],
        [0.50, 0.70],
        loss_thresholds=[0.05],
    )

    assert unchanged[0].reaction_classification == "ALLOCATION_UNCHANGED"
    assert increased[0].reaction_classification == "ALLOCATION_INCREASED"


def test_unreached_threshold_is_not_returned() -> None:
    breaches = historical_threshold_breaches(
        [0.10, -0.02, 0.03],
        [0.50, 0.50, 0.50],
        loss_thresholds=[
            0.05,
            0.10,
        ],
    )

    assert breaches == ()


@pytest.mark.parametrize(
    "invalid_returns",
    [
        [],
        [0.10, math.nan],
        [[0.10, -0.10]],
    ],
)
def test_invalid_return_vectors_are_rejected(
    invalid_returns: object,
) -> None:
    with pytest.raises(
        ValueError,
    ):
        drawdown_series(
            invalid_returns  # type: ignore[arg-type]
        )


def test_mismatched_lengths_are_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="equal lengths",
    ):
        row_aligned_net_returns(
            [0.10, -0.10],
            [0.50],
            [0.00, 0.10],
            cost_rate=0.0025,
        )


@pytest.mark.parametrize(
    "cost_rate",
    [
        -0.01,
        math.inf,
    ],
)
def test_invalid_cost_rate_is_rejected(
    cost_rate: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="cost_rate",
    ):
        row_aligned_net_returns(
            [0.10],
            [0.50],
            [0.00],
            cost_rate=cost_rate,
        )


@pytest.mark.parametrize(
    "thresholds",
    [
        [],
        [0.0],
        [1.0],
        [-0.10],
    ],
)
def test_invalid_thresholds_are_rejected(
    thresholds: list[float],
) -> None:
    with pytest.raises(
        ValueError,
    ):
        historical_threshold_breaches(
            [0.10, -0.10],
            [0.50, 0.50],
            loss_thresholds=thresholds,
        )


def test_negative_turnover_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="turnover",
    ):
        row_aligned_net_returns(
            [0.10],
            [0.50],
            [-0.10],
            cost_rate=0.0025,
        )


@pytest.mark.parametrize(
    "periodic_return",
    [
        -1.0,
        -1.20,
    ],
)
def test_total_loss_or_worse_is_rejected(
    periodic_return: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="greater than minus one",
    ):
        equity_curve([periodic_return])


@pytest.mark.parametrize(
    "tolerance",
    [
        -1e-6,
        math.inf,
    ],
)
def test_invalid_episode_tolerance_is_rejected(
    tolerance: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="tolerance",
    ):
        identify_drawdown_episodes(
            [0.10, -0.10],
            tolerance=tolerance,
        )


def test_breach_input_length_mismatch_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="equal lengths",
    ):
        historical_threshold_breaches(
            [0.10, -0.10],
            [0.50],
            loss_thresholds=[0.05],
        )


@pytest.mark.parametrize(
    "reduction_fraction",
    [
        0.0,
        1.0,
        -0.10,
        math.inf,
    ],
)
def test_invalid_reduction_fraction_is_rejected(
    reduction_fraction: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="reduction_fraction",
    ):
        historical_threshold_breaches(
            [0.10, -0.10],
            [0.50, 0.40],
            loss_thresholds=[0.05],
            reduction_fraction=reduction_fraction,
        )


@pytest.mark.parametrize(
    "tolerance",
    [
        -1e-6,
        math.inf,
    ],
)
def test_invalid_breach_tolerance_is_rejected(
    tolerance: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="tolerance",
    ):
        historical_threshold_breaches(
            [0.10, -0.10],
            [0.50, 0.40],
            loss_thresholds=[0.05],
            tolerance=tolerance,
        )


def test_duplicate_loss_levels_are_deduplicated() -> None:
    breaches = historical_threshold_breaches(
        [0.10, -0.10],
        [0.0, -0.10],
        loss_thresholds=[
            0.05,
            0.05,
        ],
    )

    assert len(breaches) == 1
    assert breaches[0].observations_to_fractional_reduction is None
