from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from hilmarbench.quantitative_exports import (
    CONTROLLED_FILENAMES,
    REQUIRED_SECTIONS,
    build_public_quantitative_export,
    validate_public_quantitative_payload,
    verify_public_quantitative_export,
)


def valid_payload() -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": 2,
        "release_target": "v0.3.0",
        "classification": ("public_aggregated_candidate"),
        "limitations": [
            "Retrospective aggregate evidence only.",
            "No independent validation claim.",
        ],
    }

    for section in REQUIRED_SECTIONS:
        payload[section] = {}

    payload["execution_cost_delay"] = {
        "records": [
            {
                "candidate": (
                    "artifact_verified_reference" if index < 18 else "comparison_candidate_01"
                ),
                "cost_bps": float(index % 6),
                "delay_days": int(index % 3),
            }
            for index in range(36)
        ]
    }

    payload["placebo_test"] = {
        "metrics": {
            name: {
                "observation_source": ("public_artifact_verified_aggregate"),
                "observed": 1.0,
                "upper_tail_empirical_pvalue": 0.05,
            }
            for name in (
                "final_equity",
                "cagr",
                "sharpe",
                "calmar",
            )
        }
    }

    payload["historical_block_monte_carlo"] = {
        "records": [
            {
                "portfolio": "portfolio_01",
                "block_size": index + 1,
                "simulation_length_days": 365,
            }
            for index in range(8)
        ]
    }

    payload["shadow_monitoring"] = {
        "production_readiness_decision": ("not_made"),
        "pilot_or_limited_production_approval": (False),
    }

    payload["probabilistic_sharpe_ratio"] = {
        "verification_level": "artifact-verified",
        "methodological_status": ("accepted_with_disclosed_limitation"),
        "probability": 0.99,
        "test_statistic": 3.9,
        "observations": 2211,
        "annualization": 365,
        "skewness": 0.6,
        "pearson_kurtosis": 9.0,
        "observed_annualized_sharpe": 1.5,
        "limitation": ("Serial dependence is not explicitly corrected."),
        "methodological_verdict": ("Accepted with disclosed limitation."),
    }

    payload["deflated_sharpe_ratio"] = {
        "verification_level": "artifact-verified",
        "methodological_status": ("accepted_with_disclosed_limitation"),
        "probability": 0.98,
        "test_statistic": 3.8,
        "observations": 2211,
        "annualization": 365,
        "trial_count": 15,
        "expected_maximum_sharpe": 0.01,
        "skewness": 0.6,
        "pearson_kurtosis": 9.0,
        "limitation": ("The underlying candidate matrix is withheld."),
        "methodological_verdict": ("Accepted with disclosed limitation."),
    }

    payload["multiple_testing"] = {
        "verification_level": "artifact-verified",
        "benchmark": "zero daily return",
        "observations": 2211,
        "candidate_count": 15,
        "block_size": 21,
        "repetitions": 2000,
        "white_reality_check": {
            "reported_p_value": 0.001,
            "methodological_status": ("requalified_non_studentized_test"),
            "methodological_verdict": ("Non-studentized test."),
        },
        "hansen_spa": {
            "reported_p_value": 0.001,
            "methodological_status": ("accepted_with_disclosed_limitation"),
            "methodological_verdict": ("Studentized test."),
        },
        "finite_resampling_limitation": (
            "Reported values are bounded by finite resampling resolution."
        ),
        "private_matrix_disclosed": False,
    }

    payload["backtest_overfitting"] = {
        "verification_level": "artifact-verified",
        "method": ("CSCV and Probability of Backtest Overfitting"),
        "observations": 2211,
        "candidate_count": 15,
        "blocks": 8,
        "combinations_per_setting": 70,
        "tested_setting_count": 4,
        "pbo_minimum": 0.10,
        "pbo_median": 0.15,
        "pbo_mean": 0.18,
        "pbo_maximum": 0.31,
        "results_below_0_20": 3,
        "all_combinations_completed": True,
        "exact_sensitivity_settings_disclosed": False,
        "limitation": ("Exact sensitivity settings remain withheld."),
    }

    benchmarks = (
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
    )

    payload["moving_block_bootstrap"] = {
        "verification_level": "artifact-verified",
        "method": ("Retrospective moving-block bootstrap of compounded outperformance."),
        "benchmark_count": 11,
        "public_benchmark_set_reconciled": True,
        "positive_cagr_differences": 11,
        "significant_at_5_percent": 2,
        "records": [
            {
                "benchmark": benchmark,
                "nostra_cagr": 0.52,
                "benchmark_cagr": 0.30,
                "cagr_difference": 0.22,
                "annualized_log_outperformance": 0.16,
                "ci95_lower_annualized_log": -0.05,
                "ci95_upper_annualized_log": 0.39,
                "one_sided_p_value": (0.01 if index < 2 else 0.10),
                "significant_compounded_outperformance": (index < 2),
            }
            for index, benchmark in enumerate(benchmarks)
        ],
        "excluded_analyses": ("Incremental, predictive and ablation analyses."),
        "limitation": ("Significance is benchmark-specific."),
    }

    payload["historical_reverse_stress"] = {
        "verification_level": "artifact-verified",
        "methodological_status": "accepted_with_observations",
        "decision_status": "PASS_WITH_OBSERVATION",
        "analysis_type": ("historical_dynamic_loss_breach_analysis"),
        "observations": 2211,
        "evaluation_period": {
            "start": "2020-05-14",
            "end": "2026-06-02",
        },
        "governing_conventions": [
            "Realized historical paths only.",
            "Loss levels are measured from historical peaks.",
        ],
        "economic_reconciliation": {
            "status": "PASS",
            "maximum_absolute_delta": 1.0061396160665481e-16,
            "public_convention_name": ("row_aligned_effective_allocation"),
        },
        "global_results": {
            "drawdown_episode_count": 104,
            "loss_breach_record_count": 40,
            "maximum_model_drawdown": -0.2139050350373155,
        },
        "loss_level_results": [
            {
                "target_nav_loss": loss,
                "historically_breached": count > 0,
                "breach_episode_count": count,
                **(
                    {
                        "observations_to_breach": {
                            "minimum": 1,
                            "median": 5.0,
                            "maximum": 167,
                        },
                        "observed_btc_path_to_breach": {
                            "minimum_cumulative_return_range": {
                                "minimum": -0.50,
                                "median": -0.20,
                                "maximum": -0.06,
                            },
                            "compounded_return_range": {
                                "minimum": -0.50,
                                "median": -0.20,
                                "maximum": -0.06,
                            },
                        },
                        "allocation_reaction_counts": reactions,
                        "allocation_reaction_shares": {
                            "reduced_at_breach": (reactions["reduced_at_breach"] / count),
                            "increased_at_breach": (reactions["increased_at_breach"] / count),
                            "unchanged_at_breach": (reactions["unchanged_at_breach"] / count),
                            ("reduced_by_at_least_25pct_before_breach"): (
                                reactions["reduced_by_at_least_25pct_before_breach"] / count
                            ),
                        },
                        "turnover_to_breach": {
                            "minimum": 0.0,
                            "median": 0.5,
                            "maximum": 4.0,
                        },
                    }
                    if count > 0
                    else {
                        "observed_non_breach_is_not_a_bound": True,
                    }
                ),
            }
            for loss, count, reactions in (
                (
                    0.05,
                    25,
                    {
                        "reduced_at_breach": 13,
                        "increased_at_breach": 10,
                        "unchanged_at_breach": 2,
                        "reduced_by_at_least_25pct_before_breach": 6,
                    },
                ),
                (
                    0.10,
                    10,
                    {
                        "reduced_at_breach": 6,
                        "increased_at_breach": 3,
                        "unchanged_at_breach": 1,
                        "reduced_by_at_least_25pct_before_breach": 4,
                    },
                ),
                (
                    0.15,
                    4,
                    {
                        "reduced_at_breach": 1,
                        "increased_at_breach": 2,
                        "unchanged_at_breach": 1,
                        "reduced_by_at_least_25pct_before_breach": 1,
                    },
                ),
                (
                    0.20,
                    1,
                    {
                        "reduced_at_breach": 1,
                        "increased_at_breach": 0,
                        "unchanged_at_breach": 0,
                        "reduced_by_at_least_25pct_before_breach": 1,
                    },
                ),
                (
                    0.25,
                    0,
                    {
                        "reduced_at_breach": 0,
                        "increased_at_breach": 0,
                        "unchanged_at_breach": 0,
                        "reduced_by_at_least_25pct_before_breach": 0,
                    },
                ),
                (
                    0.30,
                    0,
                    {
                        "reduced_at_breach": 0,
                        "increased_at_breach": 0,
                        "unchanged_at_breach": 0,
                        "reduced_by_at_least_25pct_before_breach": 0,
                    },
                ),
            )
        ],
        "governance_decision": {
            "status": "PASS_WITH_OBSERVATION",
            "principal_observations": [
                "Allocation reduction was not universal.",
            ],
            "monitoring_requirement": ("Continue monitoring severe declines."),
        },
        "limitations": [
            "The analysis covers realized historical paths only.",
            "Observed non-breach is not a future loss bound.",
        ],
        "evidence_commitment_sha256": (
            "83b47296d8eee4da8629cd2ef65a8a9f906fbc77a5b0b7aba3b254ec66710f62"
        ),
    }

    payload["counterfactual_reverse_stress"] = {
        "all_phase_offsets_tested": True,
        "baseline_reconciliation_max_abs_delta": 1.7763568394002505e-15,
        "daily_paths_disclosed": False,
        "decision_status": "historical_research_evidence",
        "dominant_vulnerability_class": "directional_core_freshness_and_integrity",
        "exact_private_settings_disclosed": False,
        "historical_scope": "2020-05-14_to_2026-06-02",
        "inference_stage_scenarios": 67,
        "internal_variables_disclosed": False,
        "isolated_input_corruption_failure_found": False,
        "limitation": "The public payload omits daily paths, internal variables, model "
        "settings and exact breakpoints. Results are historical counterfactual "
        "evidence and are not forecasts.",
        "observations": 2211,
        "private_evidence_commitment_sha256": (
            "ba1ea95fdca6dfe6fcc28140294ecfcb173a5248c82a16ae17296ae66e9d9e26"
        ),
        "randomized_repetitions": {"adverse_state_injection": 50, "noise": 30},
        "refined_failure_families": 8,
        "refined_failure_frontiers": 87,
        "refinement_scenarios": 4709,
        "retraining_and_core_scenarios": 132,
        "total_scenarios": 4908,
        "verification_level": "artifact-verified",
    }

    payload["var_es_backtesting"] = {
        "verification_level": "artifact-verified",
        "methodological_status": "accepted_with_observations",
        "decision_status": "PASS_WITH_OBSERVATION",
        "observations": 2211,
        "canonical_calibration_window_days": 365,
        "sensitivity_calibration_windows_days": [
            250,
            365,
            500,
        ],
        "risk_periods_days": [1, 10],
        "confidence_levels": [0.95, 0.99],
        "canonical_results": [
            {
                "risk_period_days": horizon,
                "confidence_level": confidence,
                "observations": (1846 if horizon == 1 else 184),
                "expected_exception_count": (
                    92.3
                    if (
                        horizon,
                        confidence,
                    )
                    == (1, 0.95)
                    else 18.46
                    if (
                        horizon,
                        confidence,
                    )
                    == (1, 0.99)
                    else 9.2
                    if (
                        horizon,
                        confidence,
                    )
                    == (10, 0.95)
                    else 1.84
                ),
                "exception_count": (
                    93
                    if (
                        horizon,
                        confidence,
                    )
                    == (1, 0.95)
                    else 21
                    if (
                        horizon,
                        confidence,
                    )
                    == (1, 0.99)
                    else 11
                    if (
                        horizon,
                        confidence,
                    )
                    == (10, 0.95)
                    else 4
                ),
                "exception_rate": 0.05,
                "kupiec_p_value": 0.50,
                "exact_binomial_p_value": 0.50,
                "christoffersen_independence_p_value": 0.50,
                "christoffersen_conditional_coverage_p_value": 0.50,
                ("es_normalized_tail_loss_bootstrap_p_value"): 0.50,
                "exception_cluster_count": 1,
                "maximum_exception_cluster_length": 1,
                "traffic_light": (
                    "AMBER"
                    if (
                        horizon,
                        confidence,
                    )
                    == (10, 0.99)
                    else "GREEN"
                ),
                "reason_codes": (
                    [
                        "NO_FORMAL_REJECTION_AT_5_PERCENT",
                        "LOW_EXPECTED_EXCEPTION_COUNT",
                    ]
                    if (
                        horizon,
                        confidence,
                    )
                    == (10, 0.99)
                    else ["NO_FORMAL_REJECTION_AT_5_PERCENT"]
                ),
            }
            for horizon, confidence in (
                (1, 0.95),
                (1, 0.99),
                (10, 0.95),
                (10, 0.99),
            )
        ],
        "canonical_traffic_light_counts": {
            "GREEN": 3,
            "AMBER": 1,
            "RED": 0,
        },
        "all_sensitivity_traffic_light_counts": {
            "GREEN": 7,
            "AMBER": 4,
            "RED": 1,
        },
        "limitations": ["Retrospective aggregate evidence."],
        "evidence_commitment_sha256": "a" * 64,
    }
    payload["temporal_dependence_sharpe"] = {
        "annualization": 365,
        "autocorrelation_records": [
            {"autocorrelation": -0.018947971484975727, "lag_count": 1},
            {"autocorrelation": 0.032076421991579146, "lag_count": 5},
            {"autocorrelation": -0.0066060936356148745, "lag_count": 10},
            {"autocorrelation": 0.00882624379064061, "lag_count": 21},
            {"autocorrelation": 0.01847963223659721, "lag_count": 30},
            {"autocorrelation": -0.046740496288189715, "lag_count": 60},
        ],
        "automatic_lag_count": 7,
        "automatic_lag_rule": "floor(4*(n/100)^(2/9))",
        "bootstrap_method": "circular moving-block percentile interval for annualized arithmetic "
        "Sharpe",
        "bootstrap_repetitions": 2000,
        "bootstrap_seed_base": 20260731,
        "bootstrap_sensitivity_records": [
            {
                "block_size": 5,
                "bootstrap_median": 1.5832757926564578,
                "bootstrap_positive_share": 1.0,
                "confidence_level": 0.95,
                "interval_lower": 0.7832200708866145,
                "interval_upper": 2.341941700487583,
            },
            {
                "block_size": 10,
                "bootstrap_median": 1.590115660106567,
                "bootstrap_positive_share": 1.0,
                "confidence_level": 0.95,
                "interval_lower": 0.8143331837768503,
                "interval_upper": 2.373328381240761,
            },
            {
                "block_size": 21,
                "bootstrap_median": 1.5669386650446135,
                "bootstrap_positive_share": 1.0,
                "confidence_level": 0.95,
                "interval_lower": 0.7571871501731903,
                "interval_upper": 2.3500727862679986,
            },
            {
                "block_size": 30,
                "bootstrap_median": 1.59640559068229,
                "bootstrap_positive_share": 1.0,
                "confidence_level": 0.95,
                "interval_lower": 0.7836849444600525,
                "interval_upper": 2.4057367210870804,
            },
            {
                "block_size": 60,
                "bootstrap_median": 1.5767359668590792,
                "bootstrap_positive_share": 1.0,
                "confidence_level": 0.95,
                "interval_lower": 0.7608419436086805,
                "interval_upper": 2.44657493185048,
            },
        ],
        "canonical_block_size": 21,
        "canonical_hac_adjusted_annualized_sharpe": 1.4931827873589063,
        "canonical_hac_lag_count": 21,
        "canonical_volatility_inflation_factor": 1.0632905273384274,
        "conventional_annualized_sharpe": 1.5876871133835144,
        "decision_status": "PASS_WITH_OBSERVATION",
        "diagnostics": {
            "all_bootstrap_lower_bounds_positive": True,
            "all_hac_sharpes_positive": True,
            "raw_serial_dependence_detected_at_5pct": True,
            "volatility_dependence_detected_at_5pct": True,
        },
        "evidence_commitment_sha256": (
            "94a36288bcf86d6289056d1fa7cb2bf894c4af520312728f552982606edcd749"
        ),
        "formal_methods": [
            "Bartlett-kernel Newey-West long-run variance",
            "Ljung-Box portmanteau tests on periodic and squared centered periodic returns",
            "deterministic circular moving-block bootstrap",
        ],
        "hac_sensitivity_records": [
            {
                "hac_adjusted_annualized_sharpe": 1.596359853071572,
                "lag_count": 5,
                "volatility_inflation_factor": 0.9945671775249356,
            },
            {
                "hac_adjusted_annualized_sharpe": 1.5896187989510528,
                "lag_count": 7,
                "volatility_inflation_factor": 0.9987848120764468,
            },
            {
                "hac_adjusted_annualized_sharpe": 1.5739824692187443,
                "lag_count": 10,
                "volatility_inflation_factor": 1.008706986534337,
            },
            {
                "hac_adjusted_annualized_sharpe": 1.4931827873589063,
                "lag_count": 21,
                "volatility_inflation_factor": 1.0632905273384274,
            },
            {
                "hac_adjusted_annualized_sharpe": 1.4409568241397386,
                "lag_count": 30,
                "volatility_inflation_factor": 1.1018283731931904,
            },
            {
                "hac_adjusted_annualized_sharpe": 1.347218580252575,
                "lag_count": 60,
                "volatility_inflation_factor": 1.1784925895884368,
            },
        ],
        "limitations": [
            "The analysis is retrospective and does not constitute independent validation.",
            "Newey-West adjustment addresses linear serial dependence but does not model "
            "the full conditional distribution.",
            "Ljung-Box p-values reported as zero indicate numerical underflow, not "
            "mathematical zero.",
            "Bootstrap conclusions remain conditional on the disclosed block-size sensitivity set.",
        ],
        "ljung_box_records": [
            {
                "lag_count": 5,
                "p_value": 0.5494145562274486,
                "p_value_below_machine_precision": False,
                "series": "periodic_returns",
                "statistic": 4.000009689997235,
            },
            {
                "lag_count": 10,
                "p_value": 0.22926316945783223,
                "p_value_below_machine_precision": False,
                "series": "periodic_returns",
                "statistic": 12.90094130200967,
            },
            {
                "lag_count": 21,
                "p_value": 0.003263652508535611,
                "p_value_below_machine_precision": False,
                "series": "periodic_returns",
                "statistic": 42.87213245473431,
            },
            {
                "lag_count": 30,
                "p_value": 0.0002090612096298496,
                "p_value_below_machine_precision": False,
                "series": "periodic_returns",
                "statistic": 65.16294049497266,
            },
            {
                "lag_count": 5,
                "p_value": 1.0864331619492298e-28,
                "p_value_below_machine_precision": False,
                "series": "squared_centered_periodic_returns",
                "statistic": 141.01924144496283,
            },
            {
                "lag_count": 10,
                "p_value": 5.217545752547138e-44,
                "p_value_below_machine_precision": False,
                "series": "squared_centered_periodic_returns",
                "statistic": 231.0324649717583,
            },
            {
                "lag_count": 21,
                "p_value": 1.0665696131549399e-78,
                "p_value_below_machine_precision": False,
                "series": "squared_centered_periodic_returns",
                "statistic": 433.47749474341055,
            },
            {
                "lag_count": 30,
                "p_value": 3.5482733363605085e-84,
                "p_value_below_machine_precision": False,
                "series": "squared_centered_periodic_returns",
                "statistic": 487.9547070812303,
            },
        ],
        "methodological_status": "accepted_with_observations",
        "observations": 2211,
        "verification_level": "artifact-verified",
    }

    return payload


