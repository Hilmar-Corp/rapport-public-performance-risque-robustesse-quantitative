from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from hilmarbench.publication import (
    build_public_release,
    verify_release,
)


def _write_valid_inputs(
    root: Path,
) -> tuple[Path, Path]:
    metrics = pd.DataFrame(
        {
            "strategy": [
                "NOSTRA_AI",
                "BUY_AND_HOLD",
            ],
            "cost_bps": [
                25.0,
                25.0,
            ],
            "date_start": [
                "2020-01-01",
                "2020-01-01",
            ],
            "date_end": [
                "2020-01-03",
                "2020-01-03",
            ],
            "observations": [
                3,
                3,
            ],
            "final_equity": [
                1.30,
                1.20,
            ],
            "total_return": [
                0.30,
                0.20,
            ],
            "cagr": [
                0.0,
                0.0,
            ],
            "annualized_volatility": [
                0.20,
                0.30,
            ],
            "sharpe": [
                1.0,
                0.8,
            ],
            "maximum_drawdown": [
                -0.10,
                -0.20,
            ],
            "calmar": [
                0.0,
                0.0,
            ],
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
                1.00,
                1.10,
                1.30,
            ],
            "nostra_ai_drawdown": [
                0.00,
                0.00,
                0.00,
            ],
            "buy_and_hold_equity": [
                1.00,
                1.10,
                1.20,
            ],
            "buy_and_hold_drawdown": [
                0.00,
                0.00,
                0.00,
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


def test_build_release_rejects_existing_output(
    tmp_path: Path,
) -> None:
    metrics_path, daily_path = _write_valid_inputs(tmp_path)

    output = tmp_path / "release"
    output.mkdir()

    with pytest.raises(
        FileExistsError,
        match="Output already exists",
    ):
        build_public_release(
            metrics_path,
            daily_path,
            output,
            private_artifact_sha256="a" * 64,
        )


def test_build_release_rejects_invalid_hash(
    tmp_path: Path,
) -> None:
    metrics_path, daily_path = _write_valid_inputs(tmp_path)

    with pytest.raises(
        ValueError,
        match="lowercase SHA-256",
    ):
        build_public_release(
            metrics_path,
            daily_path,
            tmp_path / "release",
            private_artifact_sha256="invalid",
        )


def test_build_release_rejects_missing_metric_column(
    tmp_path: Path,
) -> None:
    metrics_path, daily_path = _write_valid_inputs(tmp_path)

    metrics = pd.read_csv(metrics_path)
    metrics = metrics.drop(columns="calmar")
    metrics.to_csv(
        metrics_path,
        index=False,
    )

    with pytest.raises(
        ValueError,
        match="Missing metric columns",
    ):
        build_public_release(
            metrics_path,
            daily_path,
            tmp_path / "release",
            private_artifact_sha256="b" * 64,
        )


def test_release_audit_detects_nostra_time_series(
    tmp_path: Path,
) -> None:
    metrics_path, daily_path = _write_valid_inputs(tmp_path)

    output = tmp_path / "release"

    build_public_release(
        metrics_path,
        daily_path,
        output,
        private_artifact_sha256="c" * 64,
    )

    curves_path = output / "baseline_daily_curves.csv"

    curves = pd.read_csv(curves_path)
    curves["nostra_equity"] = 1.0
    curves.to_csv(
        curves_path,
        index=False,
    )

    issues = verify_release(output)

    assert any("Nostra time series forbidden" in issue for issue in issues)


def test_release_audit_detects_invalid_commitment(
    tmp_path: Path,
) -> None:
    metrics_path, daily_path = _write_valid_inputs(tmp_path)

    output = tmp_path / "release"

    build_public_release(
        metrics_path,
        daily_path,
        output,
        private_artifact_sha256="d" * 64,
    )

    commitment_path = output / "nostra_artifact_commitment.json"

    commitment_path.write_text(
        json.dumps(
            {
                "algorithm": "SHA-256",
                "private_evaluation_artifact_sha256": ("invalid"),
            }
        ),
        encoding="utf-8",
    )

    issues = verify_release(output)

    assert any("invalid SHA-256 commitment" in issue for issue in issues)
