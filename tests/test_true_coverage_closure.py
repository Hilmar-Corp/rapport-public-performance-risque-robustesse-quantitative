from __future__ import annotations

import builtins
import copy
import csv
import json
import math
import shutil
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pandas as pd
import pytest

import hilmarbench.backtest as backtest_module
import hilmarbench.historical_reverse_stress as reverse_stress
import hilmarbench.hmm as hmm_module
import hilmarbench.publication as publication
import hilmarbench.quantitative_exports as quantitative_exports
import hilmarbench.risk_backtesting as risk_backtesting
import hilmarbench.statistical_tests as statistical_tests
import hilmarbench.temporal_statistics as temporal_statistics
from hilmarbench.backtest import BacktestConfig
from hilmarbench.metrics import compute_performance_metrics
from hilmarbench.strategies import (
    fixed_exposure,
    momentum_exposure,
    moving_average_exposure,
    prices_from_returns,
    volatility_target_exposure,
)

ROOT = Path(__file__).resolve().parents[1]

PACKAGE = ROOT / "artifacts" / "candidates" / "v0.3.0" / "quantitative_aggregates"


def _complete_payload() -> dict[str, Any]:
    payload: dict[str, Any] = json.loads((PACKAGE / "metadata.json").read_text(encoding="utf-8"))

    for section in quantitative_exports.REQUIRED_SECTIONS:
        wrapper = json.loads(
            (PACKAGE / quantitative_exports.PAYLOAD_FILENAMES[section]).read_text(encoding="utf-8")
        )

        payload[section] = wrapper["data"]

    return payload


def _section(name: str) -> dict[str, Any]:
    return copy.deepcopy(_complete_payload()[name])


def _assert_invalid(
    issues: list[str],
) -> None:
    assert issues


def _counterfactual_issues(
    section: Any,
) -> list[str]:
    return quantitative_exports._validate_counterfactual_reverse_stress(section)


def _historical_issues(
    section: Any,
) -> list[str]:
    return quantitative_exports._validate_historical_reverse_stress(section)


def _var_es_issues(
    section: Any,
) -> list[str]:
    return quantitative_exports._validate_var_es_backtesting(section)


def _temporal_issues(
    section: Any,
) -> list[str]:
    issues: list[str] = []

    quantitative_exports._validate_temporal_dependence_sharpe(
        {
            "temporal_dependence_sharpe": section,
        },
        issues,
    )

    return issues


def _public_input_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    metrics = pd.DataFrame(
        [
            {
                "strategy": "Nostra AI",
                "cost_bps": 25.0,
                "date_start": "2020-05-14",
                "date_end": "2026-06-02",
                "observations": 2211,
                "final_equity": 12.0,
                "total_return": 11.0,
                "cagr": 0.50,
                "annualized_volatility": 0.30,
                "sharpe": 1.50,
                "maximum_drawdown": -0.20,
                "calmar": 2.50,
            },
            {
                "strategy": "Buy and Hold",
                "cost_bps": 25.0,
                "date_start": "2020-05-14",
                "date_end": "2026-06-02",
                "observations": 2211,
                "final_equity": 7.0,
                "total_return": 6.0,
                "cagr": 0.35,
                "annualized_volatility": 0.55,
                "sharpe": 0.80,
                "maximum_drawdown": -0.80,
                "calmar": 0.44,
            },
        ]
    )

    daily = pd.DataFrame(
        {
            "date": [
                "2026-01-01",
                "2026-01-02",
            ],
            "buy_and_hold_equity": [
                1.0,
                1.1,
            ],
            "buy_and_hold_drawdown": [
                0.0,
                -0.1,
            ],
            "nostra_equity": [
                1.0,
                1.2,
            ],
            "private_position": [
                0.5,
                0.7,
            ],
            "unrelated_surface": [
                1.0,
                2.0,
            ],
        }
    )

    return metrics, daily


def _write_public_inputs(
    root: Path,
    *,
    metrics: pd.DataFrame | None = None,
    daily: pd.DataFrame | None = None,
) -> tuple[Path, Path]:
    root.mkdir(
        parents=True,
        exist_ok=True,
    )

    default_metrics, default_daily = _public_input_frames()

    metrics_path = root / "metrics.csv"
    daily_path = root / "daily.csv"

    (default_metrics if metrics is None else metrics).to_csv(
        metrics_path,
        index=False,
    )

    (default_daily if daily is None else daily).to_csv(
        daily_path,
        index=False,
    )

    return metrics_path, daily_path


def _build_valid_release(
    root: Path,
) -> Path:
    metrics_path, daily_path = _write_public_inputs(root / "inputs")

    output = root / "release"

    publication.build_public_release(
        metrics_path,
        daily_path,
        output,
        private_artifact_sha256=("a" * 64),
    )

    assert publication.verify_release(output) == []

    return output


def test_strategy_validation_failure_modes() -> None:
    returns = pd.Series(
        [
            0.01,
            -0.02,
            0.03,
        ]
    )

    for initial_price in (
        math.nan,
        math.inf,
    ):
        with pytest.raises(
            ValueError,
            match="finite",
        ):
            prices_from_returns(
                returns,
                initial_price=initial_price,
            )

    with pytest.raises(
        ValueError,
        match="positive",
    ):
        prices_from_returns(
            returns,
            initial_price=0.0,
        )

    with pytest.raises(
        ValueError,
        match="finite",
    ):
        fixed_exposure(
            returns.index,
            exposure=math.inf,
        )

    with pytest.raises(
        ValueError,
        match="positive",
    ):
        momentum_exposure(
            prices_from_returns(returns),
            lookback=0,
        )

    with pytest.raises(
        ValueError,
        match="positive",
    ):
        moving_average_exposure(
            prices_from_returns(returns),
            fast_window=0,
            slow_window=2,
        )

    with pytest.raises(
        ValueError,
        match="lower",
    ):
        moving_average_exposure(
            prices_from_returns(returns),
            fast_window=2,
            slow_window=2,
        )

    invalid_volatility_cases = (
        {
            "window": 1,
        },
        {
            "target_annualized_volatility": math.nan,
        },
        {
            "target_annualized_volatility": 0.0,
        },
        {
            "periods_per_year": math.nan,
        },
        {
            "periods_per_year": 0.0,
        },
        {
            "minimum_exposure": math.nan,
        },
        {
            "maximum_exposure": math.nan,
        },
        {
            "minimum_exposure": 2.0,
            "maximum_exposure": 1.0,
        },
    )

    for arguments in invalid_volatility_cases:
        with pytest.raises(ValueError):
            volatility_target_exposure(
                returns,
                **arguments,
            )


