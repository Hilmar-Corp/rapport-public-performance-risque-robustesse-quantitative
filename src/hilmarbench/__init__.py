"""Transparent benchmark and backtesting utilities."""

from hilmarbench.backtest import BacktestConfig, run_backtest
from hilmarbench.metrics import compute_performance_metrics

__all__ = [
    "BacktestConfig",
    "compute_performance_metrics",
    "run_backtest",
]

__version__ = "0.2.1"
