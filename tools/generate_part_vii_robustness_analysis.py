#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import PercentFormatter

ROOT = Path(__file__).resolve().parents[1]

SOURCE_DIR = ROOT / "artifacts" / "candidates" / "v0.3.0" / "quantitative_aggregates"

SUPPORT_DIR = ROOT / "artifacts" / "report_support" / "part_vii"
FIGURES_DIR = ROOT / "docs" / "figures"
TABLES_DIR = ROOT / "docs" / "tables"

SUMMARY_PATH = SUPPORT_DIR / "part_vii_robustness_summary.json"
MANIFEST_PATH = SUPPORT_DIR / "manifest.json"
CHECKSUMS_PATH = SUPPORT_DIR / "SHA256SUMS"

MARKDOWN_PATH = TABLES_DIR / "part_vii_robustness_results.md"

FIGURE_STATIONARITY = FIGURES_DIR / "figure_7_1_stationarity_diagnostics.png"
FIGURE_DRIFT = FIGURES_DIR / "figure_7_2_distribution_drift_rates.png"
FIGURE_REGIME_ACTIVE = FIGURES_DIR / "figure_7_3_regime_active_log_return.png"
FIGURE_REGIME_SHARPE = FIGURES_DIR / "figure_7_4_regime_sharpe_comparison.png"
FIGURE_CONFIGURATION = FIGURES_DIR / "figure_7_5_configuration_similarity.png"
FIGURE_PLACEBO = FIGURES_DIR / "figure_7_6_placebo_empirical_pvalues.png"

FIGURE_PATHS = [
    FIGURE_STATIONARITY,
    FIGURE_DRIFT,
    FIGURE_REGIME_ACTIVE,
    FIGURE_REGIME_SHARPE,
    FIGURE_CONFIGURATION,
    FIGURE_PLACEBO,
]

SOURCE_FILES = {
    "stationarity": "stationarity.json",
    "distribution_drift": "distribution_drift.json",
    "market_regimes": "market_regimes.json",
    "configuration_sensitivity": "configuration_sensitivity.json",
    "placebo_test": "placebo_test.json",
    "ablation": "ablation.json",
    "data_resilience": "data_resilience.json",
}

SOURCE_SHA256 = {
    "stationarity": ("d9477db1d63d5e4cb8d94e0efe3f2a7eb5fa4420d12297f8332f90e5165b644b"),
    "distribution_drift": ("c63529eb069230da89537131b264a69068519e26e7ce67527d0d840bdf7b3a6a"),
    "market_regimes": ("9edf14197bafae5de1375f329886d85f1f8418051b2825f36763ca5a83588b12"),
    "configuration_sensitivity": (
        "1b69daae92a5811c5657f39672661d956474d275b45e19091dea0e682a43acf0"
    ),
    "placebo_test": ("62a03185ddb83ea631fc4eb66fc835d3e54bf64d2f44a2d2898023361347f2f7"),
    "ablation": ("f4611a66e7cdad0c62cba1bb6f413083a810bb23eaf1d94b41b0a13b91145c2c"),
    "data_resilience": ("7c65c02584d68b0e5be9a8c7729651f5e3c7cf7c8670c52b348e26b817bdc74a"),
}

EXPECTED_SECTIONS = {
    "stationarity": "stationarity",
    "distribution_drift": "distribution_drift",
    "market_regimes": "market_regimes",
    "configuration_sensitivity": "configuration_sensitivity",
    "placebo_test": "placebo_test",
    "ablation": "ablation",
    "data_resilience": "data_resilience",
}

NOSTRA_COLOR = "#1f77b4"
CONDITIONAL_COLOR = "#ff7f0e"
NEUTRAL_COLOR = "#8a8a8a"
LIGHT_NEUTRAL_COLOR = "#c7c7c7"
GRID_COLOR = "#d9d9d9"
AXIS_COLOR = "#777777"
TEXT_COLOR = "#222222"

OBSERVATIONS = 2211
ANNUALIZATION = 365


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def close(
    observed: float,
    expected: float,
    tolerance: float = 1e-12,
) -> bool:
    return math.isclose(
        observed,
        expected,
        rel_tol=tolerance,
        abs_tol=tolerance,
    )


def load_sources() -> dict[str, dict[str, Any]]:
    payloads: dict[str, dict[str, Any]] = {}

    for name, filename in SOURCE_FILES.items():
        path = SOURCE_DIR / filename

        require(
            path.is_file(),
            f"Source absente : {path.relative_to(ROOT)}",
        )

        observed_sha = sha256_file(path)

        require(
            observed_sha == SOURCE_SHA256[name],
            f"Empreinte source non conforme pour {filename}: {observed_sha}",
        )

        payload = json.loads(path.read_text(encoding="utf-8"))

        require(
            payload.get("schema_version") == 1,
            f"Version de schéma non conforme pour {filename}.",
        )
        require(
            payload.get("section") == EXPECTED_SECTIONS[name],
            f"Section non conforme pour {filename}.",
        )
        require(
            isinstance(payload.get("data"), dict),
            f"Bloc data absent pour {filename}.",
        )

        payloads[name] = payload

    return payloads


def validate_quantile_order(
    quantiles: dict[str, Any],
    keys: list[str],
    message: str,
) -> None:
    values = [float(quantiles[key]) for key in keys]

    require(
        values == sorted(values),
        message,
    )


