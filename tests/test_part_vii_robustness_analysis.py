from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

SOURCE_DIR = ROOT / "artifacts" / "candidates" / "v0.3.0" / "quantitative_aggregates"
SUPPORT_DIR = ROOT / "artifacts" / "report_support" / "part_vii"

SUMMARY_PATH = SUPPORT_DIR / "part_vii_robustness_summary.json"
MANIFEST_PATH = SUPPORT_DIR / "manifest.json"
CHECKSUMS_PATH = SUPPORT_DIR / "SHA256SUMS"

MARKDOWN_PATH = ROOT / "docs" / "tables" / "part_vii_robustness_results.md"
GENERATOR_PATH = ROOT / "tools" / "generate_part_vii_robustness_analysis.py"

FIGURE_PATHS = [
    ROOT / "docs" / "figures" / "figure_7_1_stationarity_diagnostics.png",
    ROOT / "docs" / "figures" / "figure_7_2_distribution_drift_rates.png",
    ROOT / "docs" / "figures" / "figure_7_3_regime_active_log_return.png",
    ROOT / "docs" / "figures" / "figure_7_4_regime_sharpe_comparison.png",
    ROOT / "docs" / "figures" / "figure_7_5_configuration_similarity.png",
    ROOT / "docs" / "figures" / "figure_7_6_placebo_empirical_pvalues.png",
]

