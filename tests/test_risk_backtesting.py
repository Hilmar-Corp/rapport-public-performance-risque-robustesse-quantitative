from __future__ import annotations

import numpy as np
import pytest

from hilmarbench.risk_backtesting import (
    christoffersen_conditional_coverage,
    christoffersen_independence,
    exact_binomial_coverage_p_value,
    exception_cluster_summary,
    expected_shortfall_calibration_test,
    kupiec_unconditional_coverage,
    validation_traffic_light,
)


def test_kupiec_matches_nominal_exception_frequency() -> None:
    exceptions = np.zeros(100, dtype=bool)
    exceptions[::20] = True

    result = kupiec_unconditional_coverage(
        exceptions,
        0.05,
    )

    assert result.statistic == pytest.approx(0.0)
    assert result.p_value == pytest.approx(1.0)


def test_kupiec_zero_exceptions_is_not_forced_to_zero() -> None:
    result = kupiec_unconditional_coverage(
        np.zeros(250, dtype=bool),
        0.01,
    )

    assert result.statistic > 0.0
    assert 0.0 < result.p_value < 1.0


def test_exact_binomial_coverage_at_nominal_rate() -> None:
    exceptions = np.zeros(100, dtype=bool)
    exceptions[::20] = True

    p_value = exact_binomial_coverage_p_value(
        exceptions,
        0.05,
    )

    assert p_value > 0.90


def test_christoffersen_detects_clustered_exceptions() -> None:
    exceptions = np.zeros(250, dtype=bool)
    exceptions[100:110] = True

    result = christoffersen_independence(
        exceptions,
    )

    assert result.n11 == 9
    assert result.p_value < 0.01


def test_conditional_coverage_is_sum_of_components() -> None:
    exceptions = np.zeros(250, dtype=bool)
    exceptions[[20, 40, 80, 120, 180]] = True

    unconditional = kupiec_unconditional_coverage(
        exceptions,
        0.02,
    )
    independence = christoffersen_independence(
        exceptions,
    )
    conditional = christoffersen_conditional_coverage(
        exceptions,
        0.02,
    )

    assert conditional.statistic == pytest.approx(unconditional.statistic + independence.statistic)
    assert conditional.degrees_of_freedom == 2


def test_exception_cluster_summary() -> None:
    exceptions = np.array(
        [
            0,
            1,
            1,
            0,
            0,
            1,
            0,
            1,
            1,
            1,
        ],
        dtype=bool,
    )

    summary = exception_cluster_summary(exceptions)

    assert summary.exception_count == 6
    assert summary.cluster_count == 3
    assert summary.maximum_cluster_length == 3
    assert summary.mean_cluster_length == pytest.approx(2.0)
    assert summary.minimum_gap_between_exceptions == 0


def test_es_calibration_accepts_exact_periodic_tail_mean() -> None:
    losses = np.tile(
        np.array([0.0, 0.0, 0.0, 4.0]),
        100,
    )
    var_forecasts = np.full(
        losses.size,
        1.0,
    )
    es_forecasts = np.full(
        losses.size,
        4.0,
    )

    result = expected_shortfall_calibration_test(
        losses,
        var_forecasts,
        es_forecasts,
        0.25,
        block_length=4,
        bootstrap_repetitions=999,
        seed=7,
    )

    assert result.statistic == pytest.approx(0.0)
    assert result.mean_tail_loss_to_es_ratio == pytest.approx(1.0)
    assert result.exceedances == 100
    assert result.p_value_underestimation > 0.05


def test_es_calibration_detects_material_underestimation() -> None:
    losses = np.tile(
        np.array([0.0, 0.0, 0.0, 4.0]),
        100,
    )
    var_forecasts = np.full(
        losses.size,
        1.0,
    )
    es_forecasts = np.full(
        losses.size,
        2.0,
    )

    result = expected_shortfall_calibration_test(
        losses,
        var_forecasts,
        es_forecasts,
        0.25,
        block_length=4,
        bootstrap_repetitions=999,
        seed=11,
    )

    assert result.statistic == pytest.approx(1.0)
    assert result.p_value_underestimation < 0.05


def test_es_forecast_below_var_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="greater than or equal",
    ):
        expected_shortfall_calibration_test(
            [0.0, 1.0, 2.0],
            [1.0, 1.0, 1.0],
            [0.5, 0.5, 0.5],
            0.05,
            bootstrap_repetitions=99,
        )


def test_green_traffic_light() -> None:
    decision = validation_traffic_light(
        p_values=[0.20, 0.30, 0.40],
        expected_exception_count=20.0,
    )

    assert decision.colour == "GREEN"
    assert decision.reason_codes == ("NO_FORMAL_REJECTION_AT_5_PERCENT",)


