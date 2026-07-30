from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from hilmarbench.backtest import (
    BacktestConfig,
    run_backtest,
)
from hilmarbench.hmm import (
    walk_forward_hmm_exposure,
)
from hilmarbench.metrics import (
    compute_performance_metrics,
)
from hilmarbench.strategies import (
    fixed_exposure,
    momentum_exposure,
    moving_average_exposure,
    prices_from_returns,
    volatility_target_exposure,
)

COST_BPS = 25.0
TARGET_VOLATILITY = 0.50

STRATEGY_ORDER = [
    "BUY_AND_HOLD",
    "FIXED_50",
    "MOMENTUM_30",
    "MOMENTUM_60",
    "MOMENTUM_90",
    "MOMENTUM_180",
    "MOMENTUM_270",
    "MA_50_200",
    "VOL_TARGET_14",
    "VOL_TARGET_30",
    "HMM_3_STATE_WALKFORWARD",
]

CURVE_NAMES = {
    "BUY_AND_HOLD": "buy_and_hold",
    "FIXED_50": "fixed_50",
    "MOMENTUM_30": "momentum_30",
    "MOMENTUM_60": "momentum_60",
    "MOMENTUM_90": "momentum_90",
    "MOMENTUM_180": "momentum_180",
    "MOMENTUM_270": "momentum_270",
    "MA_50_200": "ma_50_200",
    "VOL_TARGET_14": "vol_target_14",
    "VOL_TARGET_30": "vol_target_30",
    "HMM_3_STATE_WALKFORWARD": ("hmm_3_state_walkforward"),
}

METRIC_COLUMNS = [
    "strategy",
    "cost_bps",
    "date_start",
    "date_end",
    "observations",
    "final_equity",
    "total_return",
    "cagr",
    "annualized_volatility",
    "sharpe",
    "maximum_drawdown",
    "calmar",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Reproduce the committed public benchmark release from its canonical public input."
        )
    )

    parser.add_argument(
        "--release-dir",
        type=Path,
        default=Path("artifacts/latest"),
    )

    return parser.parse_args()


def reconstruct_asset_returns(
    curves: pd.DataFrame,
) -> pd.Series:
    equity = pd.to_numeric(
        curves["buy_and_hold_equity"],
        errors="raise",
    ).astype(float)

    returns = equity.pct_change()

    returns.iloc[0] = float(equity.iloc[0]) - 1.0 + COST_BPS / 10_000.0

    returns.index = pd.to_datetime(
        curves["timestamp"],
        utc=True,
        errors="raise",
    )

    returns.name = "asset_return"

    if returns.isna().any():
        raise ValueError("Reconstructed asset return contains missing values.")

    return returns


def build_decisions(
    returns: pd.Series,
) -> dict[str, tuple[pd.Series, int]]:
    price = prices_from_returns(returns)

    decisions: dict[
        str,
        tuple[pd.Series, int],
    ] = {
        "BUY_AND_HOLD": (
            fixed_exposure(
                returns.index,
                exposure=1.0,
            ),
            0,
        ),
        "FIXED_50": (
            fixed_exposure(
                returns.index,
                exposure=0.5,
            ),
            0,
        ),
    }

    for lookback in (
        30,
        60,
        90,
        180,
        270,
    ):
        decisions[f"MOMENTUM_{lookback}"] = (
            momentum_exposure(
                price,
                lookback=lookback,
            ),
            1,
        )

    decisions["MA_50_200"] = (
        moving_average_exposure(
            price,
            fast_window=50,
            slow_window=200,
        ),
        1,
    )

    for window in (
        14,
        30,
    ):
        decisions[f"VOL_TARGET_{window}"] = (
            volatility_target_exposure(
                returns,
                window=window,
                target_annualized_volatility=(TARGET_VOLATILITY),
                periods_per_year=365.0,
                minimum_exposure=0.0,
                maximum_exposure=1.0,
            ),
            1,
        )

    hmm_signal, diagnostics = walk_forward_hmm_exposure(
        returns,
        minimum_training_observations=730,
        refit_frequency=30,
        volatility_window=20,
        random_seeds=(
            11,
            29,
            47,
        ),
    )

    if diagnostics["fit_count"] <= 0:
        raise ValueError("The HMM reproduction accepted no fitted model.")

    decisions["HMM_3_STATE_WALKFORWARD"] = (
        hmm_signal.reindex(returns.index),
        1,
    )

    return decisions


