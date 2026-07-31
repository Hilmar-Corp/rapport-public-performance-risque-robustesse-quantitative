from __future__ import annotations

import shutil
from pathlib import Path

from tools.audit_public_repository import (
    QUANTITATIVE_AGGREGATE_CANDIDATE,
    audit_quantitative_aggregate_candidate,
)

ROOT = Path(__file__).resolve().parents[1]

SOURCE_CANDIDATE = ROOT / QUANTITATIVE_AGGREGATE_CANDIDATE


def copy_candidate(
    destination_root: Path,
) -> Path:
    destination = destination_root / QUANTITATIVE_AGGREGATE_CANDIDATE

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copytree(
        SOURCE_CANDIDATE,
        destination,
    )

    return destination


def test_candidate_audit_accepts_controlled_package(
    tmp_path: Path,
) -> None:
    copy_candidate(tmp_path)

    assert not (audit_quantitative_aggregate_candidate(tmp_path))


def test_candidate_audit_rejects_missing_package(
    tmp_path: Path,
) -> None:
    issues = audit_quantitative_aggregate_candidate(tmp_path)

    assert issues == [
        (f"{QUANTITATIVE_AGGREGATE_CANDIDATE}: required quantitative aggregate candidate missing")
    ]


def test_candidate_audit_detects_tampering(
    tmp_path: Path,
) -> None:
    candidate = copy_candidate(tmp_path)

    stationarity = candidate / "stationarity.json"

    stationarity.write_text(
        stationarity.read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )

    issues = audit_quantitative_aggregate_candidate(tmp_path)

    assert any(
        ("manifest SHA-256 mismatch: stationarity.json") in issue
        or ("SHA256SUMS mismatch: stationarity.json") in issue
        for issue in issues
    )
