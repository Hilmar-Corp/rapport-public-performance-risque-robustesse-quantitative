from __future__ import annotations

import copy
import csv
import json
import re
from pathlib import Path
from typing import Any

from hilmarbench.quantitative_exports import (
    FORBIDDEN_PUBLIC_FRAGMENTS,
    PAYLOAD_FILENAMES,
    REQUIRED_SECTIONS,
    validate_public_quantitative_payload,
    verify_public_quantitative_export,
)

ROOT = Path(__file__).resolve().parents[1]

PACKAGE = ROOT / "artifacts" / "candidates" / "v0.3.0" / "quantitative_aggregates"

SECTION = "counterfactual_reverse_stress"

PRIVATE_COMMITMENT = "ba1ea95fdca6dfe6fcc28140294ecfcb173a5248c82a16ae17296ae66e9d9e26"


def _wrapper() -> dict[str, Any]:
    return json.loads((PACKAGE / "counterfactual_reverse_stress.json").read_text(encoding="utf-8"))


def _section() -> dict[str, Any]:
    wrapper = _wrapper()

    assert wrapper["schema_version"] == 1
    assert wrapper["section"] == SECTION

    data = wrapper["data"]

    assert isinstance(
        data,
        dict,
    )

    return data


def _complete_payload() -> dict[str, Any]:
    metadata = json.loads((PACKAGE / "metadata.json").read_text(encoding="utf-8"))

    payload: dict[str, Any] = dict(metadata)

    for section in REQUIRED_SECTIONS:
        wrapper = json.loads((PACKAGE / PAYLOAD_FILENAMES[section]).read_text(encoding="utf-8"))

        payload[section] = wrapper["data"]

    return payload


def test_counterfactual_reverse_stress_is_controlled() -> None:
    assert SECTION in REQUIRED_SECTIONS

    assert PAYLOAD_FILENAMES[SECTION] == "counterfactual_reverse_stress.json"


def test_counterfactual_reverse_stress_package_verifies() -> None:
    assert verify_public_quantitative_export(PACKAGE) == []

    assert validate_public_quantitative_payload(_complete_payload()) == []


def test_counterfactual_reverse_stress_quantitative_contract() -> None:
    section = _section()

    assert section["verification_level"] == "artifact-verified"

    assert section["observations"] == 2211

    assert section["total_scenarios"] == 4908

    assert (
        section["inference_stage_scenarios"]
        + section["retraining_and_core_scenarios"]
        + section["refinement_scenarios"]
        == 4908
    )

    assert section["refined_failure_frontiers"] == 87

    assert section["refined_failure_families"] == 8

    assert section["randomized_repetitions"] == {
        "adverse_state_injection": 50,
        "noise": 30,
    }

    assert section["all_phase_offsets_tested"] is True

    assert section["baseline_reconciliation_max_abs_delta"] <= 1e-12

    assert section["private_evidence_commitment_sha256"] == PRIVATE_COMMITMENT


def test_counterfactual_reverse_stress_rejects_bad_counts() -> None:
    payload = _complete_payload()

    section = copy.deepcopy(payload[SECTION])

    section["total_scenarios"] = 4907

    payload[SECTION] = section

    issues = validate_public_quantitative_payload(payload)

    assert any("scenario counts do not reconcile" in issue for issue in issues)


def test_counterfactual_reverse_stress_rejects_bad_reconciliation() -> None:
    payload = _complete_payload()

    section = copy.deepcopy(payload[SECTION])

    section["baseline_reconciliation_max_abs_delta"] = 1e-6

    payload[SECTION] = section

    issues = validate_public_quantitative_payload(payload)

    assert any("reconciliation delta is invalid" in issue for issue in issues)


def test_counterfactual_reverse_stress_rejects_disclosure_flags() -> None:
    payload = _complete_payload()

    section = copy.deepcopy(payload[SECTION])

    section["daily_paths_disclosed"] = True

    section["internal_variables_disclosed"] = True

    section["exact_private_settings_disclosed"] = True

    payload[SECTION] = section

    issues = validate_public_quantitative_payload(payload)

    assert any("daily_paths_disclosed" in issue for issue in issues)

    assert any("internal_variables_disclosed" in issue for issue in issues)

    assert any("exact_private_settings_disclosed" in issue for issue in issues)


def test_counterfactual_reverse_stress_rejects_private_details() -> None:
    prohibited_fields = (
        "scenario_id",
        "severity",
        "daily_trace",
        "daily_returns",
        "daily_positions",
        "internal_inputs",
        "model_coefficients",
        "private_breakpoints",
        "selected_inputs",
        "source_path",
        "source_ledger",
    )

    for field in prohibited_fields:
        payload = _complete_payload()

        section = copy.deepcopy(payload[SECTION])

        section[field] = "forbidden"

        payload[SECTION] = section

        issues = validate_public_quantitative_payload(payload)

        assert any("prohibited detailed fields" in issue for issue in issues)


def test_counterfactual_reverse_stress_has_no_ip_leak() -> None:
    serialized = json.dumps(
        _wrapper(),
        ensure_ascii=False,
        sort_keys=True,
    ).lower()

    violations = [fragment for fragment in FORBIDDEN_PUBLIC_FRAGMENTS if fragment in serialized]

    assert violations == []

    extra_forbidden = (
        "/users/",
        "/home/",
        "clovishilmarcher",
        "workbench/results/private",
        "v5246_position",
        "base_position",
        "selected_features",
        "scenario_id",
        "daily_trace",
        "source_ledger",
    )

    for fragment in extra_forbidden:
        assert fragment not in serialized

    assert (
        re.search(
            r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
            serialized,
        )
        is None
    )

    assert not re.search(
        r"20\d{2}-\d{2}-\d{2}t"
        r"\d{2}:\d{2}:\d{2}",
        serialized,
    )


def test_historical_and_counterfactual_reverse_stress_are_separate() -> None:
    historical = json.loads(
        (PACKAGE / "historical_reverse_stress.json").read_text(encoding="utf-8")
    )

    counterfactual = _wrapper()

    assert historical["section"] == "historical_reverse_stress"

    assert counterfactual["section"] == SECTION

    assert historical != counterfactual


def test_qnt_rst_002_governance_contract() -> None:
    matrix_path = ROOT / "governance" / "quantitative_validation_control_matrix.csv"

    commitments_path = ROOT / "governance" / "quantitative_evidence_commitments.csv"

    with matrix_path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as stream:
        matrix = {row["control_id"]: row for row in csv.DictReader(stream)}

    with commitments_path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as stream:
        commitments = {row["control_id"]: row for row in csv.DictReader(stream)}

    assert "historical_reverse_stress.json" in matrix["QNT-RST-001"]["public_evidence"]

    assert "counterfactual_reverse_stress.json" in matrix["QNT-RST-002"]["public_evidence"]

    assert matrix["QNT-RST-002"]["private_evidence_commitment_sha256"] == PRIVATE_COMMITMENT

    commitment = commitments["QNT-RST-002"]

    assert commitment["private_evidence_commitment_sha256"] == PRIVATE_COMMITMENT

    assert commitment["public_evidence_items"] == "1"
