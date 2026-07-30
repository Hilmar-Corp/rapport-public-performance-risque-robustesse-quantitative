from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
import pytest

from hilmarbench.backtest import (
    BacktestConfig,
    run_backtest,
)

ROOT = Path(__file__).resolve().parents[1]


def test_governed_negative_exposure_is_supported() -> None:
    index = pd.date_range(
        "2026-01-01",
        periods=1,
        freq="D",
        tz="UTC",
    )

    returns = pd.Series(
        [0.10],
        index=index,
    )

    decision = pd.Series(
        [-0.10],
        index=index,
    )

    frame = run_backtest(
        returns,
        decision,
        execution_lag_days=0,
        config=BacktestConfig(
            cost_bps=25.0,
            minimum_position=-0.10,
            maximum_position=1.0,
        ),
    )

    assert frame.iloc[0]["position"] == pytest.approx(-0.10)

    assert frame.iloc[0]["turnover"] == pytest.approx(0.10)


def test_machine_methodology_records_distinct_ranges() -> None:
    data = json.loads((ROOT / "artifacts/latest/methodology.json").read_text(encoding="utf-8"))

    assert data["public_baselines"]["exposure_minimum"] == 0.0

    assert data["public_baselines"]["exposure_maximum"] == 1.0

    assert data["nostra"]["governed_exposure_minimum"] == -0.10

    assert data["nostra"]["governed_exposure_maximum"] == 1.0


def test_github_actions_are_immutably_pinned() -> None:
    workflows = sorted((ROOT / ".github/workflows").glob("*.yml"))

    assert workflows

    pattern = re.compile(
        r"^\s*uses:\s*[^@\s]+@([0-9a-f]{40})\s*$",
        re.MULTILINE,
    )

    for workflow in workflows:
        text = workflow.read_text(encoding="utf-8")

        uses_lines = [line for line in text.splitlines() if "uses:" in line]

        assert uses_lines

        matches = pattern.findall(text)

        assert len(matches) == len(uses_lines), workflow


def test_exact_constraint_file() -> None:
    path = ROOT / "requirements/constraints-py313.txt"

    lines = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]

    assert len(lines) >= 10

    assert all("==" in line and " @ " not in line for line in lines)


def test_versioned_release_matches_latest() -> None:
    latest = ROOT / "artifacts/latest"

    releases = ROOT / "artifacts/releases"

    versioned = max(
        (
            release
            for release in releases.iterdir()
            if (
                release.is_dir()
                and release.name.startswith("v")
                and all(part.isdigit() for part in release.name[1:].split("."))
            )
        ),
        key=lambda release: tuple(int(part) for part in release.name[1:].split(".")),
    )

    latest_files = {path.name: path.read_bytes() for path in latest.iterdir() if path.is_file()}

    versioned_files = {
        path.name: path.read_bytes() for path in versioned.iterdir() if path.is_file()
    }

    assert versioned_files == latest_files