def validate_sources(payloads: dict[str, dict[str, Any]]) -> None:
    stationarity = payloads["stationarity"]["data"]
    drift = payloads["distribution_drift"]["data"]
    regimes = payloads["market_regimes"]["data"]
    configuration = payloads["configuration_sensitivity"]["data"]
    placebo = payloads["placebo_test"]["data"]
    ablation = payloads["ablation"]["data"]
    resilience = payloads["data_resilience"]["data"]

    require(
        stationarity["series_tested"] == 8,
        "Le contrôle de stationnarité doit porter sur huit séries.",
    )
    require(
        stationarity["adf_reject_unit_root_5pct"] == 2,
        "Nombre de rejets ADF non conforme.",
    )
    require(
        stationarity["kpss_reject_stationarity_5pct"] == 7,
        "Nombre de rejets KPSS non conforme.",
    )
    require(
        stationarity["consistent_stationarity_5pct"] == 1,
        "Nombre de diagnostics concordants de stationnarité non conforme.",
    )
    require(
        stationarity["conflicting_tests_5pct"] == 1,
        "Nombre de diagnostics contradictoires non conforme.",
    )
    require(
        stationarity["cusum_break_candidate_count"] == 8,
        "Nombre de candidats de rupture CUSUM non conforme.",
    )

    validate_quantile_order(
        stationarity["adf_pvalue_quantiles"],
        ["q00", "q05", "q25", "q50", "q75", "q95", "q100"],
        "Ordre des quantiles ADF non conforme.",
    )
    validate_quantile_order(
        stationarity["kpss_pvalue_quantiles"],
        ["q00", "q05", "q25", "q50", "q75", "q95", "q100"],
        "Ordre des quantiles KPSS non conforme.",
    )

    rolling = drift["rolling_windows"]
    train_test = drift["train_test_folds"]

    for name, block in [
        ("fenêtres glissantes", rolling),
        ("plis apprentissage-évaluation", train_test),
    ]:
        require(
            block["anonymous_series_count"] == 8,
            f"Nombre de séries anonymisées non conforme pour {name}.",
        )
        require(
            block["comparisons"] == 136,
            f"Nombre de comparaisons non conforme pour {name}.",
        )

    require(
        rolling["ks_reject_equal_distribution_5pct"] == 134,
        "Nombre de rejets KS des fenêtres glissantes non conforme.",
    )
    require(
        rolling["psi_at_least_0_25"] == 125,
        "Nombre de PSI élevés des fenêtres glissantes non conforme.",
    )
    require(
        rolling["absolute_standardized_shift_at_least_1_00"] == 80,
        "Nombre de décalages standardisés des fenêtres glissantes non conforme.",
    )

    require(
        train_test["ks_reject_equal_distribution_5pct"] == 131,
        "Nombre de rejets KS des plis non conforme.",
    )
    require(
        train_test["psi_at_least_0_25"] == 130,
        "Nombre de PSI élevés des plis non conforme.",
    )
    require(
        train_test["absolute_standardized_shift_at_least_1_00"] == 37,
        "Nombre de décalages standardisés des plis non conforme.",
    )

    records = regimes["records"]

    require(
        regimes["regime_count"] == 10,
        "Nombre de régimes non conforme.",
    )
    require(
        regimes["aggregate_rows"] == 10,
        "Nombre de lignes agrégées de régime non conforme.",
    )
    require(
        isinstance(records, list) and len(records) == 10,
        "Les analyses de régime doivent contenir dix enregistrements.",
    )
    require(
        len({str(record["regime"]) for record in records}) == 10,
        "Les identifiants de régime doivent être uniques.",
    )
    require(
        all(
            float(record["nostra_annualized_volatility"])
            < float(record["btc_annualized_volatility"])
            for record in records
        ),
        "Nostra doit présenter une volatilité inférieure dans les dix régimes.",
    )
    require(
        all(
            float(record["nostra_conditional_max_drawdown"])
            > float(record["btc_conditional_max_drawdown"])
            for record in records
        ),
        "Nostra doit présenter une perte maximale moins profonde dans les dix régimes.",
    )
    require(
        all(float(record["nostra_sharpe"]) > float(record["btc_sharpe"]) for record in records),
        "Nostra doit présenter un Sharpe supérieur dans les dix régimes.",
    )

    positive_active = sum(float(record["annualized_active_log_return"]) > 0.0 for record in records)
    negative_active = sum(float(record["annualized_active_log_return"]) < 0.0 for record in records)

    require(
        positive_active == 8 and negative_active == 2,
        "La surperformance de régime doit être positive huit fois et négative deux fois.",
    )

    require(
        configuration["configurations_executed"] == 34,
        "Nombre de configurations exécutées non conforme.",
    )
    require(
        configuration["configurations_failed"] == 0,
        "Aucune configuration ne doit avoir échoué.",
    )
    require(
        configuration["decision_status"] == "descriptive_evidence_only",
        "Statut méthodologique de sensibilité non conforme.",
    )
    require(
        configuration["exact_configuration_values_disclosed"] is False,
        "Les valeurs exactes des configurations doivent rester non publiées.",
    )

    similarities = configuration["similarity_quantiles"]

    for metric in [
        "direction_agreement",
        "pearson_similarity",
        "spearman_similarity",
        "prediction_path_mae",
        "prediction_path_rmse",
    ]:
        validate_quantile_order(
            similarities[metric],
            ["q00", "q05", "q25", "q50", "q75", "q95", "q100"],
            f"Ordre des quantiles non conforme pour {metric}.",
        )

    require(
        placebo["permutations"] == 500,
        "Nombre de permutations placebo non conforme.",
    )
    require(
        float(placebo["cost_bps"]) == 25.0,
        "Coût du test placebo non conforme.",
    )
    require(
        placebo["delay_days"] == 0,
        "Délai du test placebo non conforme.",
    )

    expected_placebo_pvalues = {
        "cagr": 0.01197605,
        "final_equity": 0.01197605,
        "sharpe": 0.03792415,
        "calmar": 0.37125749,
    }

    for metric, expected in expected_placebo_pvalues.items():
        observed = float(placebo["metrics"][metric]["upper_tail_empirical_pvalue"])

        require(
            close(observed, expected, tolerance=1e-8),
            f"Valeur p placebo non conforme pour {metric}.",
        )

    require(
        ablation["anonymous_ablation_count"] == 15,
        "Nombre d'ablations anonymisées non conforme.",
    )
    require(
        ablation["paired_bootstrap_comparisons"] == 14,
        "Nombre de comparaisons appariées d'ablation non conforme.",
    )
    require(
        ablation["comparisons_with_interval_including_zero"] == 14,
        "Les quatorze intervalles d'ablation doivent inclure zéro.",
    )
    require(
        ablation["comparisons_with_positive_95pct_interval"] == 0,
        "Aucun intervalle d'ablation ne doit être entièrement positif.",
    )
    require(
        ablation["comparisons_with_negative_95pct_interval"] == 0,
        "Aucun intervalle d'ablation ne doit être entièrement négatif.",
    )
    require(
        ablation["identities_disclosed"] is False,
        "Les identités des ablations doivent rester non publiées.",
    )
    require(
        ablation["decision_status"] == "descriptive_evidence_only",
        "Statut méthodologique des ablations non conforme.",
    )

    require(
        resilience["scenario_count_excluding_baseline"] == 23,
        "Nombre de scénarios de résilience non conforme.",
    )
    require(
        resilience["scenario_family_count"] == 3,
        "Nombre de familles de scénarios non conforme.",
    )
    require(
        resilience["bootstrap_runs"] == 300,
        "Nombre de répétitions de résilience non conforme.",
    )
    require(
        resilience["bootstrap_block_length"] == 30,
        "Longueur de bloc de résilience non conforme.",
    )
    require(
        resilience["cross_provider_comparison_completed"] is False,
        "La comparaison croisée entre fournisseurs ne doit pas être déclarée achevée.",
    )
    require(
        resilience["decision_status"] == "descriptive_evidence_only",
        "Statut méthodologique de résilience non conforme.",
    )


