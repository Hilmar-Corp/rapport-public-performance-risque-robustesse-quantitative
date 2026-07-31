"""Generic execution-cost, market-impact and capacity models."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, replace
from itertools import product
from typing import Literal

import pandas as pd

CapacityConstraint = Literal[
    "fixed_cost",
    "expected_edge",
    "participation_limit",
]


def _require_finite_non_negative(
    value: float,
    *,
    name: str,
) -> None:
    if not math.isfinite(value) or value < 0.0:
        raise ValueError(f"{name} must be finite and non-negative.")


def _require_finite_positive(
    value: float,
    *,
    name: str,
) -> None:
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError(f"{name} must be finite and positive.")


@dataclass(frozen=True)
class ExecutionCostAssumptions:
    """Calibrable assumptions for a generic execution-cost model.

    All cost inputs are expressed in basis points. Volatility is expressed
    as a decimal daily volatility, and participation rates are fractions of
    daily traded notional.
    """

    fee_bps: float = 0.0
    half_spread_bps: float = 0.0
    slippage_bps: float = 0.0
    impact_coefficient_bps: float = 0.0
    impact_exponent: float = 0.5
    reference_participation_rate: float = 0.01
    reference_volatility: float = 0.04
    maximum_participation_rate: float = 0.10

    def __post_init__(self) -> None:
        for name in (
            "fee_bps",
            "half_spread_bps",
            "slippage_bps",
            "impact_coefficient_bps",
        ):
            _require_finite_non_negative(
                float(getattr(self, name)),
                name=name,
            )

        _require_finite_positive(
            self.impact_exponent,
            name="impact_exponent",
        )
        _require_finite_positive(
            self.reference_participation_rate,
            name="reference_participation_rate",
        )
        _require_finite_positive(
            self.reference_volatility,
            name="reference_volatility",
        )
        _require_finite_positive(
            self.maximum_participation_rate,
            name="maximum_participation_rate",
        )

        if self.maximum_participation_rate > 1.0:
            raise ValueError("maximum_participation_rate cannot exceed 1.0.")

    @property
    def fixed_cost_bps(self) -> float:
        """Return fee, spread and slippage costs before market impact."""

        return self.fee_bps + self.half_spread_bps + self.slippage_bps


@dataclass(frozen=True)
class ExecutionCostEstimate:
    """Cost decomposition for one hypothetical order."""

    order_notional: float
    daily_volume_notional: float
    participation_rate: float
    fee_bps: float
    spread_bps: float
    slippage_bps: float
    market_impact_bps: float
    total_cost_bps: float
    total_cost_notional: float
    within_participation_limit: bool


@dataclass(frozen=True)
class CapacityEstimate:
    """Economic capacity implied by edge and participation constraints."""

    expected_gross_edge_bps: float
    maximum_notional: float
    participation_rate: float
    estimated_cost_bps: float
    residual_edge_bps: float
    binding_constraint: CapacityConstraint


def estimate_execution_cost(
    *,
    order_notional: float,
    daily_volume_notional: float,
    daily_volatility: float,
    assumptions: ExecutionCostAssumptions,
) -> ExecutionCostEstimate:
    """Estimate implementation cost for a hypothetical order.

    Market impact follows a configurable power law:

        coefficient
        x (participation / reference participation) ** exponent
        x (volatility / reference volatility)

    The default exponent of 0.5 corresponds to a square-root impact model.
    """

    _require_finite_non_negative(
        order_notional,
        name="order_notional",
    )
    _require_finite_positive(
        daily_volume_notional,
        name="daily_volume_notional",
    )
    _require_finite_non_negative(
        daily_volatility,
        name="daily_volatility",
    )

    if order_notional == 0.0:
        return ExecutionCostEstimate(
            order_notional=0.0,
            daily_volume_notional=daily_volume_notional,
            participation_rate=0.0,
            fee_bps=0.0,
            spread_bps=0.0,
            slippage_bps=0.0,
            market_impact_bps=0.0,
            total_cost_bps=0.0,
            total_cost_notional=0.0,
            within_participation_limit=True,
        )

    participation_rate = order_notional / daily_volume_notional

    participation_scale = (
        participation_rate / assumptions.reference_participation_rate
    ) ** assumptions.impact_exponent

    volatility_scale = daily_volatility / assumptions.reference_volatility

    market_impact_bps = assumptions.impact_coefficient_bps * participation_scale * volatility_scale

    total_cost_bps = assumptions.fixed_cost_bps + market_impact_bps

    total_cost_notional = order_notional * total_cost_bps / 10_000.0

    return ExecutionCostEstimate(
        order_notional=order_notional,
        daily_volume_notional=daily_volume_notional,
        participation_rate=participation_rate,
        fee_bps=assumptions.fee_bps,
        spread_bps=assumptions.half_spread_bps,
        slippage_bps=assumptions.slippage_bps,
        market_impact_bps=market_impact_bps,
        total_cost_bps=total_cost_bps,
        total_cost_notional=total_cost_notional,
        within_participation_limit=(participation_rate <= assumptions.maximum_participation_rate),
    )


def estimate_capacity_from_edge(
    *,
    expected_gross_edge_bps: float,
    daily_volume_notional: float,
    daily_volatility: float,
    assumptions: ExecutionCostAssumptions,
) -> CapacityEstimate:
    """Estimate break-even notional under cost and participation limits."""

    _require_finite_non_negative(
        expected_gross_edge_bps,
        name="expected_gross_edge_bps",
    )
    _require_finite_positive(
        daily_volume_notional,
        name="daily_volume_notional",
    )
    _require_finite_non_negative(
        daily_volatility,
        name="daily_volatility",
    )

    fixed_cost_bps = assumptions.fixed_cost_bps

    if expected_gross_edge_bps <= fixed_cost_bps:
        return CapacityEstimate(
            expected_gross_edge_bps=(expected_gross_edge_bps),
            maximum_notional=0.0,
            participation_rate=0.0,
            estimated_cost_bps=fixed_cost_bps,
            residual_edge_bps=(expected_gross_edge_bps - fixed_cost_bps),
            binding_constraint="fixed_cost",
        )

    impact_scale = (
        assumptions.impact_coefficient_bps * daily_volatility / assumptions.reference_volatility
    )

    if impact_scale == 0.0:
        edge_participation_rate = math.inf
    else:
        available_impact_budget = expected_gross_edge_bps - fixed_cost_bps

        edge_participation_rate = assumptions.reference_participation_rate * (
            available_impact_budget / impact_scale
        ) ** (1.0 / assumptions.impact_exponent)

    participation_rate = min(
        edge_participation_rate,
        assumptions.maximum_participation_rate,
    )

    maximum_notional = participation_rate * daily_volume_notional

    estimate = estimate_execution_cost(
        order_notional=maximum_notional,
        daily_volume_notional=daily_volume_notional,
        daily_volatility=daily_volatility,
        assumptions=assumptions,
    )

    binding_constraint: CapacityConstraint = (
        "expected_edge"
        if edge_participation_rate <= assumptions.maximum_participation_rate
        else "participation_limit"
    )

    return CapacityEstimate(
        expected_gross_edge_bps=expected_gross_edge_bps,
        maximum_notional=maximum_notional,
        participation_rate=participation_rate,
        estimated_cost_bps=estimate.total_cost_bps,
        residual_edge_bps=(expected_gross_edge_bps - estimate.total_cost_bps),
        binding_constraint=binding_constraint,
    )


def build_execution_scenario_surface(
    *,
    order_notionals: Sequence[float],
    daily_volume_notionals: Sequence[float],
    daily_volatilities: Sequence[float],
    slippage_bps_values: Sequence[float],
    assumptions: ExecutionCostAssumptions,
) -> pd.DataFrame:
    """Build a deterministic synthetic execution-cost scenario surface.

    The function varies order notional, traded volume, daily volatility and
    slippage while preserving all other assumptions. It does not use client,
    broker, venue or proprietary Nostra data.
    """

    grids = {
        "order_notionals": tuple(order_notionals),
        "daily_volume_notionals": tuple(daily_volume_notionals),
        "daily_volatilities": tuple(daily_volatilities),
        "slippage_bps_values": tuple(slippage_bps_values),
    }

    for name, values in grids.items():
        if not values:
            raise ValueError(f"{name} must contain at least one value.")

    rows: list[dict[str, float | bool]] = []

    for (
        order_notional,
        daily_volume_notional,
        daily_volatility,
        slippage_bps,
    ) in product(
        grids["order_notionals"],
        grids["daily_volume_notionals"],
        grids["daily_volatilities"],
        grids["slippage_bps_values"],
    ):
        scenario_assumptions = replace(
            assumptions,
            slippage_bps=float(slippage_bps),
        )

        estimate = estimate_execution_cost(
            order_notional=float(order_notional),
            daily_volume_notional=float(daily_volume_notional),
            daily_volatility=float(daily_volatility),
            assumptions=scenario_assumptions,
        )

        rows.append(
            {
                "order_notional": estimate.order_notional,
                "daily_volume_notional": (estimate.daily_volume_notional),
                "daily_volatility": float(daily_volatility),
                "participation_rate": (estimate.participation_rate),
                "fee_bps": estimate.fee_bps,
                "spread_bps": estimate.spread_bps,
                "slippage_bps": estimate.slippage_bps,
                "market_impact_bps": (estimate.market_impact_bps),
                "total_cost_bps": estimate.total_cost_bps,
                "total_cost_notional": (estimate.total_cost_notional),
                "within_participation_limit": (estimate.within_participation_limit),
            }
        )

    frame = pd.DataFrame(rows)

    return frame.sort_values(
        [
            "daily_volume_notional",
            "daily_volatility",
            "order_notional",
            "slippage_bps",
        ],
        kind="stable",
        ignore_index=True,
    )
