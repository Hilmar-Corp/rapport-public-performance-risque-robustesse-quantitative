from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from hilmarbench.hmm import (
    walk_forward_hmm_exposure,
)


@pytest.mark.slow
def test_future_data_does_not_change_past_hmm_signal() -> None:
    generator = np.random.default_rng(123)

    index = pd.date_range(
        "2020-01-01",
        periods=900,
        freq="D",
        tz="UTC",
    )

    original = pd.Series(
        generator.normal(
            loc=0.0003,
            scale=0.025,
            size=len(index),
        ),
        index=index,
    )

    modified = original.copy()
    cutoff = 780

    modified.iloc[cutoff:] = generator.normal(
        loc=-0.02,
        scale=0.09,
        size=len(modified) - cutoff,
    )

    original_signal, _ = walk_forward_hmm_exposure(
        original,
        minimum_training_observations=300,
        refit_frequency=30,
        random_seeds=(11,),
    )

    modified_signal, _ = walk_forward_hmm_exposure(
        modified,
        minimum_training_observations=300,
        refit_frequency=30,
        random_seeds=(11,),
    )

    common_index = original_signal.index.intersection(modified_signal.index)

    historical_index = common_index[common_index < index[cutoff]]

    assert len(historical_index) > 0

    pd.testing.assert_series_equal(
        original_signal.loc[historical_index],
        modified_signal.loc[historical_index],
        check_exact=False,
        rtol=1e-10,
        atol=1e-12,
    )