def reproduce(
    returns: pd.Series,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    decisions = build_decisions(returns)

    config = BacktestConfig(
        cost_bps=COST_BPS,
        initial_equity=1.0,
        initial_position=0.0,
        minimum_position=0.0,
        maximum_position=1.0,
    )

    curves: dict[str, Any] = {
        "timestamp": returns.index,
    }

    metric_rows: list[dict[str, Any]] = []

    for strategy in STRATEGY_ORDER:
        decision, lag = decisions[strategy]

        frame = run_backtest(
            returns,
            decision.reindex(returns.index),
            execution_lag_days=lag,
            config=config,
        )

        curve_name = CURVE_NAMES[strategy]

        curves[f"{curve_name}_equity"] = frame["equity"].to_numpy()

        curves[f"{curve_name}_drawdown"] = frame["drawdown"].to_numpy()

        metrics = compute_performance_metrics(
            frame["strategy_return"],
            equity=frame["equity"],
            drawdown=frame["drawdown"],
            position=frame["position"],
            turnover=frame["turnover"],
            transaction_cost=(frame["transaction_cost"]),
            periods_per_year=365.0,
        )

        metric_rows.append(
            {
                "strategy": strategy,
                "cost_bps": COST_BPS,
                **{
                    key: metrics[key]
                    for key in METRIC_COLUMNS
                    if key
                    not in {
                        "strategy",
                        "cost_bps",
                    }
                },
            }
        )

    return (
        pd.DataFrame(curves),
        pd.DataFrame(
            metric_rows,
            columns=METRIC_COLUMNS,
        ),
    )


def compare_curves(
    expected: pd.DataFrame,
    actual: pd.DataFrame,
) -> None:
    if list(expected.columns) != list(actual.columns):
        raise AssertionError(
            "Curve schemas differ.\n"
            f"Expected: {list(expected.columns)}\n"
            f"Actual:   {list(actual.columns)}"
        )

    expected_dates = pd.to_datetime(
        expected["timestamp"],
        utc=True,
        errors="raise",
    )

    actual_dates = pd.to_datetime(
        actual["timestamp"],
        utc=True,
        errors="raise",
    )

    pd.testing.assert_index_equal(
        pd.Index(expected_dates),
        pd.Index(actual_dates),
        exact=True,
    )

    for column in expected.columns:
        if column == "timestamp":
            continue

        expected_values = pd.to_numeric(
            expected[column],
            errors="raise",
        ).to_numpy(dtype=float)

        actual_values = pd.to_numeric(
            actual[column],
            errors="raise",
        ).to_numpy(dtype=float)

        if column.startswith("hmm_3_state"):
            relative_tolerance = 5e-6
            absolute_tolerance = 5e-8
        else:
            relative_tolerance = 1e-10
            absolute_tolerance = 1e-12

        np.testing.assert_allclose(
            actual_values,
            expected_values,
            rtol=relative_tolerance,
            atol=absolute_tolerance,
            equal_nan=True,
            err_msg=(f"Curve reproduction failed: {column}"),
        )


def compare_metrics(
    expected: pd.DataFrame,
    actual: pd.DataFrame,
) -> None:
    expected = expected.loc[
        expected["strategy"].isin(STRATEGY_ORDER),
        METRIC_COLUMNS,
    ].reset_index(drop=True)

    actual = actual.loc[
        :,
        METRIC_COLUMNS,
    ].reset_index(drop=True)

    if list(expected["strategy"]) != list(actual["strategy"]):
        raise AssertionError("Metric strategy order differs.")

    for column in (
        "strategy",
        "date_start",
        "date_end",
    ):
        if list(expected[column].astype(str)) != list(actual[column].astype(str)):
            raise AssertionError(f"Metric field differs: {column}")

    if not np.array_equal(
        expected["observations"].to_numpy(dtype=int),
        actual["observations"].to_numpy(dtype=int),
    ):
        raise AssertionError("Metric observations differ.")

    for column in (
        "cost_bps",
        "final_equity",
        "total_return",
        "cagr",
        "annualized_volatility",
        "sharpe",
        "maximum_drawdown",
        "calmar",
    ):
        expected_values = pd.to_numeric(
            expected[column],
            errors="raise",
        ).to_numpy(dtype=float)

        actual_values = pd.to_numeric(
            actual[column],
            errors="raise",
        ).to_numpy(dtype=float)

        np.testing.assert_allclose(
            actual_values,
            expected_values,
            rtol=5e-6,
            atol=5e-8,
            equal_nan=True,
            err_msg=(f"Metric reproduction failed: {column}"),
        )


def main() -> None:
    args = parse_args()
    release = args.release_dir.resolve()

    expected_curves = pd.read_csv(release / "baseline_daily_curves.csv")

    expected_metrics = pd.read_csv(release / "benchmark_metrics.csv")

    returns = reconstruct_asset_returns(expected_curves)

    actual_curves, actual_metrics = reproduce(returns)

    compare_curves(
        expected_curves,
        actual_curves,
    )

    compare_metrics(
        expected_metrics,
        actual_metrics,
    )

    nostra = expected_metrics.loc[
        expected_metrics["strategy"].astype(str).str.upper() == "NOSTRA_AI"
    ]

    if len(nostra) != 1:
        raise AssertionError("The release must contain one Nostra aggregate row.")

    if nostra.iloc[0]["verification_level"] != "artifact-verified":
        raise AssertionError("Nostra must remain artifact-verified.")

    print("REFERENCE RELEASE REPRODUCTION PASSED")
    print(f"Release: {release}")
    print(f"Observations: {len(returns)}")
    print(f"Public strategies reproduced: {len(STRATEGY_ORDER)}")
    print("Nostra status: aggregate artifact-verified")


if __name__ == "__main__":
    main()
