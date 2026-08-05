from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

PATH = ROOT / "artifacts" / "report_support" / "part_vi" / "bitcoin_passive_hac_sharpe.json"


def load_payload() -> dict[str, object]:
    return json.loads(PATH.read_text(encoding="utf-8"))


def test_bitcoin_hac_contract() -> None:
    payload = load_payload()

    assert payload["schema_version"] == 1
    assert payload["analysis"] == ("bitcoin_passive_hac_sharpe")

    assert payload["period"] == {
        "start": "2020-05-14",
        "end": "2026-06-02",
        "observations": 2211,
        "annualization": 365,
    }


def test_bitcoin_hac_reconciliation() -> None:
    payload = load_payload()

    assert float(payload["reconciliation"]["final_equity"]) == pytest.approx(
        7.212950328296465,
        rel=1e-14,
        abs=1e-15,
    )


def test_bitcoin_hac_canonical_values() -> None:
    canonical = load_payload()["canonical"]

    assert canonical["lag_count"] == 21

    assert float(canonical["conventional_annualized_sharpe"]) == pytest.approx(
        0.8535246890964329,
        rel=1e-14,
        abs=1e-15,
    )

    assert float(canonical["hac_adjusted_annualized_sharpe"]) == pytest.approx(
        0.8183668937097701,
        rel=1e-14,
        abs=1e-15,
    )

    assert float(canonical["volatility_inflation_factor"]) == pytest.approx(
        1.0429609208985564,
        rel=1e-14,
        abs=1e-15,
    )


def test_bitcoin_hac_sensitivity_lags() -> None:
    records = load_payload()["sensitivity_records"]

    assert [int(record["lag_count"]) for record in records] == [5, 7, 10, 21, 30, 60]

    expected = [
        0.8633818216080775,
        0.8552099317467419,
        0.8492328804609579,
        0.8183668937097701,
        0.8016460827936712,
        0.7349583327640395,
    ]

    observed = [float(record["hac_adjusted_annualized_sharpe"]) for record in records]

    assert observed == pytest.approx(
        expected,
        rel=1e-14,
        abs=1e-15,
    )


def test_bitcoin_hac_is_integrated_into_summary() -> None:
    summary_path = (
        ROOT / "artifacts" / "report_support" / "part_vi" / "part_vi_statistical_summary.json"
    )

    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    reading = summary["consolidated_reading"]

    assert float(reading["bitcoin_canonical_hac_adjusted_sharpe"]) == pytest.approx(
        0.8183668937097701,
        rel=1e-14,
        abs=1e-15,
    )

    assert float(reading["canonical_hac_sharpe_advantage"]) == pytest.approx(
        0.6748158936491362,
        rel=1e-14,
        abs=1e-15,
    )


def test_bitcoin_hac_is_integrated_into_markdown() -> None:
    markdown_path = ROOT / "docs" / "tables" / "part_vi_statistical_results.md"

    markdown = markdown_path.read_text(encoding="utf-8")

    assert "Bitcoin passif HAC" in markdown
    assert "0,8184" in markdown
    assert "+0,6748" in markdown
    assert "Aucun calcul HAC équivalent du bitcoin passif" not in markdown
