from __future__ import annotations

from pathlib import Path

from hilmarbench.publication import (
    build_manifest,
    verify_manifest,
    write_sha256s,
)


def test_manifest_is_deterministic(
    tmp_path: Path,
) -> None:
    (tmp_path / "a.txt").write_text(
        "alpha\n",
        encoding="utf-8",
    )

    (tmp_path / "b.json").write_text(
        '{"value": 2}\n',
        encoding="utf-8",
    )

    manifest = tmp_path / "manifest.json"

    build_manifest(
        tmp_path,
        manifest,
    )

    first = manifest.read_bytes()

    build_manifest(
        tmp_path,
        manifest,
    )

    second = manifest.read_bytes()

    assert first == second
    assert (
        verify_manifest(
            tmp_path,
            manifest,
        )
        == []
    )


def test_manifest_detects_tampering(
    tmp_path: Path,
) -> None:
    data = tmp_path / "data.csv"

    data.write_text(
        "x\n1\n",
        encoding="utf-8",
    )

    manifest = tmp_path / "manifest.json"

    build_manifest(
        tmp_path,
        manifest,
    )

    data.write_text(
        "x\n2\n",
        encoding="utf-8",
    )

    issues = verify_manifest(
        tmp_path,
        manifest,
    )

    assert any("SHA-256 mismatch" in issue for issue in issues)


def test_sha256s_contains_manifest(
    tmp_path: Path,
) -> None:
    (tmp_path / "data.txt").write_text(
        "data\n",
        encoding="utf-8",
    )

    build_manifest(
        tmp_path,
        tmp_path / "manifest.json",
    )

    checksums = tmp_path / "SHA256SUMS"

    write_sha256s(
        tmp_path,
        checksums,
    )

    text = checksums.read_text(encoding="utf-8")

    assert "manifest.json" in text
    assert "data.txt" in text
