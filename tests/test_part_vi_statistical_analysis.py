from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

SOURCE_DIR = ROOT / "artifacts" / "candidates" / "v0.3.0" / "quantitative_aggregates"

SUPPORT_DIR = ROOT / "artifacts" / "report_support" / "part_vi"

SUMMARY_PATH = SUPPORT_DIR / "part_vi_statistical_summary.json"
BITCOIN_HAC_PATH = SUPPORT_DIR / "bitcoin_passive_hac_sharpe.json"
MANIFEST_PATH = SUPPORT_DIR / "manifest.json"
CHECKSUMS_PATH = SUPPORT_DIR / "SHA256SUMS"

MARKDOWN_PATH = ROOT / "docs" / "tables" / "part_vi_statistical_results.md"

GENERATOR_PATH = ROOT / "tools" / "generate_part_vi_statistical_analysis.py"
BITCOIN_GENERATOR_PATH = ROOT / "tools" / "generate_part_vi_bitcoin_hac.py"
INTEGRATOR_PATH = ROOT / "tools" / "integrate_part_vi_bitcoin_hac.py"

FIGURE_PATHS = [
    ROOT / "docs" / "figures" / "figure_6_1_pbo_aggregate_sensitivity.png",
    ROOT / "docs" / "figures" / "figure_6_2_benchmark_bootstrap_pvalues.png",
    ROOT / "docs" / "figures" / "figure_6_3_benchmark_bootstrap_intervals.png",
    ROOT / "docs" / "figures" / "figure_6_4_hac_sharpe_sensitivity.png",
    ROOT / "docs" / "figures" / "figure_6_5_circular_bootstrap_intervals.png",
]


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


def test_part_vi_summary_contract() -> None:
    payload = load_summary()

    assert payload["schema_version"] == 1
    assert payload["package"] == ("part_vi_statistical_report_support")
    assert payload["model"] == "Nostra AI V5.246"
    assert payload["source_release"] == "v0.3.0"

    period = payload["period"]

    assert period == {
        "start": "2020-05-14",
        "end": "2026-06-02",
        "observations": 2211,
        "annualization": 365,
    }


def test_psr_and_dsr_controlled_values() -> None:
    payload = load_summary()

    psr = payload["probabilistic_sharpe_ratio"]
    dsr = payload["deflated_sharpe_ratio"]

    assert float(psr["probability"]) == pytest.approx(
        0.999967305016425,
        rel=1e-14,
        abs=1e-15,
    )
    assert float(psr["observed_annualized_sharpe"]) == pytest.approx(
        1.587687113383514,
        rel=1e-14,
        abs=1e-15,
    )

    assert int(dsr["trial_count"]) == 15
    assert float(dsr["probability"]) == pytest.approx(
        0.99996656687852,
        rel=1e-14,
        abs=1e-15,
    )


def test_multiple_testing_contract() -> None:
    multiple = load_summary()["multiple_testing"]

    assert multiple["candidate_count"] == 15
    assert multiple["repetitions"] == 2000
    assert multiple["block_size"] == 21
    assert multiple["private_matrix_disclosed"] is False

    assert multiple["white_reality_check"]["reported_p_value"] == 0.0
    assert multiple["hansen_spa"]["reported_p_value"] == 0.0


def test_pbo_controlled_values() -> None:
    pbo = load_summary()["backtest_overfitting"]

    assert pbo["blocks"] == 8
    assert pbo["tested_setting_count"] == 4
    assert pbo["results_below_0_20"] == 3

    assert float(pbo["pbo_minimum"]) == pytest.approx(0.1)
    assert float(pbo["pbo_median"]) == pytest.approx(0.157142857142857)
    assert float(pbo["pbo_mean"]) == pytest.approx(0.182142857142857)
    assert float(pbo["pbo_maximum"]) == pytest.approx(0.314285714285714)


