from __future__ import annotations

from pathlib import Path

from hilmarbench.publication import scan_tree


def test_clean_tree_passes(
    tmp_path: Path,
) -> None:
    (tmp_path / "README.md").write_text(
        "Public benchmark documentation.\n",
        encoding="utf-8",
    )

    assert scan_tree(tmp_path) == []


def test_absolute_private_path_is_rejected(
    tmp_path: Path,
) -> None:
    private_path = "/" + "Users" + "/private-user/project"

    (tmp_path / "notes.txt").write_text(
        private_path,
        encoding="utf-8",
    )

    issues = scan_tree(tmp_path)

    assert any("absolute macOS user path" in issue for issue in issues)


def test_generic_private_column_is_rejected(
    tmp_path: Path,
) -> None:
    (tmp_path / "trace.csv").write_text(
        "timestamp,private_model_position\n2026-01-01,0.5\n",
        encoding="utf-8",
    )

    issues = scan_tree(tmp_path)

    assert any("private column forbidden" in issue for issue in issues)


def test_serialized_model_is_rejected(
    tmp_path: Path,
) -> None:
    (tmp_path / "model.pkl").write_bytes(b"not-a-real-model")

    issues = scan_tree(tmp_path)

    assert any("forbidden file type" in issue for issue in issues)