SOURCE_SHA256 = {
    "stationarity.json": ("d9477db1d63d5e4cb8d94e0efe3f2a7eb5fa4420d12297f8332f90e5165b644b"),
    "distribution_drift.json": ("c63529eb069230da89537131b264a69068519e26e7ce67527d0d840bdf7b3a6a"),
    "market_regimes.json": ("9edf14197bafae5de1375f329886d85f1f8418051b2825f36763ca5a83588b12"),
    "configuration_sensitivity.json": (
        "1b69daae92a5811c5657f39672661d956474d275b45e19091dea0e682a43acf0"
    ),
    "placebo_test.json": ("62a03185ddb83ea631fc4eb66fc835d3e54bf64d2f44a2d2898023361347f2f7"),
    "ablation.json": ("f4611a66e7cdad0c62cba1bb6f413083a810bb23eaf1d94b41b0a13b91145c2c"),
    "data_resilience.json": ("7c65c02584d68b0e5be9a8c7729651f5e3c7cf7c8670c52b348e26b817bdc74a"),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
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


def test_part_vii_summary_contract() -> None:
    payload = load_summary()

    assert payload["schema_version"] == 1
    assert payload["package"] == "part_vii_robustness_report_support"
    assert payload["model"] == "Nostra AI V5.246"
    assert payload["source_release"] == "v0.3.0"

    assert payload["period"] == {
        "start": "2020-05-14",
        "end": "2026-06-02",
        "observations": 2211,
        "annualization": 365,
    }


def test_stationarity_controlled_values() -> None:
    stationarity = load_summary()["stationarity"]

    assert stationarity["series_tested"] == 8
    assert stationarity["adf_reject_unit_root_5pct"] == 2
    assert stationarity["kpss_reject_stationarity_5pct"] == 7
    assert stationarity["consistent_stationarity_5pct"] == 1
    assert stationarity["conflicting_tests_5pct"] == 1
    assert stationarity["cusum_break_candidate_count"] == 8


def test_distribution_drift_controlled_values() -> None:
    drift = load_summary()["distribution_drift"]

    rolling = drift["rolling_windows"]
    train_test = drift["train_test_folds"]

    assert rolling["comparisons"] == 136
    assert rolling["ks_reject_equal_distribution_5pct"] == 134
    assert rolling["psi_at_least_0_25"] == 125
    assert rolling["absolute_standardized_shift_at_least_1_00"] == 80

    assert train_test["comparisons"] == 136
    assert train_test["ks_reject_equal_distribution_5pct"] == 131
    assert train_test["psi_at_least_0_25"] == 130
    assert train_test["absolute_standardized_shift_at_least_1_00"] == 37


def test_regime_controlled_values() -> None:
    payload = load_summary()
    regimes = payload["market_regimes"]
    reading = payload["consolidated_reading"]

    records = regimes["records"]

    assert regimes["regime_count"] == 10
    assert regimes["aggregate_rows"] == 10
    assert len(records) == 10

    assert reading["regimes_with_positive_active_log_return"] == 8
    assert reading["regimes_with_lower_nostra_volatility"] == 10
    assert reading["regimes_with_less_severe_nostra_drawdown"] == 10
    assert reading["regimes_with_higher_nostra_sharpe"] == 10

    assert all(
        float(record["nostra_annualized_volatility"]) < float(record["btc_annualized_volatility"])
        for record in records
    )
    assert all(
        float(record["nostra_conditional_max_drawdown"])
        > float(record["btc_conditional_max_drawdown"])
        for record in records
    )
    assert all(float(record["nostra_sharpe"]) > float(record["btc_sharpe"]) for record in records)


def test_configuration_sensitivity_contract() -> None:
    configuration = load_summary()["configuration_sensitivity"]

    assert configuration["configurations_executed"] == 34
    assert configuration["configurations_failed"] == 0
    assert configuration["decision_status"] == "descriptive_evidence_only"
    assert configuration["exact_configuration_values_disclosed"] is False

    similarities = configuration["similarity_quantiles"]

    assert float(similarities["direction_agreement"]["q50"]) == pytest.approx(0.96698327)
    assert float(similarities["pearson_similarity"]["q50"]) == pytest.approx(0.96544295)
    assert float(similarities["spearman_similarity"]["q50"]) == pytest.approx(0.94487811)


def test_placebo_controlled_values() -> None:
    payload = load_summary()
    placebo = payload["placebo_test"]
    reading = payload["consolidated_reading"]

    assert placebo["permutations"] == 500
    assert placebo["cost_bps"] == 25.0
    assert placebo["delay_days"] == 0

    assert float(placebo["metrics"]["cagr"]["upper_tail_empirical_pvalue"]) == pytest.approx(
        0.01197605
    )
    assert float(
        placebo["metrics"]["final_equity"]["upper_tail_empirical_pvalue"]
    ) == pytest.approx(0.01197605)
    assert float(placebo["metrics"]["sharpe"]["upper_tail_empirical_pvalue"]) == pytest.approx(
        0.03792415
    )
    assert float(placebo["metrics"]["calmar"]["upper_tail_empirical_pvalue"]) == pytest.approx(
        0.37125749
    )

    assert reading["placebo_metrics_below_5_percent"] == [
        "cagr",
        "final_equity",
        "sharpe",
    ]
    assert reading["placebo_metrics_not_below_5_percent"] == [
        "calmar",
    ]


def test_ablation_contract() -> None:
    ablation = load_summary()["ablation"]

    assert ablation["anonymous_ablation_count"] == 15
    assert ablation["paired_bootstrap_comparisons"] == 14
    assert ablation["comparisons_with_interval_including_zero"] == 14
    assert ablation["comparisons_with_positive_95pct_interval"] == 0
    assert ablation["comparisons_with_negative_95pct_interval"] == 0
    assert ablation["identities_disclosed"] is False
    assert ablation["decision_status"] == "descriptive_evidence_only"


def test_data_resilience_contract() -> None:
    resilience = load_summary()["data_resilience"]

    assert resilience["scenario_count_excluding_baseline"] == 23
    assert resilience["scenario_family_count"] == 3
    assert resilience["bootstrap_runs"] == 300
    assert resilience["bootstrap_block_length"] == 30
    assert resilience["cross_provider_comparison_completed"] is False
    assert resilience["decision_status"] == "descriptive_evidence_only"


def test_seven_frozen_sources_are_reconciled() -> None:
    source_records = load_summary()["source_files"]

    assert len(source_records) == 7

    for record in source_records:
        relative_path = str(record["path"])
        path = ROOT / relative_path

        assert path.parent == SOURCE_DIR
        assert path.is_file()
        assert path.stat().st_size == int(record["size_bytes"])
        assert sha256_file(path) == record["sha256"]
        assert sha256_file(path) == SOURCE_SHA256[path.name]


def test_markdown_structure_and_typography() -> None:
    markdown = MARKDOWN_PATH.read_text(encoding="utf-8")

    expected_headings = [
        "## Tableau 7.1",
        "## Tableau 7.2",
        "## Tableau 7.3",
        "## Tableau 7.4",
        "## Tableau 7.5",
        "## Tableau 7.6",
        "## Tableau 7.7",
        "## Tableau 7.8",
        "## Limites obligatoires",
    ]

    for heading in expected_headings:
        assert heading in markdown

    assert "134" in markdown
    assert "131" in markdown
    assert "34 configurations exécutées" in markdown
    assert "14 intervalles appariés sur 14 incluent zéro" in markdown
    assert "Aucune comparaison croisée entre plusieurs fournisseurs" in markdown


def test_six_controlled_figures_are_valid_pngs() -> None:
    assert len(FIGURE_PATHS) == 6

    for path in FIGURE_PATHS:
        assert path.is_file()
        assert path.stat().st_size > 50_000

        width, height = png_dimensions(path)

        assert width == 3520
        assert height == 1980


def test_part_vii_manifest_and_checksums_reconcile() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    assert manifest["package"] == "part_vii_robustness_report_support"

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


def test_no_private_path_is_published() -> None:
    controlled_text_paths = [
        GENERATOR_PATH,
        SUMMARY_PATH,
        MANIFEST_PATH,
        CHECKSUMS_PATH,
        MARKDOWN_PATH,
    ]

    forbidden_fragments = [
        "/Users/clovishilmarcher",
        "v5249_v5246_exact_daily_trace",
        "import_20260729T085854Z",
    ]

    for path in controlled_text_paths:
        content = path.read_text(encoding="utf-8")

        for fragment in forbidden_fragments:
            assert fragment not in content


def test_consolidated_reading_is_proportionate() -> None:
    reading = load_summary()["consolidated_reading"]

    assert reading["stationarity_can_be_assumed"] is False
    assert reading["pervasive_distribution_drift_detected"] is True
    assert reading["cross_provider_comparison_completed"] is False
    assert reading["reading_status"] == "favorable_with_material_observations"
