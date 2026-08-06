from __future__ import annotations

import hashlib
import json
import struct
from itertools import pairwise
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

SOURCE_DIR = ROOT / "artifacts" / "candidates" / "v0.3.0" / "quantitative_aggregates"
SUPPORT_DIR = ROOT / "artifacts" / "report_support" / "part_ix"

SUMMARY_PATH = SUPPORT_DIR / "part_ix_execution_capacity_shadow_summary.json"
MANIFEST_PATH = SUPPORT_DIR / "manifest.json"
CHECKSUMS_PATH = SUPPORT_DIR / "SHA256SUMS"

MARKDOWN_PATH = ROOT / "docs" / "tables" / "part_ix_execution_capacity_shadow_results.md"
GENERATOR_PATH = ROOT / "tools" / "generate_part_ix_execution_capacity_shadow_analysis.py"

FIGURE_PATHS = [
    ROOT / "docs" / "figures" / "figure_9_1_cost_delay_cagr.png",
    ROOT / "docs" / "figures" / "figure_9_2_cost_delay_risk_adjusted_performance.png",
    ROOT / "docs" / "figures" / "figure_9_3_synthetic_execution_cost_surface.png",
    ROOT / "docs" / "figures" / "figure_9_4_synthetic_capacity_constraints.png",
]

SOURCE_SHA256 = {
    "execution_cost_delay.json": (
        "ae0485d907b9c3cb01fb26dbe05f95bbdc127491b31a458bfdb051fbc04ae38c"
    ),
    "shadow_monitoring.json": ("6f7199b73f3423ab1eeb4c4cf7572939ddd0cb7f86b81fa3e5e2adb042e02d7d"),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for block in iter(
            lambda: stream.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def load_summary() -> dict[str, object]:
    return json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))


def png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()

    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    assert data[12:16] == b"IHDR"

    return struct.unpack(
        ">II",
        data[16:24],
    )


def test_part_ix_summary_contract() -> None:
    payload = load_summary()

    assert payload["schema_version"] == 1
    assert payload["section"] == "part_ix_execution_capacity_shadow"
    assert payload["model"] == "Nostra AI V5.246"
    assert payload["source_release"] == "v0.3.0"

    assert payload["historical_evaluation"] == {
        "start": "2020-05-14",
        "end": "2026-06-02",
        "observations": 2211,
        "annualization": 365,
    }


def test_two_frozen_sources_are_reconciled() -> None:
    sources = load_summary()["sources"]

    assert len(sources) == 2

    for record in sources:
        path = ROOT / str(record["path"])

        assert path.parent == SOURCE_DIR
        assert path.is_file()
        assert sha256_file(path) == str(record["sha256"])
        assert sha256_file(path) == SOURCE_SHA256[path.name]
        assert record["schema_version"] == 1


def test_historical_cost_delay_grid_contract() -> None:
    historical = load_summary()["historical_cost_delay"]

    assert historical["verification_level"] == "artifact-verified"
    assert historical["candidate_count"] == 2
    assert historical["record_count"] == 36
    assert historical["reference_record_count"] == 18
    assert historical["comparison_record_count"] == 18
    assert historical["cost_levels_bps"] == [
        0.0,
        10.0,
        25.0,
        50.0,
        75.0,
        100.0,
    ]
    assert historical["delay_levels_days"] == [0, 1, 2]
    assert float(historical["reference_reconciliation_max_abs_delta"]) <= 1e-12


def test_selected_historical_scenarios_match_controlled_values() -> None:
    selected = load_summary()["historical_cost_delay"]["selected_reference_scenarios"]

    baseline = selected["baseline_25bps_0day"]
    high_cost = selected["high_cost_100bps_0day"]
    delayed = selected["delay_25bps_2days"]
    combined = selected["combined_100bps_2days"]

    assert float(baseline["cagr"]) == pytest.approx(0.52453667)
    assert float(baseline["sharpe"]) == pytest.approx(1.58768711)
    assert float(baseline["maximum_drawdown"]) == pytest.approx(-0.21390504)
    assert float(baseline["final_equity"]) == pytest.approx(12.86364198)

    assert float(high_cost["cagr"]) == pytest.approx(0.43879971)
    assert float(high_cost["sharpe"]) == pytest.approx(1.38956058)
    assert float(high_cost["maximum_drawdown"]) == pytest.approx(-0.23465869)

    assert float(delayed["cagr"]) == pytest.approx(0.49602016)
    assert float(delayed["sharpe"]) == pytest.approx(1.52783998)
    assert float(delayed["maximum_drawdown"]) == pytest.approx(-0.23442840)

    assert float(combined["cagr"]) == pytest.approx(0.41189284)
    assert float(combined["sharpe"]) == pytest.approx(1.32903353)
    assert float(combined["maximum_drawdown"]) == pytest.approx(-0.25467519)


