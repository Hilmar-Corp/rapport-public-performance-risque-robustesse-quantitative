"""Price-only Gaussian HMM evaluated using walk-forward filtering."""

from __future__ import annotations

import math
from itertools import pairwise
from typing import Any

import numpy as np
import pandas as pd


def _logsumexp(values: np.ndarray) -> float:
    maximum = float(np.max(values))
    return maximum + math.log(float(np.exp(values - maximum).sum()))


def _gaussian_log_probability(
    observation: np.ndarray,
    mean: np.ndarray,
    covariance: np.ndarray,
) -> float:
    dimension = len(observation)
    matrix = np.asarray(covariance, dtype=float) + np.eye(dimension) * 1e-6

    sign, log_determinant = np.linalg.slogdet(matrix)

    if sign <= 0:
        matrix = matrix + np.eye(dimension) * 1e-4
        sign, log_determinant = np.linalg.slogdet(matrix)

    difference = observation - mean
    inverse = np.linalg.pinv(matrix)
    quadratic = float(difference.T @ inverse @ difference)

    return -0.5 * (dimension * math.log(2.0 * math.pi) + log_determinant + quadratic)


def _filter_sequence(
    observations: np.ndarray,
    *,
    initial_probability: np.ndarray,
    transition_matrix: np.ndarray,
    means: np.ndarray,
    covariances: np.ndarray,
    transition_before_first: bool,
) -> tuple[np.ndarray, list[np.ndarray]]:
    probability = np.asarray(initial_probability, dtype=float)
    probability = probability / probability.sum()

    history: list[np.ndarray] = []

    for index, observation in enumerate(observations):
        if index > 0 or transition_before_first:
            prior = probability @ transition_matrix
        else:
            prior = probability

        prior = np.clip(prior, 1e-15, None)

        log_values = np.asarray(
            [
                math.log(float(prior[state]))
                + _gaussian_log_probability(
                    observation,
                    means[state],
                    covariances[state],
                )
                for state in range(len(prior))
            ]
        )

        normalizer = _logsumexp(log_values)
        probability = np.exp(log_values - normalizer)
        probability = probability / probability.sum()

        history.append(probability.copy())

    return probability, history


def walk_forward_hmm_exposure(
    asset_return: pd.Series,
    *,
    minimum_training_observations: int = 730,
    refit_frequency: int = 30,
    volatility_window: int = 20,
    random_seeds: tuple[int, ...] = (11, 29, 47),
) -> tuple[pd.Series, dict[str, Any]]:
    """Generate a three-state HMM exposure without future smoothing."""

    try:
        from hmmlearn.hmm import GaussianHMM
    except ImportError as exc:
        raise RuntimeError("hmmlearn is required for the HMM benchmark.") from exc

    returns = pd.to_numeric(asset_return, errors="coerce").astype(float)

    log_return = np.log1p(returns.clip(lower=-0.999999))

    trailing_volatility = log_return.rolling(
        volatility_window,
        min_periods=volatility_window,
    ).std(ddof=1) * math.sqrt(365.0)

    features = pd.DataFrame(
        {
            "log_return": log_return,
            "trailing_volatility": trailing_volatility,
        }
    ).dropna()

    if len(features) <= minimum_training_observations:
        raise ValueError("Insufficient history for HMM training.")

    signal = pd.Series(
        np.nan,
        index=features.index,
        dtype=float,
        name="hmm_3_state",
    )

    fit_count = 0
    failure_count = 0
    block_start = minimum_training_observations

    while block_start < len(features):
        block_end = min(
            block_start + refit_frequency,
            len(features),
        )

        training = features.iloc[:block_start]
        evaluation = features.iloc[block_start:block_end]

        mean = training.mean()
        standard_deviation = training.std(ddof=1).replace(0.0, 1.0)

        training_scaled = ((training - mean) / standard_deviation).to_numpy(dtype=float)

        evaluation_scaled = ((evaluation - mean) / standard_deviation).to_numpy(dtype=float)

        best_model = None
        best_score = -np.inf

        for seed in random_seeds:
            try:
                model = GaussianHMM(
                    n_components=3,
                    covariance_type="full",
                    n_iter=300,
                    tol=1e-4,
                    random_state=seed,
                    min_covar=1e-5,
                )

                model.fit(training_scaled)

                monitor = getattr(model, "monitor_", None)
                history = list(getattr(monitor, "history", []))

                monotonic = all(
                    current >= previous - 1e-6 for previous, current in pairwise(history)
                )

                if monitor is None or not monitor.converged or not monotonic:
                    failure_count += 1
                    continue

                score = float(model.score(training_scaled))

                if np.isfinite(score) and score > best_score:
                    best_model = model
                    best_score = score

            except Exception:
                failure_count += 1

        if best_model is None:
            block_start = block_end
            continue

        last_training_probability, _ = _filter_sequence(
            training_scaled,
            initial_probability=best_model.startprob_,
            transition_matrix=best_model.transmat_,
            means=best_model.means_,
            covariances=best_model.covars_,
            transition_before_first=False,
        )

        state_order = np.argsort(best_model.means_[:, 0])

        state_exposure = np.zeros(3, dtype=float)
        state_exposure[state_order[0]] = 0.0
        state_exposure[state_order[1]] = 0.5
        state_exposure[state_order[2]] = 1.0

        _, probabilities = _filter_sequence(
            evaluation_scaled,
            initial_probability=last_training_probability,
            transition_matrix=best_model.transmat_,
            means=best_model.means_,
            covariances=best_model.covars_,
            transition_before_first=True,
        )

        for timestamp, probability in zip(
            evaluation.index,
            probabilities,
            strict=True,
        ):
            signal.loc[timestamp] = float(probability @ state_exposure)

        fit_count += 1
        block_start = block_end

    signal = signal.dropna().clip(lower=0.0, upper=1.0)

    diagnostics = {
        "states": 3,
        "minimum_training_observations": minimum_training_observations,
        "refit_frequency": refit_frequency,
        "volatility_window": volatility_window,
        "fit_count": fit_count,
        "failure_count": failure_count,
        "signal_start": str(signal.index.min()) if not signal.empty else None,
        "signal_end": str(signal.index.max()) if not signal.empty else None,
    }

    return signal, diagnostics
