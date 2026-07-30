from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Final

from hypothesis import given
from hypothesis import strategies as st

ROOT: Final = Path(__file__).resolve().parents[1]
RELEASE_DIR: Final = ROOT / "artifacts" / "latest"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


@given(
    left=st.floats(
        allow_nan=False,
        allow_infinity=False,
        width=64,
    ),
    right=st.floats(
        allow_nan=False,
        allow_infinity=False,
        width=64,
    ),
)
def test_numeric_comparison_is_symmetric(
    left: float,
    right: float,
) -> None:
    assert math.isclose(
        left,
        right,
        rel_tol=1e-10,
        abs_tol=1e-12,
    ) == math.isclose(
        right,
        left,
        rel_tol=1e-10,
        abs_tol=1e-12,
    )


@given(
    value=st.floats(
        allow_nan=False,
        allow_infinity=False,
        width=64,
    ),
)
def test_finite_values_remain_finite_under_identity(
    value: float,
) -> None:
    assert math.isfinite(value)
    assert math.isfinite(value * 1.0)


def test_release_manifest_hashes_are_valid() -> None:
    checksum_file = RELEASE_DIR / "SHA256SUMS"
    assert checksum_file.is_file()

    entries = [
        line.split(maxsplit=1)
        for line in checksum_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert entries

    for expected_hash, filename in entries:
        clean_filename = filename.lstrip("*")
        artifact = RELEASE_DIR / clean_filename

        assert artifact.is_file(), clean_filename
        assert len(expected_hash) == 64
        assert sha256(artifact) == expected_hash
