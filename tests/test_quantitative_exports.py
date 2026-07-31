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
