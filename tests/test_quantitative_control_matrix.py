from __future__ import annotations

import csv
import re
from pathlib import Path

from tools.audit_public_repository import ALLOWED_CSV_PATHS, CONTROLLED_CSV_SCHEMAS

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "governance" / "quantitative_validation_control_matrix.csv"
COMMITMENTS = ROOT / "governance" / "quantitative_evidence_commitments.csv"

SHA256 = re.compile(r"^[0-9a-f]{64}$")

MATRIX_FIELDS = {
    "control_id",
    "domain",
    "control_question",
    "method",
    "public_status",
    "gap",
    "public_evidence",
    "private_evidence_commitment_sha256",
    "ip_classification",
    "limitation",
}

COMMITMENT_FIELDS = {
    "control_id",
    "public_evidence_items",
    "public_evidence_commitment_sha256",
    "public_commitment_scheme",
    "private_evidence_items",
    "private_evidence_commitment_sha256",
    "private_commitment_scheme",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_quantitative_control_matrix_contract() -> None:
    rows = read_csv(MATRIX)

    assert len(rows) == 24
    assert set(rows[0]) == MATRIX_FIELDS

    control_ids = [row["control_id"] for row in rows]

    assert len(control_ids) == len(set(control_ids))
    assert all(control_id.startswith("QNT-") for control_id in control_ids)

    for row in rows:
        for required in (
            "domain",
            "control_question",
            "method",
            "public_status",
            "gap",
            "ip_classification",
            "limitation",
        ):
            assert row[required].strip()

        commitment = row["private_evidence_commitment_sha256"]

        if commitment:
            assert SHA256.fullmatch(commitment)


def test_quantitative_evidence_commitments_contract() -> None:
    rows = read_csv(COMMITMENTS)

    assert len(rows) == 24
    assert set(rows[0]) == COMMITMENT_FIELDS
    for row in rows:
        public_count = int(row["public_evidence_items"])
        private_count = int(row["private_evidence_items"])

        public_commitment = row["public_evidence_commitment_sha256"]
        public_scheme = row["public_commitment_scheme"]
        private_commitment = row["private_evidence_commitment_sha256"]
        private_scheme = row["private_commitment_scheme"]

        assert public_count >= 0
        assert private_count >= 0
        assert bool(public_commitment) is (public_count > 0)
        assert bool(public_scheme) is (public_count > 0)
        assert bool(private_commitment) is (private_count > 0)
        assert bool(private_scheme) is (private_count > 0)

        if public_commitment:
            assert SHA256.fullmatch(public_commitment)
            assert public_scheme == "sha256-canonical-public-evidence-v2"

        if private_commitment:
            assert SHA256.fullmatch(private_commitment)
            assert private_scheme == "sha256-canonical-json-v1"


def test_public_control_artifacts_do_not_expose_private_paths() -> None:
    text = "\n".join(
        (
            MATRIX.read_text(encoding="utf-8"),
            COMMITMENTS.read_text(encoding="utf-8"),
        )
    )

    forbidden = (
        "/" + "Users/",
        "private_" + "working_copy",
        "dossier_" + "interne_complet",
        "quantitative_" + "corpus_original",
        "Nostra Quantitative " + "Evidence",
    )

    for fragment in forbidden:
        assert fragment not in text


def test_quantitative_csvs_are_controlled_by_public_audit() -> None:
    matrix_relative = MATRIX.relative_to(ROOT)
    commitments_relative = COMMITMENTS.relative_to(ROOT)

    assert matrix_relative in ALLOWED_CSV_PATHS
    assert commitments_relative in ALLOWED_CSV_PATHS

    with MATRIX.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        matrix_reader = csv.DictReader(handle)
        matrix_header = tuple(matrix_reader.fieldnames or ())

    with COMMITMENTS.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        commitments_reader = csv.DictReader(handle)
        commitments_header = tuple(commitments_reader.fieldnames or ())

    assert matrix_header == CONTROLLED_CSV_SCHEMAS[matrix_relative]
    assert commitments_header == CONTROLLED_CSV_SCHEMAS[commitments_relative]


def test_quantitative_csvs_use_lf_line_endings() -> None:
    for path in (MATRIX, COMMITMENTS):
        assert b"\r" not in path.read_bytes()


def test_public_commitments_are_reproducible() -> None:
    from tools.update_quantitative_public_commitments import (
        expected_rows,
    )

    assert read_csv(COMMITMENTS) == expected_rows()


def test_matrix_and_registry_private_commitments_match() -> None:
    matrix = {row["control_id"]: row for row in read_csv(MATRIX)}

    commitments = {row["control_id"]: row for row in read_csv(COMMITMENTS)}

    assert set(matrix) == set(commitments)

    for control_id, matrix_row in matrix.items():
        assert (
            matrix_row["private_evidence_commitment_sha256"]
            == commitments[control_id]["private_evidence_commitment_sha256"]
        )