def test_reference_performance_degrades_monotonically_with_cost() -> None:
    records = load_summary()["historical_cost_delay"]["reference_records"]

    for delay in (0, 1, 2):
        selected = sorted(
            [record for record in records if int(record["delay_days"]) == delay],
            key=lambda record: float(record["cost_bps"]),
        )

        cagrs = [float(record["cagr"]) for record in selected]
        sharpes = [float(record["sharpe"]) for record in selected]
        equities = [float(record["final_equity"]) for record in selected]

        assert all(left > right for left, right in pairwise(cagrs))
        assert all(left > right for left, right in pairwise(sharpes))
        assert all(left > right for left, right in pairwise(equities))
        assert all(value > 0.0 for value in cagrs)
        assert all(value > 0.0 for value in sharpes)


def test_synthetic_execution_surface_contract() -> None:
    framework = load_summary()["generic_execution_framework"]
    records = framework["synthetic_execution_surface"]
    assumptions = framework["synthetic_assumptions"]

    assert framework["status"] == ("methodologically_available_not_real_world_calibrated")
    assert len(records) == 48

    assert assumptions["fee_bps"] == pytest.approx(2.0)
    assert assumptions["half_spread_bps"] == pytest.approx(3.0)
    assert assumptions["slippage_bps"] == pytest.approx(5.0)
    assert assumptions["impact_coefficient_bps"] == pytest.approx(8.0)
    assert assumptions["impact_exponent"] == pytest.approx(0.5)
    assert assumptions["reference_participation_rate"] == pytest.approx(0.01)
    assert assumptions["maximum_participation_rate"] == pytest.approx(0.10)


def test_synthetic_execution_costs_are_monotonic() -> None:
    records = load_summary()["generic_execution_framework"]["synthetic_execution_surface"]

    for volatility in (0.02, 0.04, 0.08):
        for slippage in (0.0, 5.0, 10.0, 25.0):
            selected = sorted(
                [
                    record
                    for record in records
                    if (
                        float(record["daily_volatility"]) == pytest.approx(volatility)
                        and float(record["slippage_bps"]) == pytest.approx(slippage)
                    )
                ],
                key=lambda record: float(record["order_notional"]),
            )

            costs = [float(record["total_cost_bps"]) for record in selected]
            impacts = [float(record["market_impact_bps"]) for record in selected]

            assert len(selected) == 4
            assert costs == sorted(costs)
            assert impacts == sorted(impacts)


def test_synthetic_capacity_contract() -> None:
    framework = load_summary()["generic_execution_framework"]
    records = framework["synthetic_capacity_records"]

    assert len(records) == 21
    assert framework["real_capacity_estimate_available"] is False

    calibration = framework["real_calibration_inputs_available"]

    assert not any(calibration.values())

    for record in records:
        assert float(record["maximum_notional"]) <= 10_000_000.0
        assert float(record["participation_rate"]) <= 0.10
        assert record["binding_constraint"] in {
            "fixed_cost",
            "expected_edge",
            "participation_limit",
        }


def test_synthetic_capacity_is_monotonic_in_edge() -> None:
    records = load_summary()["generic_execution_framework"]["synthetic_capacity_records"]

    for volatility in (0.02, 0.04, 0.08):
        selected = sorted(
            [
                record
                for record in records
                if float(record["daily_volatility"]) == pytest.approx(volatility)
            ],
            key=lambda record: float(record["expected_gross_edge_bps"]),
        )

        notionals = [float(record["maximum_notional"]) for record in selected]

        assert notionals == sorted(notionals)
        assert notionals[0] == pytest.approx(0.0)
        assert notionals[-1] == pytest.approx(10_000_000.0)


def test_shadow_monitoring_matches_frozen_snapshot() -> None:
    shadow = load_summary()["shadow_monitoring"]

    assert shadow["first_observed_day"] == "2026-06-26"
    assert shadow["last_observed_day"] == "2026-07-20"
    assert shadow["calendar_days"] == 25
    assert shadow["observed_days"] == 23
    assert shadow["missing_day_count"] == 2
    assert float(shadow["coverage_ratio"]) == pytest.approx(0.92)
    assert shadow["complete_month_claim"] is False
    assert shadow["technical_collection_complete"] is True
    assert shadow["human_approval_required"] is True
    assert shadow["pilot_or_limited_production_approval"] is False
    assert shadow["production_readiness_decision"] == "not_made"