def test_benchmark_significance_rule() -> None:
    payload = load_summary()
    bootstrap = payload["moving_block_bootstrap"]
    reading = payload["consolidated_reading"]

    records = bootstrap["records"]

    assert len(records) == 11
    assert bootstrap["positive_cagr_differences"] == 11
    assert bootstrap["significant_at_5_percent"] == 2

    for record in records:
        p_value = float(record["one_sided_p_value"])
        lower = float(record["ci95_lower_annualized_log"])
        official = bool(record["significant_compounded_outperformance"])

        assert official is (p_value < 0.05 and lower > 0.0)

    assert reading["official_significant_benchmarks"] == [
        "FIXED_50",
        "HMM_3_STATE_WALKFORWARD",
    ]

    assert reading["p_below_0_05_but_interval_crosses_zero"] == [
        "MA_50_200",
        "MOMENTUM_270",
    ]


def test_temporal_dependence_contract() -> None:
    payload = load_summary()
    temporal = payload["temporal_dependence_sharpe"]
    reading = payload["consolidated_reading"]

    assert temporal["canonical_hac_lag_count"] == 21
    assert temporal["decision_status"] == ("PASS_WITH_OBSERVATION")

    assert float(temporal["canonical_hac_adjusted_annualized_sharpe"]) == pytest.approx(
        1.4931827873589063,
        rel=1e-14,
        abs=1e-15,
    )

    assert [int(record["lag_count"]) for record in temporal["hac_sensitivity_records"]] == [
        5,
        7,
        10,
        21,
        30,
        60,
    ]

    assert [int(record["block_size"]) for record in temporal["bootstrap_sensitivity_records"]] == [
        5,
        10,
        21,
        30,
        60,
    ]

    assert all(
        float(record["interval_lower"]) > 0.0
        for record in temporal["bootstrap_sensitivity_records"]
    )

    assert reading["all_circular_bootstrap_lower_bounds_positive"] is True


def test_six_frozen_sources_are_reconciled() -> None:
    source_records = load_summary()["source_files"]

    assert len(source_records) == 6

    for record in source_records:
        relative_path = str(record["path"])
        path = ROOT / relative_path

        assert path.parent == SOURCE_DIR
        assert path.is_file()
        assert path.stat().st_size == int(record["size_bytes"])
        assert sha256_file(path) == record["sha256"]


def test_markdown_structure_and_typography() -> None:
    markdown = MARKDOWN_PATH.read_text(encoding="utf-8")

    expected_headings = [
        "## Tableau 6.1",
        "## Tableau 6.2",
        "## Tableau 6.3",
        "## Tableau 6.4",
        "## Tableau 6.5A",
        "## Tableau 6.5B",
        "## Tableau 6.5C",
        "## Tableau 6.6",
        "## Limites obligatoires",
    ]

    for heading in expected_headings:
        assert heading in markdown

    forbidden_fragments = [
        "Verdict officiel|",
        "Significatif|",
        "essaisagrégés",
        "répétitionspubliées",
    ]

    for fragment in forbidden_fragments:
        assert fragment not in markdown

    assert ("Deux comparaisons sur onze satisfont la règle complète") in markdown
    assert "0,8184" in markdown
    assert "Aucun calcul HAC équivalent" not in markdown


def test_five_controlled_figures_are_valid_pngs() -> None:
    assert len(FIGURE_PATHS) == 5

    for path in FIGURE_PATHS:
        assert path.is_file()
        assert path.stat().st_size > 50_000

        width, height = png_dimensions(path)

        assert width >= 3000
        assert height >= 1600


def test_part_vi_manifest_and_checksums_reconcile() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    manifest_records = {str(record["path"]): record for record in manifest["files"]}

    expected_paths = {
        SUMMARY_PATH.relative_to(ROOT).as_posix(),
        BITCOIN_HAC_PATH.relative_to(ROOT).as_posix(),
        MARKDOWN_PATH.relative_to(ROOT).as_posix(),
        GENERATOR_PATH.relative_to(ROOT).as_posix(),
        BITCOIN_GENERATOR_PATH.relative_to(ROOT).as_posix(),
        INTEGRATOR_PATH.relative_to(ROOT).as_posix(),
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


def test_discrete_axis_semantics_are_explicit() -> None:
    source = GENERATOR_PATH.read_text(encoding="utf-8")

    assert ("Configurations de retards Newey-West testées") in source
    assert ("Tailles de bloc circulaire testées") in source
