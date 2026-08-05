from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

SOURCE_DIR = ROOT / "artifacts" / "candidates" / "v0.3.0" / "quantitative_aggregates"
SUPPORT_DIR = ROOT / "artifacts" / "report_support" / "part_viii"

SUMMARY_PATH = SUPPORT_DIR / "part_viii_risk_stress_summary.json"
MANIFEST_PATH = SUPPORT_DIR / "manifest.json"
CHECKSUMS_PATH = SUPPORT_DIR / "SHA256SUMS"

MARKDOWN_PATH = ROOT / "docs" / "tables" / "part_viii_risk_stress_results.md"
GENERATOR_PATH = ROOT / "tools" / "generate_part_viii_risk_stress_analysis.py"

FIGURE_PATHS = [
    (ROOT / "docs" / "figures" / "figure_8_1_tail_risk_comparison.png"),
    (ROOT / "docs" / "figures" / "figure_8_2_var_es_canonical_backtesting.png"),
    (ROOT / "docs" / "figures" / "figure_8_3_drawdown_depth_distribution.png"),
    (ROOT / "docs" / "figures" / "figure_8_4_monte_carlo_risk_probabilities.png"),
    (ROOT / "docs" / "figures" / "figure_8_5_historical_reverse_stress.png"),
    (ROOT / "docs" / "figures" / "figure_8_6_counterfactual_reverse_stress_scope.png"),
]