def test_shadow_does_not_claim_client_or_external_validation() -> None:
    shadow = load_summary()["shadow_monitoring"]
    outcome = load_summary()["outcome_analysis"]

    assert shadow["client_orders_executed"] is False
    assert shadow["client_production_use"] is False
    assert shadow["external_independent_validation"] is False
    assert shadow["performance_outcome_metrics_disclosed"] is False

    assert outcome["status"] == "LIMITED_OBSERVATION_WINDOW"
    assert outcome["historical_to_shadow_performance_comparison_available"] is False
    assert "does not establish production readiness" in outcome["authorized_conclusion"]


def test_evidence_tiers_are_separated() -> None:
    separation = load_summary()["evidence_separation"]

    assert separation["historical"]["status"] == "artifact-verified"
    assert separation["shadow"]["status"] == ("internal_operational_evidence")
    assert separation["pilot"]["status"] == ("not_approved_in_public_snapshot")
    assert separation["client_production"]["status"] == "not_established"


def test_markdown_structure_and_controlled_language() -> None:
    markdown = MARKDOWN_PATH.read_text(encoding="utf-8")

    expected_headings = [
        "## Tableau 9.1",
        "## Tableau 9.2",
        "## Tableau 9.3",
        "## Tableau 9.4",
        "## Lecture consolidée",
        "### Limites",
    ]

    for heading in expected_headings:
        assert heading in markdown

    assert "43,88 %" in markdown
    assert "49,60 %" in markdown
    assert "41,19 %" in markdown
    assert "23 jours observés" in markdown
    assert "couverture de 92 %" not in markdown.lower()
    assert "ne représentent ni Nostra AI" in markdown
    assert "n'est pas une estimation de capacité réelle" in markdown
    assert "Aucune décision publique de readiness" in markdown


def test_four_controlled_figures_are_valid_pngs() -> None:
    assert len(FIGURE_PATHS) == 4

    for path in FIGURE_PATHS:
        assert path.is_file()
        assert path.stat().st_size > 20_000

        width, height = png_dimensions(path)

        assert width >= 2_000
        assert height >= 1_000
        assert 1.70 <= width / height <= 1.80


def test_part_ix_manifest_and_checksums_reconcile() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    assert manifest["package"] == ("part_ix_execution_capacity_shadow_report_support")
    assert manifest["model"] == "Nostra AI V5.246"
    assert manifest["source_release"] == "v0.3.0"

    manifest_records = {str(record["path"]): record for record in manifest["files"]}

    expected_paths = {
        SUMMARY_PATH.relative_to(ROOT).as_posix(),
        MARKDOWN_PATH.relative_to(ROOT).as_posix(),
        GENERATOR_PATH.relative_to(ROOT).as_posix(),
        *[path.relative_to(ROOT).as_posix() for path in FIGURE_PATHS],
    }

    assert set(manifest_records) == expected_paths

    checksum_records: dict[str, str] = {}

    for line in CHECKSUMS_PATH.read_text(encoding="utf-8").splitlines():
        digest, relative_path = line.split(maxsplit=1)
        checksum_records[relative_path] = digest

    assert set(checksum_records) == expected_paths

    for relative_path, record in manifest_records.items():
        path = ROOT / relative_path
        observed_sha = sha256_file(path)

        assert path.is_file()
        assert path.stat().st_size == int(record["size_bytes"])
        assert observed_sha == record["sha256"]
        assert observed_sha == checksum_records[relative_path]


def test_no_private_path_or_uncontrolled_claim_is_published() -> None:
    controlled_text_paths = [
        GENERATOR_PATH,
        SUMMARY_PATH,
        MANIFEST_PATH,
        CHECKSUMS_PATH,
        MARKDOWN_PATH,
    ]

    forbidden_fragments = [
        "/Users/clovishilmarcher",
        "private_working_copy",
        "daily_nostra_position",
        "daily_nostra_return",
        'production_ready": true',
        'capacity_estimate_available": true',
        'external_independent_validation": true',
    ]

    for path in controlled_text_paths:
        content = path.read_text(encoding="utf-8")

        for fragment in forbidden_fragments:
            assert fragment not in content
