import numpy as np

from hilmarbench.statistical_tests import (
    compounded_outperformance,
    cscv_pbo,
    deflated_sharpe_ratio,
    equity_to_returns,
    probabilistic_sharpe_ratio,
    purge_training_indices,
    reality_check_and_spa,
)


def test_probabilistic_sharpe_ratio() -> None:
    rng = np.random.default_rng(10)
    returns = rng.normal(0.0015, 0.015, 1_000)

    result = probabilistic_sharpe_ratio(returns)

    assert 0.0 <= result["probability"] <= 1.0
    assert result["observations"] == 1_000
    assert result["annualization"] == 365


def test_deflated_sharpe_ratio() -> None:
    rng = np.random.default_rng(11)
    returns = rng.normal(0.0015, 0.015, 1_000)
    trial_sharpes = np.linspace(-0.2, 1.4, 15)

    psr = probabilistic_sharpe_ratio(returns)
    dsr = deflated_sharpe_ratio(
        returns,
        trial_sharpes_annualized=trial_sharpes,
    )

    assert 0.0 <= dsr["probability"] <= 1.0
    assert dsr["trial_count"] == 15
    assert dsr["expected_maximum_sharpe"] > 0.0
    assert dsr["probability"] <= psr["probability"]


def test_reality_check_and_spa_are_deterministic() -> None:
    rng = np.random.default_rng(12)
    matrix = rng.normal(0.0002, 0.01, size=(300, 5))

    first = reality_check_and_spa(
        matrix,
        block_size=21,
        repetitions=200,
        seed=42,
    )
    second = reality_check_and_spa(
        matrix,
        block_size=21,
        repetitions=200,
        seed=42,
    )

    assert first == second

    for key in (
        "white_reality_check_pvalue",
        "hansen_spa_pvalue",
    ):
        assert 0.0 <= first[key] <= 1.0


def test_statistical_input_contracts() -> None:
    import pytest

    with pytest.raises(ValueError, match="three finite"):
        probabilistic_sharpe_ratio([0.01, 0.02])

    with pytest.raises(ValueError, match="positive variance"):
        probabilistic_sharpe_ratio([0.01, 0.01, 0.01])

    with pytest.raises(ValueError, match="annualization"):
        probabilistic_sharpe_ratio(
            [0.01, -0.01, 0.02],
            annualization=0,
        )

    returns = [0.01, -0.01, 0.02, -0.005]

    with pytest.raises(ValueError, match="two trial"):
        deflated_sharpe_ratio(returns, [1.0])

    with pytest.raises(ValueError, match="dispersion"):
        deflated_sharpe_ratio(returns, [1.0, 1.0])

    with pytest.raises(ValueError, match="two-dimensional"):
        reality_check_and_spa(np.ones(100))

    with pytest.raises(ValueError, match="Insufficient"):
        reality_check_and_spa(np.ones((5, 2)))

    with pytest.raises(ValueError, match="positive"):
        reality_check_and_spa(
            np.ones((100, 2)),
            block_size=0,
        )


def test_corrected_cscv_pbo_purge() -> None:
    train = np.array(
        list(range(0, 10)) + list(range(20, 30)) + list(range(40, 50)) + list(range(60, 70))
    )
    test = np.array(
        list(range(10, 20)) + list(range(30, 40)) + list(range(50, 60)) + list(range(70, 80))
    )

    purged = purge_training_indices(
        train,
        test,
        n_observations=80,
        purge=2,
    )

    assert len(purged) < len(train)

    for observation in purged:
        assert np.min(np.abs(test - observation)) > 2


def test_cscv_pbo_is_deterministic() -> None:
    rng = np.random.default_rng(20260730)
    matrix = rng.normal(size=(800, 15))

    first = cscv_pbo(matrix, n_blocks=8, purge=30)
    second = cscv_pbo(matrix, n_blocks=8, purge=30)

    assert first == second
    assert first["combinations"] == 70
    assert first["purge_observations"] == 30
    assert 0.0 <= first["pbo"] <= 1.0
    assert first["minimum_train_observations"] < 400


