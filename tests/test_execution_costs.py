from __future__ import annotations

import math

import pytest

from hilmarbench.execution import (
    ExecutionCostAssumptions,
    estimate_capacity_from_edge,
    estimate_execution_cost,
)


def assumptions() -> ExecutionCostAssumptions:
    return ExecutionCostAssumptions(
        fee_bps=2.0,
        half_spread_bps=3.0,
        slippage_bps=5.0,
        impact_coefficient_bps=8.0,
        impact_exponent=0.5,
        reference_participation_rate=0.01,
        reference_volatility=0.04,
        maximum_participation_rate=0.10,
    )


def test_fixed_cost_components_are_additive() -> None:
    config = assumptions()

    assert config.fixed_cost_bps == pytest.approx(10.0)


def test_zero_notional_has_zero_execution_cost() -> None:
    estimate = estimate_execution_cost(
        order_notional=0.0,
        daily_volume_notional=100_000_000.0,
        daily_volatility=0.04,
        assumptions=assumptions(),
    )

    assert estimate.participation_rate == 0.0
    assert estimate.total_cost_bps == 0.0
    assert estimate.total_cost_notional == 0.0
    assert estimate.within_participation_limit


def test_execution_cost_decomposition() -> None:
    estimate = estimate_execution_cost(
        order_notional=1_000_000.0,
        daily_volume_notional=100_000_000.0,
        daily_volatility=0.04,
        assumptions=assumptions(),
    )

    assert estimate.participation_rate == pytest.approx(0.01)
    assert estimate.fee_bps == pytest.approx(2.0)
    assert estimate.spread_bps == pytest.approx(3.0)
    assert estimate.slippage_bps == pytest.approx(5.0)
    assert estimate.market_impact_bps == pytest.approx(8.0)
    assert estimate.total_cost_bps == pytest.approx(18.0)
    assert estimate.total_cost_notional == pytest.approx(1_800.0)


def test_square_root_impact_scales_with_notional() -> None:
    low = estimate_execution_cost(
        order_notional=1_000_000.0,
        daily_volume_notional=100_000_000.0,
        daily_volatility=0.04,
        assumptions=assumptions(),
    )

    high = estimate_execution_cost(
        order_notional=4_000_000.0,
        daily_volume_notional=100_000_000.0,
        daily_volatility=0.04,
        assumptions=assumptions(),
    )

    assert high.market_impact_bps == pytest.approx(2.0 * low.market_impact_bps)


def test_impact_is_monotonic_in_volatility() -> None:
    low = estimate_execution_cost(
        order_notional=1_000_000.0,
        daily_volume_notional=100_000_000.0,
        daily_volatility=0.02,
        assumptions=assumptions(),
    )

    high = estimate_execution_cost(
        order_notional=1_000_000.0,
        daily_volume_notional=100_000_000.0,
        daily_volatility=0.08,
        assumptions=assumptions(),
    )

    assert high.market_impact_bps > low.market_impact_bps


def test_participation_limit_is_reported() -> None:
    estimate = estimate_execution_cost(
        order_notional=20_000_000.0,
        daily_volume_notional=100_000_000.0,
        daily_volatility=0.04,
        assumptions=assumptions(),
    )

    assert estimate.participation_rate == pytest.approx(0.20)
    assert not estimate.within_participation_limit


def test_capacity_is_zero_when_edge_does_not_cover_fixed_cost() -> None:
    capacity = estimate_capacity_from_edge(
        expected_gross_edge_bps=9.0,
        daily_volume_notional=100_000_000.0,
        daily_volatility=0.04,
        assumptions=assumptions(),
    )

    assert capacity.maximum_notional == 0.0
    assert capacity.binding_constraint == "fixed_cost"
    assert capacity.residual_edge_bps == pytest.approx(-1.0)


def test_capacity_can_be_bound_by_expected_edge() -> None:
    capacity = estimate_capacity_from_edge(
        expected_gross_edge_bps=18.0,
        daily_volume_notional=100_000_000.0,
        daily_volatility=0.04,
        assumptions=assumptions(),
    )

    assert capacity.maximum_notional == pytest.approx(1_000_000.0)
    assert capacity.participation_rate == pytest.approx(0.01)
    assert capacity.estimated_cost_bps == pytest.approx(18.0)
    assert capacity.residual_edge_bps == pytest.approx(0.0)
    assert capacity.binding_constraint == "expected_edge"


def test_capacity_can_be_bound_by_participation_limit() -> None:
    capacity = estimate_capacity_from_edge(
        expected_gross_edge_bps=1_000.0,
        daily_volume_notional=100_000_000.0,
        daily_volatility=0.04,
        assumptions=assumptions(),
    )

    assert capacity.maximum_notional == pytest.approx(10_000_000.0)
    assert capacity.participation_rate == pytest.approx(0.10)
    assert capacity.binding_constraint == "participation_limit"
    assert capacity.residual_edge_bps > 0.0


def test_zero_impact_model_is_participation_bound() -> None:
    config = ExecutionCostAssumptions(
        fee_bps=2.0,
        half_spread_bps=3.0,
        slippage_bps=5.0,
        impact_coefficient_bps=0.0,
        maximum_participation_rate=0.05,
    )

    capacity = estimate_capacity_from_edge(
        expected_gross_edge_bps=20.0,
        daily_volume_notional=200_000_000.0,
        daily_volatility=0.04,
        assumptions=config,
    )

    assert capacity.maximum_notional == pytest.approx(10_000_000.0)
    assert capacity.estimated_cost_bps == pytest.approx(10.0)
    assert capacity.binding_constraint == "participation_limit"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("fee_bps", -1.0),
        ("half_spread_bps", math.inf),
        ("slippage_bps", math.nan),
        ("impact_coefficient_bps", -1.0),
        ("impact_exponent", 0.0),
        ("reference_participation_rate", 0.0),
        ("reference_volatility", 0.0),
        ("maximum_participation_rate", 1.01),
    ],
)
def test_invalid_assumptions_are_rejected(
    field: str,
    value: float,
) -> None:
    kwargs = {
        "fee_bps": 0.0,
        "half_spread_bps": 0.0,
        "slippage_bps": 0.0,
        "impact_coefficient_bps": 0.0,
        "impact_exponent": 0.5,
        "reference_participation_rate": 0.01,
        "reference_volatility": 0.04,
        "maximum_participation_rate": 0.10,
    }
    kwargs[field] = value

    with pytest.raises(ValueError):
        ExecutionCostAssumptions(**kwargs)


@pytest.mark.parametrize(
    ("order_notional", "daily_volume", "volatility"),
    [
        (-1.0, 100.0, 0.04),
        (1.0, 0.0, 0.04),
        (1.0, 100.0, -0.01),
        (math.inf, 100.0, 0.04),
    ],
)
def test_invalid_execution_inputs_are_rejected(
    order_notional: float,
    daily_volume: float,
    volatility: float,
) -> None:
    with pytest.raises(ValueError):
        estimate_execution_cost(
            order_notional=order_notional,
            daily_volume_notional=daily_volume,
            daily_volatility=volatility,
            assumptions=assumptions(),
        )
