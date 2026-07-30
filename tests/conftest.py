from __future__ import annotations

import logging

import numpy as np
import pandas as pd
import pytest


@pytest.fixture(autouse=True)
def silence_external_hmm_logging() -> None:
    logging.getLogger("hmmlearn.base").setLevel(logging.ERROR)


@pytest.fixture
def daily_index() -> pd.DatetimeIndex:
    return pd.date_range(
        "2025-01-01",
        periods=10,
        freq="D",
        tz="UTC",
    )


@pytest.fixture
def deterministic_returns() -> pd.Series:
    index = pd.date_range(
        "2020-01-01",
        periods=1_000,
        freq="D",
        tz="UTC",
    )

    generator = np.random.default_rng(20260729)

    return pd.Series(
        generator.normal(
            loc=0.0004,
            scale=0.025,
            size=len(index),
        ),
        index=index,
        name="asset_return",
    )
