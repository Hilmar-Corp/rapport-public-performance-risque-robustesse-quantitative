"""Public-safe quantitative aggregate export packaging."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 2
EXPORT_SCHEMA_VERSION = 1

REQUIRED_SECTIONS = (
    "stationarity",
    "distribution_drift",
    "market_regimes",
    "execution_cost_delay",
    "placebo_test",
    "tail_risk",
    "var_es_backtesting",
    "historical_block_monte_carlo",
    "data_resilience",
    "configuration_sensitivity",
    "ablation",
    "shadow_monitoring",
    "probabilistic_sharpe_ratio",
    "deflated_sharpe_ratio",
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
    "var_es_backtesting": "var_es_backtesting.json",
    "historical_block_monte_carlo": "historical_block_monte_carlo.json",
    "data_resilience": "data_resilience.json",
    "configuration_sensitivity": "configuration_sensitivity.json",
    "ablation": "ablation.json",
    "shadow_monitoring": "shadow_monitoring.json",
    "probabilistic_sharpe_ratio": "probabilistic_sharpe_ratio.json",
    "deflated_sharpe_ratio": "deflated_sharpe_ratio.json",
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

    issues.extend(_validate_var_es_backtesting(payload.get("var_es_backtesting")))
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
