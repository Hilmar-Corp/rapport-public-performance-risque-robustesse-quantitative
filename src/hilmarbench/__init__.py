"""Transparent benchmark and backtesting utilities."""

from hilmarbench.backtest import BacktestConfig, ExecutionModelInputs, run_backtest
from hilmarbench.execution import (
    CapacityEstimate,
    ExecutionCostAssumptions,
    ExecutionCostEstimate,
    build_execution_scenario_surface,
    estimate_capacity_from_edge,
    estimate_execution_cost,
)
from hilmarbench.metrics import compute_performance_metrics

__all__ = [
    "BacktestConfig",
    "CapacityEstimate",
    "ExecutionCostAssumptions",
    "ExecutionCostEstimate",
    "ExecutionModelInputs",
    "build_execution_scenario_surface",
    "compute_performance_metrics",
    "estimate_capacity_from_edge",
    "estimate_execution_cost",
    "run_backtest",
]

__version__ = "0.2.1"