def test_equity_to_returns_reconstructs_curve() -> None:
    returns = np.array([0.10, -0.05, 0.02])
    equity = np.cumprod(1.0 + returns)

    reconstructed = equity_to_returns(equity)

    np.testing.assert_allclose(reconstructed, returns)


def test_compounded_outperformance_is_deterministic() -> None:
    strategy = np.full(300, 0.001)
    benchmark = np.zeros(300)

    first = compounded_outperformance(
        strategy,
        benchmark,
        block_size=21,
        repetitions=200,
        seed=42,
    )
    second = compounded_outperformance(
        strategy,
        benchmark,
        block_size=21,
        repetitions=200,
        seed=42,
    )

    assert first == second
    assert first["strategy_cagr"] > first["benchmark_cagr"]
    assert first["cagr_difference"] > 0
    assert first["ci95_lower_annualized_log"] > 0
    assert first["one_sided_p_value"] < 0.05
    assert first["significant_at_5pct"] is True


def test_purge_training_indices_contracts() -> None:
    import pytest

    train = np.arange(20)
    test = np.arange(20, 40)

    with pytest.raises(ValueError):
        purge_training_indices(
            train,
            test,
            n_observations=40,
            purge=-1,
        )

    np.testing.assert_array_equal(
        purge_training_indices(
            train,
            test,
            n_observations=40,
            purge=0,
        ),
        train,
    )

    empty = np.array([], dtype=int)

    np.testing.assert_array_equal(
        purge_training_indices(
            empty,
            test,
            n_observations=40,
            purge=5,
        ),
        empty,
    )

    np.testing.assert_array_equal(
        purge_training_indices(
            train,
            empty,
            n_observations=40,
            purge=5,
        ),
        train,
    )


def test_cscv_pbo_input_contracts() -> None:
    import pytest

    with pytest.raises(ValueError):
        cscv_pbo(np.ones(20))

    with pytest.raises(ValueError):
        cscv_pbo(np.ones((20, 1)))

    with pytest.raises(ValueError):
        cscv_pbo(
            np.ones((20, 2)),
            n_blocks=3,
        )

    with pytest.raises(ValueError):
        cscv_pbo(
            np.ones((4, 2)),
            n_blocks=6,
        )

    rng = np.random.default_rng(123)
    matrix = rng.normal(size=(80, 4))

    with pytest.raises(RuntimeError):
        cscv_pbo(
            matrix,
            n_blocks=8,
            purge=100,
        )


def test_equity_to_returns_contracts() -> None:
    import pytest

    with pytest.raises(ValueError):
        equity_to_returns([])

    with pytest.raises(ValueError):
        equity_to_returns([1.0, np.nan])

    with pytest.raises(ValueError):
        equity_to_returns([1.0, 0.0])


def test_compounded_outperformance_contracts() -> None:
    import pytest

    valid = np.zeros(30)

    with pytest.raises(ValueError):
        compounded_outperformance(
            np.zeros(30),
            np.zeros(29),
        )

    with pytest.raises(ValueError):
        compounded_outperformance(
            np.zeros(10),
            np.zeros(10),
            block_size=21,
        )

    with pytest.raises(ValueError):
        compounded_outperformance(
            valid,
            valid,
            annualization=0,
        )

    with pytest.raises(ValueError):
        compounded_outperformance(
            valid,
            valid,
            block_size=0,
        )

    with pytest.raises(ValueError):
        compounded_outperformance(
            valid,
            valid,
            repetitions=0,
        )

    non_finite = valid.copy()
    non_finite[0] = np.nan

    with pytest.raises(ValueError):
        compounded_outperformance(
            non_finite,
            valid,
        )

    invalid_return = valid.copy()
    invalid_return[0] = -1.0

    with pytest.raises(ValueError):
        compounded_outperformance(
            invalid_return,
            valid,
        )
