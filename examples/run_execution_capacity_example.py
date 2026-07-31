"""Synthetic execution-cost and capacity example.

The numerical assumptions are illustrative only. They do not represent
Nostra AI, a client, a broker, an exchange or observed execution quality.
"""

from __future__ import annotations

from hilmarbench.execution import (
    ExecutionCostAssumptions,
    build_execution_scenario_surface,
    estimate_capacity_from_edge,
)


def main() -> None:
    assumptions = ExecutionCostAssumptions(
        fee_bps=2.0,
        half_spread_bps=3.0,
        slippage_bps=5.0,
        impact_coefficient_bps=8.0,
        impact_exponent=0.5,
        reference_participation_rate=0.01,
        reference_volatility=0.04,
        maximum_participation_rate=0.10,
    )

    surface = build_execution_scenario_surface(
        order_notionals=[
            250_000.0,
            1_000_000.0,
            4_000_000.0,
            10_000_000.0,
        ],
        daily_volume_notionals=[
            100_000_000.0,
        ],
        daily_volatilities=[
            0.02,
            0.04,
            0.08,
        ],
        slippage_bps_values=[
            0.0,
            5.0,
            10.0,
            25.0,
        ],
        assumptions=assumptions,
    )

    capacity = estimate_capacity_from_edge(
        expected_gross_edge_bps=18.0,
        daily_volume_notional=100_000_000.0,
        daily_volatility=0.04,
        assumptions=assumptions,
    )

    print(
        surface.to_string(
            index=False,
            float_format=lambda value: f"{value:.6f}",
        )
    )

    print()
    print(
        "Synthetic break-even notional:",
        f"{capacity.maximum_notional:.2f}",
    )
    print(
        "Binding constraint:",
        capacity.binding_constraint,
    )


if __name__ == "__main__":
    main()