def test_metrics_explicit_equity_and_drawdown_paths() -> None:
    index = pd.date_range(
        "2026-01-01",
        periods=4,
        freq="D",
    )

    returns = pd.Series(
        [
            0.01,
            -0.02,
            0.03,
            0.01,
        ],
        index=index,
    )

    equity = pd.Series(
        [
            1.01,
            0.9898,
            1.019494,
            1.02968894,
        ],
        index=index,
    )

    drawdown = pd.Series(
        [
            0.0,
            -0.02,
            0.0,
            0.0,
        ],
        index=index,
    )

    result = compute_performance_metrics(
        returns,
        equity=equity,
        drawdown=drawdown,
        position=pd.Series(
            [
                0.0,
                0.5,
                1.0,
                0.5,
            ],
            index=index,
        ),
        turnover=pd.Series(
            [
                0.0,
                0.5,
                0.5,
                0.5,
            ],
            index=index,
        ),
        transaction_cost=pd.Series(
            [
                0.0,
                0.001,
                0.001,
                0.001,
            ],
            index=index,
        ),
    )

    assert result["final_equity"] == pytest.approx(equity.iloc[-1])

    assert result["maximum_drawdown"] == pytest.approx(-0.02)

    assert result["mean_position"] == pytest.approx(0.5)

    assert result["turnover"] == pytest.approx(1.5)

    assert result["transaction_cost_sum"] == pytest.approx(0.003)


def test_backtest_catastrophic_return_and_net_accounting() -> None:
    index = pd.RangeIndex(1)

    with pytest.raises(
        ValueError,
        match="-100%",
    ):
        backtest_module.run_backtest(
            pd.Series(
                [
                    -1.0,
                ],
                index=index,
            ),
            pd.Series(
                [
                    1.0,
                ],
                index=index,
            ),
            execution_lag_days=0,
            config=BacktestConfig(cost_bps=0.0),
        )

    frame = pd.DataFrame(
        {
            "position": [
                1.0,
            ],
            "asset_return": [
                0.1,
            ],
            "transaction_cost": [
                0.01,
            ],
            "gross_strategy_return": [
                0.1,
            ],
            "strategy_return": [
                0.5,
            ],
        }
    )

    with pytest.raises(
        ValueError,
        match="Net return",
    ):
        backtest_module.validate_accounting(frame)


def test_historical_reverse_stress_peak_candidate_is_ignored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    episode = reverse_stress.DrawdownEpisode(
        episode_number=1,
        peak_index=0,
        start_index=1,
        trough_index=1,
        end_index=1,
        recovery_index=None,
        recovered_in_sample=False,
        maximum_drawdown=-0.30,
    )

    monkeypatch.setattr(
        reverse_stress,
        "drawdown_series",
        lambda _: np.asarray(
            [
                -0.20,
                -0.30,
            ],
            dtype=float,
        ),
    )

    monkeypatch.setattr(
        reverse_stress,
        "identify_drawdown_episodes",
        lambda *_args, **_kwargs: (episode,),
    )

    result = reverse_stress.historical_threshold_breaches(
        [
            -0.1,
            -0.1,
        ],
        [
            1.0,
            0.5,
        ],
        loss_thresholds=[
            0.10,
        ],
    )

    assert result == ()


def test_statistical_invalid_psr_variance_term(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        statistical_tests,
        "skew",
        lambda *_args, **_kwargs: 1000.0,
    )

    monkeypatch.setattr(
        statistical_tests,
        "kurtosis",
        lambda *_args, **_kwargs: 1.0,
    )

    with pytest.raises(
        ValueError,
        match="variance term",
    ):
        statistical_tests.probabilistic_sharpe_ratio(
            [
                0.01,
                0.02,
                0.03,
                0.04,
            ]
        )


def test_risk_backtesting_internal_failure_modes() -> None:
    with pytest.raises(
        ValueError,
        match="one-dimensional",
    ):
        risk_backtesting._finite_vector(
            [
                [
                    1.0,
                ],
            ],
            name="x",
        )

    with pytest.raises(
        ValueError,
        match="must not be empty",
    ):
        risk_backtesting._finite_vector(
            [],
            name="x",
        )

    with pytest.raises(
        ValueError,
        match="finite",
    ):
        risk_backtesting._finite_vector(
            [
                1.0,
                math.nan,
            ],
            name="x",
        )

    invalid_counts = (
        (
            -1,
            1,
            0.5,
        ),
        (
            2,
            1,
            0.5,
        ),
    )

    for successes, total, probability in invalid_counts:
        with pytest.raises(
            ValueError,
            match="counts",
        ):
            risk_backtesting._bernoulli_log_likelihood(
                successes,
                total,
                probability,
            )

    for probability in (
        -0.1,
        1.1,
    ):
        with pytest.raises(
            ValueError,
            match="probability",
        ):
            risk_backtesting._bernoulli_log_likelihood(
                0,
                1,
                probability,
            )

    assert (
        risk_backtesting._bernoulli_log_likelihood(
            1,
            1,
            0.0,
        )
        == -math.inf
    )

    assert (
        risk_backtesting._bernoulli_log_likelihood(
            0,
            1,
            1.0,
        )
        == -math.inf
    )

    with pytest.raises(
        ValueError,
        match="strictly between",
    ):
        risk_backtesting.exact_binomial_coverage_p_value(
            [
                0,
                1,
            ],
            0.0,
        )

    zeros = risk_backtesting.christoffersen_independence(
        [
            0,
            0,
            0,
        ]
    )

    ones = risk_backtesting.christoffersen_independence(
        [
            1,
            1,
            1,
        ]
    )

    assert zeros.n10 == 0
    assert zeros.n11 == 0
    assert ones.n00 == 0
    assert ones.n01 == 0

    red = risk_backtesting.validation_traffic_light(
        p_values=[
            0.001,
        ],
        expected_exception_count=1.0,
    )

    assert red.colour == "RED"

    assert "LOW_EXPECTED_EXCEPTION_COUNT" in red.reason_codes


def test_temporal_degenerate_and_bootstrap_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    constant = [
        1.0,
        1.0,
        1.0,
        1.0,
    ]

    with pytest.raises(
        ValueError,
        match="positive variance",
    ):
        temporal_statistics.sample_autocorrelation(
            constant,
            1,
        )

    with pytest.raises(
        ValueError,
        match="positive variance",
    ):
        temporal_statistics.newey_west_long_run_variance(
            constant,
            lag_count=1,
        )

    with pytest.raises(
        ValueError,
        match="positive variance",
    ):
        temporal_statistics.hac_adjusted_sharpe(
            constant,
            lag_count=1,
        )

    with monkeypatch.context() as patch:
        patch.setattr(
            temporal_statistics.math,
            "isfinite",
            lambda _value: False,
        )

        with pytest.raises(
            ValueError,
            match="long-run variance",
        ):
            temporal_statistics.newey_west_long_run_variance(
                [
                    0.01,
                    -0.02,
                    0.03,
                    -0.01,
                ],
                lag_count=1,
            )

    with monkeypatch.context() as patch:
        patch.setattr(
            temporal_statistics,
            "_circular_moving_block_indices",
            lambda observations, block_size, rng: np.zeros(
                observations,
                dtype=np.int64,
            ),
        )

        with pytest.raises(
            RuntimeError,
            match="Too few finite",
        ):
            temporal_statistics.moving_block_sharpe_interval(
                np.linspace(
                    -0.05,
                    0.05,
                    10,
                ),
                block_size=2,
                repetitions=99,
            )