def format_number(value: float, decimals: int = 3) -> str:
    return f"{value:.{decimals}f}".replace(".", ",")


def format_percent(value: float, decimals: int = 2) -> str:
    return f"{value * 100:.{decimals}f}".replace(".", ",") + " %"


def format_integer(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def source_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    for name, filename in SOURCE_FILES.items():
        path = SOURCE_DIR / filename

        records.append(
            {
                "name": name,
                "path": path.relative_to(ROOT).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )

    return records


def build_summary(
    payloads: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    stationarity = payloads["stationarity"]["data"]
    drift = payloads["distribution_drift"]["data"]
    regimes = payloads["market_regimes"]["data"]
    configuration = payloads["configuration_sensitivity"]["data"]
    placebo = payloads["placebo_test"]["data"]
    ablation = payloads["ablation"]["data"]
    resilience = payloads["data_resilience"]["data"]

    regime_records = regimes["records"]

    consolidated_reading = {
        "stationarity_can_be_assumed": False,
        "pervasive_distribution_drift_detected": True,
        "regime_count": 10,
        "regimes_with_positive_active_log_return": sum(
            float(record["annualized_active_log_return"]) > 0.0 for record in regime_records
        ),
        "regimes_with_lower_nostra_volatility": sum(
            float(record["nostra_annualized_volatility"])
            < float(record["btc_annualized_volatility"])
            for record in regime_records
        ),
        "regimes_with_less_severe_nostra_drawdown": sum(
            float(record["nostra_conditional_max_drawdown"])
            > float(record["btc_conditional_max_drawdown"])
            for record in regime_records
        ),
        "regimes_with_higher_nostra_sharpe": sum(
            float(record["nostra_sharpe"]) > float(record["btc_sharpe"])
            for record in regime_records
        ),
        "configuration_count": int(configuration["configurations_executed"]),
        "configuration_failures": int(configuration["configurations_failed"]),
        "placebo_metrics_below_5_percent": [
            metric
            for metric in ["cagr", "final_equity", "sharpe", "calmar"]
            if float(placebo["metrics"][metric]["upper_tail_empirical_pvalue"]) < 0.05
        ],
        "placebo_metrics_not_below_5_percent": [
            metric
            for metric in ["cagr", "final_equity", "sharpe", "calmar"]
            if float(placebo["metrics"][metric]["upper_tail_empirical_pvalue"]) >= 0.05
        ],
        "ablation_intervals_including_zero": int(
            ablation["comparisons_with_interval_including_zero"]
        ),
        "ablation_paired_comparisons": int(ablation["paired_bootstrap_comparisons"]),
        "data_resilience_scenarios": int(resilience["scenario_count_excluding_baseline"]),
        "cross_provider_comparison_completed": bool(
            resilience["cross_provider_comparison_completed"]
        ),
        "reading_status": "favorable_with_material_observations",
    }

    return {
        "schema_version": 1,
        "package": "part_vii_robustness_report_support",
        "model": "Nostra AI V5.246",
        "source_release": "v0.3.0",
        "period": {
            "start": "2020-05-14",
            "end": "2026-06-02",
            "observations": OBSERVATIONS,
            "annualization": ANNUALIZATION,
        },
        "stationarity": stationarity,
        "distribution_drift": drift,
        "market_regimes": regimes,
        "configuration_sensitivity": configuration,
        "placebo_test": placebo,
        "ablation": ablation,
        "data_resilience": resilience,
        "consolidated_reading": consolidated_reading,
        "source_files": source_records(),
        "mandatory_limitations": [
            (
                "Les séries, régimes, configurations et ablations sont publiés sous "
                "une forme anonymisée."
            ),
            (
                "Les contrôles de configuration, d'ablation et de résilience des "
                "données constituent des preuves descriptives."
            ),
            (
                "La non-stationnarité et la dérive observées empêchent de supposer "
                "une distribution stable sur l'ensemble de la période."
            ),
            (
                "Aucune comparaison croisée entre plusieurs fournisseurs de données "
                "n'est déclarée achevée."
            ),
            (
                "Les résultats sont rétrospectifs et ne démontrent ni invariance "
                "future ni relation causale."
            ),
        ],
    }


def write_json(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def regime_sort_key(record: dict[str, Any]) -> int:
    return int(str(record["regime"]).split("_")[-1])


def write_markdown(summary: dict[str, Any]) -> None:
    stationarity = summary["stationarity"]
    drift = summary["distribution_drift"]
    regimes = sorted(
        summary["market_regimes"]["records"],
        key=regime_sort_key,
    )
    configuration = summary["configuration_sensitivity"]
    placebo = summary["placebo_test"]
    ablation = summary["ablation"]
    resilience = summary["data_resilience"]
    reading = summary["consolidated_reading"]

    rolling = drift["rolling_windows"]
    train_test = drift["train_test_folds"]

    rolling_ks_rate = rolling["ks_reject_equal_distribution_5pct"] / rolling["comparisons"]
    train_test_ks_rate = train_test["ks_reject_equal_distribution_5pct"] / train_test["comparisons"]
    rolling_shift_rate = (
        rolling["absolute_standardized_shift_at_least_1_00"] / rolling["comparisons"]
    )
    train_test_shift_rate = (
        train_test["absolute_standardized_shift_at_least_1_00"] / train_test["comparisons"]
    )

    lines = [
        "# Partie VII - Non-stationnarité et robustesse",
        "",
        "## Tableau 7.1 - Diagnostics de stationnarité et de rupture",
        "",
        "| Indicateur | Résultat |",
        "|---|---:|",
        f"| Séries anonymisées testées | {stationarity['series_tested']} |",
        (
            "| Rejets ADF de la racine unitaire au seuil de 5 % | "
            f"{stationarity['adf_reject_unit_root_5pct']} |"
        ),
        (
            "| Rejets KPSS de la stationnarité au seuil de 5 % | "
            f"{stationarity['kpss_reject_stationarity_5pct']} |"
        ),
        (
            "| Diagnostics concordants de stationnarité | "
            f"{stationarity['consistent_stationarity_5pct']} |"
        ),
        (f"| Diagnostics contradictoires | {stationarity['conflicting_tests_5pct']} |"),
        (f"| Candidats de rupture CUSUM | {stationarity['cusum_break_candidate_count']} |"),
        "",
        "## Tableau 7.2 - Dérive des distributions",
        "",
        "| Indicateur | Fenêtres glissantes | Plis apprentissage-évaluation |",
        "|---|---:|---:|",
        (f"| Comparaisons | {rolling['comparisons']} | {train_test['comparisons']} |"),
        (
            "| Rejets KS de l'égalité des distributions | "
            f"{rolling['ks_reject_equal_distribution_5pct']} "
            f"({format_percent(rolling_ks_rate)}) | "
            f"{train_test['ks_reject_equal_distribution_5pct']} "
            f"({format_percent(train_test_ks_rate)}) |"
        ),
        (
            "| PSI supérieur ou égal à 0,25 | "
            f"{rolling['psi_at_least_0_25']} "
            f"({format_percent(rolling['psi_at_least_0_25'] / rolling['comparisons'])}) | "
            f"{train_test['psi_at_least_0_25']} "
            f"({format_percent(train_test['psi_at_least_0_25'] / train_test['comparisons'])}) |"
        ),
        (
            "| Décalage standardisé absolu supérieur ou égal à 1 | "
            f"{rolling['absolute_standardized_shift_at_least_1_00']} "
            f"({format_percent(rolling_shift_rate)}) | "
            f"{train_test['absolute_standardized_shift_at_least_1_00']} "
            f"({format_percent(train_test_shift_rate)}) |"
        ),
        "",
        "## Tableau 7.3 - Résultats par régime anonymisé",
        "",
        (
            "| Régime | Observations | Surperformance logarithmique annualisée | "
            "Sharpe Nostra | Sharpe bitcoin | Volatilité Nostra | "
            "Volatilité bitcoin | Perte maximale Nostra | Perte maximale bitcoin |"
        ),
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for record in regimes:
        lines.append(
            "| "
            f"{record['regime']} | "
            f"{format_integer(int(record['observations']))} | "
            f"{format_percent(float(record['annualized_active_log_return']))} | "
            f"{format_number(float(record['nostra_sharpe']))} | "
            f"{format_number(float(record['btc_sharpe']))} | "
            f"{format_percent(float(record['nostra_annualized_volatility']))} | "
            f"{format_percent(float(record['btc_annualized_volatility']))} | "
            f"{format_percent(float(record['nostra_conditional_max_drawdown']))} | "
            f"{format_percent(float(record['btc_conditional_max_drawdown']))} |"
        )

    similarity = configuration["similarity_quantiles"]

    lines.extend(
        [
            "",
            "## Tableau 7.4 - Sensibilité anonymisée de configuration",
            "",
            "| Mesure | Minimum | Quantile 5 % | Médiane | Quantile 95 % | Maximum |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )

    configuration_rows = [
        ("Accord directionnel", "direction_agreement", True),
        ("Similarité de Pearson", "pearson_similarity", True),
        ("Similarité de Spearman", "spearman_similarity", True),
        ("Erreur absolue moyenne de trajectoire", "prediction_path_mae", False),
        ("Erreur quadratique moyenne de trajectoire", "prediction_path_rmse", False),
    ]

    for label, key, is_percentage in configuration_rows:
        quantiles = similarity[key]
        formatter = format_percent if is_percentage else format_number

        lines.append(
            f"| {label} | "
            f"{formatter(float(quantiles['q00']))} | "
            f"{formatter(float(quantiles['q05']))} | "
            f"{formatter(float(quantiles['q50']))} | "
            f"{formatter(float(quantiles['q95']))} | "
            f"{formatter(float(quantiles['q100']))} |"
        )

    lines.extend(
        [
            "",
            (
                f"Configurations exécutées : "
                f"{configuration['configurations_executed']}. "
                f"Configurations en échec : {configuration['configurations_failed']}."
            ),
            "",
            "## Tableau 7.5 - Placebos et permutations",
            "",
            (
                "| Métrique | Valeur observée | Médiane des permutations | "
                "Valeur p empirique | Lecture |"
            ),
            "|---|---:|---:|---:|---|",
        ]
    )

    placebo_labels = {
        "cagr": "CAGR",
        "final_equity": "Capital final",
        "sharpe": "Ratio de Sharpe",
        "calmar": "Ratio de Calmar",
    }

    for metric in ["cagr", "final_equity", "sharpe", "calmar"]:
        record = placebo["metrics"][metric]
        observed = float(record["observed"])
        median = float(record["permutation_quantiles"]["q50"])
        p_value = float(record["upper_tail_empirical_pvalue"])

        if metric == "cagr":
            observed_text = format_percent(observed)
            median_text = format_percent(median)
        else:
            observed_text = format_number(observed, 4)
            median_text = format_number(median, 4)

        reading_text = "Inférieur à 5 %" if p_value < 0.05 else "Non inférieur à 5 %"

        lines.append(
            f"| {placebo_labels[metric]} | "
            f"{observed_text} | "
            f"{median_text} | "
            f"{format_percent(p_value)} | "
            f"{reading_text} |"
        )

    lines.extend(
        [
            "",
            "## Tableau 7.6 - Ablations anonymisées",
            "",
            "| Indicateur | Résultat |",
            "|---|---:|",
            (f"| Ablations anonymisées recensées | {ablation['anonymous_ablation_count']} |"),
            (
                "| Comparaisons appariées soumises au bootstrap | "
                f"{ablation['paired_bootstrap_comparisons']} |"
            ),
            (
                "| Intervalles à 95 % incluant zéro | "
                f"{ablation['comparisons_with_interval_including_zero']} |"
            ),
            (
                "| Intervalles entièrement positifs | "
                f"{ablation['comparisons_with_positive_95pct_interval']} |"
            ),
            (
                "| Intervalles entièrement négatifs | "
                f"{ablation['comparisons_with_negative_95pct_interval']} |"
            ),
            "",
            "### Variations économiques des ablations",
            "",
            "| Métrique | Minimum | Médiane | Maximum |",
            "|---|---:|---:|---:|",
        ]
    )

    ablation_labels = {
        "cagr_delta": ("Écart de CAGR", True),
        "final_equity_delta": ("Écart de capital final", False),
        "maximum_drawdown_delta": ("Écart de perte maximale", True),
        "sharpe_delta": ("Écart de Sharpe", False),
        "sortino_delta": ("Écart de Sortino", False),
    }

    for key, (label, is_percentage) in ablation_labels.items():
        quantiles = ablation["economic_delta_quantiles"][key]
        formatter = format_percent if is_percentage else format_number

        lines.append(
            f"| {label} | "
            f"{formatter(float(quantiles['q00']), 4)} | "
            f"{formatter(float(quantiles['q50']), 4)} | "
            f"{formatter(float(quantiles['q100']), 4)} |"
        )

    lines.extend(
        [
            "",
            "## Tableau 7.7 - Résilience des données",
            "",
            "| Paramètre | Résultat |",
            "|---|---:|",
            (f"| Scénarios hors référence | {resilience['scenario_count_excluding_baseline']} |"),
            (f"| Familles de scénarios | {resilience['scenario_family_count']} |"),
            (f"| Répétitions de rééchantillonnage | {resilience['bootstrap_runs']} |"),
            (f"| Longueur des blocs | {resilience['bootstrap_block_length']} observations |"),
            ("| Comparaison croisée entre fournisseurs achevée | Non |"),
            "",
            "### Variations des métriques sous perturbation des données",
            "",
            "| Métrique | Minimum | Médiane | Maximum |",
            "|---|---:|---:|---:|",
        ]
    )

    resilience_labels = {
        "annualized_volatility_delta": ("Écart de volatilité annualisée", True),
        "cagr_delta": ("Écart de CAGR", True),
        "final_equity_delta": ("Écart de capital final", False),
        "maximum_drawdown_delta": ("Écart de perte maximale", True),
        "prediction_coverage_delta": ("Écart de couverture des prédictions", False),
        "sharpe_delta": ("Écart de Sharpe", False),
    }

    for key, (label, is_percentage) in resilience_labels.items():
        quantiles = resilience["metric_delta_quantiles"][key]
        formatter = format_percent if is_percentage else format_number

        lines.append(
            f"| {label} | "
            f"{formatter(float(quantiles['q00']), 4)} | "
            f"{formatter(float(quantiles['q50']), 4)} | "
            f"{formatter(float(quantiles['q100']), 4)} |"
        )

    lines.extend(
        [
            "",
            "## Tableau 7.8 - Conclusion consolidée de robustesse",
            "",
            "| Dimension | Résultat contrôlé | Lecture autorisée |",
            "|---|---|---|",
            (
                "| Stationnarité | "
                "Une seule série sur huit présente un diagnostic concordant de stationnarité ; "
                "sept rejets KPSS et huit candidats CUSUM | "
                "La stabilité statistique des séries ne peut pas être supposée |"
            ),
            (
                "| Dérive des distributions | "
                "134 rejets KS sur 136 entre fenêtres et 131 sur 136 entre plis | "
                "La dérive est généralisée dans les comparaisons publiées |"
            ),
            (
                "| Régimes de marché | "
                f"{reading['regimes_with_positive_active_log_return']} régimes sur 10 "
                "avec surperformance logarithmique positive ; réduction du risque dans "
                "les dix régimes | "
                "La réduction du risque est plus uniforme que la surperformance |"
            ),
            (
                "| Sensibilité de configuration | "
                "34 configurations exécutées, aucune défaillance, similarités médianes élevées | "
                "La trajectoire est généralement stable sans être parfaitement invariante |"
            ),
            (
                "| Placebos | "
                "CAGR, capital final et Sharpe sous le seuil de 5 % ; Calmar au-dessus | "
                "Résultat favorable pour trois métriques, non concluant pour le Calmar |"
            ),
            (
                "| Ablations | "
                "14 intervalles appariés sur 14 incluent zéro | "
                "Aucun composant anonymisé n'est isolément décisif dans la preuve publiée |"
            ),
            (
                "| Résilience des données | "
                "23 scénarios hors référence ; médianes des écarts généralement proches de zéro | "
                "Résilience interne descriptive, sans validation inter-fournisseurs |"
            ),
            "",
            "## Limites obligatoires",
            "",
        ]
    )

    for limitation in summary["mandatory_limitations"]:
        lines.append(f"- {limitation}")

    lines.extend(
        [
            "",
            (
                "Conclusion contrôlée : les résultats soutiennent une robustesse "
                "historique favorable malgré une non-stationnarité et une dérive "
                "matérielles. Cette conclusion ne démontre ni stabilité future, "
                "ni invariance du modèle, ni absence de risque de régime."
            ),
            "",
        ]
    )

    MARKDOWN_PATH.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def configure_plotting() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 12,
            "axes.titlesize": 18,
            "axes.labelsize": 13,
            "xtick.labelsize": 11,
            "ytick.labelsize": 11,
            "legend.fontsize": 11,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": AXIS_COLOR,
            "axes.labelcolor": TEXT_COLOR,
            "xtick.color": TEXT_COLOR,
            "ytick.color": TEXT_COLOR,
            "text.color": TEXT_COLOR,
        }
    )


def style_axis(
    axis: plt.Axes,
    *,
    x_grid: bool = False,
    y_grid: bool = True,
) -> None:
    axis.set_axisbelow(True)

    if x_grid:
        axis.grid(
            axis="x",
            color=GRID_COLOR,
            linewidth=0.8,
            alpha=0.8,
        )

    if y_grid:
        axis.grid(
            axis="y",
            color=GRID_COLOR,
            linewidth=0.8,
            alpha=0.8,
        )

    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)


def save_figure(
    figure: plt.Figure,
    path: Path,
) -> None:
    figure.tight_layout()
    figure.savefig(
        path,
        dpi=220,
        facecolor="white",
        metadata={"Software": "HilmarCorp"},
    )
    plt.close(figure)


def plot_stationarity(stationarity: dict[str, Any]) -> None:
    labels = [
        "Rejets ADF\nde racine unitaire",
        "Rejets KPSS\nde stationnarité",
        "Stationnarité\nconcordante",
        "Tests\ncontradictoires",
        "Candidats\nde rupture CUSUM",
    ]
    values = [
        int(stationarity["adf_reject_unit_root_5pct"]),
        int(stationarity["kpss_reject_stationarity_5pct"]),
        int(stationarity["consistent_stationarity_5pct"]),
        int(stationarity["conflicting_tests_5pct"]),
        int(stationarity["cusum_break_candidate_count"]),
    ]
    colors = [
        NOSTRA_COLOR,
        CONDITIONAL_COLOR,
        NOSTRA_COLOR,
        CONDITIONAL_COLOR,
        NEUTRAL_COLOR,
    ]

    figure, axis = plt.subplots(figsize=(16, 9))
    bars = axis.bar(
        labels,
        values,
        color=colors,
        width=0.68,
    )

    axis.set_title(
        "Diagnostics agrégés de stationnarité et de rupture",
        pad=20,
    )
    axis.set_ylabel("Nombre de séries ou de candidats")
    axis.set_ylim(0, 9)
    axis.set_yticks(range(0, 10))
    axis.axhline(
        int(stationarity["series_tested"]),
        color=LIGHT_NEUTRAL_COLOR,
        linestyle="--",
        linewidth=1.4,
        label="Huit séries anonymisées testées",
    )

    axis.bar_label(
        bars,
        labels=[str(value) for value in values],
        padding=6,
        fontsize=12,
    )

    style_axis(axis)
    axis.legend(loc="upper left", frameon=False)

    save_figure(figure, FIGURE_STATIONARITY)


def plot_distribution_drift(drift: dict[str, Any]) -> None:
    rolling = drift["rolling_windows"]
    train_test = drift["train_test_folds"]

    labels = [
        "Rejet KS\nà 5 %",
        "PSI ≥ 0,25",
        "Décalage standardisé\nabsolu ≥ 1",
    ]

    rolling_values = [
        rolling["ks_reject_equal_distribution_5pct"] / rolling["comparisons"],
        rolling["psi_at_least_0_25"] / rolling["comparisons"],
        (rolling["absolute_standardized_shift_at_least_1_00"] / rolling["comparisons"]),
    ]
    train_values = [
        train_test["ks_reject_equal_distribution_5pct"] / train_test["comparisons"],
        train_test["psi_at_least_0_25"] / train_test["comparisons"],
        (train_test["absolute_standardized_shift_at_least_1_00"] / train_test["comparisons"]),
    ]

    positions = np.arange(len(labels))
    width = 0.34

    figure, axis = plt.subplots(figsize=(16, 9))

    rolling_bars = axis.bar(
        positions - width / 2,
        rolling_values,
        width,
        label="Fenêtres glissantes",
        color=NOSTRA_COLOR,
    )
    train_bars = axis.bar(
        positions + width / 2,
        train_values,
        width,
        label="Plis apprentissage-évaluation",
        color=CONDITIONAL_COLOR,
    )

    axis.set_title(
        "Fréquence des diagnostics de dérive des distributions",
        pad=20,
    )
    axis.set_ylabel("Part des 136 comparaisons")
    axis.set_xticks(positions)
    axis.set_xticklabels(labels)
    axis.set_ylim(0, 1.08)
    axis.yaxis.set_major_formatter(PercentFormatter(1.0))

    axis.bar_label(
        rolling_bars,
        labels=[format_percent(value, 1) for value in rolling_values],
        padding=5,
        fontsize=11,
    )
    axis.bar_label(
        train_bars,
        labels=[format_percent(value, 1) for value in train_values],
        padding=5,
        fontsize=11,
    )

    style_axis(axis)
    axis.legend(loc="upper right", frameon=False)

    save_figure(figure, FIGURE_DRIFT)


def plot_regime_active_return(regimes: dict[str, Any]) -> None:
    records = sorted(
        regimes["records"],
        key=regime_sort_key,
    )

    labels = [str(record["regime"]) for record in records]
    values = [float(record["annualized_active_log_return"]) for record in records]
    colors = [NOSTRA_COLOR if value > 0.0 else CONDITIONAL_COLOR for value in values]

    positions = np.arange(len(labels))

    figure, axis = plt.subplots(figsize=(16, 9))

    bars = axis.barh(
        positions,
        values,
        color=colors,
        height=0.66,
    )

    axis.set_title(
        "Surperformance logarithmique annualisée par régime anonymisé",
        pad=20,
    )
    axis.set_xlabel("Nostra AI moins bitcoin passif")
    axis.set_yticks(positions)
    axis.set_yticklabels(labels)
    axis.invert_yaxis()
    axis.xaxis.set_major_formatter(PercentFormatter(1.0))
    axis.axvline(
        0.0,
        color=AXIS_COLOR,
        linewidth=1.2,
    )

    axis.bar_label(
        bars,
        labels=[format_percent(value, 1) for value in values],
        padding=5,
        fontsize=11,
    )

    style_axis(
        axis,
        x_grid=True,
        y_grid=False,
    )

    save_figure(figure, FIGURE_REGIME_ACTIVE)


def plot_regime_sharpe(regimes: dict[str, Any]) -> None:
    records = sorted(
        regimes["records"],
        key=regime_sort_key,
    )

    labels = [str(record["regime"]) for record in records]
    nostra_values = [float(record["nostra_sharpe"]) for record in records]
    btc_values = [float(record["btc_sharpe"]) for record in records]

    positions = np.arange(len(labels))
    width = 0.36

    figure, axis = plt.subplots(figsize=(16, 9))

    nostra_bars = axis.bar(
        positions - width / 2,
        nostra_values,
        width,
        label="Nostra AI",
        color=NOSTRA_COLOR,
    )
    btc_bars = axis.bar(
        positions + width / 2,
        btc_values,
        width,
        label="Bitcoin passif",
        color=CONDITIONAL_COLOR,
    )

    axis.set_title(
        "Ratios de Sharpe par régime anonymisé",
        pad=20,
    )
    axis.set_ylabel("Ratio de Sharpe annualisé")
    axis.set_xticks(positions)
    axis.set_xticklabels(labels, rotation=30, ha="right")
    axis.axhline(
        0.0,
        color=AXIS_COLOR,
        linewidth=1.0,
    )

    axis.bar_label(
        nostra_bars,
        labels=[format_number(value, 2) for value in nostra_values],
        padding=4,
        fontsize=9,
        rotation=90,
    )
    axis.bar_label(
        btc_bars,
        labels=[format_number(value, 2) for value in btc_values],
        padding=4,
        fontsize=9,
        rotation=90,
    )

    minimum = min(min(nostra_values), min(btc_values))
    maximum = max(max(nostra_values), max(btc_values))
    axis.set_ylim(min(-0.4, minimum - 0.1), maximum + 0.45)

    style_axis(axis)
    axis.legend(loc="upper left", frameon=False)

    save_figure(figure, FIGURE_REGIME_SHARPE)


def plot_configuration_similarity(configuration: dict[str, Any]) -> None:
    similarities = configuration["similarity_quantiles"]

    labels = [
        "Accord directionnel",
        "Pearson",
        "Spearman",
    ]
    keys = [
        "direction_agreement",
        "pearson_similarity",
        "spearman_similarity",
    ]

    medians = [float(similarities[key]["q50"]) for key in keys]
    lower_errors = [
        median - float(similarities[key]["q05"]) for key, median in zip(keys, medians, strict=True)
    ]
    upper_errors = [
        float(similarities[key]["q95"]) - median for key, median in zip(keys, medians, strict=True)
    ]

    positions = np.arange(len(labels))

    figure, axis = plt.subplots(figsize=(16, 9))

    axis.errorbar(
        positions,
        medians,
        yerr=[lower_errors, upper_errors],
        fmt="o",
        markersize=12,
        linewidth=2.2,
        capsize=10,
        color=NOSTRA_COLOR,
        ecolor=NEUTRAL_COLOR,
    )

    axis.set_title(
        "Similarité des trajectoires sous variations anonymisées de configuration",
        pad=20,
    )
    axis.set_ylabel("Similarité ou taux d'accord")
    axis.set_xticks(positions)
    axis.set_xticklabels(labels)
    axis.set_ylim(0.65, 1.02)
    axis.yaxis.set_major_formatter(PercentFormatter(1.0))

    for position, median in zip(positions, medians, strict=True):
        axis.annotate(
            format_percent(median, 1),
            (position, median),
            xytext=(0, 14),
            textcoords="offset points",
            ha="center",
            fontsize=12,
        )

    axis.text(
        0.01,
        0.02,
        (
            "Points : médianes. Barres : quantiles 5 % à 95 %. "
            "34 configurations exécutées, aucune défaillance."
        ),
        transform=axis.transAxes,
        fontsize=10,
        color=NEUTRAL_COLOR,
    )

    style_axis(axis)

    save_figure(figure, FIGURE_CONFIGURATION)


def plot_placebo(placebo: dict[str, Any]) -> None:
    metrics = ["cagr", "final_equity", "sharpe", "calmar"]
    labels = [
        "CAGR",
        "Capital final",
        "Sharpe",
        "Calmar",
    ]
    values = [
        float(placebo["metrics"][metric]["upper_tail_empirical_pvalue"]) for metric in metrics
    ]
    colors = [NOSTRA_COLOR if value < 0.05 else CONDITIONAL_COLOR for value in values]

    figure, axis = plt.subplots(figsize=(16, 9))

    bars = axis.bar(
        labels,
        values,
        color=colors,
        width=0.65,
    )

    axis.set_title(
        "Valeurs p empiriques des tests placebo par permutation",
        pad=20,
    )
    axis.set_ylabel("Valeur p empirique")
    axis.set_ylim(0, max(values) * 1.22)
    axis.yaxis.set_major_formatter(PercentFormatter(1.0))
    axis.axhline(
        0.05,
        color=AXIS_COLOR,
        linestyle="--",
        linewidth=1.5,
        label="Seuil indicatif de 5 %",
    )

    axis.bar_label(
        bars,
        labels=[format_percent(value, 2) for value in values],
        padding=6,
        fontsize=12,
    )

    style_axis(axis)
    axis.legend(loc="upper left", frameon=False)

    save_figure(figure, FIGURE_PLACEBO)


def generate_figures(summary: dict[str, Any]) -> None:
    configure_plotting()

    plot_stationarity(summary["stationarity"])
    plot_distribution_drift(summary["distribution_drift"])
    plot_regime_active_return(summary["market_regimes"])
    plot_regime_sharpe(summary["market_regimes"])
    plot_configuration_similarity(summary["configuration_sensitivity"])
    plot_placebo(summary["placebo_test"])


def controlled_output_paths() -> list[Path]:
    return [
        SUMMARY_PATH,
        MARKDOWN_PATH,
        Path(__file__).resolve(),
        *FIGURE_PATHS,
    ]


def write_manifest_and_checksums() -> None:
    records: list[dict[str, Any]] = []

    for path in sorted(
        controlled_output_paths(),
        key=lambda item: item.relative_to(ROOT).as_posix(),
    ):
        records.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )

    manifest = {
        "schema_version": 1,
        "package": "part_vii_robustness_report_support",
        "model": "Nostra AI V5.246",
        "source_release": "v0.3.0",
        "period": {
            "start": "2020-05-14",
            "end": "2026-06-02",
            "observations": OBSERVATIONS,
            "annualization": ANNUALIZATION,
        },
        "status": (
            "Paquet institutionnel de support de la Partie VII consacré à la "
            "non-stationnarité, à la dérive et à la robustesse."
        ),
        "files": records,
    }

    write_json(
        MANIFEST_PATH,
        manifest,
    )

    checksum_lines = [f"{record['sha256']}  {record['path']}" for record in records]

    CHECKSUMS_PATH.write_text(
        "\n".join(checksum_lines) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    SUPPORT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    payloads = load_sources()
    validate_sources(payloads)

    summary = build_summary(payloads)

    write_json(
        SUMMARY_PATH,
        summary,
    )
    write_markdown(summary)
    generate_figures(summary)
    write_manifest_and_checksums()

    print("PASS_PART_VII_ROBUSTNESS_SUPPORT_READY")
    print(f"Résumé : {SUMMARY_PATH.relative_to(ROOT)}")
    print(f"Tableaux : {MARKDOWN_PATH.relative_to(ROOT)}")
    print(f"Figures : {len(FIGURE_PATHS)}")
    print(f"Sources gelées réconciliées : {len(SOURCE_FILES)}")


if __name__ == "__main__":
    main()
