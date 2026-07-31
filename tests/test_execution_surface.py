from __future__ import annotations

import pandas as pd
import pytest

from hilmarbench.execution import (
    ExecutionCostAssumptions,
    build_execution_scenario_surface,
)


def assumptions() -> ExecutionCostAssumptions:
    return ExecutionCostAssumptions(
        fee_bps=2.0,
        half_spread_bps=3.0,
        slippage_bps=0.0,
        impact_coefficient_bps=8.0,
        impact_exponent=0.5,
        reference_participation_rate=0.01,
        reference_volatility=0.04,
        maximum_participation_rate=0.10,
    )


def test_surface_contains_cartesian_product() -> None:
    surface = build_execution_scenario_surface(
        order_notionals=[
            1_000_000.0,
            4_000_000.0,
        ],
        daily_volume_notionals=[
            100_000_000.0,
        ],
        daily_volatilities=[
            0.02,
            0.04,
        ],
        slippage_bps_values=[
            0.0,
            5.0,
            10.0,
        ],
        assumptions=assumptions(),
    )

    assert len(surface) == 12
    assert list(surface.columns) == [
        "order_notional",
        "daily_volume_notional",
        "daily_volatility",
        "participation_rate",
        "fee_bps",
        "spread_bps",
        "slippage_bps",
        "market_impact_bps",
        "total_cost_bps",
        "total_cost_notional",
        "within_participation_limit",
    ]


def test_surface_is_deterministic() -> None:
    kwargs = {
        "order_notionals": [
            4_000_000.0,
            1_000_000.0,
        ],
        "daily_volume_notionals": [
            100_000_000.0,
        ],
        "daily_volatilities": [
            0.04,
        ],
        "slippage_bps_values": [
            10.0,
            0.0,
            5.0,
        ],
        "assumptions": assumptions(),
    }

    first = build_execution_scenario_surface(
        **kwargs,
    )
    second = build_execution_scenario_surface(
        **kwargs,
    )

    pd.testing.assert_frame_equal(
        first,
        second,
    )


def test_total_cost_is_monotonic_in_slippage() -> None:
    surface = build_execution_scenario_surface(
        order_notionals=[
            1_000_000.0,
        ],
        daily_volume_notionals=[
            100_000_000.0,
        ],
        daily_volatilities=[
            0.04,
        ],
        slippage_bps_values=[
            0.0,
            5.0,
            10.0,
            25.0,
        ],
        assumptions=assumptions(),
    )

    assert surface["total_cost_bps"].is_monotonic_increasing


def test_market_impact_is_monotonic_in_order_notional() -> None:
    surface = build_execution_scenario_surface(
        order_notionals=[
            1_000_000.0,
            4_000_000.0,
            9_000_000.0,
        ],
        daily_volume_notionals=[
            100_000_000.0,
        ],
        daily_volatilities=[
            0.04,
        ],
        slippage_bps_values=[
            5.0,
        ],
        assumptions=assumptions(),
    )

    assert surface["market_impact_bps"].is_monotonic_increasing


@pytest.mark.parametrize(
    "field",
    [
        "order_notionals",
        "daily_volume_notionals",
        "daily_volatilities",
        "slippage_bps_values",
    ],
)
def test_empty_surface_grid_is_rejected(
    field: str,
) -> None:
    kwargs = {
        "order_notionals": [
            1_000_000.0,
        ],
        "daily_volume_notionals": [
            100_000_000.0,
        ],
        "daily_volatilities": [
            0.04,
        ],
        "slippage_bps_values": [
            5.0,
        ],
        "assumptions": assumptions(),
    }

    kwargs[field] = []

    with pytest.raises(
        ValueError,
        match=field,
    ):
        build_execution_scenario_surface(
            **kwargs,
        )
