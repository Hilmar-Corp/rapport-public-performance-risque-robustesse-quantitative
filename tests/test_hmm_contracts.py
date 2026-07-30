from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from hilmarbench.backtest import (
    BacktestConfig,
    run_backtest,
)
from hilmarbench.hmm import (
    walk_forward_hmm_exposure,
)


class StableGaussianHMM:
    def __init__(
        self,
        *args: object,
        **kwargs: object,
    ) -> None:
        self.startprob_ = np.array([1.0 / 3.0] * 3)

        self.transmat_ = np.array(
            [
                [0.90, 0.05, 0.05],
                [0.05, 0.90, 0.05],
                [0.05, 0.05, 0.90],
            ]
        )

        self.means_ = np.array(
            [
                [-1.0, 0.0],
                [0.0, 0.0],
                [1.0, 0.0],
            ]
        )

        self.covars_ = np.stack(
            [
                np.eye(2),
                np.eye(2),
                np.eye(2),
            ]
        )

        self.monitor_ = SimpleNamespace(
            converged=True,
            history=[0.0, 1.0],
        )

    def fit(
        self,
        values: np.ndarray,
    ) -> StableGaussianHMM:
        assert values.ndim == 2
        return self

    def score(
        self,
        values: np.ndarray,
    ) -> float:
        return float(-np.square(values).sum())


class UnstableGaussianHMM(StableGaussianHMM):
    def __init__(
        self,
        *args: object,
        **kwargs: object,
    ) -> None:
        super().__init__(
            *args,
            **kwargs,
        )

        self.monitor_ = SimpleNamespace(
            converged=False,
            history=[1.0, 0.0],
        )


def make_returns(
    observations: int = 400,
) -> pd.Series:
    generator = np.random.default_rng(91)

    return pd.Series(
        generator.normal(
            0.0004,
            0.02,
            observations,
        ),
        index=pd.date_range(
            "2020-01-01",
            periods=observations,
            freq="D",
            tz="UTC",
        ),
    )


def test_insufficient_hmm_history_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="Insufficient",
    ):
        walk_forward_hmm_exposure(
            make_returns(100),
            minimum_training_observations=100,
        )


def test_hmm_signal_respects_bounds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import hmmlearn.hmm

    monkeypatch.setattr(
        hmmlearn.hmm,
        "GaussianHMM",
        StableGaussianHMM,
    )

    signal, diagnostics = walk_forward_hmm_exposure(
        make_returns(),
        minimum_training_observations=100,
        refit_frequency=50,
        volatility_window=10,
        random_seeds=(1,),
    )

    assert not signal.empty

    assert (signal >= 0.0).all()

    assert (signal <= 1.0).all()

    assert diagnostics["fit_count"] > 0
    assert diagnostics["failure_count"] == 0


def test_hmm_is_deterministic_for_fixed_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import hmmlearn.hmm

    monkeypatch.setattr(
        hmmlearn.hmm,
        "GaussianHMM",
        StableGaussianHMM,
    )

    returns = make_returns()

    first_signal, first_diagnostics = walk_forward_hmm_exposure(
        returns,
        minimum_training_observations=100,
        refit_frequency=50,
        volatility_window=10,
        random_seeds=(1,),
    )

    second_signal, second_diagnostics = walk_forward_hmm_exposure(
        returns,
        minimum_training_observations=100,
        refit_frequency=50,
        volatility_window=10,
        random_seeds=(1,),
    )

    pd.testing.assert_series_equal(
        first_signal,
        second_signal,
    )

    assert first_diagnostics == second_diagnostics


def test_unstable_hmm_fits_are_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import hmmlearn.hmm

    monkeypatch.setattr(
        hmmlearn.hmm,
        "GaussianHMM",
        UnstableGaussianHMM,
    )

    signal, diagnostics = walk_forward_hmm_exposure(
        make_returns(),
        minimum_training_observations=100,
        refit_frequency=50,
        volatility_window=10,
        random_seeds=(1,),
    )

    assert signal.empty
    assert diagnostics["fit_count"] == 0
    assert diagnostics["failure_count"] > 0


def test_hmm_decision_is_applied_only_next_day(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import hmmlearn.hmm

    monkeypatch.setattr(
        hmmlearn.hmm,
        "GaussianHMM",
        StableGaussianHMM,
    )

    returns = make_returns()

    signal, _ = walk_forward_hmm_exposure(
        returns,
        minimum_training_observations=100,
        refit_frequency=50,
        volatility_window=10,
        random_seeds=(1,),
    )

    aligned_signal = signal.reindex(returns.index)

    result = run_backtest(
        returns,
        aligned_signal,
        execution_lag_days=1,
        config=BacktestConfig(
            cost_bps=0.0,
        ),
    )

    first_signal_date = signal.index[0]
    first_signal_location = returns.index.get_loc(first_signal_date)

    assert (
        result.loc[
            first_signal_date,
            "position",
        ]
        == 0.0
    )

    next_date = returns.index[first_signal_location + 1]

    assert result.loc[
        next_date,
        "position",
    ] == pytest.approx(signal.iloc[0])
