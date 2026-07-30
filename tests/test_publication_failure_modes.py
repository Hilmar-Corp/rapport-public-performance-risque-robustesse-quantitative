from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from hilmarbench.publication import (
    build_manifest,
    build_public_release,
    scan_tree,
    verify_manifest,
)


def _write_valid_inputs(root: Path) -> tuple[Path, Path]:
    metrics = pd.DataFrame(
        {
            "strategy": ["NOSTRA_AI", "BUY_AND_HOLD"],
            "cost_bps": [25.0, 25.0],
            "date_start": ["2020-05-14", "2020-05-14"],
            "date_end": ["2026-06-02", "2026-06-02"],
            "observations": [2211, 2211],
            "final_equity": [12.754, 6.905],
            "total_return": [11.754, 5.905],
            "cagr": [0.5069, 0.3651],
            "annualized_volatility": [0.2891, 0.5725],
            "sharpe": [1.562, 0.829],
            "maximum_drawdown": [-0.2139, -0.7663],
            "calmar": [2.37, 0.476],
        }
    )
    daily = pd.DataFrame(
        {
            "timestamp": ["2026-01-31T00:00:00Z", "2026-02-01T00:00:00Z", "2026-02-28T00:00:00Z"],
            "nostra_ai_equity": [1.1, 1.2, 1.3],
            "nostra_ai_drawdown": [0.0, -0.01, 0.0],
            "buy_and_hold_equity": [1.0, 1.1, 1.2],
            "buy_and_hold_drawdown": [0.0, -0.02, 0.0],
        }
    )
    metrics_path = root / "metrics.csv"
    daily_path = root / "daily.csv"
    metrics.to_csv(metrics_path, index=False)
    daily.to_csv(daily_path, index=False)
    return (metrics_path, daily_path)


def _build_valid_release(root: Path) -> Path:
    metrics_path, daily_path = _write_valid_inputs(root)
    output = root / "release"
    build_public_release(metrics_path, daily_path, output, private_artifact_sha256="a" * 64)
    return output


def test_scan_tree_ignores_internal_directories(tmp_path: Path) -> None:
    ignored = tmp_path / ".git"
    ignored.mkdir()
    hidden_private_path = "/" + "Users" + "/ignored-user/private"
    (ignored / "ignored.txt").write_text(hidden_private_path, encoding="utf-8")
    directory = tmp_path / "normal-directory"
    directory.mkdir()
    (directory / "safe.md").write_text("Public benchmark documentation.\n", encoding="utf-8")
    assert scan_tree(tmp_path) == []


def test_scan_tree_rejects_environment_file(tmp_path: Path) -> None:
    (tmp_path / ".env.production").write_text("TOKEN=example\n", encoding="utf-8")
    issues = scan_tree(tmp_path)
    assert any("environment file forbidden" in issue for issue in issues)


def test_scan_tree_rejects_binary_and_paths(tmp_path: Path) -> None:
    (tmp_path / "model.npz").write_bytes(b"binary")
    server_path = "/" + "opt" + "/" + "hilmar" + "/private"
    address = "192" + ".168" + ".10" + ".20"
    (tmp_path / "notes.md").write_text(f"{server_path}\n{address}\n", encoding="utf-8")
    issues = scan_tree(tmp_path)
    assert any("forbidden file type" in issue for issue in issues)
    assert any("private server path" in issue for issue in issues)
    assert any("IPv4 address" in issue for issue in issues)