def test_low_power_downgrades_green_to_amber() -> None:
    decision = validation_traffic_light(
        p_values=[0.20, 0.30],
        expected_exception_count=2.5,
    )

    assert decision.colour == "AMBER"
    assert "LOW_EXPECTED_EXCEPTION_COUNT" in decision.reason_codes


def test_formal_rejection_at_one_percent_is_red() -> None:
    decision = validation_traffic_light(
        p_values=[0.20, 0.005],
        expected_exception_count=10.0,
    )

    assert decision.colour == "RED"
    assert decision.reason_codes == ("FORMAL_REJECTION_AT_1_PERCENT",)


@pytest.mark.parametrize(
    "exceptions, message",
    [
        ([], "must not be empty"),
        ([[0, 1]], "one-dimensional"),
        ([0.0, np.nan], "finite"),
        ([0, 2], "only zero or one"),
    ],
)
def test_invalid_exception_inputs_are_rejected(
    exceptions: object,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        kupiec_unconditional_coverage(
            exceptions,  # type: ignore[arg-type]
            0.05,
        )


@pytest.mark.parametrize(
    "probability",
    [0.0, 1.0, -0.1, 1.1],
)
def test_invalid_exception_probability_is_rejected(
    probability: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="strictly between",
    ):
        kupiec_unconditional_coverage(
            [0, 1, 0],
            probability,
        )


def test_independence_requires_two_observations() -> None:
    with pytest.raises(
        ValueError,
        match="at least two",
    ):
        christoffersen_independence([0])


def test_cluster_summary_with_no_exceptions() -> None:
    summary = exception_cluster_summary([0, 0, 0])

    assert summary.exception_count == 0
    assert summary.cluster_count == 0
    assert summary.maximum_cluster_length == 0
    assert summary.minimum_gap_between_exceptions is None


def test_cluster_summary_with_single_exception() -> None:
    summary = exception_cluster_summary([0, 1, 0])

    assert summary.exception_count == 1
    assert summary.cluster_count == 1
    assert summary.median_gap_between_exceptions is None


@pytest.mark.parametrize(
    "losses, var_values, es_values, probability, message",
    [
        (
            [0.0, 1.0],
            [1.0],
            [1.0, 1.0],
            0.05,
            "equal lengths",
        ),
        (
            [0.0, 1.0],
            [-1.0, 1.0],
            [1.0, 1.0],
            0.05,
            "non-negative",
        ),
        (
            [0.0, 1.0],
            [0.5, 0.5],
            [0.0, 1.0],
            0.05,
            "strictly positive",
        ),
        (
            [0.0, 1.0],
            [0.5, 0.5],
            [1.0, 1.0],
            0.0,
            "strictly between",
        ),
    ],
)
def test_es_calibration_invalid_inputs(
    losses: list[float],
    var_values: list[float],
    es_values: list[float],
    probability: float,
    message: str,
) -> None:
    with pytest.raises(
        ValueError,
        match=message,
    ):
        expected_shortfall_calibration_test(
            losses,
            var_values,
            es_values,
            probability,
            bootstrap_repetitions=99,
        )


def test_es_calibration_rejects_invalid_block_length() -> None:
    with pytest.raises(
        ValueError,
        match="block_length",
    ):
        expected_shortfall_calibration_test(
            [0.0, 1.0, 2.0],
            [0.5, 0.5, 0.5],
            [1.0, 1.0, 1.0],
            0.05,
            block_length=4,
            bootstrap_repetitions=99,
        )


def test_es_calibration_rejects_too_few_bootstraps() -> None:
    with pytest.raises(
        ValueError,
        match="at least 99",
    ):
        expected_shortfall_calibration_test(
            [0.0, 1.0, 2.0],
            [0.5, 0.5, 0.5],
            [1.0, 1.0, 1.0],
            0.05,
            block_length=1,
            bootstrap_repetitions=10,
        )


def test_amber_traffic_light_at_five_percent() -> None:
    decision = validation_traffic_light(
        p_values=[0.03, 0.20],
        expected_exception_count=10.0,
    )

    assert decision.colour == "AMBER"
    assert decision.reason_codes == ("FORMAL_REJECTION_AT_5_PERCENT",)


def test_traffic_light_rejects_invalid_inputs() -> None:
    with pytest.raises(
        ValueError,
        match="between zero and one",
    ):
        validation_traffic_light(
            p_values=[1.5],
            expected_exception_count=10.0,
        )

    with pytest.raises(
        ValueError,
        match="non-negative",
    ):
        validation_traffic_light(
            p_values=[0.5],
            expected_exception_count=-1.0,
        )
