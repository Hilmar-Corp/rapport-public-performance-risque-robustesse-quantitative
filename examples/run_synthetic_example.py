"""Run a code-path smoke test on stationary synthetic returns."""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from hilmarbench.backtest import (
    BacktestConfig,
    run_backtest,
    validate_accounting,
)
from hilmarbench.hmm import walk_forward_hmm_exposure
from hilmarbench.strategies import (
    fixed_exposure,
    momentum_exposure,
    moving_average_exposure,
    prices_from_returns,
    volatility_target_exposure,
)


def main() -> None:
    """Exercise every public benchmark without making performance claims."""

    logging.getLogger("hmmlearn.base").setLevel(logging.ERROR)

    generator = np.random.default_rng(7)

    index = pd.date_range(
        "2018-01-01",
        periods=2_500,
        freq="D",
        tz="UTC",
    )

    returns = pd.Series(
        generator.normal(
            loc=0.0003,
            scale=0.025,
            size=len(index),
        ),
        index=index,
        name="asset_return",
    )

    price = prices_from_returns(returns)

    strategies: dict[str, tuple[pd.Series, int]] = {
        "buy_and_hold": (
            fixed_exposure(index, exposure=1.0),
            0,
        ),
        "fixed_50": (
            fixed_exposure(index, exposure=0.5),
            0,
        ),
        "momentum_90": (
            momentum_exposure(price, lookback=90),
            1,
        ),
        "ma_50_200": (
            moving_average_exposure(
                price,
                fast_window=50,
                slow_window=200,
            ),
            1,
        ),
        "vol_target_30": (
            volatility_target_exposure(
                returns,
                window=30,
                target_annualized_volatility=0.30,
            ),
            1,
        ),
    }

    hmm_signal, hmm_diagnostics = walk_forward_hmm_exposure(
        returns,
        minimum_training_observations=730,
        refit_frequency=30,
    )

    strategies["hmm_3_state"] = (
        hmm_signal.reindex(index),
        1,
    )

    rows = []

    for name, (decision, lag) in strategies.items():
        result = run_backtest(
            returns,
            decision,
            execution_lag_days=lag,
            config=BacktestConfig(cost_bps=25.0),
        )

        validate_accounting(result)

        rows.append(
            {
                "strategy": name,
                "status": "PASS",
                "observations": len(result),
                "first_equity": float(result["equity"].iloc[0]),
                "last_equity": float(result["equity"].iloc[-1]),
            }
        )

    print("SYNTHETIC SMOKE TEST - NO EMPIRICAL OR PERFORMANCE SIGNIFICANCE")
    print()
    print(pd.DataFrame(rows).to_string(index=False))
    print()
    print(
        "HMM fits accepted:",
        hmm_diagnostics["fit_count"],
    )
    print(
        "HMM fits rejected:",
        hmm_diagnostics["failure_count"],
    )


if __name__ == "__main__":
    main()
