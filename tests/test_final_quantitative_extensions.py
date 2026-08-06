from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


EXTENSION = load_module(
    "generate_final_quantitative_extensions",
    ROOT / "tools" / "generate_final_quantitative_extensions.py",
)
INDEPENDENT = load_module(
    "independently_recalculate_accounting_core",
    ROOT / "tools" / "independently_recalculate_accounting_core.py",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def test_constant_exposure_reconciles_half_scaling() -> None:
    raw = np.array([0.10, -0.05, 0.02], dtype=float)
    observed = EXTENSION.constant_exposure_returns(
        raw,
        0.5,
        cost_rate=0.0025,
    )
    expected = np.array([0.04875, -0.025, 0.01], dtype=float)
    np.testing.assert_allclose(observed, expected, rtol=0.0, atol=1e-15)


def test_strategy_restarts_from_cash() -> None:
    raw = np.array([0.10, -0.05, 0.02], dtype=float)
    exposure = np.array([0.4, 0.7, 0.2], dtype=float)
    returns, turnover = EXTENSION.strategy_returns_from_cash(
        raw,
        exposure,
        cost_rate=0.0025,
    )
    expected_turnover = np.array([0.4, 0.3, 0.5], dtype=float)
    expected_returns = exposure * raw - 0.0025 * expected_turnover
    np.testing.assert_allclose(turnover, expected_turnover, rtol=0.0, atol=1e-15)
    np.testing.assert_allclose(returns, expected_returns, rtol=0.0, atol=1e-15)


def test_maximum_drawdown_includes_initial_capital() -> None:
    returns = np.array([0.10, -0.20, 0.05], dtype=float)
    observed = EXTENSION.maximum_drawdown(returns)
    expected = (1.10 * 0.80) / 1.10 - 1.0
    assert abs(observed - expected) <= 1e-15


def test_independent_delay_and_turnover() -> None:
    asset = np.array([0.10, -0.05, 0.02, 0.03], dtype=float)
    exposure = np.array([0.4, 0.7, 0.2, 0.5], dtype=float)
    result = INDEPENDENT.independently_backtest(
        asset,
        exposure,
        cost_bps=25.0,
        extra_delay=1,
    )
    expected_exposure = np.array([0.0, 0.4, 0.7, 0.2], dtype=float)
    expected_turnover = np.array([0.0, 0.4, 0.3, 0.5], dtype=float)
    expected_returns = expected_exposure * asset - 0.0025 * expected_turnover
    np.testing.assert_allclose(result["exposure"], expected_exposure, rtol=0.0, atol=1e-15)
    np.testing.assert_allclose(result["turnover"], expected_turnover, rtol=0.0, atol=1e-15)
    np.testing.assert_allclose(result["net_returns"], expected_returns, rtol=0.0, atol=1e-15)


def test_metrics_contract() -> None:
    returns = np.array([0.01, -0.02, 0.03, 0.00], dtype=float)
    extension_metrics = EXTENSION.metrics(returns)
    independent_metrics = INDEPENDENT.independently_measure(returns)
    for field in (
        "final_equity",
        "cagr",
        "annualized_volatility",
        "sharpe",
        "maximum_drawdown",
    ):
        assert abs(float(extension_metrics[field]) - independent_metrics[field]) <= 1e-15


def test_committed_manifests_and_summaries() -> None:
    manifests = [
        ROOT / "artifacts" / "report_support" / "part_v_extension" / "manifest.json",
        ROOT / "artifacts" / "report_support" / "part_vii_extension" / "manifest.json",
        ROOT / "artifacts" / "report_support" / "part_x" / "manifest.json",
    ]
    for manifest_path in manifests:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert payload["schema_version"] == 1
        assert payload["model"] == "Nostra AI V5.246"
        assert payload["source_release"] == "v0.3.0"
        for record in payload["files"]:
            path = ROOT / record["path"]
            assert path.is_file()
            assert path.stat().st_size == record["size_bytes"]
            assert sha256_file(path) == record["sha256"]


def test_summary_publication_boundaries() -> None:
    part_v = json.loads(
        (
            ROOT
            / "artifacts"
            / "report_support"
            / "part_v_extension"
            / "part_v_final_extension_summary.json"
        ).read_text(encoding="utf-8")
    )
    part_vii = json.loads(
        (
            ROOT
            / "artifacts"
            / "report_support"
            / "part_vii_extension"
            / "part_vii_entry_rolling_summary.json"
        ).read_text(encoding="utf-8")
    )
    part_x = json.loads(
        (
            ROOT
            / "artifacts"
            / "report_support"
            / "part_x"
            / "independent_accounting_recalculation_summary.json"
        ).read_text(encoding="utf-8")
    )

    assert len(part_v["comparators"]) == 4
    assert len(part_v["concentration"]) == 12
    assert len(part_v["attribution"]["exposure_buckets"]) == 4
    assert len(part_vii["rolling_horizons"]) == 5
    assert (
        part_vii["start_date_sensitivity"]["monthly_start_count_with_at_least_365_observations"]
        >= 40
    )
    assert len(part_x["scenario_records"]) == 9
    differences = part_x["reconciliation"]["maximum_aggregate_absolute_differences"]
    assert max(float(value) for value in differences.values()) <= 5e-8