def test_valid_payload_contract() -> None:
    assert not validate_public_quantitative_payload(valid_payload())


def test_private_fragment_is_rejected() -> None:
    payload = valid_payload()
    payload["stationarity"] = {
        "private_path": ("/" + "Users/example/" + "private_" + "working_copy")
    }

    issues = validate_public_quantitative_payload(payload)

    assert any("forbidden public fragment" in issue for issue in issues)


def test_exact_tuning_field_is_rejected() -> None:
    payload = valid_payload()
    payload["configuration_sensitivity"] = {"purge": 30}

    issues = validate_public_quantitative_payload(payload)

    assert any(issue == "forbidden public fragment: purge" for issue in issues)


def test_build_and_verify_export(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "input.json"
    output_dir = tmp_path / "export"

    input_path.write_text(
        json.dumps(
            valid_payload(),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    build_public_quantitative_export(
        input_path,
        output_dir,
    )

    assert {path.name for path in output_dir.iterdir() if path.is_file()} == CONTROLLED_FILENAMES

    assert not verify_public_quantitative_export(output_dir)


def test_modified_export_is_rejected(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "input.json"
    output_dir = tmp_path / "export"

    input_path.write_text(
        json.dumps(
            valid_payload(),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    build_public_quantitative_export(
        input_path,
        output_dir,
    )

    stationarity_path = output_dir / "stationarity.json"

    wrapper = json.loads(stationarity_path.read_text(encoding="utf-8"))
    wrapper["data"]["modified"] = True

    stationarity_path.write_text(
        json.dumps(
            wrapper,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    issues = verify_public_quantitative_export(output_dir)

    assert any("SHA-256 mismatch" in issue or "SHA256SUMS mismatch" in issue for issue in issues)


def test_monitoring_approval_claim_is_rejected() -> None:
    payload = deepcopy(valid_payload())
    payload["shadow_monitoring"]["pilot_or_limited_production_approval"] = True

    issues = validate_public_quantitative_payload(payload)

    assert any("must not claim pilot" in issue for issue in issues)


def _write_valid_input(
    tmp_path: Path,
) -> Path:
    input_path = tmp_path / "input.json"
    input_path.write_text(
        json.dumps(
            valid_payload(),
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return input_path


def test_validation_contract_failure_modes() -> None:
    payload = valid_payload()

    payload.pop("stationarity")
    payload["unexpected_section"] = {}
    payload["schema_version"] = 99
    payload["release_target"] = "v9.9.9"
    payload["classification"] = "private"
    payload["limitations"] = []
    payload["distribution_drift"] = []
    payload["execution_cost_delay"] = {"records": "invalid"}
    payload["placebo_test"] = {"metrics": []}
    payload["historical_block_monte_carlo"] = {"records": {}}
    payload["shadow_monitoring"] = {
        "production_readiness_decision": "approved",
        "pilot_or_limited_production_approval": True,
    }

    issues = validate_public_quantitative_payload(payload)
    joined = "\n".join(issues)

    assert "missing top-level fields" in joined
    assert "unexpected top-level fields" in joined
    assert "schema_version must equal 2" in joined
    assert "release_target must equal v0.3.0" in joined
    assert "classification must equal" in joined
    assert "limitations must be a non-empty" in joined
    assert "distribution_drift must be a JSON object" in joined
    assert "execution_cost_delay.records must be a list" in joined
    assert "placebo_test.metrics must be an object" in joined
    assert "historical_block_monte_carlo.records must be a list" in joined
    assert "must not claim a production-readiness decision" in joined
    assert "must not claim pilot or production approval" in joined


def test_validation_nested_failure_modes() -> None:
    payload = valid_payload()

    payload["execution_cost_delay"] = {"records": [{"candidate": "artifact_verified_reference"}]}

    payload["placebo_test"] = {
        "metrics": {
            "final_equity": 1.0,
            "cagr": {"observation_source": "private"},
        }
    }

    payload["historical_block_monte_carlo"] = {
        "records": [
            "invalid",
            {
                "portfolio": "portfolio_01",
                "horizon_days": 365,
            },
        ]
    }

    issues = validate_public_quantitative_payload(payload)
    joined = "\n".join(issues)

    assert "execution reference record count must equal 18" in joined
    assert "execution comparison record count must equal 18" in joined
    assert "execution total record count must equal 36" in joined
    assert "placebo metrics must equal" in joined
    assert "placebo metric final_equity must be an object" in joined
    assert "placebo metric cagr has an invalid observation source" in joined
    assert "Monte Carlo record count must equal 8" in joined
    assert "Monte Carlo record 0 must be an object" in joined
    assert "Monte Carlo record 1 has no simulation_length_days" in joined
    assert "Monte Carlo record 1 contains horizon_days" in joined


def test_build_rejects_non_object_input(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "input.json"
    input_path.write_text(
        json.dumps([]),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Aggregate input must be a JSON object",
    ):
        build_public_quantitative_export(
            input_path,
            tmp_path / "export",
        )


def test_build_rejects_invalid_payload(
    tmp_path: Path,
) -> None:
    payload = valid_payload()
    payload["schema_version"] = 99

    input_path = tmp_path / "input.json"
    input_path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Invalid public quantitative payload",
    ):
        build_public_quantitative_export(
            input_path,
            tmp_path / "export",
        )


def test_build_rejects_uncontrolled_output_file(
    tmp_path: Path,
) -> None:
    input_path = _write_valid_input(tmp_path)
    output_dir = tmp_path / "export"
    output_dir.mkdir()
    (output_dir / "rogue.txt").write_text(
        "uncontrolled",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="uncontrolled files",
    ):
        build_public_quantitative_export(
            input_path,
            output_dir,
        )


def test_rebuild_is_deterministic(
    tmp_path: Path,
) -> None:
    input_path = _write_valid_input(tmp_path)
    output_dir = tmp_path / "export"

    build_public_quantitative_export(
        input_path,
        output_dir,
    )

    first = {path.name: path.read_bytes() for path in output_dir.iterdir() if path.is_file()}

    build_public_quantitative_export(
        input_path,
        output_dir,
    )

    second = {path.name: path.read_bytes() for path in output_dir.iterdir() if path.is_file()}

    assert first == second
    assert not verify_public_quantitative_export(output_dir)


def test_verify_missing_directory_and_file_contract(
    tmp_path: Path,
) -> None:
    missing_issues = verify_public_quantitative_export(tmp_path / "missing")

    assert missing_issues == [f"export directory missing: {tmp_path / 'missing'}"]

    input_path = _write_valid_input(tmp_path)
    output_dir = tmp_path / "export"

    build_public_quantitative_export(
        input_path,
        output_dir,
    )

    (output_dir / "stationarity.json").unlink()
    (output_dir / "rogue.json").write_text(
        "{}",
        encoding="utf-8",
    )

    issues = verify_public_quantitative_export(output_dir)
    joined = "\n".join(issues)

    assert "missing export files: stationarity.json" in joined
    assert "unexpected export files: rogue.json" in joined


def test_verify_rejects_unreadable_metadata(
    tmp_path: Path,
) -> None:
    input_path = _write_valid_input(tmp_path)
    output_dir = tmp_path / "export"

    build_public_quantitative_export(
        input_path,
        output_dir,
    )

    (output_dir / "metadata.json").write_text(
        "{",
        encoding="utf-8",
    )

    issues = verify_public_quantitative_export(output_dir)

    assert any("metadata.json unreadable" in issue for issue in issues)


def test_verify_rejects_unreadable_section(
    tmp_path: Path,
) -> None:
    input_path = _write_valid_input(tmp_path)
    output_dir = tmp_path / "export"

    build_public_quantitative_export(
        input_path,
        output_dir,
    )

    (output_dir / "stationarity.json").write_text(
        "{",
        encoding="utf-8",
    )

    issues = verify_public_quantitative_export(output_dir)

    assert any("stationarity.json unreadable" in issue for issue in issues)


def test_verify_rejects_invalid_section_wrapper(
    tmp_path: Path,
) -> None:
    input_path = _write_valid_input(tmp_path)
    output_dir = tmp_path / "export"

    build_public_quantitative_export(
        input_path,
        output_dir,
    )

    (output_dir / "stationarity.json").write_text(
        json.dumps(
            {
                "schema_version": 99,
                "section": "wrong",
            }
        ),
        encoding="utf-8",
    )

    issues = verify_public_quantitative_export(output_dir)
    joined = "\n".join(issues)

    assert "stationarity.json: invalid schema_version" in joined
    assert "stationarity.json: invalid section identifier" in joined
    assert "stationarity.json: data field missing" in joined


def test_verify_rejects_unreadable_manifest(
    tmp_path: Path,
) -> None:
    input_path = _write_valid_input(tmp_path)
    output_dir = tmp_path / "export"

    build_public_quantitative_export(
        input_path,
        output_dir,
    )

    (output_dir / "manifest.json").write_text(
        "{",
        encoding="utf-8",
    )

    issues = verify_public_quantitative_export(output_dir)

    assert any("manifest.json unreadable" in issue for issue in issues)


def test_verify_manifest_failure_modes(
    tmp_path: Path,
) -> None:
    input_path = _write_valid_input(tmp_path)
    output_dir = tmp_path / "export"

    build_public_quantitative_export(
        input_path,
        output_dir,
    )

    malformed_manifest = {
        "files": [
            "invalid-entry",
            {
                "path": 123,
            },
            {
                "path": "metadata.json",
                "sha256": "0" * 64,
                "size_bytes": 0,
            },
            {
                "path": "missing.json",
                "sha256": "0" * 64,
                "size_bytes": 0,
            },
        ]
    }

    (output_dir / "manifest.json").write_text(
        json.dumps(malformed_manifest),
        encoding="utf-8",
    )

    issues = verify_public_quantitative_export(output_dir)
    joined = "\n".join(issues)

    assert "manifest file paths do not match" in joined
    assert "manifest contains a non-object entry" in joined
    assert "manifest entry path is invalid" in joined
    assert "manifest SHA-256 mismatch: metadata.json" in joined
    assert "manifest size mismatch: metadata.json" in joined
    assert "manifest file missing: missing.json" in joined


def test_verify_rejects_non_list_manifest_entries(
    tmp_path: Path,
) -> None:
    input_path = _write_valid_input(tmp_path)
    output_dir = tmp_path / "export"

    build_public_quantitative_export(
        input_path,
        output_dir,
    )

    (output_dir / "manifest.json").write_text(
        json.dumps(
            {
                "files": "invalid",
            }
        ),
        encoding="utf-8",
    )

    issues = verify_public_quantitative_export(output_dir)

    assert any("manifest files field must be a list" in issue for issue in issues)


def test_verify_checksum_failure_modes(
    tmp_path: Path,
) -> None:
    input_path = _write_valid_input(tmp_path)
    output_dir = tmp_path / "export"

    build_public_quantitative_export(
        input_path,
        output_dir,
    )

    (output_dir / "SHA256SUMS").write_text(
        "invalid-line\n" + ("0" * 64) + "  metadata.json\n",
        encoding="utf-8",
    )

    issues = verify_public_quantitative_export(output_dir)
    joined = "\n".join(issues)

    assert "SHA256SUMS contains an invalid line" in joined
    assert "SHA256SUMS paths do not match" in joined
    assert "SHA256SUMS mismatch: metadata.json" in joined


def test_var_es_backtesting_contract_failure_modes() -> None:
    payload = valid_payload()
    section = payload["var_es_backtesting"]

    section["decision_status"] = "PASS"
    section["canonical_results"][0]["kupiec_p_value"] = 1.5
    section["canonical_results"][1]["risk_period_days"] = 2
    section["canonical_traffic_light_counts"] = {
        "GREEN": 4,
        "AMBER": 0,
        "RED": 0,
    }
    section["evidence_commitment_sha256"] = "invalid"

    issues = validate_public_quantitative_payload(payload)
    joined = "\n".join(issues)

    assert ("decision_status must equal PASS_WITH_OBSERVATION") in joined
    assert "invalid kupiec_p_value" in joined
    assert ("canonical horizon and confidence combinations are invalid") in joined
    assert ("canonical traffic-light counts are invalid") in joined
    assert ("lowercase SHA-256 digest") in joined


def test_var_es_backtesting_rejects_non_object() -> None:
    payload = valid_payload()
    payload["var_es_backtesting"] = []

    issues = validate_public_quantitative_payload(payload)

    assert any("var_es_backtesting must be a JSON object" in issue for issue in issues)


def test_var_es_backtesting_rejects_invalid_section_contract() -> None:
    payload = valid_payload()
    section = payload["var_es_backtesting"]

    section["verification_level"] = "unverified"
    section["methodological_status"] = "rejected"
    section["observations"] = 0
    section["canonical_calibration_window_days"] = 250
    section["sensitivity_calibration_windows_days"] = [
        250,
        500,
    ]
    section["risk_periods_days"] = [1]
    section["confidence_levels"] = [0.95]
    section["canonical_results"] = "invalid"
    section["all_sensitivity_traffic_light_counts"] = {
        "GREEN": 12,
        "AMBER": 0,
        "RED": 0,
    }
    section["limitations"] = []

    issues = validate_public_quantitative_payload(payload)
    joined = "\n".join(issues)

    assert ("verification_level must equal artifact-verified") in joined
    assert ("methodological_status must equal accepted_with_observations") in joined
    assert "observations must equal 2211" in joined
    assert ("canonical_calibration_window_days must equal 365") in joined
    assert ("sensitivity windows must equal 250, 365 and 500 days") in joined
    assert ("horizons must equal 1 and 10 days") in joined
    assert ("confidence levels must equal 0.95 and 0.99") in joined
    assert ("canonical_results must be a list") in joined
    assert ("canonical result count must equal 4") in joined
    assert ("sensitivity traffic-light counts are invalid") in joined
    assert ("limitations must be a non-empty string list") in joined


def test_temporal_dependence_sharpe_contract_failure_modes() -> None:
    payload = valid_payload()
    section = payload["temporal_dependence_sharpe"]

    section["verification_level"] = "unverified"
    section["methodological_status"] = "accepted"
    section["decision_status"] = "PASS"
    section["observations"] = 2_210
    section["annualization"] = 252
    section["automatic_lag_count"] = 8
    section["canonical_hac_lag_count"] = 30
    section["canonical_block_size"] = 30
    section["canonical_hac_adjusted_annualized_sharpe"] = -1.0
    section["canonical_volatility_inflation_factor"] = 0.5
    section["bootstrap_repetitions"] = 1_000
    section["diagnostics"] = {}
    section["evidence_commitment_sha256"] = "invalid"

    issues = validate_public_quantitative_payload(payload)
    joined = "\n".join(issues)

    assert "must be artifact-verified" in joined
    assert ("methodological_status must equal accepted_with_observations") in joined
    assert ("decision_status must equal PASS_WITH_OBSERVATION") in joined
    assert "observations must equal 2211" in joined
    assert "annualization must equal 365" in joined
    assert "automatic lag count must equal 7" in joined
    assert ("canonical HAC lag count must equal 21") in joined
    assert ("canonical block size must equal 21") in joined
    assert "canonical HAC Sharpe is invalid" in joined
    assert ("canonical volatility inflation is invalid") in joined
    assert ("bootstrap repetitions must equal 2000") in joined
    assert "diagnostics are invalid" in joined
    assert ("commitment must be a lowercase SHA-256 digest") in joined


def test_temporal_dependence_sharpe_record_failure_modes() -> None:
    payload = valid_payload()
    section = payload["temporal_dependence_sharpe"]

    section["autocorrelation_records"][0]["autocorrelation"] = 2.0
    section["autocorrelation_records"][1]["lag_count"] = 1

    section["ljung_box_records"][0]["p_value"] = 2.0
    section["ljung_box_records"][1]["statistic"] = -1.0
    section["ljung_box_records"][2]["series"] = "invalid"

    section["hac_sensitivity_records"][0]["hac_adjusted_annualized_sharpe"] = 0.0
    section["hac_sensitivity_records"][1]["volatility_inflation_factor"] = 0.0
    section["hac_sensitivity_records"][2]["lag_count"] = 5

    section["bootstrap_sensitivity_records"][0]["interval_lower"] = 3.0
    section["bootstrap_sensitivity_records"][0]["interval_upper"] = 2.0
    section["bootstrap_sensitivity_records"][1]["bootstrap_positive_share"] = 2.0
    section["bootstrap_sensitivity_records"][2]["confidence_level"] = 0.90
    section["bootstrap_sensitivity_records"][3]["block_size"] = 5

    issues = validate_public_quantitative_payload(payload)
    joined = "\n".join(issues)

    assert "invalid autocorrelation value" in joined
    assert "autocorrelation lag set is invalid" in joined
    assert "invalid Ljung-Box p-value" in joined
    assert "invalid Ljung-Box statistic" in joined
    assert "Ljung-Box combinations are invalid" in joined
    assert "invalid HAC Sharpe" in joined
    assert "invalid HAC inflation factor" in joined
    assert "HAC sensitivity lag set is invalid" in joined
    assert "invalid bootstrap interval" in joined
    assert "invalid positive bootstrap share" in joined
    assert ("bootstrap confidence level must equal 0.95") in joined
    assert "bootstrap block-size set is invalid" in joined


def test_temporal_dependence_sharpe_requires_object() -> None:
    payload = valid_payload()
    payload["temporal_dependence_sharpe"] = []

    issues = validate_public_quantitative_payload(payload)

    assert "temporal_dependence_sharpe must be an object" in issues


def test_historical_reverse_stress_contract_failure_modes() -> None:
    payload = valid_payload()
    section = payload["historical_reverse_stress"]

    section["observations"] = 2200
    section["global_results"]["loss_breach_record_count"] = 39
    section["loss_level_results"][0]["breach_episode_count"] = 24
    section["evidence_commitment_sha256"] = "invalid"

    issues = validate_public_quantitative_payload(payload)

    assert any("observations must equal 2211" in issue for issue in issues)
    assert any("record count must equal 40" in issue for issue in issues)
    assert any("count is invalid" in issue for issue in issues)
    assert any("commitment is invalid" in issue for issue in issues)


def test_historical_reverse_stress_requires_object() -> None:
    payload = valid_payload()
    payload["historical_reverse_stress"] = []

    issues = validate_public_quantitative_payload(payload)

    assert "historical_reverse_stress must be a JSON object" in issues


def test_historical_reverse_stress_rejects_invalid_metadata() -> None:
    payload = valid_payload()
    section = payload["historical_reverse_stress"]

    assert isinstance(section, dict)

    section["evaluation_period"] = {}
    section["governing_conventions"] = []
    section["economic_reconciliation"] = []

    issues = validate_public_quantitative_payload(payload)

    assert any("evaluation period is invalid" in issue for issue in issues)
    assert any("governing conventions" in issue for issue in issues)
    assert any("economic reconciliation must be an object" in issue for issue in issues)


def test_historical_reverse_stress_rejects_invalid_reconciliation() -> None:
    payload = valid_payload()
    section = payload["historical_reverse_stress"]

    assert isinstance(section, dict)

    reconciliation = section["economic_reconciliation"]

    assert isinstance(reconciliation, dict)

    reconciliation["status"] = "FAIL"
    reconciliation["public_convention_name"] = "invalid"
    reconciliation["maximum_absolute_delta"] = -1.0

    issues = validate_public_quantitative_payload(payload)

    assert any("reconciliation must pass" in issue for issue in issues)
    assert any("economic convention is invalid" in issue for issue in issues)
    assert any("reconciliation delta is invalid" in issue for issue in issues)


def test_historical_reverse_stress_rejects_invalid_global_results() -> None:
    payload = valid_payload()
    section = payload["historical_reverse_stress"]

    assert isinstance(section, dict)

    section["global_results"] = []

    issues = validate_public_quantitative_payload(payload)

    assert any("global results must be an object" in issue for issue in issues)

    payload = valid_payload()
    section = payload["historical_reverse_stress"]

    assert isinstance(section, dict)

    results = section["global_results"]

    assert isinstance(results, dict)

    results["drawdown_episode_count"] = 103
    results["loss_breach_record_count"] = 39
    results["maximum_model_drawdown"] = False

    issues = validate_public_quantitative_payload(payload)

    assert any("episode count must equal 104" in issue for issue in issues)
    assert any("record count must equal 40" in issue for issue in issues)
    assert any("maximum drawdown is invalid" in issue for issue in issues)


def test_historical_reverse_stress_rejects_invalid_loss_level_records() -> None:
    payload = valid_payload()
    section = payload["historical_reverse_stress"]

    assert isinstance(section, dict)

    section["loss_level_results"] = []

    issues = validate_public_quantitative_payload(payload)

    assert any("loss-level coverage is invalid" in issue for issue in issues)

    payload = valid_payload()
    section = payload["historical_reverse_stress"]

    assert isinstance(section, dict)

    records = section["loss_level_results"]

    assert isinstance(records, list)

    records.append("invalid")
    records[0]["target_nav_loss"] = "invalid"

    issues = validate_public_quantitative_payload(payload)

    assert any("must be an object" in issue for issue in issues)
    assert any("invalid identifiers" in issue for issue in issues)


def test_historical_reverse_stress_rejects_inconsistent_breach_records() -> None:
    payload = valid_payload()
    section = payload["historical_reverse_stress"]

    assert isinstance(section, dict)

    records = section["loss_level_results"]

    assert isinstance(records, list)

    records[0]["target_nav_loss"] = 0.40
    records[1]["historically_breached"] = False
    records[4]["observed_non_breach_is_not_a_bound"] = False

    issues = validate_public_quantitative_payload(payload)

    assert any("unexpected loss level" in issue for issue in issues)
    assert any("breach flag is inconsistent" in issue for issue in issues)
    assert any("non-breach limitation must be disclosed" in issue for issue in issues)


def test_historical_reverse_stress_rejects_invalid_reaction_counts() -> None:
    payload = valid_payload()
    section = payload["historical_reverse_stress"]

    assert isinstance(section, dict)

    records = section["loss_level_results"]

    assert isinstance(records, list)

    records[0]["allocation_reaction_counts"] = []

    issues = validate_public_quantitative_payload(payload)

    assert any("reaction counts must be an object" in issue for issue in issues)

    payload = valid_payload()
    section = payload["historical_reverse_stress"]

    assert isinstance(section, dict)

    records = section["loss_level_results"]

    assert isinstance(records, list)

    reactions = records[0]["allocation_reaction_counts"]

    assert isinstance(reactions, dict)

    reactions["reduced_at_breach"] = -1

    issues = validate_public_quantitative_payload(payload)

    assert any("reaction counts are invalid" in issue for issue in issues)

    payload = valid_payload()
    section = payload["historical_reverse_stress"]

    assert isinstance(section, dict)

    records = section["loss_level_results"]

    assert isinstance(records, list)

    reactions = records[0]["allocation_reaction_counts"]

    assert isinstance(reactions, dict)

    reactions["reduced_at_breach"] = 12

    issues = validate_public_quantitative_payload(payload)

    assert any("counts do not reconcile" in issue for issue in issues)


def test_historical_reverse_stress_rejects_invalid_reaction_shares() -> None:
    payload = valid_payload()
    section = payload["historical_reverse_stress"]

    assert isinstance(section, dict)

    records = section["loss_level_results"]

    assert isinstance(records, list)

    records[0]["allocation_reaction_shares"] = []

    issues = validate_public_quantitative_payload(payload)

    assert any("reaction shares must be an object" in issue for issue in issues)

    payload = valid_payload()
    section = payload["historical_reverse_stress"]

    assert isinstance(section, dict)

    records = section["loss_level_results"]

    assert isinstance(records, list)

    shares = records[0]["allocation_reaction_shares"]

    assert isinstance(shares, dict)

    shares["reduced_at_breach"] = 2.0

    issues = validate_public_quantitative_payload(payload)

    assert any("allocation share" in issue for issue in issues)


def test_historical_reverse_stress_rejects_invalid_governance_and_limits() -> None:
    payload = valid_payload()
    section = payload["historical_reverse_stress"]

    assert isinstance(section, dict)

    section["governance_decision"] = []
    section["limitations"] = []

    issues = validate_public_quantitative_payload(payload)

    assert any("governance decision must be an object" in issue for issue in issues)
    assert any("limitations must be a non-empty string list" in issue for issue in issues)

    payload = valid_payload()
    section = payload["historical_reverse_stress"]

    assert isinstance(section, dict)

    governance = section["governance_decision"]

    assert isinstance(governance, dict)

    governance["status"] = "PASS"

    issues = validate_public_quantitative_payload(payload)

    assert any("governance status is invalid" in issue for issue in issues)