def _install_fake_hmm(
    monkeypatch: pytest.MonkeyPatch,
    implementation: type[Any],
) -> None:
    package = types.ModuleType("hmmlearn")

    child = types.ModuleType("hmmlearn.hmm")

    child.GaussianHMM = implementation

    package.hmm = child

    monkeypatch.setitem(
        sys.modules,
        "hmmlearn",
        package,
    )

    monkeypatch.setitem(
        sys.modules,
        "hmmlearn.hmm",
        child,
    )


def _hmm_returns() -> pd.Series:
    return pd.Series(
        np.linspace(
            -0.03,
            0.04,
            20,
        ),
        index=pd.date_range(
            "2026-01-01",
            periods=20,
            freq="D",
        ),
    )


def test_hmm_covariance_regularization_and_import_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    value = hmm_module._gaussian_log_probability(
        np.asarray(
            [
                0.0,
            ]
        ),
        np.asarray(
            [
                0.0,
            ]
        ),
        np.asarray(
            [
                [
                    -1.0,
                ],
            ]
        ),
    )

    assert math.isfinite(value)

    original_import = builtins.__import__

    def blocked_import(
        name: str,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        if name == "hmmlearn.hmm":
            raise ImportError("blocked")

        return original_import(
            name,
            *args,
            **kwargs,
        )

    monkeypatch.setattr(
        builtins,
        "__import__",
        blocked_import,
    )

    with pytest.raises(
        RuntimeError,
        match="hmmlearn is required",
    ):
        hmm_module.walk_forward_hmm_exposure(
            _hmm_returns(),
            minimum_training_observations=3,
            refit_frequency=2,
            volatility_window=2,
        )


def test_hmm_model_failure_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class MonitorFailureHMM:
        def __init__(
            self,
            *,
            random_state: int,
            **_kwargs: Any,
        ) -> None:
            self.random_state = random_state

        def fit(
            self,
            _values: np.ndarray,
        ) -> MonitorFailureHMM:
            if self.random_state == 1:
                self.monitor_ = None
            elif self.random_state == 2:
                self.monitor_ = SimpleNamespace(
                    converged=False,
                    history=[
                        0.0,
                        1.0,
                    ],
                )
            else:
                self.monitor_ = SimpleNamespace(
                    converged=True,
                    history=[
                        1.0,
                        0.0,
                    ],
                )

            return self

        def score(
            self,
            _values: np.ndarray,
        ) -> float:
            return 1.0

    _install_fake_hmm(
        monkeypatch,
        MonitorFailureHMM,
    )

    signal, diagnostics = hmm_module.walk_forward_hmm_exposure(
        _hmm_returns(),
        minimum_training_observations=3,
        refit_frequency=2,
        volatility_window=2,
        random_seeds=(
            1,
            2,
            3,
        ),
    )

    assert signal.empty
    assert diagnostics["fit_count"] == 0
    assert diagnostics["failure_count"] > 0

    class RaisingHMM:
        def __init__(
            self,
            **_kwargs: Any,
        ) -> None:
            pass

        def fit(
            self,
            _values: np.ndarray,
        ) -> RaisingHMM:
            raise RuntimeError("fit failed")

    _install_fake_hmm(
        monkeypatch,
        RaisingHMM,
    )

    signal, diagnostics = hmm_module.walk_forward_hmm_exposure(
        _hmm_returns(),
        minimum_training_observations=3,
        refit_frequency=2,
        volatility_window=2,
        random_seeds=(1,),
    )

    assert signal.empty
    assert diagnostics["failure_count"] > 0


def test_hmm_missing_covariance_and_score_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class MissingCovarianceHMM:
        def __init__(
            self,
            **_kwargs: Any,
        ) -> None:
            self.monitor_ = SimpleNamespace(
                converged=True,
                history=[
                    0.0,
                    1.0,
                ],
            )

            self.covars_ = None

        def fit(
            self,
            _values: np.ndarray,
        ) -> MissingCovarianceHMM:
            return self

        def score(
            self,
            _values: np.ndarray,
        ) -> float:
            return 1.0

    _install_fake_hmm(
        monkeypatch,
        MissingCovarianceHMM,
    )

    signal, diagnostics = hmm_module.walk_forward_hmm_exposure(
        _hmm_returns(),
        minimum_training_observations=3,
        refit_frequency=2,
        volatility_window=2,
        random_seeds=(1,),
    )

    assert signal.empty
    assert diagnostics["failure_count"] > 0

    class SelectableHMM:
        def __init__(
            self,
            *,
            random_state: int,
            **_kwargs: Any,
        ) -> None:
            self.random_state = random_state

            self.monitor_ = SimpleNamespace(
                converged=True,
                history=[
                    0.0,
                    1.0,
                ],
            )

            self.startprob_ = np.asarray(
                [
                    1 / 3,
                    1 / 3,
                    1 / 3,
                ]
            )

            self.transmat_ = np.asarray(
                [
                    [
                        0.8,
                        0.1,
                        0.1,
                    ],
                    [
                        0.1,
                        0.8,
                        0.1,
                    ],
                    [
                        0.1,
                        0.1,
                        0.8,
                    ],
                ]
            )

            self.means_ = np.asarray(
                [
                    [
                        -1.0,
                        0.0,
                    ],
                    [
                        0.0,
                        0.0,
                    ],
                    [
                        1.0,
                        0.0,
                    ],
                ]
            )

            self.covars_ = np.asarray(
                [
                    np.eye(2),
                    np.eye(2),
                    np.eye(2),
                ]
            )

        def fit(
            self,
            _values: np.ndarray,
        ) -> SelectableHMM:
            return self

        def score(
            self,
            _values: np.ndarray,
        ) -> float:
            if self.random_state == 1:
                return 1.0

            if self.random_state == 2:
                return 0.5

            return math.nan

    _install_fake_hmm(
        monkeypatch,
        SelectableHMM,
    )

    signal, diagnostics = hmm_module.walk_forward_hmm_exposure(
        _hmm_returns(),
        minimum_training_observations=3,
        refit_frequency=2,
        volatility_window=2,
        random_seeds=(
            1,
            2,
            3,
        ),
    )

    assert not signal.empty
    assert diagnostics["fit_count"] > 0


def test_publication_scan_tree_io_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    text_root = tmp_path / "text"

    text_root.mkdir()

    target = text_root / "unreadable.txt"

    target.write_text(
        "safe",
        encoding="utf-8",
    )

    original_read_text = Path.read_text

    def broken_read_text(
        self: Path,
        *args: Any,
        **kwargs: Any,
    ) -> str:
        if self == target:
            raise OSError("blocked")

        return original_read_text(
            self,
            *args,
            **kwargs,
        )

    with monkeypatch.context() as patch:
        patch.setattr(
            Path,
            "read_text",
            broken_read_text,
        )

        issues = publication.scan_tree(text_root)

    assert any("unreadable file" in issue for issue in issues)

    csv_root = tmp_path / "csv"

    csv_root.mkdir()

    csv_path = csv_root / "surface.csv"

    csv_path.write_text(
        "safe,value\n1,2\n",
        encoding="utf-8",
    )

    def broken_reader(
        _stream: Any,
    ) -> Any:
        raise OSError("blocked CSV")

    with monkeypatch.context() as patch:
        patch.setattr(
            publication.csv,
            "reader",
            broken_reader,
        )

        issues = publication.scan_tree(csv_root)

    assert any("unreadable CSV" in issue for issue in issues)


def test_publication_manifest_output_exclusions(
    tmp_path: Path,
) -> None:
    root = tmp_path / "manifest"

    root.mkdir()

    (root / "data.txt").write_text(
        "data\n",
        encoding="utf-8",
    )

    (root / "SHA256SUMS").write_text(
        "placeholder\n",
        encoding="utf-8",
    )

    manifest_path = root / "manifest.json"

    manifest = publication.build_manifest(
        root,
        manifest_path,
    )

    names = {entry["path"] for entry in manifest["files"]}

    assert names == {
        "data.txt",
    }

    publication.write_sha256s(
        root,
        root / "SHA256SUMS",
    )

    checksum_text = (root / "SHA256SUMS").read_text(encoding="utf-8")

    assert "SHA256SUMS" not in (checksum_text)


def test_publication_build_release_failure_modes(
    tmp_path: Path,
) -> None:
    metrics, daily = _public_input_frames()

    metrics_path, daily_path = _write_public_inputs(tmp_path / "valid")

    existing_output = tmp_path / "existing"

    existing_output.mkdir()

    with pytest.raises(FileExistsError):
        publication.build_public_release(
            metrics_path,
            daily_path,
            existing_output,
            private_artifact_sha256=("a" * 64),
        )

    with pytest.raises(
        ValueError,
        match="lowercase SHA",
    ):
        publication.build_public_release(
            metrics_path,
            daily_path,
            tmp_path / "invalid-sha",
            private_artifact_sha256="invalid",
        )

    missing_metrics = metrics.drop(
        columns=[
            "sharpe",
        ]
    )

    missing_metrics_path, missing_daily_path = _write_public_inputs(
        tmp_path / "missing-metric",
        metrics=missing_metrics,
        daily=daily,
    )

    with pytest.raises(
        ValueError,
        match="Missing metric",
    ):
        publication.build_public_release(
            missing_metrics_path,
            missing_daily_path,
            tmp_path / "missing-metric-output",
            private_artifact_sha256=("a" * 64),
        )

    zero_observations = metrics.copy()

    zero_observations.loc[
        0,
        "observations",
    ] = 0

    zero_metrics_path, zero_daily_path = _write_public_inputs(
        tmp_path / "zero-observations",
        metrics=zero_observations,
        daily=daily,
    )

    with pytest.raises(
        ValueError,
        match="observations",
    ):
        publication.build_public_release(
            zero_metrics_path,
            zero_daily_path,
            tmp_path / "zero-observations-output",
            private_artifact_sha256=("a" * 64),
        )

    zero_equity = metrics.copy()

    zero_equity.loc[
        0,
        "final_equity",
    ] = 0.0

    zero_equity_path, zero_equity_daily = _write_public_inputs(
        tmp_path / "zero-equity",
        metrics=zero_equity,
        daily=daily,
    )

    with pytest.raises(
        ValueError,
        match="final_equity",
    ):
        publication.build_public_release(
            zero_equity_path,
            zero_equity_daily,
            tmp_path / "zero-equity-output",
            private_artifact_sha256=("a" * 64),
        )

    duplicate_timestamp = daily.copy()

    duplicate_timestamp["timestamp"] = duplicate_timestamp["date"]

    duplicate_metrics, duplicate_daily = _write_public_inputs(
        tmp_path / "duplicate-timestamp",
        metrics=metrics,
        daily=duplicate_timestamp,
    )

    with pytest.raises(
        ValueError,
        match="Exactly one timestamp",
    ):
        publication.build_public_release(
            duplicate_metrics,
            duplicate_daily,
            tmp_path / "duplicate-timestamp-output",
            private_artifact_sha256=("a" * 64),
        )

    insufficient_daily = daily[
        [
            "date",
            "buy_and_hold_equity",
        ]
    ]

    insufficient_metrics, insufficient_path = _write_public_inputs(
        tmp_path / "insufficient-curves",
        metrics=metrics,
        daily=insufficient_daily,
    )

    with pytest.raises(
        ValueError,
        match="Insufficient",
    ):
        publication.build_public_release(
            insufficient_metrics,
            insufficient_path,
            tmp_path / "insufficient-output",
            private_artifact_sha256=("a" * 64),
        )


def test_publication_verify_release_failure_modes(
    tmp_path: Path,
) -> None:
    base = _build_valid_release(tmp_path / "base")

    def duplicate(
        name: str,
    ) -> Path:
        destination = tmp_path / name

        shutil.copytree(
            base,
            destination,
        )

        return destination

    surface = duplicate("surface")

    (surface / "SHA256SUMS").unlink()

    (surface / "unexpected.txt").write_text(
        "safe\n",
        encoding="utf-8",
    )

    issues = publication.verify_release(surface)

    assert any("required release file missing" in issue for issue in issues)

    assert any("unexpected release file" in issue for issue in issues)

    schema = duplicate("schema")

    metrics = pd.read_csv(schema / "benchmark_metrics.csv")

    metrics.drop(
        columns=[
            "sharpe",
        ]
    ).to_csv(
        schema / "benchmark_metrics.csv",
        index=False,
    )

    assert any("invalid schema" in issue for issue in publication.verify_release(schema))

    no_nostra = duplicate("no-nostra")

    metrics = pd.read_csv(no_nostra / "benchmark_metrics.csv")

    metrics.loc[metrics["strategy"] != "Nostra AI"].to_csv(
        no_nostra / "benchmark_metrics.csv",
        index=False,
    )

    assert any(
        "invalid Nostra row count" in issue for issue in publication.verify_release(no_nostra)
    )

    wrong_verification = duplicate("wrong-verification")

    metrics = pd.read_csv(wrong_verification / "benchmark_metrics.csv")

    metrics.loc[
        metrics["strategy"] == "Nostra AI",
        "verification_level",
    ] = "code-reproducible"

    metrics.to_csv(
        wrong_verification / "benchmark_metrics.csv",
        index=False,
    )

    assert any(
        "invalid Nostra verification" in issue
        for issue in publication.verify_release(wrong_verification)
    )

    wrong_baseline = duplicate("wrong-baseline")

    metrics = pd.read_csv(wrong_baseline / "benchmark_metrics.csv")

    metrics.loc[
        metrics["strategy"] != "Nostra AI",
        "verification_level",
    ] = "artifact-verified"

    metrics.to_csv(
        wrong_baseline / "benchmark_metrics.csv",
        index=False,
    )

    assert any(
        "invalid baseline verification" in issue
        for issue in publication.verify_release(wrong_baseline)
    )

    daily_surface = duplicate("daily-surface")

    pd.DataFrame(
        {
            "date": [
                "2026-01-01",
            ],
            "timestamp": [
                "2026-01-01",
            ],
            "nostra_equity": [
                1.0,
            ],
            "unexpected": [
                1.0,
            ],
            "private_position": [
                1.0,
            ],
        }
    ).to_csv(
        daily_surface / "baseline_daily_curves.csv",
        index=False,
    )

    issues = publication.verify_release(daily_surface)

    assert any("invalid timestamp surface" in issue for issue in issues)

    assert any("Nostra time series forbidden" in issue for issue in issues)

    assert any("unexpected column" in issue for issue in issues)

    assert any("private column forbidden" in issue for issue in issues)

    methodology = duplicate("methodology")

    methodology_payload = json.loads((methodology / "methodology.json").read_text(encoding="utf-8"))

    nostra = methodology_payload["nostra"]

    for key in (
        "model_code_in_github",
        "daily_equity_in_github",
        "daily_positions_public",
        "daily_returns_public",
        "turnover_public",
    ):
        nostra[key] = True

    nostra["website_daily_equity"] = False

    nostra["website_minimum_delay_days"] = 0

    (methodology / "methodology.json").write_text(
        json.dumps(methodology_payload),
        encoding="utf-8",
    )

    issues = publication.verify_release(methodology)

    assert any("must be false" in issue for issue in issues)

    assert any("website_daily_equity" in issue for issue in issues)

    assert any("website delay" in issue for issue in issues)

    unreadable_methodology = duplicate("unreadable-methodology")

    (unreadable_methodology / "methodology.json").write_text(
        "{",
        encoding="utf-8",
    )

    assert any(
        "methodology.json: unreadable" in issue
        for issue in publication.verify_release(unreadable_methodology)
    )

    invalid_commitment = duplicate("invalid-commitment")

    commitment_payload = json.loads(
        (invalid_commitment / "nostra_artifact_commitment.json").read_text(encoding="utf-8")
    )

    commitment_payload["private_evaluation_artifact_sha256"] = "invalid"

    (invalid_commitment / "nostra_artifact_commitment.json").write_text(
        json.dumps(commitment_payload),
        encoding="utf-8",
    )

    assert any(
        "invalid SHA-256 commitment" in issue
        for issue in publication.verify_release(invalid_commitment)
    )

    unreadable_commitment = duplicate("unreadable-commitment")

    (unreadable_commitment / "nostra_artifact_commitment.json").write_text(
        "{",
        encoding="utf-8",
    )

    assert any(
        "nostra_artifact_commitment.json: unreadable" in issue
        for issue in publication.verify_release(unreadable_commitment)
    )


def test_counterfactual_validator_exhaustive_failure_modes() -> None:
    valid = _section("counterfactual_reverse_stress")

    assert _counterfactual_issues(valid) == []

    _assert_invalid(_counterfactual_issues(None))

    case = copy.deepcopy(valid)

    for field in (
        "verification_level",
        "observations",
        "historical_scope",
        "total_scenarios",
        "inference_stage_scenarios",
        "retraining_and_core_scenarios",
        "refinement_scenarios",
        "refined_failure_frontiers",
        "refined_failure_families",
        "all_phase_offsets_tested",
        "isolated_input_corruption_failure_found",
        "dominant_vulnerability_class",
        "daily_paths_disclosed",
        "internal_variables_disclosed",
        "exact_private_settings_disclosed",
        "decision_status",
    ):
        case[field] = None

    _assert_invalid(_counterfactual_issues(case))

    for field in (
        "total_scenarios",
        "inference_stage_scenarios",
        "retraining_and_core_scenarios",
        "refinement_scenarios",
    ):
        for value in (
            True,
            "invalid",
        ):
            case = copy.deepcopy(valid)

            case[field] = value

            _assert_invalid(_counterfactual_issues(case))

    case = copy.deepcopy(valid)

    case["total_scenarios"] += 1

    _assert_invalid(_counterfactual_issues(case))

    for value in (
        True,
        "invalid",
        -1.0,
        1e-6,
    ):
        case = copy.deepcopy(valid)

        case["baseline_reconciliation_max_abs_delta"] = value

        _assert_invalid(_counterfactual_issues(case))

    case = copy.deepcopy(valid)

    case["randomized_repetitions"] = {}

    _assert_invalid(_counterfactual_issues(case))

    for value in (
        1,
        "short",
        "g" * 64,
    ):
        case = copy.deepcopy(valid)

        case["private_evidence_commitment_sha256"] = value

        _assert_invalid(_counterfactual_issues(case))

    for value in (
        None,
        " ",
    ):
        case = copy.deepcopy(valid)

        case["limitation"] = value

        _assert_invalid(_counterfactual_issues(case))

    case = copy.deepcopy(valid)

    for field in (
        "scenario_id",
        "severity",
        "daily_trace",
        "daily_returns",
        "daily_positions",
        "internal_inputs",
        "model_coefficients",
        "private_breakpoints",
        "selected_inputs",
        "source_path",
        "source_ledger",
    ):
        case[field] = "forbidden"

    _assert_invalid(_counterfactual_issues(case))


def test_historical_validator_exhaustive_failure_modes() -> None:
    valid = _section("historical_reverse_stress")

    assert _historical_issues(valid) == []

    _assert_invalid(_historical_issues(None))

    case = copy.deepcopy(valid)

    for field in (
        "verification_level",
        "methodological_status",
        "decision_status",
        "analysis_type",
        "observations",
    ):
        case[field] = None

    case["evaluation_period"] = {}

    _assert_invalid(_historical_issues(case))

    for value in (
        None,
        [],
        [
            "",
        ],
    ):
        case = copy.deepcopy(valid)

        case["governing_conventions"] = value

        _assert_invalid(_historical_issues(case))

    case = copy.deepcopy(valid)

    case["economic_reconciliation"] = None

    _assert_invalid(_historical_issues(case))

    for field, value in (
        (
            "status",
            "FAIL",
        ),
        (
            "public_convention_name",
            "invalid",
        ),
        (
            "maximum_absolute_delta",
            True,
        ),
        (
            "maximum_absolute_delta",
            "invalid",
        ),
        (
            "maximum_absolute_delta",
            1e-3,
        ),
    ):
        case = copy.deepcopy(valid)

        case["economic_reconciliation"][field] = value

        _assert_invalid(_historical_issues(case))

    case = copy.deepcopy(valid)

    case["global_results"] = None

    _assert_invalid(_historical_issues(case))

    for field, value in (
        (
            "drawdown_episode_count",
            0,
        ),
        (
            "loss_breach_record_count",
            0,
        ),
        (
            "maximum_model_drawdown",
            True,
        ),
        (
            "maximum_model_drawdown",
            "invalid",
        ),
        (
            "maximum_model_drawdown",
            0.0,
        ),
    ):
        case = copy.deepcopy(valid)

        case["global_results"][field] = value

        _assert_invalid(_historical_issues(case))

    case = copy.deepcopy(valid)

    case["loss_level_results"] = None

    _assert_invalid(_historical_issues(case))

    case = copy.deepcopy(valid)

    case["loss_level_results"][0] = None

    _assert_invalid(_historical_issues(case))

    for field, value in (
        (
            "target_nav_loss",
            True,
        ),
        (
            "target_nav_loss",
            "invalid",
        ),
        (
            "breach_episode_count",
            True,
        ),
        (
            "breach_episode_count",
            "invalid",
        ),
    ):
        case = copy.deepcopy(valid)

        case["loss_level_results"][0][field] = value

        _assert_invalid(_historical_issues(case))

    case = copy.deepcopy(valid)

    case["loss_level_results"][0]["target_nav_loss"] = 0.07

    _assert_invalid(_historical_issues(case))

    case = copy.deepcopy(valid)

    case["loss_level_results"][0]["breach_episode_count"] += 1

    _assert_invalid(_historical_issues(case))

    case = copy.deepcopy(valid)

    case["loss_level_results"][0]["historically_breached"] = False

    _assert_invalid(_historical_issues(case))

    zero_index = next(
        index
        for index, record in enumerate(valid["loss_level_results"])
        if record["breach_episode_count"] == 0
    )

    case = copy.deepcopy(valid)

    case["loss_level_results"][zero_index]["observed_non_breach_is_not_a_bound"] = False

    _assert_invalid(_historical_issues(case))

    positive_index = next(
        index
        for index, record in enumerate(valid["loss_level_results"])
        if record["breach_episode_count"] > 0
    )

    case = copy.deepcopy(valid)

    case["loss_level_results"][positive_index]["allocation_reaction_counts"] = None

    _assert_invalid(_historical_issues(case))

    reaction_keys = (
        "reduced_at_breach",
        "increased_at_breach",
        "unchanged_at_breach",
        "reduced_by_at_least_25pct_before_breach",
    )

    for key in reaction_keys:
        for value in (
            True,
            -1,
            "invalid",
        ):
            case = copy.deepcopy(valid)

            case["loss_level_results"][positive_index]["allocation_reaction_counts"][key] = value

            _assert_invalid(_historical_issues(case))

    case = copy.deepcopy(valid)

    case["loss_level_results"][positive_index]["allocation_reaction_counts"][
        "reduced_at_breach"
    ] += 1

    _assert_invalid(_historical_issues(case))

    case = copy.deepcopy(valid)

    case["loss_level_results"][positive_index]["allocation_reaction_shares"] = None

    _assert_invalid(_historical_issues(case))

    case = copy.deepcopy(valid)

    for key in case["loss_level_results"][positive_index]["allocation_reaction_shares"]:
        case["loss_level_results"][positive_index]["allocation_reaction_shares"][key] = "invalid"

    _assert_invalid(_historical_issues(case))

    for value in (
        None,
        {
            "status": "FAIL",
        },
    ):
        case = copy.deepcopy(valid)

        case["governance_decision"] = value

        _assert_invalid(_historical_issues(case))

    for value in (
        None,
        [],
        [
            "",
        ],
    ):
        case = copy.deepcopy(valid)

        case["limitations"] = value

        _assert_invalid(_historical_issues(case))

    case = copy.deepcopy(valid)

    case["evidence_commitment_sha256"] = "invalid"

    _assert_invalid(_historical_issues(case))


def test_var_es_validator_exhaustive_failure_modes() -> None:
    valid = _section("var_es_backtesting")

    assert _var_es_issues(valid) == []

    _assert_invalid(_var_es_issues(None))

    case = copy.deepcopy(valid)

    for field in (
        "verification_level",
        "methodological_status",
        "decision_status",
        "observations",
        "canonical_calibration_window_days",
    ):
        case[field] = None

    case["sensitivity_calibration_windows_days"] = []

    case["risk_periods_days"] = []

    case["confidence_levels"] = []

    _assert_invalid(_var_es_issues(case))

    case = copy.deepcopy(valid)

    case["canonical_results"] = None

    _assert_invalid(_var_es_issues(case))

    case = copy.deepcopy(valid)

    case["canonical_results"] = []

    _assert_invalid(_var_es_issues(case))

    case = copy.deepcopy(valid)

    case["canonical_results"][0] = None

    _assert_invalid(_var_es_issues(case))

    for field, value in (
        (
            "risk_period_days",
            True,
        ),
        (
            "risk_period_days",
            "invalid",
        ),
        (
            "confidence_level",
            True,
        ),
        (
            "confidence_level",
            "invalid",
        ),
    ):
        case = copy.deepcopy(valid)

        case["canonical_results"][0][field] = value

        _assert_invalid(_var_es_issues(case))

    p_value_fields = (
        "kupiec_p_value",
        "exact_binomial_p_value",
        "christoffersen_independence_p_value",
        "christoffersen_conditional_coverage_p_value",
        "es_normalized_tail_loss_bootstrap_p_value",
    )

    case = copy.deepcopy(valid)

    for field in p_value_fields:
        case["canonical_results"][0][field] = True

    _assert_invalid(_var_es_issues(case))

    case = copy.deepcopy(valid)

    case["canonical_results"][0]["traffic_light"] = "INVALID"

    _assert_invalid(_var_es_issues(case))

    for value in (
        None,
        [],
        [
            "",
        ],
    ):
        case = copy.deepcopy(valid)

        case["canonical_results"][0]["reason_codes"] = value

        _assert_invalid(_var_es_issues(case))

    case = copy.deepcopy(valid)

    for field in (
        "observations",
        "exception_count",
        "expected_exception_count",
        "exception_rate",
        "exception_cluster_count",
        "maximum_exception_cluster_length",
    ):
        case["canonical_results"][0][field] = -1

    _assert_invalid(_var_es_issues(case))

    case = copy.deepcopy(valid)

    case["canonical_results"][0]["risk_period_days"] = 999

    _assert_invalid(_var_es_issues(case))

    case = copy.deepcopy(valid)

    case["canonical_traffic_light_counts"] = {}

    case["all_sensitivity_traffic_light_counts"] = {}

    _assert_invalid(_var_es_issues(case))

    for value in (
        1,
        "short",
        "g" * 64,
    ):
        case = copy.deepcopy(valid)

        case["evidence_commitment_sha256"] = value

        _assert_invalid(_var_es_issues(case))

    for value in (
        None,
        [],
        [
            "",
        ],
    ):
        case = copy.deepcopy(valid)

        case["limitations"] = value

        _assert_invalid(_var_es_issues(case))


def test_temporal_export_validator_exhaustive_failure_modes() -> None:
    valid = _section("temporal_dependence_sharpe")

    assert _temporal_issues(valid) == []

    _assert_invalid(_temporal_issues(None))

    case = copy.deepcopy(valid)

    for field in (
        "verification_level",
        "methodological_status",
        "decision_status",
        "observations",
        "annualization",
        "automatic_lag_rule",
        "automatic_lag_count",
        "canonical_hac_lag_count",
        "canonical_block_size",
        "bootstrap_repetitions",
        "diagnostics",
    ):
        case[field] = None

    _assert_invalid(_temporal_issues(case))

    for field, values in (
        (
            "conventional_annualized_sharpe",
            (
                True,
                math.inf,
                0.0,
            ),
        ),
        (
            "canonical_hac_adjusted_annualized_sharpe",
            (
                True,
                -1.0,
                valid["conventional_annualized_sharpe"],
            ),
        ),
        (
            "canonical_volatility_inflation_factor",
            (
                True,
                1.0,
            ),
        ),
    ):
        for value in values:
            case = copy.deepcopy(valid)

            case[field] = value

            _assert_invalid(_temporal_issues(case))

    case = copy.deepcopy(valid)

    case["autocorrelation_records"] = None

    _assert_invalid(_temporal_issues(case))

    case = copy.deepcopy(valid)

    case["autocorrelation_records"][0] = None

    _assert_invalid(_temporal_issues(case))

    case = copy.deepcopy(valid)

    case["autocorrelation_records"][0]["lag_count"] = True

    case["autocorrelation_records"][0]["autocorrelation"] = 2.0

    _assert_invalid(_temporal_issues(case))

    case = copy.deepcopy(valid)

    case["autocorrelation_records"] = case["autocorrelation_records"][1:]

    _assert_invalid(_temporal_issues(case))

    case = copy.deepcopy(valid)

    case["ljung_box_records"] = None

    _assert_invalid(_temporal_issues(case))

    case = copy.deepcopy(valid)

    case["ljung_box_records"][0] = None

    _assert_invalid(_temporal_issues(case))

    case = copy.deepcopy(valid)

    record = case["ljung_box_records"][0]

    record["series"] = 1

    record["lag_count"] = True

    record["statistic"] = -1.0

    record["p_value"] = 2.0

    record["p_value_below_machine_precision"] = None

    _assert_invalid(_temporal_issues(case))

    case = copy.deepcopy(valid)

    case["ljung_box_records"] = case["ljung_box_records"][1:]

    _assert_invalid(_temporal_issues(case))

    case = copy.deepcopy(valid)

    case["hac_sensitivity_records"] = None

    _assert_invalid(_temporal_issues(case))

    case = copy.deepcopy(valid)

    case["hac_sensitivity_records"][0] = None

    _assert_invalid(_temporal_issues(case))

    case = copy.deepcopy(valid)

    record = case["hac_sensitivity_records"][0]

    record["lag_count"] = True

    record["hac_adjusted_annualized_sharpe"] = -1.0

    record["volatility_inflation_factor"] = -1.0

    _assert_invalid(_temporal_issues(case))

    case = copy.deepcopy(valid)

    case["hac_sensitivity_records"] = case["hac_sensitivity_records"][1:]

    _assert_invalid(_temporal_issues(case))

    case = copy.deepcopy(valid)

    case["bootstrap_sensitivity_records"] = None

    _assert_invalid(_temporal_issues(case))

    case = copy.deepcopy(valid)

    case["bootstrap_sensitivity_records"][0] = None

    _assert_invalid(_temporal_issues(case))

    case = copy.deepcopy(valid)

    record = case["bootstrap_sensitivity_records"][0]

    record["block_size"] = True

    record["interval_lower"] = True

    record["interval_upper"] = True

    record["bootstrap_median"] = True

    record["bootstrap_positive_share"] = 2.0

    record["confidence_level"] = 0.5

    _assert_invalid(_temporal_issues(case))

    case = copy.deepcopy(valid)

    record = case["bootstrap_sensitivity_records"][0]

    record["interval_lower"] = 2.0

    record["interval_upper"] = 1.0

    record["bootstrap_median"] = 3.0

    _assert_invalid(_temporal_issues(case))

    case = copy.deepcopy(valid)

    case["bootstrap_sensitivity_records"] = case["bootstrap_sensitivity_records"][1:]

    _assert_invalid(_temporal_issues(case))

    for field in (
        "formal_methods",
        "limitations",
    ):
        for value in (
            None,
            [],
            [
                "",
            ],
        ):
            case = copy.deepcopy(valid)

            case[field] = value

            _assert_invalid(_temporal_issues(case))

    for value in (
        1,
        "short",
        "g" * 64,
    ):
        case = copy.deepcopy(valid)

        case["evidence_commitment_sha256"] = value

        _assert_invalid(_temporal_issues(case))


def test_top_level_quantitative_validator_failure_modes() -> None:
    valid = _complete_payload()

    assert quantitative_exports.validate_public_quantitative_payload(valid) == []

    def validate(
        payload: dict[str, Any],
    ) -> list[str]:
        issues = quantitative_exports.validate_public_quantitative_payload(payload)

        _assert_invalid(issues)

        return issues

    case = copy.deepcopy(valid)

    del case["schema_version"]

    case["unexpected"] = True

    validate(case)

    for field, value in (
        (
            "schema_version",
            -1,
        ),
        (
            "release_target",
            "invalid",
        ),
        (
            "classification",
            "invalid",
        ),
        (
            "limitations",
            None,
        ),
        (
            "limitations",
            [],
        ),
        (
            "limitations",
            [
                "",
            ],
        ),
    ):
        case = copy.deepcopy(valid)

        case[field] = value

        validate(case)

    for section in quantitative_exports.REQUIRED_SECTIONS:
        case = copy.deepcopy(valid)

        case[section] = None

        validate(case)

    case = copy.deepcopy(valid)

    case["limitations"] = [
        "/" + "Users" + "/private/path",
    ]

    validate(case)

    case = copy.deepcopy(valid)

    case["execution_cost_delay"]["records"] = None

    validate(case)

    case = copy.deepcopy(valid)

    case["execution_cost_delay"]["records"] = []

    validate(case)

    case = copy.deepcopy(valid)

    case["placebo_test"]["metrics"] = None

    validate(case)

    case = copy.deepcopy(valid)

    case["placebo_test"]["metrics"] = {
        "invalid": {},
    }

    validate(case)

    case = copy.deepcopy(valid)

    first_metric = next(iter(case["placebo_test"]["metrics"]))

    case["placebo_test"]["metrics"][first_metric] = None

    validate(case)

    case = copy.deepcopy(valid)

    first_metric = next(iter(case["placebo_test"]["metrics"]))

    case["placebo_test"]["metrics"][first_metric]["observation_source"] = "invalid"

    validate(case)

    case = copy.deepcopy(valid)

    case["historical_block_monte_carlo"]["records"] = None

    validate(case)

    case = copy.deepcopy(valid)

    case["historical_block_monte_carlo"]["records"] = []

    validate(case)

    case = copy.deepcopy(valid)

    case["historical_block_monte_carlo"]["records"][0] = None

    validate(case)

    case = copy.deepcopy(valid)

    record = case["historical_block_monte_carlo"]["records"][0]

    record.pop(
        "simulation_length_days",
        None,
    )

    record["horizon_days"] = 10

    validate(case)

    case = copy.deepcopy(valid)

    case["shadow_monitoring"]["production_readiness_decision"] = "approved"

    case["shadow_monitoring"]["pilot_or_limited_production_approval"] = True

    validate(case)

    case = copy.deepcopy(valid)

    psr = case["probabilistic_sharpe_ratio"]

    psr["verification_level"] = "invalid"

    psr["observations"] = 0

    psr["probability"] = True

    validate(case)

    case = copy.deepcopy(valid)

    dsr = case["deflated_sharpe_ratio"]

    dsr["verification_level"] = "invalid"

    dsr["observations"] = 0

    dsr["trial_count"] = 0

    dsr["probability"] = 2.0

    validate(case)

    case = copy.deepcopy(valid)

    multiple = case["multiple_testing"]

    multiple["verification_level"] = "invalid"

    multiple["candidate_count"] = 0

    multiple["repetitions"] = 0

    multiple["private_matrix_disclosed"] = True

    multiple["finite_resampling_limitation"] = ""

    multiple["white_reality_check"] = None

    multiple["hansen_spa"]["reported_p_value"] = True

    validate(case)

    case = copy.deepcopy(valid)

    overfitting = case["backtest_overfitting"]

    overfitting["verification_level"] = "invalid"

    overfitting["candidate_count"] = 0

    overfitting["blocks"] = 0

    overfitting["tested_setting_count"] = 0

    overfitting["all_combinations_completed"] = False

    overfitting["exact_sensitivity_settings_disclosed"] = True

    overfitting["pbo_minimum"] = True

    overfitting["pbo_median"] = "invalid"

    overfitting["pbo_mean"] = None

    overfitting["pbo_maximum"] = []

    validate(case)

    case = copy.deepcopy(valid)

    overfitting = case["backtest_overfitting"]

    overfitting["pbo_minimum"] = 0.8

    overfitting["pbo_median"] = 0.2

    overfitting["pbo_mean"] = 0.9

    overfitting["pbo_maximum"] = 0.5

    validate(case)

    case = copy.deepcopy(valid)

    bootstrap = case["moving_block_bootstrap"]

    bootstrap["verification_level"] = "invalid"

    bootstrap["public_benchmark_set_reconciled"] = False

    bootstrap["benchmark_count"] = 0

    bootstrap["positive_cagr_differences"] = 0

    bootstrap["significant_at_5_percent"] = 0

    bootstrap["records"] = None

    validate(case)

    case = copy.deepcopy(valid)

    records = case["moving_block_bootstrap"]["records"]

    records[0]["benchmark"] = "INVALID"

    for row in records:
        row["cagr_difference"] = -1.0

        row["significant_compounded_outperformance"] = False

    validate(case)


def test_quantitative_export_invalid_checksum_line(
    tmp_path: Path,
) -> None:
    copied = tmp_path / "package"

    shutil.copytree(
        PACKAGE,
        copied,
    )

    checksum_path = copied / "SHA256SUMS"

    checksum_path.write_text(
        "invalid-line\n",
        encoding="utf-8",
    )

    issues = quantitative_exports.verify_public_quantitative_export(copied)

    assert "SHA256SUMS contains an invalid line" in issues


def test_publication_csv_private_header_detection(
    tmp_path: Path,
) -> None:
    root = tmp_path / "private-header"

    root.mkdir()

    path = root / "surface.csv"

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as stream:
        writer = csv.writer(stream)

        writer.writerow(
            [
                "date",
                "model_position",
            ]
        )

        writer.writerow(
            [
                "2026-01-01",
                "0.5",
            ]
        )

    issues = publication.scan_tree(root)

    assert any("private column forbidden" in issue for issue in issues)


def test_remaining_backtest_gross_accounting_branch() -> None:
    frame = pd.DataFrame(
        {
            "position": [1.0],
            "asset_return": [0.10],
            "transaction_cost": [0.01],
            "gross_strategy_return": [0.50],
            "strategy_return": [0.09],
        }
    )

    with pytest.raises(
        ValueError,
        match="Gross return",
    ):
        backtest_module.validate_accounting(frame)


def test_remaining_publication_filter_branches(
    tmp_path: Path,
) -> None:
    scan_root = tmp_path / "non-text"
    scan_root.mkdir()

    (scan_root / "opaque.bin").write_bytes(b"\x00\x01\x02")

    assert publication.scan_tree(scan_root) == []

    metrics, daily = _public_input_frames()

    daily["model_position_equity"] = [
        1.0,
        1.1,
    ]

    metrics_path, daily_path = _write_public_inputs(
        tmp_path / "private-curve-input",
        metrics=metrics,
        daily=daily,
    )

    output = tmp_path / "private-curve-release"

    publication.build_public_release(
        metrics_path,
        daily_path,
        output,
        private_artifact_sha256="a" * 64,
    )

    released_daily = pd.read_csv(output / "baseline_daily_curves.csv")

    assert "model_position_equity" not in released_daily.columns


def test_remaining_publication_absent_file_branches(
    tmp_path: Path,
) -> None:
    base = _build_valid_release(tmp_path / "base")

    filenames = (
        "benchmark_metrics.csv",
        "baseline_daily_curves.csv",
        "methodology.json",
        "nostra_artifact_commitment.json",
        "manifest.json",
    )

    for index, filename in enumerate(filenames):
        copied = tmp_path / f"missing-{index}"

        shutil.copytree(
            base,
            copied,
        )

        (copied / filename).unlink()

        issues = publication.verify_release(copied)

        assert any(
            filename in issue and "required release file missing" in issue for issue in issues
        )


def test_remaining_quantitative_checksum_read_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    copied = tmp_path / "package"

    shutil.copytree(
        PACKAGE,
        copied,
    )

    checksum_path = copied / "SHA256SUMS"
    original_read_text = Path.read_text

    def controlled_read_text(
        self: Path,
        *args: Any,
        **kwargs: Any,
    ) -> str:
        if self == checksum_path:
            raise OSError("controlled checksum read failure")

        return original_read_text(
            self,
            *args,
            **kwargs,
        )

    monkeypatch.setattr(
        Path,
        "read_text",
        controlled_read_text,
    )

    issues = quantitative_exports.verify_public_quantitative_export(copied)

    assert any("SHA256SUMS unreadable" in issue for issue in issues)
