from __future__ import annotations

from pathlib import Path

import pandas as pd


def _write_inputs(root: Path) -> tuple[Path, Path]:
    metrics = pd.DataFrame(
        {
            "strategy": ["NOSTRA_AI", "BUY_AND_HOLD"],
            "cost_bps": [25.0, 25.0],
            "date_start": ["2020-05-14", "2020-05-14"],
            "date_end": ["2026-06-02", "2026-06-02"],
            "observations": [2211, 2211],
            "final_equity": [12.75, 6.9],
            "total_return": [11.75, 5.9],
            "cagr": [0.5, 0.36],
            "annualized_volatility": [0.29, 0.57],
            "sharpe": [1.56, 0.83],
            "maximum_drawdown": [-0.21, -0.76],
            "calmar": [2.37, 0.48],
        }
    )
    daily = pd.DataFrame(
        {
            "timestamp": ["2026-01-31T00:00:00Z", "2026-02-01T00:00:00Z", "2026-02-28T00:00:00Z"],
            "nostra_ai_equity": [1.1, 1.2, 1.3],
            "nostra_ai_drawdown": [0.0, 0.0, -0.01],
            "buy_and_hold_equity": [1.0, 1.1, 1.2],
            "buy_and_hold_drawdown": [0.0, 0.0, -0.02],
        }
    )
    metrics_path = root / "metrics.csv"
    daily_path = root / "daily.csv"
    metrics.to_csv(metrics_path, index=False)
    daily.to_csv(daily_path, index=False)
    return (metrics_path, daily_path)