def test_scan_tree_reports_unreadable_text(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "broken.md"
    target.write_text("content\n", encoding="utf-8")
    original = Path.read_text

    def failing_read_text(self: Path, *args: Any, **kwargs: Any) -> str:
        if self == target:
            raise OSError("simulated read failure")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", failing_read_text)
    issues = scan_tree(tmp_path)
    assert any("unreadable file" in issue for issue in issues)


def test_scan_tree_reports_unreadable_csv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "broken.csv"
    target.write_text("timestamp,value\n2026-01-01,1\n", encoding="utf-8")
    original = Path.open

    def failing_open(self: Path, *args: Any, **kwargs: Any) -> Any:
        if self == target and kwargs.get("newline") == "":
            raise OSError("simulated CSV failure")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", failing_open)
    issues = scan_tree(tmp_path)
    assert any("unreadable CSV" in issue for issue in issues)


def test_verify_manifest_rejects_invalid_json(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{invalid", encoding="utf-8")
    issues = verify_manifest(tmp_path, manifest)
    assert any("manifest unreadable" in issue for issue in issues)


def test_verify_manifest_rejects_invalid_shapes(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"files": {"not": "a list"}}), encoding="utf-8")
    issues = verify_manifest(tmp_path, manifest)
    assert "manifest files field is not a list" in issues
    manifest.write_text(
        json.dumps(
            {
                "files": [
                    12,
                    {"path": 42},
                    {"path": "missing.txt", "size_bytes": 0, "sha256": "0" * 64},
                ]
            }
        ),
        encoding="utf-8",
    )
    issues = verify_manifest(tmp_path, manifest)
    assert any("non-object entry" in issue for issue in issues)
    assert any("no valid path" in issue for issue in issues)
    assert any("missing.txt: file missing" in issue for issue in issues)
    assert any("missing.txt: listed but absent" in issue for issue in issues)


def test_verify_manifest_detects_tampering_and_extra_file(tmp_path: Path) -> None:
    data = tmp_path / "data.txt"
    data.write_text("alpha\n", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    build_manifest(tmp_path, manifest)
    data.write_text("alpha changed\n", encoding="utf-8")
    (tmp_path / "unexpected.txt").write_text("extra\n", encoding="utf-8")
    issues = verify_manifest(tmp_path, manifest)
    assert any("size mismatch" in issue for issue in issues)
    assert any("SHA-256 mismatch" in issue for issue in issues)
    assert any("unexpected.txt: unlisted file" in issue for issue in issues)


def test_build_release_rejects_existing_output(tmp_path: Path) -> None:
    metrics_path, daily_path = _write_valid_inputs(tmp_path)
    output = tmp_path / "release"
    output.mkdir()
    with pytest.raises(FileExistsError, match="Output already exists"):
        build_public_release(metrics_path, daily_path, output, private_artifact_sha256="a" * 64)


def test_build_release_rejects_missing_metrics(tmp_path: Path) -> None:
    metrics_path, daily_path = _write_valid_inputs(tmp_path)
    metrics = pd.read_csv(metrics_path)
    metrics = metrics.drop(columns=["calmar"])
    metrics.to_csv(metrics_path, index=False)
    with pytest.raises(ValueError, match="Missing metric columns"):
        build_public_release(
            metrics_path, daily_path, tmp_path / "release", private_artifact_sha256="a" * 64
        )


@pytest.mark.parametrize(
    "daily_columns",
    [
        {"not_a_date": ["2026-01-01"], "nostra_ai_equity": [1.0], "nostra_ai_drawdown": [0.0]},
        {
            "date": ["2026-01-01"],
            "timestamp": ["2026-01-01"],
            "nostra_ai_equity": [1.0],
            "nostra_ai_drawdown": [0.0],
        },
    ],
)
def test_build_release_rejects_invalid_timestamp_surface(
    tmp_path: Path, daily_columns: dict[str, list[object]]
) -> None:
    metrics_path, _ = _write_valid_inputs(tmp_path)
    daily_path = tmp_path / "invalid-daily.csv"
    pd.DataFrame(daily_columns).to_csv(daily_path, index=False)
    with pytest.raises(ValueError, match="Exactly one timestamp"):
        build_public_release(
            metrics_path, daily_path, tmp_path / "release", private_artifact_sha256="a" * 64
        )


def test_scan_tree_ignores_coverage_artifacts(tmp_path: Path) -> None:
    private_path = "/" + "Users" + "/coverage-user/private-project"
    for name in (".coverage", ".coverage.worker-1", "coverage.xml"):
        (tmp_path / name).write_text(private_path, encoding="utf-8")
    (tmp_path / "safe.md").write_text("Public benchmark documentation.\n", encoding="utf-8")
    assert scan_tree(tmp_path) == []
