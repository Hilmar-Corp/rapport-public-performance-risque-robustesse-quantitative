from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from hilmarbench.metrics import (
    compute_performance_metrics,
)
from hilmarbench.publication import (
    build_public_release,
    verify_release,
)


def _write_inputs(
    root: Path,
) -> tuple[Path, Path]:
    metrics = pd.DataFrame(
        {
            "strategy": [
                "NOSTRA_AI",
                "BUY_AND_HOLD",
            ],
            "cost_bps": [25.0, 25.0],
            "date_start": [
                "2020-01-01",
                "2020-01-01",
            ],
            "date_end": [
                "2020-01-03",
                "2020-01-03",
            ],
            "observations": [3, 3],
            "final_equity": [1.3, 1.2],
            "total_return": [0.0, 0.0],
            "cagr": [0.0, 0.0],
            "annualized_volatility": [
                0.2,
                0.3,
            ],
            "sharpe": [1.0, 0.8],
            "maximum_drawdown": [
                -0.1,
                -0.2,
            ],
            "calmar": [0.0, 0.0],
        }
    )

    daily = pd.DataFrame(
        {
            "timestamp": [
                "2020-01-01",
                "2020-01-02",
                "2020-01-03",
            ],
            "nostra_ai_equity": [
                1.0,
                1.1,
                1.3,
            ],
            "nostra_ai_drawdown": [
                0.0,
                0.0,
                0.0,
            ],
            "buy_and_hold_equity": [
                1.0,
                1.1,
                1.2,
            ],
            "buy_and_hold_drawdown": [
                0.0,
                0.0,
                0.0,
            ],
        }
    )

    metrics_path = root / "metrics.csv"
    daily_path = root / "daily.csv"

    metrics.to_csv(
        metrics_path,
        index=False,
    )

    daily.to_csv(
        daily_path,
        index=False,
    )

    return metrics_path, daily_path


def test_release_contains_no_nostra_time_series(
    tmp_path: Path,
) -> None:
    metrics_path, daily_path = _write_inputs(tmp_path)

    output = tmp_path / "release"

    build_public_release(
        metrics_path,
        daily_path,
        output,
        private_artifact_sha256=("a" * 64),
    )

    assert {path.name for path in output.iterdir() if path.is_file()} == {
        "SHA256SUMS",
        "baseline_daily_curves.csv",
        "benchmark_metrics.csv",
        "manifest.json",
        "methodology.json",
        "nostra_artifact_commitment.json",
    }

    baseline = pd.read_csv(output / "baseline_daily_curves.csv")

    assert not any(column.lower().startswith("nostra") for column in baseline.columns)

    assert verify_release(output) == []


def test_release_methodology_matches_final_policy(
    tmp_path: Path,
) -> None:
    metrics_path, daily_path = _write_inputs(tmp_path)

    output = tmp_path / "release"

    build_public_release(
        metrics_path,
        daily_path,
        output,
        private_artifact_sha256=("b" * 64),
    )

    methodology = json.loads((output / "methodology.json").read_text(encoding="utf-8"))

    nostra = methodology["nostra"]

    assert nostra["daily_equity_in_github"] is False

    assert nostra["daily_positions_public"] is False

    assert nostra["daily_returns_public"] is False

    assert nostra["website_daily_equity"] is True

    assert nostra["website_minimum_delay_days"] == 14


def test_cagr_uses_observation_count() -> None:
    returns = pd.Series(
        [0.10, 0.00, 0.00],
        index=pd.to_datetime(
            [
                "2020-01-01",
                "2020-01-10",
                "2020-02-01",
            ]
        ),
    )

    result = compute_performance_metrics(
        returns,
        periods_per_year=365.0,
    )

    expected = 1.10 ** (365.0 / 3.0) - 1.0

    assert result["cagr"] == pytest.approx(expected)