SOURCE_SHA256 = {
    "tail_risk.json": ("29b9d94ec87da8249ae32086084bf1956f6f36bd39f0ff3db624216a67b68c56"),
    "var_es_backtesting.json": ("c1d74d449a23c1de99a5a701d97457e263f3957b796f2d1b30142a8b877fba8b"),
    "drawdown_duration_recovery.json": (
        "aac55eeef0278cbf70ee1f7816c1822d657bdc0c7b2013e65a3b6020cbd16a2d"
    ),
    "historical_block_monte_carlo.json": (
        "ddae15816201f3524eb9d8914838fda2b9cae051d7a6aecca37338afb1c9afb3"
    ),
    "historical_reverse_stress.json": (
        "679ef9da38ccaacab70b83594e460093d5c26fe975488d2a30403cae1ca5cbf5"
    ),
    "counterfactual_reverse_stress.json": (
        "8a5b35f8c9bd8da227802223c1018ac05a8e7b1ec5bd66a4e5a98b35d004aeb0"
    ),
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


def records_by_key(
    records: list[dict[str, object]],
    key: str,
) -> dict[str, dict[str, object]]:
    return {str(record[key]): record for record in records}


def test_part_viii_summary_contract() -> None:
    payload = load_summary()

    assert payload["schema_version"] == 1
    assert payload["section"] == "part_viii_risk_stress"
    assert payload["model"] == "Nostra AI V5.246"
    assert payload["source_release"] == "v0.3.0"

    assert payload["period"] == {
        "start": "2020-05-14",
        "end": "2026-06-02",
        "observations": 2211,
        "annualization": 365,
    }


def test_tail_risk_controlled_values() -> None:
    tail = load_summary()["tail_risk"]
    records = records_by_key(
        tail["records"],
        "portfolio",
    )

    nostra = records["nostra_ai"]
    bitcoin = records["bitcoin_benchmark"]

    assert float(nostra["historical_var_95_daily"]) == pytest.approx(0.02036101)
    assert float(nostra["historical_es_95_daily"]) == pytest.approx(0.03207062)
    assert float(nostra["historical_var_99_daily"]) == pytest.approx(0.03876511)
    assert float(nostra["historical_es_99_daily"]) == pytest.approx(0.05297551)

    assert float(bitcoin["historical_var_95_daily"]) == pytest.approx(0.04629105)
    assert float(bitcoin["historical_es_95_daily"]) == pytest.approx(0.06872081)
    assert float(bitcoin["historical_var_99_daily"]) == pytest.approx(0.08277503)
    assert float(bitcoin["historical_es_99_daily"]) == pytest.approx(0.10791114)

    for metric in (
        "historical_var_95_daily",
        "historical_es_95_daily",
        "historical_var_99_daily",
        "historical_es_99_daily",
    ):
        assert float(nostra[metric]) < float(bitcoin[metric])

    comparisons = tail["comparisons"]

    assert float(comparisons["var_95_reduction_ratio"]) > 0.50
    assert float(comparisons["es_95_reduction_ratio"]) > 0.50
    assert float(comparisons["var_99_reduction_ratio"]) > 0.50
    assert float(comparisons["es_99_reduction_ratio"]) > 0.50


def test_var_es_canonical_contract() -> None:
    var_es = load_summary()["var_es_backtesting"]

    assert var_es["decision_status"] == "PASS_WITH_OBSERVATION"
    assert var_es["methodological_status"] == "accepted_with_observations"
    assert var_es["canonical_calibration_window_days"] == 365
    assert var_es["observations"] == 2211

    assert var_es["canonical_traffic_light_counts"] == {
        "AMBER": 1,
        "GREEN": 3,
        "RED": 0,
    }

    assert var_es["all_sensitivity_traffic_light_counts"] == {
        "AMBER": 4,
        "GREEN": 7,
        "RED": 1,
    }

    results = var_es["canonical_results"]

    assert len(results) == 4

    pvalue_keys = (
        "kupiec_p_value",
        "exact_binomial_p_value",
        "christoffersen_independence_p_value",
        "christoffersen_conditional_coverage_p_value",
        "es_normalized_tail_loss_bootstrap_p_value",
    )

    for record in results:
        for key in pvalue_keys:
            assert float(record[key]) >= 0.05

    amber = [record for record in results if record["traffic_light"] == "AMBER"]

    assert len(amber) == 1
    assert amber[0]["risk_period_days"] == 10
    assert float(amber[0]["confidence_level"]) == pytest.approx(0.99)
    assert "LOW_EXPECTED_EXCEPTION_COUNT" in amber[0]["reason_codes"]


def test_var_es_governance_decision() -> None:
    governance = load_summary()["var_es_backtesting"]["governance_decision"]

    assert governance["approved_specification"] == ("365-day trailing historical simulation")
    assert governance["non_approved_specification"] == (
        "250-day calibration for 99 percent tail-risk measures"
    )
    assert "monitoring" in governance["monitoring_requirement"].lower()


def test_drawdown_controlled_values() -> None:
    drawdowns = load_summary()["drawdown_duration_recovery"]

    assert drawdowns["decision_status"] == "PASS_WITH_OBSERVATION"
    assert drawdowns["right_censoring_disclosed"] is True

    nostra = drawdowns["strategies"]["nostra_ai"]
    bitcoin = drawdowns["strategies"]["bitcoin_benchmark"]

    assert nostra["episode_count"] == 104
    assert bitcoin["episode_count"] == 50

    assert float(nostra["maximum_drawdown"]) == pytest.approx(-0.21390503503731573)
    assert float(bitcoin["maximum_drawdown"]) == pytest.approx(-0.7662925431645915)

    assert nostra["longest_observed_episode"]["observed_duration_observations"] == 239
    assert bitcoin["longest_observed_episode"]["observed_duration_observations"] == 847

    assert nostra["unrecovered_episode_count"] == 1
    assert bitcoin["unrecovered_episode_count"] == 1

    assert float(nostra["time_under_water_share"]) < float(bitcoin["time_under_water_share"])


def test_drawdown_depth_duration_relationship() -> None:
    strategies = load_summary()["drawdown_duration_recovery"]["strategies"]

    for strategy in strategies.values():
        all_episodes = strategy["depth_duration_spearman_all"]
        recovered = strategy["depth_duration_spearman_recovered"]

        assert float(all_episodes["rho"]) > 0.85
        assert float(all_episodes["p_value"]) < 0.05
        assert float(recovered["rho"]) > 0.85
        assert float(recovered["p_value"]) < 0.05


def test_monte_carlo_contract() -> None:
    monte_carlo = load_summary()["historical_block_monte_carlo"]

    assert monte_carlo["method"] == ("joint_moving_block_historical_resampling")

    scope = monte_carlo["scope"]

    assert scope["block_sizes"] == [7, 21, 30, 60]
    assert scope["simulation_length_days"] == 365
    assert scope["repetitions_per_configuration"] == 10_000
    assert scope["joint_resampling"] is True

    records = monte_carlo["records"]

    assert len(records) == 8

    for record in records:
        assert int(record["repetitions"]) == 10_000
        assert int(record["simulation_length_days"]) == 365
        assert float(record["probability_nostra_has_lower_drawdown"]) >= 0.9999

    comparative = monte_carlo["comparative_ranges"]

    assert float(comparative["probability_nostra_beats_btc_terminal"]["minimum"]) == pytest.approx(
        0.5482
    )
    assert float(comparative["probability_nostra_beats_btc_terminal"]["maximum"]) == pytest.approx(
        0.5807
    )


def test_monte_carlo_risk_is_lower_for_nostra() -> None:
    records = load_summary()["historical_block_monte_carlo"]["records"]

    for block_size in (7, 21, 30, 60):
        nostra = next(
            record
            for record in records
            if record["portfolio"] == "nostra_ai" and int(record["block_size"]) == block_size
        )
        bitcoin = next(
            record
            for record in records
            if (
                record["portfolio"] == "bitcoin_benchmark"
                and int(record["block_size"]) == block_size
            )
        )

        assert float(nostra["probability_terminal_loss"]) < float(
            bitcoin["probability_terminal_loss"]
        )
        assert float(nostra["probability_drawdown_below_minus_20pct"]) < float(
            bitcoin["probability_drawdown_below_minus_20pct"]
        )
        assert float(nostra["probability_drawdown_below_minus_30pct"]) < float(
            bitcoin["probability_drawdown_below_minus_30pct"]
        )
        assert float(nostra["maximum_drawdown_median"]) > float(bitcoin["maximum_drawdown_median"])


def test_historical_reverse_stress_contract() -> None:
    reverse_stress = load_summary()["historical_reverse_stress"]

    assert reverse_stress["decision_status"] == "PASS_WITH_OBSERVATION"
    assert reverse_stress["economic_reconciliation"]["status"] == "PASS"
    assert reverse_stress["global_results"]["drawdown_episode_count"] == 104
    assert reverse_stress["global_results"]["loss_breach_record_count"] == 40
    assert float(reverse_stress["global_results"]["maximum_model_drawdown"]) == pytest.approx(
        -0.2139050350373155
    )

    indexed = {
        float(record["target_nav_loss"]): record for record in reverse_stress["loss_level_results"]
    }

    expected_counts = {
        0.05: 25,
        0.10: 10,
        0.15: 4,
        0.20: 1,
        0.25: 0,
        0.30: 0,
    }

    assert set(indexed) == set(expected_counts)

    for level, expected_count in expected_counts.items():
        assert indexed[level]["breach_episode_count"] == expected_count

    assert indexed[0.25]["historically_breached"] is False
    assert indexed[0.30]["historically_breached"] is False
    assert indexed[0.25]["observed_non_breach_is_not_a_bound"] is True
    assert indexed[0.30]["observed_non_breach_is_not_a_bound"] is True


def test_historical_allocation_reaction_is_not_universal() -> None:
    reverse_stress = load_summary()["historical_reverse_stress"]

    indexed = {
        float(record["target_nav_loss"]): record for record in reverse_stress["loss_level_results"]
    }

    five = indexed[0.05]
    ten = indexed[0.10]
    fifteen = indexed[0.15]

    assert float(five["allocation_reaction_shares"]["reduced_at_breach"]) == pytest.approx(0.52)
    assert float(ten["allocation_reaction_shares"]["reduced_at_breach"]) == pytest.approx(0.60)
    assert float(fifteen["allocation_reaction_shares"]["reduced_at_breach"]) == pytest.approx(0.25)

    assert float(fifteen["allocation_reaction_shares"]["increased_at_breach"]) == pytest.approx(
        0.50
    )


def test_counterfactual_reverse_stress_contract() -> None:
    counterfactual = load_summary()["counterfactual_reverse_stress"]

    assert counterfactual["verification_level"] == "artifact-verified"
    assert counterfactual["observations"] == 2211
    assert counterfactual["total_scenarios"] == 4908
    assert counterfactual["inference_stage_scenarios"] == 67
    assert counterfactual["retraining_and_core_scenarios"] == 132
    assert counterfactual["refinement_scenarios"] == 4709
    assert counterfactual["total_scenarios"] == 67 + 132 + 4709

    assert counterfactual["refined_failure_frontiers"] == 87
    assert counterfactual["refined_failure_families"] == 8
    assert counterfactual["dominant_vulnerability_class"] == (
        "directional_core_freshness_and_integrity"
    )
    assert counterfactual["isolated_input_corruption_failure_found"] is False
    assert counterfactual["all_phase_offsets_tested"] is True


def test_six_frozen_sources_are_reconciled() -> None:
    source_records = load_summary()["sources"]

    assert len(source_records) == 6

    for record in source_records:
        path = ROOT / str(record["path"])

        assert path.parent == SOURCE_DIR
        assert path.is_file()
        assert sha256_file(path) == str(record["sha256"])
        assert sha256_file(path) == SOURCE_SHA256[path.name]
        assert record["schema_version"] == 1


def test_markdown_structure_and_controlled_reading() -> None:
    markdown = MARKDOWN_PATH.read_text(encoding="utf-8")

    expected_headings = [
        "## Tableau 8.1",
        "## Tableau 8.2",
        "## Tableau 8.3",
        "## Tableau 8.4",
        "## Tableau 8.5",
        "## Tableau 8.6",
        "## Lecture consolidée",
        "### Limites",
    ]

    for heading in expected_headings:
        assert heading in markdown

    assert "PASS_WITH_OBSERVATION" not in markdown
    assert "4 908" in markdown
    assert "10 000 trajectoires" in markdown
    assert "54,82 % à 58,07 %" in markdown
    assert "99,99 % à 100 %" in markdown
    assert "ne constitue pas une borne de perte" in markdown
    assert "censurés à droite" in markdown
    assert "fraîcheur et l'intégrité du cœur directionnel" in markdown


def test_six_controlled_figures_are_valid_pngs() -> None:
    assert len(FIGURE_PATHS) == 6

    for path in FIGURE_PATHS:
        assert path.is_file()
        assert path.stat().st_size > 30_000

        width, height = png_dimensions(path)

        assert width >= 2_000
        assert height >= 1_000
        assert 1.60 <= width / height <= 1.90


def test_part_viii_manifest_and_checksums_reconcile() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    assert manifest["package"] == ("part_viii_risk_stress_report_support")
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


def test_no_private_path_or_trace_is_published() -> None:
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
        "daily_nostra_return",
        "daily_nostra_position",
        "private_daily_path",
    ]

    for path in controlled_text_paths:
        content = path.read_text(encoding="utf-8")

        for fragment in forbidden_fragments:
            assert fragment not in content


def test_consolidated_assessment_is_proportionate() -> None:
    assessment = load_summary()["consolidated_assessment"]

    assert assessment["status"] == "FAVORABLE_WITH_MATERIAL_OBSERVATIONS"

    findings = assessment["findings"]
    limitations = assessment["limitations"]

    assert len(findings) >= 10
    assert len(limitations) >= 7

    joined_findings = " ".join(findings)
    joined_limitations = " ".join(limitations)

    assert "faible puissance" in joined_findings
    assert "54,82 % à 58,07 %" in joined_findings
    assert "4 908 scénarios" in joined_findings
    assert "ni immédiate ni universelle" in joined_findings

    assert "non prédictives" in joined_limitations
    assert "bornes de perte" in joined_limitations
    assert "validation externe indépendante" in joined_limitations
