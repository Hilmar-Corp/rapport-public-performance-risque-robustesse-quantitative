"""Public-safe quantitative aggregate export packaging."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any, TypeGuard, cast

SCHEMA_VERSION = 2
EXPORT_SCHEMA_VERSION = 1

REQUIRED_SECTIONS = (
    "stationarity",
    "distribution_drift",
    "market_regimes",
    "execution_cost_delay",
    "placebo_test",
    "tail_risk",
    "historical_reverse_stress",
    "var_es_backtesting",
    "historical_block_monte_carlo",
    "data_resilience",
    "configuration_sensitivity",
    "ablation",
    "shadow_monitoring",
    "probabilistic_sharpe_ratio",
    "deflated_sharpe_ratio",
    "temporal_dependence_sharpe",
    "multiple_testing",
    "backtest_overfitting",
    "moving_block_bootstrap",
)

METADATA_FIELDS = (
    "schema_version",
    "release_target",
    "classification",
    "limitations",
)

FORBIDDEN_PUBLIC_FRAGMENTS = (
    "/users/",
    "private_working_copy",
    "dossier_interne_complet",
    "quantitative_corpus_original",
    "p_up",
    "position",
    "exposure",
    "feature",
    "variant",
    "threshold",
    "coefficient",
    "parameter",
    "source_trace",
    "source_ledger",
    "source_sha",
    "learning_rate",
    "regularization",
    "min_train",
    "test_window",
    "purge",
    "horizon_days",
    "lth_sopr",
    "mvrv",
    "nupl",
    "asopr",
)

PAYLOAD_FILENAMES = {
    "stationarity": "stationarity.json",
    "distribution_drift": "distribution_drift.json",
    "market_regimes": "market_regimes.json",
    "execution_cost_delay": "execution_cost_delay.json",
    "placebo_test": "placebo_test.json",
    "tail_risk": "tail_risk.json",
    "historical_reverse_stress": "historical_reverse_stress.json",
    "var_es_backtesting": "var_es_backtesting.json",
    "historical_block_monte_carlo": "historical_block_monte_carlo.json",
    "data_resilience": "data_resilience.json",
    "configuration_sensitivity": "configuration_sensitivity.json",
    "ablation": "ablation.json",
    "shadow_monitoring": "shadow_monitoring.json",
    "probabilistic_sharpe_ratio": "probabilistic_sharpe_ratio.json",
    "deflated_sharpe_ratio": "deflated_sharpe_ratio.json",
    "temporal_dependence_sharpe": "temporal_dependence_sharpe.json",
    "multiple_testing": "multiple_testing.json",
    "backtest_overfitting": "backtest_overfitting.json",
    "moving_block_bootstrap": "moving_block_bootstrap.json",
}

CONTROLLED_FILENAMES = {
    "metadata.json",
    *PAYLOAD_FILENAMES.values(),
    "manifest.json",
    "SHA256SUMS",
}


def _canonical_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for block in iter(
            lambda: stream.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def _validate_historical_reverse_stress(
    section: Any,
) -> list[str]:
    """Validate historical loss-breach evidence."""

    issues: list[str] = []

    if not isinstance(section, dict):
        return ["historical_reverse_stress must be a JSON object"]

    expected_scalars = {
        "verification_level": "artifact-verified",
        "methodological_status": "accepted_with_observations",
        "decision_status": "PASS_WITH_OBSERVATION",
        "analysis_type": ("historical_dynamic_loss_breach_analysis"),
        "observations": 2211,
    }

    for field, expected in expected_scalars.items():
        if section.get(field) != expected:
            issues.append(f"historical_reverse_stress.{field} must equal {expected}")

    if section.get("evaluation_period") != {
        "start": "2020-05-14",
        "end": "2026-06-02",
    }:
        issues.append("historical_reverse_stress evaluation period is invalid")

    conventions = section.get("governing_conventions")

    if (
        not isinstance(conventions, list)
        or not conventions
        or not all(isinstance(item, str) and item for item in conventions)
    ):
        issues.append(
            "historical_reverse_stress governing conventions must be a non-empty string list"
        )

    reconciliation = section.get("economic_reconciliation")

    if not isinstance(reconciliation, dict):
        issues.append("historical_reverse_stress economic reconciliation must be an object")
    else:
        if reconciliation.get("status") != "PASS":
            issues.append("historical_reverse_stress economic reconciliation must pass")

        if reconciliation.get("public_convention_name") != "row_aligned_effective_allocation":
            issues.append("historical_reverse_stress public economic convention is invalid")

        delta = reconciliation.get("maximum_absolute_delta")

        if (
            not isinstance(delta, int | float)
            or isinstance(delta, bool)
            or not 0.0 <= float(delta) <= 1e-12
        ):
            issues.append("historical_reverse_stress economic reconciliation delta is invalid")

    global_results = section.get("global_results")

    if not isinstance(global_results, dict):
        issues.append("historical_reverse_stress global results must be an object")
    else:
        if global_results.get("drawdown_episode_count") != 104:
            issues.append("historical_reverse_stress drawdown episode count must equal 104")

        if global_results.get("loss_breach_record_count") != 40:
            issues.append("historical_reverse_stress loss-breach record count must equal 40")

        maximum_drawdown = global_results.get("maximum_model_drawdown")

        if (
            not isinstance(
                maximum_drawdown,
                int | float,
            )
            or isinstance(
                maximum_drawdown,
                bool,
            )
            or not math.isclose(
                float(maximum_drawdown),
                -0.2139050350373155,
                rel_tol=0.0,
                abs_tol=1e-12,
            )
        ):
            issues.append("historical_reverse_stress maximum drawdown is invalid")

    results = section.get("loss_level_results")

    if not isinstance(results, list):
        issues.append("historical_reverse_stress loss-level results must be a list")
        results = []

    expected_counts = {
        0.05: 25,
        0.10: 10,
        0.15: 4,
        0.20: 1,
        0.25: 0,
        0.30: 0,
    }
    actual_counts: dict[float, int] = {}

    for index, record in enumerate(results):
        if not isinstance(record, dict):
            issues.append(f"historical_reverse_stress loss-level record {index} must be an object")
            continue

        raw_loss = record.get("target_nav_loss")
        raw_count = record.get("breach_episode_count")

        if (
            not isinstance(raw_loss, int | float)
            or isinstance(raw_loss, bool)
            or not isinstance(raw_count, int)
            or isinstance(raw_count, bool)
        ):
            issues.append(
                f"historical_reverse_stress loss-level record {index} has invalid identifiers"
            )
            continue

        loss = float(raw_loss)
        count = raw_count
        actual_counts[loss] = count

        if loss not in expected_counts:
            issues.append("historical_reverse_stress contains an unexpected loss level")
            continue

        if count != expected_counts[loss]:
            issues.append(f"historical_reverse_stress loss-level count is invalid for {loss}")

        breached = record.get("historically_breached")

        if breached is not (count > 0):
            issues.append("historical_reverse_stress historical breach flag is inconsistent")

        if count == 0:
            if record.get("observed_non_breach_is_not_a_bound") is not True:
                issues.append("historical_reverse_stress non-breach limitation must be disclosed")
            continue

        reactions = record.get("allocation_reaction_counts")

        if not isinstance(reactions, dict):
            issues.append("historical_reverse_stress allocation reaction counts must be an object")
            continue

        reduced = reactions.get("reduced_at_breach")
        increased = reactions.get("increased_at_breach")
        unchanged = reactions.get("unchanged_at_breach")
        reduced_early = reactions.get("reduced_by_at_least_25pct_before_breach")

        reaction_values = (
            reduced,
            increased,
            unchanged,
            reduced_early,
        )

        if not all(
            isinstance(value, int) and not isinstance(value, bool) and value >= 0
            for value in reaction_values
        ):
            issues.append("historical_reverse_stress allocation reaction counts are invalid")
        elif (
            cast(int, reduced) + cast(int, increased) + cast(int, unchanged) != count
            or cast(int, reduced_early) > count
        ):
            issues.append("historical_reverse_stress allocation reaction counts do not reconcile")

        shares = record.get("allocation_reaction_shares")

        if not isinstance(shares, dict):
            issues.append("historical_reverse_stress allocation reaction shares must be an object")
        else:
            for name, value in shares.items():
                if (
                    not isinstance(
                        value,
                        int | float,
                    )
                    or isinstance(value, bool)
                    or not 0.0 <= float(value) <= 1.0
                ):
                    issues.append(f"historical_reverse_stress allocation share {name} is invalid")

    if actual_counts != expected_counts:
        issues.append("historical_reverse_stress loss-level coverage is invalid")

    governance = section.get("governance_decision")

    if not isinstance(governance, dict):
        issues.append("historical_reverse_stress governance decision must be an object")
    elif governance.get("status") != "PASS_WITH_OBSERVATION":
        issues.append("historical_reverse_stress governance status is invalid")

    limitations = section.get("limitations")

    if (
        not isinstance(limitations, list)
        or not limitations
        or not all(isinstance(item, str) and item for item in limitations)
    ):
        issues.append("historical_reverse_stress limitations must be a non-empty string list")

    commitment = section.get("evidence_commitment_sha256")

    if commitment != "83b47296d8eee4da8629cd2ef65a8a9f906fbc77a5b0b7aba3b254ec66710f62":
        issues.append("historical_reverse_stress evidence commitment is invalid")

    return issues


def _validate_var_es_backtesting(
    section: Any,
) -> list[str]:
    """Validate the controlled public VaR/ES backtesting section."""

    issues: list[str] = []

    if not isinstance(section, dict):
        return ["var_es_backtesting must be a JSON object"]

    expected_scalars = {
        "verification_level": "artifact-verified",
        "methodological_status": "accepted_with_observations",
        "decision_status": "PASS_WITH_OBSERVATION",
        "observations": 2211,
        "canonical_calibration_window_days": 365,
    }

    for field, expected in expected_scalars.items():
        if section.get(field) != expected:
            issues.append(f"var_es_backtesting.{field} must equal {expected}")

    if section.get("sensitivity_calibration_windows_days") != [250, 365, 500]:
        issues.append("var_es_backtesting sensitivity windows must equal 250, 365 and 500 days")

    if section.get("risk_periods_days") != [1, 10]:
        issues.append("var_es_backtesting horizons must equal 1 and 10 days")

    if section.get("confidence_levels") != [0.95, 0.99]:
        issues.append("var_es_backtesting confidence levels must equal 0.95 and 0.99")

    results = section.get("canonical_results")

    if not isinstance(results, list):
        issues.append("var_es_backtesting.canonical_results must be a list")
        results = []

    if len(results) != 4:
        issues.append("var_es_backtesting canonical result count must equal 4")

    required_p_values = (
        "kupiec_p_value",
        "exact_binomial_p_value",
        "christoffersen_independence_p_value",
        "christoffersen_conditional_coverage_p_value",
        ("es_normalized_tail_loss_bootstrap_p_value"),
    )

    expected_combinations = {
        (1, 0.95),
        (1, 0.99),
        (10, 0.95),
        (10, 0.99),
    }

    combinations: set[tuple[int, float]] = set()
    computed_counts = {
        "GREEN": 0,
        "AMBER": 0,
        "RED": 0,
    }

    for index, record in enumerate(results):
        if not isinstance(record, dict):
            issues.append(f"var_es_backtesting canonical record {index} must be an object")
            continue

        horizon = record.get("risk_period_days")
        confidence = record.get("confidence_level")

        if (
            isinstance(horizon, int)
            and not isinstance(horizon, bool)
            and isinstance(
                confidence,
                (int, float),
            )
            and not isinstance(confidence, bool)
        ):
            combinations.add(
                (
                    horizon,
                    float(confidence),
                )
            )
        else:
            issues.append(
                f"var_es_backtesting canonical record {index} has invalid horizon or confidence"
            )

        for field in required_p_values:
            value = record.get(field)

            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not 0.0 <= float(value) <= 1.0
            ):
                issues.append(f"var_es_backtesting canonical record {index} has invalid {field}")

        light = record.get("traffic_light")

        if light not in computed_counts:
            issues.append(f"var_es_backtesting canonical record {index} has invalid traffic_light")
        else:
            computed_counts[light] += 1

        reasons = record.get("reason_codes")

        if (
            not isinstance(reasons, list)
            or not reasons
            or not all(isinstance(reason, str) and reason for reason in reasons)
        ):
            issues.append(f"var_es_backtesting canonical record {index} has invalid reason_codes")

        for count_field in (
            "observations",
            "exception_count",
            "expected_exception_count",
            "exception_rate",
            "exception_cluster_count",
            "maximum_exception_cluster_length",
        ):
            value = record.get(count_field)

            if not isinstance(value, (int, float)) or isinstance(value, bool) or float(value) < 0.0:
                issues.append(
                    f"var_es_backtesting canonical record {index} has invalid {count_field}"
                )

    if combinations != expected_combinations:
        issues.append(
            "var_es_backtesting canonical horizon and confidence combinations are invalid"
        )

    expected_canonical_counts = {
        "GREEN": 3,
        "AMBER": 1,
        "RED": 0,
    }

    if section.get("canonical_traffic_light_counts") != expected_canonical_counts:
        issues.append("var_es_backtesting canonical traffic-light counts are invalid")

    if computed_counts != expected_canonical_counts:
        issues.append(
            "var_es_backtesting canonical records do not reconcile with traffic-light counts"
        )

    if section.get("all_sensitivity_traffic_light_counts") != {
        "GREEN": 7,
        "AMBER": 4,
        "RED": 1,
    }:
        issues.append("var_es_backtesting sensitivity traffic-light counts are invalid")

    commitment = section.get("evidence_commitment_sha256")

    if (
        not isinstance(commitment, str)
        or len(commitment) != 64
        or any(character not in "0123456789abcdef" for character in commitment)
    ):
        issues.append("var_es_backtesting evidence commitment must be a lowercase SHA-256 digest")

    limitations = section.get("limitations")

    if (
        not isinstance(limitations, list)
        or not limitations
        or not all(isinstance(item, str) and item for item in limitations)
    ):
        issues.append("var_es_backtesting limitations must be a non-empty string list")

    return issues


def _validate_temporal_dependence_sharpe(
    payload: Mapping[str, Any],
    issues: list[str],
) -> None:
    section = payload.get("temporal_dependence_sharpe")

    if not isinstance(section, dict):
        issues.append("temporal_dependence_sharpe must be an object")
        return

    def finite_number(
        value: object,
    ) -> TypeGuard[int | float]:
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(float(value))
        )

    if section.get("verification_level") != "artifact-verified":
        issues.append("temporal_dependence_sharpe must be artifact-verified")

    if section.get("methodological_status") != "accepted_with_observations":
        issues.append(
            "temporal_dependence_sharpe methodological_status must equal accepted_with_observations"
        )

    if section.get("decision_status") != "PASS_WITH_OBSERVATION":
        issues.append("temporal_dependence_sharpe decision_status must equal PASS_WITH_OBSERVATION")

    if section.get("observations") != 2211:
        issues.append("temporal_dependence_sharpe observations must equal 2211")

    if section.get("annualization") != 365:
        issues.append("temporal_dependence_sharpe annualization must equal 365")

    conventional = section.get("conventional_annualized_sharpe")

    if not finite_number(conventional) or abs(float(conventional) - 1.587687113383514) > 1e-12:
        issues.append("temporal_dependence_sharpe conventional Sharpe is invalid")

    if section.get("automatic_lag_rule") != "floor(4*(n/100)^(2/9))":
        issues.append("temporal_dependence_sharpe automatic lag rule is invalid")

    if section.get("automatic_lag_count") != 7:
        issues.append("temporal_dependence_sharpe automatic lag count must equal 7")

    if section.get("canonical_hac_lag_count") != 21:
        issues.append("temporal_dependence_sharpe canonical HAC lag count must equal 21")

    if section.get("canonical_block_size") != 21:
        issues.append("temporal_dependence_sharpe canonical block size must equal 21")

    canonical_hac = section.get("canonical_hac_adjusted_annualized_sharpe")
    canonical_inflation = section.get("canonical_volatility_inflation_factor")

    if (
        not finite_number(canonical_hac)
        or float(canonical_hac) <= 0.0
        or (finite_number(conventional) and float(canonical_hac) >= float(conventional))
    ):
        issues.append("temporal_dependence_sharpe canonical HAC Sharpe is invalid")

    if not finite_number(canonical_inflation) or float(canonical_inflation) <= 1.0:
        issues.append("temporal_dependence_sharpe canonical volatility inflation is invalid")

    autocorrelation_records = section.get("autocorrelation_records")
    expected_acf_lags = {
        1,
        5,
        10,
        21,
        30,
        60,
    }
    observed_acf_lags: set[int] = set()

    if not isinstance(
        autocorrelation_records,
        list,
    ):
        issues.append("temporal_dependence_sharpe autocorrelation_records must be a list")
    else:
        for record in autocorrelation_records:
            if not isinstance(record, dict):
                issues.append(
                    "temporal_dependence_sharpe contains an invalid autocorrelation record"
                )
                continue

            lag = record.get("lag_count")
            correlation = record.get("autocorrelation")

            if not isinstance(lag, int) or isinstance(lag, bool):
                issues.append("temporal_dependence_sharpe contains an invalid autocorrelation lag")
            else:
                observed_acf_lags.add(lag)

            if not finite_number(correlation) or not -1.0 <= float(correlation) <= 1.0:
                issues.append(
                    "temporal_dependence_sharpe contains an invalid autocorrelation value"
                )

        if observed_acf_lags != expected_acf_lags:
            issues.append("temporal_dependence_sharpe autocorrelation lag set is invalid")

    ljung_box_records = section.get("ljung_box_records")
    expected_ljung_box_pairs = {
        ("periodic_returns", 5),
        ("periodic_returns", 10),
        ("periodic_returns", 21),
        ("periodic_returns", 30),
        (
            "squared_centered_periodic_returns",
            5,
        ),
        (
            "squared_centered_periodic_returns",
            10,
        ),
        (
            "squared_centered_periodic_returns",
            21,
        ),
        (
            "squared_centered_periodic_returns",
            30,
        ),
    }
    observed_ljung_box_pairs: set[tuple[str, int]] = set()

    if not isinstance(ljung_box_records, list):
        issues.append("temporal_dependence_sharpe ljung_box_records must be a list")
    else:
        for record in ljung_box_records:
            if not isinstance(record, dict):
                issues.append("temporal_dependence_sharpe contains an invalid Ljung-Box record")
                continue

            series = record.get("series")
            lag = record.get("lag_count")
            statistic = record.get("statistic")
            p_value = record.get("p_value")
            underflow = record.get("p_value_below_machine_precision")

            if isinstance(series, str) and isinstance(lag, int) and not isinstance(lag, bool):
                observed_ljung_box_pairs.add(
                    (
                        series,
                        lag,
                    )
                )
            else:
                issues.append("temporal_dependence_sharpe contains an invalid Ljung-Box identifier")

            if not finite_number(statistic) or float(statistic) < 0.0:
                issues.append("temporal_dependence_sharpe contains an invalid Ljung-Box statistic")

            if not finite_number(p_value) or not 0.0 <= float(p_value) <= 1.0:
                issues.append("temporal_dependence_sharpe contains an invalid Ljung-Box p-value")

            if not isinstance(underflow, bool):
                issues.append(
                    "temporal_dependence_sharpe contains an invalid p-value underflow flag"
                )

        if observed_ljung_box_pairs != expected_ljung_box_pairs:
            issues.append("temporal_dependence_sharpe Ljung-Box combinations are invalid")

    hac_records = section.get("hac_sensitivity_records")
    expected_hac_lags = {
        5,
        7,
        10,
        21,
        30,
        60,
    }
    observed_hac_lags: set[int] = set()

    if not isinstance(hac_records, list):
        issues.append("temporal_dependence_sharpe hac_sensitivity_records must be a list")
    else:
        for record in hac_records:
            if not isinstance(record, dict):
                issues.append("temporal_dependence_sharpe contains an invalid HAC record")
                continue

            lag = record.get("lag_count")
            sharpe = record.get("hac_adjusted_annualized_sharpe")
            inflation = record.get("volatility_inflation_factor")

            if not isinstance(lag, int) or isinstance(lag, bool):
                issues.append("temporal_dependence_sharpe contains an invalid HAC lag")
            else:
                observed_hac_lags.add(lag)

            if not finite_number(sharpe) or float(sharpe) <= 0.0:
                issues.append("temporal_dependence_sharpe contains an invalid HAC Sharpe")

            if not finite_number(inflation) or float(inflation) <= 0.0:
                issues.append("temporal_dependence_sharpe contains an invalid HAC inflation factor")

        if observed_hac_lags != expected_hac_lags:
            issues.append("temporal_dependence_sharpe HAC sensitivity lag set is invalid")

    if section.get("bootstrap_repetitions") != 2000:
        issues.append("temporal_dependence_sharpe bootstrap repetitions must equal 2000")

    bootstrap_records = section.get("bootstrap_sensitivity_records")
    expected_block_sizes = {
        5,
        10,
        21,
        30,
        60,
    }
    observed_block_sizes: set[int] = set()

    if not isinstance(bootstrap_records, list):
        issues.append("temporal_dependence_sharpe bootstrap sensitivity records must be a list")
    else:
        for record in bootstrap_records:
            if not isinstance(record, dict):
                issues.append("temporal_dependence_sharpe contains an invalid bootstrap record")
                continue

            block_size = record.get("block_size")
            lower = record.get("interval_lower")
            upper = record.get("interval_upper")
            median = record.get("bootstrap_median")
            positive_share = record.get("bootstrap_positive_share")
            confidence = record.get("confidence_level")

            if not isinstance(block_size, int) or isinstance(block_size, bool):
                issues.append("temporal_dependence_sharpe contains an invalid bootstrap block size")
            else:
                observed_block_sizes.add(block_size)

            if not finite_number(lower) or not finite_number(upper) or float(lower) >= float(upper):
                issues.append("temporal_dependence_sharpe contains an invalid bootstrap interval")

            if not finite_number(median) or (
                finite_number(lower)
                and finite_number(upper)
                and not float(lower) <= float(median) <= float(upper)
            ):
                issues.append("temporal_dependence_sharpe contains an invalid bootstrap median")

            if not finite_number(positive_share) or not 0.0 <= float(positive_share) <= 1.0:
                issues.append(
                    "temporal_dependence_sharpe contains an invalid positive bootstrap share"
                )

            if confidence != 0.95:
                issues.append(
                    "temporal_dependence_sharpe bootstrap confidence level must equal 0.95"
                )

        if observed_block_sizes != expected_block_sizes:
            issues.append("temporal_dependence_sharpe bootstrap block-size set is invalid")

    diagnostics = section.get("diagnostics")

    expected_diagnostics = {
        "raw_serial_dependence_detected_at_5pct": True,
        "volatility_dependence_detected_at_5pct": True,
        "all_hac_sharpes_positive": True,
        "all_bootstrap_lower_bounds_positive": True,
    }

    if diagnostics != expected_diagnostics:
        issues.append("temporal_dependence_sharpe diagnostics are invalid")

    formal_methods = section.get("formal_methods")
    limitations = section.get("limitations")

    if (
        not isinstance(formal_methods, list)
        or not formal_methods
        or not all(isinstance(item, str) and item.strip() for item in formal_methods)
    ):
        issues.append("temporal_dependence_sharpe formal_methods must be a non-empty string list")

    if (
        not isinstance(limitations, list)
        or not limitations
        or not all(isinstance(item, str) and item.strip() for item in limitations)
    ):
        issues.append("temporal_dependence_sharpe limitations must be a non-empty string list")

    commitment = section.get("evidence_commitment_sha256")

    if (
        not isinstance(commitment, str)
        or len(commitment) != 64
        or any(character not in "0123456789abcdef" for character in commitment)
    ):
        issues.append(
            "temporal_dependence_sharpe evidence commitment must be a lowercase SHA-256 digest"
        )


def validate_public_quantitative_payload(
    payload: Mapping[str, Any],
) -> list[str]:
    """Validate one already-sanitized aggregate payload."""

    issues: list[str] = []

    expected_top_level = {
        *METADATA_FIELDS,
        *REQUIRED_SECTIONS,
    }

    actual_top_level = set(payload)

    missing = sorted(expected_top_level - actual_top_level)
    unexpected = sorted(actual_top_level - expected_top_level)

    if missing:
        issues.append("missing top-level fields: " + ", ".join(missing))

    if unexpected:
        issues.append("unexpected top-level fields: " + ", ".join(unexpected))

    if payload.get("schema_version") != SCHEMA_VERSION:
        issues.append(f"schema_version must equal {SCHEMA_VERSION}")

    if payload.get("release_target") != "v0.3.0":
        issues.append("release_target must equal v0.3.0")

    if payload.get("classification") != "public_aggregated_candidate":
        issues.append("classification must equal public_aggregated_candidate")

    limitations = payload.get("limitations")

    if (
        not isinstance(limitations, list)
        or not limitations
        or not all(isinstance(item, str) and item.strip() for item in limitations)
    ):
        issues.append("limitations must be a non-empty list of strings")

    for section in REQUIRED_SECTIONS:
        if section in payload and not isinstance(
            payload[section],
            dict,
        ):
            issues.append(f"{section} must be a JSON object")

    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
    ).lower()

    for fragment in FORBIDDEN_PUBLIC_FRAGMENTS:
        if fragment in serialized:
            issues.append(f"forbidden public fragment: {fragment}")

    execution = payload.get("execution_cost_delay")

    if isinstance(execution, dict):
        records = execution.get("records")

        if not isinstance(records, list):
            issues.append("execution_cost_delay.records must be a list")
        else:
            reference_count = sum(
                1
                for row in records
                if isinstance(row, dict) and row.get("candidate") == "artifact_verified_reference"
            )

            comparison_count = sum(
                1
                for row in records
                if isinstance(row, dict)
                and isinstance(
                    row.get("candidate"),
                    str,
                )
                and row["candidate"].startswith("comparison_candidate_")
            )

            if reference_count != 18:
                issues.append("execution reference record count must equal 18")

            if comparison_count != 18:
                issues.append("execution comparison record count must equal 18")

            if len(records) != 36:
                issues.append("execution total record count must equal 36")

    placebo = payload.get("placebo_test")

    if isinstance(placebo, dict):
        metrics = placebo.get("metrics")

        if not isinstance(metrics, dict):
            issues.append("placebo_test.metrics must be an object")
        else:
            expected_metrics = {
                "final_equity",
                "cagr",
                "sharpe",
                "calmar",
            }

            if set(metrics) != expected_metrics:
                issues.append("placebo metrics must equal final_equity, cagr, sharpe and calmar")

            for name, metric in metrics.items():
                if not isinstance(metric, dict):
                    issues.append(f"placebo metric {name} must be an object")
                    continue

                if metric.get("observation_source") != "public_artifact_verified_aggregate":
                    issues.append(f"placebo metric {name} has an invalid observation source")

    monte_carlo = payload.get("historical_block_monte_carlo")

    if isinstance(monte_carlo, dict):
        records = monte_carlo.get("records")

        if not isinstance(records, list):
            issues.append("historical_block_monte_carlo.records must be a list")
        else:
            if len(records) != 8:
                issues.append("Monte Carlo record count must equal 8")

            for index, row in enumerate(records):
                if not isinstance(row, dict):
                    issues.append(f"Monte Carlo record {index} must be an object")
                    continue

                if "simulation_length_days" not in row:
                    issues.append(f"Monte Carlo record {index} has no simulation_length_days")

                if "horizon_days" in row:
                    issues.append(f"Monte Carlo record {index} contains horizon_days")

    monitoring = payload.get("shadow_monitoring")

    if isinstance(monitoring, dict):
        if monitoring.get("production_readiness_decision") != "not_made":
            issues.append("shadow monitoring must not claim a production-readiness decision")

        if monitoring.get("pilot_or_limited_production_approval") is not False:
            issues.append("shadow monitoring must not claim pilot or production approval")

    psr = payload.get("probabilistic_sharpe_ratio")

    if isinstance(psr, dict):
        if psr.get("verification_level") != "artifact-verified":
            issues.append("PSR must be artifact-verified")

        if psr.get("observations") != 2211:
            issues.append("PSR observation count must equal 2211")

        probability = psr.get("probability")

        if (
            not isinstance(
                probability,
                int | float,
            )
            or isinstance(
                probability,
                bool,
            )
            or not 0.0 <= float(probability) <= 1.0
        ):
            issues.append("PSR probability must be between zero and one")

    dsr = payload.get("deflated_sharpe_ratio")

    if isinstance(dsr, dict):
        if dsr.get("verification_level") != "artifact-verified":
            issues.append("DSR must be artifact-verified")

        if dsr.get("observations") != 2211:
            issues.append("DSR observation count must equal 2211")

        if dsr.get("trial_count") != 15:
            issues.append("DSR trial count must equal 15")

        probability = dsr.get("probability")

        if (
            not isinstance(
                probability,
                int | float,
            )
            or isinstance(
                probability,
                bool,
            )
            or not 0.0 <= float(probability) <= 1.0
        ):
            issues.append("DSR probability must be between zero and one")

    multiple_testing = payload.get("multiple_testing")

    if isinstance(
        multiple_testing,
        dict,
    ):
        if multiple_testing.get("verification_level") != "artifact-verified":
            issues.append("multiple testing must be artifact-verified")

        if multiple_testing.get("candidate_count") != 15:
            issues.append("multiple-testing candidate count must equal 15")

        if multiple_testing.get("repetitions") != 2000:
            issues.append("multiple-testing repetitions must equal 2000")

        if multiple_testing.get("private_matrix_disclosed") is not False:
            issues.append("the private candidate matrix must not be disclosed")

        finite_limitation = multiple_testing.get("finite_resampling_limitation")

        if (
            not isinstance(
                finite_limitation,
                str,
            )
            or not finite_limitation.strip()
        ):
            issues.append("finite-resampling limitation must be disclosed")

        for test_name in (
            "white_reality_check",
            "hansen_spa",
        ):
            test_result = multiple_testing.get(test_name)

            if not isinstance(
                test_result,
                dict,
            ):
                issues.append(f"{test_name} must be an object")
                continue

            p_value = test_result.get("reported_p_value")

            if (
                not isinstance(
                    p_value,
                    int | float,
                )
                or isinstance(
                    p_value,
                    bool,
                )
                or not 0.0 <= float(p_value) <= 1.0
            ):
                issues.append(f"{test_name} p-value must be between zero and one")

    overfitting = payload.get("backtest_overfitting")

    if isinstance(
        overfitting,
        dict,
    ):
        if overfitting.get("verification_level") != "artifact-verified":
            issues.append("PBO must be artifact-verified")

        if overfitting.get("candidate_count") != 15:
            issues.append("PBO candidate count must equal 15")

        if overfitting.get("blocks") != 8:
            issues.append("PBO block count must equal 8")

        if overfitting.get("tested_setting_count") != 4:
            issues.append("PBO tested-setting count must equal 4")

        if overfitting.get("all_combinations_completed") is not True:
            issues.append("PBO combinations must be complete")

        if overfitting.get("exact_sensitivity_settings_disclosed") is not False:
            issues.append("exact PBO sensitivity settings must remain withheld")

        raw_pbo_minimum = overfitting.get("pbo_minimum")
        raw_pbo_median = overfitting.get("pbo_median")
        raw_pbo_mean = overfitting.get("pbo_mean")
        raw_pbo_maximum = overfitting.get("pbo_maximum")

        if (
            isinstance(
                raw_pbo_minimum,
                bool,
            )
            or not isinstance(
                raw_pbo_minimum,
                int | float,
            )
            or isinstance(
                raw_pbo_median,
                bool,
            )
            or not isinstance(
                raw_pbo_median,
                int | float,
            )
            or isinstance(
                raw_pbo_mean,
                bool,
            )
            or not isinstance(
                raw_pbo_mean,
                int | float,
            )
            or isinstance(
                raw_pbo_maximum,
                bool,
            )
            or not isinstance(
                raw_pbo_maximum,
                int | float,
            )
        ):
            issues.append("PBO aggregate values must be numeric")
        else:
            pbo_minimum = float(raw_pbo_minimum)
            pbo_median = float(raw_pbo_median)
            pbo_mean = float(raw_pbo_mean)
            pbo_maximum = float(raw_pbo_maximum)

            if not (
                0.0 <= pbo_minimum <= pbo_median <= pbo_maximum <= 1.0
                and pbo_minimum <= pbo_mean <= pbo_maximum
            ):
                issues.append("PBO aggregate values are inconsistent")

    bootstrap = payload.get("moving_block_bootstrap")

    if isinstance(
        bootstrap,
        dict,
    ):
        if bootstrap.get("verification_level") != "artifact-verified":
            issues.append("moving-block bootstrap must be artifact-verified")

        if bootstrap.get("public_benchmark_set_reconciled") is not True:
            issues.append("bootstrap benchmark set must reconcile with the public benchmark set")

        if bootstrap.get("benchmark_count") != 11:
            issues.append("bootstrap benchmark count must equal 11")

        if bootstrap.get("positive_cagr_differences") != 11:
            issues.append("positive CAGR difference count must equal 11")

        if bootstrap.get("significant_at_5_percent") != 2:
            issues.append("significant bootstrap comparison count must equal 2")

        records = bootstrap.get("records")

        if not isinstance(
            records,
            list,
        ):
            issues.append("moving_block_bootstrap.records must be a list")
        else:
            expected_benchmarks = {
                "BUY_AND_HOLD",
                "FIXED_50",
                "HMM_3_STATE_WALKFORWARD",
                "MA_50_200",
                "MOMENTUM_180",
                "MOMENTUM_270",
                "MOMENTUM_30",
                "MOMENTUM_60",
                "MOMENTUM_90",
                "VOL_TARGET_14",
                "VOL_TARGET_30",
            }

            actual_benchmarks = {
                row.get("benchmark")
                for row in records
                if isinstance(
                    row,
                    dict,
                )
            }

            if len(records) != 11 or actual_benchmarks != expected_benchmarks:
                issues.append("bootstrap records must contain exactly the 11 public benchmarks")

            positive_count = sum(
                1
                for row in records
                if isinstance(
                    row,
                    dict,
                )
                and isinstance(
                    row.get("cagr_difference"),
                    int | float,
                )
                and not isinstance(
                    row.get("cagr_difference"),
                    bool,
                )
                and float(row["cagr_difference"]) > 0.0
            )

            significant_count = sum(
                1
                for row in records
                if isinstance(
                    row,
                    dict,
                )
                and row.get("significant_compounded_outperformance") is True
            )

            if positive_count != 11:
                issues.append("all bootstrap CAGR differences must be positive")

            if significant_count != 2:
                issues.append("exactly two bootstrap records must be significant")

    issues.extend(_validate_historical_reverse_stress(payload.get("historical_reverse_stress")))
    issues.extend(_validate_var_es_backtesting(payload.get("var_es_backtesting")))
    _validate_temporal_dependence_sharpe(
        payload,
        issues,
    )

    return issues


def build_public_quantitative_export(
    input_path: Path,
    output_dir: Path,
) -> None:
    """Package a sanitized aggregate payload into controlled files."""

    payload = json.loads(input_path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise ValueError("Aggregate input must be a JSON object.")

    issues = validate_public_quantitative_payload(payload)

    if issues:
        raise ValueError("Invalid public quantitative payload:\n- " + "\n- ".join(issues))

    if output_dir.exists():
        existing = {path.name for path in output_dir.iterdir() if path.is_file()}

        unexpected = existing - CONTROLLED_FILENAMES

        if unexpected:
            raise ValueError(
                "Output directory contains uncontrolled files: " + ", ".join(sorted(unexpected))
            )
    else:
        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    for filename in CONTROLLED_FILENAMES:
        path = output_dir / filename

        if path.is_file():
            path.unlink()

    metadata = {key: payload[key] for key in METADATA_FIELDS}

    files_to_write: dict[str, bytes] = {
        "metadata.json": _canonical_json_bytes(metadata),
    }

    for section in REQUIRED_SECTIONS:
        filename = PAYLOAD_FILENAMES[section]

        files_to_write[filename] = _canonical_json_bytes(
            {
                "schema_version": (EXPORT_SCHEMA_VERSION),
                "section": section,
                "data": payload[section],
            }
        )

    for filename, content in files_to_write.items():
        (output_dir / filename).write_bytes(content)

    manifest_entries = []

    for filename in sorted(files_to_write):
        path = output_dir / filename

        manifest_entries.append(
            {
                "path": filename,
                "sha256": _sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )

    manifest = {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "release_target": payload["release_target"],
        "classification": payload["classification"],
        "files": manifest_entries,
    }

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_bytes(_canonical_json_bytes(manifest))

    checksum_paths = [
        *sorted(files_to_write),
        "manifest.json",
    ]

    checksums = "".join(
        f"{_sha256_file(output_dir / filename)}  {filename}\n" for filename in checksum_paths
    )

    (output_dir / "SHA256SUMS").write_text(
        checksums,
        encoding="utf-8",
        newline="\n",
    )


def verify_public_quantitative_export(
    output_dir: Path,
) -> list[str]:
    """Verify a packaged public quantitative aggregate export."""

    issues: list[str] = []

    if not output_dir.is_dir():
        return [f"export directory missing: {output_dir}"]

    actual_files = {path.name for path in output_dir.iterdir() if path.is_file()}

    missing = sorted(CONTROLLED_FILENAMES - actual_files)
    unexpected = sorted(actual_files - CONTROLLED_FILENAMES)

    if missing:
        issues.append("missing export files: " + ", ".join(missing))

    if unexpected:
        issues.append("unexpected export files: " + ", ".join(unexpected))

    if issues:
        return issues

    try:
        metadata = json.loads((output_dir / "metadata.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [f"metadata.json unreadable: {error}"]

    reconstructed: dict[str, Any] = dict(metadata)

    for section in REQUIRED_SECTIONS:
        path = output_dir / PAYLOAD_FILENAMES[section]

        try:
            wrapper = json.loads(path.read_text(encoding="utf-8"))
        except (
            OSError,
            json.JSONDecodeError,
        ) as error:
            issues.append(f"{path.name} unreadable: {error}")
            continue

        if wrapper.get("schema_version") != EXPORT_SCHEMA_VERSION:
            issues.append(f"{path.name}: invalid schema_version")

        if wrapper.get("section") != section:
            issues.append(f"{path.name}: invalid section identifier")

        if "data" not in wrapper:
            issues.append(f"{path.name}: data field missing")
            continue

        reconstructed[section] = wrapper["data"]

    if not issues:
        issues.extend(validate_public_quantitative_payload(reconstructed))

    try:
        manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        issues.append(f"manifest.json unreadable: {error}")
        manifest = {}

    entries = manifest.get("files")

    if not isinstance(entries, list):
        issues.append("manifest files field must be a list")
    else:
        expected_manifest_paths = {
            "metadata.json",
            *PAYLOAD_FILENAMES.values(),
        }

        actual_manifest_paths = {entry.get("path") for entry in entries if isinstance(entry, dict)}

        if actual_manifest_paths != (expected_manifest_paths):
            issues.append("manifest file paths do not match the controlled payload")

        for entry in entries:
            if not isinstance(entry, dict):
                issues.append("manifest contains a non-object entry")
                continue

            filename = entry.get("path")

            if not isinstance(filename, str):
                issues.append("manifest entry path is invalid")
                continue

            path = output_dir / filename

            if not path.is_file():
                issues.append(f"manifest file missing: {filename}")
                continue

            if entry.get("sha256") != _sha256_file(path):
                issues.append(f"manifest SHA-256 mismatch: {filename}")

            if entry.get("size_bytes") != path.stat().st_size:
                issues.append(f"manifest size mismatch: {filename}")

    checksum_path = output_dir / "SHA256SUMS"

    try:
        checksum_lines = checksum_path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        issues.append(f"SHA256SUMS unreadable: {error}")
        checksum_lines = []

    checksum_entries: dict[str, str] = {}

    for line in checksum_lines:
        parts = line.split(
            "  ",
            maxsplit=1,
        )

        if len(parts) != 2:
            issues.append("SHA256SUMS contains an invalid line")
            continue

        checksum_entries[parts[1]] = parts[0]

    expected_checksum_paths = {
        "metadata.json",
        *PAYLOAD_FILENAMES.values(),
        "manifest.json",
    }

    if set(checksum_entries) != (expected_checksum_paths):
        issues.append("SHA256SUMS paths do not match the controlled export")

    for filename, expected_digest in checksum_entries.items():
        path = output_dir / filename

        if path.is_file() and _sha256_file(path) != expected_digest:
            issues.append(f"SHA256SUMS mismatch: {filename}")

    return issues
